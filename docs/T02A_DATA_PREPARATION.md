# T02-A：数据输入契约与 CPU 数据准备验收

时间：2026-11-10 19:39（Asia/Hong_Kong）。**T02-A 限定范围通过；整个 T02 未完成，完整 C3 仍未通过。**
按 [任务授权](T02A_TASK.md) 实施，仅使用合成数据做功能测试；网页上传/数据选择入口留给 T02-B，
不声称公开数据 Demo、Unsloth/OpenCompass 接入、训练或平台全链路完成。

## 交付与行为

- [v1 契约](../schemas/conversation-v1.md)、[单条 JSON Schema](../schemas/conversation-v1.schema.json)：UTF-8 无 BOM、messages 必填，
  可选首条 system，然后 user/assistant 交替并以 assistant 结束；content 非空白，ID/来源规则明确。
- [CPU 组件/CLI](../integrations/data_preparation/prepare.py)：先验证全部输入、任何非法行明确失败，按规范 messages 精确去重，
  合并共同来源及跨来源重复形成的连通组，固定种子按组划分；输出非空且无跨集重复，来源组不拆开。
- 输出 train/validation 两份 messages-only JSONL、全部重复出现的来源映射、统计、manifest。
  manifest 登记输入 Dataset ID/版本/字节/SHA256、参数、实际执行代码和环境版本、四个输出的 SHA256；
  自身 SHA256 在上传前日志/Artifact/Dataset state 另存。契约不把文档分块冒充带答案样本。
- [ClearML 控制器](../integrations/data_preparation/clearml_run.py)：唯一项目树、本地原子台账、创建前 pending 保护、
  `Task.script.diff` 完整源码快照、空闲门禁入队和独立下载验收；复用原 CPU Agent、SDK/认证和存储。
  处理 Task 的 Preparation 参数/SDK runtime 引用输入，Results 引用输出；输出 Dataset provenance 回指输入与处理 Task。
  输入/输出是不同名称的转换资产，各自版本 1.0.0；没有继承原始文件进训练输出，未创建模型或 Pipeline。
- [合成夹具](../examples/t02a/README.md)、[测试/复验入口](../tests/t02a/README.md)：单元测试、CLI、真实 Agent、Fork 页面、下载和保护检查。

## 真实执行与资产台账

命名空间 `TieSheAI-T02A-20261110T112914Z`。本轮新建严格 4 个项目节点、3 个 Task、0 Model；两个 Dataset 的 ID 就是各自承载 Task ID。

| 资产 | ID / 状态 |
|---|---|
| 输入 Dataset / 承载 Task | `7aa679c269ea42bc9240676e332ed504`，input-conversations v1.0.0，completed/final |
| CPU 处理 Task | `c0b6cd3261164c89b24c7cda38875bfa`，data_processing，真实 Agent completed |
| 输出 Dataset / 承载 Task | `1073a6bcf81e406cbbe5d8dde0d7cd73`，prepared-conversations v1.0.0，completed/final |
| 既有 Queue | `9821226b7d1c4d57b4dae4418bd1f28b`，rail-cpu；入队前两次确认无排队/运行作业 |
| 既有 Worker | `tiesheai-rail-cpu:cpu0`；Python 3.11.18 / SDK 2.1.12 / Agent 3.0.3 |

| 项目节点（含 SDK 隐藏节点） | ID |
|---|---|
| TieSheAI-T02A-20261110T112914Z/.datasets/prepared-conversations | `8b0b4f4d49814b2fbf27fba3b8baa16f` |
| TieSheAI-T02A-20261110T112914Z/.datasets | `a976dcaafed1452785318133170553f7` |
| TieSheAI-T02A-20261110T112914Z/.datasets/input-conversations | `bf372700289d40a3afc9dcf9c254b067` |
| TieSheAI-T02A-20261110T112914Z | `f523a2a292d44fa199ca36cc2457574c` |

[Fork 处理 Task](http://127.0.0.1:18080/projects/f523a2a292d44fa199ca36cc2457574c/experiments/c0b6cd3261164c89b24c7cda38875bfa/output/log)。
完整台账 `infra/evidence/t02a/ledger.json`（含所有项目/Task ID）、`created-ids.jsonl`（本地控制器创建响应）、
`inventory-before.json` / `inventory-final.json`；Worker 输出 Dataset ID 在创建后立即写回台账。
后续继续先核对台账；pending 创建结果不明时停止并核对服务端，不能删除台账重造对象。
prepare/submit 对 completed 台账分别再执行一次，均退出 0，无新对象/重复入队；未做中断故障注入。

Agent 源码 SHA256：`3845ca8496d52b1b632334bb69a4622bf6ff984073f98c46fdebacd4fe4423f9`；本地组件、服务端 script.diff、Agent 执行日志/Execution 参数和 manifest 完全一致。
无远端 repository/commit，源码不依赖未 push 的 GitHub 状态；实际 queue pull 日志、queued→in_progress→completed 已回读。
仅处理 Task 由 Agent 真实执行；两个 Dataset 的 SDK 封存状态不冒充 Agent 作业。
输入 Dataset 记录在 Task runtime `datasets` / `orig_datasets.input-conversations/1.0.0`。

输入 14 行/2378 B，SHA256 `9e584b6256904b2b2ff335f05e4f497f24cd3a2f1dcd59a7aab3e4fa93ba4dcd`。
合法 14、非法 0、唯一 12、移除重复 2、来源连通组 5；seed=42，目标验证**组**比例 0.25，
验证 1 组/2 条、训练 4 组/10 条，实际验证样本比例 1/6。没有为凑样本比例拆来源组。
统计写入 Task scalar/日志/Artifact/输出 Dataset，并独立回读核对。

| 输出文件 | 字节 | SHA256 |
|---|---:|---|
| `manifest.json` | 1235 | `ed3af7f78808c19437354c2a2a38ce536b12f1ce7b6907f09054f33fa70a097c` |
| `sources.jsonl` | 3167 | `57a609ebba57235dcbe982989ddde236ca6f9e1c597c635efcefce94587197ae` |
| `statistics.json` | 269 | `58ac671caa8b2df568f10c83645b0273197c87d0d745266d41272dee716fb31e` |
| `train.jsonl` | 1264 | `41fd501bcbefac0c9bb3282ac64393fd202edf88cbc735bf815e5dae656a305f` |
| `validation.jsonl` | 252 | `ebff555b360ee80c1cc67f7aeedcc21ef866ea701b079c79b8e5aeb0713b343c` |

## 验收命令、退出码与证据

以下命令从仓库根目录执行；SDK 命令先 `source infra/agent/env.sh`。
`python3 -B tests/t02a/run.py <证据标签> <实际命令…>` 记录实际 argv、开始时间、退出码、耗时和输出路径，
完整记录为 `infra/evidence/t02a/commands.jsonl`，该目录及凭据受 Git 忽略；不复制敏感原始日志到 Git。

| 命令（省略证据包装器） | 实际结果 / 退出码 | 证据（均在 infra/evidence/t02a/） |
|---|---|---|
| `python3 -B -m unittest discover -s tests/t02a -p 'test_*.py' -v` | 8 组测试及非法输入子例全部通过 / 0 | unit-tests.txt、unit-tests-final.txt |
| `python3 -B integrations/data_preparation/prepare.py --input examples/t02a/conversations.jsonl --output infra/evidence/t02a/local-prepared --seed 42 --validation-fraction 0.25` | CLI 成功，训练10/验证2 / 0 | local-cli.txt、local-prepared/；局部环境版本与 Agent 环境分列 |
| `python -B integrations/data_preparation/clearml_run.py prepare` | 唯一输入 Dataset/处理 Task 创建、输入上传封存 / 0 | assets-prepare.txt、ledger.json |
| `python -B integrations/data_preparation/clearml_run.py submit` | 空闲门禁通过后唯一 Task 入 rail-cpu / 0 | submit.txt、idle-*.json、dependencies-before.json |
| `python -B integrations/data_preparation/clearml_run.py verify --timeout 300` | 真实 Agent completed、下载/复现通过 / 0 | agent-verify.txt、observed-status.json、processing-task.json、task-console.txt、sdk-verification.json |
| `python -B integrations/data_preparation/clearml_run.py verify --timeout 10` | 增补上传前日志/Artifact metadata 哈希与执行 Python 核对通过 / 0 | agent-final-verify.txt；未重新执行作业 |
| `python -B integrations/data_preparation/clearml_run.py prepare` / `submit`（复用台账） | 均无重复创建/入队 / 0、0 | resume-prepare.txt、resume-submit.txt、inventory-final.json |
| `node tests/t02a/browser.cjs fork-r4` | Fork 16 步与3份真实下载通过 / 0 | browser-r4.txt、fork-r4-browser.json、fork-r4-*.png / download-* |
| `python3 -B tests/t02a/check.py browser --label fork-r4` | 页面/ZIP每个成员/manifest字节与哈希、错误逐项分类通过 / 0 | browser-download-check-r4.txt、browser-verification.json、browser-console-review.json |
| `python3 -B infra/evidence/t02a/snapshot.py after` + `python -B tests/t02a/check.py preservation` | 前后保护检查通过 / 0、0 | snapshot-after.json、preservation-result.json |
| `python3 -B tests/t02a/check.py delivery` | 文档/引用/范围/忽略/敏感模式/HANDOFF行数/三仓库diff最终通过 / 0 | delivery-final.txt、delivery-result.json |

单元测试包含有效系统/多轮/中文数据、非法 JSON/字段/角色/Unicode、空白内容、重复键/ID、混合非法行不产出、
精确去重、跨来源重复传递合组、同种子全部文件逐字节一致、不同种子变化、换序保持划分、集合隔离、
不可拆单组失败、参数边界及 CLI 失败退出 2/拒绝覆盖。非法输入在本地测试，未另外创建失败 Agent Task。

SDK 验收强制下载所有 Dataset 的 state/data/provenance 和报告 Artifact，不依赖已有材料化缓存；
新 ZIP 独立解包、每文件大小与 SHA256 一致，再用下载的输入和相同参数在同环境复算，五个输出全部字节一致。
所有输出的上传前日志 SHA256 和两个报告的 Artifact metadata 哈希也与下载一致。

浏览器直接登录 Fork：检查 Task completed、Agent 日志、参数/输入 ID/版本、manifest Artifact、
两个 Dataset 的版本/文件名/完整哈希、真实 Task information 链接；从现有 Artifact 按钮实际下载。
manifest 1235 B、输入 ZIP 406 B、输出 ZIP 2597 B，浏览器下载与 SDK 逐字节一致；两 ZIP 全成员与 manifest 核对。
三个 GET 均走同源 `/files/`、HTTP 200、携 Cookie，无手改 DOM/href、伪造响应或鉴权绕过。

保护性拦截继续阻断用户偏好、统计选项写入及第三方；34 条 console、8 条 pageerror 均逐条关联到这些拦截
或既有可选 credentials.json/onboarding.json 404，没有未知业务端点/未分类错误。
GitHub fetch 的归因是基于相同阶段被阻断 URL 与固定堆栈的推断，原文保留。
JSON manifest 的 DevTools 响应体旁路观察为 0 B，实际 download 为 1235 B；文件字节验收以真实保存文件为依据，
该采集限制在 browser-verification.json 单列，不用 0 B 响应观察替代实际下载。两 ZIP 的响应体采集与保存文件哈希一致。

## 初轮失败与保留

- browser-r1 / 退出 1：manifest 哈希同时出现在 metadata 和 Hash 两处，严格定位歧义；修正验收定位。
- browser-r2 / 退出 1：Dataset 详情弹层遮挡 Task information，popup 等待超时；按现有 UI 关闭弹层后点击真实链接。
- browser-r3、r4 均 16 步/3份下载通过、退出 0；r4 增加等待网络响应结束的旁路采集，产品/部署未改。
- browser-download-check / 退出 1：异步错误跨阶段边界 5ms 到达，原按相同阶段关联失败；改为唯一匹配的
  100ms 内结构化错误、已知被阻断 URL 和构造器，不通配忽略 pageerror。
- browser-download-check-final / 退出 1：JSON 的 DevTools body 旁路为 0B，原错误地要求旁路体哈希也相同；
  最终逐字节核验真实 download，并单列采集限制；ZIP旁路哈希仍严格核对。所有原失败与文件留存。

## 修改范围、保护与限制

新增 `integrations/data_preparation/` 两脚本、`schemas/` 两契约文件、`examples/t02a/` 两示例文件、
`tests/t02a/` 六文件及本文；更新 STATUS/HANDOFF/DECISIONS/ROADMAP/T02A_TASK 的当前状态。
保留全部既有改动，未改 Web/Server Fork、部署/Agent/队列配置、历史数据或 C3-B 夹具。
七容器 ID/启动/健康/端口/挂载/重启次数、Agent PID/启动/配置元数据、pip freeze、三仓库 HEAD/index、
旧项目/Task/Model/偏好完整对象、历史 Artifact 远端文件哈希和 C2 release 清单前后不变。
仅本轮 rail-cpu 入队/拉取使 Queue last_update 改变，配置与原空队列最终保持；没有新 Queue。
未重启任何服务、安装包、启用 GPU、训练、创建 Pipeline、暂存、提交、push 或清理对象。

保留未验证项：完整 C3、Model GENERAL/菜单 inline、文本预览/输入模型消费、四风险端点、分享/角色/完整文件权限、
Server Fork、GPU、远程端到端、跨主机环境重建/启动/备份恢复及长期负载；本轮不扩验。
当前组件为内存处理、精确内容去重，未验大规模/语义去重；依赖正确 source_id 才能隔离语义来源。
此版 Agent 接入复用宿主机环境，台账为本机操作证据；未宣称跨主机发布、自动恢复或环境隔离。

## T02-B 如何复用（尚未授权实施）

网页上传入口按 v1 契约先校验，将输入登记为 Dataset，表单固定输入 ID/版本、seed 和验证组比例；
复用 `prepare()` / 独立脚本快照和已有 Task/Agent 机制发起处理，每次操作建立对应台账并回传处理 Task ID。
数据选择入口读取输出 Dataset ID/版本、manifest/SHA256、统计和 train/validation 两文件，链接到现有日志/Artifact。
当前本轮控制器固定唯一命名空间和 ledger，T02-B 需把每次用户操作的台账/参数接到受控现有 API 入口；
沿用鉴权与队列边界，不新增后台/数据库/调度器。后续训练适配器再绑定基座和 chat template。
T02-B、公开数据 Demo、T03/GPU/训练或其他 C3 修复必须用户分别明确授权，本轮到此停止。
