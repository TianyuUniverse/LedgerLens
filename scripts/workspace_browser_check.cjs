// Synthetic data only: purpose review, WeChat XLSX and ordinary savings.
const fs=require('node:fs/promises'),path=require('node:path');
const {spawn,execFileSync}=require('node:child_process');const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'..'),base='http://127.0.0.1:8780',out=path.join(ROOT,'output/evidence');
const wait=ms=>new Promise(r=>setTimeout(r,ms)),check=(v,m)=>{if(!v)throw Error(m);};
async function main(){
  const python=process.env.FINANCE_PYTHON||'python';await fs.mkdir(out,{recursive:true});await fs.mkdir(path.join(ROOT,'tmp'),{recursive:true});
  const fixture=path.join(ROOT,'tmp','wechat-synthetic.xlsx');execFileSync(python,['-c','from tests.test_wechat_import import workbook,payment;from pathlib import Path;import sys;Path(sys.argv[1]).write_bytes(workbook([payment("ui-001"),payment("ui-002",当前状态="已全额退款"),payment("ui-003",交易对方="示例大学",商品="校园充值",备注="/")]))',fixture],{cwd:ROOT,windowsHide:true});
  const server=spawn(python,[path.join(ROOT,'app.py'),'--port','8780','--db',path.join(ROOT,'tmp','workspace-'+Date.now()+'.sqlite')],{cwd:ROOT,windowsHide:true,stdio:'ignore',env:{...process.env,FINANCE_AI_DISABLE:'1'}});let browser,page;
  try{
    for(let i=0;i<60;i++){try{const r=await fetch(base+'/api/config');await r.arrayBuffer();if(r.ok)break;}catch{}await wait(100);}
    browser=await chromium.launch({headless:true,channel:'msedge'});page=await browser.newPage({viewport:{width:1440,height:1050},reducedMotion:'reduce'});const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base+'#memories');await page.waitForFunction(()=>typeof state!=='undefined'&&state?.adventure);
    check(!await page.locator('#trial-open,#adventure-scene,#adventure-toast').count(),'Game controls still loaded');
    await page.locator('.memory-demo summary').click();await page.locator('#memory-seed').click();await page.locator('#setup-dialog').waitFor({state:'visible'});await page.locator('#setup-close').click();
    check(await page.locator('[data-memory-review]').count()===3,'Pending bills not shown inline');
    await page.locator('.pending-memory-card').filter({hasText:'伙食费'}).locator('button').click();
    await page.locator('#setup-purpose-context').filter({hasText:'华南理工大学'}).waitFor();
    const talk=async text=>{await page.locator('#setup-message').fill(text);await page.locator('#setup-send').click();await page.waitForFunction(()=>!setupBusy&&!!setupResult);};
    const confirm=async()=>{await page.locator('#setup-confirm').click();await page.locator('#setup-dialog').waitFor({state:'hidden'});};
    await talk('这是食堂的伙食费');
    check(await page.locator('[data-memory-policy]').count()===3,'Remembering decisions not explicit');
    await page.locator('[data-memory-policy=auto]').click();await page.waitForFunction(()=>!setupBusy&&setupResult?.draft.auto_apply);
    check(!await page.evaluate(()=>state.memories.length),'Memory saved before confirmation');
    await page.screenshot({path:path.join(out,'memory-conversation.png')});await confirm();
    check(await page.evaluate(()=>activePage==='memories'&&memoryTab==='saved'),'Save should return to memory list');
    await page.locator('.memory-card').filter({hasText:'自动分类'}).waitFor();
    check((await page.locator('.memory-condition-list').first().innerText()).includes('交易对方是'),'Exact payee matching is misleading');
    await page.locator('[data-memory-edit]').click();await page.locator('#setup-preview').filter({hasText:'当前保存的规则'}).waitFor();
    await talk('名称改成校园伙食费');check(await page.evaluate(()=>setupResult.draft.auto_apply),'Editing silently disabled automatic reuse');await confirm();
    await page.locator('#memory-followup').click();await page.getByRole('status').filter({hasText:'记忆自动识别 1 笔'}).waitFor();
    await page.locator('[data-memory-tab=pending]').click();await page.screenshot({path:path.join(out,'memory-pending.png')});
    await page.locator('[data-memory-tab=saved]').click();await page.screenshot({path:path.join(out,'memory-rules.png')});
    await page.locator('[data-memory-delete]').click();await page.locator('#memory-delete-dialog').waitFor({state:'visible'});await page.locator('#memory-delete-cancel').click();check(await page.locator('.memory-card').count()===1,'Cancel deleted memory');
    await page.goto(base+'#overview');await page.locator('#csv-file').setInputFiles(fixture);await page.locator('#bill-import-confirm:not([disabled])').waitFor();
    const before=await page.evaluate(()=>state.transactions.length);check(await page.locator('#bill-import-summary').innerText().then(s=>s.includes('本次新增')),'Import preview missing');await page.screenshot({path:path.join(out,'wechat-import-preview.png')});
    check((await(await fetch(base+'/api/state')).json()).transactions.length===before,'Preview wrote transactions');
    await page.locator('#bill-import-cancel').click();check((await(await fetch(base+'/api/state')).json()).transactions.length===before,'Cancel wrote transactions');
    await page.locator('#csv-file').setInputFiles(fixture);await page.locator('#bill-import-confirm:not([disabled])').click();await page.locator('#bill-import-dialog').waitFor({state:'hidden'});check((await(await fetch(base+'/api/state')).json()).transactions.length===before+2,'Unexpected WeChat import count');
    await page.goto(base+'#overview');await page.locator('#csv-file').setInputFiles(fixture);await page.locator('#bill-import-confirm:not([disabled])').waitFor();check(await page.locator('#bill-import-summary').innerText().then(s=>s.includes('已导入重复')),'Duplicate preview missing');await page.locator('#bill-import-confirm').click();await page.locator('#bill-import-dialog').waitFor({state:'hidden'});check((await(await fetch(base+'/api/state')).json()).transactions.length===before+2,'Duplicate XLSX inserted');
    await page.goto(base+'#adventure');await page.waitForFunction(()=>activePage==='goals');await page.locator('#new-adventure-goal').click();await talk('旅行基金，想攒1000元');await confirm();await page.locator('[data-adventure-entry]').click();await talk('存入100元');await confirm();await page.locator('.savings-amount').filter({hasText:'100.00'}).waitFor();check(!((await page.locator('body').innerText()).match(/经验|训练场|徽章|等级|冒险|远征|营地/)),'Game text still visible');await page.screenshot({path:path.join(out,'savings-goals.png')});
    await page.reload();await page.locator('.savings-amount').filter({hasText:'100.00'}).waitFor();
    for(const id of ['overview','records','insights','goals','memories','smart-plans','assistant']){await page.goto(base+'#'+id);check(await page.locator('main>section:visible').count()<=2,'Sections leaked: '+id);}
    await page.setViewportSize({width:390,height:844});await page.goto(base+'#memories');await page.locator('[data-memory-tab=pending]').click();check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile memory overflow');await page.screenshot({path:path.join(out,'memory-mobile.png'),fullPage:true});await page.locator('[data-memory-review]').first().click();check(await page.locator('#setup-dialog').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Purpose dialog overflow');await page.locator('#setup-close').click();
    await page.goto(base+'#overview');await page.locator('#csv-file').setInputFiles(fixture);await page.locator('#bill-import-confirm:not([disabled])').waitFor();check(await page.locator('#bill-import-dialog').evaluate(el=>el.scrollWidth<=el.clientWidth+1),'Import dialog overflow');await page.screenshot({path:path.join(out,'wechat-import-mobile.png')});await page.locator('#bill-import-cancel').click();
    check(!errors.length,errors.join('; '));const result={passed:true,checked_at:new Date().toISOString(),synthetic_only:true,external_model_calls:0,checks:['pending bills visible inline','bill context before conversation','explicit remembering policy','draft before save','return to saved memories','edit preserves auto setting','future import reuses memory','delete requires confirmation','native XLSX preview','cancel does not write','confirm imports exact eligible rows','order-ID deduplication','game UI removed','legacy adventure URL reaches savings','goals and allocations preserved','seven pages','390px layout']};await fs.writeFile(path.join(out,'workspace_browser_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
  }catch(e){if(page)await page.screenshot({path:path.join(ROOT,'tmp','workspace-failure.png'),fullPage:true}).catch(()=>{});throw e;}finally{if(browser)await browser.close();server.kill();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
