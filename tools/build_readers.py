"""Build offline HTML readers for extracted figures and tables."""
from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_CATALOG = {
    row.get("local_slug"): row
    for row in json.loads((ROOT / "papers.json").read_text(encoding="utf-8"))
    if row.get("local_slug")
}


def esc(value: object) -> str:
    return html.escape(str("" if value is None else value), quote=True)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_assets(kind: str) -> list[dict]:
    rows = []
    for manifest_path in sorted(ROOT.glob("*/manifest.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        catalog = PAPER_CATALOG.get(manifest_path.parent.name, {})
        metadata = {**catalog, **(data.get("metadata") or {})}
        for asset in data.get("assets", []):
            if asset.get("kind") != kind:
                continue
            original_path = manifest_path.parent / asset.get("original", "")
            if not original_path.exists():
                continue
            vectors = []
            if kind == "figure":
                for vector in asset.get("vector", []):
                    vector_path = manifest_path.parent / vector
                    if vector_path.exists():
                        vectors.append((vector_path.suffix.lower().lstrip("."), rel(vector_path)))
            latex_path = manifest_path.parent / asset.get("latex", "")
            rows.append({
                "paper": data.get("paper", manifest_path.parent.name),
                "title": metadata.get("title", data.get("paper", manifest_path.parent.name)),
                "venue": metadata.get("venue", ""),
                "venue_short": metadata.get("venue_short", metadata.get("venue", "")),
                "venue_full": metadata.get("venue_full", metadata.get("venue", "")),
                "venue_type": metadata.get("venue_type", ""),
                "year": metadata.get("year", ""),
                "classification": metadata.get("classification", ""),
                "cas_display": metadata.get("cas_display", ""),
                "ccf_display": metadata.get("ccf_display", ""),
                "ranking_display": metadata.get("ranking_display", ""),
                "label": asset.get("label", ""),
                "caption": asset.get("caption_en", asset.get("caption", "")),
                "caption_en": asset.get("caption_en", asset.get("caption", "")),
                "caption_zh": asset.get("caption_zh", ""),
                "page": asset.get("page", ""),
                "original": rel(original_path),
                "vectors": vectors,
                "vector_status": asset.get("vector_status", metadata.get("vector_status", "")),
                "ppt_status": asset.get("ppt_status", metadata.get("ppt_status", "")),
                "svg_status": asset.get("svg_status", metadata.get("svg_status", "")),
                "download_note": asset.get("download_note", metadata.get("download_note", "")),
                "vector_mode": asset.get("vector_mode", ""),
                "latex": rel(latex_path) if kind == "table" and latex_path.exists() else "",
                "latex_mode": asset.get("latex_mode", ""),
                "official_url": metadata.get("official_url", "") or metadata.get("pdf_url", ""),
            })
    rows.sort(key=lambda r: (r["paper"].lower(), str(r["label"])))
    return rows


def page_css() -> str:
    return """
      :root { color-scheme: light; --ink:#17202a; --muted:#5f6b76; --line:#d9e0e6; --accent:#165d8d; --soft:#f5f8fa; }
      * { box-sizing:border-box; }
      body { margin:0; color:var(--ink); background:#fff; font-family:Segoe UI,Microsoft YaHei,Arial,sans-serif; }
      header { position:sticky; top:0; z-index:5; background:rgba(255,255,255,.96); border-bottom:1px solid var(--line); padding:18px clamp(18px,4vw,56px) 14px; }
      h1 { margin:0 0 6px; font-size:26px; line-height:1.2; }
      .sub { color:var(--muted); font-size:14px; }
      nav { display:flex; gap:10px; margin-top:14px; flex-wrap:wrap; }
      nav a, .link { color:var(--accent); text-decoration:none; border:1px solid #b9ccda; background:#f7fbfe; padding:7px 11px; border-radius:5px; font-size:13px; }
      nav a:hover, .link:hover { background:#eaf4fa; }
      .toolbar { display:flex; gap:10px; align-items:center; margin-top:14px; flex-wrap:wrap; }
      input { flex:1 1 320px; min-height:38px; border:1px solid #b9c4cc; border-radius:5px; padding:0 12px; font-size:14px; }
      select { min-height:38px; border:1px solid #b9c4cc; border-radius:5px; padding:0 10px; background:#fff; }
      main { padding:26px clamp(18px,4vw,56px) 60px; max-width:1800px; margin:auto; }
      .summary { color:var(--muted); margin:0 0 18px; font-size:14px; }
      .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:18px; align-items:start; }
      article { border:1px solid var(--line); border-radius:7px; overflow:hidden; background:#fff; box-shadow:0 2px 10px rgba(25,45,60,.06); }
      .media { background:var(--soft); border-bottom:1px solid var(--line); padding:10px; text-align:center; }
      .media img { display:block; width:100%; max-height:720px; object-fit:contain; background:#fff; }
      .body { padding:14px 15px 16px; }
      .paper { font-size:13px; font-weight:650; color:var(--accent); margin-bottom:5px; }
      .paper-link { color:inherit; text-decoration:none; }
      .paper-link:hover { color:var(--accent); text-decoration:underline; text-underline-offset:2px; }
      .paper-badges { display:flex; gap:5px; flex-wrap:wrap; margin:5px 0 7px; }
      .paper-badge { display:inline-flex; border:1px solid #c4d5df; border-radius:999px; padding:2px 7px; background:#f7fbfe; color:var(--muted); font-size:11px; line-height:1.35; }
      .paper-badge:nth-child(1) { color:var(--accent); font-weight:700; }
      .paper-badge:nth-child(2) { color:var(--accent); }
      .paper-badge.badge-cas { background:#f5faf7; border-color:#b9d8c4; color:#276b3a; }
      .paper-badge.badge-ccf { background:#fff9ed; border-color:#e5c98b; color:#7b5b16; }
      h2 { font-size:17px; line-height:1.35; margin:0 0 8px; }
      .meta { color:var(--muted); font-size:12px; line-height:1.5; margin-bottom:10px; }
      .caption { font-size:13px; line-height:1.55; white-space:pre-wrap; }
      .actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:13px; }
      details { margin-top:12px; border-top:1px solid var(--line); padding-top:10px; }
      summary { cursor:pointer; color:var(--accent); font-size:13px; }
      .vectors { display:flex; gap:8px; flex-wrap:wrap; margin-top:9px; }
      .empty { padding:30px; border:1px dashed var(--line); color:var(--muted); text-align:center; }
      .hidden { display:none !important; }
      footer { border-top:1px solid var(--line); color:var(--muted); padding:18px clamp(18px,4vw,56px) 30px; font-size:12px; }
      @media (max-width:600px) { h1 { font-size:22px; } .grid { grid-template-columns:1fr; } header { position:static; } }
    """


def page_html(kind: str, rows: list[dict]) -> str:
    is_fig = kind == "figure"
    label = "图片" if is_fig else "表格"
    title = f"全景压缩恢复论文{label}阅读器"
    data = json.dumps(rows, ensure_ascii=False)
    cards = []
    for i, row in enumerate(rows):
        badges = [
            str(row["year"]) if row["year"] else "",
            f'{row["venue_type"]} {row["venue_short"]}'.strip() if row["venue_short"] else row["venue"],
            row["ranking_display"] or (row["ccf_display"] if row["venue_type"] == "会议" else row["cas_display"]),
        ]
        badge_html = "".join(
            f'<span class="paper-badge {"badge-cas" if index == 2 and row["venue_type"] == "期刊" else "badge-ccf" if index == 2 else f"badge-{index}"}">{esc(value)}</span>'
            for index, value in enumerate(badges) if value
        )
        vector_links = "".join(f'<a class="link" href="{esc(path)}" target="_blank">打开 {esc(ext.upper())}</a>' for ext, path in row["vectors"]) if is_fig else ""
        if is_fig and not vector_links and row.get("vector_status") == "unavailable_temporary":
            vector_links = '<span class="meta">PPT/SVG 暂不可用（本批次暂未绘制）</span>'
        if not is_fig and row["latex"]:
            latex_label = "打开 LaTeX（可编辑）" if row["latex_mode"] == "extracted_tabular" else "打开 LaTeX（图像包装）"
            vector_links = f'<a class="link" href="{esc(row["latex"])}" download>{esc(latex_label)}</a>'
        title = f'<a class="paper-link" href="{esc(row["official_url"])}" target="_blank" rel="noopener noreferrer">{esc(row["title"])}</a>' if row["official_url"] else esc(row["title"])
        caption = esc(row["caption_en"])
        if row["caption_zh"] and row["caption_zh"] != row["caption_en"]:
            caption = f'<span class="caption-label">EN</span>{caption}<br><span class="caption-label">中文</span>{esc(row["caption_zh"])}'
        mode = (row["vector_mode"] if is_fig else row["latex_mode"]) or ("未生成矢量文件" if is_fig else "未生成 LaTeX")
        card = f'''<article data-index="{i}" data-search="{esc((row["title"] + " " + row["paper"] + " " + row["label"] + " " + row["caption"]).lower())}">
          <div class="media"><img loading="lazy" src="{esc(row["original"])}" alt="{esc(row["label"])} {esc(row["title"])}"></div>
          <div class="body">
            <div class="paper">{esc(row["paper"])}</div>
            <h2>{esc(row["label"])} · {title}</h2>
            <div class="paper-badges">{badge_html}</div>
            <div class="meta">{esc(row["venue_full"] or row["venue"])} · PDF 第 {int(row["page"])+1} 页（页索引 {esc(row["page"])}）<br>{esc(row["classification"])}</div>
            <div class="caption">{caption}</div>
            <div class="actions"><a class="link" href="{esc(row["original"])}" target="_blank">打开原始 PNG</a></div>
            <details><summary>{'矢量/可编辑文件' if is_fig else 'LaTeX 表格代码'}（{esc(mode)}）</summary><div class="vectors">{vector_links or '<span class="meta">暂无文件</span>'}</div></details>
          </div>
        </article>'''
        cards.append(card)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<style>{page_css()}</style></head>
<body><header><h1>{esc(title)}</h1><div class="sub">离线阅读 · 图片不含 caption，caption 在图片下方显示</div>
<nav><a href="index.html">资料首页</a><a href="figures.html">图片阅读器</a><a href="tables.html">表格阅读器</a></nav>
<div class="toolbar"><input id="search" type="search" placeholder="搜索论文、图表编号或图注"><select id="paper"><option value="">全部论文</option></select><select id="sort"><option value="paper">按论文排序</option><option value="label">按编号排序</option></select></div></header>
<main><p id="summary" class="summary"></p><div id="grid" class="grid">{"".join(cards) if cards else '<div class="empty">没有找到可显示的资产。</div>'}</div><div id="empty" class="empty hidden">没有匹配的条目。</div></main>
<footer>图片原始 PNG 与 SVG/PPTX、表格 LaTeX 均为本地相对链接。复杂位图的 SVG 是路径描摹，文字可能不是语义可编辑文本。</footer>
<script>
const rows={data};
const articles=[...document.querySelectorAll('article')];
const search=document.getElementById('search'), paper=document.getElementById('paper'), sort=document.getElementById('sort'), grid=document.getElementById('grid'), empty=document.getElementById('empty'), summary=document.getElementById('summary');
const papers=[...new Set(rows.map(r=>r.paper))].sort(); papers.forEach(p=>{{const o=document.createElement('option');o.value=p;o.textContent=p;paper.appendChild(o);}});
function render() {{ const q=search.value.trim().toLowerCase(), p=paper.value, mode=sort.value; const order=[...articles].sort((a,b)=>{{const ra=rows[+a.dataset.index], rb=rows[+b.dataset.index]; return mode==='label'?ra.label.localeCompare(rb.label,undefined,{{numeric:true}}):ra.paper.localeCompare(rb.paper);}}); order.forEach(a=>grid.appendChild(a)); let n=0; order.forEach(a=>{{const r=rows[+a.dataset.index], ok=(!q||a.dataset.search.includes(q))&&(!p||r.paper===p); a.classList.toggle('hidden',!ok); if(ok)n++;}}); summary.textContent=`共 ${{rows.length}} 个{esc(label)}，当前显示 ${{n}} 个`; empty.classList.toggle('hidden',n!==0);}}
[search,paper,sort].forEach(x=>x.addEventListener('input',render)); render();
</script></body></html>'''


def index_html(figures: list[dict], tables: list[dict]) -> str:
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全景压缩恢复论文图表阅读器</title><style>{page_css()} .home{{max-width:900px;margin:70px auto;padding:0 22px}} .choice{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;margin-top:28px}} .choice a{{display:block;padding:24px;border:1px solid var(--line);border-radius:7px;text-decoration:none;color:var(--ink);background:var(--soft)}} .choice strong{{display:block;font-size:20px;margin-bottom:8px}} </style></head><body><main class="home"><h1>全景压缩恢复论文图表阅读器</h1><p class="sub">本地离线页面，按论文、编号和图注检索已截取的论文图片与表格。</p><div class="choice"><a href="figures.html"><strong>图片阅读器</strong><span>{len(figures)} 个图片条目，含主图、架构图和子图。</span></a><a href="tables.html"><strong>表格阅读器</strong><span>{len(tables)} 个表格条目，含原始 PNG 和可下载的 LaTeX 代码。</span></a></div></main></body></html>'''


def main() -> None:
    figures = load_assets("figure")
    tables = load_assets("table")
    (ROOT / "figures.html").write_text(page_html("figure", figures), encoding="utf-8")
    (ROOT / "tables.html").write_text(page_html("table", tables), encoding="utf-8")
    # index.html is the GitHub Pages comparison app and is maintained separately.
    print(f"figures={len(figures)} tables={len(tables)}; index.html preserved")


if __name__ == "__main__":
    main()
