const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});try{
 const page=await browser.newPage();page.setDefaultTimeout(12000);const base=process.env.BASE_URL||'http://localhost:5180';
 await page.route('https://fonts.googleapis.com/**',r=>r.abort());await page.route('https://fonts.gstatic.com/**',r=>r.abort());
 const account=await page.request.post(base+'/api/auth/register',{headers:{'X-Panned-Out-Request':'1'},form:{email:`save-${Date.now()}@example.test`,password:'suggestion-test-password2026'}});assert.equal(account.status(),201);
 await page.goto(base+'/meal-plans');const region=page.getByRole('region',{name:'Browse recipes',exact:true});await region.getByRole('link').first().waitFor();
 const name=await region.locator('h3').first().innerText();const button=region.getByRole('button',{name:`Save ${name} to My Recipes`,exact:true});await button.click();
 const form=region.getByRole('form',{name:`Save ${name}`,exact:true});await form.getByRole('button',{name:'Save recipe',exact:true}).click();await region.getByRole('button',{name:`${name} saved to My Recipes`,exact:true}).waitFor();
 await page.reload();await region.getByRole('button',{name:`${name} saved to My Recipes`,exact:true}).waitFor();
 await region.getByRole('link').first().click();await page.locator('.journal-intro h1').waitFor();await page.getByRole('button',{name:`${name} saved to My Recipes`,exact:true}).waitFor();
 let saved=await (await page.request.get(base+'/api/recipes')).json();assert.equal(saved.length,1);assert.ok(saved[0].suggestedId);
 await page.goto(base+'/meal-plans');await region.getByRole('link').first().waitFor();
 const next=await region.locator('h3').nth(1).innerText();await page.route('**/api/recipes/*/save',r=>r.fulfill({status:503,contentType:'application/json',body:'{"error":"Test save failed"}'}));
 await region.getByRole('button',{name:`Save ${next} to My Recipes`,exact:true}).click();const second=region.getByRole('form',{name:`Save ${next}`,exact:true});await second.getByRole('button',{name:'Save recipe',exact:true}).click();await region.getByRole('alert').getByText(/Test save failed/).waitFor();
 await page.unroute('**/api/recipes/*/save');await second.getByRole('button',{name:'Save recipe',exact:true}).click();await region.getByRole('button',{name:`${next} saved to My Recipes`,exact:true}).waitFor();
 const catalog=await (await page.request.get(base+'/api/recipes?filter=suggested')).json();
 for(const category of ['High Protein','Low Calorie','Keto']) {
  const suggestion=catalog.find(recipe=>recipe.plan===category);assert.ok(suggestion);
  const response=await page.request.post(base+'/api/recipes/'+encodeURIComponent(suggestion.id)+'/save',{headers:{'X-Panned-Out-Request':'1'},form:{mealType:'Dinner'}});assert.ok([200,201].includes(response.status()));
  await page.goto(base+'/recipes');await page.getByRole('button',{name:category,exact:true}).click();await page.getByRole('heading',{name:suggestion.name,exact:true}).waitFor();
 }
 console.log('PASS saved High Protein, Low Calorie and Keto recipes appear under their dietary filters');
 console.log('PASS card/detail save state, reload, single copy, failure and retry');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
