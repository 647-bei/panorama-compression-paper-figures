"""Locate figure/table captions and render caption-free content crops.

The script intentionally keeps the original PDF untouched. Coordinates in the
manifest are PDF points with a zero-based page index. A figure/table is treated
as one page region: panel labels and text inside the artwork are retained, but
the surrounding caption and unrelated body paragraphs are excluded.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz


LABEL_TOKEN = r"(?:\d+[a-z]?|[ivxlcdm]+)"
# Many IEEE PDFs emit table captions as an uppercase label on its own line
# (for example ``TABLE II``) followed by the descriptive title.  Accept an
# end-of-label or title boundary while keeping the body-reference filters
# below responsible for rejecting prose such as ``listed in Table II``.
CAPTION_RE = re.compile(
    rf"(?:^|\s)(?:fig(?:ure)?\.?\s*{LABEL_TOKEN}|table\s*{LABEL_TOKEN})"
    rf"\s*(?:[.:|]|(?=\s+[A-Z(])|$)", re.I
)
FIG_RE = re.compile(rf"^\s*(?:fig(?:ure)?\.?\s*{LABEL_TOKEN})\s*[.:|]", re.I)


def roman_to_int(value: str) -> str:
    if value.isdigit():
        return value
    total = 0
    prev = 0
    for char in value.upper()[::-1]:
        number = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}.get(char, 0)
        total += -number if number < prev else number
        prev = max(prev, number)
    return str(total or value)


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


def text_blocks(page: fitz.Page) -> list[tuple[fitz.Rect, str]]:
    """Return text blocks with their line count for paragraph filtering."""
    out: list[tuple[fitz.Rect, str]] = []
    for b in page.get_text("blocks"):
        if len(b) < 7 or not b[4].strip():
            continue
        out.append((fitz.Rect(b[:4]), b[4]))
    return out


def visual_rects(page: fitz.Page) -> list[fitz.Rect]:
    """Collect page graphics and images, excluding page-wide furniture rules."""
    out: list[fitz.Rect] = []
    page_w, page_h = page.rect.width, page.rect.height
    for drawing in page.get_drawings():
        r = fitz.Rect(drawing["rect"])
        # A few IEEE/Nature PDFs contain a page-sized background drawing. It
        # must not join every caption's cluster or suppress the real artwork.
        if r.width >= page_w * 0.95 and r.height >= page_h * 0.95:
            continue
        # Table borders and chart grid lines can have zero area in the PDF
        # drawing model. Keep sufficiently long strokes while dropping tiny
        # glyph-like fragments.
        if r.get_area() < 0.8 and max(r.width, r.height) < 4:
            continue
        # Headers, footers and crop marks are not part of an asset. They are
        # usually a page-wide 1 pt rule and would otherwise join a figure.
        if r.height <= 2.5 and r.width >= page_w * 0.72 and (r.y0 < 48 or r.y1 > page_h - 48):
            continue
        out.append(r)
    for image in page.get_image_info(xrefs=True):
        r = fitz.Rect(image["bbox"])
        if r.get_area() >= 1.0:
            out.append(r)
    return out


def overlap_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
    overlap = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    return overlap / max(1.0, min(a.width, b.width))


def visual_clusters(rects: list[fitz.Rect], gap: float = 85.0) -> list[list[fitz.Rect]]:
    """Group graphics into vertically contiguous artwork regions."""
    if not rects:
        return []
    clusters: list[list[fitz.Rect]] = []
    for rect in sorted(rects, key=lambda r: (r.y0, r.x0)):
        if not clusters:
            clusters.append([rect])
            continue
        previous = clusters[-1]
        previous_y1 = max(r.y1 for r in previous)
        if rect.y0 <= previous_y1 + gap:
            previous.append(rect)
        else:
            clusters.append([rect])
    return clusters


def detected_table_boxes(page: fitz.Page) -> list[fitz.Rect]:
    """Use MuPDF's table detector when it finds a coherent table region."""
    try:
        found = page.find_tables().tables
    except Exception:
        return []
    return [fitz.Rect(table.bbox) for table in found if fitz.Rect(table.bbox).get_area() >= 20]


def merge_table_boxes(boxes: list[fitz.Rect], gap: float = 10.0) -> list[fitz.Rect]:
    """Merge row-wise detections that form one table."""
    merged: list[fitz.Rect] = []
    for box in sorted(boxes, key=lambda r: (r.y0, r.x0)):
        if not merged:
            merged.append(fitz.Rect(box))
            continue
        previous = merged[-1]
        if box.y0 <= previous.y1 + gap and overlap_ratio(box, previous) >= 0.15:
            merged[-1] = fitz.Rect(
                min(previous.x0, box.x0), min(previous.y0, box.y0),
                max(previous.x1, box.x1), max(previous.y1, box.y1),
            )
        else:
            merged.append(fitz.Rect(box))
    return merged


def table_text_bbox(
    page: fitz.Page,
    cap: fitz.Rect,
    next_cap: fitz.Rect | None,
    blocks: list[tuple[fitz.Rect, str]],
    direction: str = "below",
) -> fitz.Rect | None:
    """Infer a table extent from consecutive text rows.

    Some PDFs contain text tables with hairline rules that PyMuPDF cannot
    group reliably. In that case the short blocks immediately below the
    caption provide a better boundary than the next plot on the page.
    """
    page_w = page.rect.width
    if direction == "above":
        lower = max(0.0, cap.y0 - 260)
        upper = cap.y0 + 2
    else:
        lower = cap.y1 - 2
        upper = next_cap.y0 - 4 if next_cap and next_cap.y0 > cap.y1 + 8 else page.rect.height
    candidates: list[tuple[fitz.Rect, str]] = []
    for rect, text in blocks:
        if direction == "above":
            if rect.y1 < lower or rect.y1 >= upper:
                continue
        elif rect.y0 < lower or rect.y0 >= upper:
            continue
        if cap.width < page_w * 0.70 and overlap_ratio(rect, cap) < 0.15:
            continue
        compact = re.sub(r"\s+", "", text)
        if rect.height > 30 and len(compact) > 70:
            continue
        candidates.append((rect, text))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0].y0, item[0].x0), reverse=direction == "above")
    first = candidates[0][0]
    if direction == "above":
        if cap.y0 - first.y1 > 52:
            return None
    elif first.y0 - cap.y1 > 52:
        return None
    selected = [first]
    last_y = first.y1
    for rect, _text in candidates[1:]:
        gap = (last_y - rect.y1) if direction == "above" else (rect.y0 - last_y)
        if gap > 34:
            break
        selected.append(rect)
        last_y = min(last_y, rect.y0) if direction == "above" else max(last_y, rect.y1)
    if len(selected) < 2:
        return None
    return rect_union(selected)


def cluster_bbox(cluster: list[fitz.Rect]) -> fitz.Rect:
    # ``Rect.__or__`` can discard zero-height/zero-width PDF strokes. Tables
    # often consist of exactly those strokes, so compute extrema explicitly.
    return fitz.Rect(
        min(r.x0 for r in cluster),
        min(r.y0 for r in cluster),
        max(r.x1 for r in cluster),
        max(r.y1 for r in cluster),
    )


def caption_column_cluster(cluster: list[fitz.Rect], cap: fitz.Rect, page_width: float) -> list[fitz.Rect]:
    """Select one column when a vertically adjacent cluster contains two tables."""
    if cap.width >= page_width * 0.70:
        return cluster
    groups: list[list[fitz.Rect]] = []
    for rect in sorted(cluster, key=lambda r: (r.x0, r.y0)):
        if not groups:
            groups.append([rect])
            continue
        previous = groups[-1]
        previous_x1 = max(r.x1 for r in previous)
        if rect.x0 <= previous_x1 + 14:
            previous.append(rect)
        else:
            groups.append([rect])
    if len(groups) <= 1:
        return cluster
    cluster_box = cluster_bbox(cluster)
    if cluster_box.width >= page_width * 0.58:
        wide_groups = [group for group in groups if cluster_bbox(group).width >= page_width * 0.24]
        if len(wide_groups) < 2:
            return cluster
    scored = []
    for group in groups:
        box = cluster_bbox(group)
        scored.append((overlap_ratio(box, cap), group))
    scored.sort(key=lambda item: item[0], reverse=True)
    # If the cluster is made of separate left/right columns, use the caption's
    # column. A single full-width figure usually has touching image tiles and
    # remains one group.
    return scored[0][1] if scored[0][0] >= 0.15 else cluster


def choose_visual_cluster(
    page: fitz.Page,
    cap: fitz.Rect,
    kind: str,
    graphics: list[fitz.Rect],
    blocks: list[tuple[fitz.Rect, str]],
    previous_cap: fitz.Rect | None,
    next_cap: fitz.Rect | None,
    table_boxes: list[fitz.Rect] | None = None,
) -> fitz.Rect | None:
    """Choose the whole artwork region adjacent to a caption.

    The previous implementation unioned every text block in a look-back window,
    which absorbed two-column body text and sometimes dropped the top row of a
    large figure. Clustering only drawings/images keeps a multi-panel figure as
    one region while leaving prose outside it.
    """
    page_w, page_h = page.rect.width, page.rect.height
    if kind == "figure":
        # Raster figures may have an image bbox that overlaps the first few
        # points of the caption. Include that small overlap, then the final
        # crop is clipped at the caption boundary.
        candidates = [r for r in graphics if r.y0 < cap.y0 and r.y1 <= cap.y0 + 12]
        if not candidates:
            candidates = [r for r in graphics if r.y0 >= cap.y1 - 4]
        # A previous caption in the other column belongs to a separate
        # side-by-side figure and must not clip the current figure's artwork.
        previous_same_column = previous_cap and overlap_ratio(previous_cap, cap) >= 0.50
        lower = previous_cap.y1 - 6 if previous_same_column else 0
        candidates = [r for r in candidates if r.y1 >= lower]
    else:
        # MuPDF's table detector is reliable for bordered and text tables. A
        # few publishers place the caption below the table, so search both
        # directions and prefer the nearest same-column region.
        table_candidates = merge_table_boxes(table_boxes or [])
        later_cap = next_cap if next_cap and next_cap.y0 > cap.y1 + 8 else None
        valid_below = []
        valid_above = []
        for box in table_candidates:
            same_column = cap.width >= page_w * 0.70 or overlap_ratio(box, cap) >= 0.15
            if not same_column:
                continue
            if box.y0 >= cap.y1 - 3 and box.y0 - cap.y1 <= 320:
                if not later_cap or box.y0 <= later_cap.y0 + 6:
                    valid_below.append(box)
            # Some PDFs place the caption line inside the detector's final
            # table bbox. Accept that small overlap and let the nearest table
            # win; the crop is still bounded by the table detector itself.
            above_ok = box.y1 <= cap.y0 + 3 or (
                box.y0 < cap.y0 and box.y1 <= cap.y1 + 3 and cap.y0 - box.y1 <= 40
            )
            if above_ok and cap.y0 - box.y1 <= 160:
                valid_above.append(box)
        text_box = table_text_bbox(page, cap, later_cap, blocks, "below")
        if valid_above:
            valid_above.sort(key=lambda r: (cap.y0 - r.y1, -r.get_area()))
            return valid_above[0]
        if valid_below:
            valid_below.sort(key=lambda r: (r.y0 - cap.y1, -r.get_area()))
            return valid_below[0]
        if text_box is not None:
            return text_box

        candidates = [r for r in graphics if r.y0 >= cap.y1 - 4]
        upper = later_cap.y0 + 6 if later_cap else page_h
        candidates = [r for r in candidates if r.y0 <= upper]
        # Captions below a table need the preceding visual cluster. Only use it
        # when no meaningful graphics were found after the caption.
        if candidates and min((r.y0 for r in candidates), default=page_h) - cap.y1 <= 110:
            # The normal table-caption-above layout.
            pass
        else:
            candidates = []
        if not candidates:
            # Caption-below layout (used by several conference tables).
            if valid_above:
                valid_above.sort(key=lambda r: (cap.y0 - r.y1, -r.get_area()))
                return valid_above[0]
            text_box = table_text_bbox(page, cap, later_cap, blocks, "above")
            if text_box is not None:
                return text_box
            candidates = [r for r in graphics if r.y1 <= cap.y0 + 4 and r.y1 >= cap.y0 - 220]
    if not candidates:
        return None

    clusters = visual_clusters(candidates)
    scored: list[tuple[float, fitz.Rect]] = []
    for cluster in clusters:
        cluster = caption_column_cluster(cluster, cap, page_w)
        box = cluster_bbox(cluster)
        if kind == "figure":
            distance = max(0.0, cap.y0 - box.y1)
        else:
            above = box.y1 <= cap.y0 + 4
            distance = max(0.0, cap.y0 - box.y1) if above else max(0.0, box.y0 - cap.y1)
        x_match = overlap_ratio(box, cap)
        full_width = box.width >= page_w * 0.58
        # Captions can be split into a left-column text block even when the
        # artwork spans the full page. Full-width graphics should win on their
        # vertical proximity alone.
        score = distance + (0 if full_width else (1.0 - x_match) * 160.0)
        scored.append((score, box))
    scored.sort(key=lambda item: item[0])
    return scored[0][1]


def find_caption_blocks(page: fitz.Page) -> list[tuple[fitz.Rect, str, str]]:
    blocks = []
    # Use line bboxes instead of the enclosing PDF text block. In conference
    # PDFs, a table's rows and its caption are frequently emitted as one block;
    # the caption bbox must begin at the caption line so the table can be found
    # immediately above it and body rows are not treated as caption text.
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        lines = []
        for line in b.get("lines", []):
            spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
            if not spans:
                continue
            text = re.sub(r"\s+", " ", "".join(s["text"] for s in spans)).strip()
            rect = fitz.Rect(spans[0]["bbox"])
            for span in spans[1:]:
                rect |= fitz.Rect(span["bbox"])
            lines.append((rect, text))
        if not lines:
            continue
        block_rect = fitz.Rect(lines[0][0])
        for rect, _text in lines[1:]:
            block_rect |= rect
        full_text = " ".join(text for _rect, text in lines)
        marker = CAPTION_RE.search(full_text)
        if not marker:
            blocks.append((block_rect, full_text, False))
            continue
        # Locate the line containing the marker in the normalized line stream.
        cursor = 0
        line_index = 0
        for index, (_rect, line_text) in enumerate(lines):
            end = cursor + len(line_text)
            if marker.start() <= end:
                line_index = index
                break
            cursor = end + 1
        candidate_text = " ".join(text for _rect, text in lines[line_index:])
        local_marker = CAPTION_RE.search(candidate_text)
        if not local_marker:
            blocks.append((block_rect, full_text, False))
            continue
        prefix = candidate_text[:local_marker.start()].strip()
        token = local_marker.group(0).strip()
        prefix_lower = prefix.lower()
        # Abbreviated “Fig.” occurrences inside prose are almost always
        # references. Real captions in this collection either begin with Fig.
        # or use the full “Figure” label when a legend precedes it.
        if (
            re.match(r"fig(?:\.|\s)", token, re.I)
            and prefix
            and not re.fullmatch(r"(?:\([a-z]\)\s*)+", prefix, re.I)
        ):
            blocks.append((block_rect, full_text, False))
            continue
        body_cue = re.search(
            r"(?:as\s+shown|shown\s+in|see\s+(?:fig|figure|table)|in\s+(?:fig|figure|table)|"
            r"from\s+(?:fig|figure|table)|listed\s+in|reported\s+in|described\s+in|"
            r"illustrated\s+in|we\s+(?:visualize|list|show|compare|plot)|"
            r"results?\s+in|according\s+to)",
            prefix_lower,
        )
        if body_cue:
            blocks.append((block_rect, full_text, False))
            continue
        caption_rect = fitz.Rect(lines[line_index][0])
        for rect, _text in lines[line_index + 1:]:
            caption_rect |= rect
        text = candidate_text[local_marker.start():].strip()
        blocks.append((caption_rect, text, True))
    blocks.sort(key=lambda item: (item[0].y0, item[0].x0))
    found = []
    used: set[int] = set()
    for i, (rect, text, is_caption) in enumerate(blocks):
        if i in used or not is_caption:
            continue
        kind = "figure" if FIG_RE.match(text) else "table"
        parts = [text]
        rects = [rect]
        used.add(i)
        current = rect
        for j in range(i + 1, len(blocks)):
            next_rect, next_text, next_is_caption = blocks[j]
            if next_is_caption and re.match(r"\s*(?:fig(?:ure)?\.?\s*\d|table\s*\d)", next_text, re.I):
                break
            vertical_gap = next_rect.y0 - current.y1
            horizontal_gap = max(0.0, max(next_rect.x0 - current.x1, current.x0 - next_rect.x1))
            horizontal_overlap = max(0.0, min(next_rect.x1, current.x1) - max(next_rect.x0, current.x0))
            # Captions can be split across columns (Nature pages) or across
            # consecutive lines (two-column conference PDFs). Do not consume a
            # normal paragraph separated by a larger vertical gap.
            same_column = horizontal_overlap >= 0.5 * min(current.width, next_rect.width)
            side_by_side = horizontal_overlap <= 2 and horizontal_gap <= 30
            if kind == "table":
                # Table captions in this collection are single blocks. Keeping
                # the following block out is essential because it is usually
                # the table header immediately below the caption.
                continuation = False
            else:
                # Keep a caption's adjacent side-by-side text blocks, but do
                # not consume a normal paragraph in the same column below it.
                continuation = (
                    vertical_gap <= 4 and side_by_side
                    and next_rect.height <= max(24.0, current.height * 1.5)
                )
            if not continuation:
                break
            parts.append(next_text)
            rects.append(next_rect)
            used.add(j)
            current = fitz.Rect(
                min(current.x0, next_rect.x0), min(current.y0, next_rect.y0),
                max(current.x1, next_rect.x1), max(current.y1, next_rect.y1),
            )
        bbox = fitz.Rect(
            min(r.x0 for r in rects), min(r.y0 for r in rects),
            max(r.x1 for r in rects), max(r.y1 for r in rects),
        )
        found.append((bbox, " ".join(parts), kind))
    return sorted(found, key=lambda item: (item[0].y0, item[0].x0))


def add_inside_text(page: fitz.Page, box: fitz.Rect, cap: fitz.Rect, kind: str, blocks: list[tuple[fitz.Rect, str]]) -> fitz.Rect:
    """Include labels/axis text inside the artwork without pulling prose in."""
    selected = [box]
    for rect, text in blocks:
        # Nature article running headers ("Article", DOI, journal title) sit
        # just above full-width figures. They are page furniture, not artwork
        # labels, and must never enter the crop.
        if kind == "figure" and rect.y0 < 45 and (rect.x0 < 72 or rect.x1 > page.rect.width - 72):
            continue
        # A caption is never allowed back into the crop, even if it touches the
        # visual bbox. The crop itself is the final authority on that boundary.
        if kind == "figure" and rect.y1 > cap.y0 + 2:
            continue
        if kind == "table" and rect.y0 < cap.y1 - 2:
            continue
        x_overlap = overlap_ratio(rect, box)
        y_overlap = max(0.0, min(rect.y1, box.y1) - max(rect.y0, box.y0))
        inside = x_overlap >= 0.15 and y_overlap > 0
        # Small panel labels and axis titles may sit just outside a plotted
        # rectangle. Section headings above a figure are excluded; short
        # multiline x-axis labels below it are retained.
        above_edge = rect.height <= 10.5 and x_overlap >= 0.25 and abs(rect.y1 - box.y0) <= 24
        below_edge = (
            kind == "figure" and rect.height <= 36 and x_overlap >= 0.25
            and abs(rect.y0 - box.y1) <= 50
        )
        near_edge = above_edge or below_edge
        # Multi-line body paragraphs are never inferred as artwork labels
        # unless they are materially inside the visual region.
        compact = re.sub(r"\s+", "", text)
        # Long body paragraphs are broad or text-heavy. Multi-line panel and
        # x-axis labels can also have several lines, so line count alone must
        # not exclude them.
        paragraph = rect.height > 24 and (
            rect.width > page.rect.width * 0.45 or len(compact) > 120
        )
        if (inside or near_edge) and (inside or not paragraph):
            selected.append(rect)
    return clamp_rect(rect_union(selected) or box, page)


def candidate_bbox(
    page: fitz.Page,
    cap: fitz.Rect,
    kind: str,
    graphics: list[fitz.Rect],
    blocks: list[tuple[fitz.Rect, str]],
    previous_cap: fitz.Rect | None,
    next_cap: fitz.Rect | None,
    table_boxes: list[fitz.Rect] | None = None,
) -> fitz.Rect | None:
    visual = choose_visual_cluster(page, cap, kind, graphics, blocks, previous_cap, next_cap, table_boxes)
    if visual is None:
        # Do not fabricate a crop from an arbitrary page strip. Body text often
        # contains a reference such as “as shown in Fig. 4”; without an
        # adjacent graphic/table that is not an asset caption.
        return None
    visual = clamp_rect(visual, page)
    if kind == "figure" and visual.y1 > cap.y0:
        visual.y1 = cap.y0
        if visual.y1 <= visual.y0:
            return None
    if kind == "figure":
        distance = max(0.0, cap.y0 - visual.y1) if visual.y1 <= cap.y0 + 4 else max(0.0, visual.y0 - cap.y1)
    else:
        distance = max(0.0, cap.y0 - visual.y1) if visual.y1 <= cap.y0 + 4 else max(0.0, visual.y0 - cap.y1)
    # A real caption is close to its artwork. This guard removes body
    # references that happen to share a page with an unrelated figure.
    if distance > 160:
        return None
    return add_inside_text(page, visual, cap, kind, blocks)


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
            # The Nature PDF appends Extended Data after the numbered article
            # pages. Keep the article's five figures and two tables here; the
            # supplementary figures use a separate numbering namespace and
            # would otherwise collide with Fig. 1--5 in the web comparison.
            if slug_dir.name == "NMI_MultiResolution_2026" and page_no >= 14:
                continue
            if args.page_renders:
                (slug_dir / "page_renders").mkdir(parents=True, exist_ok=True)
                render(page, page.rect, slug_dir / "page_renders" / f"page_{page_no:03d}.png", 1.5)
            captions = find_caption_blocks(page)
            if not captions:
                continue
            graphics = visual_rects(page)
            blocks = text_blocks(page)
            table_boxes = detected_table_boxes(page)
            for idx, (cap, text, kind) in enumerate(captions, start=1):
                label_m = re.match(rf"\s*(?:fig(?:ure)?\.?|table)\s*({LABEL_TOKEN})", text, re.I)
                token = roman_to_int(label_m.group(1)) if label_m else f"p{page_no+1}_{idx}"
                label = ("Fig" if kind == "figure" else "Table") + token
                label = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
                # HEAL-SWIN's Table 9 is an appendix cross-reference printed
                # in the main text rather than a main-paper table region.
                if slug_dir.name == "HEAL-SWIN_CVPR2024" and label == "Table9":
                    continue
                previous_cap = captions[idx - 2][0] if idx > 1 else None
                next_cap = captions[idx][0] if idx < len(captions) else None
                content = candidate_bbox(page, cap, kind, graphics, blocks, previous_cap, next_cap, table_boxes)
                if content is None or content.get_area() < 4:
                    continue
                # The content bbox is the crop. It deliberately excludes the
                # caption; captions are rendered separately by the web viewer.
                crop = content
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
                    "caption_en": text,
                    "caption_zh": "",
                    "caption_bbox": [round(x, 3) for x in cap],
                    "content_bbox": [round(x, 3) for x in content],
                    "crop_bbox": [round(x, 3) for x in crop],
                    "original": str(out_path.relative_to(slug_dir)).replace("\\", "/"),
                    "vector": [],
                })
        # A body reference can still share a page with the real asset. Keep
        # one record per paper/label and retain the largest coherent crop;
        # genuine tables/figures are materially larger than the small text
        # fragment produced by a reference.
        unique: dict[tuple[str, str], dict] = {}
        for record in records:
            key = (record["kind"], record["label"])
            area = max(0.0, record["content_bbox"][2] - record["content_bbox"][0]) * max(
                0.0, record["content_bbox"][3] - record["content_bbox"][1]
            )
            old = unique.get(key)
            if old is None:
                unique[key] = record
                continue
            old_area = max(0.0, old["content_bbox"][2] - old["content_bbox"][0]) * max(
                0.0, old["content_bbox"][3] - old["content_bbox"][1]
            )
            if area > old_area:
                unique[key] = record
        records = sorted(unique.values(), key=lambda r: (r["page"], r["kind"], r["label"]))
        manifest = {
            "paper": slug_dir.name,
            "pdf": str(pdf.relative_to(slug_dir)).replace("\\", "/"),
            "pages": len(doc),
            "assets": records,
            "notes": ["Coordinates use PDF points and page indexes start at 0.", "Original crops contain only figure/table content; captions are stored as metadata for the web viewer."],
        }
        (slug_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        all_records.append(manifest)
        print(f"{slug_dir.name}: {len(records)} candidates")
    (root / "asset_candidates.json").write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
