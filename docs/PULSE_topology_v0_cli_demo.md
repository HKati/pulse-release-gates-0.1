# PULSE topology v0 CLI demo

> Practical CLI demo path for the optional topology layer on top of
> deterministic PULSE artifacts.

This page is a **hands-on demo guide**.

It is for readers who want to see how the current topology-family tools fit
together from the command line without confusing demo outputs with the
repository’s normative release path.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- topology tools are optional and diagnostic
- CLI demo outputs are reviewer-facing artifacts, not automatic policy rewrites

For the conceptual layer, see:

- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_topology_v0_methods.md`
- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_decision_field_v0_overview.md`

For the quickest Decision Engine path, see:

- `docs/PULSE_topology_v0_quickstart_decision_engine_v0.md`

---

## 1. What this CLI demo is for

Use this page if you want to:

- start from a real baseline `status.json`,
- generate optional topology inputs from the command line,
- inspect the current live tool CLIs in your checkout,
- and produce a compact reviewer-facing topology summary.

This is the CLI-level “show me the moving parts” page.

It is **not** the normative release workflow.

---

## 2. Minimum prerequisites

You should have:

- a checked-out repo,
- Python available,
- a baseline run artifact:
  - `PULSE_safe_pack_v0/artifacts/status.json`

Recommended companion artifact:

- `PULSE_safe_pack_v0/artifacts/report_card.html`

If you do not have a real baseline `status.json`, stop here.  
The topology family should not be treated as authoritative without it.

---

## 3. Demo flow at a glance

The shortest honest CLI demo is:

1. run the deterministic baseline,
2. generate optional paradox context,
3. inspect optional Stability Map tooling,
4. inspect/run the Decision Engine,
5. read the output as a reviewer-facing summary.

A good mental model is:

- baseline first
- optional context second
- compact summary last

---

## 4. Step 1 — Produce the deterministic baseline

From repo root:

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

Expected baseline artifacts:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

Quick sanity check:

```bash
python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status PULSE_safe_pack_v0/artifacts/status.json
```

Interpretation:

this is the authoritative machine-readable baseline for the rest of the demo

---

## 5. Step 2 — Generate optional paradox context

Create a working output directory:

```bash
mkdir -p out
```

Then generate a paradox field from the baseline artifact directory:

```bash
python PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py \
  --status-dir PULSE_safe_pack_v0/artifacts \
  --output out/paradox_field_v0.json
```

You can inspect the live CLI anytime with:

```bash
python PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py --help
```

Expected output:

- `out/paradox_field_v0.json`

Interpretation:

- this is optional conflict/tension structure for later reviewer interpretation
- it does not change baseline release semantics

---

## 6. Step 3 — Inspect the Stability Map demo surface

The repository currently exposes a demo Stability Map tool surface.

Start by inspecting the live CLI in your checkout:

```bash
python PULSE_safe_pack_v0/tools/pulse_stability_map_demo_v0.py --help
```

What matters conceptually:

- the current repo-level surface is a demo/prototype Stability Map path
- it is useful for learning the topology stack
- it should not be overstated as a fully generalized production stability-map pipeline

If your local checkout exposes an output file, keep it alongside the other demo
artifacts.

Typical demo output name:

- `stability_map_v0_demo.json`

Interpretation:

- this gives you an optional stability-oriented topology input
- it is diagnostic context, not a normative gate artifact

---

## 7. Step 4 — Inspect the Decision Engine CLI

Now inspect the live Decision Engine surface:

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py --help
```

The current repo-level expectation is:

- required input:
  - one baseline `status.json`
- optional inputs:
  - Stability Map
  - paradox field
- output:
  - `decision_engine_v0.json`

The exact CLI flag spelling should follow the live `--help` output in your own
checkout.

That is the safest and most honest CLI-demo rule.

---

## 8. Step 5 — Run the Decision Engine with the artifacts you actually have

Run the Decision Engine using:

- the required baseline `PULSE_safe_pack_v0/artifacts/status.json`
- optional `out/paradox_field_v0.json`, if produced
- optional Stability Map demo artifact, if produced

Write the result to a compact output such as:

- `out/decision_engine_v0.json`

Follow the exact flag names from:

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py --help
```

Do not fabricate optional inputs just to make the output look richer.

Missing optional context is better than invented context.

---

## 9. Minimal demo modes

You do not need the full stack every time.

### Mode A — Baseline only

Inputs:

- `PULSE_safe_pack_v0/artifacts/status.json`

Use when:

- you want the smallest possible reviewer-facing summary
- you are only proving the Decision Engine path works

### Mode B — Baseline + paradox field

Inputs:

- baseline `status.json`
- `out/paradox_field_v0.json`

Use when:

- you want conflict/tension structure in the summary
- you want a more honest description of fragile runs

### Mode C — Baseline + paradox field + Stability Map

Inputs:

- baseline `status.json`
- `out/paradox_field_v0.json`
- Stability Map demo artifact, if available

Use when:

- you want the richest current topology demo path
- you are building reviewer notes or dashboard prototypes

---

## 10. How to read the demo outputs

Recommended reading order:

1. baseline `status.json`
2. baseline `report_card.html`
3. optional `paradox_field_v0.json`
4. optional Stability Map artifact
5. `decision_engine_v0.json`

This order matters.

It keeps the compact topology summary anchored to the evidence beneath it.

---

## 11. Example reviewer interpretations

### Baseline PASS, quiet optional context

Possible reviewer-facing posture:

- `release_state: PROD_OK`
- `stability_type: stable_good`

Meaning:

- positive baseline
- low reviewer concern
- ordinary confidence

### Baseline PASS, noisier optional context

Possible reviewer-facing posture:

- `release_state: STAGE_ONLY`
- `stability_type: unstably_good`

Meaning:

- deterministic baseline still passes
- but paradox/stability context suggests caution

### Baseline FAIL

Possible reviewer-facing posture:

- `release_state: BLOCK`
- `stability_type: stable_bad or unstably_bad`

Meaning:

- the baseline still governs
- optional context may explain the posture more honestly, but does not silently undo the failure

---

## 12. What remains normative

Keep this boundary stable:

- deterministic baseline gating remains authoritative
- topology CLI artifacts remain diagnostic
- Decision Engine output is a compact reviewer-facing summary
- missing optional artifacts must never be treated as evidence of calm or PASS

If a compact topology summary and the deterministic baseline disagree, the
baseline wins.

---

## 13. Recommended demo archive bundle

When this CLI demo produces a result worth keeping, archive together:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`
- `out/paradox_field_v0.json`, when produced
- Stability Map demo output, when produced
- `out/decision_engine_v0.json`, when produced
- any short reviewer note derived from the same run

This makes the demo chain reconstructible later.

---

## 14. Common mistakes to avoid

Do not:

- skip the baseline and read only the compact summary
- treat demo outputs as silent policy changes
- assume missing optional overlays imply stability
- fabricate topology inputs
- confuse a useful reviewer-facing summary with the normative release contract

The CLI demo is valuable precisely because it stays honest about those limits.

---

## 15. Summary

The shortest honest topology CLI demo is:

- produce a real deterministic baseline
- optionally generate paradox context
- optionally inspect/use the Stability Map demo surface
- run the Decision Engine against the artifacts you actually have
- read the result as a reviewer-facing interpretation layer

That is enough to make the topology stack useful for:

- demos
- governance prototypes
- reviewer handoff
- dashboard experiments

without blurring the repository’s normative release boundary.
