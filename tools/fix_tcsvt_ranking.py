from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def fix(m: dict) -> bool:
    if "TCSVT" not in str(m.get("venue", "")) and "TCSVT" not in str(m.get("venue_short", "")):
        return False
    m["cas_zone"] = 1
    m["cas_display"] = "中科院 1区 TOP（2025）"
    m["ranking_display"] = "中科院 1区 TOP（2025）"
    m["classification"] = "中科院 1区 TOP（2025）"
    return True

def main() -> None:
    papers = ROOT / "papers.json"
    data = json.loads(papers.read_text(encoding="utf-8"))
    changed = 0
    for p in data:
        if fix(p): changed += 1
    papers.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for mf in ROOT.glob("*/manifest.json"):
        d = json.loads(mf.read_text(encoding="utf-8"))
        m = d.get("metadata") or {}
        if fix(m):
            d["metadata"] = m
            mf.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed += 1
    print("updated", changed, "TCSVT records")

if __name__ == "__main__": main()
