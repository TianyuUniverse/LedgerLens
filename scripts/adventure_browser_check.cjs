// Goal journey evidence on isolated synthetic data; no provider calls.
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {spawn}=require('node:child_process');const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'..'),base='http://127.0.0.1:8773',out=path.join(ROOT,'output/evidence');
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function check(value,message){if(!value)throw Error(message);}

async function main(){
  await fs.mkdir(out,{recursive:true});await fs.mkdir(path.join(ROOT,'tmp'),{recursive:true});
  const server=spawn(process.env.FINANCE_PYTHON||'python',[path.join(ROOT,'app.py'),'--port','8773','--db',path.join(ROOT,'tmp',`adventure-${Date.now()}.sqlite`)],{cwd:ROOT,windowsHide:true,stdio:'ignore',env:{...process.env,FINANCE_AI_DISABLE:'1'}});
  let browser,page;
  try{
    for(let i=0;i<60;i++){try{const r=await fetch(base+'/api/config');await r.arrayBuffer();if(r.ok)break;}catch{}await wait(100);}
    browser=await chromium.launch({headless:true,channel:process.env.FINANCE_BROWSER||'msedge'});
    const context=await browser.newContext({viewport:{width:1440,height:1650}});page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base);await page.locator('#adventure-level').filter({hasText:'第 1 级'}).waitFor();
    await page.locator('#adventure').screenshot({path:path.join(out,'adventure-start.png')});
    await page.locator('#new-adventure-goal').click();await page.locator('#adventure-goal-title').fill('暑假旅行基金');await page.locator('#adventure-goal-target').fill('1000');
    await page.locator('#adventure-goal-form button[type=submit]').click();await page.locator('#adventure-goal-dialog').waitFor({state:'hidden'});
    await page.locator('#adventure-focus').filter({hasText:'暑假旅行基金'}).waitFor();
    const state=async()=>await (await fetch(base+'/api/state')).json();
    let data=await state();const goalId=data.adventure.goals[0].id;check(data.adventure.xp===20,'First goal XP mismatch');
    await page.locator('#demo').click();await page.getByRole('status').filter({hasText:'新增 30 笔'}).waitFor();
    const xpAfterImport=(await state()).adventure.xp;
    await page.locator('#demo').click();await page.getByRole('status').filter({hasText:'跳过 30 笔重复'}).waitFor();check((await state()).adventure.xp===xpAfterImport,'Duplicate import earned XP');
    // Review a true own-account transfer without changing its financial meaning.
    await page.locator('[data-adventure-quest=review]').click();await page.locator('#purpose-dialog').waitFor({state:'visible'});
    await page.locator('#purpose-text').fill('本人账户之间的正常转账');await page.locator('#remember-purpose').uncheck();await page.locator('#purpose-form button[type=submit]').click();await page.locator('#purpose-dialog').waitFor({state:'hidden'});
    await page.locator('#adventure-level').filter({hasText:'第 2 级'}).waitFor();await page.locator('[data-adventure-theme=ocean]').click();await page.locator('#adventure-world.ocean').waitFor();
    await page.locator('#memory-seed').click();await page.locator('#purpose-dialog').waitFor({state:'visible'});await page.locator('#cancel-purpose').click();
    await page.locator('#rows tr').filter({hasText:'伙食费'}).first().locator('[data-purpose]').click();await page.locator('#purpose-kind').selectOption('expense');await page.locator('#purpose-category').selectOption('Food');await page.locator('#purpose-text').fill('校园伙食费');await page.locator('#auto-memory').check();await page.locator('#purpose-form button[type=submit]').click();await page.locator('#purpose-dialog').waitFor({state:'hidden'});
    await page.locator('[data-adventure-quest=reflect]').click();await page.locator('#adventure-reflect-month').fill('2026-09');await page.locator('#adventure-reflect-note').fill('本月购物开支较多，下个月先列清单再购买。');await page.locator('#adventure-reflect-form button[type=submit]').click();await page.locator('#adventure-reflect-dialog').waitFor({state:'hidden'});
    await page.locator('#smart-plan-form button[type=submit]').click();await page.locator('[data-save-style=balanced]').click();await page.getByRole('status').filter({hasText:'审核后的方案已保存'}).waitFor();
    async function allocate(amount,kind='deposit'){
      await page.locator('#adventure-focus [data-adventure-entry]').click();await page.locator('#adventure-entry-kind').selectOption(kind);await page.locator('#adventure-entry-amount').fill(amount);await page.locator('#adventure-entry-note').fill('已经为旅行留出的储蓄');await page.locator('#adventure-entry-form button[type=submit]').click();await page.locator('#adventure-entry-dialog').waitFor({state:'hidden'});
      await page.getByRole('status').filter({hasText:'储蓄进展已记录'}).waitFor();
    }
    await allocate('250');await page.locator('.goal-percent').filter({hasText:'25'}).waitFor();check((await state()).adventure.xp===205,'Quarter milestone mismatch');
    await page.getByRole('button',{name:'关闭提示',exact:true}).click();
    await page.locator('#adventure').screenshot({path:path.join(out,'adventure-quarter.png')});
    await allocate('100','withdraw');await allocate('100');check((await state()).adventure.xp===205,'Milestone XP repeated after withdraw');
    const key=crypto.randomUUID().replaceAll('-','');
    await page.evaluate(async({goalId,key})=>{
      const {token}=await(await fetch('/api/config')).json();
      const body={goal_id:goalId,kind:'deposit',amount:'250',note:'同一操作重试',request_id:key};
      for(let i=0;i<2;i++){const r=await fetch('/api/adventure/entries',{method:'POST',headers:{'Content-Type':'application/json','X-Ledger-Token':token},body:JSON.stringify(body)});if(!r.ok)throw Error('Allocation retry failed');await r.json();}
    },{goalId,key});
    await page.reload();await page.locator('.goal-percent').filter({hasText:'50'}).waitFor();
    await allocate('500');await page.locator('.goal-percent').filter({hasText:'100'}).waitFor();await page.locator('#adventure-level').filter({hasText:'第 4 级'}).waitFor();
    await page.locator('[data-adventure-theme=space]').click();await page.locator('#adventure-world.space').waitFor();
    data=await state();check(data.adventure.xp===375,'Final XP mismatch');check(data.adventure.daily_quests.every(q=>q.complete),'Daily quests not all connected');
    check(data.adventure.badges.some(b=>b.id==='first_finish'&&b.earned),'Goal-completion badge missing');
    await page.getByRole('button',{name:'关闭提示',exact:true}).click();
    await page.locator('#adventure').screenshot({path:path.join(out,'adventure-complete.png')});
    await page.locator('#adventure-focus [data-adventure-entry]').click();await page.locator('#adventure-entry-kind').selectOption('withdraw');await page.locator('#adventure-entry-amount').fill('1001');await page.locator('#adventure-entry-form button[type=submit]').click();await page.locator('#adventure-entry-error').filter({hasText:'不能超过'}).waitFor();await page.locator('[data-close-adventure=adventure-entry-dialog]').click();
    await page.locator('[data-adventure-archive]').click();await page.locator('#adventure-confirm-archive').click();await page.locator('#adventure-archive-dialog').waitFor({state:'hidden'});await page.locator('.archived-goals summary').click();await page.locator('[data-adventure-restore]').click();await page.locator('#adventure-focus').filter({hasText:'暑假旅行基金'}).waitFor();
    await page.reload();await page.locator('#adventure-level').filter({hasText:'第 4 级'}).waitFor();check((await state()).adventure.xp===375,'Page reload changed XP');
    const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true});const mp=await mobile.newPage();mp.on('pageerror',e=>errors.push(e.message));await mp.goto(base);await mp.locator('#adventure-focus').filter({hasText:'暑假旅行基金'}).waitFor();
    await mp.locator('#adventure').screenshot({path:path.join(out,'adventure-mobile.png')});check(!(await mp.evaluate(()=>document.documentElement.scrollWidth>390)),'Game has mobile horizontal overflow');
    await mobile.close();await context.close();check(errors.length===0,'Page errors: '+errors.join(','));
    const evidence={run_at:new Date().toISOString(),passed:true,model_calls:false,page_errors:errors,goal_target_fen:100000,goal_balance_fen:data.adventure.goals[0].balance_fen,final_xp:375,level:4,
      checks:['create personal goal','import mission and duplicate rejection','review mission on real pending record','memory badge','reflection mission','saved-plan badge','quarter/half/complete scenery','withdraw and redeposit without extra XP','idempotent allocation retry','theme unlocks','goal-completion badge','invalid withdrawal','archive and restore','persistent progress on reload','390px mobile layout']};
    await fs.writeFile(path.join(out,'adventure_browser_check.json'),JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence,null,2));
  }catch(error){if(page)await page.screenshot({path:path.join(ROOT,'tmp','adventure-failure.png'),fullPage:true}).catch(()=>{});throw error;}
  finally{if(browser)await browser.close();server.kill();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
