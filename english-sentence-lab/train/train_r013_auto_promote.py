#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, random, sys
from pathlib import Path
import torch, torch.nn as nn

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"train"))
sys.path.insert(0,str(ROOT/"scripts"))
import train_ud_role as base
import train_r012_safe_feed as safe
import train_r012_regression_patch as reg
from train_gold_finetune import clone_state
from train_gold_replay import freeze_lower
from promoted_shards import iter_promoted

VERSION="1.8.3-AUTO-PROMOTED-SILVER"
AUTO=ROOT/"artifacts/v1.8.3_auto_promoted_silver_role.pt"
CORE=ROOT/"artifacts/v1.8.2_r012_school_regression_role.pt"

def iter_jsonl(path):
    if not path.exists(): return
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip(): yield json.loads(line)

def exact_rate(m): return m["sentence_exact"]/max(m["sentences"],1)

def load_promoted(path,blocked,max_rows):
    rows=[]
    for r in iter_promoted(path):
        p=r.get("promotion",{})
        if p.get("status")!="auto_promoted_silver" or p.get("gate_version")!="PROMOTED-SILVER-1": continue
        k=safe.norm_text(r.get("text",""))
        if not k or k in blocked: continue
        ex=safe.to_example(r,"promoted:"+str(r.get("source",{}).get("key","external")),0.12)
        if ex is not None: rows.append((p.get("accepted_at_utc",""),k,ex))
    rows.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return [x[2] for x in rows[:max_rows]],len(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--promoted",default="data/promoted_silver/promoted.jsonl")
    ap.add_argument("--out",default="artifacts/v1.8.3_auto_promoted_silver_role.pt")
    ap.add_argument("--metrics",default="artifacts/v1.8.3_auto_promoted_silver_metrics.json")
    ap.add_argument("--report",default="artifacts/auto_promote_latest.json")
    ap.add_argument("--epochs",type=int,default=2)
    ap.add_argument("--batch",type=int,default=32)
    a=ap.parse_args()
    torch.set_num_threads(4); random.seed(91313); torch.manual_seed(91313)
    device=torch.device("cpu")

    gold,dev,eval_only,stats,_=safe.load_ud_web(ROOT/"data/web_corpus_bot")
    blocked={safe.norm_text(x[2]) for x in gold+dev+eval_only}
    promoted,total=load_promoted(ROOT/a.promoted,blocked,1200)
    report={"version":VERSION,"candidate_accepted":False,"promoted_selected":len(promoted),"promoted_available":total}
    if len(promoted)<64:
        report["reason"]="not_enough_promoted_rows"
        (ROOT/a.report).write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); return

    base_path=AUTO if AUTO.exists() else CORE
    ck=torch.load(base_path,map_location="cpu",weights_only=False)
    model=base.RoleNet().to(device); model.load_state_dict(ck["model"],strict=True); freeze_lower(model)

    # deterministic gold replay, plus low-weight promoted silver
    replay=sorted(gold,key=lambda x:hashlib.sha256(safe.norm_text(x[2]).encode()).hexdigest())[:10000]
    target_validation=reg.school_sets()[1]
    baseline_dev=safe.evaluate(model,dev,device,a.batch)
    baseline_target=reg.evaluate(model,target_validation,device)
    baseline_score=baseline_dev["neural_role_acc"]+0.05*exact_rate(baseline_dev)+0.05*baseline_target["neural_role_acc"]

    mix=list(replay)+list(promoted)
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=3e-6,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=device)
    lossfn=nn.CrossEntropyLoss(weight=weights,reduction="none")
    best=None; best_score=baseline_score; best_epoch=0; hist=[]
    for ep in range(1,a.epochs+1):
        tr=safe.weighted_train_epoch(model,mix,opt,lossfn,device,a.batch,91313+ep)
        dm=safe.evaluate(model,dev,device,a.batch)
        tm=reg.evaluate(model,target_validation,device)
        score=dm["neural_role_acc"]+0.05*exact_rate(dm)+0.05*tm["neural_role_acc"]
        gates={
          "ud_token_safe":dm["neural_role_acc"]>=baseline_dev["neural_role_acc"]-0.0003,
          "ud_exact_safe":exact_rate(dm)>=exact_rate(baseline_dev)-0.001,
          "regression_validation_safe":tm["neural_role_acc"]>=baseline_target["neural_role_acc"]-0.003,
          "composite_improved":score>=baseline_score+0.0001,
        }
        safe_ok=all(gates.values())
        hist.append({"epoch":ep,"train":tr,"ud_dev":dm,"target_validation":tm,"score":score,"gates":gates,"safe":safe_ok})
        if safe_ok and score>best_score:
            best_score=score; best_epoch=ep; best=clone_state(model)
    if best is None:
        report.update({"reason":"no_candidate_passed_promotion_gates","parent":base_path.name,
                       "baseline":{"ud_dev":baseline_dev,"target_validation":baseline_target,"score":baseline_score},"history":hist})
        (ROOT/a.report).write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); return

    model.load_state_dict(best)
    selected_dev=safe.evaluate(model,dev,device,a.batch)
    selected_target=reg.evaluate(model,target_validation,device)
    metrics={
      "version":VERSION,"parent_checkpoint":base_path.name,"selected_epoch":best_epoch,
      "feed":{"gold_replay_sentences":len(replay),"promoted_silver_sentences":len(promoted),"promoted_available":total,
              "promoted_weight":0.12},
      "baseline":{"ud_dev":baseline_dev,"target_validation":baseline_target,"score":baseline_score},
      "selected":{"ud_dev":selected_dev,"target_validation":selected_target,"score":best_score},
      "history":hist,
      "policy":{"raw_external_never_directly_trained":True,"promoted_silver_only":True,
                "official_test_never_fit_or_select":True,"tatoeba_daily500_never_fit_or_select":True,
                "ud_token_max_regression":0.0003,"ud_exact_max_regression":0.001,
                "regression_validation_max_regression":0.003,"composite_min_gain":0.0001},
    }
    out=ROOT/a.out; out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"model":model.state_dict(),"config":{"source":"auto-promoted-silver","roles":base.I2ROLE},"metrics":metrics},out)
    (ROOT/a.metrics).write_text(json.dumps(metrics,indent=2)+"\n")
    report.update({"candidate_accepted":True,"reason":"promotion_gates_passed","parent":base_path.name,
                   "selected_epoch":best_epoch,"baseline_score":baseline_score,"selected_score":best_score})
    (ROOT/a.report).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
