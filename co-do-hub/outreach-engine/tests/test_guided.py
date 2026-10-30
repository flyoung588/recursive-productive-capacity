import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
S=importlib.util.spec_from_file_location('guided',Path(__file__).resolve().parents[1]/'runtime.py')
m=importlib.util.module_from_spec(S);S.loader.exec_module(m)


def plan(prefix):
    return {'candidates':[{'id':str(i),'question':prefix+str(i),'distinct_mechanism':'mechanism '+str(i),
             'falsification_queries':[prefix+' strong existing result '+str(i)]} for i in range(3)],
            'no_invite_option':{'when_to_decline':'no credible joint value'}}


class GuidedTest(unittest.TestCase):
    def test_person_facts_do_not_transfer(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.Runtime(d)
            learned={'lessons':[{'id':'general','scope':'transferable'},
                {'id':'specific','scope':'person_specific','applies_to':['other-person']}]}
            self.assertEqual([x['id'] for x in r.scoped_lessons(learned,'New Person')['lessons']],['general'])
    def test_duplicates_are_not_three_candidates(self):
        p=plan('question');p['candidates'][1]['question']=p['candidates'][0]['question']
        with self.assertRaises(ValueError):m.Runtime.validate_candidates(p)
    def test_both_branch_queries_enter_shared_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.Runtime(d)
            def search(q,path):return {'query':q,'api_url':'https://example.org/'+q,'items':[]}
            def sources(result,path,max_pages):return [{'url':result['api_url'],'text':'controlled metadata fixture'}]
            with patch.object(r,'search',side_effect=search),patch.object(r,'sources',side_effect=sources):
                evidence=r.retrieve_counterevidence([plan('alpha'),plan('beta')],Path(d)/'pair')
            self.assertEqual(len(evidence['searches']),6)
            self.assertEqual(len(evidence['balanced_model_sources']),6)
    def test_no_invite_never_generates_mail(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.Runtime(d);folder=Path(d)/'branch';context={'co_do':{'open_questions':''},'historical_experience':{'lessons':[]}}
            source={'sources':[],'search':{}};counter={'sources':[],'balanced_model_sources':[]}
            with patch.object(r,'model',return_value={'selected_id':'NO_INVITE','selection_reason':'no defensible joint gain'}) as call:
                result=r.guided_finish(context,source,counter,plan('questions'),folder,{'status':'RUNNING'})
            self.assertEqual(result['status'],'NO_CREDIBLE_INTERSECTION');self.assertEqual(call.call_count,1)
            self.assertFalse((folder/'invitation.call.json').exists())
    def test_actual_request_context_is_private_and_cache_bound(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.Runtime(d);path=Path(d)/'stage.call.json'
            raw={'provider':'openai','model':'gpt-6.1-sol','outputs':[{'text':'{"ok":true}'}]}
            with patch.object(r,'command',return_value=raw):r.model('science',{'historical_experience':{'lessons':[{'id':'transfer'}]}},path)
            request=m.load(path.with_suffix('.request.json'))
            self.assertEqual(request['context']['historical_experience']['lessons'][0]['id'],'transfer')
            self.assertEqual(path.with_suffix('.request.json').stat().st_mode&0o777,0o600)
            m.save(path,{'returncode':0,'stdout':json.dumps(raw)})
            with self.assertRaises(ValueError):r.model('different science',{},path)

if __name__=='__main__':unittest.main()
