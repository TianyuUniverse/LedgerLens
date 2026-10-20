import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from app import create_server
from ledger.domain import DomainError
from ledger.service import Ledger


CSV = ('date,description,amount,kind,category,counterparty,note\n'
       '2026-09-10,食堂午餐,20.25,expense,Food,示例食堂,伙食费\n'
       '2026-09-11,电费,30,expense,Utilities,示例舍友,电费\n'
       '2026-09-12,兼职,100,income,Income,,\n'
       '2026-09-13,账户划转,9,transfer,Transfer,,\n')


class TransactionDeleteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Ledger(Path(self.tmp.name) / 'delete.sqlite', clock=lambda:datetime(2026,10,20,tzinfo=timezone.utc))
        self.ledger.import_csv(CSV)

    def tearDown(self):
        self.tmp.cleanup()

    def delete(self, record_id=1):
        row = next(r for r in self.ledger.transactions() if r['id'] == record_id)
        return self.ledger.delete_transaction({'id':record_id, 'expected_revision':row['revision']})

    def test_exact_bill_removed_and_totals_budgets_updated_without_changing_goals(self):
        self.ledger.set_budget('Food', '50')
        self.ledger.adventure.create_goal({'title':'旅行', 'target':'1000', 'initial':'50', 'request_id':uuid.uuid4().hex})
        goals = self.ledger.adventure.state()['goals']
        others = [r for r in self.ledger.transactions() if r['id'] != 1]
        self.assertTrue(self.delete()['deleted'])
        self.assertEqual(self.ledger.transactions(), others)
        state = self.ledger.state()
        self.assertEqual(state['overview']['expense_fen'], 3000)
        self.assertEqual(state['overview']['income_fen'], 10000)
        self.assertEqual(state['overview']['transfer_fen'], 900)
        self.assertEqual(state['overview']['net_fen'], 7000)
        self.assertEqual(state['budgets'][0]['spent_fen'], 0)
        self.assertEqual(state['adventure']['goals'], goals)
        audit = next(a for a in state['audit'] if a['action'] == 'transaction_delete')
        self.assertEqual(json.loads(audit['details'])['before']['amount_fen'], 2025)

    def test_stale_revision_is_rejected_without_deletion(self):
        self.ledger.edit(1, {'amount':'21'})
        before = self.ledger.transactions()
        with self.assertRaisesRegex(DomainError, '已修改'):
            self.ledger.delete_transaction({'id':1, 'expected_revision':1})
        self.assertEqual(self.ledger.transactions(), before)

    def test_invalid_or_missing_identity_cannot_delete_any_bill(self):
        before = self.ledger.transactions()
        for raw in ({}, {'id':1}, {'id':True,'expected_revision':1}, {'id':1,'expected_revision':True},
                    {'id':'1','expected_revision':1}, {'id':1,'expected_revision':0},
                    {'id':1,'expected_revision':1,'all':True}, {'id':999,'expected_revision':1}):
            with self.subTest(raw=raw), self.assertRaises(DomainError):
                self.ledger.delete_transaction(raw)
        self.assertEqual(self.ledger.transactions(), before)

    def test_deleted_id_is_not_reused_and_same_file_can_be_imported_again(self):
        old_max = max(r['id'] for r in self.ledger.transactions())
        self.delete(4)
        reopened = Ledger(self.ledger.path)
        self.assertEqual(reopened.import_csv(CSV)['inserted'], 1)
        self.assertGreater(max(r['id'] for r in reopened.transactions()), old_max)
        self.assertEqual(reopened.overview()['transfer_fen'], 900)

    def test_second_delete_cannot_affect_other_rows(self):
        self.delete()
        before = self.ledger.transactions()
        with self.assertRaisesRegex(DomainError, '已不存在'):
            self.ledger.delete_transaction({'id':1,'expected_revision':1})
        self.assertEqual(self.ledger.transactions(), before)

    def test_deleting_all_rows_leaves_valid_empty_state(self):
        for record_id in (1,2,3,4):
            self.delete(record_id)
        state = self.ledger.state()
        self.assertEqual(state['transactions'], [])
        self.assertEqual(state['overview']['expense_fen'], 0)
        self.assertIsNone(state['plan'])

    def test_derived_results_and_only_deleted_bill_drafts_are_invalidated(self):
        first = self.ledger.setup_chat.chat({'mode':'purpose','message':'这是餐饮费','use_model':False,'context':{'record_id':1}})
        other = self.ledger.setup_chat.chat({'mode':'purpose','message':'这是电费','use_model':False,'context':{'record_id':2}})
        goal = self.ledger.setup_chat.chat({'mode':'goal','message':'想存1000元','use_model':False})
        with self.ledger.connection() as con:
            con.execute("INSERT OR REPLACE INTO settings VALUES('generated_plan','{}')")
            con.execute("INSERT OR REPLACE INTO settings VALUES('plan',?)", (json.dumps({'target':'1000','current':'0','months':6}),))
        self.ledger.reports.generate({'kind':'month','anchor':'2026-09','use_model':False})
        self.delete()
        with self.assertRaises(DomainError):
            self.ledger.setup_chat.commit({'conversation_id':first['conversation_id'],'revision':first['revision']})
        self.assertEqual(self.ledger.setup_chat.load(other['conversation_id'])['mode'], 'purpose')
        self.assertEqual(self.ledger.setup_chat.load(goal['conversation_id'])['mode'], 'goal')
        with self.ledger.connection() as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM period_reports').fetchone()[0], 0)
            self.assertIsNone(con.execute("SELECT value FROM settings WHERE key='generated_plan'").fetchone())
            self.assertIsNotNone(con.execute("SELECT value FROM settings WHERE key='plan'").fetchone())

    def test_memory_survives_and_can_be_edited_and_reused_without_source_bill(self):
        mid = self.ledger.memory.confirm(1, {'kind':'expense','category':'Food','purpose':'食堂伙食',
            'match':{'counterparty':'示例食堂','note':'伙食费'},'remember':True,'auto_apply':True})['memory_id']
        memory = self.ledger.memory.list()
        self.delete()
        self.assertEqual(self.ledger.memory.list(), memory)
        edit = self.ledger.setup_chat.chat({'mode':'purpose','message':'用途改成校园伙食费','use_model':False,
            'context':{'record_id':1,'memory_id':mid}})
        self.ledger.setup_chat.commit({'conversation_id':edit['conversation_id'],'revision':edit['revision']})
        self.assertEqual(self.ledger.memory.list()[0]['version'], 2)
        result = self.ledger.import_csv('date,description,amount,kind,counterparty,note\n2026-09-14,充值,18,expense,示例食堂,伙食费\n')
        self.assertEqual(result['auto_labeled'], 1)
        with self.assertRaises(DomainError):
            self.ledger.setup_chat.initial('purpose', {'record_id':1})
        with self.assertRaises(DomainError):
            self.ledger.setup_chat.initial('purpose', {'record_id':2,'memory_id':mid})

    def test_failed_audit_rolls_back_bill_and_cache_changes(self):
        before = self.ledger.transactions()
        with self.ledger.connection() as con:
            con.execute("INSERT OR REPLACE INTO settings VALUES('generated_plan','{}')")
        with patch.object(self.ledger, 'audit', side_effect=RuntimeError('injected failure')):
            with self.assertRaises(RuntimeError):
                self.delete()
        self.assertEqual(self.ledger.transactions(), before)
        with self.ledger.connection() as con:
            self.assertIsNotNone(con.execute("SELECT value FROM settings WHERE key='generated_plan'").fetchone())


class TransactionDeleteHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = create_server(Path(self.tmp.name) / 'http.sqlite', 0)
        self.server.ledger.import_csv(CSV)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        with urllib.request.urlopen(self.base + '/api/config') as response:
            self.token = json.load(response)['token']

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.tmp.cleanup()

    def request(self, raw, token=True, origin=None):
        headers = {'Content-Type':'application/json'}
        if token: headers['X-Ledger-Token'] = self.token
        if origin: headers['Origin'] = origin
        req = urllib.request.Request(self.base + '/api/transactions/delete', json.dumps(raw).encode(), headers)
        with urllib.request.urlopen(req) as response:
            return json.load(response)

    def test_route_deletes_exact_record_and_rejects_stale_state(self):
        self.server.ledger.edit(1, {'amount':'22'})
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.request({'id':1,'expected_revision':1})
        self.assertEqual(err.exception.code, 400)
        self.assertTrue(self.request({'id':1,'expected_revision':2})['deleted'])
        self.assertEqual(len(self.server.ledger.transactions()), 3)

    def test_route_requires_token_and_same_origin(self):
        for kwargs in ({'token':False}, {'origin':'https://other.example'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(urllib.error.HTTPError) as err:
                self.request({'id':1,'expected_revision':1}, **kwargs)
            self.assertEqual(err.exception.code, 403)
        self.assertEqual(len(self.server.ledger.transactions()), 4)


if __name__ == '__main__':
    unittest.main()
