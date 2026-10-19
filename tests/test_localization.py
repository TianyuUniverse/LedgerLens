"""Chinese input/export interoperability and presentation boundaries."""
import csv
import io
import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from app import create_server
from ledger.domain import DomainError
from ledger.localization import chinese_csv, public_payload
from ledger.service import Ledger

ROOT=Path(__file__).resolve().parents[1]
CHINESE='日期,交易描述,金额,收支类型,消费分类,交易对方,备注,原始类型,原始分类\n2026-09-01,每月生活费,1000,收入,收入,家人,,收入,收入\n2026-09-02,大学食堂,20.25,支出,餐饮,学校,伙食费,支出,教育\n2026-09-03,账户调拨,100,转账,转账,本人账户,,转账,转账\n'


class ChineseDomainTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.ledger=Ledger(Path(self.tmp.name)/'zh.sqlite')
    def tearDown(self):self.tmp.cleanup()
    def test_chinese_headers_kinds_and_categories_keep_financial_meaning(self):
        self.ledger.import_csv(CHINESE);view=self.ledger.overview()
        self.assertEqual((view['income_fen'],view['expense_fen'],view['transfer_fen']),(100000,2025,10000))
        meal=next(r for r in self.ledger.transactions() if r['description']=='大学食堂')
        self.assertEqual((meal['kind'],meal['category'],meal['source_category']),('expense','Food','教育'))
    def test_chinese_export_roundtrip_and_duplicate_detection(self):
        self.ledger.import_csv(CHINESE);export=chinese_csv(self.ledger.transactions()).decode('utf-8-sig')
        self.assertIn('日期,交易描述,金额,收支类型,消费分类',export)
        self.assertNotIn('expense',export);self.assertNotIn('Food',export)
        self.assertEqual(self.ledger.import_csv(export)['duplicates'],3)
    def test_mixed_alias_duplicate_headers_rejected_atomically(self):
        with self.assertRaises(DomainError):self.ledger.import_csv('date,日期,description,amount,kind\n2026-09-01,2026-09-01,ok,1,expense\n')
        self.assertEqual(self.ledger.transactions(),[])
    def test_export_preserves_existing_english_record_identity(self):
        self.ledger.import_csv((ROOT/'samples/transactions.csv').read_text(encoding='utf-8'))
        exported=chinese_csv(self.ledger.transactions()).decode('utf-8-sig')
        self.assertIn('Taobao clothes September',exported)
        self.assertEqual(self.ledger.import_csv(exported)['duplicates'],30)
    def test_translation_preserves_raw_identifiers_and_custom_user_text(self):
        raw={'description':'Original English merchant','purpose':'My own English purpose','category':'Food','kind':'expense',
             'amount_fen':2025,'decision_reason':'Manual correction','assumption':'No records. Import data first.'}
        translated=public_payload(raw)
        for key in ('description','purpose','category','kind','amount_fen'):self.assertEqual(translated[key],raw[key])
        self.assertEqual(translated['decision_reason'],'用户手动修正')
    def test_all_finance_result_types_render_in_chinese(self):
        self.ledger.import_csv((ROOT/'samples/transactions.csv').read_text(encoding='utf-8'))
        for question in ('What is my total spending?','我的餐饮支出是多少？','九月为什么比八月花得多？','六个月存6000，娱乐每月至少留200。','九月消费复盘'):
            with self.subTest(question=question):
                result=self.ledger.ask(question,locale='zh')
                self.assertTrue(result['supported']);self.assertFalse(re.search(r'[A-Za-z]',result['answer']),result['answer'])
        self.assertIn('10,200.00',self.ledger.ask('total spending',locale='zh')['answer'])
    def test_chinese_export_still_escapes_spreadsheet_formulas(self):
        self.ledger.import_csv('date,description,amount,kind,category,counterparty,note\n2026-09-01,=danger(),1,expense,Food,+payee,@note\n')
        exported=list(csv.DictReader(io.StringIO(chinese_csv(self.ledger.transactions()).decode('utf-8-sig'))))[0]
        self.assertEqual(exported['交易描述'],"'=danger()");self.assertEqual(exported['交易对方'],"'+payee");self.assertEqual(exported['备注'],"'@note")


class ChineseHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.server=create_server(Path(cls.tmp.name)/'http.sqlite',0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
        with urllib.request.urlopen(cls.base+'/api/config') as r:cls.token=json.load(r)['token']
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
    def request(self,path,body=None):
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type':'application/json','X-Ledger-Token':self.token,'Accept-Language':'zh-CN'})
        return urllib.request.urlopen(req)
    def test_sample_download_is_chinese_and_importable(self):
        with self.request('/sample.csv') as response:text=response.read().decode('utf-8-sig')
        self.assertIn('9月淘宝服饰',text);self.assertIn('收支类型',text)
        with self.request('/api/import',{'csv':text}) as response:self.assertEqual(json.load(response)['inserted'],30)
        with self.request('/api/export?lang=zh') as response:export=response.read().decode('utf-8-sig')
        self.assertIn('消费分类',export);self.assertNotIn('expense',export)
    def test_invalid_import_and_model_disclosure_are_chinese(self):
        with self.assertRaises(urllib.error.HTTPError) as error:self.request('/api/import',{'csv':'date,description,amount,kind\n2026-02-30,bad,1,expense\n'})
        response=json.load(error.exception)
        self.assertIn('未保存任何账单',response['error']);self.assertIn('第 2 行',response['error']);self.assertNotIn('Row',response['error'])
        with self.request('/api/config') as response:config=json.load(response)
        self.assertEqual(config['labels']['Food'],'餐饮')


if __name__=='__main__':unittest.main()
