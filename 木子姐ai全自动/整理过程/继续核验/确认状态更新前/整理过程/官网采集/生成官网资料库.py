# -*- coding: utf-8 -*-
from pathlib import Path
from urllib.parse import urlsplit,quote,unquote
from decimal import Decimal
from collections import Counter,defaultdict
import json,csv,re,hashlib,html as escape_html,copy
from lxml import html
from PIL import Image,ImageOps
from 采集官网 import lang_text,cls,compact,save,ROOT,OUT,STAMP

E=escape_html.escape
def text(content):
    if not content:return ''
    return compact(html.fromstring('<div>'+content+'</div>'))

def md(s):return str(s).replace('|','\\|').replace('\n',' / ')
def href(p):return quote(str(p).replace('\\','/'),safe='/')
def localrel(p,base):
    import os
    return href(os.path.relpath(p,base))

def write_csv(path,rows,fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    pages=json.loads((OUT/'页面清单.json').read_text(encoding='utf-8'))
    resources=json.loads((OUT/'资源清单.json').read_text(encoding='utf-8'))
    media=json.loads((OUT/'公开媒体清单.json').read_text(encoding='utf-8'))['items']
    content=json.loads((OUT/'公开内容清单.json').read_text(encoding='utf-8'))
    source_urls={r['url']:r for r in resources}
    knowledge=ROOT/'知识库/官网';knowledge.mkdir(exist_ok=True)
    pdir=knowledge/'产品';pdir.mkdir(exist_ok=True)
    store={r['permalink']:r for r in content['store-products']['items']}
    api_products={r['link']:r for r in content['product']['items']}
    products=[]
    pairs=[]
    docs=[]
    for i,r in enumerate(pages,1):
        r['id']=f'W-PAGE{i:03}'
        d=html.fromstring((OUT/r['raw_path']).read_bytes())
        body=(d.xpath('//body') or [d])[0]
        r['full_text_en']=lang_text(body,'en')
        r['full_text_zh_view']=lang_text(body,'zh')
        # 完整正文保留共享英文块和站点页脚，避免中文切换视图被误认为完整翻译。
        (OUT/r['text_path']).write_text(f'# {r["title"]}\n\n来源：{r["url"]}\n\n采集：{r["captured_at"]}\n\n## 英文视图全文\n\n{r["full_text_en"]}\n\n## 中文切换视图全文（共用块可能仍是英文）\n\n{r["full_text_zh_view"]}\n',encoding='utf-8')
        docs.append({'id':r['id'],'kind':'website_page','url':r['url'],'captured_at':r['captured_at'],'title':r['title'],'text_en':r['full_text_en'],'text_zh_view':r['full_text_zh_view'],'source_status':'官网公开页面；宣传事实未经独立核验'})
        for pair in r.get('bilingual_pairs',[]):pairs.append({'source':r['url'],**pair})
        if not r.get('product'):continue
        p=r['product'];s=store.get(r['url'],{});ap=api_products.get(r['url'],{})
        slug=urlsplit(r['url']).path.rstrip('/').rsplit('/',1)[-1]
        candidate=bool(re.match(r'^(body-cream-|course-|face-natural-skin-|hand-cream-soft-|schampoo-with-)',slug))
        no_price=not bool(p['price_text'])
        prices=s.get('prices',{})
        current=None
        if not no_price and prices.get('price') not in ('',None):
            current=str(Decimal(prices['price'])/(Decimal(10)**prices.get('currency_minor_unit',2)))
        def section(c):
            nodes=d.xpath('//*['+cls(c)+']')
            return {'en':lang_text(nodes[0],'en'),'zh':lang_text(nodes[0],'zh')} if nodes else {'en':'','zh':''}
        detail_nodes=d.xpath('//details')
        inci='\n'.join(compact(n) for n in detail_nodes if 'ingredients' in compact(n).lower() or '成分' in compact(n))
        summary_nodes=d.xpath('//*['+cls('summary')+']')
        chinese_names=[]
        # 官网未设置正式中文H1；不把营销段落中的译名自动当作已确认SKU名。
        item={'id':f'W-PROD{len(products)+1:03}','wp_id':s.get('id',ap.get('id')),'url':r['url'],'name':p['name'],'slug':slug,'chinese_official_name':None,'categories':[x['name'] for x in s.get('categories',[])],'price_display':p['price_text'] or '询价 / Enquire about this product','currency':'SGD','current_api_amount_if_frontend_priced':current,'api_prices_raw':prices,'price_status':'询价；API 0不表示免费' if no_price else '官网及公开Store API采集快照','api_stock_snapshot':{'is_in_stock':s.get('is_in_stock'),'is_purchasable':s.get('is_purchasable')},'sku':s.get('sku',''),'type':s.get('type',''),'attributes':s.get('attributes',[]),'variations':s.get('variations',[]),'images':s.get('images',[]),'description_api':text(s.get('description','')),'short_description':p['short_description'],'benefits':section('pd-benefits'),'formula':section('pd-formula-section'),'ritual':section('pd-ritual'),'inci_source_text':inci,'bilingual_pairs':r.get('bilingual_pairs',[]),'classification':'疑似主题模板商品，待业务确认' if candidate else 'LA REINE品牌命名商品，未确认实际可售范围','is_template_candidate':candidate,'captured_at':r['captured_at'],'page_source':r['text_path'],'knowledge_path':f'产品/{slug}.md','verified_claims':False}
        if no_price and 'Enquire about this product' not in p['text_en']:
            item['price_display']='未提供价格（疑似模板）' if candidate else '未提供价格'
            item['price_status']='未提供价格；API 0不表示免费'
        item['frontend_category_text']=p['categories']
        item['api_categories']=item['categories']
        front_cats=re.sub(r'^Categor(?:y|ies):\s*','',p['categories']).strip()
        if front_cats:item['categories']=[v.strip() for v in front_cats.split(',') if v.strip()]
        item['frontend_price_raw']=p['price_text']
        price_nodes=d.xpath('//*['+cls('summary')+']//*['+cls('price')+']')
        if price_nodes:
            clean=copy.deepcopy(price_nodes[0])
            for node in clean.xpath('.//*['+cls('screen-reader-text')+']'):node.drop_tree()
            old=clean.xpath('.//del');new=clean.xpath('.//ins')
            item['price_display']=f'原价{compact(old[0])}；现价{compact(new[0])}' if old and new else (compact(clean) or item['price_display'])
        products.append(item)
        lines=[f'# {item["name"]}','','- 编号：'+item['id'],f'- 来源：[{item["url"]}]({item["url"]})',f'- 采集：{item["captured_at"]}',f'- 分类：{", ".join(item["categories"])}',f'- 资料状态：{item["classification"]}',f'- 页面价格：{item["price_display"]}；页面币种SGD。',f'- 正式中文SKU名：页面H1未提供，留空。','- 真实性边界：以下成分、特色及效果均为官网表述，未独立验证。','','## 官网产品介绍（原文）','',item['short_description'] or item['description_api'] or '该页未提供独立的完整产品说明。']
        for key,title in [('benefits','产品特色'),('formula','配方信息'),('ritual','护理定位/用法提示')]:
            lines+=['',f'## {title} · English','',item[key]['en'] or '未提供','',f'## {title} · 中文切换视图','',item[key]['zh'] or '未提供']
        lines+=['','## 完整成分字段（如有）','',inci or '未找到独立的完整成分表；不能依据主打成分推定完整配方。','','## 商品图片','']
        for image in item['images']:
            resource=source_urls.get(image['src'])
            if resource and resource.get('path'):
                path=localrel(OUT/resource['path'],pdir)
                lines.append(f'- [本地图片]({path}) · [官网原图]({image["src"]})')
            else:lines.append(f'- [官网原图]({image["src"]})（本地下载状态见资源清单）')
        lines+=['','## 价格与库存快照','',f'前台显示：{item["price_display"]}。接口价格字段原样保存于产品目录JSON；货币最小单位按currency_minor_unit解释。询价商品即使接口为0也不记录为免费。库存字段只是接口快照，未验证可成交或可配送。','',f'[页面全文]({localrel(OUT/r["text_path"],pdir)})']
        (pdir/(slug+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    save(OUT/'页面清单.json',pages)
    save(knowledge/'产品目录.json',products)
    fields=['id','wp_id','name','url','categories','price_display','currency','current_api_amount_if_frontend_priced','price_status','classification','captured_at']
    write_csv(knowledge/'产品价格快照.csv',[{**p,'categories':' / '.join(p['categories'])} for p in products],fields)
    write_csv(knowledge/'中英文对照.csv',pairs,['source','en','zh'])
    with (knowledge/'官网知识条目.jsonl').open('w',encoding='utf-8') as f:
        for r in docs:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    # 公开API内容不等同于当前页面呈现；单独保留发布状态及内容，不混入已验证产品事实。
    api_dir=OUT/'公开内容正文';api_dir.mkdir(exist_ok=True)
    for key in ['pages','posts','product']:
        for row in content[key]['items']:
            name=f'{key}-{row["id"]}-{row["slug"]}.md'
            raw_content=row.get('content',{}).get('rendered','')
            body=text(raw_content)
            (api_dir/name).write_text(f'# {text(row["title"]["rendered"])}\n\n来源：{row["link"]}\n\n公开API类型：{key}；状态：{row.get("status")}。本记录不代表当前主题一定显示此内容。\n\n{body or "公开API正文为空；以已采集页面视图为准。"}\n',encoding='utf-8')

    # 图片/视频/字体原始资源索引，以媒体ID为标识；显示站点上的实际引用情况。
    media_rows=[]
    for m in media:
        asset=source_urls.get(m['source_url'],{})
        media_rows.append({'id':f'W-M{m["id"]}','wp_media_id':m['id'],'title':text(m['title']['rendered']),'url':m['source_url'],'mime_type':m['mime_type'],'kind':'视频' if m['mime_type'].startswith('video/') else '字体' if m['mime_type'].startswith('font/') else '图片','width':m.get('media_details',{}).get('width'),'height':m.get('media_details',{}).get('height'),'status':asset.get('status'),'path':asset.get('path',''),'sha256':asset.get('sha256',''),'bytes':asset.get('bytes',0),'alt':m.get('alt_text',''),'caption':text(m.get('caption',{}).get('rendered','')),'referenced_by_pages':[u for u in asset.get('sources',[]) if '/wp-json/' not in u],'usage_status':'有页面直接引用' if any('/wp-json/' not in u for u in asset.get('sources',[])) else '仅公开媒体库发现；不认定当前前台使用','variants':len(m.get('media_details',{}).get('sizes',{})),'captured_at':asset.get('captured_at'),'source_api':f'https://lareine.com.sg/wp-json/wp/v2/media/{m["id"]}'})
    save(OUT/'媒体原件索引.json',media_rows)
    write_csv(OUT/'媒体原件索引.csv',media_rows,['id','wp_media_id','title','kind','mime_type','width','height','status','path','sha256','bytes','usage_status','url','source_api'])
    write_csv(OUT/'资源清单.csv',[{**r,'roles':' / '.join(r['roles']),'sources':' | '.join(r['sources'])} for r in resources],['url','status','path','content_type','bytes','sha256','roles','sources','error'])
    lines=['# 官网产品索引','','本索引按官网现有页面和公开接口整理。所有条目保留来源，疑似模板不删除也不自动视作实际经营商品。','',f'共{len(products)}个商品地址，其中{sum(p["is_template_candidate"] for p in products)}个因命名含主题示例特征标记待确认。前台有价格{sum(bool(p["frontend_price_raw"]) for p in products)}个，询价{sum(p["price_status"].startswith("询价") for p in products)}个。价格是2026-11-24快照，非承诺有效报价。','','| 编号 | 名称 | 分类 | 前台价格（SGD） | 状态 |','| --- | --- | --- | --- | --- |']
    for p in products:lines.append(f'| {p["id"]} | [{md(p["name"])}]({href(p["knowledge_path"])}) | {md(" / ".join(p["categories"]))} | {md(p["price_display"])} | {p["classification"]} |')
    (knowledge/'产品索引.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    # 去重报告保留全部路径；不删除原始或派生文件。
    hashes=defaultdict(list)
    for r in resources:
        if r.get('status')==200:hashes[r['sha256']].append(r['url'])
    duplicates=[{'sha256':k,'urls':v} for k,v in hashes.items() if len(v)>1]
    save(OUT/'重复资源.json',duplicates)
    image_failures=[]
    thumbnails=OUT/'缩略图';thumbnails.mkdir(exist_ok=True)
    for r in media_rows:
        if r['kind']!='图片' or not r['path'] or r['mime_type'].endswith('svg+xml'):continue
        try:
            with Image.open(OUT/r['path']) as im:
                im=ImageOps.exif_transpose(im).convert('RGB');im.thumbnail((420,420))
                im.save(thumbnails/(r['id']+'.jpg'),quality=84)
                r['thumbnail']='缩略图/'+r['id']+'.jpg'
        except Exception as e:image_failures.append({'id':r['id'],'error':str(e)})
    save(OUT/'媒体原件索引.json',media_rows)
    save(OUT/'图片解码异常.json',image_failures)
    build_gallery(products,pages,media_rows,resources,knowledge)
    validate(pages,products,media_rows,resources,duplicates,image_failures)
    print(json.dumps({'products':len(products),'pages':len(pages),'media':len(media_rows),'resources':len(resources),'resource_failures':sum(r.get('status')!=200 for r in resources)},ensure_ascii=False))

def build_gallery(products,pages,media,resources,knowledge):
    cards=[]
    mapping={r['url']:r for r in resources}
    def card(kind,title,sub,body,links,preview='',flag=''):
        search=' '.join([kind,title,sub,body])
        cards.append(f'<article data-kind="{E(kind,quote=True)}" data-search="{E(search.lower(),quote=True)}" data-flag="{E(flag,quote=True)}">{preview}<div class="body"><small>{E(sub)}</small><h2>{E(title)}</h2><p>{E(body)}</p><footer>{links}</footer></div></article>')
    for p in products:
        preview=''
        if p['images']:
            a=mapping.get(p['images'][0]['src'],{})
            if a.get('path'):preview=f'<img loading="lazy" src="{href(a["path"])}" alt="{E(p["name"],quote=True)}">'
        link=localrel(knowledge/p['knowledge_path'],OUT)
        card('商品',p['name'],p['id']+' · '+' / '.join(p['categories']),p['price_display']+' · SGD · '+p['classification'],f'<a href="{link}">本地产品资料</a> · <a target="_blank" rel="noopener" href="{p["url"]}">官网来源</a>',preview,'待确认模板' if p['is_template_candidate'] else '品牌命名')
    for m in media:
        preview=''
        if m['path']:
            src=href(m.get('thumbnail') or m['path'])
            if m['kind']=='图片':preview=f'<a href="{href(m["path"])}" target="_blank"><img loading="lazy" src="{src}" alt="{E(m["title"],quote=True)}"></a>'
            elif m['kind']=='视频':preview=f'<video controls preload="none" src="{href(m["path"])}" aria-label="{E(m["title"],quote=True)}"></video>'
        link=f'<a href="{href(m["path"])}" target="_blank">打开本地原件</a> · ' if m['path'] else ''
        card('原始素材',m['title'],m['id']+' · '+m['kind']+' · '+m['mime_type'],m['usage_status']+' · 状态 '+str(m['status']),link+f'<a target="_blank" rel="noopener" href="{m["url"]}">官网原件</a>',preview,m['kind'])
    for p in pages:
        card('页面',p['title'],p['id'],p['url']+' · '+str(len(p.get('bilingual_pairs',[])))+'组双语节点',f'<a href="{href(p["text_path"])}">本地全文</a> · <a target="_blank" rel="noopener" href="{p["url"]}">官网来源</a>')
    # 完整尺寸变体与技术文件均可检索，不让缩略版本挤占默认原件视图。
    originals={m['url'] for m in media}
    for a in resources:
        if a['url'] in originals:continue
        link=f'<a href="{href(a["path"])}" target="_blank">本地文件</a> · ' if a.get('path') else ''
        card('尺寸与技术文件',unquote(urlsplit(a['url']).path.rsplit('/',1)[-1]),a.get('content_type',''),str(a.get('status'))+' · '+' / '.join(a['roles']),link+f'<a href="{E(a["url"],quote=True)}" target="_blank" rel="noopener">来源</a>')
    template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LA REINE 官网资料与素材归档</title><style>
*{box-sizing:border-box}body{margin:0;background:#f7f4ed;color:#24231f;font:15px/1.65 system-ui,"Microsoft YaHei",sans-serif}header,main{max-width:1480px;margin:auto;padding:28px}header{padding-top:42px}h1{font-size:32px;margin:5px 0}a{color:#71531c}nav{display:flex;gap:20px;flex-wrap:wrap}p{max-width:1100px;color:#666}.tools{position:sticky;top:0;background:#f7f4edf5;z-index:3;display:flex;gap:12px;padding:16px 0;flex-wrap:wrap}input,select{padding:11px;border:1px solid #c8bd9f;border-radius:7px;background:white;font:inherit}input{flex:1;min-width:210px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:18px}article{background:white;border:1px solid #e3dccb;border-radius:10px;overflow:hidden}article[hidden]{display:none}img,video{width:100%;height:250px;object-fit:contain;background:#eeeae0;display:block}.body{padding:18px;overflow-wrap:anywhere}h2{font-size:17px;margin:7px 0}.body p{font-size:13px;white-space:pre-wrap}small{color:#8b6b31}footer{border-top:1px solid #eee;padding-top:12px}#count{padding-bottom:14px}input:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #997333;outline-offset:3px}
</style><header><small>LA REINE · 本地归档 · 2026-11-24</small><h1>官网资料与素材库</h1><p>STATS。原始页面、公开接口与资源逐项保留来源网址。官网公开媒体库包含历史素材、模板和字体，并非全部代表当前在售商品；疑似模板已单独标记。官网宣传不等于已核验功效。本预览只读取本地文件，点击官网链接才会访问外网。</p><nav><a href="../../知识库/官网/产品索引.md">产品知识库</a><a href="../../知识库/官网/品牌与联系资料.md">品牌资料</a><a href="../../知识库/官网/与聊天资料的差异.md">来源差异</a><a href="媒体原件索引.csv" download>原件CSV</a><a href="资源清单.csv" download>全部资源CSV</a><a href="采集报告.md">覆盖与校验报告</a><a href="../../素材库/素材预览.html">原微信素材</a></nav></header><main><div class="tools"><input id="q" aria-label="搜索官网资料" placeholder="搜索产品、文件名、编号、关键词…"><select id="kind" aria-label="选择资料类型"><option>商品</option><option>原始素材</option><option>页面</option><option>尺寸与技术文件</option><option value="">全部</option></select><select id="flag" aria-label="选择标记"><option value="">全部标记</option><option>品牌命名</option><option>待确认模板</option><option>图片</option><option>视频</option><option>字体</option></select></div><div id="count" role="status" aria-live="polite"></div><div class="grid">CARDS</div><p id="empty" hidden>没有匹配项，请调整筛选条件。</p></main><script>
const cards=Array.from(document.querySelectorAll('article'));const q=document.getElementById('q'),kind=document.getElementById('kind'),flag=document.getElementById('flag');function filter(){const term=q.value.trim().toLowerCase();let n=0;for(const c of cards){const show=(!kind.value||c.dataset.kind===kind.value)&&(!flag.value||c.dataset.flag===flag.value)&&c.dataset.search.includes(term);c.hidden=!show;if(show)n++;}document.getElementById('count').textContent=`显示 ${n} 项 / 全部 ${cards.length} 项`;document.getElementById('empty').hidden=n>0;}q.addEventListener('input',filter);kind.addEventListener('change',filter);flag.addEventListener('change',filter);filter();
</script></html>'''
    counts=f'{len(pages)}个公开页面 · {len(products)}个商品地址 · {len(media)}项公开媒体原件 · {len(resources)}个资源URL'
    (OUT/'官网资料预览.html').write_text(template.replace('STATS',counts).replace('CARDS','\n'.join(cards)),encoding='utf-8')

def validate(pages,products,media,resources,duplicates,image_failures):
    errors=[];downloaded=[r for r in resources if r.get('status')==200 and r.get('path')]
    for r in downloaded:
        p=OUT/r['path']
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:errors.append(r['url'])
    failures=[{'url':r['url'],'status':r.get('status'),'error':r.get('error')} for r in resources if r.get('status')!=200]
    save(OUT/'下载失败.json',failures)
    report={'captured_date':'2026-11-24','timezone':'Asia/Shanghai','scope':'站点地图与页面链接的公开内容、公开WordPress媒体/内容/Store API、CSS引用资源；不含需授权登录的后台或未公开文件','page_count':len(pages),'page_http_statuses':dict(Counter(str(r['status']) for r in pages)),'page_queue_remaining':json.loads((OUT/'页面未处理.json').read_text(encoding='utf-8')),'product_count':len(products),'template_candidates':sum(r['is_template_candidate'] for r in products),'products_with_frontend_price':sum(bool(r['frontend_price_raw']) for r in products),'products_enquiry_only':sum(r['price_status'].startswith('询价') for r in products),'public_media_originals':len(media),'media_types':dict(Counter(r['kind'] for r in media)),'originals_downloaded':sum(bool(r['path']) and r['status']==200 for r in media),'resource_urls':len(resources),'downloaded_resources':len(downloaded),'downloaded_bytes':sum(r['bytes'] for r in downloaded),'resource_failures':failures,'sha256_errors':errors,'exact_duplicate_groups':len(duplicates),'image_decode_errors':image_failures,'website_browser_check':'已实测首页与Aqua Light Toner中英切换；中文模式仍有共享英文块','website_screenshots':'官网截图接口两次超时，未生成截图；DOM/HTML及正文已保存','no_private_data_access':'未登录、未获取订单/客户数据、未提交表单或操作购物车','binary_scope_note':'公开媒体接口列出0份PDF，当前页面未发现PDF下载链接；原微信批次的2份PDF仍在原始资料','complete_publicly_discovered_scope':not failures and not errors and not image_failures and not json.loads((OUT/'页面未处理.json').read_text(encoding='utf-8'))}
    source_media=json.loads((OUT/'公开媒体清单.json').read_text(encoding='utf-8'))
    report['media_api_total_discrepancy']={'header_reported_total':source_media['reported_total'],'unique_records_returned':len(media),'not_returned_by_public_api':source_media['reported_total']-len(media),'note':'分页复核见媒体分页核对.json；未返回记录的内容未知'}
    report['unique_original_source_urls']=len(set(m['url'] for m in media))
    report['unique_original_urls_downloaded']=len(set(m['url'] for m in media if m['status']==200))
    if report['media_api_total_discrepancy']['not_returned_by_public_api']:report['complete_publicly_discovered_scope']=False
    save(OUT/'采集校验.json',report)
    lines=['# 官网采集报告','','日期：2026-11-24（北京时间）。官网：https://lareine.com.sg/。','',f'- 页面：{len(pages)}，商品地址：{len(products)}；页面队列剩余：{len(report["page_queue_remaining"])}。',f'- 公开媒体原件：{len(media)}，已下载：{report["originals_downloaded"]}；类型：{report["media_types"]}。',f'- 资源URL：{len(resources)}，下载成功：{len(downloaded)}，失败：{len(failures)}；大小约{report["downloaded_bytes"]/1024/1024:.1f}MiB。',f'- SHA-256校验异常：{len(errors)}；图片解码异常：{len(image_failures)}；完全重复内容组：{len(duplicates)}（保留路径，不删除）。',f'- 商品前台显示价格：{report["products_with_frontend_price"]}；询价：{report["products_enquiry_only"]}；疑似模板：{report["template_candidates"]}。','','## 采集范围','',report['scope']+'。公开媒体库可能包含历史素材；资源路径日期不代表当前发布日期。对外部社交平台不做扩展抓取，不推测服务器未公开目录。站点“全部资料”的交付边界为本次可公开发现的资源，不是后台数据库备份。','','## 文件与证据','','- `站点地图/`、`robots.txt`、`站点发现.json`：入口与发现依据。','- `页面原始/`、`页面正文/`、`页面清单.json`：HTTP原文、双语切换视图全文和链接。','- `公开API/`、`公开内容正文/`：公开接口原始返回和发布内容正文；不自动等同于前台当前呈现。','- `站点资源/`：图片、视频、字体、尺寸变体及CSS/JS资源原件。','- `资源清单.json/CSV`、`媒体原件索引.json/CSV`：网址、本地路径、哈希、大小、引用来源、状态。','- `下载失败.json`、`图片解码异常.json`、`重复资源.json`：异常与去重证据。','- `浏览器快照/`：首页及商品语言切换的DOM与可见文本；官网截图接口超时，未生成官网截图。','','## 已完成、未完成与风险','','已完成：公开站点入口及链接遍历、公开媒体枚举、资源下载、产品资料与价格快照、双语节点提取、来源差异记录和本地预览。','未完成：登录后台资料、未公开文件、实际成交/配送/库存确认、功效与资质核验、全部图片内嵌文字OCR审校。','风险点：部分商品疑似主题模板；询价商品接口为0；水光命名与聊天PDF不同；中英切换并不表示所有共享文字都有翻译。',f'验证结果：已下载文件哈希异常{len(errors)}，下载失败{len(failures)}；真实浏览器的本地预览验收另记于采集校验JSON。']
    if failures:
        lines+=['','## 未下载成功项目','']+[f'- {r["url"]}：{r["status"]}；{r.get("error","")}' for r in failures]
    discrepancy=report['media_api_total_discrepancy']
    lines+=['','## 分页总数与实际返回的差异','',f'媒体API声明{discrepancy["header_reported_total"]}条，两种分页均返回同一组{len(media)}条，另{discrepancy["not_returned_by_public_api"]}条未公开返回、内容未知。{len(media)}条记录对应{report["unique_original_source_urls"]}个原件URL，成功下载{report["originals_downloaded"]}条记录、{report["unique_original_urls_downloaded"]}个原件URL；失效占位图影响两条记录。详见媒体分页核对.json。']
    (OUT/'采集报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
