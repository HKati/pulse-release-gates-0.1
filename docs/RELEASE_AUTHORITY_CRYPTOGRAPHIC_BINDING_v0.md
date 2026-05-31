# Release Authority Cryptographic Binding v0

This document defines the cryptographic binding layer for PULSE release-authority artifacts. It does not change PULSEmech decision semantics; it makes the recorded authority path verifiable as an artifact relationship.

## Purpose

Release Authority Cryptographic Binding v0 defines the artifact relationship that later cryptographic attestation will bind.

The layer records how a PULSE release-authority run is connected across:

- recorded run identity,
- source commit identity,
- `status.json`,
- declared gate policy,
- workflow-effective materialized required gate set,
- strict CI gate-enforcement result,
- release-decision materialization record,
- Quality Ledger reader artifact,
- release authority manifest / trace artifact,
- binding subject list,
- binding hash.

The goal is to make the recorded PULSE authority path portable, digest-backed, and externally verifiable as an artifact relationship.

## Carrier roles

| Carrier | Artifact / path | Role |
|---|---|---|
| Authority carrier | `status.json` → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement | Carries the PULSEmech release-authority path |
| Provenance carrier | `artifact_provenance_binding_v0.json` | Records the artifact relationship around the authority path |
| Reader carrier | Quality Ledger | Presents the recorded state as a public reader surface |
| Attestation carrier | later cryptographic attestation over the provenance binding | Verifies the provenance binding as an attested artifact relationship |

Artifact Provenance Binding v0 is the provenance carrier for the PULSEmech authority path.

## Authority path

The PULSEmech authority path remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
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
+ workflow_effective_required_gate_set_sha256
+ declared_policy_ci_result
+ release_decision_label
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

The `authority_carrier` section records the artifacts and effective gate materialization that carry the PULSEmech authority path.

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
      "effective_source": "workflow-effective:required+release_required",
      "policy_sets": ["required", "release_required"],
      "gate_ids": ["..."],
      "sha256": "..."
    },
    "declared_policy_ci_result": {
      "source": "check_gates.py",
      "result": "allow",
      "exit_code": 0
    },
    "release_decision": {
      "label": "PROD-PASS",
      "source": "release_decision_v0.json",
      "producer": "materialize_release_decision.py"
    }
  }
}
```

The materialized required gate set records the workflow-effective gate source.

For example:

- core / non-release CI runs may materialize `core_required`;
- release-grade runs may materialize `required + release_required`;
- explicit workflow or status metadata may record the effective selected gate set directly.

The binding hashes the effective required gate set enforced by CI for the recorded run.

`check_gates.py` carries the strict fail-closed gate-enforcement result.

Release-level labels such as `PROD-PASS`, `STAGE-PASS`, or `FAIL` are recorded as release-decision materialization outputs.

The binding records both layers:

- CI gate-enforcement result;
- release-decision label and its materialized source.

## Workflow-effective gate set

The workflow-effective gate set is the concrete gate set enforced for the recorded run.

It is represented as structured data before hashing.

Suggested canonical object:

```json
{
  "effective_source": "workflow-effective:required+release_required",
  "policy_sets": ["required", "release_required"],
  "gate_ids": ["gate_a", "gate_b", "gate_c"]
}
```

For a core / non-release run, the canonical object may be:

```json
{
  "effective_source": "workflow-effective:core_required",
  "policy_sets": ["core_required"],
  "gate_ids": ["gate_a", "gate_b"]
}
```

For a run whose required gates are recorded directly by status or workflow metadata, the canonical object may be:

```json
{
  "effective_source": "metrics.required_gates",
  "policy_sets": [],
  "gate_ids": ["gate_a", "gate_b"]
}
```

The binding uses the effective gate set that corresponds to the recorded CI enforcement path.

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

The Quality Ledger presents the recorded state as a public reader surface.

The cryptographic binding records which reader artifact belongs to the recorded authority artifact set.

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

Additional trace, audit, or preservation artifacts may be added as named binding subjects when they belong to the recorded run package.

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
      "role": "workflow_effective_required_gate_set",
      "path": "inline:authority_carrier.materialized_required_gate_set",
      "sha256": "..."
    },
    {
      "role": "declared_policy_ci_result",
      "path": "inline:authority_carrier.declared_policy_ci_result",
      "sha256": "..."
    },
    {
      "role": "release_decision",
      "path": "PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
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

Each subject records:

- role,
- path,
- sha256.

The role describes the artifact’s position in the release-authority binding set.

## Binding hash

The binding record carries a `binding_hash`.

The binding hash is the compact digest of the recorded release-authority artifact relationship.

Suggested rule:

```text
binding_hash = sha256(canonical_json_bytes(binding_without_binding_hash))
```

## Canonical JSON byte rule

All digests over structured JSON objects in this binding use the same canonical byte rule.

Canonical JSON bytes are produced as:

```python
json.dumps(
    value,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
).encode("utf-8")
```

Rules:

- object keys are sorted;
- no insignificant whitespace is emitted;
- UTF-8 bytes are hashed;
- no trailing newline is included;
- NaN and Infinity are not allowed;
- the value being hashed must not include its own digest field.

For `binding_hash`, the canonical object is the binding object with `binding_hash` omitted.

For `materialized_required_gate_set.sha256`, the canonical object is the effective required gate set object with its own `sha256` omitted.

For inline binding subjects, the canonical object is the referenced inline object with its own digest field omitted when present.

## Verification model

A verifier recomputes:

- `status.json` digest,
- declared policy digest,
- workflow-effective materialized required gate set digest,
- strict CI gate-enforcement result digest when represented inline,
- release-decision materialization digest when represented as an artifact,
- Quality Ledger digest,
- release authority manifest digest,
- binding subject digests,
- `binding_hash`.

Verification accepts the binding when the recorded artifact relationship matches the current artifact set.

Verification reports mismatch when a bound artifact changes, disappears, or no longer matches its recorded digest.

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

```text
status.json
declared gate policy
workflow-effective materialized required gate set
strict CI gate-enforcement result
release-decision materialization record
Quality Ledger reader artifact
release authority manifest / trace artifact
binding_hash
```

## Attestation carrier

The attestation carrier is the later cryptographic attestation over the provenance binding.

The attestation layer binds the recorded artifact relationship by signing or attesting the binding artifact and its subject set.

This makes the PULSE release-authority artifact relationship portable across CI, archive, publication, and review surfaces.

## Mechanical value

Release Authority Cryptographic Binding v0 gives PULSE a digest-backed artifact relationship around the authority path.

It lets a reviewer, verifier, CI job, archive, or later attestation system inspect the same connected artifact set:

```text
recorded run identity
+ source commit
+ status artifact
+ declared policy
+ workflow-effective materialized required gate set
+ strict CI gate-enforcement result
+ release-decision materialization record
+ reader artifact
+ trace artifact
+ binding hash
```

This is the cryptographic binding boundary for PULSE release-authority artifacts.

## Scope held by this document

This document defines the cryptographic binding layer and introduction path for PULSE release-authority artifacts.

The held carrier split is:

```text
Authority carrier:
status.json → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement

Provenance carrier:
artifact_provenance_binding_v0.json

Reader carrier:
Quality Ledger

Attestation carrier:
later cryptographic attestation over the provenance binding
```

Artifact Provenance Binding v0 is the provenance carrier for the PULSEmech authority path.
