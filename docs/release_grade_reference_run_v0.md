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

- stage: reference definition  
- normative: false  
- target lane: release-grade  
- authority role: documentation / operational guidance  

The reference run definition describes how to produce and review a release-grade
PULSE run. It does not create a new gate and does not promote any diagnostic
surface into release authority.

---

## Core smoke vs release-grade reference

PULSE intentionally separates the smaller Core lane from release-grade runs.

### Core lane

The Core lane is the minimal deterministic integration path.

It is useful for:

- first integration  
- local artifact inspection  
- baseline CI wiring  
- validating the basic release-governance path  
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
Core lane = smallest deterministic release-governance lane
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
Release-grade reference run = materialized evidence release-governance reference
```

---

## Next implementation steps

Suggested next steps:

- Produce one non-stubbed release-grade reference run.  
- Archive its `status.json`, Quality Ledger, release authority manifest, and
  audit bundle.  
- Document the run in a short reference-run note.  
- Link the reference run from the README or documentation index.  
- Use the reference run as the baseline for future enterprise-grade release
  governance examples.
