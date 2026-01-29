# External detectors

> **Implementation guide (schemas, examples, integration patterns):**
> [`docs/external_detector_summaries.md`](external_detector_summaries.md)

PULSE supports an external detector layer that can enrich run artefacts (e.g. `status.json`)
with additional safety and quality signals (for example: external alignment scanners,
safety classifiers, jailbreak probes).

The PULSE safe-pack does **not** hard-wire any single detector implementation. Instead, it defines
an interface and expects integrations to:

- run external tools (e.g., model scanners, policy checkers),
- write their findings into a structured summary (JSON / JSONL),
- augment the PULSE status artefacts with those findings (merge/attach + optional composite gates),
- respect the policy encoded in the active profile (thresholds, risk limits, and whether external results
  are gating or advisory).

## Gating vs advisory modes

There are two conceptual ways to use external detectors:

1. **Gating mode (often the default for “ship/no-ship”)**  
   External summaries are combined into a composite gate such as `external_all_pass`.
   The CI workflow enforces that gate as *required*, so any failing external check can block the release
   (fail-closed).

2. **Advisory / shadow mode**  
   External findings are ingested for reporting and governance, but are **not** wired into any required
   gate. In this setup, external detectors are CI-neutral and do not change the release decision.

Downstream users can choose either mode by adjusting their required gate set and/or profile policy.

## External Detectors Policy (v0.1)

This policy captures recommended hardening when external detectors are enabled.

- **Allow-list:** only call detectors hosted on domains listed under `profiles/*` →
  `external_detectors.allow_domains`.
- **Timeouts:** enforce `timeout_ms_per_call` and `timeout_ms_overall`; on timeout/network error →
  deterministic `FAIL` (fail-closed).
- **Versioning:** record each detector as `name@sha256:...` inside `status.json`.
- **Audit:** include number/status of calls and total wall time in the Quality Ledger notes.

> Note: if your integration does **not** “call” remote detectors (i.e., you only ingest offline summaries),
> the allow-list/timeout points still apply to the workflow step that produces those summaries.

## Determinism note (important)

To preserve deterministic release semantics, treat external detector outputs as **immutable artefacts**:
pin tool versions, archive outputs, and have PULSE consume the archived summaries.
If a required external artefact is missing, it must never be silently interpreted as `PASS`.

## References

- Safe-pack overview (external detectors): `PULSE_safe_pack_v0/docs/EXTERNAL_DETECTORS.md`
- Implementation guide: `docs/external_detector_summaries.md`
