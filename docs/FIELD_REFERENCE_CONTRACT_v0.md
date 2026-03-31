# Field-Reference Contract v0

## Purpose

This contract prevents file-first interpretation drift in a continuously evolving repository.

No single file, README fragment, workflow slice, or isolated artifact SHALL be treated as the full reference frame of the repository.

Repository interpretation MUST begin from the field, and only then descend to local files.

This contract exists to prevent circular repair during stabilization work, especially when a repository is evolving while a stable base is being prepared for the next phase.

---

## Core Rule

Interpretation SHALL be field-first, role-aware, and file-second.

A local artifact is validly interpretable only relative to the repository field it belongs to.

---

## Repository Field

For interpretation purposes, the repository field consists of:

1. repository purpose
2. normative contracts
3. authority boundaries
4. workflow / CI enforcement behavior
5. artifact semantics
6. normative vs diagnostic separation
7. local file role within the whole system

No single file SHALL override field meaning by isolation.

---

## Precedence Order

When ambiguity exists, interpretation SHALL follow this order:

1. explicit repository purpose
2. normative contract files
3. authority-boundary statements
4. workflow / CI enforcement behavior
5. artifact meaning in context
6. local file role
7. local file contents
8. README prose or explanatory text

Lower layers SHALL NOT redefine higher layers by implication.

---

## Local File Rule

A file MAY describe:

- a local mechanism
- a partial workflow step
- a helper process
- a documentation slice
- a diagnostic renderer
- a supporting export path

A file SHALL NOT be assumed to describe:

- total repository meaning
- global policy
- full system authority
- full release semantics

unless the field explicitly declares that authority.

---

## Normative vs Diagnostic Rule

Before interpreting any file or artifact, the following MUST be decided:

- is it normative
- is it diagnostic
- is it explanatory
- is it archival
- is it shadow-only

No interpretation is valid before this classification is made.

---

## Prohibited Inference

The following inference is non-admissible:

> "this file says X, therefore the repository means X"

This is invalid unless field-level confirmation exists.

Likewise invalid:

- inferring global policy from a README paragraph
- inferring authority from artifact proximity
- inferring release semantics from diagnostic output
- inferring repository intent from a single implementation file
- inferring system-level meaning from a local workflow slice

---

## Field Binding Requirement

Any proposed interpretation of a local file MUST include explicit binding to:

- the repository-level purpose it serves
- the contract layer it belongs to
- whether it can affect release semantics
- whether it is authoritative or shadow-only
- what it is not allowed to redefine

If this binding is absent, the interpretation is incomplete.

---

## Review Rule

Review SHALL NOT ask only:

- "what does this file say?"

Review MUST ask first:

- "what field does this file belong to?"
- "what is this file allowed to mean?"
- "what is this file not allowed to redefine?"
- "is this normative, diagnostic, explanatory, archival, or shadow-only?"

Only then may local reading begin.

---

## Drift Resolution Rule

When mismatch appears between files, artifacts, docs, or workflow behavior, the first question is NOT which file is right in isolation.

The required sequence is:

1. identify the field role of the artifact
2. identify whether the artifact is normative or diagnostic
3. identify the authority layer involved
4. determine whether the mismatch is:
   - local drift
   - field evolution
   - enforcement gap
   - explanatory lag
5. repair at the authoritative layer first

Compensating lower-layer patches SHALL NOT be used as the primary repair method.

---

## Failure Mode

File-first reading produces circular repair:

1. local reading
2. local correction
3. field mismatch
4. compensating patch
5. repeated drift

This SHALL be treated as interpretation failure, not repository failure.

---

## Human–Model Workshop Rule

This repository is a human–machine workshop.

Models operating in this repository SHALL receive and follow field-first interpretation guidance.

Model assistance MUST NOT be anchored to a single file as if that file were the entire repository reference frame.

When the repository is in an active stabilization phase, model assistance SHALL prioritize:

1. field coherence
2. authority-level repair
3. stable-base construction
4. non-circular correction

This rule exists so that model participation strengthens repository stability instead of amplifying local drift.

---

## Operational Summary

Field first.  
Role second.  
Authority third.  
File fourth.

Never whole-from-part by isolation.  
Never authority-from-proximity.  
Never policy-from-fragment.  
Never release-semantics-from-diagnostic output.

Interpretation begins at the field.
