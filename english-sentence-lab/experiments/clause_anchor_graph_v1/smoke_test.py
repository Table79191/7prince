from __future__ import annotations
import sys
from pathlib import Path
import torch
from model import ClauseAnchorGraph,ROLE2I,POS2I
from data import owner_targets

def main():
    toks=[
      {"id":1,"text":"Although","pos":"SCONJ","head":4,"deprel":"mark"},
      {"id":2,"text":"she","pos":"PRON","head":4,"deprel":"nsubj"},
      {"id":3,"text":"had","pos":"AUX","head":4,"deprel":"aux"},
      {"id":4,"text":"warned","pos":"VERB","head":8,"deprel":"advcl"},
      {"id":5,"text":"the","pos":"DET","head":6,"deprel":"det"},
      {"id":6,"text":"manager","pos":"NOUN","head":8,"deprel":"nsubj"},
      {"id":7,"text":"had","pos":"AUX","head":8,"deprel":"aux"},
      {"id":8,"text":"left","pos":"VERB","head":0,"deprel":"root"},
    ]
    owners,heads=owner_targets(toks)
    assert set(heads)=={3,7},(owners,heads)
    assert owners[1]==3 and owners[5]==7,(owners,heads)

    m=ClauseAnchorGraph()
    B,L=2,11
    batch={
      "wid":torch.randint(0,16384,(B,L)),
      "pos":torch.randint(0,len(POS2I),(B,L)),
      "shape":torch.rand(B,L,8),
    }
    mask=torch.ones(B,L,dtype=torch.bool)
    gold_owner=torch.arange(L).unsqueeze(0).repeat(B,1)
    out=m(batch,mask,gold_owner)
    assert out["head_logits"].shape==(B,L)
    assert out["owner_logits"].shape==(B,L,L)
    assert out["role_logits"].shape==(B,L,6)
    loss=out["role_logits"].sum()+out["head_logits"].sum()+out["owner_logits"][out["owner_logits"]>-1e8].sum()
    loss.backward()
    assert all(p.grad is not None for p in m.parameters() if p.requires_grad)
    print("ClauseAnchorGraph smoke test: ok")
    print("params",sum(p.numel() for p in m.parameters()))

if __name__=="__main__":main()
