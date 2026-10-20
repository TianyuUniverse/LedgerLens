"""Package a reviewable source and deliverables bundle without data or credentials."""
import hashlib
import json
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'output'
files=[]
for folder in ('ledger','static','samples','tests','scripts','docs','assets','output','.github'):
    for file in (ROOT/folder).rglob('*'):
        if file.is_file() and not file.name.startswith('~$') and '__pycache__' not in file.parts and file.suffix not in ('.zip','.pyc') and file.name not in ('package_manifest.json','LedgerLens_Proposal.pdf','LedgerLens_Proposal.pptx','LedgerLens_Proposal_2026-10-10_v2.pdf','LedgerLens_Proposal_2026-10-10_v2.pptx','LedgerLens_Proposal_Expanded_EN_v2.pdf','LedgerLens_Proposal_Expanded_EN_v2.pptx','LedgerLens_Proposal_Expanded_EN_v3.pdf','LedgerLens_Proposal_Expanded_EN_v3.pptx'):files.append(file)
files.extend(ROOT/name for name in ('.gitignore','README.md','CONTRIBUTING.md','Start_LedgerLens.bat','app.py'))
private=ROOT/'data/provider.json'
credential=json.loads(private.read_text(encoding='utf-8')).get('api_key','') if private.exists() else ''
for file in files:
    if file.name in ('.env','provider.json') or 'data' in file.relative_to(ROOT).parts:
        raise RuntimeError('Private configuration selected for packaging.')
    if credential and credential.encode() in file.read_bytes():
        raise RuntimeError('Private credential found in a shared artifact. Packaging stopped.')
manifest={'package':'LedgerLens CSSE2026 WeChat XLSX, purpose memory and conversational savings 2026-10-20','files':[{'path':str(file.relative_to(ROOT)).replace('\\','/'),'size':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()} for file in sorted(files)],'excluded':['private user databases','data/provider.json and credentials','.git','node_modules','temporary build files']}
manifest_path=out/'package_manifest.json';manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');files.append(manifest_path)
target=out/'LedgerLens_Final_Project.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for file in files:z.write(file,'LedgerLens/'+str(file.relative_to(ROOT)).replace('\\','/'))
with zipfile.ZipFile(target) as z:
    broken=z.testzip()
    if broken:raise RuntimeError('Corrupted entry: '+broken)
    print(f'{target}\n{len(z.namelist())} files. {target.stat().st_size:,} bytes. Archive integrity passed.')
