"""Compare numbered main-text figure/table labels with extracted manifests.

This is a conservative text gate. It deliberately stops at References and
keeps Extended Data/Supplementary labels in a separate field for review.
Visual caption-boundary checks still require page-render inspection.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = r"(?:\d+|[IVXLCDM]+)"
LABEL_RE = re.compile(rf"^\s*(?:(?:fig(?:ure)?\.?\s*\.?\s*({TOKEN_RE}))|(?:table\s*\.?\s*({TOKEN_RE})))\b", re.I)
EXT_RE = re.compile(rf"^\s*(?:extended\s+data|supplementary|supp\.)\s+(?:fig(?:ure)?\.?\s*\.?\s*({TOKEN_RE})|table\s*\.?\s*({TOKEN_RE}))\b", re.I)


def label(kind: str, number: str) -> str:
    if number.isdigit():
        value = number
    else:
        total = 0
        previous = 0
        for char in number.upper()[::-1]:
            current = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}.get(char, 0)
            total += -current if current < previous else current
            previous = max(previous, current)
        value = str(total or number)
    return ("Fig" if kind == "figure" else "Table") + value


def expected(pdf: Path) -> tuple[set[tuple[str, str]], set[str]]:
    main: set[tuple[str, str]] = set()
    extended: set[str] = set()
    with fitz.open(pdf) as doc:
        stopped = False
        for page in doc:
            lines = [re.sub(r"\s+", " ", x).strip() for x in page.get_text().splitlines()]
            for line in lines:
                if re.match(r"^(references|bibliography)\b", line, re.I):
                    stopped = True
                    break
                ext = EXT_RE.match(line)
                if ext:
                    if ext.group(1):
                        extended.add("Fig" + str(int(ext.group(1))))
                    elif ext.group(2):
                        extended.add("Table" + str(int(ext.group(2))))
                    continue
                if stopped:
                    break
                match = LABEL_RE.match(line)
                if match:
                    if match.group(1):
                        main.add(("figure", label("figure", match.group(1))))
                    elif match.group(2):
                        main.add(("table", label("table", match.group(2))))
            if stopped:
                break
    return main, extended


def main() -> None:
    rows = []
    for manifest_path in sorted(ROOT.glob("*/manifest.json")):
        paper = manifest_path.parent
        pdf = paper / "pdf" / "paper.pdf"
        if not pdf.exists():
            continue
        try:
            exp, ext = expected(pdf)
        except Exception as exc:
            rows.append({"paper": paper.name, "status": "pdf_error", "error": str(exc)})
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assets = {(a.get("kind"), a.get("label")) for a in manifest.get("assets", [])}
        asset_list = [(a.get("kind"), a.get("label")) for a in manifest.get("assets", [])]
        duplicates = [x for x, count in Counter(asset_list).items() if count > 1]
        rows.append({
            "paper": paper.name,
            "expected_figures": sorted(x[1] for x in exp if x[0] == "figure"),
            "expected_tables": sorted(x[1] for x in exp if x[0] == "table"),
            "extended_or_supplementary": sorted(ext),
            "extracted_figures": sorted(x[1] for x in assets if x[0] == "figure"),
            "extracted_tables": sorted(x[1] for x in assets if x[0] == "table"),
            "missing": sorted(exp - assets),
            "extra": sorted(assets - exp),
            "duplicate": sorted(set(duplicates)),
            "status": "pass" if exp == assets and not duplicates else "review",
        })
    out = ROOT / "metadata" / "expected_count_qa.json"
    out.write_text(json.dumps({"papers": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"papers": len(rows), "pass": sum(r.get("status") == "pass" for r in rows), "review": sum(r.get("status") == "review" for r in rows), "pdf_error": sum(r.get("status") == "pdf_error" for r in rows)}
    print(json.dumps(summary, ensure_ascii=False))
    for row in rows:
        if row.get("status") != "pass":
            print(row["paper"], "missing=", row.get("missing"), "extra=", row.get("extra"), "extended=", row.get("extended_or_supplementary"))


if __name__ == "__main__":
    main()
