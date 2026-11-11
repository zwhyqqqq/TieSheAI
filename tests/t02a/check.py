"""T02-A delivery checks: real downloads, protected state, docs and changes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'infra/evidence/t02a'
MODIFIED = {'docs/STATUS.md', 'docs/HANDOFF.md', 'docs/DECISIONS.md', 'docs/ROADMAP.md', 'docs/T02A_TASK.md'}
NEW_PREFIXES = ('integrations/data_preparation/', 'schemas/', 'examples/t02a/', 'tests/t02a/')
NEW_DOC = 'docs/T02A_DATA_PREPARATION.md'


def read(name):
    return json.loads((E / name).read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, obj):
    (E / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def live_inventory():
    import importlib.util
    spec = importlib.util.spec_from_file_location('fixtures_readonly', ROOT / 'tests/c3b/fixtures.py')
    f = importlib.util.module_from_spec(spec); spec.loader.exec_module(f)
    f.E = E
    return f.inventory()


def preservation():
    before, after = read('snapshot-before.json'), read('snapshot-after.json')
    for key in ('containers', 'agent', 'volumes', 'credential_metadata', 'release'):
        assert before[key] == after[key], ('protected runtime changed', key)
    assert len(after['containers']) == 7
    assert all(c['health'] == 'healthy' and c['status'] == 'running' for c in after['containers'])
    for repo in before['git']:
        assert before['git'][repo]['head'] == after['git'][repo]['head']
        assert before['git'][repo]['index'] == after['git'][repo]['index']
        if repo != '.': assert before['git'][repo] == after['git'][repo], repo
    for name, digest in before['files'].items():
        if name not in MODIFIED:
            assert after['files'].get(name) == digest, ('existing file changed', name)
    added = set(after['files']) - set(before['files'])
    assert added and all(x == NEW_DOC or x.startswith(NEW_PREFIXES) for x in added), sorted(added)
    b, a, ledger = read('inventory-before.json'), live_inventory(), read('ledger.json')
    for kind in ('tasks', 'models', 'projects'):
        for oid, obj in b[kind].items():
            assert a[kind].get(oid) == obj, ('old object changed', kind, oid)
        new_ids = set(a[kind]) - set(b[kind])
        assert new_ids == set(ledger['objects'][kind]), (kind, new_ids)
    assert len(ledger['objects']['tasks']) == 3 and len(ledger['objects']['projects']) == 4
    assert not ledger['objects']['models']
    for obj in ledger['objects']['projects'].values():
        assert obj['name'] == ledger['project'] or obj['name'].startswith(ledger['project'] + '/')
    project_ids = set(ledger['objects']['projects'])
    for obj in ledger['objects']['tasks'].values(): assert obj['project'] in project_ids
    assert set(b['queues']) == set(a['queues'])
    for oid, obj in b['queues'].items():
        expected, actual = dict(obj), dict(a['queues'][oid])
        if oid == ledger['queue_id']:
            expected.pop('last_update'); actual.pop('last_update')  # authorized enqueue/pull updates this timestamp
        assert expected == actual, ('queue configuration/entries changed', oid)
    assert b['preferences_sha256'] == a['preferences_sha256']
    assert (E / 'python-before.txt').read_bytes() == (E / 'python-after.txt').read_bytes()
    # Historical artifacts, including C3-B fixture files, must retain their original bytes.
    from clearml import Task
    artifact_checks = []
    for oid, obj in b['tasks'].items():
        for name, artifact in Task.get_task(task_id=oid).artifacts.items():
            data = Path(artifact.get_local_copy(extract_archive=False, force_download=True, raise_on_error=True)).read_bytes()
            assert sha(data) == artifact.hash and len(data) == artifact.size
            artifact_checks.append({'task': oid, 'key': name, 'bytes': len(data), 'sha256': sha(data)})
    write('inventory-final.json', a)
    write('preservation-result.json', {'pass': True, 'containers_unchanged': 7,
          'agent_process_config_environment_unchanged': True, 'existing_files_preserved': True,
          'three_repo_heads_indexes_preserved': True, 'old_objects_unchanged': True,
          'only_expected_new_objects': ledger['objects'], 'queue_empty_configuration_unchanged': True,
          'expected_queue_last_update_changed': True, 'historical_artifacts': artifact_checks})
    print('PASS seven containers/Agent/config/environment, prior files and three Git indexes, full old objects, C3-B files and queue configuration')


def browser(label):
    state, sdk = read(label + '-browser.json'), read('sdk-verification.json')
    assert state['pass'] and all(x['ok'] for x in state['steps'])
    assert len(state['steps']) == 16, len(state['steps'])
    assert len(state['downloads']) == 3
    assert not state['unknownErrors'] and not state['observerErrors']
    records = []
    for stage, ds in (('input', sdk['datasets']['input']), ('output', sdk['datasets']['output'])):
        dl = next(x for x in state['downloads'] if x['stage'] == stage + '-archive-real-download')
        data = (E / dl['file']).read_bytes()
        assert dl['failure'] is None
        assert sha(data) == dl['sha256'] == ds['artifacts']['data']['sha256']
        assert len(data) == dl['bytes'] == ds['artifacts']['data']['bytes']
        with zipfile.ZipFile(E / dl['file']) as z:
            assert set(z.namelist()) == set(ds['files'])
            for name, item in ds['files'].items():
                raw = z.read(name)
                assert sha(raw) == item['sha256'] and len(raw) == item['bytes']
                assert raw == (E / ('downloaded-' + stage) / name).read_bytes()
        records.append({'dataset': ds['id'], 'browser_archive': dl, 'all_member_bytes_verified': True})
    report = next(x for x in state['downloads'] if x['stage'] == 'task-report-real-download')
    assert (E / report['file']).read_bytes() == (E / 'downloaded-output/manifest.json').read_bytes()
    # Check all browser errors individually against the explicit read protection.
    correlations = []
    used = set()
    for err in state.get('pageErrors', []):
        match = next(((i, e) for i, e in enumerate(state['errors']) if i not in used and
                     e['name'] == 'HttpErrorResponse' and e['status'] == 0 and
                     e['constructor'] == err['message'] and err['name'] == '' and
                     abs(e['observedAt'] - err['observedAt']) < 100 and
                     any(b['url'] == e['url'] for b in state['blocked'])), None)
        assert match, ('unclassified browser exception', err)
        used.add(match[0]); correlations.append({'pageError': err, 'structured': match[1]})
    assert all(b['reason'] != 'unknown endpoint; deny pending contract review' for b in state['blocked'])
    assert all(n['http'] == 200 and n.get('business', 200) == 200 for n in state['network'] if n['api'])
    optional = {'http://127.0.0.1:18080/credentials.json', 'http://127.0.0.1:18080/onboarding.json'}
    for n in state['network']:
        if n['http'] >= 400: assert n['http'] == 404 and n['url'] in optional, n
    file_net = [n for n in state['network'] if '/files/' in n['url']]
    from urllib.parse import urlsplit
    observed_body_limits = []
    for dl in state['downloads']:
        expected_artifact = (sdk['report_artifacts']['manifest.json'] if dl['stage'] == 'task-report-real-download' else
                             sdk['datasets']['input' if dl['stage'].startswith('input-') else 'output']['artifacts']['data'])
        expected_url = 'http://127.0.0.1:18080/files' + urlsplit(expected_artifact['uri']).path
        matches = [n for n in file_net if n['stage'] == dl['stage'] and n['url'] == expected_url]
        assert matches and all(n['http'] == 200 and n['sentCookie'] for n in matches), dl
        assert not any(f['url'] == expected_url for f in state['failed'])
        for n in matches:
            if n.get('bytes') == 0:
                # Chromium's DevTools body observer is empty for this JSON fetch;
                # saved download bytes are independently checked above, never replaced by observer bytes.
                assert dl['stage'] == 'task-report-real-download' and dl['bytes'] == expected_artifact['bytes']
                observed_body_limits.append({'stage': dl['stage'], 'observer_bytes': 0,
                                            'actual_download_bytes': dl['bytes'], 'actual_download_sha256': dl['sha256']})
            else:
                assert n.get('sha256') == dl['sha256'] and n.get('bytes') == dl['bytes'], n
    console_review = []
    for c in state['console']:
        url = c['location']['url']
        reason = None
        if c['text'] == 'Failed to load resource: the server responded with a status of 404 (Not Found)':
            assert url in optional and any(n['url'] == url and n['http'] == 404 for n in state['network'])
            reason = 'known optional configuration 404'
        elif c['text'] == 'Failed to load resource: net::ERR_BLOCKED_BY_CLIENT.Inspector':
            assert any(b['url'] == url for b in state['blocked']) and any(f['url'] == url for f in state['failed'])
            reason = 'intentional read protection; exact failed request URL'
        elif c['text'] == 'ERROR le':
            errors = [e for e in c.get('arguments', []) if e and e.get('status') is not None]
            assert errors and all(e['name'] == 'HttpErrorResponse' and e['status'] == 0 and
                                  any(b['url'] == e['url'] for b in state['blocked']) for e in errors)
            reason = 'structured status=0 exception from explicitly blocked URL'
        elif c['text'].startswith('TypeError: Failed to fetch\n'):
            assert c['stage'] == 'login' and 'chunk-6ERHWGZE.js' in c['text']
            assert any(f['stage'] == c['stage'] and f['url'] == 'https://api.github.com/repos/clearml/clearml' for f in state['failed'])
            reason = 'GitHub fetch inference from same-stage blocked request and exact saved stack; unchanged from historical C3-B'
        assert reason, ('unclassified console error', c)
        console_review.append({**c, 'classification': reason})
    for b in state['blocked']:
        assert b['reason'] in ('third-party', 'User settings write', 'Server statistics option write')
        assert any(f['url'] == b['url'] for f in state['failed'])
    write('browser-console-review.json', console_review)
    write('browser-verification.json', {'pass': True, 'label': label, 'steps': len(state['steps']),
          'downloads': records, 'report_download': report, 'page_error_correlations': correlations,
          'optional_config_404': sorted(optional), 'same_origin_file_downloads': file_net,
          'read_protection_retained': True, 'no_unknown_endpoint': True, 'response_body_observer_limits': observed_body_limits})
    print('PASS real Fork task/status/logs/parameters, Dataset content hashes, three real downloads and independent ZIP member checks')


def delivery():
    assert read('sdk-verification.json')['pass'] and read('preservation-result.json')['pass'] and read('browser-verification.json')['pass']
    for repo in (ROOT, ROOT / 'clearml-web', ROOT / 'clearml-server'):
        for args in (['diff', '--check'], ['diff', '--cached', '--check']):
            subprocess.run(['git', '-C', str(repo), *args], check=True)
    handoff = (ROOT / 'docs/HANDOFF.md').read_text()
    status = (ROOT / 'docs/STATUS.md').read_text()
    assert len(handoff.splitlines()) <= 100
    for text in (handoff, status):
        assert 'T02-A' in text and 'T02-B' in text and '完整 C3' in text
    inspect_files = [ROOT / n for n in MODIFIED | {NEW_DOC}]
    inspect_files += [p for prefix in NEW_PREFIXES for p in (ROOT / prefix).rglob('*') if p.is_file()]
    references = []
    for path in inspect_files:
        text = path.read_text()
        assert not re.search(r'(?i)(?:password|secret_key|api_key|access_key)\s*[:=]\s*[\"\'][^\"\']{8,}', text), path
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)', text):
                if re.match(r'^[a-z]+:', target) or target.startswith('#'): continue
                ref = target.split('#')[0]
                assert (path.parent / ref).exists(), (path, target)
                references.append((str(path.relative_to(ROOT)), ref))
    subprocess.run(['git', 'check-ignore', 'infra/evidence/t02a/ledger.json', 'infra/.local/agent/clearml.conf'], cwd=ROOT, check=True, stdout=subprocess.PIPE)
    write('delivery-result.json', {'pass': True, 'handoff_lines': len(handoff.splitlines()),
                                  'checked_files': sorted(str(p.relative_to(ROOT)) for p in inspect_files),
                                  'relative_references_checked': len(references), 'three_repo_diff_checks': 6})
    print('PASS document consistency/references, scope/preservation, sensitive patterns/ignore, HANDOFF line limit and six Git whitespace checks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['preservation', 'browser', 'delivery'])
    parser.add_argument('--label', default='fork-r4')
    args = parser.parse_args()
    if args.action == 'preservation': preservation()
    elif args.action == 'browser': browser(args.label)
    else: delivery()
