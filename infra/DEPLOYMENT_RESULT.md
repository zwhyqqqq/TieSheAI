# T01-A 实际部署结果

记录时间：2026-11-09 20:56（Asia/Hong_Kong，UTC+08:00）。

结论：基础服务验收通过，六个容器均处于 running / healthy，当前容器 RestartCount
均为 0。服务保持运行。本轮未配置 Agent、未创建训练任务、未执行 git push，未进入 T01-B。

## 实际运行版本

| 服务 | 镜像版本 | 镜像 digest（前缀） | 实测 |
|---|---|---|---|
| apiserver / fileserver / webserver | clearml/server:2.4.0 | 5ec4aed2e40c | 三者 healthy |
| mongo | mongo:8.0.15 | f4d54619262a | db.version() = 8.0.15；ping ok=1 |
| redis | redis:8.2.3 | 0908d9af26bf | redis_version=8.2.3；PONG；appendonly=yes |
| elasticsearch | elasticsearch:8.19.9 | dee84085936b | version=8.19.9；cluster status=green |

完整 digest、运行镜像 ID 和架构记录于 `/root/TieSheAI/infra/images.lock.json`。
`compose.yaml` 已同时锁定版本和 digest，`verify.py` 也比对了实际运行镜像 ID。

API 容器中 `apiserver.version.__version__` 为 `2.4.0`。
Web `/version.json` 返回 `2.4.0-722`，内含 Server commit
`7eb608002473ec6ae41ae849c0a80c0cfba7fd58` 和 Web commit
`dd9ee2af002a417611c40e8b36b1462d6cff2311`。
这是发行镜像自带的 Web，不是本地 Angular 2.5.0 Fork 的构建产物。

## 地址与 HTTP 验收

| 地址 | 实际结果 |
|---|---|
| http://127.0.0.1:8008/debug.ping | HTTP 200；meta.result_code=200；data.msg=ClearML server |
| http://127.0.0.1:8080/ | HTTP 200；应用 HTML 有效 |
| http://127.0.0.1:8080/env.js | HTTP 200 |
| http://127.0.0.1:8080/polyfills-JUTM3XWE.js | HTTP 200；非 HTML 回退页 |
| http://127.0.0.1:8080/scripts-7XNDUXAS.js | HTTP 200；非 HTML 回退页 |
| http://127.0.0.1:8080/main-Y2VLLEHT.js | HTTP 200；非 HTML 回退页 |
| http://127.0.0.1:8081/ | HTTP 200；OK |
| http://127.0.0.1:8080/api/debug.ping | HTTP 200；API 反向代理有效 |
| http://127.0.0.1:8080/files/ | HTTP 200；OK；Fileserver 反向代理有效 |
| http://127.0.0.1:8008/v2.35/server.info | 未登录返回 HTTP 401；保留鉴权，未绕过 |

数据库端口没有发布到宿主机，三个应用端口均仅绑定 127.0.0.1。
远程访问需要同时转发 8008 / 8080 / 8081；命令见 `README.md`。

## 实施与检查命令

```bash
bash /root/TieSheAI/infra/prepare-host.sh
bash /root/TieSheAI/infra/compose.sh config --quiet
bash /root/TieSheAI/infra/configure-docker-proxy.sh http://127.0.0.1:7890
bash /root/TieSheAI/infra/compose.sh pull
bash /root/TieSheAI/infra/compose.sh up -d --wait --wait-timeout 600
python3 -B /root/TieSheAI/infra/verify.py
bash /root/TieSheAI/infra/compose.sh exec -T webserver nginx -t
```

最终 Compose up 与 `verify.py` 均退出 0。nginx 配置检查通过。
shell 语法检查、Compose 配置解析、Git 忽略规则检查均通过。

`verify.py` 检查项目恰好包含六个服务、健康状态、锁定镜像及实际镜像 ID、必需的
持久化挂载、API 健康响应、Web HTML/脚本、Fileserver 响应、反向代理和数据库探测。

## 持久化与主机变更

创建八个 `tiesheai-clearml_` 前缀的命名卷，覆盖 MongoDB 数据/configdb、Redis AOF、
Elasticsearch 数据/日志、Fileserver 文件、ClearML 日志和 Web nginx 日志。
外部配置保存在 infra 下已忽略的 `.local/clearml/config`、`.local/clearml/web`，
以只读方式挂载。Web 日志文件已实际生成，访问日志非空，错误日志为空。
容器重建时复用了这些卷；未删除卷、未覆盖已有数据或用户配置。

新增的主机文件：

- `/etc/sysctl.d/99-tiesheai-clearml.conf`：vm.max_map_count 从 65530 提高到 1048576，
  已实时生效，并配置为后续启动加载。
- `/etc/systemd/system/docker.service.d/90-tiesheai-proxy.conf`：Docker daemon 使用本机
  已有的 127.0.0.1:7890 代理；未修改 `/etc/docker/daemon.json`。

Docker 服务已确认 enabled。新增配置遇到同名不同内容文件会拒绝覆盖。
首次部署前 Docker 容器、镜像、数据卷均为空，`/opt/clearml` 不存在。
两个 ClearML Fork 工作区在结束时仍干净，业务源码无改动。
根目录尚无 Git 提交；没有暂存、提交或推送。本地 `.env`、运行配置和原始日志受
`infra/.gitignore` 排除；模板与部署代码未保存密码、API key 或 token。

## 已处理的问题与剩余边界

1. 首次镜像拉取因 Docker daemon 未继承命令行代理而超时；独立 systemd drop-in
   生效后拉取成功。以后拉取镜像仍依赖该代理可用，已有本地镜像的服务启动无需重新拉取。
2. 首次启动把 API 依赖设置为等待 Fileserver 健康，Fileserver 又先访问 API 鉴权，
   导致依赖失败。最终改为数据库 → API → Fileserver/Web，重建后六个容器均健康，
   当前 Fileserver 日志无此启动连接失败。
3. 初版验收把匿名 server.info 的 401 当作失败。实际服务有鉴权；最终验收明确记录
   401，并从容器源码和镜像核验版本，没有关闭或绕过鉴权。
4. 未验证：浏览器内交互与用户登录、认证后的业务 API、Fileserver 认证上传/下载、
   CPU Agent/Task/Artifact、主机重启恢复、备份恢复及长期负载。它们不计入本轮完成结果。
5. 仅监听回环地址；未进行远程客户端 SSH 转发的端到端验证。

## 原始证据

本机 `/root/TieSheAI/infra/evidence/` 中保存：

- `acceptance.txt`：最终完整验收输出，结尾为 T01-A live acceptance: PASS。
- `containers.txt`、`runtime.json`：服务状态、端口、运行镜像和持久化挂载。
- `services.log`：最终容器日志；`nginx-check.txt`：nginx 配置检查。
- `mongo-version.txt`、`redis-version.txt`、`elasticsearch-version.json`、`web-version.json`。
- `sysctl.txt`、`volumes.txt`、`recorded_at.txt`。
- `t01a-pull.log`、`t01a-up.log`、`t01a-up-final.log`、`t01a-converge.log`：
  拉取和部署过程，包含首次依赖失败及最终收敛成功记录。
- `acceptance-initial-auth-check.txt`：初版验收遇到匿名 401 的原始记录。

这些原始日志仅保存在本地，不进入 Git。
