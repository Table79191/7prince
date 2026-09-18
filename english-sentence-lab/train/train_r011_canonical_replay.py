#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, random, sys
from collections import Counter
from pathlib import Path
import torch
import torch.nn as nn

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"train")); sys.path.insert(0,str(ROOT/"scripts"))
import train_ud_role as base
from canonical_roles import canonicalize_ud, canonicalize_masc
import train_gold_ewt_masc_replay as masc_legacy

VERSION="1.8.0-R011-CANONICAL-CLEAN"

def make_example(toks, decisions, text, family):
    if any(d.role=="AMBIG" for d in decisions): return None
    roles=[d.role for d in decisions]
    weak=base.weak_base_roles(toks)
    feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]
    labels=[base.ROLE2I[r] for r in roles]
    return (feats,labels,text,family)

def load_ud_canonical(root,max_train=10000,max_val=2000):
    train=[]; val=[]; stats=Counter()
    for path in sorted(Path(root).rglob("*.conllu")):
        corpus=path.parent.name
        split="train" if "-train." in path.name else ("dev" if "-dev." in path.name else "test")
        rows=[]
        for meta,toks in base.parse_conllu(path):
            if not (2<=len(toks)<=160): continue
            toks=base.normalize_surface_tokens(toks)
            ex=make_example(toks,canonicalize_ud(toks),meta.get("text",""),corpus)
            if ex is None:
                stats["ambig_sentences_dropped"]+=1; continue
            rows.append(ex)
        random.Random(79191+len(path.name)).shuffle(rows)
        if split=="train":
            rows=rows[:max_train]; train.extend(rows); stats["train"]+=len(rows)
        elif split=="dev":
            rows=rows[:max_val]; val.extend(rows); stats["val"]+=len(rows)
        else:
            stats["official_test_excluded"]+=len(rows)
    return train,val,dict(stats)

def load_masc_canonical(root):
    train=[]; val=[]; stats=Counter(); root=Path(root)
    for path in sorted(root.rglob("*.conll")):
        if "__MACOSX" in path.parts: continue
        text=masc_legacy.decode_bytes(path.read_bytes()); lines=[]
        for raw in text.splitlines()+[""]:
            if raw.strip():
                lines.append(raw.rstrip("\r")); continue
            if not lines: continue
            toks,reason=masc_legacy.parse_masc_sentence(lines); lines=[]
            if toks is None:
                stats[f"reject_{reason}"]+=1; continue
            ex=make_example(toks,canonicalize_masc(toks)," ".join(t["text"] for t in toks),"masc")
            if ex is None:
                stats["ambig_sentences_dropped"]+=1; continue
            h=int(hashlib.sha1((path.name+"\n"+ex[2]).encode("utf-8")).hexdigest()[:8],16)%100
            (train if h<85 else val).append(ex)
            stats["train" if h<85 else "val"]+=1
    return train,val,dict(stats)

def evaluate(model,data,device,batch):
    return base.evaluate(model,data,device,batch)

def score(m):
    return 1.25*m["ewt"]["neural_role_acc"]+m["ud"]["neural_role_acc"]+0.70*m["masc"]["neural_role_acc"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",default="none")
    ap.add_argument("--ud",default="data/ud")
    ap.add_argument("--ewt",default="data/gold_external/ewt")
    ap.add_argument("--masc",default="data/gold_external/masc_conll/extracted/masc-conll/data")
    ap.add_argument("--out",default="artifacts/v1.8.0_r011_canonical_role.pt")
    ap.add_argument("--metrics",default="artifacts/v1.8.0_r011_canonical_metrics.json")
    ap.add_argument("--epochs",type=int,default=3); ap.add_argument("--batch",type=int,default=32)
    args=ap.parse_args()
    torch.set_num_threads(4); random.seed(79191); torch.manual_seed(79191); device=torch.device("cpu")

    ud_tr,ud_va,ud_stats=load_ud_canonical(args.ud,6000,1200)
    ew_tr,ew_va,ew_stats=load_ud_canonical(args.ewt,16000,2000)
    ma_tr,ma_va,ma_stats=load_masc_canonical(args.masc)
    if not ud_tr or not ew_tr or not ud_va or not ew_va:
        raise SystemExit("clean R011 split unexpectedly empty")

    if str(args.base).lower() not in {"", "none", "random"}:
        raise SystemExit("clean R011 must start from random initialization; pretrained bases are forbidden")
    model=base.RoleNet().to(device)
    sets={"ewt":ew_va,"ud":ud_va,"masc":ma_va}
    baseline={k:evaluate(model,v,device,args.batch) for k,v in sets.items()}
    best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    best=baseline; best_epoch=0; best_score=score(baseline)

    mix=list(ud_tr)+list(ew_tr)+list(ma_tr)
    opt=torch.optim.AdamW(model.parameters(),lr=4e-5,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=device)
    lossfn=nn.CrossEntropyLoss(weight=weights,reduction="none")
    history=[]
    for ep in range(1,args.epochs+1):
        random.Random(88110+ep).shuffle(mix)
        model.train(); tok=cor=0; lsum=0.0
        for st in range(0,len(mix),args.batch):
            items=mix[st:st+args.batch]; b,y,m=base.collate(items,device)
            opt.zero_grad(set_to_none=True); z=model(b,m)
            raw=lossfn(z.view(-1,6),y.view(-1)).view_as(y); loss=(raw*m).sum()/m.sum()
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
            with torch.no_grad():
                p=z.argmax(-1); n=int(m.sum().item()); tok+=n; cor+=int(((p==y)&m).sum().item()); lsum+=float(loss.item())*n
        cur={k:evaluate(model,v,device,args.batch) for k,v in sets.items()}
        sc=score(cur)
        safe=(cur["ewt"]["neural_role_acc"]>=baseline["ewt"]["neural_role_acc"]-0.005 and
              cur["ud"]["neural_role_acc"]>=baseline["ud"]["neural_role_acc"]-0.0075 and
              cur["masc"]["neural_role_acc"]>=baseline["masc"]["neural_role_acc"]-0.005)
        history.append({"epoch":ep,"train":{"tokens":tok,"loss":lsum/max(tok,1),"accuracy":cor/max(tok,1)},"eval":cur,"score":sc,"safe":safe})
        if safe and sc>best_score:
            best_score=sc; best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}; best=cur; best_epoch=ep

    model.load_state_dict(best_state)
    metrics={"version":VERSION,"base":"random-init","selected_epoch":best_epoch,"baseline":baseline,"selected":best,"history":history,
             "data_stats":{"ud":ud_stats,"ewt":ew_stats,"masc":ma_stats},
             "policy":{"official_train_only_for_fit":True,"official_dev_only_for_selection":True,"official_test_never_fit_or_select":True,
                       "synthetic_gold_not_used_for_fit_or_selection":True,"canonical_role_spec":"v2-head-only"},
             "note":"Clean R011 lineage starts from random initialization and excludes every official UD/EWT test row from fitting and model selection."}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"model":model.state_dict(),"config":{"gru":3,"attn":1,"source":"random init + canonical UD/EWT/MASC train only","roles":base.I2ROLE,"canonical_role_spec":"v2-head-only"},"metrics":metrics},out)
    Path(args.metrics).write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metrics,indent=2))

if __name__=="__main__": main()
