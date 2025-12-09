# EPF hazard forecasting (proto-module)

The `epf_hazard_forecast` module is a prototype for **relational hazard
forecasting** in the PULSE · EPF (Extended Paradox Field) layer.

The goal is to provide a simple **field-level early-warning signal** that
does *not* wait for a concrete error event, but monitors the relationship
between the current EPF field state and a stable reference.

---

## High-level idea

Instead of treating errors as isolated events, the module looks at how the
field behaves relative to a "good" baseline:

- how far the current snapshot `x(t)` is from a reference `x*`,
- how stable the field appears to be,
- how fast this relationship is drifting.

From these ingredients the module builds an early-warning index `E(t)` and
classifies the result into three zones:

- **GREEN** – field stable, no near-term hazard
- **AMBER** – field distortion (pre-hazard regime)
- **RED** – field unstable (hazard imminent or active)

This makes it easier to see that something is "off" in the EPF layer
*before* a concrete failure manifests.

---

## Inputs and outputs

The module is intentionally minimal and does not depend on concrete PULSE
metrics. It only works with generic dict-like snapshots and a small history
of distances.

### Inputs

- `current_snapshot: Dict[str, float]`  
  Current metrics snapshot, e.g. a feature vector used by a release gate.
- `reference_snapshot: Dict[str, float]`  
  "Good" baseline snapshot representing a stable EPF configuration.
- `stability_metrics: Dict[str, float]`  
  Existing stability signals, e.g. `{ "RDSI": 0.82 }`.
- `history_T: List[float]`  
  Recent history of distance values between `x(t)` and `x*`.
- `cfg: HazardConfig` *(optional)*  
  Weights and thresholds for the early-warning index.

### Output

`forecast_hazard(...)` returns a `HazardState` dataclass with:

- `T` – distance between current and reference snapshot
- `S` – stability index in `[0, 1]` (higher ⇒ more stable)
- `D` – short-horizon drift estimate of `T`
- `E` – combined early-warning index
- `zone` – `"GREEN" | "AMBER" | "RED"`
- `reason` – short explanation string suitable for logs and dashboards

---

## Hazard index

The early-warning index is defined as:

```text
E(t) = α · D(t) + β · (1 - S(t))
```

where:

- `D(t)` is the average absolute change in `T` over a short history window,
- `S(t)` is a stability index in `[0, 1]` (e.g. derived from RDSI),
- `α`, `β` are configurable weights in `HazardConfig`.

The thresholds for the zones are also part of `HazardConfig`:

- `E < warn_threshold` → **GREEN**
- `warn_threshold ≤ E < crit_threshold` → **AMBER**
- `E ≥ crit_threshold` → **RED**

Note that `E(t)` is not restricted to `[0, 1]`; its scale depends on the
magnitude of the metrics and on the chosen weights. The thresholds are
therefore configuration / calibration parameters.

---

## API summary

```python
from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (
    HazardConfig,
    HazardState,
    forecast_hazard,
)
```

### `HazardConfig`

```python
from dataclasses import dataclass

@dataclass
class HazardConfig:
    alpha: float = 1.0
    beta: float = 1.0
    warn_threshold: float = 0.3
    crit_threshold: float = 0.7
    min_history: int = 3
```

- `alpha`, `beta` – weights for drift and stability loss in `E(t)`
- `warn_threshold`, `crit_threshold` – zone boundaries
- `min_history` – size of the short `T` history window used to estimate `D(t)`

### `forecast_hazard(...)`

```python
from PULSE_safe_pack_v0.epf.epf_hazard_forecast import (
    HazardConfig,
    forecast_hazard,
)

cfg = HazardConfig(
    alpha=1.0,
    beta=1.0,
    warn_threshold=0.3,
    crit_threshold=0.7,
)

history_T: list[float] = []  # maintained by the caller across calls

state = forecast_hazard(
    current_snapshot=current_features,
    reference_snapshot=baseline_features,
    stability_metrics={"RDSI": rdsi_value},
    history_T=history_T,
    cfg=cfg,
)

# update history for next call
history_T.append(state.T)

# react to the zone
if state.zone == "RED":
    log_critical("EPF hazard detected", extra={"reason": state.reason})
elif state.zone == "AMBER":
    log_warning("EPF field distortion", extra={"reason": state.reason})
else:
    log_info("EPF field stable", extra={"reason": state.reason})
```

---

## Integration notes

- The module is **proto-level** and does not participate directly in
  release gating yet.
- Integration into real gates should happen via a thin adapter that:
  - maps existing PULSE metrics into `current_snapshot` / `reference_snapshot`,
  - provides a stability metric (e.g. RDSI),
  - keeps a short `history_T` per gate or per field.
- The thresholds and weights in `HazardConfig` are expected to be tuned
  based on real data and monitoring experience.

---

## Limitations and future work

This prototype is intentionally simple. Potential future extensions:

- more advanced distance metrics (normalisation, Mahalanobis distance),
- smoothed or weighted drift estimators,
- richer explanations including which metrics contributed most to `T`,
- wiring the hazard signal into actual release gates as an optional
  early-warning quality gate.

---

## Quickstart

To see the hazard probe in action on a small synthetic time series, run:

```bash
python examples/epf_hazard_quickstart.py


The script maintains a short T history, calls forecast_hazard(...)
on each step, and prints T, S, D, E together with the selected
zone and the explanation string. This is a minimal way to get an
intuition for how the early-warning index evolves over time.


