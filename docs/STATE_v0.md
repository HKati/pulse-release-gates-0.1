# PULSE v0 — current state snapshot

> High-level reader note for where the repository currently stands.
>
> This is a **state snapshot**, not the normative contract.
>
> For normative semantics, use:
>
> - `docs/STATUS_CONTRACT.md`
> - `docs/GLOSSARY_v0.md`
> - `pulse_gate_policy_v0.yml`
> - `.github/workflows/pulse_ci.yml`

---

## 1. What is normative today

The normative release path is still anchored to:

- the final run artefact: `PULSE_safe_pack_v0/artifacts/status.json`
- gate enforcement: `PULSE_safe_pack_v0/tools/check_gates.py`
- repo-level gate policy: `pulse_gate_policy_v0.yml`
- the primary CI wiring: `.github/workflows/pulse_ci.yml`

Release semantics are intended to stay fail-closed:

- missing required gates fail,
- required gates must be literal boolean `true` to pass,
- diagnostic overlays must not silently change shipping decisions.

This remains the stable center of the repository.

---

## 2. Core path for first-time adopters

The repository still exposes a smaller Core profile for first integrations:

- `PULSE_safe_pack_v0/profiles/pulse_policy_core.yaml`

That profile is:

- `experimental`
- minimal by design
- aimed at first-time adopters

Its documented `core_required_gates` are:

- `pass_controls_refusal`
- `pass_controls_sanit`
- `sanitization_effective`
- `q1_grounded_ok`
- `q4_slo_ok`

The Core profile also includes a refusal-delta policy block, but that
block remains CI-neutral by design: it is for tooling and review
surfaces, not for silently replacing deterministic gate outcomes.

---

## 3. External detectors: supported, but not universally mandatory

External detectors remain part of the repository model, but the current
policy is layered.

At repo level:

- external detector adoption is optional,
- aggregate external results can be promoted into required gating,
- evidence presence is a separate question from aggregate pass/fail.

In practice, the repository policy still distinguishes between:

- a broader `required` gate set, which can include `external_all_pass`,
- and a smaller `core_required` set, which stays focused on a minimal
  deterministic path.

That means:

- external detector signals can be normative,
- but they are not the universal default for every integration path.

For more detail, see:

- `docs/EXTERNAL_DETECTORS.md`
- `docs/external_detector_summaries.md`
- `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`

---

## 4. Status artefact and Quality Ledger

The main safe-pack entrypoint currently produces at least:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

Recommended interpretation:

- `status.json` is the machine-readable source of truth for one run
- `report_card.html` is the human-readable Quality Ledger view over that run

The ledger remains an explanation layer, not a second decision engine.

When present, stability signals such as RDSI still belong in the
interpretation / review layer unless a repository explicitly promotes
them into required policy.

---

## 5. Shadow contract program: now a real repo surface

The repository is no longer best understood as only a deterministic gate
pack with informal shadow add-ons.

It now includes an explicit shadow-contract program with:

- repo-level shadow contract guidance,
- a common shadow artifact contract surface,
- machine-readable schema/checker patterns for shadow artefacts,
- and a machine-readable shadow layer registry.

Important boundary:

- shadow layers may be documented, schema-bound, checker-validated,
  fixture-backed, test-backed, workflow-wired, and machine-registered,
- but they remain non-normative unless policy explicitly promotes them.

This means the repository now has:

- a deterministic release-governance core,
- plus a contract-disciplined shadow program around it.

That is a meaningful architectural step beyond “optional diagnostics”.

---

## 6. Machine-readable shadow layer registry

The repository now includes a machine-readable shadow registry stack:

- `shadow_layer_registry_v0.yml`
- `schemas/shadow_layer_registry_v0.schema.json`
- `PULSE_safe_pack_v0/tools/check_shadow_layer_registry.py`
- `tests/fixtures/shadow_layer_registry_v0/*`
- `tests/test_check_shadow_layer_registry.py`
- `.github/workflows/shadow_layer_registry.yml`

This registry is governance-facing and descriptive.

It records:

- shadow layer identity,
- stage and target stage,
- authority boundary,
- workflow entrypoints,
- artifacts,
- schema/checker surfaces,
- fixtures and tests,
- and run-reality states.

It does **not** create release authority by itself.

---

## 7. Relational Gain v0: contract-hardened shadow pilot

Relational Gain v0 is now best described as a **contract-hardened
shadow-only module**.

Current state:

- shadow-only
- machine-registered
- `current_stage: shadow-contracted`
- `target_stage: advisory`
- `consumer_authority: review-only`
- `normative: false`

Current hardening surface includes:

- dedicated checker / fold-in / runner
- layer-specific schema
- layer-specific contract checker
- canonical PASS / WARN / FAIL fixtures
- checker regression tests
- non-interference tests
- dedicated workflow
- dedicated layer docs
- optional-layer and registry sync
- status-surface documentation for `meta.relational_gain_shadow`

This means Relational Gain v0 is no longer just a shadow experiment or
research note.

It is now a fully implemented and contract-disciplined shadow pilot.

---

## 8. EPF line: broader research path, narrower hardened summary surface

The broader EPF line remains **research-stage** and diagnostic.

That is still the right top-level classification.

However, the current `epf_paradox_summary.json` surface is now
contract-hardened.

Current summary-surface hardening includes:

- `schemas/epf_paradox_summary_v0.schema.json`
- `PULSE_safe_pack_v0/tools/check_epf_paradox_summary_contract.py`
- canonical positive and negative fixtures
- `tests/test_check_epf_paradox_summary_contract.py`
- workflow-level validation in `.github/workflows/epf_experiment.yml`
- machine-registration in `shadow_layer_registry_v0.yml`

So the correct current reading is:

- **broader EPF line** → research diagnostic
- **current paradox summary surface** → contract-hardened, non-normative summary artifact

This distinction matters.

EPF should inform inspection, comparison, and future policy evolution,
but it must not silently override the deterministic baseline release path.

For operational guidance, see:

- `docs/PARADOX_RUNBOOK.md`
- `docs/PULSE_epf_shadow_quickstart_v0.md`

---

## 9. Drift and governance

PULSE already exposes several artefacts that are useful for drift-aware
governance:

- deterministic gate outcomes
- `status.json`
- Quality Ledger / report card
- optional external detector summaries
- Relational Gain shadow artefacts
- EPF / paradox shadow artefacts
- machine-readable shadow registry state

However, the repository still does **not** ship a full long-horizon drift
monitoring system with built-in time-series alerting or automatic
threshold adaptation.

That broader drift story is still expected to be built on top of
archived PULSE artefacts.

For the current high-level framing, see:

- `docs/DRIFT_OVERVIEW.md`

---

## 10. Practical reading of the repo today

A good mental model for the repository today is:

- **core deterministic release gating** at the center,
- **artifact-first reporting** around it,
- **contract-disciplined shadow layers** on top,
- and **governance / audit surfaces** growing around the same immutable
  run artefacts.

The repository is no longer best described as:

> “just one fixed gate pack”

It is better understood as:

- a deterministic release-governance core,
- plus additive diagnostic and review layers,
- plus a machine-readable shadow registration and validation surface,
- with explicit separation between normative and diagnostic meaning.

---

## 11. What should be kept stable

When the architecture evolves, the following should remain stable:

- the normative source of release meaning,
- the separation between normative and diagnostic layers,
- fail-closed handling of required gates,
- artifact-first review and auditability,
- and the rule that shadow presence does not itself imply promotion.

If one of those changes, update the canonical docs in the same change set.
