## The PULSE status artefact (`status.json`)

PULSE safe-packs produce a single machine-readable status artefact for each CI run:

- `artifacts/status.json`

This file is the central place where all gate-relevant information is collected. It is:

- written by PULSE tools during the safe-pack run,
- consumed by other tools (e.g. `augment_status.py`, `check_gates.py`),
- and used as input for human-readable reports such as the Quality Ledger.

A single `status.json` corresponds to exactly one release candidate (model or service
configuration) and one concrete CI run.

---

### High-level structure

At a high level, `status.json` is a JSON object with three main sections:

- release-level metadata (optional, but recommended),
- `metrics`: numeric and boolean signals produced by tests and detectors,
- `gates`: boolean decisions derived from metrics and policies.

A typical layout looks like:

```json
{
  "release_id": "model-x-2026-01-15",
  "model_version": "v3.1.0",
  "metrics": {
    "...": "..."
  },
  "gates": {
    "...": true
  },

  "refusal_delta_pass": true,
  "external_all_pass": false

  /* possibly other top-level mirrors or summary fields */
}

The exact set of fields depends on the safe-pack configuration and the detectors that
are enabled, but the pattern is consistent:

metrics describe what was measured,

gates describe what decision was taken.

Metrics

metrics is a flat object that aggregates numerical and boolean signals from the
safe-pack. Examples include:

refusal-related metrics:

metrics.refusal_delta_n – number of evaluated refusal pairs

metrics.refusal_delta – estimated refusal delta

metrics.refusal_delta_ci_low / metrics.refusal_delta_ci_high

metrics.refusal_policy – the policy name used for evaluation

metrics.refusal_pass_min / metrics.refusal_pass_strict

external detector metrics (populated by augment_status.py):

metrics.llamaguard_violation_rate

metrics.promptfoo_fail_rate

metrics.garak_issue_rate

metrics.azure_risk_rate

metrics.promptguard_attack_detect_rate

Each external metric entry is also recorded in external.metrics with its threshold and
per-detector pass flag. The copy in metrics provides a simple, flat view that is
easy to consume from CI, dashboards and post-processing scripts.

Safe-packs may add additional metrics as needed (SLOs, invariants, business-specific
checks, etc.). All of them share the same purpose: they record what the tests saw.

Gates

gates is a map of boolean decisions. Each gate typically corresponds to one safety
or quality contract that must hold for the release to proceed. Examples:

gates.refusal_delta_pass – derived from the refusal delta summary

gates.external_all_pass – aggregate decision over all external detectors

other gates defined by the safe-pack (e.g. invariants, SLOs)

In addition to the gates object, some gates are also mirrored at the top level of the
status artefact for convenience:

status["refusal_delta_pass"]

status["external_all_pass"]

These mirrors make it easy to query individual gates with simple CLI tools such as
jq without digging into nested structures.

Downstream tooling may also compute an overall decision such as:

overall_pass – combined result of all required gates

depending on the governance policy of the project.

External detector section: external

augment_status.py maintains a dedicated external section that describes the
per-detector metrics and the aggregate external gate:

"external": {
  "metrics": [
    {
      "name": "promptguard_attack_detect_rate",
      "value": 0.20,
      "threshold": 0.10,
      "pass": false
    }
  ],
  "all_pass": false
}

Key points:

external.metrics – list of objects, one per external detector:

name – metric name,

value – measured rate,

threshold – configured maximum allowed rate,

pass – detector-level decision (value <= threshold).

external.all_pass – aggregate decision across all external detectors,
controlled by the external_overall_policy setting in thresholds.json.

The value of external.all_pass is mirrored into:

gates["external_all_pass"]

status["external_all_pass"]

so CI and other tools can rely on a single boolean flag.

Relationship to other artefacts

status.json is designed to be consumed by multiple tools:

augment_status.py

takes a baseline status.json,

enriches it with refusal, external and other derived metrics,

ensures gate mirrors (refusal_delta_pass, external_all_pass) are present.

check_gates.py (or equivalent gate-checking tool)

reads the extended status.json,

enforces required gates (e.g. exits non-zero if a mandatory gate is false),

may compute an overall_pass flag for convenience.

Quality Ledger / human-readable reports

use metrics and gates to render tables and explanations,

provide the forensic trail for audits and incident response.

Because the status artefact is a simple JSON file, it can also be archived, versioned
and diffed like any other build artefact. This makes it a natural anchor for
forensic-style questions such as:

“What exactly did we test for release X?”

“How did our refusal metrics change between release N and N+1?”

“Which external detectors blocked this deployment?”




