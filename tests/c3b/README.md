# C3-B 首轮受控夹具与验收

范围和结果见 [夹具报告](../../docs/T01C3B_FIXTURES.md)。复用现有 SDK、凭据、Playwright 和 Chromium；不安装依赖。
所有脚本须从 `/root/TieSheAI` 执行，证据固定在已忽略的 `infra/evidence/t01c3b/`。

```bash
source infra/agent/env.sh
python3 -B tests/c3b/run.py sdk-recheck python -B tests/c3b/fixtures.py verify
python3 -B tests/c3b/run.py assets-recheck python -B tests/c3b/fixtures.py assets
python3 -B tests/c3b/run.py history-recheck python -B tests/c3b/fixtures.py history
python3 -B tests/c3b/run.py inventory-recheck python -B tests/c3b/fixtures.py compare
node tests/c3b/browser.cjs 18080 recheck-fork
node tests/c3b/browser.cjs 8080 recheck-official
python3 -B tests/c3b/check.py browser --fork-label accept-18080-recheck-fork --official-label accept-8080-recheck-official
```

浏览器每次新建独立 context，使用既有用户真实登录，从 Dataset/Model 列表进入详情。
实际下载由应用原按钮触发；不改 href、不伪造响应，受控阻断调用 route.abort。
`readonly-contracts.json` 保留明确审阅来源；仅新增 `events.debug_images` 读取契约，
同时限制 metrics.task 属于台账的两个 Dataset ID。偏好、统计与第三方仍阻断，未知端点默认拒绝。
错误原文、结构化对象、页错误、逐项匹配、HTTP/业务码、截图、下载分别保存。
`check.py browser` 验证下载 ZIP 内容、父版本材料化、Model 字节/哈希及真实双向链接，
同时输出未分类控制台日志；通过采证不代表完整 C3。

Model GENERAL 的文件按钮只打开 inline JSON；真正下载入口为创建 Task 的
ARTIFACTS → OUTPUT MODELS → MODEL NAME 旁下载按钮。
Dataset CONTENT 的下载图标只显示 CLI 命令；真正浏览器下载入口为
Task information → ARTIFACTS → OTHER → data → FILE PATH 旁按钮。
v2 ZIP 是新增文件的增量包，继承文件位于 v1 ZIP；页面文件表列出合并后的两个文件。

`prepare` 和 `create` 是本轮首次创建的实际命令，**不是只读复验步骤**：

```bash
# 本轮已经执行；原台账存在时 prepare 会拒绝，不得删除台账后再造对象。
python -B tests/c3b/fixtures.py prepare
python -B tests/c3b/fixtures.py create
```

prepare 在服务器写入前保存唯一命名空间和完整历史库存。create 使用
`use_current_task=False`、显式 Fileserver、同步 Model 上传和 wait_for_uploads；
保留两 Dataset completed、Model Task created。无入队、Agent 执行或训练调用。
台账按已知 ID 续跑，pending 创建不明时拒绝自动重试；创建 HTTP 返回 ID 立即另记
created-ids.jsonl。Dataset SDK 隐藏项目的自动祖先 ID 由全库存增量补记。
失败时保留对象、ID 和证据；没有自动删除或清理逻辑。

本轮原 before 基线不得覆盖。snapshot.py before 对已有基线拒绝覆盖；after 仅采集当前状态。
最终保护检查为 `python3 -B tests/c3b/check.py preservation`，文档检查为
`python3 -B tests/c3b/check.py delivery`。它们依赖本轮已有基线，不声称异机环境可直接重建。
所有正式命令和退出码见 commands.jsonl；历史失败及 r3/r4/r5/r6 证据保留，最终选择由
selected-browser-labels.json 明确指定。
