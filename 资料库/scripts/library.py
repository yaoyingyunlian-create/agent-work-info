"""Portable library tools. Standard library only; no network or server required."""
from pathlib import Path, PurePosixPath
import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import sys
import zipfile
from urllib.parse import quote, unquote, urlsplit

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / '资料库'

def is_within(path, base):
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False

def read_rows():
    return json.loads((ROOT / '索引/文件清单.json').read_text(encoding='utf-8'))

def local_path(base, value, encoded=False):
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or '\\' in value:
        raise ValueError(f'必须为相对路径: {value}')
    path = (base / (unquote(parsed.path) if encoded else value)).resolve()
    if not is_within(path, PROJECT):
        raise ValueError(f'路径越界: {value}')
    return path

def write_manifest(rows):
    (ROOT / '索引/文件清单.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    with (ROOT / '索引/文件清单.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def render():
    rows = read_rows()
    annotations = json.loads((ROOT / '索引/素材标注.json').read_text(encoding='utf-8'))
    cards = []
    esc = html.escape
    for row in rows:
        row.update(annotations.get(row['sha256'], {'category': '待分类', 'description': '新增资料待人工检查', 'review': '未审阅'}))
        if row['duplicate_of']:
            continue
        path = quote('../' + row['path'], safe='/')
        preview = quote('../' + row['preview'], safe='/') if row['preview'] else ''
        media = f'<img loading="lazy" src="{preview}" alt="{esc(row["id"])} 预览">' if preview else ''
        details = f'{row["width"]} × {row["height"]}' if row['width'] else ''
        if row['duration']:
            details += f' · {row["duration"]} 秒'
        cards.append(f'<article data-kind="{row["kind"]}">{media}<h2>{row["id"]} · {row["kind"]}</h2><p>{esc(row["category"])}</p><p>{esc(row["description"])}</p><p>{esc(row["name"])}</p><p>{details}</p><small>{esc(row["review"])}</small><p><a href="{path}">打开原文件</a></p></article>')
    style = 'body{font:15px system-ui,sans-serif;background:#f5f3ee;color:#292522;margin:24px}header{background:#f5f3ee;padding:12px 0}input,select{padding:10px;max-width:100%;box-sizing:border-box}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,250px),1fr));gap:16px}article{background:white;padding:16px;border-radius:10px;overflow-wrap:anywhere}article[hidden]{display:none}img{width:100%;height:220px;object-fit:contain}h2{font-size:17px}a{color:#65462e}small{color:#5e5a54}'
    page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>璞慧素材库</title><style>' + style + '</style></head><body><header><a href="../../index.html">返回资料中心</a><h1>璞慧 · 素材库</h1><p>本地离线资料，完全重复文件合并展示。视频为抽样帧，功效及素材授权待核实。</p><label>搜索 <input id="q" type="search" placeholder="编号、名称、分类或内容"></label> <label>类型 <select id="k"><option value="">全部</option><option>图片</option><option>视频</option><option>文档</option><option>文字</option></select></label> <span id="count" role="status" aria-live="polite"></span></header><main>' + ''.join(cards) + '</main><script>const q=document.getElementById("q"),k=document.getElementById("k"),count=document.getElementById("count");function filter(){let n=0;document.querySelectorAll("article").forEach(a=>{a.hidden=!(a.textContent.toLowerCase().includes(q.value.trim().toLowerCase())&&(!k.value||a.dataset.kind===k.value));if(!a.hidden)n++});count.textContent=n+" 项"}q.addEventListener("input",filter);k.addEventListener("change",filter);filter()</script></body></html>'
    (ROOT / '素材库/index.html').write_text(page, encoding='utf-8')
    # Knowledge search embeds text, so file:// needs no fetch, backend or network.
    docs = []
    for file in sorted((ROOT / '知识库').glob('*.md')):
        text = file.read_text(encoding='utf-8')
        def link(match):
            label, target = match.groups()
            return f'<a href="{quote(target, safe="/")}">{esc(label)}</a>'
        body = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, esc(text))
        docs.append(f'<article><h2>{esc(file.stem)}</h2><pre>{body}</pre></article>')
    knowledge = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>璞慧知识库</title><style>' + style + 'main{display:block}article{margin:18px 0}pre{white-space:pre-wrap;font:inherit;line-height:1.7}</style></head><body><a href="../../index.html">返回资料中心</a><h1>知识库</h1><p>搜索覆盖已整理文字及可提取PDF正文；视频全文和图片文字尚未收录。</p><label>搜索文字 <input id="q" type="search"></label><main>' + ''.join(docs) + '</main><script>document.getElementById("q").addEventListener("input",e=>document.querySelectorAll("article").forEach(a=>a.hidden=!a.textContent.toLowerCase().includes(e.target.value.trim().toLowerCase())))</script></body></html>'
    (ROOT / '知识库/index.html').write_text(knowledge, encoding='utf-8')
    write_manifest(rows)
    print(f'已生成素材库与知识库：{len(cards)} 份独立资料')

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
    def handle_starttag(self, tag, attrs):
        self.targets.extend(v for k, v in attrs if k in ('src', 'href') and v)

def verify():
    rows = read_rows()
    errors = []
    ids = {r['id'] for r in rows}
    if len(ids) != len(rows):
        errors.append('重复素材ID')
    by_id = {r['id']: r for r in rows}
    indexed = set()
    for row in rows:
        try:
            file = local_path(ROOT, row['path'])
            indexed.add(file)
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != row['sha256']:
                errors.append(f'{row["id"]}: 原文件缺失或哈希不一致')
            if row['preview'] and not local_path(ROOT, row['preview']).is_file():
                errors.append(f'{row["id"]}: 预览缺失')
            other = by_id.get(row['duplicate_of'])
            if row['duplicate_of'] and (not other or other['sha256'] != row['sha256'] or other['duplicate_of']):
                errors.append(f'{row["id"]}: 重复关联异常')
        except ValueError as exc:
            errors.append(str(exc))
    actual = {p.resolve() for p in (ROOT / '原始资料').rglob('*') if p.is_file()}
    if actual != indexed:
        errors.append('原始目录与清单不一致，请重新建库')
    for file in PROJECT.rglob('*.html'):
        if any(x in file.relative_to(PROJECT).parts for x in ('.venv', 'dist', '.git', 'tmp')):
            continue
        parser = Links()
        parser.feed(file.read_text(encoding='utf-8'))
        for value in parser.targets:
            try:
                if not local_path(file.parent, value, encoded=True).is_file():
                    errors.append(f'{file.name}: 无效链接 {value}')
            except ValueError as exc:
                errors.append(str(exc))
    result = {'files': len(rows), 'unique': sum(not r['duplicate_of'] for r in rows), 'errors': errors, 'browser_verified': False}
    (ROOT / '索引/最终验证.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return not errors

def pack(output):
    if not verify():
        raise ValueError('校验失败，停止打包')
    output = Path(output).resolve()
    if is_within(output, ROOT):
        raise ValueError('压缩包不能位于资料库内')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids silently replacing a prior customer delivery.
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PROJECT.rglob('*')):
            rel = p.relative_to(PROJECT)
            if p.is_file() and not any(x in rel.parts for x in ('.git', '.venv', '__pycache__', 'dist', 'tmp')) and not p.name.startswith('.env') and p != output:
                z.write(p, Path('GloriaX') / rel)
    with zipfile.ZipFile(output) as z:
        if z.testzip():
            raise ValueError('压缩包完整性检查失败')
    print(f'迁移包已验证: {output}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('render')
    sub.add_parser('verify')
    package = sub.add_parser('package')
    package.add_argument('--output', default=str(PROJECT / 'dist/GloriaX-client.zip'))
    args = parser.parse_args()
    if args.command == 'render':
        render()
    elif args.command == 'verify':
        return 0 if verify() else 1
    else:
        pack(args.output)
    return 0

if __name__ == '__main__':
    sys.exit(main())
