#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, random, sys
from collections import Counter
from pathlib import Path
import torch
import torch.nn as nn

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'train')); sys.path.insert(0,str(ROOT/'scripts'))
import train_ud_role as base
from canonical_roles import canonicalize_ud, canonicalize_masc
from train_gold_finetune import load_gold, train_epoch, clone_state
from train_gold_replay import freeze_lower
import train_gold_ewt_masc_replay as masc_legacy


def make_example(toks, decisions, text, family):
    if any(d.role=='AMBIG' for d in decisions): return None
    roles=[d.role for d in decisions]
    weak=base.weak_base_roles(toks)
    feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]
    labels=[base.ROLE2I[r] for r in roles]
    return (feats,labels,text,family)


def load_ud_canonical(root, max_train=10000, max_val=2000):
    train=[]; val=[]; stats=Counter()
    for path in sorted(Path(root).rglob('*.conllu')):
        corpus=path.parent.name
        split='train' if '-train.' in path.name else ('dev' if '-dev.' in path.name else 'test')
        rows=[]
        for meta,toks in base.parse_conllu(path):
            if not (2<=len(toks)<=160): continue
            ex=make_example(toks,canonicalize_ud(toks),meta.get('text',''),corpus)
            if ex is None: stats['ambig_sentences_dropped']+=1; continue
            rows.append(ex)
        random.Random(79191+len(path.name)).shuffle(rows)
        if split=='train':
            rows=rows[:max_train]; train.extend(rows); stats['train']+=len(rows)
        elif split=='dev':
            rows=rows[:max_val]; val.extend(rows); stats['val']+=len(rows)
        else:
            # deterministic 85/15 only when no explicit train/dev split is available
            for ex in rows[:max_train]:
                h=int(hashlib.sha1(ex[2].encode('utf-8')).hexdigest()[:8],16)%100
                (train if h<85 else val).append(ex); stats['train' if h<85 else 'val']+=1
    return train,val,dict(stats)


def load_masc_canonical(root):
    train=[]; val=[]; stats=Counter()
    root=Path(root)
    for path in sorted(root.rglob('*.conll')):
        if '__MACOSX' in path.parts: continue
        text=masc_legacy.decode_bytes(path.read_bytes()); lines=[]
        for raw in text.splitlines()+['']:
            if raw.strip(): lines.append(raw.rstrip('\r'))
            elif lines:
                toks,reason=masc_legacy.parse_masc_sentence(lines); lines=[]
                if toks is None: stats[f'reject_{reason}']+=1; continue
                ex=make_example(toks,canonicalize_masc(toks),' '.join(t['text'] for t in toks),'masc')
                if ex is None: stats['ambig_sentences_dropped']+=1; continue
                h=int(hashlib.sha1((path.name+'\n'+ex[2]).encode('utf-8')).hexdigest()[:8],16)%100
                (train if h<85 else val).append(ex); stats['train' if h<85 else 'val']+=1
    return train,val,dict(stats)


def eval_all(model, sets, dev, batch):
    return {k:base.evaluate(model,v,dev,batch) for k,v in sets.items() if v}


def score(m):
    # gold protects old capabilities; canonical UD/EWT are the main target; MASC is consistency anchor
    return (1.00*m['gold']['neural_role_acc'] + 1.25*m['ewt']['neural_role_acc'] +
            1.00*m['ud']['neural_role_acc'] + 0.70*m['masc']['neural_role_acc'])


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base',default='artifacts/v1.7.5_gold_ewt_masc_role.pt')
    ap.add_argument('--ud',default='data/ud')
    ap.add_argument('--ewt',default='data/gold_external/ewt')
    ap.add_argument('--masc',default='data/gold_external/masc_conll/extracted/masc-conll/data')
    ap.add_argument('--gold-train',default='data/gold/gold_v2_train_18000.jsonl')
    ap.add_argument('--gold-val',default='data/gold/gold_v2_val_4000.jsonl')
    ap.add_argument('--out',default='artifacts/v1.8.0_r011_canonical_role.pt')
    ap.add_argument('--metrics',default='artifacts/v1.8.0_r011_canonical_metrics.json')
    ap.add_argument('--epochs',type=int,default=2); ap.add_argument('--batch',type=int,default=32)
    args=ap.parse_args()
    torch.set_num_threads(4); random.seed(79191); torch.manual_seed(79191); dev=torch.device('cpu')

    ud_tr,ud_va,ud_stats=load_ud_canonical(args.ud,6000,1200)
    ew_tr,ew_va,ew_stats=load_ud_canonical(args.ewt,16000,2000)
    ma_tr,ma_va,ma_stats=load_masc_canonical(args.masc)
    gold_tr=load_gold(args.gold_train); gold_va=load_gold(args.gold_val)

    ck=torch.load(args.base,map_location='cpu',weights_only=False)
    model=base.RoleNet().to(dev); model.load_state_dict(ck['model'],strict=True); freeze_lower(model)
    sets={'gold':gold_va,'ewt':ew_va,'ud':ud_va,'masc':ma_va}
    baseline=eval_all(model,sets,dev,args.batch); best_state=clone_state(model); best=baseline; best_epoch=0; best_score=score(baseline)

    # canonical data dominates; synthetic gold replay prevents collapse of old task conventions
    rng=random.Random(88110)
    rng.shuffle(gold_tr); gold_replay=gold_tr[:6000]
    mix=list(ud_tr)+list(ew_tr)+list(ma_tr)+gold_replay
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=3e-5,weight_decay=3e-4)
    weights=torch.tensor([0.35,0.75,0.9,1.05,1.6,0.8],device=dev)
    lossfn=nn.CrossEntropyLoss(weight=weights,reduction='none')
    history=[]

    for ep in range(1,args.epochs+1):
        random.Random(88110+ep).shuffle(mix)
        logs=train_epoch(model,mix,opt,lossfn,dev,args.batch,250,88110+ep)
        cur=eval_all(model,sets,dev,args.batch); sc=score(cur)
        safe=(cur['gold']['neural_role_acc']>=baseline['gold']['neural_role_acc']-0.003 and
              cur['masc']['neural_role_acc']>=baseline['masc']['neural_role_acc']-0.003 and
              cur['ewt']['neural_role_acc']>=baseline['ewt']['neural_role_acc']-0.003)
        history.append({'epoch':ep,'eval':cur,'score':sc,'safe':safe,'last_train':logs[-1]})
        if safe and sc>best_score:
            best_score=sc; best_state=clone_state(model); best=cur; best_epoch=ep

    model.load_state_dict(best_state)
    metrics={
      'version':'1.8.0-R011-CANONICAL-REPLAY','base':Path(args.base).name,'selected_epoch':best_epoch,
      'baseline':baseline,'selected':best,'history':history,
      'data_stats':{'ud':ud_stats,'ewt':ew_stats,'masc':ma_stats,'gold_replay':len(gold_replay)},
      'selection_used_chaos50':False,
      'note':'UD/EWT/MASC labels use canonical_roles.py; any sentence containing AMBIG is excluded from supervised training.'
    }
    out=Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({'model':model.state_dict(),'config':{'gru':3,'attn':1,'source':'v1.7.5 + canonical UD/EWT/MASC + gold replay','roles':base.I2ROLE},'metrics':metrics},out)
    Path(args.metrics).write_text(json.dumps(metrics,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(metrics,indent=2))

if __name__=='__main__': main()
