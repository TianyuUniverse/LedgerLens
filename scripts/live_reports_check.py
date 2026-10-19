"""Opt-in live checks using synthetic data only; secrets never enter evidence."""
import json
import sys
import tempfile
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ledger.provider import load_local_config
from ledger.service import Ledger
def main():
    load_local_config(ROOT)
    with tempfile.TemporaryDirectory() as directory:
        ledger=Ledger(Path(directory)/'synthetic.sqlite',clock=lambda:datetime(2026,10,19,12,tzinfo=timezone(timedelta(hours=8))))
        ledger.import_csv((ROOT/'samples/transactions.csv').read_text(encoding='utf-8'))
        before=ledger.transactions();xp=ledger.adventure.state()['xp'];reports=[]
        for kind,anchor in (('month','2026-09'),('week','2026-09-21')):
            result=ledger.reports.generate({'kind':kind,'anchor':anchor,'use_model':True})
            reports.append({'kind':kind,'anchor':anchor,'mode':result['generation']['mode'],
                'notice':result['generation']['notice'],'coaching':result['coaching'],'facts':result['facts']})
        draft=ledger.quick_entry.draft({'text':'昨天在食堂吃午饭25元','use_model':True})
        passed=all(r['mode']=='ai' for r in reports) and draft['mode']=='ai' and ledger.transactions()==before and ledger.adventure.state()['xp']==xp
        evidence={'run_at':datetime.now(timezone.utc).isoformat(),'passed':passed,'synthetic_only':True,
            'report_calls':2,'draft_calls':1,'reports':reports,'draft':draft,'ledger_unchanged':ledger.transactions()==before,
            'xp_unchanged':ledger.adventure.state()['xp']==xp,'limitation':'Three integration cases, not a held-out accuracy evaluation or user study.'}
        path=ROOT/'output/evidence/live_reports_check.json';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'passed':passed,'report_modes':[r['mode'] for r in reports],'draft_mode':draft['mode'],'ledger_unchanged':evidence['ledger_unchanged'],'evidence':str(path)},ensure_ascii=False))
        if not passed:raise SystemExit(1)
if __name__=='__main__':main()
