# 首次使用引导

由WorkBuddy读取SKILL.md后，在当前对话自然询问；脚本返回结构化建议，不会自己弹窗或读取聊天记录。宿主实际对话触发仍需在WorkBuddy验证。无需持久化“首次使用”标记：当前资料充分就执行，不足就补问。

## 命令

在技能目录运行 `py -3.12 -X utf8 scripts/cli.py guide`，或不带参数运行cli.py。此入口仅使用Python标准库，安装求解依赖之前即可使用。

`guide --input TASK/context.json --output TASK/guide.json` 接受部分上下文；未指定output时只输出JSON。路径使用用户指定任务目录，不覆盖原始文件。输出questions最多3项；remaining_question_keys提示后续缺口，不能一次全部发给用户。回答合并后重新调用，已知问题消失。

## 上下文字段

沿用标准输入的profile、mode、calendar、slots、demands、rules等字段，并支持这些引导专用字段：

| 字段 | 用途或取值 |
| --- | --- |
| goal | new新排 / check检查 / adjust调补课 / template模板 |
| materials | teacher_excel任课表 / schedule已有课表 / text文字规则 / none暂无 |
| source_files | 已提供文件路径列表；读取内容后再补充具体数据 |
| solution_path或assignments | 已有方案路径或安排数据 |
| change_request | 调整目标及需保留的安排 |
| preferences_confirmed | 已询问并确认特殊偏好，包括明确无特殊要求 |
| external_scope_confirmed | 已确认本次检查的外部占用范围 |

例如用户说“高中，先给模板”，上下文可直接是：

```json
{"profile":"senior","goal":"template","materials":"none"}
```

此时返回create_template，不要求先填完日期、教师和课程。用户说“培训机构，检查这张课表”，可用：

```json
{"profile":"training","goal":"check","source_files":["D:/任务/已有课表.xlsx"]}
```

先读取文件，提取实际作息、安排与课程；不能仅填source_files便假定已完成读取或校验。solution_path也只表示资料存在，后续仍需读取并独立校验。

## 提醒与执行边界

- 高中提醒同科同日最多2节及同半天相邻连堂；特殊情况显式配置。
- 小学、初中提醒不同作息、共享教师与场地；培训提醒课时单位、兼职时间与通勤。
- 示例数据必须替换；不编造空缺字段，不将草稿称为正式课表。
- 预检报告包含guidance，求解前生成solution.json.guidance.json；提醒不会改变求解规则或阻断用户已授权的有限范围试排。
- 缺少Python3.12时由宿主直接按SKILL.md进行中文引导，运行排课前再按setup.ps1说明准备环境。无需为问问题先安装第三方依赖。
