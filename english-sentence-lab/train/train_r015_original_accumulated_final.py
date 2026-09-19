#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random, sys
from pathlib import Path
import torch
import torch.nn as nn

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"train"))
sys.path.insert(0,str(ROOT/"scripts"))

import train_ud_role as base
import train_r012_safe_feed as safe
import train_r012_regression_patch as reg
from train_gold_finetune import clone_state
from promoted_shards import iter_promoted

VERSION="1.8.5-R015-ACCUMULATED-FINAL"
PARENT=ROOT/"artifacts/v1.8.3_auto_promoted_silver_role.pt"

def exact_rate(m):
    return m["sentence_exact"]/max(m["sentences"],1)

def iter_jsonl(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def load_all_promoted(path,blocked,weight=0.08):
    rows=[]; dropped=0
    for r in iter_promoted(path):
        p=r.get("promotion",{})
        if p.get("status")!="auto_promoted_silver" or p.get("gate_version")!="PROMOTED-SILVER-1":
            continue
        k=safe.norm_text(r.get("text",""))
        if not k or k in blocked:
            dropped+=1; continue
        ex=safe.to_example(r,"promoted:"+str(r.get("source",{}).get("key","external")),weight)
        if ex is not None:
            rows.append(ex)
        else:
            dropped+=1
    # deterministic order independent of append history
    rows.sort(key=lambda x:safe.norm_text(x[2]))
    return rows,dropped

def set_lower_trainable(model,trainable):
    for module in [model.word,model.pre,model.suf,model.pos,model.brole,model.shape,model.proj]:
        for p in module.parameters():
            p.requires_grad=trainable
    for module in [model.gru,model.blocks,model.out]:
        for p in module.parameters():
            p.requires_grad=True

def train_epoch(model,data,opt,lossfn,device,batch,seed):
    rows=list(data); random.Random(seed).shuffle(rows)
    model.train(); total_loss=weighted=0.0; tokens=correct=0
    for st in range(0,len(rows),batch):
        items=rows[st:st+batch]
        b,y,m=base.collate(items,device)
        sw=torch.tensor([float(x[4]) for x in items],device=device).unsqueeze(1)
        opt.zero_grad(set_to_none=True)
        z=model(b,m)
        raw=lossfn(z.reshape(-1,6),y.reshape(-1)).reshape_as(y)
        wm=m.float()*sw
        denom=wm.sum().clamp_min(1.0)
        loss=(raw*wm).sum()/denom
        loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),0.9); opt.step()
        with torch.no_grad():
            p=z.argmax(-1)
            n=int(m.sum()); tokens+=n; correct+=int(((p==y)&m).sum())
            w=float(wm.sum()); weighted+=w; total_loss+=float(loss)*w
    return {"sentences":len(rows),"tokens":tokens,"weighted_tokens":weighted,
            "loss":total_loss/max(weighted,1.0),"train_acc":correct/max(tokens,1)}

def eval_all(model,dev,target,device,batch):
    dm=safe.evaluate(model,dev,device,batch)
    tm=reg.evaluate(model,target,device,batch)
    score=(dm["neural_role_acc"]
           +0.06*exact_rate(dm)
           +0.06*tm["neural_role_acc"]
           +0.02*exact_rate(tm))
    return dm,tm,score

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--parent",default=str(PARENT.relative_to(ROOT)))
    ap.add_argument("--web-corpus",default="data/web_corpus_bot")
    ap.add_argument("--promoted",default="data/promoted_silver/promoted.jsonl")
    ap.add_argument("--out",default="artifacts/r015_accumulated_final_role.pt")
    ap.add_argument("--metrics",default="artifacts/r015_accumulated_final_metrics.json")
    ap.add_argument("--batch",type=int,default=48)
    ap.add_argument("--silver-weight",type=float,default=0.08)
    ap.add_argument("--seed",type=int,default=91515)
    a=ap.parse_args()

    torch.set_num_threads(4); random.seed(a.seed); torch.manual_seed(a.seed)
    device=torch.device("cpu")

    gold,dev,eval_only,stats,_=safe.load_ud_web(ROOT/a.web_corpus)
    blocked={safe.norm_text(x[2]) for x in gold+dev+eval_only}
    promoted,dropped=load_all_promoted(ROOT/a.promoted,blocked,a.silver_weight)
    school_train,school_val=reg.school_sets()

    if not gold or not dev or len(promoted)<1000:
        raise SystemExit("R015 requires gold/dev and accumulated promoted silver")

    ck=torch.load(ROOT/a.parent,map_location="cpu",weights_only=False)
    model=base.RoleNet().to(device); model.load_state_dict(ck["model"],strict=True)

    baseline_dev,baseline_school,baseline_score=eval_all(model,dev,school_val,device,a.batch)
    best_state=clone_state(model); best_score=baseline_score; best_phase="parent"; hist=[]

    mix=list(gold)+list(promoted)+list(school_train)
    weights=torch.tensor([0.35,0.78,0.92,1.08,1.72,0.78],device=device)
    lossfn=nn.CrossEntropyLoss(weight=weights,reduction="none")

    phases=[
      {"name":"upper_accumulated","lower":False,"lr":2.5e-6,"epochs":1},
      {"name":"full_polish","lower":True,"lr":6.0e-7,"epochs":2},
    ]

    for phase in phases:
        set_lower_trainable(model,phase["lower"])
        opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                              lr=phase["lr"],weight_decay=3e-4)
        for ep in range(1,phase["epochs"]+1):
            tr=train_epoch(model,mix,opt,lossfn,device,a.batch,a.seed+len(hist)+1)
            dm,tm,score=eval_all(model,dev,school_val,device,a.batch)
            gates={
              "ud_token_safe":dm["neural_role_acc"]>=baseline_dev["neural_role_acc"]-0.0005,
              "ud_exact_safe":exact_rate(dm)>=exact_rate(baseline_dev)-0.0015,
              "school_safe":tm["neural_role_acc"]>=baseline_school["neural_role_acc"]-0.0020,
              "composite_improved":score>baseline_score+0.00002,
            }
            safe_ok=all(gates.values())
            rec={"phase":phase["name"],"epoch":ep,"lr":phase["lr"],"train":tr,
                 "ud_dev":dm,"school_validation":tm,"score":score,"gates":gates,"safe":safe_ok}
            hist.append(rec); print(json.dumps(rec))
            if safe_ok and score>best_score:
                best_score=score; best_state=clone_state(model)
                best_phase=f'{phase["name"]}:{ep}'

    model.load_state_dict(best_state)
    final_dev,final_school,final_score=eval_all(model,dev,school_val,device,a.batch)
    accepted=best_phase!="parent"

    metrics={
      "version":VERSION,
      "parent_checkpoint":str(a.parent),
      "parent_version":ck.get("metrics",{}).get("version","unknown"),
      "candidate_accepted":accepted,
      "selected_phase":best_phase,
      "params":sum(p.numel() for p in model.parameters()),
      "feed":{
        "approved_gold_train_sentences":len(gold),
        "accumulated_promoted_silver_sentences":len(promoted),
        "promoted_rows_dropped_after_recheck":dropped,
        "promoted_silver_weight":a.silver_weight,
        "school_replay_sentences":len(school_train),
        "combined_sentences":len(mix),
        "ud_stats":dict(stats),
      },
      "baseline":{"ud_dev":baseline_dev,"school_validation":baseline_school,"score":baseline_score},
      "selected":{"ud_dev":final_dev,"school_validation":final_school,"score":final_score},
      "history":hist,
      "policy":{
        "all_current_promoted_silver_included":True,
        "raw_tatoeba_mediawiki_never_directly_trained":True,
        "official_test_never_fit_or_select":True,
        "ud_dev_selection_only":True,
        "school_validation_never_fit":True,
        "chaos_and_shared_hardsets_not_used_for_selection":True,
      }
    }

    out=ROOT/a.out; out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"model":model.state_dict(),
                "config":dict(ck.get("config",{}),source="R015 accumulated final",
                              roles=base.I2ROLE,version=VERSION),
                "metrics":metrics},out)
    (ROOT/a.metrics).write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metrics,indent=2))

    if not accepted:
        raise SystemExit("R015: no accumulated-data candidate passed clean selection gates")

if __name__=="__main__":
    main()
