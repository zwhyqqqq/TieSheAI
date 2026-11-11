#!/usr/bin/env python3
"""Read-only live acceptance checks; no SDK, Agent, or task creation."""
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import urllib.parse
import urllib.error


def main():
    infra = Path(__file__).resolve().parent
    command = ['bash', str(infra / 'compose.sh')]
    config = json.loads(subprocess.check_output(command + ['config', '--format', 'json'], text=True))
    expected = {'mongo', 'redis', 'elasticsearch', 'fileserver', 'apiserver', 'webserver'}
    ids = subprocess.check_output(command + ['ps', '-aq'], text=True).split()
    if not ids:
        raise RuntimeError('No project containers exist')
    containers = json.loads(subprocess.check_output(['docker', 'inspect', *ids], text=True))
    image_lock = json.loads((infra / 'images.lock.json').read_text())
    required_mounts = {
        'mongo': {'/data/db', '/data/configdb'},
        'redis': {'/data'},
        'elasticsearch': {'/usr/share/elasticsearch/data', '/usr/share/elasticsearch/logs'},
        'apiserver': {'/mnt/fileserver', '/opt/clearml/config', '/var/log/clearml'},
        'fileserver': {'/mnt/fileserver', '/opt/clearml/config', '/var/log/clearml'},
        'webserver': {'/mnt/external_files/configs', '/opt/clearml/config', '/var/log/nginx'},
    }
    actual = {c['Config']['Labels']['com.docker.compose.service'] for c in containers}
    if actual != expected:
        raise RuntimeError(f'Service mismatch: expected {expected}, got {actual}')
    for c in containers:
        name = c['Config']['Labels']['com.docker.compose.service']
        state = c['State']
        if state['Status'] != 'running' or state.get('Health', {}).get('Status') != 'healthy':
            raise RuntimeError(f'{name}: {state["Status"]}, health={state.get("Health", {}).get("Status")}')
        image = c['Config']['Image']
        if ':latest' in image or '@sha256:' not in image or image != config['services'][name]['image']:
            raise RuntimeError(f'{name}: unpinned image {image}')
        if c['Image'] != image_lock[image.split('@', 1)[0]]['id']:
            raise RuntimeError(f'{name}: runtime image ID differs from images.lock.json')
        persistent = {m['Destination'] for m in c['Mounts'] if m['Type'] in ('volume', 'bind')}
        if not required_mounts[name] <= persistent:
            raise RuntimeError(f'{name}: missing persistent mounts {required_mounts[name] - persistent}')
        print(f'PASS {name}: running, healthy, restarts={c["RestartCount"]}, image={image}')
        print(f'PASS {name}: persistent mounts {sorted(required_mounts[name])}')
    # Do not let HTTP proxy settings redirect loopback acceptance probes.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def get(service, path):
        port = config['services'][service]['ports'][0]
        host = port.get('host_ip', '127.0.0.1')
        if host in ('0.0.0.0', '::'):
            host = '127.0.0.1'
        url = f'http://{host}:{port["published"]}{path}'
        with opener.open(url, timeout=15) as response:
            body = response.read()
            if response.status != 200:
                raise RuntimeError(f'{url}: HTTP {response.status}')
        print(f'PASS HTTP 200 {url}')
        return body

    ping = json.loads(get('apiserver', '/debug.ping'))
    if ping.get('meta', {}).get('result_code') != 200 or ping.get('data', {}).get('msg') != 'ClearML server':
        raise RuntimeError('Invalid API ping response')
    try:
        info = json.loads(get('apiserver', '/v2.35/server.info'))
        if info.get('data', {}).get('version') != '2.4.0':
            raise RuntimeError(f'Unexpected server version: {info.get("data")}')
        print('PASS server.info:', json.dumps(info['data'], sort_keys=True))
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        print('PASS server.info access control: anonymous request returns HTTP 401 (authenticated API not tested)')
    version = subprocess.check_output(command + ['exec', '-T', 'apiserver', 'python3', '-c',
        'from apiserver.version import __version__; print(__version__)'], text=True).strip()
    if version != '2.4.0':
        raise RuntimeError(f'Unexpected runtime server source version: {version}')
    print(f'PASS runtime apiserver.version: {version}')
    html = get('webserver', '/')
    if b'<html' not in html.lower() or b'<script' not in html.lower():
        raise RuntimeError('Web response is not the application HTML')
    scripts = re.findall(r'<script[^>]+src=["\x27]([^"\x27]+)', html.decode())
    if not scripts:
        raise RuntimeError('Web application has no script assets')
    for src in scripts:
        parsed = urllib.parse.urlsplit(src)
        if parsed.scheme or parsed.netloc:
            continue
        body = get('webserver', urllib.parse.urljoin('/', src))
        if not body or b'<html' in body[:200].lower():
            raise RuntimeError(f'Invalid JavaScript asset: {src}')
    if get('fileserver', '/').strip() != b'OK':
        raise RuntimeError('Invalid Fileserver response')
    proxied_ping = json.loads(get('webserver', '/api/debug.ping'))
    if proxied_ping.get('meta', {}).get('result_code') != 200:
        raise RuntimeError('Web API proxy failed')
    if get('webserver', '/files/').strip() != b'OK':
        raise RuntimeError('Web Fileserver proxy failed')
    for name, cmd in [
        ('mongo', ['mongosh', '--quiet', '--eval', 'db.adminCommand({ping: 1})']),
        ('redis', ['redis-cli', 'ping']),
        ('elasticsearch', ['curl', '-fsS', 'http://127.0.0.1:9200/_cluster/health']),
    ]:
        result = subprocess.check_output(command + ['exec', '-T', name, *cmd], text=True).strip()
        print(f'PASS {name} probe: {result}')
    print('T01-A live acceptance: PASS (no Agent or training task created)')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
