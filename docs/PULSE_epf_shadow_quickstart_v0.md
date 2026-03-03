# PULSE EPF shadow quickstart (v0)

> Command-level quickstart for the optional EPF shadow comparison path.

This guide shows the **current practical EPF shadow flow** used in this
repository.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- EPF shadow is diagnostic and CI-neutral
- disagreement between baseline and EPF is something to inspect, not an
  automatic policy rewrite

For disagreement triage, see:

- `docs/PARADOX_RUNBOOK.md`

For the broader repository state, see:

- `docs/STATE_v0.md`
- `docs/DRIFT_OVERVIEW.md`

---

## 1. What this quickstart is for

Use this quickstart if you want to:

- run the current EPF shadow experiment locally,
- understand what the GitHub workflow is doing,
- inspect baseline vs EPF shadow differences,
- reproduce `epf_report.txt` / `epf_paradox_summary.json` style outputs.

This is **not** the main release-gating path.

---

## 2. Current workflow at a glance

The repository ships an optional workflow:

```text
.github/workflows/epf_experiment.yml
```

Current shape:

- it is a shadow / non-blocking workflow,
- it tries to generate a baseline via `PULSE_safe_pack_v0/tools/run_all.py`,
- it then evaluates:
  - deterministic baseline → `status_baseline.json`
  - EPF shadow → `status_epf.json`
- it compares the two and writes:
  - `epf_report.txt`
  - `epf_paradox_summary.json`

The uploaded artifact bundle is:

```text
epf-ab-artifacts
```

The quick way to think about it:

- **baseline** = deterministic decision
- **EPF shadow** = “what changes near the boundary if adaptive shadow logic is enabled?”
- **comparison output** = triage input for humans

---

## 3. Local quickstart

From repo root:

### Step 1 — Try to produce a baseline PULSE run

```bash
python PULSE_safe_pack_v0/tools/run_all.py || true
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

This mirrors the current GitHub Actions workflow shape much more closely than
assuming `run_all.py` always produced a real baseline artifact.

---

## 4. What the two runs mean

### Baseline run

The baseline run is the deterministic reference.

Interpret it as:

- “What does the current gate logic say without EPF shadow enabled?”

This is the authoritative release decision path.

### EPF shadow run

The EPF shadow run is a diagnostic comparison layer.

Interpret it as:

- “If we enable the shadow EPF logic around the boundary, do any decisions look fragile or different?”

This does **not** automatically change the main release outcome.

---

## 5. Expected outputs

After a successful local comparison flow, the most important artefacts are:

- `status_baseline.json`
- `status_epf.json`

In GitHub Actions, the workflow also writes and uploads:

- `epf_report.txt`
- `epf_paradox_summary.json`

Recommended reading order:

1. baseline deterministic status
2. EPF shadow status
3. `epf_report.txt`
4. `epf_paradox_summary.json`

---

## 6. Stub / degraded mode matters

The current workflow is best-effort.

That means it can fall back to degraded or stub behavior if key inputs are
missing.

### Common degraded cases

#### A. `run_all.py` did not produce a real baseline

If `PULSE_safe_pack_v0/artifacts/status.json` is missing after `run_all.py`,
the workflow falls back to a stub `status.json`.

#### B. `pulse_gates.yaml` is missing

If `pulse_gates.yaml` is absent, both baseline and EPF comparison stay in stub
mode.

#### C. `scripts/check_gates.py` is missing

If the checker is absent, the workflow keeps stub-style outputs instead of a
real comparison.

### Practical rule

Before treating a disagreement as meaningful, first confirm the run was
**real**, not degraded.

Use:

- job logs,
- `epf_report.txt`,
- and the actual JSON artifacts

to verify that the comparison genuinely happened.

---

## 7. How to read disagreement

A difference between baseline and EPF shadow usually means one of these:

- boundary sensitivity,
- missing / weak evidence,
- config drift,
- implementation drift,
- or real behavioral fragility near threshold.

Do **not** jump straight from:

- “EPF shadow disagreed”

to:

- “the release policy must change.”

Instead:

1. confirm the run was real,
2. inspect the affected gate(s),
3. classify the disagreement,
4. decide whether this is:
   - just a shadow warning,
   - a coverage gap,
   - a config issue,
   - or something important enough to track.

For the full triage path, use:

- `docs/PARADOX_RUNBOOK.md`

---

## 8. What remains normative

Keep this boundary stable:

- the main deterministic release path is still the normative one
- the EPF shadow path is diagnostic
- policy changes belong in the normal reviewed policy / CI path, not in shadow quick fixes

That is the whole point of keeping EPF shadow **useful without making it
silently authoritative**.

---

## 9. Minimal checklist

Before you trust an EPF shadow result, confirm:

- `PULSE_safe_pack_v0/artifacts/status.json` exists, or you knowingly reproduced the stub path
- `pulse_gates.yaml` exists, or you knowingly stayed in stub mode
- `scripts/check_gates.py` ran successfully, or you knowingly stayed in stub mode
- `status_baseline.json` is real enough for your comparison goal
- `status_epf.json` is real enough for your comparison goal
- any reported disagreement is reproducible

If those conditions are not met, fix the wiring first.

---

## 10. Related docs

- `docs/PARADOX_RUNBOOK.md` — what to do when baseline and shadow disagree
- `docs/STATE_v0.md` — current repository model
- `docs/DRIFT_OVERVIEW.md` — how shadow artifacts support drift-aware governance
- `docs/status_json.md` — how to read the status artifacts
