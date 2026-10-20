import json,sys,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from ledger.service import Ledger
from ledger.provider import load_local_config
load_local_config(root)
with tempfile.TemporaryDirectory() as directory:
    ledger=Ledger(Path(directory)/'test.sqlite',clock=lambda:datetime(2026,10,20,12,tzinfo=timezone(timedelta(hours=8))))
    ledger.import_csv((root/'samples/memory_seed.csv').read_text(encoding='utf-8'));record=next(r for r in ledger.transactions() if r['note']=='伙食费')
    before=ledger.transactions();xp=ledger.adventure.state()['xp']
    result=ledger.setup_chat.chat({'mode':'purpose','message':'这是食堂伙食费，以后相同用途备注自动归为餐饮','context':{'record_id':record['id']},'use_model':True})
    trial=ledger.trials.start({'use_model':True})
    evidence={'checked_at':datetime.now(timezone.utc).isoformat(),'synthetic_only':True,'calls':2,'purpose_source':result['source'],'purpose_ready':result['ready'],'purpose_missing':result['missing'],'trial_source':trial['source'],'ledger_and_xp_unchanged':ledger.transactions()==before and ledger.adventure.state()['xp']==xp}
    evidence['passed']=result['source']=='ai' and result['ready'] and trial['source']=='ai' and evidence['ledger_and_xp_unchanged']
    (root/'output/evidence/live_setup_completion_check.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(evidence,ensure_ascii=False))
    if not evidence['passed']:raise SystemExit(1)
