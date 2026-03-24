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
- `main` branch pushes and version tag pushes (`v*` / `V*`) enforce `required`
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

`external_summaries_present` is not part of the base policy sets listed above.

In strict external evidence mode, workflow enforcement additionally requires:

- `external_summaries_present`
- `external_all_pass`

Use strict mode for release-grade paths when external summaries must be present and fail closed.

## Practical rule

If you need the shortest accurate answer to “what blocks shipping?”, read this page together with:

- `pulse_gate_policy_v0.yml`
- `docs/STATUS_CONTRACT.md`
- `docs/RUNBOOK.md`

Use this page for human orientation.
Use the policy file and workflow enforcement as the normative truth.
