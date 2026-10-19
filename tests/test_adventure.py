"""Goal allocation arithmetic, earned rewards, idempotency and HTTP boundaries."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from app import create_server
from ledger.domain import DomainError
from ledger.service import Ledger

ROOT=Path(__file__).resolve().parents[1]
BASE=(ROOT/'samples/transactions.csv').read_text(encoding='utf-8')
SEED=(ROOT/'samples/memory_seed.csv').read_text(encoding='utf-8')


class AdventureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'game.sqlite'
        self.clock=[datetime(2026,10,19,10,tzinfo=timezone(timedelta(hours=8)))]
        self.ledger=Ledger(self.path,clock=lambda:self.clock[0]);self.game=self.ledger.adventure
    def tearDown(self):self.tmp.cleanup()
    def create(self,**changes):
        return self.game.create_goal({'title':'旅行基金','target':'6000','initial':'0','deadline':'2027-04-19','request_id':uuid.uuid4().hex,**changes})['id']
    def entry(self,goal,amount,kind='deposit',**changes):
        return self.game.add_entry({'goal_id':goal,'amount':amount,'kind':kind,'note':'每一步','request_id':uuid.uuid4().hex,**changes})
    def goal(self,goal_id):return next(g for g in self.game.state()['goals'] if g['id']==goal_id)
    def xp(self):return self.game.state()['xp']

    def test_fresh_state_and_reads_do_not_earn_rewards(self):
        before=self.game.state()
        for _ in range(3):self.ledger.state()
        self.assertEqual(self.game.state(),before);self.assertEqual(before['level'],1);self.assertEqual(before['xp'],0)
    def test_create_goal_stores_original_money_and_awards_first_goal_once(self):
        goal=self.create(initial='0.30');self.create(title='备用金')
        self.assertEqual(self.goal(goal)['balance_fen'],30);self.assertEqual(self.xp(),20)
        self.assertEqual(self.ledger.transactions(),[])
    def test_goal_creation_request_replay_and_payload_conflict(self):
        raw={'title':'旅行','target':'100','initial':0,'deadline':'2026-10-20','request_id':uuid.uuid4().hex}
        first=self.game.create_goal(raw);self.clock[0]+=timedelta(days=2)
        repeat=self.game.create_goal(raw)
        self.assertEqual(first['id'],repeat['id']);self.assertTrue(repeat['replayed']);self.assertEqual(self.xp(),20)
        with self.assertRaises(DomainError):self.game.create_goal({**raw,'title':'另一个目标'})
    def test_goal_limits_archive_and_restore_preserve_history(self):
        goals=[self.create() for _ in range(3)]
        with self.assertRaises(DomainError):self.create()
        self.game.archive_goal({'goal_id':goals[0],'archived':True});self.create()
        with self.assertRaises(DomainError):self.game.archive_goal({'goal_id':goals[0],'archived':False})
        self.game.archive_goal({'goal_id':goals[1],'archived':True});self.game.archive_goal({'goal_id':goals[0],'archived':False})
        self.assertFalse(self.goal(goals[0])['archived'])
    def test_goal_input_boundaries_are_atomic(self):
        for change in ({'target':'0'},{'target':'NaN'},{'initial':'6001'},{'deadline':'2026-10-18'},{'deadline':False},{'title':' '},{'request_id':'bad'},{'xp':1000}):
            with self.subTest(change=change),self.assertRaises(DomainError):self.create(**change)
        self.assertEqual(self.game.state()['goals'],[]);self.assertEqual(self.xp(),0)
    def test_exact_deposit_withdraw_and_source_ledger_unchanged(self):
        self.ledger.import_csv(BASE);before=self.ledger.transactions();goal=self.create(target='1',initial='0.10')
        self.entry(goal,'0.20');self.entry(goal,'0.10','withdraw')
        self.assertEqual(self.goal(goal)['balance_fen'],20);self.assertEqual(before,self.ledger.transactions())
    def test_milestone_rewards_only_once_after_withdraw_and_redeposit(self):
        goal=self.create();self.entry(goal,'1500');self.assertEqual(self.xp(),50)
        self.entry(goal,'1000','withdraw');self.entry(goal,'1000')
        self.assertEqual(self.xp(),50);self.assertEqual(self.goal(goal)['progress_pct'],25)
        self.entry(goal,'4500');self.assertEqual(self.xp(),220)
        self.assertTrue(self.goal(goal)['complete']);self.assertEqual(self.goal(goal)['remaining_fen'],0)
    def test_initial_progress_does_not_award_milestone_experience(self):
        goal=self.create(initial='3000');self.assertEqual(self.xp(),20)
        self.assertTrue(all(m['collected'] for m in self.goal(goal)['milestones'][:2]))
        self.entry(goal,'1000','withdraw');self.entry(goal,'1000');self.assertEqual(self.xp(),20)
        self.entry(goal,'1500');self.assertEqual(self.xp(),70)
    def test_invalid_withdraw_and_closed_goal_cannot_change_balance(self):
        goal=self.create();self.entry(goal,'10')
        with self.assertRaises(DomainError):self.entry(goal,'10.01','withdraw')
        self.game.archive_goal({'goal_id':goal,'archived':True})
        with self.assertRaises(DomainError):self.entry(goal,'1')
        self.assertEqual(self.goal(goal)['balance_fen'],1000)
    def test_concurrent_retry_records_one_allocation_and_one_reward(self):
        goal=self.create();key=uuid.uuid4().hex
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.entry(goal,'1500',request_id=key),range(2)))
        self.assertEqual(self.goal(goal)['balance_fen'],150000);self.assertEqual(self.xp(),50)
        self.assertEqual(sum(r['replayed'] for r in results),1);self.assertEqual(len(self.game.state()['entries']),1)
    def test_retry_of_allocation_after_archiving_is_not_applied_twice(self):
        goal=self.create();key=uuid.uuid4().hex;self.entry(goal,'10',request_id=key)
        self.game.archive_goal({'goal_id':goal,'archived':True})
        self.assertTrue(self.entry(goal,'10',request_id=key)['replayed'])
        with self.assertRaises(DomainError):self.entry(goal,'11',request_id=key)
    def test_daily_milestone_cap_across_multiple_goals(self):
        first=self.create(target='10');second=self.create(target='10')
        self.entry(first,'10');self.entry(second,'10')
        self.assertEqual(self.xp(),220);self.assertTrue(self.goal(second)['complete'])
        self.assertTrue(all(m['collected'] for m in self.goal(second)['milestones']))
    def test_operation_rolls_back_allocations_rewards_and_audit_together(self):
        goal=self.create();before=self.game.state()
        with patch.object(self.ledger,'audit',side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):self.entry(goal,'6000')
        self.assertEqual(before,self.game.state())
    def test_import_reward_requires_new_rows_not_duplicate_clicks(self):
        self.ledger.import_csv(BASE);first=self.xp();self.assertEqual(first,30)
        self.ledger.import_csv(BASE);self.clock[0]+=timedelta(days=1);self.ledger.import_csv(BASE)
        self.assertEqual(self.xp(),first);self.assertFalse(self.game.state()['daily_quests'][0]['complete'])
    def test_review_and_memory_reward_require_real_confirmation(self):
        self.ledger.import_csv(SEED)
        record=next(r for r in self.ledger.transactions() if r['note']=='伙食费')
        before=self.xp()
        raw={'kind':'expense','category':'Food','purpose':'校园伙食费','remember':True,'auto_apply':True,'match':{'note':'伙食费'}}
        self.ledger.memory.confirm(record['id'],raw);self.assertEqual(self.xp()-before,60)
        first=self.xp();self.ledger.memory.confirm(record['id'],raw);self.assertEqual(self.xp(),first)
    def test_monthly_reflection_requires_data_and_daily_reward_is_unique(self):
        with self.assertRaises(DomainError):self.game.reflect({'month':'2026-09','note':'先整理账单再制定计划'})
        self.ledger.import_csv(BASE);before=self.xp()
        self.game.reflect({'month':'2026-09','note':'本月购物增加，下周列好采购清单。'})
        self.assertEqual(self.xp()-before,45)
        self.game.reflect({'month':'2026-09','note':'本月交通稳定，继续保持合理预算。'})
        self.assertEqual(self.xp()-before,45);self.assertIn('交通',self.game.state()['reflection']['note'])
    def test_local_midnight_resets_quests_and_streak_tracks_action_dates(self):
        self.clock[0]=datetime(2026,10,19,15,59,tzinfo=timezone.utc)
        self.ledger.import_csv(BASE);self.assertEqual(self.game.state()['today'],'2026-10-19')
        self.clock[0]+=timedelta(minutes=2)
        self.assertEqual(self.game.state()['today'],'2026-10-20');self.assertFalse(self.game.state()['daily_quests'][0]['complete'])
        self.assertEqual(self.game.state()['streak'],1)
        self.game.reflect({'month':'2026-09','note':'今天重新确认每月购物预算。'});self.assertEqual(self.game.state()['streak'],2)
    def test_weekly_three_distinct_days_and_no_penalty_after_gap(self):
        self.ledger.import_csv(BASE)
        for _ in range(2):
            self.clock[0]+=timedelta(days=1);self.game.reflect({'month':'2026-09','note':'今天认真核对消费并保持预算。'})
        state=self.game.state();self.assertEqual(state['weekly_days'],3);self.assertTrue(state['weekly_complete'])
        before=state['xp'];self.game.reflect({'month':'2026-09','note':'修改心得也不会重复获得奖励。'});self.assertEqual(self.xp(),before)
        self.clock[0]+=timedelta(days=3);self.assertEqual(self.game.state()['streak'],0);self.assertEqual(self.xp(),before)
    def test_locked_theme_rejects_forged_level_and_unlocks_from_actual_xp(self):
        with self.assertRaises(DomainError):self.game.set_theme({'theme':'space'})
        with self.assertRaises(DomainError):self.game.set_theme({'theme':'ocean','xp':10000})
        goal=self.create();self.entry(goal,'6000');self.assertGreaterEqual(self.game.state()['level'],2)
        self.game.set_theme({'theme':'ocean'});self.assertEqual(self.game.state()['theme'],'ocean')
    def test_reopening_database_keeps_goals_levels_and_no_migration_bonus(self):
        goal=self.create();self.entry(goal,'1500');before=self.game.state()
        reopened=Ledger(self.path,clock=lambda:self.clock[0])
        self.assertEqual(before,reopened.adventure.state())
    def test_read_only_assistant_and_review_tools_do_not_earn_experience(self):
        self.ledger.import_csv(BASE);before=self.xp()
        self.ledger.tools.monthly_review({'month':'2026-09'});self.ledger.ask('九月消费复盘')
        self.assertEqual(self.xp(),before)


class AdventureHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.server=create_server(Path(cls.tmp.name)/'http.sqlite',0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        with urllib.request.urlopen(cls.base+'/api/config') as response:cls.token=json.load(response)['token']
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
    def request(self,path,body=None,token=True,origin=None):
        headers={'Content-Type':'application/json','Accept-Language':'zh-CN'}
        if token:headers['X-Ledger-Token']=self.token
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with urllib.request.urlopen(req) as response:return json.load(response)
    def test_goal_workflow_and_state(self):
        goal=self.request('/api/adventure/goals',{'title':'中文目标','target':'100','initial':'0','request_id':uuid.uuid4().hex})
        self.request('/api/adventure/entries',{'goal_id':goal['id'],'kind':'deposit','amount':'25','request_id':uuid.uuid4().hex})
        current=self.request('/api/state')['adventure']
        self.assertEqual(current['goals'][0]['progress_pct'],25);self.assertEqual(current['goals'][0]['balance_fen'],2500)
    def test_new_routes_require_session_and_same_origin(self):
        for route in ('goals','entries','archive','reflect','theme'):
            with self.subTest(route=route),self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/adventure/'+route,{},token=False)
            self.assertEqual(error.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/adventure/theme',{'theme':'forest'},origin='https://other.example')
        self.assertEqual(error.exception.code,403)
    def test_client_cannot_claim_quest_or_supply_xp(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/adventure/claim',{'quest':'import','xp':99999})
        self.assertEqual(error.exception.code,404)
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/adventure/goals',{'title':'伪造经验','target':100,'request_id':uuid.uuid4().hex,'xp':99999})
        self.assertEqual(error.exception.code,400)


if __name__=='__main__':unittest.main()
