'use strict';
const uiIcons={book:'<path d="M5 4h13a2 2 0 0 1 2 2v15H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3zM4 17h16M8 8h8M8 11h5"/>',chart:'<path d="M4 4v16h17M8 14l4-5 4 3 5-7"/>',star:'<path d="m12 3 3 6 6 1-4.5 4.5 1 6-5.5-3-5.5 3 1-6L3 10l6-1z"/>',chat:'<path d="M4 4h16v13H9l-5 4V4zM8 9h8M8 13h5"/>',coin:'<circle cx="12" cy="12" r="9"/><path d="m8 7 4 5 4-5M12 12v6M8 12h8M8 15h8"/>'};
const uiIcon=name=>`<svg viewBox="0 0 24 24" aria-hidden="true">${uiIcons[name]}</svg>`;
const entryPaths={Food:'<path d="M6 3v7m-3-7v4q0 3 3 3t3-3V3M6 10v11M17 3q-5 5-3 10h4M18 3v18"/>',Shopping:'<path d="M5 7h14l1 14H4L5 7zM8 8V6a4 4 0 0 1 8 0v2"/>',Housing:'<path d="m2 11 10-8 10 8M5 10v11h14V10M9 21v-7h6v7"/>',Transport:'<rect x="5" y="3" width="14" height="17" rx="3"/><path d="M5 12h14M8 20v2m8-2v2M8 7h8M8 16h1m6 0h1"/>',Entertainment:'<path d="M9 18V5l10-2v13M9 8l10-2"/><ellipse cx="6" cy="18" rx="3" ry="2"/><ellipse cx="16" cy="16" rx="3" ry="2"/>',Utilities:'<path d="M8 3v5m8-5v5M5 8h14v4a7 7 0 0 1-14 0V8zM12 19v3"/>',Health:'<rect x="3" y="6" width="18" height="15" rx="2"/><path d="M8 6V3h8v3M12 10v7m-4-3h8"/>',Education:'<path d="m2 8 10-5 10 5-10 5L2 8zM6 10v7q6 5 12 0v-7M22 8v9"/>',Other:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',Income:uiIcons.coin,Transfer:'<path d="M3 7h17l-4-4M21 17H4l4 4"/>'};
const entryIcon=c=>`<svg viewBox="0 0 24 24" aria-hidden="true">${entryPaths[c]||entryPaths.Other}</svg>`;
function openQuickEntry(){
  $('quick-entry-form').reset();$('entry-date').value=state.adventure.today;$('entry-date').max=state.adventure.today;
  $('entry-category').innerHTML=options(state.expense_categories,'Food');$('entry-error').textContent='';$('entry-draft-notice').textContent='填写后确认保存，账单会沿用分类记忆和重复检查。';
  $('entry-use-model').disabled=!state.model_enabled;renderEntryCategories();$('quick-entry-dialog').showModal();
}
function renderEntryCategories(){
  const kind=$('entry-kind').value,categories=kind==='expense'?state.expense_categories:[kind==='income'?'Income':'Transfer'];
  if(!categories.includes($('entry-category').value))$('entry-category').innerHTML=options(categories,categories[0]);
  $('entry-category-grid').innerHTML=categories.map(c=>`<button type="button" class="category-pick ${c===$('entry-category').value?'selected':''}" data-entry-category="${c}" aria-pressed="${c===$('entry-category').value}"><span>${entryIcon(c)}</span>${esc(l(c))}</button>`).join('');
}
$('open-quick-entry').addEventListener('click',openQuickEntry);$('mobile-quick-entry').addEventListener('click',openQuickEntry);
$('entry-kind').addEventListener('change',()=>{$('entry-category').innerHTML=options($('entry-kind').value==='expense'?state.expense_categories:[$('entry-kind').value==='income'?'Income':'Transfer']);renderEntryCategories();});
$('entry-category').addEventListener('change',renderEntryCategories);
$('entry-category-grid').addEventListener('click',e=>{const c=e.target.closest('[data-entry-category]')?.dataset.entryCategory;if(c){$('entry-category').value=c;renderEntryCategories();}});
$('entry-parse').addEventListener('click',async()=>{
  const button=$('entry-parse');button.disabled=true;$('entry-error').textContent='';
  try{const result=await api('/api/entries/draft',{text:$('entry-sentence').value,use_model:$('entry-use-model').checked});
    for(const [key,id] of Object.entries({date:'entry-date',description:'entry-description',amount:'entry-amount',kind:'entry-kind',counterparty:'entry-payee',note:'entry-note'}))$(id).value=result.record[key];
    $('entry-category').innerHTML=options(result.record.kind==='expense'?state.expense_categories:[result.record.category],result.record.category);renderEntryCategories();$('entry-draft-notice').textContent=result.notice;
  }catch(error){$('entry-error').textContent=errorMessage(error);}finally{button.disabled=false;}
});
$('entry-cancel').addEventListener('click',()=>$('quick-entry-dialog').close());
$('quick-entry-form').addEventListener('submit',async e=>{
  e.preventDefault();const button=e.submitter;button.disabled=true;$('entry-error').textContent='';
  try{const result=await api('/api/entries/save',{date:$('entry-date').value,description:$('entry-description').value,amount:$('entry-amount').value,kind:$('entry-kind').value,category:$('entry-category').value,counterparty:$('entry-payee').value,note:$('entry-note').value});$('quick-entry-dialog').close();await refresh();notice(result.saved?'账单已保存，图表已更新。':'这笔账单已经记录，已跳过重复提交。');}
  catch(error){$('entry-error').textContent=errorMessage(error);}finally{button.disabled=false;}
});
document.querySelectorAll('[data-ui-icon]').forEach(el=>el.innerHTML=uiIcon(el.dataset.uiIcon));
