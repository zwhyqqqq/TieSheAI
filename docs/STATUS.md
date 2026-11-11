# 项目状态与跨对话交接

更新时间：2026-11-11 14:51（Asia/Hong_Kong，UTC+08:00）。
工作目录：`/root/TieSheAI`。协作规则见 [AGENTS.md](../AGENTS.md)，
技术决策与边界见 [DECISIONS.md](DECISIONS.md)，精简交接见 [HANDOFF.md](HANDOFF.md)。
平台开发目标、T01-C2 至 T08 计划及历史 T09 范围说明见 [ROADMAP.md](ROADMAP.md)。
每次阶段任务及其他任务结束（含失败/中断）同时更新 HANDOFF 与本文；
HANDOFF 不超过 100 行，保留最新阶段及必要历史摘要，原始日志只引用路径。

## 当前阶段

| 项目 | 状态 | 依据与范围 |
|---|---|---|
| T00：源码和环境审计 | 已完成 | 用户已确认；本次未发现独立 T00 审计报告，不补造审计细节或测试结果 |
| T01-A：ClearML 2.4.0 基础部署 | 已完成 | T01-C3-A 前后复核通过，6/6 running / healthy、RestartCount=0；容器 ID 和启动时间均未变化 |
| T01-B：ClearML CPU Agent 联调 | 已完成 | 原有真实 Task/Artifact 验收通过；T01-C3-A 前后 Agent active/running，PID/启动时间/重启次数、配置与 Python 环境未变化；本轮未重跑任务 |
| T01-C1：Web Fork 构建验证 | 已完成 | 主应用和 Widgets 构建、资源完整性通过；仅修复 Widgets assets 复制配置，见 [构建报告](T01C1_BUILD.md) |
| 独立本地版本检查点 | 已完成 | 三仓库提交与本地 bundle 源码恢复验收通过；本轮核对提交与记录关键哈希一致，未重新恢复；见 [说明](VERSION_CHECKPOINT.md) |
| T01-C2 | 已完成 | C2 历史 Fork v2 与下载修复均已验。当前 18080 运行 T02-B release，见 [部署报告](T01C2_DEPLOYMENT.md) 和 [T02-B 报告](T02B_WEB_DATA_ENTRY.md) |
| T01-C3-A | 只读检查与问题记录已完成 | 两站页面/API 矩阵完成；发现 Fork Artifact 下载差异，缺样本/受限项未验，见 [兼容性报告](T01C_COMPATIBILITY.md) |
| 独立 Artifact 下载修复 | 已通过 | 同源 /files 真实按钮下载/字节与哈希、独立正式构建及 C2 v2 回退恢复通过，见 [修复报告](T01C_ARTIFACT_DOWNLOAD_FIX.md) |
| T01-C3-B 首轮 | 限定夹具/关系/可用下载入口验收通过 | 两 Dataset 版本、Draft+OutputModel；GENERAL 仅 inline、文本预览/输入消费 N/A，见 [夹具报告](T01C3B_FIXTURES.md) |
| T01-C3 整体 | 完整 C3 未通过 | T02-A/B 只覆盖各自验收路径 |
| T02-A | 已通过（合成功能测试） | v1 契约/CPU 组件/真实 Agent/Dataset/18080下载通过，见 [报告](T02A_DATA_PREPARATION.md) |
| T02-B | 限定验收通过 | 网页上传/CPU/下载/选择与回退恢复通过，见 [T02-B 报告](T02B_WEB_DATA_ENTRY.md) |
| T02 公开数据与训练输入交接 | 已通过本轮对话 JSONL 流程 | 24 条 OASST1 原始问答经网页上传和真实 CPU 处理，训练 18 / 验证 6，选择恢复、下载和 SDK 核验通过，见 [报告](T02_PUBLIC_DATA_ACCEPTANCE.md) |
| 整个 T02 | 对话 JSONL 数据流程通过，其他输入形态未验 | 固定输出 Dataset 版本及 Manifest 哈希 |
| T03-A | 数据、资源诊断、CPU 模板检查通过；GPU 环境受阻，未完整通过 | [训练准备验收](T03A_TRAINING_READINESS.md) |
| T03 训练适配器 | 源码与 CPU 预检通过 | [适配器验收](T03_TRAINING_ADAPTER.md)，CUDA 训练与真实 Model 登记待验 |
| T03 真实训练 / T04–T08 | 未启动 | GPU 环境复验与真实训练分别按授权执行 |
| T09：历史科研/课题交付 | 当前范围排除，未启动 | 用户明确本项目只需平台开发；不作为平台 Demo 完成门槛 |
| GPU | 训练入口 CUDA 门禁实测退出 3 | T03-A 历史 `nvidia-smi` 退出 9，VMware 来宾无 NVIDIA PCI 设备 |
| ClearML Web / Server Fork 集成 | Web C2 基础独立部署通过；完整兼容未通过 | Web C3-A 已完成，Artifact 下载另已修复；其他缺样本/受限项及 Server Fork 运行仍未验 |

## 实际部署基线

部署结论及完整操作记录：[infra/DEPLOYMENT_RESULT.md](../infra/DEPLOYMENT_RESULT.md)。
原始证据时间：2026-11-09 20:56:05（Asia/Hong_Kong）；最新 C3-A 前后复核日期为
2026-11-10，六服务仍健康且身份/启动时间不变。下表保留官方六服务基线，
新独立 Fork 站点见 C2 任务记录；后续对话检查运行状态时应重新复核。

Compose 项目：`tiesheai-clearml`；Linux / amd64；六个服务：

| 服务 | 实际版本 | 验收结果 |
|---|---|---|
| apiserver / fileserver / webserver | `clearml/server:2.4.0` | 3/3 healthy，API 容器内版本 2.4.0 |
| mongo | `mongo:8.0.15` | healthy，ping ok=1 |
| redis | `redis:8.2.3` | healthy，PONG，AOF 已开启 |
| elasticsearch | `elasticsearch:8.19.9` | healthy，集群 green |

镜像版本和 digest 同时锁定于 [compose.yaml](../infra/compose.yaml)，完整 digest、
运行镜像 ID 与架构见 [images.lock.json](../infra/images.lock.json)。
Web `/version.json` 为 `2.4.0-722`；这是官方发行镜像自带的 Web。
本地 `clearml-web/package.json` 为 **Web 应用版本 2.5.0**（Angular 21 依赖），
`clearml-server/apiserver/version.py` 为 **Server 2.4.0**。上表为原六服务的官方 Web
基线；新独立 Fork 站点见下文 C2。

| 用途 | 本机地址 | 已验收行为 |
|---|---|---|
| Web | `http://127.0.0.1:8080/` | HTML、env.js 和引用的 JS 资源 HTTP 200 |
| API | `http://127.0.0.1:8008/debug.ping` | HTTP 200，meta.result_code=200 |
| Fileserver | `http://127.0.0.1:8081/` | HTTP 200，OK |
| Web 代理 | `http://127.0.0.1:8080/api/debug.ping`、`/files/` | HTTP 200，代理响应有效 |
| 受保护接口 | `http://127.0.0.1:8008/v2.35/server.info` | 匿名 HTTP 401；T01-B SDK 认证调用 HTTP 200，Task/Queue/Worker/事件 API 已通过 |

仅绑定回环地址；数据库端口未发布。远程访问需同时转发 8008 / 8080 / 8081，
操作见 [infra/README.md](../infra/README.md)，远程客户端端到端访问尚未验收。

持久化使用八个 `tiesheai-clearml_` 前缀命名卷，覆盖数据库、文件及日志；外部配置
位于 `infra/.local/clearml/config`、`infra/.local/clearml/web`，以只读方式挂载。
容器重建已复用卷，未执行删除卷或备份恢复。

既有主机配置（本次未修改）：

- `/etc/sysctl.d/99-tiesheai-clearml.conf`：`vm.max_map_count=1048576`。
- `/etc/systemd/system/docker.service.d/90-tiesheai-proxy.conf`：Docker daemon
  使用 `http://127.0.0.1:7890` 代理；拉取镜像依赖该代理可用。
- Docker 已记录为 enabled；真实主机重启后的服务恢复尚未验证。

## 验收证据与遗留问题

原始证据保留于本机 `infra/evidence/`，受 `infra/.gitignore` 排除：

- `acceptance.txt`：最终 `T01-A live acceptance: PASS`；覆盖六服务、镜像 ID、
  持久化挂载、HTTP/静态脚本/代理及数据库探测。
- `containers.txt`、`runtime.json`、`volumes.txt`：容器、端口、挂载及卷。
- `nginx-check.txt`：nginx 配置检查通过。
- `web-version.json`、`mongo-version.txt`、`redis-version.txt`、
  `elasticsearch-version.json`：实际服务版本。
- `recorded_at.txt`、`sysctl.txt`、`services.log` 及 `t01a-*.log`：时间、主机参数与部署过程。

已处理问题包括 Docker daemon 代理未生效导致拉取超时，以及 API / Fileserver
循环等待；当前依赖顺序为数据库 → API → Fileserver / Web。初版验收曾误判匿名
401；最终验收保留鉴权，并核对容器内版本。

T01-B 现已另行通过认证 SDK / Task / Queue / Worker / 事件 API，以及 CPU Agent /
Task / Artifact 上传下载验收，不将这些结果追溯计入 T01-A。
C2 已补验独立 Fork 基础浏览器登录与认证读取；尚未验证完整交互/业务兼容、
Fileserver 完整访问控制策略、Server Fork 集成、GPU、远程
SSH 转发端到端、跨主机环境重建、Agent/主机重启恢复、备份恢复及长期负载。

## T01-B 验收时运行状态

以下保留 T01-B 原有完整链路验收；T01-C1 只读复核了 Agent 进程、配置和环境，
确认未受构建影响，未重新执行 Smoke Task。

- 普通 Agent 3.0.3，SDK 2.1.12，Python 3.11.18；复用 `clearml-backend`，未安装包。
- systemd 服务 `tiesheai-clearml-cpu-agent` 保持 active/running，未启用开机自启。
  Worker `tiesheai-rail-cpu:cpu0` 仅监听 `rail-cpu`
  （Queue ID `9821226b7d1c4d57b4dae4418bd1f28b`）。
- 最终 Task `d13dc5bcdbc248f0bb80509eb66b9b36`，状态 completed；
  `cpu_smoke/check_passed=1.0`；Agent 从服务端取得完整脚本快照后执行。
- Artifact 上传前、强制下载后和固定 fixture 的 SHA256 均为
  `b00ed20e939a658612bc0586861bf1af2ece002c6b20bcfee5255194592555a9`。
- 凭据仅在 `infra/.local/agent/clearml.conf`（0600，父目录 0700），本地证据位于
  `infra/evidence/t01b/`，两者均已验证受 Git 忽略。原始日志不复制到交接文档。
- 操作说明：[CPU Agent](../infra/agent/README.md)；Task URL、Artifact URI、
  验收证据及失败记录：[T01-B 验收报告](T01B_ACCEPTANCE.md)。

## 任务交接记录

### 2026-11-11 14:51 T03 训练适配器与 CPU 预检通过

- **时间（Asia/Hong_Kong）** 2026-11-11 14:51。
- **任务 / 阶段及状态** 训练适配器源码与 CPU 预检通过。T03-A GPU 环境受阻，真实训练未启动。
- **本次结果与项目进度** 参数化入口绑定封存 Dataset v1.0.0、Manifest 和固定 Qwen revision。只读 SDK、本地缓存及 Hub 小文件下载的预检结果一致。训练 18 / 验证 6，最长 331 / 302 tokens，有效 labels 3026 / 978。每轮 assistant 正文和 EOS 监督，system/user、角色头和 padding 屏蔽。实现 Unsloth/LoRA、ClearML 日志与 adapter 包登记路径。
- **实际修改文件** 新增 `integrations/training/{train,inputs,gpu}.py`、`tests/t03/test_training.py` 和 [验收报告](T03_TRAINING_ADAPTER.md)。更新 STATUS、HANDOFF、ROADMAP、DECISIONS。证据保存于 Git 忽略的 `infra/evidence/t03-training-adapter/`。
- **测试命令、结果、退出码及证据** `python -B -m integrations.training.train --preflight` 的本地、SDK、Hub 路径最终各 0。SDK 12 个 GET 全部 200。两版 Transformers 的 `python -B -m unittest discover -s tests/t03 -v` 各 14 项、各 0。版本拒绝 2、超长拒绝 1、CUDA 门禁 3。API 签名、三仓库、七容器、两服务、交付检查均 0。SDK 验收曾遇到 ABI 不符和 PLY 自动缓存写入，解析器表已按原包恢复，禁写复验通过。实际命令、失败和修复记录见 `commands.jsonl` 与验收报告，交付检查见同目录 `delivery-result.json`。
- **遗留问题 / 未验证项** GPU 精度、Unsloth 实际加载、优化更新、显存峰值、Agent 运行及实际 Model 上传回读待验。未创建 ClearML 业务对象、未下载完整权重或运行训练。
- **下一步启动条件** 提供获配 GPU 的节点和兼容驱动并明确授权 T03-A 续验。GPU 门禁通过后另行授权真实训练与 ClearML 产物验收。

### 2026-11-11 14:31 复核 T03-A 阻塞并交付训练适配器提示词

- **时间（Asia/Hong_Kong）** 2026-11-11 14:31。
- **任务与状态** 本地证据复核与提示词交付完成。T03-A GPU 环境受阻，真实训练未启动。
- **结果** 核对已保存的数据SDK/本地记录、五数据文件、八个模型/tokenizer小文件哈希和模板统计，GPU阻塞沿用T03-A实测证据。下一轮建议在资源落实期间完成训练适配器和CPU预检，覆盖完整对话契约及labels。
- **修改** 新增 `docs/T03_ADAPTER_TASK.md`，更新 ROADMAP、STATUS、HANDOFF。
- **验证** 本轮内联Python证据核对退出0。`python3 -B infra/evidence/t03-adapter-prompt-20261111/check.py` 文档引用、范围、HANDOFF和三仓库差异检查通过，退出0。证据同目录 `t03a-review.json`、`result.json`，原状态 `before.json`。
- **遗留** GPU分配方式或可用节点待用户提供，当前模板脚本针对本轮单轮样例，多轮适配待开发。GPU运行和框架安装沿用原未验结论。
- **下一步启动条件** 用户交付 [训练适配器提示词](T03_ADAPTER_TASK.md) 后实施代码与CPU预检，获得GPU资源后再续验T03-A和真实训练。

### 2026-11-11 09:28 T03-A 训练准备部分通过，GPU 环境受阻

- **时间（Asia/Hong_Kong）** 2026-11-11 09:28。
- **任务 / 阶段及状态** T03-A 数据绑定、主机诊断、CPU 模板检查通过；独立训练环境受阻，未完整通过。真实训练未启动。
- **本次结果与项目进度** ClearML SDK 强制回读封存 Dataset `65d2ce482a484ff0a7e2ef6f0f4dbe67` v1.0.0，Manifest 与五成员哈希通过，训练 18 / 验证 6。固定候选 Qwen2.5-0.5B-Instruct 官方 revision `7ae557604adf67be50417f59c2c2f167def9a775`，两版 Transformers 的 CPU 模板验证结果一致，最长 331 / 302 tokens，512 上限无需截断。候选 16-bit LoRA 与独立环境草案见 [训练准备验收](T03A_TRAINING_READINESS.md)。
- **实际修改文件** 新增 `docs/T03A_TRAINING_READINESS.md`，更新 STATUS、HANDOFF、ROADMAP、DECISIONS，新增忽略证据 `infra/evidence/t03a/`。
- **测试命令、结果、退出码及证据** `check_data.py local/sdk`、`lspci -nnk`、`journalctl -k`、`fetch_model.py` 最终、两次 `check_template.py`、`check_stack.py`、`snapshot.py before/after` 与 `check_delivery.py` 均退出 0。 `nvidia-smi` 退出 9，`nvcc` 不存在（127）。首次配置下载 curl 63、脚本 1，调整传输上限后重试通过。完整命令和证据索引见 `infra/evidence/t03a/commands.jsonl`。
- **遗留问题 / 未验证项** VMware 来宾无 NVIDIA PCI 设备，内核报告 `No NVIDIA GPU found`；R470 亦低于候选 cu126 驱动要求。独立环境安装、PyTorch GPU 算术、BF16/FP16、Unsloth 导入和显存峰值待验。未下载模型权重或启动训练，三仓库、七容器、两服务保护核对通过。
- **下一步启动条件** 虚拟化管理员确认 GPU 分配或提供有 GPU 的节点，验证来宾设备和匹配驱动后经明确授权续验 T03-A。GPU Agent、完整权重和真实训练另行授权。

### 2026-11-11 09:17 复核数据交接并交付 T03-A 提示词

- **时间（Asia/Hong_Kong）** 2026-11-11 09:17。
- **任务与状态** 数据交接复核和提示词交付完成，T03 等待启动，公开对话 JSONL 数据流程验收通过。
- **结果** 核对固定 Dataset ID/版本、Manifest 及五个本地文件哈希，训练18条、验证6条、跨集精确样本交集为0。下一轮建议复核当前训练资源，硬件可用时验证独立环境，再固定模型 revision 与模板。
- **修改** 新增 `docs/T03A_TASK.md`，更新 ROADMAP、STATUS、HANDOFF。
- **验证** 内联 Python 数据哈希与划分核对退出0，结果 `infra/evidence/t03a-prompt-20261111/data-review.json`。同目录 `check.py` 检查文档、引用、范围、HANDOFF行数和三仓库差异通过，退出0，详见 `result.json`。本轮 GPU/运行验收沿用历史记录。
- **遗留** 当前训练资源、Unsloth环境和基座版本待实测。首次文档补丁因 ROADMAP 上下文未匹配而失败，按实际内容重新应用后通过核对。
- **下一步启动条件** 用户交付 [T03-A 提示词](T03A_TASK.md) 后执行资源和环境准备，真实训练另按准备结果安排。

### 2026-11-11 09:10 T02 公开数据验证与训练交接通过

- **时间（Asia/Hong_Kong）** 2026-11-11 09:10。
- **任务 / 阶段及状态** 本轮 T02 公开对话 JSONL 流程与训练输入交接通过，T03–T08 未开始，完整 C3 未通过。
- **本次结果与项目进度** 固定 OASST1 revision `37d790373da332a4c8be24bd29ec1550e7f04c3f` 及 Apache-2.0 许可。
  12 来源树取 24 问答，输入 25166 B。既有 Fork 新请求真实网页上传、synthetic=false、rail-cpu completed，
  输出训练 18 / 验证 6，9 / 3 来源组无交集。选择刷新恢复、实际 ZIP 下载与 SDK 全字节一致，五成员哈希通过。
- **交接资产** 请求 `d92f50aa-6098-4060-890a-75c78e832067`，输入 `105c93c7072544a891b46aa1c2737f1c`，
  Task `2862b8f03f5e47d6bab99b233909b73a`，输出 `65d2ce482a484ff0a7e2ef6f0f4dbe67` v1.0.0，
  Manifest `8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f`。train/validation 路径、条数及 SHA-256 见 [验收报告](T02_PUBLIC_DATA_ACCEPTANCE.md)。
- **实际修改文件** 新增 docs/T02_PUBLIC_DATA_ACCEPTANCE.md，更新 STATUS、HANDOFF、ROADMAP。
  忽略目录 infra/evidence/t02-public-data/ 保存来源/许可、取样清单、转换与核验脚本、截图、ZIP、解包成员及 training-handoff.json。
- **测试命令、结果、退出码及证据** convert.py 最终 0，browser.cjs new 的 8 步操作完成后错误断言退出 1，
  同请求 resume 6 步退出 0；verify.py resume、baseline.py before/after、protection.py 最终及 delivery.py 均 0。
  完整命令与退出码见同目录 commands.jsonl，结果 job-verification.json、protection-result.json、delivery-result.json。
  首轮转换缺审核字段与保护检查父项目时间戳断言各退出 1，修正并保留原证据。
- **保护与遗留问题 / 未验证项** 七容器身份、Agent/适配服务、当前 release、三仓库 HEAD/index、两个 Fork 工作区、
  旧对象/偏好与 20 份历史 Artifact 哈希核对通过。本轮新增 2 隐藏项目、3 Task。
  当前项目两父节点及队列 last_update 更新。历史页面 `le` 错误保留，跨用户/ACL/并发/故障/重启恢复和其他输入形态未验。
- **下一步启动条件（须用户明确授权，不自动执行）** T03 按本报告输出 ID、版本、Manifest 和 train/validation 哈希读取。
  训练环境、GPU、基座 revision、适配、部署/推理/评估另行安排，停在 T03 启动前。

### 2026-11-11 08:53 复核 T02-B 并交付公开数据验证提示词

- **时间（Asia/Hong_Kong）** 2026-11-11 08:53。
- **任务与状态** 本地证据复核和提示词交付完成。T02-B 限定通过，整个 T02 未完成，完整 C3 未通过。
- **结果** 核对三项资产 ID、11 步浏览器记录、保护检查，并重算保存的 ZIP 和五成员哈希。统计为 8 条输入、7 条唯一、训练 6 条、验证 1 条。复核基于既有证据。
- **修改** 新增 `docs/T02_PUBLIC_DATA_TASK.md`，更新 ROADMAP、STATUS 和 HANDOFF。
- **验证** `python3 -B infra/evidence/t02-public-data-prompt-20261111/check.py review` 和同脚本 `delivery` 最终通过，均退出 0。文档引用、改动范围、HANDOFF 行数及三仓库工作区与暂存区差异检查通过。证据为同目录 `t02b-review.json` 和 `result.json`。首次内联核对将步骤列表当成整数，退出 1，已修正。
- **遗留** 公开数据网页流程、训练输入交接以及 T02-B 报告列出的权限和故障条件待验。浏览器、SDK 和 Agent 的运行验收沿用原记录。
- **下一步启动条件** 用户交付提示词后，使用当前项目的新请求做公开数据验收。交接 Dataset 版本和 Manifest 哈希后再安排 T03。见 [提示词](T02_PUBLIC_DATA_TASK.md)。

### 2026-11-11 08:43 T02-B 网页数据准备限定验收通过

- **时间（Asia/Hong_Kong）** 2026-11-11 08:43。
- **任务 / 阶段及状态** T02-B 限定验收通过，18080 运行 `data-entry-20261111-v1`。整个 T02、完整 C3 及公开数据 Demo 尚待完成。
- **本次结果与项目进度** 「数据准备」完成 JSONL 上传、Dataset 登记、CPU 配置与提交、状态、错误、下载和选择。
  真正的 rail-cpu Agent 处理 8 条合成数据，得唯一 7 条、训练 6 条、验证 1 条。同一请求重试返回相同资产。
  输入 `e33a0984bab14f53aeed3bef921bdac9`、Task `8cb1b683ccd24937a365a3ec03516e45`、
  输出 `2d0c777b4e9d4ec9a5ac539ef3931eaa`，两份 Dataset 均为 v1.0.0。
- **实际修改文件** Web 的 data-preparation 组件三文件、app.routes.ts、侧栏模板。
  新增 integrations/data_entry 四脚本、infra/data-entry 的 systemd 单元、infra/web-fork 的四个发布文件、tests/t02b 四脚本和验收报告。
  更新 STATUS/HANDOFF/ROADMAP/DECISIONS/T02B_TASK 及 Fork README，完整清单见 [报告](T02B_WEB_DATA_ENTRY.md)。
- **测试命令、结果、退出码及证据** unittest 核心 8 项、下载边界 36 项、test_adapter.py 7 项、正式主应用及 Widgets、browser.cjs full 11 步、
  verify.py job/protection/delivery、旧版回退与新版恢复均为 0。实际命令及证据在 `infra/evidence/t02b/commands.jsonl`。
  ZIP 与 SDK 下载相同，五成员哈希通过。原六服务、Agent、13 份历史 Task Artifact、旧资产和三仓库 HEAD/index 前后核对通过。
- **遗留问题 / 未验证项** 跨用户 Worker 作业、完整 Fileserver ACL、真实故障对账、外部客户端并发入队及主机启动恢复待验。
  页面支持 1 MiB 内对话 JSONL 和已登记单 ZIP 输出。完整 C3 和公开数据 Demo 仍待验。
- **下一步启动条件（须用户明确授权）** 下一阶段由用户单独安排。运行入口、回退和恢复命令见 [T02-B 报告](T02B_WEB_DATA_ENTRY.md)。

### 2026-11-10 20:06：T02-B 实施中断（用户明确暂停）

- 时间（Asia/Hong_Kong）：2026-11-10 20:06。
- 任务 / 阶段及状态：T02-B 实施中，**用户要求暂停，未完成、未验收**；T02-A 历史限定通过，整个T02未完成，完整C3未通过。
- 本次结果与项目进度：读取任务/交接/部署约束，建立本轮Git/容器/Agent/资产/依赖只读基线；
  检查原生Dataset创建页面为CLI/SDK示例，已起草当前会话SDK隔离进程、Unix socket受认证适配、逐请求台账与
  无宿主机台账依赖的Agent包装器。上述为未验证实现，不作为已确认选型或可用功能。
- 实际修改文件：新增 integrations/data_entry/common.py、operations.py、server.py、worker.py，
  infra/data-entry/tiesheai-web-data-entry.service、tests/t02b/run.py；本次暂停补记STATUS/HANDOFF。
  未修改Web/Server Fork或现有部署配置；T02-A核心/CLI及旧台账未改。
- 测试命令、结果、退出码及证据：只读基线与库存采集退出0，证据 `infra/evidence/t02b/snapshot-before.json`、
  inventory-before.json、python-before.txt、compose-before.yaml、nginx-before.conf；
  `python3 -B tests/t02b/run.py syntax python3 -B -` 对4份适配源码ast.parse通过、退出0，见commands.jsonl/syntax.txt。
  尚未运行核心/权限/幂等/错误条件测试、浏览器上传/提交、真实Agent、构建、发布或回退恢复验收。
- 遗留问题 / 未验证项：当前代码草稿需完整审查和功能测试；Angular入口尚未编写，适配服务尚未安装/启动，
  .local运行台账尚未初始化；未创建本轮Dataset/Task、未入队或执行CPU作业，未重启服务/修改Agent配置。
  无暂存/提交/push。原C3、公开数据Demo/GPU/训练/远程/运维未验保持。
- 下一步启动条件（须用户明确授权，不自动执行）：用户明确说继续后恢复T02-B；先核对代码和基线是否有外部变化，
  继续实现网页/适配与测试，再按授权发布18080并做真实浏览器→Agent→产物/哈希及回退恢复验收。

### 2026-11-10 19:45：复核 T02-A 证据并交付 T02-B 提示词

- 时间（Asia/Hong_Kong）：2026-11-10 19:45。
- 任务 / 阶段及状态：本地证据复核与下一轮提示词交付完成；T02-A 限定通过，整个 T02 未完成，完整 C3 仍未通过。
- 本次结果与项目进度：核对 ledger 三资产 ID、当前组件/Agent 快照哈希、14→12→10/2 统计及四份通过记录；
  对已保存的三份真实浏览器下载重新算哈希、解包逐成员核对，通过。未重新运行 SDK/浏览器/Agent 或新建作业。
  T02-B 拟实现网页上传→登记→CPU处理→查看/选择结果；识别当前固定合成样例/台账及宿主机台账依赖，要求逐请求适配。
- 实际修改文件：新增 `docs/T02B_TASK.md`，更新 `docs/ROADMAP.md`、`docs/STATUS.md`、`docs/HANDOFF.md`。
- 测试命令、结果、退出码及证据：本轮内联 Python 证据复核退出0，结果 `infra/evidence/t02b-prompt-20261110/t02a-review.json`；
  `python3 -B infra/evidence/t02b-prompt-20261110/check.py` 文档/引用/范围/HANDOFF和三仓库差异检查最终通过、退出0，
  结果同目录 `result.json`，原状态 `before.json`；历史8组测试仅核对原日志，不冒称本轮重跑。
  首轮核对器将“不要重跑”断言为“不重跑”，退出1；修正字面断言后通过，原结果 `result-initial.json` 保留。
- 遗留问题 / 未验证项：网页入口/逐请求接入未开发；原生API是否需最薄适配层待实施验证，非已确认选型；
  公开数据Demo、训练/GPU、完整C3及既往未验项保持。所有源码、既有运行配置、历史证据和资产未改。
- 下一步启动条件（须用户明确授权，不自动执行）：用户交付 [T02-B 提示词](T02B_TASK.md) 后实施；
  仅按提示词范围安排 Fork 更新和新CPU作业，不自动进入T03或把T02/C3标记完成。

### 2026-11-10 19:39：T02-A 数据输入契约与 CPU 数据准备

- 时间（Asia/Hong_Kong）：2026-11-10 19:39。
- 任务 / 阶段及状态：**T02-A 限定范围通过；整个 T02 未完成，完整 C3 仍未通过**。T02-B/T03 未启动。
- 本次结果与项目进度：实现 conversation-v1 契约、CPU 严格校验/精确去重/来源连通组合并/固定种子划分，
  产出 train/validation、来源映射、统计/manifest；真实 rail-cpu Agent completed，参数/日志/指标/代码与文件哈希回读通过。
  合成输入14→唯一12（重复2），训练10/验证2；Fork 18080 任务/日志/参数/Dataset内容及3份真实下载通过。
- 资产台账：项目 `TieSheAI-T02A-20261110T112914Z`，4项目节点/3Task/0Model；输入 Dataset `7aa679c269ea42bc9240676e332ed504` v1.0.0，
  处理 Task `c0b6cd3261164c89b24c7cda38875bfa`，输出 Dataset `1073a6bcf81e406cbbe5d8dde0d7cd73` v1.0.0；
  全部 ID 与续跑保护见 `infra/evidence/t02a/ledger.json` 和 [完整报告](T02A_DATA_PREPARATION.md)。
- 实际修改文件：新增 integrations/data_preparation/ 两脚本、schemas/ 两契约、examples/t02a/ 两示例、
  tests/t02a/ 六文件、docs/T02A_DATA_PREPARATION.md；更新 STATUS/HANDOFF/DECISIONS/ROADMAP/T02A_TASK。
  保留旧改动，未改两个 Fork/部署/Agent/队列配置，无重启/训练/Pipeline/暂存/提交/push。
- 测试命令、结果、退出码及证据：`python3 -B -m unittest discover -s tests/t02a -p 'test_*.py' -v` 8组通过、0；
  prepare.py 本地 CLI、clearml_run.py prepare/submit/verify 与台账复用、node tests/t02a/browser.cjs fork-r4、
  check.py browser/preservation/delivery 最终均0；实际 argv/耗时/退出码见 `infra/evidence/t02a/commands.jsonl`。
  SDK五文件字节复现、浏览器16步/3份download及ZIP全成员校验通过；七容器/Agent/依赖/旧完整对象/C3-B文件/
  三仓库HEAD和index保持，Queue只因本轮作业更新last_update；结果 sdk-verification/browser-verification/
  preservation-result/delivery-result.json。browser r1/r2定位/弹层和初轮两次checker失败均留证据，最终已修正。
- 遗留问题 / 未验证项：合成数据不算公开Demo；网页上传/选择留T02-B；Unsloth/OpenCompass/训练未接入。
  JSON响应体旁路采集0B单列限制，真实manifest下载1235B核对通过；旧C3/GENERAL/权限/Server Fork/GPU/远程/运维未验保留。
  内存处理规模、语义去重、跨主机/中断恢复未验；完整命令/哈希/限制见报告。
- 下一步启动条件（须用户明确授权，不自动执行）：单独授权T02-B，复用本轮契约/CPU核心/Task快照、
  Dataset ID/版本/manifest/统计和既有Agent接入网页上传与数据选择；整个T02和后续阶段不自动标记完成。

### 2026-11-10：交付 T02-A 数据准备组件实施提示词

- 时间（Asia/Hong_Kong）：2026-11-10 17:37。
- 任务 / 阶段及状态：下一轮提示词已整理；完整 C3 仍未通过，T02–T08 尚未实施。
- 本次结果与项目进度：按平台开发范围将下一轮限定为输入契约、CPU 数据准备组件、
  真实 Agent 执行和 Dataset 回读；网页上传/选择入口留作 T02-B，T02-A 不替代整个 T02。
  既有 C3 问题按本任务依赖判断，不将未验证项改为通过；当前仅交付提示词，未创建作业或数据。
- 实际修改文件：新增 `docs/T02A_TASK.md`，更新 `docs/ROADMAP.md`、`docs/STATUS.md`、`docs/HANDOFF.md`。
- 测试命令、结果、退出码及证据：`python3 -B infra/evidence/t02a-prompt-20261110/check.py`
  文档/引用/任务边界、HANDOFF 行数、修改范围及三仓库工作区/暂存区差异检查通过、退出 0；
  原状态 `before.json`，结果 `result.json`，均在上述忽略目录；未复验浏览器/Agent/运行服务。
- 遗留问题 / 未验证项：组件、契约、网页上传/选择均未实现；GPU/训练及历史 C3 未验证事实保留。
- 下一步启动条件（须用户明确授权，不自动执行）：用户将 [T02-A 提示词](T02A_TASK.md) 交给实施对话；
  真实执行须先确认既有 CPU 队列空闲，后续 T02-B/T03 另行安排。

### 2026-11-10：平台五项功能与验收主线对齐

- 时间（Asia/Hong_Kong）：2026-11-10 17:31。
- 任务 / 阶段及状态：附件全文核对和规划调整已形成；仅澄清范围，不启动任何实施。
- 本次结果与项目进度：独立读取《技术方案.md》V0.1 全文（wc -l 为 181，逻辑行 182），补齐上传/训练/部署/调用/
  评估的开发内容和当前差距表。沿用此前 D14 排除 T09，并消除专家评分/模型效果提升门槛的歧义。
  C3 按五项流程必要依赖收口；GENERAL 修复转保留候选，最近主线建议数据入口/组件接入。
  历史完整 C3 未通过结论不变，未将范围调整冒充通过；《工作进度汇报》仍未提供。
- 实际修改文件：仅 `docs/ROADMAP.md`、`docs/DECISIONS.md`、`docs/STATUS.md`、`docs/HANDOFF.md`；
  保留此前 17:20 范围澄清及所有任务成果。附件只读，证据在忽略的 `infra/evidence/platform-plan-alignment/`。
- 测试命令、结果、退出码及证据：`python3 -B infra/evidence/platform-plan-alignment/check.py`
  最终通过、退出 0，核对附件哈希/五功能范围、引用/格式/凭据模式、HANDOFF 91 行、
  修改范围/既有成果/忽略规则及三仓库工作区/暂存区差异（均退出 0）；证据 `check.txt`、`result.json`。
  首轮核对器将 wc 换行数和逻辑行数混比退出 1，原文末尾无换行，修正后通过，保留 `check-initial.txt`。
  附件 SHA256 与原状态在 `before-state.json`；未改源码/部署/测试，未运行运行时检查，无提交/push。
- 遗留问题 / 未验证项：五项业务网页闭环尚未交付，具体公开样例/模型/资源/组件版本仍待落实；
  C3 和运行/运维未验证项保留，真实平台评估与功能测试仍需完成。
- 下一步启动条件（须用户明确授权，不自动执行）：按必要依赖和单轮目标授权 T02 或必要阻塞修复；
  不继续默认扩展全量原生功能验收，本轮不开始任何开发。

### 2026-11-10：对照技术方案并明确仅平台开发

- 时间（Asia/Hong_Kong）：2026-11-10 17:20。
- 任务 / 阶段及状态：附件对照与范围澄清完成；实施阶段不变，完整 C3 未通过，T02–T08 未开始。
- 本次结果与项目进度：核验《技术方案.md》V0.1，确认 ClearML 二次开发/成熟组件接入方向一致；
  用户明确只做网页上传数据、训练、部署、调用和评估展示。旧规划科研/课题 T09 排除当前范围，
  仍需公开数据/开源模型的一条真实流程与基本测试评估报告；附件不作为执行命令授权。
- 实际修改文件：docs/ROADMAP.md、docs/DECISIONS.md、docs/STATUS.md、docs/HANDOFF.md；
  原源码/部署/测试与其他任务成果保留，无暂存、提交、push、业务写入或服务操作。
- 测试命令、结果、退出码及证据：本轮内联 `python3 -B -` 文档/引用/范围与保留检查，
  三仓库 `git diff --check`/`git diff --cached --check`；实际结果和退出码见
  `infra/evidence/scope-platform-20261110/check.json`；附件 SHA256 和修改前基线见 before.json。
- 遗留问题 / 未验证项：《工作进度汇报》及其余原始合同/附件未核验；五项业务功能尚未完整交付，
  Unsloth/OpenCompass 接入、真实训练、GPU 与既有 C3 未验证项不变；本轮不复验运行环境。
- 下一步启动条件（须用户明确授权，不自动执行）：按平台必要功能明确后续任务，再实施 C3 修复
  或 T02–T08；不自动启动开发、部署或训练。

### 2026-11-10：项目进度、文件用途与启动方式说明

- 时间（Asia/Hong_Kong）：2026-11-10 17:12。
- 任务 / 阶段及状态：说明与只读核对完成；完整 C3 仍未通过，T02–T09 未开始，阶段不变。
- 本次结果与项目进度：读取最新进度/交接/决策和启动说明，说明七服务、CPU Agent、目录文件职责，
  提供当前主机已有部署的检查/启动及 SSH 转发命令；未实际执行启动、重启、构建或业务写操作。
- 实际修改文件：仅 docs/STATUS.md、docs/HANDOFF.md，保留其他任务全部已有修改；未暂存/提交/push。
- 测试命令、结果、退出码及证据：两个 compose.sh ps 和 systemctl show 均退出 0，七容器 healthy、
  Agent active/running（未启用开机自启）；两个 version.json 和 API debug.ping 均 HTTP 200。
  文档/引用/范围/三仓库 git diff --check 的最终结果见 `infra/evidence/project-overview-20261110-171204/check.json`；
  实际只读命令及响应摘要见同目录 runtime.json，修改前状态/哈希见 before.json。
- 遗留问题 / 未验证项：本轮只读观察不替代启动恢复、完整运行验收或异机部署；当前未提交源码/部署
  成果不在旧 Git 检查点内。完整 C3、GPU、训练和原有未验证项不变。
- 下一步启动条件（须用户明确授权，不自动执行）：Model 下载修复及其他 C3/T02 工作另行授权。

### 2026-11-10：核对 C3-B 首轮并交付 Model 下载入口修复提示词

- 时间（Asia/Hong_Kong）：2026-11-10 17:12。
- 任务 / 阶段及状态：首轮报告/证据核对完成，下一轮提示词已整理；不实施修复，完整 C3 仍未通过。
- 本次结果与项目进度：首轮 PASS/完整 C3 false、台账精确 ID、11 个报告/脚本哈希及六份浏览器
  下载文件字节/SHA256 一致，两站各记录 24 步。本轮未重跑 SDK/浏览器/运行验收。
  GENERAL 和模型菜单源码明确为下载入口，但仅导航签名 URL；两站 inline 是共有行为限制，
  不能直接认定 Server 不兼容。建议复用现有 Model/Task 最小修复，不重复创建夹具。
- 实际修改文件：仅 `docs/ROADMAP.md`、`docs/STATUS.md`、`docs/HANDOFF.md`；
  C3-B 及并发月度核对的全部成果保留。证据 `infra/evidence/c3b-next-prompt/` 保持忽略。
- 测试命令、结果、退出码及证据：证据核对内联 `python3 -B -` 首次因核对器对整数 steps
  调用 len() 退出 1，按真实结构改为计数核对后退出 0；见 `review.json`、基线 `before-state.json`。
  `python3 -B infra/evidence/c3b-next-prompt/check.py` 通过、退出 0：引用/格式/凭据模式、
  阶段/范围、HANDOFF 87 行、忽略/既有成果与 Git 保留检查通过；三仓库工作区/暂存区
  差异检查均退出 0，证据 `check.txt`、`result.json`。不改业务源码/部署或创建对象，不提交/push。
- 遗留问题 / 未验证项：GENERAL/菜单下载未修；Dataset 预览、输入 Model 消费、Pipeline、
  四风险端点、分享/角色/完整文件策略、外部存储和 Server Fork/GPU/运维仍未验。
- 下一步启动条件（须用户明确授权，不自动执行）：用户交付 Model 下载最小修复提示词，
  只授权必要 Web 修改/测试/构建/新 release/仅 Fork 切换及回退；复用现有台账，不造对象。
  通过后再明确 Pipeline 草稿及无 Agent 监听专用队列的范围，最终整理 C3 收口清单，不自动进入 T02。

### 2026-11-10 17:04：再次核对 11 月计划完成情况

- 时间（Asia/Hong_Kong）：2026-11-10 17:04。
- 任务 / 阶段及状态：计划对照核查完成；11 月计划整体未完成，阶段进度保持不变。
- 本次结果与项目进度：直接读取用户附件《开发计划11月(1).md》，仅作计划对照，不作为实施授权。
  相较 11 月 9 日旧核对，C2 独立部署、下载修复与 C3-B 首轮已取得新证据，不沿用旧记录的“Fork 未部署”。

| 11 月交付 | 当前结论 | 已有证据及剩余缺口 |
|---|---|---|
| ClearML 基础平台（必须） | 核心部署及部分基础功能已验收 | 六服务、认证 API、浏览器基础登录/读取、Dataset 两版本/关系/下载和 Model 链接已通过；完整 C3 与受限功能仍未通过，不从夹具外推全面兼容 |
| 容器化部署环境（必须） | 配置与本机部署已完成，目标环境待验 | 锁定镜像、Compose、持久化及部署说明已有；目标云端部署、远程端到端及跨主机重建尚未验收 |
| 前端基础适配（必须） | 未完成 | Web Fork 已构建和独立部署、Artifact 下载已修复；平台名称、Logo、必要菜单适配仍无交付验收 |
| 任务执行环境（必须） | 已完成（CPU 基础任务范围） | T01-B Agent 实际执行 Smoke，参数、状态、日志、指标及 Artifact 上传下载通过；不包含真实训练 |
| Unsloth 初步接入（争取） | 未开始 / 未验收 | 无独立训练环境、训练适配及真实微调证据；GPU 既往驱动检查失败，本次未复验 |

- 实际修改文件：仅 docs/STATUS.md、docs/HANDOFF.md；核对证据位于忽略目录 infra/evidence/november-review-20261110/。
- 测试命令、结果、退出码及证据：python3 -B infra/evidence/november-review-20261110/check.py，
  文档结论/相对路径/HANDOFF 行数/修改范围与原改动保留检查、三仓库 git diff --check 通过，退出 0；见 result.json。
  本次读取历史验收报告，未重跑服务、浏览器、Agent、构建、GPU 或训练测试；不补造运行验收。
- 遗留问题 / 未验证项：必做交付尚未全部验收，Unsloth 为争取项；截至 11 月 10 日不能认定月底延期。
  核对时 ROADMAP 尚未同步首轮结论；后续已由规划任务更新，当前以最新 ROADMAP/STATUS 和夹具报告为准。
- 下一步启动条件（须用户明确授权，不自动执行）：按月度缺口单独安排；前端明确名称/Logo/入口，
  目标部署明确云端环境，训练明确 GPU、模型和数据；不自动进入任何实施阶段。

### 2026-11-10 16:59：C3-B 首轮 Dataset / Model 受控夹具与页面验证

- 时间（Asia/Hong_Kong）：2026-11-10 16:59。
- 任务 / 阶段及状态：本轮实施/采证完成，限定夹具、版本/父关系、双向链接和可用下载入口验收通过；完整 C3 仍未通过。
- 本次结果与项目进度：唯一命名空间 `T01-C3B-Fixture-20261110T084159Z-f57ac4d6`，3 个新项目节点、2 个 Dataset data_processing Task
  正常 started→completed、1 个 created testing Task、1 个测试 OutputModel；所有新增 ID/必要附属资产见 ledger 与夹具报告。
  两站独立 context 从真实列表进入详情，各 24 步、3 份真实下载；v1 197 B、v2 193 B ZIP，Model 118 B，
  字节/hash 和解包合成文本一致；v2 继承 v1，Model↔Task 真链接 ID 一致。SDK state/文件材料化另单列。
  Model GENERAL 按钮仅 inline JSON、零下载；Dataset CONTENT 按钮仅 CLI 命令，文本内联预览无样本，未冒充通过。
- 实际修改文件：新增 docs/T01C3B_FIXTURES.md、tests/c3b 的 8 个脚本/契约/README；兼容报告追加矩阵，
  更新 STATUS/HANDOFF/DECISIONS。所有原改动保留；无源码/部署/鉴权/旧业务变更，无重启/清理/暂存/提交/push。
- 测试命令、结果、退出码及证据：source infra/agent/env.sh 后 fixtures.py prepare/create/verify/assets/history/compare 均 0；
  node tests/c3b/browser.cjs 18080 r7、8080 r6 均 0；check.py browser/preservation/delivery 最终均 0，
  原 infra/verify.py 前后 0/0、pip freeze 一致；七容器身份/启动/重启/挂载/端口/网络/健康、Agent、
  2483 Web/323 Server 源码、两份各 1502 文件 release、原完整对象/Artifact/偏好/队列和 Git HEAD/index 保持。
  证据 infra/evidence/t01c3b/commands.jsonl、ledger.json、sdk-verification.json、ancillary-assets.json、
  browser-results.json、accept-18080-r7-*、accept-8080-r6-*、preservation-result.json、delivery-result.json。
  首次脚本语法、定位器/SVG 判定、初轮 debug_images 保护及重复错误观察导致退出 1，原证据保留，修正采证器后通过。
- 遗留问题 / 未验证项：Artifact PREVIEW 的 116 B 是 SDK 中间 ZIP 大小，非原文件；CONTENT/归档头 71/80 B 正确。
  失败续跑防护未做真实故障注入。GENERAL 直按钮不下载、文本内联预览和输入模型消费 N/A；官方 Dataset fetch CORS
  失败后真实回退下载成功，Fork 可选 404 保留。新增 debug_images 只读契约限两 Dataset ID；偏好/统计/第三方
  仍阻断，最终错误逐项关联、无未知通配忽略。Pipeline、四风险端点、分享/完整文件/角色权限及其他受限项仍另验。
- 下一步启动条件（须用户明确授权，不自动执行）：沿用现有台账复验；任何新对象、功能修复、清理、其他 C3/T02
  工作均须另授权，不自动进入后续阶段。完整结论见 [夹具报告](T01C3B_FIXTURES.md)。

### 2026-11-10：按约定延时复核下载修复并交付 C3-B 提示词

- 时间（Asia/Hong_Kong）：2026-11-10 13:34；目标 13:24，实际首次复核时钟为 13:24:31。
- 任务 / 阶段及状态：按用户明确选择，仅复核下载修复并提供 C3-B 提示词；未实施 C3-B，
  完整 C3 仍未通过。通过当前会话等待约定时间，无后台自动化、系统定时器或新聊天创建。
- 本次结果与项目进度：源码审阅未发现必须先返修的阻塞；委派执行现有 Node 测试，
  36 项通过。当前 2483 源文件、1502 新 release、1502 C2 v2 文件与记录清单一致；
  两份真实下载各 122 字节，与 fixture 逐字节及 SHA256 一致。当前七容器 healthy，
  身份/启动时间/绑定、Agent 元数据与修复后快照一致，在线 version.json 与固定 release 一致。
  真实浏览器点击和部署回退只复核既有证据，未重跑；明确拟定 Dataset/Model 最小夹具范围。
- 实际修改文件：仅 `docs/ROADMAP.md`、`docs/STATUS.md`、`docs/HANDOFF.md`；
  本轮快照/清单复核/时钟与审阅结果位于忽略的 `infra/evidence/c3b-prompt/`，全部源码、
  修复/兼容报告、部署配置、已有未提交修改及三仓库 HEAD/暂存区保持；不提交或 push。
- 测试命令、结果、退出码及证据：子代理执行 `node clearml-web/tests/artifact-download.cjs`
  退出 0、TOTAL PASS 36，记录 `agent-review.json`，stdout 在本对话工具执行记录。
  `python3 -B infra/evidence/c3b-prompt/review.py` 初次退出 1：本轮核对器将 NetworkSettings
  暴露端口枚举与历史 HostConfig 绑定混比；按相同字段修正后退出 0，Agent 字段也完整对齐。
  原失败 `review-initial.txt`，通过结果 `review.txt`、`review-result.json`；延时见 `timing.json`。
  `python3 -B infra/evidence/c3b-prompt/check.py` 通过、退出 0：引用/格式/凭据模式、
  阶段/范围、HANDOFF 93 行、忽略规则、源码/报告/部署及 Git 既有改动保留检查通过，
  三仓库工作区/暂存区差异检查均退出 0；证据 `check.txt`、`result.json`。
  没有创建 Dataset/Model/Task/项目、调用写 API 或启动任务。
- 遗留问题 / 未验证项：完整 C3、四风险触发、受控夹具/关系、其他存储签名、文件全策略、
  Server Fork/GPU/远程及运维仍未验。拟定的 Dataset 承载 Task 状态流转必须明确允许，
  不误等同于 Agent 执行；Model 草稿 Task 保持 created，输入模型消费关系仍可能 N/A。
- 下一步启动条件（须用户明确授权，不自动执行）：用户将 C3-B 限定提示词交给实施对话，
  仅在全新专用项目树创建两 Dataset 版本/必要承载 Task、一个 Draft Task 和一个 OutputModel；
  不入队/训练/运行 Pipeline，不改变旧业务或设置，不自动进入 T02。

### 2026-11-10 09:48：独立 Artifact 下载按钮修复

- 时间（Asia/Hong_Kong）：2026-11-10 09:48。
- 任务 / 阶段及状态：独立下载修复通过；完整 C3 仍未通过，未进入 C3-B/T02。
- 本次结果与项目进度：从原按钮复现旧失败后，修复可信 Fileserver 识别/同源代理、
  签名、fetch HTTP 错误检查和相对导航回退；显式历史别名仅在 Fork 运行配置。
  独立主/Widgets 正式构建、新固定 release `artifact-download-20261110-v1`；
  运行 `2.5.0-artifact-fix-0b92177bcb35`，HEAD 基点 be71d50 + 未提交补丁/源码清单定义修复版本。
- 实际修改文件：Web 七文件 url.ts、artifact-download.ts（新）、app.constants.ts、
  environments/base.ts、base-admin.service.ts、common-experiments-info.effects.ts、
  tests/artifact-download.cjs（新）；根 infra/web-fork 的 compose.yaml/nginx.conf/verify.py/
  README.md，新增 prepare-download-release.py；新增 docs/T01C_ARTIFACT_DOWNLOAD_FIX.md，
  兼容报告追加结果，更新 STATUS/HANDOFF/DECISIONS。原 ROADMAP/C2 报告等改动保留。
- 测试命令、结果、退出码及证据：Node 边界测试最终 36 项、退出 0；现有锁定工具链
  `pnpm --dir clearml-web run build --output-path out/artifact-download-fix/main` 和
  build-widgets 同参数输出 widgets，65.893/21.011 秒、均 0，原有 4/6 警告保留。
  check-artifacts.py 最终 0，C1 原清单/新构建共享资源一致、874 JS 语法通过。
  Compose config/up、三轮 manifest HTTP 验收均 0，1502 文件、404/SPA/Widgets/API/文件/
  匿名受保护 401 通过；浏览器 before/new/rollback/restored 四轮均 0（旧轮验证失败复现）。
  新版两轮真实 download、cpu-smoke.json 122 字节、与 fixture 逐字节及 SHA256 一致，
  同源 /files HTTP 200 携 Cookie、无 CORS，无手改链接/伪造响应。回退 C2 v2 旧清单
  一致、无下载；恢复新版后复验成功，最终 healthy。基础登录/历史 Task/日志/标量/Widgets
  实际绘图回归通过。完整命令/退出码见 infra/evidence/artifact-download-fix/commands.jsonl，
  清单/source-version.json、release-version.json、*-browser.json/PNG、下载文件和 result.json。
  原六服务 verify.py 前后 0/0、compare-final.py 0，PID 205189/NRestarts=0/原六容器 ID/
  启动时间/挂载/端口/网络、C1 原产物、C2 v2、历史库存/Task/Artifact/偏好/配置元数据/
  Python 环境均不变；只 Fork 三次重建。文档/范围/保留/引用/忽略/敏感模式/三仓库
  HEAD/暂存区/diff 最终 check-delivery.py 退出 0，证据 delivery-check.txt。
- 失败记录：首轮测试替身只接受数组、首构建 noImplicitReturns、产物检查 favicon query
  路径均退出 1，修正后通过；首次批处理未在检查器失败停止，先切 Fork，随后补齐检查，
  后续回退恢复失败即停。原日志保留，未将失败或旧版无下载算成新版通过。
- 遗留问题 / 未验证项：无本修复阻塞；完整 C3/受控夹具/四风险触发、其他共享调用方
  写入或真实 S3 签名、完整文件权限、远程、Server Fork/GPU/运维仍未验。保持偏好/
  统计/第三方保护，原有错误逐项归因，未通配忽略。无 Server 改动、业务对象/任务创建、
  入队/训练、Git 暂存/提交/push。
- 下一步启动条件（须用户明确授权，不自动执行）：新版 18080 保持运行；后续 C3-B
  夹具/操作或其他阶段须另授权，Dataset 承载 Task 仍须明确包括，完整 C3 不因下载修复通过。

### 2026-11-10：复核 C3-A 并交付 Artifact 下载修复提示词

- 时间（Asia/Hong_Kong）：2026-11-10 09:29。
- 任务 / 阶段及状态：C3-A 报告核对和下一轮提示词已整理；不实施修复，完整 C3 仍未通过。
- 本次结果与项目进度：读取兼容报告、C3-A 交付/运行保护记录与 URL/签名/下载源码，
  确认任务采证完成不代表全面兼容；交付报告哈希映射匹配，记录的 7 容器/1502 release
  文件保护通过。本轮只核对既有证据，未重跑浏览器或运行验收。ROADMAP 最近候选改为
  Artifact 最小修复，明确 Web 构建/新 release/仅 Fork 更新、可信 URL 匹配和真实下载门槛。
- 实际修改文件：仅 `docs/ROADMAP.md`、`docs/STATUS.md`、`docs/HANDOFF.md`；
  本地证据 `infra/evidence/artifact-fix-prompt/` 保持忽略；兼容报告、全部源码与 C2 部署原样保留。
- 测试命令、结果、退出码及证据：证据核对内联 `python3 -B -` 初次退出 1，原因是
  本轮核对脚本把 `report_sha256` 映射误作单个哈希；按实际字段逐文件核对后退出 0，
  见 `review.json`。`python3 -B infra/evidence/artifact-fix-prompt/check.py` 首轮因核对器
  对等价状态措辞断言过窄退出 1，修正后及最终检查退出 0；保留 `check-initial.txt`。
  文档引用/格式/凭据模式、阶段/范围、HANDOFF 90 行、忽略规则、源码/部署/报告保留
  及三仓库工作区/暂存区差异检查通过；证据 `check.txt`、`result.json`，基线 `before-state.json`。
- 遗留问题 / 未验证项：下载缺陷未修；Dataset/Model/Pipeline 样本、四风险端点触发、
  偏好/统计/外部请求及 Server Fork/GPU/运维仍未验。无暂存、提交、push 或服务变更。
- 下一步启动条件（须用户明确授权，不自动执行）：用户交付下载修复提示词后按其中
  范围实施；只允许新建 release 并更新 Fork，原六服务/Agent/业务记录不改；真实页面
  下载/哈希、共享 URL 边界和回退通过后，再单独授权 C3-B 夹具与操作。

### 2026-11-10：T01-C3-A 只读页面/API 兼容性检查

- 时间（Asia/Hong_Kong）：2026-11-10 09:13。
- 任务 / 阶段及状态：C3-A 检查与问题记录已完成；完整 C3 未通过，C3-B/T02–T09 未开始。
- 本次结果与项目进度：复用 C2 工具与已有用户，在 18080/8080 独立 context 中完成
  每站 22 项主矩阵、7 项补测、5 项空态深链复核。主矩阵含库存读取，各覆盖 33 个认证/
  读取端点；API HTTP 均 200，已解析业务码均 200（auth.login 响应体不读），使用到的字段
  检查符合实际契约。项目/Task/参数/日志/标量/Artifact 元数据、队列/Worker 可读；
  Dataset/Model/Pipeline 无样本，仅列表/空态，不计详情、版本、操作兼容通过。
- 实际修改文件：仅新增 `docs/T01C_COMPATIBILITY.md`，更新 `docs/STATUS.md`、
  `docs/HANDOFF.md`；本地工具、源码静态摘录、截图、网络/下载证据在忽略的
  `infra/evidence/t01c3/`。原 ROADMAP、DECISIONS、C2 报告/部署配置及全部已有改动保留；
  两 Fork 干净，无源码/部署配置改动，无 Git 暂存、提交、push。
- 兼容问题：实际页面点击原绝对 8081 链接，两站均可读固定 Artifact；点击下载按钮时
  两站初次 fetch 共有 CORS 错误，官方回退真实下载并通过 SHA256，Fork 只回退为 inline
  JSON、未产生下载，主矩阵及补测重复确认。相对 `/files` 与绝对历史 URI 的 Fileserver
  识别/回退差异见报告；本轮未手工改写链接替代页面验证，两站 UI 均未使用 /files 分支。
  两站有 NG0953 切页 warning（具体业务根因未定位），官方空态指南偶发 ace 未定义；
  未将未知/受限错误通配忽略。Fork 根项目卡片数差异源自 shallow_search 查询不同。
- 风险与静态评估：四风险端点均未实际调用，响应 N/A；Pipeline/出队分支缺夹具，
  operations-log 客户端方法未找到业务调用，报告可见 Share 只复制链接；reports.share
  有权限写入副作用，仅静态分析。23 个服务/Schema +111 个业务 Python 文件与运行镜像
  SHA256 全相同，不足以要求切换/修改 Server Fork，仍未运行验收。
- 测试命令、结果、退出码及证据：`python3 -B infra/verify.py` 前后 0/0；snapshot.py
  before/after、pip freeze、static-server.py、compare-business.py、make-allowlist.py、
  risk-scan.py、analyze.py、compare-final.py 均退出 0；Node probe.cjs/matrix.cjs/
  supplement.cjs/empty-deep-recheck.cjs 均退出 0（采证完成，不等于全页面兼容通过）。
  初次六条定位器操作因隐藏 tooltip/错误次级 tab 超时，补测修正定位后全部成功；
  初期 `_ex`/Reports 字段观察标签按实际源契约纠正，原记录保留。正式命令、耗时、退出码
  见 commands.jsonl；matrix-*-browser.json、supplement-*-browser.json、empty-recheck-*-browser.json
  和对应 PNG、matrix-analysis.json、server-comparison.json、business-comparison.json、
  blocked-correlations.json、runtime-result.json 为主要证据。文档/范围/引用/保留/忽略/
  敏感模式与三仓库差异最终检查 `check-delivery.py` 退出 0，见 delivery-check.txt。
- 保护复核：68 个明确端点契约，未知拒绝；偏好/统计/第三方共 159 条阻断全部关联到
  同 URL/阶段的 requestfailed，均受限未验，未伪造成功响应。原 7 容器 healthy、ID/
  StartedAt/重启次数/挂载/网络/端口不变，Agent PID 205189/NRestarts=0/配置/依赖不变。
  C2 release 1502 文件、三仓库 HEAD/暂存区、原配置及历史库存/Task/Artifact/偏好哈希不变；
  未读取凭据文件内容，仅核对凭据文件元数据；未新建业务对象、入队/运行任务或重启服务。
- 遗留问题 / 未验证项：Fork 下载功能缺口；C3-B 夹具/有副作用操作、四风险触发路径、
  模型/数据集/管道详情关系、完整文件权限/远程/Server Fork/GPU/运维仍未验。
- 下一步启动条件（须用户明确授权，不自动执行）：建议先单独授权 Artifact 下载最小
  Web 修复及原页面回归，再按报告清单批准受控夹具；Dataset 可能创建承载 Task 须一并
  授权。没有批准的专用队列/排队操作不得为触发风险端点入队，不自动进入 C3-B/T02。

### 2026-11-10：复核 C2 记录并交付 C3 首轮提示词

- 时间（Asia/Hong_Kong）：2026-11-10 08:45。
- 任务 / 阶段及状态：C2 报告与本地证据核对通过；仅交付 C3 第一轮提示词，C3/T02–T09 未开始。
- 本次结果与项目进度：读取 C2 浏览器/HTTP/JS/交付及前后对比记录；记录的浏览器与交付
  pass 为 true、1502 文件及 874 JS 条目、4 个阻断相关错误一致，10 个交付文件哈希匹配。
  本轮未重跑这些运行测试。更新 ROADMAP 的 C2 已完成状态，建议 C3-A 先做只读矩阵，
  C3-B 受控操作/缺陷修复按结果另行授权；A 完成不代表整个 C3 通过。
- 实际修改文件：仅 `docs/ROADMAP.md`、`docs/STATUS.md`、`docs/HANDOFF.md`；
  证据 `infra/evidence/c3-prompt/` 保持忽略。全部既有 C2 文件、D11 决策与未提交修改保留，
  无 Git 暂存、提交或 push；未重建、重配或重启任何服务。
- 测试命令、结果、退出码及证据：C2 记录/哈希核对内联 `python3 -B -` 退出 0，
  结果 `review.json`，变更前基线 `before-state.json`；
  `python3 -B infra/evidence/c3-prompt/check.py` 通过、退出 0，核对引用/格式/凭据模式、
  阶段/范围、HANDOFF 行数、忽略规则、Git/既有 C2 成果保留与历史验收记录一致性；
  三仓库工作区及暂存区差异检查均退出 0，证据 `check.txt`、`result.json`。
- 遗留问题 / 未验证项：C2 的偏好/统计/第三方阻断继续作为受限条件，不外推完整兼容；
  Dataset/Model/Pipeline 若缺样本，只能验空态。完整 C3、文件权限策略、Server Fork 运行、
  GPU 和运维等仍未验。C3-A 提示词不授权新建测试对象、入队或 Pipeline。
- 下一步启动条件（须用户明确授权，不自动执行）：用户将 C3-A 提示词交给实施对话，
  完成页面/API 只读矩阵、四风险端点分类、Server Fork 静态差异及后续操作清单；
  确认 C3-B 的夹具/允许操作范围后再执行，不能自动进入 T02。

### 2026-11-10：T01-C2 ClearML Web Fork 独立部署

- 时间（Asia/Hong_Kong）：2026-11-10 08:39。
- 任务 / 阶段及状态：T01-C2 通过；C3 / T02–T09 未开始，不自动执行后续阶段。
- 本次结果与项目进度：独立单 Web Compose 项目 `tiesheai-web-fork` 运行于
  `127.0.0.1:18080`，复用锁定 ClearML 2.4.0 镜像的 Nginx 和原 API/Fileserver；
  C1 两套产物逐文件哈希相同后复制到独立只读 `c2-be71d50-v2` release，原产物不变。
  Web 源码为 `be71d50e7504eb00a2e09900fabbe8697ed23558`、package 2.5.0，
  运行标识 `2.5.0-fork-be71d50-c2`；Server Fork 未运行。已有未提交 ROADMAP 原样保留。
- 实际修改文件：新增 `infra/web-fork/compose.yaml`、`nginx.conf`、`compose.sh`、
  `prepare-release.py`、`verify.py`、`README.md`、`docs/T01C2_DEPLOYMENT.md`；
  更新 `docs/STATUS.md`、`docs/HANDOFF.md`、`docs/DECISIONS.md`。本地 release/工具/证据
  在 `.local/` 和 `infra/evidence/t01c2/`，均忽略；未修改两个 Fork、原 Compose 或 Agent。
- 测试命令、结果、退出码及证据：`python3 -B infra/verify.py` 前后退出 0；
  `prepare-release.py` 退出 0，Compose config/up 与 nginx -t 退出 0；
  `python3 -B infra/web-fork/verify.py` 退出 0，全部 1502 文件 HTTP 字节/哈希一致、
  874 个 JS 的 `node --check` 均退出 0，JS 分块/字体/Plotly/缺失 404/SPA/Widgets/
  redirect/query/配置/代理通过；匿名受保护 API 和 Artifact 401 保持鉴权。
  独立 Playwright 1.56.1 / Chromium 141.0.7390.37 浏览器脚本最终退出 0：已有用户登录、
  Set-Cookie/纯 Cookie server.info、历史 Task/Artifact SHA256 和 Widgets 历史标量图通过，
  context 隔离/7 个字体响应通过。只读保护阻断偏好/统计写入及第三方请求，4 个相应
  HttpErrorResponse 已逐项归因保留，不把限制下的结果扩大为完整无干预兼容验收。
  `snapshot.py before/after` 和最终 `compare-final.py` 均退出 0：六容器 ID/StartedAt/
  重启次数/配置/挂载和 Agent PID 205189/NRestarts=0/环境不变，Task/Artifact/三任务清单不变。
  `check-delivery.py` 最终退出 0，文档/引用/范围/敏感信息/忽略及三仓库 diff 检查通过。
  全部证据位于 `infra/evidence/t01c2/`，详见 [报告](T01C2_DEPLOYMENT.md)；关键文件
  `commands.jsonl`、`snapshot-*.json`、`browser-*.json/png`、`release-manifest.json`、
  `js-syntax.json`、`compare-final-fixed.txt`、`delivery-check.txt`。
- 失败记录：首次新容器 chown、Artifact location 优先级、浏览器定位器、v1 map 清理
  误改 Plotly、v2 测试阻断分类器及 Mounts 数组顺序比较均曾失败，修正后通过；
  浏览器安装解压停滞主动中止后 CRC 校验独立解压成功；匿名 Artifact 401 为预期。
  原始失败证据完整保留，具体退出码和归因见 C2 报告；原服务无新增异常。
- 遗留问题 / 未验证项：无 C2 阻塞；完整 C3、未拦截写入/外部更新、所有绝对文件链接、
  Fileserver 全策略、Server Fork、GPU、远程端到端及重启/恢复/长期负载仍未验证。
- 下一步启动条件（须用户明确授权，不自动执行）：C2 站点保持运行；C3 或其他任务
  须另行授权。启停/仅停止本项目回退见 `infra/web-fork/README.md`；不暂存、提交或 push。

### 2026-11-10：核对版本检查点并交付 T01-C2 提示词

- 时间（Asia/Hong_Kong）：2026-11-10 08:20。
- 任务 / 阶段及状态：已核对检查点报告并整理下一步提示词；T01-C2/C3 与后续阶段仍未开始。
- 本次结果与项目进度：读取检查点证据，当前三仓库 HEAD 与用户报告一致，检查前均干净；
  根/Web/Server 关键文件哈希与记录一致、bundle 文件存在。本轮未重跑 bundle 恢复，
  不把历史 verify/恢复/fsck 记为本轮执行。更新 ROADMAP 的检查点完成状态，下一步为 C2。
- 实际修改文件：仅 `docs/ROADMAP.md`、`docs/STATUS.md`、`docs/HANDOFF.md`；
  本地证据位于已忽略的 `infra/evidence/c2-prompt/`。本轮不暂存、提交或 push，
  因交接更新，根仓库现有上述未提交文档；两个 Fork 和检查点提交保持不变。
- 测试命令、结果、退出码及证据：检查点 HEAD/关键文件核对内联 `python3 -B -` 退出 0；
  `python3 -B infra/evidence/c2-prompt/check.py` 通过、退出 0，核对文档引用/格式/凭据模式、
  阶段一致性、HANDOFF 81 行、修改范围/忽略规则、提交/暂存区与 Fork 保留；三仓库
  工作区及暂存区 `git diff --check` 均退出 0。证据 `check.txt`、`result.json`，基线
  `before-state.json`；本轮不执行运行时或部署检查。
- 遗留问题 / 未验证项：未推送提交的获取边界和原有部署/浏览器/API/GPU 未验证项不变。
  C2 提示词要求独立站点/只读 release、显式运行配置与代理、Widgets 路径、隔离浏览器
  上下文及基础登录读取、原服务前后回归；C3 完整业务矩阵不计入 C2。
- 下一步启动条件（须用户明确授权，不自动执行）：用户将 T01-C2 提示词交给实施对话
  后按范围执行；保留本轮未提交文档，不覆盖原服务，不自动进入 C3。

### 2026-11-09：独立任务——本地 Git 版本检查点

- 时间（Asia/Hong_Kong）：2026-11-09 22:12。
- 任务 / 阶段及状态：本地源码检查点验收通过；T00/T01-A/T01-B/T01-C1 仍已完成，
  T01-C2/C3 与 T02–T09 均未开始。
- 本次结果与项目进度：根仓库按明确清单保存 31 个文件（原有 28 个验收成果及本次
  3 个新文件）；两个 Fork 保留独立 `.git`，根仓库忽略其工作目录，以 revisions.json
  记录 origin、基点、保存提交与应用版本，无 submodule/subtree/gitlink。
  Web 仅 angular.json 修复提交为 `be71d50e7504eb00a2e09900fabbe8697ed23558`；
  Server 干净，保持 `2ebdc43951b9432cc7fa528bbb3a7100fc6fe805`，无空提交。
  三个 master 完整历史 bundle 均通过空仓库 verify、独立临时目录克隆及源码核对；
  不导出根仓库 Codex 内部引用。未 push、部署、重启服务或进入 C2。
- 实际修改文件：新增 `.gitignore`、`configs/revisions.json`、`docs/VERSION_CHECKPOINT.md`；
  更新 `docs/DECISIONS.md`、`docs/STATUS.md`、`docs/HANDOFF.md`；两个 Fork 本地
  `.git/info/exclude` 增补忽略规则，未改 Fork 的已跟踪忽略文件。原有部署、Agent、
  Smoke、规划与验收报告内容保持；首次根提交后仅追加 STATUS/HANDOFF 验收记录提交。
- 测试命令、结果、退出码及证据：`python3 -B infra/evidence/version-checkpoint/check.py`
  的 `--phase prepared`、`--phase staged`、`--phase initial` 均退出 0；每轮 353 项核对通过，
  包括文件范围/既有内容保留、实际凭据字面量/密钥模式扫描、忽略规则、Markdown 引用、
  HANDOFF 行数、版本关系、Git 状态及三仓库 `git diff --check`/`git diff --cached --check`。
  `python3 -B infra/evidence/version-checkpoint/bundle_restore.py --phase initial` 退出 0，
  内含三个仓库 `git bundle create`、空仓库 `git bundle verify`、本地 `git clone --branch master`、
  `git fsck --full --strict`，全部退出 0；目标提交、完整 tree、根仓库全部文件及 Fork 关键文件
  SHA256 一致，恢复目录 `/tmp/tiesheai-checkpoint-initial-raahjoqg`，没有启动服务。
  证据根目录 `infra/evidence/version-checkpoint/`：`before-state.json`、`root-files.json`、
  `web-commit*.json`、`root-initial-commit*.json`、`audit-*.json`、`bundle-*-commands.json`、
  `restore-initial.json`；验收文档提交后的最终复验及根 SHA 见 `restore-final.json`、`result.json`。
  最终 bundle 位于其 `bundles/`；原始根 bundle 另保留在 `bundles/initial/`。
  起始根仓库无 HEAD，`git rev-parse --verify HEAD` 预期退出 128，不是验收失败。
- 遗留问题 / 未验证项：本任务无验收阻塞；未推送的本地提交不能从 GitHub 获取。
  本机 bundle 只证明源码可恢复，不包含数据库/卷、凭据、依赖、构建产物或主机配置；
  不等于异机灾备、数据库恢复、跨主机部署或环境复现。历史运行时/Agent/构建未重跑，
  原有 GPU、Fork 集成、浏览器和运维未验证项不变。
- 下一步启动条件（须用户明确授权，不自动执行）：本任务完成后停止；推送、T01-C2
  或其他实施任务须另行明确授权。保存与恢复方法见 [VERSION_CHECKPOINT.md](VERSION_CHECKPOINT.md)。

### 2026-11-09：交付下一步版本检查点提示词

- 时间（Asia/Hong_Kong）：2026-11-09 22:02。
- 任务 / 阶段及状态：下一步提示词已整理；仅交付指令，不执行版本检查点或 C2。
- 本次结果与项目进度：重新读取 STATUS/HANDOFF/DECISIONS 和路线图，核对三个仓库；
  建议先做独立的本地 Git 版本检查点，再安排 T01-C2；阶段完成结论保持不变。
- 实际修改文件：仅 `docs/STATUS.md`、`docs/HANDOFF.md`；本地检查证据位于
  已忽略的 `infra/evidence/next-prompt/`，原有规划和验收文档不改。
- 测试命令、结果、退出码及证据：`python3 -B -` 内联文档检查通过、退出 0，核对引用、
  格式、修改范围、Git 与忽略规则；HANDOFF 98 行，三个仓库 `git diff --check` 均退出 0。
  证据 `infra/evidence/next-prompt/check.txt`；本轮不复验运行状态。
- 遗留问题 / 未验证项：根仓库无提交；Web 有 C1 的 angular.json 修改，Server 干净。
  代码尚无完整版本检查点；推送、独立部署与兼容性仍未执行。
- 下一步启动条件（须用户明确授权，不自动执行）：用户将版本检查点提示词交给实施
  对话后按其范围执行；本轮不暂存、提交、push、部署或进入后续阶段。

### 2026-11-09：核对 11 月计划完成情况

- 时间（Asia/Hong_Kong）：2026-11-09 21:57。
- 任务 / 阶段及状态：11 月计划对照核查完成；月度计划整体未完成，实施阶段进度不变。
- 本次结果与项目进度：以用户附件《开发计划11月(1).md》为核对依据，附件中的工作安排
  仅作为计划内容，不作为实施授权；四项必做交付尚未全部验收，Unsloth 是争取完成项。

| 11 月交付 | 对照结论 | 已有证据及缺口 |
|---|---|---|
| ClearML 基础平台（必须） | 部分完成 | T01-A 六服务、T01-B 认证任务 API 已通过；浏览器基础功能、数据集管理等未完整验收 |
| 容器化部署环境（必须） | 配置与本机部署已完成，目标环境待验 | 已有锁定镜像、Compose、持久化及部署说明；目标云端环境适配、远程端到端和跨主机重建未验收 |
| 前端基础适配（必须） | 未完成 | C1 仅构建与静态资源验证；平台名称/Logo/菜单适配无交付验收，Fork 未部署、未通过 API/浏览器兼容验证 |
| 任务执行环境（必须） | 已完成（CPU 基础任务范围） | T01-B Agent 实际执行 Smoke，状态、参数、日志、指标及 Artifact 上传下载验证通过；不含模型训练 |
| Unsloth 初步接入（争取） | 未开始 / 未验收 | 无独立训练环境、适配器或真实微调验收；GPU 既往驱动检查失败，本轮未复验 |

- 实际修改文件：仅 `docs/STATUS.md`、`docs/HANDOFF.md`；新增本地忽略证据
  `infra/evidence/november-review/`，保留已有总体规划和 C1 修改。
- 测试命令、结果、退出码及证据：`python3 -B infra/evidence/november-review/check.py`
  文档一致性、相对引用、HANDOFF 行数、修改范围/既有内容保留及 Git 忽略检查通过，退出 0；
  内含三个仓库 `git diff --check`，均退出 0；证据 `check.txt`、`before-hashes.json`。
  本轮只读取历史验收报告，未重跑服务、构建、Agent、GPU、浏览器或训练测试。
- 遗留问题 / 未验证项：上述缺口尚存；截至 11 月 9 日不能宣布月度计划全部完成，
  也不能据此认定月底延期。核对时总体规划文档尚待原任务验收；后续结果见下方规划记录。
- 下一步启动条件（须用户明确授权，不自动执行）：授权具体月度缺口任务后实施；
  前端需明确名称/Logo/必要入口，目标部署需明确环境，训练需明确资源、模型和数据。

### 2026-11-09：接续原对话并制定总体规划

- 时间（Asia/Hong_Kong）：2026-11-09 21:59。
- 任务 / 阶段及状态：总体规划完成，文档验收通过；保留 T00、T01-A、
  T01-B、T01-C1 已完成结论，T01-C2/C3 与 T02–T09 均未启动。
- 本次结果与项目进度：读取《规划Codex实施方案》及分享对话历史，恢复铁路勘察设计
  知识注入平台目标与阶段编号；形成总体路线图、Demo/课题交付边界、阶段验收、
  版本/GPU 门禁、共享契约与最近的 C2 任务卡。原始三份需求附件和 ZIP 未核验，
  旧对话选型建议、场景数量、指标及工期不记为本轮确认的正式条款。
  期间发现 C1 实施任务已更新交接；首次文档基线检查退出 1，未合入旧版本补丁，
  随后重读 AGENTS/STATUS/HANDOFF/DECISIONS、C1 报告及证据，刷新基线并保留成果。
  结束前另有月度核对更新共享文档，已保留其记录，并据该任务结论补入 11 月优先级；
  本轮未直接核验月度计划附件，也不认领该任务的检查结果。
- 实际修改文件：新增 `docs/ROADMAP.md`；更新 `docs/STATUS.md`、`docs/HANDOFF.md`。
  本地快照与检查证据位于已忽略的 `infra/evidence/planning/`，不复制原对话全文入库。
- 测试命令、结果、退出码及证据：`python3 -B infra/evidence/planning/check.py` 通过、
  退出 0；核对文档引用/格式/阶段一致性、凭据模式、HANDOFF 93 行、忽略规则、
  改动范围和 C1 成果保留，三个仓库 `git diff --check` 均退出 0；证据 `check.txt`、
  `result.json`。初次并发变化保护检查退出 1，刷新基线后检查退出 0，快照为
  `before-state.json` / `before-edit-state.json`；来源及并发事件见 `source-retrieval.json`。
  已只读核对 C1 的构建/产物/交付证据；本轮未重跑构建、服务、SDK、Agent、GPU、训练或 Pipeline。
- 遗留问题 / 未验证项：原始需求和首场景、数据/模型、正式评估口径待核对；独立部署、
  Fork 兼容、GPU 和运维未验证项延续。Web 的 C1 `angular.json` 修改保留，Server 干净；
  根仓库无提交。AGENTS、DECISIONS 和 C1 报告本轮不改，无暂存、提交或 push。
- 下一步启动条件（须用户明确授权，不自动执行）：建议先单独处理版本检查点，再
  授权 T01-C2 独立部署、T01-C3 兼容验证；按 ROADMAP 定义范围。进入 T02/T03 前
  补齐需求、业务样例、契约与评估口径；本轮不进入实施阶段。

### 2026-11-09：T01-C1 ClearML Web Fork 构建验证

- 时间（Asia/Hong_Kong）：2026-11-09 21:47。
- 任务 / 阶段及状态：T01-C1 已完成；T01-C2 未开始，未独立部署或 API 联调。
- 本次结果与项目进度：现有 Node 24.16.0 / pnpm 10.34.9 / Angular 21.2.x 环境下，
  主应用和 Widgets 构建成功；初次 Widgets 编译退出 0 但共享资源缺失，最小修复后
  重建并通过完整性检查。主应用 1817 文件、57,230,243 字节；Widgets 318 文件、
  19,240,661 字节。原有六服务及 Agent 进程/配置/Python 环境未受影响。
- 实际修改文件：`clearml-web/angular.json`；新增 `docs/T01C1_BUILD.md`；更新
  `AGENTS.md`、`docs/STATUS.md`、`docs/HANDOFF.md`、`docs/DECISIONS.md`。
  产物位于 Web Fork 忽略的 build/dist，证据位于已忽略的 `infra/evidence/t01c1/`。
- 测试命令、结果、退出码及证据：`pnpm run build` 69.324 秒、退出 0；
  `pnpm run build-widgets` 初次 20.430 秒、修复后 21.204 秒，均退出 0。
  `python3 -B infra/evidence/t01c1/check-artifacts.py` 初次退出 1（Widgets assets 为
  普通文本文件），修复后退出 0；入口/分块/CSS/共享资源及 SHA256 清单验证通过。
  主应用 4 条警告、Widgets 6 条警告，无编译错误；未调整预算。
  前后 `python3 -B infra/verify.py` 均退出 0；容器、Agent、pip freeze、配置哈希比对通过。
  `python3 -B infra/evidence/t01c1/check-delivery.py` 及三个仓库 `git diff --check`
  均退出 0。命令耗时、完整警告、产物清单、前后运行状态及检查日志见证据目录和构建报告。
- 遗留问题 / 未验证项：无 T01-C1 验收阻塞；保留非阻塞构建警告。独立部署、运行时
  configuration/env/版本信息、浏览器/Widgets 功能、API 兼容及干净环境安装未验证。
  18080 仅方案分析且前后均无监听；Server Fork 干净，Web Fork 仅 angular.json 修改。
  根仓库原有未跟踪内容保留；未暂存、提交或 push，未替换现有服务。
- 下一步启动条件（须用户明确授权，不自动执行）：用户明确授权 T01-C2 的部署与
  联调范围及验收标准；可据构建报告评估 127.0.0.1:18080 独立站点，不自动启动。

### 2026-11-09：建立精简任务交接机制

- 时间（Asia/Hong_Kong）：2026-11-09 21:37。
- 任务 / 阶段及状态：交接机制建立完成，文档验收通过；T00、T01-A、T01-B 已完成，
  T01-C 尚未开始，本轮未启动任何后续阶段。
- 本次结果与项目进度：新增 100 行以内的 HANDOFF，记录最新 T01-B 阶段和必要历史；
  AGENTS 明确每次任务结束同时更新 HANDOFF / STATUS，原始日志保留原位置，
  不虚构验收、Git 更新前检查忽略规则和敏感信息；DECISIONS D07 同步该机制。
  修正 AGENTS 中 T01-B 未开始的过期描述，区分历史验收和本轮文档检查。
- 实际修改文件：新增 `docs/HANDOFF.md`；更新 `AGENTS.md`、`docs/STATUS.md`、
  `docs/DECISIONS.md`。本轮检查证据新增于已忽略的 `infra/evidence/handoff/`。
- 测试命令、结果、退出码及证据：`python3 -B infra/evidence/handoff/check.py` 通过、
  退出 0；核对 HANDOFF 行数、Markdown 引用、阶段/历史证据一致性、敏感信息、
  忽略规则和修改范围，并执行根仓库及两份 Fork 的 `git diff --check`（均退出 0）。
  证据 `infra/evidence/handoff/check.txt`，修改前哈希见同目录 `before-hashes.json`。
  已读取 T01-A/T01-B 原有验收证据；未重跑运行时、SDK、Agent 或 GPU 检查。
- 遗留问题 / 未验证项：无本轮文档验收阻塞；沿用上文未验证边界，不将本轮证据阅读
  视为运行时复验。根仓库尚无提交且原有内容未跟踪，两份 Fork 干净；无暂存、提交或 push。
- 下一步启动条件（须用户明确授权，不自动执行）：用户明确指定 T01-C 或其他任务的
  范围与验收标准；下一任务先读取 STATUS、HANDOFF 和 DECISIONS，再按授权行动。

### 2026-11-09：T01-B ClearML CPU Agent 联调

- 时间（Asia/Hong_Kong）：2026-11-09 21:25；任务 / 阶段及状态：T01-B 已完成。
- 本次结果与项目进度：认证 SDK 配置、`rail-cpu`、CPU Agent 和真实 Smoke Task
  完整执行通过；T01-A 前后复核仍为六服务 healthy；T01-C 未开始。
- 实际修改文件：新增 `infra/agent/README.md`、`clearml.conf.example`、
  `configure_sdk.py`、`env.sh`、`start.sh`、`tiesheai-clearml-cpu-agent.service`；
  新增 `tests/smoke/cpu_smoke.py`、`run_cpu_smoke.py`、`expected.json`；
  新增 `docs/T01B_ACCEPTANCE.md`，更新 `docs/STATUS.md`、`docs/DECISIONS.md`。
  主机另新增 systemd unit；本地安全配置和证据位于忽略目录。
- 测试命令、结果、退出码及证据：前后 `python3 -B infra/verify.py` 均退出 0；
  最终 `source infra/agent/env.sh` 后 `python -B tests/smoke/run_cpu_smoke.py
  --evidence infra/evidence/t01b` 退出 0、PASS。参数、指标、Agent 取队列日志、
  completed、服务端源码及 Artifact SHA256 全部通过。环境 `pip freeze` 前后 `cmp`
  退出 0；shell/systemd/文档和引用/凭据扫描/改动范围检查通过，退出 0。
  明细见验收报告；本地 `latest.json`、`smoke-run.log`、最终 Task 子目录、
  `delivery-checks.txt` 保留证据。
- 遗留问题 / 未验证项：无阶段验收阻塞；第一次 Agent Task 因 CPU 检查失败，
  第二次 Task completed 但验收器/大整数指标检查失败，均保留实际记录，未改写结果。
  最终任务重新执行并独立验收通过。其余未验证边界见上节；服务重启恢复、远程和
  Fork/GPU 不计入完成范围。根仓库尚无提交，当前使用单脚本快照；两份 Fork 干净，
  原有部署文件无改动，无 Git 暂存、提交或推送。
- 下一步启动条件（须用户明确授权，不自动执行）：用户定义并授权 T01-C 或其他
  具体任务；当前保留 CPU Agent 运行，不自动创建后续任务。

### 2026-11-09：建立跨 Codex 对话的上下文交接

- 状态：已完成，文档检查通过；不改变上述阶段进度。
- 实际修改文件（均为新增）：`AGENTS.md`、`docs/STATUS.md`、`docs/DECISIONS.md`。
- 已读取部署结果、Compose、镜像锁定清单及上述验收证据，保留现有部署约束。
- 测试：`python3 -B /root/TieSheAI/infra/verify.py` 退出 0，再次输出
  `T01-A live acceptance: PASS`，6/6 healthy；结果见本次 Codex 执行输出，
  未覆盖历史 `infra/evidence/acceptance.txt`。
- 环境检查：`nvidia-smi` 退出 9，报告无法与 NVIDIA 驱动通信，GPU 问题仍未解决。
- 文档检查：`python3 -B -`（本次执行记录中的内联检查）退出 0；三份文档格式与
  所有 Markdown 相对引用有效，AGENTS 交接规则齐全，阶段和版本与证据一致，
  13 个现有部署文件 SHA-256 与修改前一致。
- 改动范围检查：根目录及两份 Fork 的 `git status --short` 已核对；两份 Fork
  工作区干净。根仓库原有源码目录和 infra 文件仍未跟踪，不属于本次新增内容。
  三个仓库的 `git diff --check` 均退出 0；新建未跟踪文档由上述内联检查覆盖。
- 遗留问题：沿用上节未验证项；本次未修复 GPU，未运行 Fork 集成测试。
- 下一步：等待用户明确指定任务；未启动 T01-B / T01-C，未修改业务源码、部署配置，
  未执行 Git 暂存、提交或推送。
