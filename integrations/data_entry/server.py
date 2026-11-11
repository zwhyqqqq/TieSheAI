"""Authenticated same-origin data preparation adapter over a private Unix socket.

No arbitrary commands, paths, scripts, URLs or credentials are accepted. All SDK
operations use an isolated process with the validated caller's session token.
"""
import base64
import fcntl
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import socketserver
import subprocess
import tempfile
from urllib.parse import urlsplit
import requests

from common import API, PYTHON, STATE, MAX_FILE, core, init_state, request_path, owned, digest, write, Rejected

CONFIG = None


def upload_body(body):
    if set(body)-{'request_id','content_base64','filename','synthetic_fixture'}:
        raise Rejected('上传字段无效')
    if type(body.get('synthetic_fixture')) is not bool:
        raise Rejected('请明确数据是否为合成测试')
    name = body.get('filename')
    if not isinstance(name,str) or len(name)>160 or '/' in name or '\\' in name or not name.lower().endswith('.jsonl'):
        raise Rejected('请选择JSONL文件')
    try: raw = base64.b64decode(body['content_base64'], validate=True)
    except (ValueError, KeyError, TypeError):
        raise Rejected('上传编码无效') from None
    if not raw: raise Rejected('文件为空')
    if len(raw)>MAX_FILE: raise Rejected('文件超过1 MiB限制',413)
    # Authority is the unchanged T02-A core, including all-line validation and split feasibility.
    with tempfile.TemporaryDirectory(prefix='data-entry-check-') as directory:
        path=Path(directory)/'conversations.jsonl';path.write_bytes(raw)
        try: core.prepare(path,Path(directory)/'checked')
        except core.ContractError as exc: raise Rejected(str(exc),422) from None
    return raw


def sdk(body, user, token):
    env=os.environ.copy()
    for key in ('CLEARML_API_ACCESS_KEY','CLEARML_API_SECRET_KEY','TRAINS_API_ACCESS_KEY','TRAINS_API_SECRET_KEY'):
        env.pop(key,None)
    env.update(CLEARML_CONFIG_FILE=str(STATE/'sdk.conf'),CLEARML_AUTH_TOKEN=token,
               CLEARML_API_HOST=API,CLEARML_WEB_HOST='http://127.0.0.1:18080',
               CLEARML_FILES_HOST='http://127.0.0.1:8081',PYTHONDONTWRITEBYTECODE='1')
    command=[PYTHON,'-B',str(Path(__file__).resolve().with_name('operations.py'))]
    try:
        process=subprocess.run(command,input=json.dumps({**body,'owner':user}).encode(),stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,env=env,timeout=180)
    except subprocess.TimeoutExpired:
        raise Rejected('操作超时，结果待核对；请刷新请求，不会重复创建',409) from None
    # Never persist the environment/token/stdin. SDK diagnostic output stays local.
    with (STATE/'operations.log').open('ab') as log:
        log.write(process.stderr)
    lines=process.stdout.decode('utf-8',errors='replace').splitlines()
    result=next((json.loads(x[len('T02B_RESPONSE '):]) for x in reversed(lines) if x.startswith('T02B_RESPONSE ')),None)
    if not result: raise Rejected('适配操作中断，结果待核对',409)
    if not result['ok']: raise Rejected(result['error'],result['status'])
    return result['data']


class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
    daemon_threads=True


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass  # no cookies, query strings or file content in access logs
    def address_string(self): return 'local-proxy'

    def reply(self,status,data,binary=False):
        raw=data if binary else json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/zip' if binary else 'application/json; charset=utf-8')
        if binary: self.send_header('Content-Disposition','attachment; filename="prepared-conversations.zip"')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(raw)

    def identity(self):
        cookie=self.headers.get('Cookie','')
        if not cookie: raise Rejected('请先登录ClearML',401)
        response=requests.post(API+'/v2.35/users.get_current_user',headers={'Cookie':cookie},json={},timeout=15)
        result=response.json()
        if response.status_code!=200 or result.get('meta',{}).get('result_code')!=200:
            raise Rejected('请重新登录ClearML',401)
        parsed=SimpleCookie();parsed.load(cookie)
        token=parsed.get('clearml_token_basic')
        if not token: raise Rejected('缺少当前用户会话',401)
        return result['data']['user'],token.value

    def do_GET(self): self.handle_request(False)
    def do_POST(self): self.handle_request(True)

    def handle_request(self,mutation):
        try:
            user,token=self.identity();uid=user['id']
            path=urlsplit(self.path).path
            if mutation:
                origin=self.headers.get('Origin')
                if self.headers.get('X-TieSheAI-Request')!='1' or (origin and (urlsplit(origin).scheme not in ('http', 'https') or urlsplit(origin).netloc != self.headers.get('Host'))):
                    raise Rejected('请求来源校验失败',403)
                if self.headers.get('Sec-Fetch-Site') not in (None,'same-origin','none'):
                    raise Rejected('不允许跨站提交',403)
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                    raise Rejected('仅接受JSON请求',415)
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=(MAX_FILE*4//3+16384): raise Rejected('请求超过上传限制',413)
                body=json.loads(self.rfile.read(length))
                if not isinstance(body,dict): raise Rejected('请求必须是对象')
            else: body={}
            if path=='/data-entry/api/bootstrap' and not mutation:
                records=[]
                for file in (STATE/'requests').glob('*.json'):
                    record=json.loads(file.read_text())
                    if record['owner']==uid: records.append(record)
                selected_path=STATE/'selections'/(digest(uid.encode())+'.json')
                selected=json.loads(selected_path.read_text()) if selected_path.exists() else None
                return self.reply(200,{'user':{'id':uid,'name':user['name']},'requests':sorted(records,key=lambda r:r['created'],reverse=True),
                                       'selected':selected,'max_bytes':MAX_FILE})
            if path=='/data-entry/api/catalog' and not mutation:
                return self.reply(200,sdk({'action':'catalog'},uid,token))
            if path.startswith('/data-entry/api/requests/') and not mutation:
                request_id=path.rsplit('/',1)[-1];owned(request_id,uid)
                with request_path(request_id).with_suffix('.lock').open('a') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX)
                    result=sdk({'action':'status','request_id':request_id},uid,token)
                    return self.reply(200,result)
            if path in ('/data-entry/api/upload','/data-entry/api/submit') and mutation:
                request_id=body.get('request_id');record_path=request_path(request_id)
                raw=upload_body(body) if path.endswith('/upload') else None
                with record_path.with_suffix('.lock').open('a') as lock:
                    fcntl.flock(lock,fcntl.LOCK_EX)
                    if raw is not None:
                        fingerprint=digest(raw+core.encoded([body['filename'],body['synthetic_fixture']]))
                        if record_path.exists():
                            _,record=owned(request_id,uid)
                            if record['fingerprint']!=fingerprint: raise Rejected('此请求编号已绑定其他上传内容',409)
                            if record.get('pending'): raise Rejected('此前操作结果待核对，不会重复创建',409)
                            return self.reply(200,record)
                        from datetime import datetime,timezone
                        write(record_path,{'request_id':request_id,'owner':uid,'project':CONFIG['project'],'fingerprint':fingerprint,
                                           'filename':body['filename'],'synthetic_fixture':body['synthetic_fixture'],
                                           'input_sha256':digest(raw),'input_bytes':len(raw),'status':'uploading','pending':None,
                                           'created':datetime.now(timezone.utc).isoformat()})
                        result=sdk({**body,'action':'upload'},uid,token)
                    else:
                        owned(request_id,uid)
                        if set(body)-{'request_id','seed','validation_fraction'}: raise Rejected('处理字段无效')
                        # Serializes this entry's idle-check/create/enqueue operations across all users.
                        with (STATE/'queue.lock').open('a') as queue_lock:
                            fcntl.flock(queue_lock,fcntl.LOCK_EX)
                            result=sdk({**body,'action':'submit'},uid,token)
                    return self.reply(200,result)
            if path in ('/data-entry/api/select', '/data-entry/api/archive') and mutation:
                if set(body)!={'dataset_id'} or not isinstance(body['dataset_id'],str): raise Rejected('数据集选择无效')
                if path.endswith('/archive'):
                    result = sdk({**body, 'action': 'archive'}, uid, token)
                    return self.reply(200, base64.b64decode(result['archive_base64']), True)
                with (STATE / 'selections' / (digest(uid.encode()) + '.lock')).open('a') as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    return self.reply(200, sdk({**body, 'action': 'select'}, uid, token))
            raise Rejected('入口不存在',404)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Rejected as exc: self.reply(exc.status,{'error':str(exc)})
        except (ValueError,KeyError,TypeError): self.reply(400,{'error':'请求格式无效'})
        except Exception: self.reply(503,{'error':'数据服务暂时不可用，请刷新；已有资产不会被重新创建'})


if __name__=='__main__':
    CONFIG=init_state()
    directory=STATE/'socket';directory.mkdir(mode=0o750,exist_ok=True)
    directory.chmod(0o750);os.chown(directory,0,65534)
    sock=directory/'adapter.sock'
    if sock.exists(): sock.unlink()  # systemd owns the single adapter process
    with Server(str(sock),Handler) as server:
        os.chown(sock,0,65534);sock.chmod(0o660)
        server.serve_forever()
