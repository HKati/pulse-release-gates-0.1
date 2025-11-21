# Paradox field and memory metrics (v0)

## 1. Goal

The paradox layer sits on top of the Topology v0 family and provides a
**conflict and memory field** over the release decision space.

Its goals are:

- to quantify where goals / rules are in strongest conflict,
- to show which conflicts keep coming back over many runs,
- to support human triage on **where to intervene first**.

The layer is **shadow‑only**:

- it does not change gate logic or release decisions,
- it only observes, scores, stores artefacts, and drives dashboards.


## 2. Conceptual model: Topology v0 + fields

The Stability Map v0 represents the release decision surface.
For each `ReleaseState` it attaches several fields:

- **Decision**
  - `decision`: ship / hold / rollback / …
- **Stability**
  - `instability_score` – how strong the conflict is (0–1 or scaled),
  - `rdsi` – Release Decision Stability Index, a proxy for confidence.
- **Paradox field**
  - `paradox_field_v0` – per‑axis conflict statistics.
- **EPF field**
  - `epf_field_v0` – physical signal snapshot (phi / theta / energy).

Mathematically we treat these as **discrete fields** over the state set:

- `instability_score : States → ℝ`,
- `rdsi             : States → [0,1]`,
- `paradox_field_v0 : States × Axes → ℝ^k × Labels`,
- `epf_field_v0     : States → ℝ^3` (phi, theta, energy).

The paradox layer uses these fields to answer questions like:

- which paradox axes hurt the most,
- which axes keep coming back,
- where EPF and paradox tension line up into “dangerous regions”.


## 3. Metrics

### 3.1 Instability score

`instability_score` is a weighted combination of multiple features:

\[
instability(state) = \sum_i w_i \cdot feature_i(state)
\]

where `feature_i` can be derived from:

- rule conflicts,
- policy / safety violations,
- quality signals,
- any other gate‑level indicators.

The weights `w_i` control **what the system is sensitive to**.

**Interpretation**

- low instability → mostly aligned signals and objectives,
- high instability → strong conflict between “ship” pressure and
  safety/quality constraints.


### 3.2 RDSI – Release Decision Stability Index

`rdsi ∈ [0,1]` measures how stable / trustworthy the decision looks.

High RDSI:

- many mutually reinforcing signals,
- little disagreement between subsystems.

Low RDSI:

- lots of disagreement or missing data,
- decision might be fragile or “shaky”.

Over time RDSI can be calibrated empirically:

- for example, we can look at how often runs with a given RDSI range
  required rollback / hot‑fix afterwards.


### 3.3 Paradox field and tension

`paradox_field_v0` captures statistics per paradox axis.

For each axis we track (at least):

- `runs_seen` – in how many runs this axis appeared at all,
- `times_dominant` – how often it was the dominant conflict,
- `max_tension`, `avg_tension` – tension levels (0–1 or scaled),
- `severity` – LOW / MEDIUM / HIGH / CRITICAL,
- `priority` – 1–4 (1 = highest).

#### Tension

**Tension** is a scalar on [0,1] that measures
how strong the contradiction is between two goals / rules
along a given axis.

- 0  → effectively no meaningful conflict on this axis,
- 1  → maximal conflict within the current normalisation.

The exact construction of `tension` is left flexible in v0
(it may combine constraint violations, objective trade‑offs, etc.),
but the paradox field assumes it is:

- comparable across runs,
- monotonic in “how bad the conflict feels”.


#### Severity buckets

`severity` is derived from `tension` by bucketing:

- LOW,
- MEDIUM,
- HIGH,
- CRITICAL.

In v0 this can be implemented with fixed thresholds, e.g.:

- LOW:      `tension ∈ [0.00, 0.25)`,
- MEDIUM:   `tension ∈ [0.25, 0.50)`,
- HIGH:     `tension ∈ [0.50, 0.75)`,
- CRITICAL: `tension ∈ [0.75, 1.00]`.

Later versions can switch to **data‑driven thresholds**,
for example based on empirical quantiles from the paradox history
(“top 5% of tension values is CRITICAL”, etc.).


### 3.4 Priority – what to resolve first?

`priority ∈ {1,2,3,4}` is a v0 heuristic that combines:

- how bad an axis is in a single run (`severity`),
- how often it shows up (`runs_seen`),
- how often it dominates (`times_dominant`).

One possible shape:

1. map `severity` to an integer level, e.g.  
   LOW=1, MEDIUM=2, HIGH=3, CRITICAL=4,
2. compute a raw score such as:

\[
raw = severity\_level
    \cdot (1 + \alpha \cdot \log(1 + runs\_seen))
    \cdot (1 + \beta  \cdot times\_dominant)
\]

3. bucket `raw` back into 4 priority bands.

v0 does not enforce a specific formula; the important points are:

- higher `severity` → higher priority,
- frequent and often dominant axes bubble up,
- rare/low‑impact axes naturally drift to lower priority.

Future extensions might add:

- **recency weighting** (down‑weight very old paradoxes),
- a flag that marks axes as “addressed” and gradually reduces their priority
  if tension actually goes down after an intervention.


## 4. EPF as a physical field

EPF is treated as an external, physical‑style signal that we log
in shadow‑only mode.

For each `ReleaseState` we store:

- `phi_potential` – potential / “energy level” of the physical space,
- `theta_distortion` – distortion / deformation of the system,
- `energy_delta` – change between runs (strengthening / weakening).

We treat EPF as a field:

\[
EPF(state) = (\phi, \theta, \Delta E)
\]

EPF is not used directly for gate decisions in v0:

- it does not change status computation,
- it only helps interpret decisions and paradox regions afterwards.

Typical usage patterns:

- “many red paradox axes + high EPF energy” → dangerous region,
- correlate EPF spikes with paradox tension spikes over time.


## 5. Memory / trace layer

The memory / trace layer adds a **time dimension**
to the paradox and EPF fields.

### 5.1 Per‑run summary

`summarise_decision_paradox_v0.py` produces a single summary file
per run:

- `decision_paradox_summary_v0.json`

This “atomic memo” contains:

- decision (ship / hold / rollback),
- stability snapshot (`rdsi`, `instability_score`),
- paradox overview (e.g. `max_tension`, dominant axes),
- EPF overview (`phi`, `theta`, `energy`).

Each summary is one point in the time series.


### 5.2 Historical aggregation

`summarise_paradox_history_v0.py` consumes many per‑run summaries
and builds:

- `paradox_history_v0.json`

This artefact includes e.g.:

- `runs[]` – runs with zones and EPF snapshots,
- `paradox_history` – per‑axis statistics:
  - `runs_seen`, `times_dominant`,
  - `max_tension`, `avg_tension`,
- `epf_history` – time‑series aggregates for phi/theta:
  - min / max / avg over time.

The maths here is classic time‑series aggregation:

- mean / max,
- counts,
- zone counts (how many times an axis or run was green / yellow / red).


### 5.3 Resolution plan and dashboard

`build_paradox_resolution_v0.py` takes `paradox_history_v0.json`
and produces:

- `paradox_resolution_v0.json`

For each axis:

- `severity`,
- `priority`,
- optional human‑readable focus / notes.

This is not a policy engine; it is a **triage helper**
for humans who decide where to invest effort.

`build_paradox_resolution_dashboard_v0.py` turns the resolution plan
into a dashboard‑friendly view (for charts and panels).


## 6. Dashboard views

The paradox diagrams and dashboards are built on top of the fields
and history data.

Some examples:

### 6.1 Pareto view over paradox axes

- x‑axis: paradox axes,
- y‑axis: tension or `times_dominant`.

This is a **Pareto view**:

- a small number of axes usually contribute most of the total pain,
- those are the natural starting points for resolution work.


### 6.2 Instability × RDSI quadrants

- x‑axis: `rdsi` (decision stability),
- y‑axis: `instability_score` (conflict strength).

We can partition this plane into zones:

- green  – low instability, high RDSI,
- yellow – mixed region,
- red    – high instability, low RDSI (risky runs).

Optionally we can define an explicit **risk field**:

\[
risk(state) = instability(state) \cdot (1 - rdsi(state))
\]

and use it in time‑series charts or Pareto plots
(“which runs carry the most risk?”).


### 6.3 Decision streaks / run patterns

Decision streaks show sequences of PASS / FAIL / rollback / changes
over time.

They help us see:

- paradoxes that fired only once and never came back,
- paradoxes that we keep hitting repeatedly,
  indicating deeper structural misalignment.


### 6.4 Delta log

`append_delta_log_v0.py` appends one JSON object per run to:

- `delta_log_v0.jsonl`

Each row is a small snapshot:

- decision,
- instability metrics and zones,
- paradox summary,
- EPF energy,
- git metadata, etc.

This is effectively an **event‑sourced log** of how the system evolves
run by run, and can drive additional notebooks / dashboards.


## 7. Future directions (v1 ideas)

Some natural evolutions of this v0 design:

- **Data‑driven severity buckets**  
  Use quantiles from `paradox_history_v0.json`
  instead of hand‑chosen thresholds.

- **Recency‑aware priority**  
  Combine severity, frequency, dominance, and recency
  so that very old, already resolved paradoxes
  naturally drop in priority.

- **Change‑point detection on time series**  
  Detect sudden jumps in tension / EPF energy that may correspond
  to code or configuration changes.

- **Combined EPF × paradox risk panels**  
  e.g. highlight runs where paradox severity is CRITICAL
  and EPF deviation is in the top 5% at the same time.

All of these can be added incrementally without changing
the underlying artefact schemas.

## 8. Decision risk field v0 (optional extension)

### 8.1 Motivation

Instability and RDSI already give a 2D view of how “conflicted” and how
“stable” a decision is.

For dashboards and history it is often useful to have a **single scalar**
that captures “how risky this decision looks in hindsight”.

The v0 decision risk field does exactly that:

- high when instability is high and RDSI is low,
- low when instability is low or RDSI is high,
- bounded on \[0, 1].

### 8.2 Definition

Assuming both `instability_score` and `rdsi` lie in \[0, 1]:

\[
risk\_raw(state) = instability\_score(state) \cdot (1 - rdsi(state))
\]

We then clamp to \[0, 1] to be safe:

\[
risk(state) = \min\left(1, \max\left(0, risk\_raw(state)\right)\right)
\]

**Interpretation**

- `risk ≈ 0`  
  → either the decision is very stable (`rdsi ≈ 1`) or there is almost
  no conflict (`instability_score ≈ 0`).

- `risk ≈ 1`  
  → strong conflict and low decision stability at the same time.

Examples:

- `instability_score = 0.9`, `rdsi = 0.2`  
  → `risk_raw = 0.9 * (1 - 0.2) = 0.72` → high risk.
- `instability_score = 0.3`, `rdsi = 0.9`  
  → `risk_raw = 0.3 * 0.1 = 0.03` → low risk.

### 8.3 Risk zones

We derive a discrete `risk_zone` from the scalar risk, using the same
threshold pattern as for severity:

- LOW
- MEDIUM
- HIGH
- CRITICAL
- (optionally: UNKNOWN for missing data)

A simple v0 choice:

- LOW:      `risk ∈ [0.00, 0.25)`
- MEDIUM:   `risk ∈ [0.25, 0.50)`
- HIGH:     `risk ∈ [0.50, 0.75)`
- CRITICAL: `risk ∈ [0.75, 1.00]`

If instability or RDSI is missing, we can set:

- `risk = null` and `risk_zone = "UNKNOWN"`.

This keeps the pipeline safe in the presence of incomplete artefacts.

### 8.4 Where we log the risk field

The risk field is **derived** from existing data; it does not need to be
stored in the Stability Map itself. Instead we attach it in the memory /
trace artefacts:

#### Per-run summary (`decision_paradox_summary_v0.json`)

Under the stability block we add:

- `risk_score_v0` – float in \[0, 1] or `null`,
- `risk_zone` – `"LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | "UNKNOWN"`.

Example snippet:

```json
{
  "decision": "ship",
  "stability": {
    "instability_score": 0.68,
    "rdsi": 0.42,
    "risk_score_v0": 0.39,
    "risk_zone": "MEDIUM"
  },
  "paradox_overview": { ... },
  "epf_overview": { ... }
}
