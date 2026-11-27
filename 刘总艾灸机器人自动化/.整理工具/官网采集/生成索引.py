from pathlib import Path
import json,csv,re,hashlib,urllib.parse,xml.etree.ElementTree as ET,collections
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'整理成果';CAP=OUT/'官网采集/2026-11-27';ASSET=OUT/'素材库/官网素材/2026-11-27';KB=OUT/'知识库/06_官网资料_20261127'
def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def canonical(url):
    u=urllib.parse.urlsplit(url);return u.scheme+'://'+u.netloc+u.path.rstrip('/')
pages=[]
for p in sorted((CAP/'页面').glob('*.json')):
    d=json.loads(p.read_text(encoding='utf-8'));key=p.stem
    pages.append(dict(id='W-'+key,key=key,url=d['url'],requested_url=d.get('requested_url',d['url']),title=d['title'],lang=d.get('lang'),collected_at='2026-11-27',settled=d.get('settled',True),status='登录限制' if '-account' in key or '-orders' in key else '官网展示，未独立核实',characters=len(d['text']),text_path=p.with_suffix('.txt').relative_to(ROOT).as_posix(),json_path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
save(CAP/'来源清单.json',pages)
md='# 官网页面来源与采集覆盖\n\n采集日期：2026-11-27。按公开链接与站点地图访问，保留渲染后全文、DOM、图片/视频引用及公开表单字段。不保存Cookie、登录令牌或账户信息。页面HTML是证据快照，非完整离线网站。浏览器截图接口两次超时，未冒称已取得页面截图。\n\n[知识库](../../知识库/06_官网资料_20261127/README.md) · [素材库](../../素材库/官网素材/2026-11-27/README.md) · [来源JSON](来源清单.json) · [公开托管档位JSON](托管展示档位.json)\n\n| 来源ID | 页面/状态 | 采集网址 | 原文 |\n| --- | --- | --- | --- |\n'
for p in pages:
    md+=f'| {p["id"]} | {p["title"]}；{p["status"]} | [官网]({p["url"]}) | [TXT](页面/{p["key"]}.txt) · [JSON](页面/{p["key"]}.json) |\n'
(CAP/'README.md').write_text(md,encoding='utf-8')
# 卡片文本只用于待确认快照；不混入已确认政策。
tiers=[]
for p in pages:
    match=re.fullmatch(r'(zh|en)-rental-([A-Z]{2})-cycle-(\d)',p['key'])
    if not match:continue
    lang,region,cycle=match.groups();d=json.loads((ROOT/p['json_path']).read_text(encoding='utf-8'))
    for field in d.get('fields',[]):
        text=field.get('text','') or ''
        if field['tag']!='BUTTON' or not re.search(r'\d+\s*USD',text):continue
        amount=re.search(r'([\d,]+)\s*USD',text);rate=re.search(r'(\d+(?:\.\d+)?)\s*%',text)
        if not rate:continue
        tiers.append(dict(source_id=p['id'],lang=lang,region=region,period_days=[90,180,360][int(cycle)],deposit_usd=int(amount.group(1).replace(',','')) if amount else None,display_daily_rate_percent=rate.group(1) if rate else None,raw_card=text,status='官网展示，存在测试数据，不是有效收益政策'))
save(CAP/'托管展示档位.json',tiers)
assets=json.loads((ASSET/'素材清单.json').read_text(encoding='utf-8'));seen={}
for r in assets:
    r['original_filename']=urllib.parse.unquote(urllib.parse.urlsplit(r['url']).path.split('/')[-1])
    if r.get('sha256'):
        r['duplicate_of']=seen.get(r['sha256']);seen.setdefault(r['sha256'],r['id'])
    if r['status']=='downloaded':
        assert hashlib.sha256((ROOT/r['local_path']).read_bytes()).hexdigest()==r['sha256']
        r['content_language']='中文图文/中文短片为主，页面语言不等于素材语言'
save(ASSET/'素材清单.json',assets)
with (ASSET/'素材清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
    fields=['id','original_filename','status','kind','width','height','duration','bytes','sha256','duplicate_of','url','local_path','error']
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(assets)
md='# 官网素材库\n\n来源：airobot2028.com公开页面，采集于2026-11-27。57条URL：50张图片、6段短片下载成功，1条测试图片URL返回404。按SHA-256为30种图片内容、2种短片内容；保留所有URL对应，不把重复素材当作新增作品。\n\n[素材CSV](素材清单.csv) · [素材JSON](素材清单.json) · [知识库](../../../知识库/06_官网资料_20261127/README.md) · [全部图片OCR检索](OCR/图片OCR_检索版.txt)\n\n## 选材说明\n\n- 热疗图：WA002—WA006与WA035—WA039，画面写射频，但对应商城产品1命名存在冲突。\n- 艾灸图：WA007、WA012—WA015及WA040、WA044—WA047。\n- 舌诊图：WA008、WA017—WA020及WA041、WA049—WA052；报告为展示，不是检测病例。\n- 冲击波图：WA009、WA021—WA024及WA042、WA053—WA056。\n- 配送图：WA010、WA026—WA028；迎宾图：WA029—WA033。\n- WA001为加盟门店效果图，不能当作真实门店照片。WA034为404测试图片，不可使用。\n\n## 图片总览\n\n'+ ' · '.join(f'[第{i}张](预览/图片总览_{i}.jpg)' for i in range(1,7))+'\n\n## 视频内容\n\n6条短片均约15.04秒，720p横版（以清单实际尺寸为准），全时段解码通过，并逐个检查0/3/6/9/12/结尾六帧。是宣传演示/带特效画面，不认定为实机实测视频；未原速连续播放验收。\n\nWA011、WA025、WA043、WA057为同一冲击波宣传短片；WA016、WA048为同一艾灸宣传短片。英文网页也引用相同的中文文件。自动语言检测为中文，原始ASR仍有“挨救”等明显误字，只作为初稿，不自动进入正式知识或可发布字幕。视频可见文案与网页存在明火等冲突，见知识库待确认项。\n\n| 编号 | 视频总览 | 机器音频初稿 |\n| --- | --- | --- |\n'
for r in assets:
    if 'duration' in r:
        md+=f'| {r["id"]} | [六帧预览](预览/{r["id"]}_视频总览.jpg) | [TXT](OCR/{r["id"]}_音频转写.txt) · [JSON](OCR/{r["id"]}_音频转写.json) |\n'
md+='\n## 原件与来源\n\n本目录下载物按URL哈希命名，原文件名保留在清单，SHA-256用于校验和去重。官网公开展示不等于已取得第三方图片、人物、音乐或品牌的商业复用授权。图片OCR未逐字校对，WA026/WA030参数已目视抽检；图中医疗效果、案例和数值未独立核验。\n\n| ID | 原文件名 | 文件/状态 | 尺寸或时长 | 重复关联 | 来源 |\n| --- | --- | --- | --- | --- | --- |\n'
for r in assets:
    local='[下载原件]('+Path(r['local_path']).name+')' if r['status']=='downloaded' else '404/未下载'
    size=f'{r.get("width","")}×{r.get("height","")}'+(f'；{r["duration"]:.2f}秒' if 'duration' in r else '')
    md+=f'| {r["id"]} | {r["original_filename"]} | {local} | {size} | {r.get("duplicate_of") or "独立内容"} | [官网文件]({r["url"]}) |\n'
(ASSET/'README.md').write_text(md,encoding='utf-8')
ocr=json.loads((ASSET/'OCR/图片OCR.json').read_text(encoding='utf-8'))
ocrtext='机器OCR检索版，仅去除汉字间空格，未逐字校对。\n'
for r in ocr:ocrtext+='\n\n【'+r['id']+'】\n'+re.sub(r'(?<=[\u4e00-\u9fff])[^\S\n]+(?=[\u4e00-\u9fff])','',r['text'])
(ASSET/'OCR/图片OCR_检索版.txt').write_text(ocrtext,encoding='utf-8')
names=['CUCA AI智能按摩机器人','AI艾灸机器人','AI中医智能检测舌诊仪','AI中击波理疗机器人','室内外送货机器人','迎宾接待机器人']
prices=[20000,20000,9900,20000,30000,20000];markets=[28800,28800,13800,28800,36800,23800]
entries=[]
for n in range(1,7):
    entries.append(dict(id=f'WEB-P{n:02}',category='产品',title_zh=names[n-1],title_en=json.loads((CAP/f'页面/en-products-{n}.json').read_text(encoding='utf-8'))['title'],currency='SGD',display_price=prices[n-1],reference_market_price=markets[n-1],collected_at='2026-11-27',status='官网展示，非正式报价，型号与宣传待确认',source_ids=[f'W-zh-products-{n}',f'W-en-products-{n}'],source_urls=[f'https://www.airobot2028.com/{lang}/products/{n}' for lang in ['zh','en']],source_texts={lang:(CAP/f'页面/{lang}-products-{n}.txt').read_text(encoding='utf-8') for lang in ['zh','en']},specifications={lang:(CAP/f'页面/{lang}-products-{n}-tab-0.txt').read_text(encoding='utf-8') for lang in ['zh','en']}))
for key in ['about','agents','franchise','rental-hosting']:
    entries.append(dict(id='WEB-'+key,category='公司/商务',collected_at='2026-11-27',status='官网自述；营销UI与测试数据不得当作正式政策',source_ids=[f'W-{lang}-{key}' for lang in ['zh','en']],source_urls=[f'https://www.airobot2028.com/{lang}/{key}/' for lang in ['zh','en']],source_texts={lang:(CAP/f'页面/{lang}-{key}.txt').read_text(encoding='utf-8') for lang in ['zh','en']}))
save(KB/'知识条目.json',entries)
urls=[e.text for e in ET.fromstring((CAP/'sitemap.xml').read_text(encoding='utf-8')).findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
covered={canonical(p['requested_url']) for p in pages};missing=[u for u in urls if canonical(u) not in covered];assert not missing,missing
stats=dict(collected_at='2026-11-27',sitemap_pages=len(urls),sitemap_covered=len(urls)-len(missing),snapshots=len(pages),assets_url_count=len(assets),downloaded=sum(r['status']=='downloaded' for r in assets),failed=sum(r['status']!='downloaded' for r in assets),unique_asset_contents=len(seen),images=sum(r.get('local_path','').endswith(('.jpg','.png')) for r in assets),videos=sum('duration'in r for r in assets),ocr_images=len(ocr),rental_card_observations=len(tiers),original16_hashes='PASS')
originals=json.loads((OUT/'清单/原始文件清单.json').read_text(encoding='utf-8'))
for r in originals:assert hashlib.sha256((ROOT/r['原始路径']).read_bytes()).hexdigest()==r['sha256']
save(OUT/'清单/官网采集验证_20261127.json',stats)
print(json.dumps(stats,ensure_ascii=False,indent=2))
