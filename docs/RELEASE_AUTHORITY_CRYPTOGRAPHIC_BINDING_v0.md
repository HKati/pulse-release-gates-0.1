````markdown
# Release Authority Cryptographic Binding v0

This document defines the cryptographic binding layer for PULSE release-authority artifacts. It does not change PULSEmech decision semantics; it makes the recorded authority path verifiable as an artifact relationship.

## Purpose

Release Authority Cryptographic Binding v0 defines the artifact relationship that later cryptographic attestation will bind.

The layer records how a PULSE release-authority run is connected across:

- recorded run identity,
- source commit identity,
- `status.json`,
- declared gate policy,
- materialized required gate set,
- declared-policy CI decision,
- Quality Ledger reader artifact,
- release authority manifest / trace artifact,
- binding subject list,
- binding hash.

The goal is to make the recorded PULSE authority path portable, digest-backed, and externally verifiable as an artifact relationship.

## Carrier roles

| Carrier | Artifact / path | Role |
|---|---|---|
| Authority carrier | `status.json` → declared gate policy → materialized required gate set → strict fail-closed CI enforcement | Carries the PULSEmech release-authority path |
| Provenance carrier | `artifact_provenance_binding_v0.json` | Records the artifact relationship around the authority path |
| Reader carrier | Quality Ledger | Presents the recorded state as a public reader surface |
| Attestation carrier | later cryptographic attestation over the provenance binding | Verifies the provenance binding as an attested artifact relationship |

Artifact Provenance Binding v0 is the provenance carrier for the PULSEmech authority path.

## Authority path

The PULSEmech authority path remains:

```text
status.json
→ declared gate policy
→ materialized required gate set
→ strict fail-closed CI enforcement
→ CI allow/block release decision
```

Release Authority Cryptographic Binding v0 records the artifact relationship around that path.

## Cryptographic binding target

The binding target is the recorded release-authority artifact set:

```text
recorded_run_identity
+ git_sha
+ status_json_sha256
+ declared_policy_sha256
+ materialized_required_gate_set_sha256
+ declared_policy_ci_decision
+ quality_ledger_sha256
+ release_authority_manifest_sha256
+ binding_subjects
+ binding_hash
```

This artifact set becomes the subject of later cryptographic attestation.

## Provenance carrier

The provenance carrier is:

```text
artifact_provenance_binding_v0.json
```

Suggested top-level identity:

```json
{
  "schema_id": "pulse.release_authority_cryptographic_binding.v0",
  "schema_version": "0.1.0",
  "producer": {
    "name": "build_artifact_provenance_binding_v0.py",
    "version": "0.1.0"
  },
  "created_utc": "..."
}
```

## Authority carrier binding

The `authority_carrier` section records the artifacts that carry the PULSEmech authority path.

Suggested shape:

```json
{
  "authority_carrier": {
    "status_json": {
      "path": "PULSE_safe_pack_v0/artifacts/status.json",
      "sha256": "..."
    },
    "declared_gate_policy": {
      "path": "pulse_gate_policy_v0.yml",
      "sha256": "..."
    },
    "materialized_required_gate_set": {
      "source": "policy:required",
      "gate_ids": ["..."],
      "sha256": "..."
    },
    "declared_policy_ci_decision": {
      "label": "PROD-PASS",
      "source": "check_gates.py"
    }
  }
}
```

The materialized required gate set digest is computed from a canonical JSON representation of the selected gate source and ordered gate IDs.

Suggested canonical input:

```json
{
  "source": "policy:required",
  "gate_ids": ["gate_a", "gate_b", "gate_c"]
}
```

## Reader carrier binding

The `reader_carrier` section connects the Quality Ledger artifact to the same recorded run.

Suggested shape:

```json
{
  "reader_carrier": {
    "quality_ledger": {
      "path": "PULSE_safe_pack_v0/artifacts/report_card.html",
      "sha256": "..."
    }
  }
}
```

## Trace carrier binding

The `trace_carrier` section connects release-authority trace artifacts to the same recorded run.

Suggested shape:

```json
{
  "trace_carrier": {
    "release_authority_manifest": {
      "path": "PULSE_safe_pack_v0/artifacts/release_authority_v0.json",
      "sha256": "..."
    }
  }
}
```

## Binding subjects

The `binding_subjects` array lists the artifacts bound by the provenance record.

Suggested shape:

```json
{
  "binding_subjects": [
    {
      "role": "status_json",
      "path": "PULSE_safe_pack_v0/artifacts/status.json",
      "sha256": "..."
    },
    {
      "role": "declared_gate_policy",
      "path": "pulse_gate_policy_v0.yml",
      "sha256": "..."
    },
    {
      "role": "materialized_required_gate_set",
      "path": "inline:authority_carrier.materialized_required_gate_set",
      "sha256": "..."
    },
    {
      "role": "quality_ledger",
      "path": "PULSE_safe_pack_v0/artifacts/report_card.html",
      "sha256": "..."
    },
    {
      "role": "release_authority_manifest",
      "path": "PULSE_safe_pack_v0/artifacts/release_authority_v0.json",
      "sha256": "..."
    }
  ]
}
```

## Binding hash

The binding record carries a `binding_hash`.

Suggested rule:

```text
binding_hash = sha256(canonical_json(binding_without_binding_hash))
```

The binding hash is the compact digest of the recorded release-authority artifact relationship.

## Verification model

A verifier recomputes:

- `status.json` digest,
- declared policy digest,
- materialized required gate set digest,
- Quality Ledger digest,
- release authority manifest digest,
- binding subject digests,
- `binding_hash`.

Verification accepts the binding when the recorded artifact relationship matches the current artifact set.

## Introduction path

The cryptographic binding layer is introduced in stages.

### Stage 1 — Binding definition

Define the release-authority cryptographic binding boundary and artifact relationship.

### Stage 2 — Binding materialization

Generate:

```text
PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
```

### Stage 3 — Binding verification

Verify the binding by recomputing artifact digests and the binding hash.

### Stage 4 — CI materialization

Materialize and verify the binding in CI after the recorded run artifacts exist.

### Stage 5 — Cryptographic attestation

Attest the binding artifact as the compact carrier of the recorded release-authority artifact relationship.

Primary attestation subject:

```text
artifact_provenance_binding_v0.json
```

Carried subjects:

- `status.json`,
- declared gate policy,
- materialized required gate set,
- Quality Ledger reader artifact,
- release authority manifest / trace artifact,
- `binding_hash`.

## Mechanical value

Release Authority Cryptographic Binding v0 gives PULSE a digest-backed artifact relationship around the authority path.

It lets a reviewer, verifier, CI job, archive, or later attestation system inspect the same connected artifact set:

```text
recorded run identity
+ source commit
+ status artifact
+ declared policy
+ materialized required gate set
+ CI decision record
+ reader artifact
+ trace artifact
+ binding hash
```

This is the cryptographic binding boundary for PULSE release-authority artifacts.
````
