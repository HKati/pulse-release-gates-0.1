# PULSE EPF shadow pipeline walkthrough (v0)

> Detailed walkthrough of the current EPF experiment pipeline used in this
> repository.

This document explains the **current implementation flow** of the EPF shadow
experiment.

Important boundary:

- the deterministic baseline remains the authoritative release path
- the EPF shadow path is diagnostic and CI-neutral
- disagreement between baseline and EPF is triage input for humans, not an
  automatic policy rewrite

For the shorter command-level version, see:

- `docs/PULSE_epf_shadow_quickstart_v0.md`

For disagreement handling, see:

- `docs/PARADOX_RUNBOOK.md`

For the broader repo model, see:

- `docs/STATE_v0.md`
- `docs/DRIFT_OVERVIEW.md`

---

## 1. What this pipeline is

The repository ships an optional workflow:

```text
.github/workflows/epf_experiment.yml
```

This workflow performs a same-baseline comparison:

- produce or recover a baseline `status.json`
- create two working copies from that same baseline input
- run:
  - deterministic baseline evaluation
  - EPF shadow evaluation
- compare the resulting decisions
- emit human- and machine-readable comparison artefacts

The goal is not to replace the main release gates.  
The goal is to expose boundary fragility, shadow disagreements, and paradox
candidates in a reviewable form.

---

## 2. Trigger model

The current workflow runs on:

- `workflow_dispatch`
- push to `main` when selected paths change

The current path filter includes:

- `PULSE_safe_pack_v0/**`
- `tools/**`
- `scripts/**`
- `pulse_gates.yaml`
- `.github/workflows/epf_experiment.yml`

This makes the workflow useful for:

- EPF / checker edits
- safe-pack changes
- shadow config changes
- targeted manual re-runs

---

## 3. Step-by-step pipeline

### 3.1 Checkout and Python setup

The workflow first:

- checks out the repository
- sets up Python 3.11

This is just the runtime scaffold for the later steps.

### 3.2 Dependency install (best-effort)

The next step tries to install dependencies.

Preferred path:

- if `PULSE_safe_pack_v0/requirements.txt` exists, install from there

Fallback path:

- otherwise install a minimal set:
  - `numpy`
  - `jsonschema>=4,<5`

Important nuance:

- dependency installation is best-effort
- if install fails, the workflow warns and continues in stub / best-effort mode

That means a green or completed shadow workflow does not automatically prove
that the full EPF experiment really ran.

### 3.3 Prepare baseline input

The workflow then tries to produce a baseline status artefact via:

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

If that succeeds and writes:

- `PULSE_safe_pack_v0/artifacts/status.json`

the workflow copies that file into:

- `status.json`

If `run_all.py` is missing or no baseline artefact appears, the workflow falls
back to a stub file:

```json
{"metrics": {}}
```

This `status.json` becomes the common input for both the baseline and EPF shadow
branches.

### 3.4 Deterministic baseline branch

The baseline branch starts from the common baseline input:

- `status.json` → `status_baseline.json`

Then the workflow checks whether:

- `pulse_gates.yaml`

exists.

- if it does not exist, the workflow stays in stub mode and skips real gate evaluation
- if it does exist and `scripts/check_gates.py` is present, the workflow runs:

```bash
python scripts/check_gates.py \
  --config pulse_gates.yaml \
  --status status_baseline.json \
  --defer-policy fail
```

Interpretation:

- this is the deterministic baseline reference for the experiment workflow
- it is still not the main repository release workflow; it is the baseline branch inside the shadow experiment

### 3.5 EPF shadow branch

The EPF branch also starts from the same common baseline input:

- `status.json` → `status_epf.json`

Again, if `pulse_gates.yaml` is missing, the workflow stays in stub mode.

If the config and checker are available, it runs:

```bash
python scripts/check_gates.py \
  --config pulse_gates.yaml \
  --status status_epf.json \
  --epf-shadow \
  --seed 1737 \
  --defer-policy warn
```

Interpretation:

- this is the seeded shadow comparison branch
- it is deliberately configured to warn rather than fail-closed
- it exists to expose instability / disagreement, not to overrule the baseline

---

## 4. What gets compared

After both branches run, the workflow compares:

- baseline decisions from:
  - `status_baseline.json["decisions"]`
- EPF shadow decisions from:
  - `status_epf.json["experiments"]["epf"]`

The compare step normalizes EPF entries so that, when an EPF gate entry is a dictionary, it prefers:

- `decision`
- otherwise `status`
- otherwise the raw value

A gate is counted as changed when:

- the EPF-side value is present
- and the EPF-side value differs from the baseline-side value

This is the current comparison contract for the experiment workflow.

---

## 5. Output artefacts

The compare step writes two main artefacts.

### `epf_report.txt`

Human-readable short summary including:

- dependency install return code
- `run_all.py` return code
- baseline checker return code
- EPF checker return code
- total number of baseline gates
- number of changed baseline → EPF decisions
- up to 20 example gate deltas

### `epf_paradox_summary.json`

Structured machine-readable summary including:

- dependency / run rc values
- `total_gates`
- `changed`
- a small list of example differences

### Uploaded artifact bundle

The workflow uploads:

- `epf-ab-artifacts`

containing:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

---

## 6. Step Summary behavior

The workflow also writes a GitHub Step Summary.

Typical outcomes:

- if changed gates > 0:

  ⚠️ EPF shadow detected N gate(s) with different decisions than the baseline.

- otherwise:

  ✅ EPF shadow run: no gate-level decision changes detected.

This is a convenience surface for quick triage.  
The uploaded artefacts remain the real evidence.

---

## 7. Real run vs degraded run

This distinction matters a lot.

### A. Real run

A run is close to “real” when:

- dependencies installed well enough
- `run_all.py` produced a genuine baseline `status.json`
- `pulse_gates.yaml` exists
- `scripts/check_gates.py` exists
- both baseline and EPF checker steps actually ran

### B. Degraded / stub run

A run is degraded when one or more of these happen:

- dependency install failed
- `run_all.py` failed to produce baseline status
- `pulse_gates.yaml` is missing
- `scripts/check_gates.py` is missing

In those cases, the workflow can still produce outputs, but those outputs are
not strong evidence of a meaningful paradox or EPF disagreement.

Practical rule:

Before interpreting a disagreement, first verify the run was real enough to trust.

Use:

- job logs
- return codes in `epf_report.txt`
- and the contents of the uploaded JSON artefacts

---

## 8. Relationship to the main release path

This pipeline is not the repository’s primary release-gating workflow.

The main normative release meaning lives elsewhere, including:

- the final safe-pack `status.json`
- repo policy
- the primary release CI path

This EPF experiment pipeline is a diagnostic side path that helps answer:

- where is the decision boundary fragile?
- which gates flip in shadow mode?
- which changes deserve deeper review?

It should inform governance work, not silently replace it.

---

## 9. Recommended reading order

When inspecting one EPF experiment run, read artefacts in this order:

1. `epf_report.txt`  
   quickly tells you whether the run was real or degraded  
   shows how many gate differences were observed

2. `epf_paradox_summary.json`  
   gives a compact structured summary of the same event

3. `status_baseline.json`  
   inspect the baseline deterministic decision state

4. `status_epf.json`  
   inspect the shadow-side experiment output

If the disagreement matters, continue with:

- `docs/PARADOX_RUNBOOK.md`

---

## 10. Local reproduction

A close local reproduction of the current workflow is:

```bash
python PULSE_safe_pack_v0/tools/run_all.py || true

if [ -f PULSE_safe_pack_v0/artifacts/status.json ]; then
  cp PULSE_safe_pack_v0/artifacts/status.json status.json
else
  echo '{"metrics": {}}' > status.json
fi

if [ -f status.json ]; then
  cp status.json status_baseline.json
  cp status.json status_epf.json
else
  echo '{"decisions": {}}' > status_baseline.json
  echo '{"experiments":{"epf":{}}}' > status_epf.json
fi

if [ -f pulse_gates.yaml ] && [ -f scripts/check_gates.py ]; then
  python scripts/check_gates.py \
    --config pulse_gates.yaml \
    --status status_baseline.json \
    --defer-policy fail

  python scripts/check_gates.py \
    --config pulse_gates.yaml \
    --status status_epf.json \
    --epf-shadow \
    --seed 1737 \
    --defer-policy warn
else
  echo "Stub/degraded local reproduction: pulse_gates.yaml or scripts/check_gates.py missing."
fi

```

This mirrors the current CI behavior more closely, including the stub fallback
path when `run_all.py` does not produce `PULSE_safe_pack_v0/artifacts/status.json`
or when the EPF checker/config inputs are missing.

Then inspect:

- `status_baseline.json`
- `status_epf.json`

and, if you want parity with the workflow, summarize the differences the same
way the CI compare step does.

---

## 11. What this pipeline is good for

This pipeline is especially useful for:

- spotting threshold fragility
- prioritising follow-up evaluation work
- surfacing paradox candidates
- separating “deterministically passing” from “operationally stable”
- documenting why a gate may deserve closer review later

It is not a replacement for the main release policy.

---

## 12. Summary

The current EPF experiment pipeline should be understood as:

- a same-baseline A/B comparison workflow
- with best-effort execution
- producing review artefacts
- for diagnostic governance work

Its job is to make disagreement visible and reproducible, while keeping the deterministic baseline authoritative until a reviewed policy change says otherwise.
