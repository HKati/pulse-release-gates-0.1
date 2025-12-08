# PULSE quickstart safe-pack

This directory contains a tiny, self‑contained PULSE safe‑pack that shows
what a `status.json` looks like and how it maps to the Quality Ledger docs.

The goal is to give you a concrete, hackable starting point before you plug
PULSE into a real CI/CD pipeline.

## 1. What this example shows

This quickstart pack demonstrates:

- a minimal `status.json` for a single model / image,
- how refusal delta, external detectors and quality/SLO gates are represented,
- how a small helper script can print a human‑readable summary from `status.json`,
- how this ties back to the more detailed docs under `docs/`.

It is deliberately small and synthetic so that you can safely experiment with
the numbers and immediately see how the gates respond.

## 2. Files in this directory

- `status_quickstart.json`  
  A minimal status snapshot for one “release”. It contains:
  - refusal‑delta metrics and thresholds,
  - a couple of quality/SLO metrics (groundedness and latency),
  - the overall gate decisions.
- `external/llamaguard_summary.json`  
  Toy summary for a safety classifier (LlamaGuard).
- `external/promptfoo_summary.json`  
  Toy summary for prompt regression tests.
- `external/garak_summary.json`  
  Toy summary for Garak “new critical” findings.
- `external/azure_eval_summary.json`  
  Toy summary for an Azure indirect jailbreak evaluation.
- `run_quickstart.py`  
  Helper script that:
  - loads `status_quickstart.json`,
  - prints a short, human‑readable summary of the key gates,
  - points you to the Quality Ledger example.

(If some filenames differ slightly in your repo, treat this list as a guide
and adjust accordingly.)

## 3. How this relates to the docs

This quickstart pack is a concrete example of the concepts described in:

- `docs/status_json.md` – overall `status.json` structure,
- `docs/refusal_delta_gate.md` – refusal‑delta metrics and gates,
- `docs/external_detectors.md` – how external detector summaries are folded in,
- `docs/quality_ledger.md` – what the Quality Ledger is and how it is rendered,
- `docs/quality_ledger_example.md` – a worked example of a rendered ledger.

You can read those first and then inspect this pack, or start here and jump
to the docs when you want more detail.

## 4. How to run

From the repository root:

    python examples/quickstart_safe_pack/run_quickstart.py

You should see output similar to:

    PULSE quickstart – demo status.json

    Model:       my-llm-v3.1
    Profile:     PULSE_quickstart_profile_v0
    Decision:    PASS
    RDSI:        0.86 (CI: 0.78–0.92)

    Refusal delta: +0.06 on 120 pairs (threshold ≥ 0.05) -> refusal_delta_pass = True
    External detectors: external_all_pass = True (all configured detectors within their thresholds in this run)
    Groundedness (Q1):  89.0% (target ≥ 92.0%)
    Latency p95 (Q4):   480 ms (SLO ≤ 500 ms)

    Quality/SLO gate:   quality_slo_pass = True
    Overall gate:       overall_pass = True

    Done. For a fuller human‑readable view, see the Quality Ledger example in
    docs/quality_ledger_example.md.

## 5. Where to go from here

From here you can:

- tweak the numbers in `examples/quickstart_safe_pack/status_quickstart.json`
  to see how the printed summary changes,
- use the same structure as a template for your own CI‑produced `status.json`
  artefacts,
- cross‑reference the other docs to understand how PULSE derives its gates:
  - `docs/status_json.md`
  - `docs/refusal_delta_gate.md`
  - `docs/external_detectors.md`
  - `docs/quality_ledger.md`
  - `docs/quality_ledger_example.md`

The idea is that once you are comfortable with this tiny safe‑pack, you can:

- swap in your own model id / container image,
- connect real evaluation scripts that populate `status.json`,
- plug the generated `status.json` and Quality Ledger into your CI/CD pipeline
  and deployment workflow.

When that happens, the quickstart example remains useful as:

a regression test for the PULSE tooling itself, and

a minimal reference for new contributors and auditors who want to see
“the smallest possible pack” before diving into full‑scale runs.

::contentReference[oaicite:0]{index=0}

