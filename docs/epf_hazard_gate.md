# EPF hazard gate (design note)

This document sketches how to turn the EPF hazard forecasting probe into
a **soft gate** in PULSE, using the existing signals:

- `T(t)` – distance between current and baseline,
- `S(t)` – stability index,
- `D(t)` – short-horizon drift,
- `E(t)` – early-warning index and its zone:

  - `GREEN` – stable field, no near-term hazard
  - `AMBER` – field distortion (pre-hazard regime)
  - `RED` – unstable field, hazard imminent or active

The goal is to define a **gate policy** that is:

- simple and explainable,
- conservative enough for safety,
- and still usable in a CI / release workflow.

At this stage, the gate is intended to be **opt-in and experimental**.

---

## 1. Inputs

The gate consumes a `HazardState` from the EPF probe, plus optional
metadata:

- `HazardState`:
  - `T` – distance between `current_snapshot` and `reference_snapshot`
  - `S` – stability index in `[0,1]`
  - `D` – short-horizon drift of `T`
  - `E` – early-warning index
  - `zone` – `"GREEN" | "AMBER | "RED"`
  - `reason` – short explanation string

- `meta` (optional):
  - `run_id`, `experiment_id`, `commit`, etc.
  - used for reporting, not for the decision itself.

---

## 2. Gate outputs

The hazard gate can output:

- a **binary decision**: `hazard_ok ∈ {True, False}`
- a **severity** level: `LOW | MEDIUM | HIGH`
- a **reason string** for logging / UI

These can be mapped to existing PULSE gate patterns:

- `hazard_ok` → an additional boolean gate in `status.json`,
- severity and reason → fields in `metrics` or in a separate artefact
  (e.g. `epf_hazard_log.jsonl`).

---

## 3. Policy options

Several policies are possible, depending on how strict we want to be.

### 3.1 Policy A – RED-only block

- `hazard_ok = (zone != "RED")`

Interpretation:

- GREEN → OK
- AMBER → OK (but monitor)
- RED → block / manual review

Pros:

- minimal disruption: AMBER does not cause hard failures,
- RED is reserved for strong signals (high E).

Cons:

- does not treat persistent AMBER as an error,
- purely binary decision; no gradation of risk.

### 3.2 Policy B – AMBER+RED with different actions

- `hazard_ok = (zone == "GREEN")`
- `severity = zone` (or `LOW/MEDIUM/HIGH` mapping)

Possible handling:

- GREEN → automatic pass
- AMBER → pass, but require:
  - explicit acknowledgement, or
  - additional review in dashboards
- RED → fail or require manual override

Pros:

- more conservative: GREEN is required for a clean pass,
- supports richer workflows (e.g. "release, but alert").

Cons:

- more disruptive in early calibration phases,
- requires additional process/tooling around AMBER.

### 3.3 Policy C – E-based numeric thresholds

Instead of using only the zone, we can work directly with `E`:

- `hazard_ok = (E < crit_threshold)`
- `severity` based on `E` ranges, for example:

  - `E < warn_threshold` → LOW
  - `warn_threshold ≤ E < crit_threshold` → MEDIUM
  - `E ≥ crit_threshold` → HIGH

This matches the underlying `HazardConfig` parameters and keeps the
policy continuous in terms of `E`.

---

## 4. Recommended initial policy

For an **experimental, low-friction** gate, a good starting point is:

- **Binary gate**: RED-only block

  ```text
  hazard_ok = (zone != "RED")

Logging:

Always log HazardState (including reason) to epf_hazard_log.jsonl.

Optionally expose severity in metrics.

This allows the system to fail only in clearly unstable situations,
while still surfacing AMBER states for monitoring.

5. Integration into status.json (sketch)

Conceptually, an EPF hazard gate could be integrated like this:

Add a new gate to status["gates"]:
"epf_hazard_ok": true
Derive it from HazardState:
epf_hazard_ok = hazard_state.zone != "RED"
Optionally add hazard metrics:
"metrics": {
  "hazard_E": 0.12,
  "hazard_zone": "GREEN",
  "hazard_severity": "LOW",
  ...
}

The report card can then show epf_hazard_ok as one more gate row,
aligned with existing checks.

6. Safety and calibration considerations

Before enabling the gate as a hard blocker, consider:

Calibration period
Run the probe and log its output for a number of releases (e.g.
weeks) without enforcing a decision. Analyse:

distributions of E,

frequency of GREEN/AMBER/RED,

correlation with downstream incidents or anomalies.

Threshold tuning
If needed, update HazardConfig.warn_threshold and
HazardConfig.crit_threshold based on observed data.

Scope of enforcement
Start with:

a single EPF experiment or environment, or

a specific gate where EPF signals are strongest,

before rolling out across all gates / products.

Human-in-the-loop
For early deployments, treat RED as:

a trigger for manual review, rather than an immediate hard stop, or

a soft block that can be overridden with an explicit reason.

7. Current status

At the time of writing:

The EPF hazard probe (epf_hazard_forecast.py) is implemented and
tested.

Hazard results are logged via the adapter to epf_hazard_log.jsonl.

A small inspector tool can summarise E and zone statistics per gate.

This document describes how to turn those signals into a gate policy,
but does not enforce it yet. Any future change that adds an actual
epf_hazard_ok gate should reference this design note and clearly
indicate whether:

the gate is experimental / non-blocking, or

the gate is enforced as a hard blocker for specific workflows.

