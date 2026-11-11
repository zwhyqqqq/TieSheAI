# T01-C1：ClearML Web Fork 构建验证

记录时间：2026-11-09 21:47（Asia/Hong_Kong，UTC+08:00）。

**结论：通过。** 主应用和 Widgets 构建成功；修复 Widgets 共享资源复制配置后，
两套实际产物完整性检查通过。现有六服务和 CPU Agent 未重启，运行环境未改变。
本轮未独立部署、未启动 18080 服务、未进行 Web Fork/API 联调，未进入 T01-C2。

## 仓库与工具链

| 项目 | 实际检查 |
|---|---|
| 根仓库 | 无提交；已有 AGENTS、docs、infra、tests 和两个独立 Fork 等内容未跟踪，保留原状态 |
| Web Fork 基点 | `5c4943bfecb3971e50b379b0af1db6b4c63954cf`；开始时工作区干净 |
| Server Fork | `2ebdc43951b9432cc7fa528bbb3a7100fc6fe805`；前后均干净，业务源码无修改 |
| Web 应用版本 | `package.json` 为 2.5.0，与当前官方镜像 Web 2.4.0-722 分开记录 |
| Node | 24.16.0；现有 fnm 环境，无安装或切换 |
| pnpm | 10.34.9；项目 engines 为 `^10` |
| Angular | core/compiler 21.2.25；CLI/build 21.2.26；CDK/Material 21.2.14 |
| TypeScript / RxJS / zone.js | 5.9.3 / 7.8.2 / 0.16.3 |
| Node 要求 | 本机 Angular 包声明 `^20.19.0 || ^22.12.0 || >=24.0.0`，当前满足 |

版本由 `node --version`、`pnpm --version`、`pnpm exec ng version` 和已安装包的
`package.json` 核对。仓库 README 与 CI 均使用 Node 24 / pnpm 10。
复用已有 `node_modules`；本轮没有执行 install，没有修改 package.json、pnpm lock、
workspace 或 npm 配置。全新机器的依赖安装尚未复验。

## 构建配置与实际执行

工作目录为 `/root/TieSheAI/clearml-web`。两项目使用 `@angular/build:application`。
构建进程设置 `CI=true NG_CLI_ANALYTICS=false NG_BUILD_MAX_WORKERS=2`，nice=10；
两次初始构建顺序执行，避免同时占用大量资源。耗时由外层 monotonic 时钟测量，
包含 pnpm 和 Angular 子进程的完整运行时间。

| 命令 / 轮次 | 时间（Asia/Hong_Kong） | 耗时 | 退出码 |
|---|---|---|---|
| `pnpm run build` | 21:41:44–21:42:53 | 69.324 秒 | 0 |
| `pnpm run build-widgets` 初次 | 21:42:53–21:43:14 | 20.430 秒 | 0 |
| `pnpm run build-widgets` 资源修复后 | 21:44:05–21:44:26 | 21.204 秒 | 0 |

- 主应用：`ng build --configuration production --source-map`，生产配置优化、文件名
  hash；脚本的 `--source-map` 覆盖配置中的 false，实际生成 635 个 map 文件。
  输出为 `build/browser/`，并使用 production environment/build-specifics 替换。
- Widgets：`ng build --project report-widgets --configuration production`，
  输出为 `dist/report-widgets/browser/`，实际没有 source map。
  initial 预算 warning=1 MB / error=2 MB；组件样式 warning=2 kB / error=5 kB。
- 主应用只定义组件样式 warning=6 kB。没有调整任何预算或隐藏警告来通过验收。

## 发现的问题与最小修复

初次两条编译命令都退出 0，但产物验收退出 1：Widgets 输出中的
`app/webapp-common/assets` 是 21 字节普通文本文件，内容是相对路径，并非资源目录。
对应源码占位文件在 Git 中也是 100644 普通文件；构建器按原配置将其直接复制。
结果缺少 `plotly-2.35.0.min.js` 等动态加载的共享资源，仅检查 index.html 不足以发现。

仅修改 Web Fork 的 [angular.json](../clearml-web/angular.json)：将该占位文件和
其下不存在的字体路径两条 assets 声明，替换为明确的目录复制规则：

```json
{
  "glob": "**/*",
  "input": "src/app/webapp-common/assets",
  "output": "app/webapp-common/assets"
}
```

递归复制已包含字体，不再保留重复且无效的字体声明。未修改组件、占位文件、依赖、
Server 业务源码或主应用构建配置。重建 Widgets 后，两套产物验收均通过。
主应用原产物哈希保持不变，无需重复构建。

## 实际产物与完整性验收

| 产物根目录（相对 Web Fork） | 文件数 | 总字节 | 根级 JS / CSS | map |
|---|---:|---:|---|---:|
| `build/browser/` | 1817 | 57,230,243 | 372 / 2 | 635 |
| `dist/report-widgets/browser/` | 318 | 19,240,661 | 11 / 2 | 0 |

静态完整性检查执行 `python3 -B infra/evidence/t01c1/check-artifacts.py`，修复后退出 0：

- 两套 index.html 存在，引用的入口 JS、预加载分块和样式均为实际非空文件。
- JS 静态/动态 import 分块、声明的 source map、CSS 字体等本地资源引用有效。
- 两套共享资源均为目录，逐文件与源码比对 SHA256；包含完整 Plotly、字体和图标。
- 主应用包含 env.js、logo、Ace 资源；Widgets 包含动态加载的 `trains-icons.css`。
- 每套产物保存逐文件字节数和 SHA256 清单。没有将编译产物当作浏览器运行或 API
  兼容性验收；没有启动静态 HTTP 服务。

index.html SHA256：

```text
主应用：437e04c34ebfdbfa8247a9ac0650e809bb03bbf0a8329d1956cbf540d3a5c3ea
Widgets：fcdd27f1c9eab2690a15791911df4839d2ad93c283a64ee74210dff6159a2dff
```

## 警告与错误

三次构建均没有编译错误。主应用有 4 条警告；两次 Widgets 各有相同的 6 条警告。

| 项目 | 警告 |
|---|---|
| 主应用 | ngx-markdown-editor 的 bare import 被依赖的 sideEffects 声明裁剪；未验证其浏览器行为 |
| 主应用组件样式 | markdown-editor 12.62 kB、experiment-graphs 7.23 kB、table 8.42 kB，超过 6 kB warning |
| Widgets initial | 1.51 MB，超过 1 MB warning，低于 2 MB error |
| Widgets 组件样式 | graph-viewer 2.83 kB、image-viewer 3.80 kB、single-graph 4.42 kB、debug-image-snippet 2.10 kB、breadcrumbs 2.86 kB；均超过 2 kB warning，低于 5 kB error |

初次产物验收的 assets 错误及退出 1 保留原证据；修复后的完整检查退出 0。
所有警告明细见 `warnings.json` 和原始构建日志，不在交接文件中复制长日志。

## T01-A / T01-B 未受影响的检查

- 前后 `python3 -B infra/verify.py` 均退出 0：六个服务 running/healthy，RestartCount=0，
  镜像、挂载、端口、现有 Web 静态资源/代理及数据库健康检查通过；匿名 server.info 仍为 401。
- 六容器的 ID、StartedAt、RestartCount 前后完全相同，没有重建或重启。
- `systemctl show tiesheai-clearml-cpu-agent` 前后内容相同：active/running、MainPID 205189、
  NRestarts=0，启动时间仍为 2026-11-09 21:20:19（Asia/Hong_Kong）。
- `clearml-backend` 的 pip freeze 前后完全相同，且与 T01-B 原有快照相同。
  原有部署/Agent 文件、本地凭据和主机 Agent unit 哈希未变化。
- 端口 18080 前后均无监听。未创建新的 Agent 任务，未重做 T01-B 完整任务链路。
  此处确认现有进程/配置/环境未受影响，不替代新的训练或 API 联调测试。

## 后续 18080 独立部署分析（未实施）

以下为基于源码和产物的待验证方案，不是部署完成结论或已确认的运行选型：

1. 后续可用独立 Nginx 静态站点或独立 Compose 项目，绑定 `127.0.0.1:18080`。
   将两套产物复制到独立只读 release 目录，主应用映射 `/`，Widgets 映射 `/widgets/`；
   各自配置 SPA fallback，Widgets 资源路径必须从其自己的产物目录解析。
   `/widgets` 重定向到 `/widgets/`，以匹配相对资源和 `../configuration.json` 的解析。
2. 提供独立的运行时 `/configuration.json`，显式设定 `apiBaseUrl: "/api"`、
   `fileBaseUrl: "/files"`；Widgets 路由所需 baseHref 在下一阶段验证。
   主应用生产 assets 没有复制源目录顶层的 configuration.json，不能假定它已随构建生成。
   18080 也不在源码的 Fileserver 端口自动推断分支中，须显式配置。
3. `/api/`、`/files/` 在新站点分别转发至现有 API / Fileserver，剥离前缀、保留鉴权。
   如采用宿主机 Nginx，可访问 `127.0.0.1:8008 / 8081`；如采用独立桥接容器，
   不可把容器内 127.0.0.1 当作宿主机。可评估加入现有 `tiesheai-clearml_default`
   external network，使用 `apiserver:8008 / fileserver:8081`；本轮未创建或连接容器。
4. 按实际部署子路径处理 env.js 中 `${CLEARML_SERVER_SUB_PATH}` 占位符，并按需提供
   能区分 Fork 提交与官方发行版的版本信息；当前生产顶层没有 version.json。
   主应用 source map 是否随站点发布也应在部署打包时明确。
5. 下一阶段须验证静态响应、SPA/Widgets 路由、登录、Cookie/鉴权、API/文件代理和
   浏览器行为；不能用此次构建成功替代 Web 2.5.0 与 Server 2.4.0 的兼容性验收。

本轮没有创建 nginx/Compose 配置，没有启动服务或改变现有 8080 Web。

## 修改、证据与剩余边界

实际修改：Web Fork 的 `angular.json`；根仓库的 `AGENTS.md`、`docs/STATUS.md`、
`docs/HANDOFF.md`、`docs/DECISIONS.md`，以及新增本报告。
AGENTS 将会过期的固定阶段描述改为引用 STATUS/HANDOFF；新决策记录仅限已验证范围。
Web Fork 最终只有 angular.json 修改；Server Fork 干净。未暂存、提交或 push。
构建产物、node_modules 和 Angular 缓存沿用 Web Fork 忽略规则，原始证据沿用 infra 忽略规则。

本地证据目录：`infra/evidence/t01c1/`（不进入 Git）：

- `angular-version.txt`、`node-packages.json`、`web-config-hashes.json`：工具链与配置哈希。
- `build.log`、`build-widgets-initial.log`、`build-widgets.log`、`warnings.json`：构建输出。
- `build-results-initial.json`、`build-widgets-rebuild.json`：命令、开始/结束时间、耗时、退出码。
- `artifact-check-initial.txt`（退出 1）、`artifact-check.txt`（退出 0）、`artifacts.json`、
  `main-artifact-manifest.json`、`widgets-artifact-manifest.json`：实际产物验证与清单。
- `t01a-before.txt`、`t01a-after.txt`、`containers-before.txt`、`containers-after.txt`、
  `agent-before.txt`、`agent-after.txt`、`python-environment-*.txt`、`port18080-*.txt`：前后运行环境。
- `check-delivery.py`、`delivery-checks.txt`：本轮文档/证据一致性、敏感信息、忽略规则、
  Git 差异与范围检查，执行退出 0；`before-hashes.json` 和 `git-*-before.txt` 保留基线。

T01-C1 无未解决的验收阻塞；保留上述非阻塞构建警告。独立部署、运行配置、浏览器/
Widgets 功能、API 联调、干净环境依赖安装均未验证。T01-C2 未开始，须用户明确授权。
