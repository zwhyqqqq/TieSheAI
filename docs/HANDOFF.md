# 跨 Codex / ChatGPT 对话精简交接

更新时间：2026-11-11 14:51（Asia/Hong_Kong）。目录 `/root/TieSheAI`。
入口：[STATUS](STATUS.md)、[DECISIONS](DECISIONS.md)、[AGENTS](../AGENTS.md)、[ROADMAP](ROADMAP.md)。
范围为平台开发，覆盖网页上传、训练、部署、调用及评估。旧 T09 科研课题范围排除。

## 当前阶段

| 阶段 | 状态 |
|---|---|
| T00 / T01-A / B | 历史通过。本轮七容器、CPU Agent 和适配服务的运行身份核对通过 |
| T01-C1 / C2 | 历史构建、独立部署通过 |
| T01-C3-A / 下载修复 / C3-B 首轮 | 历史限定验收通过，旧报告保留失败和 N/A |
| 完整 C3 | 未通过，其他受限路径仍待授权验收 |
| T02-A | 合成 CPU 核心、Agent、Dataset、Fork 下载限定通过 |
| T02-B | 合成网页上传、CPU 处理、下载和选择限定通过 |
| T02 | 公开对话 JSONL 数据流程与训练输入交接通过，其他输入形态未验 |
| T03-A | 数据、资源诊断、CPU 模板检查通过；GPU 环境受阻，未完整通过 |
| T03 训练适配器 | 源码与 CPU 预检通过。真实 GPU 训练与产物登记待验 |
| T03 真实训练 / T04–T08 | 未启动 |

## 最近实施 T03 训练适配器

- 入口 `python -B -m integrations.training.train --preflight`。SDK、本地数据、Hub tokenizer 三路径预检通过。训练 18 / 验证 6，最长 331 / 302，512 上限无需截断。
- 可选 system、多轮、assistant 正文与 EOS、padding、数据哈希和 CUDA 门禁回归，两版 Transformers 各 14 项通过。CUDA 缺失退出 3，版本不符 2，超长 1。
- 新增 `integrations/training/{train,inputs,gpu}.py`、`tests/t03/test_training.py` 与 [验收报告](T03_TRAINING_ADAPTER.md)，更新 STATUS、HANDOFF、ROADMAP、DECISIONS。
- 预检、单测、API 签名、运行身份和交付检查最终退出 0。SDK 12 个只读 GET 均 200。跨 Python 导入产生的解析器缓存已按原包恢复，禁写复验通过。命令与证据见 `infra/evidence/t03-training-adapter/commands.jsonl`。
- 真实训练须先经授权续验 T03-A 的设备、驱动与依赖，再另行验证权重加载、优化更新、GPU Agent 和实际 Model 上传回读。

## 最近实施 T03-A 训练准备

- 本地交接和 ClearML SDK 强制回读封存版本一致，Manifest 与五成员 SHA-256 通过，固定训练 18 / 验证 6。数据身份和哈希见下节。
- VMware 来宾无 NVIDIA PCI 设备。当前 `nvidia-smi` 退出 9，内核历史及当前窗口均有 `No NVIDIA GPU found`。R470 已安装且有 DKMS 模块。12 vCPU，RAM 可用约 11 GiB，磁盘可用约 61 GiB。
- 固定候选 `Qwen/Qwen2.5-0.5B-Instruct` revision `7ae557604adf67be50417f59c2c2f167def9a775`，Apache-2.0。CPU 两版 Transformers 均通过 24 条模板与标签核验，最长 331 / 302 tokens，512 上限无截断。
- 候选单卡 16-bit LoRA，r=8，batch=1，梯度累积 3，1 epoch / 6 更新。独立 GPU 环境未创建，GPU 算术、精度、Unsloth 导入和模型加载待验。
- 新增 [训练准备验收](T03A_TRAINING_READINESS.md)，更新 STATUS、HANDOFF、ROADMAP、DECISIONS。
- `check_data.py local/sdk`、硬件诊断命令、`fetch_model.py` 最终、两次 `check_template.py`、`check_stack.py`、`snapshot.py before/after`、`check_delivery.py` 均退出 0。 `nvcc` 不存在（127）；首次小配置下载失败（curl 63，脚本 1）后复验通过。证据与完整命令见 `infra/evidence/t03a/commands.jsonl`。
- 由虚拟化管理员确认设备分配或提供 GPU 节点，驱动兼容后经明确授权续验。完整权重、GPU Agent 和真实训练另行授权。

## 最近 T02 公开数据与训练输入交接

- 历史通过。[验收报告](T02_PUBLIC_DATA_ACCEPTANCE.md) 与 [任务要求](T02_PUBLIC_DATA_TASK.md)。
- OASST1 Apache-2.0，revision `37d790373da332a4c8be24bd29ec1550e7f04c3f`，原始样本 ID/分组/许可均留证。
- 12 来源树、24 问答，输入 25166 B。网页 synthetic=false，seed=42、验证组比例 0.25。
- 请求 `d92f50aa-6098-4060-890a-75c78e832067`，沿用 T02-B 当前项目、账户及发布。
- 输入 Dataset `105c93c7072544a891b46aa1c2737f1c` v1.0.0。
- Task `2862b8f03f5e47d6bab99b233909b73a`，真实 rail-cpu Agent completed。
- **T03 输出 Dataset `65d2ce482a484ff0a7e2ef6f0f4dbe67` v1.0.0。**
- **Manifest SHA-256 `8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f`。**
- `train.jsonl` 18 条，SHA-256 `3852e6b04b80487e69bf7f286ac6edf6e607791c235828b47f14067047ae028f`。
- `validation.jsonl` 6 条，SHA-256 `53ad388ff76c8b9fcec8ede1e3e3ee0948c086ed9ff9f671eb83c4a65d2aa345`。
- 训练/验证 9/3 来源组，精确重复和来源组跨集交集均为 0，来源映射覆盖全部原始 ID。
- 网页选择、刷新恢复及实际下载完成。ZIP 12325 B，与 SDK 强制回读全字节相同，五成员哈希通过。
- 本地解包 `infra/evidence/t02-public-data/downloaded/`，机器交接 `training-handoff.json` 位于同一证据根目录。
- 新增公开数据验收报告，更新 STATUS/HANDOFF/ROADMAP，忽略证据目录保存来源、样本、脚本、截图、ZIP 和核验结果。
- convert.py 最终 0、浏览器 resume 6 步 0、verify.py resume 0、baseline.py before/after 0、protection.py 最终 0、delivery.py 0。
- commands.jsonl、job-verification.json、protection-result.json、delivery-result.json 均在 `infra/evidence/t02-public-data/`。
- 初轮转换和保护断言失败已修正。网页 new 8 步均完成后因历史 `le` 页面错误断言退出 1，原请求复验通过，错误保留。
- 本轮保护三仓库 HEAD/index、两个 Fork 工作区、服务/发布、旧对象/偏好与 20 份历史 Artifact。
- 仅新增本请求的 2 隐藏项目/3 Task。当前项目两父节点与 rail-cpu last_update 更新，详见报告。
- 以下 T02-B 结果为历史验收，当前选中版本以本节公开数据输出为准。

## 最近实施 T02-B

- 入口 [数据准备](http://127.0.0.1:18080/data-preparation)。[完整验收](T02B_WEB_DATA_ENTRY.md)。
- release `data-entry-20261111-v1`，Web 版本 `2.5.0-data-entry-f4670e27128c`，当前运行在 18080。
- 同源适配层校验 ClearML 会话并以同一身份调用 SDK，私有 Unix socket 提供服务。
  `tiesheai-web-data-entry.service` 使用既有 Python 环境，启停与回退命令见 [Fork README](../infra/web-fork/README.md)。
- JSONL 上限 1 MiB，seed 默认 42，验证组比例默认 0.25。校验与 CPU 核心复用 T02-A。
  台账在 `infra/.local/data-entry/`，以请求 ID 和用户记录，同请求重放沿用现有对象。
- 项目 `TieSheAI-T02B-20261111T003331Z`，请求 `a8679cf8-070f-4a71-bf3f-278f8d88cc15`。
- 输入 Dataset v1.0.0 `e33a0984bab14f53aeed3bef921bdac9`。
- 处理 Task `8cb1b683ccd24937a365a3ec03516e45`，真实 rail-cpu Agent completed。
- 输出 Dataset v1.0.0 `2d0c777b4e9d4ec9a5ac539ef3931eaa`。
- 8 条合成输入、7 条唯一数据、训练 6、验证 1。浏览器可选择 T02-A 输出与本轮输出，刷新后恢复版本和 Manifest 哈希。
- 浏览器下载 ZIP 2358 B，SHA-256 `48655cd2d4b8cff610561a12c0521d5688f9b3e3f2b74dbe0729568fb91baec1`。
  SDK 强制回读字节一致，ZIP 五成员和独立复算通过。
- 实际修改为 Web 入口、侧栏及三个组件文件，适配和 Worker 四脚本，systemd 单元、Fork 四个发布文件和 README，tests/t02b 四文件，验收及交接文档。详见报告。
- 核心 8 项、下载边界 36 项、适配 7 项、主应用/Widgets、真实浏览器 11 步、SDK 核验和保护检查均通过、退出 0。
- 回退 `artifact-download-20261110-v1` 后旧下载通过，恢复新版后请求、选择、原生 Dataset/任务产物链接通过。
- 历史 T02-B 保留原六服务容器和 Agent、旧 release、原资产与 13 份 Artifact，当时新增 4 项目节点、3 Task。
- 证据 `infra/evidence/t02b/` 下 commands.jsonl、full-browser.json、job-verification.json、protection-result.json、各次发布清单和浏览器记录。
- 恢复验证按当前台账读取已存在请求。故障结果不明时按请求和 ClearML 对象核对。

## 必要历史记录

- [T02-A 报告](T02A_DATA_PREPARATION.md) 记录 14 条输入去重后 12 条，训练 10、验证 2。
- T02-A 输入 `7aa679c269ea42bc9240676e332ed504`、Task `c0b6cd3261164c89b24c7cda38875bfa`、输出 `1073a6bcf81e406cbbe5d8dde0d7cd73`。
- [C3-B 报告](T01C3B_FIXTURES.md) 与 `infra/evidence/t01c3b/ledger.json` 记录旧项目、Dataset v1/v2、Draft Task 和 Model。
- [Artifact 修复报告](T01C_ARTIFACT_DOWNLOAD_FIX.md) 与旧 release 保留。官方 8080 和 Server 2.4.0 继续使用原六服务。
- Web HEAD `be71d50e7504eb00a2e09900fabbe8697ed23558` 有既有未提交修改，本轮核对工作区一致。Server Fork HEAD `2ebdc43951b9432cc7fa528bbb3a7100fc6fe805`。
- [本地检查点](VERSION_CHECKPOINT.md) 及原 STATUS 历史记录仍可查询，当前工作区以实际状态为准。

## 遗留与启动条件

- 合成验收及公开对话 JSONL 流程均通过。其他输入形态、完整平台 Demo 和完整 C3 仍待完成。
- 跨用户 Worker 作业、完整 Fileserver ACL、外部客户端同时入队、真实网络故障对账和主机重启恢复待验。
- PDF/Word、问答生成、GPU 环境续验、真实训练、部署、评估和 Pipeline 依各阶段独立授权。当前停在真实训练启动前。
