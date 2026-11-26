# -*- coding: utf-8 -*-
"""使用人工阅读分类结果生成本批索引；不重跑原件导入，不修改原件。"""
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote
import json,csv,io,hashlib,html,posixpath

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'素材库/新增20261125'
WORK=Path(__file__).parent
DATE='2026-11-26'
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def save(p,s):
 p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8')
def dump(p,x):save(p,json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def url(p):return quote(p,safe='/')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

originals=load('素材库/新增20261125/原件清单.json')
slides=load('素材库/新增20261125/PPT逐页文字.json')
embedded=load('素材库/新增20261125/PPT嵌入素材清单.json')
ppt=originals[-1]['path']
titles=[
'Yvelise MELANIN VITALITY SERUM 白底产品图，50ml',
'Yvelise MELANIN VITALITY SHAMPOO 白底产品图，300ml',
'Yvelise头皮活力精华液：植物、保湿与维生素成分图，50mL',
'Yvelise草本强韧洗发水：清洁、修护与调理成分图，300mL',
'Hair Vitality Shampoo植物与配方视觉',
'Hair Vitality Serum植物、配方与导液梳视觉',
'精华主图1：英文Serum/50mL，中文错写草本养护洗发露',
'精华主图2：何首乌、人参、莲叶、黑芝麻',
'精华主图3：22种草本精华宣传',
'精华详情01：多重植萃头皮养护精华主视觉',
'精华详情02：头皮痛点',
'精华详情03：草本成分示意',
'精华详情04：双护理与使用方法',
'精华详情05：前后案例',
'精华详情06：50mL与成分信息',
'精华详情合成长图（01至06）',
'洗发水主图1：草本养护洗发露300mL',
'洗发水主图2：何首乌、人参、当归、侧柏叶',
'洗发水主图3：净养专强与22种草本宣传',
'洗发水详情01：主视觉',
'洗发水详情02：头皮痛点',
'洗发水详情03：草本成分示意',
'洗发水详情04：特色与使用方法',
'洗发水详情05：前后案例',
'洗发水详情06：300mL与成分信息',
'洗发水详情合成长图（01至06）',
'洗护组合主图1：300mL洗发水与50mL精华',
'洗护组合主图2：植物与双瓶',
'洗护组合主图3：22种草本与双护理',
'洗护组合详情01：双瓶主视觉',
'洗护组合详情02：头皮痛点',
'洗护组合详情03：洗发水成分',
'洗护组合详情04：洗发水特色与用法',
'洗护组合详情05：精华成分',
'洗护组合详情06：精华特色与用法',
'洗护组合详情07：前后案例',
'洗护组合详情08：双产品规格与成分',
'洗护组合详情合成长图（01至08）',
'粉之密PPT29：54页可编辑演示文件'
]
page_titles=[
'粉之密·粉嫩术封面','李暖心/MUZI与品牌经历','A’PRETTI公司与粉之密品牌介绍','产品全家福','品牌标识与文化','车间与检测图像','HSA通知函：美白霜4号与平衡霜2号','HSA通知函：焕颜精华套盒与平衡霜3号','HSA通知函：唇部平衡霜1号；商标申请资料','林峰/Mr.Lin介绍','门店选项目八项标准','色素困扰与成因示意','私密困扰与营销切入','项目营销主张','项目对比表（8800元）','粉嫩焕颜精华套盒','平衡霜1号','平衡霜2号5ml','平衡霜3号5ml','美白霜4号5ml','蜜桃喷雾30ML','光波仪与光色技术描述','技术与作用宣传','适用部位宣传','时长与效果宣传','分解、阻断、修复宣传','乳晕案例拼图','唇色分类','唇部案例1','唇部案例2','唇部案例3','唇部案例4','唇部案例5','唇部案例6','咨询表模板与服务价格表','粉唇沟通、拍照与准备','粉唇操作流程原文','粉唇操作后护理与禁忌','粉唇禁忌人群与间隔原文','身体局部美白流程原文','乳晕准备与流程原文','私密准备与流程原文','粉嫩操作后注意事项原文','平衡霜用法原文','另一版操作后护理原文','加盟原价$1500','加盟产品配置','加盟活动$1268','加盟活动与打版服务','加盟活动与门票','结束页','加盟福利$1168及服务价目表','加盟/分公司/联合创始人政策表','乳晕及私密案例拼图'
]
assert len(titles)==39 and len(page_titles)==54
items=[]
for i,(r,title) in enumerate(zip(originals,titles),1):
 group='瓶身产品图' if i<=2 else '成分视觉' if i<=6 else '头皮精华' if i<=16 else '草本洗发水' if i<=26 else '洗护组合' if i<=38 else '粉之密演示源文件'
 cases=i in (14,24,36)
 items.append({**r,'content':title,'scene':'内部产品资料与培训；案例使用范围待确认' if i==39 else '案例复核；使用前核对肖像及案例授权' if cases else '产品介绍、电商组稿及成分主题检索；按差异清单选图','category':group,'source':'用户提供新增目录20261125；来源相对路径见source_relative','source_url':'','rights':'待确认；未提供独立版权/肖像/商业复用授权','stage':'原始来件/可编辑演示源文件' if i==39 else '原始来件/合成长图' if i in (16,26,38) else '原始来件/详情分片' if i in list(range(10,16))+list(range(20,26))+list(range(30,38)) else '原始来件/产品宣传图','version':'用户来件批次20261125；制作与生效日期待确认','status':'用户提供；已阅读分类，具体差异保留','ai_status':'待确认；无生成记录','derived_from':'','inherit_prior_confirmation':False,'reviewed_at':DATE,'internal':i==39 or cases})

page_rows=[]
for s,title in zip(slides,page_titles):
 n=s['page'];internal=27<=n<=45 or n>=52
 p=f'素材库/新增20261125/PPT页面/P{n:02}.png'
 category='内部培训' if 36<=n<=45 else '案例/咨询表' if 27<=n<=35 or n==54 else '招商与价格历史版本' if 46<=n<=50 or n in (52,53) else '历史资质' if 6<=n<=9 else '品牌与产品'
 r={'id':f'N1125-P{n:02}','path':p,'page':n,'content':title,'category':category,'scene':'内部检索/审阅；不作为新增原始产品证明','source':'本机PowerPoint按原PPT只读渲染','rights':'继承原PPT；具体授权待确认','stage':'中间产物/演示页渲染','version':'20261125来件；2026-11-26渲染','status':'已按页视觉分类；小字未完整OCR审校','ai_status':'本机渲染；原图AI来源待确认','derived_from':ppt,'sha256':digest(ROOT/p),'internal':internal,'inherit_prior_confirmation':False,'text':s['text']}
 page_rows.append(r);items.append(r)

by_member={r['ppt_member']:r for r in embedded}
pages_for=defaultdict(list)
for s in slides:
 for rel in s['relationships']:
  if rel['Type'].endswith('/image'):
   member=posixpath.normpath(posixpath.join('ppt/slides',rel['Target']))
   if member in by_member:pages_for[member].append(s['page'])
for i,r in enumerate(embedded,1):
 pages=sorted(set(pages_for[r['ppt_member']]))
 items.append({**r,'id':f'N1125-E{i:02}','content':'PPT嵌入资源 '+Path(r['path']).name+'；页面 '+(','.join(map(str,pages)) or '无直接页引用，可能经版式/母版关联'),'category':'PPT嵌入资源','scene':'编辑参考；先查看所关联整页，不根据资源文件名猜测用途','source':'原PPT ZIP内媒体成员；按关系XML关联页码','rights':'继承原PPT；肖像、图片授权待确认','stage':'中间产物/PPT拆解资源','version':'20261125来件；原字节提取2026-11-26','status':'已提取并核对；不标为独立新来件','ai_status':'原素材AI来源待确认；提取不生成新画面','derived_from':ppt,'pages':pages,'internal':True,'inherit_prior_confirmation':False})
dump('素材库/新增20261125/素材目录.json',items)
dump('素材库/新增20261125/PPT页面索引.json',page_rows)
buf=io.StringIO(newline='');fields=['id','path','content','category','scene','stage','version','source','source_relative','rights','status','ai_status','derived_from','pages','sha256','bytes','width','height']
w=csv.DictWriter(buf,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(items)
save('素材库/新增20261125/素材目录.csv','\ufeff'+buf.getvalue())

families=[]
for full,parts in [(16,range(10,16)),(26,range(20,26)),(38,range(30,38))]:
 families.append({'composite':originals[full-1]['path'],'parts':[originals[n-1]['path'] for n in parts],'basis':'逐图视觉检查对应详情段落；合成长图与分片用途不同；未做像素拼接一致性断言','action':'全部保留；整页展示用长图，局部编辑参考分片'})
dump('素材库/新增20261125/组合与分片关系.json',families)
groups=defaultdict(list)
for r in items:groups[r['sha256']].append(r['path'])
baseline=load('整理过程/新增20261125/导入前基线.json');old=defaultdict(list)
for r in baseline:old[r['sha256']].append(r['path'])
duplicates={'method':'SHA-256；相似内容、长图与分片不按完全重复处理','new_original_vs_old_matches':[r for r in originals if r['identical_existing_paths']],'within_batch':[{'sha256':h,'paths':v,'recommended_entry':v[0],'action':'保留全部；按整页上下文选用'} for h,v in groups.items() if len(v)>1],'derived_vs_old':[{'path':r['path'],'identical_old_paths':old[r['sha256']],'action':'保留来源关系；原文件保持原位'} for r in items[39:] if old[r['sha256']]]}
dump('素材库/新增20261125/重复核对.json',duplicates)
lines=['# 20261125新增素材索引','','整理日期：2026-11-26。39份原始来件（38图片、1份54页PPT）；另54张渲染页及61个PPT嵌入资源，均单列为衍生文件。','','[可搜索预览](新增素材预览.html) · [CSV](素材目录.csv) · [完整JSON](素材目录.json) · [知识摘要](../../知识库/20261125新增资料.md) · [逐页文字（不是完整OCR）](粉之密PPT逐页原文.txt)','','原件不移动或改名；原图未提供的作者、制作日期、AI来源和商业授权均待确认。编号N1125与旧A/W编号并存。','','## 原始来件','','| 编号 | 内容 | 阶段 | 原件 |','| --- | --- | --- | --- |']
for r in items[:39]:lines.append(f"| {r['id']} | {r['content']} | {r['stage']} | [打开](../../{url(r['path'])}) |")
lines+=['','## 派生资源与版本','','- [54页PPT页码索引](../../知识库/粉之密产品与培训索引.md)；页面保留版式，XML文字不含全部图片文字。','- [61个嵌入资源及页码关系](素材目录.json)：只表示资源在PPT中的直接引用，未做独立授权判断。','- [组合与分片关系](组合与分片关系.json)：3张合成长图及各自分片均保留。','- [重复核对](重复核对.json)：39个原件与此前库无哈希相同项；相近产品画面不是删除依据。','','## 后续维护','','原件只增不覆盖；修订图另存“主题_用途_v02_日期”，登记derived_from。PPT修订另存版本并保留页码映射；资质、价格、护理流程的改版不得仅靠文件名较新自动取代旧版。新增批次不要重跑导入脚本；修改本批人工分类后可运行建立批次索引.py，再运行全库维护索引.py。']
save('素材库/新增20261125/素材索引.md','\n'.join(lines)+'\n')

esc=html.escape
def card(r):
 p='../../'+url(r['path']);is_ppt=r['path'].endswith('.pptx')
 visual='' if is_ppt else f'<a href="{p}"><img loading="lazy" src="{p}" alt="{esc(r["content"])}"></a>'
 text=f'<pre>{esc(r.get("text", ""))}</pre>' if r.get('text') else ''
 search=esc(' '.join(str(r.get(k,'')) for k in ('id','content','category','text')))
 return f'<article class="card" data-search="{search}" data-category="{esc(r["category"])}">{visual}<h3>{esc(r["id"])} · {esc(r["content"])}</h3><p>{esc(r["stage"])}</p><a href="{p}">打开原件/页面</a>{text}</article>'
normal=[r for r in items[:93] if not r['internal']];private=[r for r in items[:93] if r['internal']]
cats=sorted(set(r['category'] for r in items[:93]))
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>20261125新增资料预览</title><style>body{font:16px/1.6 system-ui,sans-serif;margin:24px;background:#f7f6f3;color:#282828}header{max-width:1100px}input,select{padding:10px;margin:8px 8px 8px 0;max-width:90%}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}.card{background:white;padding:14px;border:1px solid #ddd;border-radius:10px;overflow-wrap:anywhere}.card img{width:100%;height:230px;object-fit:contain}.card h3{font-size:16px}pre{white-space:pre-wrap;max-height:180px;overflow:auto;font:14px/1.5 system-ui}details{margin:24px 0}summary{cursor:pointer;padding:12px;background:#eee}a{color:#315880}[hidden]{display:none!important}</style><header><h1>20261125新增资料</h1><p>39份来件：38图片＋1份54页PPT。下方图片与PPT整页分开编号；61个嵌入资源另见清单。案例、咨询表与培训内容默认折叠，仅供内部检索。折叠不是访问权限控制。</p><p><a href="素材索引.md">素材索引</a> · <a href="../../知识库/20261125新增资料.md">知识摘要</a> · <a href="素材目录.csv">完整CSV</a> · <a href="粉之密PPT逐页原文.txt">文字提取</a></p><input id="q" aria-label="检索关键词" placeholder="搜编号、产品、页码或正文"><select id="category" aria-label="分类"><option value="">全部分类</option>'''
page+=''.join(f'<option>{esc(c)}</option>' for c in cats)
page+='</select><p id="count" role="status"></p></header><main><section class="grid">'+''.join(map(card,normal))+'</section><details><summary>展开案例、咨询表、演示源文件与内部培训页</summary><section class="grid">'+''.join(map(card,private))+'</section></details></main>'
page+='''<script>const cards=Array.from(document.querySelectorAll('.card'));const q=document.getElementById('q'),category=document.getElementById('category');function filter(){const term=q.value.trim().toLocaleLowerCase();let n=0;for(const c of cards){const ok=(!category.value||c.dataset.category===category.value)&&c.dataset.search.toLocaleLowerCase().includes(term);c.hidden=!ok;if(ok)n++;}document.getElementById('count').textContent=`匹配 ${n} / ${cards.length} 项（含折叠区；需要时手动展开）`;}q.addEventListener('input',filter);category.addEventListener('change',filter);filter();</script></html>'''
save('素材库/新增20261125/新增素材预览.html',page)

page_index=['# 粉之密产品与培训页码索引','','来源：[粉之密PPT29.pptx](../'+url(ppt)+')。文件名含29，实际54页。2026-11-26只读渲染并按页视觉分类；文字层已提取，图片内文字未完整OCR。','','[文字提取TXT](../素材库/新增20261125/粉之密PPT逐页原文.txt) · [预览](../素材库/新增20261125/新增素材预览.html) · [差异和价格](20261125新增资料.md)','','P36–45保留为内部培训原文，不合并成统一护理SOP。P27/P54涉及私密部位案例，其肖像和使用范围未附独立授权。','','| 页码 | 内容 | 分类 | 页面 |','| --- | --- | --- | --- |']
for r in page_rows:page_index.append(f"| P{r['page']:02} | {r['content']} | {r['category']} | [查看](../{url(r['path'])}) |")
save('知识库/粉之密产品与培训索引.md','\n'.join(page_index)+'\n')
print(json.dumps({'originals':len(originals),'slides':len(page_rows),'embedded':len(embedded),'catalog':len(items),'within_batch_duplicate_groups':len(duplicates['within_batch']),'derived_old_matches':len(duplicates['derived_vs_old'])},ensure_ascii=False))
