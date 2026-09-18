#!/usr/bin/env python3
"""Legacy v1.7.1-compatible wrapper with safe split handling.

Official train is fit data, official dev is validation data, and every test
file (including test-only treebanks) is excluded from fitting and selection.
Historical v1.7.x artifacts are preserved, but rerunning this script must not
reproduce the old test-only 85/15 leakage behavior.
"""
from __future__ import annotations
import hashlib, json, random, sys
from collections import Counter
from pathlib import Path
import torch
import train_ud_role as base


def load_examples(data_root, max_per_corpus=40000, max_len=160):
    train=[]; val=[]; per=Counter()
    for path in sorted(Path(data_root).rglob('*.conllu')):
        corpus=path.parent.name
        split='train' if '-train.' in path.name else ('dev' if '-dev.' in path.name else 'test')
        has_train=any(path.parent.glob('*-ud-train.conllu'))
        candidates=[]
        for meta,toks in base.parse_conllu(path):
            if not (2<=len(toks)<=max_len): continue
            gold=base.phrase_roles(toks); weak=base.weak_base_roles(toks)
            feats=[base.feat_token(t,b) for t,b in zip(toks,weak)]
            labels=[base.ROLE2I[r] for r in gold]
            candidates.append((feats,labels,meta.get('text',''),corpus))
        random.Random(79191+len(corpus)).shuffle(candidates)
        if split=='train':
            selected=candidates[:max_per_corpus]
            train.extend(selected); per[(corpus,'train')]+=len(selected)
        elif split=='dev':
            selected=candidates[:max(500,min(len(candidates),4000))]
            val.extend(selected); per[(corpus,'val')]+=len(selected)
        else:
            per[(corpus,'test_excluded')]+=len(candidates)
    return train,val,per

base.load_examples=load_examples
base.main()

# Normalize the version label after the shared trainer writes its outputs.
def arg_after(flag, default):
    try: return sys.argv[sys.argv.index(flag)+1]
    except (ValueError,IndexError): return default

metrics_path=Path(arg_after('--metrics','artifacts/v1.7.1_ud_full_metrics.json'))
out_path=Path(arg_after('--out','artifacts/v1.7.1_ud_full_role.pt'))
if metrics_path.exists():
    m=json.loads(metrics_path.read_text(encoding='utf-8'))
    m['version']='1.7.1-UD-FULL-SAFE-REBUILD'
    metrics_path.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
if out_path.exists():
    ck=torch.load(out_path,map_location='cpu',weights_only=False)
    if isinstance(ck,dict):
        ck.setdefault('config',{})['source']='UD-safe-rebuild'
        if isinstance(ck.get('metrics'),dict): ck['metrics']['version']='1.7.1-UD-FULL-SAFE-REBUILD'
        torch.save(ck,out_path)
