import json
from pathlib import Path
import fitz

ROOT = Path('.')

def save_crop(slug, label, page_index, bbox, caption, name):
    d = ROOT / slug
    mf = d / 'manifest.json'
    data = json.loads(mf.read_text(encoding='utf-8'))
    page = fitz.open(d / data['pdf'])[page_index]
    rect = fitz.Rect(*bbox)
    out = d / 'figures' / 'original' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    pix = page.get_pixmap(matrix=fitz.Matrix(4,4), clip=rect, alpha=False)
    pix.save(out)
    asset = {
        'kind':'figure','label':label,'page':page_index,
        'caption':caption,'caption_en':caption,'caption_zh':'',
        'caption_bbox': [0,0,0,0], 'content_bbox': list(bbox), 'crop_bbox': list(bbox),
        'original': str(out.relative_to(d)).replace('\\','/'),
        'vector': [], 'vector_status':'unavailable_temporary','ppt_status':'unavailable_temporary','svg_status':'unavailable_temporary',
        'download_note':'PPT/SVG 暂不可用；当前提供去 caption 的原始 PNG；表格另提供 LaTeX。'
    }
    data['assets'].append(asset)
    data['assets'].sort(key=lambda a:(a['page'],a['kind'],a['label']))
    mf.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Nature MI Fig. 6: visual is on page 8 while its caption is at bottom of page 7.
slug='Adopting_a_human_developmental_visual_diet_yields_robust_and_shape_based_AI_vision_2026'
cap='Fig. 6 | ANNs trained with DVD exhibit enhanced degradation robustness to image degradations and adversarial attacks. a, Alignment of DVD-B-trained and baseline models with human data for blur and noise robustness. b, Resilience to various image degradations, including different levels of noise, blurring, image quality deficits and weather effects. c, Improved resilience to white-box and black-box adversarial attacks.'
save_crop(slug,'Fig6',7,(38,42,562,714),cap,'Fig6_p008.png')

# CVPRW NTIRE Burst HDR Fig. 1 is the left-column dataset overview on page 3.
slug='NTIRE_2026_Challenge_on_Efficient_Burst_HDR_and_Restoration_Datasets_Methods_and_Results_2026'
cap='Figure 1. Overview of the proposed competition dataset. (a) A representative HDR GT RGB image and (b) a corresponding cropped patch highlighting local details. (c) The RAW reference frame, which is spatially aligned with the GT, and (d) a sequence of auxiliary RAW frames captured at varying exposure levels.'
save_crop(slug,'Fig1',2,(55,45,300,225),cap,'Fig1_p003.png')

# Remove known body-reference/appendix false positives before QA.
for slug, remove in {
 'CHROMA_MILL_Joint_Low_Light_Enhancement_and_White_Balance_under_Colored_Illumination_2027': {('figure','Fig7'),('table','Table6'),('table','Table7')},
 'Freeze_the_Structure_Free_the_Color_Fourier_Domain_Training_for_Unpaired_Smartphone_ISP_2026': {('table','Table4')},
 'NTIRE_2026_Challenge_on_Efficient_Burst_HDR_and_Restoration_Datasets_Methods_and_Results_2026': {('table','Table2')},
}.items():
    mf=ROOT/slug/'manifest.json'; data=json.loads(mf.read_text(encoding='utf-8'))
    data['assets']=[a for a in data['assets'] if (a.get('kind'),a.get('label')) not in remove]
    mf.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('manual fixes applied')
