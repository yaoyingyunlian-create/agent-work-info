"""整理 Star 来源文件，保留原件并生成可追溯的素材索引。需要 Pillow 与 ffmpeg/ffprobe。"""
from pathlib import Path
from PIL import Image, ImageOps
import csv
import hashlib
import html
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / '素材库'
ORIGINALS = ROOT / '原始资料' / 'Star来源'
SOURCE = Path(r'C:\Users\ZIQINGBO\Desktop\新建文件夹\star')


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    annotations = json.loads((ASSETS / '素材标注.json').read_text(encoding='utf-8'))
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    if SOURCE.is_dir():
        incoming = {p.name for p in SOURCE.iterdir() if p.is_file()}
        if incoming != set(annotations):
            raise ValueError('来源文件集合变化，请先更新素材标注，避免编号或描述错配')
        for name in annotations:
            source, target = SOURCE / name, ORIGINALS / name
            if target.exists():
                if digest(source) != digest(target):
                    raise ValueError(f'同名原件变化，停止覆盖：{name}')
            else:
                shutil.copy2(source, target)
    if {p.name for p in ORIGINALS.iterdir() if p.is_file()} != set(annotations):
        raise ValueError('原始资料与标注集合不一致')
    rows, seen = [], {}
    (ASSETS / '缩略图').mkdir(exist_ok=True)
    (ASSETS / '视频抽帧').mkdir(exist_ok=True)
    for name, note in annotations.items():
        p = ORIGINALS / name
        sha = digest(p)
        row = dict(note, filename=name, bytes=p.stat().st_size, sha256=sha,
                   path=p.relative_to(ROOT).as_posix(), source_id='SRC-002',
                   received_date='2026-11-26', authorization='待确认',
                   duplicate_of=seen.get(sha, ''), verification='图片可见内容核对' if note['type']=='I' else '10%/50%/90%三帧检查；未完整播放或转录')
        seen.setdefault(sha, row['id'])
        thumb = ASSETS / '缩略图' / (row['id'] + '.jpg')
        if row['type'] == 'I':
            with Image.open(p) as im:
                row.update(width=im.width, height=im.height)
                if not thumb.exists():
                    im=ImageOps.exif_transpose(im).convert('RGB')
                    im.thumbnail((600, 600))
                    im.save(thumb, quality=88)
        else:
            meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
            v=next(s for s in meta['streams'] if s['codec_type']=='video')
            row.update(width=v['width'], height=v['height'], duration=float(meta['format']['duration']),
                       audio=any(s['codec_type']=='audio' for s in meta['streams']))
            row['frames']=[]
            for j, fraction in enumerate((.1,.5,.9),1):
                frame=ASSETS/'视频抽帧'/f"{row['id']}-{j}.jpg"
                if not frame.exists():
                    subprocess.run(['ffmpeg','-v','error','-ss',str(row['duration']*fraction),'-i',str(p),'-frames:v','1','-vf','scale=600:-2','-y',str(frame)],check=True)
                row['frames'].append({'path':frame.relative_to(ROOT).as_posix(),'seconds':round(row['duration']*fraction,3)})
            if not thumb.exists():
                shutil.copy2(ASSETS/'视频抽帧'/f"{row['id']}-1.jpg",thumb)
            row['media_packet_sha256']=subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0','-c','copy','-f','hash','-hash','sha256','-']).decode('ascii').strip().split('=')[1]
        row['thumbnail']=thumb.relative_to(ROOT).as_posix()
        rows.append(row)
    packets={}
    for row in rows:
        key=row.get('media_packet_sha256')
        row['same_media_as']=packets.get(key,'') if key else ''
        if key:
            packets.setdefault(key,row['id'])
    write(ASSETS/'素材清单.json',json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    fields=['素材编号','分类','文件名','相对路径','文件类型','字节数','SHA256','内容描述','关联业务','语言','来源编号','接收日期','授权状态','使用范围','重复于','备注','宽','高','时长秒','音视频包相同于']
    with (ASSETS/'素材清单.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(fields)
        for r in rows:
            writer.writerow([r['id'],r['category'],r['filename'],r['path'],Path(r['filename']).suffix,r['bytes'],r['sha256'],r['description'],r['related'],r['language'],r['source_id'],r['received_date'],r['authorization'],'内部参考；对外使用待授权',r['duplicate_of'],r['verification'],r['width'],r['height'],r.get('duration',''),r['same_media_as']])
    e=html.escape
    cards=[]
    for r in rows:
        search=' '.join(str(r.get(k,'')) for k in ('id','category','filename','description','related','language'))
        frames=''
        if r['type']=='V':
            frames='<details><summary>三帧检查</summary>'+''.join(f'<a href="../{e(x["path"])}"><img loading="lazy" src="../{e(x["path"])}" alt="{r["id"]} {x["seconds"]}秒"></a>' for x in r['frames'])+'</details>'
        same=f'<p>音视频包与 {r["same_media_as"]} 相同，原文件 SHA-256 不同；保留两份。</p>' if r['same_media_as'] else ''
        cards.append(f'<article data-type="{r["type"]}" data-search="{e(search,quote=True)}"><a href="../{e(r["path"])}"><img loading="lazy" class="cover" src="../{e(r["thumbnail"])}" alt="{e(r["title"])}"></a><h2>{r["id"]} · {e(r["title"])}</h2><p>{e(r["category"])} · {r["width"]}×{r["height"]}'+(f' · {r["duration"]:.2f}秒' if r['type']=='V' else '')+f'</p><p>{e(r["description"])}</p><p class="muted">{e(r["verification"])} · 授权待确认</p>{same}<a href="../{e(r["path"])}">打开原件</a>{frames}</article>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Star 素材预览</title><style>body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#10151f;color:#eee}header{padding:28px;max-width:1500px;margin:auto}h1{margin:0;color:#ff8737}input,select{font:inherit;padding:10px;margin:6px 10px 6px 0;max-width:90%}input{width:480px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;padding:0 28px 28px;max-width:1500px;margin:auto}article{background:#1e2736;padding:16px;border-radius:12px}article[hidden]{display:none}h2{font-size:19px}a{color:#ffab71}.cover{width:100%;height:260px;object-fit:contain;background:#080c13}details img{max-width:100%;max-height:220px}.muted{color:#bdc7d5}</style><header><h1>STAR ARENA / STREAK 素材库</h1><p>2026-11-26 · 23 张图片 / 13 个视频 · 原始文件共 321,707,025 字节</p><p>方案与参考资料；不表示项目已落地或合作已签约。视频仅检查三帧，未完整播放或转录。所有素材对外使用授权待确认。</p><label for="q">搜索</label><input id="q" placeholder="编号、名称、分类、关键词"><label for="type">类型</label><select id="type"><option value="">全部</option><option value="I">图片</option><option value="V">视频</option></select><p id="count" aria-live="polite"></p></header><main>'''+''.join(cards)+'''</main><script>const q=document.querySelector('#q'),t=document.querySelector('#type'),cards=[...document.querySelectorAll('article')];function filter(){let n=0;cards.forEach(c=>{c.hidden=!(c.dataset.search.toLowerCase().includes(q.value.trim().toLowerCase())&&(!t.value||c.dataset.type===t.value));if(!c.hidden)n++});document.querySelector('#count').textContent=`显示 ${n} / ${cards.length} 项`}q.addEventListener('input',filter);t.addEventListener('change',filter);filter();</script></html>'''
    write(ASSETS/'素材预览.html',page)
    print(f'完成：{len(rows)} 份原件；{sum(r["bytes"] for r in rows):,} 字节；音视频包重复 {sum(bool(r["same_media_as"]) for r in rows)} 对。')


if __name__=='__main__':
    main()
