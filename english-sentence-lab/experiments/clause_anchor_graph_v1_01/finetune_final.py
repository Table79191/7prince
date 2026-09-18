from __future__ import annotations
import argparse,json,random,time
from pathlib import Path
import torch
import torch.nn as nn

from model import ClauseAnchorGraph,ROLE2I
from data import load_corpus,balanced_train,collate
from train import evaluate,role_weights

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

@torch.no_grad()
def mine_hard(model,rows,device,batch_size=24,hard_n=3600,replay_n=1400,seed=79191):
    model.eval(); scored=[]
    for st in range(0,len(rows),batch_size):
        items=rows[st:st+batch_size]
        b,y,owner,heads,mask,sw=collate(items,device)
        o=model(b,mask)
        pred_owner=o["owner_logits"].argmax(-1)
        pred=model.role_logits(o["hidden"],pred_owner).argmax(-1)
        hp=(torch.sigmoid(o["head_logits"])>=.45)
        for j,x in enumerate(items):
            n=len(x["roles"])
            yy=y[j,:n]; pp=pred[j,:n]; oo=owner[j,:n]; po=pred_owner[j,:n]
            role_err=(pp!=yy)
            core=((yy==ROLE2I["S"])|(yy==ROLE2I["O"])|(yy==ROLE2I["C"]))
            comp=(yy==ROLE2I["C"])
            score=float(role_err.sum()) + 1.8*float((role_err&core).sum()) + 1.2*float((role_err&comp).sum())
            score += .45*float((po!=oo).sum())
            gold_h=heads[j,:n]>.5
            score += .25*float((hp[j,:n]!=gold_h).sum())
            score /= max(n,1)**0.5
            scored.append((score,x))
    scored.sort(key=lambda z:z[0],reverse=True)
    hard=[x for _,x in scored[:hard_n]]
    hard_ids={id(x) for x in hard}
    pool=[x for _,x in scored if id(x) not in hard_ids]
    random.Random(seed+404).shuffle(pool)
    replay=pool[:replay_n]
    selected=hard+replay
    random.Random(seed+405).shuffle(selected)
    return selected,{
      "candidate_sentences":len(rows),"hard_selected":len(hard),"replay_selected":len(replay),
      "top_score":scored[0][0] if scored else 0.0,
      "median_selected_score":scored[min(len(scored)-1,max(0,hard_n//2))][0] if scored else 0.0,
    }

def tuned_role_weights(data,device):
    w,counts=role_weights(data,device)
    w=w.clone()
    w[ROLE2I["C"]]*=1.22
    w[ROLE2I["S"]]*=1.07
    w[ROLE2I["O"]]*=1.07
    w=w/w.mean()
    return w,counts

def train_one(model,rows,opt,device,batch_size,seed,class_weights):
    data=list(rows); random.Random(seed).shuffle(data)
    role_loss=nn.CrossEntropyLoss(weight=class_weights,reduction="none")
    head_loss=nn.BCEWithLogitsLoss(reduction="none")
    total=den_total=0.0
    model.train()
    for st in range(0,len(data),batch_size):
        items=data[st:st+batch_size]
        b,y,owner,heads,mask,sw=collate(items,device)
        opt.zero_grad(set_to_none=True)
        o=model(b,mask,gold_owner=owner)
        rl=role_loss(o["role_logits"].reshape(-1,6),y.reshape(-1)).reshape_as(y)
        hl=head_loss(o["head_logits"],heads)
        ol=nn.functional.cross_entropy(o["owner_logits"].transpose(1,2),owner,reduction="none")
        wm=mask.float()*sw.unsqueeze(1); den=wm.sum().clamp_min(1.)
        loss=(rl*wm).sum()/den + .35*(hl*wm).sum()/den + .48*(ol*wm).sum()/den
        loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),.80); opt.step()
        total+=float(loss)*float(den); den_total+=float(den)
    return total/max(den_total,1.0)

def score(m):
    return m["predicted_owner_role_accuracy"]+.10*m["predicted_owner_sentence_exact_rate"]+.05*m["clause_head_f1"]+.08*m["owner_accuracy"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--init-model",required=True)
    ap.add_argument("--data",default=str(ROOT/"data/web_corpus_bot"))
    ap.add_argument("--candidate-per-source",type=int,default=4000)
    ap.add_argument("--hard-n",type=int,default=3600)
    ap.add_argument("--replay-n",type=int,default=1400)
    ap.add_argument("--epochs",type=int,default=2)
    ap.add_argument("--batch",type=int,default=20)
    ap.add_argument("--lr",type=float,default=5e-5)
    ap.add_argument("--out",required=True); ap.add_argument("--metrics",required=True)
    ap.add_argument("--seed",type=int,default=79191)
    a=ap.parse_args()

    torch.set_num_threads(4); random.seed(a.seed); torch.manual_seed(a.seed)
    device=torch.device("cpu")
    ck=torch.load(a.init_model,map_location="cpu",weights_only=False)
    model=ClauseAnchorGraph().to(device); model.load_state_dict(ck["model"])

    train,dev,stats=load_corpus(a.data)
    candidates=balanced_train(train,a.seed+707,a.candidate_per_source)
    selected,mining=mine_hard(model,candidates,device,a.batch,a.hard_n,a.replay_n,a.seed)
    cw,counts=tuned_role_weights(selected,device)

    before=evaluate(model,dev,device,a.batch)
    parent_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
    best_state=parent_state; best_metric=before; best_score=score(before); selected_epoch=0; hist=[]
    opt=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=2e-4)

    for ep in range(1,a.epochs+1):
        t=time.time(); loss=train_one(model,selected,opt,device,a.batch,a.seed+7000+ep,cw)
        m=evaluate(model,dev,device,a.batch); s=score(m)
        hist.append({"epoch":ep,"loss":loss,"seconds":time.time()-t,"dev":m,"score":s})
        print(json.dumps(hist[-1]))
        # Final tune is conservative: the candidate must improve the clean-dev composite.
        if s>best_score:
            best_score=s; best_metric=m; selected_epoch=ep
            best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}

    model.load_state_dict(best_state)
    after=evaluate(model,dev,device,a.batch)
    metrics={
      "version":"CLAUSE-ANCHOR-GRAPH-V1.01-FINAL",
      "parent_version":ck.get("config",{}).get("version"),
      "strategy":"clean-train disagreement/hard-example mining + replay + conservative low-LR fine-tune",
      "mining":mining,"selected_train_sentences":len(selected),"selected_epoch":selected_epoch,
      "epochs_attempted":a.epochs,"lr":a.lr,"role_counts":counts,"role_weights":cw.tolist(),
      "before":before,"after":after,"history":hist,
      "data_policy":{"final_blind16_used_for_training":False,"novel_hard14_used_for_training":False,
                     "original_hard64_used_for_training":False,"official_test_excluded":True},
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    torch.save({"model":model.state_dict(),"config":{"roles":[None,"S","V","O","C","M"],
                "version":"CLAUSE-ANCHOR-GRAPH-V1.01-FINAL"},"metrics":metrics},a.out)
    Path(a.metrics).write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metrics,indent=2))

if __name__=="__main__": main()
