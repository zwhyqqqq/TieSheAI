# T01-C3-A：只读页面与 API 兼容性检查

记录时间：2026-11-10 09:11（Asia/Hong_Kong）。

**本轮检查与问题记录已完成；完整 T01-C3 未通过。** 18080/8080 的受限只读矩阵
覆盖现有数据，发现 Fork Artifact 下载按钮的实际行为差异。没有修复代码或部署配置，
没有创建业务对象。C3-B、完整 C3、Server Fork 运行、T02 均未执行。

## 版本、范围与证据规则

- Fork：18080，Web package 2.5.0，源码 `be71d50e7504eb00a2e09900fabbe8697ed23558`，
  C2 固定只读 release `c2-be71d50-v2`，运行标识 `2.5.0-fork-be71d50-c2`。
- 官方对照：8080，Web `2.4.0-722`；两站复用同一原官方 Server 2.4.0 / Fileserver。
  Server Fork `2ebdc43951b9432cc7fa528bbb3a7100fc6fe805`，未启动。
- 根 HEAD `2416ec050809c7b9ec5f991341c27c462cef29f8`；保留检查前全部未提交成果，
  包括 ROADMAP、C2 配置/报告及 DECISIONS。两 Fork 干净，HEAD/暂存区未变。
- 复用 C2 Playwright 1.56.1 / Chromium 141.0.7390.37；每站新建独立 context、用既有
  `TieSheAI T01-B CPU` 用户真实登录。Cookie 不能按端口隔离，未共用 context/profile。
- 原始证据：[infra/evidence/t01c3/](../infra/evidence/t01c3/)，受 Git 忽略，目录 0700。
  保存 HTTP/业务状态、请求参数、响应字段类型/长度、控制台/异常、实际下载、截图，
  不存认证头、Cookie/token 值或登录响应体，不读取 SDK 凭据文件。
- `matrix-<port>-browser.json` 逐步记录 URL、实际动作代码、DOM、截图、端点、字段、
  控制台和阻断。主矩阵每站 22 项，另每站 7 项补测、5 项空态深链复核；前置探测单列。
  `matrix-analysis.json` 按实际 Server 契约复核字段；原始观察器误将 `_ex` 及 Reports
  当作单数对象的标签已注明更正，不修改实际响应、不将标签错误算作后端缺陷。

## 只读允许清单与保护

精确端点清单见 [allowlist.json](../infra/evidence/t01c3/allowlist.json)，共 **68** 项，
每项记录契约来源/源码行和原因；按服务实现的查询/聚合/投影审阅，不按 HTTP GET/POST
或 `get_*` 名称放行。`auth.login` 单列为本轮授权的既有用户认证动作，不创建 API 凭据。
所有未审阅端点默认拒绝；不伪造成功响应，不覆盖页面链接，不解除鉴权。

| 服务 | 本轮明确允许的动作（均带此前服务名前缀） |
|---|---|
| projects | get_by_id, get_all, get_all_ex, get_hyper_parameters, get_hyperparam_values, get_model_metadata_keys, get_model_metadata_values, get_model_tags, get_project_tags, get_task_parents, get_task_tags, get_unique_metric_variants, get_user_names |
| tasks | get_all, get_all_ex, get_by_id, get_by_id_ex, get_configuration_names, get_configurations, get_hyper_params, get_types |
| models | get_all, get_all_ex, get_by_id, get_by_id_ex, get_by_task_id, get_frameworks |
| events | get_multi_task_metrics, get_multi_task_plots, get_scalar_metric_data, get_scalar_metrics_and_variants, get_task_events, get_task_latest_scalar_values, get_task_log, get_task_metrics, get_task_plots, get_task_single_value_metrics, get_vector_metrics_and_variants, multi_task_scalar_metrics_iter_histogram, scalar_metrics_iter_histogram, vector_metrics_iter_histogram |
| queues | get_all, get_all_ex, get_by_id, get_default, get_num_entries, get_queue_metrics, peek_task |
| workers | get_activity_report, get_all, get_count, get_metric_keys, get_stats |
| users | get_all, get_all_ex, get_current_user, get_preferences |
| organization | get_entities_count, get_project_workloads, get_tags, get_user_companies |
| reports | get_all_ex, get_tags, get_task_data |
| 其他 | server.info, debug.ping, login.supported_modes；auth.login 仅认证 |

特别排除 `queues.get_next_task`（会取走/分派任务）、入队/出队、Task 状态更改、
Pipeline 启动/删除、偏好/统计设置写入、reports.share。四个风险接口不会因客户端
声明而自动进入允许清单，也没有构造请求来强行触发它们。

保护允许既有本地 8008 API、8081 文件及站点资源的读取；外部 GitHub/updates 等全部
阻断，非 API 本地写请求亦拒绝。对每条阻断记录 URL/阶段/原因和对应 requestfailed。
全轮 159 条阻断均有同 URL、同阶段的失败记录，见
[blocked-correlations.json](../infra/evidence/t01c3/blocked-correlations.json)：
偏好写入 63、统计选项写入 44、第三方请求 52；**全部为受限未验证，不计兼容通过**。
主矩阵 F/O 分别阻断 35/34 条；详细逐条记录保留，不把 ERROR le/j 等 minified 名称通配忽略。

## 页面 / API 只读矩阵

F=18080 Fork，O=8080 官方；表中“200/200”为 HTTP/业务码。主矩阵含前后库存读取，
每站实际覆盖 33 个认证/读取端点，API 响应 F 126 / O 130 条，HTTP 均 200；除刻意不读
响应体的 auth.login 外，已解析业务码均 200。字段检查基于实际 `data` 结构，缺字段 0；
这只证明本轮使用到的字段与现有数据可读取，不证明所有可选字段、权限角色或无样本详情。
共同引导接口 S：login.supported_modes、server.info、users.get_current_user/get_preferences。

控制台标记：R=保护阻断（读写相关项目受限未验）；L=Fork 可选 JSON 404 回退；
N=两站 NG0953 切页警告，业务根因未定位；A=官方空态示例编辑器偶发 ace 未定义。
R/L 不掩盖其他问题；N 与 A 均单独保留。每页完整 console/errors/failed 见同名浏览器 JSON。
表内错误/警告/异常/阻断是对应采证阶段的实际条数，包含保护引起的日志；
异步轮询可能跨阶段到达，不将到达阶段等同唯一业务触发点。

| 检查项 | 实际操作 | 实际功能 API（另有 S） | HTTP/业务码、前端字段/显示 | 控制台与结论 | 截图 F / O |
|---|---|---|---|---|---|
| Projects 列表 | 访问 /projects；读取卡片与数量 | `projects.get_all_ex`, `projects.get_project_tags`, `projects.get_user_names` | 200/200；projects[].id/name/stats/sub_projects；F 根列表 1 项、O 2 项，差异由 shallow_search 解释 | F 控制台6错/0警、异常2、阻断3（R,L）；O 控制台6错/0警、异常0、阻断3（R）。只读列表可用，卡片数差异另解 | [F](../infra/evidence/t01c3/matrix-18080-projects-list.png) / [O](../infra/evidence/t01c3/matrix-8080-projects-list.png) |
| Projects 筛选/层级导航 | 点击搜索图标，输入 TieSheAI、清空，再实际点击 TieSheAI → Smoke | `projects.get_all_ex`（真实搜索；补测） | 200/200；筛选返回可见卡片；最终进入已有 Smoke 项目任务页 | F 控制台7错/0警、异常3、阻断4（R,L）；O 控制台8错/0警、异常0、阻断4（R）。定位器补测成功；无数据写入 | [F](../infra/evidence/t01c3/supplement-18080-projects-filter-visible.png) / [O](../infra/evidence/t01c3/supplement-8080-projects-filter-visible.png) |
| 已有项目详情 | 深链 /projects/<project>/overview | `organization.get_tags`, `projects.get_all_ex`, `projects.get_model_tags`, `projects.get_task_tags`, `projects.get_user_names` | 200/200；项目名称/导航显示，overview 为已有项目未填写的空内容 | F 控制台6错/0警、异常2、阻断3（R,L）；O 控制台6错/0警、异常0、阻断3（R）。只读已有空 overview；编辑未验 | [F](../infra/evidence/t01c3/matrix-18080-project-overview-deep.png) / [O](../infra/evidence/t01c3/matrix-8080-project-overview-deep.png) |
| Experiments 列表 | 深链进入已有项目任务列表；读取三个历史 Task | `organization.get_tags`, `projects.get_all_ex`, `projects.get_model_tags`, `projects.get_task_parents`, `projects.get_task_tags`, `projects.get_user_names`, `tasks.get_all_ex`, `tasks.get_types` | 200/200；tasks[].id/name/status/type/project；2 completed、1 failed | F 控制台6错/0警、异常2、阻断3（R,L）；O 控制台6错/0警、异常0、阻断3（R）。3 个历史任务可读，failed 为既有 | [F](../infra/evidence/t01c3/matrix-18080-experiments-list.png) / [O](../infra/evidence/t01c3/matrix-8080-experiments-list.png) |
| Task 导航/详情 | 双击实际任务行；再深链目标 Task execution | `organization.get_tags`, `projects.get_all_ex`, `projects.get_model_tags`, `projects.get_task_tags`, `projects.get_user_names`, `tasks.get_by_id_ex` | 200/200；tasks[]/execution/script；标题与 completed、脚本/CPU 执行信息 | F 控制台7错/0警、异常3、阻断4（R,L）；O 控制台8错/0警、异常0、阻断4（R）。真实行导航/深链可读 | [F](../infra/evidence/t01c3/matrix-18080-task-execution-deep.png) / [O](../infra/evidence/t01c3/matrix-8080-task-execution-deep.png) |
| Task 参数 | 实际点击 CONFIGURATION；补测再点击 Smoke 分组 | `tasks.get_configuration_names` | 200/200；hyperparams.Execution/Smoke；limit=10000、expected_sum_squares=333383335000 | F 控制台6错/0警、异常2、阻断3（R,L）；O 控制台6错/0警、异常0、阻断3（R）。Smoke 参数可读；保存未验 | [F](../infra/evidence/t01c3/supplement-18080-task-parameters-smoke-click.png) / [O](../infra/evidence/t01c3/supplement-8080-task-parameters-smoke-click.png) |
| Task 日志 | 实际点击 CONSOLE | `events.get_task_log` | 200/200；events[] 的 msg/timestamp/level；看到 Process completed successfully | F 控制台0错/0警、异常0、阻断0；O 控制台0错/0警、异常0、阻断0。历史日志可读 | [F](../infra/evidence/t01c3/matrix-18080-task-log.png) / [O](../infra/evidence/t01c3/matrix-8080-task-log.png) |
| Task 指标 | 实际点击 SCALARS，等待 Plotly 图表 | `events.get_task_single_value_metrics`, `events.scalar_metrics_iter_histogram`, `tasks.get_all_ex` | 200/200；标量直方图任务/metric/variant 结构；cpu_smoke/check_passed=1 | F 控制台0错/0警、异常0、阻断0；O 控制台0错/0警、异常0、阻断0。标量图可读；其他图表缺样本 | [F](../infra/evidence/t01c3/matrix-18080-task-metrics.png) / [O](../infra/evidence/t01c3/matrix-8080-task-metrics.png) |
| Task Artifact 详情 | 点击 ARTIFACTS → cpu-smoke-json 原有条目 | `tasks.get_by_id_ex` | 200/200；artifact uri/hash/content_size/type_data；122 B、固定 SHA256 | F 控制台0错/0警、异常0、阻断0；O 控制台0错/0警、异常0、阻断0。详情可读；下载另列未通过 | [F](../infra/evidence/t01c3/matrix-18080-task-artifacts.png) / [O](../infra/evidence/t01c3/matrix-8080-task-artifacts.png) |
| Workers / Agent | 从实际侧栏进入 Workers；补测深链复核 | `workers.get_activity_report`, `workers.get_all` | 200/200；workers[]、activity report 的 active/total.counts/dates；既有 tiesheai-rail-cpu:cpu0 与 rail-cpu | F 控制台1错/0警、异常1、阻断1（R）；O 控制台2错/0警、异常0、阻断1（R）。既有 Worker 状态可读 | [F](../infra/evidence/t01c3/matrix-18080-workers-navigation.png) / [O](../infra/evidence/t01c3/matrix-8080-workers-navigation.png) |
| Queues | 从顶部 QUEUES tab 实际导航，补测成功；另测深链 | `projects.get_user_names`, `queues.get_all_ex`, `queues.get_queue_metrics` | 200/200；queues[].id/name/entries/workers；default、rail-cpu 两队列，空队列 | F 控制台1错/1警、异常1、阻断1（R,N）；O 控制台2错/1警、异常0、阻断1（R,N）。列表/统计可读，排队操作未验 | [F](../infra/evidence/t01c3/supplement-18080-queues-top-navigation.png) / [O](../infra/evidence/t01c3/supplement-8080-queues-top-navigation.png) |
| Datasets | 实际点击侧栏 Datasets；再做独立深链与 reload | `projects.get_all_ex`, `projects.get_project_tags` | 200/200；projects[] 为空；请求明确 system_tags=dataset，显示 NO DATASETS TO SHOW | F 控制台1错/1警、异常1、阻断1（R,N）；O 控制台2错/1警、异常0、阻断1（R,N）。仅列表/空态，详情版本未验；官方深链另有 A | [F](../infra/evidence/t01c3/matrix-18080-datasets-navigation.png) / [O](../infra/evidence/t01c3/matrix-8080-datasets-navigation.png) |
| Models | 深链 /projects/*/models | `models.get_all_ex`, `models.get_frameworks`, `organization.get_tags`, `projects.get_model_tags`, `projects.get_user_names` | 200/200；models[] 为空；framework/tag 响应，显示 No data to show | F 控制台6错/0警、异常2、阻断3（R,L）；O 控制台6错/0警、异常0、阻断3（R）。仅空列表，详情关系未验 | [F](../infra/evidence/t01c3/matrix-18080-models-list-deep.png) / [O](../infra/evidence/t01c3/matrix-8080-models-list-deep.png) |
| Pipelines | 实际侧栏进入；深链 reload 与独立复验 | `models.get_all_ex`, `projects.get_all_ex`, `projects.get_project_tags` | 200/200；projects[] 为空，system_tags=pipeline/type=controller；显示 NO PIPELINES TO SHOW | F 控制台7错/1警、异常3、阻断4（R,L,N）；O 控制台9错/1警、异常0、阻断4（R,N,A）。仅列表/空态，DAG/运行未验；N/A 问题保留 | [F](../infra/evidence/t01c3/matrix-18080-pipelines-navigation.png) / [O](../infra/evidence/t01c3/matrix-8080-pipelines-navigation.png) |
| Reports 读取背景 | 只读打开 Reports 列表，辅助 share 风险分类 | `projects.get_all_ex`, `projects.get_user_names`, `reports.get_all_ex`, `reports.get_tags` | 200/200；data.tasks[] 为空（不是 data.reports） | F 控制台6错/0警、异常2、阻断3（R,L）；O 控制台6错/0警、异常0、阻断3（R）。仅空列表；share 只作静态分析 | [F](../infra/evidence/t01c3/matrix-18080-reports-list-static-context.png) / [O](../infra/evidence/t01c3/matrix-8080-reports-list-static-context.png) |

项目真实层级导航补测截图 `supplement-<port>-project-navigation-visible.png`；
任务列表双击记录为 `matrix-<port>-task-navigation`。原参数页先显示 Execution，
补测点击 Smoke 后看到 `limit=10000` 等固定参数。没有点击保存、编辑、运行或示例代码执行。
前端的 `tasks.get_by_id_ex` 返回 `data.tasks[]`，`reports.get_all_ex` 也返回
`data.tasks[]`；字段校验依据运行实现（tasks.py:258、reports.py:179），不能误要求单数 task/reports。

Dataset 请求包含 `search_hidden=true`、`system_tags=[dataset]`、
`include_stats_filter.type=[data_processing]`、`include_dataset_stats=true`，结果 projects=[]。
Pipeline 请求包含 `system_tags=[pipeline]`、`include_stats_filter.type=[controller]`，
结果 projects=[]。Models 列表 models=[]，前后库存 models=[]。没有用普通 Smoke Task
充当 Dataset/Model/Pipeline 样本；所有详情、版本/输入输出关系、DAG、运行与操作均缺数据未验。
队列无排队任务，不能验证 queued 状态、出队弹窗、任务调度或队列顺序。

## Artifact：实际页面点击与真实下载

两站均从 **ARTIFACTS → cpu-smoke-json** 原有条目进入；再点击 FILE PATH 链接及相邻
下载按钮。没有改 DOM href，没有手工把 8081 链接替换成 /files，没有用脚本代理读取冒充 UI 下载。

| 实际动作 | F 18080 | O 8080 | 结论与证据 |
|---|---|---|---|
| 原路径链接 | 弹出原绝对 127.0.0.1:8081 页面，HTTP 200，显示 122 字节 JSON | 同样 HTTP 200、JSON | 两站链接读取通过；matrix-*-browser.json 的 artifactPopups |
| 详情页下载按钮 | 首次 fetch 返回 HTTP 200 但 CORS 拒绝；无 download 事件，回退只打开 inline JSON | 首次 fetch 同样 CORS 拒绝；回退后产生 cpu-smoke.json 下载 | **Fork 下载不通过**，官方回退能完成下载；主矩阵与补测各复现一次 |
| 最终响应 | Content-Disposition: inline; filename=cpu-smoke.json | attachment; filename=cpu-smoke.json，实际文件已保存且 SHA256 一致 | supplement-*-browser.json 的 corsHeaders/downloads/allOpenPages |
| /files UI 使用 | 本轮实际 Artifact 点击未生成 /files 请求 | 本轮同样未生成 /files 请求 | UI 代理分支未覆盖，不能计通过；C2 的手工认证代理读取历史证据不代替本项 |

原路径打开后的 DOM 文本哈希与官方实际下载文件哈希均为
`b00ed20e939a658612bc0586861bf1af2ece002c6b20bcfee5255194592555a9`。
真实下载证据：`matrix-8080-download-0-cpu-smoke.json`、
`supplement-8080-download-0-cpu-smoke.json`；Fork 两次均没有下载文件。
网络观察到 Access-Control-Allow-Origin=*、缺少 Access-Control-Allow-Credentials；
credentialed fetch 被浏览器拒绝，并有 requestfailed，而不是 API 业务码失败。

**P2 / C3 功能缺口：Fork 的历史 Artifact 下载按钮未完成下载。** 源码解释与实测一致：

- [url.ts](../clearml-web/src/app/shared/utils/url.ts) 第 3–4 行，仅用
  `url.startsWith(HTTP.FILE_BASE_URL)` 识别 Fileserver。
- Fork 运行配置 FILE_BASE_URL 是 `/files`，历史 URI 为绝对 8081，匹配失败；
  [base-admin.service.ts](../clearml-web/src/app/webapp-common/settings/admin/base-admin.service.ts):65–84
  的 Fileserver 分支也受此判断影响。此处为源码归因，不声称读取了官方运行配置内部对象。
- [common-experiments-info.effects.ts](../clearml-web/src/app/webapp-common/experiments/effects/common-experiments-info.effects.ts):403–446
  先执行 credentials=include 的 fetch；失败回退到导航时，只有识别为 Fileserver 才加 download。
  官方最终 attachment 下载、Fork inline JSON，与该分支差异一致。
- 这是现有部署/历史绝对 URI 与新 Web 的组合差异；不能据 CORS 共同出现，就把 Fork
  下载失败全部归为后端故障。C2 的基本代理读取通过结论保留，未曾覆盖此真实按钮流程。

最小修复建议（**未实施、须另授权**）：对明确配置的 Fileserver 源地址/历史别名作 URL
规范化，统一到同源 /files 后再签名/下载，验证 download 参数与响应处理；不泛化重写任意
外部 URL，不关闭鉴权，不先全局放开 Fileserver CORS，不先改 Server API。
下一轮仍应从原页面点击并检查 download 事件/文件哈希，不能仅测代理 URL。

## 与官方站的其他差异和未定位问题

1. **项目根卡片数量不同，但读取契约一致。** F root projects.get_all_ex 使用
   shallow_search=true，O 为 false；相同后端分别返回 1/2 项。F 点击 TieSheAI → Smoke
   与搜索均能取得现有子项目。源码
   [common-projects.effects.ts](../clearml-web/src/app/webapp-common/projects/common-projects.effects.ts):135
   明确按搜索/标签决定 shallow_search；这不是数据丢失或 API 缺字段的证据。
2. **L：可选运行 JSON 回退。** F 主矩阵 credentials.json/onboarding.json 共 18 次 404，
   没有伪装为 index 的 200；已有用户仍登录成功。O 没有这些 404。未导出这些文件内容，
   不将此项等同缺失 JS/字体，也不宣称可选 onboarding 的全部行为通过。
3. **R：保护相关错误。** F 主矩阵有 25 个结构化 HttpErrorResponse，全部 status=0、URL
   对应明确阻断请求；O 相同保护更多由 Angular ErrorHandler 以 ERROR j 写到 console。
   console 原文、逐条失败请求保留；未把 minified 名称一概视为正常。偏好/统计写入与第三方
   功能均受限未验，没有返回伪造成功。
4. **N：两站共有 NG0953 warning。** 主矩阵分别在离开任务/队列进入 Dataset、Model
   转入 Pipeline 附近出现，共各 2 次。安装的 Angular core `_resource-chunk.mjs`:40
   将 953 的 warning 用于已销毁 OutputRef 的 emit；具体业务组件/异步来源尚未定位。
   页面本轮列表显示仍完成，但不把这条 warning 消除或通配忽略，也不能宣称完整生命周期无误。
5. **A：官方空态指南偶发 ace 未定义。** 主矩阵在 O pipelines-deep 记录
   `ReferenceError: ace is not defined`；独立 context 复查 /pipelines 和 /datasets 的深链/reload，
   O datasets-reload 再记录该错误，F 本轮复查未出现。对应指南代码编辑区可能不显示，
   但 API 仍 200/200、空数据成立。属于官方对照页也有的前端/资源时序问题；具体根因未定位，
   不算 Fork 新引入的 API 阻塞。原始 console 堆栈和 empty-recheck-8080-*.png 保留。

## 四个历史风险端点

“未实际调用”的响应为 **N/A**，不写成 200 或 404；没有以客户端声明判定实际阻塞。
受检代码没有 handler 并不替代运行时端点探测。本轮未向这四个路径发起人工 API 请求。

| 风险端点 | Web 源码位置、触发条件 | Server 契约/静态状态 | 本轮实际调用/响应/影响 |
|---|---|---|---|
| pipelines.check_new_run | pipelines.service.ts:73–74；run-pipeline-controller-dialog.component.ts:171–190。创建新 Pipeline 选项开启、有 baseController task 且 project/name 非空时，400ms 防抖查询已有名称 | 受检 services/pipelines.py 与 pipelines.conf 无活动定义；Fork release 有字符串、官方 Web 未见该字符串 | 未调用，N/A；无 controller/Pipeline 样本，不打开运行流程。潜在条件性兼容风险，未计通过，当前空列表不受阻 |
| queues.get_by_task_id | queues.service.ts:434–435；experiment-menu.component.ts:223–225 的 dequeuePopup，在确认出队前查询所选任务的队列 | 受检 queues 服务/Schema 无定义；models.get_by_task_id 是另一服务，不能混同。Fork release 有字符串、官方未见 | 未调用，N/A；无 queued Task、未进入出队弹窗。潜在出队辅助查询风险，未计通过；不能据此补接口 |
| tasks.get_operations_log | tasks.service.ts:1377–1378；仅生成客户端声明；experiment-operations-log 组件有类型引用，但未找到调用该方法/使用组件 selector 的业务代码 | 受检 tasks.py/tasks.conf 无活动定义；两套 Web 均含声明字符串 | 未调用，N/A；当前 Task 参数/日志/标量读取不依赖它。休眠声明/未覆盖能力，不能认定当前阻塞或兼容通过 |
| reports.share | reports.service.ts:450–477；生成方法无实际调用者；report.component.ts:350 的可见 share() 只复制当前链接 | reports.py:393–403 及 reports.conf:320 起实现/Schema 被注释；注释中的 share_task 会改变访问/分享状态，两套 Web 均含声明字符串 | 仅静态分析，未调用、N/A。不能把复制链接等同此 API；如后续使用，需单独授权权限写入/负例测试 |

完整位置与搜索结果：[risk-static.json](../infra/evidence/t01c3/risk-static.json)、
[risk-packaged-web.json](../infra/evidence/t01c3/risk-packaged-web.json)。上述简写路径均位于
`clearml-web/src/app/business-logic/api-services/` 或 `clearml-web/src/app/webapp-common/`；
可直接从 JSON 得到确切文件与行。没有为了消除静态差异改动后端。

## Server Fork 静态差异评估

以 docker exec **只读导出源码文本**，不启动第二个 Server，不读取运行凭据或配置。
23 个相关 services/*.py 与 schema/services/*.conf、111 个 bll/apimodels/database/service_repo
Python 文件，合计 **134/134 SHA256 相同**；当前比较范围内没有业务/API 实现差异。
证据：server-comparison.json、business-comparison.json、runtime-code/、endpoints.json。
服务/schema 比较覆盖 projects/tasks/events/queues/workers/models/pipelines/reports/users/organization。

这不证明镜像所有文件、依赖、插件、配置、环境或完整 Git tree 与 Fork 相同；尤其没有
声称 Server Fork 已部署/通过运行验证。当前证据**不支持为解决上述问题立即修改或切换
Server Fork**：下载问题发生在 URL 识别/浏览器流程，四风险接口在受检两份实现中都缺少
活动 handler，单纯换同版本 Fork 不会因此补出实现。

若以后要验证 Server Fork 自身，建议另行授权独立项目/端口、独立数据库/文件卷和测试
账号/数据，不连接现有业务数据进行未经验证的迁移；本轮未作运行选型或部署决策。

## 前后基线与原服务保护

- 原六服务和独立 Fork 共 7 个容器均 healthy，RestartCount=0；ID、Created/StartedAt、
  镜像、端口、挂载、网络 EndpointID/Alias 前后完全相同，卷清单不变。
- Agent active/running、PID 205189、NRestarts=0、启动时间不变；pip freeze 前后相同。
  主机 Agent unit 哈希与 C2 保存哈希相同（该项是历史基线对照，不冒称新建前快照）。
- 全部既有部署文件、C2 release 1502 文件及两个 Fork 未改变；凭据文件不读内容，仅
  inode/大小/mtime/ctime/权限前后相同。STATUS/HANDOFF 外的原有文件哈希保持。
- 首次 probe 与两站矩阵/补测的前后库存一致：2 项目、3 Task（completed×2、failed×1）、
  2 队列、0 Model，目标 Task 完整记录与 Artifact 元数据不变，用户偏好哈希不变。
  当前没有 Dataset/Pipeline 样本；历史 Artifact 实际打开/下载的内容哈希与固定 fixture 相同。
- 未新建/修改/删除业务对象或设置，未入队/出队、执行 Agent/训练/Pipeline、重启服务或删卷。
  三仓库 HEAD/暂存区保留；无暂存、提交、push。日志/统计的正常访问记录及 Agent 心跳
  会继续产生，不将这些自然变化当成容器重启或业务修改。

## 实际检查命令、退出码与失败记录

命令均在 `/root/TieSheAI`。每个正式命令由
`python3 -B infra/evidence/t01c3/run.py <证据名> <命令...>` 记录实际参数、UTC 时间、耗时、
退出码与输出文件，见 commands.jsonl。UTC 转 Asia/Hong_Kong 为 +08:00。

| 实际命令 | 退出码/结果 | 证据 |
|---|---|---|
| `python3 -B infra/evidence/t01c3/snapshot.py before/after` | 0/0，三仓库、7 容器、Agent、配置/发布基线 | snapshot-before.json、snapshot-after.json |
| `python3 -B infra/verify.py` 前后 | 0/0，原六服务健康、端口、版本、代理/鉴权基线 | t01a-before.txt、t01a-after.txt |
| Agent Python `-m pip freeze` 前后 | 0/0，内容一致 | python-before.txt、python-after.txt |
| `python3 -B infra/evidence/t01c3/static-server.py`、`compare-business.py` | 0/0，23+111 文件一致 | static-server.txt、business-comparison.txt |
| `python3 -B infra/evidence/t01c3/make-allowlist.py` | 0，68 个明确契约 | allowlist.txt、allowlist.json |
| `node infra/evidence/t01c3/probe.cjs` | 0，既有用户/项目/Artifact 探测采证；手工猜测的 /read mode 不匹配现有 output，不作为 Artifact 页面通过依据 | probe-*-browser.json；后由真实点击覆盖 |
| `node infra/evidence/t01c3/matrix.cjs` | 0 表示矩阵采证完成；每站 3 条定位器操作失败，不代表业务通过 | matrix-*-browser.json、matrix-browser.txt |
| `node infra/evidence/t01c3/supplement.cjs` | 0，两站各 7 条操作成功；实际下载行为差异仍存在 | supplement-*-browser.json、browser-supplement.txt |
| `node infra/evidence/t01c3/empty-deep-recheck.cjs` | 0，深链/reload 采证；官方 ace 错误仍记录 | empty-recheck-*-browser.json、empty-deep-recheck.txt |
| `python3 -B infra/evidence/t01c3/risk-scan.py`、`python3 -B -`（risk-packaged-web 字符串检查） | 0/0，静态分类；不试调用写接口 | risk-static-refined.txt、risk-packaged-web.txt |
| `python3 -B infra/evidence/t01c3/analyze.py` | 0，状态/字段/异常复核；非全兼容通过断言 | matrix-analysis.txt、matrix-analysis.json |
| `python3 -B infra/evidence/t01c3/compare-final.py` | 0，前后运行/历史数据/配置保护通过 | compare-final.txt、runtime-result.json |
| `python3 -B infra/evidence/t01c3/check-delivery.py` | 最终退出 0，文档/引用/范围/保留/忽略/差异检查 | delivery-check.txt、delivery-result.json |

如实保留测试限制与失败：初次定位器在两站各误选隐藏 tooltip 两次和工作区次级 QUEUES
一次，操作等待超时；未强制点击绕过，改用可见卡片及顶部 tab 后补测成功。
初期响应观察器误要求 `_ex` 的单数 task / Reports 的 reports 字段，基于已有实际响应和
源实现纠正了分类器；原标签保留。部分探索性 rg/ls 未匹配返回 1/2，不是部署/API 故障。
Artifact 下载行为差异、CORS、NG0953 和官方 ace 异常未修复，未将它们写成测试通过。

## 未验证项、下一轮夹具及允许操作建议

本轮无采证工具阻塞，但 **Fork 实际 Artifact 下载功能尚不满足完整 C3**；N/A 与受限项
也未通过。下列都是后续任务建议，**没有自动授权或执行**：

| 后续目标 | 所需夹具/明确授权 | 建议允许操作与继续禁止的范围 |
|---|---|---|
| 优先修复 Artifact 下载 | 可继续复用现有历史 Task/Artifact，不必先造业务对象 | 单独授权 Web URL/下载流程最小修改、构建、新固定 release、仅更新 Fork 测试容器；继续禁止改原 8080/API/Fileserver/Agent、改历史 URI/业务记录或放宽鉴权 |
| Dataset 详情/版本/关系 | 专用项目下两个最小合成 Dataset 版本；**Dataset SDK/API 可能创建承载 Task，须一并明确授权** | 仅批准的命名空间内创建/上传小样本/读取版本与关系；不入队、不运行训练；清理仅明确批准的 ID，不能删卷 |
| Model 详情/权重/Task 关系 | 专用注册 Model、已批准的小文件及专用 Draft Task 关系 | 元数据登记和限定文件上传/下载、详情读取；不安装框架、训练、发布推理服务；修改/清理另列 ID |
| Pipeline 详情/DAG/命名检查 | 不运行的专用 controller 草稿、最小 DAG/版本；现有普通 testing Task 不能替代 | 若用户批准，可读详情、打开命名对话框后取消；禁止提交运行、controller/step 执行；check_new_run 契约/能力门禁另评审 |
| queues.get_by_task_id 条件分支 | 须有 queued Task；本轮没有，不能靠 completed Task 假验 | 若将来需要，须另行批准**无 Agent 监听的专用队列与排队操作**，不能复用 rail-cpu；只打开/取消出队确认也需明确范围，不能默认批准入队 |
| operations log / reports.share | 前者先确认实际业务入口；后者仅在专用报告/权限测试场景确有需求时 | 不为死声明补接口；报告 API 分享涉及权限写入须独立授权，复制链接不能替代权限测试 |
| 偏好、统计与外部请求 | 专用测试用户；全局统计设置如需操作宜在隔离后端；外部域名须明确允许 | 不改现有用户设置，不能用用户隔离替代全局设置隔离；未授权外部请求仍阻断，受限结果不计通过 |
| N/A 深层兼容与 N/A 角色权限 | 与上列夹具相应的角色、正负例、文件访问条件 | 明确样本/能力范围后续做 C3-B；Fileserver 全策略、远程端到端、Server Fork 运行、GPU/恢复/负载仍另验 |

建议下一步先单列 **Artifact 下载最小修复与原页面回归**，随后按明确夹具清单授权受控
C3-B；保留所有阻断/错误和数据保护。没有依据要求现在切换 Server Fork，也不自动进入 T02。

## 2026-11-10 09:48：独立 Artifact 下载修复结果（保留上方 C3-A 原失败）

- 本独立修复通过，新版 `artifact-download-20261110-v1` / `2.5.0-artifact-fix-0b92177bcb35` 保持运行；
  完整 C3 仍未通过，未执行 C3-B 或创建夹具。详见 [修复报告](T01C_ARTIFACT_DOWNLOAD_FIX.md)。
- 修复 URL origin/路径边界识别、显式历史别名到同源 /files、签名/fetch/相对导航回退、
  HTTP 错误不保存；未改 Server/Fileserver/CORS/鉴权。原 Artifact URI 不变。
- 新版两轮均从原页面按钮捕获真实 download，cpu-smoke.json 为 122 字节，与固定 fixture
  逐字节相同，SHA256 `b00ed20e939a658612bc0586861bf1af2ece002c6b20bcfee5255194592555a9`；
  实际网络同源 /files、Cookie、HTTP 200，无跨源失败，匿名同文件仍 401。
- 回退 C2 v2：完整旧清单一致并重现无 download；再恢复新版后真实下载复验通过。
  C1 产物、C2 v2 全文件哈希、原六服务/Agent/历史库存/用户偏好未变；仅 Fork 允许重建。
- 36 项边界测试、正式主/Widgets 独立构建、874 JS 语法、1502 发布文件 HTTP 哈希、
  登录/Task/日志/标量/Widgets/代理/404/401 回归通过；警告与失败修正记录未删除。
- P2 Artifact 下载缺口已在本范围修复；上方其他未知/受限/缺样本/未触发项目仍未通过。
  证据 `infra/evidence/artifact-download-fix/`；没有把 C3-A 的原失败改写为当时已成功。


## 2026-11-10 16:59：C3-B 首轮 Dataset / Model 受控夹具验收

**本轮限定夹具、版本/父关系、双向链接及可用入口下载通过；完整 C3 仍未通过。**
完整台账、字节/哈希、URI、命令/退出码和异常见 [夹具报告](T01C3B_FIXTURES.md)。
本轮使用修复 release 18080 / 原官方 8080，各用独立 context 和已有用户，从真实列表进入详情。

| 本轮矩阵 | 18080 | 8080 | 页面与 SDK 区分 / 未验证项 |
|---|---|---|---|
| 同名 Dataset 两版本 / Final | 通过 | 通过 | 真卡片/版本列表；v1 `276ab235dfdb468b8bef3cd389020794`，v2 `1cac2e75863f4f09a5d05b795a275ff3` |
| v2→v1 父关系 | 通过 | 通过 | 两图节点/一箭头、选中节点与真实 Task 链接 ID；SDK state 独立验证 |
| 继承/新增文件展示 | 通过 | 通过 | v1 inherited.txt；v2 inherited.txt+added.txt，显示 71/80 B 和完整 SHA256 |
| Dataset 文件内容/下载 | 通过（可用入口） | 通过（可用入口） | Task information→ARTIFACTS/data 下载两 ZIP，解包比对内容并按父关系合并；不是 SDK 查询代替 UI |
| Dataset CONTENT 下载图标 / PREVIEW | CLI 命令 / N/A | CLI 命令 / N/A | 图标不产生下载；实际 debug_images 200/200 空结果，无文本内联预览样本 |
| Model 详情 / 双向 Task 关系 | 通过 | 通过 | Model `62ec3a648ff74162bd1a5c13b844b79d` ↔ Draft testing Task `388557dbadf6452fba94d9ab5e8f3ce6`；链接实际打开并核对 ID，Task created |
| Model GENERAL 文件按钮 | inline JSON，未下载 | inline JSON，未下载 | 118 B 内容/hash 正确，零 download 事件；不计此按钮下载通过 |
| Model 可用下载入口 | 通过 | 通过 | 创建 Task 的输出 Model 名称旁按钮，真实下载 118 B、逐字节/SHA256 一致 |
| 输入模型消费关系 | N/A | N/A | 没有消费 Task 样本，不创建额外对象 |

每站最终 24 步、3 份真实 download；页面文件表和下载字节独立于 SDK 底层验证记录。
两 Dataset Task 正常 started/completed，不代表 Agent 执行；Model 文件明确不是训练权重。
新增严格为 3 项目节点/3 Task/1 Model 及必要附属资产；历史完整记录/Artifact、偏好、队列、
七容器/Agent、三仓库 HEAD/index/源码和部署均保持，未暂存、提交、push 或清理。
精确审阅后仅增加 events.debug_images 的受控读取（限本轮两 Dataset ID）；偏好/统计/第三方仍阻断。
最终 HTTP/业务状态、控制台及阻断数量见夹具报告；官方 Dataset 下载初次 CORS 失败和真实回退下载并存，
Fork 可选配置 404 保留，所有异常逐项关联，没有通配忽略未知错误或伪造响应。
初轮未知 debug_images 阻断、测试定位/观察器失败保留，未改写历史轮为通过。
Pipeline、四风险端点、分享权限、完整文件/角色权限、其他存储签名、Server Fork/GPU/远程/运维仍未验。
仅停止在本轮 C3-B；完整 C3、后续阶段及 Model GENERAL 按钮修复均需另授权。

本轮补记：Task Artifact PREVIEW 的 116 bytes 来自 SDK 写 ZIP 过程的归档大小，非单文件大小；
两站 CONTENT 和下载 ZIP 头均为正确的 71/80 B，详见夹具报告及 sdk-preview-source.json。未修改 SDK。
