#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path

import numpy as np
import torch

from architecture import RoleNet

EXPECTED_SHA256 = '8104c105ae89797cd77ae8dbf0e98c9e081d1463ccac212b2b9654c0f438e9db'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--weights-dir', default='weights')
    ap.add_argument('--npz-out', default='v161_gru3_attn1_state_f16.npz')
    ap.add_argument('--pt-out', default='v161_gru3_attn1_state.pt')
    args = ap.parse_args()

    root = Path(__file__).resolve().parent
    parts = sorted((root / args.weights_dir).glob('part*.b64'))
    if not parts:
        raise SystemExit('no weight parts found')

    b64 = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
    raw = base64.b64decode(b64)
    got = hashlib.sha256(raw).hexdigest()
    if got != EXPECTED_SHA256:
        raise SystemExit(f'SHA256 mismatch: {got} != {EXPECTED_SHA256}')

    npz_path = root / args.npz_out
    npz_path.write_bytes(raw)
    z = np.load(npz_path)
    state = {k: torch.from_numpy(z[k].astype(np.float32, copy=False)) for k in z.files}

    model = RoleNet()
    model.load_state_dict(state, strict=True)
    torch.save({'model': model.state_dict(), 'config': {'gru': 3, 'attn': 1, 'source': 'v1.6.1-f16-reconstruction'}}, root / args.pt_out)
    print(f'restored {len(state)} tensors; parameters={sum(p.numel() for p in model.parameters())}; sha256={got}')


if __name__ == '__main__':
    main()
