import unittest,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from finance import Ledger,money
class Tests(unittest.TestCase):
 def setUp(self):
  self.l=Ledger(':memory:')
  self.l.add_account('A','Alex','SEK');self.l.add_account('B','Sam','SEK');self.l.add_account('C','Alex','EUR')
 def load(self,text,account=1):return self.l.import_csv(text,account,'date','description','amount')
 def test_transfer_across_months_and_people(self):
  self.load('date,description,amount\n2026-09-30,Salary,100.00\n2026-09-30,Transfer,-40.00')
  self.load('date,description,amount\n2026-10-01,Transfer,40.00',2)
  self.l.link(2,3)
  self.assertEqual(self.l.summary('SEK')['months'][0]['income'],10000)
  self.assertEqual(self.l.summary('SEK')['months'][0]['expenses'],0)
  self.assertEqual(self.l.summary('SEK')['months'][1]['income'],0)
  self.assertEqual(self.l.summary('SEK',['Sam'])['months'][0]['income'],0)
  self.assertEqual(sum(a['balance'] for a in self.l.balances() if a['currency']=='SEK'),10000)
  self.l.unlink(1);self.assertEqual(self.l.summary('SEK')['months'][1]['income'],4000)
 def test_duplicates_and_repeated_rows(self):
  text='date,description,amount\n2026-09-01,Shop,-2.00\n2026-09-01,Shop,-2.00'
  self.assertEqual(self.load(text)['added'],2);self.assertEqual(self.load(text)['duplicates'],2)
 def test_atomic_invalid_import(self):
  with self.assertRaises(ValueError):self.load('date,description,amount\n2026-09-01,Shop,-2.00\nbad,Shop,1')
  self.assertEqual(self.l.rows(),[])
 def test_currency_and_invalid_transfer(self):
  self.load('date,description,amount\n2026-09-01,Transfer,-2.00')
  self.load('date,description,amount\n2026-09-01,Transfer,2.00',3)
  self.assertEqual(self.l.candidates(),[])
  with self.assertRaises(ValueError):self.l.link(1,2)
 def test_refund(self):
  self.load('date,description,amount\n2026-09-01,Shop,-20.00\n2026-09-02,Refund,5.00')
  self.l.categorise(2,'Refund');s=self.l.summary('SEK')['months'][0]
  self.assertEqual((s['income'],s['expenses'],s['net']),(0,1500,-1500))
 def test_swedish_and_rule(self):
  self.l.import_csv('Datum;Text;Belopp\n01.09.2026;ICA;-1 234,50',1,'Datum','Text','Belopp','%d.%m.%Y',',',';')
  self.assertEqual(self.l.rows()[0]['amount'],-123450)
  self.l.categorise(1,'Groceries',True)
  self.load('date,description,amount\n2026-09-02,ICA,-2.00')
  self.assertEqual(self.l.rows()[1]['category'],'Groceries')
 def test_bank_id(self):
  text='date,description,amount,id\n2026-09-01,Shop,-2.00,X'
  for _ in range(2):self.l.import_csv(text,1,'date','description','amount',id_col='id')
  self.assertEqual(len(self.l.rows()),1)
 def test_minor_units(self):
  self.assertEqual(money('1 000,01'),100001)
  for value in ['NaN','1.001']:
   with self.assertRaises(ValueError):money(value,'.')
if __name__=='__main__':unittest.main()
