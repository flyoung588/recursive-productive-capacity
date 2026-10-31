#!/usr/bin/env python3
"""Real, pinned, CC-BY-4.0 OCV holdout evaluation; observational and exploratory.
Compares simple baselines, never calls the 24-hour sample true equilibrium.
No upstream person has agreed to collaborate in this experiment.
"""
import csv, hashlib, io, json, math, pathlib, statistics, urllib.request

COMMIT = "ec8f3f3bc0898bb440432cb11a434250d6bcbb0c"
DOI = "10.21227/651q-8v82"
CHEM = dict(apr="LFP",bse="LFP",sg="NMC",lg="LCO",oem="LCO",
            li="LiPo cathode unknown",ar="NiCd",au="NiMH")
BLOB = {
"charge_apr":"a1c379994f26d77781582b555e4130c7e1ba248a",
"charge_bse":"97aaca87c80662fcbc08e3b78d1b458021bf1ad6",
"charge_sg":"d86966e2a4b77a55d32936ec54eb4de8ed728884",
"charge_lg":"54d60c466ad3c40ccaf789bd79da6af4c8bfbaf3",
"charge_oem":"064355805fceaee4e59f5eb4c837d6627d8e9c29",
"charge_li":"12f109d8dc0c8473b232babbd81c26a7c5470c41",
"charge_ar":"1d9cb1da261e8b81b6877593f3f0d32355e20003",
"charge_au":"7808ad80a0bc76ad1cc3d108120e7756056a2bae",
"discharge_apr":"20d0a6bb3b62556062c217555453fe55571981d5",
"discharge_bse":"547110452eba1c659ecdd714112de087e7c486f3",
"discharge_sg":"f45ba212f6264ed8de1b3008e5a6061b2e8f6f91",
"discharge_lg":"8da2d7552295197daa6ef82d9041fa6b31c8210d",
"discharge_oem":"d2cb1442b0d70b44194b2237395e27b6905d404e",
"discharge_li":"613cf6d0bfb5301a70f4bb3cb2ff77927e1c229d",
"discharge_ar":"a5630e844284dd99d6c280550b978e933e8a94f9",
"discharge_au":"f3cc20b4cca462caa8a8b77dd3ed71c2fcd4e5e6"
}
OUT=pathlib.Path("out");OUT.mkdir(exist_ok=True)
def save_csv(name,rows):
    with (OUT/name).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def line_fit(x,y):
    n=len(x);sx=sum(x);sy=sum(y);sxx=sum(z*z for z in x);sxy=sum(z*v for z,v in zip(x,y))
    d=n*sxx-sx*sx
    if abs(d)<1e-12: return sy/n,0
    b=(n*sxy-sx*sy)/d;return (sy-b*sx)/n,b
def exponential(t,y,T):
    pairs=[(a,b) for a,b in zip(t,y) if a<=T+1e-8]
    ts=[p[0] for p in pairs];ys=[p[1] for p in pairs];n=len(ts)
    best=(float("inf"),0,0)
    for j in range(145):
        tau=0.02*3000**(j/144)
        e=[math.exp(-z/tau) for z in ts];a,b=line_fit(e,ys)
        err=sum((v-a-b*z)**2 for z,v in zip(e,ys))/n
        if err<best[0]: best=(err,a+b*math.exp(-24/tau),tau)
    return best[1],best[2]
def log_tail(t,y,T):
    pairs=[(math.log(a+.15),b) for a,b in zip(t,y) if T/4-1e-8<=a<=T+1e-8]
    a,b=line_fit([z[0] for z in pairs],[z[1] for z in pairs])
    return a+b*math.log(24.15)

curves=[];observations=[];provenance=[]
for key,expected in BLOB.items():
    name="ocv_relaxation_24h__24h_"+key+".csv"
    url="https://raw.githubusercontent.com/BulyK47/battery-datasets/"+COMMIT+"/ocv-relaxation-24h/csv/"+name
    req=urllib.request.Request(url,headers={"User-Agent":"CoDo-JV002-Research/0.2"})
    with urllib.request.urlopen(req,timeout=45) as f: raw=f.read()
    got=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if got!=expected:raise RuntimeError("Pinned input changed: "+name+" "+got)
    provenance.append({"path":name,"github_blob_sha1":got,"size_bytes":len(raw)})
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames[0]!="Timestamp [h]":raise RuntimeError("Unexpected header "+name)
    rows=list(reader)
    if len(rows)!=1441:raise RuntimeError("Unexpected 1min sample count "+name)
    t=[float(r["Timestamp [h]"]) for r in rows]
    if abs(t[0])>1e-8 or abs(t[-1]-24)>1e-8 or any(abs(b-a-1/60)>1e-8 for a,b in zip(t,t[1:])):
        raise RuntimeError("Unexpected time geometry "+name)
    cell=key.split("_")[-1];direction=key.split("_")[0]
    for channel in reader.fieldnames[1:]:
        soc=int(channel.split("_")[-1].split("-")[0])
        v=[float(r[channel]) for r in rows]
        if not all(math.isfinite(z) for z in v):raise RuntimeError("Nonfinite: "+channel)
        ident=cell+"_"+direction+"_"+str(soc)
        curves.append(dict(id=ident,cell=cell,chem=CHEM[cell],direction=direction,soc=soc,t=t,v=v))
        for ti,vi in zip(t,v):
            observations.append(dict(test_id="BULYK47_OCV_"+ident,timestamp_s=round(ti*3600,6),
               voltage_V=vi,measurement_type="ocv_relaxation",chemistry=CHEM[cell],
               conditioning_direction=direction,conditioning_soc_target_pct=soc,
               current_A="",temperature_C="",source_doi=DOI,source_license="CC-BY-4.0"))
if len(curves)!=30 or len(observations)!=43230 or len(set(c["cell"] for c in curves))!=8:
    raise RuntimeError("Unqualified full dataset geometry")
bench=[];metrics=[]
for c in curves:
    v=c["v"];t=c["t"];truth=statistics.median(v[-11:]);start=v[0]
    metrics.append(dict(id=c["id"],cell=c["cell"],chem=c["chem"],direction=c["direction"],
            target_soc_pct=c["soc"],start_V=start,end_24h_V=v[-1],
            median_last_10min_V=truth,observed_change_mV=round((v[-1]-start)*1000,3)))
    for T in [1,4,8]:
        hold=v[60*T];exp,tau=exponential(t,v,T);log=log_tail(t,v,T)
        bench.append(dict(id=c["id"],cell=c["cell"],chem=c["chem"],direction=c["direction"],cutoff_h=T,
            target_24h_V=truth,hold_V=hold,exp_V=exp,log_V=log,
            hold_error_mV=abs(hold-truth)*1000,exp_error_mV=abs(exp-truth)*1000,
            log_error_mV=abs(log-truth)*1000,fit_tau_hours=tau))
def aggreg(T,model):
    r=[x for x in bench if x["cutoff_h"]==T];errs=[x[model+"_error_mV"] for x in r]
    groups={}; 
    for x in r: groups.setdefault(x["cell"],[]).append(x[model+"_error_mV"])
    return dict(n=len(errs),n_cells=len(groups),trace_MAE_mV=round(statistics.mean(errs),3),
        cell_macro_MAE_mV=round(statistics.mean(statistics.mean(z) for z in groups.values()),3),
        trace_median_mV=round(statistics.median(errs),3),worst_mV=round(max(errs),3),
        n_over5mV=sum(v>5 for v in errs),n_over10mV=sum(v>10 for v in errs))
result=dict(executed=True,source_commit=COMMIT,source_doi=DOI,n_files=len(BLOB),n_cells=8,
            n_curves=len(curves),n_samples=len(observations),models={
                str(T):{m:aggreg(T,m) for m in ["hold","exp","log"]} for T in [1,4,8]},
            has_real_collaborators=False,proof_of_unique_joint_value=False,discovery_claim=False,
            observation_target="24h window tail median; NOT equilibrium OCV",
            limitations=["8 distinct cells; 30 highly dependent curves","small and chemically heterogeneous dataset",
            "simple fixed-parameter baselines not state-of-art methods","no new independent observation or external author approval"])
save_csv("curve_metrics.csv",metrics)
save_csv("holdout_models.csv",bench)
save_csv("semantic_preserving_measurements.csv",observations)
(OUT/"provenance.json").write_text(json.dumps(provenance,indent=2)+"\n")
(OUT/"results.json").write_text(json.dumps(result,indent=2)+"\n")
print("FULL_INPUT_REPRODUCTION_DONE",json.dumps(result,ensure_ascii=False))
