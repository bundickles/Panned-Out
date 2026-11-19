const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');const assert=require('node:assert/strict');
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRz0AAAAASUVORK5CYII=','base64');
const success={status:'success',requiresConfirmation:true,recipe:{name:'AI Rice Bowl',ingredients:['1 cup rice','1 cup beans'],steps:['Cook rice.','Add beans.']},warnings:['Review AI ingredients before cooking.']};
(async()=>{const b=await chromium.launch({headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'],...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});try{
 const p=await b.newPage();p.setDefaultTimeout(10000);const base=process.env.BASE_URL||'http://localhost:5186',headers={'X-Panned-Out-Request':'1'};
 await p.route('https://fonts.googleapis.com/**',r=>r.abort());await p.route('https://fonts.gstatic.com/**',r=>r.abort());
 assert.equal((await p.request.post(base+'/api/auth/register',{headers,form:{email:`photo-ui-${Date.now()}@example.test`,password:'photo-ui-test-password'}})).status(),201);
 let mode='success',available=true,posts=0,release;
 await p.route('**/api/ai/photo-recipe',async r=>{
  if(r.request().method()==='GET')return r.fulfill({json:{available}});
  posts++;assert.ok(['image/png','image/jpeg'].includes(r.request().headers()['content-type']));assert.equal(r.request().headers()['x-panned-out-request'],'1');if(r.request().headers()['content-type']==='image/png')assert.deepEqual(r.request().postDataBuffer(),png);else assert.equal(r.request().postDataBuffer().readUInt16BE(0),0xffd8);
  if(mode==='held')await new Promise(resolve=>{release=resolve});
  if(mode==='error')return r.fulfill({status:503,json:{error:'Temporary photo failure'}});
  if(mode==='none')return r.fulfill({json:{status:'no_result',recipe:null,message:'No recognizable food found.'}});
  if(mode==='malformed')return r.fulfill({json:{status:'success',requiresConfirmation:true,recipe:{name:'Broken'}}});
  await r.fulfill({json:success}).catch(()=>{});
 });
 const upload=()=>p.locator('#ai-photo-upload').setInputFiles({name:'food.png',mimeType:'image/png',buffer:png});
 const studio=()=>p.getByRole('region',{name:'AI photo recipe',exact:true});
 await p.goto(base+'/ai-photo');
 await p.locator('#ai-photo-upload').setInputFiles({name:'food.webp',mimeType:'image/webp',buffer:png});await p.getByRole('alert').getByText('Choose a JPEG or PNG image.',{exact:true}).waitFor();assert.equal(posts,0);
 await p.locator('#ai-photo-upload').setInputFiles({name:'large.png',mimeType:'image/png',buffer:Buffer.alloc(5*1024*1024+1)});await p.getByRole('alert').getByText('Choose an image no larger than 5 MB.',{exact:true}).waitFor();
 await upload();await studio().getByRole('button',{name:'Analyze photo',exact:true}).click();const review=p.getByRole('region',{name:'Review generated recipe',exact:true});await review.getByLabel('Recipe name',{exact:true}).waitFor();assert.equal((await (await p.request.get(base+'/api/recipes')).json()).length,0);
 await review.getByRole('button',{name:'Save recipe',exact:true}).click();await review.getByRole('alert').getByText(/Review the ingredients/).waitFor();assert.equal((await (await p.request.get(base+'/api/recipes')).json()).length,0);
 await review.getByLabel('Recipe name',{exact:true}).fill('My reviewed rice bowl');await review.getByLabel('I reviewed the ingredients and instructions.',{exact:true}).check();
 await p.route('**/api/recipes',r=>r.request().method()==='POST'?r.fulfill({status:503,json:{error:'Test save failure'}}):r.continue());await review.getByRole('button',{name:'Save recipe',exact:true}).click();await review.getByRole('alert').getByText('Test save failure',{exact:true}).waitFor();assert.equal(await review.getByLabel('Recipe name',{exact:true}).inputValue(),'My reviewed rice bowl');await p.unroute('**/api/recipes');
 await review.getByRole('button',{name:'Save recipe',exact:true}).click();await p.waitForURL(/\/recipes\/\d+$/);await p.getByRole('heading',{name:'My reviewed rice bowl',exact:true}).waitFor();await p.reload();await p.getByRole('heading',{name:'My reviewed rice bowl',exact:true}).waitFor();assert.equal((await (await p.request.get(base+'/api/recipes')).json()).length,1);
 console.log('PASS raw upload/validation, editable draft, explicit review, no auto-save, save failure/retry and detail reload');
 for(const value of ['none','error','malformed']){mode=value;await p.goto(base+'/ai-photo');await upload();await studio().getByRole('button',{name:'Analyze photo',exact:true}).click();if(value==='none')await studio().getByText('No recognizable food found.',{exact:true}).waitFor();else await studio().getByRole('alert').waitFor();assert.equal(await p.getByRole('region',{name:'Review generated recipe',exact:true}).count(),0);}
 mode='success';await studio().getByRole('button',{name:'Analyze photo',exact:true}).click();await review.getByLabel('Recipe name',{exact:true}).waitFor();
 mode='held';await studio().getByRole('button',{name:'Analyze photo',exact:true}).click();await studio().getByRole('button',{name:'Cancel analysis',exact:true}).click();if(release)release();await p.waitForTimeout(150);assert.equal(await review.count(),0);
 mode='held';await studio().getByRole('button',{name:'Analyze photo',exact:true}).click();await p.getByRole('button',{name:'Remove photo',exact:true}).click();if(release)release();await p.waitForTimeout(150);assert.equal(await studio().count(),0);assert.equal(await review.count(),0);
 available=false;await upload();await studio().getByText('Photo recognition is not configured yet.',{exact:false}).waitFor();assert.equal(await studio().getByRole('button',{name:'Analyze photo',exact:true}).isDisabled(),true);
 available=true;mode='none';await p.getByRole('button',{name:'Use camera',exact:true}).click();await p.waitForFunction(()=>document.querySelector('video')?.videoWidth>0);await p.getByRole('button',{name:'Capture photo',exact:true}).click();await studio().getByRole('button',{name:'Analyze photo',exact:true}).click();await studio().getByText('No recognizable food found.',{exact:true}).waitFor();console.log('PASS fake camera capture sends a real JPEG through the same analysis flow');
 console.log('PASS no-result, malformed output, server error/manual retry, cancellation/stale result and missing configuration');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
