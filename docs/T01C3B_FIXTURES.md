# T01-C3-B 首轮：Dataset / Model 受控夹具与页面验证

时间：2026-11-10 16:59（Asia/Hong_Kong）。**本轮实施及采证完成，限定的夹具、版本/父关系、双向链接、可用入口下载验收通过；完整 C3 仍未通过。**
Model GENERAL 的文件按钮只打开 inline JSON，不算浏览器下载通过；Task 输出 Model 的真实下载入口已通过。
Dataset PREVIEW 没有文本预览样本；文件内容验证来自真实页面下载后解包，不以 SDK 成功替代页面测试。
本轮不修改 Web/Server/SDK 源码、部署、鉴权或原业务对象，不入队、不执行 Agent 作业、训练、模型加载或推理。

## 命名空间、对象与状态

写入前由 prepare 建立唯一命名空间 `T01-C3B-Fixture-20261110T084159Z-f57ac4d6`，保存全库存基线与 ledger.json。
没有复用业务项目/Task/Dataset/Model；创建失败/中断不删除对象、不自动造替代对象。
两个 Dataset 同名 `T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text`，v1/v2 分别以 SDK 语义版本 `1.0.0` / `2.0.0` 登记。
Dataset ID 即承载 Task ID，不另计为两个独立对象；两次 create 都显式 `use_current_task=False`。

| 新对象 | ID | 关系、最终状态 |
|---|---|---|
| 专用根项目 | `562f2b1f041240d08096a43c86c6ef34` | `T01-C3B-Fixture-20261110T084159Z-f57ac4d6` |
| SDK 隐藏中间项目 | `adea05224c404ec786bf4707d429c0bd` | 根项目下 `.datasets`，hidden |
| SDK 隐藏 Dataset 项目 | `16a2a0c5fafa468194219a8771d6dd95` | `.datasets/<dataset_name>`，dataset / hidden |
| Dataset v1 / data_processing Task | `276ab235dfdb468b8bef3cd389020794` | 无父版本；started → completed（SDK 本地登记/上传/封存） |
| Dataset v2 / data_processing Task | `1cac2e75863f4f09a5d05b795a275ff3` | 父 `276ab235dfdb468b8bef3cd389020794`；started → completed |
| 专用 testing Draft Task | `388557dbadf6452fba94d9ab5e8f3ce6` | created；输出 Model `62ec3a648ff74162bd1a5c13b844b79d` |
| OutputModel | `62ec3a648ff74162bd1a5c13b844b79d` | Draft / ready=false；创建 Task `388557dbadf6452fba94d9ab5e8f3ce6`；不是训练权重 |

两 Dataset 的正常状态流转已明确授权，不是 Agent 执行。新 Task 的 execution.queue/last_worker 均无 Agent 调度记录，
创建日志无 enqueue/dequeue；原 Queue 条目和 Agent 进程不变。日志事件 worker 字段 `lab` 是本地 SDK 主机标签，不能当作 Agent 作业证据。
附属资产只有各 Dataset 的 data/state 两 Artifact、配置/运行属性、各 7 条日志和 2 条结构/谱系 plot；
Draft Task 日志/plot/Artifact 数为 0，输出 Model 单列。事件返回不含独立 ID，以 task/type/metric/variant/iter/timestamp 标识。
完整台账、服务器实际记录与附属资产见 [ledger.json](../infra/evidence/t01c3b/ledger.json)、[ancillary-assets.json](../infra/evidence/t01c3b/ancillary-assets.json)。

## 文件、远端存储与 SDK 独立验证

使用既有 `clearml-backend` / SDK 2.1.12 和原配置；没有安装依赖、生成凭据或初始化训练 Task。
Dataset upload 指定原 Fileserver；OutputModel 使用
`update_weights(upload_uri='http://127.0.0.1:8081', async_enable=False, auto_delete_file=False)`，随后
`wait_for_uploads(timeout=60)`。以实际服务器 Model URI 及认证下载字节确认上传，未把本地路径登记当成上传。

| 文件 / 存储对象 | 字节 | SHA256 |
|---|---:|---|
| `added.txt`（v2 新增） | 80 | `e296dccd32f0e8637ffa204df206d3d2b38aaa1ce417161fbb4bb3349e941f25` |
| `inherited.txt`（继承 v1） | 71 | `d18ad733395b4a0172de1d3167a85d43df51136581f256cbc12eb270940dd4f6` |
| v1 `data`（实际远端下载） | 197 | `b143e215cfa6000a9c38fcf18976badb02f313bafd03e7a160058a5c9a4ccc9a` |
| v1 `state`（实际远端下载） | 629 | `b84ffc3b358da1c1cfff4184527adbffe1c9eb0cc3bdb074dd2ec092cd871961` |
| v2 `data`（实际远端下载） | 193 | `af949394bedc371f7a8e62e14a70f97c2149934eaf828e6d05c6a171db516e8e` |
| v2 `state`（实际远端下载） | 1061 | `e02adf7acd44faa0645287a019075893e6c9600c658a436ed72449f6ac25a94c` |
| `TEST_FIXTURE_NOT_TRAINED_WEIGHTS.json` | 118 | `3100cf09221f63cbc849518c414f8a9aa761d50be0674e04f2481e36cbb8d7b3` |

v1 ZIP 只含 inherited.txt，v2 ZIP 只含 added.txt；v2 继承文件没有重复上传。
SDK get_local_copy 材料化 v2 为两个文件，各自逐字节和 SHA256 与合成文本一致；state.dependency_graph 明确 v2→v1。
Model JSON 含 `fixture_only=true`、`trained_weights=false`，未调用加载/推理代码。
以下为实际存储 URI，均已真实认证下载 HTTP 200；Artifact 登记的 content_size/hash 与远端字节一致。

- v1 data: `http://127.0.0.1:8081/T01-C3B-Fixture-20261110T084159Z-f57ac4d6/.datasets/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text.276ab235dfdb468b8bef3cd389020794/artifacts/data/dataset.276ab235dfdb468b8bef3cd389020794.yswaa7rf.zip`
- v1 state: `http://127.0.0.1:8081/T01-C3B-Fixture-20261110T084159Z-f57ac4d6/.datasets/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text.276ab235dfdb468b8bef3cd389020794/artifacts/state/state.json`
- v2 data: `http://127.0.0.1:8081/T01-C3B-Fixture-20261110T084159Z-f57ac4d6/.datasets/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text.1cac2e75863f4f09a5d05b795a275ff3/artifacts/data/dataset.1cac2e75863f4f09a5d05b795a275ff3.9k5j2i_o.zip`
- v2 state: `http://127.0.0.1:8081/T01-C3B-Fixture-20261110T084159Z-f57ac4d6/.datasets/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Synthetic-Text.1cac2e75863f4f09a5d05b795a275ff3/artifacts/state/state.json`
- Model: `http://127.0.0.1:8081/T01-C3B-Fixture-20261110T084159Z-f57ac4d6/T01-C3B-Fixture-20261110T084159Z-f57ac4d6-Model-Draft.388557dbadf6452fba94d9ab5e8f3ce6/models/TEST_FIXTURE_NOT_TRAINED_WEIGHTS.json`

详细 SDK 结果：[sdk-verification.json](../infra/evidence/t01c3b/sdk-verification.json)；真实 SDK HTTP/业务码：sdk-http.jsonl、sdk-create-http.jsonl。
SDK 创建/更新的已记录 API HTTP/业务码均为 200/200；文件上传调用的独立 HTTP 状态未由首轮观察器单列，
不能补造上传状态码，成功依据为同步上传返回、wait、服务端 URI 及真实 HTTP 200 下载哈希。
原历史两个 Artifact 在本轮创建后复读，与写入前登记 hash/size 均一致，最终 Smoke 也与固定 fixture 一致；
不声称本轮在创建前重新下载过原文件，见 historical-artifact-check.json。

## 真实页面矩阵

复用已有 Playwright/Chromium 与已有用户；18080、8080 各自新建独立 context，Cookie 不按端口隔离。
从真实 Dataset 卡片/Model 行进入详情；Task information、LINEAGE→CREATED BY、Task→Model 链接均真实点击，
没有用深链冒充列表导航、改 href、手改 URI、route.fulfill 或伪造成功响应。
Fork 运行固定 release `artifact-download-20261110-v1` / `2.5.0-artifact-fix-0b92177bcb35`；
官方 `2.4.0-722`，Server 仍是官方 2.4.0；两 Fork 源码 HEAD、原未提交补丁和运行 release 均未变。

| 检查项 | 18080 Fork | 8080 官方 | 实际证据 / 限制 |
|---|---|---|---|
| Dataset 列表→版本详情 | 通过 | 通过 | 唯一卡片，两个版本均 Final；真实版本列表/关系图 |
| v2→v1 父关系与 ID | 通过 | 通过 | 两图节点、一条父→子箭头；逐个点节点，Task information href 对应完整 ID；SDK state 另独立核对 |
| 文件展示 | 通过 | 通过 | v1 一文件；v2 inherited.txt + added.txt，71/80 B 和完整 SHA256 均显示 |
| Dataset PREVIEW | 无文本预览，N/A | 无文本预览，N/A | 实际 debug_images 200/200、metrics=[]；No preview to show，不能称内容内联预览通过 |
| CONTENT 下载图标 | CLI 命令 | CLI 命令 | 仅显示 clearml-data get --id，不计浏览器下载；未执行该 CLI 代替 UI |
| Dataset 可用浏览器下载 | 通过 | 通过 | Task information→ARTIFACTS→OTHER/data→FILE PATH 旁按钮；每站 v1/v2 两个真实 download |
| Dataset 下载内容完整性 | 通过 | 通过 | 各 ZIP 字节/hash 与已登记远端一致；解包内容比对固定合成文本，再按父关系合并，覆盖继承与新增文件 |
| Model 列表→详情 | 通过 | 通过 | Draft、URL、明确 TEST FIXTURE 描述和 Model ID |
| Model GENERAL 文件按钮 | 仅 inline JSON | 仅 inline JSON | 118 B 内容/hash 正确，但零 download 事件；保留功能限制，不伪称此按钮完成下载 |
| Model→创建 Task | 通过 | 通过 | LINEAGE/CREATED BY 链接 href 与弹出页均为 `388557dbadf6452fba94d9ab5e8f3ce6` |
| Task→输出 Model | 通过 | 通过 | ARTIFACTS/OUTPUT MODELS 的 MODEL NAME 链接及新详情页均为 `62ec3a648ff74162bd1a5c13b844b79d`；Draft Task 保持 created |
| Model 可用浏览器下载 | 通过 | 通过 | 上述 Task 输出 Model 名称旁下载按钮；每站真实 download，118 B、逐字节及 SHA256 正确 |
| 输入模型消费关系 | N/A | N/A | 未创建消费 Task，无样本，不以输出关系替代 |

每站 24 个页面步骤；每站 3 份真实下载：v1 197 B、v2 193 B、Model 118 B。
最终采用的完整步骤、URL、DOM、截图、响应字段和下载事件分别见：
- 18080: [accept-18080-r7-browser.json](../infra/evidence/t01c3b/accept-18080-r7-browser.json)；截图 `accept-18080-r7-*.png`，下载文件 `accept-18080-r7-download-*`。
- 8080: [accept-8080-r6-browser.json](../infra/evidence/t01c3b/accept-8080-r6-browser.json)；截图 `accept-8080-r6-*.png`，下载文件 `accept-8080-r6-download-*`。

另保留一个显示口径差异：两站 Task Artifact 的 PREVIEW 字符串为 `inherited.txt - 116 bytes` /
`added.txt - 116 bytes`。SDK `utilities/parallel.py:297` 使用正在写入的 ZIP 的 `self.size`，
该属性取磁盘归档大小，并非单文件原始大小；dataset.py 将该字符串作为 Artifact preview 登记。
因此不能把 116 当作文件大小；CONTENT 表和 ZIP 头的原文件大小正确为 71/80 B，下载无损。
源码摘录与归档头见 sdk-preview-source.json；本轮不修改 SDK 或已有 Artifact 记录。

浏览器落盘的 ZIP 经 check.py 独立解包/比对，不是重新用 SDK 下载来冒充页面下载。
SDK 底层验证单列；只有实际页面/下载事件支持上表页面结论。

## HTTP、控制台和保护

只读清单沿用 C3-A 的 68 项，加一项源码审阅的 events.debug_images，且请求 metrics.task 必须属于本轮两 Dataset ID。
契约来源为 services/events.py:856–881、bll/event/metric_events_iterator.py 的 ES 查询和可选 Redis 翻页缓存；
不会修改 Task/Model/队列/用户设置。默认仍拒绝未知端点；偏好/统计/第三方请求继续 route.abort，HTTP/业务码 N/A。
初轮两站 PREVIEW 的 debug_images 均被未知端点保护阻断；这些原证据保留，不记作当时预览验收通过。

| 最终正式轮 | API 响应 / 端点 | HTTP/业务码 | 控制台 error/warning | 结构化 window 错误 | 阻断 |
|---|---|---|---|---|---|
| 18080 | 129 / 28 | 均 200/200（auth.login 不读取响应体） | 49 / 0 | 19，均与精确阻断 URL 对应 | {'third-party': 8, 'Server statistics option write': 7, 'User settings write': 12} |
| 8080 | 137 / 28 | 均 200/200（auth.login 不读取响应体） | 60 / 0 | 0，均与精确阻断 URL 对应 | {'third-party': 8, 'Server statistics option write': 7, 'User settings write': 13} |

Fork 下载均走同源 /files、HTTP 200；无 CORS 错误。官方 Dataset Archive 首次 credentialed fetch
仍出现 CORS/ERR_FAILED，随后由应用原导航回退真实下载成功（Fileserver inline→attachment）；两阶段原始证据均保存。
Model GENERAL 实际响应为 inline；Task 输出 Model 的实际响应/事件按真实网络保存，没有改响应头。
Fork 可选 credentials.json/onboarding.json 仍为 404，属于已记录的配置回退；未将其伪装为 200。
最终无未分类控制台错误/警告；每条日志按具体文字、阶段、结构化参数、URL 和 requestfailed 关联，
不是按 ERROR le/j 通配忽略。Fork 的 window HttpErrorResponse 与 Playwright pageerror 是同一事件的两种观察，
逐条按阶段、constructor/message、时间差 <2 秒及已阻断 URL 一对一关联，原记录不删除。
GitHub fetch TypeError 的归因为同阶段被阻断请求与堆栈推断，未声称已修复第三方行为。
偏好/统计/第三方仍为受限未验证；控制台逐条分类见 *-console-review.json，网络/下载总表见 browser-results.json。

## 运行、库存和 Git 保护

写入前保存 snapshot-before.json、inventory-before.json、protected-files-before.json、pip freeze；
七容器的 ID/Created/StartedAt/RestartCount/健康/挂载/端口/网络、Agent PID/启动时间/重启次数、
凭据 inode/mtime/ctime/权限及 Python 依赖前后一致，七容器 healthy、RestartCount=0。
原 Compose/Agent/unit/凭据文件另与已有 C2 哈希复核一致；Web 2483、Server 323 个源码文件、
C2 v2 和下载修复 release 各 1502 文件哈希均与本轮 before 一致。在线版本与固定 release 一致。
所有历史完整项目/Task/Model 记录、历史两个 Artifact 字节、偏好哈希、两条 Queue 的完整记录/entries 均未变。
新增集合严格等于台账：3 项目、3 Task、1 Model；没有 Pipeline、Queue、凭据或额外测试对象。
保存全部三仓库 HEAD/index/原 diff，原 Web 七文件修复、根仓库已有修改均保留，无暂存/提交/push。
保护结果见 preservation-result.json、inventory-comparison.json、historical-artifact-check.json；
这些是本轮复验，历史 Smoke 执行/构建/回退记录没有重跑或冒认。

## 可复验脚本、实际命令与退出码

脚本与操作：[tests/c3b/README.md](../tests/c3b/README.md)。首次创建已执行，复验请沿用现有台账，
不要删除台账或另开命名空间。fixtures.py prepare 拒绝已有台账，snapshot.py before 拒绝覆盖基线；
pending 未知创建会停止，已知 ID 按台账续跑，创建响应 ID 即时写入 created-ids.jsonl。
所有正式命令的完整 argv、UTC 起始时间、耗时、退出码和输出位置见 [commands.jsonl](../infra/evidence/t01c3b/commands.jsonl)。

| 实际命令（工作目录 /root/TieSheAI） | 结果 / 退出码 | 主要证据 |
|---|---|---|
| python3 -B infra/evidence/t01c3b/snapshot.py before；pip freeze；python3 -B infra/verify.py 前后 | 全部 0 | snapshot-before/after.json、python-before/after.txt、services-before/after.txt |
| source infra/agent/env.sh 后 python -B tests/c3b/fixtures.py prepare | 0；先建台账，零服务器写入 | prepare.txt、ledger.json、inventory-before.json |
| python -B tests/c3b/fixtures.py create | 0；两 Dataset 上传封存、Draft+OutputModel 真实上传 | create.txt、created-ids.jsonl、sdk-create-http.jsonl |
| python -B tests/c3b/fixtures.py verify / assets / history / compare | 全部 0 | sdk-verify.txt、ancillary-assets.txt、historical-artifacts.txt、final-inventory.txt |
| node tests/c3b/browser.cjs 18080 r7 | 0；24 步及 3 份真实下载 | browser-18080-r7.txt、accept-18080-r7-* |
| node tests/c3b/browser.cjs 8080 r6 | 0；24 步及 3 份真实下载 | browser-8080-r6.txt、accept-8080-r6-* |
| python3 -B tests/c3b/check.py browser | 最终 0；下载内容、页面 ID、HTTP/错误/阻断复核 | browser-analysis-final.txt、browser-results.json |
| python3 -B tests/c3b/check.py preservation | 0 | preservation.txt、preservation-result.json |
| python3 -B tests/c3b/check.py delivery | 最终 0 | delivery.txt、delivery-result.json |
| python3 -B infra/evidence/t01c3b/finalize.py | 0；全部新脚本语法/实际凭据字面量/结果核对 | final-check.txt、result.json |

所有退出 1 的原证据保留：首次 browser.cjs 多一个右括号的 SyntaxError；Fork r2 的 Task information
可访问名称精确匹配不符；官方 r3/r4 的 SVG 绘制时序及竖直 path 零宽度 visible 判定错误；
早期 browser-analysis 发现 debug_images 未审阅阻断；Fork r6 把同一受阻请求的两种错误观察误当新增未知错误。
均修正测试/采证器后通过，未修改产品源码/配置或伪造成功响应。探索脚本 exit=0 只代表采证，
内部 tooltip/版本文字/关闭面板/tab 定位失败及原截图保留，不计通过；部分探索 rg 路径不存在退出 2，非服务故障。
OutputModel.id 在真正上传前为 None，是 SDK 延迟创建行为；创建响应 ID 已即时落日志，
随后仅补齐本地台账，未重复造 Model。最终脚本在该响应到达时立即持久化 model ID。

## 实际修改和边界

新增本文、tests/c3b 的夹具/浏览器/审核/快照/命令记录脚本、只读契约和 README；
兼容报告只追加本轮矩阵，更新 STATUS/HANDOFF，并在 DECISIONS 记录本轮授权边界。
本轮证据全部位于已忽略 infra/evidence/t01c3b/，不加入 Git；保留原始失败、截图和已创建对象。
Model GENERAL 直按钮零下载事件、Dataset 文本内联预览无样本、输入 Model 消费 N/A；Artifact PREVIEW 的中间 ZIP 大小口径另有说明。
最终创建脚本补强 ID 即时落盘与续跑保护后完成语法审阅；未再创建第二套夹具，未做真实故障注入/失败恢复实验。无自动修复或清理。
Pipeline、四风险端点（原报告所列）、分享权限、角色/完整文件权限、真实其他存储签名、
Server Fork 运行、GPU、远程和运维项目仍须另验。后续任务须用户明确授权，不自动进入 T02 或其他阶段。
