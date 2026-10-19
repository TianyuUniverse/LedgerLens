"""Read-only finance tools and explicitly confirmed scenario saving."""
import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal
from .domain import DomainError, EXPENSE_CATEGORIES, money, rounded, validate_month
from .memory import normalized


def fields(raw, allowed):
    if not isinstance(raw, dict) or set(raw)-set(allowed):
        raise DomainError('Unknown tool argument.')


def revision(rows):
    values = sorted((r['id'],r['date'],r['description'],r['amount_fen'],r['kind'],r['category'],r['revision']) for r in rows)
    return hashlib.sha256(json.dumps(values,ensure_ascii=False).encode()).hexdigest()


def window(rows):
    if not rows:
        raise DomainError('Import records first.')
    year,month=map(int,max(r['date'][:7] for r in rows).split('-'))
    ordinal=year*12+month-1
    names=[f'{(ordinal-offset)//12:04d}-{(ordinal-offset)%12+1:02d}' for offset in (2,1,0)]
    return [r for r in rows if r['date'][:7] in names],names


def exclusions(ids, rows):
    if not isinstance(ids,list) or len(ids)>5000 or any(type(i) is not int or i<=0 for i in ids):
        raise DomainError('Excluded IDs must be a list of positive integers.')
    if set(ids)-{r['id'] for r in rows}:
        raise DomainError('An excluded record does not exist in this analysis period.')
    return set(ids)


class FinanceTools:
    def __init__(self,ledger):
        self.ledger=ledger

    def query_transactions(self,raw):
        fields(raw,('month','category','description','kind','exclude_ids'))
        rows=self.ledger.transactions()
        month=raw.get('month')
        if month is not None:
            validate_month(month)
            rows=[r for r in rows if r['date'][:7]==month]
        elif rows:
            rows,_=window(rows)
        omitted=exclusions(raw.get('exclude_ids',[]),rows)
        category,kind,description=raw.get('category'),raw.get('kind','expense'),raw.get('description')
        if category is not None and category not in EXPENSE_CATEGORIES:
            raise DomainError('Choose an expense category.')
        if kind not in ('expense','income','transfer'):
            raise DomainError('Choose a financial kind.')
        if description is not None and (not isinstance(description,str) or not 1<=len(description)<=300):
            raise DomainError('Description query must contain 1-300 characters.')
        rows=[r for r in rows if r['kind']==kind and r['id'] not in omitted
              and (category is None or r['category']==category)
              and (description is None or normalized(description) in normalized(r['description']+' '+r['counterparty']+' '+r['note']))]
        keys=('id','date','description','counterparty','note','amount_fen','kind','category')
        return {'tool':'query_transactions','month':month,'kind':kind,'category':category,
                'total_fen':sum(r['amount_fen'] for r in rows),'record_ids':[r['id'] for r in rows],
                'records':[{k:r[k] for k in keys} for r in rows[:100]],'record_count':len(rows),
                'truncated':len(rows)>100,'exclude_ids':sorted(omitted)}

    def compare_periods(self,raw,rows=None):
        fields(raw,('first_month','second_month','exclude_ids'))
        first,second=validate_month(raw.get('first_month')),validate_month(raw.get('second_month'))
        if first==second:
            raise DomainError('Choose two different months.')
        rows=self.ledger.transactions() if rows is None else rows
        scoped=[r for r in rows if r['date'][:7] in (first,second)]
        omitted=exclusions(raw.get('exclude_ids',[]),scoped)
        expenses=[r for r in scoped if r['kind']=='expense' and r['id'] not in omitted]
        totals={m:sum(r['amount_fen'] for r in expenses if r['date'][:7]==m) for m in (first,second)}
        categories=[]
        for category in EXPENSE_CATEGORIES:
            selected=[r for r in expenses if r['category']==category]
            a=sum(r['amount_fen'] for r in selected if r['date'][:7]==first)
            b=sum(r['amount_fen'] for r in selected if r['date'][:7]==second)
            if a or b:
                categories.append({'category':category,'first_fen':a,'second_fen':b,'delta_fen':b-a,'record_ids':[r['id'] for r in selected]})
        return {'tool':'compare_periods','first_month':first,'second_month':second,'first_fen':totals[first],
                'second_fen':totals[second],'delta_fen':totals[second]-totals[first],
                'categories':sorted(categories,key=lambda c:abs(c['delta_fen']),reverse=True),
                'record_ids':[r['id'] for r in expenses],'exclude_ids':sorted(omitted),
                'missing_months':[m for m in (first,second) if not any(r['date'][:7]==m for r in scoped)],
                'assumption':'Imported records only. Transfers excluded. Missing months have no records, not proven zero real spending. Changes do not establish personal motivation.'}

    def generate_savings_plans(self,raw,rows=None):
        fields(raw,('target','current','months','locked','floors'))
        target=money(raw.get('target'))
        current=money(raw.get('current',0),allow_zero=True)
        months=raw.get('months')
        if type(months) is not int or not 1<=months<=60:
            raise DomainError('Months must be an integer from 1 to 60.')
        locked=raw.get('locked',['Housing'])
        floors=raw.get('floors',{})
        if not isinstance(locked,list) or any(c not in EXPENSE_CATEGORIES for c in locked) or len(locked)!=len(set(locked)):
            raise DomainError('Locked categories must be distinct expense categories.')
        if not isinstance(floors,dict) or set(floors)-set(EXPENSE_CATEGORIES):
            raise DomainError('Unknown floor category.')
        floors={k:money(v,allow_zero=True) for k,v in floors.items()}
        rows=self.ledger.transactions() if rows is None else rows
        selected,names=window(rows)
        monthly={c:rounded(Decimal(sum(r['amount_fen'] for r in selected if r['kind']=='expense' and r['category']==c))/3) for c in EXPENSE_CATEGORIES}
        income=rounded(Decimal(sum(r['amount_fen'] for r in selected if r['kind']=='income'))/3)
        for category in locked:
            if floors.get(category,0)>monthly[category]:
                raise DomainError(f'{category} is fixed below its requested minimum. Change one of these conflicting limits.')
        start={c:max(monthly[c],floors.get(c,0)) for c in EXPENSE_CATEGORIES}
        cap_rates={'Housing':0,'Health':0,'Education':0,'Utilities':10,'Food':20,'Transport':20,'Shopping':50,'Entertainment':50,'Other':20}
        caps={c:0 if c in locked else max(0,min(rounded(Decimal(monthly[c])*cap_rates[c]/100),start[c]-floors.get(c,0))) for c in EXPENSE_CATEGORIES}
        base_savings=income-sum(start.values())
        required=math.ceil(Decimal(max(0,target-current))/months)
        needed=max(0,required-base_savings)
        available=sum(caps.values())
        cut_total=min(needed,available)
        options=[]
        styles=[('balanced','Balanced',None),('shopping_first','Shopping first',['Shopping','Entertainment','Other','Utilities','Transport','Food','Housing','Health','Education']),
                ('less_food_change','Keep dining changes small',['Entertainment','Shopping','Other','Transport','Utilities','Food','Housing','Health','Education'])]
        for key,label,order in styles:
            cuts={c:0 for c in EXPENSE_CATEGORIES}
            if order is None and available:
                cuts={c:cut_total*caps[c]//available for c in EXPENSE_CATEGORIES}
                remainder=cut_total-sum(cuts.values())
                for c in sorted(EXPENSE_CATEGORIES,key=lambda c:cut_total*caps[c]%available,reverse=True):
                    if remainder and cuts[c]<caps[c]:
                        cuts[c]+=1;remainder-=1
            else:
                remaining=cut_total
                for c in order or []:
                    cuts[c]=min(remaining,caps[c]);remaining-=cuts[c]
            amounts={c:start[c]-cuts[c] for c in EXPENSE_CATEGORIES}
            violations=[f'{c} is locked' for c in locked if amounts[c]!=monthly[c]]
            violations += [f'{c} below minimum' for c in EXPENSE_CATEGORIES if amounts[c]<floors.get(c,0)]
            assert not violations
            monthly_savings=income-sum(amounts.values())
            projected=current+monthly_savings*months
            options.append({'style':key,'label':label,'monthly_amounts_fen':amounts,'monthly_cuts_fen':cuts,
                            'monthly_savings_fen':monthly_savings,'projected_fen':projected,'gap_fen':max(0,target-projected),
                            'feasible':projected>=target,'constraints_passed':True,'violations':violations})
        inputs={'target':str(Decimal(target)/100),'current':str(Decimal(current)/100),'months':months,
                'locked':locked,'floors':{k:str(Decimal(v)/100) for k,v in floors.items()}}
        return {'tool':'generate_savings_plans','inputs':inputs,'baseline_monthly_fen':monthly,'monthly_income_fen':income,
                'required_monthly_fen':required,'options':options,'record_ids':[r['id'] for r in selected if r['kind']!='transfer'],
                'ledger_revision':revision(rows),'periods':names,'default_cut_caps_pct':cap_rates,'saved':False,
                'assumption':'Three calendar-month mean, with missing months counted as zero. Income and category averages round to fen separately. Default reduction caps are proposal assumptions. Hard locks and minimums never relax. Future spending is not guaranteed.'}

    def save_plan(self,raw):
        fields(raw,('inputs','style','ledger_revision'))
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            rows=[dict(r) for r in con.execute('SELECT * FROM transactions')]
            result=self.generate_savings_plans(raw.get('inputs'),rows)
            if raw.get('ledger_revision')!=result['ledger_revision']:
                raise DomainError('Records changed since this preview. Generate and review the plans again.')
            option=next((o for o in result['options'] if o['style']==raw.get('style')),None)
            if not option:
                raise DomainError('Select a generated plan.')
            saved={'inputs':result['inputs'],'style':option['style'],'ledger_revision':result['ledger_revision']}
            con.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('generated_plan',?)",(json.dumps(saved),))
            self.ledger.audit(con,'generated_plan_save',{'inputs':saved,'result':option})
        return {**option,'saved':True}

    def monthly_review(self,raw):
        fields(raw,('month',))
        rows=self.ledger.transactions()
        if not rows:
            raise DomainError('Import records first.')
        month=validate_month(raw.get('month') or max(r['date'][:7] for r in rows))
        year,m=map(int,month.split('-'));ordinal=year*12+m-2
        previous=f'{ordinal//12:04d}-{ordinal%12+1:02d}'
        comparison=self.compare_periods({'first_month':previous,'second_month':month},rows)
        groups=defaultdict(list)
        for record in rows:
            if record['kind']=='expense' and record['date'][:7]<=month:
                groups[normalized(record['counterparty'] or record['description'])].append(record)
        recurring=[]
        for key,items in groups.items():
            current=[r for r in items if r['date'][:7]==month]
            if current and len({r['date'][:7] for r in items})>=2:
                recurring.append({'description':key,'months':sorted({r['date'][:7] for r in items}),
                                  'record_ids':[r['id'] for r in items],'notice':'Repeated counterparty or description. Not proof of an unwanted subscription.'})
        small=[r for r in rows if r['date'][:7]==month and r['kind']=='expense' and r['amount_fen']<=2000]
        return {'tool':'monthly_review','month':month,'comparison':comparison,'recurring':recurring[:20],
                'small_payments':{'count':len(small),'total_fen':sum(r['amount_fen'] for r in small),'record_ids':[r['id'] for r in small]},
                'record_ids':sorted(set(comparison['record_ids']+[i for group in recurring[:20] for i in group['record_ids']])),
                'notice':'Only record patterns are reported. Ask the user before inferring motivation or cancelling a subscription.'}

    def dispatch(self,name,raw):
        approved={'query_transactions':self.query_transactions,'compare_periods':self.compare_periods,
                  'generate_savings_plans':self.generate_savings_plans,'monthly_review':self.monthly_review}
        if name=='retrieve_category_memories':
            fields(raw,('record_id',))
            if type(raw.get('record_id')) is not int:
                raise DomainError('Record ID must be an integer.')
            record=next((r for r in self.ledger.transactions() if r['id']==raw['record_id']),None)
            if not record:
                raise DomainError('Record does not exist.')
            memories=self.ledger.memory.retrieve(record)
            return {'tool':name,'record_ids':[record['id']],'memories':[{k:m[k] for k in ('id','kind','category','purpose','match','matches','auto_apply')} for m in memories]}
        if name not in approved:
            raise DomainError('Tool is not approved.')
        return approved[name](raw)
