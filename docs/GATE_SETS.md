# Gate sets

This page is a human-readable summary of the current policy-defined gate sets.

## Normative source of truth

The normative source of truth remains:

- `pulse_gate_policy_v0.yml`
- `PULSE_safe_pack_v0/tools/check_gates.py`
- `.github/workflows/pulse_ci.yml`

If this page and the policy disagree, the policy and workflow enforcement win.

## Current enforcement summary

- `pull_request` runs enforce `core_required`
- pushes to `main` enforce `core_required` by default
- version tag pushes (`v*` / `V*`) enter release-grade mode and enforce `required + release_required`
- `workflow_dispatch` runs enforce `core_required` by default; with `strict_external_evidence=true`, they enter release-grade mode and enforce `required + release_required`
- required gates are fail-closed on missing / false
- the `advisory` set is currently empty

## Gate matrix

| Gate | `core_required` | `required` |
|---|---:|---:|
| `pass_controls_refusal` | Yes | Yes |
| `pass_controls_sanit` | Yes | Yes |
| `sanitization_effective` | Yes | Yes |
| `q1_grounded_ok` | Yes | Yes |
| `q4_slo_ok` | Yes | Yes |
| `refusal_delta_pass` | No | Yes |
| `effect_present` | No | Yes |
| `external_all_pass` | No | Yes |
| `psf_monotonicity_ok` | No | Yes |
| `psf_mono_shift_resilient` | No | Yes |
| `pass_controls_comm` | No | Yes |
| `psf_commutativity_ok` | No | Yes |
| `psf_comm_shift_resilient` | No | Yes |
| `sanit_shift_resilient` | No | Yes |
| `psf_action_monotonicity_ok` | No | Yes |
| `psf_idempotence_ok` | No | Yes |
| `psf_path_independence_ok` | No | Yes |
| `psf_pii_monotonicity_ok` | No | Yes |
| `q2_consistency_ok` | No | Yes |
| `q3_fairness_ok` | No | Yes |


## Strict external evidence note

`release_required` is a policy-defined evidence set that currently contains:

- `external_summaries_present`
- `external_all_pass`

In the current v0 workflow implementation, release-grade mode still enforces `required` via `PULSE_POLICY_SET="required"`.

Strict external evidence mode additionally makes evidence presence fail closed in the workflow path, but the workflow does not yet materialize `release_required` as a separate `check_gates.py` enforce set.

Therefore, do not describe the current workflow as enforcing `required + release_required` unless `.github/workflows/pulse_ci.yml` is changed accordingly in the same change.

## Practical rule

If you need the shortest accurate answer to “what blocks shipping?”, read this page together with:

- `pulse_gate_policy_v0.yml`
- `docs/STATUS_CONTRACT.md`
- `docs/RUNBOOK.md`

Use this page for human orientation.
Use the policy file and workflow enforcement as the normative truth.
