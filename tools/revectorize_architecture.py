"""Rebuild architecture/framework figures as actual editable SVG/PPTX.

Visual comparison plots remain screenshot assets.  This pass targets captions
that identify a pipeline, architecture, framework, module or schematic and
replaces any failed full-image PPTX wrapper with native PDF extraction or
path-traced editable shapes for raster-only source figures.
"""
from __future__ import annotations
import json, re, shutil, subprocess, sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(r"C:\Users\Admin\.codex\skills\pdf-figure-vector")
ARCH = re.compile(r"architecture|framework|pipeline|workflow|overview|schematic|structure\s+of|network\s+architecture|overall\s+network|model\s+architecture|module\s+design|block", re.I)

def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        return p.returncode, p.stdout[-3000:]
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        if isinstance(out, bytes): out = out.decode("utf-8", "replace")
        return 124, "timeout\n" + out[-3000:]

def verify(pptx: Path) -> tuple[bool, str]:
    if not pptx.exists(): return False, "missing pptx"
    code, out = run([sys.executable, str(SKILL/"scripts"/"verify_pptx.py"), "--pptx", str(pptx)], SKILL)
    return code == 0 and "[OK]" in out and "矢量形状: 0" not in out, out

def main() -> None:
    qa_path = ROOT / "metadata" / "expected_count_qa.json"
    allow = {r["paper"] for r in json.loads(qa_path.read_text(encoding="utf-8")).get("papers", []) if r.get("status") == "pass"}
    done = skipped = failed = 0
    for mf in sorted(ROOT.glob("*/manifest.json")):
        slug = mf.parent
        if allow and slug.name not in allow: continue
        d = json.loads(mf.read_text(encoding="utf-8"))
        pdf = slug / d["pdf"]
        if not pdf.exists(): continue
        doc = fitz.open(pdf)
        changed = False
        for a in d.get("assets", []):
            if a.get("kind") != "figure" or not ARCH.search(a.get("caption_en", a.get("caption", ""))): continue
            vdir = slug / "figures" / "vector" / a["label"]
            pptx = vdir / (a["label"] + ".pptx")
            ok, vout = verify(pptx)
            if ok:
                a["vector_qa_architecture"] = "verified_editable_shapes"
                continue
            if vdir.exists(): shutil.rmtree(vdir)
            vdir.mkdir(parents=True, exist_ok=True)
            label = a["label"]
            bbox = ",".join(str(x) for x in a["content_bbox"])
            page = str(a["page"])
            # Prefer native PDF element extraction.  For bitmap-only figures,
            # trace the crop into freeform paths and generate a shape-based PPTX.
            page_obj = doc[int(a["page"])]
            r = fitz.Rect(a["content_bbox"])
            area = max(1.0, r.get_area())
            im_area = sum(max(0.0, (fitz.Rect(im["bbox"]) & r).get_area()) for im in page_obj.get_image_info(xrefs=True))
            drawings = sum(1 for dr in page_obj.get_drawings() if (fitz.Rect(dr["rect"]) & r).get_area() > 0)
            raster = im_area / area >= 0.60 and drawings < 25
            if raster:
                cmd = [sys.executable, str(SKILL/"scripts"/"trace_image.py"), "--image", str(slug/a["original"]), "--out", str(vdir), "--name", label, "--preset", "diagram", "--no-qa"]
                mode = "architecture_raster_trace_editable_shapes"
            else:
                cmd = [sys.executable, str(SKILL/"scripts"/"extract_figure.py"), "--pdf", str(pdf), "--page", page, "--bbox", bbox, "--out", str(vdir), "--name", label, "--no-open", "--no-clean"]
                mode = "architecture_pdf_native_editable_shapes"
            code, out = run(cmd, SKILL)
            ok, vout = verify(pptx)
            if not ok and not raster:
                cmd = [sys.executable, str(SKILL/"scripts"/"trace_image.py"), "--image", str(slug/a["original"]), "--out", str(vdir), "--name", label, "--preset", "diagram", "--no-qa"]
                mode = "architecture_raster_trace_editable_shapes_fallback"
                code, out = run(cmd, SKILL)
                ok, vout = verify(pptx)
            a["vector"] = []
            for ext in (".svg", ".pptx"):
                path = vdir / (label + ext)
                if path.exists(): a["vector"].append(str(path.relative_to(slug)).replace("\\", "/"))
            a["vector_mode"] = mode if ok else mode + "_FAILED_VERIFY"
            a["vector_exit_code"] = code
            a["vector_qa_architecture"] = vout[-1500:]
            changed = True
            if ok: done += 1
            else: failed += 1
            print(slug.name, label, mode, "OK" if ok else "FAILED", flush=True)
        if changed: mf.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        doc.close()
    print(json.dumps({"rebuilt": done, "failed": failed}, ensure_ascii=False))

if __name__ == "__main__": main()
