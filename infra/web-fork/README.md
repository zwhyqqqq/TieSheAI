# 独立 Web Fork 测试站点

当前运行 release 为 `data-entry-20261111-v1`，监听 `127.0.0.1:18080`。原下载修复 release 可回退。
Compose 项目 `tiesheai-web-fork` 只有一个非 root Nginx；镜像/digest、只读根文件系统、
只读挂载、external backend 网络与回环绑定保留。原六服务和 Agent 不参与此项目启停。

当前下载修复、源码/产物版本、真实浏览器及回退证据见
[T01C_ARTIFACT_DOWNLOAD_FIX.md](../../docs/T01C_ARTIFACT_DOWNLOAD_FIX.md)。
C2 历史部署见 [T01C2_DEPLOYMENT.md](../../docs/T01C2_DEPLOYMENT.md)，
C3-A 原失败保留在 [兼容性报告](../../docs/T01C_COMPATIBILITY.md)。完整 C3 仍未通过。

## T02-B 数据准备入口

登录后打开 [数据准备](http://127.0.0.1:18080/data-preparation)。当前版本与证据见
[T02-B 验收报告](../../docs/T02B_WEB_DATA_ENTRY.md)。`compose-data-entry.sh` 加载固定 release
及同源适配路径。适配层通过私有 Unix socket 接收请求，运行台账保存在 `infra/.local/data-entry/`。

回退使用原 `compose.sh` 和原固定 release。恢复先启动适配层，再用 `compose-data-entry.sh`。
以下命令从仓库根目录执行。

```bash
# 回退
bash infra/web-fork/compose.sh up -d --pull never --wait --wait-timeout 90
systemctl stop tiesheai-web-data-entry.service

# 恢复
systemctl start tiesheai-web-data-entry.service
bash infra/web-fork/compose-data-entry.sh up -d --pull never --wait --wait-timeout 90
```

以下为历史 Artifact 下载修复发布说明，其命令以旧 release 为目标。

## 构建和发布

本轮使用现有 Node 24.16.0 / pnpm 10.34.9，不安装依赖或改 lock。正式构建独立输出，
不会覆盖 C1 的 `build/browser` / `dist/report-widgets/browser`。

```bash
cd /root/TieSheAI
node clearml-web/tests/artifact-download.cjs
CI=true NG_CLI_ANALYTICS=false NG_BUILD_MAX_WORKERS=2 nice -n 10 pnpm --dir clearml-web run build --output-path out/artifact-download-fix/main
CI=true NG_CLI_ANALYTICS=false NG_BUILD_MAX_WORKERS=2 nice -n 10 pnpm --dir clearml-web run build-widgets --output-path out/artifact-download-fix/widgets
```

本轮源版本与补丁/源码清单在 `infra/evidence/artifact-download-fix/source-version.json`、
`web-source.patch`、`source-manifest.json`；未提交源码不能只用旧 HEAD 表示。
`prepare-download-release.py` 以该源码清单核对当前工作区，再打包新构建；新 release
已存在时拒绝覆盖。打包不发布 map，保留源构建/发布两份清单与不同哈希。
当前 release 已创建；日常启停不要重跑打包脚本。C2 `prepare-release.py` 保留作历史记录，
同样不会覆盖已有 C2 release。未来源码变更须另建版本路径和相应清单，不能原地覆盖。

## 路径、配置和鉴权

主站 `/`，Widgets `/widgets/`，308 跳转/深链/HTML base 保留。配置显式 `/api`、`/files`；
新 release 的 `fileServerAliases` 仅明确列出本机历史 Artifact 的 `http://127.0.0.1:8081`。
别名在部署配置，不硬编码到业务源码；不推断任意 8081 来源，不从业务 URI 自动扩展信任。
可信 URL 按 origin 与路径边界匹配，规范化到当前浏览器 origin 的 `/files`，保留编码/query。
外部/S3 等地址保留既有处理。原 API/Fileserver 鉴权、Cookie/Authorization 代理均不改。

`/version.json` 的 source_head、source_dirty、source_patch_sha256、source_manifest_sha256
分别表示 HEAD 基点、未提交状态及完整补丁/源码清单；`/configuration.json` 的 version
是当前运行标识。`X-TieSheAI-Web: web-fork` 只标识站点，具体版本以 JSON 与发布清单为准。
缺失静态资源返回 404，map 不发布；原 Nginx 仅该站点标识头改变，没有改变代理/CORS。

Cookie 不按端口隔离，与 8080 比较须使用独立浏览器 profile/context。
远程可转发 `ssh -N -L 18080:127.0.0.1:18080 root@192.168.52.59`，
然后打开 `http://127.0.0.1:18080/`；远程端到端仍未实测。

## 检查、停止、回退与恢复

```bash
bash /root/TieSheAI/infra/web-fork/compose.sh ps
bash /root/TieSheAI/infra/web-fork/compose.sh exec -T web nginx -t -c /etc/nginx/fork.conf
python3 -B /root/TieSheAI/infra/web-fork/verify.py
bash /root/TieSheAI/infra/web-fork/compose.sh stop
bash /root/TieSheAI/infra/web-fork/compose.sh up -d --pull never --wait --wait-timeout 90
```

回退到保留的 C2 v2，**只重建 Fork**（此版本已知按钮无实际下载）：

```bash
FORK_RELEASE_DIR=../.local/web-fork/releases/c2-be71d50-v2 bash /root/TieSheAI/infra/web-fork/compose.sh up -d --pull never --wait --wait-timeout 90
python3 -B /root/TieSheAI/infra/web-fork/verify.py --manifest /root/TieSheAI/infra/evidence/t01c2/release-manifest.json
```

恢复修复版（Compose 默认固定为新版）：

```bash
bash /root/TieSheAI/infra/web-fork/compose.sh up -d --pull never --wait --wait-timeout 90
python3 -B /root/TieSheAI/infra/web-fork/verify.py
```

本轮真实回退 v2 并从原按钮复现旧失败，再恢复新版、真实下载成功；结束时新版运行。
如需完全撤除测试入口，只 stop 此独立项目，继续使用官方 8080，不删 release 或卷。
不要对原 `/root/TieSheAI/infra/compose.yaml` 执行 stop/down/restart；不要使用删除卷选项。
