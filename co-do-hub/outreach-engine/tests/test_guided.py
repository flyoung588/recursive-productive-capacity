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
    def test_paper_read_includes_late_methods_results_not_abstract_only(self):
        text='ABSTRACT '+('background '*1800)+' METHODS randomized assignment '+('protocol '*900)+' RESULTS intervention failed '+('data '*1500)+' LIMITATIONS no human study'
        excerpt=m.paper_passages(text,7000)
        self.assertIn('randomized assignment',excerpt)
        self.assertIn('intervention failed',excerpt)
        self.assertIn('no human study',excerpt)
        self.assertLessEqual(len(excerpt),7000)
        self.assertIn('captured characters',excerpt)
    def test_primary_landing_page_resolves_its_fulltext(self):
        with patch.object(m,'fetch',side_effect=[{'url':'https://example.org/paper',
             'text':'abstract','content_type':'text/html',
             'link_records':[{'url':'https://example.org/paper.pdf','label':'PDF'}]},
             {'url':'https://example.org/paper.pdf','text':'Methods and results','content_type':'application/pdf'}]):
            source=m.Runtime.research_source('https://example.org/paper')
        self.assertEqual(source['requested_paper_url'],'https://example.org/paper')
        self.assertEqual(source['text'],'Methods and results')
    def test_missing_critical_read_is_retained_and_recovery_is_cached(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.Runtime(d);folder=Path(d)/'pair'
            source={'sources':[{'url':'https://example.org/paper','text':'abstract'}],'search':{}}
            counter={'sources':[],'searches':[],'balanced_model_sources':[]}
            with patch.object(r,'model',return_value={'source_urls':['https://example.org/paper'],
                'additional_queries':[]}),patch.object(r,'research_source',side_effect=OSError('unavailable')):
                result=r.deepen_evidence(source,[plan('a'),plan('b')],counter,folder)
            self.assertEqual(len(result['reading_recovery']['failed_reads']),1)
            self.assertEqual(result['reading_recovery']['search_completeness'],'BOUNDED_NOT_EXHAUSTIVE')
            with patch.object(r,'model',side_effect=AssertionError('must not rerun')):
                self.assertEqual(r.deepen_evidence(source,[],counter,folder),result)
    def test_blind_export_removes_condition_leak_without_editing_science(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from blind import redact
        raw={'selection_reason':'Further evidence is needed. No scoped historical lessons were supplied.',
             'applied_lesson_ids':['private-condition-id']}
        hidden=redact(raw)
        self.assertEqual(hidden,{'selection_reason':'Further evidence is needed.'})
        self.assertIn('No scoped historical',raw['selection_reason'])
        audit='Evidence still missing. No supplied historical lessons inform this selection, and no researcher interest or agreement is inferred.'
        self.assertEqual(redact(audit),'Evidence still missing. no researcher interest or agreement is inferred.')
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
    def test_source_reads_follow_relevance_and_fulltext_not_doi_alphabet(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.Runtime(d)
            result={'api_url':'https://api.example.org/query','sha256':'fixture','retrieved_at':0,
              'items':[{'DOI':'10.1234/z-top','link':[{'content-type':'application/pdf','URL':'https://example.org/top.pdf'}]},
                       {'DOI':'10.1234/a-lower'}]}
            with patch.object(r,'research_source',side_effect=lambda u:{'url':u,'text':'controlled fixture'}) as call:
                r.sources(result,Path(d)/'sources',max_pages=2)
            self.assertEqual([x.args[0] for x in call.call_args_list],
                             ['https://example.org/top.pdf','https://doi.org/10.1234/z-top'])
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
