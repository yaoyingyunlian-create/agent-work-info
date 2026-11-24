from pathlib import Path
import json

root=Path(__file__).resolve().parents[1]
rows=json.loads((root/'素材库/原件清单.json').read_text(encoding='utf-8'))
images=[r for r in rows if 'id' in r]
titles='''双乳礼盒主视觉 Lift & Contour Duo
银瓶紧致亮颜精华乳·配方成分
金瓶紧致抗皱精华乳·核心成分
金瓶紧致抗皱精华乳·配方详情
双乳护理步骤·银瓶全脸与金瓶局部叠加
双乳质地与肤感
三步护理·精华液与双乳容量及顺序
肌肤护理需求·紧致提拉焕亮
抗衰双乳礼盒·两款50g
源自新加坡·品牌与系列理念
紧致亮颜焕活精华液·100mL主视觉
精华护理诉求·紧致提拉亮泽
多肽日常养护·紧致提拉焕亮主题
双肽复配·蓝铜肽与乙酰基六肽-8
精华六大成分·协同养护
精华质地与肤感·使用方法
精华效果主题·重拾饱满无惧岁月
先精华再乳1乳2·使用顺序
精华品牌理念·源自新加坡
Peptide Renewal Essence · 100mL
Skin Goals · Firm Lift Brighten
Dual Peptides · Copper Tripeptide-1 & Acetyl Hexapeptide-8
Texture & Feel · Light as Water Soft on Skin
The Daily Ritual · A Moment for Your Skin Every Day
Your Three-Step Ritual · Essence Then Emulsions 1 & 2
Texture & Feel · Light as Water Effortless to Layer
The Formula · Six Ingredients
The Origin · Born in Singapore
焕亮净透颜·烟酰胺与二裂酵母主题
水润透亮·神经酰胺与保湿主题
草本洗发水·净澈头皮清爽蓬松
草本洗发水·强韧发根告别脆弱
草本强韧洗发水·告别头顶扁塌
28天毛囊蓄养·28天与98%效果宣传
28天毛囊蓄养·焕活毛囊与98%及92%宣传
28天毛囊蓄养·强韧发根丰盈发丝
院线级头皮抗衰全案·总览封面
品牌背景·配方库GMP SGS HSA宣传
创始人故事·暖暖 MU ZI与品牌身份
头皮危机·头皮护理痛点
头皮警报·头屑油腻泛红及白发主题
市场机遇·黑金防脱与黑银黑发双系列
三步头皮护理原理·净透营养激活宣传
产品优势对比·价格与资质宣传
活力防断发洗发水·五项特色
奢养防断发精华液·配方与阶段示意
活力黑发洗发水·五项特色
活力奢养黑发精华液·配方与白发主题
多重复合维生素·头皮养护原理宣传
电动导液梳·与徒手涂抹方式比较
电动导液梳·导液模式与设备特色
居家养护SOP·洗装梳三步及模式示意
可视导液梳·App三光EMS功能宣传
可视导液梳·检测导液防水充电功能
目标人群·四类需求与方案定位
真实案例对比记录·头皮前后对比图
产品矩阵·双系列与两类设备
双系列统一价格·零售渠道联创及设备价格
渠道支持·流量培训素材与区域保护
合作邀请·二维码与联系方式区'''.splitlines()
assert len(images)==len(titles)==60
annotations=[]
for r,title in zip(images,titles):
    n=int(r['id'][1:])
    group=('Yvelise双乳礼盒' if n<=10 else 'Yvelise精华中文' if n<=19 else 'Yvelise精华英文' if n<=28 else '护肤主题' if n<=30 else '草本洗发水' if n<=33 else '28天头皮护理' if n<=36 else '头皮护理与招商')
    risk='功效、成分、产品标签及素材授权待核验'
    if n<=10: risk='双乳套装范围、¥498文件夹价格与宣传事实待确认'
    elif n<=19: risk='¥198为源文件夹标记；正式价格和成分/功效待确认'
    elif n<=28: risk='$48为源文件夹及需求文字标记；币种和有效期未明确'
    elif n in [34,35,36,43,48,49,50,56]: risk='生发/黑发、28天、百分比或案例宣传未见原始证据；需核验'
    elif n in [38,44]: risk='GMP/SGS/HSA及制造/进口等宣传未取得对应原始证明'
    elif n==39: risk='人物履历、品牌关系及肖像使用授权待核验'
    elif n in [51,52,53,54]: risk='设备型号、参数、说明书、App及适用方式待核验'
    elif n==55: risk='招商人群定位不等于已确认适用或安全人群'
    elif n==58: risk='零售/拿货价及50%/70%比例均为图片宣传；有效条件待确认'
    elif n in [59,60]: risk='合作政策、授权及联系信息未核验；未解析二维码或发起联系'
    annotations.append(dict(id=r['id'],source_relative=r['source_relative'],source_sha256=r['sha256'],title=title,category=group,language='英文' if 20<=n<=28 else '中文',risk=risk))
out=root/'素材库/人工标注.json'
if out.exists(): raise RuntimeError('人工标注已存在，不覆盖')
out.write_text(json.dumps(annotations,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'已建立{len(annotations)}条原路径/哈希绑定标注')
