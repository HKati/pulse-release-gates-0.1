# PULSE Topology v0 – governance patterns

This document describes governance usage patterns for the Topology v0 stack:

- `status.json` (baseline PULSE safe pack)
- `paradox_field_v0.json` (paradox atoms)
- `stability_map_v0` (optional stability / curvature overlay)
- `decision_engine_v0.json` (release_state + stability_type + summaries)

The focus is not on how to compute these artefacts, but on how a **release
board / governance process** can use them to make decisions.

For technical details, see:

- `docs/PULSE_decision_engine_v0_spec.md`
- `docs/PULSE_topology_v0_cli_demo.md`
- `docs/PULSE_topology_v0_mini_example_fairness_slo_epf.md`

---

## 1. Core vocabulary recap

### 1.1. release_state

From `decision_engine_v0.decision_engine_v0.release_state`:

- `PROD_OK` – all gates satisfied
- `STAGE_ONLY` – limited failures; suitable for staging / shadow only
- `BLOCK` – many gates failed; do not release
- `UNKNOWN` – no usable gate information

### 1.2. stability_type

From `decision_engine_v0.decision_engine_v0.stability_type`:

- `stable_good` – good decision in a locally flat region
  (no strong curvature or paradox atoms)
- `unstably_good` – good decision in a curved / paradox-rich region
  (“green, but the field is bent here”)
- `stable_bad` – bad decision in a flat region
  (blocked, but in a simple, stable way)
- `unstably_bad` – bad decision in a curved region
  (blocked + high structural tension)
- `boundary_simple` – boundary decision with simple topology
  (STAGE_ONLY, but topology is flat)
- `boundary` – boundary decision with non-trivial topology
  (STAGE_ONLY + curvature / paradox)
- `unknown` – not enough information to classify

Topology signals come from:

- `stability_summary.delta_bend_max` (from stability map)
- `paradox_summary.atom_count` / `severe_atom_count` (from paradox field)

---

## 2. Pattern A – PROD_OK + unstably_good

### 2.1. Situation

- `release_state = "PROD_OK"`
- `stability_type = "unstably_good"`

Example snippet:

    {
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

Interpretation:

- All gates are green – a classic system would simply say “ship it”.
- Topology v0 says:
  - there is at least one non-trivial **paradox atom** in `paradox_field_v0`,
  - and/or non-zero curvature (`delta_bend_max > 0`).

Governance view:

> “We are on a good outcome, but sitting on a structurally tense region of
> the field (e.g. fairness vs SLO vs EPF).”

### 2.2. Governance pattern

Possible policy:

1. **Allow automatic production release** (same as PROD_OK today).

2. **Require human sign-off when `stability_type = "unstably_good"`**, for example:

   - Attach the decision engine overlay to the release ticket.
   - Show:
     - the `paradox_summary` counts, and
     - the top few atoms from `paradox_field_v0`.
   - Require a short justification for why the paradox is acceptable **for now**
     (e.g. “this fairness–SLO tradeoff is expected under current load pattern”).

3. **Track “unstably_good” frequency over time**:

   - If a given paradox atom (e.g. `{q3_fairness_ok, q4_slo_ok}`) appears
     repeatedly, treat it as a structural issue:
     - e.g. escalate to model design / data / SLO owners.

Governance outcome:

- The system can still move fast (green is green), but:
  - **“unstably_good” is not invisible**.
  - It gains a special status: allowed, but under tension, and logged.

---

## 3. Pattern B – STAGE_ONLY + boundary / boundary_simple

### 3.1. Situation

`release_state = "STAGE_ONLY"` indicates a frontier region.

Two subtypes:

- `stability_type = "boundary_simple"`
  – frontier, but topology is flat / simple.
- `stability_type = "boundary"`
  – frontier, and topology is curved / paradox-rich.

Example (simple):

    {
      "release_state": "STAGE_ONLY",
      "stability_type": "boundary_simple"
    }

Example (non-trivial):

    {
      "release_state": "STAGE_ONLY",
      "stability_type": "boundary",
      "stability_summary": {
        "delta_bend_max": 1.0
      },
      "paradox_summary": {
        "atom_count": 2
      }
    }

### 3.2. Governance pattern

Common practice:

1. **Treat STAGE_ONLY as “shadow or limited rollout only”**

   - Allowed targets:
     - staging environments,
     - dark-launch,
     - small percentage canary.

2. Distinguish between:

   - **boundary_simple**
     - frontier, but simple.
     - typical rule: allow automatic stage/canary, log, no mandatory meeting.

   - **boundary**
     - frontier with non-trivial topology.
     - typical rule:
       - require release review before rollout beyond staging,
       - inspect paradox atoms and relevant metrics.

3. Optional: use paradox atoms as “why this is a boundary” explanation:

   - show the atom responsible for the boundary classification:
     - e.g. `{"gates": ["policy.p1_user_harm_ok", "perf.slo_latency_ok"]}`.

Governance outcome:

- The *type* of frontier becomes explicit:
  - “safe frontier” (`boundary_simple`) vs “tense frontier” (`boundary`).

---

## 4. Pattern C – BLOCK + stable_bad / unstably_bad

### 4.1. Situation

`release_state = "BLOCK"` – gating logic says: do not release.

Two stability flavours:

- `stable_bad` – bad decision in a flat region.
- `unstably_bad` – bad decision in a curved / paradox region.

Example (stable_bad):

    {
      "release_state": "BLOCK",
      "stability_type": "stable_bad",
      "status_summary": {
        "failed_gates": [
          "safety.s1_blocking"
        ]
      }
    }

Example (unstably_bad):

    {
      "release_state": "BLOCK",
      "stability_type": "unstably_bad",
      "status_summary": {
        "failed_gates": [
          "safety.s1_blocking"
        ]
      },
      "paradox_summary": {
        "atom_count": 4,
        "severe_atom_count": 2
      }
    }

### 4.2. Governance pattern

Baseline:

- In both cases, the **release is blocked**.
- The difference is where to focus investigation.

Recommended action split:

1. `stable_bad`:

   - the failure is locally simple:
     - e.g. one or two obvious gate violations,
     - no non-trivial paradox structure.
   - focus:
     - fix the failing gates,
     - no need to reorganise the decision field.

2. `unstably_bad`:

   - the failure occurs in a **paradox-rich** region:
     - multiple MUS atoms,
     - non-zero curvature.
   - focus:
     - treat this as a structural issue:
       - conflicting requirements,
       - misaligned SLOs,
       - inconsistent fairness/EPF constraints.
     - involve stakeholders beyond the immediate model owner:
       - policy, risk, infra.

Governance outcome:

- “BLOCK” remains, but:
  - `unstably_bad` signals that not only the model, but the **field itself**
    is problematic,
  - it calls for a holistic intervention, not just parameter tuning.

---

## 5. Pattern D – UNKNOWN

### 5.1. Situation

`release_state = "UNKNOWN"` or `stability_type = "unknown"`:

- missing / empty `status.json`,
- incompatible format,
- or the decision engine cannot make a meaningful classification.

### 5.2. Governance pattern

Treat UNKNOWN as a **telemetry / observability failure**:

- before release:
  - avoid automatic rollout,
  - require the PULSE pipeline to be fixed or overridden explicitly.
- after release:
  - treat it as an incident in governance / observability:
    - “why are we blind to the decision field?”

If the field is empty, that itself is information: **we cannot see** –  
and that is a risk.

---

## 6. Integration patterns

### 6.1. Dashboard integration

A simple dashboard widget can use:

- `release_state`
- `stability_type`
- `paradox_summary.atom_count`
- `stability_summary.delta_bend_max`

Example columns:

- release id
- release_state
- stability_type
- paradox atoms
- max delta_bend

Colouring:

- `unstably_good` – green background + amber border,
- `boundary` – amber,
- `unstably_bad` – red + marker for “structural tension”.

### 6.2. Policy hook

A simple policy sketch:

- if `release_state = "BLOCK"` → CI blocks,
- if `release_state = "PROD_OK"` and `stability_type = "stable_good"`  
  → automatic release,
- if `release_state = "PROD_OK"` and `stability_type = "unstably_good"`  
  → manual sign-off required,
- if `release_state = "STAGE_ONLY"`  
  → staging / canary only, never full prod without review.

Decision Engine v0 does not enforce this policy by itself – it provides a
**vocabulary** on top of which policy can be defined.

---

Topology v0 thus turns the classic “pass/fail” surface into a **decision field**:
we do not only see *what* happened in a release, but also *in what kind of
field structure* the decision was made – stable, curved, paradox-rich or
on a frontier region.
