import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {FileBlob,Presentation,PresentationFile} from '@oai/artifact-tool';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const SKILL=process.env.PRESENTATION_SKILL;
const PYTHON=process.env.ARTIFACT_PYTHON;
if(!SKILL||!PYTHON)throw Error('Set PRESENTATION_SKILL and ARTIFACT_PYTHON.');
const NAME='202464870547-陈天宇-202464871352-朱俊丞-202464871290-张瀚文';
const REV=process.env.BEAUTY_REVISION||'';
const STAGE=path.join(ROOT,'tmp/decks/ledgerlens-polished'+REV);
const OUT=path.join(ROOT,'output/精美版');
const SOURCE=path.join(ROOT,'output/submission',NAME+'.pptx');
await fs.mkdir(STAGE,{recursive:true});await fs.mkdir(OUT,{recursive:true});
const source=await PresentationFile.importPptx(await FileBlob.load(SOURCE));
if(source.slides.items.length!==10)throw Error('Expected ten source slides.');
const notes=source.slides.items.map(s=>s.speakerNotes.text);
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={bg:'#F6F7F2',ink:'#163D37',body:'#3C5550',green:'#167569',muted:'#71857D',line:'#CBD8CD',sage:'#E6EEE4',dark:'#102D2C',white:'#F1F7EC',mint:'#BEE8BF',edge:'#648A79'};

function text(s,value,x,y,w,h,size=26,bold=false,color=C.body,font='Arial'){
  const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  a.text=value;a.text.style={typeface:font,fontSize:size,bold,color,insets:0};return a;
}
function line(s,x,y,w,h=0,color=C.line,width=1){
  return s.shapes.add({geometry:'line',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:color,width}});
}
function page(title,subtitle,index,dark=false){
  const s=p.slides.add();s.background.fill=dark?C.dark:C.bg;
  text(s,'LedgerLens',72,35,500,30,19,true,dark?C.mint:C.green);
  text(s,'CSSE2026  /  PROJECT PROPOSAL',800,38,408,28,15,false,dark?C.edge:C.muted);
  text(s,title,72,87,1136,70,48,true,dark?C.white:C.ink);
  if(subtitle)text(s,subtitle,74,163,1130,45,23,false,dark?C.mint:C.muted);
  line(s,72,674,1136,0,dark?C.edge:C.line,.8);
  text(s,'AI Personal Finance Assistant',72,686,900,24,14,false,dark?C.edge:C.muted);
  text(s,String(index).padStart(2,'0'),1167,682,42,30,18,true,dark?C.mint:C.green);
  return s;
}
function table(s,values,x,y,w,h,widths,size=23){
  const t=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values});
  t.borders.assign({style:'solid',fill:C.bg,width:0});
  t.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({margins:{top:13,bottom:13,left:18,right:18},anchor:'top'});
  for(let r=0;r<values.length;r++)for(let c=0;c<values[0].length;c++){
    const cell=t.getCell(r,c);cell.fill=r===0?C.green:(r%2?C.sage:C.bg);
    cell.text.style={typeface:'Arial',fontSize:r===0?21:size,bold:r===0,color:r===0?C.white:C.body};
  }
  return t;
}
async function image(s,file,x,y,w,h,alt,fit='contain'){
  const bytes=await fs.readFile(path.join(ROOT,file));
  s.images.add({blob:bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),contentType:'image/png',position:{left:x,top:y,width:w,height:h},fit,alt});
}
function diagramNode(s,title,body,x,y,w,h){
  s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:C.dark,line:{fill:C.edge,width:1.2}});
  text(s,title,x+21,y+19,w-42,40,28,true,C.mint);
  text(s,body,x+21,y+70,w-42,h-82,22,false,C.white);
}

// Cover: bitmap artwork behind editable title and member identity text.
let s=p.slides.add();s.background.fill=C.dark;
await image(s,'assets/ledgerlens/cover-emerald-lens-v1.png',0,0,1280,720,'Conceptual glass lens and receipt artwork, generated with the built-in image tool','cover');
text(s,'CSSE2026 PROJECT PROPOSAL',74,72,740,35,22,true,C.mint);
text(s,'LedgerLens',68,185,730,135,104,true,C.white);
text(s,'AI Personal Finance\nAssistant',76,334,650,118,42,false,C.white);
text(s,'10 October 2026',77,513,500,30,20,false,C.mint);
line(s,76,566,1128,0,C.edge,1);
const members=[['Chen Tianyu','陈天宇','202464870547'],['Zhu Juncheng','朱俊丞','202464871352'],['Zhang Hanwen','张瀚文','202464871290']];
members.forEach((m,i)=>{const x=76+i*397;text(s,m[0],x,590,360,31,24,true,C.white);text(s,m[1],x,626,100,27,18,false,C.mint,'Microsoft YaHei');text(s,m[2],x+111,626,250,29,20,false,C.white);});

// Contents: two open text columns, with the original eight-part order.
s=page('Table of Contents','Eight parts, from user needs to a development plan',2);
const agenda=[['User Needs & Pain Points','Initial problem hypotheses'],['Project Positioning & Users','Students and proposed scope'],['User Research','Initial insights and plan'],['Product Workflow','The complete user task'],['System Architecture','Memory, tools and exact calculations'],['Core Innovations','Design contributions to evaluate'],['Validation & Risks','Baseline evidence and planned tests'],['Plan & Outlook','Work packages and team roles']];
agenda.forEach(([title,body],i)=>{const x=i<4?72:690,y=231+(i%4)*99;text(s,String(i+1).padStart(2,'0'),x,y,72,48,36,true,C.green);text(s,title,x+91,y+2,430,39,27,true,C.ink);text(s,body,x+93,y+44,433,38,19,false,C.muted);if(i%4<3)line(s,x+92,y+88,423);});

// Needs: preserve the source table as native, editable evidence.
s=page('User Needs & Pain Points','Initial hypotheses from user-reported examples',3);
table(s,[['Possible pain point','User need'],['University payee hides meal spending','SCUT meal payments can belong in Food.'],['Utility payments look like transfers','Roommate utilities are actual spending.'],['The same labels need repeat corrections','Confirm once and reuse a contextual memory.']],72,247,1136,303,[510,626],25);
text(s,'Payment purpose needs context.',74,586,1110,49,36,true,C.ink);
text(s,'Purpose, payee and payment channel carry different information.',75,637,1110,30,21,false,C.muted);

// Positioning: a flat feature list with a clear priority hierarchy.
s=page('Project Positioning & Users','Proposed AI extensions for students using CNY records',4);
const capabilities=[['Personal category memory','Ask once, remember the confirmed purpose.'],['Conversational queries','Compare months, exclude a purchase and recalculate.'],['Savings plan generation','Keep rent fixed and respect a minimum entertainment budget.'],['Monthly review','Review category growth, recurring bills and small purchases.']];
capabilities.forEach(([title,body],i)=>{const y=230+i*91;text(s,String(i+1).padStart(2,'0'),74,y,66,43,31,true,i<3?C.green:C.muted);text(s,title,165,y,660,38,29,true,C.ink);text(s,body,166,y+43,670,40,22,false,C.body);if(i<3)line(s,166,y+82,655);});
text(s,'CNY',935,235,272,84,68,true,C.green);
text(s,'Student income,\nspending and savings',938,330,270,82,25,false,C.ink);
text(s,'Related work',939,463,269,32,21,true,C.green);
text(s,'Actual Budget\nFirefly III',940,506,265,75,23,false,C.body);
text(s,'Priority: memory, queries and checked plans. Monthly reviews follow later.',75,612,1125,33,22,true,C.green);
text(s,'Baseline: CSV input, charts and manual savings scenarios.',75,647,1125,27,20,false,C.muted);

// Research: questions and concrete planned tasks remain explicitly prospective.
s=page('User Research','Research has not started. These questions and tasks are planned.',5);
text(s,'Questions to validate',126,230,490,38,24,true,C.green);
text(s,'Planned tasks',718,230,490,38,24,true,C.green);
const questions=['Does memory reduce\nrepeat corrections?','Can similar payments\nmean different things?','Can users verify\nanswers and plans?'];
const tasks=['Label a meal payment,\nthen import another.','Same university, different tuition.\nUtilities versus own-account transfers.','Check source records\nand savings-plan limits.'];
questions.forEach((value,i)=>{const y=298+i*107;text(s,String(i+1).padStart(2,'0'),74,y+2,46,37,25,true,C.green);text(s,value,127,y,478,78,27,true,C.ink);text(s,tasks[i],720,y+2,488,85,24,false,C.body);if(i<2)line(s,126,y+92,1082);});
text(s,'Records show spending changes. Motivation requires user clarification.',75,641,1128,31,22,false,C.muted);

// Workflow: native connected steps beside the genuine baseline screenshot.
s=page('Product Workflow','Proposed personal-memory flow',6);
const steps=[['Import a transaction','Preserve original payment labels.'],['Retrieve personal memory','Match payee, note and confirmed use.'],['Confirm unclear purpose','Ask the user to choose a category.'],['Remember and classify','Reuse an approved, consistent match.'],['Analyze and plan','Query records and check savings plans.']];
steps.forEach(([title,body],i)=>{const y=228+i*80;text(s,String(i+1).padStart(2,'0'),74,y,45,34,26,true,C.green);text(s,title,132,y,365,37,26,true,C.ink);text(s,body,133,y+39,363,45,20,false,C.body);if(i<4)line(s,94,y+37,0,36,C.line,1.5);});
text(s,'EXISTING BASELINE  /  SYNTHETIC RECORDS',545,218,663,30,18,true,C.green);
await image(s,'output/evidence/dashboard-clean.png',533,260,675,384,'The existing LedgerLens baseline with synthetic transactions. Personal memory is not implemented.');
text(s,'Users can review, change or delete their memories.',76,641,1120,32,22,false,C.muted);

// Architecture: editable engineering diagram, with contextual memory in SQLite.
s=page('System Architecture','Proposed memory and tools with exact calculations',7,true);
diagramNode(s,'Browser UI','Review and confirm\nManage memories\nChat and inspect',72,229,250,163);
diagramNode(s,'Python backend','Validate tool calls\nInteger-fen calculations\nCheck source references',420,229,360,163);
diagramNode(s,'Language model','Interpret purpose\nUse retrieved context\nExplain tool results',885,229,323,163);
diagramNode(s,'SQLite','Transactions\nPersonal memories\nAudit history',72,468,250,163);
diagramNode(s,'Memory and financial tools','Retrieve confirmed patterns and validate matches\nQuery records, compare periods and verify plans\nReturn source records and exact calculations',420,468,788,163);
line(s,322,311,98,0,C.mint,1.6);line(s,780,311,105,0,C.mint,1.6);
line(s,600,392,0,76,C.mint,1.6);line(s,322,550,98,0,C.mint,1.6);
text(s,'Validated calls and results',643,418,555,29,19,false,C.mint);
text(s,'Auto-label approved matches. Confirm uncertain cases and plan saves.',75,643,1128,30,21,false,C.mint);

// Innovations: memory as the main contribution, with supporting capabilities.
s=page('Core Innovations','Proposed design contributions to evaluate in independent tasks',8);
text(s,'01',75,236,92,43,28,true,C.green);
text(s,'Personal\ncategory memory',72,296,510,168,59,true,C.ink);
text(s,'Confirmed choices guide later\npayments with a matching context.',77,498,487,93,27,false,C.body);
const innovations=[['02','Payment purpose','Confirmed utility payments count\nas Utilities expenses.'],['03','Evidence across turns','Exclude a purchase, recalculate\nand cite the source records.'],['04','Plans that respect limits','Check a six-month CNY 6,000 goal\nwhile keeping rent fixed.']];
innovations.forEach(([n,title,body],i)=>{const y=243+i*132;text(s,n,642,y+1,50,37,23,true,C.green);text(s,title,709,y,499,40,28,true,C.ink);text(s,body,711,y+46,497,76,23,false,C.body);if(i<2)line(s,710,y+119,498);});
text(s,'First confirmation creates memory. Strong matches reuse it. Conflicts ask again.',76,639,1130,33,21,true,C.green);

// Validation: measured baseline and pending model evaluation stay separate.
s=page('Validation & Risks','Existing baseline evidence and planned AI evaluation',9);
text(s,'Recorded baseline checks',74,227,520,35,24,true,C.green);
text(s,'28',68,281,220,110,94,true,C.ink);
text(s,'18 / 20',303,294,304,99,75,true,C.ink);
text(s,'Passing domain\nand HTTP tests',76,400,215,70,23,false,C.body);
text(s,'Rules on synthetic\ndevelopment examples',310,400,287,70,22,false,C.body);
text(s,'Memory and live-model tests: pending',76,491,525,36,24,true,C.green);
text(s,'Risks to check',77,551,520,32,23,true,C.ink);
text(s,'Same payee, different purpose. Unclear transfers.\nStale memories and model-service failures.',77,593,530,64,21,false,C.body);
text(s,'Planned evaluation',651,227,557,35,24,true,C.green);
table(s,[['Measure','Check'],['Memory labels','Before / after a correction'],['False auto-labels','Conflicting-purpose cases'],['Source support','Records support each claim'],['Amounts & limits','Exact sums and limits'],['Task completion','Baseline comparison']],650,280,558,310,[215,343],21);
text(s,'Independent memory cases are planned. Scores here describe the baseline only.',651,612,557,55,20,false,C.muted);

// Work plan: keep Chen Tianyu's primary development responsibilities prominent.
s=page('Plan & Outlook','Current: a local prototype with recorded checks',10);
text(s,'Development work packages',75,226,540,38,25,true,C.green);
text(s,'Proposed team roles',715,226,493,38,25,true,C.green);
const phases=[['Requirements and data model','Confirm purpose, transaction kind and memory fields.'],['Personal classification memory','Context matching, review and correction controls.'],['Conversations and savings tools','Source queries, constraints and plan revisions.'],['Interface and monthly reviews','Memory manager and explanation screens.'],['Independent evaluation and defense','Conflicting cases, failure tests and a demonstration.']];
phases.forEach(([title,body],i)=>{const y=288+i*70;text(s,String(i+1).padStart(2,'0'),76,y,45,34,25,true,C.green);text(s,title,132,y,523,36,24,true,C.ink);text(s,body,134,y+37,521,39,19,false,C.body);});
text(s,'Chen Tianyu / Project lead',716,288,492,41,30,true,C.ink);
text(s,'Requirements and system design\nAI memory, chat and savings tools\nCore development and integration',720,342,488,102,24,false,C.body);
text(s,'Zhu Juncheng',717,469,491,37,26,true,C.green);
text(s,'Data import and database\nBackend support',720,512,488,63,22,false,C.body);
text(s,'Zhang Hanwen',717,586,491,36,26,true,C.green);
text(s,'Frontend, charts, testing and demo support',720,628,488,34,22,false,C.body);
text(s,'Stage order only. Team review and contribution records follow.',76,649,569,26,18,false,C.muted);

if(p.slides.items.length!==10)throw Error('Slide count changed.');
for(let i=0;i<10;i++){
  p.slides.items[i].speakerNotes.text=notes[i]+(i===0?'\n\nCover art: conceptual glass lens and receipts generated with the built-in image tool. Asset and full prompt: docs/LedgerLens_Visual_Design.md.':'');
  const png=await p.export({slide:p.slides.items[i],format:'png',scale:2});
  await fs.writeFile(path.join(STAGE,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(STAGE,'draft.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const finalPath=path.join(OUT,NAME+REV+'.pptx');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath,pythonExecutable:PYTHON,
  integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--validate-bullet-geometry',...[3,9].flatMap(n=>['--require-native-table-slide',String(n)])],
  explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[3,9],
  fontPolicy:{basis:'reference',families:['Arial','Microsoft YaHei'],referencePath:SOURCE,referenceSha256:createHash('sha256').update(await fs.readFile(SOURCE)).digest('hex')},
  verifyArtifactToolImport:true,receiptPath:path.join(STAGE,'validation.json')});
await fs.writeFile(path.join(STAGE,'content.json'),JSON.stringify({name:NAME,revision:REV,slides:10,notes_preserved:true,editable_tables:[3,9],main_developer:'Chen Tianyu',source:SOURCE},null,2));
console.log(JSON.stringify({pptx:result.finalPath,slides:10,layout_findings:result.presentationLayout.finding_count,stage:STAGE}));
