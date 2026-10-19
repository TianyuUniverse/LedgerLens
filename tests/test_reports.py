"""Real calendar boundaries, evidence, consent, model validation and drafts."""
import copy
import json
import tempfile
import unittest
import uuid
from datetime import datetime,timedelta,timezone,date
from pathlib import Path
from unittest.mock import Mock,patch
from ledger.domain import DomainError
from ledger.provider import ProviderError
from ledger.reports import bounds
from ledger.service import Ledger

class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.clock=[datetime(2026,10,19,12,tzinfo=timezone(timedelta(hours=8)))]
        self.ledger=Ledger(Path(self.tmp.name)/'test.sqlite',clock=lambda:self.clock[0]);self.reports=self.ledger.reports
    def tearDown(self):self.tmp.cleanup()
    def add(self,day='2026-10-19',amount='25.20',kind='expense',category='Food',description='午饭'):
        return self.ledger.quick_entry.save({'date':day,'description':description,'amount':amount,'kind':kind,'category':category})
    def report(self,**kw):return self.reports.generate({'kind':'month','anchor':'2026-10',**kw})
    def provider(self,change=None):
        draft=self.reports.local_coaching(self.report())
        if change:change(draft)
        return Mock(return_value={'content':json.dumps(draft,ensure_ascii=False)})
    def test_empty_data_has_null_scores_no_invented_comparison(self):
        r=self.report();self.assertTrue(all(m['score'] is None for m in r['metrics']));self.assertIsNone(r['previous_expense_fen'])
        self.assertEqual(r['expense_fen'],0);self.assertEqual(r['coaching']['tasks'][0]['action'],'import')
    def test_exact_fen_and_transfer_exclusion(self):
        self.add(amount='0.10');self.add(amount='0.20');self.add(kind='transfer',category='Transfer',amount='500');self.add(kind='income',category='Income',amount='100')
        r=self.report();self.assertEqual((r['expense_fen'],r['income_fen'],r['net_fen']),(30,10000,9970))
        self.assertEqual(sum(c['amount_fen'] for c in r['categories']),30)
        self.assertEqual(sum(p['expense_fen'] for p in r['trend']),30)
    def test_current_month_compares_equal_elapsed_calendar_days(self):
        self.add(day='2026-09-19',amount='50');self.add(day='2026-09-20',amount='1000');self.add(amount='100')
        r=self.report();self.assertEqual(r['previous_end'],'2026-09-19');self.assertEqual(r['previous_expense_fen'],5000)
    def test_week_monday_and_cross_year_and_leap_month(self):
        p=bounds('week','2026-01-01',date(2026,10,19));self.assertEqual(str(p[0]),'2025-12-29');self.assertEqual(str(p[1]),'2026-01-04')
        self.assertEqual(str(bounds('month','2024-02',date(2026,10,19))[1]),'2024-02-29')
    def test_week_cross_month_budget_uses_each_calendar_day(self):
        self.add(day='2026-09-30');self.ledger.set_budget('Food','310')
        r=self.report(kind='week',anchor='2026-10-01')
        self.assertEqual(r['budgets'][0]['limit_fen'],round(31000*(3/30+4/31)))
    def test_future_records_are_not_used_in_partial_period(self):
        self.ledger.import_csv('date,description,amount,kind,category\n2026-10-25,future food,999,expense,Food\n')
        self.add();r=self.report();self.assertEqual(r['expense_fen'],2520);self.assertTrue(r['trend'][-1]['future'])
    def test_invalid_period_and_boolean_rejected(self):
        for raw in ({'kind':'year','anchor':'2026'},{'kind':'month','anchor':'2026-13'},{'kind':'month','anchor':'2026-11'},
                    {'kind':'week','anchor':'broken'},{'kind':'month','anchor':'2026-10','use_model':'false'},{'kind':'month','anchor':'2026-10','sql':'DROP'}):
            with self.assertRaises(DomainError):self.reports.generate(raw)
    def test_goal_trajectory_uses_as_of_not_future_progress(self):
        self.clock[0]=datetime(2026,9,10,12,tzinfo=self.clock[0].tzinfo)
        g=self.ledger.adventure.create_goal({'title':'旅行','target':'1000','initial':'100','request_id':uuid.uuid4().hex})
        self.clock[0]=datetime(2026,10,19,12,tzinfo=self.clock[0].tzinfo)
        self.ledger.adventure.add_entry({'goal_id':g['id'],'kind':'deposit','amount':'300','note':'留存','request_id':uuid.uuid4().hex})
        historical=self.report(anchor='2026-09');current=self.report()
        self.assertEqual(historical['goals'][0]['balance_fen'],10000);self.assertEqual(current['goals'][0]['balance_fen'],40000)
        self.assertIsNone(historical['goals'][0]['trend'][0]['balance_fen'])
    def test_reports_do_not_grant_experience_or_rewrite_ledger(self):
        self.add();before=self.ledger.transactions();xp=self.ledger.adventure.state()['xp']
        for _ in range(2):self.report()
        self.assertEqual(self.ledger.transactions(),before);self.assertEqual(self.ledger.adventure.state()['xp'],xp)
    def test_no_external_call_without_explicit_consent(self):
        provider=self.provider();self.reports.generate({'kind':'week','anchor':'2026-10-19'},provider=provider);provider.assert_not_called()
    def test_ai_output_cached_once_and_input_omits_transaction_text(self):
        self.add(description='PRIVATE_MERCHANT');provider=self.provider()
        first=self.reports.generate({'kind':'month','anchor':'2026-10','use_model':True},provider=provider)
        second=self.reports.generate({'kind':'month','anchor':'2026-10','use_model':True},provider=provider)
        self.assertEqual(first['generation']['mode'],'ai');self.assertTrue(second['cached']);self.assertEqual(provider.call_count,1)
        self.assertNotIn('PRIVATE_MERCHANT',json.dumps(provider.call_args.args,ensure_ascii=False))
    def test_ledger_change_invalidates_ai_cache(self):
        self.add();provider=self.provider();raw={'kind':'month','anchor':'2026-10','use_model':True}
        a=self.reports.generate(raw,provider);self.add(amount='30');b=self.reports.generate(raw,provider)
        self.assertNotEqual(a['fingerprint'],b['fingerprint']);self.assertEqual(provider.call_count,2)
    def test_unknown_evidence_and_invented_numbers_fall_back(self):
        for change in (lambda d:d['insights'][0].update(fact_id='made-up'),lambda d:d['insights'][0].update(text='省下999元'),
                       lambda d:d['tasks'][0].update(action='award_xp'),lambda d:d['comic'][0].update(scene='hack')):
            r=self.reports.generate({'kind':'month','anchor':'2026-10','use_model':True},self.provider(change))
            self.assertEqual(r['generation']['mode'],'local');self.assertIn('未通过依据检查',r['generation']['notice'])
    def test_provider_failure_can_retry(self):
        provider=Mock(side_effect=ProviderError('sanitized'));raw={'kind':'month','anchor':'2026-10','use_model':True}
        self.reports.generate(raw,provider);self.reports.generate(raw,provider);self.assertEqual(provider.call_count,2)
    def test_cached_ai_survives_reload_without_another_cloud_request(self):
        self.add();provider=self.provider()
        self.reports.generate({'kind':'month','anchor':'2026-10','use_model':True},provider)
        reopened=Ledger(self.ledger.path,clock=lambda:self.clock[0]);r=reopened.reports.generate({'kind':'month','anchor':'2026-10'})
        self.assertTrue(r['cached']);self.assertEqual(r['generation']['mode'],'ai');self.assertEqual(provider.call_count,1)
    def test_fact_ids_always_resolve_to_real_records(self):
        self.add(day='2026-09-18');self.add();r=self.report();allids={t['id'] for t in self.ledger.transactions()}
        for fact in r['facts']:self.assertTrue(set(fact['record_ids'])<=allids)
    def test_scores_range_and_missing_budget_and_income_remain_null(self):
        self.add();r=self.report();byid={m['id']:m['score'] for m in r['metrics']}
        self.assertIsNone(byid['budget']);self.assertIsNone(byid['buffer']);self.assertEqual(byid['clarity'],100)
        self.assertTrue(all(m['score'] is None or 0<=m['score']<=100 for m in r['metrics']))
    def test_sentence_draft_exact_amount_and_yesterday_no_save(self):
        draft=self.ledger.quick_entry.draft({'text':'昨天食堂午饭25.20元'})
        self.assertEqual(draft['record']['date'],'2026-10-18');self.assertEqual(draft['record']['amount'],'25.20');self.assertFalse(draft['saved'])
        self.assertEqual(self.ledger.transactions(),[])
    def test_multiple_amounts_negative_future_rejected(self):
        for text in ('午饭25元晚饭30元','午饭-1元','2026-10-20 午饭25元','午饭0.001元','没有金额'):
            with self.assertRaises(DomainError):self.ledger.quick_entry.draft({'text':text})
    def test_manual_save_confirmed_and_duplicate_does_not_award_again(self):
        first=self.add(category='Other');xp=self.ledger.adventure.state()['xp'];second=self.add(category='Other')
        self.assertTrue(first['saved']);self.assertFalse(second['saved']);self.assertEqual(self.ledger.adventure.state()['xp'],xp)
        row=self.ledger.transactions()[0];self.assertEqual(row['category_source'],'human');self.assertEqual(row['review_status'],'confirmed')
    def test_ai_draft_cannot_change_parsed_date_or_amount(self):
        provider=Mock(return_value={'content':json.dumps({'kind':'expense','category':'Food','description':'食堂午饭'})})
        draft=self.ledger.quick_entry.draft({'text':'昨天食堂午饭25元','use_model':True},provider)
        self.assertEqual(draft['mode'],'ai');self.assertEqual(draft['record']['amount'],'25');self.assertEqual(self.ledger.transactions(),[])
    def test_invalid_ai_entry_falls_back(self):
        provider=Mock(return_value={'content':'{"kind":"expense","category":"Food","description":"test","amount":999}'})
        draft=self.ledger.quick_entry.draft({'text':'食堂午饭25元','use_model':True},provider)
        self.assertEqual(draft['mode'],'local');self.assertEqual(draft['record']['amount'],'25')

if __name__=='__main__':unittest.main()
