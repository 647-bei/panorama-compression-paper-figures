"""Compact oversized vector outputs for reliable GitHub Pages hosting.

Native PDF expansion can create tens of MB of paths and bundled fonts for a
single figure.  For those assets, keep the high-resolution original PNG and
replace the heavy SVG/PPTX with a lightweight SVG/PPTX wrapper that preserves
the exact visual crop and remains selectable as one object in PowerPoint.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.util import Inches

ROOT = Path(__file__).resolve().parents[1]
THRESHOLD = 1_000_000

def wrapper_svg(label: str, original: Path, vector_dir: Path) -> None:
    rel = Path("..", "..", "original", original.name).as_posix()
    with Image.open(original) as im:
        w, h = im.size
    vector_dir.joinpath(f"{label}.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}"><image x="0" y="0" width="{w}" height="{h}" '
        f'xlink:href="{rel}" href="{rel}"/></svg>\n', encoding="utf-8")

def wrapper_pptx(label: str, original: Path, out: Path) -> None:
    with Image.open(original) as im:
        w, h = im.size
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    sw, sh = prs.slide_width, prs.slide_height
    scale = min(sw / w, sh / h)
    pw, ph = int(w * scale), int(h * scale)
    slide.shapes.add_picture(str(original), int((sw-pw)/2), int((sh-ph)/2), width=pw, height=ph)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)

def main() -> None:
    compacted = 0
    for mf in sorted(ROOT.glob("*/manifest.json")):
        data = json.loads(mf.read_text(encoding="utf-8"))
        paper = mf.parent
        for asset in data.get("assets", []):
            if asset.get("kind") != "figure":
                continue
            original = paper / asset.get("original", "")
            if not original.exists():
                continue
            label = asset.get("label", "Figure")
            vdir = paper / "figures" / "vector" / label
            svg = vdir / f"{label}.svg"
            pptx = vdir / f"{label}.pptx"
            if not svg.exists() or svg.stat().st_size <= THRESHOLD:
                continue
            for child in list(vdir.iterdir()):
                if child.is_dir():
                    shutil.rmtree(child)
                elif child.name not in {svg.name, pptx.name}:
                    child.unlink()
            wrapper_svg(label, original, vdir)
            wrapper_pptx(label, original, pptx)
            asset["vector_mode"] = (asset.get("vector_mode", "") + "+compact_raster_wrapper").strip("+")
            compacted += 1
        mf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("compacted", compacted)

if __name__ == "__main__":
    main()
