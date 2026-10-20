'use strict';
let recordPage=1,recordFilterKey='',recordDetailsId=null;
let recordDeleteTarget=null,recordDeleteBusy=false;
const recordPageSize=50;
function recordTextSource(r){
  if(r.description_origin==='user')return {label:'你填写的文字',explanation:'这段商品或用途文字由你填写或修改。'};
  if(r.ingestion_origin==='wechat'||r.source_platform==='wechat')return {label:'微信导入',explanation:'商品或交易内容来自微信导出的账单文件，AI 分类不会改写这里的原文。'};
  if(r.ingestion_origin==='csv')return {label:'CSV 导入',explanation:'这段文字来自导入文件的“交易描述”列。'};
  if(r.ingestion_origin==='sample')return {label:'示例账单',explanation:'这是为演示功能准备的示例数据。'};
  if(r.description_origin==='ai')return {label:'AI 整理 · 已确认',explanation:'AI 根据你的记账对话整理了用途文字，经你确认后保存。'};
  if(r.description_origin==='local')return {label:'记账对话 · 已确认',explanation:'程序根据你输入的记账内容提取了用途文字，经你确认后保存。'};
  if(r.ingestion_origin==='entry')return {label:'记账时已确认',explanation:'这是通过记账窗口保存的旧记录。当时没有记录是否经 AI 整理，无法确定文字的整理方式。'};
  return {label:'较早的记录',explanation:'这条旧记录未保存内容来源，无法确定文字由谁整理。'};
}
function recordClassification(r){
  if(r.review_status==='needs_review')return '待你确认';
  if(r.category_source==='human')return '你已确认';
  if(r.category_source==='memory')return '按已记住的规则分类';
  if(r.category_source==='model')return 'AI 建议';
  if(r.category_source==='rule')return '规则识别';
  return '导入时的分类';
}
function renderRows(){
  const category=$('filter').value,query=$('record-search').value.trim().toLocaleLowerCase();
  const key=JSON.stringify([category,query,trace?[...trace]:null]);if(key!==recordFilterKey){recordPage=1;recordFilterKey=key;}
  const selected=state.transactions.filter(r=>(category==='all'||r.category===category)&&(!trace||trace.has(r.id))&&(!query||[r.description,r.counterparty,r.note,r.date,String(r.id)].join(' ').toLocaleLowerCase().includes(query)));
  const pages=Math.max(1,Math.ceil(selected.length/recordPageSize));recordPage=Math.min(recordPage,pages);
  const rows=selected.slice((recordPage-1)*recordPageSize,recordPage*recordPageSize);
  $('record-count').textContent='共 '+selected.length+' 笔';
  $('record-pagination').hidden=pages<=1;$('record-page-label').textContent=recordPage+' / '+pages+' 页';$('record-prev').disabled=recordPage===1;$('record-next').disabled=recordPage===pages;
  $('rows').innerHTML=rows.length?rows.map(r=>{
    const source=recordTextSource(r),title=r.counterparty||r.description;
    return `<tr><td class="record-date">${esc(r.date)}<small>#${r.id}</small></td><td class="record-content"><strong>${esc(title)}</strong>${r.counterparty?'<p><span>商品 / 用途</span>'+esc(r.description)+'</p>':''}${r.note?'<p><span>备注</span>'+esc(r.note)+'</p>':''}<span class="record-source-label" title="${esc(source.explanation)}">${esc(source.label)}</span></td><td class="record-amount ${r.kind}"><span>${esc(l(r.kind))}</span><strong>${r.kind==='expense'?'−':r.kind==='income'?'+':''}${cash(r.amount_fen)}</strong></td><td class="record-category"><span>${esc(l(r.category))}</span><small class="${r.review_status==='needs_review'?'pending':''}">${esc(recordClassification(r))}</small></td><td class="record-actions"><button class="${r.review_status==='needs_review'?'':'secondary '}small" data-purpose="${r.id}">${r.review_status==='needs_review'?'确认用途':'修改分类'}</button><button class="text-button" data-record-details="${r.id}">详情</button></td></tr>`;
  }).join(''):'<tr class="record-empty"><td colspan="5"><strong>没有找到对应账单</strong><p>可以导入微信账单，或点击“记一笔”。</p></td></tr>';
  if($('record-detail-dialog').open)renderRecordDetails();
}
function renderRecordDetails(){
  const r=state.transactions.find(r=>r.id===recordDetailsId);if(!r){$('record-detail-dialog').close();return;}
  const source=recordTextSource(r);
  $('record-detail-title').textContent=r.counterparty||r.description;
  $('record-detail-amount').textContent=l(r.kind)+' '+cash(r.amount_fen);
  $('record-detail-content').innerHTML=`<dl class="record-detail-fields"><div><dt>日期</dt><dd>${esc(r.occurred_at||r.date)}</dd></div>${r.counterparty?'<div><dt>商家 / 交易对方</dt><dd>'+esc(r.counterparty)+'</dd></div>':''}<div><dt>商品 / 用途</dt><dd>${esc(r.description)}</dd></div>${r.note?'<div><dt>备注</dt><dd>'+esc(r.note)+'</dd></div>':''}<div><dt>文字来源</dt><dd><strong>${esc(source.label)}</strong><p>${esc(source.explanation)}</p></dd></div><div><dt>消费分类</dt><dd>${esc(l(r.category))} · ${esc(recordClassification(r))}</dd></div></dl>`;
  $('record-original-fields').innerHTML=`<dl class="record-detail-fields"><div><dt>账单编号</dt><dd>#${r.id}</dd></div><div><dt>原始类型</dt><dd>${esc(l(r.source_kind))}</dd></div><div><dt>原始分类</dt><dd>${esc(l(r.source_category))}</dd></div>${r.source_status?'<div><dt>微信交易状态</dt><dd>'+esc(r.source_status)+'</dd></div>':''}${r.external_id?'<div><dt>微信交易单号</dt><dd>'+esc(r.external_id)+'</dd></div>':''}${r.memory_id?'<div><dt>使用的分类记忆</dt><dd>#'+r.memory_id+' · 第 '+r.memory_version+' 版</dd></div>':''}${r.decision_reason?'<div><dt>分类依据</dt><dd>'+esc(l(r.decision_reason))+'</dd></div>':''}</dl><label>手动修改分类<select data-edit="${r.id}" aria-label="账单 ${r.id} 的消费分类">${options(r.kind==='expense'?state.expense_categories:[r.kind==='income'?'Income':'Transfer'],r.category)}</select></label><button class="secondary" data-review="${r.id}">获取分类建议</button>`;
}
$('record-search').addEventListener('input',renderRows);
$('record-prev').addEventListener('click',()=>{recordPage--;renderRows();$('records').scrollIntoView({behavior:'smooth'});});
$('record-next').addEventListener('click',()=>{recordPage++;renderRows();$('records').scrollIntoView({behavior:'smooth'});});
$('rows').addEventListener('click',e=>{const b=e.target.closest('[data-record-details]');if(b){recordDetailsId=Number(b.dataset.recordDetails);$('record-detail-advanced').open=false;renderRecordDetails();$('record-detail-dialog').showModal();}});
$('record-detail-close').addEventListener('click',()=>$('record-detail-dialog').close());
$('record-detail-purpose').addEventListener('click',()=>{const record=state.transactions.find(r=>r.id===recordDetailsId);$('record-detail-dialog').close();openPurpose(record);});
$('record-detail-delete').addEventListener('click',()=>{
  const r=state.transactions.find(r=>r.id===recordDetailsId);if(!r)return;
  recordDeleteTarget={id:r.id,expected_revision:r.revision};
  $('record-delete-bill').innerHTML=`<strong>${esc(r.counterparty||r.description)}</strong><span>${esc(r.date)} · ${esc(l(r.kind))}</span><b>${cash(r.amount_fen)}</b>`;
  $('record-delete-description').textContent='删除后，收支统计会重新计算。'+(r.source_platform==='wechat'||['csv','wechat'].includes(r.ingestion_origin)?'再次导入原文件，可以重新加入这笔账单。':'需要恢复时，可以重新记一笔。');
  $('record-delete-memory-note').hidden=!state.memories.some(m=>m.source_id===r.id);
  $('record-delete-error').textContent='';$('record-detail-dialog').close();$('record-delete-dialog').showModal();$('record-delete-cancel').focus();
});
function cancelRecordDelete(){
  if(recordDeleteBusy)return;
  $('record-delete-dialog').close();
  if(state.transactions.some(r=>r.id===recordDeleteTarget?.id)){recordDetailsId=recordDeleteTarget.id;renderRecordDetails();$('record-detail-dialog').showModal();$('record-detail-delete').focus();}
  recordDeleteTarget=null;
}
$('record-delete-cancel').addEventListener('click',cancelRecordDelete);
$('record-delete-dialog').addEventListener('cancel',e=>{e.preventDefault();cancelRecordDelete();});
$('record-delete-confirm').addEventListener('click',async()=>{
  if(recordDeleteBusy||!recordDeleteTarget)return;
  recordDeleteBusy=true;$('record-delete-confirm').disabled=true;$('record-delete-cancel').disabled=true;$('record-delete-error').textContent='';
  const target=recordDeleteTarget;let deleted=false;
  try{
    await api('/api/transactions/delete',target);deleted=true;
    for(const key of setupDrafts.keys()){const context=JSON.parse(key.slice(key.indexOf('{')));if(key.startsWith('purpose')&&context.record_id===target.id&&!context.memory_id)setupDrafts.delete(key);}
    smartPreview=null;$('plan-options').replaceChildren();$('review-result').replaceChildren();
    $('record-delete-dialog').close();recordDeleteTarget=null;recordDetailsId=null;
    await refresh();notice('这笔账单已删除，收支统计已更新。');
  }catch(error){if(deleted)notice('账单已删除，请刷新页面查看最新统计。',true);else $('record-delete-error').textContent=errorMessage(error);}
  finally{recordDeleteBusy=false;$('record-delete-confirm').disabled=false;$('record-delete-cancel').disabled=false;}
});
$('record-original-fields').addEventListener('change',e=>run(async()=>{const el=e.target.closest('[data-edit]');if(el){await api('/api/transactions/'+el.dataset.edit,{category:el.value},'PATCH');await refresh();notice('分类已更新。');}}));
$('record-original-fields').addEventListener('click',e=>run(async()=>{const b=e.target.closest('[data-review]');if(!b)return;proposal=await api('/api/suggest',{id:Number(b.dataset.review)});$('proposal-text').textContent=`建议：${l(proposal.kind||state.transactions.find(r=>r.id===proposal.record_id).kind)} / ${l(proposal.category)}。${proposal.reason} ${proposal.notice||''}`;$('record-detail-dialog').close();$('review-dialog').showModal();}));
