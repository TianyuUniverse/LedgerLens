'use strict';
let billUpload=null,billPreview=null,billImportEpoch=0,billImportSaving=false;
function closeBillImport(){if(billImportSaving)return;billImportEpoch++;billUpload=null;billPreview=null;$('bill-import-dialog').close();$('csv-file').value='';}
function renderBillPreview(p){
  $('bill-import-summary').innerHTML=`<div class="bill-import-stats"><div><span>账单交易</span><strong>${p.source_rows}<small> 笔</small></strong></div><div><span>本次新增</span><strong>${p.new_count}<small> 笔</small></strong></div><div><span>已导入重复</span><strong>${p.duplicates}<small> 笔</small></strong></div><div><span>单独列出</span><strong>${p.excluded_count}<small> 笔</small></strong></div></div><div class="bill-import-totals"><span>文件中可导入收入 <strong>${cash(p.income_fen)}</strong></span><span>文件中可导入支出 <strong>${cash(p.expense_fen)}</strong></span><span>账户划转 <strong>${cash(p.transfer_fen)}</strong></span></div><p class="note">${esc(p.notice)}</p>${p.partial_refund_fen?'<p class="note">部分退款已抵扣 '+cash(p.partial_refund_fen)+'，支出和预览金额均为退款后的剩余金额。</p>':''}`;
  $('bill-import-rows').innerHTML=p.preview_rows.length?'<h3>交易预览 · 前 '+p.preview_rows.length+' 笔</h3><div class="bill-preview-table"><table><thead><tr><th>日期</th><th>交易对方 / 商品</th><th>收支</th><th>金额</th></tr></thead><tbody>'+p.preview_rows.map(r=>`<tr><td>${esc(r.date)}</td><td>${esc(r.counterparty)}<small>${esc(r.description)}</small></td><td>${esc(l(r.kind))}</td><td>${cash(r.amount_fen)}</td></tr>`).join('')+'</tbody></table></div>':'<p class="note">没有需要新增的收支记录。</p>';
  $('bill-import-excluded').hidden=!p.excluded_count;
  $('bill-import-excluded-summary').textContent='查看 '+p.excluded_count+' 笔单独列出的记录';
  $('bill-import-excluded-rows').innerHTML=`<p class="note">${esc(p.refund_notice)}</p>${p.excluded_reasons.map(r=>'<p>'+esc(r.reason)+' · '+r.count+' 笔</p>').join('')}<div class="bill-excluded-list">${p.excluded_rows.map(r=>`<div><span>第 ${r.row} 行 · ${esc(r.date)} · ${esc(r.trade_type)}</span><strong>${cash(r.amount_fen)}</strong><small>${esc(r.reason)}</small></div>`).join('')}</div>`;
  $('bill-import-error').textContent=p.conflicts.length?'有 '+p.conflicts.length+' 笔已导入交易的金额或退款状态发生变化，请先核对历史账单：'+p.conflicts.map(id=>'#'+id).join('、'):'';
  $('bill-import-confirm').textContent=p.new_count?'确认导入 '+p.new_count+' 笔':'确认核对';
  $('bill-import-confirm').disabled=Boolean(p.conflicts.length);
}
$('csv-file').addEventListener('change',event=>run(async()=>{
  const file=event.target.files[0];if(!file)return;
  if(/\.csv$/i.test(file.name)){
    try{if(file.size>2000000)throw Error('CSV 文件不能超过 2 MB。');const r=await api('/api/import',{csv:await file.text()});await refresh();notice(`导入完成：新增 ${r.inserted} 笔，跳过 ${r.duplicates} 笔重复；记忆自动识别 ${r.auto_labeled} 笔，待确认 ${r.needs_review} 笔。`);if(r.needs_review){navigatePage('memories');selectMemoryTab('pending');}}finally{event.target.value='';}return;
  }
  if(!/\.xlsx$/i.test(file.name)){event.target.value='';throw Error('请选择微信导出的 .xlsx 账单，或 CSV 模板文件。');}
  if(file.size>5000000){event.target.value='';throw Error('微信账单不能超过 5 MB。');}
  const epoch=++billImportEpoch;billUpload=null;billPreview=null;
  $('bill-import-filename').textContent=file.name;$('bill-import-error').textContent='';$('bill-import-summary').innerHTML='';$('bill-import-rows').innerHTML='';$('bill-import-excluded').hidden=true;$('bill-import-confirm').disabled=true;$('bill-import-loading').hidden=false;$('bill-import-dialog').showModal();
  try{const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('无法读取该文件，请重新选择。'));reader.readAsDataURL(file);});
    const upload={filename:file.name,data:encoded};const p=await api('/api/import-file/preview',upload);if(epoch!==billImportEpoch)return;billUpload=upload;billPreview=p;renderBillPreview(p);
  }catch(error){if(epoch===billImportEpoch)$('bill-import-error').textContent=errorMessage(error);}finally{if(epoch===billImportEpoch)$('bill-import-loading').hidden=true;event.target.value='';}
}));
$('bill-import-cancel').addEventListener('click',closeBillImport);
$('bill-import-dialog').addEventListener('cancel',e=>{e.preventDefault();closeBillImport();});
$('bill-import-confirm').addEventListener('click',async()=>{
  if(!billUpload||!billPreview||billImportSaving)return;billImportSaving=true;$('bill-import-error').textContent='';$('bill-import-confirm').disabled=true;$('bill-import-confirm').textContent='正在导入…';$('bill-import-cancel').disabled=true;
  try{const result=await api('/api/import-file/confirm',{...billUpload,digest:billPreview.digest});await refresh();billImportSaving=false;closeBillImport();navigatePage('memories');selectMemoryTab(result.needs_review?'pending':'saved');notice(`微信账单导入完成：新增 ${result.inserted} 笔，跳过 ${result.duplicates} 笔重复；${result.auto_labeled} 笔按记忆分类，${result.needs_review} 笔待确认。`);}
  catch(error){$('bill-import-error').textContent=errorMessage(error);$('bill-import-confirm').disabled=false;$('bill-import-confirm').textContent='重试导入';}
  finally{billImportSaving=false;$('bill-import-cancel').disabled=false;}
});
