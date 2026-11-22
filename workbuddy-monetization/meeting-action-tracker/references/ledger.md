# 台账契约 v1

UTF-8 JSON，顶层 `schema_version: 1`、`source`（P001 等键对应逐字原文）、`tasks`（卡片数组）。ID 跨会议保持稳定。

每卡必填：`id`、`action`、`deliverable`、`acceptance`、`owner`、`due`、`dependency_state`、`depends_on`、`status`、`evidence`。未知 owner/deliverable/acceptance 用 null；due 未知用 null。dependency_state 为 unknown/none/explicit；depends_on 为已确认的本台账前置 ID 数组，未知不能假装 none。外部依赖另写 external_dependencies 并保留证据，未解除时仍不可执行。

due 示例：`{"raw":"11月9日","date":"2026-11-09","basis":"会议已明确2026年；日期按Asia/Shanghai解释"}`。不能安全换算则 date 为 null，raw 保留原话。status 取 proposed/open/in_progress/done/cancelled；提议未确认用 proposed。

evidence 为 `[{"paragraph":"P001","quote":"原文逐字片段","supports":["action","owner"]}]`。supports 可取 action/owner/due/deliverable/acceptance/dependency/status；每个非空字段均须有对应证据，dependency_state 非 unknown 时也须提供 dependency 证据。done/cancelled 必须有 status 证据。证据“存在”不等于语义“支持”，必须人工复核。

额外可保存 owner_confirmation、questions、conflicts、external_dependencies、changes。owner_confirmation 不得把原文指派直接写成已接受；conflicts 非空时不列可执行。changes 每项记录旧值、新值、本次证据与会议标识，不覆盖历史事实。
