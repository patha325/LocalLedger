import unittest,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ai
class AIIntegration(unittest.TestCase):
 def test_real_ollaborate_structured_adapter(self):
  async def chat(client,**kwargs):
   self.assertIn('category',kwargs['format']['properties'])
   return SimpleNamespace(message=SimpleNamespace(tool_calls=[],content='{"category":"Groceries","reason":"Grocery merchant"}'))
  with patch('ai.require_local'),patch('ollama.AsyncClient.chat',chat):
   result=ai.suggest('ICA','local-test')
   self.assertEqual(result.category,'Groceries')
 def test_cloud_rejected(self):
  with self.assertRaises(ValueError):ai.require_local('model-cloud')
