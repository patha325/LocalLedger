"""Local file reading, multilingual header hints and explicit transaction mapping."""
import csv
import io
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from numbers import Real
import pandas as pd
from finance import money

ALIASES = {
 'date': ['date','transaction date','booking date','datum','bokföringsdatum','transaktionsdatum','valutadatum','buchungsdatum','buchungstag','fecha','fecha operación','date opération'],
 'description': ['description','details','merchant','text','beskrivning','meddelande','mottagare','transaktion','verwendungszweck','buchungstext','beschreibung','libellé','désignation','concepto','descripción'],
 'amount': ['amount','signed amount','belopp','summa','betrag','montant','importe'],
 'debit': ['debit','withdrawal','withdrawals','uttag','utbetalning','debet','soll','débit','cargo','gasto'],
 'credit': ['credit','deposit','deposits','insättning','inbetalning','kredit','haben','crédit','abono','ingreso'],
 'id': ['transaction id','reference','referens','transaktionsid','referencia','référence','referenz'],
}
def normalise(text):
 return ' '.join(''.join(c if c.isalnum() else ' ' for c in unicodedata.normalize('NFKD',str(text)).casefold() if not unicodedata.combining(c)).split())

def suggest_columns(columns):
 """Only exact normalised aliases are suggested; ambiguity stays unmapped."""
 result={}
 for role,aliases in ALIASES.items():
  matches=[c for c in columns if normalise(c) in {normalise(a) for a in aliases}]
  result[role]=matches[0] if len(matches)==1 else None
 return result

def read_table(payload,filename,header=0,sheet=0,delimiter=',',encoding='utf-8-sig'):
 if filename.lower().endswith(('.xls','.xlsx')):
  engine='xlrd' if filename.lower().endswith('.xls') else 'openpyxl'
  frame=pd.read_excel(io.BytesIO(payload),sheet_name=sheet,header=header,engine=engine,dtype=object,keep_default_na=False)
 else:
  frame=pd.read_csv(io.StringIO(payload.decode(encoding)),sep=delimiter,header=header,dtype=str,keep_default_na=False)
 frame=frame.dropna(how='all')
 frame=frame.loc[~frame.apply(lambda row:all(str(v).strip()=='' for v in row),axis=1)]
 frame.columns=[str(c).strip() for c in frame.columns]
 if not len(frame.columns) or len(set(frame.columns))!=len(frame.columns):raise ValueError('Headers must be nonempty and unique. Select another header row.')
 return frame

def sheet_names(payload,filename):
 engine='xlrd' if filename.lower().endswith('.xls') else 'openpyxl'
 with pd.ExcelFile(io.BytesIO(payload),engine=engine) as book:return book.sheet_names

def mapped_csv(frame,mapping,date_format='%Y-%m-%d',decimal='.',split=False,reverse=False):
 required=['date','description']+(['debit','credit'] if split else ['amount'])
 if any(not mapping.get(k) or mapping[k] not in frame.columns for k in required):raise ValueError('Map all required columns first')
 chosen=[mapping[k] for k in required]
 if len(set(chosen))!=len(chosen):raise ValueError('Each required field must use a different column')
 def amount(v):
  if v is None or str(v).strip()=='':return 0
  # Native Excel numbers have no locale separators. Text cells use the chosen locale.
  return money(str(v),'.') if isinstance(v,(Real,Decimal)) and not isinstance(v,bool) else money(v,decimal)
 output=io.StringIO();writer=csv.writer(output);writer.writerow(['date','description','amount','id'])
 preview=[]
 for rownum,(_,r) in enumerate(frame.iterrows(),1):
  try:
   value=r[mapping['date']]
   if isinstance(value,(datetime,date,pd.Timestamp)):day=value.date().isoformat() if isinstance(value,datetime) else value.isoformat()
   else:day=datetime.strptime(str(value).strip(),date_format).date().isoformat()
   if split:
    debit=amount(r[mapping['debit']]);credit=amount(r[mapping['credit']])
    if debit and credit:raise ValueError('Both debit and credit are populated')
    cents=abs(credit)-abs(debit)
   else:cents=amount(r[mapping['amount']])
   if reverse:cents=-cents
   desc=str(r[mapping['description']]).strip()
   if not desc:raise ValueError('Description is empty')
   ident=str(r[mapping['id']]).strip() if mapping.get('id') else ''
   signed=format(Decimal(cents)/100,'.2f');writer.writerow([day,desc,signed,ident]);preview.append({'date':day,'description':desc,'amount':signed,'id':ident})
  except Exception as exc:raise ValueError(f'Data row {rownum}: {exc}') from exc
 return output.getvalue(),pd.DataFrame(preview)
