"""A goal journey with auditable allocations and server-earned cosmetic rewards.

Allocations are user-reported earmarked savings, not bank-verified deposits or
ledger transactions. Financial tools never mutate this module. Reward hooks run
in the same transaction as confirmed human ledger operations.
"""
import json
import re
from datetime import date, datetime, timedelta, timezone
from .domain import DomainError, money, validate_month

CHINA = timezone(timedelta(hours=8))
LEVELS = ((0,'初识星光'),(60,'营地探索者'),(150,'习惯养成者'),(300,'目标开拓者'),
          (500,'财务领航员'),(800,'远征守护者'),(1200,'星光筑梦师'))
THEMES = (('forest','森野营地',1),('ocean','海岛灯塔',2),('space','星际航线',4))
MILESTONES = ((25,30,'点亮营火'),(50,40,'搭起树屋'),(75,50,'建好观景台'),(100,80,'抵达梦想之境'))
DAILY = (('import','整理新账单','导入至少一笔未重复的账单',10,'import'),
         ('review','弄清一笔消费','确认一笔待审核账单的实际用途',15,'review'),
         ('reflect','写下复盘心得','选择有支出的月份，记录一句具体反思',20,'reflect'))
BADGES = (('first_goal','启程者','设立自己的第一个目标','flag'),
          ('first_import','账单整理员','首次导入新账单','book'),
          ('first_review','细心侦探','首次确认待审核消费','search'),
          ('first_memory','记忆种子','保存一条确认用途的分类记忆','seed'),
          ('first_plan','路线规划师','审核并保存一份储蓄测算或方案','map'),
          ('first_reflection','复盘笔记','记录第一篇消费复盘心得','note'),
          ('first_finish','梦想兑现者','通过新的储蓄记录首次抵达目标','star'),
          ('first_week','稳步前行','一周内完成三个不同日期的财务行动','sun'))


def fields(raw, allowed):
    if not isinstance(raw,dict) or set(raw)-set(allowed):
        raise DomainError('冒险请求包含无效字段。')


def text(value, name, limit, required=True):
    if not isinstance(value,str) or len(value)>limit or (required and not value.strip()):
        raise DomainError(f'{name}须为{1 if required else 0}至{limit}个字符。')
    return value.strip()


def request_id(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{32}',value):
        raise DomainError('操作编号无效，请重新打开表单。')
    return value


class Adventure:
    def __init__(self,ledger,clock=None):
        self.ledger=ledger
        self.clock=clock or (lambda:datetime.now(CHINA))
        with ledger.connection() as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS adventure_goals(
              id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,target_fen INTEGER NOT NULL CHECK(target_fen>0),
              initial_fen INTEGER NOT NULL CHECK(initial_fen>=0),deadline TEXT,archived INTEGER NOT NULL DEFAULT 0,
              request_id TEXT NOT NULL UNIQUE,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS adventure_entries(
              id INTEGER PRIMARY KEY AUTOINCREMENT,goal_id INTEGER NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('deposit','withdraw')),
              amount_fen INTEGER NOT NULL CHECK(amount_fen>0),note TEXT NOT NULL,request_id TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS adventure_rewards(
              key TEXT PRIMARY KEY,xp INTEGER NOT NULL CHECK(xp>=0),title TEXT NOT NULL,
              day TEXT NOT NULL,created_at TEXT NOT NULL,kind TEXT NOT NULL,goal_id INTEGER);
            CREATE TABLE IF NOT EXISTS adventure_reflections(
              day TEXT PRIMARY KEY,month TEXT NOT NULL,note TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS adventure_goal_entries ON adventure_entries(goal_id);
            CREATE INDEX IF NOT EXISTS adventure_reward_days ON adventure_rewards(day);
            ''')

    def now(self):
        return self.clock().astimezone(CHINA)

    def award(self,con,key,xp,title,kind='badge',goal_id=None):
        if con.execute('SELECT 1 FROM adventure_rewards WHERE key=?',(key,)).fetchone():
            return False
        today=self.now().date().isoformat()
        if kind=='milestone':
            used=con.execute("SELECT COALESCE(SUM(xp),0) FROM adventure_rewards WHERE day=? AND kind='milestone'",(today,)).fetchone()[0]
            xp=min(xp,max(0,200-used))
        con.execute('INSERT INTO adventure_rewards VALUES(?,?,?,?,?,?,?)',
                    (key,xp,title,today,self.now().isoformat(),kind,goal_id))
        return True

    def weekly(self,con):
        today=self.now().date();monday=today-timedelta(days=today.weekday())
        active=con.execute('SELECT COUNT(DISTINCT day) FROM adventure_rewards WHERE xp>0 AND day BETWEEN ? AND ?',
                           (monday.isoformat(),today.isoformat())).fetchone()[0]
        if active>=3:
            self.award(con,'week:'+monday.isoformat(),35,'完成本周三日行动','weekly')
            self.award(con,'badge:first_week',0,'稳步前行')

    def daily(self,con,key):
        spec=next(item for item in DAILY if item[0]==key)
        self.award(con,f'daily:{self.now().date().isoformat()}:{key}',spec[3],spec[1],'daily')

    def track(self,con,action,details):
        """Only trusted audit calls invoke this hook, never arbitrary client events."""
        if action=='import' and details.get('inserted_ids'):
            self.daily(con,'import');self.award(con,'badge:first_import',20,'账单整理员')
        elif action in ('edit','confirm_purpose'):
            before=details.get('before',{})
            after=details.get('after',details)
            if before.get('review_status')=='needs_review' and (before.get('kind'),before.get('category'))!=(after.get('kind'),after.get('category')):
                self.daily(con,'review');self.award(con,'badge:first_review',20,'细心侦探')
            elif action=='confirm_purpose' and before.get('review_status')=='needs_review':
                self.daily(con,'review');self.award(con,'badge:first_review',20,'细心侦探')
            if action=='confirm_purpose' and details.get('memory_id'):
                self.award(con,'badge:first_memory',25,'记忆种子')
        elif action in ('plan','generated_plan_save'):
            self.award(con,'badge:first_plan',20,'路线规划师')
        else:
            return
        self.weekly(con)

    @staticmethod
    def balance(con,goal):
        net=con.execute("SELECT COALESCE(SUM(CASE WHEN kind='deposit' THEN amount_fen ELSE -amount_fen END),0) FROM adventure_entries WHERE goal_id=?",(goal['id'],)).fetchone()[0]
        return goal['initial_fen']+net

    @staticmethod
    def goal(con,goal_id):
        if type(goal_id) is not int or goal_id<=0:
            raise DomainError('请选择有效的储蓄目标。')
        row=con.execute('SELECT * FROM adventure_goals WHERE id=?',(goal_id,)).fetchone()
        if row is None:raise DomainError('未找到这个储蓄目标。')
        return dict(row)

    def create_goal(self,raw):
        fields(raw,('title','target','initial','deadline','request_id'))
        title=text(raw.get('title'),'目标名称',60)
        target=money(raw.get('target'));initial=money(raw.get('initial',0),allow_zero=True)
        if initial>target:raise DomainError('已有储蓄不能高于目标金额，请调整目标。')
        deadline=raw.get('deadline')
        if deadline=='':deadline=None
        if deadline is not None:
            if not isinstance(deadline,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',deadline):
                raise DomainError('目标日期格式无效。')
            try:due=date.fromisoformat(deadline)
            except ValueError:raise DomainError('目标日期无效。') from None
        key=request_id(raw.get('request_id'))
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            previous=con.execute('SELECT * FROM adventure_goals WHERE request_id=?',(key,)).fetchone()
            if previous:
                if (previous['title'],previous['target_fen'],previous['initial_fen'],previous['deadline'])!=(title,target,initial,deadline):
                    raise DomainError('此操作编号已经使用，请重新打开表单。')
                return {'id':previous['id'],'saved':True,'replayed':True}
            if deadline and due<self.now().date():raise DomainError('新目标日期不能早于今天。')
            if con.execute('SELECT COUNT(*) FROM adventure_goals WHERE archived=0').fetchone()[0]>=3:
                raise DomainError('最多同时进行三个目标，请先归档一个目标。')
            cursor=con.execute('INSERT INTO adventure_goals(title,target_fen,initial_fen,deadline,request_id,created_at) VALUES(?,?,?,?,?,?)',
                               (title,target,initial,deadline,key,self.now().isoformat()))
            goal_id=cursor.lastrowid
            self.award(con,'badge:first_goal',20,'启程者')
            # Previously saved money establishes the starting point, not new XP.
            for percent,_,name in MILESTONES:
                if initial*100>=target*percent:
                    self.award(con,f'milestone:{goal_id}:{percent}',0,'起点已达到：'+name,'initial',goal_id)
            self.weekly(con)
            self.ledger.audit(con,'adventure_goal',{'id':goal_id,'title':title,'target_fen':target,'current_fen':initial,'deadline':deadline})
        return {'id':goal_id,'saved':True,'replayed':False}

    def add_entry(self,raw):
        fields(raw,('goal_id','kind','amount','note','request_id'))
        kind=raw.get('kind')
        if kind not in ('deposit','withdraw'):raise DomainError('请选择存入或取回。')
        amount=money(raw.get('amount'));note=text(raw.get('note',''),'备注',200,False)
        key=request_id(raw.get('request_id'))
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            goal=self.goal(con,raw.get('goal_id'))
            old=con.execute('SELECT * FROM adventure_entries WHERE request_id=?',(key,)).fetchone()
            if old:
                if (old['goal_id'],old['kind'],old['amount_fen'],old['note'])!=(goal['id'],kind,amount,note):
                    raise DomainError('此操作编号已经使用，请重新打开表单。')
                return {'id':old['id'],'saved':True,'replayed':True,'balance_fen':self.balance(con,goal)}
            if goal['archived']:raise DomainError('目标已归档，不能再更新金额。')
            current=self.balance(con,goal)
            if kind=='withdraw' and amount>current:raise DomainError('取回金额不能超过此目标已记录的储蓄。')
            updated=current+amount*(1 if kind=='deposit' else -1)
            if updated>10000000000:raise DomainError('目标储蓄不能超过 1 亿元。')
            cursor=con.execute('INSERT INTO adventure_entries(goal_id,kind,amount_fen,note,request_id,created_at) VALUES(?,?,?,?,?,?)',
                               (goal['id'],kind,amount,note,key,self.now().isoformat()))
            if kind=='deposit':
                for percent,xp,name in MILESTONES:
                    if updated*100>=goal['target_fen']*percent:
                        self.award(con,f"milestone:{goal['id']}:{percent}",xp,name,'milestone',goal['id'])
                if current<goal['target_fen']<=updated:
                    self.award(con,'badge:first_finish',0,'梦想兑现者')
            self.weekly(con)
            self.ledger.audit(con,'adventure_entry',{'id':cursor.lastrowid,'goal_id':goal['id'],'kind':kind,'amount_fen':amount,'note':note,'current_fen':updated})
        return {'id':cursor.lastrowid,'saved':True,'replayed':False,'balance_fen':updated}

    def archive_goal(self,raw):
        fields(raw,('goal_id','archived'))
        if type(raw.get('archived')) is not bool:raise DomainError('归档状态须为是或否。')
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE');goal=self.goal(con,raw.get('goal_id'))
            if not raw['archived'] and goal['archived'] and con.execute('SELECT COUNT(*) FROM adventure_goals WHERE archived=0').fetchone()[0]>=3:
                raise DomainError('最多同时进行三个目标，请先归档一个目标。')
            if bool(goal['archived'])!=raw['archived']:
                con.execute('UPDATE adventure_goals SET archived=? WHERE id=?',(int(raw['archived']),goal['id']))
                self.ledger.audit(con,'adventure_archive',{'goal_id':goal['id'],'archived':raw['archived']})
        return {'id':goal['id'],'archived':raw['archived']}

    def reflect(self,raw):
        fields(raw,('month','note'))
        month=validate_month(raw.get('month'));note=text(raw.get('note'),'复盘心得',300)
        if len(note)<5:raise DomainError('请写下至少五个字的具体复盘心得。')
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            if not con.execute("SELECT 1 FROM transactions WHERE date LIKE ? AND kind='expense'",(month+'-%',)).fetchone():
                raise DomainError('该月还没有支出账单，请先导入再复盘。')
            today=self.now().date().isoformat()
            previous=con.execute('SELECT * FROM adventure_reflections WHERE day=?',(today,)).fetchone()
            con.execute('INSERT OR REPLACE INTO adventure_reflections VALUES(?,?,?,?)',(today,month,note,self.now().isoformat()))
            self.daily(con,'reflect');self.award(con,'badge:first_reflection',25,'复盘笔记');self.weekly(con)
            if not previous or (previous['month'],previous['note'])!=(month,note):
                self.ledger.audit(con,'adventure_reflect',{'month':month,'note':note})
        return {'saved':True,'updated':bool(previous)}

    def set_theme(self,raw):
        fields(raw,('theme',));theme=raw.get('theme')
        spec=next((item for item in THEMES if item[0]==theme),None)
        if not spec:raise DomainError('冒险主题无效。')
        with self.ledger.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            xp=con.execute('SELECT COALESCE(SUM(xp),0) FROM adventure_rewards').fetchone()[0]
            level=sum(xp>=threshold for threshold,_ in LEVELS)
            if level<spec[2]:raise DomainError('此主题尚未解锁，完成任务提升等级后再来。')
            con.execute("INSERT OR REPLACE INTO settings VALUES('adventure_theme',?)",(theme,))
        return {'theme':theme}

    def state(self):
        today=self.now().date();monday=today-timedelta(days=today.weekday())
        with self.ledger.connection() as con:
            con.execute('BEGIN')
            rewards=[dict(r) for r in con.execute('SELECT * FROM adventure_rewards ORDER BY created_at DESC,key DESC')]
            keys={r['key'] for r in rewards};xp=sum(r['xp'] for r in rewards)
            level=sum(xp>=threshold for threshold,_ in LEVELS)
            threshold,title=LEVELS[level-1];next_xp=LEVELS[level][0] if level<len(LEVELS) else None
            goals=[]
            for row in con.execute('SELECT * FROM adventure_goals ORDER BY archived,id DESC LIMIT 30').fetchall():
                goal=dict(row);balance=self.balance(con,goal);goal.pop('request_id')
                goal.update(balance_fen=balance,remaining_fen=max(0,goal['target_fen']-balance),
                            progress_pct=min(100,balance*100//goal['target_fen']),archived=bool(goal['archived']),
                            complete=balance>=goal['target_fen'],days_left=(date.fromisoformat(goal['deadline'])-today).days if goal['deadline'] else None,
                            milestones=[{'percent':p,'xp':value,'title':name,'reached':balance*100>=goal['target_fen']*p,
                                         'collected':f"milestone:{goal['id']}:{p}" in keys} for p,value,name in MILESTONES])
                goals.append(goal)
            entries=[dict(r) for r in con.execute('SELECT e.id,e.goal_id,g.title AS goal_title,e.kind,e.amount_fen,e.note,e.created_at FROM adventure_entries e JOIN adventure_goals g ON g.id=e.goal_id ORDER BY e.id DESC LIMIT 12')]
            theme_row=con.execute("SELECT value FROM settings WHERE key='adventure_theme'").fetchone()
            reflection=con.execute('SELECT month,note FROM adventure_reflections WHERE day=?',(today.isoformat(),)).fetchone()
        days=sorted({date.fromisoformat(r['day']) for r in rewards if r['xp']>0 and r['day']<=today.isoformat()})
        active=set(days);anchor=today if today in active else today-timedelta(days=1);streak=0
        while anchor in active:streak+=1;anchor-=timedelta(days=1)
        weekly_days=sum(monday<=day<=today for day in active)
        return {'today':today.isoformat(),'suggested_deadline':(today+timedelta(days=180)).isoformat(),
                'xp':xp,'level':level,'level_title':title,'level_start_xp':threshold,'next_level_xp':next_xp,
                'streak':streak,'weekly_days':weekly_days,'weekly_complete':'week:'+monday.isoformat() in keys,
                'theme':theme_row['value'] if theme_row else 'forest',
                'themes':[{'id':code,'title':name,'level':required,'unlocked':level>=required} for code,name,required in THEMES],
                'daily_quests':[{'id':key,'title':name,'description':desc,'xp':value,'action':action,
                                 'complete':f'daily:{today.isoformat()}:{key}' in keys} for key,name,desc,value,action in DAILY],
                'badges':[{'id':code,'title':name,'description':desc,'icon':icon,'earned':'badge:'+code in keys} for code,name,desc,icon in BADGES],
                'goals':goals,'entries':entries,'recent_rewards':rewards[:8],
                'reflection':dict(reflection) if reflection else None}
