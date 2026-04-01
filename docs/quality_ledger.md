# PULSE Quality Ledger

Human-readable view over one immutable `status.json` artefact.

This page documents the current renderer behavior, not an aspirational UI.
If the renderer changes, this page should change in the same PR.

The Quality Ledger is currently rendered by:

```bash
python PULSE_safe_pack_v0/tools/render_quality_ledger.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --out PULSE_safe_pack_v0/artifacts/report_card.html
```

It reads a single final `status.json` and writes a static HTML report.

Optional publication surfaces such as GitHub Pages snapshots or PR comments remain opt-in presentation layers.
They are not required parts of the normative gating path.

---

## 1. Authority boundary

Read `gates.*` first.

For release decisions, the authoritative inputs remain:

- `status["gates"]`
- the active required gate set
- `PULSE_safe_pack_v0/tools/check_gates.py`

The ledger is a descriptive explanation layer over that same artefact.

If the ledger and CI ever disagree, treat:

- `status.json`
- required gate selection
- gate enforcement

as authoritative, and treat the renderer as buggy.

Top-level convenience or descriptive fields must not override `gates.*`.

A top-level `decision` field, when present, is descriptive only and is not the source of the ledger banner.

---

## 2. How the current renderer derives the decision banner

The current renderer computes the banner from required gates plus `metrics.run_mode`.

### Required gate resolution order

1. `metrics.required_gates`, when explicitly present
2. otherwise the gate policy file referenced by `metrics.gate_policy_path`, using:
   - `metrics.required_gate_set`, when present
   - else `core_required` for `run_mode = demo` or `core`
   - else `required` for any other run mode, including `prod`, missing, or unexpected values
3. if no required gate set can be resolved, the banner becomes `UNKNOWN`

A missing or unexpected `run_mode` does not by itself force `UNKNOWN`.
`UNKNOWN` is reserved for cases where the renderer cannot resolve a decision-bearing required gate set.

### Banner mapping

- any required gate missing or not literally `true` → `FAIL`
- all required gates pass and `run_mode = prod` → `PROD-PASS`
- all required gates pass and `run_mode = core` → `STAGE-PASS`
- all required gates pass and `run_mode = demo` → `DEMO-PASS`
- all required gates pass with any other run mode, including missing or unexpected values → `PASS`

This keeps the ledger aligned with gate enforcement rather than with any descriptive top-level label.

---

## 3. What the current HTML actually surfaces

The current renderer is intentionally narrow and deterministic.

### Header metadata

The header currently surfaces selected fields such as:

- `version`
- `created_utc`
- `metrics.run_mode`
- `metrics.git_sha`
- `metrics.run_key`
- `metrics.RDSI`

### Gate tables

The renderer groups `gates.*` into presentation buckets.

Current v0 bucketing is name-based:

- **Quality gates**
  - gate ids starting with `q1_`, `q2_`, `q3_`, or `q4_`
- **Safety gates**
  - gate ids starting with `pass_controls_` or `psf_`
  - gate ids containing `sanit`
  - `effect_present`
- **Stability / auxiliary gates**
  - `refusal_delta_pass`
  - `epf_hazard_ok`
  - gate ids starting with `external_`
- **Other gates**
  - everything else

This bucketing is a renderer heuristic.
It is not a normative policy layer.

The generic gate tables currently show:

- gate id
- PASS / FAIL

They do **not** currently render per-gate threshold explanations for every gate.

### Refusal-delta section

When refusal-delta fields are present, the renderer shows:

- `metrics.refusal_delta_n`
- `metrics.refusal_delta`
- `metrics.refusal_delta_ci_low`
- `metrics.refusal_delta_ci_high`
- `metrics.refusal_policy`
- `metrics.refusal_p_mcnemar`
- `metrics.refusal_pass_min`
- `metrics.refusal_pass_strict`
- `gates.refusal_delta_pass`

### External detectors section

When an `external` block is present, the renderer shows:

- `external.all_pass`
- `external.summaries_present`
- `external.summary_count`

and, when available, one detector row per entry in `external.metrics[]`:

- detector name
- measured value
- threshold
- PASS / FAIL

Critical reading rule:

- `external.all_pass` answers the aggregate result question
- `external.summaries_present` answers the evidence-presence question

Those are not the same signal.

### Shadow / diagnostic sections

The current renderer can also show:

- `meta.q1_reference_shadow`
- selected `metrics.hazard_*` fields as an EPF hazard overlay
- the `diagnostics` object
- a traceability section

These are visibility surfaces.
They do not create new normative gate semantics.

### Traceability section

The current traceability section surfaces:

- the resolved `status.json` path used for rendering
- `version`
- `created_utc`
- `metrics.gate_policy_path`
- `metrics.gate_policy_sha256`
- `metrics.git_sha`
- `metrics.run_key`

---

## 4. What the current renderer does **not** do

This is important for V2 truthfulness.

The current renderer does **not**:

- mutate `status.json`
- compute an alternative decision model
- treat missing required gates as PASS
- promote `meta.*`, `external`, or shadow overlays into normative authority
- automatically link JUnit / SARIF exports
- provide a generic root-cause explanation for every failed gate
- guarantee threshold text beside every gate row
- use a top-level `decision` field as release authority

If a future renderer adds any of the above, this page should be updated in the same PR.

---

## 5. How humans should read the ledger

Recommended reading order:

1. **Confirm run identity**
   - is this the correct model / run / artefact?
2. **Read the banner**
   - `FAIL`, `DEMO-PASS`, `STAGE-PASS`, `PROD-PASS`, or `UNKNOWN`
3. **Read `gates.*` next**
   - inspect failed quality, safety, stability, and other gates
4. **Check external pass vs evidence presence**
   - do not infer evidence existence from aggregate pass alone
5. **Use shadow / diagnostic panels as context**
   - helpful for investigation
   - non-normative for release enforcement
6. **Archive the run context**
   - keep the ledger together with the exact `status.json`

---

## 6. Guidance for maintainers

Keep this document aligned with the actual renderer.

When changing:

- section layout
- banner derivation
- gate bucketing
- external panel shape
- shadow panel visibility
- traceability fields

update this page in the same PR.

Normative changes must happen in this order:

1. status / schema / policy
2. gate enforcement
3. renderer behavior
4. documentation

Not the other way around.

---

## 7. Safe extension rules

New ledger panels are safe when they remain pure explanation layers over immutable artefacts.

Safe extensions include:

- richer detector tables
- organisation-specific review panels
- better traceability surfacing
- additional shadow-only context blocks

The invariants remain:

- `status.json` stays the authoritative machine artefact
- required gate enforcement stays outside the renderer
- shadow visibility stays descriptive unless explicitly promoted elsewhere
- missing or unknown evidence must not be silently shown as PASS
- the rendered output should remain deterministic from the input artefact

---

## 8. Related docs

- [STATUS_CONTRACT.md](STATUS_CONTRACT.md)
- [status_json.md](status_json.md)
- [quality_ledger_example.md](quality_ledger_example.md)
- [refusal_delta_gate.md](refusal_delta_gate.md)
- [EXTERNAL_DETECTORS.md](EXTERNAL_DETECTORS.md)
- [external_detector_summaries.md](external_detector_summaries.md)
- [RUNBOOK.md](RUNBOOK.md)
- [quickstart safe-pack README](../examples/quickstart_safe_pack/README.md)
