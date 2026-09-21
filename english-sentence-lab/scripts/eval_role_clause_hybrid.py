#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path

import torch

ROOT=Path(__file__).resolve().parents[1]
ARENA_PATH=ROOT/"arena"/"run_model_arena.py"
spec=importlib.util.spec_from_file_location("arena_mod",ARENA_PATH)
arena=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(arena)

device=torch.device("cpu")
torch.set_num_threads(4)

role_ck=torch.load(ROOT/"artifacts/arena_hotfeed/role_arena_latest.pt",map_location="cpu",weights_only=False)
clause_ck=torch.load(ROOT/"artifacts/arena_hotfeed/clause_arena_latest.pt",map_location="cpu",weights_only=False)
role=arena.rbase.RoleNet().to(device); role.load_state_dict(role_ck["model"],strict=True); role.eval()
clause=arena.cmodel.ClauseAnchorGraph().to(device); clause.load_state_dict(clause_ck["model"],strict=True); clause.eval()

_,_,dev=arena.load_pools(ROOT/"data/web_corpus_bot",ROOT/"data/promoted_silver/promoted.jsonl")

ROLE2I=arena.rbase.ROLE2I
CORE={"S","V","O","C"}


def infer_role_batch(recs,batch_size=64):
    out=[]
    with torch.no_grad():
        for st in range(0,len(recs),batch_size):
            chunk=recs[st:st+batch_size]
            items=[arena.role_item(x,1.0) for x in chunk]
            b,y,m=arena.rbase.collate(items,device)
            z=role(b,m)
            prob=torch.softmax(z,-1)
            pred=z.argmax(-1)
            conf=prob.max(-1).values
            for j,rec in enumerate(chunk):
                toks=rec["row"]["analysis"]["tokens"]; n=len(toks)
                rr=[arena.rbase.I2ROLE[int(x)] for x in pred[j,:n].tolist()]
                cc=[float(x) for x in conf[j,:n].tolist()]
                for i,t in enumerate(toks):
                    if t.get("pos") in {"VERB","AUX"}:
                        rr[i]="V"; cc[i]=1.0
                    elif t.get("pos")=="PUNCT":
                        rr[i]=None; cc[i]=1.0
                out.append((rr,cc))
    return out


def infer_clause_batch(recs,batch_size=48):
    out=[]
    with torch.no_grad():
        for st in range(0,len(recs),batch_size):
            chunk=recs[st:st+batch_size]
            items=[arena.clause_item(x,1.0) for x in chunk]
            b,y,owner,heads,mask,w=arena.cdata.collate(items,device)
            pids=b["pos"].detach().cpu().tolist()
            dec=arena.cmodel.decode(clause,b,mask,pids)
            out.extend([(x.roles,x.owners,x.clause_heads) for x in dec])
    return out


rpred=infer_role_batch(dev)
cpred=infer_clause_batch(dev)
assert len(rpred)==len(cpred)==len(dev)


def score(preds):
    tok=cor=exact=0
    for rec,p in zip(dev,preds):
        g=arena.canonical_roles(rec["row"])
        tok+=len(g)
        cor+=sum(a==b for a,b in zip(g,p))
        exact+=int(g==p)
    acc=cor/max(tok,1)
    ex=exact/max(len(dev),1)
    return {"tokens":tok,"correct":cor,"role_accuracy":acc,"sentence_exact":exact,"sentence_exact_rate":ex,"score":acc+0.06*ex}


role_only=[x[0] for x in rpred]
clause_only=[x[0] for x in cpred]
results={
    "role_only":score(role_only),
    "clause_only":score(clause_only),
}

candidates=[]
for thr in [0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85,0.90,0.93,0.95]:
    # Conservative token fusion: Clause may only replace a low-confidence RoleNet
    # decision in a sentence where ClauseAnchorGraph detects multiple clause heads.
    pred=[]
    replacements=0
    for (rr,conf),(cr,owners,heads) in zip(rpred,cpred):
        p=list(rr)
        complex_sentence=len(heads)>=2
        if complex_sentence:
            for i,(a,b,c) in enumerate(zip(rr,cr,conf)):
                if a!=b and c<thr and b is not None:
                    p[i]=b; replacements+=1
        pred.append(p)
    m=score(pred)
    m["replacements"]=replacements
    name=f"complex_lowconf_{thr:.2f}"
    results[name]=m
    candidates.append((m["score"],name,pred))

for thr in [0.60,0.70,0.80,0.85,0.90,0.93,0.95]:
    # Extra-conservative variant: only use Clause to recover a core role where
    # RoleNet currently says modifier/none.
    pred=[]
    replacements=0
    for (rr,conf),(cr,owners,heads) in zip(rpred,cpred):
        p=list(rr)
        if len(heads)>=2:
            for i,(a,b,c) in enumerate(zip(rr,cr,conf)):
                if a in {"M",None} and b in CORE and c<thr:
                    p[i]=b; replacements+=1
        pred.append(p)
    m=score(pred)
    m["replacements"]=replacements
    name=f"complex_core_recovery_{thr:.2f}"
    results[name]=m
    candidates.append((m["score"],name,pred))

best=max(candidates,key=lambda x:x[0])
baseline=results["role_only"]

# Inspect disagreement/oracle headroom.
role_better=clause_better=tie=both_wrong=0
oracle=[]
for rec,(rr,_),(cr,_,_) in zip(dev,rpred,cpred):
    g=arena.canonical_roles(rec["row"])
    er=sum(a!=b for a,b in zip(g,rr))
    ec=sum(a!=b for a,b in zip(g,cr))
    if er<ec: role_better+=1
    elif ec<er: clause_better+=1
    else: tie+=1
    if er and ec: both_wrong+=1
    oracle.append(rr if er<=ec else cr)

report={
    "role_checkpoint":role_ck.get("config",{}).get("version"),
    "clause_checkpoint":clause_ck.get("config",{}).get("version"),
    "dev_sentences":len(dev),
    "baseline":baseline,
    "clause":results["clause_only"],
    "best_candidate":{"name":best[1],**results[best[1]]},
    "best_beats_role":results[best[1]]["score"]>baseline["score"],
    "disagreement":{"role_better_sentences":role_better,"clause_better_sentences":clause_better,"tie_sentences":tie,"both_wrong_sentences":both_wrong},
    "oracle_sentence_switch":score(oracle),
    "candidates":results,
}
print(json.dumps(report,ensure_ascii=False,indent=2))
