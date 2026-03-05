# PULSE EPF shadow pipeline walkthrough (v0)

> Detailed walkthrough of the current EPF shadow experiment workflow.

This document explains the current implementation flow of the EPF shadow experiment.

It shows:

- how the workflow is triggered,
- how the shared input is prepared,
- how the deterministic and EPF shadow branches run,
- how the compare step derives gate deltas,
- which artifacts are emitted,
- how to distinguish real runs from degraded runs.

It does not define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

---

## Important boundary

- deterministic archived artifacts carry the recorded baseline result for the experiment flow
- the EPF shadow path is diagnostic and CI-neutral
- disagreement between baseline and EPF is inspection input, not an automatic policy rewrite
- missing or degraded inputs remain explicit

For the shorter command-level version, see:

- `docs/PULSE_epf_shadow_quickstart_v0.md`

For disagreement handling, see:

- `docs/PARADOX_RUNBOOK.md`

For the EPF ↔ topology relation, see:

- `docs/PULSE_topology_epf_hook_v0.md`
- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`

For broader repository state, see:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

---

# 1. What this pipeline is

The repository ships an optional workflow:

```text
.github/workflows/epf_experiment.yml
```

This workflow performs a shared-input A/B comparison:

- produce or recover a common `status.json`
- create two working copies from that same input
- run:
  - deterministic baseline evaluation
  - EPF shadow evaluation
- compare the resulting gate decisions
- emit human- and machine-readable comparison artifacts
- upload the comparison bundle

Its goal is **not** to replace deterministic release evaluation.

Its goal is to expose:

- boundary fragility
- shadow disagreement
- paradox candidates
- degraded or weakly supported comparisons

in archived, reviewable form.

---

# 2. Trigger model

The current workflow runs on:

- `workflow_dispatch`
- `push` to `main` when selected paths change

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

# 3. Step-by-step pipeline

## 3.1 Checkout and Python setup

The workflow first:

- checks out the repository
- sets up Python 3.11

This is just the runtime scaffold for the later steps.

---

## 3.2 Dependency install (best-effort)

The next step tries to install dependencies.

Preferred path:

- if `PULSE_safe_pack_v0/requirements.txt` exists, install from there

Fallback path:

- otherwise install a minimal set:

```text
numpy
jsonschema>=4,<5
```

Important nuance:

- dependency installation is best-effort
- if install fails, the workflow warns and continues in degraded / stub-capable mode

That means a completed shadow workflow does **not automatically prove** that the full EPF experiment really ran in a strong form.

---

## 3.3 Prepare shared input

The workflow then tries to produce a baseline status artifact via:

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

If that succeeds and writes:

```
PULSE_safe_pack_v0/artifacts/status.json
```

the workflow copies that file into:

```
status.json
```

If `run_all.py` is missing or no baseline artifact appears, the workflow falls back to a stub file:

```json
{"metrics": {}}
```

This `status.json` becomes the common input for both the deterministic and EPF shadow branches.

---

## 3.4 Deterministic baseline branch

The deterministic branch starts from the common input:

```
status.json → status_baseline.json
```

Then the workflow checks whether:

```
pulse_gates.yaml
```

exists.

If it does **not exist**:

- the workflow stays in stub mode
- real gate evaluation is skipped

If it **does exist** and `scripts/check_gates.py` is present, the workflow runs:

```bash
python scripts/check_gates.py \
  --config pulse_gates.yaml \
  --status status_baseline.json \
  --defer-policy fail
```

Interpretation:

- this is the deterministic reference branch inside the shadow experiment workflow
- it is a baseline read for comparison, **not a hidden rewrite of release semantics**

---

## 3.5 EPF shadow branch

The EPF branch also starts from the same common input:

```
status.json → status_epf.json
```

Again, if `pulse_gates.yaml` is missing:

- the workflow stays in stub mode

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
- it is deliberately configured to **warn rather than fail-closed**
- it exists to expose instability / disagreement, not to silently overrule the deterministic baseline

---

## 3.6 Compare and summarize

After both branches run, the workflow compares:

Baseline decisions from:

```
status_baseline.json["decisions"]
```

EPF shadow decisions from:

```
status_epf.json["experiments"]["epf"]
```

### Normalization rule on the EPF side

If an EPF gate entry is a dictionary, the compare step reads:

1. `decision`
2. otherwise `status`
3. otherwise the raw value

### Change rule

A gate is counted as changed **only when**:

- the EPF-side value is present
- and the EPF-side value differs from the baseline-side value

Important nuance:

- `False` / `0` are treated as real values, not as “missing”
- the compare step checks presence against `None`, not truthiness

This makes the compare step a **delta surface over archived outputs**, not a second release-semantics contract.

---

## 3.7 Emitted summaries and uploaded artifacts

The compare step writes:

```
epf_report.txt
epf_paradox_summary.json
```

It also appends a GitHub Step Summary containing:

- the text of `epf_report.txt`
- a one-line changed / no-change outcome

Finally, the workflow uploads:

```
epf-ab-artifacts
```

containing:

- `status_baseline.json`
- `status_epf.json`
- `epf_report.txt`
- `epf_paradox_summary.json`

---

# 4. What the compare step means

The compare step is a **structural delta read over two runs that started from the same common input**.

A difference between baseline and EPF shadow can indicate one or more of these:

- boundary sensitivity
- weak or missing evidence
- config drift
- implementation drift
- real behavioral fragility near threshold

That means:

- disagreement is important
- disagreement is inspectable
- disagreement is good input for topology / decision-field interpretation
- disagreement is **not an automatic release override**

If a delta matters, continue with:

```
docs/PARADOX_RUNBOOK.md
```

---

# 5. Output artifacts

## epf_report.txt

Human-readable short summary including:

- dependency install return code
- `run_all.py` return code
- baseline checker return code
- EPF checker return code
- total number of baseline gates
- number of changed baseline → EPF decisions
- up to 20 example gate deltas

---

## epf_paradox_summary.json

Structured machine-readable summary including:

- dependency / run return codes
- `total_gates`
- `changed`
- a small list of example differences

---

## status_baseline.json

Deterministic branch output for the comparison run.

---

## status_epf.json

EPF shadow branch output for the comparison run.

---

## GitHub Step Summary

A convenience surface for quick inspection.

The uploaded artifacts remain the **real archived evidence**.

---

# 6. Real run vs degraded run

This distinction matters a lot.

## A. Real-enough run

A run is close to **“real enough to trust”** when:

- dependencies installed well enough
- `run_all.py` produced a genuine baseline `status.json`
- `pulse_gates.yaml` exists
- `scripts/check_gates.py` exists
- both baseline and EPF checker steps actually ran
- the comparison artifacts reflect real gate outputs rather than mostly stubs

---

## B. Degraded / stub run

A run is degraded when one or more of these happen:

- dependency install failed
- `run_all.py` failed to produce baseline status
- `pulse_gates.yaml` is missing
- `scripts/check_gates.py` is missing
- command failures leave one or both branches too partial to trust

In those cases the workflow can still produce outputs, but those outputs are **not strong evidence** of a meaningful paradox or EPF disagreement.

Practical rule:

before interpreting a disagreement, first verify the run was **real enough to trust**.

Use:

- job logs
- return codes in `epf_report.txt`
- the contents of the uploaded JSON artifacts

---

# 7. Relationship to topology

This pipeline does not perform the whole topology stack by itself.

What it **does** do is produce boundary-sensitive archived artifacts that topology can later read alongside deterministic run outputs.

That makes this pipeline a useful input surface for:

- the EPF ↔ topology hook
- decision-field interpretation
- stability-oriented reading
- paradox / field analysis
- archive inspection

A real EPF disagreement can therefore become useful evidence for:

- boundary pressure
- fragility
- disagreement clustering
- paradox concentration
- reduced confidence in a “stable” read

without silently changing release semantics.

---

# 8. Relationship to release semantics

This workflow is adjacent to release semantics, but it is **not the release contract**.

Deterministic archived artifacts carry the recorded baseline result for the experiment flow.

The EPF shadow branch and the comparison summary may enrich interpretation, but they must **not silently rewrite the release-semantics contract** defined elsewhere.

If release behavior needs to change, that belongs in explicit:

- contract changes
- policy changes
- CI / workflow changes
- schema changes

not in shadow comparison wording.

---

# 9. Recommended reading order

When inspecting one EPF experiment run, read artifacts in this order:

1. `epf_report.txt`  
   quickly tells you whether the run was real or degraded  
   shows how many gate differences were observed  

2. `epf_paradox_summary.json`  
   gives a compact structured summary of the same event  

3. `status_baseline.json`  
   inspect the deterministic branch state  

4. `status_epf.json`  
   inspect the shadow-side experiment output  

If the disagreement matters, continue with:

- `docs/PARADOX_RUNBOOK.md`
- `docs/PULSE_topology_epf_hook_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`

---

# 10. Local reproduction

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

Then inspect:

- `status_baseline.json`
- `status_epf.json`

and, for workflow parity, summarize the differences the same way CI does.

---

# 11. What this pipeline is good for

This pipeline is especially useful for:

- spotting threshold fragility
- surfacing EPF disagreement
- prioritizing follow-up evaluation work
- documenting whether a run was real or degraded
- generating topology-relevant boundary-sensitive artifacts
- separating “deterministically positive/negative” from “structurally stable/unstable”

It is **not a replacement for the release-semantics contract**.

---

# 12. Summary

The current EPF experiment pipeline is best understood as:

- a shared-input A/B shadow workflow
- with best-effort execution
- producing archived comparison artifacts
- for diagnostic, topology-relevant inspection

Its job is to make disagreement **visible, reproducible, and structurally legible** while keeping the release-semantics boundary explicit.
