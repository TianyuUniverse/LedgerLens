'use strict';
const setupNames={goal:'聊聊新目标',budget:'一起安排预算',plan:'一起完善储蓄方案',entry:'聊一笔收支',allocation:'记录目标进展',reflection:'聊聊本期收获',purpose:'弄清消费用途'};
let setupMode='goal',setupContext={},setupResult=null,setupBusy=false,setupEpoch=0;
const setupDrafts=new Map();
function openSetupChat(mode,context={}){
  setupMode=mode;setupContext=context;setupResult=null;setupBusy=false;setupEpoch++;
  $('setup-title').textContent=mode==='purpose'&&context.memory_id?'修改分类记忆':setupNames[mode];$('setup-error').textContent='';$('setup-message').value='';$('setup-model').checked=Boolean(state.model_enabled);$('setup-model').disabled=!state.model_enabled;
  const key=mode+JSON.stringify(context);setupResult=setupDrafts.get(key)||null;
  $('setup-disclosure').textContent=state.model_enabled?'发送后，AI 会收到本次对话和当前草稿。消费用途审核还会发送所选账单的描述、对方与备注。确认前不会保存业务修改。':'当前使用本地对话整理。配置 AI 后可理解更自然的表达；确认前不会保存业务修改。';
  renderSetupChat();$('setup-dialog').showModal();$('setup-message').focus({preventScroll:true});
}
function setupChip(text){return `<button type="button" class="setup-chip" data-setup-message="${esc(text)}">${esc(text)}</button>`;}
function renderSetupChat(){
  const introductions={goal:'你想为哪个愿望攒钱？随便说说就好，我会帮你把细节补齐。',budget:'想先管好哪类开销？告诉我一个大概想法就好。',plan:'想存多少钱、多久实现？也可以先说说哪些生活开销不想减少。',entry:'今天想记点什么？一句话告诉我，我会帮你整理。',allocation:'这次为目标留了多少钱，还是需要取回一部分？',reflection:'这段时间有什么发现？像和朋友聊聊天一样说出来就好。',purpose:'这笔钱实际上花在什么地方？你确认后，我会整理分类和适用条件。'};
  const starters={goal:['我想为旅行攒钱','六个月攒6000，已经存了500'],budget:['每月餐饮预算600元','娱乐每个月最多200元'],plan:['六个月存6000，房租不能减','我还没想好，帮我梳理一下'],entry:['昨天食堂午饭25元','兼职收入1000元'],allocation:['今天存入100元','取回50元'],reflection:['这个月买东西前会先想一想是否需要','本月我想先了解餐饮消费'],purpose:['这是食堂的伙食费','这是舍友代收的电费和空调费']};
  const history=setupResult?.history||[{role:'assistant',content:introductions[setupMode]}];
  const selectedMemory=state.memories.find(m=>m.id===setupContext.memory_id);
  const selectedRecord=state.transactions.find(r=>r.id===setupContext.record_id)||selectedMemory?.example;
  $('setup-purpose-context').hidden=setupMode!=='purpose';
  $('setup-purpose-context').innerHTML=setupMode==='purpose'&&selectedRecord?`<div class="purpose-bill-context"><div><strong>${esc(l(selectedRecord.description))}</strong><strong>${cash(selectedRecord.amount_fen)}</strong></div><p>${esc(selectedRecord.date)} · ${esc(selectedRecord.counterparty||'未提供交易对方')}</p>${selectedRecord.note?'<p>备注：'+esc(selectedRecord.note)+'</p>':''}<p>当前分类：${esc(l(selectedRecord.kind))} · ${esc(l(selectedRecord.category))}</p></div>`:'';

  $('setup-messages').innerHTML=history.map(m=>`<div class="setup-message ${m.role==='user'?'from-user':'from-coach'}">${m.role==='user'?'':'<span class="setup-avatar">✦</span>'}<p>${esc(m.content)}</p></div>`).join('');
  $('setup-starters').innerHTML=setupResult?'':starters[setupMode].map(setupChip).join('');
  $('setup-source').textContent=setupResult?(setupResult.source==='ai'?'AI 正在帮你完善细节':'本地对话整理'):'先说想法，不必先填表格';
  $('setup-notice').textContent=l(setupResult?.notice||setupResult?.validation_notice||'');
  const result=setupResult,d=result?.draft||(selectedMemory?{...selectedMemory,remember:true}:null);
  $('setup-preview').innerHTML='';
  if(d&&Object.keys(d).length){
    let rows=[];
    const moneyRow=(name,key)=>d[key]!==undefined?[[name,cash(Math.round(Number(d[key])*100))]]:[];
    if(setupMode==='goal')rows=[['目标名称',d.title||'待补充'],...moneyRow('目标金额','target'),...moneyRow('已有储蓄','initial'),['目标日期',d.deadline||'暂不设置，可继续告诉我日期']];
    if(setupMode==='budget')rows=[['消费类别',d.category?l(d.category):'待补充'],...moneyRow('每月上限','amount')];
    if(setupMode==='plan')rows=[...moneyRow('目标金额','target'),...moneyRow('已有储蓄','current'),['时间',d.months?d.months+' 个月':'待补充'],['保持不变',(d.locked||[]).map(l).join('、')||'未指定'],['最低预算',Object.entries(d.floors||{}).map(([c,v])=>l(c)+' '+cash(Math.round(Number(v)*100))).join('、')||'未指定']];
    if(setupMode==='entry')rows=[['日期',d.date||'今天'],['描述',d.description||'待补充'],['收支类型',l(d.kind||'expense')],...moneyRow('金额','amount'),['消费类别',d.category?l(d.category):'待确认']];
    if(setupMode==='allocation')rows=[['这次操作',d.kind==='withdraw'?'从目标中取回':'为目标存入'],...moneyRow('金额','amount'),['备注',d.note||'未填写']];
    if(setupMode==='reflection')rows=[['复盘月份',d.month||'待补充'],['整理后的心得',d.note||'待补充']];
    if(setupMode==='purpose')rows=[['实际类型',d.kind?l(d.kind):'待确认'],['消费类别',d.category?l(d.category):'待确认'],['实际用途',d.purpose||'待补充'],['记住这个用途',d.remember?'是':'本次确认'],['后续自动复用',d.auto_apply?'相同条件时自动分类':'再次审核']];
    $('setup-preview').innerHTML=`<div class="setup-draft"><div class="setup-draft-heading"><strong>${result?.ready?'已经整理好了，最后核对一下':selectedMemory&&!result?'当前保存的规则':'正在一起完善'}</strong><span>${result?"尚未保存":"说说想修改哪里"}</span></div><dl>${rows.map(([name,value])=>`<div><dt>${esc(name)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl>${setupMode==='goal'?'<p class="note">没有提供已有储蓄时，草稿按零开始；你随时可以改口补充。</p>':''}${setupMode==='purpose'&&d.remember&&d.match?'<p class="memory-conditions-caption">以下条件同时符合时使用</p><ul class="memory-condition-list">'+memoryConditions(d.match)+'</ul>':''}</div>`;
    if(setupMode==='purpose'&&result){const chosen=!d.remember?'once':d.auto_apply?'auto':'review';$('setup-preview').innerHTML+=`<div class="purpose-policy" role="group" aria-label="以后如何处理类似账单"><strong>以后遇到类似账单</strong><div>${(selectedMemory?['review','auto']:['once','review','auto']).map(id=>`<button type="button" class="secondary" data-memory-policy="${id}" aria-pressed="${chosen===id}" ${setupBusy?'disabled':''}><span>${{once:'仅改这笔',review:'记住，每次确认',auto:'记住，自动分类'}[id]}</span><small>${{once:'不新增分类记忆',review:'匹配后仍请我核对',auto:'符合上面的条件才自动使用'}[id]}</small></button>`).join('')}</div></div>`;}
    if(result?.ready&&setupMode==='plan' &&result.calculation){$('setup-preview').innerHTML+=`<div class="setup-plan-options">${result.calculation.options.map(o=>`<button type="button" data-setup-confirm="${o.style}"><strong>${esc(l(o.label))}</strong><span>每月 ${cash(o.monthly_savings_fen)} · ${o.feasible?'按此情景可达标':'仍差 '+cash(o.gap_fen)}</span><small>核对并选择此方案 →</small></button>`).join('')}</div>`;}
    else if(result?.ready)$('setup-preview').innerHTML+='<button id="setup-confirm" type="button" class="setup-confirm">'+(setupMode==='purpose'?(selectedMemory?'保存记忆修改':d.remember?'确认用途并保存记忆':'只确认这笔用途'):'核对无误，确认保存')+'</button>';
  }
  $('setup-send').disabled=setupBusy;$('setup-message').disabled=setupBusy;$('setup-waiting').hidden=!setupBusy;
  $('setup-messages').scrollTop=$('setup-messages').scrollHeight;
}
async function sendSetupMessage(text,memoryPolicy=null){
  if(setupBusy||!text.trim())return;setupBusy=true;const epoch=setupEpoch;
  $('setup-error').textContent='';$('setup-send').disabled=true;$('setup-message').disabled=true;$('setup-waiting').hidden=false;
  $('setup-messages').insertAdjacentHTML('beforeend',`<div class="setup-message from-user"><p>${esc(text)}</p></div>`);$('setup-messages').scrollTop=$('setup-messages').scrollHeight;
  try{const result=await api('/api/setup/chat',{mode:setupMode,message:text,conversation_id:setupResult?.conversation_id||null,revision:setupResult?.revision,context:setupContext,use_model:memoryPolicy?false:$('setup-model').checked,...(memoryPolicy?{memory_policy:memoryPolicy}:{})});
    if(epoch!==setupEpoch)return;setupResult=result;setupDrafts.set(setupMode+JSON.stringify(setupContext),result);$('setup-message').value='';
  }catch(error){if(epoch===setupEpoch)$('setup-error').textContent=errorMessage(error);}finally{if(epoch===setupEpoch){setupBusy=false;renderSetupChat();if(setupResult?.draft)$('setup-preview').scrollIntoView({block:'nearest'});$('setup-message').focus({preventScroll:true});}}
}
async function confirmSetup(style){
  if(setupBusy||!setupResult?.ready)return;setupBusy=true;$('setup-error').textContent='';
  $('setup-preview').querySelectorAll('button').forEach(b=>b.disabled=true);
  try{const result=await api('/api/setup/confirm',{conversation_id:setupResult.conversation_id,revision:setupResult.revision,...(style?{style}:{})});setupDrafts.delete(setupMode+JSON.stringify(setupContext));$('setup-dialog').close();await refresh();
    if(result.mode==='goal'||result.mode==='allocation')navigatePage('goals');if(result.mode==='budget')navigatePage('overview');if(result.mode==='plan')navigatePage('smart-plans');if(result.mode==='entry')navigatePage('records');if(result.mode==='purpose'){navigatePage('memories');selectMemoryTab(setupContext.memory_id||result.memory_id?'saved':'pending');}
    let message='已按你确认的草稿保存。';
    if(result.mode==='allocation'){const goal=state.adventure.goals.find(g=>g.id===setupContext.goal_id);message='已'+(setupResult.draft.kind==='withdraw'?'取回':'存入')+' '+cash(Math.round(Number(setupResult.draft.amount)*100))+' · 目标进度 '+(goal?.progress_pct??0)+'%。';}
    if(result.mode==='entry'&&result.duplicates)message='这笔账单已在账本中，已跳过重复记录。';if(result.mode==='purpose')message=setupContext.memory_id?'分类记忆已更新，后续导入按新条件处理。':result.memory_id?'用途已确认，分类记忆已保存。':'这笔用途已确认，没有新增分类记忆。';notice(message);
  }catch(error){$('setup-error').textContent=errorMessage(error);$('setup-preview').querySelectorAll('button').forEach(b=>b.disabled=false);}finally{setupBusy=false;}
}
$('setup-form').addEventListener('submit',e=>{e.preventDefault();sendSetupMessage($('setup-message').value);});
$('setup-starters').addEventListener('click',e=>{const text=e.target.closest('[data-setup-message]')?.dataset.setupMessage;if(text)sendSetupMessage(text);});
$('setup-preview').addEventListener('click',e=>{if(e.target.closest('#setup-confirm'))confirmSetup();const button=e.target.closest('[data-setup-confirm]');if(button)confirmSetup(button.dataset.setupConfirm);const policy=e.target.closest('[data-memory-policy]')?.dataset.memoryPolicy;if(policy)sendSetupMessage({once:'只确认这笔，不要记住',review:'记住这个用途，但以后每次请我确认，不自动分类',auto:'记住这个用途，以后相同条件自动分类'}[policy],policy);});
$('setup-close').addEventListener('click',()=>$('setup-dialog').close());
$('setup-reset').addEventListener('click',()=>{setupDrafts.delete(setupMode+JSON.stringify(setupContext));$('setup-dialog').close();openSetupChat(setupMode,setupContext);});
$('setup-manual').addEventListener('click',()=>{$('setup-dialog').close();const context=setupContext;const mode=setupMode;if(mode==='goal')openManualAdventureGoal();if(mode==='allocation')openManualAdventureEntry(context.goal_id);if(mode==='reflection')openManualAdventureReflection(context.month);if(mode==='entry')openManualQuickEntry();if(mode==='purpose'){const record=state.transactions.find(r=>r.id===context.record_id),memory=state.memories.find(m=>m.id===context.memory_id);openManualPurpose(record||memory?.example,memory);}if(mode==='budget'){navigatePage('overview');$('manual-budget').open=true;$('budget-form').scrollIntoView();}if(mode==='plan'){navigatePage('smart-plans');$('manual-smart-plan').open=true;}});

$('chat-budget').addEventListener('click',()=>openSetupChat('budget'));$('chat-plan').addEventListener('click',()=>openSetupChat('plan'));
