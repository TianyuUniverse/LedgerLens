'use strict';
let purposeContext=null, smartPreview=null, conversation=sessionStorage.getItem('ledgerlens-conversation'), asking=false;

function renderWorkflows(){
  $('review-count').textContent=state.review_count+' 笔账单待确认';
  $('use-model').disabled=!state.model_enabled;
  if(!state.model_enabled)$('use-model').checked=false;
  $('model-disclosure').textContent=state.model_enabled?
    `已配置 ${state.model_name}。勾选后，会向服务商发送问题、最近对话和所查账单结果；未勾选时使用本地规则查询与测算。`:
    '本地规则模式。配置 AI 后可启用模型理解和工具调用。';
  renderMemoryPage();
  if(!$('review-month').value&&state.overview.months.length)$('review-month').value=state.overview.months.at(-1).month;
  const saved=state.generated_plan;
  $('saved-smart-plan').textContent=saved?`已保存：${l(saved.style)}。目标 ${cash(Number(saved.inputs.target)*100)}，期限 ${saved.inputs.months} 个月。账单或限制变化后，请重新生成并审核。`:'尚未保存生成的储蓄方案。';
}

function purposeCategories(selected){
  const kind=$('purpose-kind').value;
  $('purpose-category').innerHTML=options(kind==='expense'?state.expense_categories:[kind==='income'?'Income':'Transfer'],selected);
}
function memoryFields(){
  const editing=purposeContext?.type==='memory';
  $('memory-conditions').hidden=!$('remember-purpose').checked;
  $('memory-enabled-label').hidden=!editing;
  $('remember-purpose').disabled=editing;
}
function openPurpose(record,memory=null){openSetupChat('purpose',{record_id:record.id,...(memory?{memory_id:memory.id}:{})});}
function openManualPurpose(record,memory=null){
  purposeContext=memory?{type:'memory',memory}:{type:'record',record};
  $('purpose-title').textContent=memory?'修改分类记忆':'这笔钱实际用来做什么？';
  $('purpose-record').textContent=`账单 #${record.id} · ${record.date} · ${cash(record.amount_fen)} · ${l(record.description)} · ${record.counterparty} · ${record.note}。原始标签：${l(record.source_kind)} / ${l(record.source_category)}`;
  $('purpose-kind').value=memory?.kind||record.kind;purposeCategories(memory?.category||record.category);
  $('purpose-text').value=memory?.purpose||'';
  $('remember-purpose').checked=true;$('auto-memory').checked=memory?.auto_apply||false;$('memory-enabled').checked=memory?.enabled??true;
  const pattern=memory?.match||{counterparty:record.counterparty,description:record.description,note:record.note};
  $('match-payee').value=pattern.counterparty||'';$('match-description').value=pattern.description||'';$('match-note').value=pattern.note||'';
  $('purpose-error').textContent='';memoryFields();$('purpose-dialog').showModal();
}
function reviewPending(ids=null){
  const record=state.transactions.find(r=>r.review_status==='needs_review'&&(!ids||ids.includes(r.id)));
  if(record)openPurpose(record);else notice('当前没有待确认的账单。');
}
$('rows').addEventListener('click',e=>{const el=e.target.closest('[data-purpose]');if(el)openPurpose(state.transactions.find(r=>r.id===Number(el.dataset.purpose)));});
$('purpose-kind').addEventListener('change',()=>purposeCategories());
$('remember-purpose').addEventListener('change',memoryFields);
$('cancel-purpose').addEventListener('click',()=>$('purpose-dialog').close());
$('purpose-form').addEventListener('submit',async e=>{
  e.preventDefault();const button=e.submitter;button.disabled=true;$('purpose-error').textContent='';
  try{
    const match={};for(const [key,id] of [['counterparty','match-payee'],['description','match-description'],['note','match-note']])if($(id).value.trim())match[key]=$(id).value.trim();
    const data={kind:$('purpose-kind').value,category:$('purpose-category').value,purpose:$('purpose-text').value,match,auto_apply:$('auto-memory').checked};
    if(purposeContext.type==='memory')await api('/api/memories/'+purposeContext.memory.id,{...data,enabled:$('memory-enabled').checked},'PATCH');
    else await api('/api/confirm-purpose',{...data,id:purposeContext.record.id,remember:$('remember-purpose').checked,expected_revision:purposeContext.record.revision});
    $('purpose-dialog').close();await refresh();navigatePage('memories');selectMemoryTab(purposeContext.type==='memory'||$('remember-purpose').checked?'saved':'pending');notice('消费用途已确认并保存。记忆修改用于后续导入，历史账单保留当时的分类。');
  }catch(error){$('purpose-error').textContent=errorMessage(error);}finally{button.disabled=false;}
});
$('review-pending').addEventListener('click',()=>reviewPending());
for(const [id,phase] of [['memory-seed','seed'],['memory-followup','followup']])$(id).addEventListener('click',()=>run(async()=>{
  const result=await api('/api/memory-demo',{phase});await refresh();
  if(phase==='seed')selectMemoryTab('pending');
  notice(`第${phase==='seed'?'一':'二'}步示例：新增 ${result.inserted} 笔，跳过 ${result.duplicates} 笔重复记录；记忆自动识别 ${result.auto_labeled} 笔，待确认 ${result.needs_review} 笔。`);
  if(phase==='seed'&&result.needs_review)reviewPending(result.ids);
}));
$('memory-list').addEventListener('click',e=>run(async()=>{
  const edit=e.target.closest('[data-memory-edit]'),toggle=e.target.closest('[data-memory-toggle]'),del=e.target.closest('[data-memory-delete]');
  if(edit){const m=state.memories.find(m=>m.id===Number(edit.dataset.memoryEdit));openPurpose(m.example,m);}
  if(toggle){const m=state.memories.find(m=>m.id===Number(toggle.dataset.memoryToggle));await api('/api/memories/'+m.id,{enabled:!m.enabled},'PATCH');await refresh();notice('记忆设置已更新，历史账单保持不变。');}
  if(del){memoryDeleteId=Number(del.dataset.memoryDelete);const m=state.memories.find(m=>m.id===memoryDeleteId);$('memory-delete-name').textContent=m.purpose;$('memory-delete-dialog').showModal();}
}));

function planCards(preview){
  smartPreview=preview;
  $('plan-options').innerHTML=`<p class="note">方案预览 · ${esc(preview.periods.join(' / '))} · 平均每月收入 ${cash(preview.monthly_income_fen)} · 每月所需储蓄 ${cash(preview.required_monthly_fen)}</p><div class="option-grid">${preview.options.map(o=>`<article class="plan-option"><h3>${esc(l(o.label))}</h3><strong>${cash(o.monthly_savings_fen)}<small> 每月可储蓄</small></strong><p class="${o.feasible?'ok':'warning'}">${o.feasible?'按此情景可以达到目标':'距离目标还差：'+cash(o.gap_fen)}</p><p class="note">预计累计：${cash(o.projected_fen)} · 限制条件已校验</p><details><summary>每月类别预算</summary><dl>${Object.entries(o.monthly_amounts_fen).map(([c,v])=>`<div><dt>${esc(l(c))}${preview.inputs.locked.includes(c)?' · 固定':''}</dt><dd>${cash(v)}</dd></div>`).join('')}</dl></details><button class="small" data-save-style="${esc(o.style)}">选择并保存此方案</button></article>`).join('')}</div><p class="note">${esc(preview.assumption)}</p><p class="note">默认减支上限：${Object.entries(preview.default_cut_caps_pct).map(([k,v])=>esc(l(k))+' '+v+'%').join(' · ')}. 以上比例是本原型的测算假设，不代表已验证的生活建议。</p><button class="secondary small" id="smart-plan-trace">查看方案计算依据</button>`;
  $('smart-plan-trace').addEventListener('click',()=>showTrace(preview.record_ids,'储蓄方案使用的来源账单'));
}
$('smart-plan-form').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
  const locked=[];if($('lock-housing').checked)locked.push('Housing');if($('lock-food').checked)locked.push('Food');
  planCards(await api('/api/plans/generate',{target:$('smart-target').value,current:$('smart-current').value,months:Number($('smart-months').value),locked,floors:{Entertainment:$('entertainment-floor').value}}));
});});
$('plan-options').addEventListener('click',e=>run(async()=>{const el=e.target.closest('[data-save-style]');if(!el||!smartPreview)return;await api('/api/plans/save',{inputs:smartPreview.inputs,style:el.dataset.saveStyle,ledger_revision:smartPreview.ledger_revision});await refresh();notice('审核后的方案已保存，账单数据未被修改。');}));
$('review-form').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
  const result=await api('/api/monthly-review',{month:$('review-month').value});
  $('review-result').innerHTML=`<p class="answer-text">${esc(result.comparison.second_month+' 与 '+result.comparison.first_month)}：支出变化 ${cash(result.comparison.delta_fen)}</p><p>20 元及以下的小额消费：${result.small_payments.count} 笔，共 ${cash(result.small_payments.total_fen)}</p>${result.recurring.map(group=>`<p>${esc(l(group.description))} · ${esc(group.months.join(', '))}<br><small>${esc(group.notice)}</small></p>`).join('')}<p class="note">${esc(result.notice)} ${esc(result.comparison.assumption)}</p><button id="review-source" class="secondary small">查看复盘依据</button>`;
  $('review-source').addEventListener('click',()=>showTrace(result.record_ids,'消费复盘的来源账单'));
  if(typeof openAdventureReflection==='function'){const reflectButton=document.createElement('button');reflectButton.className='secondary small choice-button';reflectButton.textContent='记录复盘心得';reflectButton.addEventListener('click',()=>openAdventureReflection(result.month));$('review-result').append(reflectButton);}
});});

async function askConversation(){
  if(asking)return;const question=$('question').value.trim();if(!question)return;
  asking=true;const button=$('ask-form').querySelector('button');button.disabled=true;button.textContent='正在分析…';
  try{
    const result=await api('/api/ask',{question,session_id:conversation||null,use_model:$('use-model').checked});
    conversation=result.session_id;sessionStorage.setItem('ledgerlens-conversation',conversation);
    const previous=$('answer').querySelector('.conversation-turn');if(previous)$('chat-history').append(previous);
    const turn=document.createElement('div');turn.className='conversation-turn';
    turn.innerHTML=`<p class="user-question">${esc(question)}</p><p class="answer-text">${esc(result.answer)}</p><p class="note">${esc(result.source)}${result.notice?' · '+esc(result.notice):''}</p>${result.assumption?'<p class="note">'+esc(result.assumption)+'</p>':''}`;
    if(result.record_ids.length){const traceButton=document.createElement('button');traceButton.className='secondary small';traceButton.textContent='查看 '+result.record_ids.length+' 笔来源账单';traceButton.addEventListener('click',()=>showTrace(result.record_ids,'本次回答的来源账单'));turn.append(traceButton);}
    for(const choice of result.choices||[]){const choiceButton=document.createElement('button');choiceButton.className='secondary small choice-button';choiceButton.textContent=`#${choice.id} · ${l(choice.description)} · ${cash(choice.amount_fen)}`;choiceButton.addEventListener('click',()=>{$('question').value='#'+choice.id;run(askConversation);});turn.append(choiceButton);}
    if(result.data?.tool==='generate_savings_plans'){const previewButton=document.createElement('button');previewButton.className='secondary small choice-button';previewButton.textContent='查看预算并选择方案';previewButton.addEventListener('click',()=>{planCards(result.data);navigatePage('smart-plans');$('smart-plans').scrollIntoView({behavior:'smooth'});});turn.append(previewButton);}
    $('answer').replaceChildren(turn);while($('chat-history').children.length>5)$('chat-history').firstElementChild.remove();
  }finally{asking=false;button.disabled=false;button.textContent='发送';}
}
$('new-conversation').addEventListener('click',()=>{if(asking)return;conversation=null;sessionStorage.removeItem('ledgerlens-conversation');$('chat-history').replaceChildren();$('answer').textContent='已新建对话。本次比较的排除项和储蓄限制已重置。';});
