from __future__ import annotations
import argparse,json,random,time
from collections import Counter
from pathlib import Path
import torch
import torch.nn as nn

from model import ClauseAnchorGraph,VERSION
from data import load_corpus,balanced_train,collate

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def evaluate(model,data,device,batch_size=24):
    model.eval()
    tok=oracle_cor=e2e_cor=oracle_exact=e2e_exact=0
    head_tp=head_fp=head_fn=0
    owner_ok=owner_n=0
    with torch.no_grad():
        for st in range(0,len(data),batch_size):
            items=data[st:st+batch_size]
            b,y,owner,heads,mask,w=collate(items,device)
            o=model(b,mask,gold_owner=owner)
            oracle_pred=o["role_logits"].argmax(-1)
            pred_owner=o["owner_logits"].argmax(-1)
            e2e_pred=model.role_logits(o["hidden"],pred_owner).argmax(-1)

            tok+=int(mask.sum())
            oracle_cor+=int(((oracle_pred==y)&mask).sum())
            e2e_cor+=int(((e2e_pred==y)&mask).sum())

            hp=(torch.sigmoid(o["head_logits"])>=.45)&mask
            hg=(heads>.5)&mask
            head_tp+=int((hp&hg).sum())
            head_fp+=int((hp&~hg&mask).sum())
            head_fn+=int((~hp&hg&mask).sum())

            owner_ok+=int(((pred_owner==owner)&mask).sum())
            owner_n+=int(mask.sum())

            for i,x in enumerate(items):
                n=len(x["roles"])
                oracle_exact+=int(torch.equal(oracle_pred[i,:n],y[i,:n]))
                e2e_exact+=int(torch.equal(e2e_pred[i,:n],y[i,:n]))

    p=head_tp/max(head_tp+head_fp,1);r=head_tp/max(head_tp+head_fn,1)
    return {
      "sentences":len(data),"tokens":tok,
      "oracle_owner_role_accuracy":oracle_cor/max(tok,1),
      "oracle_owner_sentence_exact":oracle_exact,
      "oracle_owner_sentence_exact_rate":oracle_exact/max(len(data),1),
      "predicted_owner_role_accuracy":e2e_cor/max(tok,1),
      "predicted_owner_sentence_exact":e2e_exact,
      "predicted_owner_sentence_exact_rate":e2e_exact/max(len(data),1),
      "clause_head_precision":p,"clause_head_recall":r,
      "clause_head_f1":2*p*r/max(p+r,1e-9),
      "owner_accuracy":owner_ok/max(owner_n,1),
    }

def role_weights(data,device):
    c=Counter()
    for x in data:
        c.update(x["roles"])
    counts=torch.tensor([max(c.get(i,0),1) for i in range(6)],dtype=torch.float32)
    freq=counts/counts.sum()
    w=torch.sqrt(freq.mean()/freq)
    w=torch.clamp(w,.50,2.50)
    w=w/w.mean()
    return w.to(device),counts.tolist()

def train_epoch(model,data,opt,device,batch_size,seed,class_weights):
    rows=list(data);random.Random(seed).shuffle(rows)
    role_loss=nn.CrossEntropyLoss(weight=class_weights,reduction="none")
    head_loss=nn.BCEWithLogitsLoss(reduction="none")
    total=0.;weight_sum=0.
    model.train()
    for st in range(0,len(rows),batch_size):
        items=rows[st:st+batch_size]
        b,y,owner,heads,mask,sw=collate(items,device)
        opt.zero_grad(set_to_none=True)
        o=model(b,mask,gold_owner=owner)
        rl=role_loss(o["role_logits"].reshape(-1,6),y.reshape(-1)).reshape_as(y)
        hl=head_loss(o["head_logits"],heads)
        ol=nn.functional.cross_entropy(o["owner_logits"].transpose(1,2),owner,reduction="none")
        wm=mask.float()*sw.unsqueeze(1)
        denom=wm.sum().clamp_min(1.)
        loss=(rl*wm).sum()/denom + .35*(hl*wm).sum()/denom + .45*(ol*wm).sum()/denom
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(),1.0)
        opt.step()
        total+=float(loss)*float(denom);weight_sum+=float(denom)
    return total/max(weight_sum,1.)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",default=str(ROOT/"data/web_corpus_bot"))
    ap.add_argument("--epochs",type=int,default=5)
    ap.add_argument("--batch",type=int,default=24)
    ap.add_argument("--max-per-source",type=int,default=12000)
    ap.add_argument("--lr",type=float,default=4e-4)
    ap.add_argument("--out",default=str(HERE/"artifacts/clause_anchor_graph_v1_01.pt"))
    ap.add_argument("--metrics",default=str(HERE/"artifacts/metrics_v1_01.json"))
    ap.add_argument("--seed",type=int,default=79191)
    args=ap.parse_args()

    torch.set_num_threads(4);random.seed(args.seed);torch.manual_seed(args.seed)
    device=torch.device("cpu")
    train,dev,stats=load_corpus(args.data)
    train=balanced_train(train,args.seed,args.max_per_source)
    cw,role_counts=role_weights(train,device)
    print(json.dumps({"train":len(train),"dev":len(dev),"stats":dict(stats),"role_counts":role_counts,"role_weights":cw.tolist()},indent=2))

    model=ClauseAnchorGraph().to(device)
    opt=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=2e-4)
    baseline=evaluate(model,dev,device,args.batch)

    best=None;best_score=-1.;hist=[]
    for ep in range(1,args.epochs+1):
        t=time.time()
        loss=train_epoch(model,train,opt,device,args.batch,args.seed+ep,cw)
        m=evaluate(model,dev,device,args.batch)
        score=m["predicted_owner_role_accuracy"]+.08*m["predicted_owner_sentence_exact_rate"]+.05*m["clause_head_f1"]+.07*m["owner_accuracy"]
        rec={"epoch":ep,"loss":loss,"seconds":time.time()-t,"dev":m,"score":score}
        hist.append(rec);print(json.dumps(rec))
        if score>best_score:
            best_score=score
            best={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}

    model.load_state_dict(best)
    final=evaluate(model,dev,device,args.batch)
    metrics={
      "version":VERSION,
      "algorithm":"dilated-conv + clause-head detection + distance-aware biaffine token-to-clause graph + class-balanced clause-conditioned role decoder",
      "params":sum(p.numel() for p in model.parameters()),
      "train_sentences":len(train),"dev_sentences":len(dev),
      "role_counts":role_counts,"role_weights":cw.tolist(),
      "baseline_random":baseline,"selected":final,"history":hist,
      "metric_note":"oracle_owner_* uses gold clause owners; predicted_owner_* uses the model's own owner graph and is the honest neural end-to-end role metric before decode-time structural repairs.",
      "data_policy":{"train_only_upstream_train":True,"dev_only_upstream_dev":True,"official_test_excluded":True},
    }
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({"model":model.state_dict(),"config":{"roles":[None,"S","V","O","C","M"],"version":VERSION},"metrics":metrics},out)
    Path(args.metrics).write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(metrics,indent=2))

if __name__=="__main__":
    main()
