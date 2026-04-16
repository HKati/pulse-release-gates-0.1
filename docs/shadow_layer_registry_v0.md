# Shadow Layer Registry v0

The Shadow Layer Registry v0 is the machine-readable registry surface for
shadow layers.

It records shadow-layer contract state, authority boundary, entrypoints,
artifacts, schema/checker surfaces, and supporting validation assets.

It is a governance and contract surface.

It is **not** a release gate.

---

## Purpose

The registry exists to make shadow-layer status machine-readable.

It provides a single place to record:

- layer identity,
- contract stage,
- target stage,
- authority boundary,
- artifact and fold-in surfaces,
- schema and checker references,
- fixtures and tests,
- and run-reality states.

This lets repo-level consumers reason about shadow layers without
inventing layer state ad hoc from scattered docs.

---

## Current registry stack

Current machine-readable registry file:

```text
shadow_layer_registry_v0.yml
```

Current schema:

```text
schemas/shadow_layer_registry_v0.schema.json
```

Current semantic checker:

```text
PULSE_safe_pack_v0/tools/check_shadow_layer_registry.py
```

Current dedicated workflow:

```text
.github/workflows/shadow_layer_registry.yml
```

Current canonical positive fixture:

```text
tests/fixtures/shadow_layer_registry_v0/pass.json
```

Current checker regression tests:

```text
tests/test_check_shadow_layer_registry.py
```

---

## Role

The registry is intended to answer repo-level questions such as:

- Which shadow layers are machine-registered?
- What stage is each layer in?
- Which checker and schema define the layer contract?
- Where is the layer artifact expected?
- Where does it fold into `status.json`, if at all?
- What tests and fixtures currently back the layer?

This is useful for governance, renderer discipline, and future registry-driven tooling.

---

## Non-goals

The registry does **not**:

- create normative authority,
- change `check_gates.py` behavior,
- write under `gates.*`,
- promote a layer merely by registry presence,
- or alter release semantics.

A layer being present in the registry means it is machine-registered.

It does **not** mean it is release-authoritative.

---

## Current format

Top-level shape:

```yaml
version: "shadow_layer_registry_v0"
layers:
  - ...
```

Each layer entry may describe:

- `layer_id`
- `family`
- `current_stage`
- `target_stage`
- `default_role`
- `consumer_authority`
- `owner_surface`
- `primary_entrypoint`
- `primary_artifact`
- `status_foldin`
- `schema`
- `semantic_checker`
- `fixtures`
- `tests`
- `run_reality_states`
- `promotion_blockers`
- `normative`
- `notes`

The schema and checker together define which of these are required and
which stage-dependent constraints apply.

---

## Stage model

The current contract-stage vocabulary is:

- `research`
- `shadow-contracted`
- `advisory`
- `release-candidate`
- `release-required`

`current_stage` records current classification.

`target_stage` records intended movement only.

`target_stage` must not be used as a substitute for current status.

---

## Authority model

The current consumer-authority vocabulary is:

- `display-only`
- `review-only`
- `advisory-only`
- `policy-bound`

This describes how the layer may be consumed.

It does **not** create authority by itself.

---

## Registry invariants

The registry must satisfy all of the following:

- `version` must match the registry contract version
- each `layer_id` must be unique
- `current_stage` must use the defined vocabulary
- `target_stage`, if present, must not be lower than `current_stage`
- higher-stage entries must carry their supporting contract surfaces
- repo-relative referenced paths must remain well-formed
- `normative: true` implies `current_stage: release-required`
- `current_stage: release-required` implies `normative: true`

These rules are enforced by both:

- schema-level validation where possible
- semantic checker validation where schema alone is not sufficient

---

## Current registered layers

The current registry is seeded with:

```text
relational_gain_shadow
epf_shadow_experiment_v0
```

### relational_gain_shadow

Current recorded state:

- `current_stage: shadow-contracted`
- `target_stage: advisory`
- `consumer_authority: review-only`
- `normative: false`

Current registered surfaces include:

- `.github/workflows/relational_gain_shadow.yml`
- `schemas/relational_gain_shadow_v0.schema.json`
- `PULSE_safe_pack_v0/tools/check_relational_gain_contract.py`
- `tests/fixtures/relational_gain_shadow_v0/pass.json`
- `tests/fixtures/relational_gain_shadow_v0/warn.json`
- `tests/fixtures/relational_gain_shadow_v0/fail.json`
- `tests/test_check_relational_gain_contract.py`
- `tests/test_relational_gain_non_interference.py`

### epf_shadow_experiment_v0

Current recorded state:

- `current_stage: research`
- `target_stage: shadow-contracted`
- `consumer_authority: review-only`
- `normative: false`

Primary registered surface:

- `.github/workflows/epf_experiment.yml`
- `epf_shadow_run_manifest.json`
- `schemas/epf_shadow_run_manifest_v0.schema.json`
- `PULSE_safe_pack_v0/tools/check_epf_shadow_run_manifest_contract.py`
- `tests/fixtures/epf_shadow_run_manifest_v0/pass.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/degraded.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/stub.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/partial.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/changed_without_warn.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/changed_exceeds_total_gates.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/example_count_exceeds_changed.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/real_zero_changed_wrong_verdict.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/same_status_paths.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/missing_epf_report_source_artifact.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/invalid_overall_without_invalid_branch.json`
- `tests/fixtures/epf_shadow_run_manifest_v0/degraded_without_nonreal_branch.json`
- `tests/test_check_epf_shadow_run_manifest_contract.py`

Secondary contract-hardened diagnostic surface:

- `epf_paradox_summary.json`
- `schemas/epf_paradox_summary_v0.schema.json`
- `PULSE_safe_pack_v0/tools/check_epf_paradox_summary_contract.py`
- `tests/fixtures/epf_paradox_summary_v0/pass.json`
- `tests/fixtures/epf_paradox_summary_v0/changed_exceeds_total_gates.json`
- `tests/fixtures/epf_paradox_summary_v0/changed_positive_without_examples.json`
- `tests/fixtures/epf_paradox_summary_v0/duplicate_gate_examples.json`
- `tests/fixtures/epf_paradox_summary_v0/example_without_difference.json`
- `tests/fixtures/epf_paradox_summary_v0/examples_longer_than_changed.json`
- `tests/fixtures/epf_paradox_summary_v0/invalid_rc_string.json`
- `tests/fixtures/epf_paradox_summary_v0/changed_zero_with_examples.json`
- `tests/test_check_epf_paradox_summary_contract.py`

Interpretation:

- the broader EPF line remains `research`
- the primary machine-registered EPF surface is now the broader run manifest
- the paradox summary remains a secondary contract-hardened diagnostic artifact
- neither surface is normative

---

## Relationship to docs inventory

The repo also contains management-facing inventory surfaces such as:

- `docs/SHADOW_CONTRACT_PROGRAM_v0.md`
- `docs/OPTIONAL_LAYERS.md`

These remain useful, but they are not the same as machine-registration.

Important distinction:

- a docs inventory row is a documentation-level management surface
- a registry entry in `shadow_layer_registry_v0.yml` is a machine-readable registered state

A layer may be documented without yet being machine-registered.

---

## Relationship to workflow validation

The dedicated workflow:

```text
.github/workflows/shadow_layer_registry.yml
```

exists to validate the registry stack continuously.

It currently validates:

- the registry YAML itself,
- the canonical positive JSON fixture,
- the registry checker tests,
- and the registry checker output surface.

It also watches currently referenced Relational Gain surfaces, the EPF
primary run-manifest surfaces, and the EPF secondary paradox-summary
surfaces so registered layers cannot silently drift away from the
registry contract.

---

## Boundary

The registry is governance-facing and descriptive.

It may support:

- tooling,
- renderers,
- dashboards,
- review surfaces,
- and future registry-driven checks.

It may **not**:

- reinterpret release meaning,
- override required gates,
- or become normative without explicit policy and architecture changes.

Registry presence is not release authority.

---

## Summary

Shadow Layer Registry v0 is the machine-readable contract surface for
shadow-layer registration.

It records shadow-layer identity, stage, authority boundary, supporting
artifacts, and validation surfaces in a single repo-level registry.

It is schema-bound, checker-validated, fixture-backed, test-backed, and
workflow-wired.

It remains strictly non-normative.
