# Release-grade reference run v0 example package

This directory contains a minimal example package for a PULSE release-grade
reference run.

It is intended to show the expected artifact shape for a non-stubbed,
materialized-evidence release-grade run.

This package is an example / reference surface. It is not proof that a real
production release occurred.

---

## Files

```text
status.release_grade.pass.example.json
release_authority_v0.release_grade.pass.example.json
```

### `status.release_grade.pass.example.json`

Example final `status.json` for a successful release-grade run.

It shows:

- `metrics.run_mode = "prod"`,
- release-required evidence gates present and literal `true`,
- materialized detector evidence,
- no stubbed gate surface,
- external evidence presence and pass gates.

### `release_authority_v0.release_grade.pass.example.json`

Example `release_authority_v0.json` audit manifest for the same successful
release-grade run.

It shows:

- `run_identity.run_mode = "prod"`,
- `authority.policy_set = "required+release_required"`,
- `authority.release_required_materialized = true`,
- release-required gates included in `effective_required_gates`,
- no failed required gates,
- no missing required gates,
- `decision.state = "PROD-PASS"`,
- diagnostics preserved as non-normative.

---

## How to inspect this example

From the repository root:

```console
python PULSE_safe_pack_v0/tools/check_release_grade_reference_run_v0.py \
  --status examples/release_grade_reference_run_v0/status.release_grade.pass.example.json \
  --manifest examples/release_grade_reference_run_v0/release_authority_v0.release_grade.pass.example.json
```

Expected result:

```text
OK: release-grade reference run criteria satisfied
```

---

## Authority boundary

This example does not define release semantics.

The release-authority path remains:

```text
status.json
+ declared gate policy
+ workflow-effective required gate set
+ check_gates.py
+ primary CI workflow
= release authority
```

This package is a reference example for the release-grade artifact shape.

It does not:

- create a new policy,
- create a new gate set,
- replace `check_gates.py`,
- replace `status.json`,
- promote diagnostic surfaces into release authority,
- or prove a real production release occurred.

---

## Relation to Core smoke runs

Core smoke / integration runs are useful for validating the minimal PULSE lane.

Release-grade reference runs are stronger. They should show materialized evidence,
release-required gates, external evidence presence, non-stubbed diagnostics, and
a release-authority audit manifest.

Compact distinction:

```text
Core smoke surface = integration / visibility surface
Release-grade reference run = materialized evidence release-governance reference
```
