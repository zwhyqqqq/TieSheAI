# T02-B 网页数据准备验收

2026-11-11（Asia/Hong_Kong）限定验收通过。登录 Fork 后，从侧栏「数据准备」打开 [网页入口](http://127.0.0.1:18080/data-preparation)。

选择 conversation-v1 JSONL，点击「上传并登记 Dataset」。上传上限为 1 MiB，默认 seed 为 42，验证组比例为 0.25。点击「提交 CPU 处理」后，页面轮询真实 Task 状态，可打开原生日志和产物。处理完成后，可查看统计、下载 ZIP、打开 Dataset，并保存所选版本与 Manifest SHA-256。刷新页面会恢复请求和选择。

## 接口与发布

原生 Dataset 创建页给出 CLI 和 SDK 示例。现有接口可执行 Task 和文件操作，Dataset 登记、状态文件与封存沿用 Python SDK。Fork 的 `/data-entry/api/` 将固定操作转给 Unix socket 上的适配层。适配层先通过 ClearML 验证当前会话，再以该用户的会话在独立 SDK 进程中执行。输出目录、选择和下载均经同一用户权限查询 Task，归档由认证 Fileserver 提供。SDK 配置仅包含本机服务地址。

上传以请求 UUID、文件哈希和身份绑定记录。服务端串行处理同一请求，写入创建和入队的待核对状态，再执行 ClearML 操作。重复请求返回已有 ID。客户端在刷新后恢复请求编号，选择记录按身份保存。运行台账位于 `infra/.local/data-entry/`，证据位于 `infra/evidence/t02b/`。

Worker 通过 Task 携带源码快照、输入 Dataset ID 和版本、参数与哈希。快照复用 T02-A 核心，Worker 通过 Task 参数回传输出 ID 和封存状态。适配层核对输出归档和 Manifest 后再展示结果。任务使用既有 `rail-cpu` 与 `tiesheai-rail-cpu:cpu0`，其发布版本和配置与作业前基线一致。

| 项目 | 值 |
|---|---|
| Fork release | `data-entry-20261111-v1` |
| Web 版本 | `2.5.0-data-entry-f4670e27128c` |
| Web 源码清单 SHA-256 | `f4670e27128c1f36148075f337ab8ac8c890156aa333107c7863d899cc7d1385` |
| 私有适配包清单 SHA-256 | `b83fce75f7f86a4e7446d5f3d348a55cdda36861af91df9045b8a40ea6eb2b97` |
| 适配服务 | `tiesheai-web-data-entry.service`，仅 Unix socket |
| 运行依赖 | 现有 `clearml-backend` Python 环境和 ClearML SDK 2.1.12 |
| Agent 源码快照 SHA-256 | `05333fa81e4d7d3f23662cb5ad6143bb7dff03b9845b19b78b14214d04e64ef6` |

## 实际资产与结果

本轮唯一项目树为 `TieSheAI-T02B-20261111T003331Z`，请求为 `a8679cf8-070f-4a71-bf3f-278f8d88cc15`。网页上传独立合成样例，使用 seed 73 和验证组比例 0.34。8 条有效输入去重为 7 条，4 个来源组分成训练 6 条和验证 1 条。验证组占 1/4，验证样本占 1/7。

| 资产 | ID |
|---|---|
| 输入 Dataset v1.0.0 | `e33a0984bab14f53aeed3bef921bdac9` |
| 处理 Task，completed | `8cb1b683ccd24937a365a3ec03516e45` |
| 输出 Dataset v1.0.0 | `2d0c777b4e9d4ec9a5ac539ef3931eaa` |
| 保留的 T02-A 输出 v1.0.0，已验证可选择 | `1073a6bcf81e406cbbe5d8dde0d7cd73` |

输出 ZIP 为 2358 字节，SHA-256 为 `48655cd2d4b8cff610561a12c0521d5688f9b3e3f2b74dbe0729568fb91baec1`。Manifest SHA-256 为 `27c929accce791ec9070930f97a021039f1a37f84ddbc33f2ac4b96c049a76ce`。浏览器下载与 SDK 强制回读逐字节相同，ZIP 五成员逐项检查，核心独立复算的四个数据和统计成员也逐字节相同。Task 日志核对了实际 Agent 拉取、完成和源码哈希。

## 实际验证

命令、退出码和耗时见 `infra/evidence/t02b/commands.jsonl`。同目录保存浏览器截图、网络记录、下载、资产库存、任务日志和前后快照。

| 检查 | 实际命令或证据 | 结果 |
|---|---|---|
| T02-A 核心回归 | `python3 -B -m unittest discover -s tests/t02a -p 'test_*.py' -v` | 8 项通过，0 |
| 下载边界回归 | `node clearml-web/tests/artifact-download.cjs` | 36 项通过，0 |
| 适配层隔离测试 | `/root/miniconda3/envs/clearml-backend/bin/python -B tests/t02b/test_adapter.py` | 7 项通过，0 |
| 主应用和 Widgets 正式构建 | `build-main-final.txt`、`build-widgets.txt` | 均为 0，原依赖和样式预算警告仍有记录 |
| 新版发布和资源核验 | `fork-deploy.txt`、`fork-nginx.txt`、`fork-static.txt` | 均为 0，1505 文件哈希通过 |
| 浏览器预检 | `node tests/t02b/browser.cjs preflight preflight` | 匿名 401，会话登录及 T02-A 输出目录通过，0 |
| 浏览器全流程 | `node tests/t02b/browser.cjs full full` | 11 步通过，0 |
| Agent、来源与产物 | `python -B tests/t02b/verify.py job --browser full` | 源码快照、版本、上传字节和输出归档核对通过，0 |
| 新版历史 Artifact 下载 | `node tests/t02b/browser.cjs regression legacy-new` | 下载与历史哈希一致，0 |
| 旧版回退、新版恢复 | `rollback-*.txt`、`restore-*.txt`、`restored-browser.txt` | 两版静态校验、旧版下载、新版选择恢复和原生链接均通过，0 |
| 既有运行与资产保护 | `python -B tests/t02b/verify.py protection`、`python3 -B infra/verify.py` | 原六服务、Agent、13 个历史 Task Artifact 和全量旧资产核对通过，0 |
| 文档、清单与差异检查 | `python3 -B tests/t02b/verify.py delivery` | 证据、引用、源码及私有包清单和 Git 检查，0 |

浏览器实际验证了空文件、超限文件、非法 JSON、非法字段、非法种子和比例。两个重复上传和两个重复提交并发重放，返回相同请求、Dataset 与 Task ID。隔离测试覆盖排队、执行中、Worker 不可用、跨站请求、跨用户请求记录和入队结果待核对。库存核对本轮共新增 4 个项目节点、3 个 Task（含两份 Dataset 承载 Task）。

浏览器阻断偏好、统计和第三方请求，原生页面记录了短错误码 `le`，保存在浏览器证据中。只读目录接口的临时探针曾用错 `Path` 导入，修正后返回预期的历史输入和输出候选。最终正式验收均通过。

## 修改范围

- Web Fork 新增 `src/app/features/data-preparation/` 下的组件、模板和样式，更新 `src/app/app.routes.ts` 与侧栏模板。
- 新增 `integrations/data_entry/` 下的 `common.py`、`operations.py`、`server.py` 和 `worker.py`，复用原 [T02-A 核心](../integrations/data_preparation/prepare.py)。
- 新增 `infra/data-entry/tiesheai-web-data-entry.service`、`infra/web-fork/` 下的 Compose overlay、启动脚本、Nginx 位置片段与 release 打包脚本。原 Compose 和 Nginx 文件与回退基线逐字节一致。
- 新增 `tests/t02b/` 下的命令记录、隔离测试、浏览器测试及验收脚本。更新本报告、STATUS、HANDOFF、ROADMAP、DECISIONS、T02B_TASK 与 [Fork 运维说明](../infra/web-fork/README.md)。

## 回退与恢复

在仓库根目录执行。回退到 `artifact-download-20261110-v1` 并停止适配层，运行台账和两版 release 可继续复用。

```bash
bash infra/web-fork/compose.sh up -d --pull never --wait --wait-timeout 90
systemctl stop tiesheai-web-data-entry.service
```

恢复 T02-B。

```bash
systemctl start tiesheai-web-data-entry.service
bash infra/web-fork/compose-data-entry.sh up -d --pull never --wait --wait-timeout 90
```

## 验收边界

当前验收使用现有普通用户和与之对应的 Agent 身份。跨用户 Worker 作业、完整 Fileserver ACL、原生外部客户端同时入队的竞争及真实网络中断后的人工对账尚待验证。页面支持 1 MiB 以内的 JSONL 和本机已登记的单 ZIP 输出。适配服务手动启停，主机重启后的恢复待验。

T02-A 和 T02-B 均为合成数据限定验收。整个 T02、完整 C3 及公开数据 Demo 仍未完成。T03 和后续阶段等待独立授权。
