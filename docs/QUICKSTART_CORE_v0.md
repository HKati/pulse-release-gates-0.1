# PULSE Core Quickstart (v0)

> Minimal path to the canonical Core lane.  
> This page documents the real Core adoption path:  
> `run -> status.json -> required gates -> Quality Ledger`

---

## 1. Who this is for

Use this path if you want to:

- start with one deterministic, fail-closed PULSE lane
- keep the first adoption narrow
- ignore optional overlays on the first pass

If you are here for EPF, paradox, G-field, GPT-external, or research layers, stop here first and come back to those later.

---

## 2. What “Core” means in practice

Core is the smallest release-meaningful PULSE lane.

For Core decisions, the authoritative inputs are:

1. `status["gates"]`
2. the materialized `core_required` gate set from `pulse_gate_policy_v0.yml`
3. `PULSE_safe_pack_v0/tools/check_gates.py`

The Quality Ledger is a human-readable view over the same artefact.  
It is useful, but it is not the release authority.

Important:

- `metrics.run_mode` must be `core`
- missing required gates fail closed
- optional / shadow layers do not change Core by default

---

## 3. Profile vs policy: do not mix them up

`PULSE_safe_pack_v0/profiles/pulse_policy_core.yaml` is the human-readable Core profile.  
It explains the intent of Core and can carry per-gate config and CI-neutral refusal-delta policy.

But the canonical CI lane should not hardcode its required gates from prose or from hand-copied YAML in this page.

For the actual Core lane:

- the required gate set is materialized from `pulse_gate_policy_v0.yml`
- the workflow enforces that materialized `core_required` set
- this page follows the workflow, not the other way around

That distinction matters.  
The profile is explanatory.  
The policy + workflow + final `status.json` drive the actual lane.

---

## 4. Choose the right adoption shape

### 4.1 Recommended: vendor the canonical Core lane

If you want the real reference lane, do not copy only `PULSE_safe_pack_v0/`.

The current Core lane also relies on repo-root governance files, helper tools, and baseline fixtures.  
The narrow but truthful adoption set is:

```text
.github/workflows/pulse_core_ci.yml
PULSE_safe_pack_v0/
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
requirements.txt
pytest.ini
schemas/status/status_v1.schema.json
tools/check_yaml_unique_keys.py
tools/check_gate_registry_sync.py
tools/policy_to_require_args.py
tools/validate_status_schema.py
tests/test_core_baseline_v0.py
tests/tools/generate_core_baseline_v0.py
tests/fixtures/core_baseline_v0/
```

The safest option is to vendor this as a subtree/submodule or copy this slice as a unit.

### 4.2 Acceptable only for local exploration

If you only want a local smoke run, copying just `PULSE_safe_pack_v0/` is fine.

But that is **not** the same as the canonical Core CI lane.  
It skips the policy guardrails, registry sync check, and baseline drift control that make the lane trustworthy.

---

## 5. What the canonical Core workflow does

The canonical workflow lives at:

```text
.github/workflows/pulse_core_ci.yml
```

Treat that file as the source for the actual CI path.

At a high level, the Core workflow should:

1. check out read-only
2. set up the pinned Python version used by the reference lane
3. install the minimal Python dependencies and pytest
4. run the Core baseline drift check
5. run the YAML duplicate-key guard on the policy and gate registry
6. run the safe-pack explicitly in `core` mode
7. verify that the produced `status.json` says `metrics.run_mode = "core"`
8. check gate registry coverage against the produced `status.json`
9. materialize the required gates from `pulse_gate_policy_v0.yml` using `core_required`
10. enforce those gates fail-closed with `PULSE_safe_pack_v0/tools/check_gates.py`
11. export optional JUnit and SARIF reports
12. upload the resulting artefacts

Opinionated rule:  
do **not** hand-copy the gate list into the workflow.  
Always materialize it from policy so the lane stays aligned as policy evolves.

---

## 6. Minimal local reproduction of the canonical logic

From the repository root, on a bash-like shell:

```bash
python -m pip install -r requirements.txt pytest

python -m pytest -q tests/test_core_baseline_v0.py

python tools/check_yaml_unique_keys.py \
  pulse_gate_registry_v0.yml \
  pulse_gate_policy_v0.yml

python PULSE_safe_pack_v0/tools/run_all.py --mode core

python - <<'PY'
import json
from pathlib import Path

status = json.loads(
    Path("PULSE_safe_pack_v0/artifacts/status.json").read_text(encoding="utf-8")
)
run_mode = ((status.get("metrics") or {}).get("run_mode"))
if run_mode != "core":
    raise SystemExit(f"Expected metrics.run_mode='core', got {run_mode!r}")
print(f"Verified metrics.run_mode={run_mode}")
PY

python tools/check_gate_registry_sync.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --registry pulse_gate_registry_v0.yml \
  --emit-stubs

mapfile -t REQ < <(
  python tools/policy_to_require_args.py \
    --policy pulse_gate_policy_v0.yml \
    --set core_required \
    --format newline
)

python PULSE_safe_pack_v0/tools/check_gates.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --require "${REQ[@]}"
```

Optional reporting exports:

```bash
python PULSE_safe_pack_v0/tools/status_to_junit.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --out reports/junit.xml

python PULSE_safe_pack_v0/tools/status_to_sarif.py \
  --status PULSE_safe_pack_v0/artifacts/status.json \
  --out reports/sarif.json
```

---

## 7. How to read the outcome

Read the Core result in this order:

1. `PULSE_safe_pack_v0/artifacts/status.json`
2. the materialized `core_required` gate set
3. the exit result of `PULSE_safe_pack_v0/tools/check_gates.py`
4. `PULSE_safe_pack_v0/artifacts/report_card.html`

Reading rule:

- `gates.*` is normative
- the active required gate set determines what blocks the lane
- the Quality Ledger is descriptive
- optional/shadow layers remain non-normative unless explicitly promoted

---

## 8. What Core does not include

Core does not require, by default:

- EPF shadow or hazard overlays
- paradox / topology overlays
- G-field / GPT-external / snapshot overlays
- Parameter Golf companion artefacts
- release-grade external evidence gates

Those can be layered on later through explicit policy promotion.  
They should not bleed into the Core path by documentation drift.

---

## 9. Next docs

After this page, read:

- `docs/STATUS_CONTRACT.md`
- `docs/status_json.md`
- `docs/RUNBOOK.md`
- `docs/OPTIONAL_LAYERS.md`

If this page and the committed workflow ever disagree, treat the workflow and the produced artefacts as authoritative, then update this page in the same PR.
