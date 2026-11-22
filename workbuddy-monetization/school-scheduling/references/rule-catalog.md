# 规则目录

所有启用规则均在求解器和独立校验器实现。未知type报错；enabled=false保留在摘要但不称已满足。固定、配额、人员冲突、可用性、资源容量、资格、日负荷、通勤、轮换及锁定属于内置硬检查。

每项规则有唯一id、type、level（默认hard）、enabled（默认true）；soft附tier（默认2，较小先优化）、weight（默认1）。硬规则无优先级互相覆盖。范围可用demand_ids、teacher_ids、group_ids、course_ids，多个条件取交集；列表内取并集。by决定聚合对象，默认demand，可选teacher/group。

| type | 参数 | 精确语义 |
|---|---|---|
| daily_limit | max；unit可为minutes，否则按次数 | 每对象每日超额量 |
| consecutive | max_break_minutes默认15 | 每对象每日按起止排序，相邻活动间隔超过阈值计1；不自动套用于所有学科 |
| same_half_day | 无 | 每对象每日占用半天种类数超过1的部分；am/pm/evening由作息声明 |
| synchronize | demand_ids；across_weeks默认false | 匹配实例序号且同配额周期的需求活动同日同起点；跨周模式要求同星期同起点，允许仅一个需求锁定各周同槽 |
| min_gap | minutes | 同对象任意两活动之间不足该间隔计1；跨日以实际分钟差判断 |
| precedence | 按先后顺序的两个demand_ids；minutes默认0 | 第一个需求的每个活动均在第二个需求所有活动之前，至少间隔指定分钟；不是逐次一一匹配 |
| daily_distribution | target | 每对象每配额周期覆盖天数不足target的部分 |
| workdays | target；通常by=teacher | 每对象每配额周期授课天数不足target的部分；不默认适用兼职 |
| ampm_balance | 通常by=teacher | 每对象每配额周期缺少上午/下午的种类数；仅晚间可用者不应启用 |
| no_all_bad | slot_ids或windows；通常by=teacher | 有活动且全部落于不利时段计1，无课或有中性课不计；tier=0用于公平底线 |
| tail_excess | slot_ids或windows；max默认1 | 每对象每配额周期不利活动次数超阈值的部分 |
| preferred_time | windows | 不完整落入任一偏好窗口的活动计1 |
| minimize_gaps | 通常by=teacher；max_break_minutes默认0 | 每对象每日相邻活动的空档分钟总和，仅累计超过阈值的间隔 |

聚合周期沿用需求scope。将不同scope的教学需求混用于教师周指标时，须先统一scope，否则报告分别统计，不能称为教师整个自然周指标。合班在by=group下每个组各统计，by=teacher下每位教师只计一次。

windows含start/end及可选dates/weekdays/week_types。preferred_time要求整个活动落入窗口；不利windows只要与活动有时间交集即视为不利。slot_ids与windows对不利规则采用并集。约束精度为分钟，不同课长的公平性建议先统一课长或使用daily_limit的分钟指标；tail_excess本版按活动次数，不能声称按分钟均衡。

分层求解逐层固定本层最优值；限时只取得可行值时也可固定继续，但整体不得标OPTIMAL。time-limit包含模型构建和各层求解；不能保证任何输入都能零全坏课。调整基线change_tier默认1，按时间、教师、场地三个维度的改动计数（日期和开始时间分别计），不自动外发通知。

高一学校的W_ALL_BAD=20不能直接解释为严格优先，需改用tier=0；其他参考权重放在同层内。人名与课程名不是规则类型，学校通过ID和作用域配置，不在通用算法写姓名分支。
