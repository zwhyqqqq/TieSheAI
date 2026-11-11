# T01-B：ClearML CPU Agent 联调验收

记录时间：2026-11-09 21:23（Asia/Hong_Kong，UTC+08:00）。

**结论：通过。** 普通 CPU Agent 从 `rail-cpu` 获取任务并执行至 `completed`；
认证 API、任务参数/日志/指标、Artifact 上传与强制下载、SHA256 一致性均通过。
未执行本地 Smoke 成功运行来代替 Agent 执行。

## 环境、队列与 Agent

| 项目 | 实测 |
|---|---|
| 基础服务 | 官方 ClearML Server 2.4.0；T01-A 前后复核均 6/6 healthy，RestartCount=0 |
| 环境 | `/root/miniconda3/envs/clearml-backend`，Python 3.11.18 |
| SDK / Agent | 2.1.12 / 3.0.3（均为既有安装） |
| API / Web / Fileserver | `127.0.0.1:8008 / 8080 / 8081`，HTTP |
| SDK 认证 | 用户凭据登录成功；受保护的 `server.info` HTTP 200，版本 2.4.0；匿名仍为 401 |
| Queue | `rail-cpu`，ID `9821226b7d1c4d57b4dae4418bd1f28b` |
| Worker | `tiesheai-rail-cpu:cpu0` |
| 运行方式 | systemd 管理普通 Agent，`daemon --foreground --cpu-only --queue rail-cpu --create-queue` |
| 任务 Python | `/root/miniconda3/envs/clearml-backend/bin/python`，宿主机已有环境，跳过依赖安装 |
| 服务状态 | `tiesheai-clearml-cpu-agent.service` active/running，MainPID 205189，NRestarts=0；未启用开机自启 |

配置与启动操作见 [infra/agent/README.md](../infra/agent/README.md)。
凭据仅保存在本地 `infra/.local/agent/clearml.conf`（0600，父目录 0700），
已验证受 Git 忽略。注册流程沿用既有 Web 简单登录，不改变服务鉴权设置。

## 成功任务与执行证据

- Task ID：`d13dc5bcdbc248f0bb80509eb66b9b36`，项目 `TieSheAI/Smoke`，类型 `testing`。
- [本机任务日志页](http://127.0.0.1:8080/projects/d9d0a4660b1e467ebba8508f29b66275/tasks/d13dc5bcdbc248f0bb80509eb66b9b36/output/log)。
- 观测状态：21:22:42 queued → 21:22:44 in_progress → 21:23:09 completed。
- 服务端 `last_worker` 为上述 Worker，`execution.queue` 为上述 Queue；
  参数 `Execution/running_locally=False`，Python 绝对路径与预期一致。
- Task 日志含 Agent 的取队列记录、任务内的 Agent 上下文记录，以及
  `Process completed successfully`。以下为不含凭据的关键日志：

```text
task d13dc5bcdbc248f0bb80509eb66b9b36 pulled from 9821226b7d1c4d57b4dae4418bd1f28b by worker tiesheai-rail-cpu:cpu0
T01B_AGENT_EXECUTION task=d13dc5bcdbc248f0bb80509eb66b9b36 worker=tiesheai-rail-cpu:cpu0 python=/root/miniconda3/envs/clearml-backend/bin/python
T01B_BEFORE_UPLOAD_SHA256=b00ed20e939a658612bc0586861bf1af2ece002c6b20bcfee5255194592555a9
T01B_SMOKE_OK result=333383335000 artifact_sha256=b00ed20e939a658612bc0586861bf1af2ece002c6b20bcfee5255194592555a9
Process completed successfully
```

参数经 SDK 回读：`Smoke/limit=10000`、`expected_sum_squares=333383335000`、
`artifact_schema=1`、`device=cpu`；`Execution/cuda_visible_devices=none`，
与 Agent 3.0.3 `--cpu-only` 的设置一致。指标 `cpu_smoke/check_passed` 的 iteration=0、
value=1.0，经曲线 API 回读精确一致。完整整数计算结果另在日志和 Artifact 中核对。

根仓库有 origin，但尚无任何提交。没有尝试用不存在的提交拉取代码；通过 SDK 将
完整独立脚本存入 `script.diff`，repository 为空。Agent 从服务端获取并在本地
`infra/.local/agent/work/code/cpu_smoke.py` 执行。
提交源码与完成后服务端源码 SHA256 均为：

```text
4f0ee146a0e1a6f376d61c6d553676ebc979641126267bccf3ead4186d5871cd
```

## Artifact

名称 `cpu-smoke-json`，JSON 长度 122 字节。Artifact URI：

[下载本机 Artifact](http://127.0.0.1:8081/TieSheAI/Smoke/T01-B%20CPU%20Smoke.d13dc5bcdbc248f0bb80509eb66b9b36/artifacts/cpu-smoke-json/cpu-smoke.json)

`get_local_copy(force_download=True, extract_archive=False)` 强制下载，未以本机已缓存
文件作为下载证据。上传前日志、Artifact metadata、下载后字节和
[expected.json](../tests/smoke/expected.json) 的 SHA256 均为：

```text
b00ed20e939a658612bc0586861bf1af2ece002c6b20bcfee5255194592555a9
```

下载内容与 fixture 逐字节一致；内容为固定字段 `device=cpu`、
`message=TieSheAI T01-B CPU smoke test`、`schema_version=1`、
`sum_squares=333383335000`，无时间戳、Task ID 或环境相关字段。

## 检查命令与结果

以下相对命令均在 `/root/TieSheAI` 执行。SDK 命令先运行
`source infra/agent/env.sh`；所有管道使用 `set -euo pipefail`，证据创建使用 umask 077。

| 命令 / 检查 | 结果 | 退出码 | 本地证据（相对 `infra/evidence/t01b/`） |
|---|---|---|---|
| `python3 -B infra/verify.py`（前后） | PASS，六服务健康、镜像/端口/鉴权基线有效 | 0 / 0 | `t01a-before.txt`、`t01a-after.txt` |
| `python -B infra/agent/configure_sdk.py`（修正后） | 创建本地用户 API 配置 | 0 | `configure-sdk.log` |
| `python -B -` 调用 `Session().send_request('server','info')` | 认证 HTTP 200，SDK 连接通过 | 0 | `sdk-auth.json` |
| `python -B tests/smoke/run_cpu_smoke.py --evidence infra/evidence/t01b`（最终） | 真正 Agent 执行，完整验收 PASS | 0 | `smoke-run.log`、`latest.json` |
| `python -B -` 检查本地直接运行保护 | 拒绝执行，未调用 Task.init | 包装检查 0，预期子进程 1 | `local-execution-guard.txt` |
| `python -m pip freeze` 前后及 `cmp` | 内容完全相同，未安装/移除依赖 | 0 | `environment.txt`、`environment-after.txt` |
| `bash -n infra/agent/env.sh infra/agent/start.sh` | PASS | 0 | Codex 执行记录；`delivery-checks.txt` |
| `systemd-analyze verify infra/agent/tiesheai-clearml-cpu-agent.service`、主机文件 `cmp` | PASS | 0 | `systemd-verify.txt`；`delivery-checks.txt` |
| `python3 -B infra/evidence/t01b/check-delivery.py` | 文档/引用、Python 语法、凭据泄漏扫描、权限、文件范围通过 | 0 | `delivery-checks.txt` |
| 根仓库、两个 Fork `git diff --check`；Fork `git status --short` | PASS；两个 Fork 干净 | 0 | `delivery-checks.txt` |

依赖快照 SHA256 为 `8bce3a27d8599d1ccb1237e5afada9fc21adc62a234fca8fb70d106f2c61f2ac`。
最终任务目录 `infra/evidence/t01b/d13dc5bcdbc248f0bb80509eb66b9b36/` 包含
`acceptance.json`、`status.json`、`server-script.json`、`task-console.txt`、
`downloaded.json`。另有 `submission.json`、`worker-before.json`、
`agent-journal.log`、`agent-service.txt`、`deployment-hashes.json`。
原始证据受 Git 忽略，留在本机；本报告是可入库的脱敏验收结论。

## 如实保留的失败与修正

1. SDK 初始化首次因使用旧的 impersonation header 而在 `auth.create_credentials`
   返回 HTTP 400，命令退出 1。修正为运行版本支持的 `X-ClearML-Impersonate-As` 后，
   复用已创建用户并成功生成其凭据；未关闭鉴权。
2. Task `f916492e5cb341b883cbe83b2e433451`：Agent 真正执行后 failed，验收退出 1。
   原因是测试未接受 Agent 的 CPU 可见性值 `none`；修正后重提，失败任务保持原状态。
   证据为该 Task 子目录及 `smoke-run-initial.log`。
3. Task `022416d3356e4d56b088b25f513ec858`：Agent 执行 completed，但验收阶段退出 1。
   先修正验收器从 `get_script()` 读取不到 diff 的问题，改从完整服务端记录核对。
   随后发现大整数指标曲线返回 `333383335936.0`，而 summary 的 last 值为
   `333383335000.0`。最终改用精确的 `check_passed=1.0` 指标，计算整数保留在 JSON
   和日志，并重新执行最终任务。此中间任务未宣称通过最终验收；日志保留在
   `smoke-run-before-verifier-fix.log`、`verification-large-scalar.log` 及 Task 子目录。

## 实际修改与边界

- 新增 `infra/agent/` 的 `README.md`、`clearml.conf.example`、`configure_sdk.py`、
  `env.sh`、`start.sh`、`tiesheai-clearml-cpu-agent.service`。
- 新增 `tests/smoke/cpu_smoke.py`、`run_cpu_smoke.py`、`expected.json`。
- 新增本报告，更新 [STATUS.md](STATUS.md)、[DECISIONS.md](DECISIONS.md)。
- 主机新增 `/etc/systemd/system/tiesheai-clearml-cpu-agent.service`，创建并启动 Agent；
  本地安全配置、缓存及证据位于已忽略目录。服务未启用开机自启。
- 原有 T01-A Compose、镜像锁、nginx、verify.py 的 SHA256 未变；两个 Fork 干净。
  未重新部署基础服务，未改变卷、端口、镜像或服务鉴权，未安装包、训练框架或使用 GPU。
  根仓库仍无提交；未暂存、提交或推送。

本阶段无未解决的验收阻塞。未验证浏览器登录、远程转发端到端、Fileserver 完整访问
控制策略、跨主机环境重建、Agent/主机重启恢复、长期负载、备份恢复、GPU 或 Fork
集成；这些不计入 T01-B 完成范围。仅这条独立 CPU Smoke 链路已通过。

T01-C 未开始。下一阶段需用户明确授权并定义范围；建议先确认下一阶段目标、
任务源码发布方式和依赖隔离要求，再实施对应验收。
