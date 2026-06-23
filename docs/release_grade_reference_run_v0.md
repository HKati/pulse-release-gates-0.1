# Release-grade reference run v0

## Purpose

This document defines what counts as a PULSE release-grade reference run.

A release-grade reference run is a documented, reproducible run that exercises
the release-grade evidence path rather than the minimal Core smoke path.

Its purpose is to demonstrate the complete release-grade evidence-to-decision path:

```text
recorded current-run release evidence
→ non-stubbed candidate release state
→ canonical candidate production
→ canonical candidate replay
→ recorded release-evidence verification
→ canonical verifier replay
→ policy-derived release-required gate materialization
→ final status.json
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block release decision
```

The Quality Ledger, `release_authority_v0.json`, audit bundles, reference-run notes, Pages, dashboards, and publication artifacts preserve review, provenance, trace, or publication state.

They do not independently produce release authority.

This document is an operational reference.

It does not change release semantics, gate policy, status.json semantics,
check_gates.py behavior, primary release-decision authority, or shadow-layer
authority.

## Status

- stage: implemented release-grade evidence path; first completed public reference run pending
- normative: false
- target lane: release-grade
- authority role: documentation / operational guidance
- current-run required-gate evidence production: implemented
- non-stubbed release candidate status production: implemented
- canonical recorded-release candidate production: implemented
- canonical candidate replay: implemented
- recorded release-evidence verifier: implemented
- canonical verifier replay before materialization: implemented
- policy-derived release-required materialization: implemented
- external-summary schema validation: implemented
- external-summary semantic validation: implemented
- signer-policy admission: implemented
- cryptographic GitHub attestation verification: implemented
- exact operational release-grade signer identity: pending
- current-run attested external-evidence production lane: pending
- first completed public non-stubbed release-grade run record: pending
- qualification checker: `PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py`
- recorded evidence verifier: `PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py`
- release-required materializer: `PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py`
- release evaluator: `PULSE_safe_pack_v0/tools/check_gates.py`
- primary workflow advisory qualification: present
- qualification authority role: non-normative / non-blocking

The verifier-backed fold-in path is implemented.

Candidate evidence cannot authorize itself through local presence, a trusted-producer declaration, or a supplied verifier report.

The implemented admission path requires canonical candidate replay, recorded-evidence verification, canonical verifier replay, and atomic policy-derived release-required materialization before final gate enforcement.

External release-grade evidence must pass canonical schema and semantic validation, signer-policy admission, subject and digest binding, and cryptographic attestation verification.

The remaining operational objective is to produce current-run attested external evidence under an exact signer identity and execute the first completed public non-stubbed release-grade reference run.

The reference-run definition does not create a new gate and does not promote any verifier, materializer, diagnostic, reader, audit, or publication surface into independent release authority.

---

---

## Core smoke vs release-grade reference

PULSE intentionally separates the smaller Core lane from release-grade runs.

### Core lane

The Core lane is the minimal deterministic integration path.

It is useful for:

- first integration  
- local artifact inspection  
- baseline CI wiring  
 - validating the basic release-authority path 
- proving the narrow core_required gate set  

A Core run may be enough to show that the basic PULSE machinery works.

A Core run is not automatically a full release-grade evidence reference.

### Release-grade reference run

A release-grade reference run exercises the stronger release path.

It should demonstrate:

- `metrics.run_mode = "prod"` or the documented release-grade mode for the lane  
- materialized required gate evidence  
- no stubbed gate surface  
- external detector evidence when release-required  
- effective enforcement of `required + release_required`  
- release-authority manifest generation  
- Quality Ledger output  
- audit bundle publication  
- clear artifact traceability  

In compact form:

```
Core lane = smallest deterministic release-authority lane
Release-grade reference = materialized evidence release lane
```

---

## Release-grade lane selection

A release-grade reference run should use one of the repository-supported
release-grade paths:

- version tag push: `v* / V*`  

or:

- `workflow_dispatch` with `strict_external_evidence=true`  

The workflow-effective release-grade enforce set is:

```
required + release_required
```

The exact materialized required gates must be derived from policy, not manually
copied into workflow logic.

---

## Required evidence properties

A release-grade reference run should satisfy the following evidence properties.

### 1. Materialized gates

The run must not rely on scaffolded or stubbed gate output.

Expected release-grade boundary:

```
gates.detectors_materialized_ok = true
diagnostics.gates_stubbed != true
```

If a release-grade run emits `diagnostics.gates_stubbed=true`, it is not a valid
release-grade reference run.

---

### 2. Verified external evidence

When strict external evidence is active, release-grade external evidence must be present and admitted through the canonical verification path.

Each contributing external summary must satisfy:

- canonical `external_summary_v1` schema validation;
- detector-specific metric identity;
- declared threshold reference and comparator semantics;
- literal `result.passed = true`;
- repository, subject, commit, run, and release-candidate binding;
- canonical repo-relative evidence paths;
- raw-evidence and summary digest binding;
- exact release-grade signer-policy admission;
- a cryptographic attestation bundle;
- successful independent attestation verification;
- canonical candidate replay;
- recorded release-evidence verification.

Expected release-grade gate state:

```text
external_summaries_present = true
external_all_pass = true
```

when those gates are part of the active `release_required` set.

Canonical filename, JSON parseability, generic metric presence, self-declared verification, or digest recording alone do not establish release-grade external evidence.

Unsigned, unverified, stale, malformed, substituted, or mismatched external evidence must fail closed.

---

### 3. Required gates fail closed

All effective required gates must be present and literal boolean `true` to pass.

The release-grade path must preserve the PULSE rule:

```
literal true = PASS
false / null / missing / non-boolean = not PASS
```

---

### 4. Policy-derived gate set

The release-grade effective required gate set must be derived from
`pulse_gate_policy_v0.yml`.

The workflow must not silently hardcode a divergent release-grade gate list.

---

### 5. Status contract validation

The final `status.json` must validate against the committed status contract.

The release-grade reference run should archive the final validated `status.json`.

---

### 6. Release authority manifest

The run should produce:

```
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

The manifest must remain audit-only and non-normative.

It should record:

- run identity  
- input artifact hashes  
- policy set  
- workflow-effective required gates  
- required gate evaluation  
- decision state  
- diagnostic context  

---

### 7. Quality Ledger

The run should produce:

```
PULSE_safe_pack_v0/artifacts/report_card.html
```

The Quality Ledger should include the release authority manifest section when the
manifest is available.

The Ledger remains a reader / renderer surface.

---

### 8. Audit bundle

The run should publish the release authority audit bundle:

```
release-authority-audit-bundle
```

Current expected bundle contents:

- report_card.html  
- release_authority_v0.json  
- status.json  

The bundle is a review and traceability package, not a release-decision engine.

---

## Expected artifact set

A completed release-grade reference run should archive the complete reviewable evidence-to-decision chain.

### Current-run evidence and candidate state

```text
PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json
PULSE_safe_pack_v0/artifacts/status.json
PULSE_safe_pack_v0/artifacts/recorded_release_candidates/
PULSE_safe_pack_v0/artifacts/recorded_release_candidate_index_v0.json
```

### Verification and materialization inputs

```text
PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json
PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json
```

### External evidence, when required

```text
PULSE_safe_pack_v0/artifacts/external/*_summary.json
PULSE_safe_pack_v0/artifacts/external/*_summary.envelope.json
PULSE_safe_pack_v0/artifacts/external/*_summary.bundle.json
```

### Final release and review surfaces

```text
PULSE_safe_pack_v0/artifacts/status.json
PULSE_safe_pack_v0/artifacts/report_card.html
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
release-authority-audit-bundle
release-grade-reference-run-v0
```

### Optional CI exports

```text
reports/junit.xml
reports/sarif.json
```

Recommended review order:

1. current-run evidence and run identity;
2. candidate status and required-gate evidence;
3. canonical candidate set and candidate replay;
4. release-evidence input manifest;
5. recorded release-evidence verifier result;
6. canonical verifier replay and materialization result;
7. final `status.json`;
8. workflow-effective materialized required gate set;
9. `PULSE_safe_pack_v0/tools/check_gates.py` result;
10. primary CI allow/block decision;
11. release-authority manifest;
12. Quality Ledger;
13. release-authority audit and reference bundles.

---

## Release authority boundary

A release-grade reference run must preserve the complete PULSEmech authority boundary.

### Normative path

```text
recorded release evidence
→ final status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI workflow
→ primary CI allow/block release decision
```

### Evidence-admission and materialization layers

```text
candidate production
→ canonical candidate replay
→ recorded release-evidence verification
→ canonical verifier replay
→ release-required materialization
```

These layers determine whether candidate evidence may enter final release state.

They do not independently produce the release decision.

### Audit, review, and publication surfaces

- Quality Ledger
- verifier reports
- attestation reports
- `release_authority_v0.json`
- GitHub Step Summary
- release-authority artifacts
- audit bundles
- reference-run notes
- Pages and dashboards

These surfaces explain, verify, publish, preserve, or reconstruct the decision chain.

They must not recompute, replace, override, or silently reinterpret release authority.

---

## Acceptance criteria

A run can be called a completed release-grade reference run only if all of the following are true:

- the run uses a declared release-grade workflow path;
- `metrics.run_mode = "prod"`;
- the active policy set is `required + release_required`;
- the workflow-effective materialized required gate set is derived from declared policy;
- current-run required-gate evidence is present and identity-bound;
- the candidate release state is non-stubbed;
- stale candidate outputs were cleared before production;
- canonical candidate production succeeded;
- the supplied candidate set exactly matches canonical candidate replay;
- recorded release-evidence verification succeeded;
- the supplied verifier report exactly matches canonical verifier replay;
- release-required gates were materialized atomically from verifier-admitted evidence;
- the final `status.json` validates against the committed release-grade status contract;
- every workflow-effective required gate is present and literal `true`;
- `PULSE_safe_pack_v0/tools/check_gates.py` completed strict fail-closed enforcement;
- the primary CI allow/block result is recorded;
- required external evidence is present;
- required external evidence passed schema, semantic, signer, digest, subject, and cryptographic attestation verification;
- `release_authority_v0.json` was produced and validated;
- the Quality Ledger was generated from the final `status.json`;
- Quality Ledger / status parity passed;
- the release-authority audit bundle was produced;
- the release-grade reference bundle was produced;
- all diagnostic, verifier, audit, reader, and publication surfaces remained non-authoritative;
- the concrete run identity and artifact references were recorded in `docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md`.

---

## Qualification checker

The release-grade reference-run criteria are evaluated by:

```text
PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py
```

The checker determines whether a produced run satisfies the documented release-grade reference-run criteria.

It evaluates reference suitability.

It does not create or replace release authority.

The checker examines, among other things:

- `status.metrics.run_mode = "prod"`;
- absence of stubbed or scaffolded release evidence;
- materialized detector evidence;
- external-summary presence and pass gates when required;
- `required + release_required` policy-set representation;
- release-authority manifest presence and validation state;
- successful recorded decision state;
- optional Quality Ledger presence;
- optional audit-bundle contents.

The checker does not:

- produce current-run candidate evidence;
- admit candidate evidence;
- establish producer trust by declaration;
- replace canonical candidate replay;
- replace recorded release-evidence verification;
- replace canonical verifier replay;
- materialize `release_required` gates;
- replace `PULSE_safe_pack_v0/tools/check_gates.py`;
- change the primary CI allow/block release decision;
- promote verifier, reader, audit, or publication surfaces into authority.

Test coverage includes:

```text
tests/test_check_release_grade_reference_run_v0.py
tests/test_release_grade_reference_example_package.py
tests/test_release_grade_reference_qualification_advisory_boundary_v0.py
```

The checker is registered in:

```text
ci/tools-tests.list
```

### Workflow role

In the primary workflow, release-grade reference qualification is:

- advisory;
- non-normative;
- non-blocking;
- release-grade only.

A failed qualification may classify a run as unsuitable for use as the public reference run.

It does not reinterpret or override the underlying release decision.

### Authority rule

The normative release decision remains:

```text
recorded release evidence
→ final status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI workflow
→ primary CI allow/block release decision
```

The qualification role is:

```text
PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py
= non-authoritative release-grade reference qualification checker
```

The qualification checker answers:

```text
Does this produced run satisfy the documented release-grade reference-run criteria?
```

It does not answer:

```text
Should the primary CI workflow allow or block this release?
```

That decision remains with the canonical PULSEmech release-authority path.

A completed public release-grade reference-run record should be finalized only after the run satisfies the qualification criteria and its concrete artifact package is available for review.

---

## Primary workflow visibility

The primary PULSE workflow runs the release-grade reference qualification checker
as an advisory visibility step for release-grade runs.

Workflow surface:

```text
.github/workflows/pulse_ci.yml
```

The workflow step checks the candidate run using:

```text
PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py
```

and reports the result in the GitHub Step Summary.

This step is:

- advisory  
- non-normative  
- non-blocking  
- release-grade only  

If the checker fails, the workflow emits a warning and records the result as
Not qualified, but the normal release outcome is still determined by the
existing release-authority path:

```text
recorded release evidence
+ final status.json
+ declared gate policy
+ workflow-effective materialized required gate set
+ PULSE_safe_pack_v0/tools/check_gates.py
+ primary CI workflow
= primary CI allow/block release decision
```

The qualification step answers a different question:

Does this run satisfy the documented release-grade reference-run criteria?

It does not answer:

Should the primary CI workflow allow or block this release?

That decision remains with the normal PULSE release-authority path.

---

## Non-goals

A release-grade reference run is not:

- a new release policy  
- a new gate set
- a replacement for `PULSE_safe_pack_v0/tools/check_gates.py`
- a replacement for status.json  
- a dashboard-derived decision  
- a shadow-layer promotion  
- or a guarantee of external compliance certification  

It is a reproducible reference run that demonstrates the materialized
release-grade PULSE path.

---

## Reviewer checklist

When reviewing a candidate release-grade reference run, check:

- Which workflow path produced the run?  
- Was the run release-grade or only Core?  
- Which policy set was active?  
- What was the workflow-effective required gate set?  
- Were any required gates missing or non-true?  
- Was external evidence required?  
- Were external summaries present?  
- Was stubbed/scaffolded evidence absent from the release-grade path?                                           - Did canonical candidate replay exactly match the supplied candidate set?
- Did recorded release-evidence verification succeed?
- Did canonical verifier replay exactly match the supplied verifier report?
- Was release-required materialization atomic and policy-derived?
- Did required external evidence pass exact signer and cryptographic attestation verification?
- Did `PULSE_safe_pack_v0/tools/check_gates.py` enforce the exact workflow-effective materialized required gate set?
- Was the primary CI result recorded as allow or block? 
- Was `release_authority_v0.json` produced?  
- Did the manifest validate?  
- Did the Quality Ledger include the release authority section?  
- Was the audit bundle uploaded?  
- Did any diagnostic surface attempt to act as release authority?  

---

## Relation to public demo surfaces

Public Pages or demo surfaces may show Core or smoke-run state.

That is useful for visibility, but it should not be confused with a
release-grade reference run.

A release-grade reference run should be explicitly labeled and reviewed as such.

Recommended wording:

```
Core smoke surface = integration / visibility surface
Release-grade reference run = materialized evidence release-authority reference
```

---

## Next operational steps

The verifier, canonical replay, release-required materializer, qualification checker, and reference-run packaging path are implemented.

The next work is not to rebuild those layers.

The next operational sequence is:

1. replace deferred or wildcard release-grade signer identities with one exact operational workflow identity;
2. implement the current-run canonical external-evidence producer lane;
3. generate a cryptographic attestation bundle for the current-run external summary;
4. build the canonical external-summary envelope from the verified run identity and summary digest;
5. execute the controlled strict release-grade workflow;
6. preserve the complete current-run evidence, candidate, verifier, materialization, final-status, and CI decision chain;
7. publish the release-grade reference artifact bundle;
8. complete `docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md` with concrete run identity, artifact URLs, and SHA-256 digests;
9. link the completed public reference run from the README and documentation index;
10. use the completed run as the baseline for independent reproduction and later portability work.

The progression is:

```text
exact operational signer identity
→ current-run attested external evidence
→ controlled strict release-grade run
→ complete artifact bundle
→ completed public reference-run record
→ independent reproduction
