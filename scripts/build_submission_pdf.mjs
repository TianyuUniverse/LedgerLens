import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const SKILL=process.env.PRESENTATION_SKILL;
const PYTHON=process.env.ARTIFACT_PYTHON;
if(!SKILL||!PYTHON)throw Error('Set PRESENTATION_SKILL and ARTIFACT_PYTHON.');
const NAME='202464870547-陈天宇-202464871352-朱俊丞-202464871290-张瀚文';
const stage=path.join(ROOT,'tmp/decks/submission-20261015');
const source=path.join(ROOT,'output/LedgerLens_Proposal_AI_Memory_EN_.pptx');
const final=path.join(ROOT,'output/submission',NAME+'.pptx');
await fs.mkdir(stage,{recursive:true});
await fs.mkdir(path.dirname(final),{recursive:true});
const p=await PresentationFile.importPptx(await FileBlob.load(source));
if(p.slides.items.length!==10)throw Error('Expected ten source slides.');
const last=p.slides.items[9];
async function exact(text){
  const records=(await p.inspect({kind:'textbox',search:text,maxChars:6000})).records;
  const matches=records.filter(r=>r.slideIndex===9&&r.text===text);
  if(matches.length!==1)throw Error('Ambiguous text anchor: '+text);
  return p.resolve(matches[0].id);
}
async function update(old,text,top,height,size,bold,color){
  const shape=await exact(old);
  shape.text=text;
  shape.position={left:790,top,width:420,height};
  shape.text.style={typeface:'Arial',fontSize:size,bold,color,insets:0};
}
await update('Chen Tianyu','Chen Tianyu - Project lead',284,38,27,true,'#167569');
await update('Requirements and savings scenarios',
  'Requirements and system design\nAI memory, chat and savings tools\nCore development and integration',327,86,23,false,'#32494c');
await update('Zhu Juncheng','Zhu Juncheng',432,34,27,true,'#167569');
await update('Backend and data','Data import and database\nBackend support',473,57,23,false,'#32494c');
await update('Zhang Hanwen','Zhang Hanwen',546,34,27,true,'#167569');
await update('Interface and evaluation','Frontend and charts\nTesting and demo support',587,57,23,false,'#32494c');
const speech='We will first build memory, then add chat tools and savings plans. Next, we will test the full process. Chen Tianyu will lead the project and do most of the core work, including AI features and system integration. Zhu Juncheng will support data and backend work. Zhang Hanwen will support the interface, tests and demo. These are planned roles. Codex helped build the first version. We will review it together as a team. Thank you.';
last.speakerNotes.text='Suggested time: 4:21-5:00 (39 seconds).\n\n'+speech+'\n\nSources: Team identities and revised responsibilities supplied by the user on 15 October 2026. Expanded AI capabilities remain planned. Actual completed contributions require evidence.';
for(let i=0;i<10;i++){
  const png=await p.export({slide:p.slides.items[i],format:'png',scale:2});
  await fs.writeFile(path.join(stage,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(stage,'draft.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath:final,pythonExecutable:PYTHON,
  integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--validate-bullet-geometry',...[3,4,8,9].flatMap(n=>['--require-native-table-slide',String(n)])],
  explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[3,4,8,9],
  fontPolicy:{basis:'reference',families:['Arial','Microsoft YaHei'],referencePath:source,referenceSha256:createHash('sha256').update(await fs.readFile(source)).digest('hex')},
  verifyArtifactToolImport:true,receiptPath:path.join(stage,'validation.json')});
await fs.writeFile(path.join(stage,'submission.json'),JSON.stringify({name:NAME,slides:10,pptx:final,main_developer:'Chen Tianyu',recipient:'hytwbf09@gmail.com',email_sent:false},null,2));
console.log(JSON.stringify({pptx:result.finalPath,slides:10,layout_findings:result.presentationLayout.finding_count}));
