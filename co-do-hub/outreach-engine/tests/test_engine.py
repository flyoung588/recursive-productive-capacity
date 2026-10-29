import importlib.util
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('outreach_engine', HERE / 'engine.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
PEOPLE = {p['id']: p for p in engine.load_json(HERE / 'data' / 'researchers.json')}
EVENTS = engine.read_events()


class LearningEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.learned = engine.learn(EVENTS, PEOPLE)
        cls.untrained = dict(cls.learned,
                             weights={k: 0.0 for k in engine.FEATURES},
                             match_feedback={}, observed_outcomes={})

    def test_training_changes_pairwise_preference(self):
        self.assertEqual(self.learned['revision_pairs'], 2)
        self.assertEqual(self.learned['training_pairs_preferred'], 2)
        self.assertGreater(self.learned['mean_margin_after'], self.learned['mean_margin_before'])

    def test_person_specific_intersection_revises_with_feedback(self):
        before = engine.rank_matches(PEOPLE['aneesh-pappu'], self.untrained)
        after = engine.rank_matches(PEOPLE['aneesh-pappu'], self.learned)
        self.assertEqual(before[0]['issue_id'], 'ORG-02')
        self.assertEqual(after[0]['issue_id'], 'ORG-03')
        self.assertEqual(engine.rank_matches(PEOPLE['qing-xiao'], self.learned)[0]['issue_id'], 'ORG-01')

    def test_drafts_are_specific_and_no_sending(self):
        q = engine.generate(PEOPLE['qing-xiao'], self.learned)
        a = engine.generate(PEOPLE['aneesh-pappu'], self.learned)
        self.assertEqual(q['chosen_style'], 'human')
        self.assertEqual(a['chosen_style'], 'human')
        self.assertIn('newsrooms', q['body'])
        self.assertIn('team', a['body'].lower())
        self.assertIn('issues/5', q['body'])
        self.assertIn('issues/7', a['body'])
        self.assertFalse(q['send_authorized'])
        self.assertFalse(a['send_authorized'])
        self.assertNotEqual(q['body'], a['body'])

    def test_no_intersection_means_no_draft(self):
        bad = dict(PEOPLE['qing-xiao'], id='unrelated', intersections=[])
        self.assertEqual(engine.generate(bad, self.learned)['status'], 'NO_CREDIBLE_INTERSECTION')

    def test_actual_outcome_updates_ranking_only_if_recorded(self):
        event = dict(type='outcome', researcher_id='qing-xiao', issue_id='ORG-02',
                     kind='interested', source_ref='human-recorded-test', note='fixture')
        model = engine.learn(EVENTS + [event], PEOPLE)
        self.assertEqual(model['observed_outcomes']['qing-xiao']['ORG-02'], 1.)
        self.assertEqual(self.learned['observed_outcomes'], {})

    def test_feedback_changes_persistent_model(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'events.jsonl'
            for event in EVENTS: engine.append_event(event, path)
            base = engine.learn(engine.read_events(path), PEOPLE)
            # Additional explicit preference alters the saved weight vector.
            engine.append_event({'type':'revision', 'researcher_id':'qing-xiao',
                                 'preferred':'Your CHI 2026 research: what if the team did not exist yet? Different people and AI join as a problem develops.',
                                 'rejected':'We are building our platform. Please join our initiative. It is not a fixed team.',
                                 'source':'synthetic_test_only'}, path)
            updated = engine.learn(engine.read_events(path), PEOPLE)
            self.assertNotEqual(base['feedback_sha256'], updated['feedback_sha256'])
            self.assertNotEqual(base['weights'], updated['weights'])
            state = Path(folder) / 'learned.json'
            engine.write_json(state, updated)
            self.assertEqual(engine.load_json(state)['feedback_sha256'], updated['feedback_sha256'])

    def test_optional_local_model_protocol_is_real_and_draft_only(self):
        # Local mock simulates the OpenAI-compatible response schema; NOT a model-quality test.
        requests = []
        class Server(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers['Content-Length'])
                requests.append(json.loads(self.rfile.read(n)))
                body = ('Dear Qing, Your newsroom findings made me wonder what happens '
                        'when a team does not exist yet. Could different people and AI '
                        'come together around a real question, change its direction, '
                        'and leave useful capability for the next collaboration? '
                        'I would value your perspective on a small case we might study. '
                        'Best, Fei Yang')
                payload = json.dumps({'choices':[{'message':{'content':body}}]}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *args): pass
        srv = HTTPServer(('127.0.0.1', 0), Server)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            p = PEOPLE['qing-xiao']
            m = engine.rank_matches(p, self.learned)[0]
            result = engine.draft_with_local_model(p, m, EVENTS,
                    f'http://127.0.0.1:{srv.server_port}/v1/chat/completions', 'mock-local')
            self.assertEqual(result['status'], 'MODEL_DRAFT_UNVERIFIED')
            self.assertFalse(result['send_authorized'])
            self.assertTrue(result['human_factual_review_required'])
            self.assertEqual(len(requests), 1)
            self.assertTrue(requests[0]['messages'])
        finally:
            srv.shutdown()
            srv.server_close()
            thread.join(2)

    def test_external_model_requires_explicit_https(self):
        p = PEOPLE['qing-xiao']
        m = engine.rank_matches(p, self.learned)[0]
        with self.assertRaises(ValueError):
            engine.draft_with_local_model(p, m, EVENTS, 'http://example.org/chat', 'foo')

    def test_cli_real_execution(self):
        run = subprocess.run([sys.executable, str(HERE / 'engine.py'), 'draft', 'aneesh-pappu', '--untrained'],
                             text=True, capture_output=True, check=True)
        obj = json.loads(run.stdout)
        self.assertEqual(obj['issue_id'], 'ORG-02')
        self.assertFalse(obj['send_authorized'])


if __name__ == '__main__':
    unittest.main()
