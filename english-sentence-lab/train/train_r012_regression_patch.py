#!/usr/bin/env python3
from __future__ import annotations
import argparse, itertools, json, random, sys
from pathlib import Path
import torch
import torch.nn as nn

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"train")); sys.path.insert(0,str(ROOT/"scripts"))
import train_ud_role as base
from canonical_roles import canonicalize_ud

VERSION="1.8.2-R012-SCHOOL-REGRESSION"
SOURCE_WEIGHTS={"ewt":1.0,"atis":0.7,"childes":0.35,"eslspok":0.7,"esl":0.7}

def iter_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def row_example(row,family,weight):
    raw=row["analysis"]["tokens"]; roles=[d.role for d in canonicalize_ud(raw)]
    if "AMBIG" in roles: return None
    toks=base.normalize_surface_tokens(raw); weak=base.weak_base_roles(toks)
    feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]; labels=[base.ROLE2I[r] for r in roles]
    return (feats,labels,row.get("text",""),family,float(weight))

def load_replay(root):
    train=[]; dev=[]
    for path in sorted(Path(root).glob("*.jsonl")):
        for row in iter_jsonl(path):
            if row.get("analysis",{}).get("status")!="auto_pass": continue
            src=row.get("source",{}); key=src.get("key",path.stem); fn=src.get("filename","")
            if "-train." in fn and key in SOURCE_WEIGHTS:
                ex=row_example(row,f"replay:{key}",SOURCE_WEIGHTS[key])
                if ex: train.append(ex)
            elif "-dev." in fn:
                ex=row_example(row,f"dev:{key}",1.0)
                if ex: dev.append(ex)
    rng=random.Random(81203); rng.shuffle(train); return train[:5000],dev

def make_example(words,pos,roles,family,weight=2.0):
    toks=[{"text":w,"pos":p} for w,p in zip(words,pos)]; weak=base.weak_base_roles(toks)
    feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]; labels=[base.ROLE2I[r] for r in roles]
    return (feats,labels," ".join(words),family,float(weight))

def school_sets():
    train=[]; holdout=[]
    for wh,cop,dem in itertools.product(["what","who"],["is","are","was","were"],["this","that","these","those"]):
        if (cop in {"is","was"})!=(dem in {"this","that"}): continue
        train.append(make_example([wh,cop,dem,"?"],["PRON","AUX","DET","PUNCT"],["C","V","S",None],"school:train:wh",3.0))
        train.append(make_example([wh,"exactly",cop,dem,"?"],["PRON","ADV","AUX","DET","PUNCT"],["C","M","V","S",None],"school:train:wh",3.0))
    for words,pos,roles in [
      (["what","on","earth","was","that","?"],["PRON","ADP","NOUN","AUX","DET","PUNCT"],["C","M","M","V","S",None]),
      (["who","in","the","world","is","this","?"],["PRON","ADP","DET","NOUN","AUX","DET","PUNCT"],["C","M","M","M","V","S",None]),
      (["what","in","the","world","are","those","?"],["PRON","ADP","DET","NOUN","AUX","DET","PUNCT"],["C","M","M","M","V","S",None]),
      (["who","on","earth","were","these","?"],["PRON","ADP","NOUN","AUX","DET","PUNCT"],["C","M","M","V","S",None]),
    ]: holdout.append(make_example(words,pos,roles,"school:holdout:wh",1.0))

    prod=itertools.product(["I","we","they","she","he"],["use","need","want","see","find","take"],["my","our","their","her","his"],["0.001","1","3","10","50"],["powers","books","boxes","tools","results","ideas"])
    for s,v,d,num,n in itertools.islice(prod,160):
        train.append(make_example([s,v,d,num,"%",n,"."],["PRON","VERB","DET","NUM","SYM","NOUN","PUNCT"],["S","V","M","M","M","O",None],"school:train:np-head",2.0))
    for words in [["we","inspect","these","12","%","documents","."],["they","compare","those","7","%","models","."],["I","check","my","25","%","files","."],["she","reviews","her","4","%","samples","."]]:
        holdout.append(make_example(words,["PRON","VERB","DET","NUM","SYM","NOUN","PUNCT"],["S","V","M","M","M","O",None],"school:holdout:np-head",1.0))

    for adj,noun,verb in itertools.product(["exhausted","new","old","large","small"],["interns","students","engineers","workers","robots"],["worked","left","argued","helped","waited"]):
        train.append(make_example(["the",adj,noun,verb,"."],["DET","ADJ","NOUN","VERB","PUNCT"],["M","M","S","V",None],"school:train:adj",2.0))
    for adj,noun,verb in [("talented","designers","performed"),("gifted","children","learned"),("ready","teams","started"),("skilled","analysts","responded")]:
        holdout.append(make_example(["the",adj,noun,verb,"."],["DET","ADJ","NOUN","VERB","PUNCT"],["M","M","S","V",None],"school:holdout:adj",1.0))

    for subject,aux,verb,obj in itertools.product(["I","you","we","they"],["can","will","do","does"],["believe","see","know","use"],["it","them"]):
        train.append(make_example([subject,aux,"not",verb,obj,"."],["PRON","AUX","PART","VERB","PRON","PUNCT"],["S","V","M","V","O",None],"school:train:neg",2.0))
    for words,pos,roles in [
      (["he","should","not","rely","on","it","."],["PRON","AUX","PART","VERB","ADP","PRON","PUNCT"],["S","V","M","V","M","O",None]),
      (["she","could","not","focus","on","them","."],["PRON","AUX","PART","VERB","ADP","PRON","PUNCT"],["S","V","M","V","M","O",None]),
      (["they","must","not","perform","poorly","."],["PRON","AUX","PART","VERB","ADV","PUNCT"],["S","V","M","V","M",None]),
      (["we","would","not","practice","today","."],["PRON","AUX","PART","VERB","ADV","PUNCT"],["S","V","M","V","M",None]),
    ]: holdout.append(make_example(words,pos,roles,"school:holdout:neg",1.0))

    a={x[2].lower() for x in train}; b={x[2].lower() for x in holdout}
    if len(a)!=len(train) or len(b)!=len(holdout) or a&b: raise RuntimeError("regression train/holdout not disjoint")
    return train,holdout

def evaluate(model,data,device,batch=64): return base.evaluate(model,data,device,batch)

def train_epoch(model,data,opt,lossfn,device,batch,seed):
    rows=list(data); random.Random(seed).shuffle(rows); model.train(); total=correct=0; loss_sum=weighted=0.0
    for st in range(0,len(rows),batch):
        items=rows[st:st+batch]; b,y,m=base.collate(items,device); sw=torch.tensor([float(x[4]) for x in items],device=device).unsqueeze(1)
        opt.zero_grad(set_to_none=True); z=model(b,m); raw=lossfn(z.view(-1,6),y.view(-1)).view_as(y); wm=m.float()*sw; loss=(raw*wm).sum()/wm.sum().clamp_min(1.0)
        loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
        with torch.no_grad():
            p=z.argmax(-1); total+=int(m.sum().item()); correct+=int(((p==y)&m).sum().item()); loss_sum+=float(loss.item())*float(wm.sum().item()); weighted+=float(wm.sum().item())
    return {"tokens":total,"loss":loss_sum/max(weighted,1.0),"train_acc":correct/max(total,1)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--base",default="artifacts/v1.8.1_r012_safe_feed_role.pt"); ap.add_argument("--web-corpus",default="data/web_corpus_bot")
    ap.add_argument("--out",default="artifacts/v1.8.2_r012_school_regression_role.pt"); ap.add_argument("--metrics",default="artifacts/v1.8.2_r012_school_regression_metrics.json"); ap.add_argument("--epochs",type=int,default=5)
    args=ap.parse_args(); torch.set_num_threads(4); random.seed(81203); torch.manual_seed(81203); device=torch.device("cpu")

    ck=torch.load(args.base,map_location="cpu",weights_only=False); base_version=ck.get("metrics",{}).get("version","")
    if base_version!="1.8.1-R012-SAFE-FEED-SCHOOL-HEADS": raise SystemExit(f"refusing non-safe-feed base: {base_version!r}")
    model=base.RoleNet().to(device); model.load_state_dict(ck["model"],strict=True)
    replay,dev=load_replay(Path(args.web_corpus)); target_train,target_holdout=school_sets()
    baseline_dev=evaluate(model,dev,device); baseline_holdout=evaluate(model,target_holdout,device)

    for module in [model.word,model.pre,model.suf,model.pos,model.brole,model.shape,model.proj]:
        for p in module.parameters(): p.requires_grad=False
    mix=replay+target_train; opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=1.2e-5,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=device); lossfn=nn.CrossEntropyLoss(weight=weights,reduction="none")
    best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}; best_score=baseline_holdout["neural_role_acc"]+0.02*baseline_dev["neural_role_acc"]; selected_epoch=0; history=[]
    for ep in range(1,args.epochs+1):
        tr=train_epoch(model,mix,opt,lossfn,device,64,81203+ep); devm=evaluate(model,dev,device); hold=evaluate(model,target_holdout,device)
        safe=devm["neural_role_acc"]>=baseline_dev["neural_role_acc"]-0.003; score=hold["neural_role_acc"]+0.02*devm["neural_role_acc"]
        history.append({"epoch":ep,"train":tr,"ud_dev":devm,"target_holdout":hold,"score":score,"safe":safe})
        if safe and score>best_score:
            best_score=score; best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}; selected_epoch=ep
    if selected_epoch==0: raise SystemExit("no safe regression candidate improved the disjoint holdout")
    model.load_state_dict(best_state); selected_dev=evaluate(model,dev,device); selected_holdout=evaluate(model,target_holdout,device)
    if selected_dev["neural_role_acc"]<baseline_dev["neural_role_acc"]-0.003 or selected_holdout["neural_role_acc"]<=baseline_holdout["neural_role_acc"]: raise SystemExit("regression promotion gate failed")

    metrics={"version":VERSION,"base":Path(args.base).name,"regression_patch":{"selected_epoch":selected_epoch,"replay_sentences":len(replay),"target_train_sentences":len(target_train),"target_holdout_sentences":len(target_holdout),"train_holdout_overlap":0,
    "baseline":{"ud_dev":baseline_dev,"target_holdout":baseline_holdout},"selected":{"ud_dev":selected_dev,"target_holdout":selected_holdout},"history":history,"safety_max_ud_dev_regression":0.003,"selection_metric":"disjoint_target_holdout + 0.02*ud_dev"},
    "policy":{"official_test_never_used_for_fit_or_selection":True,"target_holdout_never_used_for_fit":True,"canonical_role_spec":"v2-head-only"}}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); torch.save({"model":model.state_dict(),"config":dict(ck.get("config",{}),school_regression_patch=True,canonical_role_spec="v2-head-only"),"metrics":metrics},out)
    Path(args.metrics).write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8"); print(json.dumps(metrics,indent=2))

if __name__=="__main__": main()
