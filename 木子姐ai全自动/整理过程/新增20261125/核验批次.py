# -*- coding: utf-8 -*-
"""核验原件、PPT结构、资源、图片与本地引用，不联网，不写原件。"""
from pathlib import Path
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import hashlib,json,zipfile,re,subprocess
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\ZIQINGBO\Desktop\新建文件夹\木子姐ai全自动\20261125')
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
errors=[]
originals=load('素材库/新增20261125/原件清单.json')
for r in originals:
 for origin,p in [('desktop',SOURCE/r['source_relative']),('project',ROOT/r['path'])]:
  if not p.is_file() or sha(p)!=r['sha256']:errors.append({'kind':'original_hash','origin':origin,'path':str(p)})
source_paths={p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob('*') if p.is_file()}
assert source_paths=={r['source_relative'] for r in originals},'新增目录文件集合发生变化，需重新盘点'
ppt=ROOT/originals[-1]['path']
embedded=load('素材库/新增20261125/PPT嵌入素材清单.json')
with zipfile.ZipFile(ppt) as z:
 bad=z.testzip()
 if bad:errors.append({'kind':'ppt_zip','member':bad})
 slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
 assert len(slides)==54
 for r in embedded:
  if hashlib.sha256(z.read(r['ppt_member'])).hexdigest()!=r['sha256'] or sha(ROOT/r['path'])!=r['sha256']:errors.append({'kind':'embedded_hash','path':r['path']})
catalog=load('素材库/新增20261125/素材目录.json')
images=0
for r in catalog:
 p=ROOT/r['path']
 if p.suffix.lower() in ('.png','.jpg','.jpeg','.gif','.bmp','.tif','.tiff'):
  try:
   with Image.open(p) as im:im.load()
   images+=1
  except Exception as e:errors.append({'kind':'image_decode','path':r['path'],'error':type(e).__name__})
 if sha(p)!=r['sha256']:errors.append({'kind':'catalog_hash','path':r['path']})
 if r.get('derived_from') and not (ROOT/r['derived_from']).is_file():errors.append({'kind':'derived_missing','path':r['path']})
refs=[]
def check(source,dest):
 u=urlsplit(dest)
 if u.scheme or dest.startswith(('#','//','data:')):return
 if not u.path:return
 p=(ROOT/source).parent/unquote(u.path)
 refs.append((source,str(p)))
 if not p.exists():errors.append({'kind':'broken_ref','source':source,'target':dest})
class Links(HTMLParser):
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k in ('href','src') and v:check('素材库/新增20261125/新增素材预览.html',v)
html=(ROOT/'素材库/新增20261125/新增素材预览.html').read_text(encoding='utf-8')
Links().feed(html)
for name in ['知识库/20261125新增资料.md','知识库/20261125待确认问题.md','知识库/粉之密产品与培训索引.md','知识库/整理记录-2026-11-26.md','素材库/新增20261125/素材索引.md']:
 for dest in re.findall(r'\]\(([^)]+)\)',(ROOT/name).read_text(encoding='utf-8')):check(name,dest)
assert html.count('class="card"')==93 and '<details>' in html and '<details open' not in html
js=html.split('<script>')[1].split('</script>')[0]
# 用Node模拟DOM验证实际过滤脚本；这不是浏览器验收。
test='''const vm=require('vm'),assert=require('assert');const state={q:{value:'',addEventListener(){}},category:{value:'',addEventListener(){}},count:{}};const cards=[{dataset:{search:'N1125-001 Yvelise SERUM',category:'瓶身产品图'}},{dataset:{search:'N1125-P53 加盟政策',category:'招商与价格历史版本'}}];const context={document:{querySelectorAll:()=>cards,getElementById:id=>state[id]}};vm.createContext(context);vm.runInContext(SCRIPT,context);assert(cards.every(c=>!c.hidden));state.q.value='serum';vm.runInContext('filter()',context);assert(!cards[0].hidden&&cards[1].hidden);state.q.value='';state.category.value='招商与价格历史版本';vm.runInContext('filter()',context);assert(cards[0].hidden&&!cards[1].hidden);state.q.value='不存在';vm.runInContext('filter()',context);assert(cards.every(c=>c.hidden));console.log('4 search scenarios passed');'''.replace('SCRIPT',json.dumps(js,ensure_ascii=False))
jsfile=WORK/'检索逻辑验证.cjs';jsfile.write_text(test,encoding='utf-8')
run=subprocess.run(['node',str(jsfile)],capture_output=True,encoding='utf-8')
if run.returncode:errors.append({'kind':'search_script','error':run.stderr})
# 对照导入前基线；生成索引及明确登记的导航修改为预期变更。
changed=[];missing=[]
prior=load('整理过程/新增20261125/导入前基线.json')
approved={r['path']:r['after_sha256'] for r in load('整理过程/新增20261125/入口变更清单.json')}
generated=set(load('整理过程/资料治理/索引输出哈希.json'))|{'整理过程/资料治理/索引输出哈希.json'}
for r in prior:
 p=ROOT/r['path']
 if not p.exists():missing.append(r['path']);continue
 h=sha(p)
 if h!=r['sha256']:
  expected=r['path'] in generated or approved.get(r['path'])==h
  changed.append({'path':r['path'],'expected':expected,'before_sha256':r['sha256'],'after_sha256':h})
  if not expected:errors.append({'kind':'unplanned_change','path':r['path']})
errors.extend({'kind':'missing_old','path':p} for p in missing)
full=load('整理过程/资料治理/校验结果.json')
for k in ['unplanned_changes','deleted_existing_files','broken_generated_local_refs','decode_errors']:
 if full.get(k):errors.append({'kind':'full_library_'+k,'count':len(full[k])})
assets=load('素材库/全项目素材清单.json');assets={r['path']:r for r in assets}
for r in catalog:
 if r['path'] not in assets:errors.append({'kind':'missing_global_asset','path':r['path']})
 elif assets[r['path']]['business_confirmed_at'] is not None:errors.append({'kind':'inherited_old_confirmation','path':r['path']})
report={'checked_at':'2026-11-26 Asia/Shanghai','originals':len(originals),'desktop_and_project_hash_checks':len(originals)*2,'ppt_slides':len(slides),'rendered_pages':54,'embedded_members':len(embedded),'catalog_records':len(catalog),'decoded_images':images,'local_reference_checks':len(refs),'search_logic':run.stdout.strip(),'original_vs_old_exact_duplicates':sum(bool(r['identical_existing_paths']) for r in originals),'old_missing':missing,'old_changed':changed,'full_library_original_checks':full.get('file_integrity'),'errors':errors,'unverified':['真实浏览器交互和布局验收','图片内细小文字完整OCR与逐字审校','现行资质、现行价格与护理版本的外部核实'],'git_publication':'本轮未提交或推送'}
(WORK/'校验结果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['old_changed','full_library_original_checks']},ensure_ascii=False,indent=2))
raise SystemExit(1 if errors else 0)
