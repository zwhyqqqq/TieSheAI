# T02-B：网页上传、数据准备与数据选择入口

状态：2026-11-11 限定验收通过，见 [实施与验收报告](T02B_WEB_DATA_ENTRY.md)。下文保留原任务要求。
前置依据：[T02-A 报告](T02A_DATA_PREPARATION.md)、[v1 契约](../schemas/conversation-v1.md)、
[ROADMAP.md](ROADMAP.md)。T02-A 原资产与证据保持，完整 C3 仍未通过。

## 可复制提示词

```text
在 /root/TieSheAI 直接实施 T02-B：网页上传、数据准备与数据选择入口。
本项目只做《技术方案.md》V0.1 的平台开发，沿用现有 ClearML Web Angular 架构、Server API/SDK 和 CPU Agent。

先读 docs/STATUS.md，再读 docs/HANDOFF.md、AGENTS.md、docs/DECISIONS.md、docs/ROADMAP.md、
docs/T02A_DATA_PREPARATION.md、schemas/conversation-v1.md；部署前另读 infra/README.md、
infra/DEPLOYMENT_RESULT.md、infra/web-fork/README.md。检查根仓库/两个 Fork 状态和子目录规则，保留全部已有改动。
T02-A 已限定通过；整个 T02 未完成，完整 C3 仍未通过。不要重跑 T02-A prepare/submit 创建资产。

交付一个真实网页流程：上传对话 JSONL → 登记输入 Dataset → 配置并提交 CPU 数据准备 →
查看运行状态/错误 → 查看并选择输出 Dataset，下载结果。用户正常操作不需要终端或手填资产 ID。

1. 在现有 Web Fork 增加必要入口和表单，沿用原生布局/组件；只支持 conversation-v1 JSONL。
   展示格式说明、上传限制及错误行号；seed 默认42，验证组比例默认0.25，说明比例按来源组计算。
   复用 prepare.py 的权威校验/去重/划分逻辑，前端校验用于反馈，不能另写一套不一致的数据处理算法。
   PDF/Word、自动问答、训练参数、品牌大改和整站重构不在本轮。
2. 优先复用现有认证 API/SDK。先核对原生上传、Dataset 和 Task 能力，记录实际采用的调用链后实现。
   若浏览器无法安全调用所需 Python SDK，可增加一个仅用于本流程的最薄服务端适配层；
   说明原生接口缺口，使用同源受认证入口、验证当前用户会话并保持资产访问权限。
   适配层只暴露固定的数据准备操作，不开放任意脚本/命令/宿主机路径，不把服务端 key/token 放到前端。
   不新增通用后台、数据库、调度器，不切换或重启官方 Server，不启动 Server Fork。
3. 把当前仅服务单轮合成测试的控制器改为可复用入口：接收实际上传文件、Dataset ID/版本和参数，
   每次操作独立记录请求 ID、输入哈希、处理 Task、输出 Dataset 和状态。
   不复用 infra/evidence/t02a/ledger.json，不固定旧项目、样例或 synthetic_fixture=True。
   运行台账放受忽略的 .local 目录，证据目录只存验收材料；处理好当前 Agent 脚本读取宿主机台账的依赖。
   双击、刷新和同一请求重试不得重复创建或入队；失败或创建结果不明须可识别，不盲目重建。
   必要重构保留 T02-A CLI/核心行为与单元测试；历史源码哈希保持历史事实，新版本另记快照哈希。
4. 输入/输出 Dataset 使用明确的 ID/版本，记录来源、参数、代码哈希和 manifest；
   通过现有 rail-cpu Agent 执行，队列/Worker 空闲时才提交，忙时页面提示，不干预旧任务。
   页面持续显示真实 Task 状态和错误，链接原生日志/Artifact/Dataset 页面。
   成功后展示唯一/重复数、训练/验证条数、Dataset ID/版本及 manifest 哈希；
   提供兼容的已完成输出 Dataset 列表和选择功能，至少可选择 T02-A 输出与本轮新输出，
   明确保存所选 ID/版本/manifest 哈希并在刷新后恢复；未完成/不兼容数据不可当作可训练数据。
   选择仅保存后续训练输入，不创建训练 Task。保留原生下载入口并提供清楚的结果访问路径。
5. 本提示词授权在唯一 TieSheAI-T02B-<时间戳> 项目树创建验收必要的 Dataset、SDK 隐藏项目/承载 Task、
   CPU 处理 Task 和上传文件；新增对象留台账，不删除或复用 T02-A/C3-B 资产。
   授权必要的 Web/组件适配代码、独立正式构建、新固定 release，并仅更新 Fork 18080。
   如确需上述最薄适配服务，允许在独立 Fork 部署范围启动，不发布公网端口，记录版本/依赖/配置及停止方式。
   保留旧 release 和部署配置快照，完成本轮回退/恢复验证；原六服务和 Agent 进程/配置保持。
6. 用真实浏览器在 18080 从文件选择开始完成整条流程，真实 Agent completed 后回读资产；
   不通过预先运行控制器、写死 Task ID 或伪造响应替代页面提交。
   下载 train/validation/manifest 或包含这些文件的归档，按成员核对字节/SHA256。
   验证非法 JSON/字段、空文件、超限、非法参数、重复提交/刷新、队列忙和未登录拒绝；
   失败路径不能误报成功。优先本地/隔离集成验证错误条件，不创建占位忙任务或停 Agent 制造失败。
   浏览器写入只放行本轮业务必须的已审阅接口和对象，继续阻断偏好/统计及第三方请求。
   重跑适用的 T02-A 核心测试、既有 Artifact 下载回归、构建和本轮页面测试；记录未覆盖的真实故障场景。
7. 新增 docs/T02B_WEB_DATA_ENTRY.md；证据放 infra/evidence/t02b/，记录实际命令/退出码、
   页面步骤、请求链、真实资产 ID、源码/发布版本、下载哈希、失败复验和限制。
   更新 STATUS/HANDOFF/ROADMAP，确认接口/部署决策时更新 DECISIONS；HANDOFF ≤100行。

本轮只做 T02-B，不进入 GPU、Unsloth训练、模型部署、OpenCompass、Pipeline或T03；
不改原鉴权/全局CORS，不清理历史数据/卷，不暂存、提交、push或自动清理新增对象。
限定验收通过不自动代表整个 T02 或完整 C3 通过；列出剩余门槛后停在本轮边界。
最终报告实际修改、测试证据、可访问入口、资产 ID、回退方式和未解决问题。
```
