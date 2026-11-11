# T01-A：ClearML 2.4.0 基础服务

范围：MongoDB、Redis、Elasticsearch、API Server、Web、Fileserver。没有
Agent、GPU 配置、训练任务或 Pipeline controller；不会自动执行 T01-B。

## 版本与方案

使用 ClearML 官方发行镜像自带的 Web，先建立对应版本的服务基线。不构建或挂载
`/root/TieSheAI/clearml-web`、`/root/TieSheAI/clearml-server` 的业务源码。

固定版本取自官方 v2.4.0 部署组合：

| 服务 | 镜像 |
|---|---|
| apiserver / webserver / fileserver | `clearml/server:2.4.0` |
| mongo | `mongo:8.0.15` |
| redis | `redis:8.2.3` |
| elasticsearch | `elasticsearch:8.19.9` |

`compose.yaml` 同时锁定版本号和 digest；最终部署的镜像 ID 见 `images.lock.json`。
发行镜像与本地 Fork 同为 Server 2.4.0，但不宣称二者源码逐字一致。

依据：

- https://github.com/clearml/clearml-server/releases/tag/v2.4.0
- https://github.com/clearml/clearml-server/blob/v2.4.0/docker/compose.yaml
- https://www.elastic.co/guide/en/elasticsearch/reference/8.19/docker.html

## 环境与首次启动

需要 Linux x86_64、可用 Docker daemon、Compose v2、Python 3（仅标准库）、
可访问镜像仓库。当前主机有约 15 GiB 内存，ES 堆固定为 1 GiB。
Python SDK 和 Conda 不参与服务运行。8008 / 8080 / 8081 应未被其他程序占用。

```bash
sudo bash /root/TieSheAI/infra/prepare-host.sh
bash /root/TieSheAI/infra/compose.sh config --quiet
bash /root/TieSheAI/infra/compose.sh pull
bash /root/TieSheAI/infra/compose.sh up -d --wait --wait-timeout 600
python3 -B /root/TieSheAI/infra/verify.py
```

`prepare-host.sh` 创建本地 `.env` 和空配置目录；已有文件不覆盖。
首次创建 `/etc/sysctl.d/99-tiesheai-clearml.conf` 并使
`vm.max_map_count >= 1048576`，不重写其他 sysctl 文件。重复执行可复用相同文件；
遇到不同内容会明确拒绝覆盖。重启后的加载尚需通过真实重启验证。

模板为 `/root/TieSheAI/infra/clearml.env.example`，实际配置文件为
`/root/TieSheAI/infra/.env`。可以调整绑定地址、端口、ES 堆大小；模板没有任何密钥。
`.env`、`.local/`、`evidence/` 已在 infra 自身的 `.gitignore` 中排除。
使用非标准 API/文件端口时，还需在 Web 外部 `configuration.json` 设置对应的
`apiBaseUrl` / `fileBaseUrl`；浏览器的自动推断默认使用 8008 / 8081。

### Docker daemon 无法直连镜像仓库时

命令行的 HTTP_PROXY 不会自动传给 systemd 管理的 Docker daemon。本机采用已运行的
`http://127.0.0.1:7890` 代理。仅在机器上确有该代理、且没有现有容器时执行：

```bash
sudo bash /root/TieSheAI/infra/configure-docker-proxy.sh http://127.0.0.1:7890
```

此脚本新增 `/etc/systemd/system/docker.service.d/90-tiesheai-proxy.conf`，
不改 `/etc/docker/daemon.json`。它会重启 Docker；检测到已有容器时拒绝执行。
其他机器能直连时不需要该步骤；代理带账号密码的地址不受此脚本支持。

## 访问与健康检查

默认仅监听 127.0.0.1：

| 用途 | URL | 验收 |
|---|---|---|
| Web | http://127.0.0.1:8080/ | HTTP 200、HTML 与本地 JS 资源有效 |
| API | http://127.0.0.1:8008/debug.ping | HTTP 200、result_code=200 |
| Server 信息鉴权 | http://127.0.0.1:8008/v2.35/server.info | 未登录返回 401；不是健康检查失败 |
| Fileserver | http://127.0.0.1:8081/ | HTTP 200、OK |
| Web 代理 API | http://127.0.0.1:8080/api/debug.ping | 有效 API 响应 |
| Web 代理文件服务 | http://127.0.0.1:8080/files/ | HTTP 200、OK |

远程客户端可把三个端口一起转发；在客户端执行：

```bash
ssh -N -L 8080:127.0.0.1:8080 -L 8008:127.0.0.1:8008 -L 8081:127.0.0.1:8081 root@192.168.52.59
```

此 IP 是本次部署时的主机地址，其他机器应替换。随后在客户端打开
http://127.0.0.1:8080/。本轮不创建 API key、不配置 Agent。对外直接开放访问、TLS、
正式账号策略不在 T01-A 中处理。
`verify.py` 从运行容器导入 `apiserver.version` 确认版本为 2.4.0，不绕过 API 鉴权。

## 持久化与配置

Compose 项目固定为 `tiesheai-clearml`，避免与既有 ClearML 部署共用数据。
首次部署前已检查本机没有 Docker 卷；不会迁移或覆盖 `/opt/clearml`。

| 卷后缀（实际前缀 `tiesheai-clearml_`） | 容器路径 / 用途 |
|---|---|
| mongo-data / mongo-config | `/data/db`、`/data/configdb` |
| redis-data | `/data`，开启 AOF |
| elastic-data / elastic-logs | ES 数据、文件日志 |
| fileserver-data | `/mnt/fileserver`，API 和 Fileserver 共享 |
| clearml-logs | `/var/log/clearml`，三个 ClearML 服务共享 |
| web-logs | `/var/log/nginx`，独立访问日志和错误日志文件 |

主机 `/root/TieSheAI/infra/.local/clearml/config` 只读挂载到 ClearML 服务配置目录。
主机 `/root/TieSheAI/infra/.local/clearml/web` 只读挂载到 Web 外部配置目录；
需要 Web 配置时放入 `configuration.json`。新目录默认为空，使用镜像内置配置。
Web 静态资源来自固定镜像，不用数据卷遮盖，重建时可恢复同一版本。

`nginx.conf.template` 只是 nginx 进程配置，保留 `/api/`、`/files/`、widgets 路由，
将 Web 日志写入持久卷；没有修改 Web 应用代码。

空实例不导入官方示例数据。未部署异步删除进程，已关闭异步 URL 删除开关。
数据库健康后启动 API，API 健康后再启动 Fileserver 和 Web。Fileserver 初始化时要
访问 API 鉴权，不能让 API 又等待 Fileserver 健康，以免形成循环依赖。

## 日常检查、停止与恢复

```bash
bash /root/TieSheAI/infra/compose.sh ps
bash /root/TieSheAI/infra/compose.sh logs --no-color --tail 100
python3 -B /root/TieSheAI/infra/verify.py
sysctl vm.max_map_count
```

只停止服务并保留容器、数据卷：

```bash
bash /root/TieSheAI/infra/compose.sh stop
bash /root/TieSheAI/infra/compose.sh up -d --wait --wait-timeout 600
```

需要重建容器时运行相同的 `up` 命令，命名卷继续保留。不要添加删除卷选项或执行
volume prune。数据库一致性备份应在停止相关写入后进行；本轮未执行备份恢复演练。

## 本轮记录

最终实际镜像、端口、容器状态、验收输出及剩余问题见 `DEPLOYMENT_RESULT.md`。
原始本地日志保存在 `/root/TieSheAI/infra/evidence/`，不进入 Git。
Fileserver 的根路径可达性不等于已验证认证上传；Task/Artifact/Agent 验收留给 T01-B。
