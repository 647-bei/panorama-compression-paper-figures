"""Batch vectorize selected figure/table crops with pdf-figure-vector."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import fitz


def svg_wrapper_pptx(svg: Path, source_png: Path, output: Path) -> bool:
    """Create a fast PPTX containing the traced SVG as an editable SVG object.

    Native freeform conversion is preferred when it is tractable. For raster
    heavy figures, embedding the already traced SVG keeps the slide crisp and
    lets PowerPoint select, resize, recolor, and ungroup the SVG object without
    spending minutes expanding tens of thousands of paths into separate shapes.
    """
    try:
        from pptx import Presentation
        from pptx.util import Inches
        from PIL import Image

        with Image.open(source_png) as image:
            width, height = image.size
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide_w, slide_h = prs.slide_width, prs.slide_height
        scale = min(slide_w / width, slide_h / height)
        pic_w, pic_h = int(width * scale), int(height * scale)
        left, top = int((slide_w - pic_w) / 2), int((slide_h - pic_h) / 2)
        slide.shapes.add_picture(str(source_png), left, top, width=pic_w, height=pic_h)
        with tempfile.TemporaryDirectory(prefix="svgwrap_") as temp:
            base = Path(temp) / "base.pptx"
            prs.save(base)
            replacement = Path(temp) / "replaced.pptx"
            with zipfile.ZipFile(base, "r") as zin, zipfile.ZipFile(replacement, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    name = item.filename
                    if name == "ppt/media/image1.png":
                        continue
                    data = zin.read(name)
                    if name == "ppt/slides/_rels/slide1.xml.rels":
                        root = ET.fromstring(data)
                        for rel in root:
                            if rel.attrib.get("Target", "").endswith("media/image1.png"):
                                rel.attrib["Target"] = "../media/traced.svg"
                        data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                    elif name == "[Content_Types].xml":
                        root = ET.fromstring(data)
                        ns = "http://schemas.openxmlformats.org/package/2006/content-types"
                        if not any(el.attrib.get("PartName") == "/ppt/media/traced.svg" for el in root):
                            ET.SubElement(root, "{" + ns + "}Override", {
                                "PartName": "/ppt/media/traced.svg",
                                "ContentType": "image/svg+xml",
                            })
                        data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                    zout.writestr(item, data)
                zout.writestr("ppt/media/traced.svg", svg.read_bytes())
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(replacement.read_bytes())
        return output.exists() and output.stat().st_size > 1000
    except Exception:
        return False


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
    # Rebuild every figure.  Tables are intentionally excluded: the website
    # provides their source as LaTeX and the user requested no table SVG/PPTX.
    # Keeping the full figure set also makes the output count match the
    # caption-derived figure count in each paper.
    return figures


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PDFVEC_PREVIEW"] = "none"
    p = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
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
        pdf = (slug / manifest["pdf"]).resolve()
        if not pdf.exists():
            continue
        doc = fitz.open(pdf)
        records = []
        for a in selected_assets(manifest):
            family = "figures" if a["kind"] == "figure" else "tables"
            label = re.sub(r"[^A-Za-z0-9_.-]+", "_", a["label"])
            out = (slug / family / "vector" / label).resolve()
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
                    inp = (slug / a["original"]).resolve()
                    # Raster tracing produces editable SVG paths and a PPTX
                    # made from those paths.  Text in a traced raster figure
                    # is path-editable rather than semantic text-editable.
                    cmd = [sys.executable, str(trace), "--image", str(inp), "--out", str(out), "--name", label, "--preset", "diagram", "--no-qa", "--no-pptx"]
                    mode = "raster_trace_svg"
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
                    inp = (slug / a["original"]).resolve()
                    fallback = [sys.executable, str(trace), "--image", str(inp), "--out", str(out), "--name", label, "--preset", "diagram", "--no-qa", "--no-pptx"]
                    fcode, fout = run(fallback, skill)
                    output = output + "\n[FALLBACK]\n" + fout
                    code = fcode
                    mode = "fallback_raster_trace"
            # If native path expansion was skipped (raster tracing or a dense
            # PDF drawing), keep a PPTX download by embedding the traced SVG as
            # one editable SVG object on a slide.
            source_png = (slug / a["original"]).resolve()
            if existing_svg.exists() and not existing_pptx.exists() and source_png.exists():
                if svg_wrapper_pptx(existing_svg, source_png, existing_pptx):
                    mode = mode + "+svg_pptx_wrapper"
            files = []
            if code == 0:
                for ext in (".svg", ".pptx"):
                    p = out / (label + ext)
                    if p.exists():
                        files.append(str(p.relative_to(slug.resolve())).replace("\\", "/"))
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
