"""公开页面、公开WordPress媒体及其引用资源的可续跑归档。仅GET，不登录或提交表单。"""
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit,parse_qsl,urlencode,unquote
from datetime import datetime,timezone,timedelta
from concurrent.futures import ThreadPoolExecutor
import requests,json,re,hashlib,time,threading,copy,html as html_entities
from lxml import html

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'官网资料/2026-11-24'
HOST='https://lareine.com.sg'
STAMP=lambda:datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
HEADERS={'User-Agent':'LAReine-LocalArchive/1.0 (public website archive)'}
MEDIA_EXT={'.jpg','.jpeg','.png','.gif','.webp','.svg','.avif','.ico','.mp4','.webm','.mov','.mp3','.wav','.ogg','.pdf','.zip','.doc','.docx','.xls','.xlsx','.ppt','.pptx'}
TECH_EXT={'.css','.js','.woff','.woff2','.ttf','.eot','.otf'}
SKIP_PATH=re.compile(r'^/(?:cart(?:-\d+)?|checkout(?:-\d+)?|my-account(?:-\d+)?|wishlist|wp-admin|wp-login\.php)(?:/|$)')

def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def get(url,binary=False):
    last=None
    for attempt in range(2):
        try:
            r=requests.get(url,headers=HEADERS,timeout=(12,40),allow_redirects=True)
            if r.status_code in (429,500,502,503,504) and attempt==0:
                time.sleep(1);continue
            return r
        except requests.RequestException as e:
            last=e
            if attempt==0:time.sleep(1)
    raise last

def canonical(url):
    p=urlsplit(url)
    host=p.netloc.lower().removeprefix('www.') if hasattr(str,'removeprefix') else p.netloc.lower().replace('www.','',1)
    if p.scheme not in ('https','http') or host!='lareine.com.sg':return None
    if SKIP_PATH.search(p.path):return None
    if p.path.startswith(('/wp-json/','/wp-content/','/wp-includes/')):return None
    if p.path.endswith(('/feed/','.xml','.php')):return None
    q=parse_qsl(p.query,keep_blank_values=True)
    if any(k not in ('page','paged','lang','product-page') for k,v in q):return None
    return urlunsplit(('https','lareine.com.sg',p.path or '/',urlencode(sorted(q)),''))

def cls(c):return 'contains(concat(" ",normalize-space(@class)," ")," '+c+' ")'

def compact(node):
    if node is None:return ''
    return '\n'.join(x.strip() for x in node.text_content().splitlines() if x.strip())

def lang_text(node,lang):
    d=copy.deepcopy(node)
    for n in d.xpath('.//script|.//style|.//noscript|.//svg|.//form'):
        if n.getparent() is not None:n.drop_tree()
    other='lr-zh' if lang=='en' else 'lr-en'
    for n in d.xpath('.//*['+cls(other)+']'):
        if n.getparent() is not None:n.drop_tree()
    return compact(d)

def parse_page(url,r):
    r.encoding='utf-8'
    d=html.fromstring(r.content,base_url=r.url)
    title=' '.join(d.xpath('//title/text()'))
    mains=d.xpath('//main') or d.xpath('//body') or [d]
    main=mains[0]
    bilingual=[]
    for en in d.xpath('//*['+cls('lr-en')+']'):
        sib=en.getnext()
        if sib is not None and 'lr-zh' in (sib.get('class') or '').split():
            bilingual.append({'en':compact(en),'zh':compact(sib)})
    links=[{'url':urljoin(r.url,a.get('href')),'text':re.sub(r'\s+',' ',a.text_content()).strip()} for a in d.xpath('//a[@href]')]
    assets={}
    def add(raw,role,alt=''):
        if not raw:return
        u=urljoin(r.url,raw.strip())
        u=urlunsplit((*urlsplit(u)[:4],''))
        if urlsplit(u).scheme not in ('http','https'):return
        assets.setdefault(u,{'url':u,'roles':[],'alts':[]})
        if role not in assets[u]['roles']:assets[u]['roles'].append(role)
        if alt and alt not in assets[u]['alts']:assets[u]['alts'].append(alt)
    for n in d.xpath('//img|//source|//video|//audio|//input[@type="image"]'):
        for attr in ['src','data-src','data-lazy-src','poster','data-large_image']:
            add(n.get(attr),n.tag+':'+attr,n.get('alt',''))
        for attr in ['srcset','data-srcset','data-lazy-srcset']:
            for part in (n.get(attr) or '').split(','):add(part.strip().split(' ')[0],n.tag+':'+attr,n.get('alt',''))
    for n in d.xpath('//link[@href]'):
        if set((n.get('rel') or '').split()) & {'stylesheet','icon','apple-touch-icon','preload','mask-icon'}:
            add(n.get('href'),'head:'+n.get('rel',''))
    for n in d.xpath('//script[@src]'):add(n.get('src'),'script')
    for n in d.xpath('//meta[@content]'):
        if n.get('property','') in ['og:image','og:video','og:audio'] or n.get('name','') in ['twitter:image','msapplication-TileImage']:
            add(n.get('content'),'meta')
    for n in d.xpath('//*[@style]|//style'):
        for raw in re.findall(r'url\(\s*[\'"]?([^\)\'"\s]+)',n.get('style','')+' '+(n.text or '')):add(raw,'css-inline')
    for link in links:
        if Path(urlsplit(link['url']).path).suffix.lower() in MEDIA_EXT:add(link['url'],'linked-file',link['text'])
    for raw in re.findall(r'https?://[^\s"\'<>\\]+',html_entities.unescape(r.text.replace('\\/','/'))):
        raw=raw.rstrip('),;]}')
        if Path(urlsplit(raw).path).suffix.lower() in MEDIA_EXT:add(raw,'source-reference')
    jsonld=[]
    for n in d.xpath('//script[@type="application/ld+json"]'):
        try:jsonld.append(json.loads(n.text or ''))
        except ValueError:pass
    text_en=lang_text(main,'en');text_zh=lang_text(main,'zh')
    product=None
    if urlsplit(url).path.startswith('/product/'):
        def first(xpath):
            nodes=d.xpath(xpath)
            return compact(nodes[0]) if nodes else ''
        headings=[re.sub(r'\s+',' ',n.text_content()).strip() for n in main.xpath('.//h1')]
        product={'url':url,'name':' / '.join(headings),'headings':headings,'price_text':first('//*['+cls('summary')+']//*['+cls('price')+']'),'currency_context':'SGD' if 'SGD $' in compact(d) else '', 'categories':first('//*['+cls('posted_in')+']'),'sku':first('//*['+cls('sku')+']'),'description':first('//*[@id="tab-description"]'),'short_description':first('//*['+cls('woocommerce-product-details__short-description')+']'),'jsonld':jsonld,'text_en':text_en,'text_zh_view':text_zh}
    return {'url':url,'final_url':r.url,'title':title,'lang':d.get('lang',''),'text_en':text_en,'text_zh_view':text_zh,'bilingual_pairs':bilingual,'links':links,'assets':list(assets.values()),'jsonld':jsonld,'product':product,'external_embeds':[{'src':n.get('src'),'title':n.get('title','')} for n in d.xpath('//iframe[@src]')]}

def crawl():
    maps=json.loads((OUT/'站点发现.json').read_text(encoding='utf-8'))
    seeds={HOST+'/'}
    excluded=[]
    for m in maps:
        for u in m['urls']:
            c=canonical(u)
            if c:seeds.add(c)
            else:excluded.append({'url':u,'reason':'账户/购物车/结账/心愿单或非内容工作流；不操作'})
    prior_path=OUT/'页面清单.json'
    records=json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.exists() else []
    records_by_url={r['url']:r for r in records if r.get('status')==200}
    done=set(records_by_url)
    queue=seeds-done
    for r in records_by_url.values():
        for link in r.get('links',[]):
            c=canonical(link['url'])
            if c and c not in done:queue.add(c)
    (OUT/'页面原始').mkdir(exist_ok=True)
    (OUT/'页面正文').mkdir(exist_ok=True)
    def fetch_page(u):
        filename=hashlib.sha256(u.encode()).hexdigest()[:16]
        at=STAMP()
        try:
            r=get(u)
            result={'url':u,'status':r.status_code,'final_url':r.url,'captured_at':at,'content_type':r.headers.get('Content-Type',''),'sha256':hashlib.sha256(r.content).hexdigest(),'bytes':len(r.content),'raw_path':f'页面原始/{filename}.html'}
            (OUT/result['raw_path']).write_bytes(r.content)
            if r.status_code==200 and 'html' in result['content_type']:
                result.update(parse_page(u,r))
                result['text_path']=f'页面正文/{filename}.md'
                (OUT/result['text_path']).write_text(f'# {result["title"]}\n\n来源：{u}\n\n采集：{at}\n\n## 英文视图（去除lr-zh节点）\n\n{result["text_en"]}\n\n## 中文切换视图（去除lr-en节点；共用内容可能仍为英文）\n\n{result["text_zh_view"]}\n',encoding='utf-8')
            return result
        except Exception as e:return {'url':u,'status':None,'captured_at':at,'error':str(e)}
    while queue and len(done)<500:
        batch=sorted(queue)[:9];queue.difference_update(batch)
        with ThreadPoolExecutor(max_workers=3) as pool:
            found=list(pool.map(fetch_page,batch))
        for r in found:
            done.add(r['url']);records_by_url[r['url']]=r
            if r.get('status')==200:
                for link in r.get('links',[]):
                    c=canonical(link['url'])
                    if c and c not in done:queue.add(c)
        queue.difference_update(done)
        save(prior_path,sorted(records_by_url.values(),key=lambda x:x['url']))
        print(json.dumps({'pages_done':len(done),'queued':len(queue),'batch':[{'url':r['url'],'status':r['status']} for r in found]},ensure_ascii=False),flush=True)
    save(OUT/'范围排除.json',excluded)
    save(OUT/'页面未处理.json',sorted(queue))

def public_media():
    # 页面link rel=https://api.w.org/公开声明了这个API根；只访问公开可读媒体。
    root=get(HOST+'/wp-json/')
    (OUT/'公开API').mkdir(exist_ok=True)
    (OUT/'公开API/root.json').write_bytes(root.content)
    routes=root.json().get('routes',{}) if root.status_code==200 else {}
    if '/wp/v2/media' not in routes:
        save(OUT/'公开媒体清单.json',{'status':'API未公开media路由','items':[]});return
    base=HOST+'/wp-json/wp/v2/media?per_page=100'
    first=get(base+'&page=1')
    (OUT/'公开API/media-1.json').write_bytes(first.content)
    if first.status_code!=200:
        save(OUT/'公开媒体清单.json',{'status':first.status_code,'items':[]});return
    count=int(first.headers.get('X-WP-TotalPages','1'))
    items=first.json()
    def one(n):
        u=base+'&page='+str(n);r=get(u)
        (OUT/f'公开API/media-{n}.json').write_bytes(r.content)
        r.raise_for_status();return r.json()
    with ThreadPoolExecutor(max_workers=3) as pool:
        for rows in pool.map(one,range(2,count+1)):items.extend(rows)
    save(OUT/'公开媒体清单.json',{'status':200,'api':base,'reported_total':int(first.headers.get('X-WP-Total',len(items))),'pages':count,'captured_at':STAMP(),'items':items})
    print(json.dumps({'public_media_items':len(items),'pages':count}),flush=True)

def public_content():
    routes=json.loads((OUT/'公开API/root.json').read_text(encoding='utf-8')).get('routes',{})
    results={}
    for endpoint in ['/wp/v2/pages','/wp/v2/posts','/wp/v2/product','/wc/store/v1/products']:
        if endpoint not in routes:continue
        key=endpoint.rsplit('/',1)[-1]
        if endpoint.startswith('/wc/'):key='store-products'
        base=HOST+'/wp-json'+endpoint+'?per_page=100'
        response=get(base+'&page=1')
        (OUT/f'公开API/{key}-1.json').write_bytes(response.content)
        if response.status_code!=200:
            results[key]={'status':response.status_code,'items':[]};continue
        items=response.json();total_pages=int(response.headers.get('X-WP-TotalPages','1'))
        for n in range(2,total_pages+1):
            r=get(base+'&page='+str(n));r.raise_for_status()
            (OUT/f'公开API/{key}-{n}.json').write_bytes(r.content);items.extend(r.json())
        results[key]={'status':response.status_code,'url':base,'total_reported':response.headers.get('X-WP-Total'),'items':items}
        print(json.dumps({'public_api':key,'count':len(items)}),flush=True)
    save(OUT/'公开内容清单.json',results)

def reparse_local():
    records=json.loads((OUT/'页面清单.json').read_text(encoding='utf-8'))
    for row in records:
        if row.get('status')!=200:continue
        r=requests.Response();r.status_code=200;r.url=row['final_url'];r._content=(OUT/row['raw_path']).read_bytes();r.encoding='utf-8'
        row.update(parse_page(row['url'],r))
    save(OUT/'页面清单.json',records)
    print('已从本地原始HTML重新解析页面引用；未重复请求网站')

def download_resources():
    from collections import defaultdict
    pages=json.loads((OUT/'页面清单.json').read_text(encoding='utf-8'))
    media=json.loads((OUT/'公开媒体清单.json').read_text(encoding='utf-8'))['items']
    refs={}
    def add(u,source,role,alt=''):
        if not u:return
        u=u.replace('\\/','/')
        p=urlsplit(u)
        if p.scheme not in ('http','https'):return
        u=urlunsplit((p.scheme,p.netloc,p.path,p.query,''))
        row=refs.setdefault(u,{'url':u,'sources':[],'roles':[],'alts':[]})
        if source not in row['sources']:row['sources'].append(source)
        if role not in row['roles']:row['roles'].append(role)
        if alt and alt not in row['alts']:row['alts'].append(alt)
    for p in pages:
        for a in p.get('assets',[]):
            for role in a['roles']:add(a['url'],p['url'],role,' / '.join(a.get('alts',[])))
    for m in media:
        src=HOST+'/wp-json/wp/v2/media/'+str(m['id'])
        add(m.get('source_url'),src,'public-media-original',m.get('title',{}).get('rendered',''))
        for size,v in m.get('media_details',{}).get('sizes',{}).items():add(v.get('source_url'),src,'public-media-size:'+size)
        orig=m.get('media_details',{}).get('original_image')
        if orig:add(urljoin(m['source_url'],orig),src,'public-media-original-unscaled')
        rendered=m.get('description',{}).get('rendered','')+' '+m.get('caption',{}).get('rendered','')
        for u in re.findall(r'https?://[^\s"\'<>]+',rendered):
            if Path(urlsplit(u).path).suffix.lower() in MEDIA_EXT:add(u,src,'public-media-caption-reference')
    content_path=OUT/'公开内容清单.json'
    if content_path.exists():
        content=json.loads(content_path.read_text(encoding='utf-8'))
        for key,block in content.items():
            for item in block['items']:
                strings=json.dumps(item,ensure_ascii=False).replace('\\/','/')
                for u in re.findall(r'https?://[^\s"\'<>\\]+',strings):
                    u=u.rstrip('),;]}')
                    if Path(urlsplit(u).path).suffix.lower() in MEDIA_EXT:add(u,item.get('link',item.get('permalink',block['url'])),'public-content-reference')
    # 浏览器实载资源补足currentSrc与动态样式。
    for p in (OUT/'浏览器快照').glob('*.json'):
        data=json.loads(p.read_text(encoding='utf-8'))
        for item in data.get('media',[]):add(item.get('url'),data['url'],'browser-currentSrc',item.get('alt',''))
    prior=OUT/'资源清单.json'
    cached={r['url']:r for r in json.loads(prior.read_text(encoding='utf-8'))} if prior.exists() else {}
    done=set();records={};queue=set(refs)
    def local_path(u):
        p=urlsplit(u)
        parts=[re.sub(r'[<>:"|?*\x00-\x1f]','_',s).rstrip('. ') or '_' for s in unquote(p.path).split('/') if s not in ('','.','..')]
        if not parts:parts=['index']
        if p.query:
            last=Path(parts[-1]);parts[-1]=last.stem+'--q'+hashlib.sha256(p.query.encode()).hexdigest()[:10]+last.suffix
        return Path('站点资源')/p.netloc/Path(*parts)
    def one(u):
        row=dict(refs[u]);path=local_path(u)
        old=cached.get(u)
        if old and old.get('status')==200 and old.get('path') and (OUT/old['path']).exists():
            data=(OUT/old['path']).read_bytes()
            if hashlib.sha256(data).hexdigest()==old['sha256']:
                row.update({k:v for k,v in old.items() if k not in ('sources','roles','alts')});return row
        try:
            r=get(u);ct=r.headers.get('Content-Type','')
            row.update(status=r.status_code,final_url=r.url,content_type=ct,captured_at=STAMP(),bytes=len(r.content),sha256=hashlib.sha256(r.content).hexdigest(),path=path.as_posix())
            if r.status_code==200 and ('text/html' not in ct or Path(urlsplit(u).path).suffix.lower() in ['.html','.htm']):
                dest=OUT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(r.content)
            else:
                row['error']='HTTP错误或资源返回HTML';row['path']=''
                if r.status_code==200:row['status']='unexpected_html'
        except Exception as e:row.update(status=None,error=str(e),captured_at=STAMP(),path='')
        return row
    while queue:
        batch=sorted(queue,key=lambda u:(0 if 'public-media-original' in refs[u]['roles'] else 1,u))[:30]
        queue.difference_update(batch)
        with ThreadPoolExecutor(max_workers=4) as pool:
            found=list(pool.map(one,batch))
        for row in found:
            u=row['url'];records[u]=row;done.add(u)
            if row.get('status')==200 and row.get('path'):
                ext=Path(urlsplit(u).path).suffix.lower()
                if ext=='.css' or 'text/css' in row.get('content_type',''):
                    css=(OUT/row['path']).read_text(encoding='utf-8',errors='replace')
                    matches=re.findall(r'url\(\s*[\'"]?([^\)\'"\s]+)',css)+re.findall(r'@import\s+[\'"]([^\'"]+)',css)
                    for raw in matches:
                        if raw.startswith(('data:','#')):continue
                        nested=urljoin(u,raw)
                        parsed=urlsplit(nested)
                        nested=urlunsplit((parsed.scheme,parsed.netloc,parsed.path,parsed.query,''))
                        add(nested,u,'stylesheet-reference')
                        if nested not in done:queue.add(nested)
        save(prior,sorted(records.values(),key=lambda r:r['url']))
        print(json.dumps({'resources_done':len(done),'queued':len(queue),'failures':sum(r.get('status')!=200 for r in records.values()),'downloaded_MB':round(sum(r.get('bytes',0) for r in records.values() if r.get('path'))/1024/1024,1)}),flush=True)
    save(OUT/'资源待处理.json',[])

if __name__=='__main__':
    import sys
    if '--media-api' in sys.argv:public_media()
    elif '--content-api' in sys.argv:public_content()
    elif '--download' in sys.argv:download_resources()
    elif '--reparse' in sys.argv:reparse_local()
    else:crawl()
