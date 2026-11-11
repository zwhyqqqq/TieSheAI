# 对话 JSONL 输入契约 v1

标识：`tiesheai.conversation.v1`。机器可读的单条结构见 [JSON Schema](conversation-v1.schema.json)，
权威过程校验见 [prepare.py](../integrations/data_preparation/prepare.py)；Schema 只描述单条结构，
轮次顺序、跨行 ID 唯一性、重复 JSON 键和 Unicode 完整性由组件执行。

输入为一个 UTF-8、无 BOM 的 JSONL 文件；每个物理行恰好一个 JSON 对象，可有末尾换行。
支持 LF/CRLF；内部空行、空文件、非法 UTF-8/JSON、重复 JSON 键、未知字段一律失败。
不进行自动格式猜测、字段补齐或非法行跳过。错误报告行号，不输出原始内容。

| 字段 | 规则 |
|---|---|
| `messages` | 必需的数组，至少一组 user/assistant；每个对象恰含 `role` 和 `content` |
| `role` | 只允许 system、user、assistant；可在首条出现一次 system，随后严格 user/assistant 交替，最后必须 assistant |
| `content` | 非空白字符串、可编码为 UTF-8；保留内容原文，不剥离空格、不做 Unicode/大小写/标点归一化 |
| `id` | 可选、非空白字符串；如存在，整个输入文件内唯一；重复样本可使用不同 ID |
| `source_id` | 可选、非空白字符串；相同值表示同一来源文档/来源组，必须进入同一个集合；值精确比较 |

```json
{"id":"synthetic-001","source_id":"synthetic-document-a","messages":[{"role":"user","content":"合成测试问题"},{"role":"assistant","content":"合成测试答案"}]}
```

示例仅用于功能测试，不是铁路专业知识或真实 Demo 数据。缺少答案的原始文档/分块不能作为有效训练样本；
PDF/Word 解析、自动生成问答、tool/function 调用、多模态、权重和模型专用模板均不在 v1 内。
来源分组要求调用者提供可信 `source_id`；组件无法识别未提供来源关系的语义相近样本。

精确去重键为仅含 `messages` 的规范 JSON：UTF-8、键排序、紧凑分隔符、非 ASCII 原文、末尾 LF，
对该字节串取 SHA256。ID/source_id 不参与去重；保留每个重复出现的行号、ID 和来源。
消息内容/顺序完全相同的样本合并；不同空格或不同文本不是精确重复，不做语义去重。

先合并精确重复，再对共同 `source_id` 建立连通组；若重复内容出现在多个来源，合并这些来源组，
包括传递关系，防止重复内容或来源泄漏。缺少来源的样本默认各自成组；相同内容仍会合并。
至少需两个独立组，否则失败；训练与验证必须均非空。

按 `SHA256(canonical_json([seed, sorted_group_sample_hashes]))` 排序，取前
`clamp(floor(group_count * validation_fraction + 0.5), 1, group_count - 1)` 组作为验证集。
`seed` 默认 42，`validation_fraction` 默认 0.25，必须在 0 与 1 之间。
比例按组计算，实际样本比例另报；大来源组不拆开以凑比例。相同输入/参数/代码/环境可逐字节复现；
输入换序不改变 train/validation，但会改变来源行号、输入哈希和 manifest。

输出目录必须不存在；所有数据校验和划分成功后才原子发布目录，失败不会发布部分成功结果。
当前是内存中的 CPU 组件，适用于本阶段小数据；尚未做超大输入/多文件流式处理或性能验收。

| 输出 | 内容 |
|---|---|
| `train.jsonl` / `validation.jsonl` | 同一契约的 messages-only 数据；以样本 SHA256 排序，无跨集重复 |
| `sources.jsonl` | 每个唯一样本的 SHA256、split、组哈希及全部原始行号/ID/source_id；结合 manifest 追到 Dataset |
| `statistics.json` | 输入/合法/非法/唯一/重复数、组数、训练/验证组数与条数、实际比例、合成标志 |
| `manifest.json` | 契约/组件版本、实际脚本 SHA256、Python/平台/ClearML SDK/Agent 版本、输入身份/字节/哈希、参数、其余四文件哈希 |

manifest 不包含自身哈希；其完整字节哈希由 ClearML Artifact 和 Dataset state、上传前日志另行登记，
避免自引用。输入/输出 Dataset 各有明确版本；处理 Task 引用输入 ID/版本，输出 provenance 指向输入和处理 Task。
输入和输出是不同名称的转换资产，不把输入 JSONL 继承进输出训练目录，不把转换伪装成原文件版本增量。

后续训练适配器应引用输出 Dataset 的 ID/版本，读取两份 JSONL、使用所选基座 tokenizer/chat template，
并固定 manifest 哈希；本轮没有安装、调用或验证 Unsloth/OpenCompass，也没有任何训练结论。
