"""Isolated HTTP and idempotency tests. These tests never call the live ClearML."""

import base64
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import socket
import sys
import tempfile
from threading import Thread
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integrations/data_entry'))
import common
import operations
import server


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__('127.0.0.1:18080', timeout=10)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(10)
        self.sock.connect(self.path)


class AdapterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='t02b-test-')
        self.addCleanup(temp.cleanup)
        state = Path(temp.name)
        for name in ('requests', 'selections'):
            (state / name).mkdir()
        self.enterContext(patch.object(common, 'STATE', state))
        self.enterContext(patch.object(server, 'STATE', state))
        self.enterContext(patch.object(server, 'CONFIG', {'project': 'isolated-test'}))

        def authenticate(handler):
            who = handler.headers.get('X-Test-User')
            if not who:
                raise common.Rejected('login required', 401)
            return {'id': who, 'name': who}, 'isolated-test-session'

        self.enterContext(patch.object(server.Handler, 'identity', authenticate))
        self.sock = str(state / 'test.sock')
        service = server.Server(self.sock, server.Handler)
        self.addCleanup(service.server_close)
        worker = Thread(target=service.serve_forever, daemon=True)
        worker.start()
        self.addCleanup(service.shutdown)
        self.raw = b'{"messages":[{"role":"user","content":"one"},{"role":"assistant","content":"answer"}]}\n' \
                   b'{"messages":[{"role":"user","content":"two"},{"role":"assistant","content":"answer"}]}\n'

    def request(self, path, body=None, user='owner', origin='http://127.0.0.1:18080'):
        connection = UnixConnection(self.sock)
        headers = {'Origin': origin, 'X-TieSheAI-Request': '1', 'Content-Type': 'application/json'}
        if user:
            headers['X-Test-User'] = user
        try:
            connection.request('GET' if body is None else 'POST', '/data-entry/api/' + path,
                               None if body is None else json.dumps(body), headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def payload(self, raw=None):
        return {'request_id': str(uuid4()), 'filename': 'conversations.jsonl',
                'synthetic_fixture': False,
                'content_base64': base64.b64encode(self.raw if raw is None else raw).decode()}

    def test_rejects_unauthenticated_and_cross_origin(self):
        with patch.object(server, 'sdk') as sdk:
            self.assertEqual(self.request('bootstrap', user=None)[0], 401)
            self.assertEqual(self.request('upload', self.payload(), origin='https://example.invalid')[0], 403)
            sdk.assert_not_called()

    def test_rejects_invalid_uploads_without_creating_record(self):
        with patch.object(server, 'sdk') as sdk:
            for raw, code in [(b'', 400), (b'{broken\n', 422), (b'{"messages":"wrong"}\n', 422),
                              (b'x' * (common.MAX_FILE + 1), 413)]:
                with self.subTest(expected=code):
                    body = self.payload(raw)
                    self.assertEqual(self.request('upload', body)[0], code)
                    self.assertFalse(common.request_path(body['request_id']).exists())
            sdk.assert_not_called()

    def test_double_upload_is_one_sdk_mutation(self):
        body = self.payload()

        def register(data, owner, token):
            path, record = common.owned(data['request_id'], owner)
            record.update(status='uploaded', input_dataset_id='one-dataset')
            common.write(path, record)
            return record

        with patch.object(server, 'sdk', side_effect=register) as sdk:
            with ThreadPoolExecutor(2) as executor:
                results = list(executor.map(lambda _: self.request('upload', body), range(2)))
            self.assertEqual([status for status, _ in results], [200, 200])
            self.assertEqual(results[0][1], results[1][1])
            self.assertEqual(self.request('upload', body)[1]['input_dataset_id'], 'one-dataset')
            self.assertEqual(self.request('upload', body, user='another')[0], 403)
            different = {**body, 'filename': 'other.jsonl'}
            self.assertEqual(self.request('upload', different)[0], 409)
            self.assertEqual(self.request('bootstrap', user='another')[1]['requests'], [])
            sdk.assert_called_once()

    def test_submit_retry_uses_recorded_task_and_parameters(self):
        body = {'request_id': str(uuid4()), 'seed': 73, 'validation_fraction': 0.34}
        path = common.request_path(body['request_id'])
        record = {'owner': 'owner', 'submitted': True, 'processing_task_id': 'one-task',
                  'submitted_parameters': common.params(body)}
        common.write(path, record)
        with patch.object(operations, 'status', return_value=record) as status:
            with patch.object(operations.Task, 'enqueue') as enqueue:
                self.assertEqual(operations.submit(body, 'owner')['processing_task_id'], 'one-task')
                with self.assertRaises(common.Rejected):
                    operations.submit({**body, 'seed': 74}, 'owner')
                enqueue.assert_not_called()
                status.assert_called_once()

    def test_ambiguous_submission_and_invalid_params_rejected(self):
        body = {'request_id': str(uuid4()), 'seed': 42, 'validation_fraction': 0.25}
        common.write(common.request_path(body['request_id']), {'owner': 'owner', 'pending': 'enqueue'})
        with patch.object(operations.Task, 'enqueue') as enqueue:
            with self.assertRaisesRegex(common.Rejected, '待核对'):
                operations.submit(body, 'owner')
            for options in [{'seed': True}, {'seed': 1.5}, {'seed': 2**31}, {'validation_fraction': 1},
                            {'validation_fraction': float('nan')}]:
                with self.assertRaises(common.Rejected):
                    operations.submit({**body, **options}, 'owner')
            enqueue.assert_not_called()

    def test_queue_busy_and_worker_unavailable(self):
        worker = {'id': 'tiesheai-rail-cpu:cpu0', 'queues': [{'id': 'rail-id'}]}
        queue = {'id': 'rail-id', 'entries': []}
        self.assertEqual(common.ensure_idle([queue], [worker], []), 'rail-id')
        for queues, workers, active in [
            ([{**queue, 'entries': ['existing-task']}], [worker], []),
            ([queue], [{**worker, 'task': 'existing-task'}], []),
            ([queue], [worker], [{'execution': {'queue': 'rail-id'}}]),
            ([queue], [], []),
        ]:
            with self.assertRaises(common.Rejected):
                common.ensure_idle(queues, workers, active)

    def test_snapshot_reuses_core_and_has_no_fixture_ledger_path(self):
        source = common.snapshot()
        compile(source, 'data_prepare.py', 'exec')
        self.assertTrue(source.startswith(common.CORE_PATH.read_text().split('\ndef agent_main():')[0]))
        self.assertNotIn('ledger_path', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
