"""Package the independently built Artifact fix; preserve all prior releases and C1 builds."""
import pathlib,json,hashlib,shutil,re,subprocess
R=pathlib.Path(__file__).resolve().parents[2];E=R/'infra/evidence/artifact-download-fix'
name='artifact-download-20261110-v1';release=R/'infra/.local/web-fork/releases'/name
assert not release.exists(),'Refusing to overwrite fixed release'
def manifest(root):
    return {str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*')) if p.is_file()}
source=json.loads((E/'source-version.json').read_text())
source_manifest=json.loads((E/'source-manifest.json').read_text())
for p,h in source_manifest.items():assert hashlib.sha256((R/'clearml-web'/p).read_bytes()).hexdigest()==h['sha256'],p
raw={};release.mkdir(parents=True)
for app in ('main','widgets'):
    src=R/f'clearml-web/out/artifact-download-fix/{app}/browser'
    raw[app]=manifest(src);assert raw[app] and (src/'index.html').exists()
    target=release if app=='main' else release/'widgets'
    shutil.copytree(src,target,dirs_exist_ok=True)
    for p in target.rglob('*.map'):p.unlink()
    for p in target.rglob('*'):
        if p.is_file() and p.suffix in ('.js','.css'):
            s=p.read_text();s=re.sub(r'(?m)^//# sourceMappingURL=[^\r\n]*(?:\r?\n|$)','',s);s=re.sub(r'/\*# sourceMappingURL=[^*\r\n]*\*/\s*\Z','',s);p.write_text(s)
    p=target/'index.html';p.write_text(re.sub(r'<base\s+href(?:="[^"]*")?\s*>','<base href="'+('/' if app=='main' else '/widgets/')+'">',p.read_text(),count=1))
version='2.5.0-artifact-fix-'+source['source_patch_sha256'][:12]
(release/'env.js').write_text('(function(window){window.__env={subPath:"",forkVersion:'+json.dumps(version)+'};})(this);\n')
config={'apiBaseUrl':'/api','fileBaseUrl':'/files','fileServerAliases':['http://127.0.0.1:8081'],'baseHref':'/','version':version,'displayedServerUrls':{'apiServer':'/api','filesServer':'/files'}}
(release/'configuration.json').write_text(json.dumps(config,indent=2)+'\n')
(release/'version.json').write_text(json.dumps({'version':version,'release':name,**source,'sourceMapsPublished':False,'backend-release':'clearml/server:2.4.0'},indent=2)+'\n')
(E/'build-manifests.json').write_text(json.dumps(raw,indent=2));deployed=manifest(release);(E/'release-manifest.json').write_text(json.dumps(deployed,indent=2))
result={'release':str(release),'version':version,'source':source,'builds':{app:{'files':len(m),'bytes':sum(v['bytes'] for v in m.values()),'manifest_sha256':hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()} for app,m in raw.items()},'release_files':len(deployed),'release_manifest_sha256':hashlib.sha256(json.dumps(deployed,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
(E/'release-version.json').write_text(json.dumps(result,indent=2))
for p in release.rglob('*'):p.chmod(0o555 if p.is_dir() else 0o444)
release.chmod(0o555);print(json.dumps(result,indent=2))
