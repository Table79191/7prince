from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
from infer import make_batch
from model import ClauseAnchorGraph, decode

# FINAL_BLIND16_V1 is evaluation-only. None of these sentences are used by training/mining.
CASES=[
{"id":"F01_NO_SOONER",
"sentence":"No sooner had the inspectors entered the warehouse than the alarm revealed that someone had disabled the ventilation system.",
"tokens":["No","sooner","had","the","inspectors","entered","the","warehouse","than","the","alarm","revealed","that","someone","had","disabled","the","ventilation","system","."],
"pos":["ADV","ADV","AUX","DET","NOUN","VERB","DET","NOUN","SCONJ","DET","NOUN","VERB","SCONJ","PRON","AUX","VERB","DET","NOUN","NOUN","PUNCT"],
"focus":{"4":"S","7":"O","10":"S","11":"V","13":"S","18":"O"}},

{"id":"F02_RAISING",
"sentence":"The scientist seemed to have overlooked the warning that the calibration software had generated.",
"tokens":["The","scientist","seemed","to","have","overlooked","the","warning","that","the","calibration","software","had","generated","."],
"pos":["DET","NOUN","VERB","PART","AUX","VERB","DET","NOUN","PRON","DET","NOUN","NOUN","AUX","VERB","PUNCT"],
"focus":{"1":"S","2":"V","5":"V","7":"O","8":"O","11":"S","13":"V"}},

{"id":"F03_EXISTENTIAL",
"sentence":"There appeared to be several discrepancies that neither reviewer could explain without examining the raw measurements.",
"tokens":["There","appeared","to","be","several","discrepancies","that","neither","reviewer","could","explain","without","examining","the","raw","measurements","."],
"pos":["PRON","VERB","PART","AUX","DET","NOUN","PRON","DET","NOUN","AUX","VERB","ADP","VERB","DET","ADJ","NOUN","PUNCT"],
"focus":{"5":"S","6":"O","8":"S","10":"V","15":"O"}},

{"id":"F04_RAISING_PASSIVE",
"sentence":"The device was believed to have remained stable until an unexpected voltage spike damaged the controller.",
"tokens":["The","device","was","believed","to","have","remained","stable","until","an","unexpected","voltage","spike","damaged","the","controller","."],
"pos":["DET","NOUN","AUX","VERB","PART","AUX","VERB","ADJ","SCONJ","DET","ADJ","NOUN","NOUN","VERB","DET","NOUN","PUNCT"],
"focus":{"1":"S","3":"V","6":"V","7":"C","12":"S","15":"O"}},

{"id":"F05_RESULTATIVE",
"sentence":"The collision knocked the access panel open before the emergency crew could secure the compartment.",
"tokens":["The","collision","knocked","the","access","panel","open","before","the","emergency","crew","could","secure","the","compartment","."],
"pos":["DET","NOUN","VERB","DET","NOUN","NOUN","ADJ","SCONJ","DET","ADJ","NOUN","AUX","VERB","DET","NOUN","PUNCT"],
"focus":{"1":"S","5":"O","6":"C","10":"S","12":"V","14":"O"}},

{"id":"F06_SMALL_CLAUSE",
"sentence":"The board considered the revised estimate too optimistic to justify the additional investment.",
"tokens":["The","board","considered","the","revised","estimate","too","optimistic","to","justify","the","additional","investment","."],
"pos":["DET","NOUN","VERB","DET","ADJ","NOUN","ADV","ADJ","PART","VERB","DET","ADJ","NOUN","PUNCT"],
"focus":{"1":"S","5":"O","7":"C","9":"V","12":"O"}},

{"id":"F07_AS_COMPARATIVE",
"sentence":"The replacement system proved as reliable as the engineers had predicted after they corrected the firmware.",
"tokens":["The","replacement","system","proved","as","reliable","as","the","engineers","had","predicted","after","they","corrected","the","firmware","."],
"pos":["DET","NOUN","NOUN","VERB","ADV","ADJ","SCONJ","DET","NOUN","AUX","VERB","SCONJ","PRON","VERB","DET","NOUN","PUNCT"],
"focus":{"2":"S","5":"C","8":"S","10":"V","12":"S","15":"O"}},

{"id":"F08_WHOEVER",
"sentence":"Whoever the committee appoints will inherit a project that previous managers repeatedly failed to stabilize.",
"tokens":["Whoever","the","committee","appoints","will","inherit","a","project","that","previous","managers","repeatedly","failed","to","stabilize","."],
"pos":["PRON","DET","NOUN","VERB","AUX","VERB","DET","NOUN","PRON","ADJ","NOUN","ADV","VERB","PART","VERB","PUNCT"],
"focus":{"0":"O","2":"S","5":"V","7":"O","8":"O","10":"S","14":"V"}},

{"id":"F09_EMBEDDED_QUESTION",
"sentence":"The auditors could not determine why the subsidiary had reported revenue that its own records did not support.",
"tokens":["The","auditors","could","not","determine","why","the","subsidiary","had","reported","revenue","that","its","own","records","did","not","support","."],
"pos":["DET","NOUN","AUX","PART","VERB","ADV","DET","NOUN","AUX","VERB","NOUN","PRON","DET","ADJ","NOUN","AUX","PART","VERB","PUNCT"],
"focus":{"1":"S","4":"V","7":"S","10":"O","11":"O","14":"S","17":"V"}},

{"id":"F10_GERUND_SUBJECT",
"sentence":"Having the interns repeat the measurement seemed unnecessary once the control sample produced the expected value.",
"tokens":["Having","the","interns","repeat","the","measurement","seemed","unnecessary","once","the","control","sample","produced","the","expected","value","."],
"pos":["VERB","DET","NOUN","VERB","DET","NOUN","VERB","ADJ","SCONJ","DET","NOUN","NOUN","VERB","DET","ADJ","NOUN","PUNCT"],
"focus":{"2":"O","3":"V","5":"O","6":"V","7":"C","11":"S","15":"O"}},

{"id":"F11_APPOSITIVE_RELATIVE",
"sentence":"The claim that the sample was pure, which several analysts had already doubted, collapsed when contamination was detected.",
"tokens":["The","claim","that","the","sample","was","pure",",","which","several","analysts","had","already","doubted",",","collapsed","when","contamination","was","detected","."],
"pos":["DET","NOUN","SCONJ","DET","NOUN","AUX","ADJ","PUNCT","PRON","DET","NOUN","AUX","ADV","VERB","PUNCT","VERB","SCONJ","NOUN","AUX","VERB","PUNCT"],
"focus":{"1":"S","4":"S","6":"C","8":"O","10":"S","15":"V","17":"S","19":"V"}},

{"id":"F12_TOUGH_MOVEMENT",
"sentence":"The manuscript was difficult for the reviewers to interpret because several references had been omitted from the appendix.",
"tokens":["The","manuscript","was","difficult","for","the","reviewers","to","interpret","because","several","references","had","been","omitted","from","the","appendix","."],
"pos":["DET","NOUN","AUX","ADJ","ADP","DET","NOUN","PART","VERB","SCONJ","DET","NOUN","AUX","AUX","VERB","ADP","DET","NOUN","PUNCT"],
"focus":{"1":"S","3":"C","6":"S","8":"V","11":"S","14":"V"}},

{"id":"F13_CAUSATIVE_PASSIVE",
"sentence":"The trainees were made to rewrite the protocol after the supervisor found the original instructions dangerously vague.",
"tokens":["The","trainees","were","made","to","rewrite","the","protocol","after","the","supervisor","found","the","original","instructions","dangerously","vague","."],
"pos":["DET","NOUN","AUX","VERB","PART","VERB","DET","NOUN","SCONJ","DET","NOUN","VERB","DET","ADJ","NOUN","ADV","ADJ","PUNCT"],
"focus":{"1":"S","5":"V","7":"O","10":"S","14":"O","16":"C"}},

{"id":"F14_ABSOLUTE",
"sentence":"The weather having worsened unexpectedly, the pilot diverted the aircraft while the dispatcher notified the ground crew.",
"tokens":["The","weather","having","worsened","unexpectedly",",","the","pilot","diverted","the","aircraft","while","the","dispatcher","notified","the","ground","crew","."],
"pos":["DET","NOUN","AUX","VERB","ADV","PUNCT","DET","NOUN","VERB","DET","NOUN","SCONJ","DET","NOUN","VERB","DET","NOUN","NOUN","PUNCT"],
"focus":{"1":"S","3":"V","7":"S","10":"O","13":"S","17":"O"}},

{"id":"F15_COORDINATED_ARGUMENTS",
"sentence":"The first team tested the sensor and the second team tested the controller that the supplier had replaced.",
"tokens":["The","first","team","tested","the","sensor","and","the","second","team","tested","the","controller","that","the","supplier","had","replaced","."],
"pos":["DET","ADJ","NOUN","VERB","DET","NOUN","CCONJ","DET","ADJ","NOUN","VERB","DET","NOUN","PRON","DET","NOUN","AUX","VERB","PUNCT"],
"focus":{"2":"S","5":"O","9":"S","12":"O","13":"O","15":"S","17":"V"}},

{"id":"F16_DOUBLE_EMBEDDING",
"sentence":"What made the result surprising was how consistently the method that critics had dismissed outperformed the established baseline.",
"tokens":["What","made","the","result","surprising","was","how","consistently","the","method","that","critics","had","dismissed","outperformed","the","established","baseline","."],
"pos":["PRON","VERB","DET","NOUN","ADJ","AUX","ADV","ADV","DET","NOUN","PRON","NOUN","AUX","VERB","VERB","DET","ADJ","NOUN","PUNCT"],
"focus":{"0":"S","3":"O","4":"C","9":"S","10":"O","11":"S","14":"V","17":"O"}}
]

def evaluate(model):
    total=correct=exact=0; rows=[]
    for c in CASES:
        b,m,p=make_batch(c["tokens"],c["pos"]); r=decode(model,b,m,p)[0]
        checks=[]; all_ok=True
        for k,gold in c["focus"].items():
            i=int(k); pred=r.roles[i]; ok=pred==gold
            total+=1; correct+=int(ok); all_ok &= ok
            checks.append({"index":i,"token":c["tokens"][i],"gold":gold,"pred":pred,"ok":ok})
        exact+=int(all_ok)
        rows.append({"id":c["id"],"sentence":c["sentence"],"focus_correct":sum(x["ok"] for x in checks),
                     "focus_total":len(checks),"exact":all_ok,"checks":checks,
                     "clause_heads":[{"index":h,"token":c["tokens"][h]} for h in r.clause_heads]})
    return {"set":"FINAL_BLIND16_V1","sentences":len(CASES),"focus_checks":total,
            "focus_correct":correct,"focus_accuracy":correct/max(total,1),
            "exact_sentences":exact,"exact_rate":exact/max(len(CASES),1),"cases":rows}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--model",required=True); ap.add_argument("--out",required=True)
    a=ap.parse_args(); ck=torch.load(a.model,map_location="cpu",weights_only=False)
    m=ClauseAnchorGraph(); m.load_state_dict(ck["model"]); m.eval()
    out=evaluate(m); out["model_version"]=ck.get("config",{}).get("version")
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("FINAL_BLIND_RESULT="+json.dumps(out,ensure_ascii=False))

if __name__=="__main__": main()
