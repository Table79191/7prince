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
    """Canonical UD -> school-style token S/V/O/C/M decisions.

    Core sentence roles are assigned to the syntactic head only. Determiners,
    possessives, adjectives, numerals, case markers, compounds and other phrase
    material remain M instead of inheriting the head's S/O/C label.
    """
    id2i, _ = _children(tokens)
    direct = {}
    cop_parents = set()

    for i, t in enumerate(tokens):
        rel = t.get("deprel", "")
        base = rel.split(":", 1)[0]
        pos = t.get("pos")
        if base in {"nsubj", "csubj", "expl"}:
            direct[i] = Decision("S", "S_UD_SUBJ_HEAD_002")
        elif base in {"obj", "iobj"}:
            direct[i] = Decision("O", "O_UD_OBJ_HEAD_002")
        if base == "cop" and t.get("head") in id2i:
            cop_parents.add(id2i[t["head"]])
        if base == "xcomp" and pos in {"ADJ", "NOUN", "PROPN", "PRON", "NUM"}:
            direct[i] = Decision("C", "C_UD_XCOMP_HEAD_002")

    for i in cop_parents:
        if tokens[i].get("pos") not in {"VERB", "AUX"}:
            direct[i] = Decision("C", "C_UD_COP_HEAD_002")

    decisions = [None] * len(tokens)
    for i, decision in direct.items():
        decisions[i] = decision

    # Preserve the existing conservative coordination policy: a conjunct of a
    # core head is review-only rather than silently inheriting S/O/C.
    for i, t in enumerate(tokens):
        if t.get("deprel", "").split(":", 1)[0] != "conj":
            continue
        head = t.get("head")
        if head in id2i and id2i[head] in direct and decisions[i] is None:
            decisions[i] = Decision("AMBIG", "COORD_REVIEW_002", "needs_review")

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
    """Canonical MASC-CONLL -> school-style head-only S/V/O/C/M roles."""
    id2i, _ = _children(tokens)
    direct = {}
    for i, t in enumerate(tokens):
        rel = t.get("deprel", "").upper()
        if rel == "SBJ":
            direct[i] = Decision("S", "S_MASC_SBJ_HEAD_002")
        elif rel == "OBJ":
            direct[i] = Decision("O", "O_MASC_OBJ_HEAD_002")
        elif rel in {"PRD", "OPRD"}:
            direct[i] = Decision("C", "C_MASC_PRD_HEAD_002")

    decisions = [None] * len(tokens)
    for i, decision in direct.items():
        decisions[i] = decision

    for i, t in enumerate(tokens):
        rel = t.get("deprel", "").upper()
        head = t.get("head")
        if rel in {"CONJ", "COORD"} and head in id2i and id2i[head] in direct:
            decisions[i] = Decision("AMBIG", "COORD_REVIEW_002", "needs_review")

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
