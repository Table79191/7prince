# SentenceLab Canonical Role Label Specification v2 — school-head

Status: **normative for current training, browser inference, and new converters**.

This version changes the span policy from v1 phrase propagation to school-style **head-only S/V/O/C** labels.

## Label set

- `S`: head token of a grammatical subject.
- `V`: every lexical verb and grammatical auxiliary in a predicate chain.
- `O`: head token of a direct/indirect object.
- `C`: head token of a subject/object complement or non-verbal predicative complement.
- `M`: modifiers/function material, including determiners, attributive adjectives, adpositions, complementizers, coordinators, infinitival `to`, adverbs, and non-head material inside an S/O/C phrase.
- `null`: punctuation.
- `AMBIG`: preprocessing sentinel; never a supervised target.

## Head-only span policy

Only the syntactic head carries S/O/C. Tightly attached phrase material does not inherit the role.

- `The/M exhausted/M interns/S worked/V ./null`
- `I/S use/V my/M 0.001/M %/M powers/O ./null`
- `The/M manager/S made/V the/M interns/O rewrite/V the/M report/O ./null`
- `The/M estimate/S was/V surprisingly/M unreliable/C ./null`

Verbal predicates remain `V` even when a source dependency relation also marks a clausal argument/complement.

## Clauses and coordination

Each clause receives its own S/V/O/C heads. Relative/WH tokens receive the role they realize in their own clause when determinable. Coordinators and complementizers are `M`. Do not propagate a core role through an entire coordinated phrase or clause.

When source structure is insufficient, emit `AMBIG` and exclude the sentence from supervised role loss.

## Data split rule

Official upstream train files may be used for fitting. Official dev files are validation-only. Official test files are never used for fitting or model selection. A test-only treebank remains evaluation-only.

## Versioning

Results labeled under v1 phrase propagation and v2 head-only semantics are not directly comparable and must not be silently combined.
