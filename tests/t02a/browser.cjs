// Real Fork UI checks and downloads. Reuse C3 read protection; never edits DOM/links/responses.
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {E,launch,session,sha}=require('./browser-lib.cjs');
const ledger=JSON.parse(fs.readFileSync(path.join(E,'ledger.json'))),sdk=JSON.parse(fs.readFileSync(path.join(E,'sdk-verification.json')));
const visible=(p,t)=>p.getByText(t,{exact:true}).filter({visible:true});
(async()=>{
 const browser=await launch(),label=process.argv[2]||'fork-accept',s=await session(browser,18080,label),p=s.page;
 const check=async(name,fn,target=p)=>{const step=await s.capture(name,fn,target);if(!step.ok)throw Error(name+': '+step.error);return step;};
 try{
  await s.login();assert(s.state.steps[0].ok);const baseline=await s.inventory('before');
  const project=JSON.parse(fs.readFileSync(path.join(E,'processing-task.json'))).project;
  await check('task-completed',async()=>{
   await p.goto(s.origin+'/projects/'+project+'/experiments/'+ledger.processing_task_id+'/output/log',{waitUntil:'networkidle'});
   await visible(p,'T02-A CPU data preparation').waitFor();
   const body=await p.locator('body').innerText();assert(/completed/i.test(body));
   s.state.taskState={id:ledger.processing_task_id,status:'completed',url:p.url()};
  });
  await check('task-agent-logs',async()=>{
   await p.getByText('T02A_PREPARATION_OK',{exact:false}).filter({visible:true}).waitFor();
   const body=await p.locator('body').innerText();
   for(const marker of ['T02A_AGENT_EXECUTION','T02A_STATISTICS','T02A_OUTPUT_DATASET',ledger.output_dataset_id,'T02A_OUTPUT_HASH'])assert(body.includes(marker),marker);
   s.state.taskLogVerified=true;
  });
  await check('task-parameters',async()=>{
   await p.getByRole('tab',{name:'CONFIGURATION',exact:true}).click();
   await visible(p,'Preparation').click();
   await p.getByText(ledger.input_dataset_id,{exact:false}).filter({visible:true}).waitFor();
   const body=await p.locator('body').innerText();assert(body.includes('input_dataset_version'));assert(body.includes('validation_fraction'));assert(body.includes(ledger.code_sha256));
  });
  await check('task-report-artifact',async()=>{
   await p.getByRole('tab',{name:'ARTIFACTS',exact:true}).click();await visible(p,'manifest.json').click();
   await visible(p,sdk.report_artifacts['manifest.json'].sha256).first().waitFor();
  });
  await check('task-report-real-download',async()=>{
   const next=p.waitForEvent('download');await p.locator('sm-labeled-row[data-id="filePathId"] button').first().click();const d=await next;assert.equal(await d.failure(),null);await s.settle();
   const actual=s.state.downloads.find(x=>x.stage==='task-report-real-download');assert(actual);assert.equal(actual.sha256,sdk.report_artifacts['manifest.json'].sha256);assert.equal(actual.bytes,sdk.report_artifacts['manifest.json'].bytes);
  });
  // Each Dataset is a separate named transformed asset; input/output relationship is in Task/provenance.
  for(const key of ['input','output']){
   const dataset=sdk.datasets[key],name=key==='input'?'input-conversations':'prepared-conversations';
   await check(key+'-dataset-list',async()=>{
    await p.goto(s.origin+'/datasets',{waitUntil:'networkidle'});
    // Navigate project card when the dataset view groups by root project.
    if(await visible(p,ledger.project).count())await visible(p,ledger.project).click();
    await visible(p,name).waitFor();await visible(p,name).click();
    await p.locator('sm-dataset-version-step').filter({hasText:'v1.0.0'}).waitFor();
   });
   await check(key+'-content-hashes',async()=>{
    await p.locator('sm-dataset-version-step').filter({hasText:'v1.0.0'}).click();
    await p.waitForFunction(id=>document.querySelector('a.arr-link')?.getAttribute('href')?.includes(id),dataset.id);
    if(!await visible(p,'CONTENT').isVisible())await p.locator('[data-id="detailsButton"]').click();
    await visible(p,'CONTENT').click();
    const table=p.locator('sm-open-dataset-version-content');
    await table.getByText(Object.keys(dataset.files)[0],{exact:true}).filter({visible:true}).waitFor();
    const body=await table.innerText();for(const [filename,info]of Object.entries(dataset.files)){assert(body.includes(filename),filename);assert(body.includes(info.sha256),info.sha256);}
    s.state[key+'Content']={datasetId:dataset.id,version:dataset.version,text:body};
   });
   let taskPage;
   await check(key+'-dataset-task-link',async()=>{
    await p.keyboard.press('Escape');
    const link=p.locator('a.arr-link').filter({hasText:'Task information'});
    [taskPage]=await Promise.all([p.waitForEvent('popup'),link.click()]);await taskPage.waitForLoadState('networkidle');assert(taskPage.url().includes(dataset.id));
   });
   await check(key+'-archive-artifact',async()=>{
    await taskPage.getByRole('tab',{name:'ARTIFACTS',exact:true}).click();await visible(taskPage,'data').click();await visible(taskPage,dataset.artifacts.data.sha256).waitFor();
   },taskPage);
   await check(key+'-archive-real-download',async()=>{
    const next=taskPage.waitForEvent('download');await taskPage.locator('sm-labeled-row[data-id="filePathId"] button').first().click();const d=await next;assert.equal(await d.failure(),null);await s.settle();
    const actual=s.state.downloads.find(x=>x.stage===key+'-archive-real-download');assert(actual);assert.equal(actual.sha256,dataset.artifacts.data.sha256);assert.equal(actual.bytes,dataset.artifacts.data.bytes);
   },taskPage);await taskPage.close();
  }
  const after=await s.inventory('after');assert.deepEqual(after,baseline);
  await s.settle();assert.equal(s.state.observerErrors.length,0);
  s.state.unknownErrors=s.state.errors.filter(e=>!(e.name==='HttpErrorResponse'&&e.status===0&&s.state.blocked.some(b=>b.url===e.url)));
  assert.equal(s.state.unknownErrors.length,0,JSON.stringify(s.state.unknownErrors));
  assert(s.state.network.filter(x=>x.api).every(x=>x.http===200&&(!('business'in x)||x.business===200)));
  const unknown=s.state.blocked.filter(x=>x.reason==='unknown endpoint; deny pending contract review');assert.equal(unknown.length,0,JSON.stringify(unknown));
  s.state.pass=true;
 }catch(e){s.state.pass=false;s.state.failure=e.stack;process.exitCode=1;}
 finally{await s.settle();s.save();await browser.close();console.log(JSON.stringify({pass:s.state.pass,steps:s.state.steps.map(x=>({name:x.name,ok:x.ok,error:x.error})),downloads:s.state.downloads,failure:s.state.failure}));}
})();
