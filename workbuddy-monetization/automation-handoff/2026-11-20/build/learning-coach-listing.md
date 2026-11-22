# 智能学习陪练：详情优化草稿

资产：os_52efb5f1213b6d5a；现有版本：1.0.1；现价：¥8 买断，保持。离线草稿，未修改平台。当前线上详情原文字段未核实；以下“原描述”仅来自本地 SKILL.md，不能直接当平台修改前快照。

本地原描述：为一至六年级孩子生成可打印的数学逻辑与解决问题练习，记录作答反馈，并提供自适应训练建议与学习周报。

## 建议填写：适用场景

给一至六年级孩子安排数学逻辑练习，家长不必每天重新凑题。输入年级，即可先生成一份无档案预览：5道题，分为基础2题、进阶2题、挑战1题，包含至少4类能力。输出可打印的双页HTML，题目页留有作答区，答案页附分步思路与常见误区；可通过浏览器打印为PDF。

需要持续记录时，由监护人同意建立昵称档案，再录入逐题对错、耗时与卡点，获得后续训练建议和学习周报。适合家长安排练习与复盘；不提供提分保证，不替代教师诊断，也不是全学科作业解答工具。

## 建议填写：首次交付示例

自建演示，非买家案例：对WorkBuddy说“给四年级生成一份数学逻辑练习，先不建档”。首次得到5道题的双页HTML：一页用于作答，一页用于核对思路。需要长期使用时，仅提供昵称、年级与训练目标，并确认监护人同意；练后按题号提供对错、耗时和卡点即可。实际练习以当前题库及脚本校验为准。

## Suggested field: Who it is for

Printable math logic and problem-solving practice for children in grades 1–6. Start with a grade-only preview: five questions, including two basic, two intermediate and one challenge question, spanning at least four ability categories. The two-page HTML includes a question sheet and an answer sheet with step-by-step reasoning and common mistakes. Print it to PDF from your browser.

With guardian consent, create a nickname-only profile, record answers, time spent and difficulties, and receive training suggestions and weekly summaries. Designed for parent-led practice and review. No score improvement guarantee; it does not replace teacher assessment or provide all-subject homework answers.

## Suggested field: Your first delivery

Synthetic demonstration, not a customer case: ask WorkBuddy, “Create a grade-four math logic practice sheet without a profile.” You receive a two-page HTML with five questions and a separate answer sheet. For ongoing records, provide a nickname, grade and training goal, confirm guardian consent, and later record per-question results, time spent and difficulties. Exercises remain subject to the available question bank and validation checks. The current exercise output is in Simplified Chinese; this English listing does not promise English exercises.

## 能力依据与验收

| 文案承诺 | 本地依据 | 验收口径 |
| --- | --- | --- |
| 一至六年级、无档案预览 | learning-coach/scripts/generate_practice.py 的 --grade 参数 | 年级参数1至6；本轮验证四年级演示，不外推六年级全部题库 |
| 5题、2/2/1难度、至少4类能力 | references/quality-rules.md；generate_practice.py | 检查生成器报告与HTML题号、答案及页数 |
| 昵称档案、监护人同意 | scripts/manage_profile.py；SKILL.md | 文案不索取真实姓名、学校、住址 |
| 反馈、训练建议、周报 | record_feedback.py、adaptive.py、weekly_report.py | 代码存在与使用说明已核对；本轮不宣称完整反馈闭环重测 |
| 浏览器打印PDF | 双页HTML及打印CSS约定 | 本轮不宣称真实打印或导出PDF已通过 |

经营基线（2026-11-20 12:14，北京时间）：后台7天标签下安装2、调用37、活跃32；累计可见账单2条另列。曝光、详情访问缺失，不计算转化率。线上文案尚未改动，观测窗口尚未开始；修改后再记录具体时间并采集新的同口径7天数据，期间新增账单另按事件时间统计。

交04：草稿可审阅，不是待发布版本；线上原字段与字段入口待核实，现有执行授权标记为false。无需新ZIP或封面，不新建资产、不改价。
