# Release-grade reference run v0

## Purpose

This document defines what counts as a PULSE release-grade reference run.

A release-grade reference run is a documented, reproducible run that exercises
the release-grade evidence path rather than the minimal Core smoke path.

Its purpose is to show the full release-authority chain with materialized
evidence:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective required gate set
→ check_gates.py
→ Quality Ledger
→ release_authority_v0.json
→ release-authority-audit-bundle
```

This document is an operational reference.

It does not change release semantics, gate policy, status.json semantics,
check_gates.py behavior, primary release-decision authority, or shadow-layer
authority.

## Status

  * stage: reference definition + qualification checker implemented + recorded release-evidence verifier prerequisite implemented
  * normative: false
  * target lane: release-grade
  * authority role: documentation / operational guidance
  * checker: `PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py`
  * recorded evidence verifier: `PULSE_safe_pack_v0/tools/check_recorded_release_evidence_v0.py`
  * test coverage: `tests/test_check_release_grade_reference_run_v0.py`
  * recorded evidence verifier test coverage: `tests/test_check_recorded_release_evidence_v0.py`
  * tools-test coverage: `ci/tools-tests.list`
  * primary workflow advisory qualification: present
  * primary workflow authority role: non-normative / non-blocking
  * fold-in status: `--release-grade-materialized` remains intentionally fail-closed for release-required evidence fold-in until a follow-up PR admits only verifier-validated evidence

Security boundary note: detector materialization artifacts, canonical external summaries, and `refusal_delta_summary.json` are no longer treated as sufficient merely because they exist locally. They must now pass the recorded release-evidence verifier, which binds identity, provenance, policy, subject, and raw evidence before later release-grade materialization can admit them.

The reference run definition describes how to produce and review a release-grade PULSE run. It does not create a new gate and does not promote any diagnostic surface into release authority.

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

### 2. External summaries

When strict external evidence is active, external detector summaries must be
present and folded into the release evidence surface.

Expected release-grade evidence:

```
external_summaries_present = true
external_all_pass = true
```

when those gates are part of the active release-required set.

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

A release-grade reference run should archive at least:

```
PULSE_safe_pack_v0/artifacts/status.json
PULSE_safe_pack_v0/artifacts/report_card.html
PULSE_safe_pack_v0/artifacts/release_authority_v0.json
```

and, when present:

```
PULSE_safe_pack_v0/artifacts/external/*_summary.json
reports/junit.xml
reports/sarif.json
release-authority-v0
release-authority-audit-bundle
```

Recommended review order:

1. status.json  
2. materialized required gate set  
3. check_gates.py result  
4. release_authority_v0.json  
5. Quality Ledger  
6. release-authority-audit-bundle  

---

## Release authority boundary

The release-grade reference run must preserve the PULSE authority boundary.

### Normative path

```
status.json
+ declared gate policy
+ workflow-effective required gate set
+ check_gates.py
+ primary CI workflow
= release authority
```

### Audit / review surfaces

- Quality Ledger  
- release_authority_v0.json  
- Step Summary  
- release-authority-v0 artifact  
- release-authority-audit-bundle  
- Pages / dashboards  

These surfaces explain, publish, or preserve the decision chain.

They must not recompute, replace, or silently reinterpret release authority.

---

## Acceptance criteria

A run can be called a release-grade reference run only if the following are true:

- The run uses a release-grade workflow path.  
- The active enforce set is `required + release_required`, or the documented
  release-grade equivalent.  
- `metrics.run_mode` reflects the release-grade lane.  
- Required gates are evaluated fail-closed.  
- Stubbed gate output is rejected or absent.  
- External summaries are present when strict external evidence is required.  
- The final `status.json` is archived.  
- The Quality Ledger is archived.  
- `release_authority_v0.json` is produced and validated.  
- The release authority audit bundle is produced.  
- Diagnostic / shadow / publication surfaces remain non-normative unless
  explicitly promoted by policy.  

---

## Qualification checker

The release-grade reference run criteria are supported by a checker:

```text
PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py
```

The checker qualifies candidate runs for operational review. It is not a
release-decision engine and does not replace check_gates.py.

It checks, among other things:

- `status.metrics.run_mode = "prod"`  
- no stubbed gate surface  
- materialized detector evidence  
- external summary presence and pass gates  
- release authority manifest presence  
- `required + release_required` policy-set representation  
- successful manifest decision state  
- optional Quality Ledger presence  
- optional audit bundle contents  

The checker is covered by:

```text
tests/test_check_release_grade_reference_run_v0.py
```

and is wired into:

```text
ci/tools-tests.list
```

Authority rule:

```text
check_gates.py = release authority evaluator
check_release_grade_reference_run_v0.py = release-grade reference qualification checker
```

The checker can reject a candidate reference run as insufficient for reference
purposes without redefining the underlying release decision.

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

The package shows the expected artifact shape for a non-stubbed,
materialized-evidence release-grade reference run.

From the repository root, the example can be inspected with:

```text
python PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py \
  --status examples/release_grade_reference_run_v0/status.release_grade.pass.example.json \
  --manifest examples/release_grade_reference_run_v0/release_authority_v0.release_grade.pass.example.json
```

Expected result:

```text
OK: release-grade reference run criteria satisfied
```

This example package is a reference surface only. It does not prove that a real
production release occurred, and it does not change release semantics, gate
policy, status.json, check_gates.py, or release authority.

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
status.json
+ declared gate policy
+ workflow-effective required gate set
+ check_gates.py
+ primary CI workflow
```

The qualification step answers a different question:

Does this run satisfy the documented release-grade reference-run criteria?

It does not answer:

Should this release pass?

That decision remains with the normal PULSE release-authority path.

---

## Non-goals

A release-grade reference run is not:

- a new release policy  
- a new gate set  
- a replacement for check_gates.py  
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
- Was stubbed/scaffolded evidence absent from the release-grade path?  
- Did `check_gates.py` enforce the required gates?  
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

## Next implementation steps

Suggested next steps:

* Use the recorded release-evidence verifier for detector materialization, canonical external summaries, and refusal-delta evidence.
* Only after verifier-admitted evidence is available, allow `--release-grade-materialized` to fold verified evidence into release-required gate booleans.
* Add public reference-run packaging in the primary workflow for release-grade runs.
* Produce one non-stubbed release-grade reference run.
* Archive its `status.json`, Quality Ledger, release authority manifest, and audit bundle.
* Document the run in a short reference-run note.
* Link the reference run from the README or documentation index.
* Use the reference run as the baseline for future enterprise-grade release governance examples.
