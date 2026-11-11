#!/usr/bin/env bash
# Optional bootstrap for hosts whose Docker daemon cannot reach Docker Hub.
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  echo 'Run as root.' >&2
  exit 1
fi
if [[ $# -ne 1 ]]; then
  echo 'Usage: bash configure-docker-proxy.sh http://127.0.0.1:7890' >&2
  exit 1
fi
if [[ -n "$(docker ps -aq)" ]]; then
  echo 'Refusing to restart Docker while containers exist; configure proxy during a maintenance window.' >&2
  exit 1
fi
python3 -B - "$1" <<'PY'
import pathlib, sys, urllib.parse
proxy = sys.argv[1]
url = urllib.parse.urlsplit(proxy)
if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
    raise SystemExit('Expected an HTTP(S) proxy URL without credentials')
if any(c in proxy for c in ('\n', '\r', '"', '%', '\\')):
    raise SystemExit('Unsupported characters in proxy URL')
target = pathlib.Path('/etc/systemd/system/docker.service.d/90-tiesheai-proxy.conf')
content = ('[Service]\n'
           f'Environment="HTTP_PROXY={proxy}"\n'
           f'Environment="HTTPS_PROXY={proxy}"\n'
           'Environment="NO_PROXY=localhost,127.0.0.1,::1"\n')
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    if target.read_text() != content:
        raise SystemExit(f'Refusing to overwrite existing configuration: {target}')
else:
    with target.open('x') as f:
        f.write(content)
print(f'Docker proxy drop-in: {target}')
PY
systemctl daemon-reload
systemctl restart docker
systemctl is-active docker
