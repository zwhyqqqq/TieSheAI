# TieSheAI 本地 Git 版本检查点

记录日期：2026-11-09（Asia/Hong_Kong）。授权范围为本地版本保存和源码恢复验证。
T00、T01-A、T01-B、T01-C1 保持已完成；T01-C2 及后续阶段未开始。
最新执行结果见 [STATUS.md](STATUS.md)、[HANDOFF.md](HANDOFF.md)。

## 仓库关系与保存范围

| 仓库 | origin | 保存内容与版本 |
|---|---|---|
| 根仓库 | `https://github.com/zwhyqqqq/TieSheAI.git` | 已验收部署、CPU Agent、Smoke 源码/fixture、规划、协作与交接文档，以及本次版本清单 |
| Web Fork | `https://github.com/T1-Otaku/clearml-web.git` | Web 2.5.0；仅提交已验收的 `angular.json` Widgets 共享资源复制修复 |
| Server Fork | `https://github.com/T1-Otaku/clearml-server` | Server 2.4.0；原提交保持不变，工作区干净，不创建空提交 |

两个 Fork 各自保留 `.git`，根仓库通过 [.gitignore](../.gitignore) 排除其工作目录；
没有 submodule/subtree、`.gitmodules` 或 gitlink。源码基点、保存提交、origin 和版本
见 [revisions.json](../configs/revisions.json)。Web 的保存提交以 C1 基点为直接父提交，
其 `angular.json` 与 C1 验收后的文件哈希一致；本轮没有重建或改变构建产物。

根仓库从无 HEAD 提交的状态开始，以明确的 31 文件清单暂存；逐文件审查并扫描凭据，
不使用 `git add .`。实际清单及哈希保存在本地证据的 `root-files.json`、`audit-*.json`。
已有部署/Agent/Smoke 源码和验收报告保留原文；旧报告中的“根仓库无提交”等描述是
对应任务验收时的历史状态，当前版本以本检查点和最新 STATUS/HANDOFF 为准。
提交身份仅对本次命令使用 `Codex <codex@localhost>`，不修改用户的全局 Git 配置。

根仓库最终提交 SHA 只写入本地 `infra/evidence/version-checkpoint/result.json`
及最终回复，不写回同一提交；验收完成后的文档提交作为普通后续提交，不 amend。
**未推送的本地提交不能从 GitHub 获取。** 本轮没有 push 或查询远端最新状态；
origin/master 仅代表本机已保存的远端跟踪引用，不能据此保证远端当前仍有相同内容。

## 排除项与本地证据

- 根仓库忽略 `.env`、`.local/`、`infra/evidence/`、凭据/私钥、依赖、构建产物、缓存、
  权重、运行数据、数据库文件和大体积归档；示例配置只含占位符。
- Fork 原有 `.gitignore` 不变；在各自 `.git/info/exclude` 追加本地安全规则，
  因而 Web 提交仍只有 `angular.json`，Server 无源码修改。这些 Git 元数据不进 bundle。
- 三个 bundle 保存在已忽略的 `infra/evidence/version-checkpoint/bundles/`，
  只导出 `refs/heads/master` 的完整可达历史，不使用 `--all`；根仓库的 Codex 内部
  快照引用不属于源码交付范围，不导出这些引用。
- 同目录上级保存 `before-state.json`、`web-commit.json`、`root-files.json`、
  `audit-*.json`、`bundle-*-commands.json`、`restore-*.json` 和最终 `result.json`。
  bundle SHA256、恢复目录、命令、退出码和目标提交均以本地证据为准。

## 源码恢复方法（不启动服务）

以下使用本机 bundle；新建临时目录，避免覆盖既有工作区。三个 bundle 都是完整的
分支历史，没有前置提交依赖。保留根仓库恢复后的两个 Fork 目录布局，但每个仍是
独立克隆。命令不会访问 GitHub，也不会安装依赖或启动任何服务。

```bash
bundle_dir=/root/TieSheAI/infra/evidence/version-checkpoint/bundles
restore_dir=$(mktemp -d /tmp/tiesheai-source-restore.XXXXXX)
git init --bare "$restore_dir/verify.git"
git -C "$restore_dir/verify.git" bundle verify "$bundle_dir/TieSheAI.bundle"
git -C "$restore_dir/verify.git" bundle verify "$bundle_dir/clearml-web.bundle"
git -C "$restore_dir/verify.git" bundle verify "$bundle_dir/clearml-server.bundle"
git clone --branch master "$bundle_dir/TieSheAI.bundle" "$restore_dir/TieSheAI"
git clone --branch master "$bundle_dir/clearml-web.bundle" "$restore_dir/TieSheAI/clearml-web"
git clone --branch master "$bundle_dir/clearml-server.bundle" "$restore_dir/TieSheAI/clearml-server"
```

恢复后分别执行 `git rev-parse HEAD`，与本地 `result.json` 的三个提交及根仓库内
`configs/revisions.json` 的 Fork 提交核对；比较根仓库全部已提交文件、Web 的
`angular.json`/`package.json`/lock 和 Server 的版本文件哈希。自动验证还检查完整
Git tree、清洁工作区、Web 修复的唯一文件与直接父提交，以及无 gitlink。

bundle 不保存远端配置和 `.git/info/exclude`。如要将恢复目录用于后续开发，先从
`configs/revisions.json` 核对 origin，再恢复本地规则；本轮验证不更改 origin：

```bash
cat "$restore_dir/TieSheAI/.gitignore" >> "$restore_dir/TieSheAI/clearml-web/.git/info/exclude"
cat "$restore_dir/TieSheAI/.gitignore" >> "$restore_dir/TieSheAI/clearml-server/.git/info/exclude"
```

仅重新克隆 GitHub 无法找回尚未推送的根仓库和 Web 新提交。应另行妥善保存三个
bundle 和本地 `result.json`；当前 bundle 与源码同机，不构成异机灾备。
本轮源码恢复验证不等于数据库/卷备份恢复、跨主机部署或运行环境复现；不包含
`.env`、SDK 凭据、主机配置、数据库、Artifact 文件、依赖或 C1 构建产物。
历史服务/Agent/构建验收仍按原报告解释，本轮不重跑这些测试、不重启服务、不进入 C2。
