#!/usr/bin/env python3
"""Recompute a private paired-run comparison. No model scores or quality verdicts."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re


def read(path):
    return json.loads(path.read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def compare(state, a, b):
    if any(not re.fullmatch(r'[a-zA-Z0-9_-]+',x) for x in (a,b)):
        raise ValueError('Invalid run ID')
    dirs=[Path(state)/'runs'/x for x in (a,b)]
    snapshots=[read(d/'state.json') for d in dirs]
    if any(x['status'] not in ('DRAFT_ONLY','NO_CREDIBLE_INTERSECTION') for x in snapshots):
        raise ValueError('Both runs must be complete review-only drafts')
    bundles=[{stage:read(d/(stage+'.json')) for stage in ('discovery','interpretation','competitors')} for d in dirs]
    if bundles[0]!=bundles[1]: raise ValueError('A/B evidence or interpretation differs')
    if snapshots[0]['input']['learning'] or not snapshots[1]['input']['learning']:
        raise ValueError('Expected A without learning and B with learning')
    if snapshots[0]['input']['researcher']!=snapshots[1]['input']['researcher']:
        raise ValueError('Different researcher inputs')
    drafts=[read(d/'delivery.json') for d in dirs]
    actual_models=[]
    usage=[]
    for d in dirs:
        models=set(); total={'input':0,'output':0,'total':0}
        for p in d.glob('*.call.json'):
            log=read(p)
            if log.get('returncode')!=0: continue
            raw=json.loads(log['stdout']);models.add(raw.get('provider','')+'/'+raw.get('model',''))
            for k in total: total[k]+=raw.get('usage',{}).get(k,0) or 0
        actual_models.append(sorted(models));usage.append(total)
    if actual_models[0]!=['openai/gpt-6.1-sol'] or actual_models[1]!=actual_models[0]:
        raise ValueError('Unexpected actual model in comparison')
    revised=read(dirs[1]/('invitation.json' if (dirs[1]/'invitation.json').exists() else 'revised_candidate.json')) if ((dirs[1]/'invitation.json').exists() or (dirs[1]/'revised_candidate.json').exists()) else {}
    upstream={}
    for d in dirs:
        upstream[d.name]={}
        for stage in ('candidates','scientific_selection','experiment','invitation'):
            p=d/(stage+'.call.request.json')
            if p.exists():
                request=read(p); experience=request.get('context',{}).get('historical_experience',{})
                upstream[d.name][stage]={'lesson_ids':[x.get('id') for x in experience.get('lessons',[])],
                                         'prompt_sha256':request['prompt_sha256']}
    candidate_questions=[[c['question'] for c in read(d/'candidates.json')['candidates']] if (d/'candidates.json').exists() else [] for d in dirs]
    return {'a':a,'b':b,'evidence_and_interpretation_identical':True,
        'bundle_sha256':digest(bundles[0]),'statuses':[x['status'] for x in snapshots],
        'candidate_questions':candidate_questions,'upstream_history_inputs':upstream,'actual_models':actual_models,
        'requested_thinking':[x['thinking'] for x in snapshots],
        'tokens_in_run_call_logs':usage,
        'draft_word_counts':[len(x.get('english_email','').split()) for x in drafts],
        'b_applied_lesson_ids':revised.get('applied_lesson_ids',[]),
        'b_person_specific_lessons_not_applied':revised.get('researcher_specific_lessons_not_applied',[]),
        'english_diff':list(difflib.unified_diff(drafts[0].get('english_email','').splitlines(),
                       drafts[1].get('english_email','').splitlines(),fromfile=a,tofile=b,lineterm='')),
        'human_review_required':['factual entailment and unsupported claims','interest fit',
            'gap falsification against literature','genuine multiparty co-production',
            'naturalness','substantive human editing needed'],
        'quality_improvement':'NOT_ESTABLISHED',
        'causal_limit':'Single stochastic pair; union counter-search corpus gives equal evidence access, not independent retrieval cost/recall. Output differences do not establish benefit.',
        'external_outcome':'NOT_OBSERVED','delivery':'DRAFT_ONLY'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',required=True)
    p.add_argument('a');p.add_argument('b');args=p.parse_args()
    print(json.dumps(compare(args.state,args.a,args.b),ensure_ascii=False,indent=2))
