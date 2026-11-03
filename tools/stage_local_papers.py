"""Stage unique local PDFs into the paper asset layout.

The inventory and title-guess files are read-only evidence produced by the
local inventory pass. PDFs stay ignored by Git; this script creates the
directory layout, metadata, and an import report.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT.parent / "_staging"
INVENTORY = STAGING / "local_paper_inventory.json"
TITLE_GUESSES = STAGING / "title_guess.tsv"
CONFERENCES = {"AAAI", "CVPR", "CVPRW", "CVPRF", "ICCV", "ICLR", "ICML", "NeurIPS", "WACV", "ECCV", "ICASSP", "OpenReview", "SysCon"}


def compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def parse_title_guesses() -> dict[str, tuple[str, str, int]]:
    result: dict[str, tuple[str, str, int]] = {}
    if not TITLE_GUESSES.exists():
        return result
    for line in TITLE_GUESSES.read_text(encoding="utf-8").splitlines():
        parts = [part.strip() for part in line.split("\t")]
        if len(parts) != 4:
            continue
        year_text, venue, title, filename = parts
        year_match = re.search(r"20\d{2}", year_text)
        result[filename] = (title, venue, int(year_match.group()) if year_match else 0)
    return result


def slugify(title: str, year: int, venue: str, used: set[str]) -> str:
    words = re.findall(r"[A-Za-z0-9]+", title)
    stem = "_".join(words[:10]) or "paper"
    venue_part = re.sub(r"[^A-Za-z0-9]+", "_", venue).strip("_") or "local"
    base = re.sub(r"_+", "_", f"{stem}_{venue_part}_{year}").strip("_")[:100]
    slug = base or "paper"
    suffix = 2
    while slug in used:
        slug = f"{base}_{suffix}"
        suffix += 1
    used.add(slug)
    return slug


def fallback_title(filename: str) -> str:
    stem = Path(filename).stem
    chunks = re.split(r"[-–—]", stem)
    candidates = [chunk.strip() for chunk in chunks if re.search(r"[A-Za-z]{3,}", chunk)]
    return max(candidates, key=len) if candidates else stem


def detect_doi_and_url(pdf: Path) -> tuple[str, str]:
    try:
        with fitz.open(pdf) as doc:
            text = "\n".join(page.get_text() for page in list(doc)[:3])
    except Exception:
        return "", ""
    doi_match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.I)
    doi = re.sub(r"[),.;]+$", "", doi_match.group(0)) if doi_match else ""
    urls = [re.sub(r"[),.;]+$", "", url) for url in re.findall(r"https?://[^\s)<>]+", text)]
    official = next((url for url in urls if "github.com" not in url.lower() and "doi.org" not in url.lower()), "")
    return official, (f"https://doi.org/{doi}" if doi else "")


def main() -> None:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    guesses = parse_title_guesses()
    catalog_path = ROOT / "papers.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    used = {str(p.get("local_slug")) for p in catalog if p.get("local_slug")}
    existing_titles = {compact(str(p.get("title", ""))): p for p in catalog if p.get("title")}
    staged: list[dict] = []
    skipped: list[dict] = []

    for entry in inventory.get("papers", []):
        primary = entry["primary"]
        source = Path(primary["path"])
        if not source.exists():
            skipped.append({"reason": "missing", "path": primary["path"]})
            continue
        title, venue, guessed_year = guesses.get(primary["filename"], ("", "", 0))
        # CVF PDFs often begin with a repeated watermark sentence. The filename
        # carries the actual paper title in those cases.
        if title.lower().startswith("except for this watermark"):
            title = ""
        title = title or fallback_title(primary["filename"])
        venue = venue or str(primary.get("venue_guess") or "Local reference")
        year = int(primary.get("year_guess") or guessed_year or 0)
        title_key = compact(title)
        if title_key and title_key in existing_titles:
            skipped.append({"reason": "already_registered", "path": primary["path"], "title": title, "local_slug": existing_titles[title_key].get("local_slug")})
            continue
        slug = slugify(title, year, venue, used)
        dest_dir = ROOT / slug
        (dest_dir / "pdf").mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest_dir / "pdf" / "paper.pdf")
        official, doi_url = detect_doi_and_url(source)
        url = official or doi_url
        venue_type = "会议" if venue in CONFERENCES else "期刊"
        metadata = {
            "local_slug": slug,
            "title": title,
            "venue": venue,
            "venue_full": venue,
            "venue_short": venue,
            "venue_type": venue_type,
            "year": year,
            "classification": "本地参考文献，分区待核验",
            "official_url": url,
            "pdf_url": url,
            "access": "local_pdf",
            "source_sha256": entry["sha256"],
            "source_paths": [copy["path"] for copy in entry.get("copies", [])],
            "source_scope": "F_reference" if primary.get("source") == "F_reference" else "Zotero",
            "ranking_display": "",
            "cas_display": "",
            "ccf_display": "",
        }
        catalog.append(metadata)
        existing_titles[title_key] = metadata
        staged.append(metadata)

    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"staged": staged, "skipped": skipped, "staged_count": len(staged), "skipped_count": len(skipped)}
    report_path = ROOT / "metadata" / "local_import_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"staged": len(staged), "skipped": len(skipped)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
