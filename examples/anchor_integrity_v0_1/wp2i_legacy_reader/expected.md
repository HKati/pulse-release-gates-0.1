# Anchor Integrity — legacy v0 proxy view

> **Legacy operational proxy only — not claim-evidence coverage.**
> No claim support, measured cycle risk, response permission or release authority is established.

## Reader boundary

- Reader profile: `legacy-v0-proxy-boundary-v1`
- Accepted input format: `anchor_integrity_v0`; raw JSON is not rewritten.
- Input path (caller-supplied): `"examples/anchor_integrity_v0_1/wp2i_legacy_reader/legacy.json"`
- Result: **LEGACY_PROXY_RENDERED**
- Fresh evidence checks executed: `false`
- Authority effect: `none`
- Release-authority activation: `false`

## Reported operational proxy

- Reported value status: `reported`
- Reported gate-signal proxy: `1.0`
- This value is copied from the legacy numeric field, not recomputed from gates.
- It is not a count or proportion of evidence-supported claims.

## Evidence measurements

| Measurement | Status | Result |
|---|---|---|
| Claim-level anchor presence | not_run | null |
| Verified binding coverage | not_run | null |
| Verified support coverage | not_run | null |
| Typed dependency-cycle detection | not_run | null |
| Loop risk | not_run | null |
| Contradiction risk | not_run | null |
| Independent-anchor classification | not_run | null |

No measured result is inferred from a legacy risk label or Paradox source presence.
Legacy state, response/gate recommendations, rationale and free-text notes are not adopted or rendered as findings.
They remain in the original input JSON for historical inspection.
This reader issues no response recommendation and does not authorize a reply or a release.

## Unverified source metadata

- run_id: `"synthetic-legacy-reader-WP2I"`
- commit: `null`
- generator: `"scripts/anchor_integrity_adapter_v0.py"`
- source_date_epoch: `null`
- status_path: `"synthetic/status.json"`
- paradox_source_path: `"synthetic/source_v0.json"`

Metadata is displayed as bounded literal text, not authenticated identity.

## Evidence-bound diagnostics

Use `tools/build_anchor_integrity_diagnostic_v0_1.py` with an explicitly pinned selection and actual input files.
See `docs/ANCHOR_INTEGRITY_v0_1_WP2H_DIAGNOSTIC_INTEGRATION.md`.
This legacy view does not run that pipeline or substitute for its report.
