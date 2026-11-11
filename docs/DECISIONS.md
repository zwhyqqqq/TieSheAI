# 技术决策与已确认边界

记录日期：2026-11-09（Asia/Hong_Kong）。本文件记录已有实施和用户明确要求，
不将待验证方案视为已确定选型。当前进度见 [STATUS.md](STATUS.md)，
精简交接见 [HANDOFF.md](HANDOFF.md)。

## D01：先建立官方 ClearML 2.4.0 服务基线

- 已采用 Docker Compose 运行 MongoDB、Redis、Elasticsearch、API、Web、Fileserver
  六个服务，项目名固定为 `tiesheai-clearml`。
- 应用镜像 `clearml/server:2.4.0`；数据库分别为 MongoDB 8.0.15、Redis 8.2.3、
  Elasticsearch 8.19.9。Compose 同时锁定版本与 digest，验收核对运行镜像 ID。
- Web 使用官方发行镜像内置资源，版本 `2.4.0-722`，先形成可复验的基础服务基线。
- 依据：[部署结果](../infra/DEPLOYMENT_RESULT.md)、[部署说明](../infra/README.md)、
  [Compose](../infra/compose.yaml)、[镜像清单](../infra/images.lock.json)。

## D02：Fork 与发行镜像分别记录、分别验收

- 本地 `clearml-web/` 应用版本 2.5.0，声明 Angular 21 依赖、pnpm `^10`；
  `clearml-server/` 声明 Server 2.4.0。它们是待后续集成验证的独立源码工作区。
- 当前基础部署不构建、不挂载两份 Fork 源码。Server 版本号相同也不能证明源码
  与发行镜像逐字一致；六容器健康不能证明本地 Web / Server Fork 兼容。
- 本条建立时仅创建交接文档；T01-B 亦不修改业务源码、不进行 Fork 构建或集成。
- 依据：`clearml-web/package.json`、`clearml-server/apiserver/version.py`、
  [部署结果](../infra/DEPLOYMENT_RESULT.md)及本次用户要求。

## D03：保留当前访问与鉴权基线

- Web / API / Fileserver 仅通过 `127.0.0.1:8080 / 8008 / 8081` 暴露，数据库
  端口不发布。远程访问采用三个端口同时 SSH 转发的既有方案。
- 不绕过 API 鉴权；匿名 `server.info` 返回 401 是预期结果。当前版本通过容器内
  `apiserver.version` 核验；认证业务 API 在 T01-A 时尚未验收。
- 2026-11-09 T01-B 补充：普通用户 API 凭据的 SDK 登录、受保护 `server.info`
  和任务/队列/Worker/事件调用已通过；匿名 server.info 仍为 401。
- 对外直接开放、TLS、正式账号策略未在 T01-A 内实施，远程转发端到端访问也未验证。
- 依据：[部署说明](../infra/README.md)、本机 `infra/evidence/acceptance.txt`。

## D04：持久化和运行配置独立保存

- 使用八个独立项目命名卷，Redis 开启 AOF；外部配置目录只读挂载。保留已有卷和
  用户配置，不删除卷、不执行 volume prune，不覆盖同名不同内容主机配置。
- Web 静态资源来自锁定镜像，不用数据卷遮盖；nginx 模板仅处理进程配置、代理和日志。
- 空实例不导入示例数据；未部署异步删除进程，关闭异步 URL 删除开关。
- `.env`、`.local/` 和 `infra/evidence/` 保持本地忽略；交接文档仅记录必要结论和
  证据路径，不写入密码、API key、token 或敏感原始日志。
- 依据：[Compose](../infra/compose.yaml)、[部署说明](../infra/README.md)、
  [忽略规则](../infra/.gitignore)。

## D05：沿用已验证的启动依赖和主机配置

- 启动顺序为数据库健康 → API 健康 → Fileserver / Web，避免鉴权初始化导致循环等待。
- Elasticsearch 堆基线 1 GiB，主机 `vm.max_map_count=1048576`。
- 镜像拉取使用已有本机 `127.0.0.1:7890` 代理，Docker 通过独立 systemd drop-in
  配置；不改 `/etc/docker/daemon.json`。代理脚本会重启 Docker，已有容器时拒绝执行。
- 本次不变更服务或主机配置；重启恢复和备份恢复仍待后续验收。
- 依据：[部署结果](../infra/DEPLOYMENT_RESULT.md)、[部署说明](../infra/README.md)。

## D06：阶段边界与 GPU 限制

- T00 已完成，T01-A 基础部署、T01-B CPU Agent / Task / Artifact 完整链路已通过。
  2026-11-09 用户另明确授权 T01-C1 Web Fork 构建验证，现已通过；T01-C2 未开始。
- T01-B 限普通 CPU Agent 和 testing 类型 Smoke Task；T01-C1 限构建及静态产物验证，
  不进行独立部署或 Web Fork/API 联调。后续阶段仍须用户明确授权，不自动展开。
- GPU 尚不可用，本次 `nvidia-smi` 无法与 NVIDIA 驱动通信；没有验证容器 GPU 能力，
  不把 GPU 训练计入完成范围。
- 2026-11-11 T03-A 复验定位到 VMware 来宾无 NVIDIA PCI 设备，需先确认虚拟化设备分配。
  GPU 环境门禁与固定训练输入见 D17。
- 本次不执行 `git push`；后续推送须有用户明确授权。
- 依据：本次用户要求、[部署结果](../infra/DEPLOYMENT_RESULT.md)及本次环境检查。

## D07：以仓库文档进行跨对话交接

- 新任务先阅读 `docs/STATUS.md`、`docs/HANDOFF.md`，随后阅读本文件及相关部署证据。
- 2026-11-09 按用户要求建立精简交接机制：每次阶段任务及其他任务结束，同时更新
  `HANDOFF.md` 与 `STATUS.md`，包含阶段/状态、修改文件、实际测试命令/结果/退出码、
  证据路径、遗留问题和后续启动条件；失败或中断也留记录，技术决策变化同步更新本文件。
- `HANDOFF.md` 不超过 100 行，仅保留最新阶段和必要历史摘要；STATUS 保留详细进度
  与任务历史，原始日志保持原位置并以路径引用，不复制大段日志或敏感信息。
- 区分历史验收和本轮复验，不虚构测试结果，不将未验证事项标记完成；如需 Git 更新，
  先检查忽略规则和敏感信息，不自动 push。
- 未通过适用测试不得标记完成；未执行、失败及受阻的检查必须如实记录。
  完成当前任务后停止，不能自动进入下一阶段。
- 依据：用户关于建立精简交接机制的本次明确要求；执行规则见 [AGENTS.md](../AGENTS.md)。

## D08：T01-B 复用宿主机环境，使用单脚本任务快照

- 依据用户本次明确要求，使用已有 `clearml-backend`：Python 3.11.18、SDK 2.1.12、
  Agent 3.0.3。以普通 Agent `--cpu-only` 监听 `rail-cpu`，通过 systemd 运行。
  任务跳过环境创建和依赖安装，前后 `pip freeze` 完全一致；不声称跨主机环境隔离。
- T01-B 验收时根仓库尚无提交，因此以 `Task.set_script()` 将独立 Smoke 源码存入服务端任务的
  `script.diff`，repository 为空；Agent 真正获取并执行。服务端源码 SHA256 与交付
  源码一致。无需 Git 推送、额外本地提交或从不完整远端克隆。
- SDK 凭据经当前简单 Web 注册/登录流程为普通用户创建，只保存在本地 0600 配置；
  模板不含凭据，原始证据沿用忽略目录。未改鉴权或基础服务配置。
- Smoke 数值指标采用 `check_passed=1.0`，整数计算结果保存在日志和固定 JSON。
  依据是中间任务实测大整数的指标曲线查询发生精度舍入；最终精确指标和 JSON 均
  通过回读验证。这不是生产训练指标设计决策。
- systemd Agent 保持运行，未启用开机自启；启动恢复和跨主机环境重建未验收。
  本决策限于本次独立 CPU Smoke，后续任务源码发布、环境隔离须按新任务评估。
- 依据：[T01-B 验收报告](T01B_ACCEPTANCE.md)、[Agent 操作说明](../infra/agent/README.md)
  和本地 `infra/evidence/t01b/` 实测证据；后续阶段不自动执行，T01-C1 授权范围见 D09。

## D09：T01-C1 仅验收构建，Widgets 显式复制共享资源

- 用户授权仅为 Web Fork 主应用与 Widgets 构建验证；现有官方 2.4.0 服务和 CPU Agent
  保持原样，不以编译成功宣称 Web 2.5.0 与 Server 2.4.0 的 API 兼容或部署完成。
- 复用本机 Node 24.16.0、pnpm 10.34.9、Angular core 21.2.25 / CLI 21.2.26，
  不安装依赖、不修改 lock。两套构建顺序执行，限制 Angular worker=2，nice=10。
- Widgets 的原共享 assets 路径实际为普通文本占位文件；初次编译成功但产物不完整。
  最小修复为 angular.json 显式从 `src/app/webapp-common/assets` 递归复制到
  `app/webapp-common/assets`，包含字体并去除无效重复字体声明；重建及资源哈希验证通过。
- 18080 独立部署分析保存在构建报告，尚未实施，不视为运行选型决定；T01-C2 待明确授权。
- 依据：用户本次 T01-C1 要求、[构建报告](T01C1_BUILD.md)、本地 `infra/evidence/t01c1/`。

## D10：本地源码检查点保留三个独立仓库

- 2026-11-09 用户明确授权本地暂存、提交及 Git bundle 源码恢复验证，禁止 push、
  部署和进入 T01-C2。根仓库管理部署/Agent/Smoke/规划/交接，忽略两个 Fork 工作目录；
  不删除嵌套 `.git`，不创建 submodule/subtree 或缺少 `.gitmodules` 的 gitlink。
- Fork 基点、保存提交、origin 和应用版本记录于 `configs/revisions.json`；Web 仅提交
  C1 的 angular.json 修复，干净的 Server 保留原提交。发行镜像版本仍独立记录。
- bundle 只包含各自 master 的完整历史，不导出 Codex 内部快照引用；凭据、原始证据、
  依赖、产物和运行数据保持本地忽略。Fork 的补充规则位于各自 `.git/info/exclude`。
- 根仓库最终 SHA 记录于本地证据及最终回复，不为自引用反复修改提交。未推送的本地
  提交不能从 GitHub 获取；本机 bundle 恢复只证明源码可恢复，不证明数据库备份、
  跨主机部署或环境复现。T01-C2 和后续实施仍须明确授权。
- 依据：本次用户指令；保存与恢复方法见 [VERSION_CHECKPOINT.md](VERSION_CHECKPOINT.md)。

## D11：T01-C2 使用单服务独立 Compose 与只读 Fork release

- 2026-11-10 08:39（Asia/Hong_Kong），用户明确授权仅独立 Web C2；最终静态、浏览器已有用户
  登录/认证只读和前后运行基线通过。C3 完整业务矩阵和 Server Fork 运行验证未授权执行。
- 项目 `tiesheai-web-fork` 仅一个 Web 容器，绑定 `127.0.0.1:18080`；复用已有锁定
  clearml/server:2.4.0 digest 内 Nginx，覆盖入口仅运行非 root Nginx；不修改原 Compose。
- 将 C1 主应用/Widgets 复制为独立固定路径 release v2，只读挂载、只读根文件系统，
  不发布 source map。只移除实际 map 指令，保留库内字符串；v1 加工错误及证据保留。
  原始/加工清单与源码/运行版本分别记录，Fork 源码和 C1 原产物保持不变。
- 主应用 `/`、Widgets `/widgets/`，各自 HTML base/SPA 回退，根配置显式 `/api`、
  `/files`；复用原 external bridge，以 Docker DNS 解析后端服务，不使用容器回环。
  代理优先匹配并保留编码/query/Authorization/Cookie/Set-Cookie，不降低鉴权。
- 浏览器基础验收使用隔离上下文，Cookie 不依赖端口隔离。为遵守用户禁止修改既有数据，
  测试工具阻断页面偏好/统计写入及外部请求；这部分未做无干预兼容验收，留给后续授权。
- 原六容器及 Agent 的进程、配置、依赖、历史 Task/Artifact 不变；没有业务对象写入、
  新任务、训练、GPU、Git 暂存/提交/push。后续实施须新授权。
- 依据：用户本轮 T01-C2 指令、[部署报告](T01C2_DEPLOYMENT.md)、
  [独立站点操作说明](../infra/web-fork/README.md)和忽略证据 `infra/evidence/t01c2/`。

## D12：Artifact 下载仅信任显式 Fileserver 根并同源代理

- 2026-11-10 09:48（Asia/Hong_Kong），独立下载修复与回退恢复通过。Fileserver URL 按解析后的
  HTTP(S) origin/路径边界匹配；部署运行配置明确列历史别名，业务源码不硬编码本机地址，
  不按任意 8081 或宽松前缀扩展信任。未知外部/S3 保留既有处理。
- 可信文件来源在签名前统一为同源 /files，保留编码/query、幂等；fetch 先验证 HTTP
  状态，401/404 等失败不保存为成功。保留网络错误的导航回退并支持相对地址。
- 不以放开全局 CORS 或关闭鉴权解决；原六服务/Agent/业务数据保持，仅 Fork 新固定
  release 更新、回退 C2 v2 再恢复，原产物/release 不覆盖。
- 未提交源码按 HEAD 基点、完整补丁和源码清单 SHA256 记录；旧 HEAD 不是完整修复版本。
  完整 C3、C3-B/T02 仍未通过/未开始，后续测试或实施须用户明确安排。
- 依据：本轮用户授权、[修复报告](T01C_ARTIFACT_DOWNLOAD_FIX.md)、实际浏览器/回退与
  边界测试证据 `infra/evidence/artifact-download-fix/`；不将未验证共享业务流程写成通过。


## D13：C3-B 首轮仅允许独立 Dataset / Model 夹具

- 2026-11-10 16:59（Asia/Hong_Kong），按用户本轮明确授权，在唯一新项目树建立同名 Dataset 两版本、
  SDK 必要隐藏项目/两个 data_processing Task/状态日志配置和 Artifact、一个 testing Draft Task 和一个 OutputModel。
- 两 Dataset 显式 use_current_task=False，允许本地 SDK started/completed 封存；这不是 Agent 执行。
  Model Task 保持 created，明确 Fileserver 上传、等待完成并验证远端字节；Model 是测试 JSON，非训练权重。
- 仍禁止入队/出队、Queue/Pipeline 创建、Agent 作业、训练、模型加载/推理、旧业务/偏好/全局统计设置修改，
  不改源码/部署/鉴权、不重启、不清理、不暂存/提交/push；新对象留台账，不自动删除或重复创建。
- 页面读保护保留，只按源码审阅增加限两 Dataset ID 的 events.debug_images；初轮未知调用先阻断，原证据保留。
  页面真实列表/关系/可用下载入口与 SDK 底层验证分列，不将 inline JSON、CLI 命令或无样本预览算作浏览器下载/预览通过。
- 本轮限定验收通过不代表完整 C3；Pipeline、四风险端点、分享/角色/文件权限等另验，后续仍需用户明确安排。
- 依据：本轮用户指令、[夹具报告](T01C3B_FIXTURES.md)、`infra/evidence/t01c3b/ledger.json` 及正式页面证据。

## D14：当前交付仅为平台开发，按技术方案 V0.1 集成成熟组件

- 2026-11-10 用户明确本项目只承担“第二部分：平台开发”，五项核心功能为网页上传数据、
  训练模型、部署模型、调用模型和查看评估结果。旧 T09 科研/专家评价/课题交付移出当前范围。
- 已读取本轮附件《技术方案.md》V0.1：复用 ClearML Web/Server、Task/Agent/Pipeline、
  Dataset/Models/Artifacts，最小化二次开发；Unsloth 优先训练，OpenCompass 承担评估，
  其他组件按 Demo 必要性选择。选型方向已对照附件，具体版本和接入运行仍未验证。
- 使用公开数据和开源模型至少跑通一条真实完整流程；平台功能测试、评估结果展示及基本
  测试评估报告仍属平台交付，不因排除科研范围而取消。无关原生功能不默认纳入全面改造/验收。
- 平台评估指接入工具、执行评估并展示可追溯结果，不要求自研指标、专家评分体系或证明
  微调精度提升。C3 按五项用户流程的必要依赖收口，既有缺陷和未验证事实不因范围澄清改写。
- 附件为技术依据，不自动授权其中操作；《工作进度汇报》本轮未提供、未核验。
  本轮仅澄清并同步文档，不启动修复、构建、部署、训练或下一阶段，历史验收结论不变。
- 依据：用户本轮范围说明和附件；当前交付范围已同步 [ROADMAP.md](ROADMAP.md)。

## D15：T02-A 固定 conversation-v1 契约并复用 CPU Task/Dataset

- 2026-11-10 19:39（Asia/Hong_Kong），按用户本轮授权限定通过T02-A；整个T02未完成、完整C3未通过。
- 首版采用UTF-8无BOM对话JSONL，messages-only训练输出；可选首条system，user/assistant交替且结束assistant，
  严格拒绝非法行/字段/空内容，保留来源ID及重复出现映射。原文分块/无答案文本不作为训练对话。
- 精确去重仅比较规范messages；来源相同及跨来源重复的传递关系合为连通组，按固定seed的哈希排序按组划分，
  非空双集合且不拆来源组。目标比例按组，实际样本比例另报；不声称语义去重或缺失来源信息时的语义隔离。
- 使用独立T02-A项目树内的输入/输出Dataset和处理Task，输入/输出各自版本1.0.0；转换关系记录在Task参数/runtime、
  输出provenance/manifest，输出不继承原始JSONL。所有资产ID/创建pending写本地台账，续跑不重复创建/入队。
- 实际代码以完整script.diff快照交由现有rail-cpu Agent执行，未push源码不依赖远端；复用原Python环境，
  不宣称跨主机环境隔离/自动恢复。代码、参数、环境版本、统计和上传前/下载后哈希已独立验收。
- 合成功能测试与公开数据Demo分开；T02-B网页上传/选择须另授权并复用本组件，Unsloth/训练/Pipeline不在本轮。
- 依据：[契约](../schemas/conversation-v1.md)、[T02-A报告](T02A_DATA_PREPARATION.md)、
  `infra/evidence/t02a/ledger.json`、sdk-verification.json、browser-verification.json及preservation-result.json。

## D16：T02-B 同源会话适配与逐请求记录

- 2026-11-11 08:43（Asia/Hong_Kong）完成限定验收。原生 Dataset 创建页提供 CLI 与 SDK 示例，网页登记、上传、封存由 Python SDK 适配。
- 18080 的固定路径转发到私有 Unix socket。适配层用当前 ClearML 会话验明身份，以同一身份启动独立 SDK 调用。输出选择和归档也通过该身份校验权限。
- 请求 UUID 与所有者和文件指纹绑定，创建、入队之前保存待核对标记。同请求重试返回已有对象，未知结果留台账核对。
- Worker 快照复用 T02-A 数据准备核心，通过 Task 参数回传输出 Dataset。输入和输出均按 ID、版本和哈希追溯。
- 独立固定 release 和私有适配包记录源码与文件清单。回退和恢复均通过。跨用户 Worker、完整 ACL 和主机启动恢复待验。
- 证据见 [T02-B 报告](T02B_WEB_DATA_ENTRY.md)。

## D17：T03-A 固定公开数据版本和模型模板，独立训练环境受 GPU 门禁约束

- 训练输入绑定封存 Dataset `65d2ce482a484ff0a7e2ef6f0f4dbe67` v1.0.0 和 Manifest SHA-256。
  本地与 ClearML SDK 强制回读五成员一致。训练 18、验证 6，按固定划分分别读取。
- 模板接入候选固定为 Apache-2.0 的 `Qwen/Qwen2.5-0.5B-Instruct` 官方 revision
  `7ae557604adf67be50417f59c2c2f167def9a775`，24 条原生模板与标签范围已通过 CPU 核验，
  512 tokens 可保留全部样本。16-bit LoRA、依赖组合及资源预算仍是待 GPU 验证的方案。
- 当前来宾没有 NVIDIA PCI 设备。获得设备和匹配驱动后才能安装并实测独立训练环境。
  GPU Agent、完整权重和真实训练按后续授权执行。
- 依据：[训练准备验收](T03A_TRAINING_READINESS.md) 与本地证据 `infra/evidence/t03a/`。

## D18：训练适配器共用 CPU 预检和训练标签

- 入口绑定 D17 的封存 Dataset、Manifest 和 Qwen 官方 revision。默认只读 SDK 获取数据，支持同哈希的本地缓存。预检仅获取 7 个固定的 tokenizer、配置与许可文件。
- 每轮 assistant 正文和 EOS 参与损失，提示与 padding 标签为 `-100`。使用动态右 padding，超出长度上限报出文件与行号。Trainer 的 CPU dataloader 已核对输入张量和标签。
- GPU 路径使用 Unsloth 加载无量化基座、配置 LoRA，Trainer 直接使用已编码的标签。CUDA 门禁先于对象和权重。日志、adapter 包和 ClearML Model 登记已有源码，运行结果以后续 GPU 实测为准。
- 依据：[训练适配器验收](T03_TRAINING_ADAPTER.md) 和本机 `infra/evidence/t03-training-adapter/`。
