# PULSE quickstart safe-pack

This directory contains a tiny, synthetic PULSE quickstart pack. It shows a small, schema-valid demo `status.json` and a helper script that prints a short human-readable summary from that artifact. The goal is to give you a concrete, hackable starting point before wiring PULSE into a real CI/CD lane.

## 1. What this example shows

This quickstart pack demonstrates:

- a minimal demo `status.json` for a single model / image  
- the required public contract anchors (`version`, `created_utc`, `metrics.run_mode`, `gates`)  
- refusal-delta metrics and gate shape  
- quality / SLO metrics and per-gate outcomes  
- the separation between aggregate external pass/fail and actual evidence presence  
- how a small helper script can print a human-readable summary from `status_quickstart.json`  

It is deliberately small and synthetic. It is for inspection, learning, and tooling regression, not a release-grade evidence pack.

## 2. Files in this directory

- `status_quickstart.json`  
  A minimal demo status snapshot for one synthetic “release”. It contains:
  - contract anchors such as `version`, `created_utc`, and `metrics.run_mode`
  - refusal-delta metrics and thresholds
  - groundedness and latency metrics
  - current demo gate outcomes

- `run_quickstart.py`  
  Helper script that:
  - loads `status_quickstart.json`
  - prints a short, human-readable summary of the current demo artifact
  - points you to the Quality Ledger example

This quickstart currently does **not** bundle example external detector summary files under `external/`.

That is intentional in this demo:

- `gates.external_all_pass` describes the aggregate external result recorded in the demo artifact  
- `gates.external_summaries_present` tells you whether archived external summary evidence is actually present  

Do not treat those as the same signal.

## 3. How this relates to the docs

This quickstart pack is a small concrete entrypoint into:

- `docs/status_json.md` – public `status.json` contract and authority boundary  
- `docs/refusal_delta_gate.md` – refusal-delta mapping and gate semantics  
- `docs/EXTERNAL_DETECTORS.md` – repo-level external evidence policy  
- `docs/external_detector_summaries.md` – how archived external summaries are folded into `status.json`  
- `docs/quality_ledger.md` – Quality Ledger purpose and structure  
- `docs/quality_ledger_example.md` – worked ledger example  

You can read those first and then inspect this pack, or start here and jump to the docs when you want more detail.

## 4. How to run

From the repository root:

```bash
python examples/quickstart_safe_pack/run_quickstart.py
```

You should see output similar to:

```
PULSE quickstart – demo status.json

Model: my-llm-v3.1
Profile: PULSE_demo_profile_v0
Decision: STAGE-PASS
RDSI: 0.82 (CI: 0.74–0.89)

Refusal delta: +0.06 on 120 pairs (threshold ≥ 0.05) -> refusal_delta_pass = True
External detectors: external_all_pass = True (all configured detectors within their thresholds in this demo)
Groundedness (Q1): 89.0% (target ≥ 92.0%) -> Q1_groundedness_pass = False
Latency p95 (SLO): 480 ms (SLO ≤ 500 ms) -> SLO_latency_p95_pass = True

Done.
```

For a fuller human-readable view, see the Quality Ledger example in `docs/quality_ledger_example.md`.

Optional schema validation:

```bash
python tools/validate_status_schema.py \
  --schema schemas/status/status_v1.schema.json \
  --status examples/quickstart_safe_pack/status_quickstart.json
```

## 5. How to read this demo correctly

Read `gates.*` first.

In the public contract, `gates.*` is the normative decision surface. Descriptive top-level fields such as `decision` are useful for humans, but they should not override the gate layer.

This demo intentionally shows that:

- `external_all_pass = True` does **not** prove that external evidence files are present  
- `external_summaries_present = False` means no archived external summary files are bundled in this quickstart example  

That separation is important in real release-grade paths.

## 6. Where to go from here

From here you can:

- tweak the numbers in `examples/quickstart_safe_pack/status_quickstart.json` to see how the printed summary changes  
- use the same structure as a template for your own CI-produced `status.json` artifacts  
- cross-reference the other docs to understand how PULSE derives and enforces its gates  

Once you are comfortable with this tiny pack, you can move on to:

- your own model id / container image  
- real evaluation scripts that populate `status.json`  
- CI wiring that validates, enforces, and renders the final artifact set  

The quickstart remains useful as:

- a regression target for the PULSE tooling itself  
- a minimal reference for new contributors and auditors who want the smallest possible pack before diving into full-scale runs  
