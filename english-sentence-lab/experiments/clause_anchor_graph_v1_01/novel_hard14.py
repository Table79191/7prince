from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
from infer import make_batch
from model import ClauseAnchorGraph, decode

CASES = [
  {
    "id":"H01_INVERSION",
    "sentence":"Only when the auditors compared the archived invoices did the accountant admit that several payments had been recorded twice.",
    "tokens":["Only","when","the","auditors","compared","the","archived","invoices","did","the","accountant","admit","that","several","payments","had","been","recorded","twice","."],
    "pos":["ADV","SCONJ","DET","NOUN","VERB","DET","ADJ","NOUN","AUX","DET","NOUN","VERB","SCONJ","DET","NOUN","AUX","AUX","VERB","ADV","PUNCT"],
    "focus":{"3":"S","7":"O","10":"S","11":"V","14":"S","17":"V"}
  },
  {
    "id":"H02_CLEFT",
    "sentence":"It was the technician who the supervisor believed had misconfigured the sensor that triggered the shutdown.",
    "tokens":["It","was","the","technician","who","the","supervisor","believed","had","misconfigured","the","sensor","that","triggered","the","shutdown","."],
    "pos":["PRON","AUX","DET","NOUN","PRON","DET","NOUN","VERB","AUX","VERB","DET","NOUN","PRON","VERB","DET","NOUN","PUNCT"],
    "focus":{"3":"C","4":"S","6":"S","11":"O","12":"S","15":"O"}
  },
  {
    "id":"H03_PSEUDOCLEFT",
    "sentence":"What the committee considered unacceptable was that the contractor had concealed the structural defect.",
    "tokens":["What","the","committee","considered","unacceptable","was","that","the","contractor","had","concealed","the","structural","defect","."],
    "pos":["PRON","DET","NOUN","VERB","ADJ","AUX","SCONJ","DET","NOUN","AUX","VERB","DET","ADJ","NOUN","PUNCT"],
    "focus":{"0":"O","2":"S","4":"C","8":"S","10":"V","13":"O"}
  },
  {
    "id":"H04_REDUCED_PASSIVE",
    "sentence":"The prototype expected to withstand extreme heat was found to have developed a microscopic fracture near the seal.",
    "tokens":["The","prototype","expected","to","withstand","extreme","heat","was","found","to","have","developed","a","microscopic","fracture","near","the","seal","."],
    "pos":["DET","NOUN","VERB","PART","VERB","ADJ","NOUN","AUX","VERB","PART","AUX","VERB","DET","ADJ","NOUN","ADP","DET","NOUN","PUNCT"],
    "focus":{"1":"S","4":"V","6":"O","8":"V","11":"V","14":"O"}
  },
  {
    "id":"H05_NOMINAL_SUBJECT",
    "sentence":"Whether the merger would reduce costs or merely shift them remained unclear to investors who had studied the proposal.",
    "tokens":["Whether","the","merger","would","reduce","costs","or","merely","shift","them","remained","unclear","to","investors","who","had","studied","the","proposal","."],
    "pos":["SCONJ","DET","NOUN","AUX","VERB","NOUN","CCONJ","ADV","VERB","PRON","VERB","ADJ","ADP","NOUN","PRON","AUX","VERB","DET","NOUN","PUNCT"],
    "focus":{"2":"S","5":"O","9":"O","11":"C","14":"S","18":"O"}
  },
  {
    "id":"H06_NEITHER_INVERSION",
    "sentence":"Neither had the reviewers noticed the missing appendix, nor did the editor realize that the citations contradicted the conclusion.",
    "tokens":["Neither","had","the","reviewers","noticed","the","missing","appendix",",","nor","did","the","editor","realize","that","the","citations","contradicted","the","conclusion","."],
    "pos":["CCONJ","AUX","DET","NOUN","VERB","DET","ADJ","NOUN","PUNCT","CCONJ","AUX","DET","NOUN","VERB","SCONJ","DET","NOUN","VERB","DET","NOUN","PUNCT"],
    "focus":{"3":"S","7":"O","12":"S","13":"V","16":"S","19":"O"}
  },
  {
    "id":"H07_CONDITIONAL_INVERSION",
    "sentence":"Had the pilot known that the alternate runway was closed, she would have diverted the aircraft before the storm reached the airport.",
    "tokens":["Had","the","pilot","known","that","the","alternate","runway","was","closed",",","she","would","have","diverted","the","aircraft","before","the","storm","reached","the","airport","."],
    "pos":["AUX","DET","NOUN","VERB","SCONJ","DET","ADJ","NOUN","AUX","ADJ","PUNCT","PRON","AUX","AUX","VERB","DET","NOUN","SCONJ","DET","NOUN","VERB","DET","NOUN","PUNCT"],
    "focus":{"2":"S","7":"S","9":"C","11":"S","16":"O","19":"S","22":"O"}
  },
  {
    "id":"H08_EXTRAPOSITION",
    "sentence":"It became obvious after the second simulation that the algorithm which the team had trusted was amplifying measurement noise.",
    "tokens":["It","became","obvious","after","the","second","simulation","that","the","algorithm","which","the","team","had","trusted","was","amplifying","measurement","noise","."],
    "pos":["PRON","VERB","ADJ","ADP","DET","ADJ","NOUN","SCONJ","DET","NOUN","PRON","DET","NOUN","AUX","VERB","AUX","VERB","NOUN","NOUN","PUNCT"],
    "focus":{"0":"S","2":"C","9":"S","12":"S","14":"V","18":"O"}
  },
  {
    "id":"H09_OBJECT_COMPLEMENT",
    "sentence":"The judge found the witness unusually evasive after the prosecutor showed her the photographs that contradicted her testimony.",
    "tokens":["The","judge","found","the","witness","unusually","evasive","after","the","prosecutor","showed","her","the","photographs","that","contradicted","her","testimony","."],
    "pos":["DET","NOUN","VERB","DET","NOUN","ADV","ADJ","SCONJ","DET","NOUN","VERB","PRON","DET","NOUN","PRON","VERB","PRON","NOUN","PUNCT"],
    "focus":{"1":"S","4":"O","6":"C","9":"S","11":"O","13":"O","14":"S","17":"O"}
  },
  {
    "id":"H10_OBJECT_CONTROL",
    "sentence":"The director persuaded the analyst whom the board had hired to revise the forecast before the clients arrived.",
    "tokens":["The","director","persuaded","the","analyst","whom","the","board","had","hired","to","revise","the","forecast","before","the","clients","arrived","."],
    "pos":["DET","NOUN","VERB","DET","NOUN","PRON","DET","NOUN","AUX","VERB","PART","VERB","DET","NOUN","SCONJ","DET","NOUN","VERB","PUNCT"],
    "focus":{"1":"S","4":"O","5":"O","7":"S","11":"V","13":"O","16":"S"}
  },
  {
    "id":"H11_NOT_ONLY",
    "sentence":"Not only did the experiment fail to confirm the hypothesis, but the follow-up analysis also revealed that the control samples had been contaminated.",
    "tokens":["Not","only","did","the","experiment","fail","to","confirm","the","hypothesis",",","but","the","follow-up","analysis","also","revealed","that","the","control","samples","had","been","contaminated","."],
    "pos":["ADV","ADV","AUX","DET","NOUN","VERB","PART","VERB","DET","NOUN","PUNCT","CCONJ","DET","ADJ","NOUN","ADV","VERB","SCONJ","DET","NOUN","NOUN","AUX","AUX","VERB","PUNCT"],
    "focus":{"4":"S","9":"O","14":"S","16":"V","20":"S","23":"V"}
  },
  {
    "id":"H12_FREE_RELATIVE",
    "sentence":"The investigators reconstructed what the witness claimed the driver had done before the camera stopped recording.",
    "tokens":["The","investigators","reconstructed","what","the","witness","claimed","the","driver","had","done","before","the","camera","stopped","recording","."],
    "pos":["DET","NOUN","VERB","PRON","DET","NOUN","VERB","DET","NOUN","AUX","VERB","SCONJ","DET","NOUN","VERB","VERB","PUNCT"],
    "focus":{"1":"S","3":"O","5":"S","8":"S","10":"V","13":"S","15":"V"}
  },
  {
    "id":"H13_COMPARATIVE_CORRELATIVE",
    "sentence":"The more carefully the engineers examined the logs, the less plausible the vendor's explanation became.",
    "tokens":["The","more","carefully","the","engineers","examined","the","logs",",","the","less","plausible","the","vendor's","explanation","became","."],
    "pos":["DET","ADV","ADV","DET","NOUN","VERB","DET","NOUN","PUNCT","DET","ADV","ADJ","DET","NOUN","NOUN","VERB","PUNCT"],
    "focus":{"4":"S","7":"O","11":"C","14":"S","15":"V"}
  },
  {
    "id":"H14_REDUCED_RELATIVES",
    "sentence":"Documents recovered from the damaged server revealed inconsistencies overlooked during the initial audit.",
    "tokens":["Documents","recovered","from","the","damaged","server","revealed","inconsistencies","overlooked","during","the","initial","audit","."],
    "pos":["NOUN","VERB","ADP","DET","ADJ","NOUN","VERB","NOUN","VERB","ADP","DET","ADJ","NOUN","PUNCT"],
    "focus":{"0":"S","1":"V","6":"V","7":"O","8":"V"}
  }
]

def evaluate(model):
    total=correct=exact=0
    rows=[]
    for c in CASES:
        batch,mask,pids=make_batch(c["tokens"],c["pos"])
        r=decode(model,batch,mask,pids)[0]
        checks=[]
        ok_all=True
        for raw_idx,gold in c["focus"].items():
            idx=int(raw_idx); pred=r.roles[idx]; ok=pred==gold
            total+=1;correct+=int(ok);ok_all &= ok
            checks.append({"index":idx,"token":c["tokens"][idx],"gold":gold,"pred":pred,"ok":ok})
        exact+=int(ok_all)
        rows.append({
          "id":c["id"],"sentence":c["sentence"],"focus_correct":sum(x["ok"] for x in checks),
          "focus_total":len(checks),"exact":ok_all,"checks":checks,
          "clause_heads":[{"index":h,"token":c["tokens"][h]} for h in r.clause_heads],
        })
    return {
      "set":"NOVEL_HARD14_V1",
      "sentences":len(CASES),"focus_checks":total,"focus_correct":correct,
      "focus_accuracy":correct/max(total,1),"exact_sentences":exact,
      "exact_rate":exact/max(len(CASES),1),"cases":rows,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    ck=torch.load(a.model,map_location="cpu",weights_only=False)
    m=ClauseAnchorGraph();m.load_state_dict(ck["model"]);m.eval()
    result=evaluate(m)
    result["model_version"]=ck.get("config",{}).get("version")
    result["training_metrics"]=ck.get("metrics",{})
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("NOVEL_HARD_RESULT="+json.dumps(result,ensure_ascii=False))

if __name__=="__main__":main()
