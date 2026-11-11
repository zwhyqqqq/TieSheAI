"""Verify C1 manifests, then create one immutable, separate deployment release."""
import hashlib,json,pathlib,re,shutil
R=pathlib.Path(__file__).resolve().parents[2]
E=R/'infra/evidence/t01c2'; E.mkdir(parents=True,exist_ok=True)
release=R/'infra/.local/web-fork/releases/c2-be71d50-v2'
def manifest(root):
 return {str(p.relative_to(root)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*')) if p.is_file()}
raw={}
for name,sub in [('main','build/browser'),('widgets','dist/report-widgets/browser')]:
 source=R/'clearml-web'/sub
 actual=manifest(source); expected=json.loads((R/f'infra/evidence/t01c1/{name}-artifact-manifest.json').read_text())
 assert actual==expected, f'{name} differs from accepted C1 artifacts'
 raw[name]=actual
assert not release.exists(), 'Refusing to overwrite an existing release'
release.mkdir(parents=True)
for name,sub in [('main','build/browser'),('widgets','dist/report-widgets/browser')]:
 dest=release if name=='main' else release/'widgets'
 shutil.copytree(R/'clearml-web'/sub,dest,dirs_exist_ok=True)
 for p in dest.rglob('*.map'): p.unlink()
 for p in dest.rglob('*'):
  if p.is_file() and p.suffix in ('.js','.css'):
   s=p.read_text(); s=re.sub(r'(?m)^//# sourceMappingURL=[^\r\n]*(?:\r?\n|$)','',s); s=re.sub(r'/\*# sourceMappingURL=[^*\r\n]*\*/\s*\Z','',s)
   p.write_text(s)
 p=dest/'index.html'; s=p.read_text(); s=re.sub(r'<base\s+href(?:="[^"]*")?\s*>', '<base href="'+('/' if name=='main' else '/widgets/')+'">',s,count=1); p.write_text(s)
(release/'env.js').write_text('(function(window){window.__env=window.__env||{};window.__env.subPath="";window.__env.forkVersion="2.5.0-be71d50-c2";})(this);\n')
config={'apiBaseUrl':'/api','fileBaseUrl':'/files','baseHref':'/','version':'2.5.0-fork-be71d50-c2','displayedServerUrls':{'apiServer':'/api','filesServer':'/files'}}
(release/'configuration.json').write_text(json.dumps(config,indent=2)+'\n')
version={'version':config['version'],'webapp-commit':'be71d50e7504eb00a2e09900fabbe8697ed23558','web-package-version':'2.5.0','backend-release':'clearml/server:2.4.0','deployment':'T01-C2','sourceMapsPublished':False}
(release/'version.json').write_text(json.dumps(version,indent=2)+'\n')
(E/'source-manifests.json').write_text(json.dumps(raw,indent=2))
(E/'release-manifest.json').write_text(json.dumps(manifest(release),indent=2))
for p in release.rglob('*'): p.chmod(0o555 if p.is_dir() else 0o444)
release.chmod(0o555)
print('C1 manifests match; created',release,'files',len(manifest(release)))
