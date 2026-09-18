# SentenceLab Canonical Role Label Specification v1

Legacy status: **frozen phrase-propagation specification**. Current training/inference uses `role_label_spec_v2.md` (school-head). Do not mix v1 and v2 metrics.

Status: **normative for new Rooping data and converters**.

This document defines the token-level grammatical roles used by SentenceLab. Source corpora such as UD, MASC, parser-assisted data, and generated DSL data must map into this specification before they may be used as supervised S/V/O/C/M training data.

## Label set

| Label | Meaning | Core rule |
|---|---|---|
| `S` | Subject phrase | Surface grammatical subject of its own clause, including passive, expletive, raising, relative/WH subjects. |
| `V` | Verbal predicate | Every lexical `VERB` and grammatical `AUX` token that belongs to a predicate chain. |
| `O` | Object phrase | Direct/indirect object or surface object-like argument selected by a predicate. |
| `C` | Complement/predicative phrase | Subject complement, object complement, resultative, or non-verbal predicative xcomp/small-clause predicate. |
| `M` | Modifier/function material | Adverbials, PP material, complementizers, discourse markers, clause linkers, infinitival `to`, parentheticals, and remaining non-core material. |
| `null` | Not scored as a role | Punctuation only. |
| `AMBIG` | Preprocessing sentinel only | Unresolved source mapping. **Never a training target.** |

## General principles

1. **Clause-local roles.** Every embedded clause gets its own S/V/O/C/M analysis. A matrix-clause object relation must not overwrite the internal roles of tokens inside an embedded clause.
2. **Surface syntax over semantics.** These are grammatical roles, not PropBank semantic arguments. Do not map `ARG0 -> S` or `ARG1 -> O` mechanically.
3. **Phrase propagation is allowed only inside the phrase.** Determiners, attributive adjectives, compounds, names, possessives, and tightly attached nominal modifiers inherit the S/O/C role of their phrase head. Propagation stops at a new clause boundary.
4. **Verbs override phrase propagation.** A token tagged `VERB` or `AUX` is `V` even when it occurs inside an S/O/C constituent.
5. **Punctuation is always `null`.**
6. **Uncertain conversions are excluded, not guessed.** A source construction that cannot be deterministically mapped becomes `AMBIG` and is removed from supervised training until audited.

## V — predicate rules

### V001 — lexical verb
Any lexical `VERB` functioning as a predicate is `V`.

Examples: `reviewed`, `rewrite`, `arguing`, `find`, `seemed`, `know`.

### V002 — auxiliary chain
Every grammatical auxiliary in a predicate chain is also `V`.

Example: `had been questioned` -> `had/V been/V questioned/V`.

### V003 — infinitival marker
Infinitival `to` is **not** `V`; it is `M`.

Example: `wanted to know` -> `wanted/V to/M know/V`.

### V004 — participial clause predicate
A participle that heads a reduced/participial clause is `V`.

Example: `Having reviewed the report` -> `Having/M reviewed/V ...`.

## S — subject rules

### S001 — ordinary subject
The full surface subject NP is `S`.

Example: `the exhausted interns rewrote it` -> `the/S exhausted/S interns/S`.

### S002 — passive subject
The grammatical subject of a passive clause remains `S`; the `by` phrase is not converted to `S`.

Example: `the report was revised by the analyst` -> `the/S report/S was/V revised/V by/M the/M analyst/M`.

### S003 — expletive subject
Surface expletives such as `it` and `there` are `S` when they occupy the grammatical subject slot.

### S004 — raising subject
A raised surface subject is `S` in the clause where it surfaces.

Example: `the estimate seemed to be wrong` -> subject NP `S`; `seemed/V to/M be/V wrong/C`.

### S005 — relative/WH subject
A relative or interrogative pronoun functioning as the subject is `S`.

Example: `the analyst who revised it` -> `who/S revised/V it/O`.

## O — object rules

### O001 — direct object
The full direct-object phrase is `O`.

### O002 — indirect object
An indirect object without a preposition is `O`.

### O003 — relative/WH object
A relative/interrogative pronoun functioning as an object is `O`.

Example: `which the committee tested` -> `which/O the/S committee/S tested/V`.

### O004 — causative object
In causatives such as `made the interns rewrite the report`, `the interns` is `O` of `made`; the embedded lexical verb remains `V`, and its own object is `O`.

### O005 — clausal complements
Do **not** propagate `O` across an entire finite/non-finite clause. Complementizers are `M`, and internal tokens receive their own clause-local labels.

Example: `she knew that the report failed` -> `she/S knew/V that/M the/S report/S failed/V`.

## C — complement rules

### C001 — copular subject complement
A non-verbal predicate complement licensed by a copula is `C`.

Examples: `was reliable`, `became a problem`, `is the best option`.

### C002 — object complement
A secondary predicate describing an object is `C`.

Example: `they found the report unreliable` -> `they/S found/V the/O report/O unreliable/C`.

### C003 — resultative
A result-state predicate is `C`.

Example: `painted the door red` -> `door/O red/C`.

### C004 — nominal/adjectival xcomp
A non-verbal open complement functioning predicatively is `C`.

### C005 — verbal xcomp
A verbal xcomp is **V**, not `C`.

Example: `made him leave` -> `made/V him/O leave/V`.

## M — modifier/function rules

### M001 — adverbial
Adverbs and adverbial phrases not functioning as C are `M`.

### M002 — PP
Prepositions and ordinary PP complements are `M` unless the PP is explicitly part of a canonical predicative complement construction audited as C.

### M003 — clause linker/complementizer
`that`, `whether`, `if`, `because`, `although`, `while`, `unless`, coordinating conjunctions, and similar linkers are `M`.

### M004 — adjunct WH
Adjunct WH forms such as `why` and `how` are `M` when they are not S/O.

### M005 — parenthetical/discourse
Parenthetical phrases, appositives used as discourse insertions, and discourse markers default to `M` unless they independently form a clause with core roles.

## Clause boundaries

Role propagation must stop before crossing any new-clause boundary. Source-specific converters must treat at least these UD relations as boundaries when propagating phrase labels:

- `acl`
- `acl:relcl`
- `advcl`
- `ccomp`
- `xcomp`
- `parataxis`

A boundary does **not** imply that all boundary-head tokens are M. The embedded predicate is still V and its internal arguments are labeled independently.

## Relative clauses and gaps

1. Label the overt relative token according to its surface role: `who/S`, `which/O`, etc.
2. Do not invent a separate hidden-gap token.
3. The antecedent NP keeps its matrix-clause role.
4. Internal relative-clause S/V/O/C/M labels are clause-local.

## Coordination

1. Each conjunct receives the grammatical role it realizes in its clause.
2. Coordinating conjunctions are `M`.
3. Shared dependents must not cause role propagation through a full coordinated clause.
4. If a source annotation does not provide enough structure to determine the role of a conjunct, mark it `AMBIG` rather than guessing.

## Span policy

When a nominal/adjectival phrase is deterministically S/O/C, the following tightly attached tokens may inherit the phrase role:

- determiners
- attributive adjectives
- compounds
- flat/name/title elements
- possessive markers and possessive nominals when structurally internal to the phrase

Do not propagate through:

- finite or non-finite clauses
- relative clauses
- adverbial clauses
- parataxis
- verbal predicates
- punctuation

## Canonical examples

### Example 1 — causative + object complement
`The manager made the interns rewrite the report and found the result unacceptable.`

Expected core labels:

`The/S manager/S made/V the/O interns/O rewrite/V the/O report/O and/M found/V the/O result/O unacceptable/C ./null`

### Example 2 — passive + relative clause
`The report which the analyst revised was approved by the committee.`

Expected core labels:

`The/S report/S which/O the/S analyst/S revised/V was/V approved/V by/M the/M committee/M ./null`

### Example 3 — indirect WH
`She asked why the schedule had changed.`

Expected core labels:

`She/S asked/V why/M the/S schedule/S had/V changed/V ./null`

### Example 4 — copular complement
`The estimate was surprisingly unreliable.`

Expected core labels:

`The/S estimate/S was/V surprisingly/M unreliable/C ./null`

## Source conversion policy

Every converted token should carry provenance during dataset construction:

```json
{
  "token": "report",
  "source_relation": "obj",
  "source_head": 7,
  "canonical_role": "O",
  "rule_id": "O001",
  "label_source": "ud_gold",
  "review_status": "auto_pass"
}
```

Allowed `review_status` values:

- `auto_pass`
- `human_pass`
- `needs_review`
- `excluded`

`needs_review`/`AMBIG` items are never included in supervised role loss.

## Versioning rule

Any future change to the meaning of S/V/O/C/M requires a new specification version. Existing frozen evaluation sets keep the specification version under which their Gold labels were created, and results from different specifications must not be silently combined.
