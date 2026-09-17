#!/usr/bin/env python3
"""Full-corpus v1.7.1 wrapper.

Fixes test-only treebanks being treated as validation-only and allows the full
CHILDES training split to be used while preserving the v1.7.0 architecture.
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
        elif has_train:
            # Official dev/test remain validation for treebanks with a train split.
            selected=candidates[:max(500,min(len(candidates),4000))]
            val.extend(selected); per[(corpus,'val')]+=len(selected)
        else:
            # Test-only treebanks: deterministic 85/15 train/validation split.
            for ex in candidates[:max_per_corpus]:
                key=ex[2].encode('utf-8')
                bucket=int(hashlib.sha1(key).hexdigest()[:8],16)%100
                target=train if bucket<85 else val
                target.append(ex)
                per[(corpus,'train' if bucket<85 else 'val')]+=1
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
    m['version']='1.7.1-UD-FULL'
    metrics_path.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
if out_path.exists():
    ck=torch.load(out_path,map_location='cpu',weights_only=False)
    if isinstance(ck,dict):
        ck.setdefault('config',{})['source']='UD-full-bootstrap'
        if isinstance(ck.get('metrics'),dict): ck['metrics']['version']='1.7.1-UD-FULL'
        torch.save(ck,out_path)
