from pathlib import Path
import json, hashlib, re, csv
from collections import Counter

root = Path(__file__).resolve().parent.parent
out = root / '整理成果'
rows = json.loads((out / '清单/原始文件清单.json').read_text(encoding='utf-8'))
for r in rows:
    p = root / r['原始路径']
    assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == r['sha256'], p
assert len(rows) == len(list((root / '知识库和素材库').iterdir())) == 16
assert len({r['id'] for r in rows}) == 16
for md in out.rglob('*.md'):
    for link in re.findall(r'\]\(([^)]+)\)', md.read_text(encoding='utf-8')):
        if link == '清单/验证记录.md' and not (out / link).exists():
            continue
        assert (md.parent / link).exists(), (md,link)
duplicates = [v for v in Counter(r['sha256'] for r in rows).values() if v > 1]
assert not duplicates
with (out / '清单/原始文件清单.csv').open(encoding='utf-8-sig', newline='') as f:
    assert len(list(csv.DictReader(f))) == 16
report = '''# 验证记录

日期：2026-11-20。

## 已完成

- 16份原始文件全部建档，编号唯一，路径存在。
- 逐件重新计算SHA-256，与整理时记录一致；原件未改动。
- 无字节完全相同的重复原件；多角度近似照片保留。
- CSV、JSON均包含16条记录；Markdown本地链接逐项检查通过。
- 图片总览3张已目视检查，9张照片均有对应预览。
- 3段视频元数据读取成功，各提取3帧并目视检查。
- 3份PDF封面已目视检查；射频PDF第2—17页另行渲染并目视阅读。
- 公司PDF50页、艾灸PDF8页已按页提取文本；射频PDF17页无文本层，已在清单明确标注。

## 未完成与风险

- 公司PDF未完成全部图像层OCR及逐页视觉核对；部分页文字抽取稀少。
- 射频PDF已摘录关键参数与功能，未形成完整逐字转写。
- 视频未连续审看、未音频转写；标签依据抽帧，不能用于完整内容结论。
- 品牌关系、资质、授权、价格有效期、医学与商务宣传未外部核验。
- PDF渲染工具报告若干缺失字体警告；已查阅射频页面主文本可读，未保证原始版式像素一致。

## 环境说明

系统默认Python缺少PDF解析库，在线安装因SSL连接失败未成功；随后使用本机Codex已附带的Python和pypdf完成提取，未新增项目依赖。
'''
(out / '清单/验证记录.md').write_text(report,encoding='utf-8')
print('PASS: 16 originals, hashes, unique IDs, no exact duplicates, local links, CSV/JSON')
