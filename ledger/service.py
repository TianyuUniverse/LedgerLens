"""Money is integer fen. Model output is a proposal, never a ledger write."""
import csv
import io
import json
import math
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .domain import CATEGORIES, EXPENSE_CATEGORIES, DomainError, money, rounded, validate_month, classify_rule, validate_record
from .memory import MemoryStore
from .analytics import FinanceTools
from .provider import classify_context, enabled
from .assistant import Assistant
from .localization import CSV_HEADERS, CATEGORY_LABELS, label
from .adventure import Adventure
from .reports import Reports
from .entry import QuickEntry
from .setup_chat import SetupChat
from .trials import Trials
from .wechat_import import WechatImport

class Ledger:
    def __init__(self, path, clock=None):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS transactions(
              id INTEGER PRIMARY KEY, date TEXT NOT NULL, description TEXT NOT NULL,
              amount_fen INTEGER NOT NULL CHECK(amount_fen>0), kind TEXT NOT NULL,
              category TEXT NOT NULL, fingerprint TEXT UNIQUE NOT NULL,
              category_source TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS budgets(category TEXT PRIMARY KEY, limit_fen INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, at TEXT NOT NULL, action TEXT NOT NULL, details TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS category_memories(
              id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, category TEXT NOT NULL, purpose TEXT NOT NULL,
              match_json TEXT NOT NULL, example_json TEXT NOT NULL, source_id INTEGER NOT NULL,
              enabled INTEGER NOT NULL, auto_apply INTEGER NOT NULL, version INTEGER NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY, state_json TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS transaction_sequence(singleton INTEGER PRIMARY KEY CHECK(singleton=1),last_id INTEGER NOT NULL);
            ''')
            con.execute('INSERT OR IGNORE INTO transaction_sequence VALUES(1,0)')
            con.execute('UPDATE transaction_sequence SET last_id=MAX(last_id,(SELECT COALESCE(MAX(id),0) FROM transactions)) WHERE singleton=1')
            columns = {r['name'] for r in con.execute('PRAGMA table_info(transactions)')}
            additions = {'counterparty':"TEXT NOT NULL DEFAULT ''", 'note':"TEXT NOT NULL DEFAULT ''",
                         'source_kind':"TEXT NOT NULL DEFAULT ''", 'source_category':"TEXT NOT NULL DEFAULT ''",
                         'import_fingerprint':'TEXT', 'memory_id':'INTEGER', 'memory_version':'INTEGER',
                         'review_status':"TEXT NOT NULL DEFAULT 'confirmed'", 'decision_reason':"TEXT NOT NULL DEFAULT ''",
                         'revision':'INTEGER NOT NULL DEFAULT 1',
                         'source_platform':"TEXT NOT NULL DEFAULT ''",'external_id':"TEXT NOT NULL DEFAULT ''",
                         'source_status':"TEXT NOT NULL DEFAULT ''",'occurred_at':"TEXT NOT NULL DEFAULT ''"}
            additions.update(ingestion_origin="TEXT NOT NULL DEFAULT 'legacy'",description_origin="TEXT NOT NULL DEFAULT 'unknown'")
            for name, declaration in additions.items():
                if name not in columns:
                    con.execute(f'ALTER TABLE transactions ADD COLUMN {name} {declaration}')
            con.execute("UPDATE transactions SET source_kind=kind WHERE source_kind=''")
            con.execute("UPDATE transactions SET source_category=category WHERE source_category=''")
            con.execute('UPDATE transactions SET import_fingerprint=fingerprint WHERE import_fingerprint IS NULL')
            con.execute('CREATE UNIQUE INDEX IF NOT EXISTS transaction_import_identity ON transactions(import_fingerprint)')
            con.execute("UPDATE transactions SET ingestion_origin='wechat',description_origin='file' WHERE ingestion_origin='legacy' AND source_platform='wechat'")
            con.execute("UPDATE transactions SET ingestion_origin='entry' WHERE ingestion_origin='legacy' AND decision_reason='用户核对快速记账后确认保存。'")
            if 'review_status' not in columns:
                con.execute("UPDATE transactions SET review_status='needs_review' WHERE category_source!='human' AND (category='Other' OR kind='transfer')")
        self.memory = MemoryStore(self)
        self.tools = FinanceTools(self)
        self.assistant = Assistant(self)
        self.adventure = Adventure(self,clock)
        self.reports = Reports(self)
        self.quick_entry = QuickEntry(self)
        self.setup_chat = SetupChat(self)
        self.trials = Trials(self)
        self.wechat_import = WechatImport(self)

    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def audit(self, con, action, details):
        con.execute('INSERT INTO audit(at,action,details) VALUES(?,?,?)', (datetime.now(timezone.utc).isoformat(), action, json.dumps(details, ensure_ascii=False)))
        self.adventure.track(con,action,details)

    def import_csv(self, content, *, confirmed=False, origin=None, description_origin=None):
        origin=origin or ('entry' if confirmed else 'csv')
        if origin not in ('csv','entry','sample') or description_origin not in (None,'user','local','ai','unknown'):raise DomainError('账单内容来源无效。')
        if not isinstance(content, str) or len(content.encode('utf-8')) > 2000000:
            raise DomainError('CSV must be UTF-8 and at most 2 MB.')
        reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
        if reader.fieldnames:
            aliases={v:k for k,v in CSV_HEADERS.items()}
            reader.fieldnames=[aliases.get(name.strip(),name.strip()) for name in reader.fieldnames]
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not {'date', 'description', 'amount', 'kind'}.issubset(reader.fieldnames):
            raise DomainError('CSV requires distinct date, description, amount, kind headers. category is optional.')
        records, errors = [], []
        for line, raw in enumerate(reader, 2):
            if line > 5001:
                raise DomainError('At most 5,000 records per import.')
            try:
                if None in raw or any(v is None for v in raw.values()):
                    raise DomainError('Column count does not match headers.')
                records.append(validate_record(raw))
            except DomainError as exc:
                errors.append(f'Row {line}: {exc}')
        if errors:
            raise DomainError('Import rejected. No records saved. ' + ' '.join(errors[:8]))
        if not records:
            raise DomainError('CSV has no records.')
        inserted, duplicates, automatic, pending = [], 0, 0, 0
        with self.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            next_id=max(con.execute('SELECT last_id FROM transaction_sequence WHERE singleton=1').fetchone()[0],con.execute('SELECT COALESCE(MAX(id),0) FROM transactions').fetchone()[0])
            for record in records:
                if record['source_platform']=='wechat':record['category_source']='rule'
                original_identity = record['fingerprint']
                existing = con.execute('SELECT id FROM transactions WHERE fingerprint=? OR import_fingerprint=?', (original_identity,original_identity)).fetchone()
                if existing:
                    duplicates += 1
                    continue
                try:
                    decision = ({'kind':record['kind'],'category':record['category'],'category_source':'human',
                        'memory_id':None,'memory_version':None,'review_status':'confirmed','decision_reason':'用户核对快速记账后确认保存。'}
                        if confirmed else self.memory.decision(record, con))
                    revised = validate_record({**record,**decision,'amount':str(Decimal(record['amount_fen'])/100)})
                    values = {**record,**revised,**decision,'id':next_id+1,'import_fingerprint':original_identity,'created_at':datetime.now(timezone.utc).isoformat(),
                        'ingestion_origin':'wechat' if record['source_platform']=='wechat' else origin,
                        'description_origin':(description_origin or 'user') if origin=='entry' else 'file'}
                    cur = con.execute('''INSERT INTO transactions(id,date,description,amount_fen,kind,category,fingerprint,category_source,created_at,
                        counterparty,note,source_kind,source_category,import_fingerprint,memory_id,memory_version,review_status,decision_reason,
                        source_platform,external_id,source_status,occurred_at,ingestion_origin,description_origin)
                        VALUES(:id,:date,:description,:amount_fen,:kind,:category,:fingerprint,:category_source,:created_at,
                        :counterparty,:note,:source_kind,:source_category,:import_fingerprint,:memory_id,:memory_version,:review_status,:decision_reason,
                        :source_platform,:external_id,:source_status,:occurred_at,:ingestion_origin,:description_origin)''',values)
                    inserted.append(cur.lastrowid)
                    next_id=cur.lastrowid
                    automatic += decision['review_status']=='auto'
                    pending += decision['review_status']=='needs_review'
                except sqlite3.IntegrityError:
                    duplicates += 1
            con.execute('UPDATE transaction_sequence SET last_id=? WHERE singleton=1',(next_id,))
            self.audit(con, 'import', {'inserted_ids': inserted, 'duplicates': duplicates})
        return {'inserted': len(inserted), 'duplicates': duplicates, 'ids': inserted, 'auto_labeled':automatic,'needs_review':pending}

    def transactions(self):
        with self.connection() as con:
            return [dict(r) for r in con.execute('SELECT * FROM transactions ORDER BY date DESC,id DESC')]

    def delete_transaction(self, raw):
        if (not isinstance(raw, dict) or set(raw) != {'id', 'expected_revision'}
                or type(raw['id']) is not int or raw['id'] <= 0
                or type(raw['expected_revision']) is not int or raw['expected_revision'] <= 0):
            raise DomainError('请选择要删除的账单，并使用最新的账单详情。')
        # Keep a concurrent purpose chat from recreating an invalidated draft.
        with self.setup_chat.lock, self.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            old = con.execute('SELECT * FROM transactions WHERE id=?', (raw['id'],)).fetchone()
            if not old:
                raise DomainError('这笔账单已不存在，请刷新账单列表。')
            if old['revision'] != raw['expected_revision']:
                raise DomainError('这笔账单已修改，请重新打开详情，核对后再删除。')
            con.execute('DELETE FROM transactions WHERE id=?', (old['id'],))
            con.execute('DELETE FROM period_reports')
            con.execute("DELETE FROM settings WHERE key='generated_plan'")
            for draft in con.execute("SELECT id,context FROM setup_chats WHERE mode='purpose'").fetchall():
                context = json.loads(draft['context'])
                if context.get('record_id') == old['id'] and not context.get('memory_id'):
                    con.execute('DELETE FROM setup_chats WHERE id=?', (draft['id'],))
            self.audit(con, 'transaction_delete', {'id':old['id'], 'before':dict(old)})
        return {'id':raw['id'], 'deleted':True}

    def edit(self, record_id, patch):
        if not isinstance(patch, dict) or not patch or set(patch) - {'date', 'description', 'amount', 'kind', 'category','counterparty','note'}:
            raise DomainError('Supply supported editable fields.')
        with self.connection() as con:
            old = con.execute('SELECT * FROM transactions WHERE id=?', (record_id,)).fetchone()
            if not old:
                raise DomainError('Record does not exist.')
            raw = {**dict(old), 'amount': str(Decimal(old['amount_fen']) / 100), **patch}
            new = validate_record(raw)
            new['description_origin']='user' if 'description' in patch and new['description']!=old['description'] else old['description_origin']
            try:
                con.execute('''UPDATE transactions SET date=:date,description=:description,amount_fen=:amount_fen,kind=:kind,
                    category=:category,fingerprint=:fingerprint,counterparty=:counterparty,note=:note,category_source='human',
                    memory_id=NULL,memory_version=NULL,review_status='confirmed',decision_reason='Manual correction',description_origin=:description_origin,revision=revision+1 WHERE id=:id''', {**new, 'id': record_id})
            except sqlite3.IntegrityError:
                raise DomainError('Edit would duplicate another record. No changes saved.') from None
            self.audit(con, 'edit', {'id': record_id, 'before': dict(old), 'after': new})
        return {'id': record_id, **new, 'category_source': 'human'}

    def overview(self, months=3):
        rows = self.transactions()
        if not rows:
            return {'months': [], 'income_fen': 0, 'expense_fen': 0, 'transfer_fen': 0, 'net_fen': 0, 'categories': [], 'record_ids': [], 'assumption': 'No records. Import data first.'}
        end = max(r['date'][:7] for r in rows)
        year, month = map(int, end.split('-'))
        names = []
        for offset in range(months - 1, -1, -1):
            ordinal = year * 12 + month - 1 - offset
            y, m = divmod(ordinal, 12)
            names.append(f'{y:04d}-{m+1:02d}')
        selected = [r for r in rows if r['date'][:7] in names]
        monthly = []
        for name in names:
            subset = [r for r in selected if r['date'].startswith(name)]
            inc = sum(r['amount_fen'] for r in subset if r['kind'] == 'income')
            exp = sum(r['amount_fen'] for r in subset if r['kind'] == 'expense')
            monthly.append({'month': name, 'income_fen': inc, 'expense_fen': exp, 'net_fen': inc-exp, 'record_count': len(subset)})
        categories = []
        for category in EXPENSE_CATEGORIES:
            subset = [r for r in selected if r['kind'] == 'expense' and r['category'] == category]
            categories.append({'category': category, 'amount_fen': sum(r['amount_fen'] for r in subset), 'record_ids': [r['id'] for r in subset]})
        inc = sum(r['income_fen'] for r in monthly)
        exp = sum(r['expense_fen'] for r in monthly)
        return {'months': monthly, 'income_fen': inc, 'expense_fen': exp, 'net_fen': inc-exp,
                'transfer_fen': sum(r['amount_fen'] for r in selected if r['kind'] == 'transfer'), 'categories': categories,
                'record_ids': [r['id'] for r in selected], 'assumption': 'Last 3 calendar months ending at latest imported month. Missing months count as zero. Data may be incomplete. Transfers excluded.'}

    def plan(self, raw, save=True):
        if not isinstance(raw, dict):
            raise DomainError('Plan must be an object.')
        target = money(raw.get('target'))
        current = money(raw.get('current', 0), allow_zero=True)
        months = raw.get('months')
        if type(months) is not int or not 1 <= months <= 60:
            raise DomainError('Months must be an integer from 1 to 60.')
        cuts = raw.get('cuts', {})
        if not isinstance(cuts, dict) or set(cuts) - set(EXPENSE_CATEGORIES):
            raise DomainError('Unknown reduction category.')
        rates = {}
        for key, value in cuts.items():
            try:
                rate = Decimal(str(value))
            except InvalidOperation:
                raise DomainError('Reductions must be numbers.') from None
            if isinstance(value, bool) or not rate.is_finite() or not 0 <= rate <= 100:
                raise DomainError('Reductions must be between 0 and 100 percent.')
            rates[key] = rate
        view = self.overview()
        if not view['record_ids']:
            raise DomainError('Import records before calculating a plan.')
        baseline = rounded(Decimal(view['net_fen']) / 3)
        reductions = [{**c, 'monthly_reduction_fen': rounded(Decimal(c['amount_fen']) / 3 * rates.get(c['category'], Decimal(0)) / 100)} for c in view['categories'] if c['category'] in rates]
        reduction = sum(c['monthly_reduction_fen'] for c in reductions)
        required = math.ceil(Decimal(max(target-current, 0)) / months)
        projected = current + (baseline + reduction) * months
        result = {'target_fen': target, 'current_fen': current, 'months': months, 'required_monthly_fen': required,
                  'baseline_monthly_fen': baseline, 'extra_required_fen': max(0, required-baseline), 'monthly_reduction_fen': reduction,
                  'scenario_monthly_fen': baseline+reduction, 'projected_fen': projected, 'gap_fen': max(0,target-projected),
                  'feasible': projected >= target, 'reductions': reductions, 'record_ids': view['record_ids'],
                  'assumption': view['assumption'] + ' Future income and spending repeat the 3-month mean. Category cuts are hypothetical. Rounding occurs per category to fen.'}
        if save:
            with self.connection() as con:
                con.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', ('plan', json.dumps(raw)))
                self.audit(con, 'plan', {'inputs': raw, 'result': result})
        return result

    def set_budget(self, category, amount):
        if category not in EXPENSE_CATEGORIES:
            raise DomainError('Choose an expense category.')
        limit = money(amount, allow_zero=True)
        with self.connection() as con:
            con.execute('INSERT OR REPLACE INTO budgets VALUES(?,?)', (category, limit))
            self.audit(con, 'budget', {'category': category, 'limit_fen': limit})
        return {'category': category, 'limit_fen': limit}

    def state(self):
        overview = self.overview()
        transactions = self.transactions()
        with self.connection() as con:
            budgets = [dict(r) for r in con.execute('SELECT * FROM budgets ORDER BY category')]
            audit = [dict(r) for r in con.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 30')]
            saved = con.execute("SELECT value FROM settings WHERE key='plan'").fetchone()
            generated = con.execute("SELECT value FROM settings WHERE key='generated_plan'").fetchone()
        latest = overview['months'][-1]['month'] if overview['months'] else None
        for budget in budgets:
            subset = [r for r in transactions if r['date'].startswith(latest or '!') and r['kind'] == 'expense' and r['category'] == budget['category']]
            spent = sum(r['amount_fen'] for r in subset)
            budget.update({'spent_fen': spent, 'overrun_fen': max(0,spent-budget['limit_fen']), 'month': latest, 'record_ids': [r['id'] for r in subset]})
        plan_input = json.loads(saved['value']) if saved else {'target': '6000', 'current': '0', 'months': 6, 'cuts': {'Shopping': 30, 'Entertainment': 50, 'Food': 10}}
        return {'transactions': transactions, 'overview': overview, 'budgets': budgets, 'audit': audit, 'categories': list(CATEGORIES),
                'expense_categories':list(EXPENSE_CATEGORIES),'memories':self.memory.list(),
                'review_count':sum(r['review_status']=='needs_review' for r in transactions),
                'generated_plan':json.loads(generated['value']) if generated else None,'adventure':self.adventure.state(),
                'plan_input': plan_input, 'plan': self.plan(plan_input, save=False) if transactions else None,
                'model_enabled':enabled(), 'model_name':os.getenv('FINANCE_AI_MODEL') if enabled() else None, 'currency': 'CNY'}

    def ask(self, question, session_id=None, provider=None, use_model=False, locale='auto'):
        return self.assistant.ask(question,session_id,provider,use_model,locale)

    def _ask_baseline(self, question, locale='en'):
        if not isinstance(question, str) or not question.strip() or len(question) > 500:
            raise DomainError('Question must contain 1-500 characters.')
        view = self.overview()
        zh=locale=='zh'
        if not view['record_ids']:
            return {'answer': '暂无账单，请先导入数据。' if zh else 'I have no imported records. Import data first.', 'record_ids': [], 'source': 'grounded tools', 'supported': False}
        q = question.casefold()
        if any(w in q for w in ('stock', 'invest', 'bitcoin', '股票', '投资', 'ignore', '忽略', 'system prompt')):
            return {'answer': '助手仅支持账单分析和储蓄测算，不提供投资建议或无关回答。' if zh else 'This assistant supports spending summaries and saved savings scenarios only. No investment or unrelated answer is available.', 'record_ids': [], 'source': 'grounded tools', 'supported': False}
        def fmt(fen):
            return f'¥{fen/100:,.2f}' if zh else f'RMB {fen/100:,.2f}'
        category = next((c for c in EXPENSE_CATEGORIES if c.casefold() in q or CATEGORY_LABELS[c] in q), None)
        if category:
            item = next(c for c in view['categories'] if c['category'] == category)
            answer = f"{category} spending across the selected 3 months is {fmt(item['amount_fen'])}."
            if zh:answer=f"最近三个月的{label(category)}支出为 {fmt(item['amount_fen'])}。"
            ids = item['record_ids']
        elif any(w in q for w in ('largest', 'biggest', '最多', '最大')):
            item = max(view['categories'], key=lambda c: c['amount_fen'])
            answer = f"The largest category is {item['category']}: {fmt(item['amount_fen'])} across the selected 3 months."
            if zh:answer=f"最近三个月支出最多的类别是{label(item['category'])}，共 {fmt(item['amount_fen'])}。"
            ids = item['record_ids']
        elif any(w in q for w in ('save', 'saving', 'goal', '储蓄', '目标', '存')):
            plan = self.state()['plan']
            answer = f"The saved scenario projects {fmt(plan['projected_fen'])} over {plan['months']} months, including existing savings. The remaining goal gap is {fmt(plan['gap_fen'])}. This is a scenario, not a prediction."
            if zh:answer=f"已保存的测算预计在 {plan['months']} 个月后累计储蓄 {fmt(plan['projected_fen'])}（包含已有储蓄），目标差额为 {fmt(plan['gap_fen'])}。这是情景测算，不是未来保证。"
            ids = plan['record_ids']
        elif any(w in q for w in ('income', '收入')):
            answer = f"Imported income is {fmt(view['income_fen'])} over the selected 3 months. Transfers are excluded."
            if zh:answer=f"最近三个月已导入的收入合计 {fmt(view['income_fen'])}，不计转账。"
            ids = [r['id'] for r in self.transactions() if r['id'] in view['record_ids'] and r['kind']=='income']
        elif any(w in q for w in ('spend', 'expense', '支出', '花')):
            answer = f"Imported spending is {fmt(view['expense_fen'])} over the selected 3 months. Monthly average: {fmt(rounded(Decimal(view['expense_fen'])/3))}."
            if zh:answer=f"最近三个月已导入的支出合计 {fmt(view['expense_fen'])}，平均每月 {fmt(rounded(Decimal(view['expense_fen'])/3))}。"
            ids = [r['id'] for r in self.transactions() if r['id'] in view['record_ids'] and r['kind']=='expense']
        else:
            return {'answer': '可以查询总支出、收入、支出最多的类别、指定类别支出，以及已保存的储蓄目标。请明确要查询的内容。' if zh else 'Supported questions: total spending, income, largest category, category spending, or saved savings goal. Please choose one.', 'record_ids': [], 'source': 'grounded tools', 'supported': False}
        return {'answer': answer, 'record_ids': ids, 'source': 'grounded tools (deterministic)', 'supported': True, 'assumption': view['assumption']}

    def suggest(self, record_id, provider=None):
        record = next((r for r in self.transactions() if r['id']==record_id), None)
        if not record:
            raise DomainError('Record does not exist.')
        baseline = classify_rule(record['description'], record['kind'])
        if record['note']:
            note_proposal=classify_rule(record['note'],record['kind'])
            if note_proposal['category']!='Other':
                baseline=note_proposal
        candidates = self.memory.retrieve(record)
        exact = [m for m in candidates if m['matches']]
        purpose=self.memory.purpose_category(record)
        conflict=exact and exact[0]['kind']=='expense' and purpose!='Other' and purpose!=exact[0]['category']
        if exact and len({(m['kind'],m['category']) for m in exact})==1 and not conflict:
            m=exact[0]
            return {'category':m['category'],'kind':m['kind'],'confidence':1.0,'source':'confirmed memory',
                    'reason':f"Memory #{m['id']} v{m['version']}: {m['purpose']}. Review current purpose before applying.",
                    'record_id':record_id,'saved':False,'memory_id':m['id']}
        if provider is None and not enabled():
            return {**baseline, 'record_id': record_id, 'saved': False, 'notice': 'Rules baseline. No language model is configured.'}
        try:
            result = provider(record['description']) if provider else classify_context(record,candidates)
            valid_fields=({'category','confidence'},{'kind','category','confidence'})
            if not isinstance(result,dict) or set(result) not in valid_fields:
                raise ValueError('Invalid model schema')
            kind=result.get('kind','expense')
            valid_category=(kind=='expense' and result['category'] in EXPENSE_CATEGORIES) or (kind in ('income','transfer') and result['category']==kind.title())
            if not valid_category or type(result['confidence']) not in (int, float) or not math.isfinite(result['confidence']) or not 0<=result['confidence']<=1:
                raise ValueError('Invalid model schema')
            return {**result,'kind':kind, 'source': 'model', 'reason': 'Context and confirmed memories supplied to the model. Review purpose and matching conditions before applying.', 'record_id': record_id, 'saved': False}
        except Exception:
            return {**baseline, 'record_id': record_id, 'saved': False, 'notice': 'Model unavailable or returned invalid output. Used rules baseline.'}

