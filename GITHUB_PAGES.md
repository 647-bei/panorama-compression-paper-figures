# GitHub Pages 部署

当前目录已经连接到 GitHub 仓库 [`647-bei/panorama-compression-paper-figures`](https://github.com/647-bei/panorama-compression-paper-figures)，GitHub Pages 地址为：

```text
https://647-bei.github.io/panorama-compression-paper-figures/
```

首次迁移到其他账号或仓库时，可在本目录执行：

```powershell
git init
git branch -M main
git add .
git commit -m "Add panoramic compression paper figure viewer"
git remote add origin https://github.com/<your-account>/<your-repository>.git
git push -u origin main
```

仓库中的 `.github/workflows/pages.yml` 会自动使用 GitHub Pages 部署。当前仓库已经启用 **GitHub Actions** 作为 Pages 来源；以后推送到 `main` 分支就会自动重新部署。部署地址格式为：

```text
https://<your-account>.github.io/<your-repository>/
```

## 更新论文数据

新增或修改论文的 manifest 后，在本地重新生成网站数据：

```powershell
$env:PYTHONUTF8 = "1"
python tools\enrich_manifests.py
python tools\build_latex_tables.py
python tools\build_site_data.py
python tools\build_readers.py  # 可选：更新 figures.html 和 tables.html
```

`build_readers.py` 不会覆盖首页 `index.html`；首页是支持双排序和跨论文对比的 GitHub Pages 应用。

`index.html` 使用 `site_data.js`，因此直接双击 HTML 也能运行，不依赖本地服务器。`site_data.json` 方便调试和其他程序读取。

## 站点功能

- **按图片位置对比**：将 `Fig. 1`、`Fig. 2`、`Table 1` 等位置分组，横向显示不同论文的同编号资产。
- **按论文浏览**：按论文分组，在同一论文内查看其图片或表格。
- **论文排序**：年份新到旧、年份旧到新、标题、期刊/会议。
- **图片排序**：编号、倒序编号、PDF 页码、标签。
- **筛选**：资料类型、年份、论文和全文搜索。
- **浏览/下载分开**：浏览模块用于图片和表格对比；下载中心提供图片原始 PNG、可用的高清 PPTX/SVG，以及表格原始 PNG 和 LaTeX。

表格 LaTeX 优先由 PDF 的表格结构自动生成，共有 40 个 `tabular` 文件；7 个结构无法可靠解析的表格使用原始高清裁切图包装，并在下载按钮上标注“图像包装”，避免误认为每个单元格都已可编辑。

## 仓库体积

当前资料包含 PDF、原始 PNG、SVG、PPTX 和页面渲染图。GitHub 单文件限制为 100 MB；如果后续加入更大的 PDF 或视频，使用 Git LFS，并考虑在 Pages 部署时排除不需要在线展示的原始 PDF 和 `page_renders`。
