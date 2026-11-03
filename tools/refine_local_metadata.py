"""Improve venue/title/year fields for imported local papers from source names and first pages."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT.parent / "_staging"


def clean_title_from_filename(path_text: str) -> str:
    stem = Path(path_text).stem
    patterns = [
        r"\s+-\s+20\d{2}\s+-\s+(.+)$",
        r"20\d{2}[^-–—]*[-–—](.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, stem)
        if match:
            candidate = match.group(1).strip(" -–—")
            if len(re.findall(r"[A-Za-z]{3,}", candidate)) >= 2:
                return re.sub(r"\s+", " ", candidate)
    return ""


def infer_venue(text: str, fallback: str) -> str:
    checks = [
        (r"nature machine intelligence", "Nature Machine Intelligence"),
        (r"nature communications", "Nature Communications"),
        (r"science advances", "Science Advances"),
        (r"pattern recognition", "Pattern Recognition"),
        (r"transactions on pattern analysis|\btpami\b", "TPAMI"),
        (r"transactions on image processing|\btip\b", "TIP"),
        (r"transactions on multimedia|\btmm\b", "TMM"),
        (r"transactions on neural networks|\b tnnls\b|\btnnls\b", "TNNLS"),
        (r"circuits and systems for video technology|\btcsvt\b", "TCSVT"),
        (r"\bcvprw\b|workshop on", "CVPRW"),
        (r"\bcvpr\b", "CVPR"),
        (r"\biccv\b", "ICCV"),
        (r"\beccv\b", "ECCV"),
        (r"\biclr\b", "ICLR"),
        (r"\bicml\b", "ICML"),
        (r"\bneurips\b", "NeurIPS"),
        (r"\baaa[i]?\b", "AAAI"),
        (r"\bwacv\b", "WACV"),
        (r"\bicassp\b", "ICASSP"),
        (r"arxiv|openreview", fallback if fallback in {"arXiv", "OpenReview"} else "arXiv"),
    ]
    lower = text.lower()
    for pattern, venue in checks:
        if re.search(pattern, lower):
            return venue
    return fallback


def title_from_first_page(lines: list[str]) -> str:
    clean = [re.sub(r"\s+", " ", line).strip() for line in lines]
    clean = [line for line in clean if line]
    skip = re.compile(r"conference|proceedings|arxiv|openreview|copyright|abstract|university|laboratory|department|\bvol\.?").search
    candidates = []
    skip = re.compile("conference|proceedings|arxiv|openreview|copyright|abstract|university|laboratory|department|vol\\.?|article|doi\\.org|journal homepage|contents lists|published online|received|accepted|check for updates", re.I).search
    for i, line in enumerate(clean[:24]):
        if re.search("abstract", line, re.I):
            break
        if skip(line) or re.match(r"^[\d\W_]+$", line) or line.count(",") >= 2 or re.search("member, ieee|graduate student|professor", line, re.I):
            continue
        if len(line) < 8 or re.search(r"[*†‡@]", line):
            continue
        if re.search(r"\b(?:et al\.?|author|received|accepted)\b", line, re.I):
            continue
        if not re.search(r"[A-Za-z]{3,}", line):
            continue
        joined = line
        for nxt in clean[i + 1:i + 4]:
            if skip(nxt) or re.search(r"[*†‡@]", nxt) or re.match(r"^[0-9]+", nxt) or nxt.count(",") >= 2 or re.search("member, ieee|graduate student|professor", nxt, re.I):
                break
            if re.search(r"\b(?:abstract|keywords|introduction)\b", nxt, re.I):
                break
            if len(nxt) > 100:
                break
            joined += " " + nxt
        candidates.append(joined)
    if not candidates:
        return ""
    # The first plausible heading is usually the paper title; avoid metadata
    # lines that contain only a venue name.
    return max(candidates[:4], key=lambda x: (len(re.findall(r"[A-Za-z]{3,}", x)), -len(x)))


def ranking(venue: str) -> str:
    conference = {
        "AAAI": "CCF会议 A类（2026）", "CVPR": "CCF会议 A类（2026）",
        "ICCV": "CCF会议 A类（2026）", "ICML": "CCF会议 A类（2026）",
        "NeurIPS": "CCF会议 A类（2026）", "ECCV": "CCF会议 B类（2026）",
        "ICLR": "CCF会议 B类（2026）", "WACV": "CCF会议 C类（2026）",
        "ICASSP": "CCF会议 B类（2026）",
    }
    journals = {
        "TPAMI": "中科院 1区 · Top（2025）", "TIP": "中科院 1区 · Top（2025）",
        "TNNLS": "中科院 1区 · Top（2025）", "TMM": "中科院 1区 · Top（2025）",
        "TCSVT": "中科院 2区（2025）", "Nature Machine Intelligence": "中科院 1区 · Top（2025）",
        "Nature Communications": "中科院 1区 · Top（2025）", "Science Advances": "中科院 1区 · Top（2025）",
        "Pattern Recognition": "中科院 1区 · Top（2025）",
    }
    return conference.get(venue, journals.get(venue, ""))


def main() -> None:
    catalog_path = ROOT / "papers.json"
    report = json.loads((ROOT / "metadata" / "local_import_report.json").read_text(encoding="utf-8"))
    firstpages = {x["sha256"]: x for x in json.loads((STAGING / "local_paper_firstpages.json").read_text(encoding="utf-8"))["papers"]}
    source_by_sha = {x.get("source_sha256"): x for x in report.get("staged", []) if x.get("source_sha256")}
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    changed = 0
    for paper in catalog:
        sha = paper.get("source_sha256")
        if not sha:
            continue
        source = source_by_sha.get(sha, {})
        paths = source.get("source_paths", [])
        filename_text = " ".join(paths)
        fp = firstpages.get(sha, {})
        page_text = " ".join(fp.get("first_page_lines", []))
        full_text = filename_text + " " + page_text
        title = clean_title_from_filename(paths[0]) if paths else ""
        current = str(paper.get("title", ""))
        page_title = title_from_first_page(fp.get("first_page_lines", []))
        generic_heading = current.startswith("The Fortieth") or current.startswith("The Thirty-Ninth") or "Conference on Artificial Intelligence" in current
        has_author_tail = bool(re.search("[0-9]", current) and current.count(",") >= 2)
        if page_title and len(re.findall(r"[A-Za-z]{3,}", page_title)) >= 4 and not re.search("member, ieee|graduate student|professor|@", page_title, re.I):
            title = page_title
        if title and (page_title or generic_heading or has_author_tail or any(ord(ch) > 127 for ch in current) or "�" in current or len(current) < 45 or current.lower().endswith((" for", " and", " the", " with", " of", " from", ":"))):
            paper["title"] = title
            changed += 1
        venue = infer_venue(full_text, str(paper.get("venue") or "Local reference"))
        if venue != paper.get("venue"):
            paper["venue"] = paper["venue_full"] = paper["venue_short"] = venue
            paper["venue_type"] = "会议" if venue in {"AAAI", "CVPR", "CVPRW", "ICCV", "ICLR", "ICML", "NeurIPS", "ECCV", "WACV", "ICASSP"} else "期刊"
            changed += 1
        if not paper.get("year"):
            match = re.search(r"20\d{2}", full_text)
            if match:
                paper["year"] = int(match.group())
                changed += 1
        if venue != "Local reference" and not paper.get("ranking_display"):
            paper["ranking_display"] = ranking(venue)
            if venue in {"AAAI", "CVPR", "CVPRW", "ICCV", "ICLR", "ICML", "NeurIPS", "ECCV", "WACV", "ICASSP"}:
                paper["ccf_display"] = paper["ranking_display"]
                paper["cas_display"] = "中科院分区：不适用（会议）"
            else:
                paper["cas_display"] = paper["ranking_display"]
                paper["ccf_display"] = "CCF：未收录（2026目录）"
            changed += 1
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changed": changed, "papers": len(catalog)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
