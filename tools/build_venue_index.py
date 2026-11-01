"""Build a de-duplicated venue index from the paper catalog.

The index keeps the current project's display metadata in one place so the same
venue is not searched and entered repeatedly. CCF uses the 2026 seventh edition;
CAS uses the 2025 upgraded journal-division table.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CCF_SOURCE = "https://www.ccf.org.cn/Academic_Evaluation/By_category/"
CCF_PDF = "https://kyc.lsu.edu.cn/_upload/article/files/20/77/2cbaa3754eb9aff9ed74cafed8ff/23a8de02-594c-445f-b084-69b0193c05b3.pdf"
CAS_SOURCE = "https://www.fenqubiao.com/"
CAS_FILE = "https://cce.ncepu.edu.cn/docs//2026-09/0e77800bf2744596a26e43c83acceed0.xlsx"


def conference(short: str, full: str) -> dict[str, object]:
    return {
        "venue_short": short,
        "venue_full": full,
        "venue_type": "会议",
        "cas_zone": None,
        "cas_top": None,
        "cas_display": "中科院分区：不适用（会议）",
        "ccf_rank": "A",
        "ccf_scope": "会议",
        "ccf_display": "CCF会议 A类（2026）",
        "ranking_display": "CCF会议 A类（2026）",
    }


def journal(
    short: str,
    full: str,
    category: str,
    ccf_rank: str | None = None,
    ccf_scope: str | None = None,
) -> dict[str, object]:
    ccf_display = (
        f"CCF{ccf_scope} {ccf_rank}类（2026）"
        if ccf_rank and ccf_scope
        else "CCF：未收录（2026目录）"
    )
    return {
        "venue_short": short,
        "venue_full": full,
        "venue_type": "期刊",
        "cas_zone": "1区",
        "cas_top": True,
        "cas_category": category,
        "cas_display": f"中科院 1区 · Top（2025，{category}）",
        "ccf_rank": ccf_rank,
        "ccf_scope": ccf_scope,
        "ccf_display": ccf_display,
        "ranking_display": f"中科院 1区 · Top（2025，{category}）",
    }


VENUES: dict[str, dict[str, object]] = {
    "CVPR": conference("CVPR", "IEEE/CVF Computer Vision and Pattern Recognition Conference"),
    "ICCV": conference("ICCV", "International Conference on Computer Vision"),
    "AAAI": conference("AAAI", "AAAI Conference on Artificial Intelligence"),
    "ICLR": conference("ICLR", "International Conference on Learning Representations"),
    "ICML": conference("ICML", "International Conference on Machine Learning"),
    "NeurIPS": conference("NeurIPS", "Conference on Neural Information Processing Systems"),
    "IEEE Transactions on Image Processing": journal(
        "TIP", "IEEE Transactions on Image Processing", "计算机科学", "A", "期刊"
    ),
    "Nature Machine Intelligence": journal(
        "NMI", "Nature Machine Intelligence", "计算机科学"
    ),
    "Nature Communications": journal(
        "Nat Commun", "Nature Communications", "综合性期刊"
    ),
    "Nature Neuroscience": journal(
        "Nat Neurosci", "Nature Neuroscience", "医学"
    ),
    "Science Advances": journal(
        "Sci Adv", "Science Advances", "综合性期刊"
    ),
}


def markdown(index: dict[str, object]) -> str:
    lines = [
        "# 期刊会议分区索引",
        "",
        "本索引按唯一 venue 去重，供论文卡片和后续检索复用。",
        "",
        "- CCF：2026 年第七版《中国计算机学会推荐国际学术会议和期刊目录》。",
        "- 中科院：2025 年升级版《中国科学院文献情报中心期刊分区表》。",
        "- `CCF：未收录` 表示该 venue 未出现在 CCF 计算机目录中，不等同于学术质量判断。",
        "",
        "| 原始 venue | 展示简称 | 类型 | 对应分区/等级 |",
        "|---|---|---|---|",
    ]
    for row in index["venues"]:  # type: ignore[index]
        lines.append(
            f"| {row['venue_full']} | {row['venue_short']} | {row['venue_type']} | "
            f"{row['ranking_display']} |"
        )
    lines.extend(
        [
            "",
            f"生成日期：{index['generated_at']}",
            "",
            f"CCF 官方目录：{CCF_SOURCE}",
            f"CCF 正式版 PDF：{CCF_PDF}",
            f"中科院分区平台：{CAS_SOURCE}",
            f"2025 升级版文件来源：{CAS_FILE}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    catalog_path = ROOT / "papers.json"
    papers = json.loads(catalog_path.read_text(encoding="utf-8"))
    for paper in papers:
        metadata = VENUES.get(paper.get("venue", ""))
        if metadata:
            paper.update(metadata)

    unique = []
    for venue, metadata in VENUES.items():
        row = {"venue": venue, **metadata}
        row["sources"] = {
            "ccf_official": CCF_SOURCE,
            "ccf_pdf": CCF_PDF,
            "cas_platform": CAS_SOURCE,
            "cas_2025_file": CAS_FILE,
        }
        unique.append(row)

    index = {
        "generated_at": date.today().isoformat(),
        "ccf_edition": "2026 第七版",
        "cas_edition": "2025 升级版",
        "venues": unique,
    }
    metadata_dir = ROOT / "metadata"
    metadata_dir.mkdir(exist_ok=True)
    (metadata_dir / "venue_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (metadata_dir / "venue_index.md").write_text(markdown(index), encoding="utf-8")
    catalog_path.write_text(json.dumps(papers, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"indexed venues={len(unique)} papers={len(papers)}")


if __name__ == "__main__":
    main()
