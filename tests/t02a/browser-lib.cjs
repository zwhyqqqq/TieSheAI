const fs=require('fs'),path=require('path'),crypto=require('crypto');
const R=path.resolve(__dirname,'../..'),E=path.join(R,'infra/evidence/t02a'),T=path.join(R,'infra/evidence/t01c2/browser-tools');
const {chromium}=require(path.join(T,'node_modules/playwright'));
const contracts=JSON.parse(fs.readFileSync(path.join(__dirname,'../c3b/readonly-contracts.json'))),allow=new Set(contracts.allowed.map(x=>x.endpoint));
const sha=x=>crypto.createHash('sha256').update(Buffer.isBuffer(x)||typeof x==='string'?x:JSON.stringify(x)).digest('hex');
function shape(v,depth=0){if(v===null)return 'null';if(Array.isArray(v))return {type:'array',length:v.length,item:v.length?shape(v[0],depth+1):null};if(typeof v==='object'){if(depth>3)return Object.keys(v).slice(0,80);return Object.fromEntries(Object.entries(v).filter(([k])=>!/(token|secret|password|credentials|access_key)/i.test(k)).slice(0,100).map(([k,x])=>[k,shape(x,depth+1)]));}return typeof v;}
async function launch(){return chromium.launch({headless:true,executablePath:path.join(T,'manual-chromium/chrome-linux/chrome'),args:['--no-sandbox']});}
async function session(browser,port,label){
 const origin=`http://127.0.0.1:${port}`,state={label,port,stage:'login',network:[],blocked:[],errors:[],console:[],failed:[],steps:[],pending:[],downloads:[]};
 const context=await browser.newContext({viewport:{width:1600,height:1050},acceptDownloads:true});
 if((await context.cookies()).length)throw Error('unclean context');
 await context.exposeBinding('__c3error',(_,e)=>state.errors.push({stage:state.stage,observedAt:Date.now(),...e}));
 await context.addInitScript(()=>window.addEventListener('error',event=>{const e=event.error;if(!e)return;let url;try{const u=new URL(e.url,location.href);url=u.origin+u.pathname}catch{}window.__c3error({name:e.name,constructor:e.constructor?.name,status:e.status,url,message:e.message||event.message});}));
 await context.route('**/*',async route=>{
  const req=route.request(),u=new URL(req.url());let endpoint=u.pathname.split('/').pop(),api=u.port==='8008'||u.pathname.startsWith('/api/');
  let reason;
  if(!['127.0.0.1','localhost'].includes(u.hostname)||!['8080','18080','8008','8081'].includes(u.port))reason='third-party';
  else if(api&&endpoint==='events.debug_images'){let body;try{body=req.postDataJSON()}catch{}const ids=JSON.parse(fs.readFileSync(path.join(E,'ledger.json')));const permitted=[ids.input_dataset_id,ids.output_dataset_id];if(!body?.metrics?.length||body.metrics.some(m=>!permitted.includes(m.task)))reason='Preview request outside fixture Dataset IDs';}
  else if(api&&!allow.has(endpoint))reason=contracts.blocked[endpoint]||'unknown endpoint; deny pending contract review';
  else if(!api&&!['GET','HEAD','OPTIONS'].includes(req.method()))reason='non-API local write';
  if(reason){state.blocked.push({stage:state.stage,method:req.method(),url:u.origin+u.pathname,endpoint:api?endpoint:undefined,reason});return route.abort('blockedbyclient');}
  return route.continue();
 });
 context.on('response',r=>{state.pending.push((async()=>{
  const u=new URL(r.url()),api=u.port==='8008'||u.pathname.startsWith('/api/');if(!api&&!(u.port==='8081'||u.pathname.startsWith('/files/'))&&r.status()<400)return;
  const entry={stage:state.stage,method:r.request().method(),url:u.origin+u.pathname,http:r.status(),type:r.headers()['content-type'],api};
  if((u.port==='8081'||u.pathname.startsWith('/files/'))){const h=await r.request().allHeaders();entry.sentCookie=!!h.cookie;entry.sentAuthorization=!!h.authorization;}
  if((u.port==='8081'||u.pathname.startsWith('/files/')))entry.corsHeaders=Object.fromEntries(Object.entries(r.headers()).filter(([k])=>['access-control-allow-origin','access-control-allow-credentials','access-control-expose-headers','content-disposition'].includes(k)));
  if(!api&&(u.port==='8081'||u.pathname.startsWith('/files/'))){try{await r.finished();const bytes=await r.body();entry.bytes=bytes.length;entry.sha256=sha(bytes);}catch(e){entry.bodyUnavailable=e.message;}}
  if(api){entry.endpoint=u.pathname.split('/').pop();
   if(entry.endpoint!=='auth.login'){
    try{const j=await r.json();entry.business=j.meta?.result_code;entry.subcode=j.meta?.result_subcode;entry.dataShape=shape(j.data);entry.resultMessage=j.meta?.result_msg;
     let b;try{b=r.request().postDataJSON()}catch{};if(b)entry.query=b;
     const expected={projects:'projects',tasks:'tasks',models:'models',queues:'queues',workers:'workers',reports:'tasks'};const [srv,action]=entry.endpoint.split('.');
     if(['get_all','get_all_ex'].includes(action)&&expected[srv])entry.fieldCheck={field:expected[srv],present:Array.isArray(j.data?.[expected[srv]])};
     if(action==='get_by_id'&&['tasks','projects','queues','models'].includes(srv)){const key=srv.slice(0,-1);entry.fieldCheck={field:key,present:!!j.data?.[key]&&typeof j.data[key]==='object'};}
     if(action==='get_by_id_ex'&&['tasks','models'].includes(srv))entry.fieldCheck={field:srv,present:Array.isArray(j.data?.[srv])};
    }catch(e){entry.parseError=e.message;}
   }
  }
  state.network.push(entry);
 })());});
 context.on('requestfailed',r=>{const u=new URL(r.url());state.failed.push({stage:state.stage,url:u.origin+u.pathname,error:r.failure()?.errorText});});
 context.on('page',p=>{
  p.on('pageerror',e=>{state.pageErrors??=[];state.pageErrors.push({stage:state.stage,observedAt:Date.now(),name:e.name,message:e.message,stack:e.stack});});
  p.on('console',m=>{if(m.type()==='error'||m.type()==='warning'){const entry={stage:state.stage,type:m.type(),text:m.text().slice(0,3000),location:m.location()};state.console.push(entry);state.pending.push((async()=>{entry.arguments=await Promise.all(m.args().map(async h=>{try{return await h.evaluate(v=>{if(!v||typeof v!=='object')return null;let url;try{const u=new URL(v.url,location.href);if(v.url)url=u.origin+u.pathname;}catch{}return {name:v.name,constructor:v.constructor?.name,status:v.status,url,message:v.message};});}catch(e){return {captureError:e.message}}}));})());}});
  p.on('download',d=>{state.pending.push((async()=>{const index=state.downloadSequence=(state.downloadSequence||0)+1;const f=path.join(E,`${label}-download-${index}-${path.basename(d.suggestedFilename())}`);await d.saveAs(f);state.downloads.push({stage:state.stage,url:d.url().split('?')[0],name:d.suggestedFilename(),file:path.basename(f),failure:await d.failure(),bytes:fs.statSync(f).size,sha256:sha(fs.readFileSync(f))});})());});
 });
 const page=await context.newPage();page.setDefaultTimeout(12000);
 async function settle(){await page.waitForTimeout(900);const results=await Promise.allSettled(state.pending);state.observerErrors=results.filter(x=>x.status==='rejected').map(x=>String(x.reason));}
 async function capture(name,action,target=page){state.stage=name;let step={name,operation:action.toString(),start:new Date().toISOString()};try{await action();await settle();step.ok=true;}catch(e){step.ok=false;step.error=e.message;}await settle();step.url=target.url();step.body=await target.locator('body').innerText().catch(()=> '');step.links=await target.locator('a').evaluateAll(xs=>xs.map(x=>({text:x.innerText,href:x.getAttribute('href'),title:x.getAttribute('title'),'aria-label':x.getAttribute('aria-label')}))).catch(()=>[]);step.controls=await target.locator('input,button,[role=tab]').evaluateAll(xs=>xs.map(x=>({tag:x.tagName,role:x.getAttribute('role'),text:x.innerText,placeholder:x.getAttribute('placeholder'),aria:x.getAttribute('aria-label'),title:x.getAttribute('title'),'data-id':x.getAttribute('data-id')}))).catch(()=>[]);step.screenshot=`${label}-${name}.png`;await target.screenshot({path:path.join(E,step.screenshot),fullPage:true,mask:[target.locator('input[type=password]'),target.getByText('TieSheAI T01-B CPU',{exact:true})]}).catch(e=>step.screenshotError=e.message);state.steps.push(step);save();return step;}
 function save(){fs.writeFileSync(path.join(E,label+'-browser.json'),JSON.stringify({...state,pending:undefined},null,2));}
 async function login(){await capture('login',async()=>{await page.goto(origin,{waitUntil:'networkidle'});const input=page.locator('input[formcontrolname="name"]');await input.waitFor({timeout:15000});await input.fill('TieSheAI T01-B CPU');const option=page.getByRole('option',{name:'TieSheAI T01-B CPU',exact:true});await option.waitFor();await option.click();await page.getByRole('button',{name:/start|sign in|login|connect/i}).click();await page.waitForURL(u=>!u.pathname.includes('login'),{timeout:20000});});}
 async function inventory(phase){state.stage='inventory-'+phase;const out=await page.evaluate(async()=>{
  const call=async(endpoint,body={})=>{const r=await fetch('/api/v2.35/'+endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(r.status!==200||j.meta.result_code!==200)throw Error(endpoint+' '+r.status);return j.data;};
  const task=(await call('tasks.get_by_id',{task:'d13dc5bcdbc248f0bb80509eb66b9b36'})).task;
  const tasks=await call('tasks.get_all',{only_fields:['id','status','name','type','project','system_tags'],page_size:500});
  const queues=await call('queues.get_all',{only_fields:['id','name','entries','tags','system_tags','metadata'],page_size:500});
  const projects=await call('projects.get_all',{only_fields:['id','name','tags','system_tags'],page_size:500});
  const models=await call('models.get_all',{only_fields:['id','name','task','project'],page_size:500});
  const prefs=await call('users.get_preferences');
  const digest=async x=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(x))))).map(x=>x.toString(16).padStart(2,'0')).join('');
  return {taskHash:await digest(task),taskStatus:task.status,artifact:task.execution.artifacts.find(x=>x.key==='cpu-smoke-json'),tasks:tasks.tasks.sort((a,b)=>a.id.localeCompare(b.id)),queues:queues.queues.sort((a,b)=>a.id.localeCompare(b.id)),projects:projects.projects.sort((a,b)=>a.id.localeCompare(b.id)),models:models.models.sort((a,b)=>a.id.localeCompare(b.id)),preferencesHash:await digest(prefs)};
 });fs.writeFileSync(path.join(E,label+'-inventory-'+phase+'.json'),JSON.stringify(out,null,2));return out;}
 return {context,page,state,origin,capture,login,inventory,settle,save};
}
module.exports={E,launch,session,sha};
