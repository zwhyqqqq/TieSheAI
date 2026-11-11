"""Create immutable Web and private adapter bundles from a formal T02-B build."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'infra/evidence/t02b'
LOCAL = ROOT / 'infra/.local/web-fork'
WEB = ROOT / 'clearml-web'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest(path):
    return {str(p.relative_to(path)): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
            for p in sorted(path.rglob('*')) if p.is_file()}


def record(name, obj):
    (EVIDENCE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def readonly(path):
    for item in path.rglob('*'):
        item.chmod(0o555 if item.is_dir() else 0o444)
    path.chmod(0o555)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', help='immutable release name')
    args = parser.parse_args()
    if not re.fullmatch(r'data-entry-\d{8}-v\d+', args.name):
        parser.error('expected data-entry-YYYYMMDD-vN')
    release = LOCAL / 'releases' / args.name
    adapter = LOCAL / 'adapters' / args.name
    if release.exists() or adapter.exists():
        raise RuntimeError('Fixed release already exists')

    names = subprocess.check_output(
        ['git', '-C', str(WEB), 'ls-files', '-z', '--cached', '--others', '--exclude-standard']
    ).decode().split('\0')
    source = {name: sha((WEB / name).read_bytes()) for name in sorted(set(names) - {''})}
    patch = subprocess.check_output(['git', '-C', str(WEB), 'diff', 'HEAD', '--binary'])
    (EVIDENCE / (args.name + '-web.patch')).write_bytes(patch)
    source_hash = sha(json.dumps(source, sort_keys=True).encode())
    version = '2.5.0-data-entry-' + source_hash[:12]
    adapter.mkdir(parents=True)
    for file in sorted((ROOT / 'integrations/data_entry').glob('*.py')) + [ROOT / 'integrations/data_preparation/prepare.py']:
        dest = adapter / file.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, dest)
    nginx = (ROOT / 'infra/web-fork/nginx.conf').read_text()
    fragment = (ROOT / 'infra/web-fork/data-entry-location.conf').read_text()
    anchor = '        location = /widgets '
    assert nginx.count(anchor) == 1
    (adapter / 'nginx.conf').write_text(nginx.replace(anchor, fragment + '\n' + anchor))
    adapter_manifest = manifest(adapter)

    builds = {}
    for app in ('main', 'widgets'):
        build = WEB / 'out/t02b' / app / 'browser'
        assert (build / 'index.html').is_file()
        builds[app] = manifest(build)
        target = release if app == 'main' else release / 'widgets'
        shutil.copytree(build, target)
        for item in target.rglob('*.map'):
            item.unlink()
        for item in target.rglob('*'):
            if item.is_file() and item.suffix in ('.js', '.css'):
                body = item.read_text()
                body = re.sub(r'(?m)^//# sourceMappingURL=[^\r\n]*(?:\r?\n|$)', '', body)
                body = re.sub(r'/\*# sourceMappingURL=[^*\r\n]*\*/\s*\Z', '', body)
                item.write_text(body)
        page = target / 'index.html'
        base = '/' if app == 'main' else '/widgets/'
        page.write_text(re.sub(r'<base\s+href(?:="[^"]*")?\s*>', '<base href="' + base + '">', page.read_text(), count=1))
    config = json.loads((LOCAL / 'releases/artifact-download-20261110-v1/configuration.json').read_text())
    config['version'] = version
    (release / 'configuration.json').write_text(json.dumps(config, indent=2) + '\n')
    (release / 'env.js').write_text('(function(window){window.__env={subPath:"",forkVersion:' + json.dumps(version) + '};})(this);\n')
    version_info = {'version': version, 'release': args.name,
                    'source_head': subprocess.check_output(['git', '-C', str(WEB), 'rev-parse', 'HEAD'], text=True).strip(),
                    'source_dirty': True, 'source_manifest_sha256': source_hash,
                    'source_patch_sha256': sha(patch),
                    'adapter_manifest_sha256': sha(json.dumps(adapter_manifest, sort_keys=True).encode()),
                    'sourceMapsPublished': False, 'backend-release': 'clearml/server:2.4.0'}
    (release / 'version.json').write_text(json.dumps(version_info, indent=2) + '\n')
    deployed = manifest(release)
    record(args.name + '-source-manifest.json', source)
    record(args.name + '-adapter-manifest.json', adapter_manifest)
    record(args.name + '-build-manifests.json', builds)
    record(args.name + '-release-manifest.json', deployed)
    record(args.name + '-version.json', version_info)
    readonly(adapter)
    readonly(release)
    print(json.dumps(version_info, indent=2))


if __name__ == '__main__':
    main()
