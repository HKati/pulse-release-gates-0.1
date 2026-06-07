# PULSE Release Evidence Verifier v0

## Status

Design contract / verifier boundary.

This document defines the trusted release-evidence verifier boundary required before release-grade evidence can be materialized into `status.json`.

It does not define release authority.

It does not replace `check_gates.py`.

It does not change gate policy, gate registry, status schema, CI allow/block behavior, DOI/Zenodo artifacts, release tags, or release artifacts.

## Purpose

The release-evidence verifier prevents local or self-declared artifacts from becoming release-required gate state.

A release-grade candidate must not derive release-required gates directly from:

- local detector materialization manifests
- generic external detector summaries
- refusal-delta summaries
- copied artifact-directory files
- self-declared boolean gate maps

The verifier exists to decide whether recorded evidence is eligible to be materialized into `status.json`.

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

The verifier is an evidence-qualification layer.

It receives candidate evidence inputs, validates their identity, provenance, subject binding, schema, digest, freshness, and policy relation, then emits a verifier report.

The verifier report may permit gate materialization only when the evidence is verified.

The verifier report must not produce an allow/block release decision.

Verifier decisions are limited to:

```text
VERIFIED
FAILED
```

`VERIFIED` means the evidence is eligible for materialization.

`FAILED` means the evidence must not materialize release-required gates.

## Required Input Classes

A release-grade evidence verifier may consume these input classes:

- detector evidence artifacts
- detector materialization reports
- external detector summaries
- refusal-delta evidence
- run identity metadata
- git / subject binding metadata
- policy and registry references
- artifact digests
- provenance records

These inputs are not trusted merely because they exist.

They become usable only after verifier checks pass.

## Trust Requirements

A candidate evidence artifact is acceptable only when these properties are verified:

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
- absence of self-declared release-required gate promotion

## Forbidden Promotion

The following mappings are forbidden without a trusted verifier:

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

## Verifier Output

The verifier emits:

```text
release_evidence_verifier_report_v0.json
```

The report must include:

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
- `gate_materialization`
- `failed_checks`
- `warnings`

## Minimal Report Shape

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
  "gate_materialization": {},
  "failed_checks": [
    "trusted verifier is not implemented"
  ],
  "warnings": []
}
```

## Gate Materialization Rule

Release-required gates may be materialized only from a verifier report with:

```text
verifier_decision == VERIFIED
```

and a gate materialization block that explicitly binds each gate to verified evidence.

A valid gate materialization entry must identify:

- gate id
- source evidence artifact
- evidence digest
- evidence schema
- detector or check identity
- subject / git SHA binding
- policy relation
- verification result

Example shape:

```json
{
  "gate_materialization": {
    "detectors_materialized_ok": {
      "value": true,
      "source": "release_evidence_verifier_report_v0",
      "evidence_artifacts": [
        {
          "path": "artifacts/detectors/detector_report.json",
          "sha256": "..."
        }
      ],
      "verified": true
    }
  }
}
```

## Fail-Closed Rule

If the verifier report is missing, invalid, stale, unbound, or `FAILED`, release-grade materialization must fail closed.

In that state, the materialized prod path must not write:

- `status.json`
- `report_card.html`
- `release_authority_v0.json`
- `release_authority_audit_bundle/`

The materialized prod path may report which untrusted inputs were observed, but it must not promote them into gate state.

## Relation to `run_all.py`

`run_all.py --mode prod --release-grade-materialized` remains a preparation path.

Until a trusted release-evidence verifier exists, this path remains fail-closed.

Future wiring must follow this sequence:

```text
candidate evidence inputs
→ release evidence verifier
→ release_evidence_verifier_report_v0.json
→ verified gate materialization
→ status.json
→ release authority manifest
→ audit bundle
```

The verifier report must be checked before any release-required gate is set to true.

## Relation to `check_gates.py`

`check_gates.py` remains the release-authority evaluator.

The verifier does not replace it.

The verifier only determines whether evidence can be materialized into `status.json`.

`check_gates.py` still evaluates the workflow-effective required gate set under declared policy and strict fail-closed CI enforcement.

## Relation to Quality Ledger

The Quality Ledger remains a reader surface.

It may display verifier report information.

It must not recompute verifier decisions.

It must not convert displayed evidence into release-required gate state.

## Review Rule

Any future PR that wires release-grade evidence materialization must answer:

- What verifier report is consumed?
- Which schema validates the report?
- Which subject / git SHA does the report bind?
- Which policy and registry digests does it bind?
- Which evidence artifacts are verified?
- Which gate ids are materialized?
- Which evidence artifact supports each gate?
- What happens if the report is missing?
- What happens if one gate lacks verified evidence?
- What prevents a self-declared artifact from becoming release evidence?

A PR must be rejected if it allows local self-declared artifacts to directly set release-required gates.

## Security Boundary

The verifier boundary exists because release-grade gate state is security-critical.

The following are security failures:

- self-declared detector booleans becoming release-required gates
- generic external summaries becoming `external_all_pass`
- refusal summaries becoming release evidence without subject binding
- artifact existence being treated as evidence validity
- copied files producing non-stubbed diagnostics
- local artifact directory control producing release-grade PASS

The correct behavior is fail-closed until evidence is verified.

## Minimal Anchor

Evidence is not trusted because it exists.

Evidence is trusted only after verification.

Verification qualifies evidence for materialization.

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
