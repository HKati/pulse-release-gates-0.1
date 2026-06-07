# PULSE Mechanical Transition Language v0

## Status

This document defines a repository-facing wording, reading, and review convention for PULSE materials.

It is non-normative. It does not define, change, replace, or override the PULSEmech release-authority path.

## Purpose

PULSE terminology must preserve the mechanical transition it represents.

PULSE materials must not reduce PULSEmech to isolated category labels, framework labels, governance labels, evaluation labels, CI labels, dashboard labels, or process labels when describing release-authority behavior.

The purpose of this rule is to keep PULSE wording aligned with the operational data path that produces a pre-deployment allow/block AI release decision.

## Scope

This rule applies to PULSE-facing language in:

- README files
- repository summaries
- documentation pages
- release-facing descriptions
- external verification packets
- publication drafts
- reviewer-facing explanations
- model, Codex, and Pro handoff materials
- future PULSE-COMPUTE documents
- future field-library, storage, routing, review, and diagnostic materials

## Core Rule

PULSE language is mechanical transition language.

A PULSE controlled term is not treated as a label alone.

A PULSE controlled term must preserve its operational role inside a visible transition path.

A PULSE statement is preferred when it exposes:

source state  
→ mapped artifact or state  
→ declared policy relation  
→ workflow-effective gate state  
→ enforcement path  
→ decision consequence

## Reference PULSEmech Data Path

The PULSEmech data path is:

**recorded release evidence → status.json → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement → pre-deployment allow/block AI release decision**

This path is the reference transition structure for PULSEmech wording.

PULSE materials should preserve this operational sequence when describing release-authority behavior.

## Canonical PULSEmech Sentence

PULSEmech maps recorded release evidence into `status.json`, materializes the workflow-effective required gate set from a declared gate policy, and enforces the resulting gate state through strict fail-closed CI into a pre-deployment allow/block AI release decision.

## Controlled-Term Requirement

Each PULSE controlled term must preserve its mechanical role.

A term is complete when the following are identifiable:

- input state
- transformation
- binding artifact or policy relation
- effective gate or decision state
- enforcement mechanism
- downstream consequence

Examples of PULSE controlled terms include:

- `PULSEmech`
- `status.json`
- declared gate policy
- workflow-effective materialized required gate set
- strict fail-closed CI
- Quality Ledger
- release-authority path
- release-authority artifact
- pre-deployment allow/block release decision

A term should be revised when it appears only as an isolated noun without its operational relation.

## Reader Instruction

PULSE materials must be read through the declared data path.

The primary interpretation path is:

evidence state  
→ artifact state  
→ policy state  
→ materialized gate state  
→ CI enforcement state  
→ release decision state

External category labels may be used only when they do not replace or obscure the PULSEmech transition path.

## Writing Instruction

PULSE text should prefer transition-bearing sentences.

Preferred structures:

**X maps into Y under Z and is enforced by W into decision state D.**

**X is recorded as Y, bound by Z, materialized as W, and enforced into D.**

**Evidence state becomes artifact state; declared policy materializes required gates; fail-closed CI enforces the resulting gate state into a pre-deployment allow/block AI release decision.**

## Review Rule

During review, PULSE statements must be checked for visible transition structure.

A sentence should be revised when it presents key PULSE terms only as isolated nouns without showing their operational relation.

Review checklist:

- Does the sentence show the source state?
- Does it show the artifact or state transformation?
- Does it show the policy relation?
- Does it show the materialized gate state?
- Does it show the enforcement path?
- Does it show the allow/block consequence?

## Repository Rule

Repository-facing PULSE language must preserve the mechanical data path before adding summary language.

The canonical PULSEmech data path has priority over category labels, shorthand descriptions, and external framing terms.

The reference path is:

**recorded release evidence → status.json → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement → pre-deployment allow/block AI release decision**

## Boundary Rule

PULSEmech remains the release-authority path.

Future diagnostic, compute, storage, routing, review, or field-library layers may reference this path, but must not replace, weaken, or alter the PULSEmech release-authority data path.

Future layers must state their relation to PULSEmech without redefining the canonical release-authority path.

Reader surfaces, diagnostic views, review packs, dashboards, summaries, ledgers, and field documents are not release authority unless they are recorded as release evidence, represented in `status.json`, selected by declared gate policy, materialized into the workflow-effective required gate set, and enforced through strict fail-closed CI.

## Misread Prevention Rule

PULSE must not be reduced to a pre-existing category by similarity alone.

When a PULSE statement can be read as a generic framework, governance process, evaluation layer, dashboard, checklist, CI utility, or compliance wrapper, the statement should be revised to expose the PULSEmech data path.

The correction method is not additional explanation.

The correction method is restoration of the transition path.

## Minimal Anchor

PULSE language is transition-bearing.

The term is not a label alone.

The correct PULSE sentence exposes the data path.

The reference PULSEmech path is:

**recorded release evidence → status.json → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement → pre-deployment allow/block AI release decision**

