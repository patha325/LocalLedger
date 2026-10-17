import unittest,sys
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from importing import suggest_columns,read_table,mapped_csv
from finance import Ledger
class ImportTests(unittest.TestCase):
 def test_languages(self):
  for columns in [['Datum','Beskrivning','Belopp'],['Date','Libellé','Montant'],['Fecha','Descripción','Importe'],['Buchungsdatum','Verwendungszweck','Betrag']]:
   hints=suggest_columns(columns)
   self.assertEqual([hints[k] for k in ['date','description','amount']],columns)
 def test_ambiguity(self):
  self.assertIsNone(suggest_columns(['date','booking date'])['date'])
  self.assertIsNone(suggest_columns(['running balance'])['amount'])
 def test_swedish_csv_to_ledger(self):
  f=read_table('Datum;Text;Belopp\n2026-10-01;ICA;-1 234,50'.encode(),'bank.csv',delimiter=';')
  data,preview=mapped_csv(f,suggest_columns(f.columns),decimal=',')
  ledger=Ledger(':memory:');ledger.add_account('Bank','A','SEK')
  ledger.import_csv(data,1,'date','description','amount')
  self.assertEqual(ledger.rows()[0]['amount'],-123450)
 def test_native_dates_numbers(self):
  f=pd.DataFrame({'Date':[datetime(2026,10,1)],'Text':['Shop'],'Amount':[-1234.50]})
  data,preview=mapped_csv(f,suggest_columns(f.columns),decimal=',')
  self.assertEqual(preview.iloc[0]['amount'],'-1234.50')
  self.assertEqual(preview.iloc[0]['date'],'2026-10-01')
 def test_split_and_reverse(self):
  f=pd.DataFrame({'date':['01/10/2026','02/10/2026'],'text':['Shop','Salary'],'debit':['2,50',''],'credit':['','100,00']})
  _,p=mapped_csv(f,suggest_columns(f.columns),'%d/%m/%Y',',',True)
  self.assertEqual(p.amount.tolist(),['-2.50','100.00'])
  f.loc[0,'credit']='1'
  with self.assertRaises(ValueError):mapped_csv(f,suggest_columns(f.columns),'%d/%m/%Y',',',True)
 def test_unknown_and_reused_mapping(self):
  f=pd.DataFrame({'a':['x']})
  with self.assertRaises(ValueError):mapped_csv(f,{'date':'a','description':'a','amount':'a'})
 def test_excel_engines_and_header(self):
  for extension,engine in [('xls','xlrd'),('xlsx','openpyxl')]:
   with patch('importing.pd.read_excel',return_value=pd.DataFrame({'Date':['2026-10-01'],'Text':['X'],'Amount':[2]})) as read:
    read_table(b'fixture','bank.'+extension,header=3,sheet='Transactions')
    self.assertEqual(read.call_args.kwargs['engine'],engine)
    self.assertEqual(read.call_args.kwargs['header'],3)
    self.assertEqual(read.call_args.kwargs['sheet_name'],'Transactions')
 def test_invalid_date_blocks(self):
  f=pd.DataFrame({'date':['bad'],'text':['Shop'],'amount':['1.00']})
  with self.assertRaisesRegex(ValueError,'Data row 1'):mapped_csv(f,suggest_columns(f.columns))
