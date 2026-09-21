#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "train"))
sys.path.insert(0, str(ROOT / "scripts"))

import train_ud_role as base
from export_r012_onnx import WebWrapper


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--checkpoint",
        default="artifacts/arena_hotfeed/role_arena_latest.pt",
    )
    ap.add_argument("--out", default="web/r012/r012_role.onnx")
    ap.add_argument("--meta", default="web/r012/model_meta.json")
    args = ap.parse_args()

    checkpoint = Path(args.checkpoint)
    ck = torch.load(checkpoint, map_location="cpu", weights_only=False)
    actual_version = (
        ck.get("config", {}).get("version")
        or ck.get("metrics", {}).get("version")
        or ""
    )
    if not str(actual_version).startswith("R015-ARENA-R"):
        raise SystemExit(
            f"refusing one-shot arena export from unexpected checkpoint version: {actual_version!r}"
        )

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

    with torch.no_grad():
        native = model(
            {
                "wid": wid,
                "pre": pre,
                "suf": suf,
                "pos": pos,
                "role": role,
                "shape": shape,
            },
            mask,
        )
        explicit = wrapper(wid, pre, suf, pos, role, shape, mask)
        wrapper_err = float((native - explicit).abs().max())

    if wrapper_err > 1e-4:
        raise SystemExit(f"manual attention wrapper mismatch: {wrapper_err}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        wrapper,
        (wid, pre, suf, pos, role, shape, mask),
        out,
        input_names=["wid", "pre", "suf", "pos", "role", "shape", "mask"],
        output_names=["logits"],
        dynamic_axes={
            "wid": {0: "batch", 1: "seq"},
            "pre": {0: "batch", 1: "seq"},
            "suf": {0: "batch", 1: "seq"},
            "pos": {0: "batch", 1: "seq"},
            "role": {0: "batch", 1: "seq"},
            "shape": {0: "batch", 1: "seq"},
            "mask": {0: "batch", 1: "seq"},
            "logits": {0: "batch", 1: "seq"},
        },
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )

    metrics = ck.get("metrics", {})
    meta = {
        "version": str(actual_version),
        "roles": base.I2ROLE,
        "pos_list": base.POS_LIST,
        "word_vocab": 8192,
        "prefix_vocab": 1024,
        "suffix_vocab": 1024,
        "feature_shape_size": 8,
        "checkpoint": checkpoint.name,
        "checkpoint_path": str(checkpoint),
        "source": "arena_hotfeed_one_shot",
        "arena_round": metrics.get("arena_round"),
        "wrapper_max_abs_error": wrapper_err,
        "browser_note": (
            "One-shot export of the persisted Arena RoleNet winner. "
            "Neural weights use school-style head-only S/V/O/C labels; "
            "browser/dependency postprocessing remains unchanged."
        ),
    }
    Path(args.meta).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "checkpoint": str(checkpoint),
        "version": actual_version,
        "arena_round": metrics.get("arena_round"),
        "wrapper_max_abs_error": wrapper_err,
        "onnx_bytes": out.stat().st_size,
    }, indent=2))


if __name__ == "__main__":
    main()
