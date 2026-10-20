"""Opt-in real model checks on an isolated synthetic ledger only."""
import json,sys,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ledger.service import Ledger
from ledger.provider import load_local_config
def main():
    load_local_config(ROOT);results=[]
    with tempfile.TemporaryDirectory() as directory:
        ledger=Ledger(Path(directory)/'test.sqlite',clock=lambda:datetime(2026,10,19,12,tzinfo=timezone(timedelta(hours=8))))
        ledger.import_csv((ROOT/'samples/transactions.csv').read_text(encoding='utf-8'));ledger.import_csv((ROOT/'samples/memory_seed.csv').read_text(encoding='utf-8'))
        def talk(mode,message,context=None,previous=None):
            raw={'mode':mode,'message':message,'context':context or {},'use_model':True}
            if previous:raw.update(conversation_id=previous['conversation_id'],revision=previous['revision'])
            r=ledger.setup_chat.chat(raw);results.append({'mode':mode,'source':r['source'],'ready':r['ready'],'notice':r['notice']});return r
        before=ledger.transactions();xp=ledger.adventure.state()['xp']
        first=talk('goal','我想为旅行攒钱');goal=talk('goal','想攒3000元，已经存了500',previous=first)
        talk('budget','每月餐饮预算600元');talk('entry','昨天食堂午饭25.20元');talk('plan','六个月存6000元，房租不能减，娱乐至少留200')
        talk('reflection','复盘2026-09：下个月购物前先列清单，再决定是否购买。',{'month':'2026-09'})
        record=next(r for r in ledger.transactions() if r['note']=='伙食费');talk('purpose','这是食堂伙食费，以后相同备注就自动归为餐饮',{'record_id':record['id']})
        unchanged=ledger.transactions()==before and ledger.adventure.state()['xp']==xp
        # Creating an isolated test goal explicitly confirms this one draft; allocation remains a draft.
        if goal['ready']:
            g=ledger.setup_chat.commit({'conversation_id':goal['conversation_id'],'revision':goal['revision']})
            talk('allocation','今天为这个目标存入100元',{'goal_id':g['id']})
        passed=all(r['source']=='ai' for r in results) and unchanged
        evidence={'checked_at':datetime.now(timezone.utc).isoformat(),'passed':passed,'synthetic_only':True,'calls':len(results),'cases':results,'drafts_did_not_modify_ledger_or_xp':unchanged,'limitation':'Integration examples only, not held-out accuracy or user research.'}
        (ROOT/'output/evidence/live_setup_check.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(evidence,ensure_ascii=False))
        if not passed:raise SystemExit(1)
if __name__=='__main__':main()
