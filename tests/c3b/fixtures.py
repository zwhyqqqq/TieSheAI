#!/usr/bin/env python3
"""C3-B controlled fixture creation and read-only verification. No execution/queue APIs.
Source infra/agent/env.sh first. prepare establishes one namespace; create resumes only
known IDs and refuses ambiguous pending creates. All evidence stays git-ignored.
"""
import argparse, hashlib, json, os, pathlib, sys, time, uuid, zipfile
from urllib.parse import urlparse
from clearml import Dataset, Task, OutputModel
from clearml.backend_api.session import Session

R = pathlib.Path(__file__).resolve().parents[2]
E = R / 'infra/evidence/t01c3b'
E.mkdir(mode=0o700, parents=True, exist_ok=True)
LEDGER = E / 'ledger.json'
S = None

def dump(path, obj):
    p = pathlib.Path(path)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + '\n')
    os.chmod(tmp, 0o600)
    tmp.replace(p)

def sha(b):
    return hashlib.sha256(b).hexdigest()

def api(endpoint, **body):
    global S
    if S is None:
        S = Session()
    service, action = endpoint.split('.')
    response = S.send_request(service, action, version='2.35', json=body)
    data = response.json()
    with (E / 'sdk-http.jsonl').open('a') as f:
        f.write(json.dumps({'time': time.time(), 'endpoint': endpoint, 'http': response.status_code,
                            'business': data.get('meta', {}).get('result_code')}) + '\n')
    assert response.status_code == 200 and data['meta']['result_code'] == 200, endpoint
    return data['data']

def inventory():
    out = {}
    for service in ('projects', 'tasks', 'models', 'queues'):
        items = []
        for page in range(100):
            batch = api(service + '.get_all', page=page, page_size=500, search_hidden=True)[service]
            items += batch
            if len(batch) < 500:
                break
        else:
            raise RuntimeError('Inventory pagination exceeded limit')
        out[service] = {x['id']: x for x in items}
    out['preferences_sha256'] = sha(json.dumps(api('users.get_preferences'), sort_keys=True).encode())
    return out

def readledger():
    d = json.loads(LEDGER.read_text())
    stage = d.get('stages', {}).get('model')
    if stage and not stage.get('id') and d['objects']['models']:
        assert len(d['objects']['models']) == 1
        stage['id'] = next(iter(d['objects']['models']))
        saveledger(d)
    return d

def saveledger(d):
    dump(LEDGER, d)

def register_delta(d):
    current = inventory()
    before = json.loads((E / 'inventory-before.json').read_text())
    for kind in ('projects', 'tasks', 'models'):
        for id_, obj in current[kind].items():
            if id_ in before[kind]:
                continue
            if kind == 'projects':
                assert obj['name'] == d['project'] or obj['name'].startswith(d['project'] + '/'), obj
            else:
                assert obj['project'] in (set(current['projects']) - set(before['projects'])), obj
            d['objects'][kind][id_] = {'name': obj['name'], 'project': obj.get('project'),
                                      'system_tags': obj.get('system_tags', [])}
    saveledger(d)
    return current

def prepare():
    assert not LEDGER.exists(), 'Existing ledger: reuse it; do not prepare another namespace'
    baseline = inventory()
    dump(E / 'inventory-before.json', baseline)
    ns = 'T01-C3B-Fixture-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
    assert all(not x['name'].startswith(ns) for x in baseline['projects'].values())
    d = {'namespace': ns, 'project': ns, 'dataset_name': ns + '-Synthetic-Text',
         'fileserver': 'http://127.0.0.1:8081', 'objects': {'projects': {}, 'tasks': {}, 'models': {}},
         'stages': {}, 'pending': None, 'no_agent_execution': True}
    saveledger(d)
    (E / 'payload').mkdir(exist_ok=True)
    (E / 'payload/inherited.txt').write_text('T01-C3B TEST FIXTURE ONLY\nSynthetic railway text v1. No business data.\n')
    (E / 'payload/added.txt').write_text('T01-C3B TEST FIXTURE ONLY\nSynthetic additional text v2. Inherits inherited.txt.\n')
    (E / 'payload/TEST_FIXTURE_NOT_TRAINED_WEIGHTS.json').write_text(
        '{"fixture_only":true,"trained_weights":false,"purpose":"C3-B upload/download relationship test; never load or infer"}\n')
    print('Prepared unique namespace', ns, 'with zero server writes')

def audit_sdk_requests():
    """Observe real HTTP responses; never save credentials or token responses."""
    import requests
    original = requests.Session.request
    def observed(self, method, url, *args, **kwargs):
        parsed = urlparse(url)
        endpoint = parsed.path.rsplit('/', 1)[-1]
        if parsed.port == 8008:
            forbidden = {'tasks.enqueue', 'tasks.dequeue', 'tasks.reset', 'tasks.delete',
                         'queues.create', 'queues.delete', 'queues.add_task', 'queues.remove_task',
                         'queues.get_next_task', 'users.set_preferences', 'organization.set_statistics'}
            assert endpoint not in forbidden, ('Forbidden fixture operation', endpoint)
        response = original(self, method, url, *args, **kwargs)
        if parsed.port == 8008 and endpoint != 'auth.login':
            try:
                body = response.json()
            except ValueError:
                body = {}
            record = {'time': time.time(), 'endpoint': endpoint, 'http': response.status_code,
                      'business': body.get('meta', {}).get('result_code')}
            with (E / 'sdk-create-http.jsonl').open('a') as f:
                f.write(json.dumps(record) + '\n')
            if endpoint in ('projects.create', 'tasks.create', 'models.create'):
                with (E / 'created-ids.jsonl').open('a') as f:
                    f.write(json.dumps({**record, 'id': body.get('data', {}).get('id')}) + '\n')
                if endpoint == 'models.create' and body.get('data', {}).get('id'):
                    saved = json.loads(LEDGER.read_text())
                    saved['stages']['model']['id'] = body['data']['id']
                    saveledger(saved)
        return response
    requests.Session.request = observed


def create():
    audit_sdk_requests()
    d = readledger()
    assert d['fileserver'] == 'http://127.0.0.1:8081'
    assert d['pending'] is None, 'Ambiguous pending create: inspect ledger/server IDs, never blindly retry'
    for key, version, filename, parent in [('v1', '1.0.0', 'inherited.txt', None), ('v2', '2.0.0', 'added.txt', 'v1')]:
        if key not in d['stages']:
            d['pending'] = key
            saveledger(d)
            ds = Dataset.create(dataset_name=d['dataset_name'], dataset_project=d['project'],
                                dataset_version=version, dataset_tags=[d['namespace'], 'TEST_FIXTURE_ONLY'],
                                parent_datasets=[d['stages'][parent]['id']] if parent else [],
                                use_current_task=False, output_uri=d['fileserver'],
                                description='TEST FIXTURE ONLY. Synthetic text, no training or Agent execution.')
            d['stages'][key] = {'id': ds.id, 'version': version, 'parents': [d['stages'][parent]['id']] if parent else [], 'finalized': False}
            d['pending'] = None
            register_delta(d)
        else:
            ds = Dataset.get(dataset_id=d['stages'][key]['id'])
        if not ds.is_final():
            if filename not in ds.list_files():
                assert ds.add_files(E / 'payload' / filename) == 1
            assert ds.upload(output_url=d['fileserver'], show_progress=False, max_workers=1) is not False
            assert ds.finalize()
        d['stages'][key]['finalized'] = True
        register_delta(d)
    if 'draft' not in d['stages']:
        d['pending'] = 'draft'
        saveledger(d)
        task = Task.create(project_name=d['project'], task_name=d['namespace'] + '-Model-Draft',
                           task_type=Task.TaskTypes.testing, detect_repository=False, packages='', add_task_init_call=False)
        d['stages']['draft'] = {'id': task.id}
        d['pending'] = None
        register_delta(d)
    else:
        task = Task.get_task(task_id=d['stages']['draft']['id'])
    assert str(task.get_status()) == 'created'
    if 'model' not in d['stages']:
        d['pending'] = 'model'
        saveledger(d)
        model = OutputModel(task=task, name=d['namespace'] + '-TEST-FIXTURE-NOT-WEIGHTS',
                            tags=[d['namespace'], 'TEST_FIXTURE_ONLY'],
                            comment='TEST FIXTURE ONLY. JSON marker; NOT trained model weights. Never load or infer.')
        # OutputModel is lazy: creation HTTP IDs are also logged immediately in created-ids.jsonl.
        d['stages']['model'] = {'id': model.id, 'task': task.id, 'uploaded': False}
        d['pending'] = None
        register_delta(d)
    else:
        model = OutputModel(task=task, base_model_id=d['stages']['model']['id'])
    if not d['stages']['model']['uploaded']:
        uri = model.update_weights(weights_filename=str(E / 'payload/TEST_FIXTURE_NOT_TRAINED_WEIGHTS.json'),
                                   upload_uri=d['fileserver'], auto_delete_file=False, async_enable=False)
        model.wait_for_uploads(timeout=60)
        assert uri and uri.startswith(d['fileserver'] + '/'), 'Must be an actual fileserver URI'
        d['stages']['model'].update(id=model.id, uri=uri, uploaded=True)
        register_delta(d)
    assert str(task.get_status()) == 'created'
    print('Created/finalized exactly two Datasets; Draft Task remains created; model upload waited')

def download(uri, target):
    assert urlparse(uri).netloc == '127.0.0.1:8081', uri
    global S
    if S is None:
        S = Session()
    # Reuse the existing SDK session's token, never persist authentication headers.
    import requests
    response = requests.get(uri, headers={'Authorization': 'Bearer ' + S.token}, timeout=30)
    assert response.status_code == 200, (uri, response.status_code)
    pathlib.Path(target).write_bytes(response.content)
    return {'uri': uri, 'http': response.status_code, 'bytes': len(response.content), 'sha256': sha(response.content)}

def verify():
    d = readledger()
    current = register_delta(d)
    result = {'datasets': {}, 'model': {}, 'input_model_consumption': 'N/A (no authorized consumer)'}
    for key in ('v1', 'v2'):
        stage = d['stages'][key]
        ds = Dataset.get(dataset_id=stage['id'])
        assert ds.is_final()
        task = api('tasks.get_by_id', task=ds.id)['task']
        assert task['type'] == 'data_processing' and task['status'] == 'completed'
        assert not task.get('execution', {}).get('queue') and not task.get('last_worker')
        arts = []
        for a in task['execution']['artifacts']:
            record = {'key': a['key'], 'type': a.get('type'), 'registered_hash': a.get('hash'),
                      'registered_bytes': a.get('content_size')}
            if a.get('uri', '').startswith(d['fileserver'] + '/'):
                local = E / (key + '-' + a['key'] + '.bin')
                record.update(download(a['uri'], local))
                assert not a.get('hash') or a['hash'] == record['sha256']
                assert a.get('content_size') == record['bytes']
                if zipfile.is_zipfile(local):
                    with zipfile.ZipFile(local) as z:
                        record['archive_files'] = [{'name': n, 'bytes': len(z.read(n)), 'sha256': sha(z.read(n))} for n in z.namelist()]
            arts.append(record)
        state_path = next(E / (key + '-' + x['key'] + '.bin') for x in arts if x['key'] == 'state')
        state = json.loads(state_path.read_text())
        dump(E / (key + '-state.json'), state)
        expected = ['inherited.txt'] if key == 'v1' else ['added.txt', 'inherited.txt']
        assert sorted(ds.list_files()) == expected
        local = pathlib.Path(ds.get_local_copy(use_soft_links=False, max_workers=1))
        files = []
        for name in expected:
            data = (local / name).read_bytes()
            assert data == (E / 'payload' / name).read_bytes()
            files.append({'name': name, 'bytes': len(data), 'sha256': sha(data)})
        # SDK state is separately checked, without substituting for browser evidence.
        assert state['dependency_graph'][ds.id] == stage['parents']
        result['datasets'][key] = {**stage, 'task_id': task['id'], 'hidden_project_id': task['project'],
                                   'status': task['status'], 'files': files, 'artifacts': arts,
                                   'dependency_graph': state['dependency_graph']}
    draft = api('tasks.get_by_id', task=d['stages']['draft']['id'])['task']
    model = api('models.get_by_id', model=d['stages']['model']['id'])['model']
    assert draft['status'] == 'created' and draft['type'] == 'testing'
    assert not draft.get('execution', {}).get('queue') and not draft.get('last_worker')
    assert model['task'] == draft['id']
    assert any(x['model'] == model['id'] for x in draft['models']['output'])
    result['model'] = {'id': model['id'], 'task': model['task'], 'task_status': draft['status'],
                       **download(model['uri'], E / 'sdk-model-download.json')}
    assert (E / 'sdk-model-download.json').read_bytes() == (E / 'payload/TEST_FIXTURE_NOT_TRAINED_WEIGHTS.json').read_bytes()
    dump(E / 'sdk-verification.json', result)
    dump(E / 'inventory-after-sdk.json', current)
    compare_inventory(current)
    print(json.dumps(result, ensure_ascii=False))

def history():
    before = json.loads((E / 'inventory-before.json').read_text())
    result = []
    for id_, task in before['tasks'].items():
        for art in task.get('execution', {}).get('artifacts', []):
            local = E / ('historical-' + id_ + '-' + art['key'] + '.bin')
            record = download(art['uri'], local)
            assert record['sha256'] == art['hash'] and record['bytes'] == art['content_size']
            if id_ == 'd13dc5bcdbc248f0bb80509eb66b9b36':
                assert local.read_bytes() == (R / 'tests/smoke/expected.json').read_bytes()
            result.append({'task': id_, 'key': art['key'], **record})
    dump(E / 'historical-artifact-check.json', {'pass': True, 'checks': result,
                                               'timing': 'After fixture creation; baseline is pre-write registered hash and fixed Smoke file'})
    print('PASS historical Artifact bytes match pre-write hashes:', len(result))


def assets():
    d = readledger()
    out = {}
    for key in ('v1', 'v2', 'draft'):
        id_ = d['stages'][key]['id']
        task = api('tasks.get_by_id', task=id_)['task']
        log = api('events.get_task_log', task=id_, batch_size=1000, order='asc')
        plots = api('events.get_task_plots', task=id_, iters=1)
        assert log['returned'] == log['total'] < 1000
        assert plots['returned'] == plots['total']
        out[key] = {'task': id_, 'artifacts': task['execution'].get('artifacts', []),
                    'log_response': log, 'plots_response': plots,
                    'configuration': task.get('configuration', {}), 'runtime': task.get('runtime', {})}
    d['ancillary_assets'] = {k: {'task': v['task'], 'artifact_keys': [a['key'] for a in v['artifacts']],
                                  'logs': len(v['log_response']['events']), 'plots': len(v['plots_response']['plots'])}
                             for k, v in out.items()}
    saveledger(d)
    dump(E / 'ancillary-assets.json', out)
    print(json.dumps(d['ancillary_assets']))


def compare_inventory(current=None):
    d = readledger()
    before = json.loads((E / 'inventory-before.json').read_text())
    current = current or inventory()
    for kind in ('projects', 'tasks', 'models'):
        assert set(current[kind]) - set(before[kind]) == set(d['objects'][kind]), kind
        for id_, obj in before[kind].items():
            assert obj == current[kind][id_], ('Historical object changed', kind, id_)
    assert current['queues'] == before['queues'], 'Queue changed'
    assert current['preferences_sha256'] == before['preferences_sha256'], 'Preferences changed'
    assert len(d['objects']['tasks']) == 3 and len(d['objects']['models']) == 1
    dump(E / 'inventory-after.json', current)
    dump(E / 'inventory-comparison.json', {'pass': True, 'new_ids': d['objects'], 'historical_objects_unchanged': True,
                                         'queues_unchanged': True, 'preferences_unchanged': True})
    print('PASS exact ID ledger delta; historical full objects, queues and preferences unchanged')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'create', 'verify', 'history', 'assets', 'compare'])
    args = parser.parse_args()
    {'prepare': prepare, 'create': create, 'verify': verify, 'history': history, 'assets': assets, 'compare': compare_inventory}[args.action]()
