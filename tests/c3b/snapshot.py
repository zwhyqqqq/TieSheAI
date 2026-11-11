import pathlib,json,subprocess,hashlib,sys
R=pathlib.Path('/root/TieSheAI');E=R/'infra/evidence/t01c3b'
if sys.argv[1]=='before' and (E/'snapshot-before.json').exists():raise RuntimeError('Before baseline already exists; refusing to replace it')
sh=lambda *a:subprocess.check_output(a,cwd=R,text=True)
out={'git':{},'files':{},'containers':[],'agent':sh('systemctl','show','tiesheai-clearml-cpu-agent','-p','MainPID','-p','NRestarts','-p','ExecMainStartTimestamp','-p','ActiveState','-p','SubState'),'volumes':sorted(sh('docker','volume','ls','-q').split()),'credential_metadata':{}}
for repo in ('.','clearml-web','clearml-server'):
 out['git'][repo]={k:sh('git','-C',repo,*v) for k,v in {'head':['rev-parse','HEAD'],'status':['status','--porcelain','--untracked-files=all'],'diff':['diff'],'index':['diff','--cached']}.items()}
for f in sh('git','ls-files','-co','--exclude-standard').splitlines():
 p=R/f
 if p.is_file():out['files'][f]=hashlib.sha256(p.read_bytes()).hexdigest()
for p in [R/'infra/.env',R/'infra/.local/agent/clearml.conf']:
 st=p.stat();out['credential_metadata'][str(p)]={'inode':st.st_ino,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'mode':st.st_mode}
ids=sh('docker','ps','-aq').split()
for c in json.loads(sh('docker','inspect',*ids)):
 if c['Config'].get('Labels',{}).get('com.docker.compose.project') not in ('tiesheai-clearml','tiesheai-web-fork'):continue
 out['containers'].append({k:c[k] for k in ('Id','Name','Image','RestartCount','Created')}|{'started':c['State']['StartedAt'],'health':c['State'].get('Health',{}).get('Status'),'status':c['State']['Status'],'ports':c['HostConfig']['PortBindings'],'mounts':sorted(c['Mounts'],key=lambda x:x['Destination']),'network':{k:{a:v[a] for a in ('NetworkID','EndpointID','IPAddress','Aliases')} for k,v in c['NetworkSettings']['Networks'].items()}})
out['containers'].sort(key=lambda x:x['Name'])
release=R/'infra/.local/web-fork/releases/c2-be71d50-v2'
out['release']={str(p.relative_to(release)):hashlib.sha256(p.read_bytes()).hexdigest() for p in release.rglob('*') if p.is_file()}
(E/('snapshot-'+sys.argv[1]+'.json')).write_text(json.dumps(out,indent=2))
if sys.argv[1]=='before':
 for p in ('docs/STATUS.md','docs/HANDOFF.md'): (E/('before-'+pathlib.Path(p).name)).write_bytes((R/p).read_bytes())
print('Snapshot',sys.argv[1],'containers',len(out['containers']),'root files',len(out['files']),'release files',len(out['release']),'credential content not read')
