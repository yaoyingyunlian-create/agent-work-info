# Ngel 运营助手

版本 0.1.3。Codex 技能插件，含初始化、脚本与复盘、双语客服与预约、规则与记忆四个入口。首次使用自动检查资料并分批询问，已回答内容保存后不重复询问，暂不能提供的项目可延期。随包附带 11 组待核验双语问答。不是已接通社交平台的 SaaS 服务，无内置平台 API、MCP 服务、后台调度或生产预约数据库。

## 安装

推荐解压 ngel-marketplace-0.1.3.zip 到独立目录，保留隐藏的 .agents 目录及 plugins 目录。使用当前 Codex CLI：

```powershell
codex plugin marketplace add 'D:\path\to\extracted-marketplace'
codex plugin add ngel-operations@ngel-local
```

命令路径换成实际解压根目录。安装后开启新聊天，调用 `$ngel-setup`；如客户端未刷新插件列表，重启客户端。此包没有公开发布。当前开发机已安装；其他接收人需要自行安装。插件包 ngel-operations-0.1.3.zip 则适合接收端支持插件 ZIP 导入的场景；此入口是否可用取决于客户端。

安装格式依据：https://developers.openai.com/plugins/build/plugins 。本机已使用 marketplace add、plugin add 完成安装，并通过 plugin list 检查 installed=true 和 enabled=true；新聊天中的技能自动选取仍需实际使用确认。

## 使用

网页操作使用 Ego Lite，定时触发由 Codex 负责。客户可直接复制 [客户使用提示词](references/customer-prompts.md)。

- `$ngel-setup` 初始化业务工作区并检查接入缺口。
- `$ngel-content` 分析提供的视频，生成五篇标准脚本及数据复盘。
- `$ngel-service` 起草回复，或在已授权且已接入的系统内发送及预约。
- `$ngel-governance` 核验知识、维护规则及业务记忆。

## 自动资料引导

`$ngel-setup` 自动运行 onboarding.py status，从十个必要字段中每批最多选择三个问题。可通过已授权连接器读取的资料先读取并确认，其他信息在聊天中询问。答案保存在用户业务工作区，模板默认值不算已确认。脚本不自动登录账号、不升级权限、不向老板或员工发送询问。

可用 `onboarding.py defer --workspace <目录> --field <字段ID>` 延后问题，后续不会反复追问；用 resume 恢复。已答字段不等于已完成外部接入，仍须核验连接、知识和业务规则。

手动初始化也可在插件根目录执行：

```powershell
python -X utf8 scripts/workspace.py init --workspace 'D:\ngel-workspace'
python -X utf8 scripts/workspace.py check --workspace 'D:\ngel-workspace'
```

本地脚本需要 Python 3.8+，无第三方依赖。init 不覆盖已有文件；check 的结构通过不代表已能上线，须查看 live_readiness_blockers。运行数据写入业务工作区，不写入插件安装目录；不将客户数据随插件分发。

## 当前运行边界

已包含技能指引、配置模板、双语来源、初始化及结构检查脚本。外部发送与预约写入默认关闭。每天 20:00 和每半小时的计划仅是配置模板，安装不会启用任务。需要确认时区、账号、渠道、员工和权威预约系统，并用实际宿主工具建立任务及验证回执。

业务记忆仅为本地文件结构和维护流程；不声称提供自动记忆服务、存储加密、并发锁或事务数据库。上线前核验平台政策、知识来源、数据保留和人工接管。不能只修改 enabled=true 就认定已上线。

## 0.1.2 校验改进

自动回复知识必须同时满足双语非空白、审核人、带时区审核日期和有效期；过期与未来审核条目不计入可用数量。时区输入验证后同步规则和计划模板，已启用计划要求先暂停；离线配置不改动宿主任务。

上线前执行 workspace.py check --strict，退出码 1 表示错误、2 表示缺少资料。普通 check 保留仅检查结构的兼容行为。configuration_ready 不代表 live_ready，外部账号仍需真实验证。
