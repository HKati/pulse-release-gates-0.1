# Gate sets

## Policy-defined gate sets

This page is the human-readable summary of:

- the policy-defined gate sets in `pulse_gate_policy_v0.yml`
- the current workflow-effective enforcement shape in `.github/workflows/pulse_ci.yml`

If this page and the committed workflow ever disagree, treat the workflow as authoritative and update this page in the same PR.

The policy currently defines four gate sets:

- `core_required` — minimal deterministic gate set for the Core CI lane
- `required` — the main normative baseline gate set
- `release_required` — release-evidence gates promoted in release-grade runs
- `advisory` — diagnostic-only gates that must not block shipping unless explicitly promoted

The current policy-defined `release_required` set contains:

- `detectors_materialized_ok`
- `external_summaries_present`
- `external_all_pass`

The current policy-defined `advisory` set also contains:

- `external_summaries_present`
- `external_all_pass`

That overlap is intentional.

These gates remain diagnostic by default in non-release lanes, and are promoted into the effective release-grade enforce set by the workflow.

## Current workflow enforcement summary

The current workflow behavior is:

- `pull_request` runs enforce `core_required`
- pushes to `main` enforce `core_required`
- version tag pushes (`v*` / `V*`) run release-grade in `prod` mode, set the base policy set to `required`, and then materialize the effective enforce set as `required + release_required`
- `workflow_dispatch` runs enforce `core_required` by default
- `workflow_dispatch` runs with `strict_external_evidence=true` run release-grade in `prod` mode, set the base policy set to `required`, and then materialize the effective enforce set as `required + release_required`
- required-like gates are fail-closed on missing / false
- advisory gates do not block shipping unless explicitly promoted into the active enforce set

Strict external evidence also keeps an earlier workflow-level fail-closed presence check for external summaries before augmentation continues.

That early check is useful because it fails fast on missing evidence before the final augmented `status.json` is enforced.

## Effective workflow sets

The most useful mental model is:

| Lane | `metrics.run_mode` | Workflow-effective enforce set |
|---|---|---|
| Core CI (`pull_request`, push to `main`, manual default) | `core` | `core_required` |
| Release-grade tag push (`v*` / `V*`) | `prod` | `required + release_required` |
| Release-grade manual run (`strict_external_evidence=true`) | `prod` | `required + release_required` |

This page distinguishes between:

- policy-defined sets
- workflow-effective enforcement

That distinction matters.

A set can exist in policy without always being active in every lane.

## Gate matrix (policy-defined)

| Gate | `core_required` | `required` | `release_required` | `advisory` |
|---|---|---|---|---|
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
| `detectors_materialized_ok` | No | No | Yes | No |
| `external_summaries_present` | No | No | Yes | Yes |
| `external_all_pass` | No | No | Yes | Yes |

## Strict external evidence note

`release_required` is now materialized in the current v0 workflow for release-grade paths.

That means strict external evidence is not only a pre-augment workflow guard anymore. In release-grade paths, the final effective fail-closed gate set is:

- `required`
- plus `release_required`

The pre-augment external-summary presence check still remains valuable because it fails early on missing evidence before augmentation continues.

In non-release lanes, external evidence stays out of the active enforce set by default. That keeps the core path narrow and deterministic, while still allowing diagnostic evidence collection.
