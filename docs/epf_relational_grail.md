# EPF Relational Hazard Overlay

## Purpose

This document describes the EPF relational hazard overlay used by the PULSE EPF diagnostic surface.

The overlay monitors the relationship between a current field state and a stable reference field state.

It derives a scalar hazard index and maps that index into a diagnostic hazard zone.

The overlay is a diagnostic layer.

It is not a release-authority carrier.

Legacy / workshop alias:

```text
EPF Relational Grail
```

Canonical technical name in this document:

```text
EPF relational hazard overlay
```

## Boundary

The EPF relational hazard overlay provides a diagnostic hazard-zone classification.

It does not replace deterministic release gates.

It does not redefine PULSEmech release authority.

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The overlay may produce evidence signals.

Those signals participate in release authority only when a specific field is:

```text
recorded as release evidence
referenced by declared policy
enforced as a required gate
checked through the strict fail-closed path
```

Until that happens, the overlay remains diagnostic.

## Core idea

The overlay evaluates:

```text
current field state
vs
stable reference field state
```

The relationship can be represented as:

```text
x vs x*
```

where:

```text
x  = current field state
x* = stable reference state
```

The overlay combines this relationship with stability signals such as:

```text
RDSI-like stability signal
field distance
short-history drift
topology region
```

From these signals it derives a scalar hazard index:

```text
E(t)
```

The hazard index is then mapped into a diagnostic zone.

## Hazard zones

| Zone | Meaning | Boundary |
|---|---|---|
| GREEN | Stable field; no near-term hazard signal | Diagnostic state |
| AMBER | Field distortion; pre-hazard regime | Diagnostic state |
| RED | Unstable field; hazard imminent or active | Diagnostic state |

The zone label is a diagnostic output.

It is not a release decision.

## Topology region

The overlay may also derive a diagnostic topology-region label from:

```text
baseline_ok
hazard_zone
```

where:

```text
baseline_ok = deterministic gate baseline excluding the hazard shadow gate
hazard_zone = GREEN / AMBER / RED
```

The topology-region mapping is:

| Topology region | Condition | Meaning |
|---|---|---|
| `stably_good` | `baseline_ok` and `zone = GREEN` | Baseline passes and no near-term hazard signal |
| `unstably_good` | `baseline_ok` and `zone ∈ {AMBER, RED}` | Baseline passes, but field distortion is present |
| `stably_bad` | not `baseline_ok` and `zone = GREEN` | Baseline fails without near-term hazard escalation |
| `unstably_bad` | not `baseline_ok` and `zone ∈ {AMBER, RED}` | Baseline fails and field distortion is present |

This topology-region label is diagnostic.

It is a map of regimes.

It is not a release gate.

## Field-first interpretation

The overlay is field-first.

It reports:

```text
coordinate signal
topological read
hazard-zone classification
supporting reason string
```

The purpose is to identify whether the relationship between the current state and the reference state is beginning to distort before a concrete failure event is observed.

Hungarian summary:

```text
A relációs hazard overlay a jelenlegi állapot és a referenciaállapot viszonyát vizsgálja.
Nem a konkrét hiba pillanatában szól, hanem akkor, amikor a mező kapcsolata a referenciaállapottal már elcsúszik.
```

## Inputs

The hazard probe operates on a deterministic numeric field vector.

Typical input sources:

```text
metrics.*
gates.*
reference snapshot
short local history
```

Gate values may be represented as:

```text
true  → 1.0
false → 0.0
```

Selected metrics remain numeric.

The field vector is a coordinate representation.

It is not an alert payload.

## Reference snapshot

A deterministic reference snapshot acts as an anchor.

Example reference rules:

```text
metrics.RDSI → 1.0
gates.*      → 1.0
other numeric metrics → 0.0
```

The reference snapshot defines the local stable baseline against which the current field state is compared.

## Hazard components

The EPF relational hazard overlay may use these components:

```text
T = distance between current and reference snapshots
S = stability signal, such as RDSI
D = short-history drift estimate
E = scalar hazard index
```

The exact implementation may normalize or scale components before deriving `E`.

The documented role of `E` is:

```text
a scalar diagnostic index for hazard-zone classification
```

## End-to-end flow

The pack exposes a simple diagnostic flow:

```text
run demo gates and generate a hazard log
→ calibrate warn / crit thresholds from that log
→ inspect baseline vs calibrated thresholds
```

All commands below are intended to be run from the repository root.

## 1. Run demo gates and generate a hazard log

```bash
python PULSE_safe_pack_v0/tools/run_all.py
```

This produces standard artifacts such as:

```text
PULSE_safe_pack_v0/artifacts/status.json
PULSE_safe_pack_v0/artifacts/report_card.html
PULSE_safe_pack_v0/artifacts/epf_hazard_log.jsonl
```

The hazard log contains EPF relational hazard overlay events.

## 2. Calibrate thresholds from the hazard log

```bash
python PULSE_safe_pack_v0/tools/epf_hazard_calibrate.py \
  --warn-p 0.80 \
  --crit-p 0.98 \
  --out-json PULSE_safe_pack_v0/artifacts/epf_hazard_thresholds_v0.json
```

The calibration helper:

```text
loads epf_hazard_log.jsonl
computes E statistics
computes min / max / mean / percentile summaries
suggests global warn_threshold and crit_threshold
optionally emits per-gate suggestions when enough samples are available
writes epf_hazard_thresholds_v0.json
```

The calibration JSON is a proposal artifact.

It is not automatically trusted.

Whether thresholds are used depends on the calibration policy.

## 3. Inspect baseline vs calibrated thresholds

```bash
python PULSE_safe_pack_v0/tools/epf_hazard_debug.py
```

The debug tool can show:

```text
calibration artifact path
global.stats.count
global.warn_threshold
global.crit_threshold
effective HazardConfig.warn_threshold
effective HazardConfig.crit_threshold
threshold-source decision
```

Possible threshold-source decisions:

```text
Using BASELINE thresholds.
Using CALIBRATED thresholds from artifact.
```

A specific calibration file can be inspected with:

```bash
python PULSE_safe_pack_v0/tools/epf_hazard_debug.py \
  --calibration path/to/epf_hazard_thresholds_v0.json
```

## Calibration policy

The EPF relational hazard overlay uses the calibration artifact only when the sample-count and numeric-validity guards are satisfied.

Expected calibration path:

```text
PULSE_safe_pack_v0/artifacts/epf_hazard_thresholds_v0.json
```

Expected sample-count field:

```text
global.stats.count
```

Minimum sample guard:

```text
MIN_CALIBRATION_SAMPLES
```

Current documented value:

```text
20
```

The calibration artifact is treated as trusted only when:

```text
global.stats.count >= MIN_CALIBRATION_SAMPLES
global.warn_threshold is numeric
global.crit_threshold is numeric
0 <= warn_threshold <= crit_threshold
```

If the calibration file is missing, invalid, undersampled, or numerically unsafe, the overlay falls back to baseline thresholds.

Baseline thresholds:

```text
warn_threshold = 0.3
crit_threshold = 0.7
```

This is intentionally conservative.

Small or toy hazard logs should not silently push the EPF relational hazard overlay into an overly aggressive or overly lax regime.

## Runtime threshold behavior

When calibration is trusted:

```text
HazardConfig.warn_threshold defaults to the calibrated warn_threshold
HazardConfig.crit_threshold defaults to the calibrated crit_threshold
```

When calibration is not trusted:

```text
HazardConfig.warn_threshold uses baseline 0.3
HazardConfig.crit_threshold uses baseline 0.7
```

This keeps threshold adoption explicit and guarded.

## Artifact surfaces

### status.json

`status.json` may contain EPF relational hazard overlay fields under:

```text
gates
metrics
diagnostics
```

Typical fields include:

```text
gates.epf_hazard_ok
metrics.hazard_zone
metrics.hazard_E
metrics.hazard_T
metrics.hazard_S
metrics.hazard_D
metrics.hazard_reason
metrics.hazard_topology_region
metrics.hazard_baseline_ok
metrics.hazard_gate_id
metrics.hazard_T_scaled
metrics.hazard_stability_map_schema
metrics.hazard_stability_map_path
```

These fields are diagnostic unless a later PR explicitly promotes a specific field through:

```text
recorded evidence inclusion
declared policy reference
required-gate enforcement
strict fail-closed CI behavior
```

### report_card.html

The Quality Ledger / report card may display EPF relational hazard overlay fields as reader-facing diagnostics.

Possible reader elements:

```text
hazard zone badge
topology region badge
E-history sparkline from hazard log
feature-mode ON / OFF state
feature source
used feature keys
calibration recommendation summary
```

These elements are reader-surface diagnostics.

They do not create release authority.

### epf_hazard_log.jsonl

Append-only JSONL hazard log entries may include:

```text
gate_id
timestamp
hazard metrics
T
S
D
E
zone
reason
explainability fields
snapshot_current
snapshot_reference
meta / provenance fields
```

The log is the substrate for:

```text
threshold calibration
higher-order map building
field-drift inspection
hazard-zone review
```

The log is diagnostic by default.

### epf_hazard_thresholds_v0.json

The calibration artifact may include:

```text
global statistics
warn_threshold
crit_threshold
per-gate threshold suggestions
recommended features
feature scaler metadata
sample-count metadata
```

The artifact is trusted only if calibration guards pass.

## Feature-aware mode

Calibration may emit:

```text
thresholds
robust feature scalers
recommended_features
```

When a calibration artifact is present and sufficiently sampled, the adapter may auto-enable feature-aware mode using:

```text
recommended features
runtime allowlists
artifact allowlists
FieldSpec allowlists
snapshot intersection
```

The feature set should be bounded by intersection to avoid phantom features.

## Where this fits in the PULSE stack

The EPF relational hazard overlay is part of the EPF diagnostic surface.

It consumes field features such as:

```text
distance between current and reference snapshots
stability signals
short-history drift
topological region
```

It produces:

```text
scalar hazard index E(t)
zone label
reason string
optional explainability fields
```

The actual release enforcement is handled elsewhere through declared gate policy.

The overlay’s role is:

```text
given the current field vector,
report hazard-zone classification and supporting reason.
```

It does not independently allow or block a release.

## Safety stance

The safety stance is:

```text
deterministic fail-closed gates remain the release-decision authority
EPF hazard is diagnostic by default
enforcement is optional and explicit
calibration is guarded by sample-count and numeric-validity checks
FieldSpec may define the coordinate system without exposing sensitive keys
```

If a later PR promotes a hazard signal into release authority, that PR must declare:

```text
recorded evidence field
policy reference
required gate wiring
fail-closed enforcement behavior
tests / regression coverage
```

Until then, the EPF relational hazard overlay remains diagnostic.

## Boundary held by this document

This document describes a diagnostic EPF hazard overlay.

It does not change:

```text
PULSEmech decision semantics
gate policy
required gate wiring
check_gates.py behavior
status schema
CI allow/block behavior
Quality Ledger renderer behavior
artifact provenance binding behavior
attestation workflow behavior
release tags
DOI / Zenodo path
```

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

## Final definition

The EPF relational hazard overlay is:

```text
a diagnostic EPF layer that compares a current field state with a stable reference state,
derives a scalar hazard index E(t),
maps that index into GREEN / AMBER / RED zones,
and records the supporting reason string.
```

It is a diagnostic carrier.

It becomes release-relevant only through explicit recorded evidence inclusion, declared policy reference, required-gate enforcement, and strict fail-closed CI behavior.
