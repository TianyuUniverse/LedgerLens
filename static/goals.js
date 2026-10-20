'use strict';
// Savings remain financial records; the game UI is retired.
let adventureEntryGoal=null,adventureArchiveGoal=null;
const adventureDrafts={};
function renderSavingsGoals(){
  const goals=state.adventure.goals,active=goals.filter(g=>!g.archived),archived=goals.filter(g=>g.archived);
  $('savings-summary').innerHTML=`<div><span>进行中的目标</span><strong>${active.length} <small>/ 3 个</small></strong></div><div><span>已为目标留出</span><strong>${cash(active.reduce((v,g)=>v+g.balance_fen,0))}</strong></div>`;
  $('savings-goals').innerHTML=active.length?active.map(g=>`<article class="panel savings-goal"><div class="savings-goal-heading"><h3>${esc(g.title)}</h3><span>${g.complete?'已达成':g.progress_pct+'%'}</span></div><div class="savings-amount"><strong>${cash(g.balance_fen)}</strong><span> / ${cash(g.target_fen)}</span></div><div class="savings-track" role="progressbar" aria-label="${esc(g.title)}储蓄进度" aria-valuenow="${g.progress_pct}" aria-valuemin="0" aria-valuemax="100"><span style="width:${g.progress_pct}%"></span></div><p>${g.complete?'已达到目标金额': '还差 '+cash(g.remaining_fen)}${g.deadline?' · '+esc(g.deadline):''}</p><div class="actions"><button data-adventure-entry="${g.id}">记录存入 / 取回</button><button class="secondary" data-adventure-archive="${g.id}">归档</button></div></article>`).join(''):'<div class="panel memory-empty"><span>＋</span><h3>先定一个想实现的小目标</h3><p>说说想存多少钱，AI 会帮你补充必要细节。</p><button data-savings-create>和 AI 聊聊目标</button></div>';
  $('new-adventure-goal').disabled=active.length>=3;
  $('new-adventure-goal').title=active.length>=3?'已有三个目标，可先归档一个':'';
  $('savings-archived').hidden=!archived.length;
  $('savings-archive-list').innerHTML=archived.map(g=>`<div class="savings-history-row"><span>${esc(g.title)} · ${cash(g.balance_fen)} / ${cash(g.target_fen)}</span><button class="secondary" data-adventure-restore="${g.id}">恢复目标</button></div>`).join('');
  $('adventure-entries').innerHTML=state.adventure.entries.length?state.adventure.entries.map(e=>`<div class="savings-history-row"><div><strong>${esc(e.goal_title)}</strong><small>${esc(e.note||'')} · ${new Date(e.created_at).toLocaleString('zh-CN',{hour12:false})}</small></div><strong>${e.kind==='deposit'?'存入':'取回'} ${cash(e.amount_fen)}</strong></div>`).join(''):'<p class="muted">确认记录存入或取回后，会在这里显示。</p>';
}
function openAdventureGoal(){openSetupChat('goal');}
function openAdventureEntry(id){openSetupChat('allocation',{goal_id:id});}
function openAdventureReflection(month){openSetupChat('reflection',{month:month||$('review-month').value||undefined});}
function openManualAdventureGoal(){
  $('adventure-goal-form').reset();$('adventure-goal-deadline').min=state.adventure.today;$('adventure-goal-deadline').value='';$('adventure-goal-error').textContent='';adventureDrafts.goal=null;$('adventure-goal-dialog').showModal();
}
function openManualAdventureEntry(id){
  const goal=state.adventure.goals.find(g=>g.id===id);if(!goal||goal.archived)return;
  adventureEntryGoal=id;$('adventure-entry-form').reset();$('adventure-entry-title').textContent=goal.title;$('adventure-entry-balance').textContent='已记录 '+cash(goal.balance_fen)+'，目标 '+cash(goal.target_fen);$('adventure-entry-error').textContent='';adventureDrafts.entry=null;$('adventure-entry-dialog').showModal();
}
function openManualAdventureReflection(month){
  $('adventure-reflect-month').value=month||$('review-month').value||state.overview.months.at(-1)?.month||'';$('adventure-reflect-note').value=state.adventure.reflection?.note||'';$('adventure-reflect-error').textContent='';$('adventure-reflect-dialog').showModal();
}
function adventureRequest(name,payload){const signature=JSON.stringify(payload);if(adventureDrafts[name]?.signature!==signature)adventureDrafts[name]={signature,id:crypto.randomUUID().replaceAll('-','')};return {...payload,request_id:adventureDrafts[name].id};}
async function submitSavings(event,errorId,task){event.preventDefault();event.submitter.disabled=true;$(errorId).textContent='';try{await task();}catch(error){$(errorId).textContent=errorMessage(error);}finally{event.submitter.disabled=false;}}
$('new-adventure-goal').addEventListener('click',openAdventureGoal);
$('goals').addEventListener('click',e=>run(async()=>{
  const b=e.target.closest('button');if(!b)return;
  if(b.hasAttribute('data-savings-create'))openAdventureGoal();
  if(b.dataset.adventureEntry)openAdventureEntry(Number(b.dataset.adventureEntry));
  if(b.dataset.adventureArchive){adventureArchiveGoal=Number(b.dataset.adventureArchive);$('adventure-archive-copy').textContent='归档“'+state.adventure.goals.find(g=>g.id===adventureArchiveGoal).title+'”？';$('adventure-archive-dialog').showModal();}
  if(b.dataset.adventureRestore){await api('/api/adventure/archive',{goal_id:Number(b.dataset.adventureRestore),archived:false});await refresh();notice('目标已恢复。');}
}));
$('adventure-goal-form').addEventListener('submit',e=>submitSavings(e,'adventure-goal-error',async()=>{await api('/api/adventure/goals',adventureRequest('goal',{title:$('adventure-goal-title').value,target:$('adventure-goal-target').value,initial:$('adventure-goal-initial').value,deadline:$('adventure-goal-deadline').value}));$('adventure-goal-dialog').close();await refresh();notice('目标已创建。');}));
$('adventure-entry-form').addEventListener('submit',e=>submitSavings(e,'adventure-entry-error',async()=>{await api('/api/adventure/entries',adventureRequest('entry',{goal_id:adventureEntryGoal,kind:$('adventure-entry-kind').value,amount:$('adventure-entry-amount').value,note:$('adventure-entry-note').value}));$('adventure-entry-dialog').close();await refresh();notice('储蓄进度已更新。');}));
$('adventure-reflect-form').addEventListener('submit',e=>submitSavings(e,'adventure-reflect-error',async()=>{await api('/api/adventure/reflect',{month:$('adventure-reflect-month').value,note:$('adventure-reflect-note').value});$('adventure-reflect-dialog').close();await refresh();notice('复盘心得已保存。');}));
$('adventure-confirm-archive').addEventListener('click',()=>run(async()=>{await api('/api/adventure/archive',{goal_id:adventureArchiveGoal,archived:true});$('adventure-archive-dialog').close();await refresh();notice('目标已归档，历史记录保留。');}));
document.querySelectorAll('[data-close-adventure]').forEach(b=>b.addEventListener('click',()=>$(b.dataset.closeAdventure).close()));
