# T03-A 训练准备验收

2026-11-11（Asia/Hong_Kong）。按 [T03-A 任务](T03A_TASK.md) 实施。**数据绑定、资源诊断、CPU tokenizer/chat template 检查通过。独立训练环境受阻，T03-A 未完整通过。真实训练未启动。**

## 固定训练输入

使用 [T02 公开数据交接](T02_PUBLIC_DATA_ACCEPTANCE.md) 的输出 Dataset `65d2ce482a484ff0a7e2ef6f0f4dbe67`，版本 `1.0.0`。机器交接为本机 `infra/evidence/t02-public-data/training-handoff.json`。

| Dataset 成员 | 样本数 | 字节 | SHA-256 |
|---|---:|---:|---|
| `manifest.json` | — | 1376 | `8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f` |
| `train.jsonl` | 18 | 17599 | `3852e6b04b80487e69bf7f286ac6edf6e607791c235828b47f14067047ae028f` |
| `validation.jsonl` | 6 | 5287 | `53ad388ff76c8b9fcec8ede1e3e3ee0948c086ed9ff9f671eb83c4a65d2aa345` |

本地五成员全部重算，交接文件、Manifest、浏览器 ZIP、历史 SDK ZIP 和解包内容相符。训练/验证的规范样本哈希交集为 0。以现有 SDK 2.1.12 只读查询同一 ID，确认版本封存、处理 Task 引用正确，强制回读 data Artifact 并重新核对五成员。新回读 ZIP 12325 B，SHA-256 `1ffd18c945c354902c551a008a864edcffccafbd24ba4c4bebe7e0d9957a17b0`。SDK 缓存单独放在本轮证据目录。

## GPU 阻塞与主机预算

| 项目 | 本轮实测 |
|---|---|
| 主机与 PCI | VMware 来宾，Linux 5.4.0-169-generic x86_64，glibc 2.31。仅枚举 VMware SVGA II `15ad:0405`，PCI 和 sysfs 均无 NVIDIA `10de` 设备 |
| GPU/显存 | `nvidia-smi` 退出 **9**。无法取得 GPU 型号、计算能力、显存容量或占用 |
| 驱动与设备 | 已安装 R470-server 470.199.02，当前内核有对应 DKMS 模块文件，Secure Boot disabled。内核中未加载 NVIDIA 模块，只看到 `/dev/nvidiactl`，没有 GPU 设备节点、NVIDIA PCI 驱动目录或 `/proc/driver/nvidia` |
| 进程环境与 CUDA | 探测进程为 root，两项 GPU 可见性变量均未设置。无 `nvcc`，无 `/usr/local/cuda`。现有 OpenCompass Python 3.10.20 可导入 `torch 2.11.0+cu130`，其编译 runtime 为 CUDA 13.0 |
| CPU/RAM/磁盘 | 12 vCPU（Xeon E7-4850 v3），15 GiB RAM、约 11 GiB available、无 swap。工作区和缓存同一 ext4 文件系统，约 61 GiB 可用；已有 Hugging Face 缓存仅见约 3.9 GiB 的 Gemma GGUF |

2026-11-09 21:01（香港时间）及本轮探测窗口的内核日志均有 `NVRM: No NVIDIA GPU found`。目前可定位到**来宾未获得 NVIDIA 设备**。仅存在的控制节点无法提供 CUDA 设备，驱动初始化后因找不到 GPU 退出。现有 CUDA wheel 的编译信息只说明它包含 CUDA 支持。来宾证据无法区分物理宿主缺卡、GPU 未分配或虚拟化透传配置异常。

后续由虚拟化管理员确认宿主 GPU 库存及来宾的 PCI passthrough/vGPU 分配，或指定已分配 GPU 的独立训练节点。先确认来宾能枚举实际 GPU，再按该卡和虚拟化平台选择兼容驱动，复验 `nvidia-smi` 的型号、计算能力及空闲显存。现有 R470 同时低于 CUDA 12.x 兼容下限，设备可见后仍需为候选环境准备受支持的驱动。cu126 方案以 CUDA 12.6 Update 3 对应的 Linux **560.35.05 或更新的兼容驱动**作为保守基线。 [VMware DirectPath I/O 文档](https://knowledge.broadcom.com/external/article?articleNumber=312208)、[NVIDIA CUDA 12.6 Update 3 驱动表](https://docs.nvidia.com/cuda/archive/12.6.3/cuda-toolkit-release-notes/index.html)、[CUDA 次版本兼容说明](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)

本轮未创建独立训练环境。PyTorch GPU 张量计算、实际 BF16/FP16、Unsloth 导入及 GPU 模型加载均因设备不可用而未执行。

## 基座、模板与条件性训练方案

选定小模型候选 `Qwen/Qwen2.5-0.5B-Instruct`，固定官方 revision **`7ae557604adf67be50417f59c2c2f167def9a775`**。公开免审批，Apache-2.0，分发时按上游 LICENSE 保留许可与通知。官方仓库显示约 4.94 亿参数，BF16 safetensors 988097824 B。仅获取 8 份小文件并以固定 revision 的 Git blob ID 验证，另存 SHA-256。Unsloth 官方目录列出同模型的 16-bit 和 4-bit Instruct 版本。实际加载仍须验证官方固定 revision，保持模型身份与 tokenizer 一致。 [Qwen 固定版本及许可](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775)、[Unsloth 模型目录](https://unsloth.ai/docs/get-started/unsloth-model-catalog)

在现有 OpenCompass Python 3.10.20 上离线验证 `AutoTokenizer`，`trust_remote_code=False`。先使用原有 Transformers 5.8.0，再用既有缓存中的 Transformers 4.57.6 和 Hugging Face Hub 0.36.2 重跑。两次均使用 Tokenizers 0.22.2、Jinja2 3.1.6，24 条结果一致。未向任何现有环境安装包。

| 划分 | 条数 | 格式化后 tokens 最小 / 中位 / 最大 | 超过 512 |
|---|---:|---:|---:|
| train | 18 | 87 / 237.5 / 331 | 0 |
| validation | 6 | 150 / 169.5 / 302 | 0 |

原始 `messages` 由模板添加默认 system 和角色标记。训练和验证均用 `add_generation_prompt=False`，字符串分步 tokenize 时用 `add_special_tokens=False`。核对直接模板 tokenization、分步 tokenization 及解码一致。另对 user-only prompt 验证 `add_generation_prompt=True` 只添加 assistant 起始提示。EOS 为 `<|im_end|>`（151645），PAD 为 `<|endoftext|>`（151643）。逐条以 offset 验证可仅为 assistant 正文和结束 EOS 建标签，屏蔽提示、尾换行和 padding。模板 SHA-256 为 `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f`。若有超长样本，预检报出 split/行号并阻止执行，避免截掉回答或 EOS。另用一条合成超长对话验证长度统计能识别超过上限的样本。 [Transformers chat template 文档](https://huggingface.co/docs/transformers/v4.43.0/en/chat_templating)

| 项目 | 待 GPU 复验的首轮配置 |
|---|---|
| 精度与量化 | 单 GPU，16-bit 冻结基座 + LoRA，无 4-bit/8-bit 量化。支持原生 BF16 且实算通过时用 BF16，否则仅在 FP16 实算通过时用 FP16。使用官方模型名和固定 revision，加载时确认 Unsloth 保留所选模型和模板 |
| LoRA | `r=8`，`alpha=16`，`dropout=0`，`bias=none`。目标 `q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj`。使用 gradient checkpointing |
| SFT | `max_seq_length=512`，动态右侧 padding，`packing=false`。训练和验证 batch 各 1，训练梯度累积 3，单 GPU 有效 batch 3。只用固定 train 18 条，1 epoch 合计 6 次优化更新。seed=42，`adamw_torch`，学习率 `1e-4`，linear，warmup 0，max_grad_norm 1.0 |
| 验证和产物 | 固定 validation 6 条，仅计算同掩码下的 validation loss，记录基座及训练后结果。每个优化步记录 train loss，末尾保存一次 adapter 和 tokenizer，并核对加载与哈希 |
| 预算估算 | 权重约 0.92 GiB。训练峰值初估 3–6 GiB（含激活、logits、优化器及 CUDA 缓冲），以至少 8 GiB 显存且开跑前约 6 GiB 可用作为候选目标。建议预留 20 GiB 本地磁盘供依赖缓存、环境、权重与产物；峰值和耗时均待实际测量 |

公开数据只有 18 个训练样本，本方案用于验证平台的真实训练链路和产物复现。6 条验证结果仅作功能证据。

## 独立环境命令草案

候选组合适用于能运行 cu126 的 Linux x86_64 GPU 节点，优先考虑支持 BF16 的 Ampere 级设备。若给到不同架构，须先核对 PyTorch、Triton、xFormers 与驱动支持。核验了 8 个发行包元数据及 24 条选定直接版本约束，见 `stack-metadata-result.json`。完整依赖解析、安装、运行及复建待设备就绪后验证。 [Unsloth 硬件要求](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)、[安装说明](https://unsloth.ai/docs/get-started/install/pip-install)、[PyTorch cu126 发布矩阵](https://pytorch.org/get-started/previous-versions/)、[xFormers cu126 wheels](https://download.pytorch.org/whl/cu126/xformers/)、[Unsloth 2026.4.8 元数据](https://pypi.org/project/unsloth/2026.4.8/)

下列草案未执行。只在目标 GPU 节点已分配设备、驱动兼容且获准续验 T03-A 时使用。从项目根目录运行。
多卡节点由管理员指定本次分配的设备，通过 `CUDA_VISIBLE_DEVICES` 将其映射为进程的 `cuda:0`。

```bash
set -euo pipefail
nvidia-smi --query-gpu=index,name,driver_version,compute_cap,memory.total,memory.free --format=csv
t03a_venv="$PWD/infra/.local/t03a-cu126-venv"
test ! -e "$t03a_venv"
python3.11 -m venv "$t03a_venv"
t03a_python="$t03a_venv/bin/python"
"$t03a_python" -m pip install --index-url https://download.pytorch.org/whl/cu126 \
  'torch==2.8.0+cu126' 'torchvision==0.23.0+cu126' 'xformers==0.0.32.post2'
"$t03a_python" -m pip install --index-url https://pypi.org/simple \
  'unsloth==2026.4.8' 'unsloth-zoo==2026.4.8' \
  'transformers==4.57.6' 'trl==0.24.0' 'peft==0.18.1' \
  'huggingface-hub==0.36.2' 'tokenizers==0.22.2' \
  'torch==2.8.0+cu126' 'torchvision==0.23.0+cu126' 'xformers==0.0.32.post2' 'triton==3.4.0'
"$t03a_python" -m pip check
"$t03a_python" -m pip freeze --all > infra/evidence/t03a/gpu-env-freeze.txt

"$t03a_python" -B - <<'PY'
import torch

assert torch.cuda.is_available()
print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0),
      torch.cuda.get_device_capability(0), torch.cuda.mem_get_info(0))
dtype = torch.bfloat16 if torch.cuda.is_bf16_supported(including_emulation=False) else torch.float16
x = torch.ones((64, 64), device="cuda:0", dtype=dtype)
y = x @ x
torch.cuda.synchronize()
assert y.is_cuda and y.dtype == dtype and torch.all(y == 64).item()
print("GPU matmul PASS", dtype)
PY

"$t03a_python" -B - <<'PY'
import importlib.metadata
from unsloth import FastLanguageModel

print("Unsloth import PASS", importlib.metadata.version("unsloth"), FastLanguageModel.__name__)
PY
```

## 下一轮真实训练接入

T03-A 续验先关闭设备和环境阻塞，再在隔离环境复跑 tokenizer 检查。真实训练须另获授权。届时先下载并核对完整权重及 adapter 输出目录，确认预定的 Unsloth 加载入口 `FastLanguageModel.from_pretrained` 接受 `revision` 和 `use_exact_model_name=True`，以实测 dtype、`load_in_16bit=True` 和 `load_in_4bit=False` 加载。验证实际权重来源、模型 config、模板、EOS/PAD、labels 和可训练参数，记录首步和峰值资源。

计划中的训练入口及参数草案如下，入口文件待后续任务实现，当前不可提交。

```bash
"$t03a_python" -m integrations.training.train \
  --dataset-id 65d2ce482a484ff0a7e2ef6f0f4dbe67 --dataset-version 1.0.0 \
  --manifest-sha256 8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f \
  --model Qwen/Qwen2.5-0.5B-Instruct --revision 7ae557604adf67be50417f59c2c2f167def9a775 \
  --max-seq-length 512 --batch-size 1 --gradient-accumulation-steps 3 \
  --epochs 1 --learning-rate 1e-4 --lora-r 8 --lora-alpha 16 --seed 42
```

后续入口应核对 train/validation 两个 SHA-256，固定精度、模板、量化、mask 和验证策略，参数/依赖/源码快照作为 ClearML 记录。获准配置 GPU Worker 和专用队列后验证它能复用或重建隔离环境，再安排一条真实作业，回读 adapter/指标/日志并验证产物加载。当前 `rail-cpu` 服务不承担该作业。

## 命令、退出码与证据

证据根为 Git 忽略的 `infra/evidence/t03a/`。完整 argv、香港时间、耗时、退出码和 stdout/stderr 文件见 `commands.jsonl`。下表中脚本路径相对证据根。环境变量、解释器完整路径及分项下载命令以台账为准。

| 实际检查 | 退出码与结果 | 证据 |
|---|---|---|
| `python3 -B check_data.py local`；现有 SDK Python `-B check_data.py sdk` | 0 / 0，固定身份、五成员与划分核验通过 | `data-local.json`、`data-sdk.json` |
| `systemd-detect-virt`、`lspci -nnk`、sysfs/设备/模块采样、`journalctl -k` | 各 0，当前及历史 GPU 缺失证据 | `virtualization.txt`、`pci.txt`、`gpu-devices.txt`、`nvidia-kernel-log.txt` |
| `nvidia-smi --query-gpu=…`、`nvcc --version` | 9，驱动无法与 GPU 通信；127，命令不存在 | `gpu-smi.txt`、`nvcc.txt` |
| `modinfo -F version nvidia`、`dkms status`、`mokutil --sb-state`、`dpkg-query -W …` | 各 0，核对已安装驱动 | `module.txt`、`dkms.txt`、`secure-boot.txt`、`nvidia-packages.txt` |
| `lscpu` / `free -h` / `df` / `du` 组合、`getconf GNU_LIBC_VERSION`、现有 OpenCompass Python 导入 torch | 各 0，主机预算和 wheel 编译版本采样 | `cpu-memory-disk.txt`、`glibc.txt`、`existing-torch.txt` |
| 固定 revision 元数据 `curl`、`python3 -B fetch_model.py` | 元数据 0。首次单文件传输大小触发 curl 63，脚本 1。调整小文件传输上限并保留最终大小及 blob 校验，复验 0 | `qwen-metadata.json`、`fetch-model.txt`、`fetch-model-final.txt`、`model-files.json` |
| 两组离线 Python `-B check_template.py`、`check_stack.py` | 各 0，24 条模板和标签范围通过；直接依赖约束核对通过 | `tokenizer-result.json`、`tokenizer-candidate-result.json`、`stack-metadata-result.json` |
| `python3 -B snapshot.py before/after`、`python3 -B check_delivery.py` | 均 0，3 个仓库、7 容器、2 个服务前后核对与文档检查通过 | `snapshot-before.json`、`snapshot-after.json`、`delivery-result.json` |

实际修改为本报告、[STATUS](STATUS.md)、[HANDOFF](HANDOFF.md)、[ROADMAP](ROADMAP.md)、[DECISIONS](DECISIONS.md) 及本地忽略证据。未下载完整权重、未配置 GPU Agent 或队列、未写入 ClearML 业务对象、未运行训练或部署。驱动/设备分配、GPU 环境和训练启动按各自授权安排。
