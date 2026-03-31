# Repository-wide model instructions

This repository is a continuously evolving human–model workshop.

Do not interpret it file-first.

Never treat a single file, README fragment, workflow slice, or isolated artifact
as the full reference frame of the repository.

Always begin from the field, then descend to local files.

## Field-first interpretation order

When ambiguity exists, interpret in this order:

1. repository purpose
2. normative contract layer
3. authority boundaries
4. workflow / CI enforcement behavior
5. artifact semantics in context
6. local file role
7. local file contents
8. README or explanatory prose

Lower layers must not redefine higher layers by implication.

## Required classification before interpretation

Before proposing any explanation, review, or fix, first determine whether the
target is:

- normative
- diagnostic
- explanatory
- archival
- shadow-only

Do not interpret a file before this classification is made.

## Local-file limitation

A local file may describe:

- a local mechanism
- a partial workflow step
- a helper process
- a documentation slice
- a renderer
- an export path

A local file must not be assumed to define:

- full repository meaning
- global policy
- full authority
- total release semantics

unless the repository field explicitly gives it that role.

## Prohibited inference

Do not make this inference:

> this file says X, therefore the repository means X

Also avoid:

- inferring global policy from a README paragraph
- inferring authority from artifact proximity
- inferring release semantics from diagnostic output
- inferring repository intent from one implementation file
- inferring system-level meaning from one workflow step

## Repair rule

When mismatch appears between files, docs, workflow behavior, or artifacts:

Do not repair one local file against another local file in isolation.

Instead:

1. identify the field role of the artifact
2. identify whether it is normative or diagnostic
3. identify the authority layer involved
4. determine whether the mismatch is:
   - local drift
   - field evolution
   - enforcement gap
   - explanatory lag
5. repair at the authoritative layer first

Compensating lower-layer edits are not the primary repair method.

## Stabilization rule

When the repository is stabilizing a base version, prioritize:

1. field coherence
2. authority-level repair
3. stable-base construction
4. non-circular correction

Do not create circular repair by aligning code, docs, or workflow fragments to
one another without first resolving the field-level meaning.

## Workflow caution

When editing workflows:

- prefer one authoritative release-context over repeated local re-derivation
- avoid duplicating release logic across multiple branches unless intentional
- stabilize the reference frame first, then reapply the intended behavior
- do not introduce local fixes that shift release meaning by accident

## Practical summary

Field first.
Role second.
Authority third.
File fourth.

Never whole-from-part by isolation.
Never authority-from-proximity.
Never policy-from-fragment.
Never release-semantics-from-diagnostic output.

This repository must be interpreted from the field.
