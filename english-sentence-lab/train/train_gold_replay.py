#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random
from pathlib import Path
import torch
import torch.nn as nn
import train_ud_role as base
from train_gold_finetune import load_gold, train_epoch, clone_state


def freeze_lower(model):
    for name,p in model.named_parameters():
        p.requires_grad=True
        if name.startswith(('word.','pre.','suf.','pos.','brole.','shape.','proj.')):
            p.requires_grad=False
        if name.startswith('gru.') and any(x in name for x in ('_l0','_l0_reverse','_l1','_l1_reverse')):
            p.requires_grad=False


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base',default='artifacts/v1.7.1_ud_full_role.pt'); ap.add_argument('--gold-train',default='data/gold/gold_v2_train_18000.jsonl'); ap.add_argument('--gold-val',default='data/gold/gold_v2_val_4000.jsonl'); ap.add_argument('--ud',default='data/ud'); ap.add_argument('--out',default='artifacts/v1.7.3_gold_replay_role.pt'); ap.add_argument('--metrics',default='artifacts/v1.7.3_gold_replay_metrics.json'); ap.add_argument('--epochs',type=int,default=2); ap.add_argument('--batch',type=int,default=32); ap.add_argument('--replay',type=int,default=8000); args=ap.parse_args()
    torch.set_num_threads(4); random.seed(79191); torch.manual_seed(79191); dev=torch.device('cpu')
    gold_train=load_gold(args.gold_train); gold_val=load_gold(args.gold_val); ud_train,ud_val,_=base.load_examples(args.ud,max_per_corpus=12000)
    rng=random.Random(79191); rng.shuffle(ud_train); replay=ud_train[:min(args.replay,len(ud_train))]
    ck=torch.load(args.base,map_location='cpu',weights_only=False); model=base.RoleNet().to(dev); model.load_state_dict(ck['model'],strict=True); freeze_lower(model)
    baseline_gold=base.evaluate(model,gold_val,dev,args.batch); baseline_ud=base.evaluate(model,ud_val,dev,args.batch)
    best_state=clone_state(model); best={'epoch':0,'gold':baseline_gold,'ud':baseline_ud}; best_score=baseline_gold['neural_role_acc']+0.6*baseline_ud['neural_role_acc']; history=[]
    params=[p for p in model.parameters() if p.requires_grad]; opt=torch.optim.AdamW(params,lr=8e-5,weight_decay=3e-4); weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=dev); lossfn=nn.CrossEntropyLoss(weight=weights,reduction='none')
    for ep in range(1,args.epochs+1):
        # Gold is the majority; replay anchors already-known supervised English.
        mix=list(gold_train)+list(replay); random.Random(79191+ep).shuffle(mix)
        logs=train_epoch(model,mix,opt,lossfn,dev,args.batch,250,89191+ep)
        g=base.evaluate(model,gold_val,dev,args.batch); u=base.evaluate(model,ud_val,dev,args.batch); score=g['neural_role_acc']+0.6*u['neural_role_acc']; rec={'epoch':ep,'gold':g,'ud':u,'score':score,'last_train':logs[-1]}; history.append(rec); print(rec)
        # Allow at most 0.75 percentage point UD regression.
        if score>best_score and u['neural_role_acc']>=baseline_ud['neural_role_acc']-0.0075:
            best_score=score; best_state=clone_state(model); best={'epoch':ep,'gold':g,'ud':u}
    model.load_state_dict(best_state)
    metrics={'version':'1.7.3-GOLD-REPLAY','params':sum(p.numel() for p in model.parameters()),'trainable_params':sum(p.numel() for p in model.parameters() if p.requires_grad),'gold_train_sentences':len(gold_train),'ud_replay_sentences':len(replay),'gold_val_sentences':len(gold_val),'baseline':{'gold':baseline_gold,'ud':baseline_ud},'history':history,'selected':best,'sealed_holdouts_included':False,'external_downloads_for_this_run':False}
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); torch.save({'model':model.state_dict(),'config':{'gru':3,'attn':1,'source':'v1.7.1 + gold-v2 + supervised-UD-replay','roles':base.I2ROLE},'metrics':metrics},out); Path(args.metrics).write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8'); print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
