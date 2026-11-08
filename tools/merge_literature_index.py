import json
from pathlib import Path
root = Path('.')
a = json.loads((root / 'metadata/literature_2026.json').read_text(encoding='utf-8'))
b = json.loads((root / 'metadata/literature_2026_2027_additions.json').read_text(encoding='utf-8'))
seen = set(); merged = []
for x in a + b:
    k = (x.get('title','').strip().lower(), x.get('year'))
    if k in seen: continue
    seen.add(k); merged.append(x)
merged.sort(key=lambda x: (int(x.get('year', 0)), x.get('venue',''), x.get('title','')), reverse=True)
(root / 'metadata/literature_2026_2027.json').write_text(json.dumps(merged, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
lines = ['# 2026–2027 相关论文索引（图像恢复/压缩恢复/失真增强/SNN/类脑视觉/KAN/小波/生物视觉）', '', f'共 {len(merged)} 篇；其中 `access=open_pdf` 的论文已进入图表裁剪流程，`metadata_only_pdf_unavailable` 仅保留官方记录。新批次图片暂不生成 PPT/SVG。', '', '| 年份 | 载体 | 题目 | 状态 | 全文/官方链接 |', '|---:|---|---|---|---|']
for x in merged:
    url = x.get('official_url') or x.get('pdf_url') or ''
    status = x.get('download_status') or x.get('status','')
    official = x.get('official_url') or url
    lines.append(f"| {x.get('year','')} | {x.get('venue','')} | [{x.get('title','')}]({url}) | {status} | [官方页面]({official}) |")
(root / 'metadata/literature_2026_2027.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('merged', len(merged), 'downloaded', sum(x.get('download_status') == 'downloaded' for x in merged))
