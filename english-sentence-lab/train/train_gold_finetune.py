#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random
from pathlib import Path
import torch
import torch.nn as nn
import train_ud_role as base


def load_gold(path):
    out=[]
    with open(path,encoding='utf-8') as f:
        for line in f:
            r=json.loads(line); toks=r['tokens']; weak=base.weak_base_roles(toks)
            feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]
            labels=[base.ROLE2I.get(t.get('role'),0) for t in toks]
            out.append((feats,labels,r['text'],r.get('family','gold')))
    return out


def train_epoch(model,data,opt,lossfn,device,batch=32,chunk=250,seed=79191):
    rng=random.Random(seed); rng.shuffle(data); model.train(); logs=[]; seen=0
    for cs in range(0,len(data),chunk):
        items=data[cs:cs+chunk]; tok=cor=0; lsum=0.0
        for st in range(0,len(items),batch):
            b,y,m=base.collate(items[st:st+batch],device); opt.zero_grad(set_to_none=True); z=model(b,m)
            raw=lossfn(z.view(-1,6),y.view(-1)).view_as(y); loss=(raw*m).sum()/m.sum(); loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
            with torch.no_grad():
                p=z.argmax(-1); n=m.sum().item(); tok+=n; cor+=((p==y)&m).sum().item(); lsum+=loss.item()*n
        seen+=len(items); rec={'sentences_seen':seen,'loss':lsum/tok,'train_acc':cor/tok}; logs.append(rec); print(rec)
    return logs


def clone_state(model): return {k:v.detach().cpu().clone() for k,v in model.state_dict().items()}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base',default='artifacts/v1.7.1_ud_full_role.pt'); ap.add_argument('--train',default='data/gold/gold_v2_train_18000.jsonl'); ap.add_argument('--val',default='data/gold/gold_v2_val_4000.jsonl'); ap.add_argument('--ud',default='data/ud'); ap.add_argument('--out',default='artifacts/v1.7.2_gold_role.pt'); ap.add_argument('--metrics',default='artifacts/v1.7.2_gold_metrics.json'); ap.add_argument('--epochs',type=int,default=2); ap.add_argument('--batch',type=int,default=32); args=ap.parse_args()
    torch.set_num_threads(4); random.seed(79191); torch.manual_seed(79191); device=torch.device('cpu')
    train=load_gold(args.train); val=load_gold(args.val); _,ud_val,_=base.load_examples(args.ud,max_per_corpus=4000)
    ck=torch.load(args.base,map_location='cpu',weights_only=False); model=base.RoleNet().to(device); model.load_state_dict(ck['model'],strict=True)
    baseline_gold=base.evaluate(model,val,device,args.batch); baseline_ud=base.evaluate(model,ud_val,device,args.batch)
    print('baseline_gold',baseline_gold); print('baseline_ud',baseline_ud)
    best_state=clone_state(model); best={'epoch':0,'gold':baseline_gold,'ud':baseline_ud}; best_score=baseline_gold['neural_role_acc']+0.35*baseline_ud['neural_role_acc']
    opt=torch.optim.AdamW(model.parameters(),lr=2.5e-4,weight_decay=2e-4); weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=device); lossfn=nn.CrossEntropyLoss(weight=weights,reduction='none'); all_logs=[]
    for ep in range(1,args.epochs+1):
        all_logs.extend(train_epoch(model,train,opt,lossfn,device,args.batch,250,79191+ep))
        g=base.evaluate(model,val,device,args.batch); u=base.evaluate(model,ud_val,device,args.batch); score=g['neural_role_acc']+0.35*u['neural_role_acc']; print('epoch',ep,'gold',g,'ud',u,'score',score)
        if score>best_score and u['neural_role_acc']>=baseline_ud['neural_role_acc']-0.02:
            best_score=score; best_state=clone_state(model); best={'epoch':ep,'gold':g,'ud':u}
    model.load_state_dict(best_state)
    metrics={'version':'1.7.2-GOLD-FINETUNE','params':sum(p.numel() for p in model.parameters()),'gold_train_sentences':len(train),'gold_val_sentences':len(val),'base_checkpoint':args.base,'baseline':{'gold':baseline_gold,'ud':baseline_ud},'selected':best,'sealed_holdouts_included':False,'last_chunks':all_logs[-12:]}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); torch.save({'model':model.state_dict(),'config':{'gru':3,'attn':1,'source':'v1.7.1 + supervised-gold-v2','roles':base.I2ROLE},'metrics':metrics},out)
    Path(args.metrics).write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8'); print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
