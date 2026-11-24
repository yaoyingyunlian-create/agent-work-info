from pathlib import Path
import hashlib, json, shutil, csv, html
from urllib.parse import quote, unquote
from PIL import Image, ImageOps, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SOURCE = Path(r'C:\Users\ZIQINGBO\Desktop\新建文件夹\木子姐ai全自动')
RAW = ROOT / '原始资料'
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 19)

def prepare():
    rows = []
    for p in sorted(SOURCE.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(SOURCE)
        dst = RAW / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f'原件冲突: {dst}')
        if not dst.exists():
            shutil.copy2(p, dst)
        row = dict(source_relative=str(rel), path=dst.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=digest)
        if p.suffix.lower() in ['.jpg', '.png', '.jpeg']:
            row['id'] = f'A{1 + sum("id" in x for x in rows):03}'
            with Image.open(dst) as im:
                row['width'], row['height'] = im.size
        rows.append(row)
    (ROOT / '素材库').mkdir(exist_ok=True)
    (ROOT / '素材库/原件清单.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    images = [r for r in rows if 'id' in r]
    out = ROOT / '整理过程'
    out.mkdir(exist_ok=True)
    for offset in range(0, len(images), 6):
        sheet = Image.new('RGB', (1500, 1900), 'white')
        draw = ImageDraw.Draw(sheet)
        for n, row in enumerate(images[offset:offset+6]):
            x, y = (n % 3) * 500, (n // 3) * 950
            with Image.open(ROOT / row['path']) as im:
                im = ImageOps.exif_transpose(im).convert('RGB')
                im.thumbnail((490, 880))
                sheet.paste(im, (x + (500-im.width)//2, y+50))
            draw.text((x+8,y+6), row['id']+' '+Path(row['source_relative']).name[-24:], fill='black', font=font)
        sheet.save(out / f'联系表-{offset//6+1:02}.jpg', quality=90)
    print(json.dumps({'files':len(rows), 'images':len(images), 'sheets':(len(images)+5)//6}, ensure_ascii=False))

def pdf_previews():
    import fitz
    dest = ROOT / '素材库/PDF页面'
    dest.mkdir(exist_ok=True)
    for p in sorted(RAW.glob('*.pdf')):
        with fitz.open(p) as doc:
            for i, page in enumerate(doc):
                page.get_pixmap(matrix=fitz.Matrix(1.15, 1.15)).save(str(dest / f'{p.stem}-{i+1}.png'))

def build():
    originals = json.loads((ROOT/'素材库/原件清单.json').read_text(encoding='utf-8'))
    annotations = json.loads((ROOT/'素材库/人工标注.json').read_text(encoding='utf-8'))
    by_source = {r['source_relative']: r for r in originals}
    assets = []
    seen = {}
    thumb_dir = ROOT/'素材库/缩略图'
    thumb_dir.mkdir(exist_ok=True)
    for a in annotations:
        r = by_source[a['source_relative']]
        if r['sha256'] != a['source_sha256']:
            raise RuntimeError(f'来源已改变，必须重新核对标注: {a["id"]}')
        entry = {**r, **a}
        entry['duplicate_of'] = seen.get(r['sha256'], '')
        seen.setdefault(r['sha256'], a['id'])
        entry['status'] = '原图已视觉分类；产品及宣传事实未独立核验'
        entry['thumbnail'] = f'缩略图/{a["id"]}.jpg'
        with Image.open(ROOT/r['path']) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((480,600))
            im.save(ROOT/'素材库'/entry['thumbnail'], quality=85)
        assets.append(entry)
    if len(assets) != sum('id' in r for r in originals):
        raise RuntimeError('有图片未标注，请核对原件清单')

    cn = ['LA REINE封面','焕颜透亮精华·透亮水光肌','青春动能素·养护抗衰','III重组胶原蛋白·肌肤年轻化','紧致抗皱精华·重塑紧致轮廓','修复水光精华·修复敏感肌肤','清颜净肤·修复痘痘肌','粉红动能素·焕活定位']
    en = ['LA REINE Cover','HydraMoist Elixir Essence','HydraMoist Kinetic Essence','HydraMoist Vitality Infusion Essence','HydraMoist Quantum Essence','HydraMoist Aqua Boost Essence','HydraMoist DermShield Essence','HydroDNA Elixir Essence']
    pages = []
    for docid, name, lang, titles in [('D001','水光（华文）','中文',cn),('D002','水光（英文）','英文',en)]:
        p = RAW/(name+'.pdf')
        for i, title in enumerate(titles,1):
            pages.append(dict(id=f'{docid}-P{i:02}', title=title, category='LA REINE水光', language=lang, path=p.relative_to(ROOT).as_posix(), preview=f'PDF页面/{name}-{i}.png', risk='英文第8页成分/定位疑似复用第7页；中英文第2页成分有差异' if i in [2,8] else '宣传事实、适用性、成分及用法待确认'))
    catalog = {'collected_at':'2026-11-24', 'timezone':'Asia/Shanghai', 'source_directory':str(SOURCE), 'scope':'用户提供本地资料；未读取微信实时窗口或完整聊天', 'images':assets, 'pdf_pages':pages}
    (ROOT/'素材库/素材目录.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    fields = ['id','title','category','language','risk','path','width','height','bytes','sha256','duplicate_of','source_relative','status']
    with (ROOT/'素材库/素材目录.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        writer.writeheader(); writer.writerows(assets)
    e = html.escape
    cards=[]
    for r in assets+pages:
        target = '../'+quote(r['path'],safe='/')
        src=quote(r.get('thumbnail',r.get('preview')),safe='/')
        preview=quote(r.get('preview',''),safe='/')
        search=' '.join(str(r.get(k,'')) for k in ['id','title','category','language','risk','source_relative'])
        extra=f'<a href="{preview}" target="_blank">页面大图</a> · ' if preview else ''
        cards.append(f'<article data-search="{e(search,quote=True)}" data-group="{e(r["category"],quote=True)}" data-lang="{r["language"]}"><a href="{preview or target}" target="_blank"><img loading="lazy" src="{src}" alt="{e(r["title"],quote=True)}"></a><div class="body"><small>{r["id"]} · {r["language"]} · {e(r["category"])}</small><h2>{e(r["title"])}</h2><p>{e(r["risk"])}</p><footer>{extra}<a href="{target}" target="_blank">打开原件</a></footer></div></article>')
    groups=''.join(f'<option>{e(c)}</option>' for c in dict.fromkeys(r['category'] for r in assets+pages))
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>木子姐 · 知识与素材库</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f2ec;color:#222;font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}header,main{max-width:1440px;margin:auto;padding:26px}header{padding-top:40px}h1{margin:4px 0;font-size:32px}h2{font-size:17px;margin:6px 0}header p{max-width:1000px;color:#555}a{color:#695425}nav{display:flex;gap:20px;flex-wrap:wrap}.tools{position:sticky;top:0;background:#f4f2ecf5;z-index:2;padding:16px 0;display:flex;gap:10px;flex-wrap:wrap}input,select{font:inherit;border:1px solid #bfb8a6;background:white;border-radius:7px;padding:10px}input{flex:1;min-width:220px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px}article{background:white;border:1px solid #e2ded3;border-radius:10px;overflow:hidden}article[hidden]{display:none}article img{width:100%;height:300px;object-fit:contain;background:#eae7e1;display:block}.body{padding:16px}small{color:#756443}.body p{color:#666;font-size:13px}footer{border-top:1px solid #eee;padding-top:10px}#count{padding-bottom:15px}#empty{padding:30px;background:white}a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #956b1b;outline-offset:3px}
</style><header><small>本地资料整理 · 2026-11-24</small><h1>木子姐 · 知识与素材库</h1><p>60张原始图片 · 2份双语PDF（16页）· 1份需求文字。按产品、主题和语言检索；点击图片查看大图。资料宣传、价格、案例与授权尚待核实。本页不联网、不上传数据。</p><nav><a href="../README.md">总索引</a><a href="../知识库/产品知识索引.md">产品知识</a><a href="../知识库/水光双语对照.md">水光双语对照</a><a href="../知识库/价格与待核验项.md">价格与待核验项</a><a href="素材目录.csv" download>下载CSV</a></nav></header><main><div class="tools"><input id="q" aria-label="搜索素材" placeholder="搜索编号、名称、成分、主题…"><select id="group" aria-label="筛选分类"><option value="">全部分类</option>GROUPS</select><select id="lang" aria-label="筛选语言"><option value="">全部语言</option><option>中文</option><option>英文</option></select></div><div id="count" role="status" aria-live="polite">共76项：60张图片与16页PDF</div><div class="grid">CARDS</div><p id="empty" hidden>没有匹配项，请更换关键词或筛选条件。</p></main><script>
const cards=Array.from(document.querySelectorAll('article'));const q=document.getElementById('q'),group=document.getElementById('group'),lang=document.getElementById('lang');function filter(){const term=q.value.trim().toLowerCase();let n=0;for(const c of cards){const show=c.dataset.search.toLowerCase().includes(term)&&(!group.value||c.dataset.group===group.value)&&(!lang.value||c.dataset.lang===lang.value);c.hidden=!show;if(show)n++;}document.getElementById('count').textContent=`显示 ${n} / ${cards.length} 项（含PDF页面）`;document.getElementById('empty').hidden=n>0;}q.addEventListener('input',filter);group.addEventListener('change',filter);lang.addEventListener('change',filter);
</script></html>'''.replace('GROUPS',groups).replace('CARDS','\n'.join(cards))
    (ROOT/'素材库/素材预览.html').write_text(page,encoding='utf-8')
    lines=['# 素材索引','','原件按来源保留，不改变图片内容。风险标记是资料使用边界，不代表产品已获验证。','','| 编号 | 标题 | 分类 | 语言 | 原件 | 风险/待核验 |','| --- | --- | --- | --- | --- | --- |']
    for r in assets:
        lines.append(f'| {r["id"]} | {r["title"]} | {r["category"]} | {r["language"]} | [打开](../{quote(r["path"],safe="/")}) | {r["risk"]} |')
    lines+=['','## PDF页面','','| 编号 | 标题 | 页面 |','| --- | --- | --- |']
    for r in pages:
        lines.append(f'| {r["id"]} | {r["title"]} | [查看]({quote(r["preview"],safe="/")}) |')
    (ROOT/'素材库/素材索引.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    summary=['# PDF阅读摘要','','D001为华文，D002为英文；图像型PDF，文本层几乎为空。本文件是视觉阅读的标题级摘要，不是完整OCR。产品和冲突说明见[水光双语对照](水光双语对照.md)。','']
    summary += [f'- {r["id"]}：{r["title"]}。风险：{r["risk"]}。' for r in pages]
    (ROOT/'知识库/PDF阅读摘要.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')
    # 只有图像空文本的提取结果也保留说明，避免被误用为完整转写。
    for p in (ROOT/'知识库/PDF提取').glob('*.txt'):
        p.write_text('此PDF为图像型，文本层未能提供可用正文。此文件不代表内容为空，也不是完整OCR。\n请查看 ../PDF阅读摘要.md 及 ../../素材库/PDF页面/ 中的视觉原页。\n',encoding='utf-8')
    report={'original_files':len(originals),'original_images':len(assets),'pdf_files':len(set(r['path'] for r in pages)),'pdf_pages':len(pages),'text_files':1,'exact_duplicate_images':[{'id':r['id'],'duplicate_of':r['duplicate_of']} for r in assets if r['duplicate_of']],'sha256_copy_check':all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in originals),'html_cards':page.count('<article '),'browser_interaction':'未验证；仅静态检查','full_chat_history':'未采集','pdf_reading':'已视觉检查全部16页标题和主要主题，未做逐字OCR审校'}
    assert report['sha256_copy_check'] and len(originals)==63 and len(assets)==60 and len(pages)==16
    (ROOT/'整理校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    import re
    for file in list(ROOT.rglob('*.md'))+[ROOT/'素材库/素材预览.html']:
        content=file.read_text(encoding='utf-8')
        refs=re.findall(r'(?:href|src)="([^"]+)"',content) if file.suffix=='.html' else re.findall(r'\]\(([^)]+)\)',content)
        for ref in refs:
            if ref.startswith(('http:','https:','#','mailto:')):
                continue
            assert (file.parent/unquote(ref)).exists(), f'失效链接: {file.name} {ref}'
    report['local_links']='全部本地Markdown/HTML文件链接存在'
    (ROOT/'整理校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    import sys
    if '--build' in sys.argv:
        pdf_previews()
        build()
    else:
        prepare()
