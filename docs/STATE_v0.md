# PULSE v0 — current state snapshot

> High-level reader note for where the repository currently stands.
> This is a snapshot, not the normative contract.

For normative semantics, use:

- `docs/STATUS_CONTRACT.md`
- `docs/GLOSSARY_v0.md`
- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`

---

## 1. What is normative today

The normative release path is anchored to:

- the final run artefact: `PULSE_safe_pack_v0/artifacts/status.json`
- gate enforcement: `PULSE_safe_pack_v0/tools/check_gates.py`
- repo-level gate policy: `pulse_gate_policy_v0.yml`
- the primary CI wiring: `.github/workflows/pulse_ci.yml`

Release semantics are intended to stay fail-closed:

- missing required gates fail,
- required gates must be literal boolean `true` to pass,
- diagnostic overlays must not silently change shipping decisions.

This is the stable center of the repository.

---

## 2. Core path for first-time adopters

The repository now exposes a smaller Core profile for first integrations:

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

The Core profile also includes a refusal-delta policy block, but that block is
CI-neutral by design: it is meant for tooling and review surfaces, not for
silently replacing deterministic gate outcomes.

---

## 3. External detectors: supported, but not universally mandatory

External detectors are part of the repository model, but the current policy is
layered.

At repo level:

- external detector adoption is optional,
- aggregate external results can be promoted into required gating,
- evidence presence is a separate question from aggregate pass/fail.

In practice, the repository policy distinguishes between:

- a broader `required` gate set, which can include
  `external_all_pass`,
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

The ledger is an explanation layer, not a second decision engine.

When present, stability signals such as RDSI belong in the interpretation /
review layer unless a repository explicitly promotes them into required policy.

---

## 5. EPF, hazard, and paradox layers

EPF and related paradox handling remain diagnostic / shadow-oriented in the
current repository model.

The dedicated EPF shadow workflow:

- `.github/workflows/epf_experiment.yml`

produces comparison artefacts such as:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

These artefacts are intended to help maintainers inspect tension between the
deterministic baseline and the shadow EPF view.

They should inform policy evolution, not silently override the main fail-closed
release path.

For operational guidance, see:

- `docs/PARADOX_RUNBOOK.md`

---

## 6. Drift and governance

PULSE already exposes several artefacts that are useful for drift-aware
governance:

- deterministic gate outcomes
- `status.json`
- Quality Ledger / report card
- optional external detector summaries
- EPF / paradox shadow artefacts

However, the repository does **not** currently ship a full long-horizon drift
monitoring system with built-in time-series alerting or automatic threshold
adaptation.

That broader drift story is still expected to be built on top of archived PULSE
artefacts.

For the current high-level framing, see:

- `docs/DRIFT_OVERVIEW.md`

---

## 7. Practical reading of the repo today

A good mental model for the repository today is:

- **core deterministic release gating** at the center,
- **artifact-first reporting** around it,
- **diagnostic overlays** layered on top,
- and **governance / audit surfaces** growing around the same immutable run
  artefacts.

The repo is no longer best described as “just one fixed gate pack”.
It is better understood as:

- a deterministic release-governance core,
- plus additive diagnostic and review layers,
- with explicit separation between normative and diagnostic meaning.

---

## 8. What should be kept stable

When the architecture evolves, the following should remain stable:

- the normative source of release meaning,
- the separation between normative and diagnostic layers,
- fail-closed handling of required gates,
- artifact-first review and auditability.

If one of those changes, update the canonical docs in the same change set.
