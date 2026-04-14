# PULSE EPF shadow quickstart (v0)

> Command-level quickstart for the current EPF shadow comparison path.
>
> This guide shows how to run the current EPF shadow comparison flow
> locally, how to read the resulting artifacts, and how to validate the
> current EPF paradox summary contract surface.
>
> It does **not** define release semantics.

Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`

Important boundary:

- deterministic archived artifacts carry the recorded baseline release result
- the EPF shadow path is diagnostic and CI-neutral
- disagreement between baseline and EPF is inspection input, not an automatic policy rewrite
- missing or degraded inputs remain explicit

For disagreement triage, see:

- `docs/PARADOX_RUNBOOK.md`

For the EPF ↔ topology relation, see:

- `docs/PULSE_topology_epf_hook_v0.md`
- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`

For broader repository state, see:

- `docs/STATE_v0.md`
- `docs/status_json.md`

---

## 1. What this quickstart is for

Use this quickstart if you want to:

- run the current EPF shadow experiment locally
- mirror the current GitHub Actions flow
- inspect baseline vs EPF shadow differences
- reproduce the main comparison inputs
- determine whether a disagreement is real or degraded
- validate the current `epf_paradox_summary.json` artifact shape

This is **not** the main release-gating path.

---

## 2. Current workflow at a glance

The repository ships an optional workflow:

```text
.github/workflows/epf_experiment.yml
```

Current shape:

- it is a shadow / non-blocking workflow
- it tries to produce a baseline via `PULSE_safe_pack_v0/tools/run_all.py`
- it falls back to a stub `status.json` if a real baseline artifact is missing

It creates two working copies from the same common input:

- deterministic baseline → `status_baseline.json`
- EPF shadow → `status_epf.json`

It compares the two and writes:

- `epf_report.txt`
- `epf_paradox_summary.json`

The uploaded artifact bundle is:

```text
epf-ab-artifacts
```

The quick way to think about it:

- baseline branch = deterministic read over the common input
- EPF shadow branch = boundary-sensitive shadow read over the same input
- comparison output = archived disagreement summary for inspection

---

## 3. Local quickstart

From repo root:

### Step 1 — Try to produce a baseline PULSE run when available

```bash
if [ -f PULSE_safe_pack_v0/tools/run_all.py ]; then
  python PULSE_safe_pack_v0/tools/run_all.py || true
else
  echo "run_all.py missing; using stub path."
fi
```

### Step 2 — Mirror the CI baseline/stub preparation

```bash
if [ -f PULSE_safe_pack_v0/artifacts/status.json ]; then
  cp PULSE_safe_pack_v0/artifacts/status.json status.json
else
  echo '{"metrics": {}}' > status.json
fi
```

### Step 3 — Create the two experiment inputs

```bash
if [ -f status.json ]; then
  cp status.json status_baseline.json
  cp status.json status_epf.json
else
  echo '{"decisions": {}}' > status_baseline.json
  echo '{"experiments":{"epf":{}}}' > status_epf.json
fi
```

### Step 4 — Run the deterministic baseline checker

```bash
if [ -f pulse_gates.yaml ] && [ -f scripts/check_gates.py ]; then
  python scripts/check_gates.py \
    --config pulse_gates.yaml \
    --status status_baseline.json \
    --defer-policy fail
else
  echo "Stub/degraded local reproduction: pulse_gates.yaml or scripts/check_gates.py missing."
fi
```

### Step 5 — Run the EPF shadow checker

```bash
if [ -f pulse_gates.yaml ] && [ -f scripts/check_gates.py ]; then
  python scripts/check_gates.py \
    --config pulse_gates.yaml \
    --status status_epf.json \
    --epf-shadow \
    --seed 1737 \
    --defer-policy warn
fi
```

This mirrors the current GitHub Actions workflow more closely than
assuming `run_all.py` always produced a real baseline artifact.

---

## 4. What the two branches mean

### Baseline branch

The baseline branch is the deterministic read over the common input.

Interpret it as:

> “What does the current gate logic record without EPF shadow enabled?”

This records the baseline release read for the experiment flow.

### EPF shadow branch

The EPF shadow branch is a boundary-sensitive diagnostic read over the
same common input.

Interpret it as:

> “If shadow EPF logic is enabled near the boundary, what looks fragile,
> pressure-loaded, or different?”

This does **not automatically change the recorded baseline result**.

---

## 5. Expected outputs

After a successful local comparison flow, the main artifacts are:

- `status_baseline.json`
- `status_epf.json`

In GitHub Actions, the workflow also writes and uploads:

- `epf_report.txt`
- `epf_paradox_summary.json`

Recommended reading order for a workflow run:

1. `epf_report.txt`
2. `epf_paradox_summary.json`
3. `status_baseline.json`
4. `status_epf.json`

For a minimal local reproduction without the compare step, start with:

- `status_baseline.json`
- `status_epf.json`

---

## 6. Current EPF artifact contract surfaces

The current EPF shadow flow now has **two** contract-relevant artifact
surfaces.

### A. Paradox summary surface

Current artifact:

epf_paradox_summary.json

Current machine-readable schema:

schemas/epf_paradox_summary_v0.schema.json

Current layer-specific contract checker:

PULSE_safe_pack_v0/tools/check_epf_paradox_summary_contract.py

Current canonical positive fixture:

tests/fixtures/epf_paradox_summary_v0/pass.json

Current checker regression tests:

tests/test_check_epf_paradox_summary_contract.py

This surface summarizes baseline vs EPF comparison at the disagreement level.

Its current shape includes:

- deps_rc
- runall_rc
- baseline_rc
- epf_rc
- total_gates
- changed
- examples

This surface is already contract-hardened, but remains descriptive and
non-normative.

### B. Broader EPF run-manifest surface

Current artifact:

epf_shadow_run_manifest.json

Current machine-readable schema:

schemas/epf_shadow_run_manifest_v0.schema.json

Current layer-specific contract checker:

PULSE_safe_pack_v0/tools/check_epf_shadow_run_manifest_contract.py

Current canonical positive fixture:

tests/fixtures/epf_shadow_run_manifest_v0/pass.json

Current checker regression tests:

tests/test_check_epf_shadow_run_manifest_contract.py

This surface records the broader EPF run context around the comparison,
including:

- common shadow artifact identity
- run_reality_state
- verdict
- source_artifacts
- relation_scope
- summary
- reasons
- payload.command_rcs
- payload.branch_states
- payload.artifacts
- payload.comparison

### Interpretation

- the paradox summary surface captures disagreement output  
- the run manifest surface captures run context, branch states,
  referenced artifacts, and comparison counters  

Both remain diagnostic and non-normative.

They do not change the normative authority of the final
status.json["gates"] path.

---

## 7. Local contract validation

After producing or editing EPF artifacts locally, validate them separately.

### Validate the paradox summary

~~~bash
python PULSE_safe_pack_v0/tools/check_epf_paradox_summary_contract.py \
  --input epf_paradox_summary.json
~~~

Optional JSON result output:

~~~bash
python PULSE_safe_pack_v0/tools/check_epf_paradox_summary_contract.py \
  --input epf_paradox_summary.json \
  --output epf_paradox_summary_contract_check.json
~~~

### Validate the broader run manifest

~~~bash
python PULSE_safe_pack_v0/tools/check_epf_shadow_run_manifest_contract.py \
  --input epf_shadow_run_manifest.json
~~~

Optional JSON result output:

~~~bash
python PULSE_safe_pack_v0/tools/check_epf_shadow_run_manifest_contract.py \
  --input epf_shadow_run_manifest.json \
  --output epf_shadow_run_manifest_contract_check.json
~~~

### Neutral absence mode

Paradox summary:

~~~bash
python PULSE_safe_pack_v0/tools/check_epf_paradox_summary_contract.py \
  --input epf_paradox_summary.json \
  --if-input-present
~~~

Run manifest:

~~~bash
python PULSE_safe_pack_v0/tools/check_epf_shadow_run_manifest_contract.py \
  --input epf_shadow_run_manifest.json \
  --if-input-present
~~~

### Interpretation

- ok: true → the artifact matches its current EPF contract  
- ok: false → the artifact shape or semantics drifted  
- neutral: true → only for missing-input handling  

Use the summary checker for disagreement-surface validation.  

Use the run-manifest checker for broader EPF branch/run-context validation.

---

## 8. Stub / degraded mode matters

The current workflow is best-effort.

That means it can fall back to degraded or stub behavior if key inputs
are missing.

### Common degraded cases

#### A. `run_all.py` did not produce a real baseline

If `PULSE_safe_pack_v0/artifacts/status.json` is missing after
`run_all.py`, the workflow falls back to a stub `status.json`.

#### B. `pulse_gates.yaml` is missing

If `pulse_gates.yaml` is absent, both baseline and EPF comparison stay
in stub mode.

#### C. `scripts/check_gates.py` is missing

If the checker is absent, the workflow keeps stub-style outputs instead
of a real comparison.

#### D. The checker ran, but the run is still too partial to trust

If command failures, missing dependencies, or other runtime problems
leave the run incomplete, treat the result as degraded until verified.

### Practical rule

Before treating a disagreement as meaningful, first confirm the run was
real enough, not just present.

Use:

- job logs
- `epf_report.txt`, when available
- `epf_paradox_summary.json`
- `epf_paradox_summary_contract_check.json`, when available
- the actual JSON artifacts
- local command output, for local reproductions

---

## 9. How to read disagreement

A difference between baseline and EPF shadow usually means one or more of these:

- boundary sensitivity
- missing / weak evidence
- config drift
- implementation drift
- real behavioral fragility near threshold

Do **not** jump straight from:

> “EPF shadow disagreed”

to:

> “the release policy must change”

Instead:

- confirm the run was real enough
- inspect the affected gate(s)
- validate the summary artifact
- classify the disagreement
- decide whether this is:
  - just a shadow warning
  - a coverage gap
  - a config issue
  - something important enough to track

If the disagreement is real, it is good input for topology /
decision-field interpretation.

It is **not an automatic release override**.

For the full triage path, use:

```text
docs/PARADOX_RUNBOOK.md
```

---

## 10. What stays explicit

Keep this boundary explicit:

- deterministic archived artifacts carry the recorded baseline result
- the EPF shadow path is diagnostic
- the paradox summary artifact is descriptive
- contract validation checks the summary surface, not release semantics
- policy changes belong in explicit contract / CI / workflow changes, not in shadow quick fixes

That is what keeps EPF shadow useful without turning it into a hidden
release rewrite.

---

## 11. Minimal checklist

Before you trust an EPF shadow result, confirm:

- `PULSE_safe_pack_v0/artifacts/status.json` exists, or you knowingly reproduced the stub path
- `pulse_gates.yaml` exists, or you knowingly stayed in stub mode
- `scripts/check_gates.py` ran successfully, or you knowingly stayed in stub mode
- `status_baseline.json` is real enough for your comparison goal
- `status_epf.json` is real enough for your comparison goal
- `epf_paradox_summary.json` validates against the current contract
- any reported disagreement is reproducible

If those conditions are not met, fix the wiring first.

---

## 12. Related docs

- `docs/PARADOX_RUNBOOK.md` — disagreement triage path
- `docs/PULSE_topology_epf_hook_v0.md` — how EPF shadow connects to topology
- `docs/PULSE_topology_overview_v0.md` — broader topology picture
- `docs/PULSE_decision_field_v0_overview.md` — decision-oriented topology read
- `docs/STATE_v0.md` — repository release model
- `docs/status_json.md` — how to read the status artifacts
- `docs/OPTIONAL_LAYERS.md` — optional/research layer map
