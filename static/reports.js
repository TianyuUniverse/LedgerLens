'use strict';
const chartColors=['#f4c537','#75b6a2','#8e9ed4','#e9a188','#baabd7','#93bac4','#bcc989','#c7b9a3','#aab1b9'];
let periodReport=null,reportSequence=0,reportSignature='',reportBusy=false;
const traceAttr=ids=>ids?.length?`data-report-trace="${ids.join(',')}" tabindex="0" role="button"`:'';
function chartShell(label,content,view='0 0 680 260'){return `<svg viewBox="${view}" class="data-svg" role="img" aria-label="${esc(label)}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI,Microsoft YaHei,sans-serif">${content}</svg>`;}
function lineChart(points,series,label){
  const W=680,H=260,L=65,R=20,T=20,B=42,innerW=W-L-R,innerH=H-T-B;
  const values=series.flatMap(s=>points.map(p=>s.value(p)).filter(v=>v!==null));
  const high=Math.max(...values,100),low=Math.min(0,...values),range=high-low||1;
  const x=i=>L+i/Math.max(1,points.length-1)*innerW,y=v=>T+(high-v)/range*innerH;
  let out='';
  for(let i=0;i<=4;i++){const v=high-range*i/4,py=y(v);out+=`<line x1="${L}" y1="${py}" x2="${W-R}" y2="${py}" stroke="#eceef0" stroke-dasharray="3 5"/><text x="${L-10}" y="${py+4}" text-anchor="end" fill="#96999d" font-size="11">${esc(cash(v))}</text>`;}
  points.forEach((p,i)=>{if(i===0||i===points.length-1||i%Math.ceil(points.length/6)===0)out+=`<text x="${x(i)}" y="${H-13}" text-anchor="middle" font-size="11" fill="#8c9095">${esc(p.date.slice(5))}</text>`;});
  series.forEach(s=>{
    let path='',segments=[];
    points.forEach((p,i)=>{const v=s.value(p);if(v===null){if(path)segments.push(path);path='';}else path+=(path?' L':'M')+x(i)+' '+y(v);});if(path)segments.push(path);
    out+=segments.map(d=>`<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.6" stroke-linejoin="round"/>`).join('');
    points.forEach((p,i)=>{const v=s.value(p);if(v===null)return;const ids=s.ids?s.ids(p):p.record_ids;out+=`<circle cx="${x(i)}" cy="${y(v)}" r="${p.has_records===false?2.5:4}" fill="${p.has_records===false?'white':s.color}" stroke="${s.color}" stroke-width="1.5" ${traceAttr(ids)}><title>${esc(p.date+' · '+s.name+' '+cash(v)+(p.has_records===false?' · 无导入账单':''))}</title></circle>`;});
  });
  return `<div class="chart-key">${series.map(s=>`<span><i style="background:${s.color}"></i>${esc(s.name)}</span>`).join('')}</div>`+chartShell(label,out);
}
function renderRadar(report){
  const metrics=report.metrics,cx=200,cy=178,r=112;
  const pt=(i,scale)=>[cx+Math.cos(-Math.PI/2+i*Math.PI/3)*r*scale,cy+Math.sin(-Math.PI/2+i*Math.PI/3)*r*scale];
  let out='';
  for(let level=1;level<=5;level++)out+=`<polygon points="${metrics.map((_,i)=>pt(i,level/5).join(',')).join(' ')}" fill="${level===5?'#fff9df':'none'}" stroke="#e8e1c4" stroke-width="1"/>`;
  // Draw the rings first so the outer background does not cover inner rings.
  out=`<polygon points="${metrics.map((_,i)=>pt(i,1).join(',')).join(' ')}" fill="#fff9df"/>`+out.replace('fill="#fff9df"','fill="none"');
  metrics.forEach((m,i)=>{const [x,y]=pt(i,1);out+=`<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#e7dfc3"/>`;});
  if(metrics.every(m=>m.score!==null))out+=`<polygon points="${metrics.map((m,i)=>pt(i,m.score/100).join(',')).join(' ')}" fill="#f5ce4c55" stroke="#d1a526" stroke-width="2.3"/>`;
  else metrics.forEach((m,i)=>{const next=metrics[(i+1)%6];if(m.score!==null&&next.score!==null){const a=pt(i,m.score/100),b=pt((i+1)%6,next.score/100);out+=`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="#d1a526" stroke-width="2.3"/>`;}});
  metrics.forEach((m,i)=>{const [lx,ly]=pt(i,1.34);if(m.score!==null){const [x,y]=pt(i,m.score/100);out+=`<circle cx="${x}" cy="${y}" r="4" fill="#dfb733" stroke="white" stroke-width="2"/>`;}
    out+=`<g ${traceAttr(m.record_ids)}><text x="${lx}" y="${ly}" text-anchor="middle" fill="#35383b" font-size="12">${esc(m.label)}</text><text x="${lx}" y="${ly+23}" text-anchor="middle" fill="${m.score===null?'#b8bbc0':'#b68b12'}" font-weight="700" font-size="23">${m.grade||'—'}</text><title>${esc(m.score===null?'缺少对应记录，暂不评分':m.score+' / 100 · '+m.definition)}</title></g>`;});
  $('report-radar').innerHTML=chartShell('六维财务习惯雷达图，缺少数据的维度不连成多边形',out,'0 0 400 370');
  $('radar-unlocked').textContent=metrics.filter(m=>m.score!==null).length+' / 6 项已解锁';
  $('report-metric-definitions').innerHTML=metrics.map(m=>`<p><strong>${esc(m.label)} · ${m.score===null?'待解锁':m.score+' / 100'}</strong><span>${esc(m.definition)}</span></p>`).join('');
}
function renderDonut(report){
  const total=report.expense_fen;let offset=0;
  const rings=report.categories.map((c,i)=>{const fraction=c.amount_fen/total,part=`<circle cx="110" cy="110" r="78" fill="none" stroke="${chartColors[i%chartColors.length]}" stroke-width="25" pathLength="100" stroke-dasharray="${fraction*100} ${100-fraction*100}" stroke-dashoffset="${-offset*100}" transform="rotate(-90 110 110)" ${traceAttr(c.record_ids)}><title>${esc(c.label+' '+cash(c.amount_fen)+' · '+(fraction*100).toFixed(1)+'%')}</title></circle>`;offset+=fraction;return part;}).join('');
  $('report-donut').innerHTML=`<div class="donut-figure">${chartShell('支出分类环形图',`<circle cx="110" cy="110" r="78" fill="none" stroke="#f1f2f3" stroke-width="25"/>${rings}<text x="110" y="103" text-anchor="middle" font-size="11" fill="#999b9f">本期已导入支出</text><text x="110" y="129" text-anchor="middle" font-size="19" font-weight="600" fill="#33363a">${esc(cash(total))}</text>`,'0 0 220 220')}</div><div class="donut-legend">${report.categories.length?report.categories.map((c,i)=>`<button ${traceAttr(c.record_ids)}><i style="background:${chartColors[i%chartColors.length]}"></i><span>${esc(c.label)}<small>${(c.amount_fen/total*100).toFixed(1)}%</small></span><strong>${cash(c.amount_fen)}</strong></button>`).join(''):'<p class="muted">还没有本期支出。</p>'}</div>`;
}
function reportFact(id){return periodReport.facts.find(f=>f.id===id);}
function factButton(id){const f=reportFact(id);return f?`<button class="fact-reference" ${traceAttr(f.record_ids)} ${f.record_ids.length?'':'disabled'}>${esc(f.text)}${f.record_ids.length?' ↗':''}</button>`:'';}
function renderCoaching(){
  const r=periodReport,c=r.coaching;
  $('report-ai-label').textContent=r.generation.label+(r.cached?' · 已缓存':'');
  $('report-coach-title').textContent=c.headline;
  $('report-ai-notice').textContent=r.generation.notice||'';
  $('report-insights').innerHTML=c.insights.map(i=>`<article><span class="insight-dot"></span><div><p>${esc(i.text)}</p>${factButton(i.fact_id)}</div></article>`).join('');
  $('report-tasks').innerHTML=c.tasks.map((t,i)=>`<article class="coach-task"><span class="task-order">${i+1}</span><div><strong>${esc(t.title)}</strong><p>${esc(t.reason)}</p>${t.fact_ids.map(factButton).join('')}</div><button class="secondary small" data-report-action="${esc(t.action)}">去看看 →</button></article>`).join('');
  $('report-comic').innerHTML=c.comic.map((panel,i)=>`<article class="comic-panel"><div class="comic-art comic-art-${i}" role="img" aria-label="小狐${['发现账单','整理用途','计划下一步','鼓励自己'][i]}"></div><span class="comic-number">0${i+1}</span><div class="comic-dialogue">${esc(panel.line)}</div><div class="comic-source">${factButton(panel.fact_id)}</div></article>`).join('');
  const task=c.tasks[0];$('adventure-ai-coach').innerHTML=`<div class="game-coach-heading"><span>✦</span><strong>小狐向导</strong><small>${r.generation.mode==='ai'?'AI 行动建议':'本地行动建议'}</small></div><p>${esc(task.reason)}</p><div><button class="secondary small" data-report-action="${esc(task.action)}">${esc(task.title)} →</button><a href="#insights">查看本期图鉴 ↗</a></div>`;
  $('comic-attribution').textContent=r.generation.mode==='ai'?'本期分镜与对白由 AI 根据统计事实生成；插画为项目预制卡通素材。':'当前展示本地四格故事模板；启用 AI 后生成本期分镜与对白。';
}
function renderPeriodReport(report){
  periodReport=report;
  $('report-range').textContent=report.start+' 至 '+report.end+(report.partial?' · 截至 '+report.as_of:'');
  $('report-total').textContent=cash(report.expense_fen);$('report-net').textContent=cash(report.net_fen);$('report-records').textContent=report.record_count+' 笔';
  $('report-change').textContent=report.previous_has_records?(report.expense_fen>=report.previous_expense_fen?'＋':'')+cash(report.expense_fen-report.previous_expense_fen):'暂无可比账单';
  $('report-comparison-period').textContent='对比 '+report.previous_start+' 至 '+report.previous_end;
  $('report-trend').innerHTML=lineChart(report.trend,[{name:'支出',color:'#e7b520',value:p=>p.future?null:p.expense_fen},{name:'收入',color:'#8ebaaa',value:p=>p.future?null:p.income_fen}],'本期每日已导入收支折线图');
  renderRadar(report);renderDonut(report);
  $('report-goal-trend').innerHTML=report.goals.length?lineChart(report.trend,report.goals.slice(0,3).map((g,i)=>({name:g.title,color:chartColors[i],value:p=>g.trend.find(t=>t.date===p.date)?.balance_fen??null,ids:()=>[]})),'目标累计储蓄折线图'):'<div class="chart-empty"><span>◇</span><strong>把愿望放进计划里</strong><p>设立目标并记录存入后，这里会展示储蓄轨迹。</p><button class="secondary small" data-report-action="goal">设立目标</button></div>';
  $('report-budget-bars').innerHTML=report.budgets.length?report.budgets.map(b=>`<div class="report-budget-row"><span>${esc(b.label)}</span><div><i style="width:${b.limit_fen?Math.min(100,b.spent_fen/b.limit_fen*100):b.spent_fen?100:0}%;background:${b.spent_fen>b.limit_fen?'#e3a08c':'#f1ca45'}"></i></div><small>${cash(b.spent_fen)} / ${cash(b.limit_fen)}</small></div>`).join(''):'<p class="note">设置类别预算后，这里展示本期按日历天折算的预算进度。</p>';
  $('report-data-note').textContent=report.notice;renderCoaching();
}
async function loadPeriodReport(useModel=false){
  const anchor=$('report-anchor').value;if(!anchor)return;
  if(useModel&&!$('report-ai-consent').checked){notice('请先确认发送本期统计指标给 AI。');return;}
  const sequence=++reportSequence;
  reportBusy=true;$('report-ai-generate').disabled=true;$('report-loading').textContent=useModel?'AI 正在阅读指标、安排任务和编写故事…':'正在整理本期图表…';
  try{const report=await api('/api/reports/generate',{kind:$('report-kind').value,anchor,use_model:useModel});if(sequence===reportSequence)renderPeriodReport(report);}
  catch(error){if(sequence===reportSequence){$('report-loading').textContent=errorMessage(error);notice(errorMessage(error),true);}}
  finally{if(sequence===reportSequence){reportBusy=false;$('report-ai-generate').disabled=!state?.model_enabled;$('report-loading').textContent=periodReport?'图表随账本更新 · 点击数据可核对来源':'';}}
}
function renderReports(){
  if(!$('report-anchor').value){const last=state.transactions.map(r=>r.date).sort().at(-1)||state.adventure.today;$('report-anchor').value=last.slice(0,7);}
  $('report-ai-generate').disabled=reportBusy||!state.model_enabled;
  const signature=JSON.stringify([state.transactions,state.budgets,state.adventure]);
  if(signature!==reportSignature){reportSignature=signature;loadPeriodReport().catch(error=>notice(errorMessage(error),true));}
}
$('report-kind').addEventListener('change',()=>{const current=$('report-anchor').value;$('report-anchor').type=$('report-kind').value==='month'?'month':'date';$('report-anchor').value=$('report-kind').value==='month'?current.slice(0,7):current.length===7?current+'-01':current;loadPeriodReport();});
$('report-anchor').addEventListener('change',()=>loadPeriodReport());
$('report-current').addEventListener('click',()=>{$('report-anchor').value=$('report-kind').value==='month'?state.adventure.today.slice(0,7):state.adventure.today;loadPeriodReport();});
$('report-ai-generate').addEventListener('click',()=>loadPeriodReport(true));
function performReportAction(action){
  if(action==='goal')openAdventureGoal();if(action==='reflect')openAdventureReflection(periodReport.start.slice(0,7));
  if(action==='review'){$('review-pending').click();$('memories').scrollIntoView({behavior:'smooth'});}
  if(action==='import')$('csv-file').click();if(action==='budget')$('budget-form').scrollIntoView({behavior:'smooth'});if(action==='plan')$('smart-plans').scrollIntoView({behavior:'smooth'});
}
$('adventure-ai-coach').addEventListener('click',event=>{const action=event.target.closest('[data-report-action]')?.dataset.reportAction;if(action)performReportAction(action);});
$('insights').addEventListener('click',event=>{
  const traceButton=event.target.closest('[data-report-trace]');if(traceButton)showTrace(traceButton.dataset.reportTrace.split(',').map(Number),'成长图鉴的来源账单');
  const action=event.target.closest('[data-report-action]')?.dataset.reportAction;
  if(action)performReportAction(action);
  const download=event.target.closest('[data-download-chart]');if(download){const svg=$(download.dataset.downloadChart).querySelector('svg');if(!svg)return;const blob=new Blob([svg.outerHTML],{type:'image/svg+xml;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='LedgerLens-'+download.dataset.downloadChart+'-'+periodReport.start+'.svg';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
});
$('insights').addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&event.target.matches('svg [data-report-trace]')){event.preventDefault();event.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
