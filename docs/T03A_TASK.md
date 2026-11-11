# T03-A 训练资源与环境准备

2026-11-11 提供下一轮实施提示词，等待用户启动。既有 GPU 检查曾失败，首轮先查明当前资源，再按实际硬件验证独立训练环境。训练数据已固定，交接见 [公开数据验收](T02_PUBLIC_DATA_ACCEPTANCE.md) 和 [总体规划](ROADMAP.md)。

## 可复制提示词

```text
在 /root/TieSheAI 实施 T03-A，完成训练资源核查、独立训练环境验证及模型接入方案。

先读 docs/STATUS.md、docs/HANDOFF.md、AGENTS.md、docs/DECISIONS.md、docs/ROADMAP.md，
以及 docs/T02_PUBLIC_DATA_ACCEPTANCE.md。检查三仓库状态，沿用项目现有协作和运维边界。

1. 读取 infra/evidence/t02-public-data/training-handoff.json，按 Dataset ID/版本和哈希核对训练输入。
   输出 Dataset 为 65d2ce482a484ff0a7e2ef6f0f4dbe67，版本1.0.0，
   Manifest SHA-256 为 8c94b1ec947e998b6056c4e83b5f86bec0f0203cdab1e5c42931dc332d6c689f。
   核对 train.jsonl 18条、validation.jsonl 6条和两文件哈希，后续方案引用这份固定划分。
2. 只读检查当前 GPU 型号、显存/占用、驱动、设备可见性、CUDA/PyTorch环境、
   CPU/RAM、可用磁盘和已有模型缓存。记录实际命令、退出码和时间，复核历史 nvidia-smi 失败现象。
   遇到异常继续做可行的只读定位，区分硬件未暴露、驱动、运行环境或权限问题，给出具体证据和最小处理步骤。
3. 查阅 Unsloth 和相关框架的官方兼容说明，按实际硬件选定可执行的安装组合。
   GPU可用时，本提示词授权在新目录创建独立 Conda/venv 环境并安装所需依赖，记录版本和安装命令。
   验证 PyTorch 的真实 GPU 张量运算、设备/计算精度以及 Unsloth 导入，记录实际结果与依赖清单。
   主机驱动变更、重启、Agent/队列配置调整留给独立任务，当前 CPU/网页服务环境继续按现有职责运行。
4. 从官方模型仓库选择一个适合资源预算的小型开源指令模型，核对使用条件和 Unsloth 支持，固定 revision。
   可下载小体积配置/tokenizer，检查 messages 到 chat template 的映射、token长度和截断策略。
   记录后续训练使用的 dtype、量化/LoRA、序列长度、batch和梯度累积、步数及预计显存/磁盘预算，
   明确哪些已实测、哪些仍为估算。用验证集评估，训练输入仅取固定的训练划分。
   硬件条件不足时，交付阻塞诊断和有条件的模型候选，注明尚待验证的兼容关系。
5. 新增 docs/T03A_TRAINING_READINESS.md，给出资源结论、环境验证结果、模型/版本方案、
   数据绑定、启动命令草案和下一轮真实 Agent 训练所需步骤。证据放 infra/evidence/t03a/。
   更新 STATUS、HANDOFF、ROADMAP，确认选型后同步 DECISIONS，HANDOFF控制在100行以内。

本轮范围止于资源、独立环境和模型接入准备。完整模型权重下载、GPU Agent配置及真实训练交给后续明确任务。
报告分别写清已通过的检查、受阻原因和实际待办，任务结束停在真实训练启动前，成果保存在本地工作区。
```
