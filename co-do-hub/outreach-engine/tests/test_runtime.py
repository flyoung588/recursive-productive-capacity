import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
P=Path(__file__).resolve().parents[1]/'runtime.py'
S=importlib.util.spec_from_file_location('runtime',P)
m=importlib.util.module_from_spec(S); S.loader.exec_module(m)

class RuntimeTest(unittest.TestCase):
    def test_citation_membership_rejects_hallucination(self):
        m.Runtime.validate_urls({'source_urls':['https://example.org/a']},{'https://example.org/a'})
        with self.assertRaises(ValueError):
            m.Runtime.validate_urls({'source_urls':['https://fake.org/b']},{'https://example.org/a'})
    def test_private_addresses_rejected(self):
        with patch.object(m.socket,'getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError): m.public_url('https://localhost/')
        with self.assertRaises(ValueError): m.public_url('file:///etc/passwd')
    def test_checkpoint_no_model_when_completed_negative_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=m.Runtime(tmp); f=Path(tmp)/'runs'/'one'
            m.save(f/'discovery.json',{'sources':[],'search':{'items':[]}})
            m.save(f/'interpretation.json',{'identity_status':'CONFIRMED'})
            m.save(f/'competitors.json',{'sources':[],'searches':[]})
            m.save(f/'lessons.json',{'lessons':[]})
            m.save(f/'intersection.json',{'status':'NO_CREDIBLE_INTERSECTION'})
            with patch.object(r,'model',side_effect=AssertionError('No repeat call')):
                self.assertEqual(r.run('new person','one')['status'],'NO_CREDIBLE_INTERSECTION')
            with self.assertRaises(ValueError): r.run('different person','one')
            self.assertEqual((f/'state.json').stat().st_mode & 0o777,0o600)
    def test_error_persists_for_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=m.Runtime(tmp)
            with patch.object(r,'search',side_effect=RuntimeError('retrieval unavailable')):
                with self.assertRaises(RuntimeError): r.run('new person','error')
            self.assertEqual(m.load(Path(tmp)/'runs/error/state.json')['status'],'FAILED')
    def test_protocol_does_not_accept_other_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=m.Runtime(tmp)
            with patch.object(r,'command',return_value={'model':'gpt-6-astra','provider':'openai'}):
                with self.assertRaises(ValueError): r.model('task',{},Path(tmp)/'call.json')
    def test_json_object_required(self):
        self.assertEqual(m.parse_json('```json\n{"ok":true}\n```'),{'ok':True})
        with self.assertRaises(ValueError): m.parse_json('[]')

if __name__=='__main__': unittest.main()
