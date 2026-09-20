#!/usr/bin/env python3
from __future__ import annotations

"""Dependency-aware SentenceLab role postprocessor.

No evaluation IDs or sentence-specific vocabulary are used here. The layer
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
COPULAR_COMPLEMENT_PREPS = {
    'in','on','at','to','from','through','under','over','inside','outside','against',
    'with','without','like','as','around','near','behind','before','after','between',
}
OBJECT_COMPLEMENT_VERBS = {
    'declare','consider','find','make','call','name','deem','elect','appoint',
    'render','prove','label','pronounce',
}
OBJECT_CONTROL_VERBS = {
    'make','let','get','allow','permit','force','cause','expect','want',
    'believe','consider','persuade','order','require','enable','encourage','ask',
}
CLAUSAL_COMPLEMENT_VERBS = {
    'assume','believe','think','say','claim','insist','discover','know','report',
    'suppose','expect','notice','realize','remember','forget','argue','agree',
    'warn','explain','admit','deny','decide','predict','suggest','hear','see',
}
PARTITIVE_SUBJECTS = {'few','many','several','most','some','none','all','both','neither','either'}
AUX_WORDS = {
    'am','is','are','was','were','be','been','being','have','has','had','do','does','did',
    'can','could','may','might','must','shall','should','will','would',
}
CONTROLLER_BOUNDARIES = {
    'that','whether','if','why','how','when','while','because','although','though',
    'unless','since','once','after','before','than','where','wherever','whenever',
}
CLAUSE_MARKERS = {'that','whether','if'}
WH_NOMINALS = {'what','who','whom','which','whatever','whoever','whomever','whichever'}
WH_ADVERBIALS = {'when','where','why','how','whenever','wherever','however'}

EMPHATIC_WH_FILLERS = {
    ('the','hell'),
    ('on','earth'),
    ('in','the','world'),
}
APPROX_PERCENT_MARKERS = {'like','about','around','approximately','roughly','nearly','almost'}
DEMONSTRATIVE_PRONOUNS = {'this','that','these','those'}


def _nearest_lexical_controller(doc, i, window=6):
    for j in range(i - 1, max(-1, i - window - 1), -1):
        t = doc[j]
        if t.is_punct or t.lower_ in CONTROLLER_BOUNDARIES or t.dep_.lower() == 'mark':
            break
        if t.pos_ == 'VERB':
            return t.lemma_.lower()
    return None


def _has_left_clause_marker(doc, i, window=7):
    for j in range(i - 1, max(-1, i - window - 1), -1):
        t = doc[j]
        if t.is_punct:
            break
        if t.lower_ in CLAUSE_MARKERS:
            return True
    return False


def _has_subject_before(doc, i):
    return any(t.dep_.lower() in SUBJECT_DEPS for t in doc[:i])


def _copular_prep_complement(t):
    """True for state/location PP complements selected by copular *be*."""
    if (t.dep_.lower() != 'pobj' or t.head.pos_ not in {'ADP','ADV'}
            or t.head.lower_ not in COPULAR_COMPLEMENT_PREPS):
        return False
    host = t.head.head
    return host.lemma_.lower() == 'be' or (
        host.dep_.lower() == 'root' and any(ch.dep_.lower() == 'cop' for ch in host.children)
    )


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
            copular_wh = (
                neural_roles[i] == 'C' and t.lower_ in WH_NOMINALS
                and any(x.lemma_.lower() == 'be' for x in doc[:i])
            )
            if not copular_wh:
                out[i] = 'O'; reason[i] = 'dep-object'
        elif dep in COMPLEMENT_DEPS:
            embedded_wh_object = (
                neural_roles[i] == 'O' and t.lower_ in WH_NOMINALS
                and t.head.lemma_.lower() == 'be'
                and any(x.lemma_.lower() in CLAUSAL_COMPLEMENT_VERBS for x in doc[:i])
            )
            if not embedded_wh_object:
                out[i] = 'C'; reason[i] = 'dep-complement'
        elif dep == 'pobj':
            # Preserve a neural core label through an "of" NP only for lexical
            # nominals whose containing nominal already has the same core role.
            # Relative/partitive pronouns ("of whom/which") remain modifiers.
            nominal_head = t.head.head if t.head.lower_ == 'of' else None
            same_of_core = (
                nominal_head is not None
                and t.pos_ != 'PRON'
                and neural_roles[i] in {'S','O','C'}
                and out[nominal_head.i] == neural_roles[i]
            )
            if same_of_core:
                out[i] = neural_roles[i]; reason[i] = 'of-np-neural-core-preserve'
            elif neural_roles[i] == 'C' and _copular_prep_complement(t):
                out[i] = 'C'; reason[i] = 'copular-pobj-complement'
            else:
                out[i] = 'M'; reason[i] = 'dep-pobj'
        elif dep == 'appos':
            out[i] = 'M'; reason[i] = 'dep-appos'
        elif dep in FUNCTION_DEPS:
            out[i] = 'M'; reason[i] = 'dep-function'
        elif dep == 'punct' or t.pos_ == 'PUNCT':
            out[i] = None; reason[i] = 'punct'
        elif t.pos_ in {'VERB','AUX'}:
            out[i] = 'V'; reason[i] = 'predicate-pos'

    # 2) Non-verbal object complement.
    for i,t in enumerate(doc):
        if (t.dep_.lower() in {'ccomp','xcomp'} and t.pos_ in NOMINAL_POS
                and t.head.lemma_.lower() in OBJECT_COMPLEMENT_VERBS):
            out[i] = 'C'; reason[i] = 'object-complement'

    # 3) No broad "of" propagation: handled conservatively in pobj above.

    # 4) Object-control / small-clause recovery.
    for i,t in enumerate(doc):
        if (t.dep_.lower() in SUBJECT_DEPS and neural_roles[i] == 'O'
                and t.pos_ in NOMINAL_POS):
            ctl = _nearest_lexical_controller(doc, i)
            if ctl in OBJECT_CONTROL_VERBS:
                out[i] = 'O'; reason[i] = 'neural-object-local-control'

    # 5) Omitted complementizer / embedded subject recovery.
    for i,t in enumerate(doc[:-1]):
        if t.dep_.lower() in OBJECT_DEPS and t.pos_ in NOMINAL_POS:
            nxt = doc[i+1]
            if (neural_roles[i] != 'O'
                    and (nxt.pos_ == 'AUX' or nxt.lower_ in AUX_WORDS)
                    and t.head.lemma_.lower() in CLAUSAL_COMPLEMENT_VERBS):
                out[i] = 'S'; reason[i] = 'clausal-object-before-aux-subject'
            elif neural_roles[i] != 'O' and t.head.pos_ == 'ADJ':
                out[i] = 'S'; reason[i] = 'object-of-adjective-subject-repair'

    # 6) Subject-auxiliary inversion repair.
    for i,t in enumerate(doc):
        if (t.dep_.lower() in {'dobj','obj'} and t.pos_ in NOMINAL_POS
                and t.head.i <= 2 and i > t.head.i
                and (t.head.pos_ == 'AUX' or t.head.lower_ in AUX_WORDS)
                and not _has_subject_before(doc, i)):
            out[i] = 'S'; reason[i] = 'initial-aux-inversion'

    # 7) Compound-to-predicate recovery.
    for i,t in enumerate(doc):
        if t.dep_.lower() != 'compound' or t.pos_ not in {'NOUN','PROPN','PRON'} or i >= t.head.i:
            continue
        if t.head.pos_ in {'VERB','AUX'}:
            out[i] = 'S'; reason[i] = 'compound-to-verb-subject-repair'
        elif neural_roles[t.head.i] == 'V' and t.head.i == i + 1:
            out[i] = 'S'; reason[i] = 'compound-to-neural-predicate-subject'
            out[t.head.i] = 'V'; reason[t.head.i] = 'neural-predicate-pos-repair'
        elif (t.head.i == i + 1 and t.head.pos_ == 'NOUN'
                and t.head.dep_.lower() == 'ccomp' and _has_left_clause_marker(doc, i)):
            out[i] = 'S'; reason[i] = 'compound-to-mistagged-ccomp-subject'
            out[t.head.i] = 'V'; reason[t.head.i] = 'mistagged-ccomp-predicate'

    # 8) Partitive quantified subjects.
    if len(doc) >= 3 and doc[0].lower_ in PARTITIVE_SUBJECTS and doc[1].lower_ == 'of':
        out[0] = 'S'; reason[0] = 'initial-partitive-subject'

    # 9) Correlative subject beginning with Neither/Either.
    if len(doc) and doc[0].lower_ in {'neither','either'}:
        stopper = 'nor' if doc[0].lower_ == 'neither' else 'or'
        stop = next((j for j,t in enumerate(doc) if t.lower_ == stopper), len(doc))
        for i in range(1, stop):
            if doc[i].pos_ in {'NOUN','PROPN','PRON'} and doc[i].dep_.lower() in {'root','pobj','dobj','obj'}:
                out[i] = 'S'; reason[i] = 'correlative-subject-repair'; break

    # 10) Clausal preposition subject recovery.
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

    # 11) Existential lexical predicates such as remain/appear.
    for i,t in enumerate(doc):
        if t.dep_.lower() == 'attr' and t.head.lemma_.lower() != 'be':
            if any(x.dep_.lower() == 'expl' and x.head.i == t.head.i for x in doc):
                out[i] = 'S'; reason[i] = 'lexical-existential-postverbal-subject'

    # 12) Garden-path recovery inside a relative clause.
    for i,t in enumerate(doc):
        if (i > 0 and t.dep_.lower() in SUBJECT_DEPS and t.pos_ == 'PRON'
                and neural_roles[i] == 'O' and t.head.i > i):
            prev = doc[i-1]
            if prev.pos_ == 'VERB' and prev.dep_.lower() in {'relcl','acl'}:
                out[i] = 'O'; reason[i] = 'relative-verb-object-recovery'

    # 13) Fronted Between-PP followed by existential there.
    if len(doc) and doc[0].lower_ == 'between':
        there_i = next((i for i,t in enumerate(doc) if t.lower_ == 'there' and t.dep_.lower() == 'expl'), None)
        if there_i is not None:
            for i,t in enumerate(doc[:there_i]):
                dep=t.dep_.lower()
                if dep == 'pobj' and t.head.lower_ == 'between':
                    out[i]='M'; reason[i]='fronted-between-pp'
                elif dep == 'nsubj' and t.head.i > there_i:
                    out[i]='M'; reason[i]='fronted-between-pp-repair'
            for i,t in enumerate(doc[:there_i]):
                if t.dep_.lower() == 'conj' and t.head.i < there_i and out[t.head.i] == 'M':
                    out[i]='M'; reason[i]='fronted-between-conj'

    # 14) Emphatic direct WH copular questions, e.g. "What the hell was that?".
    # Treat only established filler idioms as M so ordinary phrases such as
    # "What color was the car?" are not collapsed incorrectly.
    if len(doc) >= 4 and doc[0].lower_ in WH_NOMINALS:
        cop_i = next((
            i for i,t in enumerate(doc[1:],1)
            if t.lemma_.lower() == 'be' and t.pos_ in {'AUX','VERB'}
        ), None)
        if cop_i is not None and cop_i > 1:
            filler = tuple(t.lower_ for t in doc[1:cop_i] if not t.is_punct)
            if filler in EMPHATIC_WH_FILLERS:
                out[0] = 'C'; reason[0] = 'emphatic-wh-copular-complement'
                for j in range(1, cop_i):
                    if not doc[j].is_punct:
                        out[j] = 'M'; reason[j] = 'emphatic-wh-filler'
                out[cop_i] = 'V'; reason[cop_i] = 'emphatic-wh-copula'
                for j in range(cop_i + 1, len(doc)):
                    if doc[j].is_punct:
                        break
                    if doc[j].pos_ in NOMINAL_POS or doc[j].lower_ in DEMONSTRATIVE_PRONOUNS:
                        out[j] = 'S'; reason[j] = 'emphatic-wh-postcopular-subject'
                        break

    # 15) Colloquial approximate percentage objects:
    # "I used like/about 5% of my power."  spaCy commonly parses the percentage
    # under the approximator as a pobj, which would otherwise erase the direct
    # object. Under the school-head spec the percentage head (%) is O and the
    # numeral / of-PP material remains M.
    for vi,t in enumerate(doc):
        if t.pos_ != 'VERB' or t.lemma_.lower() == 'be':
            continue
        j = vi + 1
        while j < len(doc) and not doc[j].is_punct and (
            doc[j].pos_ in {'ADV','PART'} or doc[j].lower_ in {'only','just'}
        ):
            j += 1
        if j < len(doc) and doc[j].lower_ in APPROX_PERCENT_MARKERS:
            j += 1
        if j + 1 >= len(doc) or doc[j].is_punct:
            continue
        if doc[j].pos_ == 'NUM' and doc[j + 1].text == '%':
            out[j] = 'M'; reason[j] = 'percentage-number-modifier'
            out[j + 1] = 'O'; reason[j + 1] = 'approx-percentage-object'

    # 16) Conservative coordination inheritance.
    # Only copy an explicit subject/object role from a nominal head to a nominal
    # conjunct. Broad C/M inheritance caused false positives such as
    # "a need or a want", "you or anything", and "one or the other".
    for _ in range(3):
        changed=False
        for i,t in enumerate(doc):
            if t.dep_.lower() != 'conj' or t.pos_ not in {'NOUN','PROPN'}:
                continue
            head=t.head
            hdep=head.dep_.lower()
            if hdep in SUBJECT_DEPS:
                hr='S'
            elif hdep in OBJECT_DEPS:
                hr='O'
            else:
                continue
            # Respect earlier, higher-priority repairs. Coordination may inherit
            # a core role only when the postprocessed head still carries it.
            # This prevents a repaired M head inside fronted/PP material from
            # being re-expanded back into S/O by the final coordination pass.
            if out[head.i] != hr:
                continue
            if out[i] != hr:
                out[i]=hr; reason[i]='conj-inherit-explicit-core'; changed=True
        if not changed:
            break

    return out, reason
