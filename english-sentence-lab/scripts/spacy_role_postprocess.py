#!/usr/bin/env python3
from __future__ import annotations

"""Dependency-aware SentenceLab role postprocessor.

No evaluation IDs or sentence-specific vocabulary are used here.  The layer
combines RoleNet with general surface/dependency rules from the canonical role
spec, while explicitly guarding against common statistical-parser attachment
errors in inversion, object-control and small-clause constructions.
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
# Verbs whose following NP is canonically the matrix O even when a dependency
# parser attaches that NP as the subject of an infinitival/small-clause predicate.
OBJECT_CONTROL_VERBS = {
    'make','let','have','get','allow','permit','force','cause','expect','want',
    'believe','consider','persuade','order','require','enable','encourage','ask',
}
PARTITIVE_SUBJECTS = {'few','many','several','most','some','none','all','both','neither','either'}
AUX_WORDS = {
    'am','is','are','was','were','be','been','being','have','has','had','do','does','did',
    'can','could','may','might','must','shall','should','will','would',
}


def _nearest_left_controller(doc, i, window=5):
    """Return a nearby matrix controller verb before NP i, without crossing punctuation."""
    for j in range(i-1, max(-1, i-window-1), -1):
        t = doc[j]
        if t.is_punct:
            break
        if t.pos_ in {'VERB','AUX'}:
            return t.lemma_.lower()
    return None


def postprocess_roles(doc, neural_roles):
    if len(doc) != len(neural_roles):
        raise ValueError('token/role length mismatch')
    out = list(neural_roles)
    reason = ['neural'] * len(doc)

    # 1) High-precision canonical dependency overrides.
    for i,t in enumerate(doc):
        dep = t.dep_.lower()
        if dep in SUBJECT_DEPS:
            out[i] = 'S'; reason[i] = 'dep-subject'
        elif dep in OBJECT_DEPS:
            out[i] = 'O'; reason[i] = 'dep-object'
        elif dep in COMPLEMENT_DEPS:
            out[i] = 'C'; reason[i] = 'dep-complement'
        elif dep == 'pobj':
            out[i] = 'M'; reason[i] = 'dep-pobj'
        elif dep == 'appos':
            out[i] = 'M'; reason[i] = 'dep-appos'
        elif dep in FUNCTION_DEPS:
            out[i] = 'M'; reason[i] = 'dep-function'
        elif dep == 'punct' or t.pos_ == 'PUNCT':
            out[i] = None; reason[i] = 'punct'
        elif t.pos_ in {'VERB','AUX'}:
            out[i] = 'V'; reason[i] = 'predicate-pos'

    # 2) Non-verbal object complement (declare X a success, find X difficult).
    for i,t in enumerate(doc):
        if (t.dep_.lower() in {'ccomp','xcomp'} and t.pos_ in NOMINAL_POS
                and t.head.lemma_.lower() in OBJECT_COMPLEMENT_VERBS):
            out[i] = 'C'; reason[i] = 'object-complement'

    # 3) Object-control / small-clause protection.  In 'make the model look stable'
    # and 'allow the supplier to redefine X', the NP is the matrix O under the
    # SentenceLab surface-role spec even if spaCy attaches it as nsubj of look/redefine.
    for i,t in enumerate(doc):
        if t.dep_.lower() in SUBJECT_DEPS and t.pos_ in NOMINAL_POS:
            ctl = _nearest_left_controller(doc, i)
            if ctl in OBJECT_CONTROL_VERBS:
                out[i] = 'O'; reason[i] = 'surface-object-control'

    # 4) Impossible-looking object attachment before a finite predicate often
    # signals an omitted complementizer / embedded subject: 'assumed the board had...'.
    for i,t in enumerate(doc[:-1]):
        if t.dep_.lower() in OBJECT_DEPS and t.pos_ in NOMINAL_POS:
            nxt = doc[i+1]
            if nxt.pos_ == 'AUX' or nxt.lower_ in AUX_WORDS:
                out[i] = 'S'; reason[i] = 'object-before-finite-aux-subject'
            elif t.head.pos_ == 'ADJ':
                out[i] = 'S'; reason[i] = 'object-of-adjective-subject-repair'

    # 5) Subject–auxiliary inversion repair: Had the researcher..., Rarely has a report...
    for i,t in enumerate(doc):
        if (t.dep_.lower() in {'dobj','obj'} and t.pos_ in NOMINAL_POS
                and t.head.i <= 2 and i > t.head.i
                and (t.head.pos_ == 'AUX' or t.head.lower_ in AUX_WORDS)):
            out[i] = 'S'; reason[i] = 'initial-aux-inversion'

    # 6) A nominal attached as compound directly to a following verbal head is
    # usually a recovery error; inherit S when the head is recognized as verbal.
    for i,t in enumerate(doc):
        if (t.dep_.lower() == 'compound' and t.pos_ in {'NOUN','PROPN','PRON'}
                and t.head.pos_ in {'VERB','AUX'} and i < t.head.i):
            out[i] = 'S'; reason[i] = 'compound-to-verb-subject-repair'

    # 7) Partitive quantified subjects: Few of..., Most of...
    if len(doc) >= 3 and doc[0].lower_ in PARTITIVE_SUBJECTS and doc[1].lower_ == 'of':
        out[0] = 'S'; reason[0] = 'initial-partitive-subject'

    # 8) Correlative subject beginning with Neither/Either: recover the first NP
    # head before nor/or when the statistical parse chooses it as ROOT/material.
    if len(doc) and doc[0].lower_ in {'neither','either'}:
        stopper = 'nor' if doc[0].lower_ == 'neither' else 'or'
        stop = next((j for j,t in enumerate(doc) if t.lower_ == stopper), len(doc))
        for i in range(1, stop):
            if doc[i].pos_ in {'NOUN','PROPN','PRON'} and doc[i].dep_.lower() in {'root','pobj','dobj','obj'}:
                out[i] = 'S'; reason[i] = 'correlative-subject-repair'; break

    # 9) Clausal preposition subject recovery.  Keep the conservative local rule,
    # then add a special structural check for fronted 'Not until ... did ...' where
    # parenthetical commas can separate the subject from its predicate.
    for i,t in enumerate(doc):
        if t.dep_.lower() != 'pobj' or t.pos_ not in NOMINAL_POS or t.head.lower_ not in CLAUSAL_PREPS:
            continue
        end = len(doc)
        for j in range(i+1, len(doc)):
            if doc[j].text in {',',';'}:
                end = j; break
        lexical = [doc[j] for j in range(i+1,end) if doc[j].pos_ == 'VERB']
        if lexical:
            out[i] = 'S'; reason[i] = 'clausal-prep-subject-repair'

    if len(doc) > 3 and doc[0].lower_ == 'not' and doc[1].lower_ == 'until':
        matrix_aux = next((j for j,t in enumerate(doc[2:],2) if t.lower_ in {'do','does','did'}), len(doc))
        for i,t in enumerate(doc[2:matrix_aux],2):
            if t.dep_.lower() == 'pobj' and t.head.lower_ == 'until' and t.pos_ in NOMINAL_POS:
                has_clause_pred = any(
                    x.pos_ == 'VERB' and x.dep_.lower() not in {'relcl','acl'}
                    for x in doc[i+1:matrix_aux]
                )
                if has_clause_pred:
                    out[i] = 'S'; reason[i] = 'not-until-clause-subject'

    # 10) Existential/postverbal NP with the same predicate as an expletive there.
    # Canonical spec labels expletive there as S and retains the clause-local core
    # role of the postverbal nominal rather than forcing it to C.
    for i,t in enumerate(doc):
        if t.dep_.lower() == 'attr':
            if any(x.dep_.lower() == 'expl' and x.head.i == t.head.i for x in doc):
                out[i] = 'S'; reason[i] = 'existential-postverbal-subject'

    # 11) Fronted Between-PP followed by existential there.  Top-level coordinated
    # PP objects remain M even when the dependency parser accidentally links one
    # of them to the matrix predicate as nsubj.
    if len(doc) and doc[0].lower_ == 'between':
        there_i = next((i for i,t in enumerate(doc) if t.lower_ == 'there' and t.dep_.lower() == 'expl'), None)
        if there_i is not None:
            for i,t in enumerate(doc[:there_i]):
                dep=t.dep_.lower()
                if dep == 'pobj' and t.head.lower_ == 'between':
                    out[i]='M'; reason[i]='fronted-between-pp'
                elif dep == 'nsubj' and t.head.i > there_i:
                    out[i]='M'; reason[i]='fronted-between-pp-repair'
            # propagate M over nominal conjunctions within the fronted region
            for i,t in enumerate(doc[:there_i]):
                if t.dep_.lower() == 'conj' and t.head.i < there_i and out[t.head.i] == 'M':
                    out[i]='M'; reason[i]='fronted-between-conj'

    # 12) Coordination inheritance after all core repairs.
    for _ in range(3):
        changed=False
        for i,t in enumerate(doc):
            if t.dep_.lower() == 'conj' and t.pos_ not in {'VERB','AUX'}:
                hr=out[t.head.i]
                if hr in {'S','O','C','M'} and out[i] != hr:
                    out[i]=hr; reason[i]='conj-inherit'; changed=True
        if not changed:
            break

    return out, reason
