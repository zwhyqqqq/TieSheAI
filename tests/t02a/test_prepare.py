"""Contract, failure atomicity, deterministic splitting, dedup/source leakage checks."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('prepare', ROOT / 'integrations/data_preparation/prepare.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)


def row(n, source=None):
    r = {'id': str(n), 'messages': [{'role': 'user', 'content': 'SYNTHETIC 测试问题 ' + str(n)},
                                  {'role': 'assistant', 'content': 'SYNTHETIC 测试答案 ' + str(n)}]}
    if source is not None:
        r['source_id'] = source
    return r


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input = self.root / 'input.jsonl'

    def run_rows(self, rows, name='output', **kwargs):
        self.input.write_bytes(b''.join(p.encoded(x) for x in rows))
        output = self.root / name
        manifest, stats = p.prepare(self.input, output, **kwargs)
        return output, manifest, stats

    def reject(self, raw):
        self.input.write_bytes(raw)
        with self.assertRaises(p.ContractError):
            p.prepare(self.input, self.root / 'bad')
        self.assertFalse((self.root / 'bad').exists())

    def test_valid_multi_turn_system_and_unicode(self):
        a = row(1)
        a['messages'].insert(0, {'role': 'system', 'content': '合成测试，不是专业知识'})
        a['messages'] += row(2)['messages']
        output, manifest, stats = self.run_rows([a, row(3)])
        self.assertEqual(stats['unique_records'], 2)
        self.assertEqual(set(x.name for x in output.iterdir()), set(p.FILES))
        self.assertEqual(manifest['input']['sha256'], p.sha(self.input.read_bytes()))
        for name, item in manifest['outputs'].items():
            self.assertEqual(item, {'sha256': p.sha((output / name).read_bytes()), 'bytes': (output / name).stat().st_size})
        self.assertEqual(manifest['code_sha256'], p.sha(Path(p.__file__).read_bytes()))

    def test_invalid_json_fields_and_roles(self):
        bad = [b'{\n', b'[]\n', b'null\n', b'{"messages":null}\n', b'\n', b'', b'\xef\xbb\xbf{}\n', b'\xff\n',
               b'{"messages":[],"messages":[]}\n', b'{"messages":NaN}\n']
        for raw in bad:
            with self.subTest(raw=raw):
                self.reject(raw)
        for mutation in ('missing', 'extra', 'role', 'tool', 'empty', 'whitespace', 'notstring', 'turns', 'enduser', 'systemmiddle', 'ids', 'source', 'surrogate'):
            r = row(1)
            if mutation == 'missing': del r['messages']
            if mutation == 'extra': r['document'] = 'not an answer'
            if mutation == 'role': r['messages'][0]['role'] = 'assistant'
            if mutation == 'tool': r['messages'][0]['role'] = 'tool'
            if mutation == 'empty': r['messages'][1]['content'] = ''
            if mutation == 'whitespace': r['messages'][1]['content'] = '\t \n'
            if mutation == 'notstring': r['messages'][1]['content'] = 7
            if mutation == 'turns': r['messages'][1]['role'] = 'user'
            if mutation == 'enduser': r['messages'] += [r['messages'][0]]
            if mutation == 'systemmiddle': r['messages'][1]['role'] = 'system'
            if mutation == 'ids': r['id'] = ''
            if mutation == 'source': r['source_id'] = []
            if mutation == 'surrogate': r['messages'][1]['content'] = '\ud800'
            with self.subTest(mutation=mutation):
                self.reject((json.dumps(r) + '\n').encode())

    def test_mixed_invalid_records_fail_without_output(self):
        self.reject(p.encoded(row(1)) + b'{bad}\n' + p.encoded(row(2)))
        self.reject(p.encoded(row(1)) + b'\n' + p.encoded(row(2)))
        self.reject(p.encoded(row(1)) * 2 + p.encoded(row(2)))  # duplicate ID

    def test_deduplication_and_transitive_source_isolation(self):
        rows = [row(1, 'A'), row(2, 'A'), row(3, 'B'), row(4, 'C'), row(5, 'D')]
        duplicate = copy.deepcopy(rows[1]); duplicate.update(id='duplicate', source_id='B')
        rows += [duplicate]
        output, _, stats = self.run_rows(rows)
        self.assertEqual((stats['input_records'], stats['unique_records'], stats['duplicates_removed']), (6, 5, 1))
        self.assertEqual(stats['groups'], 3)
        mapping = [json.loads(x) for x in (output / 'sources.jsonl').read_text().splitlines()]
        splits = {}
        for r in mapping:
            for o in r['occurrences']:
                splits.setdefault(o['source_id'], set()).add(r['split'])
        self.assertTrue(all(len(x) == 1 for x in splits.values()))
        self.assertEqual(splits['A'], splits['B'])
        train, val = [{p.sha(p.encoded(json.loads(x))) for x in (output / f).read_text().splitlines()} for f in ('train.jsonl', 'validation.jsonl')]
        self.assertTrue(train and val)
        self.assertFalse(train & val)

    def test_reproducible_and_seed_changes(self):
        rows = [row(i) for i in range(24)]
        a, _, _ = self.run_rows(rows, 'a', seed=42)
        b, _, _ = self.run_rows(rows, 'b', seed=42)
        c, _, _ = self.run_rows(rows, 'c', seed=13)
        for name in p.FILES:
            self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
        self.assertNotEqual((a / 'validation.jsonl').read_bytes(), (c / 'validation.jsonl').read_bytes())
        d, _, _ = self.run_rows(list(reversed(rows)), 'd', seed=42)
        self.assertEqual((a / 'train.jsonl').read_bytes(), (d / 'train.jsonl').read_bytes())

    def test_exact_content_semantics(self):
        a, b, c = row(1), row(2), row(3)
        b['messages'] = copy.deepcopy(a['messages'])
        c['messages'] = copy.deepcopy(a['messages']); c['messages'][1]['content'] += ' '
        _, _, stats = self.run_rows([a, b, c])
        self.assertEqual(stats['unique_records'], 2)

    def test_unsplittable_inputs_and_parameters(self):
        for rows in ([row(1)], [row(1, 'same'), row(2, 'same')]):
            with self.assertRaises(p.ContractError): self.run_rows(rows)
        for fraction in (0, 1, -0.5, float('nan'), float('inf')):
            with self.subTest(fraction=fraction), self.assertRaises(p.ContractError):
                self.run_rows([row(1), row(2)], validation_fraction=fraction)
        with self.assertRaises(p.ContractError): self.run_rows([row(1), row(2)], seed='42')

    def test_cli_exit_and_no_overwrite(self):
        self.input.write_bytes(b'{bad}\n')
        cmd = [sys.executable, '-B', str(Path(p.__file__)), '--input', str(self.input), '--output', str(self.root / 'out')]
        r = subprocess.run(cmd, capture_output=True)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stderr)['status'], 'failed')
        self.input.write_bytes(p.encoded(row(1)) + p.encoded(row(2)))
        r = subprocess.run(cmd, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        before = (self.root / 'out/manifest.json').read_bytes()
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
        self.assertEqual(before, (self.root / 'out/manifest.json').read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
