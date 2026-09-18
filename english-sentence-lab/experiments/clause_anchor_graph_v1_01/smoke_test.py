from __future__ import annotations
import torch
from model import ClauseAnchorGraph,ROLE2I,POS2I,decode
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

    # Decoder invariants: punctuation can never be promoted to V and lexical VERB/AUX are V.
    test={
      "wid":torch.randint(0,16384,(1,5)),
      "pos":torch.tensor([[POS2I["NOUN"],POS2I["AUX"],POS2I["VERB"],POS2I["NOUN"],POS2I["PUNCT"]]]),
      "shape":torch.rand(1,5,8),
    }
    result=decode(m,test,torch.ones(1,5,dtype=torch.bool),[test["pos"][0].tolist()])[0]
    assert result.roles[1]=="V" and result.roles[2]=="V",result.roles
    assert result.roles[4] is None,result.roles
    assert all(result.owners[h]==h for h in result.clause_heads),(result.owners,result.clause_heads)

    print("ClauseAnchorGraph v1.01 smoke test: ok")
    print("params",sum(p.numel() for p in m.parameters()))

if __name__=="__main__":main()
