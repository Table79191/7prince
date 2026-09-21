#!/usr/bin/env python3
from __future__ import annotations

import numpy as np

ROLES=[None,"S","V","O","C","M"]
POS_LIST=['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
POS2I={p:i for i,p in enumerate(POS_LIST)}
ALLOWED_HEAD_POS={"VERB","ADJ","NOUN","PROPN"}
NOMINAL_POS={"NOUN","PRON","PROPN"}


def fnv1a(text:str)->int:
    h=2166136261
    for b in text.encode("utf-8","ignore"):
        h ^= b
        h=(h*16777619)&0xffffffff
    return h


def shape_features(word:str):
    lo=word.lower()
    return [
        float(bool(word[:1].isupper())),
        float(word.isupper() and any(c.isalpha() for c in word)),
        float(any(c.isdigit() for c in word)),
        float("-" in word),
        float(lo.endswith("ing")),
        float(lo.endswith("ed")),
        float(lo.endswith("ly")),
        min(len(word),20)/20.0,
    ]


class ClauseOnnxDecoder:
    """NumPy/ONNXRuntime implementation of ClauseAnchorGraph v1.01 decode."""

    def __init__(self, session, head_threshold:float=0.45):
        self.session=session
        self.head_threshold=float(head_threshold)

    def _feeds(self,tokens,pos,owners):
        L=len(tokens)
        return {
            "wid":np.asarray([[fnv1a(w.lower())%16384 for w in tokens]],dtype=np.int64),
            "pos":np.asarray([[POS2I.get(p,0) for p in pos]],dtype=np.int64),
            "shape":np.asarray([[shape_features(w) for w in tokens]],dtype=np.float32),
            "mask":np.ones((1,L),dtype=np.bool_),
            "owners":np.asarray([owners],dtype=np.int64),
        }

    def decode(self,tokens,pos):
        if len(tokens)!=len(pos):
            raise ValueError("tokens/pos length mismatch")
        if not tokens:
            return {"roles":[],"owners":[],"clause_heads":[]}

        L=len(tokens)
        dummy=np.zeros(L,dtype=np.int64)
        head_logits,owner_logits,_=self.session.run(
            ["head_logits","owner_logits","role_logits"],
            self._feeds(tokens,pos,dummy),
        )
        head_logits=head_logits[0,:L].astype(np.float64)
        owner_logits=owner_logits[0,:L,:L].astype(np.float64)
        # Stable sigmoid.
        hp=np.empty_like(head_logits)
        ge=head_logits>=0
        hp[ge]=1.0/(1.0+np.exp(-head_logits[ge]))
        ez=np.exp(head_logits[~ge])
        hp[~ge]=ez/(1.0+ez)

        heads=[
            i for i,(p,tag) in enumerate(zip(hp.tolist(),pos))
            if p>=self.head_threshold and tag in ALLOWED_HEAD_POS
        ]
        if not heads:
            candidates=[i for i,tag in enumerate(pos) if tag in ALLOWED_HEAD_POS]
            if candidates:
                heads=[max(candidates,key=lambda i:float(hp[i]))]
            else:
                heads=[int(np.argmax(hp))]

        allowed=np.zeros(L,dtype=np.bool_)
        allowed[heads]=True
        score=owner_logits.copy()
        score[:,~allowed]=-1.0e9
        owners=np.argmax(score,axis=-1).astype(np.int64)
        for h in heads:
            owners[h]=h

        _,_,role_logits=self.session.run(
            ["head_logits","owner_logits","role_logits"],
            self._feeds(tokens,pos,owners),
        )
        pred=np.argmax(role_logits[0,:L],axis=-1).astype(np.int64)
        roles=[ROLES[int(x)] for x in pred.tolist()]

        # Match ClauseAnchorGraph.decode invariants.
        for i,tag in enumerate(pos):
            if tag in {"VERB","AUX"}:
                roles[i]="V"

        for head in heads:
            members=[i for i,o in enumerate(owners.tolist()) if o==head]
            if not members or any(roles[i]=="S" for i in members):
                continue
            vp=[i for i in members if pos[i] in {"VERB","AUX"}]
            pivot=min(vp or [head])
            candidates=[i for i in members if i<pivot and pos[i] in NOMINAL_POS]
            if candidates:
                roles[max(candidates)]="S"

        for i,tag in enumerate(pos):
            if tag=="PUNCT":
                roles[i]=None

        return {
            "roles":roles,
            "owners":[int(x) for x in owners.tolist()],
            "clause_heads":[int(x) for x in heads],
            "head_probabilities":[float(x) for x in hp.tolist()],
        }
