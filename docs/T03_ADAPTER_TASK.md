# T03 训练适配器开发与 CPU 预检

2026-11-11 提供待启动的实施提示词。当前来宾缺少 NVIDIA 设备，T03-A 的 GPU 环境验收受阻。本轮建议先完成训练适配代码和可在 CPU 上验证的数据准备，将实际 GPU 运行列入后续验收。依据见 [训练准备报告](T03A_TRAINING_READINESS.md) 和 [总体规划](ROADMAP.md)。

## 可复制提示词

```text
在 /root/TieSheAI 开发 T03 训练适配器，并完成 CPU 数据预检验收。
先读 docs/STATUS.md、docs/HANDOFF.md、AGENTS.md、docs/DECISIONS.md、docs/ROADMAP.md，
以及 docs/T03A_TRAINING_READINESS.md 和 schemas/conversation-v1.md，核对三仓库状态。

1. 在 integrations/training/ 实现可复用的训练入口，参数绑定 Dataset ID/版本、Manifest SHA-256、
   模型名称/revision和训练配置。支持明确的 --preflight CPU 预检模式。
   当前数据为 65d2ce482a484ff0a7e2ef6f0f4dbe67 v1.0.0，Manifest为
   8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f。
   候选模型为 Qwen/Qwen2.5-0.5B-Instruct，revision为7ae557604adf67be50417f59c2c2f167def9a775。
2. 默认通过现有认证 SDK 只读获取封存数据，核对五文件哈希、18/6划分和来源隔离。
   CPU预检也可使用已校验的本地缓存。模型元数据和tokenizer按固定revision及哈希加载。
   复用现有数据契约和T03-A已验证的逻辑，将必要实现落到正式代码目录，避免运行入口依赖历史证据脚本路径。
3. 支持conversation-v1的可选system、多轮user/assistant，覆盖所有assistant回复正文与EOS的labels，
   将system/user与padding屏蔽为-100。保持模板、EOS/PAD和模型revision一致。
   输出tokens、有效labels、长度及超限诊断，使用512上限，超限时给出split/行号并明确失败。
   保持固定训练/验证划分，使用动态padding。检查collator实际交给trainer的labels。
4. 实现实际Unsloth/LoRA训练路径，按T03-A候选配置接入参数、日志、loss、adapter/tokenizer保存、
   哈希清单及ClearML原生Task/Model登记。查阅拟用版本的官方实现确认API，GPU相关依赖延迟加载。
   CPU预检只生成本地检查报告。普通训练路径在CUDA条件缺失时明确失败，并在业务对象创建及权重下载前返回。
   GPU环境中的模型加载、优化更新、产物加载与Model登记，列为尚待运行验证的验收项。
5. 复用当前CPU可运行的tokenizer环境，验证固定24条数据和可选system/多轮输入。
   针对哈希或版本不匹配、全屏蔽labels、padding、EOS、超长和GPU缺失退出，补必要回归测试。
   检查CPU预检与GPU缺失失败路径均无ClearML业务写入、队列提交和模型权重下载。
   现有CPU Agent、网页服务和训练数据按当前基线使用。
6. 新增 docs/T03_TRAINING_ADAPTER.md，记录实现入口、实际命令/退出码、CPU结果、GPU待验项和后续Agent接入方法。
   证据放 infra/evidence/t03-training-adapter/。更新STATUS/HANDOFF/ROADMAP，HANDOFF≤100行。

本轮授权范围为适配器源码、必要测试、只读数据获取和CPU预检，工作成果保存在本地工作区。
GPU分配、驱动与独立环境续验按资源落实情况另行启动，T03真实训练的通过结论以GPU实测为准。
```
