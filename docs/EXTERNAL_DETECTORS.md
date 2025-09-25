---- START FILE ----
# External Detectors Policy (v0.1)

- **Allow-list:** only call detectors hosted on domains listed under `profiles/*` → `external_detectors.allow_domains`.
- **Timeouts:** enforce `timeout_ms_per_call` and `timeout_ms_overall`; on timeout/network error → deterministic `FAIL` (fail-closed).
- **Versioning:** record each detector as `name@sha256:...` inside `status.json`.
- **Audit:** include number/status of calls and total wall time in the Quality Ledger notes.
---- END FILE ----
