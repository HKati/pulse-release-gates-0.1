# Artifact Provenance Binding v0

Artifact Provenance Binding v0 is the machine-readable provenance carrier for the PULSEmech authority path.

Artifact provenance binding is a traceability / provenance carrier.
It does not create release authority by itself and does not replace `status.json`,
declared policy, workflow-effective materialized required gates, `check_gates.py`,
or strict fail-closed CI enforcement.

## Mechanical role

The binding records the digest-backed artifact relationship around a recorded PULSE release-authority run.

It connects:

- recorded run identity,
- source commit identity,
- `status.json`,
- declared gate policy,
- workflow-effective required gate set,
- strict CI gate-enforcement result,
- release-decision materialization record,
- Quality Ledger reader artifact,
- release authority manifest / trace artifact,
- binding subjects,
- binding hash.

## Carrier roles

| Carrier | Artifact | Mechanical role |
|---|---|---|
| Authority carrier | `status.json` + declared policy + workflow-effective required gate set + strict CI enforcement | Carries release authority |
| Binding carrier | `artifact_provenance_binding_v0.json` | Carries digest-backed artifact relation |
| Verification carrier | `verify_artifact_provenance_binding_v0.py` | Recomputes and checks artifact relation |
| Reader carrier | Quality Ledger | Presents recorded state |
| Trace carrier | release authority manifest / release decision artifact | Preserves reconstruction and decision trace |
| Attestation carrier | later cryptographic attestation | Attests the binding carrier |

## Binding artifact

The binding artifact is:

```text
PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
```

The binding records:

```text
recorded_run_identity
+ git_sha
+ status_json_digest
+ declared_gate_policy_digest
+ workflow_effective_required_gate_set_digest
+ strict_ci_gate_enforcement_result
+ release_decision_materialization_record
+ quality_ledger_digest
+ release_authority_manifest_digest
+ binding_subjects
+ binding_hash
```

## Workflow-effective gate-set rule

The binding records the workflow-effective required gate set, not a static policy placeholder.

Resolution order:

```text
1. explicit CLI policy sets
2. status.metrics.required_gates
3. status.metrics.required_gate_set
4. run_mode fallback:
   demo/core -> core_required
   prod -> required
```

Gate order is preserved from the effective source.

Duplicate gate IDs are de-duplicated by first occurrence.

## Strict CI gate-enforcement and release-decision materialization

`check_gates.py` is the strict CI gate-enforcement carrier.

It records:

```text
allow / block
exit_code
```

Release-level labels are carried by release-decision materialization.

The split is:

```text
check_gates.py
= strict CI gate-enforcement carrier

release_decision_v0.json / materialize_release_decision.py
= release-decision materialization carrier
```

## Canonical JSON byte rule

Structured-object digests use canonical JSON bytes:

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

```text
- object keys sorted
- no insignificant whitespace
- UTF-8 bytes
- no trailing newline
- NaN / Infinity rejected
- digest field omitted from the object being digested
```

## Binding hash

The binding carries:

```text
binding_hash
```

Rule:

```text
binding_hash = sha256(canonical_json_bytes(binding_without_binding_hash))
```

The binding hash is the compact digest of the recorded artifact relationship.

## Verification carrier

The verification carrier is:

```text
PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
```

The verifier recomputes:

- file digests,
- inline object digests,
- workflow-effective required gate-set digest,
- strict CI gate-enforcement digest,
- binding subject digests,
- binding hash.

Verification accepts the binding when the recorded artifact relationship matches the current artifact set.

Verification reports mismatch when a bound artifact changes, disappears, or no longer matches its recorded digest.

## Later attestation subject

The primary future attestation subject is:

```text
artifact_provenance_binding_v0.json
```

The binding carrier lets the attestation layer bind one compact artifact relation record instead of scattering the authority artifact set across unrelated file signatures.

## Boundary

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Artifact Provenance Binding v0 carries the digest-backed artifact relationship around that authority path.
