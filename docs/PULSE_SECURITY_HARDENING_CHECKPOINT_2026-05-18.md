# PULSE Security Hardening Checkpoint — 2026-05-18

Status: checkpoint  
Scope: release-authority / artifact-integrity hardening  
Authority status: non-normative documentation checkpoint

## Purpose

This checkpoint records the current PULSE security-hardening state after the first class-level fixes for release-authority and artifact-integrity findings.

It is not a release-decision artifact.

It does not authorize, block, override, or create release authority.

The normative PULSE release decision remains:

recorded release evidence
→ status.json
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI checking
→ CI allow/block release decision

## Core rule

PULSE hardening follows the pre-materialization rule:

unsupported evidence state
→ no release authority

Missing, malformed, stale, unsigned, unverified, stubbed, scaffolded, non-materialized, non-canonical, decoy, or otherwise unsupported evidence must not materialize into release permission.

## Closed class-level fixes

### 1. Release no-stub diagnostics boundary

Closed class:

missing / malformed no-stub diagnostics
→ no release authority

Implemented hardening:

- dedicated release no-stub guard;
- explicit release-grade status contract checks;
- `gates.detectors_materialized_ok` must be literal `true`;
- `diagnostics.gates_stubbed` must be literal `false`;
- `diagnostics.scaffold` must be literal `false`;
- malformed, absent, null, or non-object diagnostics fail closed.

Security class addressed:

- no-stub release guard accepting missing or malformed diagnostics.

### 2. Canonical external evidence boundary

Closed class:

decoy / non-canonical external summary
→ no release authority

Implemented hardening:

- strict external summary precheck uses canonical detector summary names by default;
- decoy files such as `foo_summary.json` or `foo_summary.jsonl` do not satisfy external evidence presence;
- generic metric-only summary files do not satisfy release-grade external evidence by default;
- explicit `--required` remains available only for explicitly named operator checks.

Security class addressed:

- release external evidence accepting spoofed summary files.

### 3. Folded detector evidence boundary

Closed class:

strict external evidence with no recognized folded detector result
→ no release authority

Implemented hardening:

- `augment_status.py` strict mode fails closed when no recognized detector summary is successfully folded;
- decoy-only, unrecognized-only, malformed-only, or no-folded-result external evidence states cannot produce `external_all_pass=true`;
- canonical detector summaries remain the release-relevant external evidence surface;
- generic `*_summary.json/jsonl` files remain diagnostic observations only.

Security class addressed:

- strict external evidence accepting decoy summaries.

### 4. RA1 malformed gate ID boundary

Closed class:

malformed / non-string RA1 gate ID
→ structured verifier FAIL
→ no crash

Implemented hardening:

- RA1 verifier validates gate ID arrays before cross-artifact operations;
- non-string, empty, malformed, duplicate, object, array, or null gate IDs fail closed;
- malformed gate IDs no longer reach membership, set, dict-key, or join operations unchecked;
- verifier writes a structured report and exits non-zero instead of crashing.

Security class addressed:

- malformed gate IDs crashing the RA1 package verifier.

## Current hardening model

The current hardening work is no longer handled as isolated findings.

Each security issue is mapped to a class-level invariant:

finding
→ failure class
→ invariant
→ regression test
→ checkpoint

This avoids linear patch drift.

## Closed invariants

The following invariants are now established:

- release-grade status must be explicit, materialized, and non-stubbed;
- release-required external evidence must be canonical by default;
- strict external evidence requires at least one recognized folded detector result;
- malformed RA1 gate IDs must fail closed before verifier operations;
- diagnostic, shadow, ledger, dashboard, manifest, audit-bundle, report, Pages, or publication surfaces do not create release authority unless explicitly routed through declared policy and enforced as required gates.

## Remaining open hardening classes

The next candidate hardening classes are:

### 1. Release-grade status contract closure

Goal:

release-grade status contract
→ explicit required diagnostics / detector materialization / non-stub state
→ schema / validator / workflow agreement

Reason:

The workflow guard now enforces explicit non-stub release-grade status. The next class-level closure is to ensure the status contract and validator surfaces carry the same release-grade expectation where appropriate.

### 2. Artifact and package digest consistency

Goal:

package manifest / digests / payload files
→ canonical paths
→ safe paths
→ digest consistency
→ no artifact substitution

Reason:

RA1 package integrity depends on all release-reference package files being canonical, regular, declared, digest-matched, and package-root-confined.

### 3. Publication snapshot consistency

Goal:

publication surfaces
→ trace / reader only
→ match CI outcome and release identity
→ no second release-decision path

Reason:

Publication pages, ledgers, badges, and snapshots must preserve the decision trail without becoming normative release engines.

### 4. Schema / sample / status drift closure

Goal:

schemas, samples, fixtures, and generated artifacts
→ no silent drift
→ explicit baseline update when policy changes

Reason:

Baseline and schema drift can weaken reproducibility and confuse release-authority interpretation.

### 5. Authority wording drift

Goal:

README / docs / maps
→ release-authority language remains stable
→ framework / dashboard / eval-only misread is prevented

Reason:

PULSE must remain legible as release-authority mechanics, not as a generic eval framework or dashboard surface.

## Non-normative surfaces

The following surfaces remain non-normative unless explicitly promoted by declared policy and enforced as required gates:

- Quality Ledger;
- dashboards;
- badges;
- Pages;
- release authority manifests;
- audit bundles;
- publication snapshots;
- reports;
- summaries;
- shadow overlays;
- EPF / Paradox / G-field / topology diagnostic layers;
- agent-generated review notes or plans.

These surfaces may preserve, explain, reconstruct, display, or audit release evidence.

They must not authorize, block, override, or create release authority by themselves.

## Next intended code target

Recommended next code target:

release-grade status contract closure

This should align the status contract / validator / release-grade path with the already hardened no-stub guard:

- release-grade diagnostics must be explicit;
- `diagnostics.gates_stubbed` must be literal `false`;
- `diagnostics.scaffold` must be literal `false`;
- `gates.detectors_materialized_ok` must be literal `true`;
- missing, malformed, or ambiguous release-grade status must fail closed.

## Checkpoint summary

Closed:

- missing / malformed diagnostics bypass;
- decoy external summary bypass;
- strict no-folded-detector external evidence bypass;
- malformed RA1 gate ID verifier crash.

Still open as class-level hardening work:

- release-grade status contract closure;
- artifact / package digest consistency closure;
- publication snapshot consistency closure;
- schema / sample / status drift closure;
- authority wording drift closure.

Core invariant:

unsupported evidence state
→ no release authority
