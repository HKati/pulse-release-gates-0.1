# PULSE Hazard Forecasting Dashboard (v0)

The PULSE Hazard Forecasting Dashboard is the first UI concept where:

- **field tension** becomes visible,
- **drift is surfaced early**, not only after failures,
- the model shows **not just status, but near‑term future**,
- and the full rhythm of PULSE can finally be seen as a dynamic field.

This document describes a conceptual v0 of the dashboard – a structure that
can be implemented and iterated on, even if the visual design changes later.

---

## 1. Layout at a glance

The dashboard is composed of five main panels:

1. **Top Status Bar** – instant, composite signal (now)
2. **E(t) Early Warning Panel** – drift / tension (near future)
3. **Time‑Series Panel** – E(t), T(t), S(t), D(t) together over time
4. **Release Gate Integration** – decision support panel
5. **Visualized Field Map (EPF space)** – optional future panel

All panels are grounded in the same underlying quantities from the
EPF hazard forecasting module:

- `T(t)` – distance between current snapshot and baseline
- `S(t)` – stability index
- `D(t)` – drift of `T(t)`
- `E(t)` – combined early warning index

---

## 2. Panel 1 – Top Status Bar (instant composite signal)

This panel is the very top of the dashboard: a thin status strip that
shows the overall state in one glance.

Example (ASCII wireframe):

```text
╔══════════════╦══════════════════════╦══════════════════════╗
║ PULSE STATUS ║ STABILITY S(t)       ║ E(t) INDEX           ║
╠══════════════╬══════════════════════╬══════════════════════╣
║ GREEN        ║ 0.94                 ║ 0.12  (LOW)          ║
╚══════════════╩══════════════════════╩══════════════════════╝
```

**Semantics**

- **PULSE STATUS**  
  - Overall traffic‑light status (`GREEN / AMBER / RED`), derived primarily
    from `E(t)` and possibly other high‑level signals.
- **STABILITY S(t)**  
  - Field stability index in `[0,1]` (e.g. from RDSI or similar).
- **E(t) INDEX**  
  - Current early‑warning score, mapped into qualitative levels (LOW / MEDIUM / HIGH).

**Why it matters**

This is the first place where the *triple logic* appears in one line:

- current condition,
- field stability,
- near‑term hazard signal.

It upgrades the classic pass/fail status indicator into a **field‑aware,
future‑sensitive status bar**.

---

## 3. Panel 2 – E(t) Early Warning Panel (drift / tension)

The second panel zooms into the hazard forecasting module itself. It
exposes the internal quantities of the `epf_hazard_forecast` probe.

Example:

```text
EARLY WARNING — Hazard Forecast
──────────────────────────────────────────────────────────────

E(t) Index:       0.12  (LOW)
Drift D(t):       0.03
Stability S(t):   0.94
Distance T(t):    0.41

Trend:
  ↗ T(t) slowly increasing
  ↔ S(t) stable
  ↗ D(t) minor drift detected

Forecast:
  No hazard expected in next cycle
```

**Inputs**

- all values taken directly from a `HazardState`:
  - `T`, `S`, `D`, `E`, plus zone.

**Roles of the fields**

- `E(t)` – composite early‑warning signal (*field tension*).
- `D(t)` – how much the field has moved recently.
- `S(t)` – how stable the field appears.
- `T(t)` – how far the current state is from the reference.

**Trend / Forecast**

- **Trend** text summarises recent changes:
  - direction and rough magnitude of T, S, D.
- **Forecast** is a short natural‑language statement derived from E(t),
  current zone, and recent trend:
  - e.g. *"No hazard in next cycle"*,  
    *"Monitor: rising E(t) with weakening S(t)"*,  
    *"High hazard probability if current drift continues"*.

This panel is the **human‑readable face** of the EPF hazard model.

---

## 4. Panel 3 – Time‑Series Panel: E(t), T(t), S(t), D(t) together

The third panel shows how the field behaves over time. It is the most
visually rich block: four stacked time series sharing the same time axis.

Conceptual wireframe:

```text
E(t):  ────▁▂▃▃▄▅▅▆▇
T(t):  ──▁▁▂▂▃▄▄▅▅▆
S(t):  ████████▇▇▆▆▅
D(t):  ▁▁▂▂▂▃▃▃▅▆
time → t₀                       t_now
```

**What this should reveal**

- **E(t) rises before S(t) drops**  
  The early‑warning index starts climbing while stability is still high.
- **T(t) “builds up” before an instability event**  
  Distance from the baseline grows in characteristic patterns.
- **D(t) picks up subtle drifts**  
  Small but persistent movements in T(t) are made visible.

This panel transforms the field into something you can *see moving*:

- stagnating,
- drifting,
- distorting,
- recovering.

It is the bridge from **numbers** to **field dynamics**.

---

## 5. Panel 4 – Release Gate Integration (decision support)

The fourth panel connects the field‑level view to actual release
decisions. Instead of a rigid pass/fail gate, it becomes a **dynamic
decision surface**.

Example:

```text
RELEASE DECISION SUPPORT
──────────────────────────────────────────────────────────────

E(t):          LOW
S(t):          Stable
T(t) Trend:    Weak upward slope

Recommended Action:
  ✓ Safe to Release
  △ Monitor E(t) over the next cycle

Reasoning:
  Predicted stability holds for 1–2 future ticks,
  with only minor drift observed in T(t).
```

**Key ideas**

- Not just *"gate passed / gate failed"*, but:
  - *"Safe to release, but keep an eye on drift"*,
  - *"Hold release: field is unstable, E(t) is high"*, etc.
- The panel assumes:
  - a `HazardState` from the EPF probe,
  - optional additional gate data (standard metrics, tests),
  - a simple policy that maps these into:
    - action (Release / Monitor / Hold),
    - reasoning text.

This aligns safety gating with the core PULSE philosophy:
the system reasons in terms of **paradoxons and field relations**,
not solely discrete errors.

---

## 6. Panel 5 – Visualized Field Map (EPF space) – optional future panel

The fifth panel is a more advanced, optional layer that visualises the
EPF field itself as a map. It shows where the field is distorted and
how that relates to E(t).

Conceptual example:

```text
EPF FIELD DISTORTION MAP (t)
──────────────────────────────────────────────────────────────
Green basin   → low tension, high stability
Amber ridge   → moderate distortion, watch zones
Red spikes    → localised instability (aligns with E(t) peaks)
```

Possible elements:

- **Background**: regions where the field is close to the baseline (green basin).
- **Ridges / gradients**: areas with growing tension or drift (amber).
- **Spikes / hotspots**: local paradox regions (red).

This panel shows:

- where the field is bending,
- where stability is weakening,
- which "directional error" regions are expanding.

It is a natural future extension once EPF mapping and visualisation are
available.

---

## 7. Data flow and mapping to the EPF hazard module

All panels share a single underlying data flow:

1. **Snapshots**
   - `current_snapshot` – current metrics / features,
   - `reference_snapshot` – baseline (learned normal or chosen reference).

2. **Stability metrics**
   - `stability_metrics` – includes `RDSI` or related EPF stability signals.

3. **Hazard probe**
   - `HazardConfig` – configuration of weights and thresholds,
   - `forecast_hazard(...)` – called once per cycle, returns `HazardState`.

4. **History**
   - a short list `history_T` maintained across cycles to estimate drift.

5. **UI mapping**
   - **Status Bar**:
     - `zone`, `S`, `E`
   - **Early Warning Panel**:
     - `T`, `S`, `D`, `E` + derived trend/forecast text
   - **Time‑Series Panel**:
     - time‑stamped history of `T`, `S`, `D`, `E`
   - **Release Gate Panel**:
     - `zone`, `E`, trends + gate‑specific policies
   - **Field Map** (future):
     - EPF field data derived from deeper EPF layers, correlated with E(t).

This way, the entire dashboard is a **visualisation of one coherent
field‑level model**, not a collection of disconnected widgets.

---

## 8. Summary – what does this dashboard make visible?

By inserting this dashboard into the system, PULSE gains:

- ⭐ A **forward‑looking** view: hazard signals before failures.
- ⭐ Visibility into **field distortions**, not only metric thresholds.
- ⭐ Insight into the **cycle of future errors** (how instability builds).
- ⭐ A **time‑based visual narrative** of T(t), S(t), D(t), E(t).
- ⭐ A new UI category: **field‑based AI safety dashboard**, not just
  test result summaries.

This is the **PULSE Hazard Forecasting Dashboard v0**.

And it is designed to become the true visible face of the PULSE field.
