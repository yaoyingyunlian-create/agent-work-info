from pathlib import Path
import json,urllib.request,urllib.parse,hashlib,concurrent.futures,time
ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/'整理成果/官网采集/2026-11-27'
OUT=ROOT/'整理成果/素材库/官网素材/2026-11-27'
OUT.mkdir(parents=True,exist_ok=True)
sources={}
for p in sorted((CAP/'页面').glob('*.json')):
    d=json.loads(p.read_text(encoding='utf-8'))
    for kind,entries in [('image',d.get('images',[])),('media',d.get('media',[]))]:
        for e in entries:
            for url in [e.get('url') or e.get('src'),e.get('poster')]:
                if not url or not url.startswith('https://'):continue
                s=sources.setdefault(url,dict(url=url,kind=kind,pages=[],alts=[]))
                if d['url'] not in s['pages']:s['pages'].append(d['url'])
                if e.get('alt') and e['alt'] not in s['alts']:s['alts'].append(e['alt'])
manifest=OUT/'素材清单.json'
old=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
known={r['url']:r for r in old}
def download(item):
    url=item['url'];prev=known.get(url)
    if prev and prev.get('status')=='downloaded' and (ROOT/prev['local_path']).exists():
        return dict(prev,pages=item['pages'],alts=item['alts'])
    ext=Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).suffix.lower()
    key=hashlib.sha256(url.encode()).hexdigest()[:16]
    path=OUT/(key+ext)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:7897','https':'http://127.0.0.1:7897'}))
    result=dict(item,collected_at='2026-11-27',authorization='官网公开展示，不等于商业复用授权')
    try:
        with opener.open(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.airobot2028.com/'}),timeout=35) as r:
            result.update(http_status=r.status,content_type=r.headers.get('Content-Type'),final_url=r.url)
            with path.open('wb') as f:
                while True:
                    chunk=r.read(1024*512)
                    if not chunk:break
                    f.write(chunk)
        result.update(status='downloaded',local_path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    except Exception as e:result.update(status='failed',error=str(e).strip())
    print(result['status'],ext,url,flush=True)
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(download,sources.values()))
for i,r in enumerate(results,1):r['id']=known.get(r['url'],{}).get('id',f'WA{len(old)+i:03}')
manifest.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print('TOTAL',len(results),'OK',sum(r['status']=='downloaded' for r in results),flush=True)
