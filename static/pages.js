'use strict';
const pageDefinitions={
  overview:{name:'首页',title:'记好每一笔，靠近小目标。',description:'先看清收支，再安排今天的一小步。',icon:'coin'},
  records:{name:'账单明细',title:'每一笔，都清清楚楚。',description:'导入、审核和查找账单，保留每个数字的来源。',icon:'book'},
  insights:{name:'统计分析',title:'读懂自己的财务节奏。',description:'周月图表、六维习惯、AI 建议与四格日记。',icon:'chart'},
  goals:{name:'储蓄目标',title:'让每个小愿望，慢慢实现。',description:'和 AI 聊聊目标，再把行动积累成看得见的进步。',icon:'star'},
  memories:{name:'分类记忆',title:'确认一次，记住实际用途。',description:'查看和管理你确认过的分类经验。',icon:'book'},
  'smart-plans':{name:'储蓄计划',title:'找到适合自己的储蓄路线。',description:'告诉 AI 你的想法和限制，一起完善可执行的方案。',icon:'coin'},
  assistant:{name:'AI 助手',title:'想了解账本，直接问就好。',description:'多轮查账、消费比较和储蓄分析，都有依据可查。',icon:'chat'}
};
const pageAliases={adventure:'goals',plan:'smart-plans','monthly-review':'insights'};
let activePage=null;
function resolvePage(value){return pageAliases[value]|| (Object.hasOwn(pageDefinitions,value)?value:'overview');}
function activatePage(value,focus=true){
  const page=resolvePage(value),definition=pageDefinitions[page];activePage=page;
  document.querySelectorAll('[data-pages]').forEach(el=>{el.hidden=!el.dataset.pages.split(' ').includes(page);});
  document.querySelector('header h1').textContent=definition.title;document.querySelector('header .muted').textContent=definition.description;
  document.querySelector('header .eyebrow').textContent='LedgerLens / '+definition.name;
  document.title=definition.name+' · LedgerLens';document.body.dataset.currentPage=page;
  $('page-picker').value=page;
  document.querySelectorAll('aside nav a,.bottom-nav a').forEach(a=>{const selected=resolvePage(a.hash.slice(1))===page;a.classList.toggle('nav-selected',selected);if(selected)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  if(focus){document.querySelector('header h1').focus({preventScroll:true});window.scrollTo({top:0,behavior:'instant'});}
  if(pageAliases[value]){const target=$(value);const details=target?.closest('details');if(details)details.open=true;target?.scrollIntoView({behavior:'instant'});}
}
function navigatePage(value){
  const page=Object.hasOwn(pageDefinitions,value)||Object.hasOwn(pageAliases,value)?value:'overview';
  if(location.hash!=='#'+page)history.pushState(null,'','#'+page);
  activatePage(page);
}
const sideNav=document.querySelector('aside nav');sideNav.setAttribute('aria-label','主导航');
sideNav.innerHTML=Object.entries(pageDefinitions).map(([id,p])=>`<a href="#${id}"><span class="page-nav-icon">${uiIcon(p.icon)}</span>${esc(p.name)}</a>`).join('');
const h1=document.querySelector('header h1');h1.tabIndex=-1;
const headerActions=document.createElement('div');headerActions.className='page-header-actions';headerActions.append($('mode'));
const picker=document.createElement('select');picker.id='page-picker';picker.setAttribute('aria-label','切换页面');picker.innerHTML=Object.entries(pageDefinitions).map(([id,p])=>`<option value="${id}">${esc(p.name)}</option>`).join('');picker.addEventListener('change',()=>navigatePage(picker.value));headerActions.append(picker);
const quick=document.createElement('button');quick.id='header-quick-entry';quick.textContent='＋ 记一笔';quick.type='button';quick.addEventListener('click',openQuickEntry);headerActions.append(quick);document.querySelector('header').append(headerActions);
const home=document.createElement('a');home.href='#overview';home.innerHTML=`<span>${uiIcon('coin')}</span>首页`;document.querySelector('.bottom-nav').prepend(home);
document.addEventListener('click',event=>{const link=event.target.closest('a[href^="#"]');if(!link||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;const target=link.hash.slice(1);if(Object.hasOwn(pageDefinitions,target)||Object.hasOwn(pageAliases,target)){event.preventDefault();navigatePage(target);}});
window.addEventListener('hashchange',()=>activatePage(location.hash.slice(1)));window.addEventListener('popstate',()=>activatePage(location.hash.slice(1)));
activatePage(location.hash.slice(1),false);
