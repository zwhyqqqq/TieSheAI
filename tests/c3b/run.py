import pathlib,subprocess,json,sys,time
E=pathlib.Path(__file__).resolve().parents[2]/'infra/evidence/t01c3b'
name=sys.argv[1];cmd=sys.argv[2:];t=time.time();r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
p=E/(name+'.txt');p.write_bytes(r.stdout);p.chmod(0o600)
with (E/'commands.jsonl').open('a') as f:f.write(json.dumps({'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(t)),'command':cmd,'exit_code':r.returncode,'output':p.name,'seconds':round(time.time()-t,3)})+'\n')
print(name,'exit',r.returncode,'evidence',p);sys.exit(r.returncode)
