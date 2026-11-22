---
name: workbuddy-migration-audit
version: "1.0.0"
display_name: 工作空间迁移文件核对
display_name_en: Workspace Migration File Check
description: 核对迁移前后两个授权目录的文件路径与 SHA256，列出缺失、新增、内容变化及未扫描项。
description_zh: 核对迁移前后两个授权目录的文件路径与 SHA256，列出缺失、新增、内容变化及未扫描项。
description_en: Compare file paths and SHA256 hashes in two authorized directories after migration. Report missing, extra, changed, and unreadable files.
---

# 工作空间迁移文件核对

用户迁移、备份或复制工作空间后，用本技能核对两个目录的普通文件内容。

先复用已有输入，确认源目录、目标目录及扫描授权。文件体积较大时说明逐文件读取计算哈希所需时间。Python 3.10+，标准库即可，脚本路径相对于安装目录。

```text
python -X utf8 scripts/compare.py "源目录绝对路径" "目标目录绝对路径"
```

按 JSON 报告解释缺失、目标多出、内容变化、两侧跳过项。match 表示本次可扫描文件路径与字节相同；different 表示存在明确差异；incomplete 表示存在跳过或读取错误，应先呈现缺口。链接和 Windows junction 会跳过。扫描过程中源文件仍可能变化，建议在复制结束后运行。输出中保留发现的明确差异。对缺失项给出人工补复制建议，变化项建议核对修改时间和业务版本。

文件权限、时间戳、空目录、软件可启动性与数据库一致性需要单独验收。本技能只读核对，修复复制需用户另行授权。报告包含路径，分享前核查敏感名称。

英文请求使用英文解释同一 JSON 字段。用户未提供目录或无法访问本机时，明确所缺输入或实际错误。
