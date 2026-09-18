from __future__ import annotations
import argparse
import json
from pathlib import Path
import torch
from infer import make_batch
from model import ClauseAnchorGraph, decode, VERSION

SENTENCE = "Although the researcher whom the committee had expected to resign after the data that she collected were questioned insisted that the model which the interns had trained was still reliable, the director, who had already warned everyone that the deadline was unrealistic, made the exhausted team rewrite the report before anyone could discover how many assumptions had been left unexplained."

TOKENS = [
    "Although","the","researcher","whom","the","committee","had","expected","to","resign",
    "after","the","data","that","she","collected","were","questioned","insisted","that",
    "the","model","which","the","interns","had","trained","was","still","reliable",",",
    "the","director",",","who","had","already","warned","everyone","that","the","deadline",
    "was","unrealistic",",","made","the","exhausted","team","rewrite","the","report",
    "before","anyone","could","discover","how","many","assumptions","had","been","left",
    "unexplained","."
]
POS = [
    "SCONJ","DET","NOUN","PRON","DET","NOUN","AUX","VERB","PART","VERB",
    "SCONJ","DET","NOUN","PRON","PRON","VERB","AUX","VERB","VERB","SCONJ",
    "DET","NOUN","PRON","DET","NOUN","AUX","VERB","AUX","ADV","ADJ","PUNCT",
    "DET","NOUN","PUNCT","PRON","AUX","ADV","VERB","PRON","SCONJ","DET",
    "NOUN","AUX","ADJ","PUNCT","VERB","DET","ADJ","NOUN","VERB","DET","NOUN",
    "SCONJ","PRON","AUX","VERB","ADV","DET","NOUN","AUX","AUX","VERB","ADJ","PUNCT"
]
FOCUS = {
    2:"S", 3:"O", 5:"S", 7:"V", 9:"V",
    12:"S", 14:"S", 15:"V", 17:"V", 18:"V",
    21:"S", 24:"S", 26:"V", 29:"C",
    32:"S", 37:"V", 38:"O", 41:"S", 43:"C",
    45:"V", 48:"O", 49:"V", 51:"O",
    53:"S", 55:"V", 58:"S", 61:"V", 62:"C",
}
V1_BASELINE=11/28

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default=str(Path(__file__).resolve().parent/"artifacts/mini_clause_anchor_graph_v1_01.pt"))
    ap.add_argument("--out",default=str(Path(__file__).resolve().parent/"artifacts/challenge_probe_v1_01.json"))
    args=ap.parse_args()
    ck=torch.load(args.model,map_location="cpu",weights_only=False)
    model=ClauseAnchorGraph();model.load_state_dict(ck["model"]);model.eval()
    batch,mask,pids=make_batch(TOKENS,POS)
    result=decode(model,batch,mask,pids)[0]

    checks=[];correct=0
    for idx,gold in FOCUS.items():
        pred=result.roles[idx];ok=pred==gold;correct+=int(ok)
        checks.append({
            "index":idx,"token":TOKENS[idx],"gold":gold,"pred":pred,"ok":ok,
            "owner_index":result.owners[idx],"owner_token":TOKENS[result.owners[idx]],
        })
    clauses=[]
    for h in result.clause_heads:
        members=[TOKENS[i] for i,o in enumerate(result.owners) if o==h]
        clauses.append({"head_index":h,"head_token":TOKENS[h],"members":members})
    payload={
        "version":VERSION,"sentence":SENTENCE,"tokens":TOKENS,"pos":POS,
        "roles":result.roles,"owners":result.owners,"clause_heads":result.clause_heads,
        "clauses":clauses,"focus_correct":correct,"focus_total":len(FOCUS),
        "focus_accuracy":correct/len(FOCUS),"v1_baseline_accuracy":V1_BASELINE,
        "delta_vs_v1":correct/len(FOCUS)-V1_BASELINE,
        "checks":checks,"training_metrics":ck.get("metrics",{}),
    }
    assert all(result.roles[i] is None for i,p in enumerate(POS) if p=="PUNCT"),result.roles
    assert all(result.roles[i]=="V" for i,p in enumerate(POS) if p in {"VERB","AUX"}),result.roles
    assert payload["focus_accuracy"]>=V1_BASELINE, payload
    Path(args.out).parent.mkdir(parents=True,exist_ok=True)
    Path(args.out).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("CLAUSE_ANCHOR_V1_01_CHALLENGE="+json.dumps(payload,ensure_ascii=False))

if __name__=="__main__":main()
