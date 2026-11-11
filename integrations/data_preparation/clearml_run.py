"""T02-A single-run asset ledger, CPU Agent submission and independent verification.

Source infra/agent/env.sh. prepare and submit resume recorded IDs; a pending
ambiguous creation halts instead of creating duplicates. Never resets/requeues a
failed task, deletes assets, or modifies an existing task outside this ledger.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import zipfile

from clearml import Dataset, Task
from clearml.backend_api.session import Session

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name('prepare.py')
SPEC = importlib.util.spec_from_file_location('preparation', SOURCE)
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
E = ROOT / 'infra/evidence/t02a'
LEDGER = E / 'ledger.json'
PYTHON = '/root/miniconda3/envs/clearml-backend/bin/python'
WORKER = 'tiesheai-rail-cpu:cpu0'
FILESERVER = 'http://127.0.0.1:8081'
SESSION = None


def api(service, action, **payload):
    global SESSION
    SESSION = SESSION or Session()
    r = SESSION.send_request(service, action, json=payload)
    r.raise_for_status()
    j = r.json()
    if j['meta']['result_code'] != 200:
        raise RuntimeError(service + '.' + action + ' failed')
    return j['data']


def load():
    return json.loads(LEDGER.read_text())


def save(d):
    p.write_json(LEDGER, d)


def audit_creates():
    import requests
    original = requests.Session.request

    def observed(self, method, url, *args, **kwargs):
        r = original(self, method, url, *args, **kwargs)
        endpoint = url.split('?')[0].rsplit('/', 1)[-1]
        if endpoint in ('projects.create', 'tasks.create'):
            j = r.json()
            with (E / 'created-ids.jsonl').open('a') as f:
                f.write(json.dumps({'endpoint': endpoint, 'http': r.status_code,
                                   'business': j.get('meta', {}).get('result_code'),
                                   'id': j.get('data', {}).get('id')}) + '\n')
        return r
    requests.Session.request = observed


def idle():
    queues = api('queues', 'get_all', name='^rail-cpu$')['queues']
    assert len(queues) == 1, 'exactly one existing rail-cpu required'
    q = queues[0]
    workers = api('workers', 'get_all', last_seen=120)['workers']
    worker = next((w for w in workers if w['id'] == WORKER), None)
    active = api('tasks', 'get_all', status=['in_progress'], search_hidden=True)['tasks']
    p.write_json(E / ('idle-' + str(time.time_ns()) + '.json'), {'queue': q, 'workers': workers, 'active_tasks': active})
    assert worker and q['id'] in [x['id'] for x in worker.get('queues', [])], 'expected CPU worker unavailable'
    assert not q.get('entries'), 'rail-cpu busy: leave existing tasks untouched'
    assert not worker.get('task'), 'CPU worker running task: leave it untouched'
    assert not any(t.get('execution', {}).get('queue') == q['id'] or t.get('last_worker') == WORKER for t in active), 'CPU worker busy'
    return q['id']


def prepare_assets():
    if not LEDGER.exists():
        ns = 'TieSheAI-T02A-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        assert not api('projects', 'get_all', name='^' + ns + '($|/)')['projects']
        save({'project': ns, 'pending': None, 'input_dataset_id': None, 'processing_task_id': None,
              'output_dataset_id': None, 'input_version': '1.0.0', 'output_version': '1.0.0'})
    d = load()
    if d['pending']:
        raise RuntimeError('ambiguous pending create; reconcile created-ids/API before proceeding: ' + d['pending'])
    if not d['input_dataset_id']:
        d['pending'] = 'input_dataset'; save(d)
        ds = Dataset.create(dataset_project=d['project'], dataset_name='input-conversations', dataset_version=d['input_version'],
                            use_current_task=False, output_uri=FILESERVER, dataset_tags=['T02-A', 'SYNTHETIC_FUNCTIONAL_TEST'],
                            description='SYNTHETIC conversation-v1 functional test. No public demo or model training.')
        d.update(input_dataset_id=ds.id, pending=None); save(d)
    ds = Dataset.get(dataset_id=d['input_dataset_id'])
    if not ds.is_final():
        fixture = ROOT / 'examples/t02a/conversations.jsonl'
        if fixture.name not in ds.list_files():
            assert ds.add_files(fixture) == 1
        assert ds.upload(output_url=FILESERVER, show_progress=False, max_workers=1) is not False
        assert ds.finalize()
        ds._task.close()
    if not d['processing_task_id']:
        d['pending'] = 'processing_task'; save(d)
        task = Task.create(project_name=d['project'], task_name='T02-A CPU data preparation',
                           task_type=Task.TaskTypes.data_processing, script=str(SOURCE),
                           packages=['clearml==2.1.12'], add_task_init_call=False,
                           force_single_script_file=True, detect_repository=False)
        d.update(processing_task_id=task.id, pending=None); save(d)
    print(json.dumps(load(), indent=2))


def submit():
    d = load()
    if d['pending']:
        raise RuntimeError('pending create: inspect ledger first')
    task = Task.get_task(task_id=d['processing_task_id'])
    if str(task.status) != 'created':
        print('Existing task', task.id, str(task.status), '; no duplicate enqueue')
        return
    if d.get('enqueue_pending'):
        raise RuntimeError('enqueue pending; inspect task/queue instead of repeating')
    source = SOURCE.read_bytes()
    task.set_script(repository='', branch='', commit='', diff=source.decode(),
                    entry_point='prepare.py', working_dir='.', binary=PYTHON)
    task.set_tags(['T02-A', 'cpu', 'SYNTHETIC_FUNCTIONAL_TEST'])
    parameters = {'input_dataset_id': d['input_dataset_id'], 'input_dataset_version': d['input_version'],
                  'input_sha256': p.sha((ROOT / 'examples/t02a/conversations.jsonl').read_bytes()),
                  'input_filename': 'conversations.jsonl', 'seed': 42, 'validation_fraction': 0.25,
                  'output_version': d['output_version'], 'project': d['project'], 'fileserver': FILESERVER,
                  'ledger_path': str(LEDGER), 'synthetic_fixture': True, 'expected_code_sha256': p.sha(source)}
    task.set_parameters({'Preparation/' + k: v for k, v in parameters.items()})
    queue = idle()  # last check directly before enqueue; busy never changes existing queue entries
    d.update(code_sha256=p.sha(source), queue_id=queue, enqueue_pending=True); save(d)
    Task.enqueue(task, queue_id=queue)
    d.update(enqueue_pending=False, submitted=True); save(d)
    print('Enqueued', task.id, 'to existing rail-cpu', flush=True)


def download_artifacts(task, prefix):
    result = {}
    for key, artifact in task.artifacts.items():
        path = Path(artifact.get_local_copy(extract_archive=False, force_download=True, raise_on_error=True))
        data = path.read_bytes()
        target = E / (prefix + '-' + key + ('.zip' if zipfile.is_zipfile(path) else '.json'))
        target.write_bytes(data)
        assert p.sha(data) == artifact.hash, (prefix, key, 'registered artifact hash')
        assert len(data) == artifact.size
        result[key] = {'file': target.name, 'bytes': len(data), 'sha256': p.sha(data), 'uri': artifact.url}
    return result


def verify(timeout):
    d = load()
    task = Task.get_task(task_id=d['processing_task_id'])
    end = time.monotonic() + timeout
    transitions = []
    while True:
        task.reload(); status = str(task.status)
        if not transitions or transitions[-1]['status'] != status:
            transitions.append({'status': status, 'utc': datetime.now(timezone.utc).isoformat()})
            p.write_json(E / 'observed-status.json', transitions)
            print(task.id, status, flush=True)
        if status in ('completed', 'failed', 'stopped', 'closed') or time.monotonic() >= end:
            break
        time.sleep(2)
    raw_task = api('tasks', 'get_by_id', task=task.id)['task']
    p.write_json(E / 'processing-task.json', raw_task)
    console = ''
    for attempt in range(15):
        events = api('events', 'get_task_log', task=task.id, batch_size=1000, order='asc')['events']
        console = '\n'.join(e.get('msg', '') for e in events)
        if 'T02A_PREPARATION_OK' in console or status != 'completed':
            break
        time.sleep(1)
    (E / 'task-console.txt').write_text(console)
    assert status == 'completed', 'Agent did not complete; inspect existing task, never reset/recreate'
    assert raw_task['last_worker'] == WORKER
    assert raw_task['execution']['queue'] == d['queue_id']
    assert f"task {task.id} pulled from {d['queue_id']} by worker {WORKER}" in console
    assert 'T02A_AGENT_EXECUTION' in console and 'T02A_PREPARATION_OK' in console
    assert not raw_task['script']['repository']
    assert p.sha(raw_task['script']['diff'].encode()) == d['code_sha256'] == p.sha(SOURCE.read_bytes())
    parameters = task.get_parameters()
    assert parameters['Execution/running_locally'] == 'False'
    assert parameters['Execution/worker_id'] == WORKER
    assert parameters['Execution/python_executable'] == PYTHON
    assert parameters['Execution/cuda_visible_devices'] == 'none'
    assert parameters['Execution/code_sha256'] == d['code_sha256']
    d = load()
    assert parameters['Results/output_dataset_id'] == d['output_dataset_id']
    datasets, downloaded = {}, {}
    for label, key in (('input', 'input_dataset_id'), ('output', 'output_dataset_id')):
        ds = Dataset.get(dataset_id=d[key])
        assert ds.is_final() and ds._dataset_version == d[label + '_version']
        ds_task = Task.get_task(task_id=ds.id)
        arts = download_artifacts(ds_task, label)
        # Materialize in a fresh destination from independently downloaded remote archives.
        target = E / ('downloaded-' + label)
        target.mkdir(exist_ok=True)
        extracted = set()
        for name, info in arts.items():
            if name.startswith('data'):
                with zipfile.ZipFile(E / info['file']) as archive:
                    for member in archive.namelist():
                        assert Path(member).name == member, 'unexpected archive path'
                        (target / member).write_bytes(archive.read(member)); extracted.add(member)
        assert extracted == set(ds.list_files())
        datasets[label] = {'id': ds.id, 'version': ds._dataset_version, 'files': {}, 'artifacts': arts}
        for name in sorted(extracted):
            data = (target / name).read_bytes()
            datasets[label]['files'][name] = {'bytes': len(data), 'sha256': p.sha(data)}
        downloaded[label] = target
    assert (downloaded['input'] / 'conversations.jsonl').read_bytes() == (ROOT / 'examples/t02a/conversations.jsonl').read_bytes()
    output = downloaded['output']
    assert set(datasets['output']['files']) == set(p.FILES)
    manifest = json.loads((output / 'manifest.json').read_text())
    stats = json.loads((output / 'statistics.json').read_text())
    assert manifest['input']['dataset_id'] == d['input_dataset_id']
    assert manifest['input']['dataset_version'] == d['input_version']
    assert manifest['input']['processing_task_id'] == task.id
    assert manifest['input']['sha256'] == datasets['input']['files']['conversations.jsonl']['sha256']
    assert manifest['code_sha256'] == d['code_sha256']
    for name, info in manifest['outputs'].items():
        assert datasets['output']['files'][name] == info
    # Independently recompute from the downloaded input and recorded parameters.
    with tempfile_directory() as temporary:
        reproduced = Path(temporary) / 'prepared'
        p.prepare(downloaded['input'] / 'conversations.jsonl', reproduced, seed=42,
                  validation_fraction=0.25, provenance={k: v for k, v in manifest['input'].items() if k not in ('name', 'bytes', 'sha256')})
        for name in p.FILES:
            assert (output / name).read_bytes() == (reproduced / name).read_bytes(), ('reproducibility', name)
    assert (stats['input_records'], stats['unique_records'], stats['duplicates_removed']) == (14, 12, 2)
    scalars = task.get_reported_scalars()
    for key in ('input_records', 'unique_records', 'train_records', 'validation_records', 'duplicates_removed'):
        assert scalars['preparation'][key]['y'] == [float(stats[key])]
    logged_hashes = {}
    for line in console.splitlines():
        if line.startswith('T02A_OUTPUT_HASH '):
            item = json.loads(line.split(' ', 1)[1]); name = item.pop('name'); logged_hashes[name] = item
    assert logged_hashes == datasets['output']['files'], 'pre-upload output logs differ from downloaded bytes'
    report_artifacts = download_artifacts(task, 'processing')
    for name in ('manifest.json', 'statistics.json'):
        assert report_artifacts[name]['sha256'] == datasets['output']['files'][name]['sha256']
        assert task.artifacts[name].metadata['sha256_before_upload'] == report_artifacts[name]['sha256']
    assert d['input_dataset_id'] in str(raw_task.get('hyperparams', {})), 'input asset reference missing'
    metadata = Dataset.get(dataset_id=d['output_dataset_id']).get_metadata('provenance')
    assert metadata['input_dataset_id'] == d['input_dataset_id'] and metadata['processing_task_id'] == task.id
    result = {'pass': True, 'task_id': task.id, 'worker': WORKER, 'queue': d['queue_id'],
              'code_sha256': d['code_sha256'], 'parameters': parameters, 'statistics': stats,
              'datasets': datasets, 'report_artifacts': report_artifacts, 'source_snapshot_verified': True,
              'agent_queue_pull_log_verified': True, 'fresh_remote_archives_verified': True,
              'byte_identical_reproduction': True, 'pre_upload_hash_logs_verified': True, 'output_provenance': metadata}
    p.write_json(E / 'sdk-verification.json', result)
    print(json.dumps(result, indent=2))


def tempfile_directory():
    from tempfile import TemporaryDirectory
    return TemporaryDirectory(prefix='t02a-reproduce-')


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'submit', 'verify'])
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    E.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (E / 'controller.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        audit_creates()
        if args.action == 'prepare': prepare_assets()
        elif args.action == 'submit': submit()
        else: verify(args.timeout)


if __name__ == '__main__':
    main()
