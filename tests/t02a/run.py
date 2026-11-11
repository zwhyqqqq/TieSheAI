"""Capture real command, exit code and output under ignored evidence; no shell expansion."""
import json
from pathlib import Path
import subprocess
import sys
import time

E = Path(__file__).resolve().parents[2] / 'infra/evidence/t02a'
E.mkdir(parents=True, exist_ok=True, mode=0o700)
name, cmd = sys.argv[1], sys.argv[2:]
start = time.time()
r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
p = E / (name + '.txt')
p.write_bytes(r.stdout)
p.chmod(0o600)
with (E / 'commands.jsonl').open('a') as f:
    f.write(json.dumps({'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(start)), 'command': cmd,
                        'exit_code': r.returncode, 'output': p.name, 'seconds': round(time.time() - start, 3)}) + '\n')
print(name, 'exit', r.returncode, 'evidence', p)
sys.exit(r.returncode)
