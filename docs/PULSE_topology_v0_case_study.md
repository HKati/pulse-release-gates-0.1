# PULSE topology v0 case study

> Status: draft — case study / worked example.  
> Scope: one-run, artifact-derived “field read” that preserves boundary/fragility/paradox structure **without** changing deterministic release semantics.

This case study shows a practical reading order for one archived run:

1) deterministic baseline artifacts (what was recorded)  
2) optional diagnostic signal families (EPF shadow / paradox-field / external evidence)  
3) a topology-style stability posture that keeps structural distinctions visible  

This page does **not** define release semantics. Release semantics are specified in:

- `docs/STATE_v0.md`
- `docs/status_json.md`
- `docs/STATUS_CONTRACT.md`
- `pulse_gate_policy_v0.yml`
- `.github/workflows/pulse_ci.yml`

Related docs:

- Concept: `docs/PULSE_topology_v0_design_note.md`
- Overview: `docs/PULSE_topology_overview_v0.md`
- Decision-field view: `docs/PULSE_decision_field_v0_overview.md`
- Methods: `docs/PULSE_topology_v0_methods.md`
- EPF/paradox triage: `docs/PARADOX_RUNBOOK.md`

---

## Important boundary

- The deterministic archived artifacts record the baseline release result for a run.
- Topology/Decision Engine are **artifact-derived diagnostic overlays**.
- Topology may refine **stability posture** (boundary pressure, fragility, paradox concentration, evidence completeness).
- Topology must not silently rewrite CI outcomes or the recorded baseline result.
- Missing diagnostics remain explicit (missing ≠ stable, missing ≠ PASS).

---

## 1. Scenario

Assume a release candidate completes a deterministic PULSE run.

Baseline signals look “green”:

- required gates pass for the configured required set
- the run is recorded as acceptable by the deterministic artifact chain

But optional diagnostics suggest the run is not “boring”:

- near-threshold behaviour on an important quality dimension
- boundary sensitivity under a shadow/perturbation view (EPF)
- recurring tension/co-occurrence patterns in a small gate family (paradox/field view)

This is exactly where topology helps: it keeps “PASS but fragile” distinct from “PASS and robust”.

---

## 2. Artifact chain for this case

### Required baseline artifacts

These anchor the run and its recorded outcome:

- `PULSE_safe_pack_v0/artifacts/status.json`
- `PULSE_safe_pack_v0/artifacts/report_card.html`

### Optional diagnostic artifacts (when present)

These enrich the structural read but do not change the baseline record:

- EPF shadow artifacts (if the EPF pipeline was run)
- paradox/field artifacts such as `paradox_field_v0.json`
- external detector summaries (if folded in)
- hazard/instability probes (if produced)

### Optional topology / compact projection outputs

These are “read surfaces” derived from the above:

- Stability Map–style artifacts (demo/prototype or future generalized builders)
- `decision_engine_v0.json` (compact diagnostic overlay)

---

## 3. Baseline deterministic reading

Start with baseline artifacts first.

Minimal baseline interpretation:

- recorded polarity/outcome: positive (for the required set)
- failed required gates: none
- release meaning: “acceptable per baseline artifacts”

Invariant:

> Any later topology label must remain anchored to this recorded baseline outcome, not replace it.

---

## 4. Optional diagnostic context (when available)

### 4.1 EPF shadow signal (optional)

When EPF shadow evidence is present, it can reveal boundary behaviour such as:

- small perturbations flipping a nearby outcome
- local non-robustness around a threshold
- disagreement clustering around a gate family

Interpretation rule:

- EPF refines stability posture (fragility / boundary pressure).
- EPF does not overwrite the baseline outcome.

### 4.2 Paradox / field signal (optional)

When paradox/field outputs are present, they preserve conflict structure such as:

- recurrence within a gate family
- locality vs spread of tension
- isolated vs systemic fragility
- concentration vs diffusion of paradox pressure

Interpretation rule:

- paradox/field outputs are diagnostic signal families
- their absence must remain absence (not “zero tension”)

### 4.3 Evidence completeness (optional)

Track whether key evidence families are present.

Rule:

> Missing inputs stay missing. Don’t interpret missing as calmness.

---

## 5. Topology-style read of this run

A topology interpretation for the scenario might be:

- release polarity: positive (baseline)
- stability posture: unstable / fragile
- paradox pressure: present but localized
- evidence completeness: partial (if some optional families are missing)

A compact topology label for this pairing:

- `unstably_good`

Meaning:

- baseline is positive
- but the run is boundary-close / fragile under available diagnostics

---

## 6. Decision Engine overlay (illustrative but tool-shaped)

A compact Decision Engine artifact can encode the same posture in a stable, machine-readable way.

Example snippet (illustrative values):

```json
{
  "decision_engine_v0": {
    "version": "PULSE_decision_engine_v0",
    "generated_at_utc": "2025-01-10T12:34:56Z",
    "inputs": {
      "status_path": "PULSE_safe_pack_v0/artifacts/status.json",
      "stability_map_path": "out/stability_map_v0_demo.json",
      "paradox_field_path": "out/paradox_field_v0.json"
    },
    "release_state": "PROD_OK",
    "stability_type": "unstably_good",
    "status_summary": {
      "gate_count": 42,
      "failed_gates": [],
      "passed_gates": [
        "quality.q3_fairness_ok",
        "slo.q4_slo_ok"
      ],
      "rdsi": 0.94
    },
    "stability_summary": {
      "cell_count": 1,
      "delta_bend_max": 1.0
    },
    "paradox_summary": {
      "atom_count": 3,
      "severe_atom_count": 1
    }
  }
}
```

Interpretation:

- `release_state` is a compact baseline-derived encoding (diagnostic label, not the release contract)
- `stability_type` carries the fragility cue (`unstably_good`)
- the artifact remains reconstructible via `inputs.*_path`

---

## 7. Why this is better than plain PASS/FAIL

A plain:

```
PASS
```

often gets treated as “routine confidence”.

Topology preserves the distinction:

> “not blocked” is not always the same as “robust and boring”

That prevents boundary-close PASS cases from being silently treated as routine.

---

## 8. What topology does not do

Topology is not allowed to:

- silently convert baseline PASS into baseline FAIL
- silently change required gate policy
- “rescue” a failing baseline with nicer narrative
- treat missing diagnostics as evidence of stability

If policy needs to change, it belongs in the explicit contract/policy/workflow path.

---

## 9. Practical follow-up actions (when this repeats)

When a run repeatedly lands in a boundary-sensitive posture:

- keep the baseline outcome visible and unchanged
- record the diagnostic stability posture (`unstably_good`)
- check whether the same gate family keeps clustering under EPF/paradox signals
- if it repeats, open a tracked follow-up to investigate the threshold region and evidence coverage

Topology is most valuable **before the baseline starts failing**: it makes early fragility visible.

---

## 10. Contrasting cases (mental calibration)

### Case A — stable_good

- baseline positive
- quiet optional context (if present)
- low boundary pressure / low paradox concentration

### Case B — unstably_good (this case study)

- baseline positive
- boundary sensitivity / non-trivial paradox structure / partial evidence completeness
- still positive, but fragile

---

## 11. Summary

Baseline answers:

> “Is the run currently acceptable per deterministic artifacts?”

Topology adds:

> “How structurally comfortable is that answer (robust vs boundary-close vs under-observed)?”

In this case study, the honest posture is:

```
positive, but fragile
unstably_good
```
