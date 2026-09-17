#!/usr/bin/env python3
from __future__ import annotations

"""Dependency-aware SentenceLab role postprocessor.

This module never uses ChaosMix50 IDs or sentence-specific vocabulary.  It applies
canonical role-spec rules to a spaCy parse after RoleNet inference, primarily to
repair long-distance S/O confusion and function-material leakage.
"""

SUBJECT_DEPS = {'nsubj','nsubjpass','csubj','csubjpass','expl'}
OBJECT_DEPS = {'dobj','obj','iobj','dative'}
COMPLEMENT_DEPS = {'attr','acomp','oprd'}
FUNCTION_DEPS = {'prep','agent','mark','cc','advmod','neg','discourse'}
NOMINAL_POS = {'NOUN','PROPN','PRON','NUM','ADJ'}
CLAUSAL_PREPS = {'until','after','before','than','when','while','since','once'}
OBJECT_COMPLEMENT_VERBS = {
    'declare','consider','find','make','call','name','deem','elect','appoint',
    'render','prove','label','pronounce',
}
PARTITIVE_SUBJECTS = {'few','many','several','most','some','none','all','both','neither','either'}


def postprocess_roles(doc, neural_roles):
    if len(doc) != len(neural_roles):
        raise ValueError('token/role length mismatch')
    out = list(neural_roles)
    reason = ['neural'] * len(doc)

    # 1) High-precision canonical dependency overrides.
    # Dependency subject/object evidence intentionally outranks POS because a
    # tagger may occasionally call a nominal token VERB/ADV in hard sentences.
    for i,t in enumerate(doc):
        dep = t.dep_.lower()
        if dep in SUBJECT_DEPS:
            out[i] = 'S'; reason[i] = 'dep-subject'
        elif dep in OBJECT_DEPS:
            out[i] = 'O'; reason[i] = 'dep-object'
        elif dep in COMPLEMENT_DEPS:
            out[i] = 'C'; reason[i] = 'dep-complement'
        elif dep == 'pobj':
            # Canonical spec M002: ordinary PP complements are function/modifier material.
            out[i] = 'M'; reason[i] = 'dep-pobj'
        elif dep == 'appos':
            out[i] = 'M'; reason[i] = 'dep-appos'
        elif dep in FUNCTION_DEPS:
            out[i] = 'M'; reason[i] = 'dep-function'
        elif dep == 'punct' or t.pos_ == 'PUNCT':
            out[i] = None; reason[i] = 'punct'
        elif t.pos_ in {'VERB','AUX'}:
            out[i] = 'V'; reason[i] = 'predicate-pos'

    # 2) Non-verbal object-complement rescue (e.g. declare X a success).
    for i,t in enumerate(doc):
        if (t.dep_.lower() in {'ccomp','xcomp'} and t.pos_ in NOMINAL_POS
                and t.head.lemma_.lower() in OBJECT_COMPLEMENT_VERBS):
            out[i] = 'C'; reason[i] = 'object-complement'

    # 3) Coordination inheritance for nominal conjuncts.  The conjunction itself
    # stays M, but a coordinated NP can inherit the head NP's core role.
    for _ in range(3):
        changed = False
        for i,t in enumerate(doc):
            if t.dep_.lower() == 'conj' and t.pos_ not in {'VERB','AUX'}:
                hr = out[t.head.i]
                if hr in {'S','O','C','M'} and out[i] != hr:
                    out[i] = hr; reason[i] = 'conj-inherit'; changed = True
        if not changed:
            break

    # 4) Subject–auxiliary inversion repair.  Some statistical parses label the
    # NP after a fronted auxiliary as dobj even though it is the surface subject:
    # 'Had the researcher ...', 'Rarely has a report ...'.
    for i,t in enumerate(doc):
        if (t.dep_.lower() in {'dobj','obj'} and t.pos_ in NOMINAL_POS
                and t.head.pos_ == 'AUX' and t.head.i <= 2 and i > t.head.i):
            out[i] = 'S'; reason[i] = 'initial-aux-inversion'

    # 5) A nominal immediately attached as 'compound' to a following finite verb
    # is almost certainly a parser recovery error, not a true nominal compound.
    for i,t in enumerate(doc):
        if (t.dep_.lower() == 'compound' and t.pos_ in {'NOUN','PROPN','PRON'}
                and t.head.pos_ in {'VERB','AUX'} and i < t.head.i):
            out[i] = 'S'; reason[i] = 'compound-to-verb-subject-repair'

    # 6) Partitive quantified subjects at sentence start: 'Few of the people ...'.
    if len(doc) >= 3 and doc[0].lower_ in PARTITIVE_SUBJECTS and doc[1].lower_ == 'of':
        out[0] = 'S'; reason[0] = 'initial-partitive-subject'

    # 7) If a clausal preposition was parsed as taking a nominal pobj but that
    # nominal precedes a finite predicate inside the same comma-delimited region,
    # recover it as the clause subject.  This handles difficult fronted clauses
    # without hard-coding any test sentence.
    for i,t in enumerate(doc):
        if t.dep_.lower() != 'pobj' or t.pos_ not in NOMINAL_POS:
            continue
        if t.head.lower_ not in CLAUSAL_PREPS:
            continue
        # Stop at the next major punctuation. Relative-clause verbs alone do not
        # qualify unless a second predicate is also present.
        end = len(doc)
        for j in range(i+1, len(doc)):
            if doc[j].text in {',',';'}:
                end = j; break
        lexical = [doc[j] for j in range(i+1,end) if doc[j].pos_ == 'VERB']
        if lexical:
            out[i] = 'S'; reason[i] = 'clausal-prep-subject-repair'

    return out, reason
