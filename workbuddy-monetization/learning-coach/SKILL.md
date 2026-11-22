---
name: learning-coach
version: 1.0.1
display_name: 智能学习陪练
display_name_en: Learning Coach
description: >-
  当用户需要为一至六年级孩子建立匿名学习档案、生成可打印的数学逻辑与解决问题练习、录入作答反馈、查看练习历史或生成学习周报时应使用本技能。
description_zh: >-
  为一至六年级孩子生成可打印的数学逻辑与解决问题练习，记录作答反馈，并提供自适应训练建议与学习周报。
description_en: >-
  Generates printable math logic and problem-solving practice for grades 1-6, records learning feedback, and provides adaptive training suggestions and weekly reports.
agent_created: true
---

# 智能学习陪练

先确认只保存孩子昵称，且监护人已同意建立档案；不得收集真实姓名、学校或住址。使用简体中文交付，不作提分、升学或智力提升承诺。

## 档案管理

新建或查看档案时运行：

```bash
python scripts/manage_profile.py add --nickname "小明" --grade 4 --term "上学期" --frequency daily --goal "逻辑思维" --guardian-consent yes
python scripts/manage_profile.py list
```

仅在 `guardian-consent` 为 `yes` 时继续生成练习。

## 生成练习

收到“生成今天练习”“导出练习 PDF/HTML”等请求时，先读取 [质量与交付规则](references/quality-rules.md)，再运行：

```bash
python scripts/generate_practice.py --profile "小明" --date 2026-10-27 --adaptive
```

如尚未建档，可使用 `--grade 4` 生成无档案预览；预览不应写入孩子历史。脚本输出 HTML 文件路径和选题摘要。交付前确认脚本报告全部校验通过；HTML 可由浏览器打印为 PDF。

## 录入反馈与自适应

收到逐题对错、不会、耗时或卡点时，先以题号 1 至 5 对齐对应练习，再运行：

```bash
python scripts/record_feedback.py --profile "小明" --practice PB-20261027-01 --results '["对","错","不会","对","错"]' --total-minutes 28 --blocker "列表整理" --note "第3题读题慢"
python scripts/adaptive.py --profile "小明"
```

后续生成时使用 `--adaptive`。当脚本给出调整说明时，向家长说明训练重点，不将建议表述为结果保证。详细权重规则见 [自适应规则](references/adaptive-rules.md)。

## 历史与周报

查看历史时运行 `python scripts/generate_practice.py --profile "小明" --history`。生成周报时运行：

```bash
python scripts/weekly_report.py --profile "小明" --week 2026-W44
```

周报只陈述完成情况、正确率、耗时、薄弱能力和下一周可执行训练建议。

## 数据与故障处理

默认运行数据写入技能包的 `data/`。通过 `LEARNING_COACH_DATA_DIR` 指向每个家庭独立的数据目录；不要在不同家庭间混用该目录。题库为包内静态数据，运行产生的档案、练习、反馈、台账和输出文件不应打包或上传。

若任一强制校验失败，不交付练习；说明失败原因，并请求调整日期、年级或补充题库，而不是绕过校验。
