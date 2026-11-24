from pathlib import Path
import requests,json,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'官网资料/2026-11-24'
OUT.mkdir(parents=True,exist_ok=True)
HEADERS={'User-Agent':'LAReine-LocalArchive/1.0 (public website archive)'}
def get(url):
    r=requests.get(url,headers=HEADERS,timeout=(12,35))
    r.raise_for_status()
    return r

def main():
    r=get('https://lareine.com.sg/robots.txt')
    (OUT/'robots.txt').write_bytes(r.content)
    index=get('https://lareine.com.sg/wp-sitemap.xml')
    maps=[n.text for n in ET.fromstring(index.content).iter() if n.tag.endswith('}loc')]
    dest=OUT/'站点地图';dest.mkdir(exist_ok=True)
    (dest/'wp-sitemap.xml').write_bytes(index.content)
    def parse(url):
        response=get(url)
        (dest/url.rsplit('/',1)[-1]).write_bytes(response.content)
        return {'sitemap':url,'urls':[n.text for n in ET.fromstring(response.content).iter() if n.tag.endswith('}loc')]}
    with ThreadPoolExecutor(max_workers=3) as pool:
        data=list(pool.map(parse,maps))
    (OUT/'站点发现.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False,indent=2))
    r=get('https://lareine.com.sg/')
    (OUT/'首页原始.html').write_bytes(r.content)
    print('Homepage bytes:',len(r.content))

if __name__=='__main__':main()
