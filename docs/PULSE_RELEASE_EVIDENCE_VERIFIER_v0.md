# PULSE Release Evidence Verifier v0

## Status

Informational reference note / future implementation boundary.

This document records the intended verifier boundary for future release-grade evidence materialization work.

It also records the implemented verifier report schema anchor and relation-binding integrity checker anchor.

It is not a release-authority rule.

It does not define release authority.

It does not replace `check_gates.py`.

It does not reopen `--release-grade-materialized`.

It does not change gate policy, gate registry, status schema, CI allow/block behavior, DOI/Zenodo artifacts, release tags, or release artifacts.

## Purpose

This note records why a trusted release-evidence verifier is needed before local or self-declared artifacts can contribute to release-grade gate materialization.

The current release-grade materialized path remains fail-closed until such a verifier is implemented and wired.

Future verifier work should prevent release-required gates from being derived directly from:

- local detector materialization manifests
- generic external detector summaries
- refusal-delta summaries
- copied artifact-directory files
- self-declared boolean gate maps

The verifier boundary exists to qualify recorded evidence before it can be represented in `status.json`.

PULSEmech release authority remains the later path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

## Verifier Role

The release-evidence verifier is intended as an evidence-qualification layer.

A future verifier would receive candidate evidence inputs, validate their identity, provenance, subject binding, schema, digest, freshness, policy relation, registry relation, and relation bindings, then emit a verifier report.

A verifier report may support later gate materialization only when the evidence is verified by implemented checks.

The verifier report itself does not produce an allow/block release decision.

Verifier report states avoid release-authority wording and use evidence-qualification states:

```text
VERIFIED
FAILED
```

`VERIFIED` means that evidence is eligible for materialization by a future implemented materialization path.

`FAILED` means that evidence is not eligible to materialize release-required gates.

## Candidate Input Classes

A future release-evidence verifier may consume these input classes:

- detector evidence artifacts
- detector materialization reports
- external detector summaries
- refusal-delta evidence
- run identity metadata
- git / subject binding metadata
- policy and registry references
- artifact digests
- provenance records
- relation bindings

These inputs are not trusted merely because they exist.

They become usable only after implemented verifier checks pass.

## Intended Trust Properties

A future verifier should check properties such as:

- schema validity
- parseability
- canonical artifact path
- SHA-256 digest binding
- run identity binding
- subject / git SHA binding
- detector identity binding
- policy relation
- gate registry relation
- freshness / current-run relation
- non-stub / non-scaffold evidence state
- relation binding integrity
- absence of self-declared release-required gate promotion

This list is an implementation guide, not an active release-authority policy.

## Unsafe Promotion Patterns

This note treats the following direct mappings as unsafe unless a trusted verifier is implemented and explicitly validates them:

```text
detector_materialization_v0.json gates.* → status.gates.*
external summary pass/rate/value → status.gates.external_all_pass
refusal_delta_summary.json n/pass → status.gates.refusal_delta_evidence_present
local artifact existence → release-required gate true
self-declared boolean map → materialized release evidence
```

These files may be diagnostic inputs.

They may be recorded.

They may be inspected.

They may be included in an audit bundle.

They must not directly set release-required gates.

## Implemented Schema Anchor

The verifier report artifact shape is introduced as:

```text
schemas/release_evidence_verifier_report_v0.schema.json
```

Example failed report:

```text
examples/release_evidence_verifier_report_v0.failed.example.json
```

This schema defines the report structure for future verifier work.

It does not implement the verifier.

It does not make `--release-grade-materialized` permissive.

The current materialized prod path remains fail-closed until a trusted verifier is implemented and wired.

## Verifier Report Shape

The verifier report artifact is:

```text
release_evidence_verifier_report_v0.json
```

The report shape includes:

- `schema_version`
- `created_utc`
- `verifier_id`
- `verifier_version`
- `verifier_decision`
- `run_identity`
- `subject`
- `policy_binding`
- `registry_binding`
- `evidence_inputs`
- `verified_artifacts`
- `relation_bindings`
- `gate_materialization`
- `failed_checks`
- `warnings`

## Illustrative Failed Report Shape

```json
{
  "schema_version": "release_evidence_verifier_report_v0",
  "created_utc": "2026-01-01T00:00:00Z",
  "verifier_id": "pulse_release_evidence_verifier_v0",
  "verifier_version": "0.1.0",
  "verifier_decision": "FAILED",
  "run_identity": {
    "run_mode": "prod",
    "run_key": null,
    "git_sha": null
  },
  "subject": {
    "repository": null,
    "commit_sha": null,
    "release_candidate": null
  },
  "policy_binding": {
    "policy_path": "pulse_gate_policy_v0.yml",
    "policy_sha256": null,
    "policy_set": "required+release_required"
  },
  "registry_binding": {
    "registry_path": "pulse_gate_registry_v0.yml",
    "registry_sha256": null
  },
  "evidence_inputs": [],
  "verified_artifacts": [],
  "relation_bindings": [],
  "gate_materialization": {},
  "failed_checks": [
    "trusted verifier is not implemented",
    "no verified relation bindings present"
  ],
  "warnings": []
}
```

## Relation Binding Anchor

The verifier report artifact includes first-class relation bindings:

```text
relation_bindings
```

Relation bindings model the verified connections that make evidence eligible for future materialization.

They express relations such as:

```text
artifact → subject
artifact → run
artifact → policy
artifact → registry
artifact → digest
artifact → detector
artifact → gate
gate → policy
gate → verifier decision
```

This does not implement the verifier.

It does not make `--release-grade-materialized` permissive.

The current materialized prod path remains fail-closed until a trusted verifier is implemented and wired.

A future verifier may use relation bindings to expose transition-risk before release:

```text
missing relation
broken relation
stale relation
self-declared relation
unverified relation
```

A relation binding is not release authority.

A relation binding qualifies evidence for possible materialization only after verifier checks pass.

## Future Gate Materialization Direction

A future materialization path should only materialize release-required gates from an implemented verifier report when:

```text
verifier_decision == VERIFIED
```

and when each materialized gate is explicitly bound to verified evidence and verified relation bindings.

A future gate materialization entry should identify:

- gate id
- gate value
- source evidence artifact
- evidence digest
- evidence schema
- detector or check identity
- subject / git SHA binding
- policy relation
- relation binding ids
- verification result

Illustrative shape:

```json
{
  "gate_materialization": {
    "detectors_materialized_ok": {
      "value": true,
      "source": "release_evidence_verifier_report_v0",
      "verified": true,
      "evidence_artifacts": [
        {
          "path": "artifacts/detectors/detector_report.json",
          "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
          "schema_version": "detector_report_v0",
          "verified": true
        }
      ],
      "relation_bindings": [
        "detector_report_to_subject_commit"
      ],
      "policy_relation": "release_required"
    }
  }
}
```

## Relation Binding Integrity Checker

The verifier report relation-binding integrity checker is:

```text
PULSE_safe_pack_v0/tools/check_release_evidence_verifier_report_v0.py
```

Example command:

```text
python PULSE_safe_pack_v0/tools/check_release_evidence_verifier_report_v0.py \
  --report examples/release_evidence_verifier_report_v0.failed.example.json
```

The checker requires `jsonschema` for verifier report schema validation.

If `jsonschema` is unavailable, the checker fails closed.

Partial fallback validation is not allowed for `release_evidence_verifier_report_v0` reports.

After full schema validation, the checker applies relation integrity checks.

It fails closed when:

- `jsonschema` is unavailable
- schema validation cannot be completed
- `relation_bindings[].relation_id` values are duplicated
- `gate_materialization.*.relation_bindings[]` references a missing relation ID
- a referenced relation binding is not `verified=true`
- a `VERIFIED` gate materialization entry has no relation binding IDs
- verifier decision values use release-authority wording such as `PASS` or `ALLOW`

A `FAILED` report may have empty `gate_materialization`.

The checker does not implement the verifier.

It does not reopen `--release-grade-materialized`.

It does not replace `check_gates.py`.

It only checks whether a verifier report has internally consistent relation bindings.

## Current Fail-Closed State

The current `--release-grade-materialized` path is intentionally fail-closed until a trusted release-evidence verifier exists.

In the current hotfix state, local detector, external summary, and refusal-delta artifacts cannot set release-required gates true.

The materialized prod path may report which untrusted inputs were observed, but it must not promote those inputs into gate state.

This current behavior is implemented in code.

This document records the boundary and intended future direction.

## Relation to `run_all.py`

`run_all.py --mode prod --release-grade-materialized` is a preparation path.

At present, it remains fail-closed.

A future implementation may follow this sequence:

```text
candidate evidence inputs
→ release evidence verifier
→ release_evidence_verifier_report_v0.json
→ relation binding integrity check
→ verified gate materialization
→ status.json
→ release authority manifest
→ audit bundle
```

The verifier report should pass schema validation and relation integrity checks before any release-required gate is set to true.

## Relation to `check_gates.py`

`check_gates.py` remains the release-authority evaluator.

The verifier does not replace it.

The relation binding integrity checker does not replace it.

The verifier only qualifies evidence for possible materialization into `status.json`.

`check_gates.py` still evaluates the workflow-effective required gate set under declared policy and strict fail-closed CI enforcement.

## Relation to Quality Ledger

The Quality Ledger remains a reader surface.

It may display verifier report information after such a report exists.

It must not recompute verifier decisions.

It must not convert displayed evidence into release-required gate state.

It must not replace `status.json`, declared gate policy, materialized required gates, or fail-closed CI enforcement.

## Review Questions for Future Implementation PRs

A future PR that implements verifier wiring should answer:

- What verifier report is consumed?
- Which schema validates the report?
- Which subject / git SHA does the report bind?
- Which policy and registry digests does it bind?
- Which evidence artifacts are verified?
- Which relation bindings are verified?
- Which gate ids are materialized?
- Which evidence artifact supports each gate?
- Which relation binding supports each gate?
- What happens if the report is missing?
- What happens if one gate lacks verified evidence?
- What happens if one gate references a missing relation ID?
- What happens if relation IDs are duplicated?
- What prevents a self-declared artifact from becoming release evidence?

These are review questions, not an active release-authority rule in this document.

## Security Boundary Note

The verifier boundary exists because release-grade gate state is security-critical.

The following patterns should be treated as security risks in future implementation work:

- self-declared detector booleans becoming release-required gates
- generic external summaries becoming `external_all_pass`
- refusal summaries becoming release evidence without subject binding
- artifact existence being treated as evidence validity
- copied files producing non-stubbed diagnostics
- local artifact directory control producing release-grade PASS
- gate materialization referencing missing relation IDs
- duplicate relation IDs making gate relation references ambiguous
- unverified relation bindings supporting gate materialization

The correct current behavior is fail-closed until evidence is verified by an implemented verifier.

## Minimal Anchor

Evidence is not trusted because it exists.

Evidence becomes eligible for materialization only after verification.

Verification qualifies evidence for materialization.

Relation bindings connect evidence to the release-state transformation path.

Relation binding integrity prevents missing, duplicate, or unverified relations from supporting gate materialization.

Materialization writes verified gate state into `status.json`.

Release authority remains the PULSEmech path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

## Fail-closed verifier report builder skeleton

The fail-closed verifier report builder skeleton is:

```text
PULSE_safe_pack_v0/tools/build_release_evidence_verifier_report_v0.py
```

Example command:

```text
python PULSE_safe_pack_v0/tools/build_release_evidence_verifier_report_v0.py \
  --out PULSE_safe_pack_v0/artifacts/release_evidence_verifier_report_v0.json
```

The builder emits a `release_evidence_verifier_report_v0.json` report with:

```text
verifier_decision = FAILED
verified_artifacts = []
relation_bindings = []
gate_materialization = {}
```

Candidate evidence inputs may be recorded, hashed, and marked as untrusted candidate inputs.

The builder does not verify evidence.

It does not emit `VERIFIED`.

It does not materialize gates.

It does not write `status.json`.

It does not reopen `--release-grade-materialized`.

It does not replace `check_gates.py`.

The builder validates its output through the release evidence verifier report checker.

If the report is invalid or relation-integrity checks fail, the builder fails closed.
