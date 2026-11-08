"""Add the next 20 verified 2026--2027 references and stage open PDFs.

New figure assets intentionally keep vector/PPT downloads unavailable until a
separate shape-level reconstruction pass is completed.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
INCOMING = ROOT / "incoming_2026_2027"

PAPERS = [
    {
        "title": "SpikingIR: A Novel Converted Spiking Neural Network for Efficient Image Restoration",
        "year": 2026, "venue": "AAAI", "status": "published_main",
        "topic_tags": ["SNN", "image restoration", "energy efficiency"],
        "official_url": "https://ojs.aaai.org/index.php/AAAI/article/view/37769",
        "pdf_url": "https://ojs.aaai.org/index.php/AAAI/article/download/37769/41731",
        "access_note": "AAAI-26 official page; PDF route is temporarily unavailable to automated download",
        "downloadable": False,
    },
    {
        "title": "Universal Compressed Image Restoration via Codec-Aware Conditioning with Reinforcement Learning",
        "year": 2026, "venue": "AAAI", "status": "published_main",
        "topic_tags": ["compressed image restoration", "codec-aware", "reinforcement learning"],
        "official_url": "https://ojs.aaai.org/index.php/AAAI/article/view/42452",
        "pdf_url": "https://ojs.aaai.org/index.php/AAAI/article/download/42452/46413",
        "access_note": "AAAI-26 official page; PDF route is temporarily unavailable to automated download",
        "downloadable": False,
    },
    {
        "title": "Towards Efficient Low-rate Image Compression with Frequency-aware Diffusion Prior Refinement",
        "year": 2026, "venue": "AAAI", "status": "published_main",
        "topic_tags": ["low-rate compression", "frequency", "diffusion", "image restoration"],
        "official_url": "https://ojs.aaai.org/index.php/AAAI/article/view/38071",
        "pdf_url": "https://ojs.aaai.org/index.php/AAAI/article/download/38071/42033",
        "access_note": "AAAI-26 official page; PDF route is temporarily unavailable to automated download",
        "downloadable": False,
    },
    {
        "title": "HCF: Hierarchical Cascade Framework for Distributed Multi-Stage Image Compression",
        "year": 2026, "venue": "AAAI", "status": "published_main",
        "topic_tags": ["image compression", "multi-stage compression", "rate-distortion"],
        "official_url": "https://ojs.aaai.org/index.php/AAAI/article/view/38467",
        "pdf_url": "https://arxiv.org/pdf/2508.02051",
        "access_note": "AAAI-26 publication; open arXiv preprint used for figure extraction",
        "downloadable": True,
    },
    {
        "title": "DynaQuant: Dynamic Mixed-Precision Quantization for Learned Image Compression",
        "year": 2026, "venue": "AAAI", "status": "published_main",
        "topic_tags": ["learned image compression", "quantization", "low complexity"],
        "official_url": "https://ojs.aaai.org/index.php/AAAI/article/view/38464",
        "pdf_url": "https://arxiv.org/pdf/2511.07903",
        "access_note": "AAAI-26 publication; open arXiv preprint used for figure extraction",
        "downloadable": True,
    },
    {
        "title": "Test-Time Preference Optimization for Image Restoration",
        "year": 2026, "venue": "AAAI", "status": "published_main",
        "topic_tags": ["image restoration", "perceptual quality", "test-time optimization"],
        "official_url": "https://ojs.aaai.org/index.php/AAAI/article/view/37520",
        "pdf_url": "https://arxiv.org/pdf/2511.19169",
        "access_note": "AAAI-26 publication; open arXiv preprint used for figure extraction",
        "downloadable": True,
    },
    {
        "title": "LoViF 2026 Challenge on Real-World All-in-One Image Restoration: Methods and Results",
        "year": 2026, "venue": "CVPRW", "status": "published_workshop",
        "topic_tags": ["all-in-one restoration", "real-world degradation", "challenge"],
        "official_url": "https://openaccess.thecvf.com/content/CVPR2026W/LoViF/html/Chen_LoViF_2026_Challenge_on_Real-World_All-in-One_Image_Restoration_Methods_and_CVPRW_2026_paper.html",
        "pdf_url": "https://openaccess.thecvf.com/content/CVPR2026W/LoViF/papers/Chen_LoViF_2026_Challenge_on_Real-World_All-in-One_Image_Restoration_Methods_and_CVPRW_2026_paper.pdf",
        "access_note": "CVF official open PDF",
        "downloadable": True,
    },
    {
        "title": "PerFuSe: Personalized Full-Image Restoration via Modular Fusion",
        "year": 2026, "venue": "CVPRW", "status": "published_workshop",
        "topic_tags": ["image restoration", "personalized restoration", "diffusion"],
        "official_url": "https://openaccess.thecvf.com/content/CVPR2026W/P13N/html/Naeem_PerFuSe_Personalized_Full-Image_Restoration_via_Modular_Fusion_CVPRW_2026_paper.html",
        "pdf_url": "https://openaccess.thecvf.com/content/CVPR2026W/P13N/papers/Naeem_PerFuSe_Personalized_Full-Image_Restoration_via_Modular_Fusion_CVPRW_2026_paper.pdf",
        "access_note": "CVF official open PDF",
        "downloadable": True,
    },
    {
        "title": "NTIRE 2026 Challenge on Efficient Burst HDR and Restoration: Datasets, Methods, and Results",
        "year": 2026, "venue": "CVPRW", "status": "published_workshop",
        "topic_tags": ["burst HDR", "image restoration", "KAN", "efficient vision"],
        "official_url": "https://openaccess.thecvf.com/content/CVPR2026W/NTIRE/papers/Park_NTIRE_2026_Challenge_on_Efficient_Burst_HDR_and_Restoration_Datasets_CVPRW_2026_paper.pdf",
        "pdf_url": "https://openaccess.thecvf.com/content/CVPR2026W/NTIRE/papers/Park_NTIRE_2026_Challenge_on_Efficient_Burst_HDR_and_Restoration_Datasets_CVPRW_2026_paper.pdf",
        "access_note": "CVF official open PDF; includes a DUSKAN KAN restoration solution",
        "downloadable": True,
    },
    {
        "title": "NTIRE 2026 The First Challenge on Blind Computational Aberration Correction: Methods and Results",
        "year": 2026, "venue": "CVPRW", "status": "published_workshop",
        "topic_tags": ["optical aberration", "image restoration", "physics-based vision"],
        "official_url": "https://openaccess.thecvf.com/content/CVPR2026W/NTIRE/papers/Sun_NTIRE_2026_The_First_Challenge_on_Blind_Computational_Aberration_Correction_CVPRW_2026_paper.pdf",
        "pdf_url": "https://openaccess.thecvf.com/content/CVPR2026W/NTIRE/papers/Sun_NTIRE_2026_The_First_Challenge_on_Blind_Computational_Aberration_Correction_CVPRW_2026_paper.pdf",
        "access_note": "CVF official open PDF",
        "downloadable": True,
    },
    {
        "title": "Freeze the Structure, Free the Color: Fourier-Domain Training for Unpaired Smartphone ISP",
        "year": 2026, "venue": "CVPRW", "status": "published_workshop",
        "topic_tags": ["image enhancement", "Fourier domain", "smartphone ISP"],
        "official_url": "https://openaccess.thecvf.com/content/CVPR2026W/NTIRE/papers/Kim_Freeze_the_Structure_Free_the_Color_Fourier-Domain_Training_for_Unpaired_CVPRW_2026_paper.pdf",
        "pdf_url": "https://openaccess.thecvf.com/content/CVPR2026W/NTIRE/papers/Kim_Freeze_the_Structure_Free_the_Color_Fourier-Domain_Training_for_Unpaired_CVPRW_2026_paper.pdf",
        "access_note": "CVF official open PDF",
        "downloadable": True,
    },
    {
        "title": "Restore, Assess, Repeat: A Unified Framework for Iterative Image Restoration",
        "year": 2026, "venue": "CVPR", "status": "published_main",
        "topic_tags": ["image restoration", "iterative refinement", "quality assessment"],
        "official_url": "https://openaccess.thecvf.com/content/CVPR2026/html/Chen_Restore_Assess_Repeat_A_Unified_Framework_for_Iterative_Image_Restoration_CVPR_2026_paper.html",
        "pdf_url": "https://openaccess.thecvf.com/content/CVPR2026/papers/Chen_Restore_Assess_Repeat_A_Unified_Framework_for_Iterative_Image_Restoration_CVPR_2026_paper.pdf",
        "access_note": "CVF official open PDF",
        "downloadable": True,
    },
    {
        "title": "Adopting a human developmental visual diet yields robust and shape-based AI vision",
        "year": 2026, "venue": "Nature Machine Intelligence", "status": "published_main",
        "topic_tags": ["biological vision", "visual development", "image corruption robustness"],
        "official_url": "https://www.nature.com/articles/s42256-026-01228-6",
        "pdf_url": "https://www.nature.com/articles/s42256-026-01228-6.pdf",
        "access_note": "Nature open-access article PDF",
        "downloadable": True,
    },
    {
        "title": "Neural sampling from cognitive maps enables goal-directed imagination and planning",
        "year": 2026, "venue": "Nature Machine Intelligence", "status": "published_main",
        "topic_tags": ["brain-inspired", "cognitive maps", "neuromorphic computing"],
        "official_url": "https://www.nature.com/articles/s42256-026-01254-4",
        "pdf_url": "https://www.nature.com/articles/s42256-026-01254-4.pdf",
        "access_note": "Nature open-access article PDF",
        "downloadable": True,
    },
    {
        "title": "Temporal coding enables hyperacuity in event-based vision",
        "year": 2026, "venue": "Nature Communications", "status": "published_main",
        "topic_tags": ["biological vision", "event vision", "temporal coding"],
        "official_url": "https://www.nature.com/articles/s41467-026-76878-6",
        "pdf_url": "https://www.nature.com/articles/s41467-026-76878-6.pdf",
        "access_note": "Nature open-access article PDF",
        "downloadable": True,
    },
    {
        "title": "Neuronal tuning aligns dynamically with object and texture manifolds across the visual hierarchy",
        "year": 2026, "venue": "Nature Neuroscience", "status": "published_main",
        "topic_tags": ["visual cortex", "neural representation", "biological vision"],
        "official_url": "https://www.nature.com/articles/s41593-026-02207-1",
        "pdf_url": "https://www.nature.com/articles/s41593-026-02207-1.pdf",
        "access_note": "Nature article PDF",
        "downloadable": True,
    },
    {
        "title": "A single computational objective can produce specialization of streams in visual cortex",
        "year": 2026, "venue": "Nature Communications", "status": "published_main",
        "topic_tags": ["visual cortex", "brain-inspired vision", "representation learning"],
        "official_url": "https://www.nature.com/articles/s41467-026-76098-y",
        "pdf_url": "https://www.nature.com/articles/s41467-026-76098-y.pdf",
        "access_note": "Nature open-access article PDF",
        "downloadable": True,
    },
    {
        "title": "CHROMA-MILL: Joint Low-Light Enhancement and White Balance under Colored Illumination",
        "year": 2027, "venue": "WACV", "status": "accepted_wacv_2027_preprint",
        "topic_tags": ["low-light enhancement", "physical imaging", "color correction"],
        "official_url": "https://arxiv.org/abs/2611.04092",
        "pdf_url": "https://arxiv.org/pdf/2611.04092",
        "access_note": "arXiv preprint marked Accepted at WACV 2027; proceedings not yet available",
        "downloadable": True,
    },
    {
        "title": "An Agentic Framework for Quality-Aware and Scenario-Adaptive Image Compression",
        "year": 2026, "venue": "arXiv", "status": "preprint",
        "topic_tags": ["image compression", "quality-aware coding", "restoration"],
        "official_url": "https://arxiv.org/abs/2611.04960",
        "pdf_url": "https://arxiv.org/pdf/2611.04960",
        "access_note": "arXiv preprint posted November 2026",
        "downloadable": True,
    },
    {
        "title": "SNNSIR: A fully Spiking Neural Network for Stereo Image Restoration",
        "year": 2026, "venue": "Pattern Recognition", "status": "published_ahead_of_print",
        "topic_tags": ["SNN", "stereo image restoration", "energy efficiency"],
        "official_url": "https://www.sciencedirect.com/science/article/pii/S0031320326015104",
        "pdf_url": "https://doi.org/10.1016/j.patcog.2026.114546",
        "access_note": "Publisher record; full PDF requires an institutional route",
        "downloadable": False,
    },
    {
        "title": "REPAIR: Validity-guided agentic planning for image restoration under extreme compound degradations",
        "year": 2027, "venue": "Pattern Recognition", "status": "in_press_2027",
        "topic_tags": ["compound degradation", "image restoration", "agentic planning"],
        "official_url": "https://doi.org/10.1016/j.patcog.2026.115189",
        "pdf_url": "https://www.sciencedirect.com/science/article/pii/S0031320326021527",
        "access_note": "Publisher record dated April 2027; full PDF requires an institutional route",
        "downloadable": False,
    },
]


def slugify(title: str, year: int) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return f"{value}_{year}"[:150]


def fetch(url: str, out: Path) -> None:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=90) as response:
        data = response.read()
    if not data.startswith(b"%PDF-"):
        raise RuntimeError(f"download is not a PDF: {url}")
    out.write_bytes(data)


def main() -> None:
    INCOMING.mkdir(exist_ok=True)
    literature = []
    for item in PAPERS:
        row = dict(item)
        row["local_slug"] = slugify(item["title"], item["year"])
        row["download_status"] = "unavailable" if not item["downloadable"] else "pending"
        paper_dir = INCOMING / row["local_slug"]
        if item["downloadable"]:
            pdf_path = paper_dir / "pdf" / "paper.pdf"
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fetch(item["pdf_url"], pdf_path)
                row["download_status"] = "downloaded"
                row["source_sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            except Exception as exc:
                row["download_status"] = f"failed: {exc}"
        literature.append(row)
    (ROOT / "metadata" / "literature_2026_2027_additions.json").write_text(
        json.dumps(literature, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"entries": len(literature), "downloaded": sum(x["download_status"] == "downloaded" for x in literature), "incoming": str(INCOMING)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
