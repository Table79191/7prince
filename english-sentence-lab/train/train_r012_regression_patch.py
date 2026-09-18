#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "train"))
sys.path.insert(0, str(ROOT / "scripts"))

import train_ud_role as base
from canonical_roles import canonicalize_ud

VERSION = "1.8.2-R012-SCHOOL-REGRESSION"
SOURCE_WEIGHTS = {"ewt":1.0,"atis":0.7,"childes":0.35,"eslspok":0.7,"esl":0.7}
TEST_ONLY = {"ctetex","littleprince","pronouns","pud"}

def iter_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def row_example(row, family, weight):
    raw=row["analysis"]["tokens"]
    decisions=canonicalize_ud(raw)
    roles=[d.role for d in decisions]
    if "AMBIG" in roles:
        return None
    toks=base.normalize_surface_tokens(raw)
    weak=base.weak_base_roles(toks)
    feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]
    labels=[base.ROLE2I[r] for r in roles]
    return (feats,labels,row.get("text",""),family,float(weight))

def load_replay(root: Path):
    train=[]; dev=[]; eval_only=[]
    for path in sorted(root.glob("*.jsonl")):
        for row in iter_jsonl(path):
            if row.get("analysis",{}).get("status")!="auto_pass":
                continue
            src=row.get("source",{})
            key=src.get("key",path.stem)
            fn=src.get("filename","")
            if "-train." in fn and key in SOURCE_WEIGHTS:
                ex=row_example(row,f"replay:{key}",SOURCE_WEIGHTS[key])
                if ex: train.append(ex)
            elif "-dev." in fn:
                ex=row_example(row,f"dev:{key}",1.0)
                if ex: dev.append(ex)
            elif "-test." in fn and key in TEST_ONLY:
                ex=row_example(row,f"eval:{key}",1.0)
                if ex: eval_only.append(ex)
    rng=random.Random(81203)
    rng.shuffle(train)
    return train[:5000],dev,eval_only

def make_example(words, pos, roles, text=None, weight=2.0):
    toks=[{"text":w,"pos":p} for w,p in zip(words,pos)]
    weak=base.weak_base_roles(toks)
    feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]
    labels=[base.ROLE2I[r] for r in roles]
    return (feats,labels,text or " ".join(words),"school:regression",float(weight))

def school_examples():
    rows=[]

    # Direct copular WH questions. Browser input intentionally tags demonstratives
    # as DET before contextual postprocessing, so train the model on that exact input.
    singular=[("is","this"),("is","that"),("was","this"),("was","that")]
    plural=[("are","these"),("are","those"),("were","these"),("were","those")]
    for wh in ["what","who"]:
        for cop,dem in singular+plural:
            rows.append(make_example(
                [wh,cop,dem,"?"],
                ["PRON","AUX","DET","PUNCT"],
                ["C","V","S",None],
                weight=3.0,
            ))
            rows.append(make_example(
                [wh,"exactly",cop,dem,"?"],
                ["PRON","ADV","AUX","DET","PUNCT"],
                ["C","M","V","S",None],
                weight=3.0,
            ))

    for cop,dem in singular+plural:
        rows.append(make_example(
            ["what","the","hell",cop,dem,"?"],
            ["PRON","DET","NOUN","AUX","DET","PUNCT"],
            ["C","M","M","V","S",None],
            weight=4.0,
        ))
        rows.append(make_example(
            ["what","the","heck",cop,dem,"?"],
            ["PRON","DET","NOUN","AUX","DET","PUNCT"],
            ["C","M","M","V","S",None],
            weight=3.0,
        ))

    # Head-only noun phrases: modifiers must remain M, only nominal head is S/O/C.
    subj_prons=["I","we","they","she","he"]
    verbs=["use","need","want","see","find","take"]
    poss=["my","our","their","her","his"]
    nouns=["powers","books","boxes","tools","results","ideas"]
    nums=["0.001","1","3","10","50"]
    for i in range(120):
        s=subj_prons[i%len(subj_prons)]
        v=verbs[(i//2)%len(verbs)]
        d=poss[(i//3)%len(poss)]
        n=nouns[(i//5)%len(nouns)]
        num=nums[(i//7)%len(nums)]
        rows.append(make_example(
            [s,v,d,num,"%",n,"."],
            ["PRON","VERB","DET","NUM","SYM","NOUN","PUNCT"],
            ["S","V","M","M","M","O",None],
            weight=2.0,
        ))

    for i in range(100):
        adj=["exhausted","new","old","large","small"][i%5]
        noun=["interns","students","engineers","workers","robots"][i%5]
        verb=["worked","left","argued","helped","waited"][i%5]
        rows.append(make_example(
            ["the",adj,noun,verb,"."],
            ["DET","ADJ","NOUN","VERB","PUNCT"],
            ["M","M","S","V",None],
            weight=2.0,
        ))

    # Expanded contractions as the model actually sees them in the browser.
    auxs=["can","could","should","would","will","do","does","did"]
    for i in range(80):
        aux=auxs[i%len(auxs)]
        subject=["I","you","we","they"][i%4]
        verb=["believe","see","know","use"][i%4]
        obj=["it","them","this","that"][i%4]
        obj_pos="PRON" if obj in {"it","them"} else "DET"
        rows.append(make_example(
            [subject,aux,"not",verb,obj,"."],
            ["PRON","AUX","PART","VERB",obj_pos,"PUNCT"],
            ["S","V","M","V","O",None],
            weight=2.0,
        ))

    # Repeat the small high-value WH set so it is not drowned out by replay.
    core=rows[:48]
    rows.extend(core*8)
    return rows

def evaluate(model,data,device,batch=64):
    return base.evaluate(model,data,device,batch)

def train_epoch(model,data,opt,lossfn,device,batch,seed):
    rows=list(data); random.Random(seed).shuffle(rows)
    model.train(); total=correct=0; loss_sum=0.0; weighted=0.0
    for st in range(0,len(rows),batch):
        items=rows[st:st+batch]
        b,y,m=base.collate(items,device)
        sw=torch.tensor([float(x[4]) for x in items],device=device).unsqueeze(1)
        opt.zero_grad(set_to_none=True)
        z=model(b,m)
        raw=lossfn(z.view(-1,6),y.view(-1)).view_as(y)
        wm=m.float()*sw
        denom=wm.sum().clamp_min(1.0)
        loss=(raw*wm).sum()/denom
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(),1.0)
        opt.step()
        with torch.no_grad():
            p=z.argmax(-1)
            total+=int(m.sum().item())
            correct+=int(((p==y)&m).sum().item())
            loss_sum+=float(loss.item())*float(wm.sum().item())
            weighted+=float(wm.sum().item())
    return {"tokens":total,"loss":loss_sum/max(weighted,1.0),"train_acc":correct/max(total,1)}

def targeted_eval(model,target,device):
    r=evaluate(model,target,device,64)
    return r

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",default="artifacts/v1.8.1_r012_safe_feed_role.pt")
    ap.add_argument("--web-corpus",default="data/web_corpus_bot")
    ap.add_argument("--out",default="artifacts/v1.8.1_r012_safe_feed_role.pt")
    ap.add_argument("--metrics",default="artifacts/v1.8.1_r012_safe_feed_metrics.json")
    ap.add_argument("--epochs",type=int,default=5)
    args=ap.parse_args()

    torch.set_num_threads(4)
    random.seed(81203); torch.manual_seed(81203)
    device=torch.device("cpu")

    ck=torch.load(args.base,map_location="cpu",weights_only=False)
    model=base.RoleNet().to(device)
    model.load_state_dict(ck["model"],strict=True)

    replay,dev,eval_only=load_replay(Path(args.web_corpus))
    target=school_examples()

    baseline={
        "ud_dev":evaluate(model,dev,device),
        "eval_only":evaluate(model,eval_only,device),
        "target":targeted_eval(model,target,device),
    }

    # Fine-tune upper recurrent/attention/output layers; keep embeddings stable.
    for p in model.word.parameters(): p.requires_grad=False
    for p in model.pre.parameters(): p.requires_grad=False
    for p in model.suf.parameters(): p.requires_grad=False
    for p in model.pos.parameters(): p.requires_grad=False
    for p in model.brole.parameters(): p.requires_grad=False
    for p in model.shape.parameters(): p.requires_grad=False
    for p in model.proj.parameters(): p.requires_grad=False

    mix=replay+target
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1.2e-5,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=device)
    lossfn=nn.CrossEntropyLoss(weight=weights,reduction="none")

    best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    best_score=baseline["target"]["neural_role_acc"]
    selected_epoch=0; history=[]

    for ep in range(1,args.epochs+1):
        tr=train_epoch(model,mix,opt,lossfn,device,64,81203+ep)
        devm=evaluate(model,dev,device)
        targ=targeted_eval(model,target,device)
        safe=devm["neural_role_acc"] >= baseline["ud_dev"]["neural_role_acc"]-0.003
        history.append({"epoch":ep,"train":tr,"ud_dev":devm,"target":targ,"safe":safe})
        # Prefer target improvement, break ties with UD dev.
        score=targ["neural_role_acc"] + 0.02*devm["neural_role_acc"]
        best_cmp=best_score + 0.02*(baseline["ud_dev"]["neural_role_acc"] if selected_epoch==0 else 0)
        if safe and targ["neural_role_acc"]>=0.995 and (selected_epoch==0 or score>best_cmp):
            best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            best_score=targ["neural_role_acc"]
            selected_epoch=ep

    if selected_epoch==0:
        # Accept the safest best target-improving epoch even if <99.5%.
        candidates=[x for x in history if x["safe"] and x["target"]["neural_role_acc"]>baseline["target"]["neural_role_acc"]]
        if not candidates:
            raise SystemExit("no safe regression-patch candidate improved targeted accuracy")
        chosen=max(candidates,key=lambda x:(x["target"]["neural_role_acc"],x["ud_dev"]["neural_role_acc"]))
        # Re-run deterministically to chosen epoch from the baseline.
        model.load_state_dict(ck["model"],strict=True)
        for p in model.word.parameters(): p.requires_grad=False
        for p in model.pre.parameters(): p.requires_grad=False
        for p in model.suf.parameters(): p.requires_grad=False
        for p in model.pos.parameters(): p.requires_grad=False
        for p in model.brole.parameters(): p.requires_grad=False
        for p in model.shape.parameters(): p.requires_grad=False
        for p in model.proj.parameters(): p.requires_grad=False
        opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1.2e-5,weight_decay=3e-4)
        for ep in range(1,chosen["epoch"]+1):
            train_epoch(model,mix,opt,lossfn,device,64,81203+ep)
        best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        selected_epoch=chosen["epoch"]

    model.load_state_dict(best_state)
    selected={
        "ud_dev":evaluate(model,dev,device),
        "eval_only":evaluate(model,eval_only,device),
        "target":targeted_eval(model,target,device),
    }
    if selected["ud_dev"]["neural_role_acc"] < baseline["ud_dev"]["neural_role_acc"]-0.003:
        raise SystemExit("regression patch violated UD dev safety gate")

    metrics=dict(ck.get("metrics",{}))
    metrics["version"]=VERSION
    metrics["regression_patch"]={
        "selected_epoch":selected_epoch,
        "replay_sentences":len(replay),
        "target_sentences":len(target),
        "baseline":baseline,
        "selected":selected,
        "history":history,
        "safety_max_ud_dev_regression":0.003,
    }

    out=Path(args.out)
    torch.save({
        "model":model.state_dict(),
        "config":dict(ck.get("config",{}),school_regression_patch=True),
        "metrics":metrics,
    },out)
    Path(args.metrics).write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metrics["regression_patch"],indent=2))

if __name__=="__main__":
    main()
