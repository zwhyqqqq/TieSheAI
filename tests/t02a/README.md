# T02-A 复验入口

从 `/root/TieSheAI` 执行。命令由 `run.py` 记录实际参数、退出码和输出，原始证据在忽略的
`infra/evidence/t02a/`。不要删除台账或重置失败 Task，也不要并发调用控制器。

```bash
python3 -B tests/t02a/run.py unit-tests python3 -B -m unittest discover -s tests/t02a -p 'test_*.py' -v
source infra/agent/env.sh
# 已有 ledger 时只复核其中的现有 Task，不创建/入队新任务
python -B tests/t02a/run.py verify-existing python -B integrations/data_preparation/clearml_run.py verify --timeout 10
# 只读浏览器，会阻断偏好/统计写入和第三方；需要 C2 已有的 Playwright/Chromium 工具
python3 -B tests/t02a/run.py browser-repeat node tests/t02a/browser.cjs fork-repeat
python3 -B tests/t02a/run.py downloads-repeat python3 -B tests/t02a/check.py browser --label fork-repeat
```

每次为证据命令和浏览器使用新的标签，避免覆盖原始失败/成功证据。`check.py preservation` 要求本轮
before/after 快照和已登记的新对象，不能把首次实施后的状态当作新任务的原基线。
`check.py delivery` 核对文档/引用、忽略规则、敏感模式、HANDOFF 行数、三仓库 diff 和前述验收结论。
详细实际命令/退出码和限制见 [验收报告](../../docs/T02A_DATA_PREPARATION.md)。

首次实施已授权且已执行的 `clearml_run.py prepare` 创建/恢复输入 Dataset 和处理 Task，
`submit` 在空队列/空闲 Agent 门禁后只入队 ledger 内 created Task。
当前 completed 后再次 prepare/submit 均不重复创建/入队，已实测；本目录不是自动循环调度器。
ambiguous pending 只停止并要求结合 `created-ids.jsonl` 和服务端资产核对，不自动重置、重建或清理。
真实 Worker 创建输出 Dataset 前后写台账；中断/网络丢失的故障注入尚未验收。

`browser-lib.cjs` 从历史 C3-B 辅助库复用并独立保存在本目录，使用原只读端点合同；
`events.debug_images` 仅准本轮两个 Dataset ID，不改历史脚本/合同。现有身份通过原登录页登录，
不保存 Cookie/token。页面按钮生成的 download 文件独立解包，逐字节对照 SDK 下载文件与 manifest。
