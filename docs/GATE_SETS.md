# Gate sets

This page is a human-readable summary of the current policy-defined gate sets
and the current CI enforcement paths.

## Normative source of truth

The normative source of truth remains:

* `pulse_gate_policy_v0.yml`
* `PULSE_safe_pack_v0/tools/check_gates.py`
* `.github/workflows/pulse_ci.yml`

If this page and the policy or workflow disagree, the policy and workflow
enforcement win.

## Policy-defined gate sets

The policy currently defines four gate sets:

* `core_required` — minimal deterministic gate set for the core CI lane
* `required` — the main normative gate set used by the current release-grade
  workflow path
* `release_required` — policy-defined release-evidence gates
* `advisory` — diagnostic-only gates that must not block shipping

The current policy-defined `release_required` set contains:

* `external_summaries_present`
* `external_all_pass`

The current policy-defined `advisory` set also contains:

* `external_summaries_present`
* `external_all_pass`

## Current workflow enforcement summary

* `pull_request` runs enforce `core_required`
* pushes to `main` enforce `core_required` by default
* version tag pushes (`v*` / `V*`) enforce `required`
* `workflow_dispatch` runs enforce `core_required` by default; with
  `strict_external_evidence=true`, they enforce `required`
* required-like gates are fail-closed on missing / false
* advisory gates do not block shipping
* `release_required` is policy-defined, but it is **not yet materialized** as a
  separate `check_gates.py` enforce set in the current v0 workflow

## Gate matrix (policy-defined)

| Gate | `core_required` | `required` | `release_required` | `advisory` |
|---|---:|---:|---:|---:|
| `pass_controls_refusal` | Yes | Yes | No | No |
| `refusal_delta_pass` | No | Yes | No | No |
| `effect_present` | No | Yes | No | No |
| `psf_monotonicity_ok` | No | Yes | No | No |
| `psf_mono_shift_resilient` | No | Yes | No | No |
| `pass_controls_comm` | No | Yes | No | No |
| `psf_commutativity_ok` | No | Yes | No | No |
| `psf_comm_shift_resilient` | No | Yes | No | No |
| `pass_controls_sanit` | Yes | Yes | No | No |
| `sanitization_effective` | Yes | Yes | No | No |
| `sanit_shift_resilient` | No | Yes | No | No |
| `psf_action_monotonicity_ok` | No | Yes | No | No |
| `psf_idempotence_ok` | No | Yes | No | No |
| `psf_path_independence_ok` | No | Yes | No | No |
| `psf_pii_monotonicity_ok` | No | Yes | No | No |
| `q1_grounded_ok` | Yes | Yes | No | No |
| `q2_consistency_ok` | No | Yes | No | No |
| `q3_fairness_ok` | No | Yes | No | No |
| `q4_slo_ok` | Yes | Yes | No | No |
| `external_summaries_present` | No | No | Yes | Yes |
| `external_all_pass` | No | No | Yes | Yes |

## Strict external evidence note

`release_required` is a policy-defined evidence set.

In the current v0 workflow implementation, release-grade mode still enforces
`required` via `PULSE_POLICY_SET="required"`.

Strict external evidence mode additionally adds a workflow-level fail-closed
presence check for external summaries before augmentation continues.

That means:

* the current workflow does **not** yet materialize `release_required` as a
  separate `check_gates.py` enforce set
* the current workflow should **not** be described as enforcing
  `required + release_required`
* if `.github/workflows/pulse_ci.yml` is later changed to materialize
  `release_required` explicitly, this page should be updated in the same change

## Practical release-grade reading rule

For the current v0 workflow, the shortest accurate answer to
“what blocks shipping on the release-grade path?” is:

1. `required` gates enforced through `check_gates.py`
2. `run_mode=prod` enforced on release-grade runs
3. if strict external evidence mode is enabled, external summary presence is
   enforced fail-closed in the workflow path

This is narrower than `required + release_required`, and it is the wording that
matches the current workflow behavior.

## Practical rule

If you need the shortest accurate answer to “what blocks shipping?”, read this
page together with:

* `pulse_gate_policy_v0.yml`
* `docs/STATUS_CONTRACT.md`
* `docs/RUNBOOK.md`

Use this page for human orientation. Use the policy file and workflow
enforcement as the normative truth.
