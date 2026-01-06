# Documentation index

This page is the fuller index of repo documentation.
The README “Documentation map” is intentionally curated (entrypoint-first).

If you add/rename a doc under `docs/`, please update this index.

## Start here (entrypoints)
- Running PULSE in CI: [QUICKSTART_CORE_v0.md](QUICKSTART_CORE_v0.md)
- Understanding the source of truth (`status.json`): [status_json.md](status_json.md)
- When things fail (triage): [RUNBOOK.md](RUNBOOK.md)

---

## Orientation & contracts
- [STATE_v0.md](STATE_v0.md) — Current snapshot of PULSE v0 gates, signals, and tooling.
- [QUICKSTART_CORE_v0.md](QUICKSTART_CORE_v0.md) — Minimal steps to run the core pipeline.
- [RUNBOOK.md](RUNBOOK.md) — Operational runbook for triage and reruns.
- [STATUS_CONTRACT.md](STATUS_CONTRACT.md) — Contract for `status.json` shape and semantics.
- [GLOSSARY_v0.md](GLOSSARY_v0.md) — Canonical term definitions used across docs.

## Status, ledger & external signals
- [status_json.md](status_json.md) — How to read `status.json` (metrics, gates, consumers).
- [quality_ledger.md](quality_ledger.md) — Quality Ledger layout and purpose.
- [refusal_delta_gate.md](refusal_delta_gate.md) — Refusal-delta summary format + fail-closed semantics.
- [external_detectors.md](external_detectors.md) — Folding external detector summaries into status/ledger.

## Paradox field & edges
- [PULSE_paradox_field_v0_walkthrough.md](PULSE_paradox_field_v0_walkthrough.md) — How to read `paradox_field_v0`.
- [Pulse_paradox_edges_v0_status.md](Pulse_paradox_edges_v0_status.md) — Status/roadmap for `paradox_edges_v0.jsonl`.
- [paradox_edges_case_studies.md](paradox_edges_case_studies.md) — Case studies (fixture + non-fixture).
- [PARADOX_RUNBOOK.md](PARADOX_RUNBOOK.md) — What to do when EPF shadow disagrees with baseline.
- [Paradox diagram v0](paradox_diagram_v0.md) — how to generate and read the Mermaid topology view.
- [PULSE_paradox_core_v0.md](PULSE_paradox_core_v0.md) — Paradox Core v0 (deterministic core projection + markdown reviewer summary).

## EPF shadow & hazard diagnostics
- [PULSE_epf_shadow_quickstart_v0.md](PULSE_epf_shadow_quickstart_v0.md) — Command-level EPF shadow quickstart.
- [epf_relational_grail.md](epf_relational_grail.md) — Relational hazard overview + calibration/CLI examples.
- [epf_hazard_inspect.md](epf_hazard_inspect.md) — Inspect `epf_hazard_log.jsonl` from the CLI.

## Topology & field-first interpretation
- [PULSE_topology_overview_v0.md](PULSE_topology_overview_v0.md) — Topology layer overview (diagnostic overlay).
- [PULSE_decision_field_v0_overview.md](PULSE_decision_field_v0_overview.md) — Decision field v0 overview.
- [PULSE_decision_engine_v0.md](PULSE_decision_engine_v0.md) — Decision Engine v0 outputs and semantics.
- [FIELD_FIRST_INTERPRETATION.md](FIELD_FIRST_INTERPRETATION.md) — Field-first interpretation (question as projection).

## Examples & contributing
- [examples/README.md](examples/README.md) — Reproducible examples index.
- [examples/transitions_case_study_v0/README.md](examples/transitions_case_study_v0/README.md) — Transitions → paradox field/edges case study.
- [PR_SUMMARY_TOOLS.md](PR_SUMMARY_TOOLS.md) — PR summary tooling (canonical scripts).

- Contributing / workflow:
  - [../CONTRIBUTING.md](../CONTRIBUTING.md)
