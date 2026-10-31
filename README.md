# 全景极低码率压缩后质量恢复：论文与图表资产

检索日期：2026-10-31。

## 在线网站

**[打开图表浏览与下载网站](https://647-bei.github.io/panorama-compression-paper-figures/)**

网站支持按图片编号跨论文对比、按论文浏览、年份排序，以及原始图片、可编辑 PPTX 和表格 LaTeX 下载。

本目录按“一个论文一个子文件夹”保存论文正文、原始图表裁切、矢量复刻结果和元数据。当前核心范围：

- 360°/ERP/球面图像压缩、超分辨率和质量恢复；
- 低码率压缩伪影去除、频率/小波恢复和压缩补偿；
- ANN、SNN、KAN、动态稀疏和能耗效率；
- 视网膜、主动视觉、球面采样和率失真感知的生物学/物理学依据。

## 目录约定

每篇论文使用以下结构：

```text
paper-slug/
  paper.pdf                  # 合法获取的正文 PDF；没有开放 PDF 时不创建伪 PDF
  figures/original/          # 主图、架构图、子图的原始裁切 PNG
  figures/vector/            # pdf-figure-vector 输出的 SVG/PPTX
  tables/original/           # 表格裁切 PNG
  tables/latex/              # 可编辑的 LaTeX 表格代码
  page_renders/              # 定位和复核用的页面渲染图
  manifest.json              # DOI、来源、页码、bbox、文件和验收状态
  notes.md                   # 与当前全景恢复任务的对应关系和限制
```

## 离线阅读入口

- [阅读首页](index.html)
- [图片阅读器](figures.html)
- [表格阅读器](tables.html)
- [GitHub Pages 部署说明](GITHUB_PAGES.md)

两个阅读器都支持按论文、图表编号和图注搜索；原始 PNG 直接显示，图片卡片提供 SVG/PPTX，表格卡片只提供 LaTeX 下载。

首页支持两种独立的浏览方式：按图片/表格编号做跨论文同位置对比，或按论文内部浏览全部图片/表格；论文可以按年份、标题或期刊排序，图片/表格可以按编号、页码或标签排序。

首页另有“下载中心”：图片提供原始 PNG、已有的高清可编辑 PPTX/SVG 下载；表格提供原始 PNG 和 LaTeX 文件。LaTeX 文件对能从 PDF 恢复结构的表格生成 `tabular`，其余表格明确标为图像包装。

`page` 使用 PDF 的 0 起始页索引；`bbox` 使用 PDF point 坐标。原始图表裁切严格排除 caption，caption 作为网页卡片下方的独立元数据显示；矢量复刻优先调用 `C:\Users\Admin\.codex\skills\pdf-figure-vector\scripts\extract_figure.py`。对本身是位图的图，不把位图伪装成可编辑矢量；这类结果会在 `manifest.json` 中标记。

## 重要分类说明

- CVPR、ICCV、NeurIPS、ICLR、AAAI 主会论文按 CCF 人工智能会议目录的 A 类口径记录；CVPRW/NTIRE 等 workshop 单独标注，不当作 CCF-A 主会。
- IEEE TIP、TPAMI 等期刊的中科院分区会随年度和大类/小类口径变化，目录只记录期刊和 DOI，不把未经当年学校目录核对的分区写成确定结论。
- Nature Communications、Nature Neuroscience、Nature Machine Intelligence 等按 Nature Portfolio 期刊记录；它们用于高水平方法和生物/物理原理参考，不等同于 CCF 会议分类。
- PDF 只从 CVF、AAAI、NeurIPS、ICLR、arXiv、Nature 的公开 PDF 或作者公开仓储获取。出版社登录页、HTML 和无法验证 `%PDF-` 的响应不会保存为 PDF。

## 当前边界

这些论文不都是“360°极低码率压缩后同分辨率恢复”的直接基线。球面论文用于几何和采样，低码率论文用于压缩伪影与率失真，SNN/KAN论文用于计算单元和效率，视网膜论文用于原理支撑。引用或绘图时必须保留任务边界。

## 本次处理统计

- 15 篇正文 PDF 已下载并用 PyMuPDF 验证；其余论文保留官方页面和元数据。
- 主文共提取 131 张图和 51 张表，原始 PNG 按 `figures/original` 与 `tables/original` 分开保存，caption 不进入裁切。
- 131 张图均有 SVG 和 PPTX 下载；复杂位图使用路径描摹，PPTX 以 SVG 对象嵌入以保持高清和可编辑性。
- 51 张表均有 LaTeX 下载；表格不生成 SVG/PPTX。
