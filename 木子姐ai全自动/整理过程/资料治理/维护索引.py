# -*- coding: utf-8 -*-
"""只读扫描项目，刷新本脚本管理的索引；不移动、不删除、不联网，不执行旧构建器。"""
from pathlib import Path
from collections import Counter,defaultdict
from urllib.parse import urlsplit,unquote,quote
from html.parser import HTMLParser
from datetime import datetime,timezone,timedelta
import json,csv,hashlib,re,ast,sys,os
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).parent
WEB=ROOT/'官网资料/2026-11-24'
DATE='2026-11-24'
REVIEW_DATE='2026-11-26'
MEDIA={'.jpg':'图片','.jpeg':'图片','.png':'图片','.webp':'图片','.gif':'图片','.svg':'矢量/图标','.avif':'图片','.ico':'图标','.mp4':'视频','.webm':'视频','.mov':'视频','.mp3':'音频','.wav':'音频','.ogg':'音频','.pdf':'PDF资料','.psd':'设计源文件','.ai':'设计源文件','.fig':'设计源文件','.sketch':'设计源文件','.blend':'设计源文件','.aep':'设计源文件','.prproj':'设计源文件','.woff':'字体','.woff2':'字体','.ttf':'字体','.otf':'字体','.eot':'字体'}
MANAGED=['素材库/全项目素材清单.json','素材库/全项目素材清单.csv','知识库/文档登记.csv','知识库/文档登记.json','知识库/重复与版本清单.md','整理过程/资料治理/全项目文件清单.json','整理过程/资料治理/引用关系.json','整理过程/资料治理/完全重复清单.json','整理过程/资料治理/尺寸与版本关联.json','整理过程/资料治理/盘点结果.json','整理过程/资料治理/校验结果.json']
MEDIA['.pptx']='可编辑演示文档'
manifest_path=HERE/'索引输出哈希.json'
prior=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}

def rel(p):return p.relative_to(ROOT).as_posix()
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def dump(obj):return json.dumps(obj,ensure_ascii=False,indent=2)+'\n'
def write(p,data):
    name=rel(p)
    if p.exists():
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if name not in prior or prior[name]!=actual:raise RuntimeError('索引已被外部编辑，保留并停止覆盖：'+name)
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data,encoding='utf-8',newline='') if sys.version_info>=(3,10) else p.write_bytes(data.encode('utf-8'))
def csvtext(rows,fields):
    import io
    s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows);return '\ufeff'+s.getvalue()
def link(p):return quote(p,safe='/')

def main():
    before=load('整理过程/资料治理/整理前基线.json')
    original={x['path']:x for x in before['files']}
    changes=load('整理过程/资料治理/询价修复清单.json')
    allowed={x['path']:x['after_sha256'] for x in changes}
    confirmation_changes=ROOT/'整理过程/继续核验/确认状态变更.json'
    if confirmation_changes.exists():allowed.update({x['path']:x['after_sha256'] for x in json.loads(confirmation_changes.read_text(encoding='utf-8'))})
    cache_record=HERE/'编译缓存变更.json'
    if cache_record.exists():allowed.update({x['path']:x['after_sha256'] for x in json.loads(cache_record.read_text(encoding='utf-8'))})
    for batch_changes in (ROOT/'整理过程').glob('新增*/入口变更清单.json'):
        allowed.update({x['path']:x['after_sha256'] for x in json.loads(batch_changes.read_text(encoding='utf-8'))})
    allowed['README.md']=hashlib.sha256((ROOT/'README.md').read_bytes()).hexdigest()
    files=[];decoded={};filemap={}
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or rel(p) in MANAGED or p==manifest_path:continue
        b=p.read_bytes();name=rel(p)
        row={'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'extension':p.suffix.lower(),'filesystem_modified_at':datetime.fromtimestamp(p.stat().st_mtime,timezone(timedelta(hours=8))).isoformat(timespec='seconds')}
        files.append(row);filemap[name]=row
        if p.suffix.lower() in ('.md','.html','.json','.jsonl','.csv','.py','.cjs','.mjs','.txt','.css','.js'):
            try:decoded[name]=b.decode('utf-8-sig')
            except UnicodeDecodeError:pass
    # 基于已存在的来源清单，而非只凭文件名描述内容。
    chat=load('素材库/素材目录.json');resources=load('官网资料/2026-11-24/资源清单.json');media=load('官网资料/2026-11-24/媒体原件索引.json');products=load('知识库/官网/产品目录.json')
    sources={};ancestors={}
    for r in chat['images']:
        sources[r['path']]={'id':r['id'],'content':r['title'],'scene':r['category'],'source':'用户提供微信附件；原发送人/时间未确认','source_url':'','rights':'待确认；未提供肖像、图片或商业复用授权','stage':'原始素材','version':'微信附件批次 '+DATE,'status':'已视觉分类；宣传事实待确认','ai_status':'待确认；未提供生成记录','derived_from':''}
        sources['素材库/'+r['thumbnail']]={**sources[r['path']],'id':'TH-'+r['id'],'stage':'中间产物','content':'缩略图：'+r['title'],'derived_from':r['path']}
    for p in (ROOT/'原始资料').glob('*.pdf'):
        name=rel(p);sources[name]={'id':'D001' if '华文' in p.name else 'D002','content':p.stem+'：封面与7款LA REINE水光产品','scene':'双语产品资料、内容检索','source':'用户提供微信附件','source_url':'','rights':'待确认','stage':'原始资料','version':'微信附件批次 '+DATE,'status':'来源已归档；双语冲突待确认','ai_status':'待确认','derived_from':''}
    for r in resources:
        if not r.get('path'):continue
        name='官网资料/2026-11-24/'+r['path']
        sources[name]={'id':'WEB-'+hashlib.sha256(r['url'].encode()).hexdigest()[:12],'content':' / '.join(r.get('alts',[])) or '官网引用资源，逐图用途待确认','scene':'官网资料复用；依页面或产品引用选用','source':'官网公开下载；不等于授权证明','source_url':r['url'],'rights':'待确认；公开下载不等于商业/字体/肖像许可','stage':'原始网络资源' if 'public-media-original' in r.get('roles',[]) else '网站尺寸变体或技术资源','version':'官网快照 '+DATE,'status':'已保存来源与哈希；业务真实性待确认','ai_status':'待确认；未提供生成记录','derived_from':'','roles':r.get('roles',[]),'remote_sources':r.get('sources',[])}
    for m in media:
        if not m.get('path'):continue
        name='官网资料/2026-11-24/'+m['path']
        if name in sources:sources[name].update(id=m['id'],content=m['title'],scene=m['usage_status'],stage='原始网络资源',media_kind=m['kind'])
        if m.get('thumbnail'):
            thumb='官网资料/2026-11-24/'+m['thumbnail'];sources[thumb]={**sources[name],'id':'TH-'+m['id'],'content':'缩略图：'+m['title'],'stage':'中间产物','derived_from':name}
    for p in products:
        for image in p['images']:
            for name,source in sources.items():
                if source.get('source_url')==image['src']:
                    source['scene']='商品 '+p['name']+' 的产品图；销售/授权状态待确认'
                    source['status']='疑似模板；待确认' if p['is_template_candidate'] else '官网商品关联；宣传事实待确认'
    supplement=ROOT/'素材库/内容复核补充.json'
    if supplement.exists():
        for note in load('素材库/内容复核补充.json')['items']:
            for source in sources.values():
                if source.get('source_url','').split('?')[0]==note['source_url']:
                    source.update({k:v for k,v in note.items() if k!='source_url'})
    frame_manifest=HERE/'视频抽样/抽样来源.json'
    if frame_manifest.exists():
        for video in json.loads(frame_manifest.read_text(encoding='utf-8')):
            for frame in video['frames']:
                sources[frame['path']]={'content':'视频视觉抽样帧，时间'+str(frame['time_seconds'])+'秒','source':'本机FFmpeg提取；来源见抽样来源JSON','scene':'资料盘点/内容审核，不冒充原始产品照片','stage':'中间产物','version':DATE,'rights':'继承原视频，待确认','derived_from':video['path'],'ai_status':'本机视频抽帧；原视频AI来源待确认','status':'抽样证据，非全片审核'}
    # 追加批次采用独立来件状态；不继承旧批次的确认日期。
    batch_manifests=sorted((ROOT/'素材库').glob('新增*/素材目录.json'))
    for batch_manifest in batch_manifests:
        for record in json.loads(batch_manifest.read_text(encoding='utf-8')):
            sources[record['path']]={k:v for k,v in record.items() if k not in ('sha256','bytes','type','width','height','text')}
    # WordPress明确列出的sizes建立同源关系，尺寸变体不认定为重复。
    original_media=load('官网资料/2026-11-24/公开媒体清单.json')['items']
    by_url={r['source_url']:name for name,r in sources.items() if r.get('source_url')}
    for name,source in sources.items():
        u=source.get('source_url','');plain=u.split('?')[0]
        parent=by_url.get(plain)
        if '?' in u and parent and parent!=name and filemap[name]['sha256']==filemap[parent]['sha256']:
            source['derived_from']=parent;source['stage']='网站缓存副本（哈希相同）'
    families=[]
    for m in original_media:
        parent=by_url.get(m['source_url'])
        variants=[]
        for size,v in m.get('media_details',{}).get('sizes',{}).items():
            name=by_url.get(v.get('source_url'))
            if name and name!=parent:
                sources[name]['derived_from']=parent or m['source_url']
                variants.append({'size_label':size,'path':name,'width':v.get('width'),'height':v.get('height')})
        if variants:families.append({'wp_media_id':m['id'],'original_path':parent,'original_url':m['source_url'],'basis':'公开媒体API明确的sizes关联；不依据相似文件名去重','variants':variants})
    refs=[];broken=[]
    def reference(source,target,kind):
        if not target or target.startswith(('#','data:','javascript:')):return
        u=urlsplit(target)
        if u.scheme or target.startswith('//'):return
        # 原始网站HTML的根路径属于历史官网，不是本地相对链接。
        if '/页面原始/' in '/'+source or '/浏览器快照/' in '/'+source or '/站点资源/' in '/'+source or '/修复前备份/' in '/'+source or '/确认状态更新前/' in '/'+source:return
        value=unquote(u.path).replace('\\','/')
        if not value:return
        p=Path(source).parent/value
        absolute=(ROOT/p).resolve()
        try:name=absolute.relative_to(ROOT.resolve()).as_posix()
        except ValueError:return
        if absolute.exists() or name in MANAGED:refs.append({'source':source,'target':name,'kind':kind})
        else:broken.append({'source':source,'target':value,'kind':kind})
    class Links(HTMLParser):
        def __init__(self,source):super().__init__();self.source=source
        def handle_starttag(self,tag,attrs):
            for k,v in attrs:
                if k in ('src','href') and v:reference(self.source,v,'HTML '+k)
    for name,content in decoded.items():
        if '/修复前备份/' in '/'+name or '/确认状态更新前/' in '/'+name:continue
        suffix=Path(name).suffix.lower()
        if suffix=='.md':
            for dest in re.findall(r'\]\(([^)]+)\)',content):reference(name,dest,'Markdown链接')
        elif suffix=='.html':Links(name).feed(content)
        elif suffix in ('.py','.cjs','.mjs'):
            if name.startswith('官网资料/'):continue
            # 静态文字路径只验证可解析存在的候选；动态ROOT/变量拼接保留为静态分析边界。
            for value in re.findall(r'[\'"]([^\'"\r\n]{3,180})[\'"]',content):
                for candidate in (ROOT/value,ROOT/Path(name).parent/value):
                    try:exists=candidate.is_file()
                    except OSError:continue
                    if exists:
                        try:refs.append({'source':name,'target':rel(candidate),'kind':'脚本文字路径（静态）'})
                        except ValueError:pass
    # 现有JSON的路径字段按其原有约定解析；不展开原始API中不属于本地路径的字段。
    for source in ['素材库/原件清单.json','素材库/素材目录.json','官网资料/2026-11-24/页面清单.json','官网资料/2026-11-24/资源清单.json','官网资料/2026-11-24/媒体原件索引.json','知识库/官网/产品目录.json']+[rel(p) for p in batch_manifests]:
        def walk(obj):
            if isinstance(obj,list):
                for v in obj:walk(v)
            elif isinstance(obj,dict):
                for key,value in obj.items():
                    if key in ('path','thumbnail','raw_path','text_path','knowledge_path','page_source') and isinstance(value,str) and value and not urlsplit(value).scheme:
                        base=WEB if source.startswith('官网资料/') or key=='page_source' else ROOT/'知识库/官网' if key=='knowledge_path' else ROOT/'素材库' if key=='thumbnail' else ROOT
                        dest=base/value
                        if dest.exists():refs.append({'source':source,'target':rel(dest),'kind':'JSON字段 '+key})
                        else:broken.append({'source':source,'target':value,'kind':'JSON字段 '+key})
                    elif isinstance(value,(list,dict)):walk(value)
        walk(load(source))
    reference_map=defaultdict(set)
    refs=list({(r['source'],r['target'],r['kind']):r for r in refs}.values())
    for r in refs:reference_map[r['target']].add(r['source'])
    assets=[];decode_errors=[]
    confirmation=load('素材库/业务确认.json') if (ROOT/'素材库/业务确认.json').exists() else None
    for f in files:
        name=f['path'];suffix=f['extension']
        if suffix not in MEDIA:continue
        s=sources.get(name,{})
        stage=s.get('stage','用途/阶段待确认')
        if '/修复前备份/' in '/'+name:stage='历史修复备份'
        elif name.startswith('整理过程/') and not s:stage='中间产物'
        elif name.startswith('素材库/PDF页面/'):
            stage='中间产物';s={'content':'PDF页面渲染（非新增产品原件）','source':'本机由原始PDF渲染','derived_from':'原始资料/'+Path(name).stem.rsplit('-',1)[0]+'.pdf','rights':'继承原PDF；待确认','version':DATE}
        row={**f,**s,'id':s.get('id','LOCAL-'+hashlib.sha256(name.encode()).hexdigest()[:12]),'type':s.get('media_kind',MEDIA[suffix]),'stage':stage,'content':s.get('content','已有过程产物，需结合来源和引用阅读' if stage=='中间产物' else '未完成内容确认；不根据文件名推断业务用途'),'scene':s.get('scene','待确认；不直接对外使用'),'version':s.get('version','批次/版本待确认'),'source':s.get('source','待确认'),'source_url':s.get('source_url',''),'rights':s.get('rights','待确认'),'status':s.get('status','未确认最终成品状态'),'ai_status':s.get('ai_status','待确认；无可核对生成记录'),'derived_from':s.get('derived_from',''),'referenced_by':sorted(reference_map[name]),'last_reviewed':DATE,'business_confirmed_at':None}
        if suffix in ('.jpg','.jpeg','.png','.webp','.gif','.avif','.ico'):
            try:
                with Image.open(ROOT/name) as im:row.update(width=im.width,height=im.height,detected_format=im.format)
            except Exception as e:decode_errors.append({'path':name,'error_type':type(e).__name__})
        elif suffix=='.svg':
            raw=(ROOT/name).read_text(encoding='utf-8',errors='replace')
            if '<font ' in raw or '<font\n' in raw:row['type']='字体'
        row['last_reviewed']=REVIEW_DATE
        if confirmation and name in sources and s.get('inherit_prior_confirmation',True):
            row['previous_review_note']=row['status']
            row['status']=confirmation['status']
            row['business_confirmed_at']=confirmation['confirmation_date']
            row['confirmation_record']=confirmation['record']
        assets.append(row)
    videos=load('官网资料/2026-11-24/视频文件校验.json')
    durations={v['url']:v['probe'].get('format',{}).get('duration') for v in videos}
    for r in assets:
        if r['type']=='视频':r['duration_seconds']=durations.get(r.get('source_url','').split('?')[0])
    # 全项目逐字节重复：只推荐引用入口，不建议删除任一在用路径。
    groups=defaultdict(list)
    for f in files:
        if f['bytes']>0 and not f['path'].startswith('整理过程/资料治理/修复前备份/') and '/确认状态更新前/' not in '/'+f['path'] and '/__pycache__/' not in '/'+f['path']:groups[f['sha256']].append(f['path'])
    def rank(name):return (0 if name.startswith('原始资料/') else 1 if name.startswith('官网资料/') and '--q' not in name else 2 if name.startswith('知识库/') else 3,len(name),name)
    duplicates=[]
    for h,paths in groups.items():
        if len(paths)<2:continue
        recommended=sorted(paths,key=rank)[0]
        structural=(ROOT/paths[0]).read_bytes().strip() in [b'[]',b'{}'] or all(p.startswith('知识库/PDF提取/') for p in paths)
        duplicates.append({'sha256':h,'bytes_each':filemap[paths[0]]['bytes'],'paths':paths,'recommended_entry':recommended,'recommendation':'各自保留，不可互换的结构性重复' if structural else '推荐该路径作为检索入口；所有路径保留','basis':'内容相同但分别表示不同状态/来源或提取占位说明，不能相互替代' if structural else '优先用户原件，其次无查询参数的官网来源路径；选择仅用于检索与复用入口，不证明业务版本更新','action':'保留所有路径；已引用文件不得据此直接删除','references':{p:sorted(reference_map[p]) for p in paths}})
    # 文档登记覆盖知识库及原始需求、官网正文、过程报告/技术脚本；原始程序库不冒充自研文档。
    docs=[]
    for f in files:
        name=f['path'];suffix=f['extension']
        if '/修复前备份/' in '/'+name or '/确认状态更新前/' in '/'+name or '/__pycache__/' in '/'+name:continue
        isdoc=suffix=='.md' or name=='原始资料/文字.txt' or (name.startswith('整理过程/') and suffix in ('.py','.mjs','.cjs'))
        if not isdoc:continue
        content=decoded.get(name,'');title=next((line.lstrip('# ').strip() for line in content.splitlines() if line.startswith('# ')),Path(name).name)
        category='维护与技术说明' if name.startswith('整理过程/') else '官网历史证据' if name.startswith('官网资料/') else '产品说明' if name.startswith('知识库/官网/产品/') or '产品' in name else '需求' if '业务需求' in name or name=='原始资料/文字.txt' else '问题与来源对照' if any(x in name for x in ['待确认','待核验','双语','差异']) else '索引/操作说明'
        source='本项目整理；依据所链接来源' if name.startswith('知识库/') else '官网采集的本地历史快照' if name.startswith('官网资料/') else '用户提供文字' if name=='原始资料/文字.txt' else '项目整理工具/索引'
        state='来源记录（非已确认业务事实）' if name.startswith(('官网资料/','原始资料/')) else '待业务确认/维护草稿'
        if name.startswith('整理过程/'):state='过程工具；非产品业务事实'
        if name in ['知识库/业务需求与资料边界.md','知识库/价格与待核验项.md']:state='微信批次记录；需结合官网增补阅读'
        if name.startswith('官网资料/') and '/公开内容正文/' in '/'+name:state='历史接口正文；不保证前台当前展示'
        new_batch_doc=name.startswith('原始资料/2026-11-25新增/') or name in ('知识库/20261125新增资料.md','知识库/粉之密产品与培训索引.md')
        confirmed=bool(confirmation and not new_batch_doc and (name.startswith(('原始资料/','官网资料/')) or category=='产品说明'))
        docs.append({'path':name,'title':title,'category':category,'purpose':'提供产品信息和来源' if category=='产品说明' else '按分类查证与维护；用途以正文边界为准','source':source,'content_status':confirmation['status'] if confirmed else state,'previous_review_note':state if confirmed else '', 'reviewed_at':DATE,'source_updated_at':next((p['captured_at'] for p in products if '知识库/官网/'+p['knowledge_path']==name),DATE if name.startswith('官网资料/') else '待确认；见正文批次日期'),'filesystem_modified_at':f['filesystem_modified_at'],'business_confirmed_at':confirmation['confirmation_date'] if confirmed else '不适用：过程/维护文档','obsolete_status':'未收到废弃确认；不自动废弃','sha256':f['sha256']})
        docs[-1]['reviewed_at']=REVIEW_DATE
        if new_batch_doc:docs[-1].update(content_status='用户新增来件的整理记录；具体差异保留',source='用户提供20261125批次及所链接原件',business_confirmed_at='未继承旧批次确认日期',source_updated_at='2026-11-25来件目录；制作日期待确认')
    old_changes=[];missing=[]
    for name,old in original.items():
        p=ROOT/name
        if not p.exists():missing.append(name);continue
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        if digest!=old['sha256']:old_changes.append({'path':name,'allowed':name in allowed,'matches_planned_digest':digest==allowed.get(name),'before_sha256':old['sha256'],'after_sha256':digest})
    baseline_checks=[]
    for source,rows,base in [('chat',load('素材库/原件清单.json'),ROOT),('web',resources,WEB)]:
        checked=0;errs=[]
        for r in rows:
            if not r.get('path') or (source=='web' and r.get('status')!=200):continue
            p=base/r['path'];checked+=1
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:errs.append(r['path'])
        baseline_checks.append({'source':source,'checked':checked,'errors':errs})
    backup_errors=[]
    for r in changes:
        p=HERE/'修复前备份'/r['path']
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=r['before_sha256']:backup_errors.append(r['path'])
    inventory={'review_date':DATE,'baseline_file_count':len(original),'current_scanned_files':len(files),'asset_file_count':len(assets),'asset_types':dict(Counter(x['type'] for x in assets)),'asset_stages':dict(Counter(x['stage'] for x in assets)),'document_records':len(docs),'exact_duplicate_groups':len(duplicates),'dimension_families':len(families),'inbound_reference_edges':len(refs),'missing_document_types':['未发现独立会议记录','未发现独立产品技术/研发规范','未发现设计编辑源文件；已下载SVG不自动视为原始设计工程','未发现独立音频文件；MP4含音轨不计为独立音频','未发现经业务确认的最终发布成品清单'],'note':'类型和来源综合元数据、文件头/解码、正文及引用；未完整OCR或语义审校全部素材。生成索引及其输出哈希清单不参与自身文件登记，避免递归哈希；修复备份计入全文件盘点但不计入内容重复建议。'}
    report={'review_date':DATE,'file_integrity':baseline_checks,'deleted_existing_files':missing,'changed_existing_files':old_changes,'unplanned_changes':[r for r in old_changes if not r['allowed'] or not r['matches_planned_digest']],'broken_generated_local_refs':broken,'static_reference_edges':len(refs),'decode_errors':decode_errors,'runtime_validation':'本轮未运行历史联网采集/批量重建；历史浏览器验收仅作历史证据，不冒充本轮验收','scope':'静态文档/HTML/已登记JSON路径和脚本文字路径；未运行远端网络、动态脚本调用及全部UI流程'}
    inventory['review_date']=report['review_date']=REVIEW_DATE
    inventory['missing_document_types']=[x for x in inventory['missing_document_types'] if '未发现设计编辑源文件' not in x]
    inventory['editable_document_note']='新增PPTX为可编辑演示文档；仍未发现PSD/AI/Figma/剪辑工程，嵌入栅格图不等于分层设计工程'
    outputs={
      '素材库/全项目素材清单.json':dump(assets),
      '素材库/全项目素材清单.csv':csvtext([{**r,'referenced_by':' | '.join(r['referenced_by'])} for r in assets],['id','path','type','stage','content','scene','version','source','source_url','rights','status','ai_status','derived_from','width','height','duration_seconds','bytes','sha256','referenced_by','last_reviewed','business_confirmed_at']),
      '知识库/文档登记.json':dump(docs),'知识库/文档登记.csv':csvtext(docs,['path','title','category','purpose','source','source_updated_at','reviewed_at','content_status','business_confirmed_at','obsolete_status','filesystem_modified_at','sha256']),
      '整理过程/资料治理/全项目文件清单.json':dump(files),'整理过程/资料治理/引用关系.json':dump(refs),'整理过程/资料治理/完全重复清单.json':dump(duplicates),'整理过程/资料治理/尺寸与版本关联.json':dump(families),'整理过程/资料治理/盘点结果.json':dump(inventory),'整理过程/资料治理/校验结果.json':dump(report)}
    lines=['# 重复与版本清单','','复核：'+REVIEW_DATE+'。完全重复使用SHA-256确认，不将近似画面、不同尺寸或中英文不同版本当作重复。**仅推荐检索入口，不删除、不移动任何路径。**','',f'全项目非空内容重复{len(duplicates)}组；明确媒体尺寸家族{len(families)}组。修复前备份和Python缓存不参与冗余统计。','','新增批次：[组合与分片关系](../素材库/新增20261125/组合与分片关系.json)、[新增重复核对](../素材库/新增20261125/重复核对.json)。3张合成长图及分片全部保留，PPT原件、54页渲染和61嵌入资源按原件/衍生区分。','','## 完全相同内容','','| 组 | 推荐检索入口 | 相同文件路径 | 依据与动作 |','| --- | --- | --- | --- |']
    for i,r in enumerate(duplicates,1):
        paths='<br>'.join('['+Path(p).name+'](../'+link(p)+')' for p in r['paths'])
        entry='各自保留，不可互换' if r['recommendation'].startswith('各自保留') else f'[{Path(r["recommended_entry"]).name}](../{link(r["recommended_entry"])})'
        lines.append(f'| H{i:03} | {entry} | {paths} | SHA-256相同；'+('结构/占位相同而用途不同，不相互替代' if r['recommendation'].startswith('各自保留') else '全部保留，推荐项仅用作调用入口')+' |')
    lines+=['','## 相似内容、尺寸和语言版本','','- A008/A013为原件哈希确认重复；两条来源编号仍保留。','- 官网三段视频有带查询参数的等内容副本，按哈希列出；主调用入口优先无查询参数路径。','- 官网图片尺寸关联来自公开API的media_details.sizes，见[尺寸与版本关联](../整理过程/资料治理/尺寸与版本关联.json)。它们是派生关系，不能直接清理。','- 中文/英文精华海报、双语水光PDF分别保留。相同主题不代表内容一致，成分差异见水光双语对照。','- 官网CSV/JSON、报告和HTML为不同用途派生物，不因信息重叠判为冗余。','- 原始图片、缩略图、PDF页面渲染与联系表保留阶段标记；没有业务签字的文件不认定为最终成品。','','## 历史/废弃状态','','本项目未发现已明确批准废弃的资料。2026-11-24采集结果均是历史来源快照；文件修改时间不证明产品版本或当前价格。微信初始文档中“未访问官网”“没有视频”仅适用于其批次，当前项目另有官网增补与3段视频。修复前旧询价统计已存入[修复前备份](../整理过程/资料治理/修复前备份/)，不得继续用于对客报价。']
    outputs['知识库/重复与版本清单.md']='\n'.join(lines)+'\n'
    for dest in re.findall(r'\]\(([^)]+)\)',outputs['知识库/重复与版本清单.md']):reference('知识库/重复与版本清单.md',dest,'生成索引Markdown链接')
    report['broken_generated_local_refs']=broken
    report['repair_backups']={'checked':len(changes),'errors':backup_errors}
    proof=HERE/'询价修复验证.json'
    if proof.exists():report['price_fix_verification']=json.loads(proof.read_text(encoding='utf-8'))
    outputs['整理过程/资料治理/校验结果.json']=dump(report)
    # 全部先检查可写性，再写生成文件；手工编辑的索引不被静默覆盖。
    for name,data in outputs.items():
        p=ROOT/name
        if p.exists() and (name not in prior or hashlib.sha256(p.read_bytes()).hexdigest()!=prior[name]):raise RuntimeError('拒绝覆盖外部修改索引：'+name)
    for name,data in outputs.items():write(ROOT/name,data)
    manifest_path.write_text(dump({name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in outputs}),encoding='utf-8')
    print(dump({'inventory':inventory,'validation':{'hash_errors':sum(len(r['errors']) for r in baseline_checks),'missing_old_files':len(missing),'unplanned_changes':len(report['unplanned_changes']),'broken_local_refs':len(broken),'decode_errors':len(decode_errors)}}))
    if missing or backup_errors or report['unplanned_changes'] or broken or decode_errors or any(r['errors'] for r in baseline_checks):sys.exit(1)

if __name__=='__main__':main()
