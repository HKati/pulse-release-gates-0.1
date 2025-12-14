# EPF Relational Grail

The **EPF Relational Grail** is the early‑warning hazard layer in the
PULSE EPF (Extended Paradox Field) stack.

Instead of waiting for a concrete error event, it monitors:

- the *relationship* between a current state and a stable reference state
  (x vs x\*), and
- existing stability metrics (e.g. an RDSI‑like signal),

and from these signals it derives a scalar hazard index **E(t)**.

The index is mapped into three zones:

- **GREEN** – stable field, no near‑term hazard
- **AMBER** – field distortion (pre‑hazard regime)
- **RED** – unstable field, hazard imminent or active

In Hungarian: a Relációs Grál a viszony‑alapú hazard réteg – nem a konkrét
hiba pillanatában szól, hanem akkor, amikor a mező kapcsolata a referencia
állapottal már elcsúszott.

---

## End‑to‑end flow

The pack exposes a simple flow around the EPF Relational Grail:

1. run the demo gates and generate a hazard log,
2. calibrate warn/crit thresholds from that log,
3. inspect which thresholds are actually used at runtime.

All commands below are intended to be run from the repository root.

### 1. Run demo gates and generate a hazard log

```bash
python PULSE_safe_pack_v0/tools/run_all.py

This produces the standard artefacts:

PULSE_safe_pack_v0/artifacts/status.json

PULSE_safe_pack_v0/artifacts/report_card.html

PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl ← hazard events
for the EPF Relational Grail

2. Calibrate thresholds from the hazard log

python PULSE_safe_pack_v0/tools/epf_hazard_calibrate.py \
  --warn-p 0.80 \
  --crit-p 0.98 \
  --out-json PULSE_safe_pack_v0/artifacts/epf_hazard_thresholds_v0.json

The calibration helper:

loads epf_hazard_log.jsonl,

computes E statistics (min / max / mean and percentiles),

suggests global warn_threshold / crit_threshold from configurable
percentiles (warn_p, crit_p),

optionally emits per‑gate suggestions when enough samples are available,

writes everything to epf_hazard_thresholds_v0.json.

This JSON is a proposal only; whether the thresholds are actually
used depends on the calibration policy below.

3. Inspect baseline vs calibrated thresholds

python PULSE_safe_pack_v0/tools/epf_hazard_debug.py

The debug helper prints:

the built‑in baseline thresholds:

DEFAULT_WARN_THRESHOLD = 0.3

DEFAULT_CRIT_THRESHOLD = 0.7

a summary of the calibration artefact:

global.stats.count

global.warn_threshold

global.crit_threshold

the effective HazardConfig() values:

warn_threshold

crit_threshold

a one‑line decision:

“Using BASELINE thresholds (calibration missing/insufficient).” or

“Using CALIBRATED thresholds from artefact.”

If you maintain multiple calibration files, you can point the debug tool
to a specific one:

python PULSE_safe_pack_v0/tools/epf_hazard_debug.py \
  --calibration path/to/epf_hazard_thresholds_v0.json

Calibration policy

The EPF Relational Grail uses the calibration artefact only if there is
enough data to trust it.

In epf_hazard_forecast.py:

the calibration file is expected at

PULSE_safe_pack_v0/artifacts/epf_hazard_thresholds_v0.json

the global sample count is read from

global.stats.count

the guard is

MIN_CALIBRATION_SAMPLES (currently 20)

The logic is:

If the calibration file is missing or invalid →
fall back to the baseline thresholds.

If global.stats.count < MIN_CALIBRATION_SAMPLES →
still fall back to the baseline thresholds.

Only when global.stats.count >= MIN_CALIBRATION_SAMPLES and both
global.warn_threshold and global.crit_threshold are numeric and
sane (0 <= warn <= crit) do we treat the artefact as trusted.

In that case:

HazardConfig.warn_threshold defaults to the calibrated value,

HazardConfig.crit_threshold defaults to the calibrated value.

Otherwise, the baseline remains:

warn_threshold = 0.3

crit_threshold = 0.7

This is intentionally conservative: small or toy hazard logs should not
be able to silently push the EPF Relational Grail into a too aggressive
or too lax regime.

Where this fits in the PULSE stack

Conceptually:

the EPF Relational Grail sits inside the EPF layer,

it consumes features like:

distance between current and reference snapshots (T),

stability signals (S, e.g. RDSI),

short history of T to estimate drift (D),

it produces:

a scalar hazard index E(t),

a zone label (GREEN / AMBER / RED),

a short human/machine‑readable reason string.

The actual enforcement is handled elsewhere (gate policy). This module’s
job is to say:

“Given what I see in the field, this is how close we are to a hazard
regime, and this is why.”


# EPF Relational Grail — Hazard Overlay

This document describes the EPF hazard overlay as used by PULSE_safe_pack_v0.

## Intent

The EPF hazard layer is a **field-first diagnostic overlay**.
It is not meant to replace deterministic release gates, and it should not
degrade into a classic “alerts & thresholds” system.

Instead, it provides:
- a **coordinate signal** (E) over a stable field snapshot,
- a **topological read** of the current state (stably/unstably × good/bad),
- and a path to calibrated, feature-aware measurement.

## Core concepts

### Field snapshot
The hazard probe operates on a deterministic, numeric-only **field vector**:

- `metrics.*` (selected numeric metrics)
- `gates.*` (gate outcomes as 0/1)

This is explicitly a *coordinate system*, not an alert payload.

A deterministic `reference_snapshot` acts as an anchor:
- `metrics.RDSI → 1.0`
- `gates.* → 1.0`
- other numeric metrics default to `0.0`

### Hazard components
The hazard forecast yields:
- `T`: distance between current and reference
- `S`: stability proxy
- `D`: drift proxy
- `E`: aggregated hazard index
- `zone`: `GREEN / AMBER / RED`
- `reason`: human-readable explanation (safe to surface)

### Topology region (diagnostic)
We interpret the joint state of:
- `baseline_ok` (deterministic gates excluding the hazard shadow gate), and
- `hazard_zone`

as a topological label:

- `stably_good`  = baseline_ok AND zone=GREEN
- `unstably_good` = baseline_ok AND zone∈{AMBER,RED}
- `stably_bad`   = NOT baseline_ok AND zone=GREEN
- `unstably_bad`  = NOT baseline_ok AND zone∈{AMBER,RED}

This is a **map of regimes**, not a gate.

## Artifacts

### artifacts/status.json
`status.json` contains:
- `gates`: deterministic results + `epf_hazard_ok` (shadow gate by default)
- `metrics`: includes `hazard_*` fields such as `hazard_E`, `hazard_zone`,
  `hazard_topology_region`, feature-mode provenance, and calibration summary.

### artifacts/report_card.html
A demo “Quality Ledger view”:
- hazard zone badge
- topology region badge
- E-history sparkline (from hazard log)
- feature-mode ON/OFF + source + used keys
- calibration recommendation summary (if present)

### artifacts/epf_hazard_log.jsonl
Append-only JSONL log entries from the hazard adapter.
Each entry includes:
- `gate_id`, `timestamp`
- `hazard` metrics (T,S,D,E,zone,reason, explainability fields)
- optional `snapshot_current` / `snapshot_reference` (sanitized numeric-only)
- optional `meta` (e.g., provenance)

This log is the substrate for calibration and higher-order map building.

## Calibration and feature-aware mode

Calibration can emit:
- thresholds (global/per-gate), and optionally
- robust feature scalers and `recommended_features`

When a calibration artifact is present and sufficiently sampled, the adapter may
auto-enable feature mode (autowire) using:
- recommended features (preferred bound),
- optional allowlists (runtime / artifact / FieldSpec), combined by intersection,
- and snapshot intersection to avoid phantom features.

## Safety stance

- Deterministic fail-closed gates remain the source of truth.
- Hazard is diagnostic by default.
- Enforcement is optional and explicit (e.g., via environment flag in CI).
- FieldSpec can define the coordinate system without leaking sensitive keys.



