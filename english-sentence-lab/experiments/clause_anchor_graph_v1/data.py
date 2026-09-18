from __future__ import annotations
import json, random, re, sys
from collections import Counter,defaultdict
from pathlib import Path
import torch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from canonical_roles import canonicalize_ud
from model import ROLE2I,POS2I,fnv1a,shape_features

APPROVED={"ewt":1.0,"atis":0.70,"childes":0.35,"eslspok":0.70,"esl":0.70}
CLAUSE_REL={"acl","advcl","ccomp","xcomp","parataxis"}

def norm(s):
    return re.sub(r"\s+"," ",str(s).strip().lower())

def iter_jsonl(path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def clause_heads(tokens):
    id2i={int(t["id"]):i for i,t in enumerate(tokens)}
    heads=set()
    for i,t in enumerate(tokens):
        rel=str(t.get("deprel","")).split(":",1)[0]
        pos=t.get("pos")
        if int(t.get("head",0) or 0)==0:
            heads.add(i)
        if rel in CLAUSE_REL:
            heads.add(i)
        if rel=="conj" and pos in {"VERB","AUX"}:
            heads.add(i)
    if not heads and tokens:
        heads.add(0)
    return sorted(heads),id2i

def owner_targets(tokens):
    heads,id2i=clause_heads(tokens)
    hs=set(heads)
    owners=[]
    for start,t in enumerate(tokens):
        if start in hs:
            owners.append(start); continue
        cur=start; seen=set(); owner=None
        while cur not in seen:
            seen.add(cur)
            if cur in hs:
                owner=cur; break
            hid=int(tokens[cur].get("head",0) or 0)
            if hid==0 or hid not in id2i:
                break
            cur=id2i[hid]
        if owner is None:
            owner=min(heads,key=lambda h:abs(h-start))
        owners.append(owner)
    return owners,heads

def make_example(row,source_weight):
    ana=row.get("analysis",{})
    toks=ana.get("tokens",[])
    if ana.get("status")!="auto_pass" or not (2<=len(toks)<=160):
        return None
    dec=canonicalize_ud(toks)
    roles=[d.role for d in dec]
    if any(r=="AMBIG" for r in roles):
        return None
    owners,heads=owner_targets(toks)
    feats=[]
    for t in toks:
        w=str(t.get("text",""))
        feats.append({
          "wid":fnv1a(w.lower())%16384,
          "pos":POS2I.get(str(t.get("pos","UNK")),0),
          "shape":shape_features(w),
        })
    return {
      "features":feats,
      "roles":[ROLE2I[r] for r in roles],
      "owners":owners,
      "heads":[1 if i in set(heads) else 0 for i in range(len(toks))],
      "text":row.get("text",""),
      "source":row.get("source",{}).get("key","unknown"),
      "weight":float(source_weight),
    }

def load_corpus(root):
    train=[];dev=[];stats=Counter();seen=set()
    for path in sorted(Path(root).glob("*.jsonl")):
        for row in iter_jsonl(path):
            src=row.get("source",{})
            key=src.get("key",path.stem)
            fn=src.get("filename","")
            if key not in APPROVED:
                continue
            text_key=norm(row.get("text",""))
            if not text_key:
                continue
            if "-train." in fn:
                if text_key in seen:
                    continue
                ex=make_example(row,APPROVED[key])
                if ex:
                    train.append(ex);seen.add(text_key);stats[f"train:{key}"]+=1
            elif "-dev." in fn:
                ex=make_example(row,1.0)
                if ex:
                    dev.append(ex);stats[f"dev:{key}"]+=1
    return train,dev,stats

def balanced_train(train,seed=79191,max_per_source=12000):
    by=defaultdict(list)
    for x in train: by[x["source"]].append(x)
    out=[]
    for src,rows in sorted(by.items()):
        random.Random(seed+sum(map(ord,src))).shuffle(rows)
        out.extend(rows[:max_per_source])
    random.Random(seed).shuffle(out)
    return out

def collate(items,device):
    B=len(items);L=max(len(x["features"]) for x in items)
    wid=torch.zeros(B,L,dtype=torch.long)
    pos=torch.zeros(B,L,dtype=torch.long)
    shape=torch.zeros(B,L,8,dtype=torch.float32)
    roles=torch.zeros(B,L,dtype=torch.long)
    owners=torch.zeros(B,L,dtype=torch.long)
    heads=torch.zeros(B,L,dtype=torch.float32)
    mask=torch.zeros(B,L,dtype=torch.bool)
    weights=torch.ones(B,dtype=torch.float32)
    for b,x in enumerate(items):
        n=len(x["features"]);mask[b,:n]=True;weights[b]=x["weight"]
        roles[b,:n]=torch.tensor(x["roles"])
        owners[b,:n]=torch.tensor(x["owners"])
        heads[b,:n]=torch.tensor(x["heads"])
        for i,f in enumerate(x["features"]):
            wid[b,i]=f["wid"];pos[b,i]=f["pos"];shape[b,i]=torch.tensor(f["shape"])
    batch={"wid":wid.to(device),"pos":pos.to(device),"shape":shape.to(device)}
    return batch,roles.to(device),owners.to(device),heads.to(device),mask.to(device),weights.to(device)
