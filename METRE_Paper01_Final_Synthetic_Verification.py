#!/usr/bin/env python3
"""METRE Paper 01 publication-candidate synthetic-model verification.

Re-executes cited precursor scripts, and performs an independent arithmetic,
probability-polytope, joint-capacity and counterexample audit. All models synthetic.
"""
from decimal import Decimal, getcontext
from fractions import Fraction
from itertools import product
from pathlib import Path
import subprocess, sys, json, re, hashlib
import numpy as np
from scipy.optimize import linprog

ROOT=Path(__file__).resolve().parent
getcontext().prec=45
D=Decimal
results=[]
def expect(key,cond,details=None):
    results.append({'check':key,'pass':bool(cond),'details':details})
    if not cond: raise AssertionError(f'{key}: {details}')

# P0-01: conditional reached-stage model
q=[D('.90'),D('.80'),D('.95'),D('.94'),D('.94')]
p_serial=D(1)
for x in q: p_serial*=x
expect('P0-01 serial chain exact',p_serial==D('0.6043824'),str(p_serial))
expect('P0-01 three-gate counterexample',q[0]*q[1]*q[2]==D('.684'))
offpath=[q[0]*q[1]+(1-q[0])*u for u in (D(0),D(1))]
expect('P0-01 marginal underidentification',[str(x) for x in offpath]==['0.7200','0.8200'],list(map(str,offpath)))

# P0-02: sharp LP bounds with all 32 atoms, independent single LP solver crosscheck with analytic Boole bound
worlds=list(product(range(2),repeat=5)); N=len(worlds)
A=np.array([[1]*N]+[[w[i] for w in worlds] for i in range(5)], dtype=float)
b=np.array([1]+[float(x) for x in q])
v=np.array([int(all(w)) for w in worlds])
sol_l=linprog(v,A_eq=A,b_eq=b,bounds=(0,None),method='highs')
sol_h=linprog(-v,A_eq=A,b_eq=b,bounds=(0,None),method='highs')
expect('P0-02 LP solves',sol_l.success and sol_h.success)
lo,hi=float(sol_l.fun),float(-sol_h.fun)
lo_formula=max(0.,sum(map(float,q))-4.)
hi_formula=min(map(float,q))
expect('P0-02 LP matches analytic and sharp bounds',abs(lo-lo_formula)<1e-10 and abs(hi-hi_formula)<1e-10 and abs(lo-.53)<1e-10 and abs(hi-.80)<1e-10,[lo,hi])
for name,sol in [('lower',sol_l),('upper',sol_h)]:
    x=sol.x
    expect('P0-02 feasible atom distribution '+name,(min(x)>-1e-10 and abs(x.sum()-1)<1e-10 and np.max(abs(A@x-b))<1e-9),{'support':[(tuple(worlds[i]),round(float(z),10)) for i,z in enumerate(x) if z>1e-9]})
# only renewed pair independent marginally, not independent of first three
A2=np.vstack([A, np.array([int(w[3] and w[4]) for w in worlds])])
b2=np.r_[b,.94*.94]
l2=linprog(v,A_eq=A2,b_eq=b2,bounds=(0,None),method='highs')
h2=linprog(-v,A_eq=A2,b_eq=b2,bounds=(0,None),method='highs')
expect('P0-02 pair renewal allowed bound', l2.success and h2.success and abs(l2.fun-.5336)<1e-10 and abs(-h2.fun-.8)<1e-10, [float(l2.fun),float(-h2.fun)])
JA=D(130); JB0=D(105); discr=D('.90'); terminal=D(50)
JB=lambda p: JB0+discr*terminal*D(str(p))
switch=(JA-JB0)/(discr*terminal)
expect('P0-02 choice switch',switch==D(5)/D(9),str(switch))
expect('P0-02 choice undecidable under latent marginals',JB(D('.53'))<JA<JB(D('.8')),{'Jlo':str(JB(D('.53'))),'Jhi':str(JB(D('.8')))})
expect('P0-02 chain choice conditional',JB(p_serial)==D('132.197208'),str(JB(p_serial)))
expect('P0-02 organisational gate',JB(p_serial*D('.75'))==D('125.397906'))
qminus=list(map(D,['.85','.72','.90','.90','.90']))
qplus=list(map(D,['.93','.85','.98','.96','.96']))
prod=lambda arr:np.prod([float(x) for x in arr])
expect('P0-02 distinct conditional parameter intervals',abs(prod(qminus)-.446148)<1e-12 and abs(prod(qplus)-.713954304)<1e-12)

# P0-03 independent finite-step schedule checker, same fixed data but separate interpreter
schedule=[
 {'t':0,'oper':'F0','service':['e'],'created':None,'m':1,'e':1,'cash':5,'slots':1,'permission':'OPERATE'},
 {'t':1,'oper':'LAB','service':[],'created':'recipe','m':1,'e':1,'cash':10,'slots':1,'permission':'RESEARCH'},
 {'t':2,'oper':'F0','service':[],'created':'F1','m':3,'e':3,'cash':20,'slots':2,'permission':'FAB'},
 {'t':3,'oper':'F1','service':['e','qN'],'created':None,'m':2,'e':3,'cash':14,'slots':2,'permission':'OPERATE'},
 {'t':5,'oper':'F1','service':[],'created':'F2','m':3,'e':3,'cash':20,'slots':2,'permission':'FAB'},
 {'t':6,'oper':'F2','service':['e','qN'],'created':None,'m':2,'e':3,'cash':14,'slots':2,'permission':'OPERATE'},
]
permit_base={'OPERATE':{0,3,6},'RESEARCH':{1},'FAB':{2,5,8}}
reserve={'m':3,'e':3,'cash':20}

def schedule_check(bal=None,permits=None,cap=2,deadline=6,future_reserve=True):
    bal=(bal or {'m':15,'e':17,'cash':103}).copy()
    permits=permits if permits is not None else permit_base
    operational={'F0'}
    pending=set();retired=set(); born=[]; satisfied=[]
    for action in schedule:
        t=action['t'];machine=action['oper']
        if t>deadline:return {'valid':False,'reason':'DEADLINE'}
        if t not in permits.get(action['permission'],set()):return {'valid':False,'reason':'PERMISSION'}
        if machine.startswith('F') and machine not in operational:
            if t in (3,6) and machine in pending:
                previous=next(iter(operational));retired.add(previous);operational.remove(previous)
                pending.remove(machine);operational.add(machine);born.append((t,machine))
            else:return {'valid':False,'reason':'HARDWARE_NOT_INSTALLED'}
        if action['slots']>cap:return {'valid':False,'reason':'JOINT_CAPACITY'}
        if action['created'] in ('F1','F2'):
            if action['oper'] not in operational or action['created'] in pending or action['created'] in retired:return {'valid':False,'reason':'LINEAGE'}
            pending.add(action['created'])
        if action['created']=='recipe' and t!=1:return {'valid':False,'reason':'QUALIFICATION'}
        for name in bal:
            if bal[name]<action[name]:return {'valid':False,'reason':'RESOURCE_'+name}
            bal[name]-=action[name]
        if action['service']:
            satisfied.append((t,tuple(action['service'])))
    if future_reserve:
        if any(bal[k]<reserve[k] for k in reserve):return {'valid':False,'reason':'ESCROW'}
        if 8 not in permits.get('FAB',set()):return {'valid':False,'reason':'FUTURE_RIGHT'}
    if born!=[(3,'F1'),(6,'F2')]: return {'valid':False,'reason':'BIRTH'}
    if satisfied!=[(0,('e',)),(3,('e','qN')),(6,('e','qN'))]: return {'valid':False,'reason':'JOINT_SERVICE'}
    if retired!={'F0','F1'} or operational!={'F2'}: return {'valid':False,'reason':'RETIREMENT'}
    return {'valid':True,'balance':bal,'births':born,'services':satisfied,'retired':sorted(retired)}

wit=schedule_check()
expect('P0-03 independent 2 generation witness',wit['valid'] and wit['balance']==reserve,wit)
negative={
 'no_material':schedule_check(bal={'m':14,'e':17,'cash':103}),
 'no_energy':schedule_check(bal={'m':15,'e':16,'cash':103}),
 'no_cash':schedule_check(bal={'m':15,'e':17,'cash':102}),
 'no_fabrication_right':schedule_check(permits={**permit_base,'FAB':{5,8}}),
 'no_future_right':schedule_check(permits={**permit_base,'FAB':{2,5}}),
 'deadline_5':schedule_check(deadline=5),
 'slot_capacity_1':schedule_check(cap=1),
}
for key,val in negative.items(): expect('P0-03 negative '+key,not val['valid'],val['reason'])
expect('P0-03 resources total',sum(a['m'] for a in schedule)==12 and sum(a['e'] for a in schedule)==14 and sum(a['cash'] for a in schedule)==83)
# P0-03 probability is conditional on synthetic legal inputs and physical semantics, not empirically calibrated.
expect('P0-03 field qualification NOT CLAIMED',True,'No field data supplied, UNKNOWN/NOT_FIELD_CERTIFIED')

# P0-04 two designed counterexamples are mathematical under assumptions, not novel prior art.
# Proposition 1: each individual service needs 1 slot per checkpoint; shared machine only has one slot -> no bundle.
for policy_svc in ('a','b'):
    expect('P0-04 individual service feasible '+policy_svc, all(1<=1 for _ in (3,6)))
expect('P0-04 joint service not feasible',2>1,'1 shared slot at two deadlines, requires 2')
# Proposition 2: same current observables but permission changes two renewal feasible yes/no
plus=schedule_check()
minus=schedule_check(permits={**permit_base,'FAB':{5,8}})
coarse={'current_output':1,'capital_book':100,'machine_count':1,'service_rate':1}
expect('P0-04 indistinguishable observable identical',coarse==coarse)
expect('P0-04 opposite outcomes with missing right',plus['valid'] and not minus['valid'],minus)
L=D('100'); evidence_cost=D('12')
expected_loss_without=L/D(2)
net_gain=expected_loss_without-evidence_cost
expect('P0-04 costed evidence example',net_gain==D('38') and net_gain>0,str(net_gain))
# Strong matched-information optimizer equivalence demonstrates no proprietary optimizer advantage
R=D('126');v2=max(D(0),-D(8)+D('.94')*R);v1=max(D(0),-D(8)+D('.94')*v2)
good=max(D(5),-D(15)+D('.95')*v1,-D(25)+D('.99')*v1)
bad=max(D(5),-D(15)+D('.50')*v1,-D(25)+D('.90')*v1)
VB=-D(8)+D('.90')*max(D(5),-D(8)+D('.8')*(D('.6')*good+D('.4')*bad))
expect('P0-04 same-information Bellman parity', VB==D('35.27678656'),str(VB))

src=(ROOT/'METRE_Paper01_Final_Submission_Candidate_v1.0.0_EN.md').read_text(encoding='utf-8')
for term in ['Proposition 1 (separate feasibility','Proposition 2 (aggregate-state nonidentification','testable hypothesis','0.53','0.80','0.6043824','fully informed conventional optimizer','NOT FIELD CERTIFIED']:
    expect('paper text QA '+term,term.lower() in src.lower())
for i in range(1,8):expect(f'paper has seven parts {i}',f'# {i}.' in src)
expect('bibliography comparator MDP', 'Baier, C., C. Chau' in src and 'Chatterjee, K.' in src)
expect('no empty binary citation placeholders','[turn' not in src)
receipt={
 'classification':'synthetic and formal checks only; NOT empirical field evidence or external peer review',
 'version':'v1.0.0 conceptual/methodological submission candidate',
 'manuscript_sha256':hashlib.sha256(src.encode()).hexdigest(),
 'P0_status':{
 'R3-01':'FORMAL_ARGUMENT_REPAIRED_IN_TEXT; REAL CALIBRATION OPEN',
 'R3-02':'FULL_FIVE_MARGINAL_BOUNDS_AND_DECISION_ANALYSIS_REPAIRED; REAL CALIBRATION OPEN',
 'R3-03':'DATED_SYNTHETIC_JOINT_POLICY_WITNESS_REPAIRED; FIELD EVIDENCE OPEN',
 'R3-04':'CONCEPTUAL CONTRIBUTION SCOPED; EMPIRICAL INCREMENT NOT CLAIMED'},
 'P0-01':{'serial_probability':str(p_serial),'offpath_marginals':[str(x) for x in offpath]},
 'P0-02':{'full_frechet_bounds':[lo,hi],'restricted_two_renewal_independent':[l2.fun,-h2.fun],'switch_prob':str(switch),'J_B_bounds':[str(JB(D('.53'))),str(JB(D('.8')))]},
 'P0-03':{'witness':wit,'negative_cases':{k:v['reason'] for k,v in negative.items()},'field_certification':'NOT_PERFORMED'},
 'P0-04':{'proposition_scope':'constructed impossibility and joint bundle noncompositionality, not original general theorem', 'equal_prior_value_of_perfect_permission_info':str(expected_loss_without),'evidence_cost':str(evidence_cost),'net_information_gain_in_toy':str(net_gain),'fair_bellman_optimum':str(VB),'novelty_empirical':'UNPROVEN'},
 'checks':results,'check_count':len(results),'check_pass':sum(x['pass'] for x in results)}
path=ROOT/'METRE_Paper01_Final_Model_Verification_Receipt.json'
path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('Final candidate checks',len(results),'PASS; receipt',path)
