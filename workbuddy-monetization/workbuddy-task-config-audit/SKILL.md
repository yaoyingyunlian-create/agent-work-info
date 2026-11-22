---
name: workbuddy-task-config-audit
version: "1.0.0"
display_name: 定时任务运行条件核对
display_name_en: Scheduled Task Preconditions Check
description: 根据脱敏快照逐项比对定时任务预期与实际编码、工作目录、时区、数据就绪和缺值策略，输出差异与缺证项。
description_zh: 根据脱敏快照逐项比对定时任务预期与实际编码、工作目录、时区、数据就绪和缺值策略，输出差异与缺证项。
description_en: Compare expected and observed encoding, working directory, time zone, data readiness, and missing-value policy from a sanitized scheduler snapshot.
---

# 定时任务运行条件核对

用于手动正常、定时失败等场景的运行条件排查。先读取已有资料，只补问缺失的预期设置和实际运行快照。按用户提供的证据构造 UTF-8 JSON 对象，保存到本次任务的新文件。

支持五对字段。encoding 使用 expected_encoding / observed_encoding；working_directory 使用 expected_cwd / observed_cwd；timezone 使用 expected_local_time / observed_local_time；data_readiness 使用 data_ready_at / run_at；missing_value 使用 expected_missing_policy / observed_missing_policy。每个值均为字符串，日期时间须带时区偏移，例如 2026-11-22T13:00:00+08:00。

```text
python -X utf8 scripts/audit.py "快照JSON绝对路径"
```

需要 Python 3.10+，标准库即可。命令相对于技能安装目录。读取报告中 match、mismatch、unknown，分别说明对应证据和人工检查建议。缺字段和非法时间记 unknown。目录按字符串比较，等价写法可能产生差异；时区仅比较给定时刻的 UTC 偏移；数据就绪比较运行时间是否晚于或等于就绪时间。解释这些判定范围，避免扩大为完整配置正确性结论。

快照由用户提供或从已授权工具读取。本技能保持只读，报告包含目录与时间，分享前核对。英文请求以英文解释检查项与结果。读取失败报告真实错误。
