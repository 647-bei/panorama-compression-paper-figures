"""Validate downloaded PDFs and generated figure/table assets."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import fitz
from PIL import Image


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report = {"pdfs": [], "pngs": [], "svgs": [], "pptx": [], "manifests": [], "errors": []}
    for p in sorted(root.glob("*/pdf/*.pdf")):
        try:
            head = p.read_bytes()[:5]
            doc = fitz.open(p)
            ok = head == b"%PDF-" and len(doc) > 0
            report["pdfs"].append({"file": str(p.relative_to(root)), "ok": ok, "pages": len(doc), "bytes": p.stat().st_size})
            if not ok:
                report["errors"].append(str(p))
        except Exception as exc:
            report["errors"].append(f"PDF {p}: {exc}")
    for p in sorted(root.glob("*/figures/original/*.png")) + sorted(root.glob("*/tables/original/*.png")):
        try:
            with Image.open(p) as im:
                im.verify()
            with Image.open(p) as im:
                w, h = im.size
            report["pngs"].append({"file": str(p.relative_to(root)), "ok": w > 0 and h > 0, "size": [w, h]})
        except Exception as exc:
            report["errors"].append(f"PNG {p}: {exc}")
    for p in sorted(root.rglob("*.svg")):
        try:
            tree = ET.parse(p)
            root_tag = tree.getroot().tag.lower()
            text = p.read_text(encoding="utf-8", errors="ignore")
            # Native PDF extraction may use polygons, polylines, rectangles and
            # circles instead of path/text/image nodes.  Treat any drawable SVG
            # primitive as valid; the PPTX verifier separately checks editability.
            drawable = ("<path", "<text", "<image", "<polygon", "<polyline", "<rect", "<circle", "<ellipse", "<line")
            ok = root_tag.endswith("svg") and any(token in text for token in drawable)
            report["svgs"].append({"file": str(p.relative_to(root)), "ok": ok, "bytes": p.stat().st_size})
            if not ok:
                report["errors"].append(f"SVG {p}")
        except Exception as exc:
            report["errors"].append(f"SVG {p}: {exc}")
    for p in sorted(root.rglob("*.pptx")):
        try:
            with zipfile.ZipFile(p) as z:
                names = set(z.namelist())
                ok = "ppt/presentation.xml" in names and "[Content_Types].xml" in names
            report["pptx"].append({"file": str(p.relative_to(root)), "ok": ok, "bytes": p.stat().st_size})
            if not ok:
                report["errors"].append(f"PPTX {p}")
        except Exception as exc:
            report["errors"].append(f"PPTX {p}: {exc}")
    for p in sorted(root.glob("*/manifest.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            page_count = data.get("pages", 0)
            bad_pages = [a.get("page") for a in data.get("assets", []) if not isinstance(a.get("page"), int) or a.get("page") < 0 or a.get("page") >= page_count]
            missing_original = [a.get("original") for a in data.get("assets", []) if not (p.parent / a.get("original", "")).exists()]
            ok = bool(data.get("metadata")) and not bad_pages and not missing_original
            report["manifests"].append({"file": str(p.relative_to(root)), "ok": ok, "assets": len(data.get("assets", [])), "vectorized": len(data.get("vectorized", [])), "bad_pages": bad_pages, "missing_original": missing_original})
            if not ok:
                report["errors"].append(f"manifest {p}")
        except Exception as exc:
            report["errors"].append(f"manifest {p}: {exc}")
    report["counts"] = {k: len(v) for k, v in report.items() if isinstance(v, list)}
    report["ok"] = not report["errors"]
    (root / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "counts": report["counts"], "errors": report["errors"][:10]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
