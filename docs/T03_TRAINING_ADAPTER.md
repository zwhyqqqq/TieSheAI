# T03 训练适配器与 CPU 预检验收

2026-11-11（Asia/Hong_Kong）。按 [训练适配器任务](T03_ADAPTER_TASK.md) 实施。**适配器源码与 CPU 预检通过。CUDA 训练、GPU Agent 和远端模型产物待实测。** 环境前置条件见 [T03-A 报告](T03A_TRAINING_READINESS.md)。

## 入口和输入绑定

从项目根目录执行 `python -B -m integrations.training.train`。`--preflight` 走 CPU 路径，打印 JSON，可通过 `--report` 另存到新文件。该模式只执行只读下载和本地检查。固定输入如下，CLI 对不匹配的 ID、版本、Manifest 和模型身份直接报错。

| 项目 | 固定值 |
|---|---|
| ClearML Dataset | `65d2ce482a484ff0a7e2ef6f0f4dbe67` v`1.0.0` |
| Manifest SHA-256 | `8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f` |
| train SHA-256 | `3852e6b04b80487e69bf7f286ac6edf6e607791c235828b47f14067047ae028f` |
| validation SHA-256 | `53ad388ff76c8b9fcec8ede1e3e3ee0948c086ed9ff9f671eb83c4a65d2aa345` |
| 基座 | `Qwen/Qwen2.5-0.5B-Instruct` @ `7ae557604adf67be50417f59c2c2f167def9a775` |
| 模板 SHA-256 | `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f` |
| 默认训练配置 | 单卡 16-bit LoRA，无量化。r=8，alpha=16，dropout=0，bias=none。目标 q/k/v/o、gate/up/down 投影。序列上限 512，batch=1，累积 3，1 epoch 预计 6 次优化更新，seed=42，AdamW，LR=1e-4 |

默认读取经认证的 ClearML SDK 配置，按 ID 获取封存 Dataset，检查版本和五个成员，通过 SDK 下载到本地缓存。关闭 Dataset 自动创建、可写副本和当前任务运行属性登记。`--data-dir` 可读取已下载的五个文件，采用相同哈希检查。以固定 Manifest 核对全部成员大小和 SHA-256，复用 [conversation-v1](../schemas/conversation-v1.md) 的过程校验和样本哈希。核对 messages-only 输出、18/6 条数、无重复、来源映射完整、组哈希和跨集来源隔离。

默认从 Hugging Face 固定 revision 只请求 7 个小文件，包括 tokenizer、模型配置和许可证。离线用 `--tokenizer-dir`。两条路径均按内置 SHA-256 验证后在独立临时目录初始化 fast tokenizer，防止同目录额外文件覆盖模板。基座权重的下载入口只存在于通过 CUDA 门禁的训练路径。 [Qwen 官方固定 revision](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775)

在本机已有 tokenizer 环境复现离线预检如下。两条缓存路径来自 [T02 数据交接](T02_PUBLIC_DATA_ACCEPTANCE.md) 与 [T03-A](T03A_TRAINING_READINESS.md)。

```bash
HF_HUB_OFFLINE=1 /root/miniconda3/envs/opencompass/bin/python -B \
  -m integrations.training.train --preflight \
  --data-dir infra/evidence/t02-public-data/downloaded \
  --tokenizer-dir infra/evidence/t03a/qwen-tokenizer
```

## 模板与标签结果

对话可含首条 system，之后严格 user/assistant 交替。按固定原生模板核对每条渲染结果。每轮 assistant 正文和它的 EOS（151645）参与损失，system/user、角色头和模板尾换行的标签均为 `-100`。角色头与正文独立编码，保留答案前导空白并避免该空白与角色头合并成跨边界 token。正文中的字面控制标记用普通 token 表达。训练和验证均使用同一个动态右 padding collator，PAD ID 为 151643，padding 对应 attention mask 0、label `-100`。超长时报告文件和行号并退出，保留完整样本边界。

| 固定划分 | 样本 / 来源组 | 总 tokens | 有效 labels | 最短 / 最长 tokens |
|---|---:|---:|---:|---:|
| train | 18 / 9 | 3914 | 3026 | 87 / 331 |
| validation | 6 / 3 | 1230 | 978 | 150 / 302 |

24 条均无需截断，逐条 input IDs 与原生模板直接 tokenize 一致。真实 SDK 下载、本地缓存和 Hugging Face 小文件下载三条预检的文件哈希、长度与 label 统计一致。CPU 回归使用 Transformers 5.8.0 和 4.57.6 各跑 14 项，覆盖显式/隐式 system、多轮、Unicode、前导空白和字面控制标记、五成员篡改、版本或封存状态不匹配、跨集来源、超长、全屏蔽、EOS/PAD 和 CUDA 缺失。两版 Trainer 的训练与验证 dataloader 都交付与 collator 预期完全相同的 CPU tensors。回归期间没有执行模型 forward、loss 或优化器。ClearML 登记调用以 mock 检查同步参数。

## GPU 路径和产物

普通入口先查 CUDA 和单卡可见性。默认优先原生 BF16，其他可用设备走 FP16。CUDA 缺失退出 `3`，发生在数据访问、Unsloth 导入、权重下载、输出目录和业务对象创建之前。CUDA 可用且预检通过后，按固定 revision 请求唯一 safetensors 并校验大小和 SHA-256，再用离线本地快照加载 Unsloth 基座及 LoRA。检查模板、EOS/PAD、基座类型和仅 LoRA 参数可训练。使用 Transformers Trainer 直接接收已编码 inputs/labels，避免再次套用模板或构造标签。

训练代码在同一固定 validation 上计算禁用 adapter 时的基座 loss 和训练后 loss，向 ClearML 记录逐步 train loss 及两次 validation loss。通过本地 `adapter/` 目录保存 PEFT safetensors、可移植基座名/revision、tokenizer、许可证、`run-manifest.json` 与 `sha256.json`。清单记录数据身份、训练参数、依赖、源码哈希、GPU 峰值、指标和实际步数。两份清单同步上传为 Task Artifact，adapter 目录由 ClearML OutputModel 打包同步上传并记录 Model ID。源码层核对了 Unsloth 2026.4.8、Transformers 4.57.6、PEFT 0.18.1 与 ClearML 2.1.12 的 API，证据 `upstream-api.json`。 [Unsloth 发行版](https://pypi.org/project/unsloth/2026.4.8/)、[Transformers Trainer 源码](https://github.com/huggingface/transformers/blob/v4.57.6/src/transformers/trainer.py)、[PEFT 源码](https://github.com/huggingface/peft/blob/v0.18.1/src/peft/peft_model.py)、[ClearML OutputModel 源码](https://github.com/clearml/clearml/blob/v2.1.12/clearml/model.py)

### 后续 Agent 接入

先经授权续验 T03-A，确认可见设备、驱动、显存、隔离依赖、PyTorch GPU 算术和 Unsloth 导入。真实训练另行授权后，为 GPU Agent 提供可复现的本仓库源码快照、经验证的解释器、ClearML 权限和获准的上传 URI。以下为启动命令草案。从项目根目录运行，变量由 GPU 作业配置提供。

```bash
"${t03_gpu_python:?}" -B -m integrations.training.train \
  --output-dir "${t03_run_dir:?}" \
  --project "${t03_project:?}" --task-name "${t03_task_name:?}" \
  --output-uri "${t03_output_uri:?}"
```

GPU 作业须仅暴露分配的单卡。入口从实际 CLI 读取和校验参数，保存到 Task。Agent 需显式传入同一命令参数和唯一运行目录，保留认证。配置专用 GPU 队列并运行后，核对 Task 状态、实际更新步数、loss、显存峰值、Model 与 Task 的关联，回读模型包并逐文件校验，加载固定基座加 adapter。当前 GPU 算术、模型加载、优化器更新、真实 ClearML 上传与 Model 回读均待验。

## 实际命令和证据

原始命令、解释器、时间、退出码与输出路径见 `infra/evidence/t03-training-adapter/commands.jsonl`。证据目录受 Git 忽略。

| 实测 | 退出码和证据 |
|---|---|
| `python -B -m integrations.training.train --preflight --data-dir … --tokenizer-dir …` | 0，`preflight-local.json` |
| `preflight_readonly.py --preflight --tokenizer-dir …` | 最终 0，`preflight-sdk-final-clean.json`。用已有 Python 3.13 和 Transformers 4.57.6，只读复用 SDK 2.1.12。`readonly-http-final-clean.json` 记录 12 个已允许的 GET，全部 200 |
| `python -B -m integrations.training.train --preflight --data-dir …`（默认 Hub 下载） | 0，`preflight-hub.json` 和隔离 `hf-home/`，下载文件仅为 7 个已固定的小文件 |
| `python -B -m unittest discover -s tests/t03 -v` 两版 Transformers | 各 0、各 14 项通过，`unit-final.txt`、`unit-candidate-final.txt` |
| 真实 CLI 错误路径 | 版本不符退出 2、过长退出 1、CUDA 不可用退出 3，见 `version-gate.txt`、`length-gate.txt`、`cuda-gate.txt` |
| `python3 -B check_source_api.py`、`snapshot.py before/after`、`check_delivery.py` | 均 0，官方实现签名、运行身份、仓库范围、证据一致性及文档核对通过 |

首轮 SDK 预检用 OpenCompass 的 Python 3.10 跨环境导入 SDK 时遇到 cryptography ABI 不符，退出 1，未发 HTTP 请求。换用已有 Python 3.13 后通过。最初只读名单遗漏 `tasks.get_all`，SDK 容错后预检仍退出 0。补全该只读端点后所有请求均通过。

跨 Python 导入时 PLY 重建了 SDK 环境内的 `luqum/parsetab.py` 并生成 `parser.out`。已用原版 wheel、已安装 RECORD 和原 Python 3.11 字节码交叉验证并恢复表文件，保留新生成文件于证据目录。验收脚本禁用 PLY 表与调试文件写入时，首次因调用模块推断变化退出 1，显式传入调用模块后复验通过。恢复及复验退出 0，见 `parser-restored.json`、`parser-protected.txt`。

现有 5.4 内核触发 Accelerate 的版本提示，两套 CPU dataloader 测试完成。CUDA 门禁实测另见 PyTorch 的现有驱动过旧提示，来宾设备诊断沿用 T03-A 证据。

新增 [训练入口](../integrations/training/train.py)、[数据与模板](../integrations/training/inputs.py)、[GPU 训练路径](../integrations/training/gpu.py)、[CPU 回归](../tests/t03/test_training.py) 和本报告。更新 [STATUS](STATUS.md)、[HANDOFF](HANDOFF.md)、[ROADMAP](ROADMAP.md)、[DECISIONS](DECISIONS.md)。本轮没有创建 ClearML 业务对象、提交队列、下载权重或执行真实训练。
