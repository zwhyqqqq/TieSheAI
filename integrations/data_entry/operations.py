"""One SDK process per authenticated request. No shared Session or server keys."""
import base64
import io
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit
import zipfile

import requests

from common import API, FILES, PYTHON, STATE, CORE_PATH, core, digest, write, owned, snapshot, ensure_idle, params, Rejected
from clearml import Dataset, Task
from clearml.backend_api.session import Session

SESSION = None


def api(service, action, **body):
    global SESSION
    SESSION = SESSION or Session()
    response = SESSION.send_request(service, action, json=body)
    if response.status_code in (401, 403):
        raise Rejected('会话过期或当前用户无权访问此资产', response.status_code)
    response.raise_for_status()
    result = response.json()
    if result['meta']['result_code'] != 200:
        raise Rejected('ClearML 拒绝此操作', 409)
    return result['data']


def reserve(path, record, stage):
    if record.get('pending'):
        raise Rejected('上次创建结果不明，请核对请求台账后处理；不会重复创建', 409)
    record.update(pending=stage, error=None)
    write(path, record)


def remember(path, record, **fields):
    record.update(fields, pending=None)
    write(path, record)


def upload(data, user):
    path, record = owned(data['request_id'], user)
    if record.get('input_dataset_id') and record.get('status') != 'uploading':
        return record
    reserve(path, record, 'input_dataset')
    ds = Dataset.create(dataset_project=record['project'], dataset_name=record['request_id']+'-input',
                        dataset_version='1.0.0', use_current_task=False, output_uri=FILES,
                        dataset_tags=['T02-B','conversation-v1'], description=record['filename'])
    remember(path, record, input_dataset_id=ds.id, input_version='1.0.0')
    # Keep upload pending until finalize: interruption cannot silently report success.
    record['pending'] = 'input_upload'; write(path, record)
    with tempfile.TemporaryDirectory(prefix='data-entry-upload-') as directory:
        file = Path(directory) / 'conversations.jsonl'
        file.write_bytes(base64.b64decode(data['content_base64'], validate=True))
        ds.add_files(file)
        if ds.upload(output_url=FILES, show_progress=False, max_workers=1) is False or not ds.finalize():
            raise RuntimeError('input upload/finalize failed')
        ds._task.close()
    remember(path, record, status='uploaded')
    return record


def submit(data, user):
    path, record = owned(data['request_id'], user)
    options = params(data)
    if record.get('submitted_parameters') and options != record['submitted_parameters']:
        raise Rejected('同一请求的处理参数已经固定，请新建上传后修改', 409)
    if record.get('submitted'):
        return status(data, user)
    if record.get('pending'):
        raise Rejected('操作结果待核对，不会重复创建或入队', 409)
    if record['status'] not in ('uploaded', 'created'):
        raise Rejected('请先成功上传数据', 409)
    # Validate split under the final user parameters before creating a processing Task.
    source = Dataset.get(dataset_id=record['input_dataset_id'])
    local = Path(source.get_local_copy(use_soft_links=False, max_workers=1)) / 'conversations.jsonl'
    with tempfile.TemporaryDirectory(prefix='data-entry-validate-') as directory:
        core.prepare(local, Path(directory)/'check', **options)
    queue = ensure_idle(api('queues','get_all',name='^rail-cpu$')['queues'],
                        api('workers','get_all',last_seen=120)['workers'],
                        api('tasks','get_all',status=['in_progress'],search_hidden=True)['tasks'])
    if not record.get('processing_task_id'):
        reserve(path, record, 'processing_task')
        task = Task.create(project_name=record['project'], task_name=record['filename']+' CPU preparation',
                           task_type=Task.TaskTypes.data_processing, detect_repository=False,
                           packages=['clearml==2.1.12'], add_task_init_call=False)
        remember(path, record, processing_task_id=task.id, submitted_parameters=options, status='created')
    task = Task.get_task(task_id=record['processing_task_id'])
    if str(task.status) != 'created':
        raise Rejected('任务状态已变化，请刷新核对，禁止重复入队', 409)
    code = snapshot()
    code_hash = digest(code.encode())
    task.set_script(repository='', branch='', commit='', diff=code, entry_point='data_prepare.py', working_dir='.', binary=PYTHON)
    values = {**options, 'input_dataset_id': source.id, 'input_dataset_version': source.version,
              'input_sha256': record['input_sha256'], 'project': record['project'], 'fileserver': FILES,
              'request_id': record['request_id'], 'synthetic_fixture': record['synthetic_fixture'],
              'expected_code_sha256': code_hash, 'core_sha256': digest(CORE_PATH.read_bytes())}
    task.set_parameters({'Preparation/'+k:v for k,v in values.items()})
    task.set_tags(['T02-B', 'conversation-v1', record['request_id']])
    # Recheck under the adapter's queue lock directly before enqueue.
    ensure_idle(api('queues','get_all',name='^rail-cpu$')['queues'],
                api('workers','get_all',last_seen=120)['workers'],
                api('tasks','get_all',status=['in_progress'],search_hidden=True)['tasks'])
    record.update(queue_id=queue, code_sha256=code_hash)
    reserve(path, record, 'enqueue')
    Task.enqueue(task, queue_id=queue)
    remember(path, record, submitted=True, status='queued')
    return record


def status(data, user):
    path, record = owned(data['request_id'], user)
    if record.get('processing_task_id'):
        task = api('tasks','get_by_id',task=record['processing_task_id'])['task']
        record.update(status=task['status'], task_project=task['project'])
        if record.get('pending') == 'enqueue' and task['status'] in ('queued', 'in_progress', 'completed', 'failed', 'stopped'):
            record.update(submitted=True, pending=None)
        if record['status'] in ('failed','stopped','closed'):
            record['error'] = task.get('status_message') or task.get('status_reason') or 'CPU处理未完成，请查看日志'
        parameters = {section+'/'+name:val.get('value') for section, items in task.get('hyperparams',{}).items() for name,val in items.items()}
        out = parameters.get('Results/output_dataset_id')
        if out:
            record.update(output_dataset_id=out, output_version=parameters.get('Results/output_dataset_version'),
                          manifest_sha256=parameters.get('Results/manifest_sha256'))
        if record['status'] == 'completed':
            if not out or parameters.get('Results/output_creation') != 'final':
                record.update(status='needs_review', error='任务结束但输出未完整封存，请核对原生任务')
            else:
                try:
                    assets = output(out)
                    if (assets['manifest_sha256'] != record['manifest_sha256']
                            or assets['version'] != record['output_version']
                            or assets['input'].get('processing_task_id') != task['id']):
                        raise Rejected('输出版本、来源或 manifest 不匹配', 409)
                    record.update(statistics=assets['statistics'], error=None)
                except Rejected as error:
                    record.update(status='needs_review', error=str(error))
        write(path, record)
    return record


def output(oid, archive=False):
    # Authenticate the Task lookup as the current user before reading its artifact.
    task = api('tasks', 'get_by_id', task=oid)['task']
    if ('dataset' not in task.get('system_tags', [])
            or task['status'] not in ('completed', 'published', 'closed')
            or not {'T02-A', 'T02-B'}.intersection(task.get('tags', []))):
        raise Rejected('不是已完成的对话数据准备输出', 409)
    version = task.get('hyperparams', {}).get('properties', {}).get('version', {}).get('value')
    chunks = [item for item in task['execution']['artifacts'] if item['key'] == 'data']
    if not version or len(chunks) != 1:
        raise Rejected('本入口仅支持已登记版本的单归档结果', 409)
    artifact = chunks[0]
    uri = urlsplit(artifact['uri'])
    size = artifact['content_size']
    if (uri.scheme != 'http' or uri.netloc != urlsplit(FILES).netloc
            or uri.query or uri.fragment or not uri.path.endswith('.zip')
            or not 0 < size <= 4 * 1024 * 1024):
        raise Rejected('归档来源或大小不兼容', 409)
    with requests.get(artifact['uri'], headers={'Authorization': 'Bearer ' + SESSION.token},
                      timeout=20, allow_redirects=False, stream=True) as response:
        if response.status_code != 200:
            raise Rejected('当前用户无法读取数据归档', 409)
        raw = response.raw.read(size + 1)
    if len(raw) != size or digest(raw) != artifact['hash']:
        raise Rejected('数据归档大小或哈希不一致', 409)
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
            if (sorted(zipped.namelist()) != sorted(core.FILES)
                    or sum(item.file_size for item in zipped.infolist()) > 20 * 1024 * 1024):
                raise Rejected('归档结构或大小不兼容', 409)
            manifest_bytes = zipped.read('manifest.json')
            manifest = json.loads(manifest_bytes)
            if (manifest.get('contract_version') != core.CONTRACT
                    or set(manifest.get('outputs', {})) != set(core.FILES) - {'manifest.json'}):
                raise Rejected('不支持的契约或 manifest', 409)
            for name, info in manifest['outputs'].items():
                content = zipped.read(name)
                if digest(content) != info['sha256'] or len(content) != info['bytes']:
                    raise Rejected('结果文件哈希不一致', 409)
            stats = json.loads(zipped.read('statistics.json'))
            if not stats.get('train_records') or not stats.get('validation_records') or stats.get('invalid_records') != 0:
                raise Rejected('训练/验证集不完整', 409)
            provenance = manifest['input']
    except (zipfile.BadZipFile, KeyError, TypeError, AttributeError) as error:
        raise Rejected('结果归档无效', 409) from error
    result = {'id': oid, 'version': version, 'name': task['name'], 'project': task['project'],
              'manifest_sha256': digest(manifest_bytes), 'statistics': stats, 'input': provenance,
              'archive_sha256': digest(raw), 'archive_bytes': len(raw)}
    if archive:
        result['archive_base64'] = base64.b64encode(raw).decode()
    return result


def catalog():
    items = api('tasks','get_all',type=['data_processing'],status=['completed','published','closed'],
                system_tags=['dataset'], tags=['T02-A', 'T02-B'], search_hidden=True, page_size=500)['tasks']
    results = []
    for item in items:
        try: results.append(output(item['id']))
        except (Rejected, KeyError, ValueError): continue
    return {'datasets':results}


def execute(data):
    # Validate identity again inside this isolated SDK session; no shared global credentials.
    user = api('users','get_current_user')['user']['id']
    if user != data['owner']:
        raise Rejected('会话身份不匹配', 403)
    action = data['action']
    if action == 'upload': return upload(data,user)
    if action == 'submit': return submit(data,user)
    if action == 'status': return status(data,user)
    if action == 'catalog': return catalog()
    if action in ('select','archive'):
        item = output(data['dataset_id'], archive=action=='archive')
        if action == 'select':
            selected = {k:item[k] for k in ('id','version','manifest_sha256')}
            write(STATE/'selections'/(digest(user.encode())+'.json'),selected)
            return {'selected':selected}
        return item
    raise Rejected('不支持的操作',404)


if __name__ == '__main__':
    try:
        result = {'ok':True, 'data':execute(json.load(sys.stdin))}
    except Exception as exc:
        # Raw SDK errors remain local; client receives fixed safe feedback.
        import traceback
        traceback.print_exc(file=sys.stderr)
        result = {'ok':False, 'status':getattr(exc,'status',422 if isinstance(exc,core.ContractError) else 409),
                  'error':str(exc) if isinstance(exc,(Rejected,core.ContractError)) else 'ClearML操作失败或结果不明，请刷新查看；不会自动重建任务'}
    print('T02B_RESPONSE '+json.dumps(result,ensure_ascii=False),flush=True)
