# school-scheduling 1.0.3 验证摘要

验证日期：2026-11-03。开发环境：Windows、本机独立Python 3.12。

## 已完成

- SKILL.md加入首次使用对话流程：先读取资料，每轮最多3问，已知项不重复问；仅要模板直接执行。
- guide命令接受部分上下文，返回问题、分场景提醒及后续动作；CLI无参数默认引导。引导不依赖第三方库，不写全局memory。
- run.ps1在包内环境未创建时，允许通过Python Launcher运行引导。其他排课命令仍需setup.ps1准备依赖。
- 预检报告包含guidance，求解前写出guidance侧文件。提醒不改变排课硬约束或验收门槛。
- 发布school-scheduling-1.0.3.zip及SHA256 manifest，不含虚拟环境、真实师生资料和任务产物。

## 验证结果

- unittest全量30项通过，含新增引导5项和原排课流程25项；引导最终修改后再次运行5项通过。
- skill-creator quick_validate：Skill is valid。
- PowerShell run.ps1在无包内.venv时输出首轮3问，退出码0。
- ZIP完整性及每个文件与源码字节一致检查通过。
- 解压后Python -S禁用site-packages仍能运行无参数引导；中文路径上下文可读取；高中仅请求模板时不追加排课资料问题。
- 解压验证记录：.qa-school-scheduling/onboarding-1.0.3/verification.json。

## 未完成与风险点

- WorkBuddy加载技能后是否自动触发、自然表达及保存对话上下文未做宿主实测；脚本只输出建议，不会自行弹窗或读取聊天记录。
- 本批未重新运行真实22班长时间求解、目标Excel/WPS重算及联网安装。沿用此前范围说明，不能将本批引导验证作为真实学期排课验收。
- 重复询问的避免依赖宿主将对话及文件解析结果传入上下文；未读取的文件不能仅凭路径认定内容已确认。
