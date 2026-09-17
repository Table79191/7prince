#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

ROLE_SET = {None, "S", "V", "O", "C", "M", "AMBIG"}
CLAUSE_BOUNDARY = {"acl", "acl:relcl", "advcl", "ccomp", "xcomp", "parataxis"}
UD_PHRASE_PROPAGATE = {
    "det", "amod", "compound", "flat", "fixed", "nummod", "case",
    "nmod:poss", "poss", "goeswith",
}
MASC_PHRASE_PROPAGATE = {"NMOD", "AMOD", "PMOD", "NAME", "TITLE"}


@dataclass(frozen=True)
class Decision:
    role: Optional[str]
    rule_id: str
    review_status: str = "auto_pass"

    def as_dict(self):
        if self.role not in ROLE_SET:
            raise ValueError(self.role)
        return {
            "canonical_role": self.role,
            "rule_id": self.rule_id,
            "review_status": self.review_status,
        }


def _children(tokens):
    id2i = {t["id"]: i for i, t in enumerate(tokens)}
    children = {i: [] for i in range(len(tokens))}
    for i, t in enumerate(tokens):
        if t.get("head") in id2i:
            children[id2i[t["head"]]].append(i)
    return id2i, children


def _finish(tokens, decisions):
    out = []
    for t, d in zip(tokens, decisions):
        if d is None:
            if t.get("pos") == "PUNCT":
                d = Decision(None, "PUNCT_001")
            else:
                d = Decision("M", "M_DEFAULT_001")
        out.append(d)
    return out


def canonicalize_ud(tokens):
    """Canonical UD -> S/V/O/C/M decisions with provenance.

    This intentionally prefers AMBIG over guessing for coordination that would
    otherwise inherit a core phrase role without an explicit subject/object link.
    """
    id2i, children = _children(tokens)
    direct = {}
    cop_parents = set()

    for i, t in enumerate(tokens):
        rel = t.get("deprel", "")
        base = rel.split(":", 1)[0]
        pos = t.get("pos")
        if base in {"nsubj", "csubj", "expl"}:
            direct[i] = Decision("S", "S_UD_SUBJ_001")
        elif base in {"obj", "iobj"}:
            direct[i] = Decision("O", "O_UD_OBJ_001")
        if base == "cop" and t.get("head") in id2i:
            cop_parents.add(id2i[t["head"]])
        if base == "xcomp" and pos in {"ADJ", "NOUN", "PROPN", "PRON", "NUM"}:
            direct[i] = Decision("C", "C_UD_XCOMP_001")

    for i in cop_parents:
        if tokens[i].get("pos") not in {"VERB", "AUX"}:
            direct[i] = Decision("C", "C_UD_COP_HEAD_001")

    decisions = [None] * len(tokens)

    def propagate(root, decision):
        stack = [root]
        seen = set()
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            if i != root and i in direct:
                continue
            t = tokens[i]
            pos = t.get("pos")
            if pos in {"VERB", "AUX", "PUNCT"} and i != root:
                continue
            if decisions[i] is None:
                decisions[i] = Decision(
                    decision.role,
                    decision.rule_id + "_SPAN" if i != root else decision.rule_id,
                )
            for j in children.get(i, []):
                rel = tokens[j].get("deprel", "")
                base = rel.split(":", 1)[0]
                if rel in CLAUSE_BOUNDARY or base in {"ccomp", "xcomp", "advcl", "parataxis", "acl"}:
                    continue
                if base == "conj":
                    if decisions[j] is None:
                        decisions[j] = Decision("AMBIG", "COORD_REVIEW_001", "needs_review")
                    continue
                if rel in UD_PHRASE_PROPAGATE or base in {"det", "amod", "compound", "flat", "fixed", "nummod", "case"}:
                    stack.append(j)

    order = {"S": 0, "O": 1, "C": 2}
    for root, decision in sorted(direct.items(), key=lambda kv: order[kv[1].role]):
        propagate(root, decision)

    for i, t in enumerate(tokens):
        pos = t.get("pos")
        if pos == "VERB":
            decisions[i] = Decision("V", "V_LEX_001")
        elif pos == "AUX":
            decisions[i] = Decision("V", "V_AUX_001")

    for i, decision in direct.items():
        if tokens[i].get("pos") not in {"VERB", "AUX"}:
            decisions[i] = decision

    return _finish(tokens, decisions)


def canonicalize_masc(tokens):
    """Canonical MASC-CONLL -> S/V/O/C/M decisions with provenance."""
    _, children = _children(tokens)
    direct = {}
    for i, t in enumerate(tokens):
        rel = t.get("deprel", "").upper()
        if rel == "SBJ":
            direct[i] = Decision("S", "S_MASC_SBJ_001")
        elif rel == "OBJ":
            direct[i] = Decision("O", "O_MASC_OBJ_001")
        elif rel in {"PRD", "OPRD"}:
            direct[i] = Decision("C", "C_MASC_PRD_001")

    decisions = [None] * len(tokens)
    for root, decision in direct.items():
        stack = [root]
        seen = set()
        while stack:
            i = stack.pop()
            if i in seen:
                continue
            seen.add(i)
            if i != root and i in direct:
                continue
            if tokens[i].get("pos") in {"VERB", "AUX", "PUNCT"} and i != root:
                continue
            if decisions[i] is None:
                decisions[i] = Decision(
                    decision.role,
                    decision.rule_id + "_SPAN" if i != root else decision.rule_id,
                )
            for j in children.get(i, []):
                rel = tokens[j].get("deprel", "").upper()
                if rel in {"CONJ", "COORD"}:
                    if decisions[j] is None:
                        decisions[j] = Decision("AMBIG", "COORD_REVIEW_001", "needs_review")
                    continue
                if rel in MASC_PHRASE_PROPAGATE and tokens[j].get("pos") not in {"VERB", "AUX"}:
                    stack.append(j)

    for i, t in enumerate(tokens):
        if t.get("pos") == "VERB":
            decisions[i] = Decision("V", "V_LEX_001")
        elif t.get("pos") == "AUX":
            decisions[i] = Decision("V", "V_AUX_001")

    for i, decision in direct.items():
        if tokens[i].get("pos") not in {"VERB", "AUX"}:
            decisions[i] = decision

    return _finish(tokens, decisions)


def supervised_roles(decisions):
    """Return roles for supervised loss; AMBIG becomes None/excluded by caller."""
    return [None if d.role == "AMBIG" else d.role for d in decisions]
