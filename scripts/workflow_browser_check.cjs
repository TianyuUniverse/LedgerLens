// Real UI replay on a new temporary database. No external model calls.
const fs=require('node:fs/promises');
const path=require('node:path');
const {spawn}=require('node:child_process');
const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'..'),base='http://127.0.0.1:8771';
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function check(ok,message){if(!ok)throw Error(message);}

async function main(){
  const out=path.join(ROOT,'output/evidence');await fs.mkdir(out,{recursive:true});await fs.mkdir(path.join(ROOT,'tmp'),{recursive:true});
  const db=path.join(ROOT,'tmp',`workflows-${Date.now()}.sqlite`);
  const server=spawn(process.env.FINANCE_PYTHON||'python',[path.join(ROOT,'app.py'),'--port','8771','--db',db],{cwd:ROOT,stdio:'ignore',windowsHide:true,env:{...process.env,FINANCE_AI_DISABLE:'1'}});
  let browser;
  try{
    for(let i=0;i<50;i++){try{const ready=await fetch(base+'/api/config');await ready.arrayBuffer();if(ready.ok)break;}catch{}await wait(100);}
    browser=await chromium.launch({headless:true,channel:process.env.FINANCE_BROWSER||'msedge'});
    const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage(),errors=[];
    page.on('pageerror',e=>errors.push(e.message));await page.goto(base);await page.locator('#mode').filter({hasText:'本地规则模式'}).waitFor();
    await page.locator('#demo').click();await page.getByRole('status').filter({hasText:'新增 30 笔'}).waitFor();
    await page.goto(base+'#memories');await page.locator('.memory-demo summary').click();await page.locator('#memory-seed').click();await page.locator('#setup-dialog').waitFor({state:'visible'});await page.locator('#setup-manual').click();await page.locator('#purpose-dialog').waitFor({state:'visible'});
    await page.locator('#cancel-purpose').click();
    async function confirmPayment(phrase,category,purpose){
      await page.goto(base+'#records');const row=page.locator('#rows tr').filter({hasText:phrase}).first();await row.locator('[data-purpose]').click();await page.locator('#setup-manual').click();
      await page.locator('#purpose-kind').selectOption('expense');await page.locator('#purpose-category').selectOption(category);
      await page.locator('#purpose-text').fill(purpose);await page.locator('#auto-memory').check();
      await page.locator('#purpose-form button[type=submit]').click();await page.locator('#purpose-dialog').waitFor({state:'hidden'});
      await page.goto(base+'#memories');await page.locator('#memory-list').filter({hasText:purpose}).waitFor();
    }
    await confirmPayment('伙食费','Food','校园伙食费');await confirmPayment('电费和空调费','Utilities','舍友代收电费和空调费');
    await page.locator('#memory-followup').click();await page.getByRole('status').filter({hasText:'记忆自动识别 2 笔'}).waitFor();
    let state=await (await fetch(base+'/api/state')).json();
    const meal=state.transactions.find(r=>r.note==='伙食费'&&r.date.startsWith('2026-09'));
    const utility=state.transactions.find(r=>r.note==='电费和空调费'&&r.date.startsWith('2026-09'));
    const tuition=state.transactions.find(r=>r.note==='新学期学费');
    check(meal.category==='Food'&&meal.category_source==='memory','Meal memory not applied');
    check(utility.kind==='expense'&&utility.category==='Utilities','Utilities did not correct kind');
    check(tuition.category==='Education'&&tuition.review_status==='needs_review','School counterexample failed');
    await page.locator('#memories').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'purpose-memory.png')});
    await page.locator('[data-memory-edit]').first().click();await page.locator('#setup-manual').click();await page.locator('#purpose-dialog').waitFor({state:'visible'});
    await page.locator('#purpose-text').fill('舍友代收水电用途记忆');await page.locator('#purpose-form button[type=submit]').click();await page.locator('#purpose-dialog').waitFor({state:'hidden'});
    await page.locator('#memory-list').filter({hasText:'第 2 版'}).waitFor();
    await page.locator('[data-memory-toggle]').first().click();await page.locator('#memory-list').filter({hasText:'已停用'}).waitFor();
    await page.locator('[data-memory-toggle]').first().click();await page.locator('#memory-list').filter({hasText:'自动分类'}).waitFor();
    await page.goto(base+'#smart-plans');if(await page.locator('#manual-smart-plan').evaluate(el=>!el.open))await page.locator('#manual-smart-plan summary').click();await page.locator('#smart-plan-form button[type=submit]').click();await page.locator('#plan-options .plan-option').first().waitFor();
    check(await page.locator('#plan-options .plan-option').count()===3,'Missing plan alternatives');
    await page.locator('[data-save-style=balanced]').click();await page.getByRole('status').filter({hasText:'审核后的方案已保存'}).waitFor();
    await page.locator('#smart-plans').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'checked-savings-plans.png')});
    // Any record revision makes the previously generated preview stale.
    await page.goto(base+'#records');await page.locator('#rows tr').filter({hasText:'9月淘宝服饰'}).locator('[data-edit]').selectOption('Other');await page.getByRole('status').filter({hasText:'分类已更新'}).waitFor();
    await page.goto(base+'#smart-plans');await page.locator('[data-save-style=shopping_first]').click();await page.getByRole('status').filter({hasText:'账单已发生变化'}).waitFor();
    await page.goto(base+'#monthly-review');await page.locator('#review-month').fill('2026-09');await page.locator('#review-form button').click();await page.locator('#review-result').filter({hasText:'小额消费'}).waitFor();
    await page.goto(base+'#assistant');
    await page.locator('#question').fill('九月为什么比八月花得多？');await page.locator('#ask-form button').click();await page.locator('#answer').filter({hasText:'2026-08'}).waitFor();
    await page.locator('#question').fill('我想六个月存6000，房租不能减，娱乐每月至少留200。');await page.locator('#ask-form button').click();await page.locator('#answer').filter({hasText:'已生成三种方案'}).waitFor();
    await page.locator('#question').fill('我不想减少餐饮。');await page.locator('#ask-form button').click();await page.locator('#answer').filter({hasText:'不想减少餐饮'}).waitFor();
    check(await page.locator('#chat-history .conversation-turn').count()===2,'Conversation history not retained');
    await page.getByRole('button',{name:'查看预算并选择方案'}).last().click();await page.locator('#plan-options').filter({hasText:'餐饮 · 固定'}).waitFor();
    const visibleText=await page.locator('body').innerText();
    const untranslated=visibleText.match(/[A-Za-z][A-Za-z -]{2,}/g)||[];
    check(untranslated.every(word=>['LedgerLens','UTF-','CSV','AI'].includes(word.trim())), 'Untranslated UI text: '+untranslated.join(', '));
    await page.locator('#smart-target').fill('');await page.goto(base+'#smart-plans');if(await page.locator('#manual-smart-plan').evaluate(el=>!el.open))await page.locator('#manual-smart-plan summary').click();await page.locator('#smart-plan-form button[type=submit]').click();
    check((await page.locator('#smart-target').evaluate(el=>el.validationMessage)).includes('请填写'),'Native form validation is not Chinese');
    await page.locator('#smart-target').fill('6000');
    await page.goto(base+'#assistant');await page.screenshot({path:path.join(out,'finance-conversation.png')});
    await page.locator('#new-conversation').click();check(await page.locator('#chat-history .conversation-turn').count()===0,'Conversation reset failed');
    await page.goto(base+'#memories');await page.locator('[data-memory-delete]').first().click();await page.locator('#memory-delete-confirm').click();await page.getByRole('status').filter({hasText:'记忆已删除'}).waitFor();
    state=await (await fetch(base+'/api/state')).json();check(state.transactions.find(r=>r.id===utility.id).category==='Utilities','Memory delete rewrote history');
    const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true});const mp=await mobile.newPage();mp.on('pageerror',e=>errors.push(e.message));
    await mp.goto(base);await mp.locator('#count').filter({hasText:'38'}).waitFor();await mp.goto(base+'#memories');
    await mp.screenshot({path:path.join(out,'workflows-mobile.png'),fullPage:true});check(!(await mp.evaluate(()=>document.documentElement.scrollWidth>390)),'Mobile horizontal overflow');
    await mobile.close();await context.close();check(errors.length===0,'Browser script errors: '+errors.join(','));
    const evidence={run_at:new Date().toISOString(),passed:true,page_errors:errors,model:'Disabled for browser replay',checks:['purpose confirmation and memory save','approved future automatic reuse','school tuition counterexample','transfer-to-expense correction','memory edit version','disable and enable','three savings alternatives','explicit save','stale preview rejection','monthly review','Chinese multi-turn comparison and plans','constraints carried forward','new conversation','delete without rewriting labels','390px mobile overflow','Chinese system text scan','Chinese native form validation']};
    await fs.writeFile(path.join(out,'workflow_browser_check.json'),JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence,null,2));
  }finally{if(browser)await browser.close();server.kill();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
