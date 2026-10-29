#!/usr/bin/env python3
"""Co-Do Outreach Learning Engine — standard-library, local-first, never sends mail.

Source records are curated; no citation or academic novelty is inferred from an LLM.
Learning is persisted in JSON, independent of chat history.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
STATE = ROOT / 'state'
FEATURES = ('other_focus', 'research_hook', 'question', 'on_demand',
            'multi_party', 'reuse', 'disclaimer', 'self_promotion', 'length')
ISSUE_URL = 'https://github.com/flyoung588/recursive-productive-capacity/issues/'


def load_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def read_events(path=None):
    path = path or DATA / 'feedback.jsonl'
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def append_event(event, path=None):
    path = path or DATA / 'feedback.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as fp:
        fp.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + '\n')


def has(text, *terms):
    t = text.lower()
    return any(x.lower() in t for x in terms)


def features(text, person=None):
    """Observable rhetorical features, not an external scientific quality metric."""
    t = text.lower()
    length = max(1, len(text))
    other = len(re.findall(r'\byou\b|\byour\b|您|你的|您的', t))
    selfref = len(re.findall(r'\bi\b|\bwe\b|\bour\b|我|我们', t))
    hook = person.get('anchor_terms', []) if person else []
    return {
        'other_focus': min(1, other / max(1, selfref + other)),
        'research_hook': float(bool(hook) and any(x.lower() in t for x in hook)),
        'question': float('?' in t or '？' in t),
        'on_demand': float(has(t, 'around a problem', 'as the work', 'as a project', 'form around', 'grows around', 'work then needs', 'as needed', '按需', '随着', '围绕真实', '先开始', '问题出现')),
        'multi_party': float(has(t, 'people and ai', 'people and machines', 'different people', 'other people', 'another person', 'independent people', 'different contributors', '人与', '不同的人', '多方', '团队成员', '参与者')),
        'reuse': float(has(t, 'next project', 'next collaboration', 'carry over', 'across teams', 'reuse', '留下', '下一次', '积累', '传递')),
        'disclaimer': min(1, sum(t.count(x) for x in ('not a claim', 'not a request', 'do not want to', 'not to recruit', 'no fixed team', 'no preassigned', '并不是', '不意味着', '不是邀请', '没有任何', '不认为')) / 2),
        'self_promotion': min(1, sum(t.count(x) for x in ('we are building', 'our platform', 'our mission', '我们建设', '我们的平台', '邀请您加入', '加入我们')) / 2),
        'length': max(0., min(1., (length - 750) / 1200))
    }


def score(text, person, model):
    x = features(text, person)
    return sum(model['weights'][k] * x[k] for k in FEATURES)


def learn(events, people):
    """Pairwise logistic preference learner; grounded in actual before/after edits.

    No pretending two labeled corrections demonstrate generalization.
    """
    pairs = [e for e in events if e.get('type') == 'revision' and e.get('preferred') and e.get('rejected')]
    # Seeded from explicit human editorial feedback, then updated from pairwise revisions.
    w = {'other_focus': .4, 'research_hook': .8, 'question': .3,
         'on_demand': .8, 'multi_party': .8, 'reuse': .4,
         'disclaimer': -1.6, 'self_promotion': -2.2, 'length': -1.0}
    margins_before = []
    for e in pairs:
        p = people[e['researcher_id']]
        d = {k: features(e['preferred'], p)[k] - features(e['rejected'], p)[k] for k in FEATURES}
        margins_before.append(sum(w[k] * d[k] for k in FEATURES))
    # Preference log-likelihood training with bounded L2 regularization.
    for epoch in range(140):
        lr = 0.22 / (1 + epoch / 45)
        for e in pairs:
            p = people[e['researcher_id']]
            good, bad = features(e['preferred'], p), features(e['rejected'], p)
            delta = {k: good[k] - bad[k] for k in FEATURES}
            margin = sum(w[k] * delta[k] for k in FEATURES)
            grad_scale = 1. / (1. + math.exp(max(-40, min(40, margin))))
            for k in FEATURES:
                w[k] += lr * (grad_scale * delta[k] - 0.005 * w[k])
    margins_after = []
    for e in pairs:
        p = people[e['researcher_id']]
        x1, x0 = features(e['preferred'], p), features(e['rejected'], p)
        margins_after.append(sum(w[k] * (x1[k] - x0[k]) for k in FEATURES))
    choice = {}
    outcomes = {}
    for e in events:
        if e.get('type') == 'match_choice':
            key = e['researcher_id']
            choice.setdefault(key, {})
            choice[key][e['preferred_issue']] = choice[key].get(e['preferred_issue'], 0) + 1
            choice[key][e['rejected_issue']] = choice[key].get(e['rejected_issue'], 0) - 1
        if e.get('type') == 'outcome':
            key = e['researcher_id']
            issue = e['issue_id']
            outcomes.setdefault(key, {})
            value = {'interested': 1., 'not_interested': -1., 'co_study_started': 2., 'problem_corrected': -0.5}[e['kind']]
            outcomes[key][issue] = outcomes[key].get(issue, 0.) + value
    source_fingerprint = hashlib.sha256(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True) for x in events).encode()).hexdigest()
    return {'schema': 'co-do.learn.v0.1', 'weights': w, 'match_feedback': choice, 'observed_outcomes': outcomes,
            'feedback_sha256': source_fingerprint, 'revision_pairs': len(pairs),
            'training_pairs_preferred': sum(m > 0 for m in margins_after),
            'mean_margin_before': round(sum(margins_before) / len(pairs), 3) if pairs else None,
            'mean_margin_after': round(sum(margins_after) / len(pairs), 3) if pairs else None,
            'claim': 'In-sample fit only. No external researcher reply or collaboration outcome has been observed.'}


def ensure_model(events, people):
    """Refresh persisted parameters automatically when the event log changes."""
    existing = load_json(STATE / 'learned.json')
    expected = learn(events, people)
    if existing is None or existing.get('feedback_sha256') != expected['feedback_sha256']:
        write_json(STATE / 'learned.json', expected)
        return expected
    return existing


def rank_matches(person, model):
    output = []
    for m in person['intersections']:
        if m.get('evidence_status') not in ('supported_intersection', 'adjacent_hypothesis'):
            continue
        # Explicitly-curated interests and evidence are essential. Never fabricate a gap from keywords.
        if not m.get('research_question') or not m.get('evidence_urls'):
            continue
        bonus = model['match_feedback'].get(person['id'], {}).get(m['issue_id'], 0)
        value = float(m['fit']) + bonus * 2 + model.get('observed_outcomes', {}).get(person['id'], {}).get(m['issue_id'], 0.)
        output.append({'issue_id': m['issue_id'], 'score': round(value, 2),
                       'reason': m['connection'], 'question': m['research_question'],
                       'evidence_status': m['evidence_status'],
                       'evidence_urls': m['evidence_urls'], 'source_note': m.get('source_note', '')})
    return sorted(output, key=lambda m: (-m['score'], m['issue_id']))


def render(person, match, mode):
    """Distinct grounded narrative structures; learned preferences select among them."""
    chosen = next(x for x in person['intersections'] if x['issue_id'] == match['issue_id'])
    title = chosen['mail_subject']
    intro = chosen['research_observation']
    question = chosen['research_question']
    scenario = chosen['co_do_scenario']
    question_followup = chosen['specific_ask']
    issue_link = ISSUE_URL + str(chosen['issue_number'])
    if mode == 'human':
        body = (f"Dear {person['salutation']},\n\n"
                f"{intro}\n\n"
                f"It made me wonder: {question}\n\n"
                f"I'm Fei Yang, an independent researcher exploring Co-Do. {scenario}\n\n"
                f"{question_followup}\n\n"
                f"I've put the starting question here: {issue_link}\n\n"
                f"I'd be interested to hear what you think. If this connects with what you're exploring, perhaps we could exchange ideas about a small study.\n\n"
                f"Best,\nFei Yang")
    elif mode == 'research':
        body = (f"Dear {person['salutation']},\n\n{intro}\n\n"
                f"A research question this suggests is: {question}\n\n"
                f"{chosen['experiment']}\n\n"
                f"I'm exploring Co-Do, where real work can assemble independent people and AI as needed. {scenario}\n\n"
                f"{question_followup}\n\n"
                f"Research question: {issue_link}\n\n"
                f"Would you be interested in exchanging research ideas?\n\nBest,\nFei Yang")
    elif mode == 'pitch':
        body = (f"Dear {person['salutation']},\n\n"
                f"I'm Fei Yang. We are building Co-Do, our platform for organizing people and AI around work. "
                f"Our mission is to build better collaboration.\n\n"
                f"{intro}\n\n{scenario}\n\n"
                f"We would like you to join our research initiative and contribute to {match['issue_id']}. "
                f"Details: {issue_link}\n\nBest,\nFei Yang")
    elif mode == 'defensive':
        body = (f"Dear {person['salutation']},\n\n{intro}\n\n"
                f"I do not want to suggest any unsolved academic gap and this is not a claim of novelty. "
                f"This is not a request for unpaid work and not to recruit you into any fixed team.\n\n"
                f"{question}\n\n{scenario}\n\n{issue_link}\n\nBest,\nFei Yang")
    else:
        raise ValueError('unknown mode')
    return title, body


def generate(person, model, all_styles=False):
    matches = rank_matches(person, model)
    if not matches or matches[0]['score'] < 2.0:
        return {'status': 'NO_CREDIBLE_INTERSECTION', 'researcher_id': person['id'], 'matches': matches}
    top = matches[0]
    candidates = []
    for mode in ('pitch', 'defensive', 'research', 'human'):
        subject, body = render(person, top, mode)
        candidates.append({'mode': mode, 'subject': subject, 'body': body,
                           'preference_score': round(score(body, person, model), 5)})
    winner = max(candidates, key=lambda x: x['preference_score'])
    return {'status': 'REVIEW_REQUIRED', 'researcher_id': person['id'],
            'issue_id': top['issue_id'], 'issue_url': ISSUE_URL + str(next(m['issue_number'] for m in person['intersections'] if m['issue_id'] == top['issue_id'])),
            'match': top, 'chosen_style': winner['mode'], 'subject': winner['subject'],
            'body': winner['body'], 'preference_score': winner['preference_score'],
            'all_matches': matches, 'alternatives': candidates if all_styles else None,
            'send_authorized': False}



def draft_with_local_model(person, match, events, endpoint, model_name, allow_external=False):
    """Optional explicit OpenAI-compatible drafting endpoint. Never sends emails."""
    parsed = urllib.parse.urlsplit(endpoint)
    local = parsed.hostname in ('localhost', '127.0.0.1', '::1')
    if not (parsed.scheme == 'http' and local or parsed.scheme == 'https' and local
            or parsed.scheme == 'https' and allow_external):
        raise ValueError('Model endpoint must be localhost, or explicitly allowed HTTPS remote')
    intersection = next(m for m in person['intersections'] if m['issue_id'] == match['issue_id'])
    # Raw feedback (including unsent edits) never leaves the machine without opt-in.
    recent_edits = ([e for e in events if e.get('type') == 'revision'
                     and e.get('researcher_id') == person['id']][-2:] if local else [])
    preferred_examples = [e['preferred'][:1100] for e in recent_edits]
    cited = [x for x in person.get('evidence', []) if x.get('url') in intersection['evidence_urls']]
    context = {'recipient': person['name'], 'research_facts': cited,
               'research_observation': intersection['research_observation'],
               'co_do_scenario': intersection['co_do_scenario'],
               'possible_shared_question': intersection['research_question'],
               'specific_question_to_person': intersection['specific_ask'],
               'issue_url': ISSUE_URL + str(intersection['issue_number']),
               'preferred_edits_private_local_only': preferred_examples}
    system = ('Write one natural, concise, individually addressed English research invitation. '
              'Start with what this researcher actually found; move to a meaningful research question. '
              'Co-Do means projects can assemble independent PEOPLE and AI as they require, not just one person using AI. '
              'Invite dialogue rather than recruitment or task assignment. Avoid disclaimer cascades, '
              'promotional claims and made-up novelty, citations or background. Use only the stated facts. '
              'Aim for 140-230 words. Output the email body only, no markdown fencing. Never send anything.')
    payload = {'model': model_name, 'temperature': 0.5,
               'messages': [{'role':'system', 'content':system},
                            {'role':'user', 'content':json.dumps(context, ensure_ascii=False)}]}
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    headers = {'Content-Type':'application/json'}
    if not local and os.getenv('CO_DO_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['CO_DO_API_KEY']
    request = urllib.request.Request(endpoint, data=data, headers=headers, method='POST')
    with urllib.request.urlopen(request, timeout=75) as response:
        raw = json.loads(response.read(500000).decode('utf-8'))
    draft_text = raw['choices'][0]['message']['content'].strip()
    if not draft_text or len(draft_text) < 160:
        raise ValueError('model response too short to be a reviewable draft')
    allowed = set(intersection['evidence_urls'] + [ISSUE_URL + str(intersection['issue_number'])])
    found_urls = re.findall(r'https?://[^\s<>\])]+', draft_text)
    if any(x.rstrip('.,;') not in allowed for x in found_urls):
        raise ValueError('model invented or introduced a non-approved URL')
    return {'subject': intersection['mail_subject'], 'body': draft_text,
            'status':'MODEL_DRAFT_UNVERIFIED', 'source_urls':intersection['evidence_urls'],
            'local_model':local, 'human_factual_review_required':True,
            'send_authorized':False}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Co-Do recursive outreach; local drafts only, no mail sender')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('learn', help='Fit and persist pairwise preferences from feedback.jsonl')
    sub.add_parser('status', help='Show feedback and training state')
    match = sub.add_parser('match', help='Rank grounded intersections for one researcher')
    match.add_argument('researcher')
    draft = sub.add_parser('draft', help='Prepare local review-only email, never send')
    draft.add_argument('researcher')
    draft.add_argument('--untrained', action='store_true', help='Ablation: equal style preferences')
    draft.add_argument('--alternatives', action='store_true')
    draft.add_argument('--model-endpoint', help='Explicit OpenAI-compatible local URL, no default network calls')
    draft.add_argument('--model-name', help='Local model identifier at that endpoint')
    draft.add_argument('--allow-external-model', action='store_true', help='Opt-in to an HTTPS remote model; never transmits past private edits')
    feed = sub.add_parser('feedback', help='Append an actual preference pair (requires local files)')
    feed.add_argument('researcher')
    feed.add_argument('--preferred', type=Path, required=True)
    feed.add_argument('--rejected', type=Path, required=True)
    feed.add_argument('--note', default='')
    choose = sub.add_parser('choose', help='Record real human issue choice; does not contact anyone')
    choose.add_argument('researcher')
    choose.add_argument('--preferred-issue', required=True)
    choose.add_argument('--rejected-issue', required=True)
    ingest = sub.add_parser('import-researcher', help='Import a source-grounded local researcher profile JSON')
    ingest.add_argument('profile', type=Path)
    outcome = sub.add_parser('outcome', help='Record actual human-reported response, not a fabricated reply')
    outcome.add_argument('researcher')
    outcome.add_argument('--issue', required=True)
    outcome.add_argument('--kind', choices=('interested', 'not_interested', 'co_study_started', 'problem_corrected'), required=True)
    outcome.add_argument('--note', required=True)
    outcome.add_argument('--source-ref', required=True, help='Private evidence identifier, never raw email body')
    args = parser.parse_args(argv)
    people = {p['id']: p for p in load_json(DATA / 'researchers.json', [])}
    events = read_events()
    if args.command == 'import-researcher':
        p = json.loads(args.profile.read_text(encoding='utf-8'))
        if not p.get('id') or not p.get('name') or p['id'] in people:
            parser.error('researcher needs new id and name')
        if not p.get('evidence') or not p.get('intersections') or any(
                not m.get('evidence_urls') or not m.get('research_question') or not m.get('source_note')
                for m in p['intersections']):
            parser.error('source-backed evidence, questions and limitation note required')
        if any(not url.startswith('https://') for m in p['intersections'] for url in m['evidence_urls']):
            parser.error('only full HTTPS evidence URLs allowed')
        profiles = list(people.values()) + [p]
        write_json(DATA / 'researchers.json', profiles)
        print(json.dumps({'imported':p['id'], 'total_researchers':len(profiles)}, ensure_ascii=False))
    elif args.command == 'feedback':
        if args.researcher not in people: parser.error('unknown researcher')
        pref, rej = args.preferred.read_text(encoding='utf-8'), args.rejected.read_text(encoding='utf-8')
        if pref.strip() == rej.strip(): parser.error('identical alternatives cannot train')
        append_event({'type':'revision', 'researcher_id':args.researcher,
                      'preferred':pref, 'rejected':rej, 'note':args.note,
                      'created_at':datetime.now(timezone.utc).isoformat(), 'source':'human_review'})
        print(json.dumps({'appended':True, 'event_count':len(events)+1}, ensure_ascii=False))
    elif args.command == 'choose':
        if args.researcher not in people: parser.error('unknown researcher')
        ids = {m['issue_id'] for m in people[args.researcher]['intersections']}
        if args.preferred_issue not in ids or args.rejected_issue not in ids or args.preferred_issue == args.rejected_issue:
            parser.error('issues must be distinct, known intersections')
        append_event({'type':'match_choice', 'researcher_id':args.researcher,
                      'preferred_issue':args.preferred_issue,'rejected_issue':args.rejected_issue,
                      'source':'human_review', 'created_at':datetime.now(timezone.utc).isoformat()})
        print(json.dumps({'appended':True, 'event_count':len(events)+1}, ensure_ascii=False))
    elif args.command == 'outcome':
        if args.researcher not in people: parser.error('unknown researcher')
        ids = {m['issue_id'] for m in people[args.researcher]['intersections']}
        if args.issue not in ids: parser.error('unknown issue for researcher')
        append_event({'type':'outcome', 'researcher_id':args.researcher, 'issue_id':args.issue,
                      'kind':args.kind, 'note':args.note, 'source_ref':args.source_ref,
                      'created_at':datetime.now(timezone.utc).isoformat(), 'source':'human_recorded_external_event'})
        print(json.dumps({'appended':True,'event_count':len(events)+1}, ensure_ascii=False))
    elif args.command == 'learn':
        model = learn(events, people)
        write_json(STATE / 'learned.json', model)
        print(json.dumps(model, ensure_ascii=False, indent=2))
    else:
        model = ensure_model(events, people)
        if args.command == 'status':
            print(json.dumps({'researchers':list(people), 'events':len(events),
                              'stored_model':(STATE / 'learned.json').exists(),
                              'pairs':model['revision_pairs'],
                              'feedback_sha256':model['feedback_sha256']}, ensure_ascii=False, indent=2))
        else:
            if args.researcher not in people: parser.error('unknown researcher')
            p = people[args.researcher]
            if args.command == 'match':
                print(json.dumps(rank_matches(p, model), ensure_ascii=False, indent=2))
            else:
                if args.untrained:
                    model = dict(model, weights={k:0. for k in FEATURES}, match_feedback={})
                result = generate(p, model, args.alternatives)
                if args.model_endpoint:
                    if not args.model_name: parser.error('--model-name required with --model-endpoint')
                    if result['status'] == 'REVIEW_REQUIRED':
                        result['model_candidate'] = draft_with_local_model(
                            p, result['match'], events, args.model_endpoint, args.model_name,
                            allow_external=args.allow_external_model)
                dest = STATE / 'drafts' / f"{p['id']}.json"
                if not args.untrained:
                    write_json(dest, result)
                print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
