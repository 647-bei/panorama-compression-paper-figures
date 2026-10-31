"""Merge catalog metadata into per-paper asset manifests."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    papers = json.loads((root / "papers.json").read_text(encoding="utf-8"))
    by_slug = {p.get("local_slug"): p for p in papers if p.get("local_slug")}
    for mf in root.glob("*/manifest.json"):
        data = json.loads(mf.read_text(encoding="utf-8"))
        meta = by_slug.get(mf.parent.name)
        if meta:
            data["metadata"] = meta
        mf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Keep metadata-only entries auditable without inventing a PDF manifest.
    for meta in papers:
        slug = meta.get("local_slug")
        if not slug or meta.get("access") != "metadata_only_pdf_route_blocked":
            continue
        d = root / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
