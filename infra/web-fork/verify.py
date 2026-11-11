"""Check the deployed C2 release against its saved SHA256 manifest (read-only)."""
import argparse,concurrent.futures,hashlib,json,pathlib,urllib.error,urllib.request
R=pathlib.Path(__file__).resolve().parents[2]
E=R/'infra/evidence/artifact-download-fix'; BASE='http://127.0.0.1:18080'
def get(path):
    try:
        with urllib.request.urlopen(BASE+path,timeout=20) as r:
            return r.status,r.headers,r.read()
    except urllib.error.HTTPError as r:
        return r.code,r.headers,r.read()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=pathlib.Path,default=E/'release-manifest.json');args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text())
    def check(item):
        name,entry=item
        status,headers,body=get('/'+name)
        assert status==200,(name,status)
        assert hashlib.sha256(body).hexdigest()==entry['sha256'],name
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(check,manifest.items()))
    missing=['/missing.js','/widgets/missing.js','/missing.css','/widgets/missing.woff2',
             '/configuration-missing.json','/app/missing','/widgets/app/missing','/main.js.map']
    for name in missing:
        assert get(name)[0]==404,name
    for name,index in [('/projects/example/tasks/example/output/log','index.html'),
                       ('/widgets/deep/example','widgets/index.html')]:
        status,headers,body=get(name)
        assert status==200 and hashlib.sha256(body).hexdigest()==manifest[index]['sha256'],name
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args):
            return None
    try:
        urllib.request.build_opener(NoRedirect()).open(BASE+'/widgets?type=scalar')
        raise AssertionError('Expected redirect')
    except urllib.error.HTTPError as r:
        assert r.code==308 and r.headers['Location']=='/widgets/?type=scalar'
    assert json.loads(get('/api/debug.ping')[2])['meta']['result_code']==200
    assert get('/api/v2.35/server.info')[0]==401
    assert get('/files/')[2].strip()==b'OK'
    artifact='/files/TieSheAI/Smoke/T01-B%20CPU%20Smoke.d13dc5bcdbc248f0bb80509eb66b9b36/artifacts/cpu-smoke-json/cpu-smoke.json'
    assert get(artifact)[0]==401
    assert get('/api/debug.ping?t01c2=readonly')[0]==200
    result={'files_byte_hash_verified':len(manifest),'missing_resources_404':len(missing),
            'spa_deep_links':2,'widgets_redirect':308,'anonymous_server_info':401,
            'api_ping':200,'files_root':200,'anonymous_artifact':401,'query_proxy':200,'source_maps_published':0}
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    main()
