import tempfile,unittest,json
from unittest.mock import Mock
from pathlib import Path
from datetime import datetime,timedelta,timezone
from ledger.service import Ledger
from ledger.trials import CASES
from ledger.domain import DomainError

class TrialTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.ledger=Ledger(Path(self.tmp.name)/'test.sqlite',clock=lambda:datetime(2026,10,19,12,tzinfo=timezone(timedelta(hours=8))))
    def tearDown(self):self.tmp.cleanup()
    def start(self):return self.ledger.trials.start({'use_model':False})
    def answer(self,r,correct=True):
        case=next(c for c in CASES if c['id']==r['question']['id']);choice=case['answer'] if correct else next(c for c in case['choices'] if c!=case['answer'])
        return self.ledger.trials.answer({'day':r['day'],'position':r['position'],'choice':choice})
    def test_start_does_not_reward_or_expose_answer(self):
        r=self.start();self.assertEqual(self.ledger.adventure.state()['xp'],0);self.assertNotIn('answer',r['question']);self.assertEqual(r['position'],0)
    def test_wrong_answer_keeps_position_and_no_experience(self):
        r=self.answer(self.start(),False);self.assertFalse(r['feedback']['correct']);self.assertEqual(r['position'],0);self.assertEqual(self.ledger.adventure.state()['xp'],0)
    def test_three_stages_award_once_and_persist(self):
        r=self.start()
        for _ in range(3):r=self.answer(r)
        self.assertTrue(r['complete']);self.assertEqual(self.ledger.adventure.state()['xp'],15)
        for _ in range(3):self.assertTrue(self.start()['complete'])
        self.assertEqual(self.ledger.adventure.state()['xp'],15);self.assertEqual(self.ledger.transactions(),[])
    def test_old_or_invented_step_cannot_claim_reward(self):
        r=self.start()
        for raw in ({'day':r['day'],'position':3,'choice':'Food'},{'day':'2026-10-18','position':0,'choice':'Food'},{'day':r['day'],'position':0,'choice':'award_xp'}):
            with self.assertRaises(DomainError):self.ledger.trials.answer(raw)
        self.assertEqual(self.ledger.adventure.state()['xp'],0)
    def test_ai_can_upgrade_local_stories_without_resetting_progress_or_extra_calls(self):
        first=self.answer(self.start());provider=Mock(return_value={'content':json.dumps({'stories':['小狐沿着路边的线索，决定先看看这张账单的实际用途。']*3},ensure_ascii=False)})
        upgraded=self.ledger.trials.start({'use_model':True},provider)
        self.assertEqual(upgraded['position'],first['position']);self.assertEqual(upgraded['source'],'ai')
        self.ledger.trials.start({'use_model':True},provider);self.assertEqual(provider.call_count,1);self.assertEqual(self.ledger.adventure.state()['xp'],0)

if __name__=='__main__':unittest.main()
