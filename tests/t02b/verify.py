"""Read-only checks of the browser-created assets and preserved runtime."""

import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'infra/evidence/t02b'
sys.path.insert(0, str(ROOT / 'integrations/data_entry'))
import common


def load(name):
    return json.loads((EVIDENCE / name).read_text())


def save(name, data):
    (EVIDENCE / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture_api():
    spec = importlib.util.spec_from_file_location('fixtures', ROOT / 'tests/c3b/fixtures.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.E = EVIDENCE
    return module


def sdk_archive(task_id, name='data'):
    from clearml import Task

    artifact = Task.get_task(task_id=task_id).artifacts[name]
    data = Path(artifact.get_local_copy(extract_archive=False, force_download=True, raise_on_error=True)).read_bytes()
    assert sha(data) == artifact.hash and len(data) == artifact.size
    return data


def verify_job(label):
    from clearml import Dataset, Task

    browser = load(label + '-browser.json')
    assert browser['pass'] and browser['download'] and browser['retries']
    record = browser['completed']
    runtime = json.loads(common.request_path(record['request_id']).read_text())
    for key in ('request_id', 'input_dataset_id', 'input_sha256', 'processing_task_id',
                'output_dataset_id', 'manifest_sha256', 'code_sha256', 'owner'):
        assert runtime[key] == record[key], key
    api = fixture_api().api
    task_id = record['processing_task_id']
    task = Task.get_task(task_id=task_id)
    info = api('tasks.get_by_id', task=task_id)['task']
    assert info['status'] == 'completed' and info['type'] == 'data_processing'
    assert info['user'] == record['owner']
    assert info['last_worker'] == 'tiesheai-rail-cpu:cpu0'
    assert info['execution']['queue'] == record['queue_id']
    params = task.get_parameters()
    assert params['Preparation/input_dataset_id'] == record['input_dataset_id']
    assert params['Preparation/input_dataset_version'] == '1.0.0'
    assert params['Preparation/input_sha256'] == record['input_sha256']
    assert params['Preparation/request_id'] == record['request_id']
    assert int(params['Preparation/seed']) == 73 and float(params['Preparation/validation_fraction']) == 0.34
    assert params['Results/output_dataset_id'] == record['output_dataset_id']
    assert params['Execution/cuda_visible_devices'] == 'none'
    assert params['Execution/code_sha256'] == record['code_sha256']
    assert sha(info['script']['diff'].encode()) == record['code_sha256']
    assert sha(common.snapshot().encode()) == record['code_sha256']
    assert params['Preparation/core_sha256'] == sha(common.CORE_PATH.read_bytes())

    logs = api('events.get_task_log', task=task_id, batch_size=1000, order='asc')['events']
    console = '\n'.join(event['msg'] for event in logs)
    assert 'T02B_AGENT_EXECUTION' in console and 'T02B_PREPARATION_OK' in console
    assert f"task {task_id} pulled from {record['queue_id']} by worker tiesheai-rail-cpu:cpu0" in console
    (EVIDENCE / 'task-console.txt').write_text(console)

    output = Dataset.get(dataset_id=record['output_dataset_id'])
    input_dataset = Dataset.get(dataset_id=record['input_dataset_id'])
    assert output.is_final() and output.version == '1.0.0'
    assert input_dataset.is_final() and input_dataset.version == '1.0.0'
    assert set(output.list_files()) == set(common.core.FILES)
    assert input_dataset.list_files() == ['conversations.jsonl']
    raw_input = (EVIDENCE / 'browser-input.jsonl').read_bytes()
    assert sha(raw_input) == record['input_sha256']
    with zipfile.ZipFile(io.BytesIO(sdk_archive(input_dataset.id))) as zipped:
        assert zipped.read('conversations.jsonl') == raw_input

    archive = (EVIDENCE / browser['download']['file']).read_bytes()
    assert archive == sdk_archive(output.id)
    members = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        assert sorted(zipped.namelist()) == sorted(common.core.FILES)
        manifest = json.loads(zipped.read('manifest.json'))
        assert sha(zipped.read('manifest.json')) == record['manifest_sha256']
        assert sdk_archive(task_id, 'manifest.json') == zipped.read('manifest.json')
        assert manifest['input']['dataset_id'] == input_dataset.id
        assert manifest['input']['processing_task_id'] == task_id
        assert manifest['input']['request_id'] == record['request_id']
        assert manifest['code_sha256'] == record['code_sha256']
        with tempfile.TemporaryDirectory(prefix='t02b-reproduce-') as temporary:
            root = Path(temporary)
            source = root / 'conversations.jsonl'
            source.write_bytes(raw_input)
            common.core.prepare(source, root / 'output', 73, 0.34,
                                {'synthetic_fixture': True})
            for name in zipped.namelist():
                data = zipped.read(name)
                members[name] = {'sha256': sha(data), 'bytes': len(data)}
                if name != 'manifest.json':
                    assert members[name] == manifest['outputs'][name]
                    assert data == (root / 'output' / name).read_bytes(), name
    assert len(browser['selections']) == 2
    assert browser['selections'][-1] == {'id': output.id, 'version': output.version,
                                         'manifest_sha256': record['manifest_sha256']}
    save('job-verification.json', {'pass': True, 'record': record, 'archive': browser['download'],
                                   'members': members, 'browser_steps': browser['steps'],
                                   'selection': browser['selections'], 'worker': info['last_worker'],
                                   'input_archive_matches_upload': True, 'reproduced_members': 4})
    print('PASS real Agent completed, input bytes, output archive, 5 member hashes and 4 deterministic members')


def verify_protection():
    before, after = load('snapshot-before.json'), load('snapshot-after.json')
    for key in ('agent', 'volumes', 'credential_metadata', 'release'):
        assert before[key] == after[key], key
    protected = lambda snap: [c for c in snap['containers'] if not c['Name'].startswith('/tiesheai-web-fork')]
    assert protected(before) == protected(after) and len(protected(after)) == 6
    assert all(c['health'] == 'healthy' for c in after['containers'])
    for repo, previous in before['git'].items():
        current = after['git'][repo]
        assert (previous['head'], previous['index']) == (current['head'], current['index'])
        if repo == 'clearml-server':
            assert previous == current
    allowed = {'docs/HANDOFF.md', 'docs/STATUS.md', 'docs/DECISIONS.md', 'docs/ROADMAP.md',
               'docs/T02B_TASK.md', 'infra/web-fork/README.md'}
    for name, digest in before['files'].items():
        if name not in allowed:
            assert after['files'].get(name) == digest, name
    for name in ('compose.yaml', 'nginx.conf'):
        baseline = 'compose-before.yaml' if name.startswith('compose') else 'nginx-before.conf'
        assert (ROOT / 'infra/web-fork' / name).read_bytes() == (EVIDENCE / baseline).read_bytes()
    old_release = ROOT / 'infra/.local/web-fork/releases/artifact-download-20261110-v1'
    old_manifest = json.loads((ROOT / 'infra/evidence/artifact-download-fix/release-manifest.json').read_text())
    assert len(list(p for p in old_release.rglob('*') if p.is_file())) == len(old_manifest)
    assert all(sha((old_release / name).read_bytes()) == meta['sha256'] for name, meta in old_manifest.items())
    assert (EVIDENCE / 'python-before.txt').read_bytes() == (EVIDENCE / 'python-after.txt').read_bytes()

    b, a = load('inventory-before.json'), fixture_api().inventory()
    record = load('job-verification.json')['record']
    save('inventory-final.json', a)
    new = {}
    for kind in ('projects', 'tasks', 'models'):
        assert all(a[kind].get(oid) == obj for oid, obj in b[kind].items()), kind
        new[kind] = {oid: a[kind][oid] for oid in set(a[kind]) - set(b[kind])}
    assert set(new['tasks']) == {record[k] for k in ('input_dataset_id', 'processing_task_id', 'output_dataset_id')}
    assert len(new['projects']) == 4 and not new['models']
    assert all(p['name'] == record['project'] or p['name'].startswith(record['project'] + '/') for p in new['projects'].values())
    assert all(t['project'] in new['projects'] for t in new['tasks'].values())
    assert a['preferences_sha256'] == b['preferences_sha256']
    assert set(a['queues']) == set(b['queues'])
    for qid, previous in b['queues'].items():
        actual = a['queues'][qid]
        assert {k: v for k, v in actual.items() if k != 'last_update'} == {k: v for k, v in previous.items() if k != 'last_update'}
        if qid != record['queue_id']:
            assert actual == previous
    assert not a['queues'][record['queue_id']].get('entries')
    historical = []
    for task_id, item in b['tasks'].items():
        for artifact in item.get('execution', {}).get('artifacts', []):
            data = sdk_archive(task_id, artifact['key'])
            assert sha(data) == artifact['hash']
            historical.append({'task_id': task_id, 'key': artifact['key'], 'sha256': sha(data), 'bytes': len(data)})
    save('protection-result.json', {'pass': True, 'protected_services': 6, 'old_artifacts': historical,
                                    'new_objects': {k: list(v) for k, v in new.items()},
                                    'unchanged': ['agent', 'volumes', 'credentials', 'preferences', 'old objects',
                                                  'python dependencies', 'two old releases', 'three Git HEAD/indexes']})
    print('PASS six service identities, Agent, old objects, %s old artifacts, and one set of 3 new Tasks' % len(historical))


def verify_delivery():
    for name in ('job-verification.json', 'protection-result.json', 'rollback-browser.json', 'restored-browser.json',
                 'legacy-new-browser.json'):
        assert load(name)['pass'], name
    handoff = (ROOT / 'docs/HANDOFF.md').read_text()
    status = (ROOT / 'docs/STATUS.md').read_text()
    report = ROOT / 'docs/T02B_WEB_DATA_ENTRY.md'
    assert len(handoff.splitlines()) <= 100
    assert 'T02-B' in handoff and '限定通过' in handoff
    assert 'T02-B' in status and '限定验收通过' in status
    for document in (report, ROOT / 'infra/web-fork/README.md'):
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', document.read_text()):
            if not target.startswith(('http://', 'https://', '#')):
                assert (document.parent / target.split('#', 1)[0]).exists(), (document, target)
    version = load('data-entry-20261111-v1-version.json')
    source = load('data-entry-20261111-v1-source-manifest.json')
    assert all(sha((ROOT / 'clearml-web' / path).read_bytes()) == digest for path, digest in source.items())
    assert sha(json.dumps(source, sort_keys=True).encode()) == version['source_manifest_sha256']
    adapter = load('data-entry-20261111-v1-adapter-manifest.json')
    private = ROOT / 'infra/.local/web-fork/adapters/data-entry-20261111-v1'
    assert all(sha((private / path).read_bytes()) == info['sha256'] for path, info in adapter.items())
    assert sha(json.dumps(adapter, sort_keys=True).encode()) == version['adapter_manifest_sha256']
    for repo in (ROOT, ROOT / 'clearml-web', ROOT / 'clearml-server'):
        for options in (['diff', '--check'], ['diff', '--cached', '--check']):
            subprocess.run(['git', '-C', str(repo), *options], check=True)
    subprocess.run(['git', 'check-ignore', 'infra/evidence/t02b', 'infra/.local/data-entry'], cwd=ROOT, check=True)
    print('PASS delivery checks, evidence ignored, Git diff whitespace checks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['job', 'protection', 'delivery'])
    parser.add_argument('--browser', default='full')
    args = parser.parse_args()
    if args.mode == 'job':
        verify_job(args.browser)
    elif args.mode == 'protection':
        verify_protection()
    else:
        verify_delivery()
