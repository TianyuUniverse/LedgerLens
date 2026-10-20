import json,tempfile,unittest,uuid
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import Mock
from ledger.service import Ledger
from ledger.domain import DomainError

class SetupChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.ledger=Ledger(Path(self.tmp.name)/'test.sqlite',clock=lambda:datetime(2026,10,19,12,tzinfo=timezone(timedelta(hours=8))))
        self.coach=self.ledger.setup_chat
    def tearDown(self):self.tmp.cleanup()
    def talk(self,mode,text,previous=None,context=None,patch=None):
        provider=Mock(return_value={'content':json.dumps({'reply':'我把你的想法整理好了，请核对下面的草稿。','patch':patch},ensure_ascii=False)}) if patch is not None else None
        raw={'mode':mode,'message':text,'use_model':patch is not None,'context':context or {}}
        if previous:raw.update(conversation_id=previous['conversation_id'],revision=previous['revision'])
        return self.coach.chat(raw,provider)
    def confirm(self,r,**extra):return self.coach.commit({'conversation_id':r['conversation_id'],'revision':r['revision'],**extra})
    def goal(self):return self.ledger.adventure.create_goal({'title':'旅行','target':'1000','initial':'0','request_id':uuid.uuid4().hex})
    def test_goal_clarification_then_confirm_and_duplicate(self):
        a=self.talk('goal','想去旅行');self.assertFalse(a['ready']);self.assertEqual(self.ledger.adventure.state()['goals'],[])
        b=self.talk('goal','想攒3000元',a);self.assertTrue(b['ready']);self.assertEqual(b['draft']['title'],'旅行基金')
        saved=self.confirm(b);self.assertEqual(saved,self.confirm(b));self.assertEqual(len(self.ledger.adventure.state()['goals']),1)
    def test_goal_model_proposes_no_business_write(self):
        r=self.talk('goal','旅行基金，想攒3000元',patch={'title':'旅行基金','target':'3000'})
        self.assertEqual(r['source'],'ai');self.assertEqual(self.ledger.adventure.state()['xp'],0);self.assertFalse(r['saved'])
    def test_user_amount_cannot_be_changed_by_model(self):
        r=self.talk('goal','想攒3000元',patch={'target':'9000'})
        self.assertEqual(r['source'],'local');self.assertEqual(r['draft']['target'],'3000.00')
    def test_goal_initial_and_future_date(self):
        r=self.talk('goal','六个月攒6000，已经存了500',patch={'title':'安心基金','target':'6000','initial':'500','deadline':'2027-04-19'})
        self.assertTrue(r['ready']);self.assertEqual(r['draft']['initial'],'500.00');self.assertEqual(self.ledger.adventure.state()['goals'],[])
    def test_stale_conversation_does_not_overwrite_newer_draft(self):
        a=self.talk('goal','想攒3000元');b=self.talk('goal','改成5000元',a)
        with self.assertRaises(DomainError):self.confirm(a)
        with self.assertRaises(DomainError):self.talk('goal','改成2000元',a)
        self.assertEqual(b['draft']['target'],'5000.00')
    def test_budget_is_draft_until_confirmation(self):
        r=self.talk('budget','餐饮预算600元');self.assertTrue(r['ready']);self.assertEqual(self.ledger.state()['budgets'],[])
        self.confirm(r);self.assertEqual(self.ledger.state()['budgets'][0]['limit_fen'],60000)
    def test_entry_conversation_saves_exact_amount_after_confirm(self):
        r=self.talk('entry','昨天食堂午饭25.20元');self.assertTrue(r['ready']);self.assertEqual(self.ledger.transactions(),[])
        self.confirm(r);row=self.ledger.transactions()[0];self.assertEqual(row['amount_fen'],2520);self.assertEqual(row['date'],'2026-10-18')
    def test_allocation_without_confirmation_does_not_progress_or_grant_xp(self):
        goal=self.goal();xp=self.ledger.adventure.state()['xp'];r=self.talk('allocation','存入100元',context={'goal_id':goal['id']})
        self.assertTrue(r['ready']);self.assertEqual(self.ledger.adventure.state()['goals'][0]['balance_fen'],0);self.assertEqual(self.ledger.adventure.state()['xp'],xp)
        self.confirm(r);self.confirm(r);self.assertEqual(self.ledger.adventure.state()['goals'][0]['balance_fen'],10000)
    def test_invalid_allocation_context_rejected(self):
        with self.assertRaises(DomainError):self.talk('allocation','存入100元',context={'goal_id':9999})
    def test_reflection_conversation_requires_real_period_and_confirmation(self):
        self.ledger.import_csv('date,description,amount,kind,category\n2026-09-10,lunch,25,expense,Food\n')
        r=self.talk('reflection','下次买东西前先列清单',context={'month':'2026-09'});self.assertTrue(r['ready'])
        xp=self.ledger.adventure.state()['xp'];self.confirm(r);after=self.ledger.adventure.state()['xp'];self.confirm(r)
        self.assertGreater(after,xp);self.assertEqual(self.ledger.adventure.state()['xp'],after)
    def test_purpose_model_cannot_enable_memory_without_consent(self):
        self.ledger.import_csv('date,description,amount,kind,category,counterparty,note\n2026-09-10,campus payment,50,transfer,Transfer,SCUT,meal\n')
        record=self.ledger.transactions()[0]
        r=self.talk('purpose','这是伙食费',context={'record_id':record['id']},patch={'kind':'expense','category':'Food','purpose':'伙食费','remember':True,'auto_apply':True})
        self.assertFalse(r['draft']['auto_apply']);self.assertEqual(self.ledger.transactions()[0]['kind'],'transfer')
        self.confirm(r);self.assertEqual(self.ledger.transactions()[0]['category'],'Food')
    def test_plan_preview_stale_after_ledger_change(self):
        self.ledger.import_csv((Path(__file__).resolve().parents[1]/'samples/transactions.csv').read_text(encoding='utf-8'))
        r=self.talk('plan','六个月存6000元');self.assertTrue(r['ready'])
        self.ledger.quick_entry.save({'date':'2026-10-19','description':'new lunch','kind':'expense','category':'Food','amount':'10'})
        with self.assertRaises(DomainError):self.confirm(r,style='balanced')
    def test_missing_fields_and_unknown_model_action_cannot_commit(self):
        r=self.talk('goal','先聊聊',patch={'award_xp':999});self.assertFalse(r['ready'])
        with self.assertRaises(DomainError):self.confirm(r)
    def test_persistent_draft_and_confirm_result_survive_reopen(self):
        r=self.talk('goal','想攒3000元');new=Ledger(self.ledger.path);a=new.setup_chat.load(r['conversation_id']);self.assertEqual(a['draft']['target'],'3000.00')
    def test_model_cannot_drop_fixed_categories_or_lower_stated_floor(self):
        r=self.talk('plan','六个月存6000元，房租不能减，娱乐至少留200',patch={'target':'6000','months':6,'locked':[],'floors':{'Entertainment':'1'}})
        self.assertIn('Housing',r['draft']['locked']);self.assertEqual(r['draft']['floors']['Entertainment'],'200.00')
    def test_model_cannot_enable_memory_against_explicit_refusal(self):
        self.ledger.import_csv('date,description,amount,kind,category,counterparty,note\n2026-09-10,campus payment,50,transfer,Transfer,SCUT,meal\n')
        record=self.ledger.transactions()[0]
        r=self.talk('purpose','这是伙食费，不要记住',context={'record_id':record['id']},patch={'kind':'expense','category':'Food','purpose':'伙食费','remember':True,'auto_apply':True})
        self.assertFalse(r['draft']['remember']);self.assertFalse(r['draft']['auto_apply'])

    def test_editing_memory_keeps_approved_conditions_and_auto_setting(self):
        self.ledger.import_csv('date,description,amount,kind,category,counterparty,note\n2026-09-10,校园账户充值,50,expense,Education,学校,九月伙食费\n')
        record=self.ledger.transactions()[0]
        saved=self.ledger.memory.confirm(record['id'],{'kind':'expense','category':'Food','purpose':'伙食费','remember':True,'auto_apply':True,'match':{'counterparty':'学校','note':'伙食费'}})
        r=self.talk('purpose','名称改成校园伙食费',context={'record_id':record['id'],'memory_id':saved['memory_id']})
        self.assertTrue(r['draft']['auto_apply'])
        self.assertEqual(r['draft']['match'],{'counterparty':'学校','note':'伙食费'})
        self.confirm(r)
        self.assertTrue(self.ledger.memory.list()[0]['auto_apply'])

    def test_explicit_memory_policy_is_previewed_and_applies_to_followup(self):
        self.ledger.import_csv('date,description,amount,kind,category,counterparty,note\n2026-09-10,校园账户充值,50,expense,Education,学校,伙食费\n')
        record=self.ledger.transactions()[0]
        r=self.talk('purpose','这是伙食费',context={'record_id':record['id']})
        r=self.coach.chat({'mode':'purpose','message':'以后相同条件自动分类','memory_policy':'auto','use_model':False,'conversation_id':r['conversation_id'],'revision':r['revision']})
        self.assertTrue(r['draft']['auto_apply']);self.assertEqual(self.ledger.memory.list(),[])
        self.confirm(r)
        self.ledger.import_csv('date,description,amount,kind,category,counterparty,note\n2026-10-10,校园账户充值,60,expense,Education,学校,伙食费\n')
        self.assertEqual(self.ledger.transactions()[0]['review_status'],'auto')

if __name__=='__main__':unittest.main()
