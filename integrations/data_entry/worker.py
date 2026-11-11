# Appended to the unchanged T02-A CPU core as a complete Task source snapshot.
def agent_main():
    from clearml import Dataset, Task
    if not os.environ.get('CLEARML_TASK_ID') or not os.environ.get('CLEARML_WORKER_ID'):
        raise RuntimeError('CPU Agent required')
    task = Task.init(task_type=Task.TaskTypes.data_processing, reuse_last_task_id=False,
                     auto_connect_frameworks=False, auto_resource_monitoring=False)
    if Task.running_locally() or os.environ.get('CUDA_VISIBLE_DEVICES') not in ('none', '', '-1'):
        raise RuntimeError('remote CPU context required')
    params = task.connect({'input_dataset_id': '', 'input_dataset_version': '1.0.0', 'input_sha256': '',
                           'seed': 42, 'validation_fraction': 0.25, 'project': '', 'request_id': '',
                           'synthetic_fixture': False, 'expected_code_sha256': '', 'core_sha256': '',
                           'fileserver': ''}, name='Preparation')
    code_hash = sha(Path(__file__).read_bytes())
    if code_hash != params['expected_code_sha256']:
        raise RuntimeError('source snapshot mismatch')
    task.connect({'worker_id': os.environ['CLEARML_WORKER_ID'], 'running_locally': False,
                  'cuda_visible_devices': os.environ.get('CUDA_VISIBLE_DEVICES'), 'code_sha256': code_hash,
                  'python_executable': sys.executable}, name='Execution', ignore_remote_overrides=True)
    print('T02B_AGENT_EXECUTION ' + json.dumps({'task': task.id, 'worker': os.environ['CLEARML_WORKER_ID'], 'code_sha256': code_hash}), flush=True)
    ds = Dataset.get(dataset_id=params['input_dataset_id'], alias='conversation_input')
    if not ds.is_final() or ds.version != params['input_dataset_version']:
        raise ContractError('input Dataset version/final mismatch')
    local = Path(ds.get_local_copy(use_soft_links=False, max_workers=1)) / 'conversations.jsonl'
    if sha(local.read_bytes()) != params['input_sha256']:
        raise ContractError('input content hash mismatch')
    with tempfile.TemporaryDirectory(prefix='tiesheai-data-entry-') as directory:
        output = Path(directory) / 'prepared'
        manifest, stats = prepare(local, output, int(params['seed']), float(params['validation_fraction']),
                                  {'dataset_id': ds.id, 'dataset_version': ds.version, 'processing_task_id': task.id,
                                   'request_id': params['request_id'], 'synthetic_fixture': params['synthetic_fixture'],
                                   'cpu_core_sha256': params['core_sha256']})
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                task.get_logger().report_scalar('preparation', key, value=value, iteration=0)
        print('T02B_STATISTICS ' + json.dumps(stats, sort_keys=True), flush=True)
        for name in ('manifest.json', 'statistics.json'):
            if not task.upload_artifact(name, artifact_object=output / name,
                                        metadata={'sha256_before_upload': sha((output / name).read_bytes())}, wait_on_upload=True):
                raise RuntimeError('report upload failed')
        # Task is the durable asset ledger. No host-path or shared ledger dependency.
        if task.get_parameter('Results/output_creation'):
            raise RuntimeError('output creation already attempted; reconcile instead of duplicating')
        task.set_parameter('Results/output_creation', 'pending')
        out = Dataset.create(dataset_project=params['project'], dataset_name=params['request_id'] + '-prepared',
                             dataset_version='1.0.0', use_current_task=False, output_uri=params['fileserver'],
                             dataset_tags=['T02-B', 'conversation-v1'], description='conversation-v1 CPU preparation output')
        task.set_parameter('Results/output_dataset_id', out.id)
        task.set_parameter('Results/output_creation', 'created')
        out.set_metadata({'input_dataset_id': ds.id, 'input_dataset_version': ds.version,
                          'processing_task_id': task.id, 'request_id': params['request_id'],
                          'manifest_sha256': sha((output / 'manifest.json').read_bytes())}, metadata_name='provenance')
        out.add_files(output)
        if out.upload(output_url=params['fileserver'], show_progress=False, max_workers=1) is False or not out.finalize():
            raise RuntimeError('output Dataset upload/finalize failed')
        out._task.close()
        task.set_parameter('Results/output_dataset_version', '1.0.0')
        task.set_parameter('Results/manifest_sha256', sha((output / 'manifest.json').read_bytes()))
        task.set_parameter('Results/output_creation', 'final')
        for name in FILES:
            content = (output / name).read_bytes()
            print('T02B_OUTPUT_HASH ' + json.dumps({'name': name, 'bytes': len(content), 'sha256': sha(content)}), flush=True)
    print('T02B_PREPARATION_OK', flush=True)
    task.flush(wait_for_uploads=True)
    task.close()


if __name__ == '__main__':
    agent_main()
