'use strict';
let focusedAdventureGoal=null,lastAdventureXp=null,adventureToastTimer,adventureEntryGoal=null,adventureArchiveGoal=null;
const adventureDrafts={};
const newAdventureId=()=>crypto.randomUUID().replaceAll('-','');
const adventureIcon=name=>{
  const paths={flag:'M8 23V5m0 1c6-5 8 5 15 0v10c-7 5-9-5-15 0',book:'M5 6h8c2 0 3 1 3 3v17c0-3-3-3-11-3zm22 0h-8c-2 0-3 1-3 3v17c0-3 3-3 11-3z',search:'M21 21l7 7M24 14a10 10 0 1 1-20 0 10 10 0 0 1 20 0',seed:'M16 28V14M16 20C4 20 3 12 5 8c8-1 12 5 11 12m0-6C16 5 23 2 28 4c1 7-4 12-12 10',map:'M3 7l9-4 9 4 8-4v22l-8 4-9-4-9 4zm9-4v22m9-18v22',note:'M7 3h17v26H7zm4 7h9m-9 6h9m-9 6h6',star:'M16 2l4 9 10 1-8 7 3 10-9-5-9 5 3-10-8-7 10-1z',sun:'M16 1v4m0 22v4M1 16h4m22 0h4M5 5l3 3m16 16 3 3M5 27l3-3M24 8l3-3M24 16a8 8 0 1 1-16 0 8 8 0 0 1 16 0'};
  return `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="${paths[name]||paths.star}" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
};
function adventureScene(stage){
  const theme=state?.adventure.theme||'forest',accent=theme==='ocean'?'#93c6cf':theme==='space'?'#b8acd7':'#b5c99d';
  const nodes=[[77,181],[190,101],[319,178],[445,101],[563,170]];
  const icons=['<path d="M-7 8V-8m0 0q9-8 19-1v11q-10-6-19 1"/>','<path d="m-12 9 11-7 11 7M-9 10H9M0 2q-13-9 0-23-1 8 6 10 6 8-6 13z"/>','<path d="m-15-2 15-14L15-2M-11-2v16h22V-2M-3 14V3h6v11"/>','<path d="M-10 14h20M-8 10l3-26h10l3 26M-7-6H7M-7 2H7M-5-16l5-6 5 6"/>','<path d="m0-17 5 10 11 2-8 8 2 11-10-5-10 5 2-11-8-8 11-2z"/>'];
  const [fx,fy]=nodes[stage];
  return `<svg viewBox="0 0 640 280" class="journey-scene" role="img" aria-label="目标冒险地图，已点亮 ${stage} 个里程碑" xmlns="http://www.w3.org/2000/svg">
  <defs><pattern id="camp-dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#eae7d7"/></pattern></defs>
  <rect x="18" y="18" width="604" height="246" rx="24" fill="#fffdf5"/><rect x="18" y="18" width="604" height="246" rx="24" fill="url(#camp-dots)"/>
  <ellipse cx="150" cy="220" rx="55" ry="11" fill="${accent}" opacity=".16"/><ellipse cx="488" cy="213" rx="67" ry="12" fill="${accent}" opacity=".18"/>
  <path d="M77 181C123 181 139 101 190 101S263 178 319 178 392 101 445 101 521 170 563 170" fill="none" stroke="#e7e1ca" stroke-width="16" stroke-linecap="round"/>
  <path d="M77 181C123 181 139 101 190 101S263 178 319 178 392 101 445 101 521 170 563 170" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="3 10" stroke-linecap="round"/>
  ${nodes.map(([x,y],i)=>`<g transform="translate(${x},${y})"><ellipse cy="23" rx="25" ry="5" fill="#eee9d5"/><circle r="25" fill="${i<=stage?'#ffe378':'#fff'}" stroke="${i<=stage?'#d4b548':'#dedfdc'}" stroke-width="1.5"/><g stroke="${i<=stage?'#82702f':'#bbbbb2'}" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${icons[i]}</g><text y="46" text-anchor="middle" font-family="Microsoft YaHei,Segoe UI,sans-serif" font-size="10" fill="${i<=stage?'#a28a32':'#b7b7ad'}">${['出发','25% 营火','50% 小屋','75% 观景台','100% 愿望'][i]}</text></g>`).join('')}
  <g transform="translate(${fx},${fy-48})" class="world-traveler"><path d="M-13-8-15-24-3-15q7-4 13 0l12-9-3 18q4 17-16 18T-13-8" fill="#fff8dc" stroke="#a18f53" stroke-width="1.5"/><circle cx="-5" cy="-3" r="1.8" fill="#594f36"/><circle cx="9" cy="-3" r="1.8" fill="#594f36"/><path d="m0 3 3 2 3-2" fill="none" stroke="#594f36" stroke-linecap="round"/><path d="M-9 9q12 6 22-1l-1 7q-12 5-21-1z" fill="#f1cd45"/></g>
  <g fill="none" stroke="${accent}" stroke-width="2" stroke-linecap="round"><path d="M51 81v-20m0 11q-10 0-10-9 10 0 10 9m0-4q10 0 10-10-10 0-10 10M391 222v-20m0 11q-10 0-10-9 10 0 10 9m0-4q10 0 10-10-10 0-10 10"/></g>
  <g stroke="#e5ce77" stroke-width="1.5"><path d="M317 54v12m-6-6h12M574 73v10m-5-5h10"/></g></svg>`;
}

function renderAdventure(){
  const game=state?.adventure;if(!game)return;
  if(lastAdventureXp!==null&&game.xp>lastAdventureXp){
    $('adventure-toast').hidden=false;$('adventure-toast').innerHTML=`${adventureIcon('star')}<div><strong>这一步，值得被看见。</strong><span>获得 ${game.xp-lastAdventureXp} 点成长经验</span></div>`;
    clearTimeout(adventureToastTimer);adventureToastTimer=setTimeout(()=>$('adventure-toast').hidden=true,4500);
  }
  lastAdventureXp=game.xp;
  $('adventure-level').textContent='第 '+game.level+' 级';$('adventure-rank').textContent=game.level_title;
  $('adventure-xp').textContent=game.xp+' 点经验';$('adventure-next').textContent=game.next_level_xp?'距下一级 '+(game.next_level_xp-game.xp)+' 点':'已到达当前最高等级';
  const xpPercent=game.next_level_xp?Math.min(100,(game.xp-game.level_start_xp)/(game.next_level_xp-game.level_start_xp)*100):100;
  $('adventure-level-bar').setAttribute('aria-valuenow',Math.floor(xpPercent));$('adventure-level-bar').setAttribute('aria-valuemin','0');$('adventure-level-bar').setAttribute('aria-valuemax','100');$('adventure-level-bar').querySelector('span').style.width=xpPercent+'%';
  $('adventure-streak').textContent=game.streak+' 天';$('adventure-day').textContent=game.today;
  $('adventure-week').textContent=game.weekly_days+' / 3 天'+(game.weekly_complete?' · 已达成':'');
  $('adventure-world').className='adventure-world '+game.theme;
  $('adventure-themes').innerHTML=game.themes.map(theme=>`<button class="theme-choice ${theme.id===game.theme?'selected':''}" data-adventure-theme="${theme.id}" ${theme.unlocked?'':'disabled'} aria-pressed="${theme.id===game.theme}" title="${esc(theme.unlocked?theme.title:theme.title+' · 第 '+theme.level+' 级解锁')}">${esc(theme.title)}${theme.unlocked?'':' · '+theme.level+'级'}</button>`).join('');
  const active=game.goals.filter(g=>!g.archived);let goal=active.find(g=>g.id===focusedAdventureGoal)||active[0];focusedAdventureGoal=goal?.id??null;
  const stage=goal?goal.milestones.filter(m=>m.reached).length:0;
  $('adventure-scene').innerHTML=adventureScene(stage);
  $('adventure-focus').innerHTML=goal?`<div class="focus-goal-heading"><div><p class="eyebrow">${goal.complete?'愿望已抵达':'正在努力的愿望'}</p><h3>${esc(goal.title)}</h3></div><span class="goal-percent">${goal.progress_pct}<small>%</small></span></div><div class="goal-money"><strong>${cash(goal.balance_fen)}</strong><span> / ${cash(goal.target_fen)}</span></div><div class="goal-track" role="progressbar" aria-label="目标储蓄进度" aria-valuenow="${goal.progress_pct}" aria-valuemin="0" aria-valuemax="100"><span style="width:${goal.progress_pct}%"></span></div><div class="milestone-row">${goal.milestones.map(m=>`<div class="${m.reached?'reached':''}"><span>${m.reached?'✓':'◇'}</span><strong>${m.percent}%</strong><small>${esc(m.title)}</small></div>`).join('')}</div><div class="goal-action-row"><span>${goal.complete?'已经走到这里，值得为自己庆祝。':goal.days_left===null?'按自己的节奏，一点点靠近。':goal.days_left<0?'目标日期已过，仍可继续记录，不扣经验。':'距目标日期还有 '+goal.days_left+' 天'}${!goal.complete?' · 还差 '+cash(goal.remaining_fen):''}</span><button class="small" data-adventure-entry="${goal.id}">记录储蓄进展</button></div>`:
    `<div class="adventure-empty"><p class="eyebrow">每一个愿望，都有一条自己的路</p><h3>你的第一片营地，正在等你。</h3><p>为旅行、一台电脑，或一份安心感设立目标。每次向前一点，都会留下新的风景。</p><button data-adventure-create>设立我的第一个目标</button></div>`;
  $('adventure-quests').innerHTML=game.daily_quests.map(quest=>`<div class="daily-quest ${quest.complete?'quest-done':''}"><span class="quest-tick">${quest.complete?'✓':'◇'}</span><div><strong>${esc(quest.title)}</strong><p>${esc(quest.description)}</p></div><div><span class="quest-xp">＋${quest.xp} 经验</span><button class="secondary small" data-adventure-quest="${quest.action}" ${quest.complete?'disabled':''}>${quest.complete?'今日已完成':'去完成'}</button></div></div>`).join('');
  $('adventure-goals').innerHTML=active.length?active.map(g=>`<article class="journey-goal ${g.id===focusedAdventureGoal?'goal-focused':''}"><button class="goal-select" data-adventure-focus="${g.id}" aria-pressed="${g.id===focusedAdventureGoal}"><span>${g.complete?'✦ 已达成':'正在远征'}</span><h3>${esc(g.title)}</h3><p><strong>${cash(g.balance_fen)}</strong> / ${cash(g.target_fen)}</p><div class="goal-track"><span style="width:${g.progress_pct}%"></span></div></button><div class="actions"><button class="small secondary" data-adventure-entry="${g.id}">记录存入 / 取回</button><button class="small secondary" data-adventure-archive="${g.id}">归档</button></div></article>`).join(''):'<p class="muted">还没有进行中的目标，点击上方“开启新目标”出发。</p>';
  const archived=game.goals.filter(g=>g.archived);
  if(archived.length)$('adventure-goals').innerHTML+=`<details class="archived-goals"><summary>已收好的 ${archived.length} 个目标</summary>${archived.map(g=>`<div><span>${esc(g.title)} · ${cash(g.balance_fen)} / ${cash(g.target_fen)}</span><button class="small secondary" data-adventure-restore="${g.id}">重新启程</button></div>`).join('')}</details>`;
  $('adventure-badge-count').textContent=game.badges.filter(b=>b.earned).length+' / '+game.badges.length+' 枚已点亮';
  $('adventure-badges').innerHTML=game.badges.map(b=>`<div class="journey-badge ${b.earned?'badge-earned':''}" title="${esc(b.description)}"><span>${adventureIcon(b.icon)}</span><strong>${esc(b.title)}</strong><small>${b.earned?'已获得':esc(b.description)}</small></div>`).join('');
  $('adventure-entries').innerHTML=game.entries.length?game.entries.map(entry=>`<p><strong>${entry.kind==='deposit'?'存入':'取回'} ${cash(entry.amount_fen)}</strong> · ${esc(entry.goal_title)}<small>${esc(entry.note||'未填写备注')} · ${new Date(entry.created_at).toLocaleString('zh-CN',{hour12:false})}</small></p>`).join(''):'<p class="muted">你的下一步，会成为这里的第一条记录。</p>';
  $('adventure-rewards').innerHTML=game.recent_rewards.length?game.recent_rewards.map(reward=>`<p><strong>＋${reward.xp} 经验</strong> · ${esc(reward.title)}<small>${esc(reward.day)}</small></p>`).join(''):'<p class="muted">完成小任务，点亮第一份成长记录。</p>';
}

function openAdventureGoal(){openSetupChat('goal');}
function openManualAdventureGoal(){
  $('adventure-goal-form').reset();$('adventure-goal-deadline').min=state.adventure.today;$('adventure-goal-deadline').value=state.adventure.suggested_deadline;
  $('adventure-goal-error').textContent='';adventureDrafts.goal=null;$('adventure-goal-dialog').showModal();
}
function openAdventureEntry(id){openSetupChat('allocation',{goal_id:id});}
function openManualAdventureEntry(id){
  const goal=state.adventure.goals.find(g=>g.id===id);if(!goal||goal.archived)return;
  adventureEntryGoal=id;$('adventure-entry-form').reset();$('adventure-entry-title').textContent=goal.title;
  $('adventure-entry-balance').textContent='目前已为此目标记录 '+cash(goal.balance_fen)+'，目标 '+cash(goal.target_fen)+'。';
  $('adventure-entry-error').textContent='';adventureDrafts.entry=null;$('adventure-entry-dialog').showModal();
}
function openAdventureReflection(month){openSetupChat('reflection',{month:month||$('review-month').value||undefined});}
function openManualAdventureReflection(month){
  $('adventure-reflect-month').value=month||$('review-month').value||state.overview.months.at(-1)?.month||'';
  $('adventure-reflect-note').value=state.adventure.reflection?.note||'';$('adventure-reflect-error').textContent='';$('adventure-reflect-dialog').showModal();
}
function adventureRequest(name,payload){
  const signature=JSON.stringify(payload);
  if(adventureDrafts[name]?.signature!==signature)adventureDrafts[name]={signature,id:newAdventureId()};
  return {...payload,request_id:adventureDrafts[name].id};
}
async function submitAdventure(event,errorId,task){
  event.preventDefault();event.submitter.disabled=true;$(errorId).textContent='';
  try{await task();}catch(error){$(errorId).textContent=errorMessage(error);}finally{event.submitter.disabled=false;}
}
$('new-adventure-goal').addEventListener('click',openAdventureGoal);
$('adventure-goal-form').addEventListener('submit',event=>submitAdventure(event,'adventure-goal-error',async()=>{
  const result=await api('/api/adventure/goals',adventureRequest('goal',{title:$('adventure-goal-title').value,target:$('adventure-goal-target').value,initial:$('adventure-goal-initial').value,deadline:$('adventure-goal-deadline').value}));
  focusedAdventureGoal=result.id;$('adventure-goal-dialog').close();await refresh();notice('目标已设立，你的储蓄远征开始了。');
}));
$('adventure-entry-form').addEventListener('submit',event=>submitAdventure(event,'adventure-entry-error',async()=>{
  await api('/api/adventure/entries',adventureRequest('entry',{goal_id:adventureEntryGoal,kind:$('adventure-entry-kind').value,amount:$('adventure-entry-amount').value,note:$('adventure-entry-note').value}));
  $('adventure-entry-dialog').close();await refresh();notice('储蓄进展已记录。每一步，都在靠近自己的目标。');
}));
$('adventure-reflect-form').addEventListener('submit',event=>submitAdventure(event,'adventure-reflect-error',async()=>{
  await api('/api/adventure/reflect',{month:$('adventure-reflect-month').value,note:$('adventure-reflect-note').value});$('adventure-reflect-dialog').close();await refresh();notice('复盘心得已保存；同一天修改不会重复获得经验。');
}));
document.querySelectorAll('[data-close-adventure]').forEach(button=>button.addEventListener('click',()=>$(button.dataset.closeAdventure).close()));
$('adventure').addEventListener('click',event=>run(async()=>{
  const button=event.target.closest('button');if(!button)return;
  if(button.hasAttribute('data-adventure-create'))openAdventureGoal();
  if(button.dataset.adventureEntry)openAdventureEntry(Number(button.dataset.adventureEntry));
  if(button.dataset.adventureFocus){focusedAdventureGoal=Number(button.dataset.adventureFocus);renderAdventure();}
  if(button.dataset.adventureTheme){await api('/api/adventure/theme',{theme:button.dataset.adventureTheme});await refresh();}
  if(button.dataset.adventureArchive){adventureArchiveGoal=Number(button.dataset.adventureArchive);$('adventure-archive-copy').textContent='归档“'+state.adventure.goals.find(g=>g.id===adventureArchiveGoal).title+'”后，它会从进行中的目标移走。';$('adventure-archive-dialog').showModal();}
  if(button.dataset.adventureRestore){await api('/api/adventure/archive',{goal_id:Number(button.dataset.adventureRestore),archived:false});focusedAdventureGoal=Number(button.dataset.adventureRestore);await refresh();}
  if(button.dataset.adventureQuest==='import'){$('csv-file').click();}
  if(button.dataset.adventureQuest==='review'){const record=state.transactions.find(r=>r.review_status==='needs_review');if(record)openPurpose(record);else{notice('没有待确认账单时无需重复审核；导入新的模糊账单后再完成此任务。');navigatePage('records');$('records').scrollIntoView({behavior:'smooth'});}}
  if(button.dataset.adventureQuest==='reflect')openAdventureReflection();
}));
$('adventure-confirm-archive').addEventListener('click',()=>run(async()=>{await api('/api/adventure/archive',{goal_id:adventureArchiveGoal,archived:true});$('adventure-archive-dialog').close();await refresh();notice('目标已收好，历史记录和经验都已保留。');}));
document.addEventListener('DOMContentLoaded',()=>{if(state?.adventure)renderAdventure();});
