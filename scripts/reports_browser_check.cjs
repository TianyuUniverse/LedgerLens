// Isolated synthetic end-to-end evidence; never uses the private user ledger.
const fs=require('node:fs/promises'),path=require('node:path');
const {spawn}=require('node:child_process');const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'..'),base='http://127.0.0.1:8774',out=path.join(ROOT,'output/evidence');
const wait=ms=>new Promise(r=>setTimeout(r,ms));const check=(v,m)=>{if(!v)throw Error(m);};
async function main(){
  await fs.mkdir(out,{recursive:true});await fs.mkdir(path.join(ROOT,'tmp'),{recursive:true});
  const server=spawn(process.env.FINANCE_PYTHON||'python',[path.join(ROOT,'app.py'),'--port','8774','--db',path.join(ROOT,'tmp',`reports-${Date.now()}.sqlite`)],{cwd:ROOT,windowsHide:true,stdio:'ignore',env:{...process.env,FINANCE_AI_DISABLE:'1'}});
  let browser;
  try{
    for(let i=0;i<60;i++){try{const r=await fetch(base+'/api/config');await r.arrayBuffer();if(r.ok)break;}catch{}await wait(100);}
    browser=await chromium.launch({headless:true,channel:process.env.FINANCE_BROWSER||'msedge'});
    const context=await browser.newContext({viewport:{width:1440,height:1150},reducedMotion:'reduce'}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(base+'#insights');await page.locator('#report-radar svg').waitFor();
    check(await page.locator('#report-ai-generate').isDisabled(),'Cloud reports must be disabled without provider');
    await page.goto(base+'#overview');await page.locator('#demo').click();await page.locator('#count').filter({hasText:'30'}).waitFor();
    await page.goto(base+'#insights');await page.locator('#report-anchor').fill('2026-09');await page.locator('#report-anchor').dispatchEvent('change');
    await page.locator('#report-records').filter({hasText:'10 笔'}).waitFor();
    await page.locator('#report-trend svg').waitFor();check(await page.locator('#report-donut circle[role=button]').count()>0,'Donut must have evidence slices');
    await page.locator('#report-donut circle[role=button]').first().focus();await page.keyboard.press('Enter');await page.locator('#trace-label').filter({hasText:'成长图鉴'}).waitFor();
    await page.locator('#clear-trace').click();
    await page.locator('#header-quick-entry').click();await page.locator('#setup-manual').click();await page.locator('#entry-sentence').fill('昨天食堂午饭25.20元');await page.locator('#entry-parse').click();
    await page.locator('#entry-draft-notice').filter({hasText:'草稿来自本地'}).waitFor();check(await page.locator('#entry-amount').inputValue()==='25.20','Draft amount mismatch');
    const before=await (await fetch(base+'/api/state')).json();check(before.transactions.length===30,'Draft must not save');
    await page.locator('#entry-category').selectOption('Food');await page.locator('#quick-entry-form button[type=submit]').click();await page.locator('#quick-entry-dialog').waitFor({state:'hidden'});
    await page.locator('#header-quick-entry').click();await page.locator('#setup-manual').click();await page.locator('#entry-sentence').fill('兼职收入1000元');await page.locator('#entry-parse').click();await page.locator('#entry-kind').filter({has:page.locator('option:checked[value=income]')}).waitFor();
    await page.locator('#quick-entry-form button[type=submit]').click();await page.locator('#quick-entry-dialog').waitFor({state:'hidden'});
    await page.goto(base+'#overview');await page.locator('#manual-budget summary').click();await page.locator('#budget-category').selectOption('Food');await page.locator('#budget-amount').fill('300');await page.locator('#budget-form button').click();
    await page.goto(base+'#adventure');await page.locator('#new-adventure-goal').click();await page.locator('#setup-manual').click();await page.locator('#adventure-goal-title').fill('给未来的一点安心');await page.locator('#adventure-goal-target').fill('1000');await page.locator('#adventure-goal-initial').fill('100');await page.locator('#adventure-goal-form button[type=submit]').click();await page.locator('#adventure-goal-dialog').waitFor({state:'hidden'});
    await page.locator('#adventure-focus [data-adventure-entry]').click();await page.locator('#setup-manual').click();await page.locator('#adventure-entry-amount').fill('200');await page.locator('#adventure-entry-form button[type=submit]').click();await page.locator('#adventure-entry-dialog').waitFor({state:'hidden'});
    await page.goto(base+'#insights');await page.locator('#report-current').click();await page.locator('#report-total').filter({hasText:'25.20'}).waitFor();
    check(await page.locator('#report-goal-trend svg').count()===1,'Goal chart missing');
    await page.locator('#report-kind').selectOption('week');await page.locator('#report-range').filter({hasText:'至'}).waitFor();
    await page.locator('#report-kind').selectOption('month');await page.goto(base+'#insights');await page.locator('#report-current').click();
    await page.locator('#radar-unlocked').filter({hasText:'6 / 6'}).waitFor();
    await page.waitForFunction(()=>!reportBusy&&periodReport.kind==='month'&&periodReport.record_count===2);
    const image=await page.locator('.comic-art').first().evaluate(async el=>{const style=getComputedStyle(el).backgroundImage;const match=style.match(/^url\(["']?(.*?)["']?\)$/);if(!match)throw Error('Comic background missing: '+style);const i=new Image();i.src=match[1];await i.decode();return i.naturalWidth;});check(image>0,'Comic illustration missing');
    await page.locator('#notice .notice-dismiss').click().catch(()=>{});
    await page.locator('#adventure-toast').waitFor({state:'hidden'});
    await page.locator('#insights').screenshot({path:path.join(out,'reports-desktop.png')});
    await page.goto(base+'#adventure');await page.locator('#adventure').screenshot({path:path.join(out,'adventure-minimal.png')});
    await page.goto(base+'#overview');await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));
    await page.screenshot({path:path.join(out,'minimal-home.png')});
    await page.goto(base+'#insights');const download=page.waitForEvent('download');await page.locator('[data-download-chart=report-trend]').click();check((await download).suggestedFilename().endsWith('.svg'),'Chart export failed');
    await page.setViewportSize({width:390,height:844});await page.locator('#insights').scrollIntoViewIfNeeded();
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Mobile page overflow');
    await page.locator('#insights').screenshot({path:path.join(out,'reports-mobile.png')});
    await page.locator('#mobile-quick-entry').click();await page.locator('#setup-manual').click();await page.locator('#quick-entry-dialog').waitFor({state:'visible'});await page.screenshot({path:path.join(out,'quick-entry-mobile.png')});await page.locator('#entry-cancel').click();
    check(errors.length===0,'Browser errors: '+errors.join('; '));
    const result={passed:true,checked_at:new Date().toISOString(),synthetic_only:true,external_model_calls:0,checks:['period selection','interactive line and donut evidence','null-aware radar','goal trajectory','draft before save','quick entry income and expense','six dimensions','comic asset','SVG download','390px mobile','no JS errors']};
    await fs.writeFile(path.join(out,'reports_browser_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
  }finally{if(browser)await browser.close();server.kill();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
