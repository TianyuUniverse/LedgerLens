"""Read WeChat's exported XLSX locally, with a preview before any ledger write.

Only cell values are read. No formulas, macros, links or workbook code execute.
The runtime uses the Python standard library, without requiring Excel.
"""
import base64
import binascii
import csv
import hashlib
import io
import posixpath
import re
import zipfile
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from xml.etree import ElementTree as ET
from .domain import DomainError, classify_rule, money, validate_record

MAX_FILE=5_000_000
HEADERS={'交易时间','交易类型','交易对方','商品','收/支','金额(元)','当前状态','交易单号','备注'}
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
FIELDS=('date','description','amount','kind','category','counterparty','note','source_kind','source_category','source_platform','external_id','source_status','occurred_at')

def xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise DomainError('账单含有不支持的 XML 内容。')
    return ET.fromstring(data)

def workbook_rows(content):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            info=z.infolist()
            if len(info)>300 or sum(f.file_size for f in info)>30_000_000 or any(f.flag_bits&1 for f in info):
                raise DomainError('账单过大或已加密。请上传微信解压后的原始 xlsx 文件。')
            if len({f.filename for f in info})!=len(info):raise DomainError('账单文件结构异常。')
            shared=[]
            if 'xl/sharedStrings.xml' in z.namelist():
                for item in xml(z.read('xl/sharedStrings.xml')).findall('s:si',NS):
                    shared.append(''.join(t.text or '' for t in item.iterfind('.//s:t',NS)))
            wb=xml(z.read('xl/workbook.xml'));rels=xml(z.read('xl/_rels/workbook.xml.rels'))
            targets={r.get('Id'):r.get('Target','') for r in rels if r.get('TargetMode')!='External'}
            prop=wb.find('s:workbookPr',NS);epoch='1904' if prop is not None and prop.get('date1904') in ('1','true') else '1900'
            sheets=wb.findall('s:sheets/s:sheet',NS)
            if len(sheets)>10:raise DomainError('工作表过多，请选择微信原始账单。')
            result=[]
            for sheet in sheets:
                target=targets.get(sheet.get('{'+REL+'}id'),'')
                path=target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/'+target)
                if not path.startswith('xl/worksheets/') or not path.endswith('.xml'):continue
                rows=[];sheet_xml=xml(z.read(path))
                for row in sheet_xml.findall('s:sheetData/s:row',NS):
                    cells={}
                    for cell in row.findall('s:c',NS):
                        ref=cell.get('r','');m=re.fullmatch(r'([A-Z]{1,3})(\d+)',ref)
                        if not m:raise DomainError('账单单元格位置无效。')
                        col=0
                        for c in m[1]:col=col*26+ord(c)-64
                        if col>64:raise DomainError('账单列数超出支持范围。')
                        if cell.find('s:f',NS) is not None:raise DomainError('账单包含公式，请使用微信直接导出的明细文件。')
                        value=cell.findtext('s:v','',NS);typ=cell.get('t','n')
                        if typ=='s':value=shared[int(value)]
                        elif typ=='inlineStr':value=''.join(t.text or '' for t in cell.iterfind('.//s:t',NS))
                        elif typ=='e':raise DomainError('账单包含错误单元格。')
                        cells[col-1]=(value.strip(),typ)
                    if cells:rows.append((int(row.get('r','0')),cells))
                    if len(rows)>5100:raise DomainError('一次最多导入 5,000 笔账单。')
                result.append((sheet.get('name',''),rows,epoch))
            return result
    except DomainError:raise
    except (zipfile.BadZipFile,KeyError,IndexError,ValueError,ET.ParseError,RuntimeError,NotImplementedError,OSError):
        raise DomainError('无法读取这份 xlsx 文件，请使用微信直接导出并解压后的账单。') from None

def timestamp(value,typ,epoch):
    if typ=='n':
        try:
            serial=Decimal(value)
            if not serial.is_finite() or not 1<=serial<150000:raise ValueError()
            base=datetime(1904,1,1) if epoch=='1904' else datetime(1899,12,30)
            moment=base+timedelta(seconds=float(serial*86400))
            return moment.replace(microsecond=0).isoformat(sep=' ')
        except (InvalidOperation,ValueError,OverflowError):raise DomainError('交易时间无效。') from None
    try:
        moment=datetime.fromisoformat(value.replace('/','-').replace('T',' '))
        if moment.tzinfo is not None:raise ValueError()
        return moment.isoformat(sep=' ',timespec='seconds')
    except ValueError:raise DomainError('交易时间无效。') from None

def amount(value,typ='s'):
    value=re.sub(r'^[¥￥]\s*','',value).replace(',','').strip()
    try:
        val=Decimal(value)
        if not val.is_finite():raise InvalidOperation()
        rounded=val.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        # XLSX numeric cells may contain a tiny binary-to-decimal representation error.
        if typ=='n' and abs(val-rounded)<=Decimal('0.00000001'):val=rounded
        return money(str(val),allow_zero=True)
    except (InvalidOperation,ValueError):raise DomainError('金额无效，应为最多两位小数的人民币金额。') from None

def clean(value):return '' if value in ('/','-','--') else value

class WechatImport:
    def __init__(self,ledger):self.ledger=ledger

    def prepare(self,raw):
        if not isinstance(raw,dict) or set(raw)-{'filename','data','digest'}:raise DomainError('导入文件参数无效。')
        name=raw.get('filename','');encoded=raw.get('data')
        if not isinstance(name,str) or not name.lower().endswith('.xlsx'):raise DomainError('请选择微信直接导出的 .xlsx 账单。CSV 模板也可通过原入口导入。')
        if not isinstance(encoded,str) or len(encoded)>((MAX_FILE+2)//3)*4:raise DomainError('账单不能超过 5 MB。')
        try:content=base64.b64decode(encoded,validate=True)
        except (ValueError,binascii.Error):raise DomainError('文件传输不完整，请重新选择。') from None
        if not content or len(content)>MAX_FILE:raise DomainError('账单不能为空，且不能超过 5 MB。')
        digest=hashlib.sha256(content).hexdigest()
        if 'digest' in raw and raw['digest']!=digest:raise DomainError('文件已变化，请重新预览。')
        found=[]
        for sheet,rows,epoch in workbook_rows(content):
            for index,(number,cells) in enumerate(rows[:100]):
                fields={col:re.sub(r'\s+','',v[0]).replace('（','(').replace('）',')') for col,v in cells.items()}
                if HEADERS.issubset(set(fields.values())):
                    if len(set(fields.values()))!=len(fields):raise DomainError('账单表头有重复列。')
                    found.append((sheet,number,fields,rows[index+1:],epoch));break
        if len(found)!=1:raise DomainError('未找到唯一的微信交易明细表头，请使用微信直接导出的原始账单。')
        sheet,header,fields,rows,epoch=found[0]
        records=[];excluded=[];errors=[];seen={};refund_total=0;source_states={}
        for rownum,cells in rows:
            row={key:cells.get(col,('', 's'))[0] for col,key in fields.items()}
            if not any(row.values()):continue
            if not row.get('交易时间'):
                errors.append(f'第 {rownum} 行缺少交易时间');continue
            try:
                types={key:cells.get(col,('', 's'))[1] for col,key in fields.items()}
                when=timestamp(row['交易时间'],types['交易时间'],epoch)
                total=amount(row['金额(元)'],types['金额(元)']);status=row['当前状态'];trade=row['交易类型'];direction=row['收/支']
                external=row['交易单号']
                if not external or len(external)>100 or (types['交易单号']=='n' and (not external.isdigit() or len(external)>15)):
                    raise DomainError('交易单号缺失或精度已损失，请使用原始导出文件。')
                if external in source_states and source_states[external]!=status:raise DomainError('同一交易单号出现不同状态。')
                source_states[external]=status
                reason=None
                if any(t in status for t in ('已全额退款','对方已退还','已关闭','已取消','支付失败','已过期')):reason='交易已退款或未完成，不计入收支'
                elif '退款' in trade:reason='退款到账，不作为新增收入；请核对对应原支出'
                elif total==0:reason='零金额记录'
                if reason:
                    excluded.append({'row':rownum,'date':when[:10],'trade_type':trade,'amount_fen':total,'reason':reason});continue
                if '退款' in status:
                    match=re.search(r'已退款\s*[(（]\s*[¥￥]?\s*([\d,.]+)\s*[)）]',status)
                    if not match:raise DomainError('退款金额不明确，请先核对原账单。')
                    returned=amount(match[1])
                    if returned>total:raise DomainError('退款金额高于原交易金额。')
                    total-=returned;refund_total+=returned
                    if not total:
                        excluded.append({'row':rownum,'date':when[:10],'trade_type':trade,'amount_fen':returned,'reason':'已全额退款，不计入收支'});continue
                if direction in ('收入','支出'):kind='income' if direction=='收入' else 'expense'
                elif direction in ('/','不计收支','其他') and any(w in trade for w in ('零钱提现','转入零钱通','零钱通转出','充值','账户互转')):kind='transfer'
                else:raise DomainError('收支方向无法识别，请核对该行。')
                desc=clean(row['商品']) or trade;note=clean(row['备注']);payee=clean(row['交易对方'])
                category=classify_rule(desc+' '+note,kind)['category']
                record={'date':when[:10],'description':desc,'amount':f'{total//100}.{total%100:02d}','kind':kind,'category':category,'counterparty':payee,'note':note,
                    'source_kind':'微信 · '+trade+' · '+direction,'source_category':'微信未提供消费分类','source_platform':'wechat','external_id':external,'source_status':status,'occurred_at':when}
                validate_record(record)
                if external in seen:
                    if seen[external]!=record:raise DomainError('同一交易单号出现不同内容。')
                    excluded.append({'row':rownum,'date':when[:10],'trade_type':trade,'amount_fen':total,'reason':'文件内重复的交易单号'});continue
                seen[external]=record;records.append(record)
            except DomainError as exc:errors.append(f'第 {rownum} 行：{exc}')
        if errors:raise DomainError('整份账单未导入。'+'；'.join(errors[:6]))
        if not rows:raise DomainError('这份账单没有交易明细。')
        existing={r['external_id']:r for r in self.ledger.transactions() if r.get('source_platform')=='wechat'}
        duplicates=0;conflicts=[r['id'] for key,r in existing.items() if key in source_states and r['source_status']!=source_states[key]]
        for r in records:
            old=existing.get(r['external_id'])
            if not old:continue
            if (old['source_status'],old['amount_fen'])!=(r['source_status'],money(r['amount'])):
                if old['id'] not in conflicts:conflicts.append(old['id'])
            else:duplicates+=1
        totals={k:sum(money(r['amount']) for r in records if r['kind']==k) for k in ('income','expense','transfer')}
        counts=Counter(e['reason'] for e in excluded)
        preview={'format':'wechat-xlsx','digest':digest,'sheet':sheet,'header_row':header,'source_rows':len(records)+len(excluded),
            'ready_count':len(records),'new_count':sum(r['external_id'] not in existing for r in records),'duplicates':duplicates,'conflicts':conflicts,
            'excluded_count':len(excluded),'excluded_reasons':[{'reason':k,'count':v} for k,v in counts.items()],'excluded_rows':excluded,
            'income_fen':totals['income'],'expense_fen':totals['expense'],'transfer_fen':totals['transfer'],'partial_refund_fen':refund_total,
            'preview_rows':[{**r,'amount_fen':money(r['amount'])} for r in records[:8]],
            'notice':'按微信的收支方向导入。给他人转账的支出保留为支出，用途不明的请确认分类。零钱账户划转不计入收入和支出。',
            'refund_notice':'全额退款、退还、未完成交易及退款到账行已单列；部分退款按剩余金额计入支出。跨文件退款状态变化会提示核对，不自动改写旧账。'}
        return records,preview

    def preview(self,raw):return self.prepare(raw)[1]

    def commit(self,raw):
        if not isinstance(raw,dict) or not raw.get('digest'):raise DomainError('请先预览账单，再确认导入。')
        records,preview=self.prepare(raw)
        if preview['conflicts']:raise DomainError('有已导入交易的金额或退款状态发生变化，请先核对这些历史账单：'+', '.join('#'+str(i) for i in preview['conflicts'][:8]))
        if records:
            out=io.StringIO();writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader();writer.writerows(records)
            result=self.ledger.import_csv(out.getvalue())
        else:result={'inserted':0,'duplicates':0,'ids':[],'auto_labeled':0,'needs_review':0}
        return {**result,'excluded_count':preview['excluded_count'],'format':'wechat-xlsx'}
