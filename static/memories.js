'use strict';
let memoryTab=null,memoryLimit=8,memoryDeleteId=null;
const memoryConditions=pattern=>Object.entries(pattern).map(([key,value])=>`<li><span>${key==='counterparty'?'交易对方是':key==='description'?'商品或描述包含':'备注包含'}</span><strong>${esc(value)}</strong></li>`).join('');
function renderMemoryPage(){
  const pending=state.transactions.filter(r=>r.review_status==='needs_review');
  if(!memoryTab)memoryTab=pending.length?'pending':'saved';
  $('memory-pending-count').textContent=pending.length;$('memory-saved-count').textContent=state.memories.length;
  document.querySelectorAll('[data-memory-tab]').forEach(b=>{const active=b.dataset.memoryTab===memoryTab;b.setAttribute('aria-selected',active);b.tabIndex=active?0:-1;});
  $('memory-pending-panel').hidden=memoryTab!=='pending';$('memory-saved-panel').hidden=memoryTab!=='saved';
  $('review-pending').hidden=!pending.length;
  $('memory-pending-list').innerHTML=pending.length?pending.slice(0,memoryLimit).map(r=>`<article class="pending-memory-card"><div class="pending-memory-heading"><span>${esc(r.date)} · #${r.id}</span><strong>${cash(r.amount_fen)}</strong></div><h3>${esc(l(r.description))}</h3><p>${esc(r.counterparty||'未提供交易对方')}</p>${r.note?'<p class="memory-context-note">备注：'+esc(r.note)+'</p>':''}<div class="memory-current-label">当前分类 <span>${esc(l(r.category))}</span><span class="memory-review-badge">需要确认</span></div><button class="secondary" data-memory-review="${r.id}">聊聊这笔用途 →</button></article>`).join(''):'<div class="memory-empty"><span>✓</span><h3>暂时没有待确认的账单</h3><p>导入账单后，遇到用途不明或记忆冲突的记录，会在这里请你确认。</p><button class="secondary" data-memory-import>导入账单</button></div>';
  $('memory-more').hidden=pending.length<=memoryLimit;
  $('memory-more').textContent='再显示 '+Math.max(0,Math.min(8,pending.length-memoryLimit))+' 笔';
  const query=$('memory-search').value.trim().toLocaleLowerCase();
  const matches=state.memories.filter(m=>[m.purpose,l(m.category),...Object.values(m.match)].join(' ').toLocaleLowerCase().includes(query));
  $('memory-list').innerHTML=matches.length?matches.map(m=>{
    const applied=state.transactions.filter(r=>r.memory_id===m.id&&r.category_source==='memory');
    return `<article class="memory-card"><div class="memory-card-top"><span class="memory-status ${!m.enabled?'paused':''}">${!m.enabled?'已停用':m.auto_apply?'自动分类':'匹配后请我确认'}</span><span class="note">第 ${m.version} 版</span></div><h3>${esc(m.purpose)}</h3><p class="memory-result">符合条件 → <strong>${esc(l(m.kind))} · ${esc(l(m.category))}</strong></p><p class="memory-conditions-caption">以下条件需要同时符合</p><ul class="memory-condition-list">${memoryConditions(m.match)}</ul><div class="memory-card-footer"><button class="text-button" data-memory-source="${m.source_id}">来源账单 #${m.source_id} ↗</button><span>${applied.length?'已自动识别 '+applied.length+' 笔':'等待后续账单匹配'}</span></div><div class="actions"><button class="secondary small" data-memory-edit="${m.id}">修改记忆</button><button class="secondary small" data-memory-toggle="${m.id}">${m.enabled?'停用':'启用'}</button><button class="text-button memory-delete" data-memory-delete="${m.id}">删除</button></div></article>`;
  }).join(''):`<div class="memory-empty"><span>◇</span><h3>${state.memories.length?'没有找到匹配的记忆':'还没有保存分类记忆'}</h3><p>${state.memories.length?'试试搜索用途、交易对方或关键词。':'先打开一笔待确认账单，说明用途，再选择是否记住。'}</p>${!state.memories.length&&pending.length?'<button class="secondary" data-memory-switch-pending>查看待确认账单</button>':''}</div>`;
}
function selectMemoryTab(tab){memoryTab=tab;renderMemoryPage();}
$('memory-tabs').addEventListener('click',e=>{const b=e.target.closest('[data-memory-tab]');if(b)selectMemoryTab(b.dataset.memoryTab);});
$('memory-tabs').addEventListener('keydown',e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;e.preventDefault();selectMemoryTab(e.key==='Home'?'pending':e.key==='End'?'saved':memoryTab==='pending'?'saved':'pending');document.querySelector('[data-memory-tab="'+memoryTab+'"]').focus();});
$('memory-search').addEventListener('input',renderMemoryPage);
$('memory-more').addEventListener('click',()=>{memoryLimit+=8;renderMemoryPage();});
$('memories').addEventListener('click',e=>{
  const review=e.target.closest('[data-memory-review]');if(review)openPurpose(state.transactions.find(r=>r.id===Number(review.dataset.memoryReview)));
  const source=e.target.closest('[data-memory-source]');if(source)showTrace([Number(source.dataset.memorySource)],'分类记忆的来源账单');
  if(e.target.closest('[data-memory-switch-pending]'))selectMemoryTab('pending');
  if(e.target.closest('[data-memory-import]'))$('csv-file').click();
});
$('memory-delete-cancel').addEventListener('click',()=>$('memory-delete-dialog').close());
$('memory-delete-confirm').addEventListener('click',()=>run(async()=>{
  const b=$('memory-delete-confirm');b.disabled=true;
  try{await api('/api/delete-memory',{id:memoryDeleteId});$('memory-delete-dialog').close();await refresh();notice('记忆已删除，已确认的历史分类保留。');}finally{b.disabled=false;}
}));
