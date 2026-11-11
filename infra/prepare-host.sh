#!/usr/bin/env bash
set -euo pipefail
infra_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $EUID -ne 0 ]]; then
  echo 'Run this script as root (sudo bash /root/TieSheAI/infra/prepare-host.sh).' >&2
  exit 1
fi
python3 -B - "$infra_dir" <<'PY'
import pathlib, sys
infra = pathlib.Path(sys.argv[1])
source = infra / 'sysctl/99-tiesheai-clearml.conf'
target = pathlib.Path('/etc/sysctl.d/99-tiesheai-clearml.conf')
content = source.read_text()
if target.exists():
    if target.read_text() != content:
        raise SystemExit(f'Refusing to overwrite existing configuration: {target}')
else:
    with target.open('x') as f:
        f.write(content)
for subdir in ['config', 'web']:
    (infra / '.local/clearml' / subdir).mkdir(parents=True, exist_ok=True)
env = infra / '.env'
if not env.exists():
    with env.open('x') as f:
        f.write((infra / 'clearml.env.example').read_text())
    env.chmod(0o600)
print(f'Persistent sysctl configuration: {target}')
PY
current_value="$(sysctl -n vm.max_map_count)"
if (( current_value < 1048576 )); then
  sysctl -w vm.max_map_count=1048576
else
  echo "vm.max_map_count=${current_value} (already sufficient; unchanged)"
fi
