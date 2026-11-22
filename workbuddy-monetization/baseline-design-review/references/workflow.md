# 输入与运行契约

从技能根目录执行命令。Windows 下使用 `python -X utf8`。路径含空格时加引号。所有 JSON、TXT、MD 使用 UTF-8。脚本使用标准库。输出指定新文件名，避免覆盖已有结果。

## 配置

可复制 [配置模板](../assets/config-template.json)。目录相对于配置文件解析，待审与基准目录必须分离。基准目录中每个文件都须登记，额外文件、重复逻辑 ID 或同名候选都会中止。每项基准含 id、path、version、effective_date、sha256。id 表示稳定逻辑标识，例如设计说明、材料表基准或一份标准。基准清单以用户人工确认的版本和指纹为准，脚本只验证完整性和一致性。

待审每项含 id 和 path，id 即图号或说明文档标识。相对路径指向目录内文件。一个待审文件对应一个图号。PDF 多图应先逐图导出。记录原图页、版面和实体位置到 anchors 的键中。示例格式如下。

```json
{"anchors":{"P3/材料表/管材":"原文完整单元格内容","P3/右上角图签":"原文完整图签字段内容"}}
```

TXT 或 MD 以从 1 开始的原文件行号作为位置，如 L12。文本和证据须逐字一致，每段证据至少 8 个非空白字符。短字段建议使用带原始字段名的整段单元格文字作为锚点。

| 配置字段 | 含义 |
| --- | --- |
| baseline_confirmed | 用户确认后设为 true |
| review_date | 核对日期 YYYY-MM-DD |
| rules_version | 禁止提、依据及历史配置所用版本标识 |
| dimensions | 省略时使用六维 |
| suppressions | 用户确认的禁止提规则数组。可空 |
| standards | 用户确认的标准版本表。键为标准号及年号，须和候选写法一致 |
| history | 复核过的历史意见。可空 |

禁止提条目共有 id、kind、dimension、field、reason。equivalent 增加 values 数组，填入至少两个不同的非空**完整锚点文本**，两侧分别精确匹配才抑制。excluded_field 增加 locations 数组，填入该字段在待审文本的精确位置键。withdrawn 也须提供 locations，另加 basis，按标准号、年号和条款精确匹配。禁止提适用范围须由用户确认。候选须先通过两侧原文回源才可能抑制。

标准表可将旧版登记为 superseded 并注明 replaced_by，将用户已核实现行适用版本登记为 current。clauses 的键为纯条款号，值是锁定基准中的 id、location。没有可回源正文的条款进入待人工确认。包内演示版本均为虚构，本包没有默认现行标准库。

## 候选与覆盖

可复制 [候选模板](../assets/candidates-template.json)。snapshot 必须抄自当次 prepare。coverage 对每个图号和启用的维度各登记一项。state 为 reviewed 或 unavailable，note 必填。只有 reviewed 项可生成候选。reviewed 表示模型已对照过该维度，核对范围和判断仍需人工确认。

每个候选有稳定 id、sheet、location、dimension、field、problem、advice、severity、evidence。严重程度仅为高、中、低。baseline_ref 指向基准 id 和 location，baseline_quote 是其中逐字引文。basis 写为 `GB/T 00000-2026 第1.2条` 的形式，basis_quote 须逐字取自依据表所指条款锚点。位置、依据或引文无法取得时填写空字符串，交脚本分流。内容字段禁止使用占位语作为证据。

历史条目含 id、sheet、location、dimension、field、problem、basis、evidence、date、status。可用 `review --format json` 输出的 opinions 条目摘取对应字段，再由人工补日期与状态。只有 open、同图同位置同维度同字段同依据同证据的意见进入模糊匹配。匹配结果保留两轮原文和得分。keep_new 写入本轮候选 ID 即可跳过该次延续判定，其他闸仍然生效。

## 安装与试跑

将 ZIP 导入 WorkBuddy 的自定义技能入口。包根目录包含 SKILL.md。导入后可输入“使用对照校审（基准唯一版），先跑包内模拟样本”。也可将 ZIP 解压后在本机执行 demo.py。真实项目需要提供已经授权的项目文件、唯一基准和适用条款正文。
