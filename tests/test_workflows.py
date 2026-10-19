import copy
import json
import sqlite3
import tempfile
import unittest
import threading
import urllib.request
import urllib.error
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from ledger.service import Ledger, DomainError
from ledger.provider import ProviderError, load_local_config
from app import create_server

ROOT=Path(__file__).resolve().parents[1]
HEADER='date,description,amount,kind,category,counterparty,note,source_kind,source_category\n'
BASE=(ROOT/'samples/transactions.csv').read_text(encoding='utf-8')
SEED=(ROOT/'samples/memory_seed.csv').read_text(encoding='utf-8')
FOLLOW=(ROOT/'samples/memory_followup.csv').read_text(encoding='utf-8')
PLAN={'target':'6000','months':6,'locked':['Housing'],'floors':{'Entertainment':'200'}}


def call(name,args,call_id='call_test'):
    return {'role':'assistant','content':None,'tool_calls':[{'id':call_id,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]}


class WorkflowCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'ledger.sqlite';self.ledger=Ledger(self.path)
    def tearDown(self):
        self.tmp.cleanup()
    def seed(self):
        self.ledger.import_csv(SEED)
    def row(self,phrase,month=None):
        return next(r for r in self.ledger.transactions() if phrase in (r['description']+' '+r['note']) and (not month or r['date'].startswith(month)))
    def confirm(self,phrase,desired_category,pattern,**changes):
        row=self.row(phrase)
        raw={'kind':'expense','category':desired_category,'purpose':'Confirmed '+desired_category,'remember':True,'auto_apply':True,'match':pattern,'expected_revision':row['revision'],**changes}
        return self.ledger.memory.confirm(row['id'],raw)


class MemoryTests(WorkflowCase):
    def test_school_payee_without_a_purpose_requires_review(self):
        self.ledger.import_csv(HEADER+'2026-09-02,支付成功,900,expense,Education,华南理工大学,,expense,教育\n')
        self.assertEqual(self.ledger.transactions()[0]['review_status'],'needs_review')
    def test_original_context_and_pending_status_retained(self):
        self.seed();meal=self.row('伙食费');utility=self.row('电费')
        self.assertEqual((meal['category'],meal['source_category'],meal['review_status']),('Education','教育','needs_review'))
        self.assertEqual((utility['kind'],utility['source_kind'],utility['review_status']),('transfer','微信转账','needs_review'))
    def test_approved_context_reused_for_future_import(self):
        self.seed();confirmed=self.confirm('伙食费','Food',{'counterparty':'华南理工大学','note':'伙食费'})
        self.ledger.import_csv(FOLLOW);meal=self.row('伙食费','2026-09')
        self.assertEqual((meal['category'],meal['category_source'],meal['memory_id'],meal['memory_version']),('Food','memory',confirmed['memory_id'],1))
        self.assertEqual(meal['source_category'],'教育')
    def test_roommate_correction_changes_kind_and_spending(self):
        self.seed();before=self.ledger.overview()['expense_fen']
        self.confirm('电费','Utilities',{'counterparty':'舍友小林','note':'电费和空调费'})
        self.assertEqual(self.ledger.overview()['expense_fen']-before,8000)
        result=self.ledger.import_csv(FOLLOW)
        utility=self.row('电费','2026-09')
        self.assertEqual((utility['kind'],utility['category'],utility['review_status']),('expense','Utilities','auto'))
        self.assertEqual(result['auto_labeled'],1)
    def test_same_school_tuition_is_not_food(self):
        self.seed();self.confirm('伙食费','Food',{'counterparty':'华南理工大学','note':'伙食费'})
        self.ledger.import_csv(FOLLOW);tuition=self.row('学费')
        self.assertEqual((tuition['category'],tuition['review_status']),('Education','needs_review'))
    def test_roommate_other_purpose_stays_pending(self):
        self.seed();self.confirm('电费','Utilities',{'counterparty':'舍友小林','note':'电费和空调费'})
        self.ledger.import_csv(FOLLOW);other=self.row('用途待确认')
        self.assertEqual((other['kind'],other['review_status']),('transfer','needs_review'))
    def test_own_account_transfer_never_becomes_spending(self):
        self.seed();self.ledger.import_csv(FOLLOW)
        own=[r for r in self.ledger.transactions() if r['counterparty']=='本人储蓄账户']
        self.assertTrue(all(r['kind']=='transfer' for r in own))
        self.assertFalse(set(r['id'] for r in own)&set(self.ledger.tools.query_transactions({})['record_ids']))
    def test_payee_only_automatic_rule_rejected_atomically(self):
        self.seed();before=self.ledger.transactions()
        with self.assertRaises(DomainError):self.confirm('伙食费','Food',{'counterparty':'华南理工大学'})
        self.assertEqual(before,self.ledger.transactions());self.assertEqual(self.ledger.memory.list(),[])
    def test_review_only_memory_does_not_auto_correct(self):
        self.seed();self.confirm('伙食费','Food',{'counterparty':'华南理工大学'},auto_apply=False)
        self.ledger.import_csv(FOLLOW);row=self.row('伙食费','2026-09')
        self.assertEqual((row['category'],row['review_status']),('Education','needs_review'))
    def test_conflicting_memories_require_review(self):
        self.seed();pattern={'counterparty':'华南理工大学','note':'伙食费'}
        self.confirm('伙食费','Food',pattern);self.confirm('伙食费','Education',pattern)
        self.ledger.import_csv(FOLLOW);row=self.row('伙食费','2026-09')
        self.assertEqual(row['review_status'],'needs_review');self.assertNotEqual(row['category_source'],'memory')
    def test_memory_version_edit_does_not_rewrite_history(self):
        self.seed();memory=self.confirm('伙食费','Food',{'note':'伙食费'})['memory_id']
        self.ledger.import_csv(FOLLOW);before=self.ledger.transactions()
        updated=self.ledger.memory.update(memory,{'purpose':'Revised description'})
        self.assertEqual(updated['version'],2);self.assertEqual(before,self.ledger.transactions())
        self.assertEqual(self.row('伙食费','2026-09')['memory_version'],1)
    def test_disable_and_delete_stop_future_reuse_keep_labels(self):
        self.seed();memory=self.confirm('伙食费','Food',{'note':'伙食费'})['memory_id']
        self.ledger.memory.update(memory,{'enabled':False});self.ledger.import_csv(FOLLOW)
        self.assertNotEqual(self.row('伙食费','2026-09')['category_source'],'memory')
        before=self.ledger.transactions();self.ledger.memory.delete(memory)
        self.assertEqual(before,self.ledger.transactions());self.assertEqual(self.ledger.memory.list(),[])
        self.assertEqual(self.ledger.state()['audit'][0]['action'],'memory_delete')
    def test_reimport_after_kind_correction_skips_original_record(self):
        self.seed();self.confirm('电费','Utilities',{'note':'电费和空调费'})
        repeated=self.ledger.import_csv(SEED)
        self.assertEqual((repeated['inserted'],repeated['duplicates']),(0,3))
    def test_stale_confirmation_rejected_without_memory(self):
        self.seed();row=self.row('伙食费');self.ledger.edit(row['id'],{'category':'Other'})
        with self.assertRaises(DomainError):self.confirm('伙食费','Food',{'note':'伙食费'},expected_revision=1)
        self.assertEqual(self.ledger.memory.list(),[])
    def test_failed_confirmation_audit_rolls_back_memory_and_record(self):
        self.seed();before=self.ledger.transactions()
        with patch.object(self.ledger,'audit',side_effect=RuntimeError('failure')):
            with self.assertRaises(RuntimeError):self.confirm('伙食费','Food',{'note':'伙食费'})
        self.assertEqual(before,self.ledger.transactions());self.assertEqual(self.ledger.memory.list(),[])
    def test_one_off_confirmation_does_not_create_memory(self):
        self.seed();self.confirm('电费','Utilities',{},remember=False)
        self.assertEqual(self.ledger.memory.list(),[]);self.assertEqual(self.row('电费')['kind'],'expense')
    def test_confirmation_and_memory_schema_boundaries(self):
        self.seed();row=self.row('伙食费')
        for change in ({'kind':'transfer','category':'Food'},{'category':None},{'remember':'true'},{'purpose':[]},{'match':{'note':'unmatched'}},{'auto_apply':'yes'}):
            with self.subTest(change=change),self.assertRaises(DomainError):self.confirm('伙食费','Food',{'note':'伙食费'},**change)
        self.assertEqual(self.ledger.memory.list(),[])
        with self.assertRaises(DomainError):self.ledger.memory.confirm(True,{'kind':'expense','category':'Food'})
    def test_conflicting_purpose_keyword_blocks_broad_rule(self):
        self.ledger.import_csv(SEED.replace('校园账户充值','校园伙食支出'));self.confirm('伙食费','Food',{'description':'校园伙食支出'})
        self.ledger.import_csv(HEADER+'2026-10-01,校园伙食支出,100,expense,Education,华南理工大学,学费,expense,教育\n')
        row=self.row('学费');self.assertEqual(row['review_status'],'needs_review');self.assertEqual(row['category'],'Education')
    def test_generic_transfer_description_cannot_authorize_automatic_reuse(self):
        self.seed()
        with self.assertRaises(DomainError):self.confirm('电费','Utilities',{'counterparty':'舍友小林','description':'微信转账'})
        self.assertEqual(self.ledger.memory.list(),[])
    def test_database_reopen_preserves_original_labels_and_memories(self):
        self.seed();self.confirm('电费','Utilities',{'note':'电费和空调费'})
        before=self.ledger.transactions();reopened=Ledger(self.path)
        self.assertEqual(before,reopened.transactions());self.assertEqual(len(reopened.memory.list()),1)
    def test_legacy_schema_migrates_idempotently(self):
        legacy=Path(self.tmp.name)/'legacy.sqlite'
        with closing(sqlite3.connect(legacy)) as con:
            con.executescript("CREATE TABLE transactions(id INTEGER PRIMARY KEY,date TEXT,description TEXT,amount_fen INTEGER,kind TEXT,category TEXT,fingerprint TEXT UNIQUE,category_source TEXT,created_at TEXT); INSERT INTO transactions VALUES(7,'2026-08-01','legacy',500,'transfer','Transfer','old-hash','import','old-time');")
        first=Ledger(legacy);before=first.transactions();second=Ledger(legacy)
        self.assertEqual(before,second.transactions());self.assertEqual(before[0]['id'],7)
        self.assertEqual(before[0]['review_status'],'needs_review')


class ToolTests(WorkflowCase):
    def setUp(self):
        super().setUp();self.ledger.import_csv(BASE)
    def test_comparison_expected_totals_and_category_sources(self):
        result=self.ledger.tools.compare_periods({'first_month':'2026-08','second_month':'2026-09'})
        self.assertEqual((result['first_fen'],result['second_fen'],result['delta_fen']),(340000,350000,10000))
        shopping=next(c for c in result['categories'] if c['category']=='Shopping')
        self.assertEqual((shopping['first_fen'],shopping['second_fen'],shopping['delta_fen']),(65000,75000,10000))
        rows={r['id']:r for r in self.ledger.transactions()}
        self.assertTrue(all(rows[i]['category']=='Shopping' for i in shopping['record_ids']))
    def test_exclusion_changes_analysis_without_deleting(self):
        row=self.row('Taobao clothes September');before=self.ledger.transactions()
        result=self.ledger.tools.compare_periods({'first_month':'2026-08','second_month':'2026-09','exclude_ids':[row['id']]})
        self.assertEqual(result['second_fen'],312500);self.assertNotIn(row['id'],result['record_ids']);self.assertEqual(before,self.ledger.transactions())
    def test_invalid_tool_arguments_cannot_write(self):
        before=self.ledger.transactions()
        for name,args in (('delete_transactions',{}),('compare_periods',{'first_month':'2026-08','second_month':'2026-09','sql':'DELETE'}),('query_transactions',{'exclude_ids':[True]}),('query_transactions',{'month':'2026-13'}),('query_transactions',{'exclude_ids':[999999]})):
            with self.subTest(name=name),self.assertRaises(DomainError):self.ledger.tools.dispatch(name,args)
        self.assertEqual(before,self.ledger.transactions())
    def test_plans_independent_money_constraints_and_no_save(self):
        result=self.ledger.tools.generate_savings_plans(PLAN)
        self.assertEqual(result['monthly_income_fen'],400000);self.assertEqual(result['required_monthly_fen'],100000)
        for option in result['options']:
            budgets=option['monthly_amounts_fen'];self.assertEqual(budgets['Housing'],120000);self.assertGreaterEqual(budgets['Entertainment'],20000)
            self.assertEqual(option['monthly_savings_fen'],400000-sum(budgets.values()))
            self.assertEqual(option['projected_fen'],option['monthly_savings_fen']*6)
            self.assertTrue(option['constraints_passed']);self.assertEqual(option['gap_fen'],0)
        self.assertIsNone(self.ledger.state()['generated_plan'])
    def test_impossible_goal_keeps_limits_and_gap(self):
        result=self.ledger.tools.generate_savings_plans({**PLAN,'target':'100000','locked':['Housing','Food']})
        for option in result['options']:
            self.assertFalse(option['feasible']);self.assertGreater(option['gap_fen'],0)
            self.assertEqual(option['monthly_amounts_fen']['Food'],85000)
            self.assertEqual(option['monthly_amounts_fen']['Housing'],120000)
    def test_minimum_above_baseline_is_respected(self):
        result=self.ledger.tools.generate_savings_plans({**PLAN,'floors':{'Food':'1000'}})
        self.assertTrue(all(o['monthly_amounts_fen']['Food']>=100000 for o in result['options']))
        with self.assertRaises(DomainError):self.ledger.tools.generate_savings_plans({**PLAN,'locked':['Food'],'floors':{'Food':'1000'}})
    def test_preview_save_rechecks_ledger_revision(self):
        preview=self.ledger.tools.generate_savings_plans(PLAN)
        saved=self.ledger.tools.save_plan({'inputs':preview['inputs'],'style':'balanced','ledger_revision':preview['ledger_revision']})
        self.assertTrue(saved['saved']);self.assertEqual(self.ledger.state()['generated_plan']['style'],'balanced')
        self.ledger.edit(self.row('Grocery July')['id'],{'category':'Other'})
        with self.assertRaisesRegex(DomainError,'changed'):self.ledger.tools.save_plan({'inputs':preview['inputs'],'style':'shopping_first','ledger_revision':preview['ledger_revision']})
        self.assertEqual(self.ledger.state()['generated_plan']['style'],'balanced')
    def test_monthly_review_links_patterns_not_motivation(self):
        self.ledger.import_csv(HEADER+'2026-08-22,Coffee daily,12,expense,Food,Cafe,,expense,Food\n2026-09-22,Coffee daily,15,expense,Food,Cafe,,expense,Food\n2026-10-22,Coffee daily,18,expense,Food,Cafe,,expense,Food\n')
        review=self.ledger.tools.monthly_review({'month':'2026-09'})
        self.assertEqual(review['small_payments']['total_fen'],1500)
        group=next(g for g in review['recurring'] if g['description']=='cafe')
        self.assertEqual(group['months'],['2026-08','2026-09']);self.assertIn('Not proof',group['notice'])
    def test_memory_retrieval_is_read_only(self):
        self.ledger.import_csv(SEED);self.confirm('伙食费','Food',{'note':'伙食费'})
        before=self.ledger.transactions();result=self.ledger.tools.dispatch('retrieve_category_memories',{'record_id':self.row('伙食费')['id']})
        self.assertEqual(result['memories'][0]['category'],'Food');self.assertEqual(before,self.ledger.transactions())


class ConversationTests(WorkflowCase):
    def setUp(self):
        super().setUp();self.ledger.import_csv(BASE)
    def test_chinese_comparison_and_followup_persist_after_restart(self):
        result=self.ledger.ask('九月为什么比八月花得多？');session=result['session_id']
        self.assertEqual(result['data']['delta_fen'],10000)
        reopened=Ledger(self.path);result=reopened.ask('去掉Taobao clothes September这笔呢？',session)
        self.assertEqual(result['data']['second_fen'],312500)
        restored=reopened.ask('取消排除',session);self.assertEqual(restored['data']['second_fen'],350000)
    def test_ambiguous_computer_exclusion_asks_for_id(self):
        self.ledger.import_csv(HEADER+'2026-09-01,Laptop A,2000,expense,Shopping,,,,\n2026-09-02,Computer B,3000,expense,Shopping,,,,\n')
        result=self.ledger.ask('九月和八月比较');session=result['session_id'];before=self.ledger.transactions()
        choices=self.ledger.ask('那去掉买电脑这笔呢？',session)
        self.assertEqual(len(choices['choices']),2);self.assertFalse(choices['supported'])
        record_id=choices['choices'][0]['id'];result=self.ledger.ask('#'+str(record_id),session)
        self.assertEqual(result['data']['exclude_ids'],[record_id]);self.assertEqual(before,self.ledger.transactions())
    def test_cross_year_ambiguity_requests_explicit_month(self):
        self.ledger.import_csv(HEADER+'2025-09-01,old,10,expense,Food,,,,\n')
        with self.assertRaisesRegex(DomainError,'YYYY-MM'):self.ledger.ask('九月比八月')
        result=self.ledger.ask('2026-08 与 2026-09 比较');self.assertEqual(result['data']['delta_fen'],10000)
    def test_chinese_savings_and_followup_preserve_constraints(self):
        result=self.ledger.ask('我想六个月存6000，房租不能减，娱乐每月至少留200。');session=result['session_id']
        self.assertEqual(result['data']['inputs']['floors'],{'Entertainment':'200'})
        changed=self.ledger.ask('我不想减少餐饮。',session)['data']
        self.assertEqual(set(changed['inputs']['locked']),{'Housing','Food'})
        self.assertEqual(changed['inputs']['target'],'6000');self.assertEqual(changed['inputs']['months'],6)
        self.assertEqual(changed['inputs']['floors'],{'Entertainment':'200'})
    def test_conversation_ids_and_model_opt_in_are_validated(self):
        for value in ('../../config','arbitrary',True):
            with self.subTest(value=value),self.assertRaises(DomainError):self.ledger.ask('spending',value)
        with self.assertRaises(DomainError):self.ledger.ask('spending',use_model='true')
    def test_model_tool_roundtrip_only_renders_program_amounts(self):
        messages=[]
        def fake(history,tools=None):
            messages.append(copy.deepcopy(history))
            if len(messages)==1:return call('compare_periods',{'first_month':'2026-08','second_month':'2026-09'})
            return {'content':json.dumps({'result_index':0,'answer':'You spent RMB 99999999','record_ids':[999999],'preferred_style':'invented','focus_categories':['Invented']})}
        before=self.ledger.transactions();result=self.ledger.ask('九月比八月',provider=fake,use_model=True)
        self.assertTrue(result['source'].startswith('model tool calling'));self.assertNotIn('99999999',result['answer'])
        self.assertEqual(result['data']['delta_fen'],10000);self.assertEqual(before,self.ledger.transactions())
        self.assertEqual(messages[1][-1]['role'],'tool');self.assertEqual(messages[1][-1]['tool_call_id'],'call_test')
    def test_model_write_tool_or_invalid_ids_falls_back(self):
        for name,args in (('delete_transactions',{}),('query_transactions',{'exclude_ids':[999999]})):
            before=self.ledger.transactions()
            result=self.ledger.ask('total spending',provider=lambda *a,**k:call(name,args),use_model=True)
            self.assertEqual(result['source'],'local fallback · deterministic');self.assertEqual(before,self.ledger.transactions())
    def test_failed_model_does_not_persist_speculative_constraints(self):
        first=self.ledger.ask('六个月存6000，房租不能减。');session=first['session_id'];count=0
        def fake(*args,**kwargs):
            nonlocal count;count+=1
            if count==1:return call('generate_savings_plans',{'target':'1','months':1,'locked':[]})
            raise TimeoutError('PRIVATE PROVIDER BODY MUST NOT LEAK')
        result=self.ledger.ask('What is my total spending?',session,provider=fake,use_model=True)
        self.assertNotIn('PRIVATE',json.dumps(result));self.assertIn('fallback',result['source'])
        follow=self.ledger.ask('我不想减少餐饮',session)
        self.assertEqual(follow['data']['inputs']['target'],'6000');self.assertEqual(follow['data']['inputs']['months'],6)
    def test_excessive_tool_calls_are_bounded(self):
        count=0
        def fake(*a,**k):
            nonlocal count;count+=1
            return call('query_transactions',{})
        result=self.ledger.ask('total spending',provider=fake,use_model=True)
        self.assertEqual(count,3);self.assertIn('fallback',result['source'])
    def test_no_model_call_without_explicit_opt_in(self):
        def forbidden(*a,**k):raise AssertionError('External provider must not be called')
        result=self.ledger.ask('total spending',provider=forbidden)
        self.assertIn('deterministic',result['source'])
    def test_model_cannot_drop_user_limits_on_followup(self):
        first=self.ledger.ask('六个月存6000，房租不能减，娱乐每月至少留200。')
        result=self.ledger.ask('我不想减少餐饮',first['session_id'],provider=lambda *a,**k:call('generate_savings_plans',{'target':6000,'months':6,'locked':[],'floors':{}}),use_model=True)
        self.assertIn('fallback',result['source']);self.assertEqual(set(result['data']['inputs']['locked']),{'Housing','Food'})
        self.assertEqual(result['data']['inputs']['floors'],{'Entertainment':'200'})
    def test_disabled_model_ignores_local_configuration(self):
        with patch.dict('os.environ',{'FINANCE_AI_DISABLE':'1'},clear=True):
            load_local_config(ROOT)
            self.assertFalse(self.ledger.state()['model_enabled'])
            result=self.ledger.ask('total spending',use_model=True)
            self.assertIn('fallback',result['source']);self.assertEqual(result['notice'],'No model is configured.')


class WorkflowHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=create_server(Path(self.tmp.name)/'http.sqlite',0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        with urllib.request.urlopen(self.base+'/api/config') as response:self.token=json.load(response)['token']
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,body=None,method=None,token=True,origin=None):
        headers={'Content-Type':'application/json'}
        if token:headers['X-Ledger-Token']=self.token
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
        with urllib.request.urlopen(req) as response:return json.load(response)
    def test_memory_endpoints_confirm_reuse_version_and_delete(self):
        self.request('/api/memory-demo',{'phase':'seed'})
        row=next(r for r in self.request('/api/state')['transactions'] if r['note']=='伙食费')
        result=self.request('/api/confirm-purpose',{'id':row['id'],'kind':'expense','category':'Food','purpose':'Meal payment','remember':True,'auto_apply':True,'match':{'note':'伙食费'},'expected_revision':1})
        memory=result['memory_id'];self.assertEqual(self.request('/api/memory-demo',{'phase':'followup'})['auto_labeled'],1)
        self.assertEqual(self.request('/api/memories/'+str(memory),{'enabled':False},method='PATCH')['version'],2)
        self.assertTrue(self.request('/api/delete-memory',{'id':memory})['deleted'])
        self.assertEqual(self.request('/api/state')['memories'],[])
    def test_plan_conversation_and_review_endpoints(self):
        self.request('/api/demo',{})
        preview=self.request('/api/plans/generate',PLAN)
        self.assertTrue(self.request('/api/plans/save',{'inputs':preview['inputs'],'style':'balanced','ledger_revision':preview['ledger_revision']})['saved'])
        first=self.request('/api/ask',{'question':'九月为什么比八月花得多？','use_model':False})
        self.assertEqual(first['data']['delta_fen'],10000)
        self.assertEqual(self.request('/api/monthly-review',{'month':'2026-09'})['month'],'2026-09')
    def test_new_mutations_require_token_and_same_origin(self):
        for path,body,method in (('/api/confirm-purpose',{'id':1},'POST'),('/api/delete-memory',{'id':1},'POST'),('/api/memories/1',{'enabled':False},'PATCH'),('/api/plans/save',{},'POST')):
            with self.subTest(path=path),self.assertRaises(urllib.error.HTTPError) as exc:self.request(path,body,method=method,token=False)
            self.assertEqual(exc.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as exc:self.request('/api/plans/generate',PLAN,origin='https://other.example')
        self.assertEqual(exc.exception.code,403)
    def test_provider_file_is_not_exposed(self):
        for path in ('/data/provider.json','/provider.json','/../data/provider.json'):
            with self.subTest(path=path),self.assertRaises(urllib.error.HTTPError) as exc:self.request(path)
            self.assertEqual(exc.exception.code,404)
        self.assertNotIn('api_key',json.dumps(self.request('/api/state')))


if __name__=='__main__':unittest.main()
