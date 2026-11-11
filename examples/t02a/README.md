# T02-A 合成功能夹具

`conversations.jsonl` 只有合成的测试问题/答案，不是专业知识、公开数据或真实模型训练样本。
14 行包含 12 个唯一对话、2 个重复出现；相同来源成组，其中一个重复跨来源连接两个来源组。
去重后有 5 个独立组。seed=42、validation_fraction=0.25 时：train=10、validation=2。
输入/输出 SHA256、实际 Agent 执行及页面下载见 [验收报告](../../docs/T02A_DATA_PREPARATION.md)。
