# 数据契约 1.0

## 1.0.2 质量策略与草稿状态

profile=senior时，JSON和Excel均默认quality_policy=senior-standard，在标准化阶段自动补齐同科日上限2节、同日同半天、间隔不超过15分钟的连堂硬规则。反复标准化不重复添加。规则可由无范围限制、语义等价的已有硬规则满足，不能用同名禁用规则绕过。

特殊高中配置须显式给quality_policy=custom及quality_policy_reason；其他场景默认custom，不套用高中标准。quality报告仍给出参考指标，但custom下不以高中指标拒绝交付。正式采用哪些规则须在排课前向使用者展示。

校验新增quality和draft_reason。quality按教学组、实际课程和日期合并统计，可发现把同科拆成多个需求后遗漏的重复课；gate_passed是独立质量门槛。valid、quality.gate_passed与ready_for_acceptance含义不同，三者必须一并读取。不能仅以valid=true称教学质量通过。

草稿文件按原因命名：硬约束失败、教学质量未通过、待补课、资料待补全，再附“草稿”。Excel版本说明和校验结果表同步显示，不再把所有未达完整验收的结果统称“未通过校验”。

四个完整可运行示例位于 `assets/profiles/primary.json`、`junior.json`、`senior.json`、`training.json`。对应Excel位于 `assets/templates/`。JSON和Excel导入后使用相同契约。

## 任务与时间

必填：`schema_version: "1.0"`、`profile`、`mode`、`calendar`、`slots`、`groups`、`demands`。`task_id`默认schedule，`timezone`默认Asia/Shanghai。日期为YYYY-MM-DD，时间HH:MM，星期0至6（周一为0）。内部整数分钟，区间左闭右开，首版不支持跨午夜课程。

mode为weekly_template时，以2000-01-03起的连续示意周代表calendar.week_types，默认["all"]。这些不是用户学期真实日期。mode为date_range时必须提供calendar.start_date/end_date；week_anchor须为周一，不提供则start_date必须为周一。首版每任务最多731天。

calendar.weekdays默认[0,1,2,3,4]；holidays为日期列表；exceptions为包含date、open及可选schedule_weekday/week_type的对象。例外优先于假期和正常星期，同日多个例外报错。week_types从week_anchor起轮换。

slots每项有id、start、end，可限定group_ids、weekdays、dates、week_types。half_day可为am/pm/evening，默认按开始时间划分am/pm。固定课位时长必须与活动匹配。flexible=true可在窗口内生成候选，step_minutes默认5，必须为正整数。required=false表示满排时该窗口不必填。

fill_policy为demand_only（默认）或full。full只适用于明确固定课位；午休和课间不建必填课位。每个教学组每个有效日的required课位须被唯一覆盖，空闲不等于自习。先将需要的自习建立独立教学需求，教师要求按机构输入提供。

## 人员、组和资源

teachers、students每项含id、name，可有availability、unavailability、rest_minutes、daily_sessions、daily_minutes、qualifications。相同人担任不同角色使用相同ID，名称应一致。availability未提供表示未知；提供[]表示完全不可用，不能混淆。窗口含start/end及可选dates/weekdays/week_types。

groups含id、name及student_ids或memberships。memberships记录student_id/from/to（含首尾日）；student_ids为始终有效成员。membership_complete=true表示完整名单；没有个人名单时用conflicts_confirmed=true确认组间冲突关系，另用exclusive_with声明互斥组。默认同组不可重叠；拆班应建互不相交子组，共用行政班名称不作为冲突依据。提供size用于未知名单时的场地人数检查。包内不推断未提供的成员交集。

resources含id、capacity（默认1，同时活动用量）、seats（可选人数上限）、campus_id（默认default）、features、availability、setup_minutes、cleanup_minutes。不同校区间travel_minutes[source][target]以分钟给出；缺少方向不视作零。online校区及同校区默认只需transition_minutes（默认0）。

external_occupancy每项含date/start/end，可含person_ids、group_ids、resource_ids、resource_usage、campus_id、source。人员必须已声明。资源外部占用的起止时间应已包含准备与清场时间。external_scope_confirmed=true表示机构确认已提供本次声明范围的所有既有占用，external_scope_note记录范围；不代表自动掌握教师在其他机构的课程。

## 教学需求

demands每项包含id、course_id、group_ids、duration_options（整数教学分钟，默认40）及quota。teacher_ids表示共同必需教师，eligible_teacher_ids表示另选一位；resource_ids为必需资源，eligible_resource_ids另选一个。两组字段可组合；一个合班活动用多个group_ids，共同教师或场地只占用一次。

quota.unit为sessions/minutes/units，value为正整数；units额外给minutes_per_unit。scope为week（默认，每个有教学日的自然周）、week_type（每种周型的整个范围）、range（整个排课范围）。minutes/units在单一课长时须可整除；多课长时必须明确session_count，总次数和总教学分钟同时满足。课程包只填写本次范围应排数量，未进入范围的剩余量由备注另列，不当作缺额。

需求可限定slot_ids、week_types、exclude_dates、availability/unavailability；required_qualification要求所有授课教师具有该资格；required_features要求所有所分配资源具有这些特征。resource_usage映射资源ID到正整数用量，默认1。确认无需资源时必须给resource_not_applicable_reason，否则场地覆盖不完整。

rotation仅允许按周型改变teacher_ids、course_id，课长与配额不变。不同课长的轮换应建不同week_types的需求。fixed包含session_index（默认1）和可选scope/date/weekday/slot_id/start/teacher_ids/resource_ids/campus_id。一个周期内实例ID为 `需求ID@周期#序号`，周期是周一日期、周型名或range。

locks包含session_id及要锁定的date/start/slot_id/teacher_ids/resource_ids等维度。支持只锁教师不锁时间。课程先后、同步、日上限等使用rules，见规则目录。调课的baseline_assignments用于最少改动，change_tier默认1。

## 调整JSON

必须提供baseline_solution_hash（当前solution_hash）、baseline_version（当前version_hash）和operations。

```json
{
  "baseline_solution_hash": "从当前方案读取",
  "baseline_version": "从当前方案读取version_hash",
  "operations": [
    {"action": "move", "session_id": "D1@2000-01-03#1", "date": "2000-01-04", "slot_id": "P2"}
  ]
}
```

动作：move；swap带两个session_ids；cancel带session_id和reason；makeup带已取消session_id/date及目标课位；lock带session_id及fields；replan触发保留锁定的重排。move只在原配额周期与日历内变更；明确replace_calendar=true/replace_fixed=true才允许单实例跨周期改期或替代固定时段，日期仍需属于任务已展开日历。指定日原本停课时应先显式修改日历例外，不能偷偷开放假期。

补课沿用原需求、教师资格和原配额归属，若目标周型不同则采用目标周型课程/教师。如要求沿用原周型授课，须拆分明确需求。跨日期范围补课需先扩大任务日期范围并核对基线。

调整结果写next.json、next.json.input.json、next.json.validation.json。后续命令必须使用新input。取消后仍待补课，报告不能验收通过。操作不修改原有效文件；失败输出只能作为草稿。version_hash纳入输入、修订号及父版本，防止“内容回到原样”时误用过期基线。

## 结果和覆盖

求解状态：OPTIMAL/FEASIBLE/INFEASIBLE/UNKNOWN/MODEL_INVALID；人工调整标记MANUAL。每层记录状态和目标值。schema或不支持规则报输入错误，不能误报无解。

校验输出valid、ready_for_acceptance、delivery_status、hard_violations、soft_violations、quota_deltas、rule_results、coverage及哈希。valid只证明已检查输入范围；最终导出要求ready_for_acceptance。缺资料可用--draft生成带明确标记的文件。

首版不自动迁移未知schema版本。旧weekly_periods可作为quota缺省来源，但必须包在1.0契约及统一对象结构中。任何旧版扁平表先人工或导入脚本映射，不能直接假定兼容。
