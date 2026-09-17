from __future__ import annotations

import torch
import torch.nn as nn

ROLE2I = {None: 0, 'S': 1, 'V': 2, 'O': 3, 'C': 4, 'M': 5}
I2ROLE = [None, 'S', 'V', 'O', 'C', 'M']
POS_LIST = ['UNK','ADJ','ADP','ADV','AUX','CCONJ','DET','INTJ','NOUN','NUM','PART','PRON','PROPN','PUNCT','SCONJ','SYM','VERB','X']
POS2I = {x:i for i,x in enumerate(POS_LIST)}


def fnv1a(s: str) -> int:
    h = 2166136261
    for b in s.encode('utf-8', 'ignore'):
        h ^= b
        h = (h * 16777619) & 0xffffffff
    return h


def feat_token(tok):
    w = tok['text']; lo = w.lower()
    wid = fnv1a(lo) % 8192
    pre = fnv1a(lo[:3]) % 1024
    suf = fnv1a(lo[-3:]) % 1024
    pos = POS2I.get(tok.get('pos') or 'UNK', 0)
    role = ROLE2I.get(tok.get('role'), 0)
    shape = [
        1.0 if w[:1].isupper() else 0.0,
        1.0 if w.isupper() and any(c.isalpha() for c in w) else 0.0,
        1.0 if any(c.isdigit() for c in w) else 0.0,
        1.0 if '-' in w else 0.0,
        1.0 if lo.endswith('ing') else 0.0,
        1.0 if lo.endswith('ed') else 0.0,
        1.0 if lo.endswith('ly') else 0.0,
        min(len(w), 20) / 20.0,
    ]
    return wid, pre, suf, pos, role, shape


class AttentionBlock(nn.Module):
    def __init__(self, d_model=128, heads=4, dropout=0.08):
        super().__init__()
        self.attn = nn.MultiheadAttention(d_model, heads, batch_first=True, dropout=dropout)
        self.n1 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, 192),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(192, d_model),
        )
        self.n2 = nn.LayerNorm(d_model)

    def forward(self, x, mask):
        a, _ = self.attn(x, x, x, key_padding_mask=~mask, need_weights=False)
        x = self.n1(x + a)
        return self.n2(x + self.ff(x))


class RoleNet(nn.Module):
    """SentenceLab v1.6.1 role model: 3-layer BiGRU + 4-head self-attention."""
    def __init__(self):
        super().__init__()
        self.word = nn.Embedding(8192, 32)
        self.pre = nn.Embedding(1024, 8)
        self.suf = nn.Embedding(1024, 8)
        self.pos = nn.Embedding(len(POS_LIST), 16)
        self.brole = nn.Embedding(6, 8)
        self.shape = nn.Linear(8, 16)
        self.proj = nn.Linear(88, 96)
        self.gru = nn.GRU(96, 64, num_layers=3, batch_first=True, bidirectional=True)
        self.blocks = nn.ModuleList([AttentionBlock(128, 4, 0.08)])
        self.out = nn.Linear(128, 6)

    def forward(self, b, mask):
        x = torch.cat([
            self.word(b['wid']), self.pre(b['pre']), self.suf(b['suf']),
            self.pos(b['pos']), self.brole(b['role']), torch.tanh(self.shape(b['shape']))
        ], dim=-1)
        x = torch.nn.functional.gelu(self.proj(x))
        x, _ = self.gru(x)
        for block in self.blocks:
            x = block(x, mask)
        return self.out(x)
