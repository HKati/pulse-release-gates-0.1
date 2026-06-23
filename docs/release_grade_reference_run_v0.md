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
- advisory qualification subset checker: implemented
- baseline reference-bundle assembly: implemented
- complete evidence-chain reference packaging: pending
- complete reference-package verification: pending
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

A completed release-grade reference run must archive the complete reviewable evidence-to-decision chain.

The list below defines the **target complete reference package**.

The current workflow implements baseline reference-bundle assembly, but it does not yet place every item below into the single `release-grade-reference-run-v0` artifact.

### Current-run evidence and pre-materialization candidate state

```text
PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json
PULSE_safe_pack_v0/artifacts/status_baseline.json
PULSE_safe_pack_v0/artifacts/recorded_release_candidates/
PULSE_safe_pack_v0/artifacts/recorded_release_candidate_index_v0.json
```

`status_baseline.json` is the preserved pre-materialization candidate state.

It must remain distinct from the final `status.json` written after release-required materialization.

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

### Final release state and decision trace

```text
PULSE_safe_pack_v0/artifacts/status.json
PULSE_safe_pack_v0/artifacts/release_decision_v0.json
PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
PULSE_safe_pack_v0/artifacts/report_card.html
```

`release_decision_v0.json` preserves the recorded release-level decision trace.

`artifact_provenance_binding_v0.json` binds the final status, policy, Ledger, release decision, and release-authority manifest into a digest-backed verification subject.

### Review and preservation bundles

```text
release-authority-audit-bundle
release-grade-reference-run-v0
```

For a completed public reference run, `release-grade-reference-run-v0` must contain the complete evidence-chain package defined in this section.

The current baseline bundle assembly is not yet sufficient for that completed-package claim.

### Optional CI exports

```text
reports/junit.xml
reports/sarif.json
```

Recommended review order:

1. current-run identity and required-gate evidence;
2. preserved pre-materialization `status_baseline.json`;
3. canonical candidate envelopes and candidate index;
4. release-evidence input manifest;
5. recorded release-evidence verifier report;
6. canonical candidate replay result;
7. canonical verifier replay and materialization result;
8. final `status.json`;
9. workflow-effective materialized required gate set;
10. `PULSE_safe_pack_v0/tools/check_gates.py` result;
11. `release_decision_v0.json`;
12. `artifact_provenance_binding_v0.json`;
13. `release_authority_v0.json`;
14. Quality Ledger;
15. release-authority audit bundle;
16. complete release-grade reference bundle.

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
- a complete release-grade reference bundle containing the full target artifact set was produced;
- complete package presence and binding were verified independently of the advisory qualification checker; 
- all diagnostic, verifier, audit, reader, and publication surfaces remained non-authoritative;
- the concrete run identity and artifact references were recorded in `docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md`.

These are the completion criteria for the full public reference run.

The current advisory qualification checker validates only a defined subset of these criteria.

A successful qualification-checker result is necessary for the current workflow path, but it is not sufficient by itself to prove that the complete reference package exists.

---

## Qualification checker

The advisory release-grade qualification checker is:

```text
PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py
```

The checker validates a defined operational subset of the release-grade reference-run criteria.

Its current direct inputs are:

```text
final status.json
release_authority_v0.json
optional report_card.html
optional release-authority audit-bundle directory
```

The checker directly evaluates, among other things:

- `status.metrics.run_mode = "prod"`;
- absence of stubbed or scaffolded release evidence;
- literal-true release-required gate markers in the final status;
- `required + release_required` policy-set representation in the authority manifest;
- release-required materialization state in the authority manifest;
- absence of missing or failed required gates recorded by the manifest;
- the recorded manifest decision state;
- optional Quality Ledger presence;
- the baseline audit-bundle contents currently expected by the checker.

The checker does **not** currently consume or verify:

- `required_gate_evidence_v0.json`;
- `status_baseline.json`;
- the recorded-release candidate directory;
- the recorded-release candidate index;
- `release_evidence_input_manifest_v0.json`;
- `recorded_release_evidence_verifier_v0.json`;
- canonical candidate replay directly;
- canonical verifier replay directly;
- external-summary envelopes;
- cryptographic attestation bundles;
- `release_decision_v0.json`;
- `artifact_provenance_binding_v0.json`;
- the complete `release-grade-reference-run-v0` package.

Therefore:

```text
qualification checker OK
≠ complete reference-package verification
```

A successful checker result means that the current status/manifest/reference-surface subset satisfies the implemented advisory qualification checks.

It does not prove by itself that every completed-run acceptance criterion in this document has been satisfied.

The checker does not:

- produce current-run candidate evidence;
- admit candidate evidence;
- establish producer trust by declaration;
- replace canonical candidate replay;
- replace recorded release-evidence verification;
- replace canonical verifier replay;
- materialize `release_required` gates;
- replace `PULSE_safe_pack_v0/tools/check_gates.py`;
- verify the full reference package;
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

In the primary workflow, the current qualification step is:

- advisory;
- non-normative;
- non-blocking;
- release-grade only;
- limited to the checker's declared input subset.

A failed qualification may classify a run as unsuitable for use as the public reference run.

A successful qualification does not by itself classify an incomplete artifact package as a completed public reference run.

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
= non-authoritative subset qualification checker
```

The checker answers:

```text
Does the supplied final status, authority manifest, and optional reader/audit subset satisfy the implemented qualification checks?
```

It does not answer:

```text
Is the complete release-grade evidence-chain package present and independently reproducible?
```

It also does not answer:

```text
Should the primary CI workflow allow or block this release?
```

The first question requires complete-package verification.

The second remains with the canonical PULSEmech release-authority path.

A completed public release-grade reference-run record may be finalized only after:

- the advisory qualification subset passes;
- the complete target artifact package exists;
- the package's decision and provenance bindings are verified;
- its concrete artifacts are available for review.

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

When reviewing a candidate release-grade reference run, check the complete evidence-to-decision chain.

### 1. Run and lane identity

- Which workflow path produced the run?
- Was the run release-grade rather than only Core?
- Did `metrics.run_mode` equal `prod`?
- Was the active policy set `required + release_required`?
- Were repository, commit, run key, and release-candidate identities concrete and consistent?
- Was the workflow-effective materialized required gate set derived from declared policy?

### 2. Current-run evidence and candidate state

- Was `required_gate_evidence_v0.json` produced from the current run?
- Was current-run evidence bound to the repository, commit, run key, and release candidate?
- Was stale candidate output removed before production?
- Was stubbed or scaffolded evidence absent?
- Was the pre-materialization candidate state preserved as `status_baseline.json`?
- Was `status_baseline.json` kept distinct from the final `status.json`?
- Were the recorded-release candidate envelopes preserved?
- Was `recorded_release_candidate_index_v0.json` preserved?
- Did the supplied candidate set exactly match canonical candidate replay?
- Were missing, extra, modified, or substituted candidates rejected?

### 3. Recorded evidence verification

- Was `release_evidence_input_manifest_v0.json` produced?
- Was the manifest bound to the current policy and registry digests?
- Did recorded release-evidence verification succeed?
- Was `recorded_release_evidence_verifier_v0.json` preserved?
- Did the supplied verifier report exactly match canonical verifier replay?
- Were evidence-result and relation-binding result sets non-empty?
- Were all required evidence items verified?
- Were all required relation bindings satisfied?
- Was every release-required gate explicitly admissible?
- Was self-declared producer trust rejected unless confirmed by canonical replay?

### 4. External evidence

- Was external evidence required for the selected lane?
- Were all required external summaries present?
- Did each external summary pass canonical schema validation?
- Did each external summary pass detector-specific semantic validation?
- Was the signer identity exact and permitted by signer policy?
- Was the external-summary envelope present?
- Was the summary digest bound to the envelope?
- Was the raw-evidence digest verified?
- Was the cryptographic attestation bundle present?
- Did independent cryptographic attestation verification succeed?
- Were repository, subject, commit, run, and release-candidate bindings verified?
- Were unsigned, stale, malformed, substituted, or mismatched summaries rejected?

### 5. Materialization and final release state

- Was release-required materialization policy-derived?
- Was release-required materialization atomic?
- Did failed admission leave the candidate state unmodified?
- Was the final `status.json` produced only after successful verifier replay?
- Did the final `status.json` validate against the release-grade status contract?
- Was every gate in the workflow-effective materialized required gate set present?
- Was every required gate literal `true`?
- Did `PULSE_safe_pack_v0/tools/check_gates.py` enforce the exact workflow-effective materialized required gate set?
- Was the primary CI result recorded as `allow` or `block`?

### 6. Decision and provenance artifacts

- Was `release_decision_v0.json` produced?
- Does `release_decision_v0.json` preserve the release-level decision trace?
- Was `artifact_provenance_binding_v0.json` produced?
- Was `artifact_provenance_binding_v0.json` independently verified?
- Does the provenance binding cover the final status, policy, Quality Ledger, release decision, and release-authority manifest?
- Was `release_authority_v0.json` produced?
- Did the release-authority manifest validate?
- Did all decision and binding artifacts refer to the same run and final status?

### 7. Reader and audit surfaces

- Was the Quality Ledger generated from the final `status.json`?
- Did Quality Ledger / status parity pass?
- Did the Quality Ledger remain a non-authorizing reader surface?
- Was the release-authority audit bundle produced?
- Did the audit bundle contain its required baseline artifacts?
- Did any dashboard, Pages surface, report, manifest, or audit sidecar attempt to act as independent release authority?

### 8. Complete reference package

- Was the complete `release-grade-reference-run-v0` bundle produced?
- Did it contain `required_gate_evidence_v0.json`?
- Did it contain the preserved `status_baseline.json`?
- Did it contain the recorded-release candidates and candidate index?
- Did it contain the release-evidence input manifest?
- Did it contain the recorded-evidence verifier report?
- Did it contain required external-summary envelopes and attestation bundles?
- Did it contain the final `status.json`?
- Did it contain `release_decision_v0.json`?
- Did it contain `artifact_provenance_binding_v0.json`?
- Did it contain `release_authority_v0.json` and the Quality Ledger?
- Did it contain the release-authority audit bundle?
- Was complete package presence verified independently of the advisory qualification checker?
- Were package-level digest and binding relationships verified?

### 9. Qualification boundary

- Did the advisory qualification subset checker pass?
- Was its result treated only as subset qualification?
- Was qualification kept non-normative and non-blocking?
- Was a successful qualification result kept distinct from complete reference-package verification?
- Was the run prevented from being called complete until the full target package and its bindings were verified?

### 10. Public record

- Were concrete workflow, commit, run, and release-candidate identities recorded?
- Were public artifact references available?
- Were SHA-256 digests recorded for the required artifacts?
- Was `docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md` completed from the actual run?
- Was the run note kept non-authoritative?
- Was the completed reference run clearly distinguished from Core, smoke, fixture, and demo surfaces?

---

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

The current-run evidence producer, canonical candidate replay, recorded release-evidence verifier, canonical verifier replay, release-required materializer, and advisory subset qualification checker are implemented.

Baseline reference-bundle assembly is implemented.

Complete evidence-chain reference packaging and complete-package verification remain pending.

The next operational sequence is:

1. replace deferred or wildcard release-grade signer identities with one exact operational workflow identity;
2. implement the current-run canonical external-evidence producer lane;
3. generate a cryptographic attestation bundle for the current-run external summary;
4. build the canonical external-summary envelope from the verified run identity and summary digest;
5. extend `release-grade-reference-run-v0` assembly to include:
   - `required_gate_evidence_v0.json`;
   - `status_baseline.json`;
   - recorded-release candidate envelopes;
   - the candidate index;
   - the release-evidence input manifest;
   - the recorded-evidence verifier report;
   - external-summary envelopes and attestation bundles;
   - `release_decision_v0.json`;
   - `artifact_provenance_binding_v0.json`;
6. add or extend package verification so the complete reference bundle is checked independently of the advisory subset qualification checker;
7. execute the controlled strict release-grade workflow;
8. preserve the complete current-run evidence, candidate, verifier, materialization, final-status, decision, and binding chain;
9. publish the complete release-grade reference artifact bundle;
10. complete `docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md` with concrete run identity, artifact URLs, and SHA-256 digests;
11. link the completed public reference run from the README and documentation index;
12. use the completed run as the baseline for independent reproduction and later portability work.

The progression is:

```text
exact operational signer identity
→ current-run attested external evidence
→ complete evidence-chain packaging
→ complete-package verification
→ controlled strict release-grade run
→ completed public reference-run record
→ independent reproduction
```

## Follow-up PR

```text
docs(ref): correct qualification and package completeness boundary
```

Scope:

docs/release_grade_reference_run_v0.md
