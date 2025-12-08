# Quickstart: PULSE safe-pack in 5 minutes

This quickstart is for people who want to *see* what a PULSE safe-pack
produces without wiring it into a full CI pipeline yet.

It uses two tiny, self-contained examples:

- a sample `status.json` snapshot:
  `examples/quickstart_safe_pack/status_quickstart.json`
- a human-readable walkthrough of the same data:
  `docs/quality_ledger_example.md`

Together they show how PULSE turns raw metrics into a deterministic
release decision plus a readable Quality Ledger.

---

## 1. Inspect the sample `status.json`

The quickstart snapshot lives at:

```text
examples/quickstart_safe_pack/status_quickstart.json
```

It is intentionally small and only contains the fields that are used in
the Quality Ledger example:

- run metadata (model id, image, CI run id),
- refusal-delta metrics and thresholds,
- a few "Q-style" quality metrics (groundedness, latency, etc.),
- external detector outputs (LlamaGuard, Promptfoo, Garak, Azure eval),
- gate booleans: `refusal_delta_pass`, `quality_slo_pass`,
  `external_all_pass`, `overall_pass`.

You can pretty-print it with any JSON tool, for example:

```bash
jq . examples/quickstart_safe_pack/status_quickstart.json
```

or, from Python:

```python
import json
from pathlib import Path

data = json.loads(Path("examples/quickstart_safe_pack/status_quickstart.json").read_text())
print(data["decision"], data["gates"])
```

The important part is not the exact numbers, but the shape:

- metrics under `metrics.*`,
- thresholds under `thresholds.*`,
- final decisions under `gates.*`.

That is the contract that the Quality Ledger renderer consumes.

---

## 2. Map it to the Quality Ledger

Once you have seen the JSON, open:

```text
docs/quality_ledger_example.md
```

That document walks through the *same* information, but in the format a
human reviewer would see in the HTML Quality Ledger:

- a header with model, profile, commit and RDSI,
- a decision strip that summarises PASS / FAIL,
- tables for refusal stability, quality/SLOs and external detectors,
- short natural-language explanations for each gate.

You can treat the example `status_quickstart.json` as the "machine view"
and the Quality Ledger example as the "human view" of the same release.

---

## 3. How to use this in practice

Recommended flow for new users:

1. **Skim the JSON**  
   Get a feeling for how refusal, quality and external detector metrics
   are encoded, and how the gate booleans are wired.

2. **Read the Quality Ledger walkthrough**  
   See how those metrics turn into a single PASS decision, and how a
   reviewer can reconstruct *why* the release was allowed.

3. **Compare with your own stack**  
   Ask: which of your existing CI metrics could fit into this shape?
   Where would you plug in your own external detectors or SLOs?

Later, when you wire PULSE into a real CI job, the goal is that your
own `PULSE_safe_pack_v0/artifacts/status.json` has the same structure as
this quickstart snapshot — just with real metrics and thresholds.

---

## 4. Next steps

If you want to go deeper:

- See `docs/status_json.md` for a more formal description of the
  `status.json` schema.
- See `docs/refusal_delta_gate.md` and `docs/external_detectors.md`
  for details on the individual gates.
- Browse the tests under `tests/test_augment_status_*.py` to see how
  the summary and gating logic is exercised.

From here you can either:

- adapt the quickstart JSON to match your own model and thresholds, or
- run the full safe-pack pipeline and compare its `status.json` to the
  quickstart snapshot.

The quickstart is deliberately small so you can copy, tweak and extend
it without having to understand every corner of the PULSE codebase.
