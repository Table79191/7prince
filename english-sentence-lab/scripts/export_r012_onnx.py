#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "train"))
import train_ud_role as base

class WebWrapper(nn.Module):
    """Exact RoleNet inference with MHA written explicitly for dynamic ONNX export."""
    def __init__(self, model):
        super().__init__()
        self.model = model

    def _attention_block(self, x, mask, block):
        attn = block.attn
        qkv = F.linear(x, attn.in_proj_weight, attn.in_proj_bias)
        q, k, v = qkv.chunk(3, dim=-1)
        B = x.size(0)
        L = x.size(1)
        H = attn.num_heads
        D = x.size(2) // H
        q = q.reshape(B, L, H, D).transpose(1, 2)
        k = k.reshape(B, L, H, D).transpose(1, 2)
        v = v.reshape(B, L, H, D).transpose(1, 2)
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(D)
        key_mask = (~mask.bool()).unsqueeze(1).unsqueeze(1)
        scores = scores.masked_fill(key_mask, -1.0e9)
        probs = torch.softmax(scores, dim=-1)
        a = torch.matmul(probs, v)
        a = a.transpose(1, 2).contiguous().reshape(B, L, H * D)
        a = F.linear(a, attn.out_proj.weight, attn.out_proj.bias)
        x = block.n1(x + a)
        x = block.n2(x + block.ff(x))
        return x

    def forward(self, wid, pre, suf, pos, role, shape, mask):
        m = self.model
        x = torch.cat([
            m.word(wid),
            m.pre(pre),
            m.suf(suf),
            m.pos(pos),
            m.brole(role),
            torch.tanh(m.shape(shape)),
        ], dim=-1)
        x = F.gelu(m.proj(x))
        x, _ = m.gru(x)
        for block in m.blocks:
            x = self._attention_block(x, mask, block)
        return m.out(x)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default="artifacts/v1.8.2_r012_school_regression_role.pt")
    ap.add_argument("--out", default="web/r012/r012_role.onnx")
    ap.add_argument("--meta", default="web/r012/model_meta.json")
    args = ap.parse_args()

    ck = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    expected_version = "1.8.2-R012-SCHOOL-REGRESSION"
    actual_version = ck.get("metrics", {}).get("version")
    if actual_version != expected_version:
        raise SystemExit(f"refusing to export stale R012 checkpoint: {actual_version!r}")
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

    # Verify the explicit attention wrapper itself is numerically equivalent
    # before exporting.
    with torch.no_grad():
        native = model(
            {"wid":wid,"pre":pre,"suf":suf,"pos":pos,"role":role,"shape":shape},
            mask,
        )
        explicit = wrapper(wid,pre,suf,pos,role,shape,mask)
        wrapper_err = float((native-explicit).abs().max())
    print("wrapper_max_abs_error", wrapper_err)
    if wrapper_err > 1e-4:
        raise SystemExit(f"manual attention wrapper mismatch: {wrapper_err}")

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
        dynamo=False,
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
        "wrapper_max_abs_error": wrapper_err,
        "browser_note": "Neural weights use school-style head-only S/V/O/C labels. Browser normalization expands contractions such as can't -> can + not and applies shared grammar regressions."
    }
    Path(args.meta).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"exported {out} bytes={out.stat().st_size}")
    print(f"wrote {args.meta}")

if __name__ == "__main__":
    main()
