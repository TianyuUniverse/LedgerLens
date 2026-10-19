"""User-confirmed purpose memory. Only approved exact conditions may write labels."""
import json
import sqlite3
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from .domain import DomainError, EXPENSE_CATEGORIES, classify_rule, validate_record


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


GENERIC_PURPOSES = {'微信转账','支付宝转账','微信支付','支付宝支付','转账','支付成功','支付','充值','校园账户充值','transfer','payment','wechat transfer','alipay transfer','account top-up'}


class MemoryStore:
    def __init__(self, ledger):
        self.ledger = ledger

    @staticmethod
    def purpose_category(record):
        category=classify_rule(record.get('note',''),'expense')['category']
        return category if category!='Other' else classify_rule(record['description'],'expense')['category']

    def list(self, con=None):
        if con is None:
            with self.ledger.connection() as con:
                return self.list(con)
        result = []
        for item in con.execute('SELECT * FROM category_memories ORDER BY id DESC'):
            row = dict(item)
            row['match'] = json.loads(row.pop('match_json'))
            row['example'] = json.loads(row.pop('example_json'))
            row['enabled'], row['auto_apply'] = bool(row['enabled']), bool(row['auto_apply'])
            result.append(row)
        return result

    @staticmethod
    def matches(record, pattern):
        return all(normalized(value) in normalized(record[field]) if field != 'counterparty'
                   else normalized(value) == normalized(record[field])
                   for field, value in pattern.items())

    def retrieve(self, record, con=None):
        result = []
        for memory in self.list(con):
            if not memory['enabled']:
                continue
            match = memory['match']
            related = (match.get('counterparty') and normalized(match['counterparty']) == normalized(record.get('counterparty', '')))
            exact = self.matches(record, match)
            if related or exact:
                result.append({**memory, 'matches': exact})
        return result

    def decision(self, record, con=None):
        candidates = self.retrieve(record, con)
        matches = [m for m in candidates if m['matches']]
        decision = {'kind': record['kind'], 'category': record['category'], 'category_source': record['category_source'],
                    'memory_id': None, 'memory_version': None, 'decision_reason': '',
                    'review_status': 'needs_review' if record['category'] == 'Other' or record['kind'] == 'transfer' else 'confirmed'}
        purpose_signal = self.purpose_category(record)
        if record['kind']=='expense' and purpose_signal!='Other' and purpose_signal!=record['category']:
            decision.update(review_status='needs_review', decision_reason='Imported category differs from a purpose signal. Confirm the actual use.')
        if record['category']=='Education' and purpose_signal=='Other' and any(word in normalized(record['description']+' '+record.get('counterparty','')) for word in ('大学','学校','university','college')):
            decision.update(review_status='needs_review', decision_reason='An institution payee alone does not establish education spending. Confirm the actual use.')
        if not matches:
            if candidates:
                decision.update(review_status='needs_review', decision_reason='Known counterparty, but the confirmed context does not match.')
            return decision
        labels = {(m['kind'], m['category']) for m in matches}
        purpose_category = self.purpose_category(record)
        chosen = matches[0]
        conflict = purpose_category != 'Other' and chosen['kind'] == 'expense' and purpose_category != chosen['category']
        if len(labels) != 1 or not all(m['auto_apply'] for m in matches) or conflict:
            decision.update(review_status='needs_review', decision_reason='Memory requires review, conflicts with another memory, or has a different purpose signal.')
            return decision
        decision.update(kind=chosen['kind'], category=chosen['category'], category_source='memory',
                        memory_id=chosen['id'], memory_version=chosen['version'], review_status='auto',
                        decision_reason=f"Approved memory #{chosen['id']} v{chosen['version']}: {chosen['purpose']}")
        return decision

    @staticmethod
    def validate(raw, example):
        if not isinstance(raw, dict) or set(raw) - {'kind', 'category', 'purpose', 'match', 'enabled', 'auto_apply'}:
            raise DomainError('Unsupported memory fields.')
        kind, category = raw.get('kind'), raw.get('category')
        if kind not in ('income', 'expense', 'transfer') or (kind == 'expense' and category not in EXPENSE_CATEGORIES) or (kind != 'expense' and category != kind.title()):
            raise DomainError('Memory category must agree with its financial kind.')
        purpose, pattern = raw.get('purpose'), raw.get('match')
        if not isinstance(purpose, str) or not 1 <= len(purpose.strip()) <= 200:
            raise DomainError('Explain the confirmed purpose in 1-200 characters.')
        if not isinstance(pattern, dict) or not pattern or set(pattern) - {'counterparty', 'description', 'note'}:
            raise DomainError('Choose a counterparty, description phrase or note phrase for the memory.')
        if any(not isinstance(v, str) or not 2 <= len(v.strip()) <= 300 for v in pattern.values()):
            raise DomainError('Each matching condition must contain 2-300 characters.')
        pattern = {k: v.strip() for k, v in pattern.items()}
        for key in ('enabled', 'auto_apply'):
            if type(raw.get(key, key == 'enabled')) is not bool:
                raise DomainError(key + ' must be true or false.')
        auto = raw.get('auto_apply', False)
        contextual = any(k in pattern and normalized(pattern[k]) != normalized(example.get('counterparty', '')) and normalized(pattern[k]) not in GENERIC_PURPOSES for k in ('description', 'note'))
        if auto and not contextual:
            raise DomainError('Automatic reuse needs a purpose phrase in the description or note. A payee or generic payment/transfer label alone is not enough.')
        if not MemoryStore.matches(example, pattern):
            raise DomainError('The memory conditions must match the confirmed example.')
        return {**raw, 'purpose': purpose.strip(), 'match': pattern, 'enabled': raw.get('enabled', True), 'auto_apply': auto}

    def confirm(self, record_id, raw):
        if type(record_id) is not int or not isinstance(raw, dict) or set(raw) - {'kind','category','purpose','remember','auto_apply','match','expected_revision'}:
            raise DomainError('Invalid confirmation request.')
        if type(raw.get('remember', False)) is not bool:
            raise DomainError('remember must be true or false.')
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            old = con.execute('SELECT * FROM transactions WHERE id=?', (record_id,)).fetchone()
            if old is None:
                raise DomainError('Record does not exist.')
            old = dict(old)
            if 'expected_revision' in raw and (type(raw['expected_revision']) is not int or raw['expected_revision'] != old['revision']):
                raise DomainError('This record changed. Refresh and review it again.')
            kind, category = raw.get('kind'), raw.get('category')
            if kind not in ('expense','income','transfer') or (kind=='expense' and category not in EXPENSE_CATEGORIES) or (kind!='expense' and category!=kind.title()):
                raise DomainError('Choose the confirmed kind and category explicitly.')
            if 'purpose' in raw and (not isinstance(raw['purpose'],str) or not 1<=len(raw['purpose'].strip())<=200):
                raise DomainError('Purpose must contain 1-200 characters.')
            new = validate_record({**old, 'amount': str(Decimal(old['amount_fen'])/100), 'kind': raw.get('kind'), 'category': raw.get('category')})
            memory_id = None
            if raw.get('remember'):
                data = self.validate({k:raw[k] for k in ('kind','category','purpose','match','auto_apply') if k in raw}, old)
                stamp = datetime.now(timezone.utc).isoformat()
                cursor = con.execute('''INSERT INTO category_memories(kind,category,purpose,match_json,example_json,source_id,enabled,auto_apply,version,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,1,?,?)''', (data['kind'],data['category'],data['purpose'],json.dumps(data['match'],ensure_ascii=False),json.dumps(old,ensure_ascii=False),record_id,1,int(data['auto_apply']),stamp,stamp))
                memory_id = cursor.lastrowid
            try:
                con.execute('''UPDATE transactions SET kind=?,category=?,fingerprint=?,category_source='human',review_status='confirmed',
                    memory_id=?,memory_version=?,decision_reason=?,revision=revision+1 WHERE id=?''',
                    (new['kind'],new['category'],new['fingerprint'],memory_id,1 if memory_id else None,raw.get('purpose','User confirmed purpose.'),record_id))
            except sqlite3.IntegrityError:
                raise DomainError('This correction would duplicate another record. Nothing was saved.') from None
            self.ledger.audit(con,'confirm_purpose',{'id':record_id,'before':old,'kind':new['kind'],'category':new['category'],'memory_id':memory_id})
        return {'id':record_id,'memory_id':memory_id,'saved':True}

    def update(self, memory_id, patch):
        if type(memory_id) is not int or not isinstance(patch, dict) or not patch:
            raise DomainError('Choose a memory and supported changes.')
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            old = next((m for m in self.list(con) if m['id']==memory_id), None)
            if not old:
                raise DomainError('Memory does not exist.')
            if set(patch) - {'kind','category','purpose','match','enabled','auto_apply'}:
                raise DomainError('Unsupported memory change.')
            data = self.validate({**{k:old[k] for k in ('kind','category','purpose','match','enabled','auto_apply')},**patch},old['example'])
            con.execute('''UPDATE category_memories SET kind=?,category=?,purpose=?,match_json=?,enabled=?,auto_apply=?,version=version+1,updated_at=? WHERE id=?''',
                        (data['kind'],data['category'],data['purpose'],json.dumps(data['match'],ensure_ascii=False),int(data['enabled']),int(data['auto_apply']),datetime.now(timezone.utc).isoformat(),memory_id))
            self.ledger.audit(con,'memory_update',{'id':memory_id,'before':old,'changes':data,'history_rewritten':False})
        return {'id':memory_id,'version':old['version']+1}

    def delete(self, memory_id):
        if type(memory_id) is not int:
            raise DomainError('Memory ID must be an integer.')
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            old = next((m for m in self.list(con) if m['id']==memory_id), None)
            if not old:
                raise DomainError('Memory does not exist.')
            con.execute('DELETE FROM category_memories WHERE id=?',(memory_id,))
            self.ledger.audit(con,'memory_delete',{'id':memory_id,'before':old,'history_rewritten':False})
        return {'id':memory_id,'deleted':True}
