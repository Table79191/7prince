#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "train"))
import train_ud_role as base

class WebWrapper(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
    def forward(self, wid, pre, suf, pos, role, shape, mask):
        batch = {
            "wid": wid,
            "pre": pre,
            "suf": suf,
            "pos": pos,
            "role": role,
            "shape": shape,
        }
        return self.model(batch, mask.bool())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default="artifacts/v1.8.1_r012_safe_feed_role.pt")
    ap.add_argument("--out", default="web/r012/r012_role.onnx")
    ap.add_argument("--meta", default="web/r012/model_meta.json")
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    model = base.RoleNet().cpu()
    model.load_state_dict(ck["model"], strict=True)
    model.eval()
    wrapper = WebWrapper(model).eval()

    B, L = 1, 12
    wid = torch.zeros(B, L, dtype=torch.long)
    pre = torch.zeros(B, L, dtype=torch.long)
    suf = torch.zeros(B, L, dtype=torch.long)
    pos = torch.zeros(B, L, dtype=torch.long)
    role = torch.zeros(B, L, dtype=torch.long)
    shape = torch.zeros(B, L, 8, dtype=torch.float32)
    mask = torch.ones(B, L, dtype=torch.bool)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapper,
        (wid, pre, suf, pos, role, shape, mask),
        out,
        input_names=["wid","pre","suf","pos","role","shape","mask"],
        output_names=["logits"],
        dynamic_axes={
            "wid": {0:"batch",1:"seq"},
            "pre": {0:"batch",1:"seq"},
            "suf": {0:"batch",1:"seq"},
            "pos": {0:"batch",1:"seq"},
            "role": {0:"batch",1:"seq"},
            "shape": {0:"batch",1:"seq"},
            "mask": {0:"batch",1:"seq"},
            "logits": {0:"batch",1:"seq"},
        },
        opset_version=17,
        do_constant_folding=True,
    )

    meta = {
        "version": ck.get("metrics",{}).get("version","1.8.1-R012-SAFE-FEED"),
        "roles": base.I2ROLE,
        "pos_list": base.POS_LIST,
        "word_vocab": 8192,
        "prefix_vocab": 1024,
        "suffix_vocab": 1024,
        "feature_shape_size": 8,
        "checkpoint": Path(args.checkpoint).name,
        "browser_note": "Neural weights are exact R012; browser POS tagging is approximate unless a compatible POS tagger is supplied."
    }
    Path(args.meta).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"exported {out} bytes={out.stat().st_size}")
    print(f"wrote {args.meta}")

if __name__ == "__main__":
    main()
