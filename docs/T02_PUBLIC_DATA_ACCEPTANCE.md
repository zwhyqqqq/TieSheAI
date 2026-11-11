# T02 公开数据验证与训练交接验收

2026-11-11 09:10（Asia/Hong_Kong）。本轮公开对话 JSONL 网页数据流程与训练输入交接通过。T03 等待用户单独授权。
范围依据见 [任务要求](T02_PUBLIC_DATA_TASK.md)、[输入契约](../schemas/conversation-v1.md) 和 [T02-B 历史验收](T02B_WEB_DATA_ENTRY.md)。

## 来源、许可与固定版本

采用 OpenAssistant 志愿者贡献的 OASST1 对话数据。数据卡标注 Apache-2.0，官方 FAQ 同时确认数据许可。
保存该 revision 的完整 LICENSE 和 README.md。数据经过筛选、角色映射和 JSONL 序列化，问答文本保持上游原文。
归档、训练文件与许可及来源记录共同交接。上游许可和数据说明见下列官方来源。

- [固定 revision 数据卡](https://huggingface.co/datasets/OpenAssistant/oasst1/blob/37d790373da332a4c8be24bd29ec1550e7f04c3f/README.md)。
- [固定 revision LICENSE](https://huggingface.co/datasets/OpenAssistant/oasst1/blob/37d790373da332a4c8be24bd29ec1550e7f04c3f/LICENSE)。
- [OpenAssistant 官方许可说明](https://projects.laion.ai/Open-Assistant/docs/faq)。
- [Apache License 2.0 原文](https://www.apache.org/licenses/LICENSE-2.0)。

| 项目 | 固定值 |
|---|---|
| 上游 | `OpenAssistant/oasst1` |
| revision | `37d790373da332a4c8be24bd29ec1550e7f04c3f` |
| 发布导出 | `2023-04-12_oasst_ready.messages.jsonl.gz`，2023-04-12 ready_for_export |
| 导出文件 SHA-256 | `286a6e9a5a413b3272ae9c0b5a20d327983dea1c24342ae28cb244a6da65185c` |
| LICENSE SHA-256 | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` |
| conversation-v1 文件 | `infra/evidence/t02-public-data/oasst1-20230412-en-24.jsonl` |
| 输入大小 / 条数 / 来源树 | 25166 B，小于 1 MiB / 24 / 12 |
| 输入 SHA-256 | `0d7358137f2ba530af9efe99d31e9c8b530c5419d65c6e5d2f2d3d1377bf282f` |

读取完整导出的 88,838 条消息。候选消息要求树状态 ready_for_export、lang=en、review_result 为 true、
deleted 和 synthetic 为 false，文本非空且 UTF-8 不超过 2048 B。缺少审核字段的消息不入选。
根消息要求 role=prompter 且无 parent_id。按 message_tree_id 字典序选择前 12 棵至少有两条合格直接 assistant 回复的树。
每树回复按整数 rank、message_id 排序，取前两条。各取一组根问答，得到 24 条单轮对话。
这 24 条是通用英文小样本，取样用于验证数据流程。铁路领域适配、文本事实质量及微调效果均未验。

将 prompter 映射为 user，assistant 保持，text 原文作为 content。
输入 id 使用 assistant message_id，source_id 使用 message_tree_id。
相同问题的两条原始备选回答同组保留。按 UTF-8、键排序、紧凑 JSON、每条 LF 序列化，无 BOM。
`sample-inventory.json` 逐条记录输入行号、prompt_message_id、assistant_message_id、rank、message_tree_id 和规范样本哈希。
`convert.py` 固定全部筛选、排序及转换逻辑。独立临时目录重跑后输入文件和取样清单逐字节相同。

## 网页请求与真实 CPU 作业

沿用账户 `TieSheAI T01-B CPU`，项目 `TieSheAI-T02B-20261111T003331Z`。
Fork release `data-entry-20261111-v1`，Web `2.5.0-data-entry-f4670e27128c`，
Server 使用官方 `clearml/server:2.4.0`。三仓库源码基点和已有工作区差异记录于 snapshot-before.json。
当前源码与私有适配包、静态发布清单逐文件核对通过。

登录 18080 后从侧栏「数据准备」选择本轮文件，实际点击上传、CPU 提交。
勾选框和上传请求均确认 synthetic_fixture=false。提交前基线与适配层均检查 rail-cpu 空闲。
使用默认 seed=42、validation_fraction=0.25。真实 Worker `tiesheai-rail-cpu:cpu0` 拉取并完成 Task。
参数、远端完整源码快照、CPU 上下文、拉取日志、T02B_PREPARATION_OK、五个上传前哈希均核对通过。

| 资产 | 值 |
|---|---|
| 请求 UUID | `d92f50aa-6098-4060-890a-75c78e832067` |
| 输入 Dataset v1.0.0 | `105c93c7072544a891b46aa1c2737f1c` |
| 处理 Task，completed | `2862b8f03f5e47d6bab99b233909b73a` |
| 输出 Dataset v1.0.0 | `65d2ce482a484ff0a7e2ef6f0f4dbe67` |
| Manifest SHA-256 | `8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f` |
| Agent 源码快照 SHA-256 | `05333fa81e4d7d3f23662cb5ad6143bb7dff03b9845b19b78b14214d04e64ef6` |

网页实际点击选择输出版本，整页刷新后请求、版本与 Manifest 哈希恢复。
随后点击「下载结果」，保存浏览器 download 事件取得的 ZIP。续验沿用同一 UUID 和三个资产，
查询到 completed 后直接检查选择、刷新和下载。本轮总计新增 1 请求、2 个 Dataset、1 个处理 Task 及 2 个必要隐藏项目。

## SDK 回读与划分核验

浏览器 ZIP 为 12325 B，SHA-256 `1ffd18c945c354902c551a008a864edcffccafbd24ba4c4bebe7e0d9957a17b0`。
SDK force_download 回读输出 Dataset 的 data Artifact，ZIP 全字节相等。输入 Dataset 的
conversations.jsonl 与实际网页上传字节相等。两个 Dataset 均为已封存 v1.0.0。
SDK 同时核对处理 Task 的 Manifest/统计 Artifact，与 ZIP 对应成员相同。

| ZIP 文件 | 字节 | SHA-256 |
|---|---|---|
| `train.jsonl` | 17599 | `3852e6b04b80487e69bf7f286ac6edf6e607791c235828b47f14067047ae028f` |
| `sources.jsonl` | 7365 | `c5f80bf26714543e189db3432ab810ca217e20f2506a73d39952ff4cdffdfec1` |
| `validation.jsonl` | 5287 | `53ad388ff76c8b9fcec8ede1e3e3ee0948c086ed9ff9f671eb83c4a65d2aa345` |
| `manifest.json` | 1376 | `8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f` |
| `statistics.json` | 256 | `b629180356c1e62ff20736346601f991f5c48dc9d6b5d221261597a79b6a1470` |

Manifest 对应输入 Dataset ID、版本、输入哈希、请求 ID、Task ID、CPU 核心与脚本哈希和处理参数。
Manifest 内其余四文件的大小、哈希与下载相符，Manifest 自身哈希由 Task 参数、日志与网页选择记录交叉核验。
本地核心独立复算的四个数据/统计/来源文件与 Agent 输出逐字节相同。

输入 24 条全部有效，唯一 24 条，精确重复 0 条。训练 18 条、9 来源组，验证 6 条、3 来源组。
用独立规范 JSON 哈希逐条核对 train/validation，全局无重复，跨集精确样本交集为 0。
sources.jsonl 覆盖全部 24 个输入行和原始样本 ID，24 份取样记录均与上游重现输入一致。
每个 source_id 对应两条记录并全落同一集合。训练/验证 source_id 和连通 group_sha256 交集均为 0。
完整两集来源树列表在 job-verification.json 的 source_ids。

## T03 输入交接

固定读取输出 Dataset `65d2ce482a484ff0a7e2ef6f0f4dbe67`、版本 `1.0.0`，
并核对 Manifest SHA-256 `8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f`。
Dataset 内路径为 `train.jsonl`、`validation.jsonl`。
本地浏览器 ZIP 解包文件位于以下目录，文件哈希见上表。

- `/root/TieSheAI/infra/evidence/t02-public-data/downloaded/train.jsonl`，18 条。
- `/root/TieSheAI/infra/evidence/t02-public-data/downloaded/validation.jsonl`，6 条。
- 机器可读交接 `infra/evidence/t02-public-data/training-handoff.json`。
- 来源/许可附件 `infra/evidence/t02-public-data/sample-inventory.json`、LICENSE、README.md、convert.py 及固定上游导出。
- 已保存浏览器 ZIP、SDK ZIP、五个解包成员及 SDK 作业核验，详见同目录。

后续训练入口需按选定基座的 tokenizer/chat template 读取 messages-only 数据。
当前交接固定数据身份，T03 训练环境、模型 revision 和训练配置等待用户另行安排。

## 实际命令、证据与失败记录

所有脚本和原始材料位于本地忽略目录 `infra/evidence/t02-public-data/`。
命令的完整 argv、UTC 时间、退出码、耗时和 stdout/stderr 文件见 commands.jsonl。表中省略的下载参数以该台账为准。
浏览器各步骤截图以 new-/resume- 开头，网络记录仅保留路径、状态和方法。

| 检查 | 实际命令或证据 | 结果 |
|---|---|---|
| 上游获取、压缩校验及哈希 | `bash -eu -c 'base=…; for file in LICENSE README.md 2023-04-12_oasst_ready.messages.jsonl.gz; do curl …; done; sha256sum …; gzip -t …'` | 0，upstream-files.txt |
| 运行前后基线 | `source infra/agent/env.sh && python -B infra/evidence/t02-public-data/baseline.py before`，同脚本 `after` | 各 0，baseline-before/after.txt |
| 固定取样与核心校验 | `python3 -B infra/evidence/t02-public-data/convert.py infra/evidence/t02-public-data` | 最终 0，convert-final.txt |
| 网页首次真实上传、提交、选择、刷新、下载 | `node infra/evidence/t02-public-data/browser.cjs new` | 8 步操作通过，最终页面错误断言退出 1，browser-new.json/txt |
| 原请求续验、刷新恢复、实际下载 | `node infra/evidence/t02-public-data/browser.cjs resume` | 0，6 步，browser-resume.json/txt |
| SDK 回读、上游转换复现、五成员与来源隔离 | `source infra/agent/env.sh && python -B infra/evidence/t02-public-data/verify.py resume` | 0，sdk-job.txt、job-verification.json |
| 服务、Git、旧对象及历史 Artifact 保护 | `source infra/agent/env.sh && python -B infra/evidence/t02-public-data/protection.py` | 最终 0，protection-final.txt、protection-result.json |
| 文档与最终交付 | `python3 -B infra/evidence/t02-public-data/delivery.py` | 0，delivery.txt、delivery-result.json |

首轮来源结构探测对无 parent_id 的根消息直接索引出现 KeyError，随后按可选字段处理。
首轮转换对缺少 review_result 的消息直接索引退出 1，随后用 get，缺字段排除，最终校验退出 0。
最初只读 API 探测的 jq 不可用，已用 Python 解析固定 revision，不影响后续获取与哈希检查。
首次浏览器 8 步均完成，最终零页面错误断言退出 1。捕获的两条 `le` 在 T02-B 历史 full-browser.json
也有记录，均同时存在被测试保护阻断的 server.report_stats_option 请求。
复验只接受与历史一致的错误签名并要求同阶段有对应阻断记录，其他页面错误仍会失败。
该页面错误保留为限制，未修复 Fork。复验 6 步退出 0，数据和 CPU 作业由独立 SDK 验收通过。
首轮保护检查将当前项目 last_update 变化判为失败，退出 1。
核对仅当前项目及其 .datasets 父节点时间戳因新对象更新，另有 rail-cpu 的 last_update 更新。
检查调整为仅允许这些时间戳差异，最终退出 0，保留初轮证据。

## 保护结果与遗留范围

前后七容器 ID、镜像、StartedAt、RestartCount 和健康状态一致，均 healthy。
Agent 与适配服务 PID、运行起始时间、重启次数一致。发布清单前后通过，三仓库 HEAD/index、
两个 Fork 源码工作区、旧业务对象、偏好及 20 个历史 Task Artifact 哈希通过核对。
本轮实际修改为本报告、STATUS、HANDOFF、ROADMAP，以及忽略目录下公开样本、核验脚本、证据和交接文件。
当前项目必要父节点及队列时间戳更新已单列。

本次通过范围为 conversation-v1 公开对话 JSONL → 网页上传 → 真实 CPU → 输出 Dataset → 选择恢复与真实下载 → 训练输入交接。
PDF/Word 解析、自动问答、语义去重、大规模处理尚待验。完整 C3、跨用户 Worker、
Fileserver 完整 ACL、外部客户端并发入队、真实网络故障对账及主机启动恢复继续保留。
本轮保留页面 `le` 错误。T03–T08 的训练、GPU、部署、推理、评估及 Pipeline 等待用户明确授权。
