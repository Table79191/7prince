from __future__ import annotations
import argparse,json,random,time
from pathlib import Path
import torch

from model import ClauseAnchorGraph,VERSION
from data import load_corpus,balanced_train
from train import evaluate,role_weights,train_epoch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--init-model",required=True)
    ap.add_argument("--data",default=str(ROOT/"data/web_corpus_bot"))
    ap.add_argument("--epochs",type=int,default=2)
    ap.add_argument("--batch",type=int,default=16)
    ap.add_argument("--max-per-source",type=int,default=1200)
    ap.add_argument("--lr",type=float,default=1e-4)
    ap.add_argument("--out",required=True)
    ap.add_argument("--metrics",required=True)
    ap.add_argument("--seed",type=int,default=79191)
    a=ap.parse_args()

    torch.set_num_threads(4); random.seed(a.seed); torch.manual_seed(a.seed)
    device=torch.device("cpu")
    ck=torch.load(a.init_model,map_location="cpu",weights_only=False)
    model=ClauseAnchorGraph().to(device); model.load_state_dict(ck["model"])

    train,dev,stats=load_corpus(a.data)
    train=balanced_train(train,a.seed+101,a.max_per_source)
    cw,counts=role_weights(train,device)

    before=evaluate(model,dev,device,a.batch)
    best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    best_score=before["predicted_owner_role_accuracy"]+.08*before["predicted_owner_sentence_exact_rate"]+.05*before["clause_head_f1"]+.07*before["owner_accuracy"]
    hist=[]

    opt=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=2e-4)
    for ep in range(1,a.epochs+1):
        t=time.time()
        loss=train_epoch(model,train,opt,device,a.batch,a.seed+1000+ep,cw)
        m=evaluate(model,dev,device,a.batch)
        score=m["predicted_owner_role_accuracy"]+.08*m["predicted_owner_sentence_exact_rate"]+.05*m["clause_head_f1"]+.07*m["owner_accuracy"]
        rec={"epoch":ep,"loss":loss,"seconds":time.time()-t,"dev":m,"score":score}
        hist.append(rec); print(json.dumps(rec))
        # Allow only tiny clean-dev tolerance while searching for broader generalization.
        if score>=best_score-0.002:
            best_score=max(best_score,score)
            best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}

    model.load_state_dict(best)
    after=evaluate(model,dev,device,a.batch)
    metrics={
      "version":"CLAUSE-ANCHOR-GRAPH-V1.01-FT1",
      "parent_version":ck.get("config",{}).get("version",VERSION),
      "fine_tune_train_sentences":len(train),"dev_sentences":len(dev),
      "fine_tune_epochs":a.epochs,"fine_tune_lr":a.lr,
      "before":before,"after":after,"history":hist,
      "role_counts":counts,"role_weights":cw.tolist(),
      "data_policy":{"novel_hard_holdout_used_for_training":False,"official_test_excluded":True},
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    torch.save({"model":model.state_dict(),"config":{"roles":[None,"S","V","O","C","M"],"version":"CLAUSE-ANCHOR-GRAPH-V1.01-FT1"},"metrics":metrics},a.out)
    Path(a.metrics).write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metrics,indent=2))

if __name__=="__main__":main()
