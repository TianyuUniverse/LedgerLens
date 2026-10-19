import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const SKILL=process.env.PRESENTATION_SKILL;
const PYTHON=process.env.ARTIFACT_PYTHON;
if(!SKILL||!PYTHON)throw Error('PRESENTATION_SKILL and ARTIFACT_PYTHON must point to the bundled runtime.');
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const content=JSON.parse(await fs.readFile(path.join(ROOT,'docs/PROPOSAL_AI_CONTENT.json'),'utf8'));
// Rebuild the historical proposal using its archived 28-test baseline.
const evidence=JSON.parse(await fs.readFile(path.join(ROOT,'output/evidence/baseline-20261009/verification.json'),'utf8'));
if(evidence.test_count!==28||evidence.test_failures!==0||evidence.test_errors!==0||evidence.baseline_evaluation.correct!==18||evidence.baseline_evaluation.total!==20)throw Error('Evidence changed. Review the presentation claims before building.');
const NAME=process.env.PROPOSAL_EXPANDED_OUTPUT||'LedgerLens_Proposal_AI_Memory_EN';
const NOTES_ONLY=process.env.PROPOSAL_NOTES_ONLY==='1';
const stage=path.join(ROOT,'tmp/decks',NAME);
await fs.mkdir(stage,{recursive:true});
const C={ink:'#183d38',body:'#32494c',green:'#167569',muted:'#6b8183',bg:'#f5f7f2',light:'#e9f0e3',line:'#c5d6c7',white:'#ffffff'};
const reference=path.join(ROOT,NOTES_ONLY?'output/LedgerLens_Proposal_AI_Memory_EN.pptx':'output/LedgerLens_Proposal_AI_EN.pptx');
const p=await PresentationFile.importPptx(await FileBlob.load(reference));
if(p.slides.items.length!==10)throw Error('Expected the existing ten-slide proposal as the reference.');
// Reuse the original cover, contents, masters and theme. Replace the eight body slides.
if(!NOTES_ONLY)p.slides.keep([0,1]);
const words=s=>s.match(/\b[\w]+(?:['-][\w]+)*\b/g)||[];
const counts=content.slides.map(s=>words(s.speech).length);
const total=counts.reduce((a,b)=>a+b,0);
if(total<550||total>650)throw Error(`Script has ${total} words. Required range: 550-650.`);
const rawSeconds=counts.map(n=>n/total*300);
const times=rawSeconds.map(Math.floor);
let remaining=300-times.reduce((a,b)=>a+b,0);
const remainders=rawSeconds.map((v,i)=>({i,f:v-Math.floor(v)})).sort((a,b)=>b.f-a.f);
for(let i=0;i<remaining;i++)times[remainders[i].i]++;

function txt(s,value,x,y,w,h,size=28,bold=false,color=C.body,font='Arial'){
  const t=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  t.text=value;t.text.style={typeface:font,fontSize:size,bold,color,insets:0};return t;
}
function slide(index){
  const s=p.slides.add();s.background.fill=C.bg;
  txt(s,content.slides[index].title,70,43,1140,90,42,true,C.ink);
  txt(s,String(index+1).padStart(2,'0'),1172,672,40,25,17,false,C.muted);
  return s;
}
function table(s,values,x,y,w,h,widths,font=25){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
  t.borders.assign({style:'solid',fill:C.line,width:.7});
  const all=t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length});
  all.assign({margins:{top:7,bottom:7,left:12,right:12},anchor:'top'});
  for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
    const cell=t.getCell(r,c);cell.fill=r===0?C.green:(r%2?C.light:C.white);
    cell.text.style={typeface:'Arial',fontSize:font,bold:r===0,color:r===0?C.white:C.body};
  }
  return t;
}
function box(s,title,body,x,y,w,h){
  s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:C.light,line:{fill:C.line,width:1}});
  txt(s,title,x+18,y+14,w-36,42,29,true,C.ink);
  txt(s,body,x+18,y+65,w-36,h-76,25,false,C.body);
}
function connection(s,x,y,w,h=0){s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:C.green,width:2}});}
async function addScreenshot(s){
  const bytes=await fs.readFile(path.join(ROOT,'output/evidence/dashboard-clean.png'));
  s.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',fit:'contain',alt:'Initial LedgerLens rules-baseline prototype with synthetic transactions',position:{left:550,top:190,width:660,height:459}});
}

if(!NOTES_ONLY){
let s;

s=slide(2);
txt(s,'User-reported examples to validate with students',70,153,1140,50,29,true,C.green);
table(s,[['Possible pain point','User need'],['University payee hides meal spending','SCUT meal payments can belong in Food.'],['Utility payments look like transfers','Roommate utilities are actual spending.'],['The same labels need repeat corrections','Confirm once and reuse a contextual memory.']],70,239,1140,337,[480,660],26);
txt(s,'Purpose, payee and payment channel are different information.',70,612,1120,45,25,false,C.muted);

s=slide(3);
txt(s,'Proposed AI extensions for students using CNY records',70,153,1140,55,29,true,C.green);
txt(s,'Current baseline: CSV input, charts and manual savings scenarios',70,207,1130,48,24,false,C.muted);
table(s,[['Proposed capability','Example task'],['Personal category memory','Ask once, remember the confirmed purpose.'],['Conversational queries','Compare months, exclude a purchase, recalculate.'],['Savings plan generation','Keep rent fixed, entertainment at least CNY 200/month.'],['Monthly review','Review growth, recurring bills and small purchases.']],70,270,1140,304,[420,720],24);
txt(s,'Priority: classification memory, queries and checked savings plans',70,594,1140,40,25,true,C.ink);
txt(s,'Related work: Actual Budget and Firefly III',70,643,1140,35,23,false,C.muted);

s=slide(4);
txt(s,'Research has not started. These tasks and questions are planned.',70,154,1140,72,28,true,C.green);
txt(s,'Questions to validate',70,268,530,42,28,true,C.ink);
txt(s,'Planned method',680,268,530,42,28,true,C.ink);
const researchLeft=['Does memory reduce repeat corrections?','Can similar payments mean different things?','Can users verify answers and plans?'];
const researchRight=['Label a meal payment, then import another.','Same university, different tuition payment.','Roommate utilities versus own-account transfers.'];
researchLeft.forEach((v,i)=>txt(s,v,70,336+i*91,520,75,27));
researchRight.forEach((v,i)=>txt(s,v,680,336+i*91,530,75,27));
txt(s,'Records show spending changes. Motivation requires user clarification.',70,632,1140,40,24,false,C.muted);

s=slide(5);
txt(s,'Proposed workflow',70,150,430,42,23,true,C.green);
txt(s,'Existing baseline with synthetic records',550,150,660,42,23,false,C.muted);
const steps=[['1  Import a transaction','Preserve original payment labels.'],['2  Retrieve personal memory','Match payee, note and confirmed use.'],['3  Confirm unclear purpose','Ask the user to choose a category.'],['4  Remember and classify','Reuse a strong, consistent match.'],['5  Analyze and plan','Query records and verify savings plans.']];
steps.forEach(([title,body],i)=>{const y=207+i*87;s.shapes.add({geometry:'rect',position:{left:70,top:y,width:430,height:73},fill:C.light,line:{fill:C.line,width:1}});txt(s,title,87,y+8,396,32,26,true,C.ink);txt(s,body,87,y+43,396,28,21);if(i<4)connection(s,285,y+73,0,14);});
await addScreenshot(s);

s=slide(6);
txt(s,'Proposed personal memory and tools with exact calculations',70,154,1140,46,28,true,C.green);
box(s,'Browser UI','Review and confirm\nManage memories\nChat and inspect',70,210,260,178);
box(s,'Python backend','Check matches and tools\nInteger-fen arithmetic\nCheck references',410,210,350,178);
box(s,'Language model','Interpret purpose\nUse retrieved context\nExplain tool results',840,210,370,178);
connection(s,330,297,80);connection(s,760,297,80);
box(s,'SQLite','Transactions\nPersonal memories\nAudit history',70,455,260,176);
box(s,'Memory and financial tools','Retrieve confirmed patterns and validate matches\nQuery records, compare periods and verify plans\nReturn sources and calculations',410,455,800,176);
connection(s,585,388,0,67);connection(s,330,543,80);
txt(s,'Validated calls and exact results',608,414,580,35,22,false,C.muted);
txt(s,'Planned: auto-label approved matches. Confirm uncertain cases and plan saves.',70,654,1110,36,23,true,C.green);

s=slide(7);
txt(s,'Proposed contributions to evaluate in independent tasks',70,155,1140,47,28,true,C.green);
table(s,[['Design contribution','Concrete behavior'],['Personal classification memory','Confirm purpose once, reuse a matching context.'],['Payment purpose','Confirmed utility payments count as Utilities expenses.'],['Evidence across turns','Exclude a purchase, recompute and cite source records.'],['Plans that respect limits','Check a six-month CNY 6,000 goal with fixed rent.']],70,220,1140,398,[420,720],25);
txt(s,'First confirmation creates memory. Strong matches reuse it. Conflicts ask again.',70,647,1140,35,24,true,C.green);

s=slide(8);
txt(s,'Existing baseline evidence',70,155,520,42,28,true,C.green);
txt(s,'28',70,226,520,76,64,true,C.ink);
txt(s,'Passing domain and HTTP checks',70,305,520,45,25);
txt(s,'18 / 20',70,372,520,72,56,true,C.ink);
txt(s,'Rules classification on synthetic\ndevelopment examples',70,453,520,76,25);
txt(s,'Memory and live-model tests: pending',70,563,520,45,25,true,C.green);
txt(s,'Planned AI evaluation',650,155,560,42,28,true,C.green);
table(s,[['Measure','Check'],['Memory labels','Before / after a correction'],['False auto-labels','Conflicting-purpose cases'],['Source support','Records support each claim'],['Amounts & limits','Exact sums and limits'],['Task completion','Baseline comparison']],650,223,560,330,[220,340],22);
txt(s,'Risk cases: tuition to the same payee, unclear transfers, stale memories and model failure.',650,574,560,78,23,false,C.muted);
txt(s,'Independent memory cases are planned. Existing scores cover the baseline only.',70,654,1080,35,23,false,C.muted);

s=slide(9);
txt(s,'Current: a local prototype and recorded checks',70,152,1140,45,28,true,C.green);
txt(s,'Development work packages',70,233,650,42,28,true,C.ink);
const phases=[['01  Requirements and data model','Confirm purposes, kinds and memory schemas'],['02  Personal classification memory','Context matching, review and correction controls'],['03  Conversations and savings tools','Source queries, constraints and plan revisions'],['04  Interface and monthly reviews','Memory manager and explanation screens'],['05  Independent evaluation and defense','Conflicting cases, failure tests and demo']];
phases.forEach(([title,body],i)=>{txt(s,title,70,286+i*70,650,33,26,true,C.ink);txt(s,body,70,322+i*70,650,33,23);});
txt(s,'Proposed team roles',790,233,420,42,28,true,C.ink);
content.members.forEach((m,i)=>{txt(s,m.english,790,303+i*94,420,34,27,true,C.green);txt(s,m.role,790,344+i*94,420,51,24);});
txt(s,'Stage order only. Team review and contribution records are required.',70,655,1100,36,23,false,C.muted);
}

let cumulative=0;
const timing=[];
const stamp=n=>`${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;
for(let i=0;i<content.slides.length;i++){
  const part=content.slides[i];
  const range=`${stamp(cumulative)}-${stamp(cumulative+times[i])}`;
  p.slides.items[i].speakerNotes.text=`Suggested time: ${range} (${times[i]} seconds).\n\n${part.speech}\n\nSources: ${part.sources}`;
  timing.push({slide:i+1,title:part.title,words:counts[i],seconds:times[i],range});cumulative+=times[i];
  const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1.5});
  await fs.writeFile(path.join(stage,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const candidate=path.join(stage,'draft.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
const referenceSha256=createHash('sha256').update(await fs.readFile(reference)).digest('hex');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:path.join(ROOT,'output',NAME+'.pptx'),pythonExecutable:PYTHON,
  integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--validate-bullet-geometry',...[3,4,8,9].flatMap(n=>['--require-native-table-slide',String(n)])],
  explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[3,4,8,9],fontPolicy:{basis:'reference',families:['Arial','Microsoft YaHei'],referencePath:reference,referenceSha256},verifyArtifactToolImport:true,
  receiptPath:path.join(stage,'validation.json')});
let markdown=`# LedgerLens - Simple English Proposal Speaking Notes\n\nUse **LedgerLens_Proposal_AI_Memory_EN.pptx** for the ten-slide opening presentation. One speaker presents the full script.\n\nMain script: **${total} words**, about five minutes at ${Math.round(total/5)} words per minute. The suggested times help with practice. Student IDs are on the cover and do not need to be read aloud.\n\nThe main script uses short sentences and common words. The school meal, roommate bill, large purchase and savings goal examples are in the Q&A. They are not part of the five-minute main script.\n\nMemory and the new AI features are **plans**. The picture and test scores show our basic version.\n\n## Timing guide\n\n| Slide | Title | Suggested time | Words |\n| --- | --- | --- | --- |\n`;
timing.forEach(t=>markdown+=`| ${t.slide} | ${t.title} | ${t.range} | ${t.words} |\n`);
for(let i=0;i<content.slides.length;i++){markdown+=`\n## Slide ${i+1} - ${content.slides[i].title}\n\nSuggested time: ${timing[i].range} (${times[i]} seconds).\n\n${content.slides[i].speech}\n`;}
markdown+='\n## Short English Q&A\n';
content.qa.forEach(q=>markdown+=`\n**${q.question}**\n\n${q.answer}\n`);
markdown+='\n## Practice notes\n\n- The ten slide paragraphs are the main script. Read the Q&A only if asked.\n- Pause briefly before moving to the next slide.\n- Say that the AI features and student research are still plans.\n- The 18/20 score is for rules on made-up examples. We have not tested a real AI model yet.\n- The team roles are planned roles.\n- A payment name alone does not tell us what the money was used for.\n- The system should ask again when a new payment does not clearly match a memory.\n- The picture shows the basic version. It does not show the planned memory feature.\n\n## Architecture reference\n\nThe planned AI tool use follows the [official OpenAI Function calling guide](https://developers.openai.com/api/docs/guides/function-calling). The app runs the tools and gives the results to AI. The memory design, money checks and user approval rules are our project choices. This reference is not part of the spoken script.\n';
const rehearsalDeck=NOTES_ONLY?'LedgerLens_Proposal_AI_Memory_EN_Simple.pptx':NAME+'.pptx';
markdown=markdown.replace('**LedgerLens_Proposal_AI_Memory_EN.pptx**',`**${rehearsalDeck}**`);
if(NOTES_ONLY)markdown=markdown.replace('One speaker presents the full script.','One speaker presents the full script. The simple script is in its speaker notes. The same slide visuals are in **LedgerLens_Proposal_AI_Memory_EN.pdf**.');
await fs.writeFile(path.join(ROOT,'docs/PROPOSAL_SPEAKING_NOTES_EN.md'),markdown,'utf8');
await fs.writeFile(path.join(stage,'content_checks.json'),JSON.stringify({total_slides:10,spoken_words:total,total_seconds:300,timing,source_sha256:createHash('sha256').update(JSON.stringify(content)).digest('hex')},null,2));
console.log(JSON.stringify({file:result.finalPath,slides:10,script_words:total,timing_seconds:300,package_check:result.packageIntegrity.status,layout_findings:result.presentationLayout.finding_count}));
