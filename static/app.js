'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cash = fen => new Intl.NumberFormat('zh-CN',{style:'currency',currency:'CNY'}).format(fen/100);
let state, token, trace=null, proposal=null, localeLabels={};
const l=value=>localeLabels[value]??value;
async function api(path,body,method='POST'){
  const response=await fetch(path,{method,headers:{'Content-Type':'application/json','X-Ledger-Token':token,'Accept-Language':'zh-CN'},body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw Error(data.error||'请求失败，请重试。');return data;
}
function notice(text,error=false){const box=$('notice');box.hidden=false;box.textContent=text;box.className=error?'error':'';const dismiss=document.createElement('button');dismiss.type='button';dismiss.className='notice-dismiss';dismiss.setAttribute('aria-label','关闭提示');dismiss.textContent='×';dismiss.addEventListener('click',()=>box.hidden=true);box.append(dismiss);}
function errorMessage(error){return error instanceof TypeError?'无法连接本地服务，请确认软件正在运行。':(/[\u4e00-\u9fff]/.test(error.message)?error.message:'操作未完成，请刷新页面后重试。');}
async function run(task){try{return await task();}catch(error){notice(errorMessage(error),true);return null;}}
async function refresh(){const response=await fetch('/api/state',{headers:{'Accept-Language':'zh-CN'}});if(!response.ok)throw Error('无法读取账本，请重试。');state=await response.json();render();}
function options(categories,selected){return categories.map(c=>`<option value="${esc(c)}" ${c===selected?'selected':''}>${esc(l(c))}</option>`).join('');}
function showTrace(ids,label){trace=new Set(ids);$('record-search').value='';$('filter').value='all';$('trace-label').textContent=label;renderRows();navigatePage('records');$('records').scrollIntoView({behavior:'smooth'});}
function renderPlan(p){
  if(!p)return;
  $('projected').textContent=cash(p.projected_fen);$('feasible').textContent=p.feasible?'按此情景可以达到目标。':'距离目标还差 '+cash(p.gap_fen);$('feasible').className=p.feasible?'ok':'warning';
  const lines=[['目标金额',p.target_fen],['每月所需储蓄',p.required_monthly_fen],['基准每月结余',p.baseline_monthly_fen],['每月还需增加',p.extra_required_fen],['每月减少支出',p.monthly_reduction_fen],['方案每月储蓄',p.scenario_monthly_fen]];
  $('plan-details').innerHTML=lines.map(([label,value])=>`<div><dt>${label}</dt><dd>${cash(value)}</dd></div>`).join('');$('plan-assumption').textContent=p.assumption;
}
function auditValue(value,key=''){
  if(value===null)return '未设置';if(typeof value==='boolean')return value?'是':'否';
  if(typeof value==='number')return key.endsWith('_fen')?cash(value):String(value);
  if(Array.isArray(value))return value.length?value.map(item=>auditValue(item,key)).join('、'):'无';
  if(typeof value==='object')return '<dl class="audit-fields">'+Object.entries(value).filter(([k])=>!['fingerprint','import_fingerprint','ledger_revision'].includes(k)).map(([k,v])=>`<div><dt>${esc(l(k))}</dt><dd>${auditValue(v,key.endsWith('_fen')?key:k)}</dd></div>`).join('')+'</dl>';
  return esc(l(value));
}
function render(){
  const o=state.overview;$('income').textContent=cash(o.income_fen);$('expense').textContent=cash(o.expense_fen);$('net').textContent=cash(Math.round(o.net_fen/3));$('count').textContent=o.record_ids.length;
  $('period').textContent=o.months.length?o.months[0].month+' 至 '+o.months.at(-1).month:'暂无数据';$('mode').textContent=state.model_enabled?'AI 已配置 · 可启用分析':'本地规则模式 · 未配置 AI';$('assumptions').textContent=o.assumption;
  const max=Math.max(...o.months.flatMap(m=>[m.income_fen,m.expense_fen]),1);
  $('monthly-chart').innerHTML=o.months.length?o.months.map(m=>`<div class="month"><div class="chart-value">${cash(m.income_fen)} / ${cash(m.expense_fen)}</div><div class="bar-pair"><div class="bar income" style="height:${Math.max(1,m.income_fen/max*140)}px" title="收入 ${cash(m.income_fen)}"></div><div class="bar expense" style="height:${Math.max(1,m.expense_fen/max*140)}px" title="支出 ${cash(m.expense_fen)}"></div></div><div class="month-label">${esc(m.month)}</div></div>`).join(''):'<p class="muted">导入账单后，这里会显示收支图表。</p>';
  const maxCategory=Math.max(...o.categories.map(c=>c.amount_fen),1);
  $('category-chart').innerHTML=o.categories.filter(c=>c.amount_fen).sort((a,b)=>b.amount_fen-a.amount_fen).map(c=>`<button class="category-row" data-category="${esc(c.category)}"><span class="category-label"><span>${esc(l(c.category))}</span><span>${cash(c.amount_fen)}</span></span><div class="track"><span style="width:${c.amount_fen/maxCategory*100}%"></span></div></button>`).join('');
  const selected=$('filter').value;$('filter').innerHTML='<option value="all">全部分类</option>'+options(state.categories,selected);$('budget-category').innerHTML=options(state.expense_categories,$('budget-category').value||'Shopping');renderRows();
  $('budget-list').innerHTML=state.budgets.length?state.budgets.map(b=>`<div class="budget-item"><span>${esc(l(b.category))} · ${esc(b.month||'暂无数据')} · ${cash(b.spent_fen)} / ${cash(b.limit_fen)}</span><span class="${b.overrun_fen?'warning':'ok'}">${b.overrun_fen?'超出预算 '+cash(b.overrun_fen):'未超出预算'}</span><button class="secondary small" data-budget="${esc(b.category)}">查看来源账单</button></div>`).join(''):'<p class="muted small">尚未设置预算，请在上方填写每月预算。</p>';
  $('audit').innerHTML=state.audit.map(a=>{let details;try{details=JSON.parse(a.details);}catch{details=a.details;}return `<details class="audit-entry"><summary>#${a.id} · ${a.action==='import'?'导入账单':esc(l(a.action))} · ${new Date(a.at).toLocaleString('zh-CN',{hour12:false})}</summary>${auditValue(details)}</details>`;}).join('');renderPlan(state.plan);if(typeof renderWorkflows==='function')renderWorkflows();if(typeof renderSavingsGoals==='function')renderSavingsGoals();if(typeof renderReports==='function')renderReports();
}
function loadPlanInputs(){const p=state.plan_input;$('target').value=p.target;$('current').value=p.current;$('months').value=p.months;const keys=['Shopping','Entertainment','Food'];$('cut-inputs').innerHTML=keys.map(k=>`<label class="cut-row"><span>${l(k)}</span><input type="range" min="0" max="100" value="${Number(p.cuts?.[k]||0)}" data-cut="${k}" aria-label="${l(k)}减支比例"><span data-cut-value="${k}">${Number(p.cuts?.[k]||0)}%</span></label>`).join('');}
function planInput(){const cuts={};document.querySelectorAll('[data-cut]').forEach(el=>cuts[el.dataset.cut]=Number(el.value));return {target:$('target').value,current:$('current').value,months:Number($('months').value),cuts};}
$('demo').addEventListener('click',()=>run(async()=>{const r=await api('/api/demo',{});await refresh();loadPlanInputs();notice(`示例账单已加载：新增 ${r.inserted} 笔，跳过 ${r.duplicates} 笔重复记录。示例数据均为合成数据。`);}));

$('filter').addEventListener('change',()=>{trace=null;$('trace-label').textContent='';renderRows();});$('clear-trace').addEventListener('click',()=>{trace=null;$('filter').value='all';$('trace-label').textContent='';renderRows();});
$('category-chart').addEventListener('click',e=>{const b=e.target.closest('[data-category]');if(b){const c=state.overview.categories.find(c=>c.category===b.dataset.category);showTrace(c.record_ids,l(c.category)+'的来源账单');}});
$('rows').addEventListener('change',e=>run(async()=>{const el=e.target.closest('[data-edit]');if(el){await api('/api/transactions/'+el.dataset.edit,{category:el.value},'PATCH');await refresh();notice('分类已更新，用户修正已记入操作记录。');}}));
$('rows').addEventListener('click',e=>run(async()=>{const el=e.target.closest('[data-review]');if(!el)return;proposal=await api('/api/suggest',{id:Number(el.dataset.review)});$('proposal-text').textContent=`账单 #${proposal.record_id}：建议归为${l(proposal.kind||state.transactions.find(r=>r.id===proposal.record_id).kind)} / ${l(proposal.category)}。参考置信度 ${Math.round(proposal.confidence*100)}%，来源：${l(proposal.source)}。${proposal.reason} ${proposal.notice||''}`;$('review-dialog').showModal();}));
$('cancel-proposal').addEventListener('click',()=>{$('review-dialog').close();proposal=null;});$('apply-proposal').addEventListener('click',()=>run(async()=>{if(!proposal)return;const patch={category:proposal.category};if(proposal.kind)patch.kind=proposal.kind;await api('/api/transactions/'+proposal.record_id,patch,'PATCH');$('review-dialog').close();proposal=null;await refresh();notice('已确认并应用分类建议。');}));
$('plan-form').addEventListener('submit',e=>{e.preventDefault();run(async()=>{const p=await api('/api/plan',planInput());await refresh();renderPlan(p);notice('测算已完成并保存，计算假设见结果下方。');});});
$('cut-inputs').addEventListener('input',e=>{if(e.target.dataset.cut)document.querySelector(`[data-cut-value="${e.target.dataset.cut}"]`).textContent=e.target.value+'%';});$('plan-trace').addEventListener('click',()=>{if(state.plan)showTrace(state.plan.record_ids,'储蓄测算使用的账单');});
$('budget-form').addEventListener('submit',e=>{e.preventDefault();run(async()=>{await api('/api/budgets',{category:$('budget-category').value,amount:$('budget-amount').value});await refresh();notice('每月预算已保存。');});});$('budget-list').addEventListener('click',e=>{const b=e.target.closest('[data-budget]');if(b){const budget=state.budgets.find(x=>x.category===b.dataset.budget);showTrace(budget.record_ids,'预算对应的来源账单');}});
async function ask(){return askConversation();}
$('ask-form').addEventListener('submit',e=>{e.preventDefault();run(ask);});document.querySelectorAll('[data-question]').forEach(el=>el.addEventListener('click',()=>{$('question').value=el.dataset.question;run(ask);}));
run(async()=>{const r=await fetch('/api/config',{headers:{'Accept-Language':'zh-CN'}});const config=await r.json();token=config.token;localeLabels=config.labels;await refresh();loadPlanInputs();});
// Native validation language otherwise depends on the browser installation.
document.addEventListener('invalid',event=>{const field=event.target;if(!field.validity||field.validity.customError)return;const validity=field.validity;let message='请检查填写内容。';if(validity.valueMissing)message='请填写此项内容。';else if(validity.badInput||validity.typeMismatch)message='请填写有效的数值或格式。';else if(validity.rangeUnderflow)message=`数值不能小于 ${field.min}。`;else if(validity.rangeOverflow)message=`数值不能大于 ${field.max}。`;else if(validity.stepMismatch)message='请按允许的精度填写，金额最多保留两位小数。';field.setCustomValidity(message);},true);
for(const eventName of ['input','change'])document.addEventListener(eventName,event=>{if(event.target.setCustomValidity)event.target.setCustomValidity('');});
