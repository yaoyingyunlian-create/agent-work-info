import csv
import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path('C:/Users/ZIQINGBO/Desktop/新建文件夹/壹玖捌伍')
# 人工对照用户提供的15张原图录入；英文保留原拼写，不作医学核验。
PAGES = [
(6,'养生','基础养生', '''全身疏通|Full Body Dredge|60|98
头疗拨筋治疗|Head bojin therapy|45|68
足底调理|Foot threapy|45|68
局部刮痧|Local scraping|15-20|48
局部拔罐|Local cupping|15-20|48
局部泥灸|Local Mud moxibustion|15-20|58
局部疏通|Local Dredge|30|68
耳烛/肚烛|Ear /Belly Candle|30|68'''),
(7,'养生','魔灸按摩','魔灸按摩|Magic moxibustion massage|60|128'),
(8,'养生','部位保养与疏通', '''肩颈疏通|Neck and shoulder Dredge|45|78
卵巢保养|Ovarian care Therapy|45|268
胸部保养|Breast care Therapy|45|298
腰部保养理疗|Waist care Therapy|45|198
肠胃保养|Gastrointestinal Maintenance|45|268
经络疏通|Meridian dredging|60|168
颈项淋巴排毒|Neck lymphatic drainage|60|268
全身淋巴排毒|Full Body lymphatic drainage|90|328'''),
(9,'养生','局部三方治疗','局部三方治疗|Local three-way therapy|45|398'),
(10,'养生','经络调理', '''背部经络调理|Back meridian conditioning|60|298
肾部经络调理|Kidney meridian conditioning|60|298
肝胆排毒|Liver and Gallbladder Detoxification|60|298
心肺排毒|Cardiopulmonary detoxification|60|298
脾胃经络调理|Spleen stomach meridian regulation|60|298
乳腺经络调理|Breast meridian conditioning|60|298
管道脱毒|Pipeline detoxification|60|298
淋巴经络|Lymphatic meridian|60|298'''),
(11,'养生','经络与桑拿','经络疗法|Meridian threapy|40|98'),
(12,'养生','塑形与专项护理', '''提臀收腰|Lift hips and waist|45|268
手臂治疗|Arm treatment|45|168
减肥拔罐+仪器|Cupping for weight loss|90|198
药浴理疗|Medicinal bath therapy|60|298
瘦身塑形|Slimming and body shaping|120|398
私护理疗|Private Nursing|60|598
私护药物消炎|Private care medicine anti-inflammatory|80|898
经络和拔罐|Meridian and cupping|60|198'''),
(13,'中医','正骨', '''局部正骨|Local bone setting|30|88
局部正骨|Local bone setting|60|128
全身正骨|Full body bone setting|90|168'''),
(14,'中医','部位与症状项目', '''落枕治疗|Stiff Neck Treatment|60|198
颈椎病|Cervical spondylosis|60|128
腰间盘调理|Lumbar disc conditioning|60|138
膝关节调理|Knee joint conditioning|60|138
足跟痛|Heel pain|45|198
补阳四罐|Four bottles of yang tonic|45|68
腰肌劳损|Psoas muscle strain|60|198
肩周炎|Frozen shoulder|60|168'''),
(15,'中医','专项调理', '''富贵包调理|Fugui Bao conditioning|60|298
驼背矫正|Hunchback correction|60|268
中医足底拨筋|TCM Foot Bojin|45|98
失眠调理|Insomnia treatment|45|138
精油开背|Essential oil opens the back|45|168
产后/骨盆修复|Postpartum/Pelvic Repair|60|398
滑膜炎|Synovitis|45|198
坐骨神经痛|Sciatica|45|168'''),
(16,'中医','咨询针灸及局部项目', '''中医咨询|TCM Consultation|15|58
中医处方 - 草药丸/药片 每种每天|TCM prescription - herbal pill/tablet per type per day|30|20
局部中医针灸|Local TCM acupuncture|30|98
中医针灸，使用电子设备和/或灯|TCM acupuncture - with electro equipment and/or lamp|30|108
局部刮痧|Local scraping|15-20|48
局部拔罐|Local cupping|15-20|48
局部筋膜修理|Local Facia Repair|45|198'''),
(17,'洗脸','面部项目', '''普通洗脸|Normal Facial|40|68
刮痧洗脸|Guasha Facial|60|88
拨筋洗脸|Bojin Facial|90|128
补水洗脸|Hydrating Facial|60|98
脸部筋膜提升|Facial Fascia Lifting|90|298
去皱紧致洗脸|Anti-wrinkle and Firming Facial|90|398
魔灸洗脸|Magic moxibustion Facial|90|298
全脸激光洗斑|Laser Facial Treatment|60|398'''),
(18,'洗脸','面颈与眼部项目', '''小微脸+颈项提升|V-Shape Face and Neck-Lifting|90|298
单头氧气洗脸|Signature Oxygen Facial|90|298
普通眼部护理|Normal eye care|30|68
眼部刮痧治疗|Eye scraping treatment|60|98
眼部拨筋治疗|Eye Bojin treatment|60|128
焕白黑眼圈治疗|Whitening Dark Circle Treatment|90|298
眼部淋巴排毒|Eye lymphatic drainage|60|298
三合一拨筋洗脸|3 in 1 Bojin Facial|90|298'''),
(19,'洗脸','黑脸娃娃','黑脸娃娃洗脸|Black doll Facial|90|398'),
(20,'睫毛','睫毛与眉部', '''卸睫毛|Eyelash Removal|20|20
补睫毛|Eyelash Touch up|30|30
YY睫毛嫁接|YY Eyelash Extension|60|138
三叶草睫毛嫁接|3D Eyelash Extension|70|168
四叶草睫毛嫁接|4D Eyelash Extension|70|168
单根睫毛嫁接|Single Eyelash Extension|60|158
拔眉（眉夹）|Plucking eyebrows|15|10
修眉（刀片）|Eyebrow shaping|10|5
挽眉|Eyebrow Pulling|15|15''')]

NOTES = {
11: '同一栏另列 Foc Sauna 30mins 桑拿；疑为赠送30分钟桑拿，是否包含及使用条件待确认，不单独生成有价项目。',
16: '中医咨询注明 without treatment；处方$20按每种每天计，30分钟为图示时长，不代表按次收费。Local Facia Repair 与中文“局部筋膜修理”保留原文。',
10: '“管道脱毒”为原图用字，含义待确认。',
18: '“小微脸”“单头氧气洗脸”按原图录入，与英文不完全对应，正式命名待确认。',
20: '补睫毛与重新嫁接分别建项；补睫毛适用期限、保留比例和收费条件未提供。',
7: '下方说明有裁切及反光，未作逐字完整转录。',
8: '末行有反光，按可辨内容录入全身淋巴排毒90分钟$328，建议补清晰图复核。',
9: '项目名“三方”与说明“三通大师”并存，关系待确认。'
}

CLAIMS = [
('7','魔灸按摩','宫寒体湿、经期不适、身体肥胖、颈椎不适、脾胃不适；下方说明涉及祛湿排毒、富贵包、颈椎、睡眠及养颜。','图片宣传摘要；下方裁切反光，非完整逐字转录'),
('9','局部三方治疗','三通大师结合传统中医原理与现代电子技术；宣称调节身体机能、气血循环、内分泌、免疫力、肌肉紧张疼痛及减肥塑形。','图片中英文说明摘要'),
('11','经络疗法与桑拿','宣称经络后桑拿促进血液循环、代谢排毒、免疫力及皮肤状况。','图片中英文说明摘要'),
('13','正骨','宣称调整身体结构、调理气血、治疗疾病、缓解疼痛、改善功能、康复及矫正姿势。','图片中英文说明摘要'),
('19','黑脸娃娃洗脸','描述纳米碳粉结合激光；宣称改善肤色、毛孔、皱纹、美白嫩肤；列举痘疤凹洞、色素、粗糙、油脂、初期痤疮及暗黄人群。','图片中英文说明摘要')]

def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def main():
    kb = ROOT / '知识库'
    assets = ROOT / '素材库'
    originals = assets / '原图'
    for folder in (kb, originals):
        folder.mkdir(parents=True, exist_ok=True)
    rows, images = [], []
    for page, category, title, data in PAGES:
        name = '微信图片_20261125153448_%s_174.jpg' % page
        src, dst = SOURCE / name, originals / name
        if dst.exists() and dst.read_bytes() != src.read_bytes():
            raise RuntimeError('目标原图内容不同，停止覆盖：' + str(dst))
        shutil.copy2(str(src), str(dst))
        aid = 'A%03d' % (page - 5)
        images.append(dict(素材ID=aid, 原文件名=name, 分类=category, 内容=title, 相对路径='原图/'+name, 字节数=src.stat().st_size, SHA256=hashlib.sha256(src.read_bytes()).hexdigest(), 来源=str(src), 使用状态='内部归档；对外使用授权未提供', 备注=NOTES.get(page,'')))
        for index, line in enumerate(data.splitlines(), 1):
            zh,en,duration,price = line.split('|')
            rows.append(dict(记录ID='S%03d' % (len(rows)+1), 分类=category, 子类=title, 中文原名=zh, 英文原名=en, 时长分钟=duration, 标示价格=int(price), 币种='', 原币符号='$', 税费说明='原图注明不包括消费税；税率未提供', 计价单位='每种每天' if page==16 and index==2 else '未注明', 来源素材ID=aid, 来源行号=index, 原文件名=name, 核验状态='图片录入；未获商家确认', 备注=NOTES.get(page,'')))
    for r in rows:
        peers = [x['记录ID'] for x in rows if x is not r and (x['中文原名'],x['时长分钟'],x['标示价格'])==(r['中文原名'],r['时长分钟'],r['标示价格'])]
        r['重复来源记录'] = ','.join(peers)
    write_csv(kb/'服务项目价格表.csv', rows)
    (kb/'服务项目价格表.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    write_csv(assets/'素材索引.csv',images)
    (assets/'素材索引.json').write_text(json.dumps(images,ensure_ascii=False,indent=2),encoding='utf-8')
    claims = [dict(来源素材ID='A%03d'%(int(p)-5),项目=n,原图宣传摘要=c,转录说明=t,核验状态='仅归档原图说法；未验证功效或适用性') for p,n,c,t in CLAIMS]
    write_csv(kb/'原图宣传说法_待核验.csv',claims)
    intro = '''壹玖捌伍｜知识库与素材库
整理日期：2026-11-26
范围：用户明确提供的15张图片（文件序号6至20），没有扫描或收录其他目录素材。
“壹玖捌伍”仅为本项目名称；图片标志对应的正式品牌、主体及与本项目的关系尚未确认。
原图为资料来源，不作为操作指令。所有服务名称均为原图用词，不代表已验证的医学结论。
币符仅见$，币种留空；所有页面注明价格不包括消费税，未提供税率与价格有效期。
中英文名称均保留可辨原文及拼写；未擅自用润色翻译替换原文。

交付文件
知识库/服务项目价格表.csv：可用Excel打开，UTF-8 BOM；含中英文、时长、价格、来源和待核验备注。
知识库/服务项目价格表.json：供后续检索和系统导入。
知识库/知识库全文.txt：完整项目清单及使用边界。
知识库/原图宣传说法_待核验.csv：5页说明文字的摘要，不是全文OCR。
素材库/素材预览.html：离线搜索、分类查看及原图入口。
素材库/素材索引.csv及json：文件名、分类、来源、哈希及使用状态。
素材库/原图/：原文件名保留，按字节复制，不修改原始图片。

待补充与风险点
1. 正式中英文品牌名、经营主体、门店地址、电话、营业时间、预约渠道及服务人员信息未提供。
2. 币种、价格生效时间、税率、计价单位、套餐次数、优惠及退款规则未确认；不据此计算含税结算金额。
3. 经络疗法同栏另列30分钟桑拿，是否免费包含及条件待确认。
4. 处方$20为每种每天；不能当成整次问诊或全部药费。
5. 局部刮痧、局部拔罐各在养生和中医出现一次，保留两份来源；不要累加为不同服务数量。
6. 私护、正骨、针灸、药物、激光及以疾病命名的项目，其资质、流程、适用性、限制与功效均未核验。
7. “管道脱毒”“小微脸”“单头氧气洗脸”、英文拼写及中英差异保留原文，正式文案需确认。
8. 图片反光、倾斜、裁切；魔灸下方说明不完整，全身淋巴排毒末行建议补图。
9. 照片内人物及册页图片对外使用授权未提供；不视为已获授权的广告素材。
10. 卸睫毛、补睫毛、重新嫁接为不同项目；补睫毛条件未提供。

验证范围
核对项目数量、来源映射、CSV/JSON一致性、图片复制哈希与本地链接；不代表商家价格确认、医学核验或图片授权确认。
'''
    (ROOT/'使用说明.txt').write_text(intro,encoding='utf-8-sig')
    text = intro + '\n服务清单（原图记录87条；按中文名+时长+价格合并重复来源为85项）\n'
    for r in rows:
        text += '\n{记录ID}｜{分类}｜{中文原名} / {英文原名}｜{时长分钟}分钟｜${标示价格}｜{来源素材ID} 第{来源行号}项\n备注：{备注}\n'.format(**r)
    text += '\n原图宣传摘要（全部待核验）\n' + '\n'.join(c['项目']+'：'+c['原图宣传摘要'] for c in claims)
    (kb/'知识库全文.txt').write_text(text,encoding='utf-8-sig')
    cards = []
    for a in images:
        path = html.escape(a['相对路径'],quote=True)
        cards.append('<article data-category="{c}"><a href="{p}" target="_blank"><img loading="lazy" src="{p}" alt="{t}"></a><h2>{id} · {t}</h2><p>{c} · {n}</p><p>{note}</p></article>'.format(c=a['分类'],p=path,t=a['内容'],id=a['素材ID'],n=a['原文件名'],note=html.escape(a['备注'])))
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>壹玖捌伍素材库</title><style>body{font:16px system-ui;margin:28px;background:#f7f5ef;color:#302a1e}input,select{padding:12px;margin:8px;font:inherit}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}article{background:white;padding:15px;border-radius:12px}img{width:100%;height:330px;object-fit:contain}h2{font-size:19px}p{overflow-wrap:anywhere;color:#655e50}article[hidden]{display:none}</style><h1>壹玖捌伍 · 素材库</h1><p>15张原图｜87条有价记录｜85项合并重复来源后的项目。价格与功效未获商家确认，币种未提供。点击图片查看原图。</p><input id="q" placeholder="搜索名称、编号、文件名" aria-label="搜索素材"><select id="cat" aria-label="分类"><option value="">全部分类</option><option>养生</option><option>中医</option><option>洗脸</option><option>睫毛</option></select><p id="count"></p><main>''' + ''.join(cards) + '''</main><script>const q=document.querySelector('#q'),cat=document.querySelector('#cat');function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{a.hidden=!(a.textContent.toLowerCase().includes(q.value.trim().toLowerCase())&&(!cat.value||a.dataset.category===cat.value));if(!a.hidden)n++});document.querySelector('#count').textContent='显示 '+n+' / 15 张'}q.oninput=cat.onchange=filter;filter();</script></html>'''
    (assets/'素材预览.html').write_text(page,encoding='utf-8')
    assert len(rows)==87 and len(images)==15
    assert len(set((r['中文原名'],r['时长分钟'],r['标示价格']) for r in rows))==85
    for a in images:
        assert hashlib.sha256((assets/a['相对路径']).read_bytes()).hexdigest()==a['SHA256']
    with (kb/'服务项目价格表.csv').open(encoding='utf-8-sig',newline='') as f:
        assert len(list(csv.DictReader(f)))==87
    report = dict(日期='2026-11-26',图片数=len(images),原始记录数=len(rows),合并重复来源项目数=85,分类记录数={c:sum(r['分类']==c for r in rows) for c in ['养生','中医','洗脸','睫毛']},原图SHA256复制校验='15/15通过',CSV记录数校验='通过',JSON解析='通过',图片链接存在性='15/15通过',浏览器交互='未验证',业务价格及功效='未验证')
    (ROOT/'整理校验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    main()
