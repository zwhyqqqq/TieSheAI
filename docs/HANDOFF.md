# 跨 Codex / ChatGPT 对话精简交接

更新时间：2026-11-11 15:54（Asia/Hong_Kong）。目录 `/root/TieSheAI`。
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
| GitHub 项目源码 | 已发布至 [codex/tiesheai-t03](https://github.com/zwhyqqqq/TieSheAI/tree/codex/tiesheai-t03) |
| T03 真实训练 / T04–T08 | 未启动 |

## 最新项目源码保存

- 用户授权保存当前项目，根仓库分支 codex/tiesheai-t03，包含当前文档与独立Web完整补丁。见 [恢复说明](SOURCE_SNAPSHOT.md) 和 [清单](../configs/source-snapshot.json)。
- Web本地提交15afce31f2e035665ced9e61950d46423086b30e，GitHub上游只有读取权限，采用公开基点与补丁恢复。Server固定2ebdc43951b9432cc7fa528bbb3a7100fc6fe805。
- 凭据/忽略/文档检查、36项下载回归、独立克隆恢复2486文件及完整tree核验通过，最终退出0。命令与退出码在 infra/evidence/save-project-20261111/commands.jsonl。
- Web初次提交缺作者配置退出128，本次命令级配置后通过。远端SHA和最终核对结果见同目录result.json，阶段进度沿当前表。

## 当前使用入口核对

- 2026-11-11 15:19 七容器 healthy、两服务 active，18080 首页/数据页/API ping、8080 首页及8081根路径均200。`docker ps`、`systemctl is-active`、`hostname -I` 和 Python HTTP 检查退出0，证据 `infra/evidence/usage-review-20261111/runtime.json`。
- 用户电脑执行 `ssh -N -L 18080:127.0.0.1:18080 root@192.168.52.59` 后打开 `http://127.0.0.1:18080/`，登录后进入 `/data-preparation`。远程端到端及浏览器本轮未验，功能沿用历史验收。
- 本轮更新 STATUS/HANDOFF；文档、引用和范围检查 `python3 -B infra/evidence/usage-review-20261111/check.py` 与 `git diff --check` 最终退出0，证据同目录 `document-check.json`。首次检查受并发文档变化及行数限制失败，合并保留记录后复验。功能开发按对应阶段授权启动。

## 历史 GitHub 发布复核

- 15:20核对旧远端b2cdbef与本地一致，命令 `python3 -B infra/evidence/github-publication-review-20261111/check.py` 通过，退出0。更晚版本按上节快照核对。

## 本次 11 月计划核对

- 2026-11-11 15:15 直接读取附件《开发计划11月(1).md》核对，月度计划整体未完成，阶段状态沿用上表。
- 基础平台及 CPU Agent 已有功能验收；Compose 与本机部署已完成，目标云端部署和远程端到端待验。
- 前端数据准备入口已验，平台名称、Logo 及必要菜单整理尚无完整交付验收。Unsloth 适配器与 CPU 预检通过，独立 GPU 环境和真实微调待验。
- 修改STATUS/HANDOFF，文档检查 `python3 -B infra/evidence/november-review-20261111/check.py` 通过，退出0。运行测试沿用历史证据，目标云端、前端标识和GPU资源待落实。

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
- OASST1 Apache-2.0，revision `37d790373da332a4c8be24bd29ec1550e7f04c3f`。12来源树、24问答、25166 B，synthetic=false、seed42、验证组比例0.25，来源记录留证。
- 请求 `d92f50aa-6098-4060-890a-75c78e832067`，输入 Dataset `105c93c7072544a891b46aa1c2737f1c` v1.0.0，Task `2862b8f03f5e47d6bab99b233909b73a` 由真实 rail-cpu Agent完成，沿用T02-B项目与发布。
- **T03 输出 Dataset `65d2ce482a484ff0a7e2ef6f0f4dbe67` v1.0.0。**
- **Manifest SHA-256 `8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f`。**
- `train.jsonl` 18 条，SHA-256 `3852e6b04b80487e69bf7f286ac6edf6e607791c235828b47f14067047ae028f`。
- `validation.jsonl` 6 条，SHA-256 `53ad388ff76c8b9fcec8ede1e3e3ee0948c086ed9ff9f671eb83c4a65d2aa345`。
- 训练/验证9/3来源组，跨集精确重复和来源组交集均0。网页选择/恢复/下载通过，ZIP12325 B与SDK回读相同，五成员哈希通过。本地解包为 `infra/evidence/t02-public-data/downloaded/`，training-handoff.json在证据根目录。
- 修改、命令与退出码、历史页面错误、旧对象保护和新增对象台账详见公开数据报告及 `infra/evidence/t02-public-data/`，最终处理与交付检查通过。
- 以下 T02-B 结果为历史验收，当前选中版本以本节公开数据输出为准。

## 最近实施 T02-B

- 历史限定验收通过。[完整验收](T02B_WEB_DATA_ENTRY.md)与 [Fork 操作说明](../infra/web-fork/README.md)。
- 18080 运行 release `data-entry-20261111-v1`，Web 版本 `2.5.0-data-entry-f4670e27128c`；同源适配层以当前会话身份调用 SDK，私有 Unix socket 提供服务。
- 核心 8 项、下载边界 36 项、适配 7 项、主应用/Widgets、浏览器 11 步、SDK、保护检查和回退恢复通过，退出 0。
- 原验收对象、哈希和发布清单见上述报告及 `infra/evidence/t02b/`；当前训练输入沿用上节公开数据交接。

## 必要历史记录

- [T02-A 报告](T02A_DATA_PREPARATION.md) 记录 14 条输入去重后 12 条，训练 10、验证 2。
- T02-A 输入 `7aa679c269ea42bc9240676e332ed504`、Task `c0b6cd3261164c89b24c7cda38875bfa`、输出 `1073a6bcf81e406cbbe5d8dde0d7cd73`。
- [C3-B 报告](T01C3B_FIXTURES.md) 与 `infra/evidence/t01c3b/ledger.json` 记录旧项目、Dataset v1/v2、Draft Task 和 Model。
- [Artifact 修复报告](T01C_ARTIFACT_DOWNLOAD_FIX.md) 与旧 release 保留。官方 8080 和 Server 2.4.0 继续使用原六服务。
- 历史Web基点be71d50e，当前源码已存为15afce31本地提交和完整补丁。Server Fork HEAD为2ebdc43951b9432cc7fa528bbb3a7100fc6fe805。
- [本地检查点](VERSION_CHECKPOINT.md) 及原 STATUS 历史记录仍可查询，当前工作区以实际状态为准。
- 项目根仓库源码已发布。首个远端提交 `a695bbcefe42c6975fe19451d62e248ae8639404` 与本地源码提交 `9d40c37fac1b5c10480f37edb41d39d5b4106a21` 文件树相同。CLI 写入因缺少凭据退出 128，GitHub 集成发布成功。29 项回归与敏感信息扫描通过，退出 0。另更新 STATUS 与 HANDOFF，证据在 `infra/evidence/push-20261111/`。

## 遗留与启动条件

- 合成验收及公开对话 JSONL 流程均通过。其他输入形态、完整平台 Demo 和完整 C3 仍待完成。
- 跨用户 Worker 作业、完整 Fileserver ACL、外部客户端同时入队、真实网络故障对账和主机重启恢复待验。
- PDF/Word、问答生成、GPU 环境续验、真实训练、部署、评估和 Pipeline 依各阶段独立授权。当前停在真实训练启动前。
