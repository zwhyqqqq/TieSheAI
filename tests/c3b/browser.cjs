// Existing Playwright/Chromium only. Real list navigation, no fulfill/href rewriting.
const {launch,session,E,sha}=require('./browser-lib.cjs'),fs=require('fs'),path=require('path'),assert=require('assert/strict');
const ledger=JSON.parse(fs.readFileSync(path.join(E,'ledger.json'))),sdk=JSON.parse(fs.readFileSync(path.join(E,'sdk-verification.json')));
const visible=(page,text)=>page.getByText(text,{exact:true}).filter({visible:true});
(async()=>{
 const port=Number(process.argv[2]);assert([18080,8080].includes(port));
 const label='accept-'+port+(process.argv[3]?'-'+process.argv[3]:''),browser=await launch(),s=await session(browser,port,label),p=s.page;
 const check=async(name,fn,target=p)=>{const step=await s.capture(name,fn,target);if(!step.ok)throw Error(name+': '+step.error);return step;};
 try{
  await s.login();assert(s.state.steps[0].ok);const baseline=await s.inventory('before');
  await check('datasets-list',async()=>{await p.goto(s.origin+'/datasets',{waitUntil:'networkidle'});await visible(p,ledger.dataset_name).waitFor();});
  await check('versions-and-parent-graph',async()=>{
   await visible(p,ledger.dataset_name).click();
   await p.locator('sm-dataset-version-step').filter({hasText:'v1.0.0'}).waitFor();
   await p.locator('sm-dataset-version-step').filter({hasText:'v2.0.0'}).waitFor();
   await p.locator('svg.arrows path').waitFor({state:'attached'});
   const nodes=await p.locator('sm-dataset-version-step').evaluateAll(xs=>xs.map(x=>({text:x.innerText,id:x.querySelector('[data-id="processSteps"]').id,rect:x.getBoundingClientRect().toJSON(),style:x.querySelector('[data-id="processSteps"]').getAttribute('style')})));
   const arrows=await p.locator('svg.arrows path,svg.arrows polygon').evaluateAll(xs=>xs.map(x=>({type:x.tagName,d:x.getAttribute('d'),transform:x.getAttribute('transform'),points:x.getAttribute('points')})));
   assert.equal(nodes.length,2);assert.equal(arrows.filter(x=>x.type==='path').length,1);
   s.state.parentGraph={nodes,arrows};
  });
  s.state.datasets={};
  for(const key of ['v2','v1']){
   const ver=sdk.datasets[key];
   await check(key+'-content-and-id',async()=>{
    await p.locator('sm-dataset-version-step').filter({hasText:'v'+ver.version}).click();
    await p.waitForFunction(id=>document.querySelector('a.arr-link')?.getAttribute('href')?.includes(id),ver.id);
    if(!await visible(p,'CONTENT').isVisible())await p.locator('[data-id="detailsButton"]').click();
    await visible(p,'CONTENT').click();
    const table=p.locator('sm-open-dataset-version-content');
    await table.getByText(ver.files[0].name,{exact:true}).filter({visible:true}).waitFor();
    const body=await table.innerText();
    for(const f of ver.files){assert(body.includes(f.name));assert(body.includes(f.sha256));assert(body.includes(f.bytes+' B'));}
    if(key==='v1')assert(!body.includes('added.txt'));
    const link=await p.locator('a.arr-link').filter({hasText:'Task information'}).getAttribute('href');assert(link.includes(ver.id));
    s.state.datasets[key]={id:ver.id,files:ver.files,taskHref:link,contentText:body};
   });
   await check(key+'-preview',async()=>{
    await visible(p,'PREVIEW').click();
    await p.waitForTimeout(1400);
    s.state.datasets[key].previewText=await p.locator('sm-open-dataset-version-preview').innerText();
   });
   await check(key+'-download-command',async()=>{
    await visible(p,'CONTENT').click();await p.locator('[data-id="downloadButton"]').click();
    await p.getByText('clearml-data get --id '+ver.id,{exact:true}).filter({visible:true}).waitFor();
    s.state.datasets[key].downloadControl='CLI command only; no browser download';
   });
   // Escape also closes the details pane in this UI; reopen only when needed next iteration.
   await p.keyboard.press('Escape');
   let taskPage;
   await check(key+'-real-task-link',async()=>{
    const next=p.waitForEvent('popup');await p.locator('a.arr-link').filter({hasText:'Task information'}).click();taskPage=await next;
    await taskPage.waitForLoadState('networkidle');assert(taskPage.url().includes(ver.id));
   });
   await check(key+'-task-artifact-page',async()=>{
    await taskPage.getByRole('tab',{name:'ARTIFACTS',exact:true}).click();await visible(taskPage,'data').click();
    const artifact=ver.artifacts.find(x=>x.key==='data');await visible(taskPage,artifact.sha256).waitFor();
   },taskPage);
   await check(key+'-real-archive-download',async()=>{
    const next=taskPage.waitForEvent('download');await taskPage.locator('sm-labeled-row[data-id="filePathId"] button').first().click();
    const dl=await next;assert.equal(await dl.failure(),null);await s.settle();
    const artifact=ver.artifacts.find(x=>x.key==='data');const actual=s.state.downloads.find(x=>x.stage===key+'-real-archive-download');
    assert(actual);assert.equal(actual.sha256,artifact.sha256);assert.equal(actual.bytes,artifact.bytes);
   },taskPage);
   await taskPage.close();
  }
  await check('models-list',async()=>{await p.goto(s.origin+'/projects/*/models',{waitUntil:'networkidle'});await visible(p,ledger.namespace+'-TEST-FIXTURE-NOT-WEIGHTS').waitFor();});
  await check('model-from-real-row',async()=>{
   await visible(p,ledger.namespace+'-TEST-FIXTURE-NOT-WEIGHTS').dblclick();await p.locator('[data-id="downloadIcon"]').waitFor();assert(p.url().includes(sdk.model.id));
  });
  await check('model-general-file-button',async()=>{
   const next=p.waitForEvent('popup');const count=s.state.downloads.length;await p.locator('[data-id="downloadIcon"]').click();
   const filePage=await next;await filePage.waitForLoadState('networkidle');
   const text=await filePage.locator('body').innerText();assert.equal(sha(text),sdk.model.sha256);
   s.state.modelGeneralButton={url:filePage.url(),body:text,sha256:sha(text),bytes:Buffer.byteLength(text),downloadEvents:s.state.downloads.length-count,behavior:'inline JSON page'};
   await check('model-inline-content',async()=>{assert(text.includes('"trained_weights":false'));},filePage);await filePage.close();
  });
  let draft;
  await check('model-lineage-task-link',async()=>{
   await p.getByRole('tab',{name:'LINEAGE',exact:true}).click();
   const link=p.getByRole('link',{name:ledger.namespace+'-Model-Draft',exact:true});await link.waitFor();
   const href=await link.getAttribute('href');assert(href.includes(sdk.model.task));s.state.modelTaskLink={href,expectedTask:sdk.model.task};
   const next=p.waitForEvent('popup');await link.click();draft=await next;await draft.waitForLoadState('networkidle');assert(draft.url().includes(sdk.model.task));
  });
  await check('draft-task-output-model',async()=>{
   await draft.getByRole('tab',{name:'ARTIFACTS',exact:true}).click();
   // Output model is a real row in the Task artifact sidebar; select it without editing.
   const name=ledger.namespace+'-TEST-FIXTURE-NOT-WEIGHTS';
   const row=visible(draft,name);if(await row.count()===1)await row.click();
   await draft.locator('sm-experiment-models-form-view').waitFor();
   const link=draft.locator('sm-experiment-models-form-view a').filter({hasText:name});const href=await link.getAttribute('href');
   assert(href.includes(sdk.model.id));s.state.taskOutputLink={href,expectedModel:sdk.model.id};
  },draft);
  await check('draft-task-model-real-download',async()=>{
   const next=draft.waitForEvent('download');await draft.locator('sm-experiment-models-form-view button').first().click();
   const dl=await next;assert.equal(await dl.failure(),null);await s.settle();const actual=s.state.downloads.find(x=>x.stage==='draft-task-model-real-download');
   assert(actual);assert.equal(actual.sha256,sdk.model.sha256);assert.equal(actual.bytes,sdk.model.bytes);
  },draft);
  await check('task-output-link-opens-same-model',async()=>{
   const next=draft.waitForEvent('popup');await draft.locator('sm-experiment-models-form-view a').first().click();const back=await next;
   await back.waitForLoadState('networkidle');assert(back.url().includes('/models/'+sdk.model.id));s.state.outputLinkDestination=back.url();
   await check('linked-model-page',async()=>{await back.getByRole('tab',{name:'GENERAL',exact:true}).waitFor();},back);await back.close();
  },draft);
  await draft.close();
  const after=await s.inventory('after');assert.deepEqual(after,baseline);
  await s.settle();assert.equal(s.state.observerErrors.length,0);
  s.state.unknownErrors=s.state.errors.filter(e=>!(e.name==='HttpErrorResponse'&&e.status===0&&s.state.blocked.some(b=>b.url===e.url)));
  // Preserve all unclassified errors, never ignore unknown minified exceptions.
  assert.equal(s.state.unknownErrors.length,0,JSON.stringify(s.state.unknownErrors));
  const available=s.state.errors.map((e,index)=>({e,index})),used=new Set();s.state.pageErrorCorrelations=[];
  for(const pe of s.state.pageErrors||[]){
   const match=available.find(({e,index})=>!used.has(index)&&e.stage===pe.stage&&e.name==='HttpErrorResponse'&&e.status===0&&e.constructor===pe.message&&pe.name===''&&Math.abs(e.observedAt-pe.observedAt)<2000&&s.state.blocked.some(b=>b.url===e.url));
   assert(match,'Uncorrelated pageerror: '+JSON.stringify(pe));used.add(match.index);s.state.pageErrorCorrelations.push({pageError:pe,structuredError:match.e});
  }
  assert(s.state.network.filter(x=>x.api).every(x=>x.http===200&&(!('business'in x)||x.business===200)));
  s.state.inputModelConsumption='N/A';s.state.pass=true;
 }catch(e){s.state.pass=false;s.state.failure=e.stack;process.exitCode=1;}
 finally{await s.settle();s.save();await browser.close();console.log(JSON.stringify({port,pass:s.state.pass,steps:s.state.steps.map(x=>({name:x.name,ok:x.ok,error:x.error})),downloads:s.state.downloads,modelGeneralButton:s.state.modelGeneralButton,failure:s.state.failure}));}
})();
