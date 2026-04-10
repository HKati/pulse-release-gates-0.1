# Shadow Artifact Common v0

This page defines the shared contract scaffold for machine-readable shadow artifacts.

It exists to give non-normative shadow layers a common envelope before
layer-specific schema and checker rules are added.

This page does **not** make any shadow layer normative.

---

## Purpose

The common scaffold standardizes the minimum machine-readable envelope for
contracted shadow artifacts.

It is intentionally narrower than a full layer-specific contract.

It defines:

- the shared artifact envelope,
- common run-reality vocabulary,
- common verdict vocabulary,
- basic semantic consistency rules,
- and a reusable checker entrypoint.

Layer-specific contracts may extend this scaffold, but they should not weaken it.

---

## Required top-level fields

A common shadow artifact must contain:

- `artifact_version`
- `layer_id`
- `producer`
- `created_utc`
- `run_reality_state`
- `verdict`
- `source_artifacts`
- `relation_scope`
- `summary`
- `reasons`

### `artifact_version`

Layer-specific artifact version string.

Examples:

- `relational_gain_shadow_v0`
- `epf_comparison_v0`

### `layer_id`

Stable repo-level shadow layer identifier.

### `producer`

Object with at least:

- `name`
- `version`

### `created_utc`

RFC3339 / ISO-8601 timestamp in UTC.

### `run_reality_state`

Allowed values:

- `real`
- `partial`
- `stub`
- `degraded`
- `invalid`
- `absent`

### `verdict`

Allowed values:

- `pass`
- `warn`
- `fail`
- `unknown`
- `invalid`
- `absent`

### `source_artifacts`

Array of source artifact references.

Each entry must include at least one of:

- `path`
- `artifact_id`

Optional fields may include:

- `sha256`
- `role`

### `relation_scope`

Required relation-context identifier for the artifact.

This field states which relational context the artifact describes.

Without `relation_scope`, audit trails and cross-run comparison can become
ambiguous for layers that emit more than one relation surface.

Allowed shapes:

- non-empty string
- non-empty array of non-empty strings
- non-empty object for layer-specific structured scope

`relation_scope` must remain specific enough to distinguish parallel
relation outputs emitted by the same layer family.

It is required even for `absent` runs.

Absence of input is still a scoped result, not an unscoped result.

### `summary`

Object with at least:

- `headline`

Optional fields may include:

- `details`

### `reasons`

Non-empty array of machine-readable reason objects.

Each reason must include:

- `code`
- `message`

Optional:

- `severity`

---

## Optional top-level fields

The common scaffold also allows:

- `contract_checker_version`
- `foldin_eligible`
- `degraded_reasons`
- `checks`
- `payload`

Layer-specific contracts may require some of these.

---

## Common semantic rules

The common checker must enforce the following rules.

### Relation scope requirements

`relation_scope` must always be present.

It must identify the relation context being described, including
`absent` runs.

### Real runs

If `run_reality_state == "real"`:

- `degraded_reasons` must be absent or empty
- `verdict` must not be `absent`
- `verdict` must not be `invalid`

### Partial / stub / degraded runs

If `run_reality_state` is one of:

- `partial`
- `stub`
- `degraded`

then `degraded_reasons` must exist and must be non-empty.

### Absent runs

If `run_reality_state == "absent"`:

- `verdict` must be `absent`
- `foldin_eligible` must not be `true`

### Invalid runs

If `run_reality_state == "invalid"`:

- `verdict` must be `invalid`
- `foldin_eligible` must not be `true`

### Source requirements

If `run_reality_state != "absent"`:

- `source_artifacts` must be present
- `source_artifacts` must be an array
- `source_artifacts` must not be empty

### Reason requirements

`reasons` must always be a non-empty array.

---

## Neutral absence mode

The common checker supports a neutral absence mode for optional shadow inputs.

When called with `--if-input-present`:

- missing input file is not treated as a hard failure
- the checker emits a neutral result
- exit status remains success

This supports optional shadow workflows without turning missing inputs into release noise.

---

## Checker CLI

The shared checker entrypoint is:

```text
PULSE_safe_pack_v0/tools/check_shadow_artifact_contract.py
```

Expected usage:

```bash
python PULSE_safe_pack_v0/tools/check_shadow_artifact_contract.py \
  --input path/to/artifact.json \
  --expected-layer-id relational_gain_shadow
```

Neutral absence mode:

```bash
python PULSE_safe_pack_v0/tools/check_shadow_artifact_contract.py \
  --input path/to/artifact.json \
  --expected-layer-id relational_gain_shadow \
  --if-input-present
```

Optional JSON result output:

```bash
python PULSE_safe_pack_v0/tools/check_shadow_artifact_contract.py \
  --input path/to/artifact.json \
  --output path/to/result.json
```

---

## Extension rule

Layer-specific contracts should extend this scaffold by adding:

- layer-specific schema,
- layer-specific semantic rules,
- layer-specific fixture matrix,
- and layer-specific non-interference tests.

The common scaffold is the floor, not the ceiling.

---

## Acceptance rule for PR-2

PR-2 is complete when:

- the common schema exists,
- the shared semantic checker exists,
- fixtures exist for pass / degraded / absent / invalid cases,
- a test file validates the checker,
- and no normative release behavior changed.

That is enough to begin Relational Gain contract hardening on top of the common scaffold.
