# WorkBuddy 排课技能 1.0.0 验证摘要

日期：2026-11-03。交付范围：标准技能ZIP及完整源码，Windows Python 3.12首次联网安装。未自动安装到WorkBuddy，未发布市场。

## 已完成

- 技能入口、四类Excel模板及JSON样例、schema参考和规则目录。
- 周模板/日期模式、单双周、实际分钟冲突、教师/学生组/场地/设备、候选分配、配额与课程包。
- 分层目标、独立校验、版本与哈希、交换、锁定重排、停课及补课。
- Excel明细、组/教师/资源/学生视图、学校逐班周网格、公式统计和独立统计、草稿标记与导出保护。
- Python 3.12独立环境安装脚本、运行脚本、打包与基准脚本。运行依赖已按实际安装版本锁定，未改系统默认Python。

## 验证结果

- 最终ZIP解压副本：22项unittest全部通过。13种规则的求解目标与独立校验指标一致；覆盖版本、单位、走班交集、资源、通勤、缺额、停补课、锁定交换及超时等。
- 四场景均执行template/import/precheck/solve/validate/export六步CLI流程，均通过。
- 从ZIP解压目录使用setup.ps1创建另一套独立环境并安装锁定依赖，导入检查通过；run.ps1 --version返回1.0.0。
- 官方skill-creator quick_validate检查通过；开发环境pip check通过；源码语法、文档相对链接、UTF-8及ZIP排除项检查通过。
- 最终ZIP中的每个文件与源码逐字节核对一致，CRC检查通过。

| 样本 | 活动数 | 候选数 | 建模与求解秒 | 含校验导出总秒 | 状态 |
|---|---:|---:|---:|---:|---|
| primary | 6 | 120 | 0.031 | 0.094 | OPTIMAL |
| junior | 6 | 90 | 0.015 | 0.078 | OPTIMAL |
| senior | 5 | 100 | 0.031 | 0.093 | OPTIMAL |
| training | 5 | 944 | 9.813 | 9.875 | OPTIMAL |
| senior-22classes-synthetic | 990 | 990 | 0.562 | 5.375 | OPTIMAL |

以上时间来自本机单次运行，不是性能保证。进程累计峰值工作集约264.1MB。完整机器、依赖、哈希和指标见同目录benchmark JSON。

22班样本采用固定时间和合成教师，只验证990活动处理容量；不能代表真实学校自由排课、集备、体育大课和教师安排已验证。四类小样本也不能证明任意机构规模都可在120秒内完成。

## 未完成验证与风险点

- WorkBuddy实际加载、触发、附件返回、取消控制未验证；交付计划明确不自动安装，保持用户现有配置不变。
- Excel/WPS实际打开、打印效果和公式重算未验证；已验证文件可由openpyxl读取、公式结构及独立统计，不将写入公式当作已计算。
- 尚未做四类机构的真实业务试点。现有真实教师Excel只读取了工作表维度（1表、35行、24列），没有编造字段映射、名单、日历或场地补齐真实输入。
- 单任务最多731天、单实例最多20000候选、总候选最多150000。这些是拒绝超量输入的保护上限，不是已验证的规模。
- 首版不支持跨午夜、秒级时间、自动选课/分班或实时交通；课时scope与规则by的语义须按参考文档填写。
- 尚未核实的教师可用性、学生交集、资源或外部占用会阻止最终验收导出；可显式导出带标记草稿。

## 使用

解压ZIP，在school-scheduling目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 template --profile primary --output D:\排课任务\input.xlsx
```

profile可选primary/junior/senior/training。模板含脱敏示例，须替换为真实资料；后续命令见技能包SKILL.md。所有任务产物使用独立目录，不放回技能assets。

## 发布包校验

- 文件：school-scheduling-1.0.0.zip
- 文件数：32
- ZIP字节：116657
- SHA256：075201fded6131fa010924a7145b1a2a23bbd2fc07e951bbb38eaf8b8589c0e7
- 包内无虚拟环境、运行结果、真实教师或学生文件；PyYAML仅用于开发结构检查，非运行依赖。
