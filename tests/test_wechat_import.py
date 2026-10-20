import base64
import io
import tempfile
import unittest
import zipfile
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path
from xml.sax.saxutils import escape
from ledger.service import Ledger
from ledger.domain import DomainError
from app import create_server

HEADERS=['交易时间','交易类型','交易对方','商品','收/支','金额(元)','支付方式','当前状态','交易单号','商户单号','备注']
def payment(order='order-001',**patch):
    row=dict(zip(HEADERS,['2026-09-01 12:00:00','商户消费','示例校园食堂','校园账户充值','支出','25.20','零钱','支付成功',order,'/','伙食费']))
    return [patch.get(k,v) for k,v in row.items()]

def workbook(rows,headers=HEADERS,formula=False):
    """A minimal synthetic OOXML transport fixture, without personal bill data."""
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    data=[['微信支付账单明细'],*([[]]*16),headers,*rows];xml=[]
    for i,row in enumerate(data,1):
        cells=[]
        for j,v in enumerate(row):
            ref=chr(65+j)+str(i);isnum=isinstance(v,(int,float));typ='' if isnum else ' t="inlineStr"'
            value=f'<v>{v}</v>' if isnum else '<is><t>'+escape(str(v))+'</t></is>'
            cells.append(f'<c r="{ref}"{typ}>{"<f>1+1</f>" if formula and i==19 and j==5 else ""}{value}</c>')
        xml.append(f'<row r="{i}">'+''.join(cells)+'</row>')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData>'+''.join(xml)+'</sheetData></worksheet>')
    return out.getvalue()

def upload(rows,**kwargs):return {'filename':'微信示例.xlsx','data':base64.b64encode(workbook(rows,**kwargs)).decode()}

class WechatImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.ledger=Ledger(Path(self.tmp.name)/'bill.sqlite');self.importer=self.ledger.wechat_import
    def tearDown(self):self.tmp.cleanup()
    def save(self,raw):return self.importer.commit({**raw,'digest':self.importer.preview(raw)['digest']})
    def test_detects_wechat_header_after_metadata_and_only_previews(self):
        p=self.importer.preview(upload([payment()]));self.assertEqual(p['header_row'],18);self.assertEqual(p['new_count'],1);self.assertEqual(p['expense_fen'],2520);self.assertEqual(self.ledger.transactions(),[])
    def test_exact_amounts_and_stable_order_ids_avoid_merging_real_payments(self):
        raw=upload([payment('a'),payment('b')]);self.assertEqual(self.save(raw)['inserted'],2);self.assertEqual(self.save(raw)['duplicates'],2);self.assertEqual(sum(r['amount_fen'] for r in self.ledger.transactions()),5040)
    def test_transfer_to_roommate_is_expense_and_own_account_transfer_excluded(self):
        raw=upload([payment('a',交易类型='转账',商品='转账给舍友',备注='电费和空调费'),payment('b',交易类型='零钱提现',商品='/',备注='/',**{'收/支':'/'})])
        p=self.importer.preview(raw);self.assertEqual(p['expense_fen'],2520);self.assertEqual(p['transfer_fen'],2520);self.save(raw)
        self.assertEqual(next(r for r in self.ledger.transactions() if r['external_id']=='a')['category'],'Utilities')
    def test_refunds_not_counted_as_new_income_and_partial_refunds_use_net(self):
        raw=upload([payment('a',当前状态='已全额退款'),payment('b',交易类型='商户-退款',**{'收/支':'收入'}),payment('c',当前状态='已退款(￥5.20)')])
        p=self.importer.preview(raw);self.assertEqual(p['excluded_count'],2);self.assertEqual(p['income_fen'],0);self.assertEqual(p['expense_fen'],2000);self.assertEqual(p['partial_refund_fen'],520)
    def test_memory_applies_on_next_import_using_clean_context(self):
        self.save(upload([payment('a')]));r=self.ledger.transactions()[0]
        self.ledger.memory.confirm(r['id'],{'kind':'expense','category':'Food','purpose':'校园伙食','match':{'counterparty':'示例校园食堂','note':'伙食费'},'remember':True,'auto_apply':True})
        self.assertEqual(self.save(upload([payment('b')]))['auto_labeled'],1)
    def test_reimport_after_human_correction_remains_duplicate(self):
        raw=upload([payment()]);self.save(raw);r=self.ledger.transactions()[0];self.ledger.edit(r['id'],{'category':'Other'});self.assertEqual(self.save(raw)['duplicates'],1);self.assertEqual(self.ledger.transactions()[0]['category'],'Other')
    def test_changed_status_on_reimport_is_reported_before_write(self):
        self.save(upload([payment()]));changed=upload([payment(当前状态='已退款(￥5.20)')]);self.assertEqual(len(self.importer.preview(changed)['conflicts']),1)
        with self.assertRaises(DomainError):self.save(changed)
        self.assertEqual(self.ledger.transactions()[0]['amount_fen'],2520)
    def test_later_full_refund_is_reported_even_when_row_is_excluded(self):
        self.save(upload([payment()]));changed=upload([payment(当前状态='已全额退款')]);p=self.importer.preview(changed)
        self.assertEqual(p['new_count'],0);self.assertEqual(len(p['conflicts']),1)
        with self.assertRaises(DomainError):self.save(changed)
    def test_missing_header_and_formula_and_invalid_file_are_rejected(self):
        for raw in (upload([payment()],headers=['wrong']),upload([payment()],formula=True),{'filename':'bad.xlsx','data':base64.b64encode(b'bad').decode()}):
            with self.subTest(raw=raw['filename']):
                with self.assertRaises(DomainError):self.importer.preview(raw)
        self.assertEqual(self.ledger.transactions(),[])
    def test_invalid_row_rejects_entire_file(self):
        with self.assertRaises(DomainError):self.save(upload([payment('a'),payment('b',**{'金额(元)':'25.201'})]))
        self.assertEqual(self.ledger.transactions(),[])
    def test_numeric_cells_support_excel_serial_dates_and_roundoff(self):
        p=self.importer.preview(upload([payment(**{'交易时间':46266.5,'金额(元)':25.199999999999999})]));self.assertEqual(p['expense_fen'],2520);self.assertEqual(p['preview_rows'][0]['occurred_at'],'2026-09-01 12:00:00')
    def test_ambiguous_payee_is_not_automatically_education(self):
        self.save(upload([payment(交易对方='示例大学',商品='校园账户充值',备注='/')]));r=self.ledger.transactions()[0];self.assertEqual(r['category'],'Other');self.assertEqual(r['review_status'],'needs_review')
    def test_commit_needs_digest_and_blocks_changed_file(self):
        raw=upload([payment()])
        for commit in (raw,{**raw,'digest':'invalid'}):
            with self.assertRaises(DomainError):self.importer.commit(commit)
        self.assertEqual(self.ledger.transactions(),[])
    def test_only_refund_file_is_a_valid_noop(self):
        raw=upload([payment(当前状态='已全额退款')]);self.assertEqual(self.save(raw)['inserted'],0);self.assertEqual(self.ledger.transactions(),[])

class WechatHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.server=create_server(Path(self.tmp.name)/'http.sqlite',0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.base=f'http://127.0.0.1:{self.server.server_port}'
        with urllib.request.urlopen(self.base+'/api/config') as r:self.token=json.load(r)['token']
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,raw,token=True,origin=None):
        headers={'Content-Type':'application/json','Accept-Language':'zh-CN'}
        if token:headers['X-Ledger-Token']=self.token
        if origin:headers['Origin']=origin
        with urllib.request.urlopen(urllib.request.Request(self.base+path,data=json.dumps(raw).encode(),headers=headers)) as r:return json.load(r)
    def test_real_http_preview_confirm_and_duplicate(self):
        raw=upload([payment()]);preview=self.request('/api/import-file/preview',raw)
        self.assertEqual(self.server.ledger.transactions(),[])
        self.assertEqual(self.request('/api/import-file/confirm',{**raw,'digest':preview['digest']})['inserted'],1)
        self.assertEqual(self.request('/api/import-file/confirm',{**raw,'digest':preview['digest']})['duplicates'],1)
    def test_new_routes_require_same_origin_and_token(self):
        for path in ('/api/import-file/preview','/api/import-file/confirm'):
            for kwargs in ({'token':False},{'origin':'https://other.example'}):
                with self.subTest(path=path,kwargs=kwargs),self.assertRaises(urllib.error.HTTPError) as err:self.request(path,upload([payment()]),**kwargs)
                self.assertEqual(err.exception.code,403)

if __name__=='__main__':unittest.main()
