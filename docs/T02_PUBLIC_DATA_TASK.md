# T02 公开数据验证与训练交接

2026-11-11 提供实施提示词，等待用户启动。T02-A 和 T02-B 已完成合成数据限定验收。本轮拟用公开样例验证既有入口，并形成 T03 可以按版本读取的训练输入。依据见 [T02-B 验收报告](T02B_WEB_DATA_ENTRY.md)、[数据契约](../schemas/conversation-v1.md) 和 [总体规划](ROADMAP.md)。

## 可复制提示词

```text
在 /root/TieSheAI 执行 T02 的公开数据验证与训练交接。
先读 docs/STATUS.md、docs/HANDOFF.md，再读 AGENTS.md、docs/DECISIONS.md、docs/ROADMAP.md、
docs/T02B_WEB_DATA_ENTRY.md 和 schemas/conversation-v1.md。核对三仓库工作区和现有 Fork 版本。

1. 选一份适合对话微调的公开数据小样本。核实上游来源和使用条款，固定数据版本、原始样本 ID、
   取样规则和转换方法。将已有问答或对话转为 conversation-v1 JSONL，保留可核对的来源分组，
   先用现有核心校验。样本应小于 1 MiB，并能按来源分成非空训练集和验证集。
   在本地忽略目录保存取样清单、转换命令与文件 SHA-256，形成可复现的来源记录。
2. 用现有账户登录 Fork，从侧栏「数据准备」上传真实文件，「合成测试数据」保持未勾选。
   本提示词授权在适配层当前项目下发起一个新请求及相应输入 Dataset、CPU Task 和输出 Dataset，
   含 SDK 所需的隐藏项目和承载 Task。确认 rail-cpu 空闲后，通过网页提交处理。
   续跑沿用新请求的台账和 ID，创建结果不明时先对账。沿用当前发布和服务配置。
3. 等真实 Agent 完成，在网页选择输出版本并刷新验证恢复，实际下载 ZIP。
   用 SDK 回读对应资产并比较归档字节，核对五成员的 SHA-256、输入来源、处理参数、
   训练和验证记录数，以及精确重复与来源组在两集合之间的隔离。
4. 形成 docs/T02_PUBLIC_DATA_ACCEPTANCE.md，写明来源版本和取样方式、请求/任务/输入输出 Dataset ID、
   输出版本、Manifest SHA-256、train.jsonl 和 validation.jsonl 的路径、条数及哈希。
   记录实际命令、退出码、证据和遗留问题。原始材料放 infra/evidence/t02-public-data/，
   更新 STATUS、HANDOFF、ROADMAP，HANDOFF 控制在 100 行以内。

本轮范围止于公开数据进入网页、CPU 处理和训练输入交接。已有权限与运维限制继续记在交接中，
根据证据报告 T02 数据流程的通过范围。完成后停在 T03 启动前，工作成果保存在本地工作区。
```
