#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn as nn

ROOT=Path(__file__).resolve().parents[1]
CLAUSE=ROOT/"experiments"/"clause_anchor_graph_v1_01"
sys.path.insert(0,str(CLAUSE))
import model as cmodel


class ClauseWebWrapper(nn.Module):
    """Exportable ClauseAnchorGraph core with caller-supplied owner indices."""

    def __init__(self,model):
        super().__init__()
        self.model=model

    def forward(self,wid,pos,shape,mask,owners):
        batch={"wid":wid,"pos":pos,"shape":shape}
        h=self.model.encode(batch,mask)
        head_logits=self.model.head_score(h).squeeze(-1)
        owner_logits=self.model.owner(h,mask)
        role_logits=self.model.role_logits(h,owners)
        return head_logits,owner_logits,role_logits


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--checkpoint",default="artifacts/arena_hotfeed/clause_arena_latest.pt")
    ap.add_argument("--out",default="web/clause/clause_arena.onnx")
    ap.add_argument("--meta",default="web/clause/model_meta.json")
    a=ap.parse_args()

    ck=torch.load(a.checkpoint,map_location="cpu",weights_only=False)
    version=ck.get("config",{}).get("version") or ck.get("metrics",{}).get("version") or ""
    if not str(version).startswith("CLAUSE-ARENA-R"):
        raise SystemExit(f"unexpected Clause arena checkpoint: {version!r}")

    model=cmodel.ClauseAnchorGraph().cpu()
    model.load_state_dict(ck["model"],strict=True)
    model.eval()
    wrapper=ClauseWebWrapper(model).eval()

    B,L=1,12
    wid=torch.zeros(B,L,dtype=torch.long)
    pos=torch.zeros(B,L,dtype=torch.long)
    shape=torch.zeros(B,L,8,dtype=torch.float32)
    mask=torch.ones(B,L,dtype=torch.bool)
    owners=torch.zeros(B,L,dtype=torch.long)

    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    torch.onnx.export(
        wrapper,(wid,pos,shape,mask,owners),out,
        input_names=["wid","pos","shape","mask","owners"],
        output_names=["head_logits","owner_logits","role_logits"],
        dynamic_axes={
            "wid":{0:"batch",1:"seq"},
            "pos":{0:"batch",1:"seq"},
            "shape":{0:"batch",1:"seq"},
            "mask":{0:"batch",1:"seq"},
            "owners":{0:"batch",1:"seq"},
            "head_logits":{0:"batch",1:"seq"},
            "owner_logits":{0:"batch",1:"seq",2:"head_seq"},
            "role_logits":{0:"batch",1:"seq"},
        },
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )

    meta={
        "version":str(version),
        "checkpoint":Path(a.checkpoint).name,
        "checkpoint_path":str(a.checkpoint),
        "roles":cmodel.ROLES,
        "pos_list":cmodel.POS_LIST,
        "head_threshold":0.45,
        "hybrid_selector":"complex_lowconf_0.65",
        "source":"arena_hotfeed_clause",
    }
    Path(a.meta).write_text(json.dumps(meta,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"version":version,"onnx_bytes":out.stat().st_size,"meta":meta},indent=2))


if __name__=="__main__":
    main()
