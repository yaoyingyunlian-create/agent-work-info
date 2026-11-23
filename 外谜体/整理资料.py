from pathlib import Path
from PIL import Image, ImageOps
import hashlib, json, csv, html
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / '素材库'
KB = ROOT / '知识库'
for directory in (OUT, KB, OUT / '缩略图'):
    directory.mkdir(parents=True, exist_ok=True)

# 按原始文件名排序，与预览联系表的编号一致。标题为人工看图初步编目。
titles = '''吟釀艷全效菁萃露宣传长图
吟釀艷全效菁萃露宣传长图
护肤原理宣传图
护肤产品网页截图
护肤产品网页截图
芯優瑪MAX商品页
芯優瑪MAX宣传页
人物及奖项宣传页
芯優瑪MAX配方宣传页
芯優瑪MAX场景宣传页
芯優瑪MAX生活场景页
芯立強MAX商品页
芯立強MAX包装宣传页
芯立強MAX研究宣传页
芯立強MAX原料宣传页
金必瑪MAX商品页
金必瑪MAX原料宣传页
金必瑪MAX专利宣传页
備護威MAX商品页
備護威MAX研究宣传页
固穩健商品页
固穩健配方宣传页
固穩健合作宣传页
固穩健原料宣传页
固穩健配方宣传页
舒視樂MAX商品页
舒視樂MAX包装宣传页
舒視樂MAX研究宣传页
舒視樂MAX场景宣传页
舒視樂MAX人群宣传页
眼部疾病展示板
芯立強及好勁活等组合实拍
一氧化氮宣传资料
血管与年龄宣传资料
产品及配方宣传资料
穆拉德心血管产品演化宣传资料
勁活力Plus及金必瑪Plus宣传资料
貝立好系列机能奶粉宣传资料
穆拉德一氧化氮专利宣传资料
多产品包装合集
一氧化氮宣传资料
血管与年龄宣传资料
人物与奖项宣传资料
外泌體与干细胞比较宣传资料
勁有力等产品折页
一氧化氮及产品折页
牛樟芝咖啡商品页
紅藏信息能牛樟芝咖啡商品页
植得穩包装正面
植得穩包装背面
普靈寶包装正反面
固穩健包装正反面
唐舒穩包装正反面
日日光包装正反面
P26森肺草膠囊包装正反面
好夢眠眠包装正反面
P26森肺草膠囊包装侧面
樟業堂牛樟芝膠囊宣传单
樟業堂牛樟芝膠囊宣传单
牛樟芝与外泌體等宣传合集
外泌體书籍及资料聊天截图
人物与外泌體资料聊天截图
资料聊天截图
牛樟芝资料聊天截图
牛樟芝资料聊天截图
产品资料聊天截图
外泌體书籍及资料聊天截图
群聊资料截图
常泌樂膠囊包装正反面
B群及真有力组合实拍
唐舒穩与普靈寶组合实拍
常泌樂与舒秘悠组合实拍
超級NK牛樟芝等组合实拍
呀口樂与P26组合实拍
外泌體NMN与植得穩组合实拍
外泌體NMN实拍
植得穩实拍
P26森肺草膠囊实拍
绿色盒装护肤产品实拍-名称待确认
NOX盒装产品实拍
护肤面膜产品实拍-名称待确认
Aloe Vera盒装产品实拍
粉色盒装护肤产品实拍-名称待确认
勁有力超級实拍
勁活力PLUS实拍
舒秘悠实拍
常泌樂膠囊实拍
普靈寶实拍
唐舒穩实拍
真有力B群实拍
B群加实拍
日日光实拍
金必瑪PLUS实拍
芯立強PLUS实拍
巧活絡实拍
固穩健实拍
新曲線实拍
固步立实拍
舒視樂EX实拍
貝立好晶力实拍
貝立好暢力实拍
貝立好管力实拍
好夢眠眠实拍
活力沛芯立通实拍
活力沛備護通实拍
儿童口嚼锭实拍-名称待确认
鱘MAX实拍-完整名称待确认
印加果油MAX实拍
红盒产品实拍-完整名称待确认
苦瓜胜肽NMN MAX实拍
鹿类NMN MAX实拍-完整名称待确认'''.splitlines()

files = sorted((ROOT / '图片').glob('*.jpg'))
assert len(files) == len(titles), (len(files), len(titles))
rows = []
seen = {}
for i, (path, title) in enumerate(zip(files, titles), 1):
    if i <= 5 or 79 <= i <= 83:
        category = '护肤与化妆品'
    elif 6 <= i <= 30 or i in (47,48):
        category = '商品网页截图'
    elif 61 <= i <= 68:
        category = '聊天截图'
    elif i in (31,33,34,35,36,37,38,39,41,42,43,44,45,46,58,59,60):
        category = '宣传与培训资料'
    else:
        category = '产品包装实拍'
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    asset_id = f'A{i:03d}'
    with Image.open(path) as original:
        width, height = original.size
        original.verify()
    with Image.open(path) as original:
        thumb = ImageOps.exif_transpose(original).convert('RGB')
        thumb.thumbnail((360,360))
        thumb.save(OUT / '缩略图' / f'{asset_id}.jpg', quality=85)
    rows.append(dict(id=asset_id, title=title, category=category,
                     source=path.relative_to(ROOT).as_posix(), width=width, height=height,
                     bytes=path.stat().st_size, sha256=digest, duplicate_of=seen.get(digest,''),
                     status='人工缩略图初分；包装小字未逐字核验；发布授权待确认'))
    seen.setdefault(digest, asset_id)

(OUT/'素材清单.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
with (OUT/'素材清单.csv').open('w', encoding='utf-8-sig', newline='') as stream:
    writer=csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

def link(i):
    row=rows[i-1]
    return f"[{row['id']}](../{row['source']})"

groups = [
 ('护肤系列', [1,2,3,4,5,79,80,81,82,83], '绿色瓶宣传图可读到吟釀艷全效菁萃露；与后续盒装护肤品是否同系列待确认。'),
 ('芯優瑪MAX', list(range(6,12)), '按商品截图单独保留名称，不能直接当成芯立強的别名。'),
 ('芯立強系列', [12,13,14,15,32,94], 'MAX与PLUS分别留存；配方及规格关系待确认。'),
 ('金必瑪系列', [16,17,18,37,93], 'MAX与PLUS不合并为同一SKU。'),
 ('備護威／備護通', [19,20,105], '名称不同，暂作检索关联；是否对应原文“懾護威”待确认。'),
 ('固穩健', [21,22,23,24,25,52,96], '有商品截图及包装正反面。'),
 ('舒視樂系列／日日光', [26,27,28,29,30,54,92,99], '舒視樂MAX、舒視樂EX、日日光分别记录；是否对应原文“超舒視”待确认。'),
 ('牛樟芝与咖啡', [47,48,58,59,60,65,73], '咖啡、膠囊及超級NK牛樟芝不视为同一种产品。'),
 ('植得穩／外泌體NMN', [49,50,75,76,77], '名称初步转录；同框不代表同一SKU。'),
 ('普靈寶', [51,71,88], '有包装正反面和场景图。'),
 ('唐舒穩', [53,71,89], '有包装正反面和场景图。'),
 ('P26森肺草膠囊', [55,57,74,78], '包装可见P26及CISD2文字，含义及配方待复核。'),
 ('好夢眠眠', [56,103], '包装可见日本进口字样；进口与生产文件未提供。'),
 ('常泌樂／舒秘悠', [69,72,86,87], '两种产品分别留存，暂按同框建立检索关联。'),
 ('勁有力／勁活力／好勁活', [32,37,45,84,85], '原文和包装名称有差异，时长宣传尚无验证资料。'),
 ('B群系列', [70,90,91], '真有力B群与B群加分别记录。'),
 ('貝立好系列', [38,100,101,102], '晶力、暢力、管力为不同包装。'),
 ('其他产品待细分', [95,97,98,104,106,107,108,109,110,111], '部分品名需放大包装或补充原始电子资料。'),
 ('综合展示与培训资料', [31,33,34,35,36,39,40,41,42,43,44,46,61,62,63,64,66,67,68], '人物、奖项、专利、机理及疗效均为资料中的宣传内容，未做外部核验。'),
]

knowledge = ['# 产品知识索引\n', '整理日期：2026-11-23。用途：内部检索与后续补充。\n',
 '资料来源仅为本目录原件。产品名来自人工看图初步转录；分类代表素材内容，不代表成分、疗效或适用人群已获验证。包装繁体字和英文型号保留，简繁混合为原始来源差异。未做全文OCR，未补写看不清的包装小字。\n',
 '## 项目已知信息\n', '- 原始文字指定：广告主要面向东南亚。具体国家、语言、平台、客群、投放主体尚未提供。\n- 工作目录名为“外谜体”；图片中的“外泌體”为资料原词，两者暂不擅自统一为品牌名。\n', '## 产品与资料分组\n']
for name, ids, note in groups:
    knowledge += [f'### {name}\n', note+'\n', '素材：'+'、'.join(link(i) for i in ids)+'\n']
knowledge += ['## 仍需补充\n', '- 正式产品目录：标准品名、品牌主体、SKU、版本、规格、成分、生产商、产地与说明书。\n- 价格、币种、库存、渠道及有效日期；不将截图旧价格录作当前报价。\n- 目标国家、所需语言、当地产品登记文件及可使用的宣传表述。\n- 宣传出处、研究原文、专利号对应文件、人物肖像及图片使用授权。\n- 原始无压缩产品图、透明底图、正式多语言文案。\n']
(KB/'产品知识索引.md').write_text('\n'.join(knowledge), encoding='utf-8')

source_text=(ROOT/'文字.txt').read_text(encoding='utf-8')
claims=[line.strip() for line in source_text.splitlines() if line.strip()]
claims_md=['# 原始诉求与待核验项\n', '来源：[文字.txt](../文字.txt)。逐行保留原文，原文的数字、时长、排名及疗效表述均不作为知识库中的已验证事实。此表仅整理提供资料，不作医学或当地广告规则判断。\n', '| 编号 | 原文 | 整理状态 |\n|---|---|---|']
for i,line in enumerate(claims,1):
    state='已记录投放区域意向；具体国家与语言待补充' if i==1 else '原始宣传诉求；证据及准确产品对应待核验'
    claims_md.append(f'| T{i:02d} | {line} | {state} |')
claims_md += ['\n## 当前不能确定的对应关系\n', '- “根深28 种癌症”语义和产品对应不清楚，原样保留。\n- “超舒視”与图片中的舒視樂／日日光、“懾護威”与備護威／備護通：只作为检索线索，不作正式别名。\n- “全身骨关節”“心血管除油”“病中快速修復”：未指定准确SKU。\n- “日本原装进口，化粧品All in one”：现有图中未确认完整对应品名及进口文件。\n- 牛樟芝咖啡的“解酒第一名”、男性产品的24／48小时、化妆品的0.1秒等说法：未提供相应验证材料。\n']
(KB/'原始诉求与待核验项.md').write_text('\n'.join(claims_md), encoding='utf-8')

duplicates=[r for r in rows if r['duplicate_of']]
report=['# 整理与验证记录\n', '日期：2026-11-23。原文件保留，未移动、改名、覆盖或删除。\n',
 f'- 输入：1份文字，{len(rows)}张JPG。\n- 所有JPG均通过Pillow文件完整性检查；尺寸、字节数、SHA-256已写入清单。\n- 完全相同的图片：'+str(len(duplicates))+'张重复副本；去重后'+str(len(seen))+'张。\n- 人工查看5张联系表，完成图片内容初分；每张生成独立缩略图。\n',
 '## 完全重复项\n', '| 重复项 | 首次出现 |\n|---|---|']
report += [f"| {r['id']} | {r['duplicate_of']} |" for r in duplicates]
report += ['\n相似画面、不同角度、同产品不同版本均未视为完全重复。\n',
 '## 已完成\n', '- 原始资料清点、内容初分、产品关联、原始诉求保留、重复检查、JSON／CSV清单、可搜索HTML预览及Markdown索引。\n',
 '## 未完成与风险\n', '- 包装小字逐字核对、全文OCR、SKU标准化、简繁英正式名称对照尚未完成。\n- 疗效、配方、专利、进口、人物背书及发布授权未验证；截图和宣传单不等于证明文件。\n- HTML仅做静态结构与本地资源检查，未进行浏览器交互验收。\n']
(KB/'整理与验证记录.md').write_text('\n'.join(report), encoding='utf-8')

index=['# 素材库\n', '[打开可搜索预览](素材预览.html) · [CSV清单](素材清单.csv) · [JSON清单](素材清单.json)\n',
 '原件统一保存在上级“图片”目录。本库通过索引分类，避免复制原件造成多份版本。标题为人工看图初分，产品名与小字仍需复核。\n',
 '| ID | 标题 | 类型 | 尺寸 | 重复于 |\n|---|---|---|---|---|']
for r in rows:
    index.append(f"| [{r['id']}](../{r['source']}) | {r['title']} | {r['category']} | {r['width']}×{r['height']} | {r['duplicate_of']} |")
(OUT/'README.md').write_text('\n'.join(index)+'\n',encoding='utf-8')

cards=[]
for r in rows:
    e=html.escape
    duplicate=f" · 重复于{r['duplicate_of']}" if r['duplicate_of'] else ''
    cards.append(f'''<article data-category="{e(r['category'])}"><a href="../{e(r['source'])}" target="_blank" rel="noopener"><img src="缩略图/{r['id']}.jpg" alt="{e(r['title'])}" loading="lazy"></a><h2>{r['id']} {e(r['title'])}</h2><p>{e(r['category'])} · {r['width']}×{r['height']}{duplicate}</p><a href="../{e(r['source'])}">查看原图</a></article>''')
options=''.join(f'<option>{html.escape(c)}</option>' for c in sorted({r['category'] for r in rows}))
page='''<!DOCTYPE html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>外谜体 · 素材库</title>
<style>body{font:16px/1.6 system-ui,sans-serif;background:#f3f5f5;color:#20322e;margin:0;padding:28px}header{max-width:1200px;margin:auto}h1{margin:0}input,select{font:inherit;padding:10px;border:1px solid #abbcb6;border-radius:8px;margin:8px 12px 8px 0}input{width:min(350px,85%)}main{max-width:1200px;margin:20px auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(235px,1fr));gap:18px}article{background:white;padding:16px;border-radius:12px}img{width:100%;height:270px;object-fit:contain;background:#f7f7f7}h2{font-size:16px}p{font-size:14px}a{color:#185d4c}[hidden]{display:none!important}</style>
<header><h1>素材库</h1><p>111张原图 · 2026-11-23整理 · 人工初分，包装小字与宣传说法待核验</p><p><a href="../知识库/产品知识索引.md">产品知识索引</a> · <a href="素材清单.csv">下载CSV清单</a></p><label>搜索 <input id="q" placeholder="品名、编号、关键词"></label><label>类型 <select id="category"><option value="">全部</option>OPTIONS</select></label><p id="count" aria-live="polite"></p></header><main>CARDS</main>
<script>const q=document.getElementById('q'),c=document.getElementById('category'),items=[...document.querySelectorAll('article')];function filter(){let count=0;const term=q.value.trim().toLocaleLowerCase();for(const el of items){el.hidden=!(el.textContent.toLocaleLowerCase().includes(term)&&(!c.value||el.dataset.category===c.value));if(!el.hidden)count++}document.getElementById('count').textContent=`显示 ${count} / ${items.length} 张`}q.addEventListener('input',filter);c.addEventListener('change',filter);filter();</script></html>'''.replace('OPTIONS', options).replace('CARDS','\n'.join(cards))
(OUT/'素材预览.html').write_text(page,encoding='utf-8')

readme='''# 外谜体资料库

整理日期：2026-11-23。原件：文字.txt及图片目录中的111张JPG；原件保持原位。

- [素材可搜索预览](素材库/素材预览.html)：本地浏览器打开，可按编号、品名关键词或类型筛选，点击查看原图。
- [产品知识索引](知识库/产品知识索引.md)：按产品系列和资料主题查找图片。
- [原始诉求与待核验项](知识库/原始诉求与待核验项.md)：保留原文及不明确的产品对应。
- [素材文字索引](素材库/README.md)、[CSV清单](素材库/素材清单.csv)、[JSON清单](素材库/素材清单.json)：含来源、尺寸、字节数、SHA-256及完全重复关系。
- [整理与验证记录](知识库/整理与验证记录.md)：完成情况、重复项、未验证范围。

## 维护方式

新增原件先保留来源和原始文件名，再分配素材编号并更新关联。产品信息应附来源；未经核验的宣传说法继续保留待核验状态。MAX、EX、PLUS及不同配方不得仅凭近似名称合并。图片中的繁体品名及英文型号按来源留存，目前没有经过核对的正式多语言文案。

整理资料.py记录本次生成逻辑（依赖本机已有Pillow）。标题与当前111张图片按文件名排序一一对应；新增或改名后须先更新映射，不能直接套用旧编号。预览和缩略图是派生文件，原件才是来源。
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps({'images':len(rows),'unique':len(seen),'duplicates':[(r['id'],r['duplicate_of']) for r in duplicates],'categories':dict(Counter(r['category'] for r in rows))},ensure_ascii=False))
