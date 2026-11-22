# WorkBuddy 接入与故障处理

技能包含SKILL.md、scripts、references、assets及requirements.txt。上传ZIP根目录直接放SKILL.md，不额外包裹school-scheduling目录；所有子目录只含文件，不再嵌套，以满足当前平台的两级目录限制。包内不含虚拟环境、真实个人资料或运行结果。手动本地使用时，请解压到独立school-scheduling目录。具体导入入口以用户WorkBuddy版本为准，不能凭Codex的技能安装方式推断WorkBuddy一定支持。

## 本地运行

首次可先运行 `py -3.12 -X utf8 scripts/cli.py guide`，或直接运行scripts/run.ps1查看引导；即使尚未创建包内虚拟环境，引导也无需第三方依赖。按已有资料逐轮补问，每轮最多3项，详见[首次引导](onboarding.md)。宿主必须读取并展示建议；命令本身不会弹出对话框。

1. 解压到可读写目录，确认已安装Python 3.12 x64及Python Launcher。
2. 运行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1`。仅该进程使用Bypass，不修改系统执行策略；首次联网安装依赖到本技能目录.venv。
3. 运行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run.ps1 --version`，再按SKILL.md生成模板并求解。
4. 自定义虚拟环境可给setup.ps1传-EnvironmentPath；此时直接用该环境python.exe运行scripts/cli.py，run.ps1仍使用包内.venv。

相对输入/输出路径以调用时工作目录为准，建议WorkBuddy始终传绝对路径。依赖不安装到全局环境，不改默认Python。依赖安装失败保留日志，检查网络和Python版本后用同一命令重试，不删用户目录。

## 接入验收

当前上传解析器还要求SKILL.md的YAML frontmatter顶层包含version、display_name、display_name_en、description_zh和description_en；version不能仅放在metadata中。保留name和description供技能发现使用。package_release.py会检查这些字段和脚本版本一致性。此WorkBuddy发布格式含Codex通用检查器未接受的扩展字段，验收应区分目标宿主，不能用Codex检查通过替代WorkBuddy解析通过。

在用户明确要求安装时，使用目标WorkBuddy支持的本地技能导入方式，核实可发现、可触发、可运行Python、可读取用户指定输入、可返回可打开的Excel附件，以及超时/取消能否终止子进程。仅目录存在或ZIP生成不代表这一步已通过。

不自动覆盖用户现有技能、修改WorkBuddy数据库、改写技能缓存或发布到市场。若宿主没有脚本执行能力，提供本地运行命令；服务端接入另行设计。

## 状态与退出码

0为命令执行成功，2为输入/配置错误，3为已证明无解，4为限时无可行解，5为独立校验失败，1为运行异常。最终资格读JSON的ready_for_acceptance。临时UNKNOWN可增加预算重试，不能擅自删硬规则；MODEL_INVALID优先修复模型或规则。

任务产物不得随技能包上传。Excel公式需在用户实际Excel/WPS重算并核对独立统计，Python读写和公式结构检查仅为本地静态证据。
