---
name: workbuddy-repeat-audit
version: "1.0.0"
display_name: 工具调用重复线索核对
display_name_en: Repeated Tool Call Review
description: 从脱敏 JSONL 调用导出统计同一会话相邻相同工具和参数的重复线索，显式排除已标注的轮询与重试。
description_zh: 从脱敏 JSONL 调用导出统计同一会话相邻相同工具和参数的重复线索，显式排除已标注的轮询与重试。
description_en: Review consecutive identical tool calls in sanitized JSONL exports, excluding explicitly marked polling and retries.
---

# 工具调用重复线索核对

用户需要排查 Agent 重复调用工具、反复读取或执行时使用。先确认要核查的脱敏调用导出。复用用户已有导出，每行包含 session、tool 两个非空字符串及 arguments JSON 值，可选 kind 为 call、poll 或 retry，默认 call。要求保留原有会话内调用顺序。

```text
python -X utf8 scripts/audit.py "脱敏JSONL绝对路径"
```

使用 Python 3.10+ 标准库，脚本路径相对于安装目录。报告 repeat_count、explicitly_exempt_count 及重复行号与指纹。JSON 对象键排序后比较，同会话内紧邻的相同工具与参数计重复；跨会话独立统计；poll 和 retry 显式豁免并中断该会话重复链。

将结果表述为需复核线索。结合用户提供的调用目的判断是否有业务必要性，允许有意重复。缺少调用费用、耗时或执行结果时标注这些证据缺口。将原始行号与导出对照，参数可能敏感，报告只展示指纹。数据行有误时给出行号，修正输入后重跑。英文请求以英文解读结果。
