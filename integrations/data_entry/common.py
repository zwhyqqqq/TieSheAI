"""Fixed configuration and durable request records for the narrow data-entry adapter."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
STATE = Path(os.environ.get('TIESHEAI_DATA_ENTRY_STATE', ROOT / 'infra/.local/data-entry'))
API = 'http://127.0.0.1:8008'
FILES = 'http://127.0.0.1:8081'
PYTHON = '/root/miniconda3/envs/clearml-backend/bin/python'
MAX_FILE = 1024 * 1024
CORE_PATH = ROOT / 'integrations/data_preparation/prepare.py'
spec = importlib.util.spec_from_file_location('cpu_core', CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class Rejected(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    core.write_json(path, data)


def init_state():
    os.umask(0o077)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    (STATE / 'requests').mkdir(mode=0o700, exist_ok=True)
    (STATE / 'selections').mkdir(mode=0o700, exist_ok=True)
    config = STATE / 'config.json'
    if not config.exists():
        write(config, {'project': 'TieSheAI-T02B-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')})
    sdk = STATE / 'sdk.conf'
    if not sdk.exists():
        sdk.write_text(
            f'api {{ api_server: "{API}", web_server: "http://127.0.0.1:18080", files_server: "{FILES}" }}\n'
            'api.http.retries.total: 0\n'
            'api.http.wait_on_maintenance_forever: false\n'
            f'sdk.development.default_output_uri: "{FILES}"\n'
        )
    return json.loads(config.read_text())


def request_path(request_id):
    if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}', request_id):
        raise Rejected('请求编号无效')
    return STATE / 'requests' / (request_id + '.json')


def params(data):
    seed, fraction = data.get('seed'), data.get('validation_fraction')
    if type(seed) is not int or not -2147483648 <= seed <= 2147483647:
        raise Rejected('seed 必须为32位整数')
    if type(fraction) not in (int, float) or not 0 < fraction < 1:
        raise Rejected('验证组比例必须大于0且小于1')
    return {'seed': seed, 'validation_fraction': float(fraction)}


def snapshot():
    return CORE_PATH.read_text().split('\ndef agent_main():')[0] + '\n' + (Path(__file__).with_name('worker.py')).read_text()


def owned(request_id, user):
    path = request_path(request_id)
    if not path.exists():
        raise Rejected('请求不存在', 404)
    data = json.loads(path.read_text())
    if data['owner'] != user:
        raise Rejected('无权访问该请求', 403)
    return path, data


def ensure_idle(queues, workers, active):
    if len(queues) != 1:
        raise Rejected('未找到唯一的 rail-cpu 队列', 409)
    q = queues[0]
    worker = next((w for w in workers if w['id'] == 'tiesheai-rail-cpu:cpu0'), None)
    if not worker or q['id'] not in [x['id'] for x in worker.get('queues', [])]:
        raise Rejected('CPU Worker 当前不可用，请稍后再试', 409)
    if q.get('entries') or worker.get('task') or any(
        t.get('execution', {}).get('queue') == q['id'] or t.get('last_worker') == worker['id'] for t in active
    ):
        raise Rejected('rail-cpu 正忙，请稍后重试；已有任务不会被修改', 409)
    return q['id']
