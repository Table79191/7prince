#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random
from pathlib import Path
import torch
import torch.nn as nn
import train_ud_role as base
from train_gold_finetune import load_gold, train_epoch, clone_state
from train_gold_replay import freeze_lower


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base',default='artifacts/v1.7.3_gold_replay_role.pt')
    ap.add_argument('--gold-train',default='data/gold/gold_v2_train_18000.jsonl')
    ap.add_argument('--gold-val',default='data/gold/gold_v2_val_4000.jsonl')
    ap.add_argument('--ewt',default='data/gold_external/ewt')
    ap.add_argument('--ud',default='data/ud')
    ap.add_argument('--out',default='artifacts/v1.7.4_gold_ewt_role.pt')
    ap.add_argument('--metrics',default='artifacts/v1.7.4_gold_ewt_metrics.json')
    ap.add_argument('--epochs',type=int,default=2)
    ap.add_argument('--batch',type=int,default=32)
    ap.add_argument('--replay',type=int,default=8000)
    args=ap.parse_args()

    torch.set_num_threads(4); random.seed(79191); torch.manual_seed(79191); dev=torch.device('cpu')
    gold_train=load_gold(args.gold_train); gold_val=load_gold(args.gold_val)
    ewt_train,ewt_val,ewt_dist=base.load_examples(args.ewt,max_per_corpus=20000)
    ud_train,ud_val,_=base.load_examples(args.ud,max_per_corpus=12000)
    rng=random.Random(79191); rng.shuffle(ud_train); replay=ud_train[:min(args.replay,len(ud_train))]

    ck=torch.load(args.base,map_location='cpu',weights_only=False)
    model=base.RoleNet().to(dev); model.load_state_dict(ck['model'],strict=True); freeze_lower(model)

    bg=base.evaluate(model,gold_val,dev,args.batch)
    be=base.evaluate(model,ewt_val,dev,args.batch)
    bu=base.evaluate(model,ud_val,dev,args.batch)
    best_state=clone_state(model)
    best={'epoch':0,'gold':bg,'ewt':be,'ud':bu}
    best_score=bg['neural_role_acc']+0.85*be['neural_role_acc']+0.55*bu['neural_role_acc']
    history=[]

    params=[p for p in model.parameters() if p.requires_grad]
    opt=torch.optim.AdamW(params,lr=5e-5,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=dev)
    lossfn=nn.CrossEntropyLoss(weight=weights,reduction='none')

    for ep in range(1,args.epochs+1):
        mix=list(gold_train)+list(ewt_train)+list(replay)
        random.Random(99200+ep).shuffle(mix)
        logs=train_epoch(model,mix,opt,lossfn,dev,args.batch,250,99200+ep)
        g=base.evaluate(model,gold_val,dev,args.batch)
        e=base.evaluate(model,ewt_val,dev,args.batch)
        u=base.evaluate(model,ud_val,dev,args.batch)
        score=g['neural_role_acc']+0.85*e['neural_role_acc']+0.55*u['neural_role_acc']
        rec={'epoch':ep,'gold':g,'ewt':e,'ud':u,'score':score,'last_train':logs[-1]}
        history.append(rec); print(rec)
        # Gold curriculum should remain essentially solved; EWT and broad UD may not regress materially.
        safe=(g['neural_role_acc']>=0.995 and
              e['neural_role_acc']>=be['neural_role_acc']-0.005 and
              u['neural_role_acc']>=bu['neural_role_acc']-0.0075)
        if safe and score>best_score:
            best_score=score; best_state=clone_state(model); best={'epoch':ep,'gold':g,'ewt':e,'ud':u}

    model.load_state_dict(best_state)
    metrics={
        'version':'1.7.4-GOLD-EWT-REPLAY',
        'params':sum(p.numel() for p in model.parameters()),
        'trainable_params':sum(p.numel() for p in model.parameters() if p.requires_grad),
        'synthetic_gold_train_sentences':len(gold_train),
        'ewt_gold_train_sentences':len(ewt_train),
        'ud_replay_sentences':len(replay),
        'gold_val_sentences':len(gold_val),
        'ewt_eval_sentences':len(ewt_val),
        'baseline':{'gold':bg,'ewt':be,'ud':bu},
        'history':history,
        'selected':best,
        'ewt_distribution':{f'{a}:{b}':n for (a,b),n in ewt_dist.items()},
        'sealed_project_holdouts_included':False,
        'source_note':'UD English EWT train only used for fitting; official dev/test kept evaluation-only',
    }
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({'model':model.state_dict(),'config':{'gru':3,'attn':1,'source':'v1.7.3 + synthetic-gold + EWT-gold + UD-replay','roles':base.I2ROLE},'metrics':metrics},out)
    Path(args.metrics).write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
