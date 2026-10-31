# 全景低码率压缩与质量恢复文献索引

检索日期：2026-10-31。论文和图表资产位于同名英文子目录；完整字段见 `papers.json`。

## 优先阅读顺序

1. **全景/球面几何**：SphereSR、OSRT、DINN360、Spherical Pseudo-Cylindrical、HEAL-SWIN、OSLO。
2. **低码率压缩与恢复**：Beyond Perspective、CODiff、Frequency-Biased Compression and Compensation、Wavelet Feature Maps Compression。
3. **小波/频率与表示**：Nature Machine Intelligence 的 WIEN-INR、Wavelet-based Fourier Information Interaction、Rate-Distortion-Perception Tradeoff。
4. **ANN/SNN/KAN**：0.3-spike SNN、Dynamic Sparsity、KAN、Efficient Neural Codes。
5. **生物学依据**：Fixational Eye Movements、Panoramic Visual Statistics、Efficient Neural Codes。

## 核心链接

| 论文 | 年份/来源 | 适合借鉴的模块 | 正文或官方页面 |
|---|---|---|---|
| SphereSR | CVPR 2022，CCF-A | 连续球面表示、任意投影、球面超分 | [CVF 页面](https://openaccess.thecvf.com/content/CVPR2022/html/Yoon_SphereSR_360deg_Image_Super-Resolution_With_Arbitrary_Projection_via_Continuous_Spherical_CVPR_2022_paper.html) / [PDF](https://openaccess.thecvf.com/content/CVPR2022/papers/Yoon_SphereSR_360deg_Image_Super-Resolution_With_Arbitrary_Projection_via_Continuous_Spherical_CVPR_2022_paper.pdf) |
| OSRT | CVPR 2023，CCF-A | 失真感知 Transformer、全向超分 | [CVF 页面](https://openaccess.thecvf.com/content/CVPR2023/html/Yu_OSRT_Omnidirectional_Image_Super-Resolution_With_Distortion-Aware_Transformer_CVPR_2023_paper.html) / [PDF](https://openaccess.thecvf.com/content/CVPR2023/papers/Yu_OSRT_Omnidirectional_Image_Super-Resolution_With_Distortion-Aware_Transformer_CVPR_2023_paper.pdf) |
| DINN360 | CVPR 2023，CCF-A | 纬度感知可逆网络、高频恢复 | [CVF 页面](https://openaccess.thecvf.com/content/CVPR2023/html/Guo_DINN360_Deformable_Invertible_Neural_Network_for_Latitude-Aware_360deg_Image_Rescaling_CVPR_2023_paper.html) / [PDF](https://openaccess.thecvf.com/content/CVPR2023/papers/Guo_DINN360_Deformable_Invertible_Neural_Network_for_Latitude-Aware_360deg_Image_Rescaling_CVPR_2023_paper.pdf) |
| Spherical Pseudo-Cylindrical | AAAI 2024，CCF-A | 球面采样和ERP失真 | [AAAI 页面](https://ojs.aaai.org/index.php/AAAI/article/view/27846) |
| Beyond Perspective | ICCV 2025，CCF-A | 神经360°视频压缩、球面增强、位置编码 | [CVF 页面](https://openaccess.thecvf.com/content/ICCV2025/html/Regensky_Beyond_Perspective_Neural_360-Degree_Video_Compression_ICCV_2025_paper.html) / [PDF](https://openaccess.thecvf.com/content/ICCV2025/papers/Regensky_Beyond_Perspective_Neural_360-Degree_Video_Compression_ICCV_2025_paper.pdf) |
| End-to-End Optimized 360° Image Compression | IEEE TIP 2022 | 端到端360°压缩、率失真 | [PubMed 摘要](https://pubmed.ncbi.nlm.nih.gov/36166564/) |
| Learning Content-Weighted Pseudocylindrical Representation | IEEE TIP 2024 | 内容加权伪柱面表示、球面码率分配 | [PubMed 摘要](https://pubmed.ncbi.nlm.nih.gov/39418145/) |
| Learned Spherical Image Compression | IEEE TIP 2025 | 球面卷积、自注意力、Transformer上下文熵模型 | [PubMed 摘要](https://pubmed.ncbi.nlm.nih.gov/40644095/) |
| HEAL-SWIN | CVPR 2024，CCF-A | HEALPix 等面积球面网格、球面窗口注意力 | [CVF 页面](https://openaccess.thecvf.com/content/CVPR2024/html/Carlsson_HEAL-SWIN_A_Vision_Transformer_On_The_Sphere_CVPR_2024_paper.html) / [PDF](https://openaccess.thecvf.com/content/CVPR2024/papers/Carlsson_HEAL-SWIN_A_Vision_Transformer_On_The_Sphere_CVPR_2024_paper.pdf) |
| CODiff | ICCV 2025，CCF-A | 压缩感知扩散恢复、JPEG 伪影去除 | [CVF 页面](https://openaccess.thecvf.com/content/ICCV2025/html/Guo_Compression-Aware_One-Step_Diffusion_Model_for_JPEG_Artifact_Removal_ICCV_2025_paper.html) / [PDF](https://openaccess.thecvf.com/content/ICCV2025/papers/Guo_Compression-Aware_One-Step_Diffusion_Model_for_JPEG_Artifact_Removal_ICCV_2025_paper.pdf) |
| Frequency-Biased Synergistic Design | CVPR 2025，CCF-A | 低频/高频敏感性、压缩补偿联合设计 | [CVF 页面](https://openaccess.thecvf.com/content/CVPR2025/html/Liu_Frequency-Biased_Synergistic_Design_for_Image_Compression_and_Compensation_CVPR_2025_paper.html) / [PDF](https://openaccess.thecvf.com/content/CVPR2025/papers/Liu_Frequency-Biased_Synergistic_Design_for_Image_Compression_and_Compensation_CVPR_2025_paper.pdf) |
| Wavelet Feature Maps Compression | NeurIPS 2022，CCF-A | Haar 小波特征压缩、CNN 中间特征低码率传输 | [论文页](https://papers.neurips.cc/paper_files/paper/2022/hash/81f19c0e9f3e06c831630ab6662fd8ea-Abstract.html) / [PDF](https://papers.neurips.cc/paper_files/paper/2022/file/81f19c0e9f3e06c831630ab6662fd8ea-Paper-Conference.pdf) |
| KAN | ICLR 2025，CCF-A | 可学习边函数、可解释非线性映射 | [ICLR 页面](https://proceedings.iclr.cc/paper_files/paper/2025/hash/afaed89642ea100935e39d39a4da602c-Abstract-Conference.html) / [PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/afaed89642ea100935e39d39a4da602c-Paper-Conference.pdf) |
| WIEN-INR | Nature Machine Intelligence 2026 | DWT 多分辨率、频率细节、表示压缩 | [Nature 页面](https://www.nature.com/articles/s42256-026-01287-9) / [PDF](https://www.nature.com/articles/s42256-026-01287-9.pdf) |
| 0.3-spike SNN | Nature Communications 2024 | TTFS、脉冲稀疏、低事件数 | [Nature 页面](https://www.nature.com/articles/s41467-024-51110-5) / [PDF](https://www.nature.com/articles/s41467-024-51110-5.pdf) |
| Dynamic Sparsity | Nature Communications 2025，Perspective | 生物启发的动态稀疏、事件视觉 | [Nature 页面](https://www.nature.com/articles/s41467-025-65387-7) / [PDF](https://www.nature.com/articles/s41467-025-65387-7.pdf) |
| Fixational Eye Movements | Nature Communications 2024 | 视网膜脉冲、微眼动、多相位采样 | [Nature 页面](https://www.nature.com/articles/s41467-024-52304-7) / [PDF](https://www.nature.com/articles/s41467-024-52304-7.pdf) |
| Efficient Neural Codes | Nature Communications 2022 | 自然图像统计、梯度下降与高效编码 | [Nature 页面](https://www.nature.com/articles/s41467-022-35659-7) / [PDF](https://www.nature.com/articles/s41467-022-35659-7.pdf) |
| Internally generated population activity | Science Advances 2022 | 兴奋/抑制脉冲网络、Fisher information、信息传输 | [Science 页面](https://www.science.org/doi/10.1126/sciadv.abg5244) / [PDF](https://www.science.org/doi/pdf/10.1126/sciadv.abg5244?download=true) |
| Rate-Distortion-Perception Tradeoff | ICML 2019，信息论基础 | 码率、失真、感知质量评价 | [论文页](https://proceedings.mlr.press/v97/blau19a.html) / [PDF](https://proceedings.mlr.press/v97/blau19a/blau19a.pdf) |

## 原理映射

- **生物学**：视网膜的空间感受野和全景统计支持纬度/视野自适应；微眼动和脉冲时序支持多相位、时空联合重建；动态稀疏支持事件触发和选择性更新。
- **物理/信息论**：率失真感知权衡用于定义低码率恢复目标；球面等面积采样减少ERP纬度采样偏差；小波和傅里叶分解把容量分配与频率能量联系起来。
- **方法组合建议**：球面表示或纬度权重处理几何，DWT/频域支路处理低码率伪影，KAN 用于子带自适应非线性，ANN/SNN 动态稀疏用于计算和功耗控制。

## 访问边界

`papers.json` 中的 `access` 字段区分公开 PDF、作者公开 PDF、出版社 PDF 和只有元数据的条目。AAAI 2024 球面伪柱面论文当前只保存官方页面链接，因为下载响应不是 PDF；没有绕过登录或付费墙。中科院分区会随年份、大类/小类和学校目录变化，使用前请按本校当年目录复核。
