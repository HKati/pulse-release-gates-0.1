# Decision Field v0 – 5-minute tour

This is a short, hands-on tour of the PULSE Decision Field v0 layer.

In **three commands** and **three JSON artefacts** you will see:

1. `status.json` – baseline gates and metrics,
2. `paradox_field_v0.json` – paradox atoms over gates,
3. `decision_engine_v0.json` – a field-aware decision overlay with
   `release_state` and `stability_type`.

For a deeper dive, see:

- `docs/PULSE_decision_field_v0_overview.md`
- `docs/PULSE_topology_v0_cli_demo.md`
- `docs/PULSE_decision_engine_v0_unstably_good_example.md`
- `docs/PULSE_decision_engine_v0_unstably_bad_example.md`

---

## 0. Prerequisites

From the repo root:

- Python 3.11 (or compatible),
- dependencies installed:

    pip install -r requirements.txt

All commands below assume you run them from the repository root.

---

## 1. Step 1 – Run the PULSE safe pack (build `status.json`)

First, run the baseline PULSE safe pack. This evaluates gates and metrics
for a single release candidate.

Command:

    python PULSE_safe_pack_v0/tools/run_all.py

This will produce (among other artefacts):

- `PULSE_safe_pack_v0/artifacts/status.json`

A simplified example of what `status.json` might contain:

    {
      "status_v0": {
        "version": "PULSE_status_v0",
        "generated_at_utc": "2025-01-10T12:30:00Z",
        "gates": {
          "quality.q3_fairness_ok": true,
          "slo.q4_slo_ok": true,
          "safety.s1_blocking": false
        },
        "metrics": {
          "rdsi": 0.94
        }
      }
    }

Interpretation:

- gates:
  - `quality.q3_fairness_ok = true`
  - `slo.q4_slo_ok = true`
  - `safety.s1_blocking = false` (i.e. no blocking safety issue)
- metrics:
  - `rdsi = 0.94` → high stability in the traditional sense.

At this point we know:

> “This release looks green according to conventional PULSE gating.”

But we do **not yet** know anything about paradoxes or field stability.

---

## 2. Step 2 – Build the paradox field (`paradox_field_v0.json`)

Next, we mine **paradox atoms** from one or more status artefacts.

Command:

    python PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py \
      --status-dir PULSE_safe_pack_v0/artifacts \
      --output PULSE_safe_pack_v0/artifacts/paradox_field_v0.json \
      --max-atom-size 4

This writes:

- `PULSE_safe_pack_v0/artifacts/paradox_field_v0.json`

A minimal example might look like:

    {
      "paradox_field_v0": {
        "version": "PULSE_paradox_field_v0",
        "generated_at_utc": "2025-01-10T12:32:00Z",
        "source": {
          "status_dir": "PULSE_safe_pack_v0/artifacts",
          "run_count": 1
        },
        "atoms": [
          {
            "atom_id": "atom_0003",
            "gates": [
              "quality.q3_fairness_ok",
              "slo.q4_slo_ok"
            ],
            "minimal": true,
            "severity": 0.9
          }
        ]
      }
    }

Interpretation:

- `atoms[]` lists **paradox atoms**:
  - here, one atom involving:
    - `quality.q3_fairness_ok`
    - `slo.q4_slo_ok`
  - `minimal = true` → it is a minimal unsatisfiable set (MUS) in some
    region of the field.
  - `severity = 0.9` → this tradeoff is strong / recurrent.

This tells us:

> there is a **structural tension** between fairness and SLO quality,
> even if the particular run we saw in `status.json` passes both.

---

## 3. Step 3 – Build the decision engine overlay (`decision_engine_v0.json`)

Finally, we combine the baseline status and paradox field into a compact
Decision Engine v0 overlay.

Here we use only `status.json` and `paradox_field_v0.json` to keep the
tour to three commands and three JSON artefacts. A stability map can be
added later (see `PULSE_topology_v0_cli_demo.md`).

Command:


python PULSE_safe_pack_v0/tools/PULSE_safe_pack_v0/tools/pulse_paradox_atoms_v0.py \
  --status-dir PULSE_safe_pack_v0/artifacts \
  --output PULSE_safe_pack_v0/artifacts/paradox_field_v0.json \
  --max-atom-size 4

    

This writes:

- `PULSE_safe_pack_v0/artifacts/decision_engine_v0.json`

A minimal example:

    {
      "decision_engine_v0": {
        "version": "PULSE_decision_engine_v0",
        "generated_at_utc": "2025-01-10T12:34:56Z",
        "inputs": {
          "status_path": "PULSE_safe_pack_v0/artifacts/status.json",
          "stability_map_path": null,
          "paradox_field_path": "PULSE_safe_pack_v0/artifacts/paradox_field_v0.json"
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
        "stability_summary": null,
        "paradox_summary": {
          "atom_count": 3,
          "severe_atom_count": 1
        }
      }
    }

Interpretation:

- `release_state = "PROD_OK"`
  - all required gates pass → the release is green at the gating level.
- `stability_type = "unstably_good"`
  - the paradox overlay indicates **non-trivial tension**:
    - at least one severe paradox atom is present.

Intuition:

> The release is good (PROD_OK), but it lives in a **structurally tense**
> region of the decision field. Small changes in data or thresholds may
> flip the outcome.

In other words:

- the decision is allowed,
- but governance and tooling are informed that this is a **“green but
  unstable”** region, not a simple flat green.

---

## 4. Where to go next

In five minutes, you have seen:

1. **`status.json`**  
   → gates + metrics for a baseline release.

2. **`paradox_field_v0.json`**  
   → paradox atoms exposing structural tensions.

3. **`decision_engine_v0.json`**  
   → a field-aware decision with `release_state` and `stability_type`.

From here you can:

- add **stability maps** for curvature:
  - see `docs/PULSE_topology_v0_cli_demo.md`,
- explore **governance patterns** for different stability types:
  - see `docs/PULSE_topology_v0_governance_patterns.md`,
- study the **Decision Field v0 architecture**:
  - see `docs/PULSE_decision_field_v0_overview.md`,
- and inspect more detailed examples:
  - `docs/PULSE_decision_engine_v0_unstably_good_example.md`
  - `docs/PULSE_decision_engine_v0_unstably_bad_example.md`
  - `docs/PULSE_decision_trace_v0_mini_example.md`
  - `docs/PULSE_demo_v1_paradox_stability_showcase.md`

This tour is the **smallest possible path** from:

> “I ran the PULSE safe pack”

to:

> “I have a **Decision Field v0** view with paradox-aware, field-level
> stability information for my release.”
