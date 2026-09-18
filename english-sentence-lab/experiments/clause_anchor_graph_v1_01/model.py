from __future__ import annotations
from dataclasses import dataclass
import torch
import torch.nn as nn
import torch.nn.functional as F

VERSION="CLAUSE-ANCHOR-GRAPH-V1.01"
ROLES=[None,"S","V","O","C","M"]
ROLE2I={r:i for i,r in enumerate(ROLES)}
POS_LIST=['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
POS2I={p:i for i,p in enumerate(POS_LIST)}

def fnv1a(text:str)->int:
    h=2166136261
    for b in text.encode("utf-8","ignore"):
        h ^= b
        h=(h*16777619)&0xffffffff
    return h

def shape_features(word:str):
    lo=word.lower()
    return [
        float(word[:1].isupper()),
        float(word.isupper() and any(c.isalpha() for c in word)),
        float(any(c.isdigit() for c in word)),
        float("-" in word),
        float(lo.endswith("ing")),
        float(lo.endswith("ed")),
        float(lo.endswith("ly")),
        min(len(word),20)/20.0,
    ]

class GatedDilatedBlock(nn.Module):
    def __init__(self,d_model:int,dilation:int,dropout:float=.10):
        super().__init__()
        self.norm=nn.LayerNorm(d_model)
        self.conv=nn.Conv1d(d_model,2*d_model,kernel_size=3,padding=dilation,dilation=dilation)
        self.mix=nn.Conv1d(d_model,d_model,kernel_size=1)
        self.drop=nn.Dropout(dropout)
    def forward(self,x,mask):
        z=self.norm(x).transpose(1,2)
        a,b=self.conv(z).chunk(2,dim=1)
        z=torch.tanh(a)*torch.sigmoid(b)
        z=self.mix(z).transpose(1,2)
        x=x+self.drop(z)
        return x*mask.unsqueeze(-1)

class BiaffineOwner(nn.Module):
    def __init__(self,d_model:int=128,d_arc:int=96,max_rel:int=64):
        super().__init__()
        self.max_rel=max_rel
        self.dep=nn.Linear(d_model,d_arc)
        self.head=nn.Linear(d_model,d_arc)
        self.U=nn.Parameter(torch.empty(d_arc,d_arc))
        self.dep_bias=nn.Linear(d_arc,1,bias=False)
        self.head_bias=nn.Linear(d_arc,1,bias=False)
        self.rel_bias=nn.Embedding(max_rel*2+1,1)
        nn.init.xavier_uniform_(self.U)
        with torch.no_grad():
            d=torch.arange(-max_rel,max_rel+1,dtype=torch.float32).abs()
            self.rel_bias.weight[:,0].copy_(-0.06*d)

    def forward(self,h,mask):
        d=torch.tanh(self.dep(h))
        a=torch.tanh(self.head(h))
        bil=torch.einsum("bid,dh,bjh->bij",d,self.U,a)
        s=bil+self.dep_bias(d)+self.head_bias(a).transpose(1,2)
        L=h.size(1)
        tok=torch.arange(L,device=h.device).view(L,1)
        head=torch.arange(L,device=h.device).view(1,L)
        rel=(tok-head).clamp(-self.max_rel,self.max_rel)+self.max_rel
        s=s+self.rel_bias(rel).squeeze(-1).unsqueeze(0)
        valid=mask.unsqueeze(1)&mask.unsqueeze(2)
        return s.masked_fill(~valid,-1e9)

class ClauseAnchorGraph(nn.Module):
    def __init__(self,d_model=128,max_pos=256,max_rel=64):
        super().__init__()
        self.max_rel=max_rel
        self.word=nn.Embedding(16384,64)
        self.pos=nn.Embedding(len(POS_LIST),24)
        self.shape=nn.Linear(8,16)
        self.abspos=nn.Embedding(max_pos,16)
        self.input=nn.Linear(120,d_model)
        self.blocks=nn.ModuleList([GatedDilatedBlock(d_model,d) for d in (1,2,4,8,16,1)])
        self.head_score=nn.Linear(d_model,1)
        self.owner=BiaffineOwner(d_model,96,max_rel=max_rel)
        self.rel=nn.Embedding(max_rel*2+1,16)
        self.role=nn.Sequential(
            nn.Linear(d_model*3+16,192),
            nn.GELU(),
            nn.Dropout(.10),
            nn.Linear(192,96),
            nn.GELU(),
            nn.Linear(96,len(ROLES)),
        )

    def encode(self,batch,mask):
        B,L=batch["wid"].shape
        p=torch.arange(L,device=mask.device).clamp_max(self.abspos.num_embeddings-1)
        p=p.unsqueeze(0).expand(B,L)
        x=torch.cat([
            self.word(batch["wid"]),
            self.pos(batch["pos"]),
            torch.tanh(self.shape(batch["shape"])),
            self.abspos(p),
        ],dim=-1)
        x=F.gelu(self.input(x))*mask.unsqueeze(-1)
        for block in self.blocks:
            x=block(x,mask)
        return x

    def role_logits(self,h,owners):
        B,L,D=h.shape
        idx=owners.clamp_min(0).clamp_max(L-1)
        owner_h=torch.gather(h,1,idx.unsqueeze(-1).expand(B,L,D))
        tok=torch.arange(L,device=h.device).unsqueeze(0).expand(B,L)
        rel=(tok-idx).clamp(-self.max_rel,self.max_rel)+self.max_rel
        feat=torch.cat([h,owner_h,h*owner_h,self.rel(rel)],dim=-1)
        return self.role(feat)

    def forward(self,batch,mask,gold_owner=None):
        h=self.encode(batch,mask)
        head_logits=self.head_score(h).squeeze(-1)
        owner_logits=self.owner(h,mask)
        owners=gold_owner if gold_owner is not None else owner_logits.argmax(-1)
        role_logits=self.role_logits(h,owners)
        return {"hidden":h,"head_logits":head_logits,"owner_logits":owner_logits,"owners":owners,"role_logits":role_logits}

@dataclass
class DecodeResult:
    roles:list
    owners:list
    clause_heads:list

@torch.no_grad()
def decode(model,batch,mask,pos_ids,head_threshold=.45):
    model.eval()
    out=model(batch,mask)
    h=out["hidden"]
    owner_logits=out["owner_logits"]
    head_prob=torch.sigmoid(out["head_logits"])
    B,L=mask.shape
    results=[]
    allowed_heads={POS2I["VERB"],POS2I["ADJ"],POS2I["NOUN"],POS2I["PROPN"]}
    for b in range(B):
        n=int(mask[b].sum().item())
        probs=head_prob[b,:n]
        local_pos=[int(x) for x in pos_ids[b][:n]]
        heads=[
            i for i,p in enumerate(probs.tolist())
            if p>=head_threshold and local_pos[i] in allowed_heads
        ]
        if not heads:
            candidates=[i for i,pid in enumerate(local_pos) if pid in allowed_heads]
            heads=[max(candidates,key=lambda i:float(probs[i]))] if candidates else [int(probs.argmax().item())]

        head_mask=torch.full((n,),False,device=mask.device)
        head_mask[heads]=True
        score=owner_logits[b,:n,:n].clone()
        score[:,~head_mask]=-1e9
        owners=score.argmax(-1)
        for head in heads:
            owners[head]=head

        role_logits=model.role_logits(h[b:b+1,:n],owners.unsqueeze(0))[0]
        pred=role_logits.argmax(-1)

        # v1.01 follows role_label_spec_v2: every lexical VERB/AUX is V.
        for i,pid in enumerate(local_pos):
            if pid in {POS2I["VERB"],POS2I["AUX"]}:
                pred[i]=ROLE2I["V"]

        # Conservative subject repair: only when a decoded clause has no S.
        for head in heads:
            members=(owners==head).nonzero(as_tuple=False).flatten().tolist()
            if not members or any(int(pred[i])==ROLE2I["S"] for i in members):
                continue
            pivot=min([i for i in members if local_pos[i] in {POS2I["VERB"],POS2I["AUX"]}] or [head])
            candidates=[
                i for i in members
                if i<pivot and local_pos[i] in {POS2I["NOUN"],POS2I["PRON"],POS2I["PROPN"]}
            ]
            if candidates:
                pred[max(candidates)]=ROLE2I["S"]

        # Punctuation null is the final invariant so later structural repair cannot overwrite it.
        for i,pid in enumerate(local_pos):
            if pid==POS2I["PUNCT"]:
                pred[i]=0

        results.append(DecodeResult(
            roles=[ROLES[int(x)] for x in pred.tolist()],
            owners=[int(x) for x in owners.tolist()],
            clause_heads=heads,
        ))
    return results
