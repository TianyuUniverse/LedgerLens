'use strict';
let trialState=null,trialPending=null,trialBusy=false,trialPosition=0;
function renderTrial(){
  const r=trialState;if(!r)return;
  $('trial-progress').textContent='已找到 '+r.position+' / '+r.total+' 份线索';
  $('trial-avatar').style.left=(8+trialPosition*28)+'%';
  document.querySelectorAll('[data-trial-stop]').forEach(el=>el.classList.toggle('stop-reached',Number(el.dataset.trialStop)<=trialPosition));
  $('trial-label').textContent=r.source==='ai'?'AI 编写本次探险引子':'本地合成练习';
  if(trialPending){$('trial-question').innerHTML=`<div class="trial-feedback correct"><strong>这条线索找对了！</strong><p>${esc(trialPending.feedback.text)}</p><button id="trial-next">${trialPending.complete?'走向终点，领取奖励':'向前走一步 →'}</button></div>`;$('trial-next').focus({preventScroll:true});return;}
  if(r.complete){$('trial-question').innerHTML=`<div class="trial-win"><div class="trial-win-star">✦</div><h3>今天的小小探险，完成了。</h3><p>你让模糊的账单找到了实际用途。</p><strong>首次完成 ＋15 点经验</strong><p class="note">今天再进入会保留结果，不重复领奖。</p><button id="trial-done">回到我的营地</button></div>`;return;}
  const q=r.question;$('trial-question').innerHTML=`<p class="trial-story">${esc(r.story)}</p><h3>${esc(q.title)}</h3><div class="trial-clue"><strong>${esc(q.description)}</strong><p>${esc(q.note)}</p></div><p>这条线索应该放到哪里？</p><div class="trial-options">${r.choices.map((c,i)=>`<button data-trial-choice="${esc(c.id)}"><span>${i+1}</span>${esc(c.label)}</button>`).join('')}</div><p id="trial-feedback" role="status"></p>`;
}
async function openTrials(){
  $('trial-dialog').showModal();$('trial-question').textContent='正在准备今天的探险…';$('trial-error').textContent='';trialBusy=true;
  try{trialState=await api('/api/adventure/trial/start',{use_model:$('trial-use-ai').checked});trialPosition=trialState.position;trialPending=null;renderTrial();$('trial-error').textContent=trialState.generation_notice||'';}catch(error){$('trial-error').textContent=errorMessage(error);}finally{trialBusy=false;}
}
async function answerTrial(choice){
  if(trialBusy||trialPending||trialState?.complete)return;trialBusy=true;$('trial-error').textContent='';$('trial-question').querySelectorAll('button').forEach(b=>b.disabled=true);
  try{const result=await api('/api/adventure/trial/answer',{day:trialState.day,position:trialState.position,choice});
    if(result.feedback.correct){trialPending=result;renderTrial();run(refresh);}
    else{$('trial-feedback').textContent=result.feedback.text;$('trial-feedback').className='trial-hint';}
  }catch(error){$('trial-error').textContent=errorMessage(error);}finally{trialBusy=false;$('trial-question').querySelectorAll('button').forEach(b=>b.disabled=false);}
}
function advanceTrial(){if(!trialPending||trialBusy)return;trialState=trialPending;trialPending=null;trialPosition=trialState.position;renderTrial();}
$('trial-open').addEventListener('click',openTrials);$('trial-close').addEventListener('click',()=>$('trial-dialog').close());
$('trial-question').addEventListener('click',e=>{const choice=e.target.closest('[data-trial-choice]')?.dataset.trialChoice;if(choice)answerTrial(choice);if(e.target.closest('#trial-next'))advanceTrial();if(e.target.closest('#trial-done'))$('trial-dialog').close();});
$('trial-dialog').addEventListener('keydown',e=>{if(e.target.matches('input,textarea,select'))return;if(e.key==='ArrowRight'&&trialPending){e.preventDefault();advanceTrial();}if(/^[123]$/.test(e.key)&&!trialPending){const c=trialState?.choices[Number(e.key)-1];if(c){e.preventDefault();answerTrial(c.id);}}});
const originalRenderAdventure=renderAdventure;
renderAdventure=function(){originalRenderAdventure();$('trial-use-ai').disabled=!state.model_enabled;if(!$('trial-use-ai').dataset.initialized){$('trial-use-ai').checked=Boolean(state.model_enabled);$('trial-use-ai').dataset.initialized='true';}};
