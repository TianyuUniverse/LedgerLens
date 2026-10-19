const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
async function main(){
 const base='http://127.0.0.1:8765';const token=(await (await fetch(base+'/api/config')).json()).token;
 await fetch(base+'/api/demo',{method:'POST',headers:{'Content-Type':'application/json','X-Ledger-Token':token},body:'{}'});
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{const page=await browser.newPage({viewport:{width:1440,height:1000}});await page.goto(base);await page.locator('#count').filter({hasText:'30'}).waitFor();await page.screenshot({path:path.resolve('output/evidence/dashboard-clean.png')});}
 finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1});
