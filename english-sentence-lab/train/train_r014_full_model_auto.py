#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, random, sys
from datetime import datetime, timezone
from pathlib import Path
import torch, torch.nn as nn

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"train"))
sys.path.insert(0,str(ROOT/"scripts"))
import train_ud_role as base
import train_r012_safe_feed as safe
import train_r012_regression_patch as reg
from train_gold_finetune import clone_state
from promoted_shards import iter_promoted

LEGACY=ROOT/"artifacts/v1.8.3_auto_promoted_silver_role.pt"
CORE=ROOT/"artifacts/v1.8.2_r012_school_regression_role.pt"
POINTER=ROOT/"artifacts/latest_auto_model.json"

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
        ex=safe.to_example(r,"promoted:"+str(r.get("source",{}).get("key","external")),0.10)
        if ex is not None: rows.append((p.get("accepted_at_utc",""),k,ex))
    rows.sort(key=lambda x:(x[0],x[1]),reverse=True)
    return [x[2] for x in rows[:max_rows]],len(rows)

def resolve_parent():
    if POINTER.exists():
        try:
            j=json.loads(POINTER.read_text(encoding="utf-8"))
            rel=j.get("checkpoint")
            if rel:
                p=ROOT/rel
                if p.exists(): return p
        except Exception:
            pass
    if LEGACY.exists(): return LEGACY
    return CORE

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--promoted",default="data/promoted_silver/promoted.jsonl")
    ap.add_argument("--report",default="artifacts/auto_full_latest.json")
    ap.add_argument("--attempt-state",default="artifacts/full_auto_state.json")
    ap.add_argument("--epochs",type=int,default=2)
    ap.add_argument("--batch",type=int,default=32)
    ap.add_argument("--max-promoted",type=int,default=2000)
    ap.add_argument("--gold-replay",type=int,default=16000)
    ap.add_argument("--lr",type=float,default=1e-6)
    ap.add_argument("--seed",type=int,default=91414)
    a=ap.parse_args()

    torch.set_num_threads(4); random.seed(a.seed); torch.manual_seed(a.seed)
    device=torch.device("cpu")
    gold,dev,eval_only,stats,_=safe.load_ud_web(ROOT/"data/web_corpus_bot")
    blocked={safe.norm_text(x[2]) for x in gold+dev+eval_only}
    promoted,total=load_promoted(ROOT/a.promoted,blocked,a.max_promoted)

    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate_id=f"fm-{stamp}-p{total}"
    version=f"1.8.4-FULL-AUTO-{stamp}-P{total}"
    cdir=ROOT/"artifacts/auto_candidates"
    cdir.mkdir(parents=True,exist_ok=True)
    model_path=cdir/f"{candidate_id}_role.pt"
    metrics_path=cdir/f"{candidate_id}_metrics.json"

    report={
      "version":version,"candidate_id":candidate_id,"candidate_accepted":False,
      "candidate_path":str(model_path.relative_to(ROOT)),
      "metrics_path":str(metrics_path.relative_to(ROOT)),
      "promoted_selected":len(promoted),"promoted_available":total,
      "full_model_finetune":True,
    }
    if len(promoted)<64:
        report["reason"]="not_enough_promoted_rows"
        (ROOT/a.report).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,indent=2)); return

    parent=resolve_parent()
    ck=torch.load(parent,map_location="cpu",weights_only=False)
    model=base.RoleNet().to(device); model.load_state_dict(ck["model"],strict=True)
    # Full-model fine-tuning: every parameter remains trainable.
    for p in model.parameters(): p.requires_grad=True
    total_params=sum(p.numel() for p in model.parameters())
    trainable_params=sum(p.numel() for p in model.parameters() if p.requires_grad)
    if trainable_params != total_params:
        raise RuntimeError(f"full-model fine-tune invariant failed: {trainable_params}/{total_params}")

    replay=sorted(gold,key=lambda x:hashlib.sha256(safe.norm_text(x[2]).encode()).hexdigest())[:min(a.gold_replay,len(gold))]
    target_validation=reg.school_sets()[1]
    baseline_dev=safe.evaluate(model,dev,device,a.batch)
    baseline_target=reg.evaluate(model,target_validation,device)
    baseline_score=baseline_dev["neural_role_acc"]+0.05*exact_rate(baseline_dev)+0.05*baseline_target["neural_role_acc"]

    mix=list(replay)+list(promoted)
    opt=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=device)
    lossfn=nn.CrossEntropyLoss(weight=weights,reduction="none")

    best_observed=None; best_observed_score=-1.0; best_observed_epoch=0
    best_safe=None; best_safe_score=baseline_score; best_safe_epoch=0
    hist=[]
    for ep in range(1,a.epochs+1):
        tr=safe.weighted_train_epoch(model,mix,opt,lossfn,device,a.batch,a.seed+ep)
        dm=safe.evaluate(model,dev,device,a.batch)
        tm=reg.evaluate(model,target_validation,device)
        score=dm["neural_role_acc"]+0.05*exact_rate(dm)+0.05*tm["neural_role_acc"]
        gates={
          "ud_token_safe":dm["neural_role_acc"]>=baseline_dev["neural_role_acc"]-0.0002,
          "ud_exact_safe":exact_rate(dm)>=exact_rate(baseline_dev)-0.0005,
          "regression_validation_safe":tm["neural_role_acc"]>=baseline_target["neural_role_acc"]-0.002,
          "composite_improved":score>=baseline_score+0.00005,
        }
        safe_ok=all(gates.values())
        hist.append({"epoch":ep,"train":tr,"ud_dev":dm,"target_validation":tm,"score":score,"gates":gates,"safe":safe_ok})
        if score>best_observed_score:
            best_observed_score=score; best_observed_epoch=ep; best_observed=clone_state(model)
        if safe_ok and score>best_safe_score:
            best_safe_score=score; best_safe_epoch=ep; best_safe=clone_state(model)

    accepted=best_safe is not None
    chosen=best_safe if accepted else best_observed
    chosen_epoch=best_safe_epoch if accepted else best_observed_epoch
    chosen_score=best_safe_score if accepted else best_observed_score
    model.load_state_dict(chosen)
    selected_dev=safe.evaluate(model,dev,device,a.batch)
    selected_target=reg.evaluate(model,target_validation,device)

    metrics={
      "version":version,
      "candidate_id":candidate_id,
      "parent_checkpoint":str(parent.relative_to(ROOT)),
      "candidate_accepted":accepted,
      "selected_epoch":chosen_epoch,
      "selection_kind":"best_safe" if accepted else "best_observed_rejected",
      "params":total_params,
      "trainable_params":trainable_params,
      "full_model_finetune":trainable_params==total_params,
      "optimizer":{"name":"AdamW","lr":a.lr,"weight_decay":3e-4},
      "feed":{"gold_replay_sentences":len(replay),"promoted_silver_sentences":len(promoted),
              "promoted_available":total,"promoted_weight":0.10},
      "baseline":{"ud_dev":baseline_dev,"target_validation":baseline_target,"score":baseline_score},
      "selected":{"ud_dev":selected_dev,"target_validation":selected_target,"score":chosen_score},
      "history":hist,
      "policy":{"raw_external_never_directly_trained":True,"promoted_silver_only":True,
                "official_test_never_fit_or_select":True,"tatoeba_daily500_never_fit_or_select":True,
                "all_model_parameters_trainable":True,"new_checkpoint_every_attempt":True,
                "ud_token_max_regression":0.0002,"ud_exact_max_regression":0.0005,
                "regression_validation_max_regression":0.002,"composite_min_gain":0.00005},
    }
    torch.save({"model":model.state_dict(),"config":{"source":"full-model-auto-promoted-silver","roles":base.I2ROLE},"metrics":metrics},model_path)
    metrics_path.write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    report.update({
      "candidate_accepted":accepted,
      "reason":"full_model_gates_passed" if accepted else "no_full_model_candidate_passed_gates",
      "parent":str(parent.relative_to(ROOT)),
      "selected_epoch":chosen_epoch,
      "baseline_score":baseline_score,
      "selected_score":chosen_score,
      "total_params":total_params,
      "trainable_params":trainable_params,
    })
    (ROOT/a.report).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    state={"last_attempted_promoted_available":total,"last_candidate_id":candidate_id,
           "last_candidate_accepted":accepted,"updated_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    (ROOT/a.attempt_state).write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
