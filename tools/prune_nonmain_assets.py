"""Remove manifest assets outside the verified main-text expected set.

Only papers with no missing expected labels are touched.  This removes
supplementary/appendix assets that were discovered by the caption scanner and
keeps the paper-level count gate auditable.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "metadata" / "expected_count_qa.json"

def remove_path(root: Path, rel: str | None) -> None:
    if not rel:
        return
    p = root / rel
    if p.exists() and p.is_file():
        p.unlink()

def main() -> None:
    qa = json.loads(QA.read_text(encoding="utf-8"))
    changed = 0
    for row in qa["papers"]:
        if row.get("missing") or not row.get("extra"):
            continue
        paper_dir = ROOT / row["paper"]
        manifest_path = paper_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = set()
        expected.update(("figure", x) for x in row.get("expected_figures", []))
        expected.update(("table", x) for x in row.get("expected_tables", []))
        kept = []
        for asset in manifest.get("assets", []):
            key = (asset.get("kind"), asset.get("label"))
            if key in expected:
                kept.append(asset)
                continue
            remove_path(paper_dir, asset.get("original"))
            vector = asset.get("vector") or []
            if isinstance(vector, str):
                vector = [vector]
            for rel in vector:
                remove_path(paper_dir, rel)
            remove_path(paper_dir, asset.get("latex"))
            changed += 1
        manifest["assets"] = kept
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(row["paper"], "removed", len(manifest.get("assets", [])) - len(kept), "extra assets")
    print("removed_assets", changed)

if __name__ == "__main__":
    main()
