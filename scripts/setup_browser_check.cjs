const fs=require('node:fs/promises'),path=require('node:path');const {spawn}=require('node:child_process');const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'..'),base='http://127.0.0.1:8778',out=path.join(ROOT,'output/evidence');const wait=ms=>new Promise(r=>setTimeout(r,ms));const check=(v,m)=>{if(!v)throw Error(m);};
async function main(){await fs.mkdir(out,{recursive:true});const server=spawn(process.env.FINANCE_PYTHON||'python',[path.join(ROOT,'app.py'),'--port','8778','--db',path.join(ROOT,'tmp','setup-'+Date.now()+'.sqlite')],{cwd:ROOT,windowsHide:true,stdio:'ignore',env:{...process.env,FINANCE_AI_DISABLE:'1'}});let b;
try{for(let i=0;i<60;i++){try{const r=await fetch(base+'/api/config');await r.arrayBuffer();if(r.ok)break;}catch{}await wait(100);}b=await chromium.launch({headless:true,channel:'msedge'});const p=await b.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'}),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto(base);await p.waitForFunction(()=>typeof state!=='undefined'&&state?.adventure);
const nav=async id=>{await p.locator('aside nav a[href="#'+id+'"]').click();await p.waitForFunction(id=>activePage===id,id);};
for(const id of ['overview','records','insights','goals','memories','smart-plans','assistant']){await nav(id);check(await p.locator('main>section:visible').count()<=2,'Sections leaked into '+id);}
await p.goBack();check(await p.evaluate(()=>activePage)==='smart-plans','Back navigation failed');await p.goForward();check(await p.evaluate(()=>activePage)==='assistant','Forward navigation failed');
await nav('overview');await p.locator('#demo').click();await p.locator('#count').filter({hasText:'30'}).waitFor();
async function talk(text){await p.locator('#setup-message').fill(text);await p.locator('#setup-send').click();await p.waitForFunction(()=>!setupBusy&&setupResult!==null);}
async function confirm(){await p.locator('#setup-confirm').click();await p.locator('#setup-dialog').waitFor({state:'hidden'});}
await nav('goals');await p.locator('#new-adventure-goal').click();await talk('我想为旅行攒钱');check(!(await p.locator('#setup-confirm').count()),'Goal committed with missing target');await talk('想攒3000元');await p.locator('#setup-preview').filter({hasText:'3,000.00'}).waitFor();
check((await(await fetch(base+'/api/state')).json()).adventure.goals.length===0,'Chat saved before approval');await p.screenshot({path:path.join(out,'conversational-goal.png')});await confirm();
await p.locator('#savings-goals [data-adventure-entry]').click();await talk('存入100元');await confirm();await p.locator('.savings-amount').filter({hasText:'100.00'}).waitFor();
await nav('overview');await p.locator('#chat-budget').click();await talk('餐饮预算600元');await confirm();await p.locator('#budget-list').filter({hasText:'600.00'}).waitFor();
await p.locator('#header-quick-entry').click();await talk('昨天食堂午饭25.20元');await confirm();await p.locator('#rows').filter({hasText:'25.20'}).waitFor();
await nav('insights');await p.locator('#review-form button').click();await p.getByRole('button',{name:'记录复盘心得',exact:true}).click();await talk('本月买东西之前，先列一份清单再决定。');await confirm();
await nav('memories');await p.locator('.memory-demo summary').click();await p.locator('#memory-seed').click();await p.locator('#setup-dialog').waitFor({state:'visible'});await p.locator('#setup-close').click();await nav('records');await p.locator('#rows tr').filter({hasText:'伙食费'}).first().locator('[data-purpose]').click();await talk('这是食堂伙食费');await confirm();
await nav('smart-plans');await p.locator('#chat-plan').click();await talk('六个月存6000元，房租不能减');await p.locator('[data-setup-confirm=balanced]').click();await p.locator('#setup-dialog').waitFor({state:'hidden'});
check(!await p.locator('#trial-open,#adventure-scene').count(),'Game controls must be removed');
await nav('overview');await p.screenshot({path:path.join(out,'pages-home.png')});await nav('assistant');await p.screenshot({path:path.join(out,'pages-assistant.png')});
check(!((await p.locator('body').innerText()).includes('软件工程课程项目')),'Course footer still visible');
check(await p.locator('body').evaluate(el=>parseInt(getComputedStyle(el).fontSize))>=16,'Main text too small');
await p.setViewportSize({width:390,height:844});await p.locator('#page-picker').selectOption('goals');check(await p.evaluate(()=>activePage)==='goals','Mobile page picker failed');check(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile overflow');await p.screenshot({path:path.join(out,'pages-mobile.png')});
await p.locator('#header-quick-entry').click();await p.screenshot({path:path.join(out,'conversation-mobile.png')});await p.locator('#setup-close').click();check(errors.length===0,errors.join('; '));
const result={passed:true,checked_at:new Date().toISOString(),synthetic_only:true,external_model_calls:0,checks:['seven separate views','back and forward','goal clarification before save','goal allocation via chat','budget via chat','quick entry via chat','reflection via chat','purpose via chat','plan via chat','game UI removed','readable text','footer removed','390px layout']};await fs.writeFile(path.join(out,'setup_browser_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
}finally{if(b)await b.close();server.kill();}}
main().catch(e=>{console.error(e);process.exitCode=1;});
