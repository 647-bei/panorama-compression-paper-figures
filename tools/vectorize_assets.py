"""Batch vectorize selected figure/table crops with pdf-figure-vector."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import fitz


FIG_KEYWORDS = re.compile(
    r"\b(overview|framework|architecture|pipeline|workflow|network|schematic|representation|encoding|compression|transform|feature|strategy|method|model|spherical|wavelet|frequency|reprojection|reconstruction|coding)\b",
    re.I,
)


def asset_is_raster(doc: fitz.Document, asset: dict) -> bool:
    page = doc[asset["page"]]
    r = fitz.Rect(asset["content_bbox"])
    area = max(1.0, r.get_area())
    im_area = 0.0
    for im in page.get_image_info(xrefs=True):
        ir = fitz.Rect(im["bbox"])
        inter = ir & r
        if inter.get_area() > 0:
            im_area += inter.get_area()
    drawings = 0
    for d in page.get_drawings():
        if (fitz.Rect(d["rect"]) & r).get_area() > 0:
            drawings += 1
    return im_area / area >= 0.60 and drawings < 25


def drawing_count(doc: fitz.Document, asset: dict) -> int:
    page = doc[asset["page"]]
    r = fitz.Rect(asset["content_bbox"])
    return sum(1 for d in page.get_drawings() if (fitz.Rect(d["rect"]) & r).get_area() > 0)


def selected_assets(manifest: dict) -> list[dict]:
    figures = [a for a in manifest["assets"] if a["kind"] == "figure"]
    tables = [a for a in manifest["assets"] if a["kind"] == "table"]
    chosen = []
    # Always keep the first figure, then architecture/method/representation
    # figures.  This bounds the batch while retaining the assets most useful
    # for rebuilding a model diagram.
    if figures:
        chosen.append(figures[0])
    for a in figures[1:]:
        if FIG_KEYWORDS.search(a["caption"]):
            chosen.append(a)
    # Avoid producing a huge duplicate set for papers with many qualitative
    # plots; retain at most six figures per paper.
    unique = []
    seen = set()
    for a in chosen:
        key = (a["page"], a["label"])
        if key not in seen:
            unique.append(a)
            seen.add(key)
    chosen = unique[:6] + tables
    return chosen


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PDFVEC_PREVIEW"] = "none"
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout[-4000:]


def svg_has_content(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 200:
        return False
    text = path.read_text(encoding="utf-8", errors="ignore")
    return any(tag in text for tag in ("<path", "<text", "<image"))


def main() -> None:
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--skill", required=True)
    args = ap.parse_args()
    root = Path(args.root)
    skill = Path(args.skill)
    extract = skill / "scripts" / "extract_figure.py"
    trace = skill / "scripts" / "trace_image.py"
    verify = skill / "scripts" / "verify_pptx.py"
    summary = []
    for mf in sorted(root.glob("*/manifest.json")):
        slug = mf.parent
        manifest = json.loads(mf.read_text(encoding="utf-8"))
        pdf = slug / manifest["pdf"]
        if not pdf.exists():
            continue
        doc = fitz.open(pdf)
        records = []
        for a in selected_assets(manifest):
            family = "figures" if a["kind"] == "figure" else "tables"
            label = re.sub(r"[^A-Za-z0-9_.-]+", "_", a["label"])
            out = slug / family / "vector" / label
            out.mkdir(parents=True, exist_ok=True)
            bbox = ",".join(str(x) for x in a["content_bbox"])
            raster = asset_is_raster(doc, a)
            existing_svg = out / (label + ".svg")
            existing_pptx = out / (label + ".pptx")
            if existing_svg.exists() and svg_has_content(existing_svg):
                mode = "existing" if existing_pptx.exists() else "existing_svg_only"
                code, output = 0, "existing output reused"
            else:
                if existing_svg.exists():
                    existing_svg.unlink()
                if raster:
                    inp = slug / a["original"]
                    # Raster tracing produces an editable SVG path layer.  A
                    # native PPTX conversion of photo-like figures can be
                    # enormous and is not a faithful semantic reconstruction.
                    cmd = [sys.executable, str(trace), "--image", str(inp), "--out", str(out), "--name", label, "--preset", "diagram", "--no-qa", "--no-pptx"]
                    mode = "raster_trace_svg_only"
                else:
                    cmd = [sys.executable, str(extract), "--pdf", str(pdf), "--page", str(a["page"]), "--bbox", bbox, "--out", str(out), "--name", label, "--no-open", "--no-clean"]
                    mode = "pdf_vector"
                    # Dense plots and scanned tables can contain tens of
                    # thousands of paths; SVG remains editable, while PPTX
                    # conversion can monopolize memory for many minutes.
                    if drawing_count(doc, a) > 1500:
                        cmd.append("--no-pptx")
                        mode = "pdf_vector_svg_only"
                code, output = run(cmd, skill)
                if (code != 0 or not svg_has_content(existing_svg)) and not raster:
                    # Some publishers flatten a whole figure/table into one
                    # page image or expose no drawing sequence.  Fall back to
                    # the preserved crop so the asset still has a visible,
                    # auditable SVG result.
                    inp = slug / a["original"]
                    fallback = [sys.executable, str(trace), "--image", str(inp), "--out", str(out), "--name", label, "--preset", "diagram", "--no-qa", "--no-pptx"]
                    fcode, fout = run(fallback, skill)
                    output = output + "\n[FALLBACK]\n" + fout
                    code = fcode
                    mode = "fallback_raster_trace_svg_only"
            files = []
            if code == 0:
                for ext in (".svg", ".pptx"):
                    p = out / (label + ext)
                    if p.exists():
                        files.append(str(p.relative_to(slug)).replace("\\", "/"))
            qa = []
            pptx = out / (label + ".pptx")
            if pptx.exists():
                vcode, vout = run([sys.executable, str(verify), "--pptx", str(pptx)], skill)
                qa.append({"verify_pptx_code": vcode, "verify_pptx_tail": vout})
            a["vector"] = files
            a["vector_mode"] = mode
            a["vector_exit_code"] = code
            a["vector_log_tail"] = output
            a["vector_qa"] = qa
            records.append({"label": a["label"], "kind": a["kind"], "mode": mode, "exit_code": code, "files": files})
        manifest["vectorized"] = records
        mf.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        summary.append({"paper": slug.name, "selected": len(records), "success": sum(r["exit_code"] == 0 for r in records)})
        print(slug.name, len(records), "selected", sum(r["exit_code"] == 0 for r in records), "success")
    (root / "vectorization_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
