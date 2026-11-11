# T02-A：数据输入契约与 CPU 数据准备组件

状态：2026-11-10 19:39 已按用户授权实施并限定验收通过，见 [实施报告](T02A_DATA_PREPARATION.md)。
下文保留原实施提示词作为范围依据，不能将其重复交付视为新建一轮资产的授权；继续先核对台账。
依据：[ROADMAP.md](ROADMAP.md)、[当前状态](STATUS.md)、[范围决策 D14](DECISIONS.md)。
本轮实施只交付数据准备组件；网页上传与数据选择入口另列 T02-B，T02-A 通过不代表整个 T02 完成。

## 可复制提示词

```text
在 /root/TieSheAI 实施 T02-A：数据输入契约与 CPU 数据准备组件。
本项目只做《技术方案.md》V0.1 的平台开发，复用 ClearML，训练优先 Unsloth，评估用 OpenCompass。

先依次读 AGENTS.md、docs/STATUS.md、docs/HANDOFF.md、docs/DECISIONS.md、docs/ROADMAP.md，
检查根仓库和两个 Fork 的 Git 状态，保留全部已有改动。参考现有 CPU Agent 和 Smoke 实现。
完整 C3 仍未通过；只核对本任务依赖的数据上传/下载、Dataset、Task/Agent 接口。
已有未验证项照实保留；实际阻塞须记录，不顺带修复其他功能或扩大原生功能验收。

直接完成以下工作：
1. 固定最小数据契约：首版支持 UTF-8 对话 JSONL，每条含 messages，明确角色、内容及必要校验。
   先检查仓库有无可复用契约；没有则定义 v1。用少量明确标注的合成数据做功能测试。
   原始文档分块不能冒充带答案的训练样本；PDF/Word 解析、自动生成问答另轮接入。
2. 实现可复用的 CPU 数据准备组件及本地 CLI：格式校验、精确去重、固定种子划分训练/验证集。
   相同样本不得跨集合；有来源分组时按组划分。非法数据明确失败，不能静默丢弃后报成功。
   产出 train.jsonl、validation.jsonl、来源映射、统计报告和 manifest，记录契约版本、
   输入/输出 SHA256、参数、代码及环境版本。明确后续训练适配器的输入，不宣称已验证 Unsloth。
3. 用 ClearML SDK/现有 API 接入，参数引用输入 Dataset ID/版本；
   将日志、必要统计和报告记入 Task，把处理结果登记为可下载的输出 Dataset。
   不新建后台、数据库或调度器；优先复用已有依赖，不修改 Agent 环境。
4. 本提示词明确授权在唯一 TieSheAI-T02A-<时间戳> 项目树内创建必要的输入/输出 Dataset、
   SDK 承载 Task/隐藏项目及一个 CPU 数据处理 Task，上传测试数据和结果并完成必要状态更新。
   确认 rail-cpu 无现有排队/运行作业后，将本轮处理 Task 交给现有 CPU Agent 真实执行。
   若队列忙则报告阻塞，不干预旧任务。新对象记 ID 台账；续跑先查台账，避免重复创建。
   解决未 push 源码如何被 Agent 获取：可参考现有完整脚本快照方式，记录实际执行源码哈希，
   不能假定 GitHub 含本地改动；不把仅本地执行或直接改状态写成 Agent 验收通过。
5. 验证有效数据、非法 JSON/字段、空内容、重复样本、划分可重复和跨集合隔离。
   真实 Agent 作业须 completed，核对输入输出资产关系、记录数及下载字节/SHA256。
   在现有 Fork 18080 页面核对任务状态、日志和输出资产，并通过现有入口实际下载。
   页面未通过与 SDK 通过分开记录；合成测试不算公开数据的真实 Demo 闭环。
6. 新增 docs/T02A_DATA_PREPARATION.md，记录命令、退出码、Task/Dataset ID、结果和限制；
   原始证据放入已忽略的 infra/evidence/t02a/。更新 STATUS、HANDOFF，HANDOFF ≤100 行；
   确认契约决策时再更新 DECISIONS。明确 T02-A 与整个 T02 的完成状态。

边界：只实现并验收 T02-A；不改 Web/Server Fork，不部署或重启服务，不重配 Agent/队列，
不建 Pipeline、不启用 GPU、不训练或部署模型。保留原服务、历史数据及 C3-B 夹具。
不暂存、提交、push 或自动清理新增对象。不启动 T02-B/T03。
最终报告实际修改、测试及证据、资产 ID、未解决项，并说明下一轮网页上传/选择入口如何复用该组件。
```
