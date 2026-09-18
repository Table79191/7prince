from __future__ import annotations
import argparse,json
from pathlib import Path
import torch
from model import ClauseAnchorGraph,POS2I,fnv1a,shape_features,decode

def make_batch(tokens,pos):
    L=len(tokens)
    batch={
      "wid":torch.tensor([[fnv1a(w.lower())%16384 for w in tokens]],dtype=torch.long),
      "pos":torch.tensor([[POS2I.get(p,0) for p in pos]],dtype=torch.long),
      "shape":torch.tensor([[shape_features(w) for w in tokens]],dtype=torch.float32),
    }
    mask=torch.ones(1,L,dtype=torch.bool)
    return batch,mask,[batch["pos"][0].tolist()]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default=str(Path(__file__).resolve().parent/"artifacts/clause_anchor_graph_v1.pt"))
    ap.add_argument("--tokens",required=True,help="JSON list")
    ap.add_argument("--pos",required=True,help="JSON list")
    a=ap.parse_args()
    tokens=json.loads(a.tokens);pos=json.loads(a.pos)
    if len(tokens)!=len(pos):raise SystemExit("tokens/pos length mismatch")
    ck=torch.load(a.model,map_location="cpu",weights_only=False)
    m=ClauseAnchorGraph();m.load_state_dict(ck["model"]);m.eval()
    b,mask,pids=make_batch(tokens,pos)
    r=decode(m,b,mask,pids)[0]
    print(json.dumps({"tokens":tokens,"pos":pos,"roles":r.roles,"owners":r.owners,"clause_heads":r.clause_heads},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
