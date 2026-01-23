# PR Review Checklist (PULSE)

Use this checklist for any change touching gates, metrics, policies, or reports.

## A) Gate semantics
- [ ] Are you changing the meaning of an existing gate ID?
  - If yes: STOP. Create a new gate ID and deprecate the old one.
- [ ] Did you update `pulse_gate_registry_v0.yml` for any new gate ID?
- [ ] Is the gate clearly categorized (safety / quality / slo / diagnostic)?

## B) Contracts (status / ledger / trace)
- [ ] Are you adding/changing fields in status/ledger/trace?
  - If yes: update schema/contract docs and bump schema version if meaning changes.
- [ ] Are outputs still deterministic and reproducible under fixed runner + seed?

## C) Policy
- [ ] Are required gate sets explicit (PR / stage / prod)?
- [ ] If a gate is capability-dependent, is that encoded in policy (not ad-hoc in code)?

## D) Fail-closed behavior
- [ ] If required evidence is missing, does the system fail closed (not pass)?
- [ ] Are error messages actionable (which gate, which missing artifact, which key)?

## E) Diagnostics
- [ ] Is the change purely diagnostic (shadow)? Ensure it cannot flip CI status.
- [ ] If promoting diagnostic → normative, is there a deliberate versioned decision record (ADR) and a migration plan?

## F) Evidence and auditability
- [ ] Can we trace every FAIL to concrete evidence (metrics/margins/artifacts)?
- [ ] Are overrides logged with reason and scope?
