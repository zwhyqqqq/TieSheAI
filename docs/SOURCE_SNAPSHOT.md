# 项目源码快照与恢复

2026-11-11 保存当前平台源码、测试、部署模板与交接文档。根仓库使用 `codex/tiesheai-t03` 分支。
版本和校验值见 [源码清单](../configs/source-snapshot.json)，Web 改动见 [完整补丁](../patches/clearml-web/source-save-20261111.patch)。

## 保存范围

- 根仓库包含数据准备、网页适配服务、训练适配器、测试、部署模板与文档。
- Web 独立仓库本地提交为 `15afce31f2e035665ced9e61950d46423086b30e`，文件树为 `180bb9f47ea451587f17afa5bb4c2e5d9982fb9c`。
  GitHub 账户对 Web 上游具有读取权限，完整改动以根仓库内的补丁保存，基点为公开提交 `5c4943bfecb3971e50b379b0af1db6b4c63954cf`。
  补丁包含 Widgets 构建配置、Artifact 下载修复、网页数据准备入口及相应测试，共 13 个文件。
- Server 独立仓库固定为公开提交 `2ebdc43951b9432cc7fa528bbb3a7100fc6fe805`，工作区干净。
- 运行数据、凭据、本机配置和原始验收证据按忽略规则保存在原主机，需要各自备份与授权配置。

## 从 GitHub 恢复源码

在新目录执行。Web 补丁采用零行上下文，应用时使用 `--unidiff-zero`，并先核对固定基点和补丁 SHA-256。

```bash
git clone --branch codex/tiesheai-t03 --single-branch https://github.com/zwhyqqqq/TieSheAI.git
cd TieSheAI
snapshot_root="$PWD"
python3 - <<'PY'
import hashlib
import json
from pathlib import Path

manifest = json.loads(Path('configs/source-snapshot.json').read_text())
patch = Path(manifest['web']['patch'])
assert hashlib.sha256(patch.read_bytes()).hexdigest() == manifest['web']['patch_sha256']
print('Patch SHA-256 verified')
PY

git clone --no-checkout https://github.com/T1-Otaku/clearml-web.git clearml-web
git -C clearml-web checkout --detach 5c4943bfecb3971e50b379b0af1db6b4c63954cf
git -C clearml-web apply --unidiff-zero --check --index "$snapshot_root/patches/clearml-web/source-save-20261111.patch"
git -C clearml-web apply --unidiff-zero --index "$snapshot_root/patches/clearml-web/source-save-20261111.patch"
git -C clearml-web write-tree

git clone --no-checkout https://github.com/T1-Otaku/clearml-server.git clearml-server
git -C clearml-server checkout --detach 2ebdc43951b9432cc7fa528bbb3a7100fc6fe805
```

Web 的 `write-tree` 结果应为 `180bb9f47ea451587f17afa5bb4c2e5d9982fb9c`。恢复后 Web 索引记录补丁内容，可自行创建本地分支和提交。
保存清单的根仓库提交由 `git log -1 -- configs/source-snapshot.json` 查询，源码历史与本地提交保留独立记录。

## 本轮核验

凭据和忽略规则检查、36 项下载回归及独立临时克隆恢复通过。恢复后 2486 个文件的完整 Git tree 与本地 Web 提交一致。
命令、退出码和最终发布 SHA 保存在原主机 `infra/evidence/save-project-20261111/`。
技术阶段继续按 [STATUS](STATUS.md) 和 [HANDOFF](HANDOFF.md) 记录，GPU 环境和真实训练等待后续实施。
