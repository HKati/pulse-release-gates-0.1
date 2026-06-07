# PULSE Release Evidence Verifier v0

## Status

Informational reference note / future implementation boundary.

This document records the intended verifier boundary for future release-grade evidence materialization work.

It is not an implemented contract, policy, schema, CI rule, or release-authority rule.

It does not define release authority.

It does not replace `check_gates.py`.

It does not change gate policy, gate registry, status schema, CI allow/block behavior, DOI/Zenodo artifacts, release tags, or release artifacts.

## Purpose

This note records why a trusted release-evidence verifier is needed before local or self-declared artifacts can contribute to release-grade gate materialization.

The current release-grade materialized path remains fail-closed until such a verifier is implemented.

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

A future verifier would receive candidate evidence inputs, validate their identity, provenance, subject binding, schema, digest, freshness, and policy relation, then emit a verifier report.

A verifier report may support later gate materialization only when the evidence is verified by implemented checks.

The verifier report itself does not produce an allow/block release decision.

Verifier report states should avoid release-authority wording and use evidence-qualification states such as:

```text
VERIFIED
FAILED
```

`VERIFIED` would mean that the evidence is eligible for materialization by the implemented materialization path.

`FAILED` would mean that the evidence is not eligible to materialize release-required gates.

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
- absence of self-declared release-required gate promotion

This list is an implementation guide, not an active repository policy.

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

They should not directly set release-required gates.

## Future Verifier Output

A future verifier may emit:

```text
release_evidence_verifier_report_v0.json
```

A future report shape may include:

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

This document does not implement or enforce that schema.

A separate schema PR would be required before this report becomes an implemented artifact contract.

## Illustrative Report Shape

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

## Future Gate Materialization Direction

A future materialization path should only materialize release-required gates from an implemented verifier report when:

```text
verifier_decision == VERIFIED
```

and when each materialized gate is explicitly bound to verified evidence.

A future gate materialization entry should identify:

- gate id
- source evidence artifact
- evidence digest
- evidence schema
- detector or check identity
- subject / git SHA binding
- policy relation
- verification result

Illustrative shape:

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

## Current Fail-Closed State

The current `--release-grade-materialized` path is intentionally fail-closed until a trusted release-evidence verifier exists.

In the current hotfix state, local detector, external summary, and refusal-delta artifacts cannot set release-required gates true.

The materialized prod path may report which untrusted inputs were observed, but it must not promote those inputs into gate state.

This current behavior is implemented in code; this document only records the boundary and intended future direction.

## Relation to `run_all.py`

`run_all.py --mode prod --release-grade-materialized` is a preparation path.

At present, it remains fail-closed.

A future implementation may follow this sequence:

```text
candidate evidence inputs
→ release evidence verifier
→ release_evidence_verifier_report_v0.json
→ verified gate materialization
→ status.json
→ release authority manifest
→ audit bundle
```

The verifier report should be checked before any release-required gate is set to true.

## Relation to `check_gates.py`

`check_gates.py` remains the release-authority evaluator.

The verifier does not replace it.

The verifier only qualifies evidence for possible materialization into `status.json`.

`check_gates.py` still evaluates the workflow-effective required gate set under declared policy and strict fail-closed CI enforcement.

## Relation to Quality Ledger

The Quality Ledger remains a reader surface.

It may display verifier report information after such a report exists.

It must not recompute verifier decisions.

It must not convert displayed evidence into release-required gate state.

## Review Questions for Future Implementation PRs

A future PR that implements verifier wiring should answer:

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

These are review questions, not an active rejection rule in this document.

## Security Boundary Note

The verifier boundary exists because release-grade gate state is security-critical.

The following patterns should be treated as security risks in future implementation work:

- self-declared detector booleans becoming release-required gates
- generic external summaries becoming `external_all_pass`
- refusal summaries becoming release evidence without subject binding
- artifact existence being treated as evidence validity
- copied files producing non-stubbed diagnostics
- local artifact directory control producing release-grade PASS

The correct current behavior is fail-closed until evidence is verified by an implemented verifier.

## Minimal Anchor

Evidence is not trusted because it exists.

Evidence becomes eligible for materialization only after verification.

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
