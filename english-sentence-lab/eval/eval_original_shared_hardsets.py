#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, json, sys
from pathlib import Path
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"train"))
import train_ud_role as base

EXP=ROOT/"experiments/clause_anchor_graph_v1_01"

def literal_assignments(path,names):
    tree=ast.parse(Path(path).read_text(encoding="utf-8"))
    out={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
            if name in names:
                out[name]=ast.literal_eval(node.value)
    return out

def predict(model,tokens,pos):
    toks=[{"text":w,"pos":p} for w,p in zip(tokens,pos)]
    toks=base.normalize_surface_tokens(toks)
    broles=base.weak_base_roles(toks)
    feats=[base.feat_token(t,b) for t,b in zip(toks,broles)]
    b,_,m=base.collate([(feats,[0]*len(feats),"","shared-hard")],torch.device("cpu"))
    with torch.no_grad():
        pred=model(b,m)[0,:len(feats)].argmax(-1).tolist()
    roles=[base.I2ROLE[int(i)] for i in pred]
    # Canonical invariants used by the current school-head role specification.
    for i,p in enumerate(pos):
        if p in {"VERB","AUX"}: roles[i]="V"
        elif p=="PUNCT": roles[i]=None
    return roles

def score_cases(model,cases,name):
    total=correct=exact=0; rows=[]
    for c in cases:
        pred=predict(model,c["tokens"],c["pos"])
        checks=[]; all_ok=True
        for raw,gold in c["focus"].items():
            i=int(raw); ok=pred[i]==gold; correct+=int(ok); total+=1; all_ok &= ok
            checks.append({"index":i,"token":c["tokens"][i],"gold":gold,"pred":pred[i],"ok":ok})
        exact+=int(all_ok)
        rows.append({"id":c["id"],"sentence":c["sentence"],"focus_correct":sum(x["ok"] for x in checks),
                     "focus_total":len(checks),"exact":all_ok,"checks":checks})
    return {"set":name,"sentences":len(cases),"focus_correct":correct,"focus_total":total,
            "focus_accuracy":correct/max(total,1),"exact_sentences":exact,
            "exact_rate":exact/max(len(cases),1),"cases":rows}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--model",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args()
    ck=torch.load(a.model,map_location="cpu",weights_only=False)
    model=base.RoleNet(); model.load_state_dict(ck["model"],strict=True); model.eval()

    h14=literal_assignments(EXP/"novel_hard14.py",{"CASES"})["CASES"]
    f16=literal_assignments(EXP/"final_blind16.py",{"CASES"})["CASES"]
    old=literal_assignments(EXP/"challenge_probe.py",{"SENTENCE","TOKENS","POS","FOCUS"})
    old_case=[{"id":"ORIGINAL_64","sentence":old["SENTENCE"],"tokens":old["TOKENS"],
               "pos":old["POS"],"focus":{str(k):v for k,v in old["FOCUS"].items()}}]

    result={
      "model_version":ck.get("metrics",{}).get("version",ck.get("config",{}).get("version","unknown")),
      "hard14":score_cases(model,h14,"NOVEL_HARD14_V1"),
      "final_blind16":score_cases(model,f16,"FINAL_BLIND16_V1"),
      "original64":score_cases(model,old_case,"ORIGINAL_64"),
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
      "model_version":result["model_version"],
      "hard14":{k:result["hard14"][k] for k in ("focus_correct","focus_total","focus_accuracy","exact_sentences")},
      "final_blind16":{k:result["final_blind16"][k] for k in ("focus_correct","focus_total","focus_accuracy","exact_sentences")},
      "original64":{k:result["original64"][k] for k in ("focus_correct","focus_total","focus_accuracy","exact_sentences")},
    },indent=2))

if __name__=="__main__": main()
