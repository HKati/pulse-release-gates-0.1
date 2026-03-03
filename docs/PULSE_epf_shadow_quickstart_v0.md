# PULSE EPF shadow quickstart (v0)

> Command-level quickstart for the optional EPF shadow comparison path.

This guide shows the **current practical EPF shadow flow** used in this
repository.

Important boundary:

- the deterministic baseline remains the source of truth for release gating
- EPF shadow is diagnostic and CI-neutral
- disagreement between baseline and EPF is something to inspect, not an
  automatic policy rewrite

For disagreement triage, see:

- `docs/PARADOX_RUNBOOK.md`

For the broader repository state, see:

- `docs/STATE_v0.md`
- `docs/DRIFT_OVERVIEW.md`

---

## 1. What this quickstart is for

Use this quickstart if you want to:

- run the current EPF shadow experiment locally,
- understand what the GitHub workflow is doing,
- inspect baseline vs EPF shadow differences,
- reproduce `epf_report.txt` / `epf_paradox_summary.json` style outputs.

This is **not** the main release-gating path.

---

## 2. Current workflow at a glance

The repository ships an optional workflow:

```text
.github/workflows/epf_experiment.yml
