# T01-B：ClearML CPU Agent

本机使用已有 `/root/miniconda3/envs/clearml-backend` 环境：Python 3.11.18、
ClearML SDK 2.1.12、ClearML Agent 3.0.3。此次没有安装 Python 包或训练框架。
这是普通 Agent，监听 `rail-cpu`，每次执行一个任务；不使用任务容器、GPU 或 Pipeline。
验收结果见 [T01B_ACCEPTANCE.md](../../docs/T01B_ACCEPTANCE.md)。

## 本地 SDK 配置

实际文件为 `/root/TieSheAI/infra/.local/agent/clearml.conf`，权限 `0600`，
目录权限 `0700`，沿用 `infra/.gitignore` 中的 `.local/` 规则。不要复制到 Git。
模板 [clearml.conf.example](clearml.conf.example) 只有占位符。

| 用途 | 地址 |
|---|---|
| API | `http://127.0.0.1:8008` |
| Web | `http://127.0.0.1:8080` |
| Fileserver / 默认输出存储 | `http://127.0.0.1:8081` |

本机已经完成初始化，无需重新生成凭据。需要在相同部署上首次初始化时：

```bash
cd /root/TieSheAI
/root/miniconda3/envs/clearml-backend/bin/python -B infra/agent/configure_sdk.py
source infra/agent/env.sh
python -B - <<'PY'
from clearml.backend_api.session import Session
response = Session().send_request('server', 'info')
response.raise_for_status()
print('Authenticated server.info:', response.status_code)
PY
```

[configure_sdk.py](configure_sdk.py) 仅适用于当前默认简单登录模式。它在内存中读取
**实际运行镜像**的 Web 注册身份，按现有 Web 流程创建/复用 `TieSheAI T01-B CPU`
用户、登录该用户并创建独立 API 凭据。最终 SDK/Agent 使用普通用户凭据；不会保存
Web 注册身份或 token，不会关闭鉴权。已有 SDK 配置保持原样；存在同名用户歧义或
密码登录已启用时拒绝继续。密码登录环境应使用用户自己的 API 凭据。

## 启动、检查与停止

交付时已安装并启动 `tiesheai-clearml-cpu-agent.service`，未设置开机自启。
安装目标为 `/etc/systemd/system/tiesheai-clearml-cpu-agent.service`，内容与本目录
[service 文件](tiesheai-clearml-cpu-agent.service) 一致。只在目标不存在时安装；
如果存在则先 `cmp`，不要覆盖不同内容的主机配置。

```bash
cd /root/TieSheAI
systemd-analyze verify infra/agent/tiesheai-clearml-cpu-agent.service
# 首次安装，且目标尚不存在时执行：
test ! -e /etc/systemd/system/tiesheai-clearml-cpu-agent.service && \
  install -m 0644 infra/agent/tiesheai-clearml-cpu-agent.service \
  /etc/systemd/system/tiesheai-clearml-cpu-agent.service
systemctl daemon-reload
systemctl start tiesheai-clearml-cpu-agent
systemctl is-active tiesheai-clearml-cpu-agent
journalctl -u tiesheai-clearml-cpu-agent --no-pager -n 80
```

服务调用 [start.sh](start.sh)，实际命令：

```bash
source /root/TieSheAI/infra/agent/env.sh
/root/miniconda3/envs/clearml-backend/bin/python -m clearml_agent daemon \
  --foreground --cpu-only --queue rail-cpu --create-queue
```

如需前台调试，先停止 systemd 服务，再运行 `bash infra/agent/start.sh`，避免重复
Worker ID。停止服务：`systemctl stop tiesheai-clearml-cpu-agent`；停止前确认队列及
正在执行的任务。服务的整个进程组由 systemd 管理。

[env.sh](env.sh) 指定 `CLEARML_CONFIG_FILE`，并设置：

- `CLEARML_AGENT_SKIP_PIP_VENV_INSTALL` 为现有 Python 的绝对路径。
- `CLEARML_AGENT_SKIP_PYTHON_ENV_INSTALL=1`，跳过环境创建和依赖安装。
- 使用 `--cpu-only`；Agent 3.0.3 会将两个 GPU 可见性变量均设为 `none`。

Worker ID 固定为 `tiesheai-rail-cpu:cpu0`。代码、SDK 缓存和运行文件均放在本地
`infra/.local/agent/` 中。任务使用宿主机已有环境；此次复现依赖该环境，依赖快照
保存在验收证据中，并不声称已实现跨主机环境隔离。

## 提交与独立验收

```bash
cd /root/TieSheAI
source infra/agent/env.sh
python -B tests/smoke/run_cpu_smoke.py --evidence infra/evidence/t01b
```

每次省略 `--task-id` 都会新建并入队一个真实任务。只复核已有任务：

```bash
source /root/TieSheAI/infra/agent/env.sh
python -B /root/TieSheAI/tests/smoke/run_cpu_smoke.py \
  --task-id TASK_ID --evidence /root/TieSheAI/infra/evidence/t01b
```

根仓库目前没有提交。提交器使用 `Task.create()` 和 `Task.set_script()` 把
[cpu_smoke.py](../../tests/smoke/cpu_smoke.py) 的完整源码存入任务的 `script.diff`，
清空远端 repository/commit，再用 `Task.enqueue()` 加入 `rail-cpu`。Agent 从服务端
取得脚本并执行，无需克隆 Git、共享工作目录或推送。提交器本身不会执行 Smoke Test。

任务脚本检查 Agent 注入的 Task/Worker 上下文，调用 `Task.init()`、记录参数和
日志，计算 `1²+…+10000²`，记录 `cpu_smoke/check_passed=1.0`，上传固定 JSON。
临时文件在同步上传完成后删除，正常调用 `Task.close()`。

验收器从 API 核对 completed、队列、last_worker、参数、指标和 Agent 拉取日志；
比对服务端完整源码 SHA256；强制下载 Artifact，以上传前日志、Artifact metadata、
下载字节和 [expected.json](../../tests/smoke/expected.json) 四方核对 SHA256。
失败或超时返回非零退出码，保留任务 ID 和现有证据；不会重置失败任务状态。

原始日志可能含运行配置，只保存在已忽略的 `infra/evidence/`；对外提供验收报告中的
脱敏结论。Agent 仅应执行本次授权的可信任务，不会自动创建后续阶段任务。

## 官方参考

- [Agent 环境变量](https://www.clear.ml/docs/latest/docs/clearml_agent/clearml_agent_env_var/)
- [Agent CLI](https://www.clear.ml/docs/latest/docs/clearml_agent/clearml_agent_ref/)
- [SDK Task API](https://clear.ml/docs/latest/docs/references/sdk/task/)

命令和行为以本机已安装版本的 CLI 帮助、源码及实际执行结果核对。
