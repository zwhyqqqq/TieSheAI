# Web Fork Artifact 下载按钮修复

记录时间：2026-11-10 09:48（Asia/Hong_Kong）。**本独立修复通过，新版保持运行；完整 C3 仍未通过。**
范围为 Web 下载链路、独立构建/新 release 与仅 Fork 的回退恢复。未进入 C3-B/T02，
未创建业务对象、改历史 URI、改 Server/Fileserver/CORS/鉴权或重启原六服务/Agent。

## 根因与最小修改

旧 FILE_BASE_URL 为相对 `/files`，历史 URI 为绝对 8081；`startsWith` 无法识别同一
Fileserver，且容易接受相似域名/路径。签名阶段没有转同源，fetch(credentials=include)
跨源被拒，导航回退又因同一错误判断未加 download，最终仅打开 inline JSON。
旧 fetch 不检查 response.ok，还会把可见 401/404 错误体作为 Blob 处理；缺失/复杂
Content-Disposition 和 `new URL(relative)` 也可能失败。复现来自原页面按钮，不改 href。

本次 Web Fork 七文件：

| 文件（相对 clearml-web） | 修改 |
|---|---|
| src/app/shared/utils/url.ts | URL 解析后严格比较 HTTP(S) origin/路径边界、拒绝 userinfo；仅配置来源/显式别名及同源代理路径可信；规范化为同源 /files，保留编码/query/hash、幂等；未知外部/S3 原样返回 |
| src/app/app.constants.ts | 由运行配置装载 FILE_SERVER_ALIASES，缺省空数组 |
| src/environments/base.ts | 可选 fileServerAliases 类型 |
| src/app/webapp-common/settings/admin/base-admin.service.ts | 可信 Fileserver 在签名/缓存参数处理前规范化；其他存储签名分支不改 |
| src/app/shared/utils/artifact-download.ts（新增） | 相对/绝对导航 URL；追加 download 时不重排编码 query；先验 response.ok，再保存 Blob；401/404 等 HTTP 错误抛专用错误；文件名兼容普通/UTF-8/缺失头、回收 object URL |
| src/app/webapp-common/experiments/effects/common-experiments-info.effects.ts | 实际 fetch 和导航使用规范化 URL；HTTP 失败仅 dispatch downloadFailed，不保存/重试为成功；网络失败仍保留导航回退，支持相对地址 |
| tests/artifact-download.cjs（新增） | Node+既有 TypeScript/RxJS 的边界与实际 effect 表达式测试，无新框架 |

唯一历史别名 `http://127.0.0.1:8081` 在独立 release 的 configuration.json 中显式批准，
不在业务源码硬编码主机地址，不按任意 8081 端口匹配，不从任意业务 URL 扩展允许来源。
本轮未改变 Fileserver 的 `Access-Control-Allow-Origin: *` 或缺省 ACAC；同源 fetch 无需放开 CORS。

共享工具的其他调用方已静态审阅：BaseAdmin/签名缓存、Report 上传基址、Widget sample、
image viewer、删除对话框。原已正确配置的来源与同源 /files 保持目标等价；现在只对显式
可信别名扩大识别、对相似域名/路径收紧。Report 的 /files 上传基址构造已做边界测试，
但未实际上传；Sample/图片、删除、外部 S3 真实签名/凭据流程无夹具或不在授权范围，
仅验证 URL 分类与不重写，不能写成业务端到端通过。Widgets 实际标量绘图另已通过。

## 版本与不可变产物

源码未提交，**HEAD 仅为基点，不包含本次修复**：

- Web HEAD：`be71d50e7504eb00a2e09900fabbe8697ed23558`；source_dirty=true，package 2.5.0。
- 包含新文件的完整补丁 SHA256：`0b92177bcb35418804631f0ba95d1182d1c09194e40d864e1b10964714bc7c51`。
- 全部可入库 Web 文件的源码清单规范 JSON SHA256：`8036a71b5d73bc23391ac5caadced5994f2c67a4531ca89f29a76eff37042ec7`。
- 原始 patch/source-manifest/source-version 在忽略的证据目录，打包前逐文件核对未变。
- 运行版本：`2.5.0-artifact-fix-0b92177bcb35`；固定 release：`artifact-download-20261110-v1`。
- 发布清单规范 JSON SHA256：`f7372213b825c9ea7f1d456d6cb024c1f3a861aca97ee9d2757d4dda583529ca`，1502 文件、map 0。

规范 JSON 哈希均按 `json.dumps(manifest, sort_keys=True, separators=(',', ':'))` 编码计算，
不冒充缩进 JSON 文件自身哈希。主应用/Widgets 新构建分别为
1817 文件 / 57,237,282 字节、318 文件 / 19,241,353 字节；清单哈希：

- main：`33ba8ceaef130a33d7d6f5b0e8517831f2338f9fc069fca140a9caab77a1bd33`。
- Widgets：`68819e66e99d2e7aa58ee565522025163b9dc0dfbf91a098430097a2a0de5c44`。

输出独立于 C1：`clearml-web/out/artifact-download-fix/main/browser/` 和 `widgets/browser/`。
C1 原 build/browser、dist/report-widgets/browser 两套完整清单复核一致；C2 v2 全部 1502
文件逐字节哈希不变，没有覆盖。新构建/发布清单分开保存（build-manifests.json、
release-manifest.json），发布加工只处理 HTML base、env/版本/配置、map 文件/真实指令。

继续使用已锁定 `clearml/server:2.4.0@sha256:5ec4aed2e40c619da63198c22e765a00b4e3e5c06081a9c0a4ae237df66fb7bb`
内 Nginx，实际 Image ID 与原官方 Web 一致；没有拉新镜像或改后端网络。
Fork Compose 仅参数化 release 挂载、更新健康探针使之兼容真实源版本字段；Nginx 仅去掉
会过期的 C2 版本响应头，改成通用 web-fork。完整版本以 /version.json/清单为准。

## 真实浏览器下载与回退

复用 C2 Playwright 1.56.1 / Chromium 141.0.7390.37 和已有用户，每轮全新 context。
从既有 Task 原页面点击 ARTIFACTS → cpu-smoke-json → FILE PATH 旁下载按钮。
浏览器脚本没有改 href、手改 URI、route.fulfill 或伪造下载响应；路由拦截仅阻止写入/第三方。

| 阶段 | 实际 release / Fork 容器 ID 前缀 | HTTP 静态/状态 | 原按钮结果 |
|---|---|---|---|
| 变更前 | C2 v2 / 6544c6cb867d | 原六服务和站点健康 | 跨源失败，无 download |
| 首次新版 | artifact-download-20261110-v1 / 85d9e19b939f | 全文件哈希和代理检查 0 | 真 download，122 字节，fixture 逐字节一致 |
| 实测回退 | C2 v2 / 8ec3491abcf0 | 原 C2 manifest 全文件比对 0 | 再现无 download 的旧行为 |
| 恢复新版 | artifact-download-20261110-v1 / cbab419e77c9 | 新 manifest 检查 0，healthy | 再次真 download，122 字节，fixture 逐字节一致，保持运行 |

两次新版下载名均 `cpu-smoke.json`，字节与 tests/smoke/expected.json 完全相同，SHA256：

`b00ed20e939a658612bc0586861bf1af2ece002c6b20bcfee5255194592555a9`

原网络响应实际来自 `http://127.0.0.1:18080/files/TieSheAI/Smoke/T01-B%20CPU%20Smoke.../artifacts/cpu-smoke-json/cpu-smoke.json`，
HTTP 200，携带 Cookie、未携带 Authorization；请求没有去 8081，未再出现 CORS 拒绝。
随后由应用将真实成功响应 Blob 交给浏览器 download，保存文件，非脚本模拟响应。
认证和未认证同一文件读取分别为 200/401，受保护 server.info 同样为 200/401，鉴权有效。

证据在 `infra/evidence/artifact-download-fix/`：before/new/rollback/restored-browser.json、
各阶段 *-inventory-*.json、对应 PNG、new/restored-download-0-cpu-smoke.json。
网络证据只保留 Cookie/Authorization 是否存在，不保存头值或登录响应体。
回退/恢复的实际 StartedAt、完整容器 ID 和挂载见 result.json 的 fork_phases。

## 必要测试与实际命令

所有正式命令以 `python3 -B infra/evidence/artifact-download-fix/run.py <name> <命令...>`
记录到 commands.jsonl，含实际参数、UTC 时间/耗时、退出码和输出文件；显示日期为 UTC+8。

| 命令 / 检查 | 实际结果、退出码 | 证据 |
|---|---|---|
| snapshot.py before/after、原 infra/verify.py 前后、Agent Python -m pip freeze 前后 | 均 0，运行/配置/环境保护通过 | snapshot-*.json、services-*.txt、python-*.txt |
| `node clearml-web/tests/artifact-download.cjs` 最终 | 36 项通过，0；含相对/同源绝对/批准来源、编码/query/幂等、相似域名/路径/端口/协议、无效别名、外部/S3、401/404/500、文件名及实际 effect 分支 | boundary-tests-final.txt |
| `CI=true NG_CLI_ANALYTICS=false NG_BUILD_MAX_WORKERS=2 nice -n 10 pnpm --dir clearml-web run build --output-path out/artifact-download-fix/main` 最终 | 65.893 秒，0，4 条原有非阻塞警告 | build-main-final.txt |
| 同环境 `pnpm --dir clearml-web run build-widgets --output-path out/artifact-download-fix/widgets` | 21.011 秒，0，6 条原有非阻塞警告 | build-widgets.txt |
| source-version.py、prepare-download-release.py | 0/0，未提交补丁/源码清单、独立 raw/release 清单 | source-version.json、release-version.json |
| check-artifacts.py 最终 | 0，C1 保留、新构建入口/共享资源/字体/Plotly 校验；874 个发布 JS 的 node --check 全 0 | artifact-check-fixed.txt、js-syntax.json |
| `bash infra/web-fork/compose.sh config --quiet` 与三次 `up -d --pull never --wait --wait-timeout 90` | 均 0，仅 Fork 新建/回退/恢复 | compose-config/deploy-new/rollback-deploy/restore-deploy.txt |
| `python3 -B infra/web-fork/verify.py`，回退加 `--manifest infra/evidence/t01c2/release-manifest.json` | 三轮均 0；1502 文件 HTTP 字节/哈希、缺失 404、SPA/Widgets/308/query、API/文件代理、匿名受保护 401 | http-new/rollback-http/restored-http.txt |
| `node infra/evidence/artifact-download-fix/browser.cjs before/new/rollback/restored` | 四轮均 0（before/rollback 是确认旧失败，new/restored 是真实下载断言） | browser-*.txt、*-browser.json、下载文件及 PNG |
| `nginx -t -c /etc/nginx/fork.conf`（独立 Fork exec）、Node 读取工具链版本 | 0/0，配置语法与实际版本核对通过 | nginx-check.txt、toolchain.txt |
| compare-final.py | 0，六服务/Agent/历史库存/偏好/C2 release/source 构建版本保护 | compare-final.txt、result.json |
| check-delivery.py | 最终 0，文档/引用/范围/敏感模式/三仓库保留、HEAD/暂存区与 diff 检查 | delivery-check.txt、delivery-result.json |

正式构建复用 Node 24.16.0 / pnpm 10.34.9 / Angular 21.2.25/21.2.26，未安装包、
改 lock 或改变 Agent Python。单元测试的 Response 负例是独立测试夹具，不计浏览器真实
下载证据；真实页面验收使用未伪造的既有后端/Artifact。
构建警告为既有 ngx-markdown-editor sideEffects、组件样式/Widgets initial 预算，未调预算。

回归实际覆盖：已有用户登录、Cookie 受保护 API、历史 Task/日志/标量、Artifact 下载、
Widgets 深层路径实际绘图、新构建所有静态文件/字体/Plotly、缺失静态 404、代理与匿名 401。
原有可选 credentials/onboarding JSON 404 仍按旧逻辑回退；偏好/统计/第三方继续明确阻断，
对应 HttpErrorResponse(status=0)/ERROR le、GitHub fetch 的 TypeError 逐项保留于
warnings-and-blocks.json 和原浏览器 JSON，未知结构化异常为空，没有用通配忽略未知异常。
新版下载阶段没有 CORS/404 错误，也没有新增 NG0953/ace 错误；C3-A 其他页面历史警告
未因本次范围有限而宣布已修复。

## 失败记录和纠正

1. 首轮边界测试退出 1：测试替身错误地假定 concatLatestFrom 的 factory 只返回数组；
   实际支持 Observable，修正测试替身后通过。没有改变产品实现来迎合错误替身。
2. 首次主构建退出 1：项目严格 noImplicitReturns 要求显式 undefined，URL helper 末尾/
   空输入分支修正后重建通过，保留 build-main.txt。
3. 首次产物检查退出 1：检查器把 favicon.ico?v=7 当磁盘路径；改用 URL path 后通过。
   当时批处理未因检查器失败停止而先切换了 Fork；随后补齐完整资源/874 JS 检查通过，
   后续回退/恢复使用 set -e，失败即停。没有把初次产物检查写成通过，原始日志保留。
4. before/rollback 中的无下载是旧缺陷的预期复现，不能算新版通过；原 C3-A 失败记录不覆盖。

## 原运行与数据保护、交付边界

原六容器 ID/Created/StartedAt/RestartCount/挂载/端口/网络完全不变，均 healthy、重启数 0；
Agent PID 205189、NRestarts=0、启动时间/配置文件元数据/依赖不变。只有 Fork 的身份因
部署、回退、恢复改变，最终 healthy、127.0.0.1:18080、镜像 ID/digest 和只读挂载符合基线。
历史三个 Task 状态、目标完整记录/Artifact URI/元数据、项目/队列/Model 库存、用户偏好
前后相同，真实 Artifact 内容哈希相同；未重跑 Smoke 或运行 Pipeline。

根仓库及 Web/Server HEAD 和暂存区未变；Server 干净。Web 七文件未提交修改，上述
HEAD+补丁+源码清单才构成此次实际源码版本。原 ROADMAP/C2 报告等既有改动保留。

根仓库修改：infra/web-fork 的 compose.yaml、nginx.conf、verify.py、README.md，
新增 prepare-download-release.py；新增本文，兼容报告追加结果，更新 STATUS/HANDOFF/
DECISIONS。本地 raw 构建、release、补丁/日志/截图/工具均保持忽略，无暂存/提交/push。
启停、回退和恢复的精确命令见 [操作说明](../infra/web-fork/README.md)。

本修复无未解决验收阻塞。完整 C3、C3-B 夹具/操作、四风险端点触发、Dataset/Model/
Pipeline 详情关系、其他共享调用方的写入/真实存储签名、所有 HTTP 异常的真实 UI 注入、
完整文件权限、远程端到端、Server Fork 运行、GPU/运维均未扩大验收。后续须用户明确安排。
