(() => {
  const data = window.SITE_DATA || { papers: [], assets: [] };
  const state = {
    kind: "figure",
    view: "position",
    mode: "browse",
    paperSort: "year_desc",
    assetSort: "number_asc",
    year: "all",
    query: "",
  };

  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
  const paperMap = new Map(data.papers.map((paper) => [paper.id, paper]));
  const paperName = (id) => paperMap.get(id)?.title || id;
  const yearValue = (paper) => Number(paper.year) || 0;
  const positionText = (asset) => `${asset.kind === "figure" ? "Fig." : "Table"} ${asset.position_key}`;
  const paperTitle = (paper, className = "paper-link") => {
    const title = escapeHtml(paper?.title || "");
    const url = escapeHtml(paper?.official_url || paper?.pdf_url || "");
    return url ? `<a class="${className}" href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>` : title;
  };
  const paperBadgesHtml = (paper) => {
    const ranking = paper?.ranking_display || (
      paper?.venue_type === "会议" ? paper?.ccf_display : paper?.cas_display
    ) || "";
    const values = [
      paper?.year ? String(paper.year) : "",
      paper?.venue_short ? `${paper.venue_type || "载体"} ${paper.venue_short}` : (paper?.venue || ""),
      ranking,
    ].filter(Boolean);
    return values.map((value, index) => {
      const roleClass = index === 2 ? (paper?.venue_type === "会议" ? "badge-ccf" : "badge-cas") : `badge-${index}`;
      return `<span class="paper-badge ${roleClass}">${escapeHtml(value)}</span>`;
    }).join("");
  };
  const paperVenueMeta = (paper) => {
    const full = paper?.venue_full || paper?.venue || "";
    return full ? `${full} · ` : "";
  };
  const captionHtml = (asset) => {
    const en = asset.caption_en || asset.caption || "";
    const zh = asset.caption_zh || "";
    if (!zh || zh === en) return `<p>${escapeHtml(en)}</p>`;
    return `<div class="caption-pair"><p><span class="caption-label">EN</span>${escapeHtml(en)}</p><p><span class="caption-label">中文</span>${escapeHtml(zh)}</p></div>`;
  };

  function orderedPapers() {
    const ids = new Set(filteredAssets().map((asset) => asset.paper_id));
    return data.papers.filter((paper) => ids.has(paper.id)).sort((a, b) => {
      if (state.paperSort === "year_asc") return yearValue(a) - yearValue(b) || a.title.localeCompare(b.title);
      if (state.paperSort === "title") return a.title.localeCompare(b.title);
      if (state.paperSort === "venue") return (a.venue || "").localeCompare(b.venue || "") || yearValue(b) - yearValue(a);
      return yearValue(b) - yearValue(a) || a.title.localeCompare(b.title);
    });
  }

  function assetCompare(a, b) {
    if (state.assetSort === "number_desc") return b.position_number - a.position_number || b.position_suffix.localeCompare(a.position_suffix);
    if (state.assetSort === "page_asc") return a.page - b.page || a.position_number - b.position_number;
    if (state.assetSort === "label") return a.label.localeCompare(b.label, undefined, { numeric: true });
    return a.position_number - b.position_number || a.position_suffix.localeCompare(b.position_suffix) || a.page - b.page;
  }

  function filteredAssets() {
    const q = state.query.trim().toLowerCase();
    return data.assets.filter((asset) => {
      if (asset.kind !== state.kind) return false;
      const paper = paperMap.get(asset.paper_id) || {};
      if (state.year !== "all" && String(paper.year) !== state.year) return false;
      if (!q) return true;
      const text = [paper.title, paper.venue, paper.venue_short, paper.cas_display, paper.ccf_display, paper.year, asset.paper_id, asset.label, asset.position_key, asset.caption_en, asset.caption_zh, asset.caption].join(" ").toLowerCase();
      return text.includes(q);
    });
  }

  function vectorLinks(asset) {
    if (asset.kind !== "figure") return '<span class="muted">表格仅提供 LaTeX 下载</span>';
    if (!asset.vectors?.length) return asset.vector_status === "unavailable_temporary"
      ? '<span class="muted">PPT/SVG 暂不可用（本批次暂未绘制）</span>'
      : '<span class="muted">暂无 SVG/PPTX</span>';
    return asset.vectors.map((item) => `<a class="small-link" href="${escapeHtml(item.path)}" target="_blank">打开 ${escapeHtml(item.type.toUpperCase())}</a>`).join("");
  }

  function downloadLinks(asset) {
    const links = [`<a class="download-link" href="${escapeHtml(asset.original)}" download>下载原始 PNG</a>`];
    if (asset.kind === "table") {
      if (asset.latex) {
        const label = asset.latex_mode === "extracted_tabular" ? "下载 LaTeX（可编辑）" : "下载 LaTeX（图像包装）";
        links.push(`<a class="download-link latex" href="${escapeHtml(asset.latex)}" download>${label}</a>`);
      } else {
        links.push('<span class="muted">暂无 LaTeX</span>');
      }
      return links.join("");
    }
    const pptx = (asset.vectors || []).find((item) => item.type === "pptx");
    const svg = (asset.vectors || []).find((item) => item.type === "svg");
    if (pptx) links.push(`<a class="download-link primary" href="${escapeHtml(pptx.path)}" download>下载高清 PPTX</a>`);
    else links.push(`<span class="muted">${asset.ppt_status === "unavailable_temporary" ? "高清 PPTX 暂不可用（本批次暂未绘制）" : "暂无可编辑 PPTX"}</span>`);
    if (svg) links.push(`<a class="download-link" href="${escapeHtml(svg.path)}" download>下载 SVG</a>`);
    else if (asset.svg_status === "unavailable_temporary") links.push('<span class="muted">SVG 暂不可用（本批次暂未绘制）</span>');
    return links.join("");
  }

  function assetTile(asset) {
    const paper = paperMap.get(asset.paper_id) || {};
    const maxHeight = state.kind === "table" ? "table-media" : "";
    return `<article class="asset-tile ${maxHeight}">
      <a class="image-link" href="${escapeHtml(asset.original)}" target="_blank"><img loading="lazy" src="${escapeHtml(asset.original)}" alt="${escapeHtml(asset.label)} ${escapeHtml(paper.title)}"></a>
      <div class="tile-body">
        <div class="tile-label"><span class="asset-position">${escapeHtml(asset.label)}</span><span class="paper-badges">${paperBadgesHtml(paper)}</span></div>
        <h3>${paperTitle(paper)}</h3>
        <div class="tile-meta">${escapeHtml(paperVenueMeta(paper))}PDF 第 ${asset.page + 1} 页（页索引 ${asset.page}）</div>
        ${captionHtml(asset)}
        <div class="tile-actions"><div class="download-group"><span class="download-label">下载</span>${downloadLinks(asset)}</div><details><summary>${state.kind === "figure" ? "矢量文件" : "LaTeX 文件"}</summary><div class="vector-links">${vectorLinks(asset)}</div></details></div>
      </div>
    </article>`;
  }

  function assetDownloadRow(asset) {
    const paper = paperMap.get(asset.paper_id) || {};
    return `<article class="download-item"><div class="download-item-main"><strong>${escapeHtml(asset.label)}</strong><span class="paper-badges">${paperBadgesHtml(paper)}</span><span>${escapeHtml(paperVenueMeta(paper))}PDF 第 ${asset.page + 1} 页</span>${captionHtml(asset)}</div><div class="download-group">${downloadLinks(asset)}</div></article>`;
  }

  function renderPositionView(assets) {
    const groups = new Map();
    assets.forEach((asset) => {
      const key = asset.position_key;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(asset);
    });
    const order = [...groups.keys()].sort((a, b) => {
      const aa = groups.get(a)[0], bb = groups.get(b)[0];
      return state.assetSort === "number_desc" ? bb.position_number - aa.position_number : aa.position_number - bb.position_number;
    });
    return order.map((key) => {
      const group = groups.get(key).sort((a, b) => {
        const paperA = paperMap.get(a.paper_id) || {}, paperB = paperMap.get(b.paper_id) || {};
        const pa = orderedPapers().findIndex((p) => p.id === paperA.id), pb = orderedPapers().findIndex((p) => p.id === paperB.id);
        return pa - pb;
      });
      return `<section class="compare-row"><header class="row-header"><div><span class="eyebrow">同位置跨论文比较</span><h2>${escapeHtml(positionText(group[0]))}</h2></div><span class="row-count">${group.length} 篇论文</span></header><div class="asset-grid">${group.map(assetTile).join("")}</div></section>`;
    }).join("");
  }

  function renderPaperView(assets) {
    const byPaper = new Map();
    assets.forEach((asset) => {
      if (!byPaper.has(asset.paper_id)) byPaper.set(asset.paper_id, []);
      byPaper.get(asset.paper_id).push(asset);
    });
    return orderedPapers().map((paper) => {
      const rows = (byPaper.get(paper.id) || []).sort(assetCompare);
      if (!rows.length) return "";
      return `<section class="compare-row paper-row"><header class="row-header"><div><span class="eyebrow">同一论文内部浏览</span><h2>${paperTitle(paper, "paper-heading-link")}</h2><div class="row-meta"><span class="paper-badges">${paperBadgesHtml(paper)}</span>${escapeHtml(paperVenueMeta(paper))}${escapeHtml(paper.classification || "")}</div></div><span class="row-count">${rows.length} 个${state.kind === "figure" ? "图片" : "表格"}</span></header><div class="asset-grid">${rows.map(assetTile).join("")}</div></section>`;
    }).join("");
  }

  function renderDownloadView(assets) {
    const byPaper = new Map();
    assets.forEach((asset) => {
      if (!byPaper.has(asset.paper_id)) byPaper.set(asset.paper_id, []);
      byPaper.get(asset.paper_id).push(asset);
    });
    return orderedPapers().map((paper) => {
      const rows = (byPaper.get(paper.id) || []).sort(assetCompare);
      if (!rows.length) return "";
      return `<section class="download-section"><header class="row-header"><div><span class="eyebrow">下载中心</span><h2>${paperTitle(paper, "paper-heading-link")}</h2><div class="row-meta"><span class="paper-badges">${paperBadgesHtml(paper)}</span>${escapeHtml(paperVenueMeta(paper))}${rows.length} 个${state.kind === "figure" ? "图片" : "表格"}</div></div></header><div class="download-list">${rows.map(assetDownloadRow).join("")}</div></section>`;
    }).join("");
  }

  function updatePaperFilter() {
    const current = $("paper-filter").value;
    const assets = data.assets.filter((asset) => asset.kind === state.kind);
    const ids = [...new Set(assets.map((asset) => asset.paper_id))];
    $("paper-filter").innerHTML = `<option value="all">全部论文</option>` + ids.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(paperName(id))}</option>`).join("");
    if (ids.includes(current)) $("paper-filter").value = current;
  }

  function render() {
    const allForKind = data.assets.filter((asset) => asset.kind === state.kind);
    const assets = filteredAssets().filter((asset) => {
      const selected = $("paper-filter").value;
      return selected === "all" || asset.paper_id === selected;
    });
    const noun = state.kind === "figure" ? "图片" : "表格";
    if (state.mode === "download") $("view-label").textContent = `下载中心：${noun}及其可编辑文件`;
    else $("view-label").textContent = state.view === "position" ? `按${noun}位置横向比较不同论文` : `按论文查看论文内部${noun}`;
    $("mode-browse").classList.toggle("active", state.mode === "browse");
    $("mode-download").classList.toggle("active", state.mode === "download");
    $("mode-browse").setAttribute("aria-selected", String(state.mode === "browse"));
    $("mode-download").setAttribute("aria-selected", String(state.mode === "download"));
    $("summary").textContent = `共 ${allForKind.length} 个${state.kind === "figure" ? "图片" : "表格"}，当前显示 ${assets.length} 个，${new Set(assets.map((asset) => asset.paper_id)).size} 篇论文`;
    const body = state.mode === "download" ? renderDownloadView(assets) : (state.view === "position" ? renderPositionView(assets) : renderPaperView(assets));
    $("content").innerHTML = assets.length ? body : '<div class="empty">没有匹配结果，请调整筛选条件。</div>';
  }

  function bind() {
    $("mode-browse").addEventListener("click", () => { state.mode = "browse"; render(); });
    $("mode-download").addEventListener("click", () => { state.mode = "download"; render(); });
    $("kind").addEventListener("change", (event) => { state.kind = event.target.value; updatePaperFilter(); render(); });
    $("view").addEventListener("change", (event) => { state.view = event.target.value; render(); });
    $("paper-sort").addEventListener("change", (event) => { state.paperSort = event.target.value; render(); });
    $("asset-sort").addEventListener("change", (event) => { state.assetSort = event.target.value; render(); });
    $("year").addEventListener("change", (event) => { state.year = event.target.value; render(); });
    $("paper-filter").addEventListener("change", render);
    $("search").addEventListener("input", (event) => { state.query = event.target.value; render(); });
    $("reset").addEventListener("click", () => { state.query = ""; state.year = "all"; $("search").value = ""; $("year").value = "all"; $("paper-filter").value = "all"; render(); });
  }

  function start() {
    const years = [...new Set(data.papers.map((paper) => paper.year).filter(Boolean))].sort((a, b) => b - a);
    $("year").innerHTML = '<option value="all">全部年份</option>' + years.map((year) => `<option value="${escapeHtml(year)}">${escapeHtml(year)}</option>`).join("");
    updatePaperFilter();
    bind();
    render();
  }
  start();
})();
