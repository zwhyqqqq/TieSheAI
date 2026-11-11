"""TieSheAI conversation-v1 CPU preparation; stdlib CLI and Agent entry point.

No ClearML import or server mutation occurs in local mode. The complete file can
be stored in Task.script.diff; it has no repository-local import dependencies.
"""
import argparse
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile

CONTRACT = 'tiesheai.conversation.v1'
COMPONENT_VERSION = '1.0.0'
FILES = ('train.jsonl', 'validation.jsonl', 'sources.jsonl', 'statistics.json', 'manifest.json')


class ContractError(ValueError):
    """Invalid input. No records are silently discarded."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def write_json(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_bytes(encoded(obj))
    tmp.replace(path)


def strict_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ContractError('duplicate JSON key')
        obj[key] = value
    return obj


def validate(row):
    if not isinstance(row, dict) or set(row) - {'messages', 'id', 'source_id'}:
        raise ContractError('object with only messages, optional id/source_id required')
    for key in ('id', 'source_id'):
        if key in row and (not isinstance(row[key], str) or not row[key].strip()):
            raise ContractError(key + ' must be a nonblank string')
        if key in row:
            row[key].encode('utf-8')
    messages = row.get('messages')
    if not isinstance(messages, list) or len(messages) < 2:
        raise ContractError('messages must contain user/assistant turns')
    for m in messages:
        if not isinstance(m, dict) or set(m) != {'role', 'content'}:
            raise ContractError('each message requires exactly role and content')
        if m['role'] not in ('system', 'user', 'assistant'):
            raise ContractError('unsupported role')
        if not isinstance(m['content'], str) or not m['content'].strip():
            raise ContractError('content must be a nonblank string')
        try:
            m['content'].encode('utf-8')
        except UnicodeEncodeError:
            raise ContractError('unpaired Unicode surrogate') from None
    turns = messages[1:] if messages[0]['role'] == 'system' else messages
    if len(turns) < 2 or len(turns) % 2 or any(
        m['role'] != ('user' if i % 2 == 0 else 'assistant') for i, m in enumerate(turns)
    ):
        raise ContractError('optional first system, then alternating user/assistant; end assistant')
    return {'messages': messages}


def environment():
    packages = {}
    for name in ('clearml', 'clearml-agent'):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(),
            'platform': platform.platform(), 'packages': packages}


def prepare(input_file, output_dir, seed=42, validation_fraction=0.25, provenance=None):
    """Validate all lines; dedup by messages; union source groups; deterministic split.

    Exact means canonical JSON messages equality (key order ignored). Text, turn
    order and whitespace within strings are preserved. Duplicate occurrences can
    bridge multiple source groups, which are united before splitting.
    """
    if type(seed) is not int or not isinstance(validation_fraction, (float, int)) or not 0 < validation_fraction < 1:
        raise ContractError('integer seed and finite 0 < validation_fraction < 1 required')
    input_file, output_dir = Path(input_file), Path(output_dir)
    if output_dir.exists():
        raise ContractError('output directory already exists; choose a new path')
    raw = input_file.read_bytes()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        raise ContractError('input must be UTF-8 without BOM') from None
    if text.startswith('\ufeff'):
        raise ContractError('UTF-8 BOM is not supported')
    unique, ids, errors, rows = {}, set(), [], 0
    lines = text.split('\n')
    for line_no, line in enumerate(lines, 1):
        if line == '' and line_no == len(lines):
            continue  # optional final LF, never skip an interior blank record
        rows += 1
        try:
            row = json.loads(line, object_pairs_hook=strict_object,
                             parse_constant=lambda _: (_ for _ in ()).throw(ContractError('nonfinite JSON number')))
            sample = validate(row)
            if 'id' in row:
                if row['id'] in ids:
                    raise ContractError('id must be unique within the input')
                ids.add(row['id'])
            identity = sha(encoded(sample))
            entry = unique.setdefault(identity, {'sample': sample, 'occurrences': []})
            entry['occurrences'].append({'line': line_no, 'id': row.get('id'), 'source_id': row.get('source_id')})
        except (ValueError, TypeError, UnicodeError, RecursionError):
            # Do not copy private training content into validation error logs.
            errors.append({'line': line_no, 'error': 'invalid JSON or conversation-v1 fields/turns'})
    if errors:
        raise ContractError(json.dumps({'invalid_records': len(errors), 'errors': errors}, ensure_ascii=False))
    if not unique:
        raise ContractError('input contains no conversations')
    parent = {k: k for k in unique}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a, b):
        a, b = find(a), find(b)
        parent[max(a, b)] = min(a, b)

    owners = {}
    for identity, entry in sorted(unique.items()):
        for occurrence in entry['occurrences']:
            source = occurrence['source_id']
            if source is not None:
                if source in owners:
                    union(identity, owners[source])
                owners[source] = identity
    groups = {}
    for identity in sorted(unique):
        groups.setdefault(find(identity), []).append(identity)
    if len(groups) < 2:
        raise ContractError('need at least two independent groups for nonempty disjoint splits')
    # Group fraction, not row fraction. A source group is never broken to meet a target.
    ordered = sorted(groups, key=lambda k: (sha(encoded([seed, groups[k]])), k))
    nval = max(1, min(len(groups) - 1, math.floor(len(groups) * validation_fraction + 0.5)))
    validation_groups = set(ordered[:nval])
    assignments = {k: ('validation' if find(k) in validation_groups else 'train') for k in unique}
    outputs = {}
    for split in ('train', 'validation'):
        outputs[split + '.jsonl'] = b''.join(encoded(unique[k]['sample']) for k in sorted(unique) if assignments[k] == split)
    mapping = [{'sample_sha256': k, 'split': assignments[k], 'group_sha256': sha(encoded(groups[find(k)])),
                'occurrences': unique[k]['occurrences']} for k in sorted(unique)]
    outputs['sources.jsonl'] = b''.join(encoded(x) for x in mapping)
    counts = Counter(assignments.values())
    stats = {'synthetic_fixture': bool((provenance or {}).get('synthetic_fixture', False)),
             'input_records': rows, 'valid_records': rows, 'invalid_records': 0,
             'unique_records': len(unique), 'duplicates_removed': rows - len(unique),
             'groups': len(groups), 'train_groups': len(groups) - nval, 'validation_groups': nval,
             'train_records': counts['train'], 'validation_records': counts['validation'],
             'actual_validation_fraction': counts['validation'] / len(unique)}
    outputs['statistics.json'] = encoded(stats)
    manifest = {'contract_version': CONTRACT, 'component_version': COMPONENT_VERSION,
                'code_sha256': sha(Path(__file__).read_bytes()), 'environment': environment(),
                'input': {'name': input_file.name, 'bytes': len(raw), 'sha256': sha(raw), **(provenance or {})},
                'parameters': {'seed': seed, 'validation_fraction': validation_fraction,
                               'split_unit': 'connected source groups after exact deduplication',
                               'deduplication': 'SHA256 of canonical messages JSON with LF'},
                'outputs': {k: {'bytes': len(v), 'sha256': sha(v)} for k, v in sorted(outputs.items())}}
    outputs['manifest.json'] = encoded(manifest)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.prepare-', dir=output_dir.parent))
    try:
        for name, content in outputs.items():
            (staging / name).write_bytes(content)
        staging.rename(output_dir)
    except BaseException:
        shutil.rmtree(staging)
        raise
    return manifest, stats


def agent_main():
    if not os.environ.get('CLEARML_TASK_ID') or not os.environ.get('CLEARML_WORKER_ID'):
        raise RuntimeError('existing CPU Agent context required')
    from clearml import Dataset, Task
    task = Task.init(task_type=Task.TaskTypes.data_processing, reuse_last_task_id=False,
                     auto_connect_frameworks=False, auto_resource_monitoring=False)
    if Task.running_locally() or os.environ.get('CUDA_VISIBLE_DEVICES') not in ('', '-1', 'none'):
        raise RuntimeError('remote CPU-only execution required')
    params = task.connect({'input_dataset_id': '', 'input_dataset_version': '1.0.0',
                           'input_sha256': '', 'input_filename': 'conversations.jsonl',
                           'seed': 42, 'validation_fraction': 0.25, 'output_version': '1.0.0',
                           'project': '', 'fileserver': '', 'ledger_path': '',
                           'synthetic_fixture': True, 'expected_code_sha256': ''}, name='Preparation')
    if sha(Path(__file__).read_bytes()) != params['expected_code_sha256']:
        raise RuntimeError('Agent source hash mismatch')
    runtime = {'worker_id': os.environ['CLEARML_WORKER_ID'], 'python_executable': sys.executable,
               'running_locally': Task.running_locally(), 'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'),
               'code_sha256': sha(Path(__file__).read_bytes())}
    task.connect(runtime, name='Execution', ignore_remote_overrides=True)
    print('T02A_AGENT_EXECUTION ' + json.dumps(runtime, sort_keys=True), flush=True)
    # This ledger is local operational evidence on the current host, not a code dependency.
    ledger_path = Path(params['ledger_path'])
    ledger = json.loads(ledger_path.read_text())
    if ledger['project'] != params['project'] or ledger['processing_task_id'] != task.id:
        raise RuntimeError('ledger/task ownership mismatch')
    ds = Dataset.get(dataset_id=params['input_dataset_id'])
    if not ds.is_final() or ds._dataset_version != params['input_dataset_version']:
        raise RuntimeError('final input Dataset/version required')
    filename = params['input_filename']
    if filename != Path(filename).name or filename not in ds.list_files():
        raise ContractError('input filename must be a Dataset root file')
    local = Path(ds.get_local_copy(use_soft_links=False, max_workers=1)) / filename
    if sha(local.read_bytes()) != params['input_sha256']:
        raise ContractError('input Dataset content SHA256 mismatch')
    with tempfile.TemporaryDirectory(prefix='tiesheai-t02a-') as directory:
        output = Path(directory) / 'prepared'
        manifest, stats = prepare(local, output, int(params['seed']), float(params['validation_fraction']),
                                  {'dataset_id': ds.id, 'dataset_version': params['input_dataset_version'],
                                   'processing_task_id': task.id, 'synthetic_fixture': params['synthetic_fixture']})
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                task.get_logger().report_scalar('preparation', key, value=value, iteration=0)
        print('T02A_STATISTICS ' + json.dumps(stats, sort_keys=True), flush=True)
        for name in ('manifest.json', 'statistics.json'):
            content = (output / name).read_bytes()
            if not task.upload_artifact(name, artifact_object=output / name,
                                        metadata={'sha256_before_upload': sha(content)}, wait_on_upload=True):
                raise RuntimeError('report upload failed')
        # Reserve before creation; ambiguous pending creation is never retried blindly.
        ledger = json.loads(ledger_path.read_text())
        if ledger.get('output_dataset_id') or ledger.get('pending'):
            raise RuntimeError('output already exists or pending: inspect ledger; do not recreate')
        ledger['pending'] = 'output_dataset'
        write_json(ledger_path, ledger)
        out_ds = Dataset.create(dataset_project=params['project'], dataset_name='prepared-conversations',
                                dataset_version=params['output_version'], use_current_task=False,
                                output_uri=params['fileserver'], dataset_tags=['T02-A', 'SYNTHETIC_FUNCTIONAL_TEST'],
                                description='CPU-prepared conversation-v1; synthetic functional test, not a model training run.')
        ledger.update(output_dataset_id=out_ds.id, pending=None)
        write_json(ledger_path, ledger)
        out_ds.set_metadata({'input_dataset_id': ds.id, 'input_dataset_version': params['input_dataset_version'],
                             'processing_task_id': task.id, 'manifest_sha256': sha((output / 'manifest.json').read_bytes())},
                            metadata_name='provenance')
        task.set_parameter('Results/output_dataset_id', out_ds.id)
        task.set_parameter('Results/output_dataset_version', params['output_version'])
        out_ds.add_files(output)
        if out_ds.upload(output_url=params['fileserver'], show_progress=False, max_workers=1) is False:
            raise RuntimeError('output Dataset upload failed')
        if not out_ds.finalize():
            raise RuntimeError('output Dataset finalize failed')
        out_ds._task.close()
        print('T02A_OUTPUT_DATASET ' + out_ds.id, flush=True)
        for name in FILES:
            content = (output / name).read_bytes()
            print('T02A_OUTPUT_HASH ' + json.dumps({'name': name, 'bytes': len(content), 'sha256': sha(content)}), flush=True)
    print('T02A_PREPARATION_OK', flush=True)
    task.flush(wait_for_uploads=True)
    task.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', action='store_true')
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--validation-fraction', type=float, default=0.25)
    args = parser.parse_args()
    if args.agent:
        agent_main()
    else:
        if not args.input or not args.output:
            parser.error('--input and --output required in local mode')
        try:
            _, stats = prepare(args.input, args.output, args.seed, args.validation_fraction)
        except (ContractError, OSError) as exc:
            print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
            return 2
        print(json.dumps({'status': 'completed', 'statistics': stats}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    if os.environ.get('CLEARML_TASK_ID') and os.environ.get('CLEARML_WORKER_ID'):
        agent_main()
    else:
        sys.exit(main())
