---
name: workbuddy-storage-audit
version: "1.0.1"
display_name: 工作空间膨胀体检
display_name_en: WorkspaceStorageAudit
description: 只读统计已授权的 WorkBuddy 工作空间，标记受保护资产、敏感文件名与失败轨迹。
description_zh: 只读统计已授权的 WorkBuddy 工作空间，标记受保护资产、敏感文件名与失败轨迹。
description_en: Audit an authorized WorkBuddy workspace for disk usage, protected assets, sensitive filenames, and failed traces.
---

# 工作空间膨胀体检

确认用户授权的 WorkBuddy 目录。使用 Python 3.10+ 执行 `python -X utf8 scripts/audit.py "目录完整路径"`，一次只扫描一个目录。拒绝系统目录和整个盘符。仅扫描用户指定的工作空间或 WorkBuddy 数据目录。

按 JSON 输出报告目录体积、受保护路径、待人工复核路径、失败轨迹和未扫描项。体积为文件逻辑大小，未包含跳过或不可读项。敏感文件仅按名称提醒。任何路径均不判定为可安全删除，不执行删除或迁移。未知目录以及达到数量上限的扫描结果均需人工复核。无法访问本机目录时报告真实错误。
