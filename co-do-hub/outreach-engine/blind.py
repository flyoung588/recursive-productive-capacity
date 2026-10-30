#!/usr/bin/env python3
"""Export private, randomly labeled research results; never score or send them."""
import argparse
from pathlib import Path
import secrets
from runtime import load, save, Runtime


def redact(value):
    if isinstance(value,dict):
        return {k:redact(v) for k,v in value.items() if k not in (
            'applied_lesson_ids','researcher_specific_lessons_not_applied','historical_experience')}
    if isinstance(value,list):return [redact(v) for v in value]
    return value


def export(state,pair_id):
    Runtime.checked_id(pair_id);state=Path(state)
    pair=load(state/'pairs'/pair_id/'result.json')
    if not pair:raise ValueError('Pair must finish before review export')
    keypath=state/'blind_keys'/(pair_id+'.json')
    key=load(keypath)
    if key is None:
        order=['A','B']
        if secrets.randbelow(2):order.reverse()
        key=dict(zip(('X','Y'),order));save(keypath,key)
    variants={}
    for label,branch in key.items():
        folder=state/'runs'/(pair_id+'-'+branch)
        variants[label]={stage:redact(load(folder/(stage+'.json'))) for stage in
                         ('candidates','scientific_selection','experiment','delivery')}
    packet={'researcher':pair['researcher'],'variants':variants,
            'review_questions':['Are cited findings supported?','Are the candidate questions substantively different?',
             'Is the gap already answered?','What can joint work teach beyond separate work?',
             'Does the first study distinguish rival mechanisms?','Is the invitation natural and worth replying to?',
             'What substantive edits are necessary?'],
            'review_status':'NOT_YET_HUMAN_EVALUATED','source_evidence':
                load(state/'runs'/(pair_id+'-A')/'competitors.json')}
    path=state/'blind_review'/(pair_id+'.json');save(path,packet)
    lines=['# Private scientific review: '+pair['researcher'],'',
           'X/Y are randomly assigned. Conditions and learning audit are kept in a separate private key.',
           'No review or quality improvement is implied by this packet.','']
    for label,variant in variants.items():
        lines.extend(['## '+label,'','### Candidate questions',''])
        for c in variant['candidates']['candidates']:
            lines.extend(['- '+c['id']+': '+c['question'],'  Mechanism: '+c['distinct_mechanism']])
        for title,stage in [('Scientific selection and counterevidence','scientific_selection'),('First discriminating study','experiment')]:
            lines.extend(['','### '+title,'','```json',__import__('json').dumps(variant[stage],ensure_ascii=False,indent=2),'```'])
        d=variant['delivery']
        lines.extend(['','### English invitation','',d.get('subject','NO_INVITE'),'',d.get('english_email','No invitation generated.'),
                      '','### Chinese review draft','',d.get('chinese_review','No invitation generated.'),''])
    lines.extend(['## Human review questions','']+['- '+q for q in packet['review_questions']])
    markdown=path.with_suffix('.md');markdown.write_text('\n'.join(lines)+'\n');markdown.chmod(0o600)
    return {'review_packet':str(path),'review_markdown':str(markdown),'private_key':str(keypath),
            'quality_improvement':'NOT_ESTABLISHED','mail':'DRAFT_ONLY'}

if __name__=='__main__':
    import json
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',required=True)
    p.add_argument('pair_id');args=p.parse_args()
    print(json.dumps(export(args.state,args.pair_id),indent=2))
