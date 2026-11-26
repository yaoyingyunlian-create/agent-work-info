# -*- coding: utf-8 -*-
"""一次性追加批次导航，逐文件保存原字节备份及变更哈希。"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(__file__).resolve().parent
record=WORK/'入口变更清单.json'
assert not record.exists(),'入口已更新，停止覆盖'
def sha(b):return hashlib.sha256(b).hexdigest()
additions={
'README.md':'\n## 20261125新增批次（2026-11-26整理）\n\n新增39份原件：38图片＋1份54页PPT。已补头皮洗护视觉、粉之密产品、资质历史页、咨询表、培训与加盟方案。旧版报告保留原批次范围。\n\n[本批知识报告](知识库/20261125新增资料.md) · [素材预览](素材库/新增20261125/新增素材预览.html) · [素材清单](素材库/新增20261125/素材索引.md) · [具体差异](知识库/20261125待确认问题.md) · [整理记录](知识库/整理记录-2026-11-26.md)\n',
'知识库/README.md':'\n## 20261125新增资料（2026-11-26复核）\n\n[新增知识报告](20261125新增资料.md) · [粉之密54页产品与培训索引](粉之密产品与培训索引.md) · [本批具体问题](20261125待确认问题.md) · [整理记录](整理记录-2026-11-26.md) · [TXT报告](20261125新增资料.txt)\n\n38图片补充头皮精华50mL、洗发水300mL及组合主图/详情；54页PPT补充粉之密品牌、7类产品/设备、历史资质、服务价目、内部培训、案例与加盟政策。注意$1268/$1168两个合作版本、主图名称差异、历史HSA通知期限和护理页差异。\n\n本批已发现可编辑PPTX演示源文件，修正上方旧批次“未发现设计编辑工程文件”的范围说明：PSD/AI/Figma/剪辑工程仍未发现；PPT中的图片不自动等于分层设计工程。旧报告及统计维持2026-11-24快照。\n',
'素材库/README.md':'\n## 20261125新增素材（2026-11-26入库）\n\n[可搜索预览](新增20261125/新增素材预览.html) · [逐件索引](新增20261125/素材索引.md) · [CSV](新增20261125/素材目录.csv) · [JSON](新增20261125/素材目录.json) · [知识摘要](../知识库/20261125新增资料.md)\n\n39份原始来件：38图＋1份54页PPT；54渲染页、61嵌入资源另列为衍生，不重复计原件。新增PPTX为可编辑演示源文件；案例、咨询表与内部培训默认折叠。3张详情长图及分片分别保留。新批次使用N1125编号，不继承旧批次业务确认日期；原授权等缺项如实保留。\n',
'知识库/待确认问题清单.md':'\n## 20261125新增具体问题（2026-11-26）\n\n见[新增差异与缺项清单](20261125待确认问题.md)，NQ01–NQ11包括：精华主图错名、品牌与SKU映射、PPT拼写、官网Whitening与PPTBalancing差异、历史通知期限、$1268/$1168合作版本及币种、价目表范围、护理页差异、配方/案例链与授权、图片文字和设备参数缺项。既有材料确认继续有效，不重复要求整批确认。\n'
}
changes=[]
for name,addition in additions.items():
 p=ROOT/name;backup=WORK/'入口更新前'/Path(name+'.bin')
 before=backup.read_bytes() if backup.exists() else p.read_bytes()
 text=before.decode('utf-8-sig');assert '## 20261125新增' not in text
 backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_bytes(before)
 expected=(text.rstrip()+'\n'+addition).encode('utf-8')
 assert p.read_bytes() in (before,expected),'入口被外部修改，停止覆盖'
 after=(text.rstrip()+'\n'+addition).encode('utf-8');p.write_bytes(after)
 changes.append({'path':name,'before_sha256':sha(before),'after_sha256':sha(after),'backup_path':backup.relative_to(ROOT).as_posix(),'reason':'追加20261125导航与范围说明；不改旧报告正文'})
# 维护器的变更范围来自导入前实测基线，而不是当前哈希猜测。
baseline=json.loads((WORK/'导入前基线.json').read_text(encoding='utf-8'))
name='整理过程/资料治理/维护索引.py'
old=next(r for r in baseline if r['path']==name)
changes.append({'path':name,'before_sha256':old['sha256'],'after_sha256':sha((ROOT/name).read_bytes()),'reason':'支持PPTX及新增批次来源；独立确认范围；刷新复核日期；登记导航变更'})
record.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report=(ROOT/'知识库/20261125新增资料.md').read_text(encoding='utf-8')
(ROOT/'知识库/20261125新增资料.txt').write_bytes(('\ufeff'+report.replace('\n','\r\n')).encode('utf-8'))
print('入口更新4份；维护器变更登记1份；TXT已保存')
