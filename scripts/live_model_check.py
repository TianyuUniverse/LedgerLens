"""Explicit, small live smoke check on synthetic records. Never runs in unit tests."""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ledger.service import Ledger
from ledger.provider import load_local_config


def main():
    load_local_config(ROOT)
    cases=[];classifications=[]
    with tempfile.TemporaryDirectory() as temp:
        ledger=Ledger(Path(temp)/'synthetic.sqlite')
        ledger.import_csv((ROOT/'samples/transactions.csv').read_text(encoding='utf-8'))
        before=ledger.transactions()
        session=None
        for question in ('九月为什么比八月花得多？','我想六个月存6000，房租不能减，娱乐每月至少留200。','我不想减少餐饮。'):
            result=ledger.ask(question,session,use_model=True)
            session=result['session_id']
            cases.append({'question':question,'source':result['source'],'notice':result.get('notice'),
                          'tool_trace':result.get('tool_trace',[]),'answer':result['answer'],'data':result.get('data'),
                          'model_tool_call_succeeded':result['source'].startswith('model tool calling')})
        unchanged=before==ledger.transactions()
        ledger.import_csv((ROOT/'samples/memory_seed.csv').read_text(encoding='utf-8'))
        snapshot=ledger.transactions()
        for note,expected_kind,expected_category in (('伙食费','expense','Food'),('电费和空调费','expense','Utilities'),('账户调拨','transfer','Transfer')):
            record=next(r for r in snapshot if r['note']==note)
            result=ledger.suggest(record['id'])
            classifications.append({'record_id':record['id'],'context':{k:record[k] for k in ('description','counterparty','note','source_kind','source_category')},
                                   'expected':{'kind':expected_kind,'category':expected_category},'proposal':result,
                                   'passed':result['source']=='model' and result.get('kind')==expected_kind and result['category']==expected_category})
        unchanged=unchanged and snapshot==ledger.transactions()
    evidence={'run_at_utc':datetime.now(timezone.utc).isoformat(),'requested_model':os.getenv('FINANCE_AI_MODEL'),'dataset':'Synthetic course demo only. Smoke check, not a representative model accuracy evaluation.',
              'cases':cases,'classification_cases':classifications,'ledger_unchanged':unchanged,
              'passed':sum(c['model_tool_call_succeeded'] for c in cases),'total':len(cases),
              'classification_passed':sum(c['passed'] for c in classifications),'classification_total':len(classifications)}
    dest=ROOT/'output/evidence/live_model_smoke.json';dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':evidence['passed'],'total':evidence['total'],'classification_passed':evidence['classification_passed'],'classification_total':len(classifications),'ledger_unchanged':unchanged,
                      'notices':[c['notice'] for c in cases if c['notice']]},ensure_ascii=False))
    return 0 if evidence['passed']==len(cases) and all(c['passed'] for c in classifications) and unchanged else 1


if __name__=='__main__':
    raise SystemExit(main())
