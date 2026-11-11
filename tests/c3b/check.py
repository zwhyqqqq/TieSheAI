#!/usr/bin/env python3
"""Check real browser downloads, exact inventory/runtime preservation, and delivery."""
import argparse, collections, hashlib, json, pathlib, re, subprocess

R = pathlib.Path(__file__).resolve().parents[2]
E = R / 'infra/evidence/t01c3b'

def read(name):
    return json.loads((E / name).read_text())

def dump(name, obj):
    (E / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def sha(b):
    return hashlib.sha256(b).hexdigest()

def browser(fork_label, official_label):
    import zipfile
    sdk = read('sdk-verification.json')
    results = {}
    for port, label in ((18080, fork_label), (8080, official_label)):
        x = read(label + '-browser.json')
        assert x['port'] == port and x['pass'] and all(s['ok'] for s in x['steps'])
        assert not x.get('observerErrors') and not x.get('unknownErrors')
        assert len(x.get('pageErrors', [])) == len(x.get('pageErrorCorrelations', []))
        assert len(x['parentGraph']['nodes']) == 2 and len(x['parentGraph']['arrows']) == 2
        apis = [v for v in x['network'] if v.get('api')]
        assert all(v['http'] == 200 and v.get('business', 200) == 200 for v in apis)
        assert all(v.get('fieldCheck', {}).get('present', True) for v in apis)
        assert len(x['downloads']) == 3
        archives = {}
        for key in ('v1', 'v2'):
            stage = key + '-real-archive-download'
            dl = next(v for v in x['downloads'] if v['stage'] == stage)
            raw = (E / dl['file']).read_bytes()
            expected = next(v for v in sdk['datasets'][key]['artifacts'] if v['key'] == 'data')
            assert sha(raw) == dl['sha256'] == expected['sha256'] and len(raw) == expected['bytes']
            with zipfile.ZipFile(E / dl['file']) as z:
                archives[key] = {name: z.read(name) for name in z.namelist()}
            assert x['datasets'][key]['id'] == sdk['datasets'][key]['id']
            for f in sdk['datasets'][key]['files']:
                assert f['name'] in x['datasets'][key]['contentText'] and f['sha256'] in x['datasets'][key]['contentText']
        assert set(archives['v1']) == {'inherited.txt'} and set(archives['v2']) == {'added.txt'}
        merged = {**archives['v1'], **archives['v2']}
        for name, raw in merged.items():
            assert raw == (E / 'payload' / name).read_bytes()
        dl = next(v for v in x['downloads'] if v['stage'] == 'draft-task-model-real-download')
        raw = (E / dl['file']).read_bytes()
        assert raw == (E / 'payload/TEST_FIXTURE_NOT_TRAINED_WEIGHTS.json').read_bytes()
        assert sha(raw) == dl['sha256'] == sdk['model']['sha256'] and len(raw) == 118
        assert x['modelTaskLink']['expectedTask'] == sdk['model']['task']
        assert sdk['model']['id'] in x['taskOutputLink']['href'] and sdk['model']['id'] in x['outputLinkDestination']
        assert x['modelGeneralButton']['downloadEvents'] == 0
        assert x['modelGeneralButton']['sha256'] == sdk['model']['sha256']
        # Each intentional denial has an actual failed request; never substitute 200.
        for b in x['blocked']:
            assert b['reason'] in ('third-party', 'User settings write', 'Server statistics option write'), b
            assert any(f['url'] == b['url'] for f in x['failed']), b
        classifications = []
        for c in x['console']:
            same_stage_errors = [e for e in x['errors'] if e['stage'] == c['stage']]
            same_stage_errors += [v for v in c.get('arguments',[]) if v and v.get('status') is not None]
            failed = [f for f in x['failed'] if f['stage'] == c['stage']]
            status404 = [r for r in x['network'] if r['stage'] == c['stage'] and r['http'] == 404]
            reason = None
            if c['text'] == 'Failed to load resource: the server responded with a status of 404 (Not Found)':
                assert status404 and all(r['url'].endswith(('/credentials.json', '/onboarding.json')) for r in status404)
                reason = 'Known optional configuration 404; same-stage response URLs attached'
            elif c['text'] == 'Failed to load resource: net::ERR_BLOCKED_BY_CLIENT.Inspector':
                assert any(any(b['url'] == f['url'] for b in x['blocked']) for f in failed)
                reason = 'Intentional protection; same-stage failed requests attached'
            elif c['text'] in ('ERROR le', 'ERROR j'):
                assert same_stage_errors and all(e['name'] == 'HttpErrorResponse' and e['status'] == 0 and any(b['url'] == e['url'] for b in x['blocked']) for e in same_stage_errors)
                reason = 'Exact console signature correlated with structured status=0 errors and blocked URLs'
            elif c['text'].startswith(('TypeError: Failed to fetch\n','ERROR TypeError: Failed to fetch\n')):
                assert c['stage'] == 'login' and any(f['url'] == 'https://api.github.com/repos/clearml/clearml' for f in failed)
                reason = 'GitHub fetch inference from exact same-stage blocked URL and saved stack; original retained'
            elif c['text'].startswith("Access to fetch at 'http://127.0.0.1:8081/"):
                assert port == 8080 and c['stage'] in ('v1-real-archive-download','v2-real-archive-download')
                assert 'blocked by CORS policy' in c['text']
                assert any(f['error'] == 'net::ERR_FAILED' and ':8081/' in f['url'] for f in failed)
                reason = 'Official credentialed fetch CORS failure; actual navigation fallback download separately verified'
            elif c['text'] == 'Failed to load resource: net::ERR_FAILED':
                assert port == 8080 and c['stage'] in ('v1-real-archive-download','v2-real-archive-download')
                assert any(f['error'] == 'net::ERR_FAILED' and ':8081/' in f['url'] for f in failed)
                reason = 'Official CORS failed resource; actual fallback download verified separately'
            classifications.append({**c, 'classification': reason or 'UNCLASSIFIED',
                                    'error_urls': [e.get('url') for e in same_stage_errors],
                                    'failed_urls': [f['url'] for f in failed],
                                    'http404_urls': [r['url'] for r in status404]})
        unknown = [c for c in classifications if c['classification'] == 'UNCLASSIFIED']
        dump(label + '-console-review.json', classifications)
        # Unclassified warnings/errors are reported explicitly rather than suppressed.
        results[str(port)] = {'label': label, 'steps': len(x['steps']), 'api_responses': len(apis),
                              'endpoints': sorted({v['endpoint'] for v in apis}),
                              'http_business': dict(collections.Counter(str((v['http'], v.get('business', 'not read'))) for v in apis)),
                              'console_errors': sum(c['type'] == 'error' for c in x['console']),
                              'console_warnings': sum(c['type'] == 'warning' for c in x['console']),
                              'structured_errors': len(x['errors']), 'unclassified_console': unknown,
                              'blocked': dict(collections.Counter(b['reason'] for b in x['blocked'])),
                              'downloads': x['downloads'], 'browser_download_contents_exact': True,
                              'model_general_button': 'Inline JSON only; zero download events',
                              'dataset_preview': {k: v['previewText'] for k,v in x['datasets'].items()}}
    dump('browser-results.json', results)
    dump('selected-browser-labels.json', {'fork': fork_label, 'official': official_label})
    print(json.dumps(results, ensure_ascii=False))

def preservation():
    b, a = read('snapshot-before.json'), read('snapshot-after.json')
    for k in ('containers', 'agent', 'volumes', 'release', 'credential_metadata'):
        assert b[k] == a[k], k
    assert len(a['containers']) == 7 and all(c['health'] == 'healthy' and c['RestartCount'] == 0 for c in a['containers'])
    for repo in b['git']:
        for k in ('head','index'):
            assert b['git'][repo][k] == a['git'][repo][k], (repo,k)
        if repo != '.':
            assert b['git'][repo] == a['git'][repo], repo
    assert (E/'python-before.txt').read_bytes() == (E/'python-after.txt').read_bytes()
    allowed = {'docs/STATUS.md','docs/HANDOFF.md','docs/T01C_COMPATIBILITY.md','docs/DECISIONS.md'}
    for p, h in b['files'].items():
        if p not in allowed:
            assert a['files'][p] == h, p
    for name, files in read('protected-files-before.json').items():
        base = R/name if name in ('clearml-web','clearml-server') else R/'infra/.local/web-fork/releases'/name
        for p,h in files.items():
            assert sha((base/p).read_bytes()) == h, (name,p)
    prior = json.loads((R/'infra/evidence/t01c2/snapshot-after.json').read_text())['hashes']
    for filename, expected in prior.items():
        assert sha(pathlib.Path(filename).read_bytes()) == expected, filename
    assert read('inventory-comparison.json')['pass']
    # Historical Smoke file verification is after creation; original registered hash and local fixed fixture are the baseline.
    assert read('historical-artifact-check.json')['pass']
    dump('preservation-result.json', {'pass':True,'seven_container_identity_and_health_unchanged':True,
                                     'agent_environment_and_credentials_unchanged':True,
                                     'fork_sources_and_releases_unchanged':True,'historical_objects_queues_preferences_unchanged':True,
                                     'git_head_and_index_unchanged':True})
    print('PASS runtime, source/release, full old inventory, queues/preferences, historical Artifact and Git preservation')

def delivery():
    changed = {'docs/STATUS.md','docs/HANDOFF.md','docs/DECISIONS.md','docs/T01C_COMPATIBILITY.md','docs/T01C3B_FIXTURES.md'}
    changed.update(str(p.relative_to(R)) for p in (R/'tests/c3b').glob('*') if p.is_file())
    assert len((R/'docs/HANDOFF.md').read_text().splitlines()) <= 100
    for name in changed:
        text = (R/name).read_text()
        assert not re.search(r'(?i)(?:secret_key|access_key|api_key|password)\s*[=:]\s*["\'][A-Za-z0-9+/]{12,}',text), name
        if name.endswith('.md'):
            for link in re.findall(r'\]\(([^)]+)\)',text):
                if '://' not in link and not link.startswith('#'):
                    assert ((R/name).parent / link.split('#')[0]).exists(), (name,link)
    before = read('snapshot-before.json')
    for name in ('docs/DECISIONS.md','docs/T01C_COMPATIBILITY.md'):
        # Appended reports preserve the complete old content.
        old = (E/('original-'+pathlib.Path(name).name)).read_text()
        assert sha(old.encode()) == before['files'][name]
        assert (R/name).read_text().startswith(old), name
    for repo in ('.','clearml-web','clearml-server'):
        for args in (['diff','--check'],['diff','--cached','--check']):
            subprocess.run(['git','-C',str(R/repo),*args],check=True)
        for key,args in [('head',['rev-parse','HEAD']),('index',['diff','--cached'])]:
            now=subprocess.check_output(['git','-C',str(R/repo),*args],text=True)
            assert now==before['git'][repo][key]
    subprocess.run(['git','check-ignore','infra/evidence/t01c3b/ledger.json','infra/.local/agent/clearml.conf','infra/.env'],cwd=R,check=True,stdout=subprocess.PIPE)
    # Files already present before must be preserved, apart from explicitly permitted docs.
    for name,h in before['files'].items():
        if name not in changed:
            assert sha((R/name).read_bytes())==h, name
    current = set(subprocess.check_output(['git','ls-files','-co','--exclude-standard'],cwd=R,text=True).splitlines())
    assert current - set(before['files']) <= changed, current - set(before['files']) - changed
    assert '完整 C3 仍未通过' in (R/'docs/HANDOFF.md').read_text()
    assert 'C3-B 首轮' in (R/'docs/STATUS.md').read_text()
    dump('delivery-result.json', {'pass':True,'handoff_lines':len((R/'docs/HANDOFF.md').read_text().splitlines()),'modified_files':sorted(changed)})
    print('PASS document consistency, references, exact preservation, ignore rules, sensitive-pattern scan and Git checks')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['browser','preservation','delivery'])
    p.add_argument('--fork-label',default='accept-18080-r7')
    p.add_argument('--official-label',default='accept-8080-r6')
    args=p.parse_args()
    if args.action=='browser':browser(args.fork_label,args.official_label)
    else:{'preservation':preservation,'delivery':delivery}[args.action]()
