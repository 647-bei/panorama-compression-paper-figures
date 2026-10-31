"""Check generated offline HTML pages and their local asset links."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.tags: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags[tag] = self.tags.get(tag, 0) + 1
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.links.append(value)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    report = {"pages": {}, "errors": []}
    for page_name in ("index.html", "figures.html", "tables.html"):
        page = root / page_name
        parser = LinkParser()
        parser.feed(page.read_text(encoding="utf-8"))
        missing = []
        for link in parser.links:
            parsed = urlparse(link)
            if parsed.scheme or link.startswith("#"):
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.exists():
                missing.append(link)
        report["pages"][page_name] = {"links": len(parser.links), "missing": missing, "tags": parser.tags}
        report["errors"].extend(f"{page_name}: {x}" for x in missing)
    report["ok"] = not report["errors"]
    print(report)
    if report["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
