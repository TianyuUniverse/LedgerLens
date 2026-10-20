"""Opt-in real provider check using only synthetic purpose-memory examples."""
import json
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from ledger.service import Ledger
from ledger.provider import load_local_config

def main():
    load_local_config(ROOT)
    with tempfile.TemporaryDirectory() as temp:
        ledger=Ledger(Path(temp)/'synthetic.sqlite')
        ledger.import_csv('date,description,amount,kind,category,counterparty,note\n2026-09-10,校园账户充值,50,expense,Education,示例大学,伙食费\n')
        record=ledger.transactions()[0];coach=ledger.setup_chat
        first=coach.chat({'mode':'purpose','message':'这是食堂伙食费','context':{'record_id':record['id']},'use_model':True})
        assert first['source']=='ai' and first['ready']
        assert not ledger.memory.list()
        choice=coach.chat({'mode':'purpose','message':'记住，以后相同条件自动分类','conversation_id':first['conversation_id'],'revision':first['revision'],'memory_policy':'auto','use_model':False})
        saved=coach.commit({'conversation_id':choice['conversation_id'],'revision':choice['revision']})
        before=ledger.memory.list()[0]
        edit=coach.chat({'mode':'purpose','message':'只把用途名称改为校园伙食费，原来的分类、匹配条件和自动处理方式保持不变','context':{'record_id':record['id'],'memory_id':saved['memory_id']},'use_model':True})
        assert edit['source']=='ai' and edit['ready'] and edit['draft']['auto_apply']
        assert edit['draft']['match']==before['match']
        coach.commit({'conversation_id':edit['conversation_id'],'revision':edit['revision']})
        follow=ledger.import_csv('date,description,amount,kind,category,counterparty,note\n2026-10-10,校园账户充值,60,expense,Education,示例大学,伙食费\n')
        assert follow['auto_labeled']==1
        result={'passed':True,'synthetic_only':True,'external_model_calls':2,'purpose_source':first['source'],'edit_source':edit['source'],'consent_explicit':True,'editing_preserves_settings':True,'followup_auto_classified':1,'scope':'Integration smoke check, not a representative accuracy evaluation.'}
        (ROOT/'output/evidence/live_memory_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
