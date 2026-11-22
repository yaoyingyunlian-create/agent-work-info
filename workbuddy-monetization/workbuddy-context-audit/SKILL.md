---
name: workbuddy-context-audit
version: "1.0.0"
display_name: 定时任务上下文体检
display_name_en: ScheduledTaskContextAudit
description: 只读统计任务规范体量，提取可回源的约束清单，协助安排分阶段加载。
description_zh: 只读统计任务规范体量，提取可回源的约束清单，协助安排分阶段加载。
description_en: Audit the size of task instructions and extract source-linked rules for staged loading.
---

# 定时任务上下文体检

确认用户授权的专用规范目录，支持 UTF-8 Markdown 和纯文本。任务提示词可作为单独的文本文件放入该目录。运行 `python -X utf8 scripts/audit.py "规范目录"`，无需额外依赖。

输出逐文件字符数（含空白，CRLF 计为两个字符，不计 UTF-8 BOM）、全部规则锚点及可复制清单。清单按原文提取明确的规则条目和包含中英文约束词的行，合并完全相同的条目。超过 800 字则回退到按文件分阶段加载。始终对照原文确认遗漏、例外和适用阶段，尤其是表格或跨行规则。用户确认前保留原规范和任务配置。

对用户用中文或英文解释统计口径、跳过项和未验证项。字符数不直接等于 token，估算因子需由用户提供；节省积分须用同一任务的前后运行明细验证。只读执行，跳过链接，不改模型、定时任务或源文件。
