import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const SKILL=process.env.PRESENTATION_SKILL;
const PYTHON=process.env.ARTIFACT_PYTHON;
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const FONT='Arial';
const color={ink:'#183d38',body:'#32494c',green:'#167569',muted:'#6b8183',bg:'#f5f7f2',light:'#e9f0e3',line:'#c5d6c7'};
// These are historical baseline decks. Current code evidence lives one directory above.
const evidence=JSON.parse(await fs.readFile(path.join(ROOT,'output/evidence/baseline-20261009/verification.json'),'utf8'));
await fs.mkdir(path.join(ROOT,'tmp/decks'),{recursive:true});

function text(slide,value,x,y,w,h,size=28,bold=false,fill=color.body,font=FONT){
  const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;shape.text.style={typeface:font,fontSize:size,bold,color:fill,insets:0};return shape;
}
function base(p,title,number){
  const s=p.slides.add();s.background.fill=color.bg;
  text(s,title,70,49,1140,75,42,true,color.ink);
  text(s,String(number).padStart(2,'0'),1170,668,50,28,17,false,color.muted);
  return s;
}
function lines(s,items,x=70,y=180,w=1100,size=29,gap=104){
  items.forEach((item,i)=>text(s,item,x,y+i*gap,w,90,size,false));
}
function table(s,rows,x,y,w,h,widths){
  const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values:rows});
  t.borders.assign({fill:color.line,width:.6,style:'solid'});
  for(let r=0;r<rows.length;r++)for(let c=0;c<rows[0].length;c++){
    const cell=t.getCell(r,c);cell.fill=r===0?color.green:(r%2?color.light:'#ffffff');
    cell.text.style={typeface:FONT,fontSize:24,bold:r===0,color:r===0?'#ffffff':color.body};
  }
  return t;
}
function node(s,title,body,x,y,w,h){
  s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:color.light,line:{fill:color.line,width:1}});
  if(h<100){
    text(s,title,x+12,y+10,w-24,30,22,true,color.ink);
    text(s,body,x+12,y+49,w-24,h-54,17,false,color.body);
  }else{
    text(s,title,x+18,y+15,w-36,40,26,true,color.ink);
    text(s,body,x+18,y+62,w-36,h-72,23,false,color.body);
  }
}
function line(s,x,y,w,h=0){s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color.green,width:2}});}
async function image(s,file,x,y,w,h){const data=await fs.readFile(file);s.images.add({blob:data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength),contentType:'image/png',alt:'Actual LedgerLens browser screenshot',fit:'contain',position:{left:x,top:y,width:w,height:h}});}
function note(s,copy,source='Local implementation and output/evidence/verification.json'){s.speakerNotes.text=copy+'\nSources: '+source;}
async function save(p,name,tables=[],fonts=[FONT]){
  const stage=path.join(ROOT,'tmp/decks',name);await fs.mkdir(stage,{recursive:true});
  for(let i=0;i<p.slides.items.length;i++){
    const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});
    await fs.writeFile(path.join(stage,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
  }
  const draft=path.join(stage,'draft.pptx');await (await PresentationFile.exportPptx(p)).save(draft);
  const final=path.join(ROOT,'output',name+'.pptx');
  // The finalizer preserves existing outputs. Each build uses a fresh validated candidate.
  const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:draft,finalPath:final,pythonExecutable:PYTHON,
    integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--validate-bullet-geometry',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],
    explicitTotalSlideCount:p.slides.items.length,requiredNativeTableOwnerSlides:tables,fontPolicy:{basis:'design',families:fonts},verifyArtifactToolImport:true,
    receiptPath:path.join(stage,'validation.json')});
  // Bundled native PDF export currently lacks #standard-fonts/Helvetica.
  // Preserve editable PPTX and assemble the reviewed slide renders as PDF.
  execFileSync(PYTHON,[path.join(ROOT,'scripts/slides_pdf.py'),name,stage],{stdio:'inherit'});
  console.log(name, p.slides.items.length, 'slides', JSON.stringify(result));
}

const p=Presentation.create({slideSize:{width:1280,height:720}});
let s=p.slides.add();s.background.fill=color.ink;
text(s,'LedgerLens',80,170,1110,105,76,true,'#edf6e8');
text(s,'AI Personal Finance Assistant',84,293,1100,65,37,false,'#d7e9cf');
text(s,'CSSE2026 Final Project',86,440,900,45,25,false,'#bdd5c4');
text(s,'Initial AI-assisted package for team review',86,487,1100,45,23,false,'#bdd5c4');
note(s,'Our system helps a student inspect spending records and compare a savings goal. Explain that team identity and actual contributions still need to be recorded. This initial package used substantial Codex assistance.','Supplied Project Kickoff and Lecture 01. docs/AI_USAGE.md');

s=base(p,'User need and project scope',2);
text(s,'One student. One CNY ledger. One traceable savings workflow.',70,155,1110,90,31,true,color.green);
lines(s,['Import records and correct their categories.','Compare a savings goal with category reductions.','Inspect the records behind answers and budget alerts.'],70,285,1080,29,100);
note(s,'The target need is a project assumption based on the course finance brief. We performed no user interviews. Actual Budget and Firefly III informed the related-work comparison. This prototype narrows the workflow and incorporates no source code from those projects.','Project_Kickoff.pdf pages 27-30. https://github.com/actualbudget/actual . https://github.com/firefly-iii/firefly-iii');

s=base(p,'Working system',3);
await image(s,path.join(ROOT,'output/evidence/dashboard-clean.png'),70,150,825,525);
text(s,'Browser UI\n\nPython backend\n\nSQLite data\n\nNo key needed\nfor the baseline',925,190,285,440,27,true,color.green);
note(s,'Show the real browser screenshot. The sample contains 30 synthetic records. The screenshot does not establish all failure behavior, so refer to the tests later.');

s=base(p,'Architecture and model boundary',4);
node(s,'Browser','Charts, source records,\nforms and review',70,185,320,190);
node(s,'Python service','Validation, exact money,\nHTTP and model seam',480,185,320,190);
node(s,'SQLite','Transactions, budgets,\nsettings and audit',890,185,320,190);
line(s,390,280,90);line(s,800,280,90);
node(s,'Optional model provider','Merchant description in. Validated category proposal out.',480,455,610,142);
line(s,640,375,0,80);
note(s,'Follow one import from UI to HTTP boundary to service to SQLite. The model provider is optional and has no database access. Model response validation produces a proposal. The user applies it through the ordinary edit path.');

s=base(p,'Contracts and state guarantees',5);
table(s,[['Operation','Success','Failure guarantee'],['Import','Validate and save once','No partial batch'],['Edit','Correct + audit','No invalid change'],['Suggest','Return a proposal','No automatic write'],['Plan','Save exact result','Preserve valid inputs']],70,174,1140,375,[230,460,450]);
text(s,'Transfers never count as income or spending. Amounts use exact integer fen.',70,588,1120,65,26,true,color.green);
note(s,'The domain contains Transactions, Budgets, SavingsScenarios and AuditEvents. The fingerprint identifies duplicate transactions. Explain what is returned and what remains unchanged on rejection.','Lecture 02 domain/SSD/contract method and local test suite.');

s=base(p,'Six-month savings scenario',6);
text(s,'RMB 6,240',70,180,540,100,68,true,color.green);
text(s,'Projected savings against a RMB 6,000 target',75,298,1100,50,28,false);
table(s,[['Calculation','RMB per month'],['Baseline savings','600'],['Shopping reduction: 650 x 30%','195'],['Entertainment reduction: 320 x 50%','160'],['Food reduction: 850 x 10%','85'],['Scenario monthly savings','1,040']],70,385,1140,245,[770,370]);
note(s,'Imported income is 12,000 and spending 10,200 over three months. Baseline capacity is 600 per month. Hypothetical cuts total 440. Six months at 1,040 gives 6,240. Assumes complete records and stable future income and spending. Per-category reductions round to fen.');

s=base(p,'Changing one assumption',7);
text(s,'6 months',70,177,510,65,43,true,color.green);text(s,'4 months',670,177,510,65,43,true,color.green);
text(s,'RMB 6,240\nProjection',70,289,510,135,45,true,color.ink);text(s,'RMB 4,160\nProjection',670,289,510,135,45,true,color.ink);
text(s,'Goal reached in the scenario',70,460,500,88,27,false);text(s,'RMB 1,840 remaining gap',670,460,510,88,27,false);
text(s,'Only the horizon changes. Source records and reduction assumptions stay the same.',70,585,1100,65,26,false,color.muted);
note(s,'In the live demo, change the months input from six to four and save. This is an explicit comparison, not a prediction or a transfer of funds.');

s=base(p,'Failure demonstration',8);
text(s,'A valid row followed by an impossible date',70,172,1110,85,33,true,color.green);
text(s,'2026-09-01, valid record, RMB 10.00\n2026-09-32, invalid date, NaN',70,283,1110,126,31,false);
text(s,'The entire import is rejected. No rows are saved.',70,463,1110,80,33,true,color.ink);
text(s,'Repeat import: 30 duplicates skipped. Model failure: labeled rules fallback.',70,589,1110,65,26,false,color.muted);
note(s,'Show samples/invalid.csv in the app and the unchanged 30-record count. The rollback test additionally injects an audit persistence failure, and the concurrent-import test checks exactly 30 saved records.');

s=base(p,'Verification results',9);
table(s,[['Check','Measured result','Scope'],['Domain / HTTP',`${evidence.test_count} passed`,'Isolated databases'],['Rules classification','18 / 20','Synthetic descriptions'],['Grounded Q&A','9 / 9','Authored tool cases'],['Browser workflow','Passed','Edge + mobile layout'],['Live model quality','Not evaluated','No configured provider']],70,179,1140,390,[360,300,480]);
text(s,'Small authored datasets establish these cases. Real-world performance remains unmeasured.',70,597,1120,70,24,false,color.muted);
note(s,'The merchant examples are rules-informed convenience cases, not an independent held-out set. Nine Q&A cases include six supported queries and three refusals. Do not describe these as live LLM accuracy. Browser tests found no uncaught page errors.');

s=base(p,'AI supervision and disclosure',10);
lines(s,['Codex drafted the initial system and materials.','Optional runtime AI proposes a category for human review.','Code validates proposals and calculates all money.','Live-model quality and actual student review remain pending.'],70,172,1120,30,103);
note(s,'Disclose the tool, tasks, agent fixes, remaining risks and actual human changes. The user chose the topic and authorized the implementation. Team contributions cannot be invented. Explain the separate rules baseline and optional model mode.','docs/AI_USAGE.md. Supplied Lecture 01 AI responsibility. Official JSON mode: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses');

s=base(p,'Limitations and next work',11);
table(s,[['Current boundary','Next work'],['Single-user CNY CSV','Richer formats, refunds and authentication'],['Three-month average','Completeness checks and richer cash-flow assumptions'],['Keyword baseline / tool Q&A','Independent held-out model comparison'],['Local teaching server','Production hosting and operational backups']],70,180,1140,345,[550,590]);
text(s,'Team completion: real names, actual contributions, code review and defense rehearsal.',70,592,1110,70,26,true,color.green);
note(s,'State limits in terms of their consequences. No bank connection, user study or multiuser security evaluation. All sample data is synthetic. Actual team work needs to be documented before submission.');

s=base(p,'System demonstration',12);
lines(s,['Import and trace a category to its source records.','Compare six-month and four-month savings scenarios.','Show a budget overrun and an invalid CSV rejection.'],70,185,1090,32,113);
text(s,'python app.py    /    http://127.0.0.1:8765',70,571,1110,60,30,true,color.green);
note(s,'Play the 2-minute-plus captioned recording or run the live demo. Rehearse the source IDs, integer-fen arithmetic, atomic import and proposal review explanations. English demo script is in docs/DEFENSE_NOTES.md.');
if(!process.argv.includes('--proposal-only'))await save(p,'LedgerLens_Final_Slides',[5,6,9,11]);

const proposal=Presentation.create({slideSize:{width:1280,height:720}});
s=proposal.slides.add();s.background.fill=color.bg;
text(s,'LedgerLens: AI Personal Finance Assistant',70,37,1140,65,42,true,color.ink);
text(s,'陈天宇 202464870547     朱俊丞 202464871352     张瀚文 202464871290',70,111,1140,34,20,false,color.muted,'Microsoft YaHei');
text(s,'Problem & users',70,170,550,40,28,true,color.green);
text(s,'Students importing CNY records need\ntraceable spending summaries and\nan editable savings plan.',70,217,550,100,24,false);
text(s,'Core scope & related work',70,343,550,40,28,true,color.green);
text(s,'1  Import, de-duplicate and correct records.\n2  Compare goals with category reductions.\n3  Inspect answers and budget alerts.\n\nReference: Actual Budget and Firefly III.\nFocus: source links and reviewed AI proposals.',70,392,550,214,23,false);
text(s,'Architecture & AI role',680,170,530,40,28,true,color.green);
node(s,'Browser','Input + review',680,222,158,85);
node(s,'Python','Rules + AI seam',861,222,166,85);
node(s,'SQLite','Records + audit',1050,222,160,85);
line(s,838,265,23);line(s,1027,265,23);
text(s,'We will combine rules with reviewed LLM\ncategory proposals. Code calculates money.\nUsers approve a proposal before saving.',680,332,530,104,23,false);
text(s,'Verification & work plan',680,453,530,40,28,true,color.green);
text(s,'Check duplicates, invalid CSV, rollback,\nsource IDs and labeled AI outputs.\n\nNext: team review and model evaluation,\nthen integration, pre-demo and defense.',680,500,530,140,23,false);
text(s,'Risks: incomplete data and wrong labels. Controls: assumptions, source links and human review.',70,643,1140,27,19,true,color.ink);
text(s,'Proposed roles: Chen - requirements/scenarios. Zhu - backend/data. Zhang - UI/evaluation.',70,682,1140,26,18,false,color.muted);
note(s,'Proposal for 10 October 2026. Team: Chen Tianyu (陈天宇), 202464870547; Zhu Juncheng (朱俊丞), 202464871352; Zhang Hanwen (张瀚文), 202464871290. These roles are proposed, not confirmed completed work. Target users are students with CNY CSV records. The three user stories cover import/correction, goal comparison and inspectable answers/alerts. The complete workflow is import -> review -> analyze -> plan -> inspect. Data will begin with labeled synthetic records. An initial Codex-assisted local prototype already exists, but team review and live-model evaluation remain future work. Keep the AI assistance disclosure. Do not claim live-model accuracy. Compare with Actual Budget and Firefly III as related work. Planned sequence: requirements/data review, model-boundary evaluation, integration and failure checks, then pre-demo and defense. See docs/PROPOSAL_SPEAKING_NOTES.md for the English speaking script.','Supplied Project_Kickoff.pdf proposal requirements. https://github.com/actualbudget/actual . https://github.com/firefly-iii/firefly-iii');
await save(proposal,process.env.PROPOSAL_OUTPUT_NAME||'LedgerLens_Proposal_2026-10-10',[],[FONT,'Microsoft YaHei']);
