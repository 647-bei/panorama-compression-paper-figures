"""Locate figure/table captions, render their page regions, and write a manifest.

The script intentionally keeps the original PDF untouched.  Coordinates in the
manifest are PDF points with a zero-based page index.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz


CAPTION_RE = re.compile(r"^\s*(?:fig(?:ure)?\.?\s*\d+[a-z]?|table\s+\d+[a-z]?)\s*[.:|]", re.I)
FIG_RE = re.compile(r"^\s*(?:fig(?:ure)?\.?\s*\d+[a-z]?)\s*[.:|]", re.I)


def rect_union(rects: list[fitz.Rect]) -> fitz.Rect | None:
    if not rects:
        return None
    out = fitz.Rect(rects[0])
    for r in rects[1:]:
        out |= r
    return out


def clamp_rect(r: fitz.Rect, page: fitz.Page) -> fitz.Rect:
    return fitz.Rect(
        max(0, r.x0), max(0, r.y0), min(page.rect.width, r.x1), min(page.rect.height, r.y1)
    )


def block_rects(page: fitz.Page) -> list[tuple[fitz.Rect, str]]:
    out: list[tuple[fitz.Rect, str]] = []
    for b in page.get_text("blocks"):
        if len(b) < 7 or not b[4].strip():
            continue
        r = fitz.Rect(b[:4])
        out.append((r, "text"))
    for d in page.get_drawings():
        r = fitz.Rect(d["rect"])
        if r.get_area() >= 2:
            out.append((r, "drawing"))
    for im in page.get_image_info(xrefs=True):
        r = fitz.Rect(im["bbox"])
        if r.get_area() >= 2:
            out.append((r, "image"))
    return out


def find_caption_blocks(page: fitz.Page) -> list[tuple[fitz.Rect, str, str]]:
    found = []
    for b in page.get_text("blocks"):
        if len(b) < 7:
            continue
        text = re.sub(r"\s+", " ", b[4]).strip()
        if not CAPTION_RE.match(text):
            continue
        kind = "figure" if FIG_RE.match(text) else "table"
        found.append((fitz.Rect(b[:4]), text, kind))
    return found


def candidate_bbox(page: fitz.Page, cap: fitz.Rect, kind: str, objects: list[tuple[fitz.Rect, str]]) -> fitz.Rect:
    if kind == "figure":
        # Figure captions normally follow the artwork.  Limit the look-back to
        # avoid absorbing a preceding paragraph or a previous figure.
        objs = [
            r for r, typ in objects
            if r.y1 <= cap.y0 + 3 and r.y1 >= max(0, cap.y0 - 330)
            and (typ != "text" or r.height >= 5)
        ]
        if not objs:
            return clamp_rect(fitz.Rect(0, max(0, cap.y0 - 220), page.rect.width, cap.y0), page)
        u = rect_union(objs)
        assert u is not None
        return clamp_rect(u, page)
    # Table captions normally precede the table.  Include the nearby tabular
    # region, but stop before the next caption or far-away paragraph.
    # Keep the table in the same column as its caption.  This matters for
    # two-column papers where the other column contains unrelated body text.
    cap_width = max(1.0, cap.width)
    objs = []
    for r, typ in objects:
        overlap = max(0.0, min(r.x1, cap.x1) - max(r.x0, cap.x0))
        same_column = overlap / min(max(1.0, r.width), cap_width) >= 0.20 or cap_width > page.rect.width * 0.70
        if r.y0 >= cap.y1 - 3 and r.y0 <= min(page.rect.height, cap.y1 + 300) and same_column and (typ != "text" or r.height >= 5):
            objs.append(r)
    if not objs:
        return clamp_rect(fitz.Rect(0, cap.y1, page.rect.width, min(page.rect.height, cap.y1 + 220)), page)
    u = rect_union(objs)
    assert u is not None
    return clamp_rect(u, page)


def render(page: fitz.Page, rect: fitz.Rect, out: Path, zoom: float = 4.0) -> None:
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect, alpha=False)
    pix.save(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="paper collection root")
    ap.add_argument("--zoom", type=float, default=4.0)
    ap.add_argument("--page-renders", action="store_true")
    args = ap.parse_args()
    root = Path(args.root)
    all_records = []
    for pdf in sorted(root.glob("*/pdf/*.pdf")):
        slug_dir = pdf.parent.parent
        doc = fitz.open(pdf)
        records = []
        for page_no, page in enumerate(doc):
            if args.page_renders:
                (slug_dir / "page_renders").mkdir(parents=True, exist_ok=True)
                render(page, page.rect, slug_dir / "page_renders" / f"page_{page_no:03d}.png", 1.5)
            captions = find_caption_blocks(page)
            if not captions:
                continue
            objects = block_rects(page)
            for idx, (cap, text, kind) in enumerate(captions, start=1):
                label_m = re.match(r"\s*(?:fig(?:ure)?\.?|table)\s*([0-9]+[a-z]?)", text, re.I)
                label = ("Fig" if kind == "figure" else "Table") + (label_m.group(1) if label_m else f"p{page_no+1}_{idx}")
                label = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
                content = candidate_bbox(page, cap, kind, objects)
                # Keep the caption in the original raster for auditability.
                if kind == "figure":
                    crop = fitz.Rect(content.x0, content.y0, content.x1, min(page.rect.height, cap.y1 + 3))
                else:
                    crop = fitz.Rect(min(content.x0, cap.x0), max(0, cap.y0 - 3), content.x1, content.y1)
                crop = clamp_rect(crop, page)
                out_dir = slug_dir / ("figures" if kind == "figure" else "tables") / "original"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / f"{label}_p{page_no:03d}.png"
                render(page, crop, out_path, args.zoom)
                records.append({
                    "kind": kind,
                    "label": label,
                    "page": page_no,
                    "caption": text,
                    "caption_bbox": [round(x, 3) for x in cap],
                    "content_bbox": [round(x, 3) for x in content],
                    "crop_bbox": [round(x, 3) for x in crop],
                    "original": str(out_path.relative_to(slug_dir)).replace("\\", "/"),
                    "vector": [],
                })
        manifest = {
            "paper": slug_dir.name,
            "pdf": str(pdf.relative_to(slug_dir)).replace("\\", "/"),
            "pages": len(doc),
            "assets": records,
            "notes": ["Coordinates use PDF points and page indexes start at 0.", "Original crops retain the caption for auditability."],
        }
        (slug_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        all_records.append(manifest)
        print(f"{slug_dir.name}: {len(records)} candidates")
    (root / "asset_candidates.json").write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
