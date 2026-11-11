# T01-C2：ClearML Web Fork 独立部署

记录日期：2026-11-10（Asia/Hong_Kong）。本报告仅覆盖独立 Web 和基础登录读取；
C3 完整业务兼容矩阵、Server Fork 运行验证及后续阶段不在授权范围内。
最终结论与验收时间见下方验收结果及 [STATUS.md](STATUS.md)。

## 部署与版本

独立项目 `tiesheai-web-fork` 只有 `web` 一个容器，仅发布 `127.0.0.1:18080:8080`。
原 `tiesheai-clearml` 六容器、官方 Web 8080、API 8008、Fileserver 8081 及 Agent 保留。
未修改 `infra/compose.yaml`，不启动或重配 Agent，不创建业务对象，不安装训练依赖。

| 层次 | 实际版本 / 来源 |
|---|---|
| Web Fork 源码 | `be71d50e7504eb00a2e09900fabbe8697ed23558`，package 2.5.0 |
| 原始产物 | C1 的 `clearml-web/build/browser/` 与 `clearml-web/dist/report-widgets/browser/`，未重建 |
| 独立 release | `infra/.local/web-fork/releases/c2-be71d50-v2/`，运行标识 `2.5.0-fork-be71d50-c2` |
| Nginx 运行镜像 | 复用 `clearml/server:2.4.0@sha256:5ec4aed2e40c619da63198c22e765a00b4e3e5c06081a9c0a4ae237df66fb7bb` |
| 原官方 Web | `2.4.0-722`，保持 8080；新站挂载 Fork release，不使用镜像内官方 Web |
| API / Fileserver | 原官方 Server 2.4.0；没有运行本地 Server Fork |
| Server Fork 源码 | `2ebdc43951b9432cc7fa528bbb3a7100fc6fe805`，干净、未修改 |
| 根仓库 HEAD | `2416ec050809c7b9ec5f991341c27c462cef29f8`，没有暂存、提交或 push |

镜像实际 ID 与原官方 Web 相同，完整容器 ID、StartedAt、绑定、挂载见
`infra/evidence/t01c2/fork-runtime.json`。镜像入口被替换为仅运行 Nginx，用户
65534:65534，根文件系统只读、capabilities 全部移除，临时目录使用 64 MiB tmpfs。
没有新数据卷；release 和 Nginx 配置均只读挂载。

## 原始与加工产物

prepare 先与 C1 逐文件 SHA256/字节数清单核对，匹配才复制；原产物不动。
原主应用 1817 文件、635 个 map；Widgets 318 文件、无 map。发布副本共 1502 文件。

发布加工包括：主 HTML base `/`、Widgets HTML base `/widgets/`；替换 env.js
的 `${CLEARML_SERVER_SUB_PATH}` 为空 subPath 并增加 Fork 标识；添加独立
configuration.json/version.json；不发布 map，移除发布副本 JS/CSS 的 sourceMappingURL。
主应用既有 374 文件、Widgets 1 文件的哈希因此变化，不冒称原始构建哈希。
修改明细见 `release-delta.json`，两套原始清单与发布清单分别保存在
`source-manifests.json`、`release-manifest.json`。

以下为 `json.dumps(manifest, sort_keys=True, separators=(',', ':'))` 的 SHA256，
不是文件系统归档或含不同缩进 JSON 文件本身的哈希：

| 清单 | SHA256 |
|---|---|
| C1 主应用 | `fd2de51ed95e5bf192d169a8a066e43e9b23a4b01df7b9835dc8d60f4e3224f4` |
| C1 Widgets | `e7f712dd2545d2d7a6a4843dbf82b17e7706ea71d92db848e32ea1a16082589d` |
| 发布 release | `8cb7703d20b663bcedbd134b9943162e483cdbb9a74a58d343f596d20828c61a` |

release 文件权限 0444、目录 0555；容器还使用只读挂载。原 C1 完整产物再次核对，
不把部署加工的差异写回 Fork，也不改 package/lock/angular 配置。

## 路径、运行配置与鉴权代理

- 主站 `/`；主应用深层路由回退到 `/index.html`。
- `/widgets` 保留 query 并 308 到 `/widgets/`；Widgets 深层路径回退到自身 index。
  Widgets HTML base 固定 `/widgets/`，资源不随当前深层 URL 漂移；其 `../configuration.json`
  从根取得运行配置。根 baseHref `/` 供主路由使用，Widgets 本身无 Angular Router。
- `apiBaseUrl: "/api"`、`fileBaseUrl: "/files"` 和 displayedServerUrls 显式配置，
  不根据 18080 自动推断后端端口。版本配置与 env.js 均可区分 Fork。
- 使用已核实的 external bridge `tiesheai-clearml_default`，Docker DNS `127.0.0.11`
  解析 `apiserver:8008`、`fileserver:8081`。不将容器回环当宿主机。
- `/api/`、`/files/` 使用 `^~`，剥离代理前缀，保留原始编码与 query；
  Authorization、Cookie 显式转发，Set-Cookie 默认透传，不修改 Cookie domain/path。
  登录遵循现有 simple 模式，没有关闭鉴权或配置新账号/凭据。
- JS/CSS/JSON/字体/图片、assets/app/media 缺失返回 404，不被 index 的 HTTP 200 掩盖；
  map 路径始终 404。access log 不记录 Authorization、Cookie、用户名或 query。

Cookie 不按端口隔离。本次新建浏览器 context，与官方 8080 的控制 context 分离；
不使用已有浏览器配置文件。用户对比两个站点时也应使用独立浏览器配置文件。

## 实际命令与证据

以下均在 `/root/TieSheAI` 执行。运行包装器
`python3 -B infra/evidence/t01c2/run.py <证据名> <命令...>` 保存命令、UTC 时间、
退出码及输出路径至 `commands.jsonl`，原始输出只保留本地忽略证据。
UTC 记录转 Asia/Hong_Kong 为 +08:00。未把 shell 子命令探测失败当作验收通过。

| 命令 / 检查 | 退出码及结果 | 证据（相对 infra/evidence/t01c2） |
|---|---|---|
| `python3 -B infra/evidence/t01c2/snapshot.py before` | 0，保存三仓库、六容器、Agent、配置基线 | `snapshot-before.json` |
| `python3 -B infra/verify.py` 前后 | 0 / 0，六服务和官方静态/代理/数据库检查通过 | `t01a-before.txt`、`t01a-after.txt` |
| Agent Python `-m pip freeze` 前后 | 0 / 0，快照相同 | `python-before.txt`、`python-after.txt` |
| `python3 -B infra/web-fork/prepare-release.py` | 0，C1 哈希匹配、独立副本发布加工 | `prepare-release-v2.txt`、manifest/delta 文件 |
| `bash infra/web-fork/compose.sh config --quiet` | 0，单服务配置有效 | `compose-config.txt` |
| `bash infra/web-fork/compose.sh up -d --pull never --wait --wait-timeout 90` 首次 | 1，临时目录 chown 权限失败 | `fork-up.txt`、`fork-startup-failure.txt` |
| 同一 up，增加非 root user 后（最终 v2 亦执行通过） | 0，healthy | `fork-up-unprivileged.txt`、`fork-up-v2.txt` |
| `nginx -t -c /etc/nginx/fork.conf`、修复后 reload | 0 / 0 | `nginx-check-fixed.txt`、`nginx-reload-fixed.txt` |
| `python3 -B infra/web-fork/verify.py` | 0，全部 1502 文件 HTTP 字节/哈希；8 个缺失路径 404；2 个 SPA 深层路径；代理及匿名 401 | `http-check-accepted.txt` |
| `python3 -B infra/evidence/t01c2/read-history.py before/after` | 0 / 0，受保护 API、历史 Task 和 Artifact、任务清单无变化 | `history-before.json`、`history-after.json` |
| `bash infra/web-fork/compose.sh stop`、同一 up | 0 / 0，独立站点停止及恢复通过 | `fork-stop-check.txt`、`fork-start-check.txt` |
| `node infra/evidence/t01c2/browser-tools/check-browser.cjs` 最终 | 0，实际登录/认证读取/Widget 及隔离通过 | `browser-result.json`、`browser-network.json`、`browser-*.png` |
| `snapshot.py after`、`compare-final.py` 修正后 | 0 / 0，原六服务/Agent/配置/源码/历史 Task 不变 | `snapshot-after.json`、`compare-final-fixed.txt` |
| `python3 -B infra/evidence/t01c2/check-delivery.py` | 最终退出 0，文档/范围/忽略/凭据扫描及三仓库差异检查通过 | `delivery-check.txt` |

浏览器工具安装于 `infra/evidence/t01c2/browser-tools/`：Node Playwright 1.56.1，
不使用或改动 Agent Python 环境。命令为该目录 `npm init -y`、
`npm install --save-exact playwright@1.56.1`（均退出 0），以及设置独立
PLAYWRIGHT_BROWSERS_PATH 后的 `playwright install chromium`。下载完成但 Node 解压停滞，
主动终止安装进程（退出 -15，包装器为 241），原日志保留；用 Python 标准库验证 ZIP CRC
并解压到独立 manual-chromium（退出 0）。实际运行 Chromium 141.0.7390.37、build 1194，
ZIP SHA256 `5ad70cf662e7090354edbe84e1a01ac531fd217f37f5001f0d2efbe0d152b396`，
不改变主机 Python、系统包或 Agent 环境。
运行同一环境变量的 `node infra/evidence/t01c2/browser-tools/check-browser.cjs`。
网络证据只记录方法、路径、状态和是否携带鉴权，不保存头值、Cookie、token 或响应凭据。
浏览器对 API 写操作设置拦截保护，仅允许认证和读取，避免页面偏好等写回既有数据。
截图必要处遮罩姓名/输入框，保留在忽略目录。

## 失败记录与问题归因

1. 初始只读探测返回 1：末尾 `command -v chromium-browser` 未找到；不是原服务异常。
   浏览器工具随后在本轮独立目录准备。
2. 首次新容器启动失败：移除 capabilities 后 root master 尝试 chown 临时目录被拒；
   配置非 root 用户解决，重新创建的仅新项目容器，原六容器和 Agent 未触动。
3. 初始 Artifact 代理读取返回 404，验收脚本退出 1；诊断重复退出 1。
   这是本轮 Nginx 静态 JSON location 抢先匹配的错误，改为代理 `^~` 并保留原始 URI
   后认证下载 200、哈希匹配。原始失败日志保留，未修改 Artifact 或绕过认证。
4. 辅助匿名直连 Artifact 命令退出 1、HTTP 401；原 Fileserver 要求鉴权。
   后续同一历史 Artifact 携带 Bearer 直连 200、哈希匹配（`original-artifact-authenticated.txt`）。
   401 是既有预期行为，不是本轮引入的问题，也不计匿名读取通过。
5. 浏览器安装 Node 解压停滞，主动中止后独立解压验证通过；不是应用失败，证据
   `browser-install.txt`、`browser-extract-fallback.txt`。
6. 浏览器首轮把 combobox 当普通 textbox，等待超时退出 1；修正定位后实际登录通过。
   v1 浏览器随后因 Plotly 解析错误退出 1：发布加工的 sourceMappingURL 正则误改了库内
   字符串；原始 `node --check` 退出 0、v1 退出 1。改为只匹配行首 JS/文件末 CSS 真实
   指令，新建 v2（保留 v1），874 个 JS 全部语法通过，未改 C1 产物或业务源码。
   证据 `browser-initial-*`、`v1-browser-*`、`plotly-*-syntax.txt`、`release-js-syntax.txt`。
7. v2 浏览器首轮已经登录/读 Artifact/绘图/隔离成功，但测试分类器未识别外部 updates
   的主动拦截错误，退出 1。补充采集 ErrorEvent 中 HttpErrorResponse 的 name/status/url，
   仅允许 status=0 且精确匹配阻断名单的错误；最终退出 0，所有原始错误明细保留，
   不屏蔽其他异常。证据 `v2-guard-browser-*`、`browser-check-v2.txt`、最终 `browser-*.json`。
8. 初次前后比较退出 1：Docker inspect 的 Mounts 数组顺序变化，挂载项本身相同。
   按 Destination 排序后比较全部字段通过，原始快照保留；证据 `compare-initial.txt`、
   `compare-final-fixed.txt`，并未重启或重配原容器。
9. T01-B 原有 failed Task 保持 failed，两个 completed Task 保持 completed；不重新提交 Smoke。

## 验收结果与剩余边界

**T01-C2 通过**，验收记录时间 2026-11-10 08:39（Asia/Hong_Kong）；服务保持运行。

- 18080 仅回环绑定，运行的是独立 Fork release v2；Nginx 检查、单服务健康检查通过。
- 1502 个文件 HTTP 内容和发布哈希一致，覆盖入口、所有 JS 分块、字体、Plotly；
  新增 `node --check` 对 release 的 874 个 JS 全部退出 0（`js-syntax.json`、
  `release-js-syntax.txt`）。原始 Plotly 语法通过，v1 加工错误通过 v2 修复。
- SPA/Widgets 深层路径及 308/query、配置/base/env、缺失资源 404 和禁发 map 通过；
  匿名 server.info 与匿名历史 Artifact 均 401，API query 代理有效。
- Chromium 真实打开登录页，选择已有用户后登录 200，收到 HttpOnly、SameSite=Lax、
  Path=/ 的 Cookie；后续 server.info 仅发送 Cookie（未发送 Authorization）返回 200。
  独立 Bearer API/Artifact 读取亦 200，证明认证头转发有效；未创建新用户或凭据。
- 历史 Task 保持 completed；浏览器经 `/files` 下载 122 字节 Artifact，SHA256
  `b00ed20e939a658612bc0586861bf1af2ece002c6b20bcfee5255194592555a9`。
  携带只读 query 的认证下载也通过，路径中 `%20` 保留；原 URI 未被修改。
- Widgets 深层页面实际加载 Plotly 并绘制历史标量图 1 个；库文件名为 2.35.0，
  其原始库实际声明/运行版本为 2.35.2，没有改名或升级。浏览器有 7 次字体 HTTP 200，
  网络摘要 467 条响应；`browser-widgets.png` 及登录/首页/历史页截图已保存并检查。
- 8080 控制 context 中预置 Cookie/localStorage 哨兵未变，测试 context 无该哨兵，
  不使用现有浏览器 session；上下文隔离校验通过。
- 浏览器刻意阻断 users.set_preferences、server.report_stats_option 及外部 GitHub/更新请求，
  避免修改既有偏好/统计设置和向第三方发送请求。最终 4 个 HttpErrorResponse 均为
  status=0，精确对应已阻断的偏好保存和 updates 请求，保留于 guardErrors/errorDetails；
  不将它们记成后端读取失败，也不宣称未经限制的整站浏览器无错误。
  可选 credentials.json/onboarding.json 的 404 是现有代码支持的缺省回退，
  没有以 index.html 伪装 JSON；所有实际只读 API 响应均成功。
- 原六服务仍 6/6 healthy、RestartCount=0；容器 ID/Created/StartedAt/镜像/端口/挂载
  全部不变。Agent active/running、PID 205189、NRestarts=0、启动时间不变；
  既有配置 SHA256 和 Python freeze 相同。三个历史 Task 的 ID/状态清单、目标 Task
  完整记录哈希和 Artifact 哈希不变；既有 failed Task 不被归咎于 C2。
- 三仓库 HEAD/暂存区未改变，两个 Fork 干净；原 ROADMAP 未提交改动逐字节保留，
  STATUS 历史任务和 HANDOFF 必要摘要保留。未暂存、提交或 push。

无 C2 阻塞。尚未验证：C3 完整页面/API/业务矩阵、未拦截的偏好/统计写入与外部更新、
完整 Fileserver 访问控制策略、所有历史绝对 8081 链接在 UI 中的重写、Server Fork 运行、
远程端到端、长期负载、干净环境构建、主机/Agent 重启及备份恢复、GPU。
C2 通过不代表 C3 或 Server Fork 已通过；本轮完成即停止，后续须用户明确授权。

## 交付与访问 / 回退

实际新增 `infra/web-fork/compose.yaml`、`nginx.conf`、`compose.sh`、
`prepare-release.py`、`verify.py`、`README.md` 和本文；更新 STATUS/HANDOFF/DECISIONS。
根仓库原有 ROADMAP 未提交修改保留，两个 Fork 工作区保持干净。
本地 release、浏览器工具、截图与原始证据受 `.local/`、`infra/evidence/` 忽略规则保护。

访问 `http://127.0.0.1:18080/`、`http://127.0.0.1:18080/widgets/`。
启停、远程转发及只停止本测试站点的回退说明见
[infra/web-fork/README.md](../infra/web-fork/README.md)。
无需替换原服务或数据；回退后仍使用官方 `http://127.0.0.1:8080/`。
停止本项目已实测，结束时站点保持运行。
