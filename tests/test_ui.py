import unittest,tempfile,shutil
from pathlib import Path
from streamlit.testing.v1 import AppTest
class Dashboard(unittest.TestCase):
 def test_demo(self):
  root=Path(__file__).resolve().parents[1]
  with tempfile.TemporaryDirectory() as folder:
   app=Path(folder)
   for name in ['app.py','finance.py','ai.py']:shutil.copy(root/name,app/name)
   shutil.copytree(root/'examples',app/'examples')
   at=AppTest.from_file(str(app/'app.py')).run()
   self.assertEqual(len(at.exception),0)
   at.sidebar.button[0].click().run()
   self.assertEqual(len(at.exception),0)
   self.assertEqual(at.metric[0].value,'80,035.00 SEK')
   self.assertEqual(at.metric[1].value,'17,650.50 SEK')
