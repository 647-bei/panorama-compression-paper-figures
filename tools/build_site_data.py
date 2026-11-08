"""Build the compact data file consumed by the GitHub Pages viewer."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_CAPTION = re.compile(
    r"architecture|framework|pipeline|workflow|overview|schematic|structure\s+of|"
    r"network\s+architecture|overall\s+network|model\s+architecture|module\s+design|block",
    re.I,
)
LABEL_RE = re.compile(r"^(?:Fig(?:ure)?|Table)\s*([0-9]+)([A-Za-z]?)$", re.I)


def position(label: str) -> tuple[str, int, str]:
    compact = re.sub(r"\s+", "", label)
    m = LABEL_RE.match(compact)
    if not m:
        return compact.lower(), 999999, ""
    number = int(m.group(1))
    suffix = m.group(2).lower()
    return f"{number}{suffix}", number, suffix


def main() -> None:
    papers_catalog = json.loads((ROOT / "papers.json").read_text(encoding="utf-8"))
    qa_path = ROOT / "metadata" / "expected_count_qa.json"
    qa_status = {}
    if qa_path.exists():
        qa_status = {row.get("paper"): row.get("status") for row in json.loads(qa_path.read_text(encoding="utf-8")).get("papers", [])}
    papers: dict[str, dict] = {}
    catalog_by_slug = {p.get("local_slug"): p for p in papers_catalog if p.get("local_slug")}
    for p in papers_catalog:
        slug = p.get("local_slug")
        if slug and qa_status.get(slug, "pass") == "pass":
            papers[slug] = {
                "id": slug,
                "title": p.get("title", slug),
                "venue": p.get("venue", ""),
                "venue_short": p.get("venue_short", p.get("venue", "")),
                "venue_full": p.get("venue_full", p.get("venue", "")),
                "venue_type": p.get("venue_type", ""),
                "year": p.get("year", ""),
                "classification": p.get("classification", ""),
                "cas_zone": p.get("cas_zone"),
                "cas_display": p.get("cas_display", ""),
                "ccf_rank": p.get("ccf_rank"),
                "ccf_scope": p.get("ccf_scope"),
                "ccf_display": p.get("ccf_display", ""),
                "ranking_display": p.get("ranking_display", ""),
                "official_url": p.get("official_url", ""),
                "pdf_url": p.get("pdf_url", ""),
                "access": p.get("access", ""),
                "metadata_only": True,
            }
    assets = []
    for manifest_path in sorted(ROOT.glob("*/manifest.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        slug = manifest_path.parent.name
        if qa_status.get(slug, "pass") != "pass":
            continue
        metadata = {**catalog_by_slug.get(slug, {}), **(data.get("metadata") or {})}
        papers[slug] = {
            "id": slug,
            "title": metadata.get("title", slug),
            "venue": metadata.get("venue", ""),
            "venue_short": metadata.get("venue_short", metadata.get("venue", "")),
            "venue_full": metadata.get("venue_full", metadata.get("venue", "")),
            "venue_type": metadata.get("venue_type", ""),
            "year": metadata.get("year", ""),
            "classification": metadata.get("classification", ""),
            "cas_zone": metadata.get("cas_zone"),
            "cas_display": metadata.get("cas_display", ""),
            "ccf_rank": metadata.get("ccf_rank"),
            "ccf_scope": metadata.get("ccf_scope"),
            "ccf_display": metadata.get("ccf_display", ""),
            "ranking_display": metadata.get("ranking_display", ""),
            "official_url": metadata.get("official_url", ""),
            "pdf_url": metadata.get("pdf_url", ""),
            "access": metadata.get("access", ""),
            "metadata_only": False,
        }
        for asset in data.get("assets", []):
            original = manifest_path.parent / asset.get("original", "")
            if not original.exists():
                continue
            pos, number, suffix = position(asset.get("label", ""))
            vectors = []
            caption_for_asset = asset.get("caption_en", asset.get("caption", ""))
            architecture_caption = asset.get("kind") == "figure" and ARCHITECTURE_CAPTION.search(str(caption_for_asset))
            vector_mode = str(asset.get("vector_mode", ""))
            editable_architecture = (
                vector_mode.startswith("architecture_") and not vector_mode.endswith("_FAILED_VERIFY")
            ) or asset.get("vector_qa_architecture") == "verified_editable_shapes"
            for vector in asset.get("vector", []):
                # Do not expose an image-only PPTX/SVG as an editable download
                # for an architecture/framework figure. Such figures remain
                # browsable as caption-free PNGs until a shape-level rebuild is
                # verified by pdf-figure-vector's PPTX checker.
                if architecture_caption and not editable_architecture:
                    continue
                vector_path = manifest_path.parent / vector
                if vector_path.exists():
                    vectors.append({"type": vector_path.suffix.lower().lstrip("."), "path": vector_path.relative_to(ROOT).as_posix()})
            latex_path = manifest_path.parent / asset.get("latex", "")
            assets.append({
                "id": f"{slug}:{asset.get('kind')}:{asset.get('label')}:{asset.get('page')}",
                "kind": asset.get("kind", "figure"),
                "paper_id": slug,
                "label": asset.get("label", ""),
                "position_key": pos,
                "position_number": number,
                "position_suffix": suffix,
                "page": asset.get("page", 0),
                "caption": asset.get("caption_en", asset.get("caption", "")),
                "caption_en": asset.get("caption_en", asset.get("caption", "")),
                "caption_zh": asset.get("caption_zh", ""),
                "original": original.relative_to(ROOT).as_posix(),
                "vectors": vectors,
                "vector_mode": vector_mode,
                "latex": latex_path.relative_to(ROOT).as_posix() if asset.get("latex") and latex_path.exists() else "",
                "latex_mode": asset.get("latex_mode", ""),
            })
    for p in papers.values():
        p["asset_count"] = sum(1 for a in assets if a["paper_id"] == p["id"])
    result = {
        "generated": date.today().isoformat(),
        "papers": sorted(papers.values(), key=lambda p: p["id"].lower()),
        "assets": assets,
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    (ROOT / "site_data.json").write_text(serialized, encoding="utf-8")
    (ROOT / "site_data.js").write_text("window.SITE_DATA = " + serialized + ";\n", encoding="utf-8")
    print(f"papers={len(result['papers'])} assets={len(assets)}")


if __name__ == "__main__":
    main()
