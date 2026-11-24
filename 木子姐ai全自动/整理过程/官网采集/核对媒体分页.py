# -*- coding: utf-8 -*-
import requests,json
from concurrent.futures import ThreadPoolExecutor
from 采集官网 import OUT,HOST,get,save,STAMP

base=HOST+'/wp-json/wp/v2/media?per_page=20'
r=get(base+'&page=1');r.raise_for_status()
count=int(r.headers['X-WP-TotalPages'])
def one(i):
    response=r if i==1 else get(base+'&page='+str(i))
    response.raise_for_status()
    (OUT/f'公开API/media-audit-20-{i}.json').write_bytes(response.content)
    items=response.json()
    return {'page':i,'reported_total':response.headers.get('X-WP-Total'),'reported_pages':response.headers.get('X-WP-TotalPages'),'returned_count':len(items),'ids':[x['id'] for x in items]},items
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(one,range(1,count+1)))
audit={str(meta['page']):meta for meta,items in rows}
current=json.loads((OUT/'公开媒体清单.json').read_text(encoding='utf-8'))
known={r['id']:r for r in current['items']}
old=set(known)
for meta,items in rows:
    for item in items:known[item['id']]=item
result={'initial_reported_total':current['reported_total'],'initial_returned':len(current['items']),'page_audit':audit,'unique_returned_after_audit':len(known),'new_ids':sorted(set(known)-old),'note':'两种分页粒度均只读取匿名公开API，未扩大到需要鉴权的内容'}
save(OUT/'媒体分页核对.json',result)
current['items']=sorted(known.values(),key=lambda r:r['id'],reverse=True)
current['pagination_audit']=result
save(OUT/'公开媒体清单.json',current)
print(json.dumps(result,ensure_ascii=False,indent=2))
