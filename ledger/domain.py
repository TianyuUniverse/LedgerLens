"""Shared validation and exact-money primitives."""
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from .localization import CATEGORY_LABELS

EXPENSE_CATEGORIES = ('Housing', 'Food', 'Transport', 'Shopping', 'Entertainment', 'Utilities', 'Health', 'Other', 'Education')
CATEGORIES = EXPENSE_CATEGORIES + ('Income', 'Transfer')
RULES = {
    'Housing': ('rent', 'housing', '房租', '租金'),
    'Food': ('canteen', 'restaurant', 'grocery', 'coffee', 'lunch', 'dinner', '食堂', '餐', '超市', '伙食'),
    'Transport': ('metro', 'bus', 'taxi', 'didi', '地铁', '公交', '打车'),
    'Shopping': ('taobao', 'jd.com', 'clothes', 'bookstore', '淘宝', '京东', '衣服'),
    'Entertainment': ('cinema', 'movie', 'game', 'concert', '电影', '游戏'),
    'Utilities': ('electric', 'water bill', 'internet', 'phone bill', '电费', '水费', '话费'),
    'Health': ('hospital', 'pharmacy', 'clinic', '医院', '药'),
    'Education': ('tuition', 'course fee', '学费', '课程费'),
}

class DomainError(ValueError):
    pass

def money(value, allow_zero=False):
    if isinstance(value, bool) or value is None:
        raise DomainError('Amount must be a decimal number.')
    try:
        val = Decimal(str(value))
    except InvalidOperation:
        raise DomainError('Amount must be a decimal number.') from None
    if not val.is_finite() or val < 0 or (val == 0 and not allow_zero) or val > 100000000:
        raise DomainError('Amount must be positive and no greater than RMB 100,000,000.')
    if val != val.quantize(Decimal('.01')):
        raise DomainError('Amount must have at most two decimal places.')
    return int(val * 100)

def rounded(value):
    return int(Decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def validate_month(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}', value):
        raise DomainError('Month must use YYYY-MM.')
    try:
        date.fromisoformat(value + '-01')
    except ValueError:
        raise DomainError('Invalid month.') from None
    return value

def classify_rule(description, kind='expense'):
    if kind == 'income':
        return {'category': 'Income', 'confidence': 1.0, 'source': 'kind', 'reason': 'Income record.'}
    if kind == 'transfer':
        return {'category': 'Transfer', 'confidence': 1.0, 'source': 'kind', 'reason': 'Transfer excluded from income and spending.'}
    text = description.casefold()
    for category, keywords in RULES.items():
        for word in keywords:
            if word in text:
                return {'category': category, 'confidence': .85, 'source': 'rule', 'reason': 'Matched keyword: ' + word}
    return {'category': 'Other', 'confidence': .0, 'source': 'rule', 'reason': 'No known keyword. Please review.'}

def validate_record(raw):
    try:
        raw_date = raw.get('date', '')
        if not isinstance(raw_date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw_date):
            raise ValueError
        day = date.fromisoformat(raw_date).isoformat()
    except ValueError:
        raise DomainError('Date must be a valid YYYY-MM-DD.') from None
    description = raw.get('description', '')
    if not isinstance(description, str) or not description.strip() or len(description) > 300:
        raise DomainError('Description must contain 1-300 characters.')
    description = description.strip()
    kind = raw.get('kind', 'expense')
    kind = {'收入':'income','支出':'expense','转账':'transfer','账户互转':'transfer'}.get(kind,kind) if isinstance(kind,str) else kind
    if kind not in ('income', 'expense', 'transfer'):
        raise DomainError('Kind must be income, expense or transfer.')
    amount_fen = money(raw.get('amount'))
    suggestion = classify_rule(description, kind)
    category = raw.get('category') or suggestion['category']
    if isinstance(category,str):
        category = {v:k for k,v in CATEGORY_LABELS.items()}.get(category,category)
    if category not in CATEGORIES or (kind == 'expense' and category not in EXPENSE_CATEGORIES) or (kind != 'expense' and category != kind.title()):
        raise DomainError('Category must agree with record kind.')
    context = {}
    for key in ('counterparty', 'note', 'source_kind', 'source_category'):
        value = raw.get(key, '')
        if not isinstance(value, str) or len(value) > 300:
            raise DomainError(key + ' must be text with at most 300 characters.')
        context[key] = value.strip()
    identity = [day, description.casefold(), amount_fen, kind]
    if context['counterparty'] or context['note']:
        identity.extend([context['counterparty'].casefold(), context['note'].casefold()])
    fingerprint = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()
    context['source_kind'] = context['source_kind'] or raw.get('kind') or kind
    context['source_category'] = context['source_category'] or raw.get('category') or category
    return {'date': day, 'description': description, 'amount_fen': amount_fen, 'kind': kind, 'category': category, 'fingerprint': fingerprint, 'category_source': 'import' if raw.get('category') else suggestion['source'], **context}

