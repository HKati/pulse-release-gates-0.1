# Release-grade reference run v0

## Purpose

This document defines what counts as a completed PULSE release-grade reference run.

A release-grade reference run is a documented and reproducible run that exercises the release-grade evidence path rather than only the minimal Core smoke path.

Its target evidence-to-decision chain is:

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

A completed reference run must preserve enough evidence to review and reconstruct that connected path.

The Quality Ledger, verifier reports, attestation reports, `release_authority_v0.json`, `release_decision_v0.json`, provenance bindings, audit bundles, reference-run notes, Pages, dashboards, and publication artifacts preserve evidence, trace, review, binding, or publication state.

They do not independently produce release authority.

This document is an operational reference.

It does not change:

- release semantics;
- gate policy;
- registry semantics;
- `status.json` semantics;
- verifier behavior;
- materializer behavior;
- `PULSE_safe_pack_v0/tools/check_gates.py` behavior;
- primary CI authority;
- diagnostic or shadow-layer authority.

## Status

- stage: implemented and operationally demonstrated release-grade evidence path
- normative: false
- target lane: release-grade
- authority role: documentation and operational guidance
- current-run required-gate evidence production: implemented and exercised
- non-stubbed release candidate status production: implemented and exercised
- canonical recorded-release candidate production: implemented and exercised
- canonical candidate replay: implemented and exercised
- recorded release-evidence verifier: implemented and exercised
- canonical verifier replay before materialization: implemented and exercised
- policy-derived release-required materialization: implemented and exercised
- external-summary schema validation: implemented and exercised
- external-summary semantic validation: implemented and exercised
- signer-policy admission: implemented and exercised
- cryptographic GitHub attestation verification: implemented and exercised
- advisory qualification subset checker: implemented and passed
- exact operational release-grade signer identity: completed
- current-run attested external-evidence production lane: completed
- complete evidence-chain reference packaging: completed
- structural package-completeness verification: completed
- independent reference-package verification: completed
- first completed public non-stubbed release-grade run record: completed — PULSE CI #6066
- completed source commit: `46b639706e23f80fe296a8893be18e2b5ab21f7e`
- completed workflow run ID: `29249887581`
- completed run record: `docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md`
- qualification checker: `PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py`
- recorded evidence verifier: `PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py`
- release-required materializer: `PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py`
- final release evaluator: `PULSE_safe_pack_v0/tools/check_gates.py`
- primary workflow qualification role: advisory, non-normative, and non-blocking

The verifier-backed fold-in path is implemented and was exercised successfully
by PULSE CI #6066.

Candidate evidence cannot authorize itself through:

- local file presence;
- a canonical-looking filename;
- a self-declared trusted-producer field;
- a self-declared verified field;
- a supplied verifier report;
- a recorded digest without canonical replay.

The implemented and demonstrated admission path requires:

```text
canonical candidate replay
→ recorded release-evidence verification
→ canonical verifier replay
→ atomic policy-derived release-required materialization
→ final gate enforcement
```

External release-grade evidence must pass the applicable:

- canonical schema validation;
- detector-specific semantic validation;
- signer-policy admission;
- summary and raw-evidence digest binding;
- subject and commit binding;
- envelope binding;
- cryptographic attestation verification.

TThe first completed public reference execution is:

```text
PULSE CI #6066

run ID:
29249887581

source commit:
46b639706e23f80fe296a8893be18e2b5ab21f7e

run mode:
prod

result:
Success
```

The concrete evidence, artifact references, archive digests, package inventory,
qualification result, primary decision, and verification results are recorded
in:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

The reference-run definition and completed-run record do not create a new gate
and do not promote any verifier, materializer, qualification checker, package
checker, reader, audit, diagnostic, or publication surface into independent
release authority.

---

## Core smoke vs release-grade reference

PULSE intentionally separates the smaller Core lane from a completed release-grade reference run.

### Core lane

The Core lane is the minimal deterministic integration path.

It is useful for:

- first integration;
- local artifact inspection;
- baseline CI wiring;
- validating the basic release-authority path;
- proving the narrow `core_required` gate set.

A Core run may demonstrate that the basic PULSE machinery operates.

A Core run is not automatically a complete release-grade evidence reference.

### Release-grade reference run

A release-grade reference run exercises the stronger release path.

It must demonstrate:

- `metrics.run_mode = "prod"`;
- current-run required-gate evidence;
- a non-stubbed candidate release state;
- canonical candidate production;
- canonical candidate replay;
- recorded release-evidence verification;
- canonical verifier replay;
- atomic policy-derived release-required materialization;
- required external evidence when active;
- effective enforcement of `required + release_required`;
- a final validated `status.json`;
- a recorded primary CI allow/block result;
- release-decision and provenance-binding artifacts;
- release-authority manifest generation;
- Quality Ledger generation and parity;
- audit-bundle publication;
- complete reference-package assembly;
- package-level verification;
- concrete public run identity and traceability.

In compact form:

```text
Core lane
= smallest deterministic release-authority lane

Completed release-grade reference run
= complete, verified, reproducible evidence-to-decision package
```

---

## Release-grade lane selection

A release-grade reference run must use one of the repository-supported release-grade paths:

```text
version tag push: v* / V*
```

or:

```text
workflow_dispatch
strict_external_evidence = true
```

The workflow-effective release-grade policy set is:

```text
required + release_required
```

The exact workflow-effective materialized required gate set must be derived from declared policy.

It must not be manually reconstructed or silently hardcoded as a divergent list.

---

## Implemented release-grade evidence path

The implemented release-grade path currently includes:

```text
current-run required-gate evaluations
→ required_gate_evidence_v0.json
→ non-stubbed prod candidate status
→ preserved candidate-state snapshot
→ canonical recorded-release candidate production
→ release-evidence input manifest
→ canonical candidate replay
→ recorded release-evidence verification
→ verifier report
→ canonical verifier replay by the materializer
→ policy-derived release-required materialization
→ final status.json
→ release-grade status-contract validation
→ workflow-effective gate enforcement
→ primary CI allow/block release decision
```

The path also includes external-summary verification capability:

```text
canonical external summary
→ canonical external-summary envelope
→ signer-policy admission
→ cryptographic GitHub attestation verification
→ canonical candidate admission
```

The exact operational signer and current-run external-summary production lane
were exercised successfully by PULSE CI #6066. The admitted signer identity,
model revision, attestation, artifact references, and digests are recorded in
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md.

---

## Required evidence properties

### 1. Current-run evidence

A release-grade run must produce evidence from the current workflow execution.

Expected artifact:

```text
PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json
```

The evidence must be bound to:

- repository;
- current commit;
- current run key;
- release candidate;
- evaluator identity;
- evaluator digest;
- gate policy;
- registry;
- threshold or metric specification;
- raw evidence.

Stale evidence from an earlier run must not be admitted.

### 2. Non-stubbed candidate release state

The run must not rely on scaffolded or stubbed gate state.

Expected boundary:

```text
metrics.run_mode = prod
diagnostics.gates_stubbed = false
diagnostics.scaffold = false
```

The candidate release state must be built before release-required materialization.

The workflow preserves a candidate-state snapshot as:

```text
PULSE_safe_pack_v0/artifacts/status_baseline.json
```

This pre-augmentation and pre-materialization snapshot must remain distinct from the final:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

### 3. Verified external evidence

When strict external evidence is active, release-grade external evidence must be present and admitted through the canonical verification path.

Each contributing external summary must satisfy:

- canonical `external_summary_v1` schema validation;
- detector-specific tool identity;
- detector-specific metric identity;
- declared threshold reference;
- declared comparator semantics;
- literal metric pass state;
- literal aggregate `result.passed = true`;
- repository binding;
- subject binding;
- commit binding;
- run binding;
- release-candidate binding;
- canonical repository-relative evidence paths;
- raw-evidence digest binding;
- summary digest binding;
- exact release-grade signer-policy admission;
- external-summary envelope binding;
- cryptographic attestation bundle presence;
- successful independent attestation verification;
- canonical candidate replay;
- recorded release-evidence verification.

Expected release-grade gate state:

```text
external_summaries_present = true
external_all_pass = true
```

when those gates are part of the active `release_required` set.

The following do not establish release-grade external evidence by themselves:

- canonical filename;
- JSON parseability;
- generic metric presence;
- self-declared `passed = true`;
- self-declared verification;
- digest text inside an unverified object;
- unsigned evidence;
- an envelope without successful cryptographic verification.

Unsigned, unverified, stale, malformed, substituted, or mismatched external evidence must fail closed.

### 4. Canonical candidate production and replay

The current run must produce canonical recorded-release candidate envelopes.

Expected artifacts:

```text
PULSE_safe_pack_v0/artifacts/recorded_release_candidates/
PULSE_safe_pack_v0/artifacts/recorded_release_candidate_index_v0.json
```

Before evidence admission, the verifier reruns the checked-in canonical candidate producer in memory.

The supplied candidate set must exactly match canonical replay.

The verifier must reject:

- missing candidates;
- additional candidates;
- modified candidate envelopes;
- substituted candidate envelopes;
- mismatched producer metadata;
- candidate index drift;
- self-declared producer trust without replay equality.

### 5. Recorded release-evidence verification

Expected manifest:

```text
PULSE_safe_pack_v0/artifacts/release_evidence_input_manifest_v0.json
```

Expected verifier report:

```text
PULSE_safe_pack_v0/artifacts/recorded_release_evidence_verifier_v0.json
```

The verifier must check:

- manifest schema;
- run mode;
- run identity;
- subject identity;
- commit equality;
- policy set;
- policy path and digest;
- registry path and digest;
- candidate artifact digest;
- candidate schema;
- candidate run binding;
- candidate subject binding;
- canonical candidate replay;
- verified producer trust;
- raw-evidence digest;
- required-gate membership;
- relation bindings;
- gate-materialization admissibility.

The verifier report must use only:

```text
verified
failed
```

as top-level status values.

A verified report must contain an empty error list.

### 6. Canonical verifier replay and materialization

The release-required materializer consumes:

```text
PULSE_safe_pack_v0/tools/materialize_release_required_from_verifier_v0.py
```

The materializer must not trust the supplied verifier report as an independent authority object.

Before materialization, it must rerun:

```text
PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py
```

from the supplied manifest and repository root.

The supplied verifier report must exactly match canonical verifier replay.

Materialization must also require:

- `run_mode = prod`;
- current candidate-state identity matching the verifier;
- current subject identity matching the verifier;
- current policy path and digest matching the verifier;
- no stubbed gate state;
- no scaffolded gate state;
- no pre-existing release-required gate values;
- non-empty evidence results;
- non-empty relation-binding results;
- explicit admissibility for every policy-derived release-required gate.

Release-required materialization must be atomic.

Failed admission must not partially mutate the candidate release state.

### 7. Final status contract and gate enforcement

The final:

```text
PULSE_safe_pack_v0/artifacts/status.json
```

must validate against the committed release-grade status contract.

Every gate in the workflow-effective materialized required gate set must be present and literal `true`.

Final enforcement must be performed by:

```text
PULSE_safe_pack_v0/tools/check_gates.py
```

The final release-boundary result is:

```text
allow
block
```

The strict gate evaluator remains the final enforcement carrier.

### 8. Decision and provenance-binding artifacts

The workflow must produce:

```text
PULSE_safe_pack_v0/artifacts/release_decision_v0.json
```

This artifact preserves the release-level decision trace.

It is a recorded decision carrier.

It does not replace the primary CI workflow or independently create release authority.

The workflow must also produce and verify:

```text
PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
```

The provenance binding connects the applicable:

- final `status.json`;
- declared gate policy;
- Quality Ledger;
- `release_decision_v0.json`;
- `release_authority_v0.json`;
- artifact digests;
- active policy-set identity.

For applicable non-PR runs, the binding may also become the subject of a GitHub attestation job.

The binding and its attestation preserve provenance.

They do not replace strict gate enforcement.

### 9. Release-authority manifest

The run must produce:

```text
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

The manifest remains an audit and traceability carrier.

It must not become a second release-decision engine.

It should preserve:

- run identity;
- policy identity;
- workflow-effective required gates;
- release-required materialization state;
- required-gate evaluation;
- recorded decision state;
- diagnostic authority boundary.

### 10. Quality Ledger

The run must produce:

```text
PULSE_safe_pack_v0/artifacts/report_card.html
```

The Quality Ledger must be rendered from the final `status.json`.

Quality Ledger / final-status parity must pass.

The Ledger remains a reader surface.

It must not:

- compute release authority;
- override the primary CI result;
- create a break-glass authority path;
- reinterpret required-gate state.

### 11. Audit bundle

The current workflow may produce a release-authority audit bundle containing the baseline review surfaces:

```text
report_card.html
release_authority_v0.json
status.json
```

The audit bundle is a review and preservation package.

It is not a release-decision engine.

The baseline audit bundle is not the same as the complete release-grade reference package.

### 12. Complete public record

A completed public reference run must include:

- concrete workflow identity;
- repository identity;
- commit identity;
- run ID;
- run attempt;
- run key;
- release candidate;
- active policy set;
- workflow-effective required gate set;
- public artifact references;
- required SHA-256 digests;
- final qualification state;
- complete-package verification state.

The run must be recorded in:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

That note remains non-authoritative.

---

## Expected artifact set

A completed release-grade reference run must archive the complete reviewable evidence-to-decision chain.

The list below defines the **complete reference-package contract**.

PULSE CI #6066 produced the complete package as:

```text
complete-release-grade-reference-package-29249887581-1
```

The package was assembled from one fixed current-run identity, structurally
checked, digest-inventoried, and independently verified.

The older:

```text
release-grade-reference-run-v0
```

artifact remains a smaller baseline reader/review bundle.

It must not be confused with the complete evidence-chain package.

### Current-run evidence and pre-materialization candidate state

```text
PULSE_safe_pack_v0/artifacts/required_gate_evidence_v0.json
PULSE_safe_pack_v0/artifacts/status_baseline.json
PULSE_safe_pack_v0/artifacts/recorded_release_candidates/
PULSE_safe_pack_v0/artifacts/recorded_release_candidate_index_v0.json
```

`status_baseline.json` is the preserved pre-materialization candidate-state snapshot.

It must remain distinct from the final `status.json`.

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

The complete package must also preserve every raw evidence artifact referenced by admitted external summaries.

### Final release state and decision trace

```text
PULSE_safe_pack_v0/artifacts/status.json
PULSE_safe_pack_v0/artifacts/release_decision_v0.json
PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
PULSE_safe_pack_v0/artifacts/report_card.html
```

`release_decision_v0.json` preserves the recorded release-level decision trace.

`artifact_provenance_binding_v0.json` binds the final state, policy, Ledger, release decision, and release-authority manifest into a digest-backed verification subject.

### Review and preservation bundles

```text
release-authority-audit-bundle
release-grade-reference-run-v0
complete-release-grade-reference-package-29249887581-1
```

For the completed public reference run, the complete package contains the full
evidence-chain set defined in this section.

Its GitHub artifact ID, archive digest, package inventory, and internal file
digests are recorded in:

```text
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

### Optional CI exports

```text
reports/junit.xml
reports/sarif.json
```

### Recommended review order

1. current-run identity;
2. current-run required-gate evidence;
3. preserved pre-materialization `status_baseline.json`;
4. canonical candidate envelopes;
5. candidate index;
6. release-evidence input manifest;
7. recorded release-evidence verifier report;
8. canonical candidate replay result;
9. canonical verifier replay result;
10. release-required materialization result;
11. final `status.json`;
12. workflow-effective materialized required gate set;
13. `PULSE_safe_pack_v0/tools/check_gates.py` result;
14. primary CI allow/block result;
15. `release_decision_v0.json`;
16. `artifact_provenance_binding_v0.json`;
17. `release_authority_v0.json`;
18. Quality Ledger;
19. release-authority audit bundle;
20. complete release-grade reference bundle.

---

## Completed reference-package execution state

The repository retains two distinct package roles.

### Baseline reader/review bundle

```text
release-grade-reference-run-v0
```

This bundle preserves a smaller reader-facing set such as:

```text
status.json
report_card.html
release_authority_v0.json
release-authority-audit-bundle
external summaries
optional JUnit
optional SARIF
```

It remains useful for review.

It is not the complete evidence-chain package.

### Complete release-grade reference package

PULSE CI #6066 assembled:

```text
complete-release-grade-reference-package-29249887581-1
```

The complete package includes:

```text
required_gate_evidence_v0.json
status_baseline.json
recorded_release_candidates/
recorded_release_candidate_index_v0.json
release_evidence_input_manifest_v0.json
recorded_release_evidence_verifier_v0.json
LlamaGuard raw evidence
LlamaGuard evaluator manifest
canonical external summary
attestation bundle
canonical envelope
attestation-verifier report
final status.json
release_decision_v0.json
artifact_provenance_binding_v0.json
release_authority_v0.json
report_card.html
release-authority-audit-bundle
run_metadata_v0.json
package_digest_inventory_v0.json
```

Recorded verification state:

```text
package inventory file count:
23

inventory coverage:
exact

structural completeness:
135 / 135 checks passed

independent package verification:
157 / 157 checks passed
```

Therefore:

```text
baseline review bundle
≠ complete release-grade reference package

complete package assembled
+ structural completeness PASS
+ independent verification PASS
= completed package milestone
```

Package assembly, package completeness, and package verification remain
non-authorizing evidence and verification surfaces.

They do not replace the primary CI allow/block result.

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

### Decision, provenance, audit, and publication carriers

- `release_decision_v0.json`;
- `artifact_provenance_binding_v0.json`;
- attestation results;
- verifier reports;
- Quality Ledger;
- `release_authority_v0.json`;
- GitHub Step Summary;
- audit bundles;
- reference-run notes;
- Pages and dashboards.

These surfaces may explain, verify, bind, publish, preserve, or reconstruct the decision chain.

They must not:

- recompute release authority;
- replace strict gate enforcement;
- override the primary CI result;
- silently reinterpret required-gate state;
- create an independent break-glass path;
- create a second release-decision engine.

---

## Acceptance criteria

A run can be called a completed release-grade reference run only if all of the following are true:

- the run used a declared release-grade workflow path;
- `metrics.run_mode = "prod"`;
- the active policy set was `required + release_required`;
- the workflow-effective materialized required gate set was derived from declared policy;
- current-run required-gate evidence was present and identity-bound;
- the pre-materialization candidate state was preserved as `status_baseline.json`;
- the candidate release state was non-stubbed;
- stale candidate outputs were cleared before production;
- canonical candidate production succeeded;
- the supplied candidate set exactly matched canonical candidate replay;
- recorded release-evidence verification succeeded;
- the supplied verifier report exactly matched canonical verifier replay;
- release-required gates were materialized atomically from verifier-admitted evidence;
- the final `status.json` validated against the committed release-grade status contract;
- every workflow-effective required gate was present and literal `true`;
- `PULSE_safe_pack_v0/tools/check_gates.py` completed strict fail-closed enforcement;
- the primary CI allow/block result was recorded;
- required external evidence was present;
- required external evidence passed schema, semantic, signer, digest, subject, and cryptographic attestation verification;
- `release_decision_v0.json` was produced;
- `artifact_provenance_binding_v0.json` was produced and verified;
- `release_authority_v0.json` was produced and validated;
- the Quality Ledger was generated from the final `status.json`;
- Quality Ledger / final-status parity passed;
- the release-authority audit bundle was produced;
- a complete release-grade reference bundle containing the full target artifact set was produced;
- complete package presence and binding were verified independently of the advisory qualification checker;
- all diagnostic, verifier, audit, reader, decision-trace, provenance, and publication surfaces remained non-authoritative;
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

### Current direct inputs

The checker's current direct inputs are:

```text
final status.json
release_authority_v0.json
optional report_card.html
optional release-authority audit-bundle directory
```

### Current direct checks

The checker directly evaluates, among other things:

- `status.metrics.run_mode = "prod"`;
- `status.diagnostics.gates_stubbed = false`;
- `status.diagnostics.scaffold = false`;
- literal-true values for the current hardcoded release-required reference gates;
- `release_authority_v0` schema identity;
- `manifest.run_identity.run_mode = "prod"`;
- `required+release_required` policy-set representation;
- `release_required_materialized = true`;
- presence of the expected release-required gates in the manifest's effective gate list;
- absence of recorded failed required gates;
- absence of recorded missing required gates;
- an accepted manifest decision-state marker;
- `decision.fail_closed = true`;
- optional shadow-surface non-normative state;
- optional Quality Ledger file presence;
- current baseline audit-bundle file presence.

The checker currently accepts historical/internal manifest decision-state markers:

```text
PASS
PROD-PASS
```

for its subset qualification logic.

Those compatibility markers do not redefine the canonical release-boundary vocabulary:

```text
allow
block
```

### Not directly verified by this checker

The checker does not currently consume or verify:

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

A successful checker result means only that the supplied final status, authority manifest, and optional reader/audit subset satisfy the implemented advisory qualification checks.

It does not prove by itself that every completed-run acceptance criterion in this document has been satisfied.

### Non-authority boundary

The checker does not:

- produce current-run evidence;
- produce candidate evidence;
- admit candidate evidence;
- establish producer trust by declaration;
- replace canonical candidate replay;
- replace recorded release-evidence verification;
- replace canonical verifier replay;
- materialize `release_required` gates;
- replace `PULSE_safe_pack_v0/tools/check_gates.py`;
- verify the full reference package;
- change the primary CI allow/block result;
- promote verifier, reader, audit, or publication surfaces into authority.

### Test coverage

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

A successful qualification does not classify an incomplete artifact package as a completed public reference run.

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

Complete-package verification is required for the first question.

The canonical PULSEmech release-authority path answers the second.

A completed public release-grade reference-run record may be finalized only after:

- the advisory qualification subset passes;
- the complete target artifact package exists;
- package presence is verified;
- decision and provenance bindings are verified;
- the concrete artifacts are available for review.

---

## Primary workflow visibility

The primary workflow runs the advisory subset qualification checker for release-grade runs.

Workflow:

```text
.github/workflows/pulse_ci.yml
```

Checker:

```text
PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py
```

Current supplied inputs:

```text
PULSE_safe_pack_v0/artifacts/status.json
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
PULSE_safe_pack_v0/artifacts/report_card.html
PULSE_safe_pack_v0/artifacts/release_authority_audit_bundle
```

The result is reported in the GitHub Step Summary.

The workflow step is:

- advisory;
- non-normative;
- non-blocking;
- release-grade only.

If the checker fails, the workflow records:

```text
Not qualified (advisory)
```

while leaving the release outcome unchanged.

If the checker succeeds, the workflow records:

```text
Qualified
```

for the implemented subset.

Neither result replaces the normative path:

```text
recorded release evidence
+ final status.json
+ declared gate policy
+ workflow-effective materialized required gate set
+ PULSE_safe_pack_v0/tools/check_gates.py
+ primary CI workflow
= primary CI allow/block release decision
```

The current workflow may assemble and upload a baseline reference bundle after:

- advisory subset qualification succeeds;
- Quality Ledger / final-status parity succeeds.

Baseline bundle upload does not by itself prove complete-package verification.

---

## Example package

A minimal example package is available at:

```text
examples/release_grade_reference_run_v0/
```

It contains:

```text
README.md
status.release_grade.pass.example.json
release_authority_v0.release_grade.pass.example.json
```

The package demonstrates the current advisory qualification-checker subset.

It does not contain or prove the complete target evidence-chain package.

From the repository root, the example may be checked with:

```text
python PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py \
  --status examples/release_grade_reference_run_v0/status.release_grade.pass.example.json \
  --manifest examples/release_grade_reference_run_v0/release_authority_v0.release_grade.pass.example.json
```

Expected result:

```text
OK: release-grade reference run criteria satisfied
```

In this context, the message means that the supplied example satisfies the checker's implemented subset.

It does not prove:

- a real production release;
- canonical candidate replay;
- canonical verifier replay;
- cryptographic external-evidence verification;
- complete package assembly;
- complete package verification;
- a completed public reference run.

---

## Non-goals

A release-grade reference run is not:

- a new release policy;
- a new gate set;
- a replacement for `PULSE_safe_pack_v0/tools/check_gates.py`;
- a replacement for final `status.json`;
- a verifier-report-derived decision;
- an attestation-derived decision;
- a dashboard-derived decision;
- a Quality Ledger override;
- a shadow-layer promotion;
- an independent break-glass path;
- a guarantee of external compliance certification.

It is a reproducible, complete, verified reference package for the implemented release-grade PULSEmech path.

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
- Was `status_baseline.json` kept distinct from final `status.json`?
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
- Did each summary pass canonical schema validation?
- Did each summary pass detector-specific semantic validation?
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
- Did failed admission leave candidate state unmodified?
- Was final `status.json` produced only after successful verifier replay?
- Did final `status.json` validate against the release-grade status contract?
- Was every gate in the workflow-effective materialized required gate set present?
- Was every required gate literal `true`?
- Did `PULSE_safe_pack_v0/tools/check_gates.py` enforce the exact workflow-effective materialized required gate set?
- Was the primary CI result recorded as `allow` or `block`?

### 6. Decision and provenance artifacts

- Was `release_decision_v0.json` produced?
- Does `release_decision_v0.json` preserve the release-level decision trace?
- Was `artifact_provenance_binding_v0.json` produced?
- Was `artifact_provenance_binding_v0.json` independently verified?
- Does the provenance binding cover final status, policy, Quality Ledger, release decision, and release-authority manifest?
- Was `release_authority_v0.json` produced?
- Did the release-authority manifest validate?
- Did all decision and binding artifacts refer to the same run and final status?

### 7. Reader and audit surfaces

- Was the Quality Ledger generated from final `status.json`?
- Did Quality Ledger / final-status parity pass?
- Did the Quality Ledger remain a non-authorizing reader surface?
- Was the release-authority audit bundle produced?
- Did the audit bundle contain its required baseline artifacts?
- Did any dashboard, Pages surface, report, manifest, note, or audit sidecar attempt to act as independent release authority?

### 8. Complete reference package

- Was the complete `release-grade-reference-run-v0` bundle produced?
- Did it contain `required_gate_evidence_v0.json`?
- Did it contain preserved `status_baseline.json`?
- Did it contain recorded-release candidates and the candidate index?
- Did it contain the release-evidence input manifest?
- Did it contain the recorded-evidence verifier report?
- Did it contain required external-summary envelopes?
- Did it contain required attestation bundles?
- Did it contain final `status.json`?
- Did it contain `release_decision_v0.json`?
- Did it contain `artifact_provenance_binding_v0.json`?
- Did it contain `release_authority_v0.json`?
- Did it contain the Quality Ledger?
- Did it contain the release-authority audit bundle?
- Was complete package presence verified independently of the advisory qualification checker?
- Were package-level digest and binding relationships verified?

### 9. Qualification boundary

- Did the advisory qualification subset checker pass?
- Was its result treated only as subset qualification?
- Was qualification kept non-normative and non-blocking?
- Was successful qualification kept distinct from complete reference-package verification?
- Was the run prevented from being called complete until the full target package and its bindings were verified?

### 10. Public record

- Were concrete workflow, commit, run, and release-candidate identities recorded?
- Were public artifact references available?
- Were SHA-256 digests recorded for the required artifacts?
- Was `docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md` completed from the actual run?
- Was the run note kept non-authoritative?
- Was the completed reference run clearly distinguished from Core, smoke, fixture, and demo surfaces?

---

## Relation to public demo surfaces

Public Pages, Kaggle notebooks, example packages, and demo surfaces may show:

- Core state;
- smoke-run state;
- fixture state;
- diagnostic evidence;
- reader-visible release state.

Those surfaces may be useful for visibility and review.

They must not be confused with a completed public release-grade reference run.

Recommended wording:

```text
Core smoke surface
= integration and visibility surface

Release-grade example package
= qualification-subset fixture

Completed public release-grade reference run
= complete, verified, reproducible evidence-chain package
```

---

## Next operational steps

The current-run evidence producer, canonical candidate replay, recorded release-evidence verifier, canonical verifier replay, release-required materializer, cryptographic attestation verifier, and advisory subset qualification checker are implemented.

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
   - external-summary envelopes;
   - external-summary attestation bundles;
   - `release_decision_v0.json`;
   - `artifact_provenance_binding_v0.json`;
6. add or extend package verification so the complete reference bundle is checked independently of the advisory subset qualification checker;
7. execute the controlled strict release-grade workflow;
8. preserve the complete current-run evidence, candidate, verifier, materialization, final-status, decision, and provenance-binding chain;
9. publish the complete release-grade reference artifact bundle;
10. complete `docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md` with concrete run identity, artifact URLs, and SHA-256 digests;
11. link the completed public reference run from the README and documentation index;
12. use the completed run as the baseline for independent reproduction and later portability work.

The progression is:

```text
The first completed public non-stubbed hosted release-grade reference run now
exists.

Canonical baseline:

```text
workflow:
PULSE CI #6066

workflow run ID:
29249887581

source commit:
46b639706e23f80fe296a8893be18e2b5ab21f7e

record:
docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md
```

The next operational work begins after—not before—this reference state.

Recommended sequence:

1. preserve the completed record in the README and documentation index;
2. retain the exact workflow, artifact, attestation, and digest references;
3. produce an independent reproduction procedure from the complete package;
4. test artifact export and verification outside the original workflow;
5. define controlled failure variants against the fixed #6066 baseline;
6. exercise portability across a second operator or execution environment;
7. begin larger candidate-state batches only after reconstruction remains stable;
8. use HPC diagnostically against the fixed completed reference state;
9. keep SLSA/VSA release-required activation in a separate bounded promotion PR;
10. preserve the existing release-authority boundary throughout later scaling.

The progression is now:

```text
completed public reference state
→ independent reproduction
→ portability validation
→ controlled failure variants
→ larger candidate-state batches
→ HPC-supported analysis
```

The completed run does not activate SLSA/VSA as release-required.

It does not create a GitHub Release, version tag, Zenodo record, DOI, or
production deployment claim.

PULSEmech remains the release-authority mechanism:

```text
recorded release evidence
→ final status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block result
```
