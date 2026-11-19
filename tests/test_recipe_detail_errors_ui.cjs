const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');const assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});try{
const p=await b.newPage();const base=process.env.BASE_URL||'http://localhost:5181';await p.route('https://fonts.googleapis.com/**',r=>r.abort());await p.route('https://fonts.gstatic.com/**',r=>r.abort());const headers={'X-Panned-Out-Request':'1'};
await p.request.post(base+'/api/auth/register',{headers,form:{email:`detail-errors-${Date.now()}@example.test`,password:'detail-error-test-password'}});
for(const id of ['999999999','suggested%3A999999']){await p.goto(base+'/recipes/'+id);await p.getByRole('heading',{name:'Recipe not found',exact:true}).waitFor();assert.equal(await p.getByRole('button',{name:'Retry opening recipe',exact:true}).count(),0);}
await p.route('**/api/recipes',r=>r.fulfill({status:503,contentType:'application/json',body:'{"error":"Temporarily unavailable"}'}));await p.goto(base+'/recipes/999999999');await p.getByRole('heading',{name:'Unable to open recipe',exact:true}).waitFor();await p.getByRole('button',{name:'Retry opening recipe',exact:true}).waitFor();
await p.unroute('**/api/recipes');await p.getByRole('button',{name:'Retry opening recipe',exact:true}).click();await p.getByRole('heading',{name:'Recipe not found',exact:true}).waitFor();assert.equal(await p.getByRole('button',{name:'Retry opening recipe',exact:true}).count(),0);
console.log('PASS missing private/catalog recipes have no retry; transient failure supports retry and recovers to not-found');
}finally{await b.close()}})().catch(e=>{console.error(e);process.exit(1)});
