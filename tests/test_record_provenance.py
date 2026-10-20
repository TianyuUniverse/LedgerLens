import json,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import Mock
from ledger.service import Ledger
from ledger.domain import DomainError

class RecordProvenanceTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.ledger=Ledger(Path(self.tmp.name)/'record.sqlite')
    def tearDown(self):self.tmp.cleanup()
    def test_import_and_category_correction_preserve_file_text_origin(self):
        self.ledger.import_csv('date,description,amount,kind\n2026-09-10,账单原始商品,20,expense\n')
        row=self.ledger.transactions()[0];self.assertEqual(row['ingestion_origin'],'csv');self.assertEqual(row['description_origin'],'file')
        self.ledger.edit(row['id'],{'category':'Food'});self.assertEqual(self.ledger.transactions()[0]['description_origin'],'file');self.assertEqual(self.ledger.transactions()[0]['description'],'账单原始商品')
    def test_user_edit_to_imported_text_is_identified_as_user_edit(self):
        self.ledger.import_csv('date,description,amount,kind\n2026-09-10,原始商品,20,expense\n');self.ledger.edit(self.ledger.transactions()[0]['id'],{'description':'我填写的午餐'})
        self.assertEqual(self.ledger.transactions()[0]['description_origin'],'user')
    def test_ai_draft_and_manual_override_are_distinguished(self):
        provider=Mock(return_value={'content':json.dumps({'kind':'expense','category':'Food','description':'食堂午餐'})})
        draft=self.ledger.quick_entry.draft({'text':'昨天午饭20元','use_model':True},provider)
        self.ledger.quick_entry.save({**draft['record'],'draft_id':draft['draft_id']});r=self.ledger.transactions()[0]
        self.assertEqual(r['ingestion_origin'],'entry');self.assertEqual(r['description_origin'],'ai')
        self.ledger.quick_entry.save({**draft['record'],'description':'我改成早餐','draft_id':draft['draft_id']})
        self.assertEqual(self.ledger.transactions()[0]['description_origin'],'user')
    def test_local_draft_is_not_labeled_as_ai(self):
        draft=self.ledger.quick_entry.draft({'text':'昨天午饭20元','use_model':False});self.ledger.quick_entry.save({**draft['record'],'draft_id':draft['draft_id']})
        self.assertEqual(self.ledger.transactions()[0]['description_origin'],'local')
    def test_chat_tracks_ai_description_across_amount_only_followup(self):
        provider=Mock(return_value={'content':json.dumps({'reply':'已整理，请核对。','patch':{'description':'食堂午餐','kind':'expense','category':'Food'}})})
        a=self.ledger.setup_chat.chat({'mode':'entry','message':'昨天午饭20元','use_model':True},provider)
        b=self.ledger.setup_chat.chat({'mode':'entry','message':'25元','conversation_id':a['conversation_id'],'revision':a['revision'],'use_model':False})
        self.ledger.setup_chat.commit({'conversation_id':b['conversation_id'],'revision':b['revision']})
        self.assertEqual(self.ledger.transactions()[0]['description_origin'],'ai');self.assertEqual(self.ledger.transactions()[0]['amount_fen'],2500)
    def test_forged_draft_id_is_rejected(self):
        with self.assertRaises(DomainError):self.ledger.quick_entry.save({'date':'2026-09-10','description':'午餐','amount':'20','kind':'expense','category':'Food','draft_id':uuid.uuid4().hex})
        self.assertEqual(self.ledger.transactions(),[])
    def test_deleted_ids_are_not_reused_for_unrelated_new_bills(self):
        self.ledger.import_csv('date,description,amount,kind\n2026-09-10,first,20,expense\n2026-09-11,second,30,expense\n')
        highest=max(r['id'] for r in self.ledger.transactions())
        with self.ledger.connection() as con:con.execute('DELETE FROM transactions')
        reopened=Ledger(self.ledger.path);reopened.import_csv('date,description,amount,kind\n2026-09-12,new,40,expense\n')
        self.assertGreater(reopened.transactions()[0]['id'],highest)

if __name__=='__main__':unittest.main()
