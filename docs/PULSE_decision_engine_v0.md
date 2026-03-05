# PULSE Decision Engine v0

> Compact decision-oriented overlay derived from archived PULSE artifacts.

This note describes the current Decision Engine v0.

It explains:

- what the Decision Engine does today
- which artifacts it reads
- how it derives its current compact labels
- what it emits
- how it relates to topology and release semantics

It does not define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`
- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`

Important boundary:

- deterministic archived artifacts carry the recorded release result for a run
- Decision Engine v0 remains artifact-derived and diagnostic
- it does not silently mutate CI or release semantics
- optional topology inputs may enrich the read, but missing inputs remain explicit

For the broader topology picture, see:

- `docs/PULSE_topology_overview_v0.md`
- `docs/PULSE_topology_v0_design_note.md`
- `docs/PULSE_decision_field_v0_overview.md`
- `docs/PULSE_topology_v0_methods.md`

For examples, see:

- `docs/PULSE_decision_engine_v0_unstably_good_example.md`
- `docs/PULSE_decision_engine_v0_unstably_bad_example.md`
- `docs/PULSE_demo_v1_paradox_stability_showcase.md`

---

## 1. What Decision Engine v0 is

The Decision Engine is a compact decision-oriented projection over archived PULSE artifacts for a single run.

It is not a second gate engine.  
It is not the release contract.  
It is not a hidden rewrite of CI semantics.

Its job is narrower:

- read the archived `status` artifact
- optionally read topology-related overlays
- compress selected parts of that evidence into a small downstream label set
- preserve traceable summaries of why that compact label was emitted

This makes it useful for dashboards, archive inspection, demos, and downstream automation that needs a compact read without losing the evidence chain completely.

---

## 2. Current repo-level tool

Tool:

```text
PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py
```

Current method role:

- reads one required `status.json` artifact
- may also read one optional `stability_map_v0` artifact
- may also read one optional `paradox_field_v0` artifact
- emits a `decision_engine_v0` JSON overlay

Recommended output filename when materialized:

```text
decision_engine_v0.json
```

The exact output path is caller-chosen via `--output`.

---

## 3. Why the Decision Engine exists

Flat gate output is necessary, but sometimes too verbose or too low-level for downstream consumption.

At the same time, a full topology or decision-field read can be richer than some consumers need.

Decision Engine v0 exists to occupy that middle layer:

- more structured than prose-only summary
- more compact than raw gate-by-gate artifacts
- still traceable back to archived evidence

---

## 4. Inputs the current tool reads

### 4.1 Required input: `status.json`

The current tool treats `status.json` as the required anchor artifact.

When building its compact summary, it:

- prefers the top-level `gates` block when present
- falls back to `results` for older or alternative shapes
- recursively collects boolean gate fields

It records:

- total gate count
- failed gate names
- passed gate names

It also surfaces selected metrics such as:

- `rdsi`
- `rdsi_ci_lower`
- `rdsi_ci_upper`

when they are present.

This is a summary read over archived status data, not a reimplementation of CI policy.

### 4.2 Optional input: `stability_map_v0`

When a stability-map artifact is supplied, the current tool extracts a compact stability summary.

Today that summary is intentionally coarse and focuses on:

- `cell_count`
- `delta_bend_max`

The current implementation accepts either:

- a root `stability_map_v0` object containing `cells`
- or a root-level `cells` list for robustness

The current repo-level stability-map surface is still demo-grade, so this optional input may come from a synthetic or experimental artifact rather than from a fully general production builder.

### 4.3 Optional input: `paradox_field_v0`

When a paradox-field artifact is supplied, the current tool extracts a compact paradox summary.

Today that summary focuses on:

- `atom_count`
- `severe_atom_count`

In the current heuristic, an atom is treated as severe when:

```text
severity >= 0.8
```

---

## 5. Current compact classifications

Decision Engine v0 currently emits two main compact labels:

- `release_state`
- `stability_type`

These are downstream encodings.  
They are not replacement release semantics.

### 5.1 `release_state`

The current tool derives `release_state` heuristically from the archived gate summary.

Current values are:

- `PROD_OK`
- `STAGE_ONLY`
- `BLOCK`
- `UNKNOWN`

Current rule set:

- `UNKNOWN` if no gates were found
- `PROD_OK` if no gates failed
- `STAGE_ONLY` if some gates failed but the failure count is still small
- `BLOCK` if failures are numerous enough that the run is coarsely read as blocked

More precisely, the current heuristic uses:

```text
STAGE_ONLY when the number of failed gates is less than or equal to max(1, total_gates // 4)
```

This is a descriptive compression rule in the current tool, not the normative CI contract.

### 5.2 `stability_type`

The current tool derives `stability_type` from:

- the compact `release_state`
- optional stability-map summary
- optional paradox summary

Current values are:

- `stable_good`
- `unstably_good`
- `stable_bad`
- `unstably_bad`
- `boundary`
- `boundary_simple`
- `unknown`

Current heuristic idea:

- if either `delta_bend_max > 0.0` or `atom_count > 0`, the tool treats the run as having a topology signal
- that signal is then combined with `release_state` to choose a compact `stability_type`

Current mapping:

- `PROD_OK` + no topology signal → `stable_good`
- `PROD_OK` + topology signal → `unstably_good`
- `BLOCK` + no topology signal → `stable_bad`
- `BLOCK` + topology signal → `unstably_bad`
- `STAGE_ONLY` + no topology signal → `boundary_simple`
- `STAGE_ONLY` + topology signal → `boundary`
- `UNKNOWN` → `unknown`

This is intentionally coarse.  
It is useful as a compact overlay, but it is not the full decision-field or topology surface.

---

## 6. Output shape

The tool emits a JSON structure under:

```text
decision_engine_v0
```

The current output typically contains:

- `version`
- `generated_at_utc`
- `inputs`
- `release_state`
- `stability_type`
- `status_summary`
- `stability_summary`
- `paradox_summary`

This makes the output compact, machine-readable, and still traceable to the input artifacts.

---

## 7. Relationship to topology and the decision field

A clean conceptual split is:

- topology = the broader field-structural family
- Stability Map = minimal carrier of stability-oriented structure
- decision field = richer decision-oriented structural projection
- Decision Engine = compact downstream encoding of selected archived evidence

The Decision Engine therefore does not replace topology.  
It compresses selected parts of topology-relevant evidence into a smaller operational surface.

That compression is useful, but it should stay honest about what is lost:

- region structure
- adjacency
- boundary nuance
- paradox localization
- evidence-completeness detail

If that richer structure matters, read the decision field or topology artifacts directly.

---

## 8. Relationship to release semantics

Decision Engine v0 is adjacent to release semantics, but it is not the release contract.

That means:

- it may summarize archived evidence
- it may emit compact labels such as `BLOCK`, `STAGE_ONLY`, `PROD_OK`, and `UNKNOWN`
- it may materialize coarse `stability_type` labels
- it must not silently rewrite CI behavior or policy meaning

If release behavior needs to change, that belongs in explicit:

- contract changes
- policy changes
- workflow changes
- schema changes

not in Decision Engine wording alone.

---

## 9. CLI examples

### Minimal run

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --output PULSE_safe_pack_v0/artifacts/decision_engine_v0.json
```

### Run with optional topology inputs

```bash
python PULSE_safe_pack_v0/tools/pulse_decision_engine_v0.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --stability-map PULSE_safe_pack_v0/artifacts/stability_map_v0_demo.json \
  --paradox-field PULSE_safe_pack_v0/artifacts/paradox_field_v0.json \
  --output PULSE_safe_pack_v0/artifacts/decision_engine_v0.json
```

If optional topology artifacts are missing, the tool still works from `status.json` alone.

---

## 10. Non-goals

Decision Engine v0 should not:

- replace deterministic gate evaluation
- become a hidden policy layer
- treat missing optional topology artifacts as stability
- imply that compact labels are richer than the archived evidence underneath them
- pretend that the current heuristic is already a fully general multi-run decision system
- silently overrule the recorded baseline result

---

## 11. Design invariants

A healthy Decision Engine layer keeps these invariants stable:

- archived status artifacts remain the required anchor
- optional topology artifacts enrich the read without rewriting release semantics
- compact labels remain traceable to archived evidence
- missing optional inputs remain explicitly missing
- the same high-level release outcome may correspond to different structural states
- the Decision Engine remains a compression layer, not a replacement for topology

---

## 12. Summary

Decision Engine v0 is best understood as a compact, artifact-derived downstream encoding over archived PULSE run artifacts.

Today, it reads:

- required `status.json`
- optional `stability_map_v0`
- optional `paradox_field_v0`

and emits:

- a compact `release_state`
- a coarse `stability_type`
- traceable summaries of the contributing artifacts

That makes it useful for dashboards, demos, and downstream automation while keeping the release-semantics boundary explicit.
