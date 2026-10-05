"""Exact-money household ledger. No model participates in arithmetic."""
import sqlite3, csv, io, hashlib, json
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from collections import Counter

CATEGORIES = ['Uncategorised','Groceries','Housing','Transport','Children','Restaurants','Subscriptions','Health','Shopping','Salary','Other income','Refund']

def money(value, decimal=','):
    value = str(value).strip().replace('\u00a0','').replace(' ','').replace('−','-')
    if decimal == ',': value = value.replace('.','').replace(',','.')
    else: value = value.replace(',','')
    x = Decimal(value)
    if not x.is_finite() or x != x.quantize(Decimal('.01')): raise ValueError('Amount must have at most two decimal places')
    return int(x * 100)

class Ledger:
    def __init__(self, path):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,owner TEXT NOT NULL,currency TEXT NOT NULL,opening INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY,account INTEGER NOT NULL REFERENCES accounts(id),day TEXT NOT NULL,description TEXT NOT NULL,amount INTEGER NOT NULL,category TEXT NOT NULL DEFAULT 'Uncategorised',fingerprint TEXT NOT NULL UNIQUE,transfer INTEGER REFERENCES transfers(id));
        CREATE TABLE IF NOT EXISTS transfers(id INTEGER PRIMARY KEY,debit INTEGER NOT NULL UNIQUE REFERENCES transactions(id),credit INTEGER NOT NULL UNIQUE REFERENCES transactions(id));
        CREATE TABLE IF NOT EXISTS rules(merchant TEXT PRIMARY KEY,category TEXT NOT NULL);
        ''')
    def accounts(self): return [dict(r) for r in self.db.execute('SELECT * FROM accounts ORDER BY name')]
    def add_account(self,name,owner,currency,opening=0):
        if not name.strip() or not owner.strip() or currency not in ['SEK','EUR','GBP','USD']: raise ValueError('Name, owner and supported currency required')
        with self.db:self.db.execute('INSERT INTO accounts(name,owner,currency,opening) VALUES(?,?,?,?)',(name.strip(),owner.strip(),currency,opening))
    def rows(self):
        return [dict(r) for r in self.db.execute('SELECT t.*,a.name,a.owner,a.currency FROM transactions t JOIN accounts a ON a.id=t.account ORDER BY day,id')]
    def import_csv(self,text,account,day_col,desc_col,amount_col,date_format='%Y-%m-%d',decimal='.',delimiter=',',id_col=None):
        if not any(a['id']==account for a in self.accounts()): raise ValueError('Unknown account')
        parsed=[]; counts=Counter(); rules=dict(self.db.execute('SELECT merchant,category FROM rules'))
        for line,r in enumerate(csv.DictReader(io.StringIO(text),delimiter=delimiter),2):
            try:
                d=datetime.strptime(r[day_col].strip(),date_format).date().isoformat(); desc=r[desc_col].strip(); amount=money(r[amount_col],decimal)
                if not desc: raise ValueError('Empty description')
                base=json.dumps([account,d,desc,amount],ensure_ascii=False); counts[base]+=1
                key=json.dumps([account,'bank-id',r[id_col]]) if id_col and r[id_col] else base+':'+str(counts[base])
                fp=hashlib.sha256(key.encode()).hexdigest(); category=rules.get(desc.casefold(),'Uncategorised')
                parsed.append((account,d,desc,amount,category,fp))
            except (ValueError,KeyError,InvalidOperation) as e: raise ValueError(f'Row {line}: {e}') from e
        before=self.db.total_changes
        with self.db:self.db.executemany('INSERT OR IGNORE INTO transactions(account,day,description,amount,category,fingerprint) VALUES(?,?,?,?,?,?)',parsed)
        added=self.db.total_changes-before
        return {'added':added,'duplicates':len(parsed)-added}
    def categorise(self,tid,category,remember=False):
        if category not in CATEGORIES: raise ValueError('Invalid category')
        row=self.db.execute('SELECT description FROM transactions WHERE id=?',(tid,)).fetchone()
        if not row:raise ValueError('Unknown transaction')
        with self.db:
            self.db.execute('UPDATE transactions SET category=? WHERE id=?',(category,tid))
            if remember:self.db.execute('INSERT OR REPLACE INTO rules VALUES(?,?)',(row[0].casefold(),category))
    def candidates(self,days=3):
        rows=[r for r in self.rows() if r['transfer'] is None]; result=[]
        for a in rows:
            if a['amount']>=0:continue
            for b in rows:
                if b['account']==a['account'] or b['currency']!=a['currency'] or b['amount']!=-a['amount']:continue
                if abs((date.fromisoformat(a['day'])-date.fromisoformat(b['day'])).days)<=days:result.append((a,b))
        return result
    def link(self,debit,credit):
        rows={r['id']:r for r in self.rows()}; a=rows[debit];b=rows[credit]
        if a['transfer'] or b['transfer'] or a['amount']>=0 or a['amount']!=-b['amount'] or a['account']==b['account'] or a['currency']!=b['currency']:raise ValueError('Transfers require unlinked opposite amounts in different accounts with the same currency')
        with self.db:
            cursor=self.db.execute('INSERT INTO transfers(debit,credit) VALUES(?,?)',(debit,credit))
            self.db.execute('UPDATE transactions SET transfer=? WHERE id IN (?,?)',(cursor.lastrowid,debit,credit))
    def unlink(self,transfer):
        with self.db:
            self.db.execute('UPDATE transactions SET transfer=NULL WHERE transfer=?',(transfer,))
            self.db.execute('DELETE FROM transfers WHERE id=?',(transfer,))
    def summary(self,currency,owners=None):
        rows=[r for r in self.rows() if r['currency']==currency and (owners is None or r['owner'] in owners)]
        # A household transfer remains neutral in person views; account balances retain both legs.
        months={}; cats={}
        for r in rows:
            m=r['day'][:7]; v=months.setdefault(m,{'month':m,'income':0,'expenses':0,'net':0,'transfers':0})
            if r['transfer']:
                v['transfers']+=abs(r['amount']);continue
            if r['amount']>0 and r['category']!='Refund':v['income']+=r['amount']
            else:
                expense=-r['amount'];v['expenses']+=expense;cats[r['category']]=cats.get(r['category'],0)+expense
            v['net']=v['income']-v['expenses']
        return {'months':sorted(months.values(),key=lambda r:r['month']), 'categories':cats,'transaction_ids':[r['id'] for r in rows if not r['transfer']]}
    def balances(self):
        return [{**a,'balance':a['opening']+sum(r['amount'] for r in self.rows() if r['account']==a['id'])} for a in self.accounts()]
