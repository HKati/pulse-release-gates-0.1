# External detectors

> **Implementation guide (repo-level):**  
> [`docs/external_detector_summaries.md`](../../docs/external_detector_summaries.md)  
> (schemas, examples, integration patterns)

PULSE supports an external detector layer that can enrich the status with additional safety and
quality signals (for example: external alignment or safety scanners).

The PULSE safe-pack itself does **not** hard-wire any specific external detector implementation.
Instead, it defines an interface and expects integrations to:

- run external tools (e.g. model scanners, policy checkers),
- write their findings into an extended status structure (typically via JSON/JSONL summaries),
- respect the policy encoded in the profile (thresholds, risk limits, and whether external results
  are gating or advisory).


## Gating vs advisory modes

There are two conceptual ways to use external detectors:

1. **Gating mode (this repository’s default)**  
   In the main pipeline, external summaries are combined into a composite gate such as
   `external_all_pass`. The CI workflow (`.github/workflows/pulse_ci.yml`) includes this gate in the
   enforced gate list, and `tools/augment_status.py` computes the flag from external metrics and
   thresholds.

   When external detectors are enabled and any metric crosses the configured threshold,
   `external_all_pass` becomes `FAIL`, and CI will **fail** as part of deterministic gating.
   In other words, in this configuration external detectors *do* contribute to pass/fail outcomes.

2. **Advisory / shadow mode**  
   The same interface can be used in a purely advisory way (for example in shadow workflows or
   research runs), where external findings are logged for analysis, reporting and governance but are
   **not** wired into any required gate. In that setup, external detectors are CI-neutral and do not
   change the release decision.

This repository ships the **gating** configuration by default for the main PULSE CI, while still
allowing downstream users to wire external detectors in advisory-only mode in their own workflows or
profiles if desired.


## Repo-level documentation

For the full, up-to-date top-level documentation in this repository:

- Policy (gating vs advisory, defaults):  
  [`docs/EXTERNAL_DETECTORS.md`](../../docs/EXTERNAL_DETECTORS.md)

- External detector summaries (schemas, examples, integration patterns):  
  [`docs/external_detector_summaries.md`](../../docs/external_detector_summaries.md)


## Archival note

If you archive this pack (e.g. via Zenodo/DOI), consider including this file plus the two
repo-level documents above so that external detector behavior remains transparent and reproducible
for downstream users.
