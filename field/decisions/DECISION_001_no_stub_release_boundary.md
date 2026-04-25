# DECISION 001 — No-Stub Release Boundary

## Decision

PULSE may run in scaffold, smoke, demo, or core modes for field exploration and baseline validation.

However, any release-grade or production-authoritative lane must fail closed if the run is based on stubbed gates, scaffold diagnostics, all-true smoke profiles, or missing detector materialization evidence.

## Rule

A PULSE status artifact cannot be treated as release-grade evidence if any of the following are true:

- `diagnostics.gates_stubbed == true`
- `diagnostics.scaffold == true`
- `diagnostics.stub_profile` indicates an all-true or smoke profile
- required release evidence is missing
- `gates.detectors_materialized_ok` is missing or not literal `true`
- external detector evidence is required but absent, malformed, or not all-pass

## Rationale

PULSE separates diagnostic observation from release authority.

A scaffold/core pass may prove that the PULSE machinery works. It does not prove that real safety evidence has been materialized.

This distinction prevents dashboards, ledgers, smoke tests, and generated summaries from being confused with actual release authority.

## Non-goals

This decision does not remove scaffold, demo, field, or shadow modes.

Those modes remain important for development and field exploration. The rule only prevents them from being promoted silently into release-grade authority.

## Testable invariant

If a status artifact claims or is checked as release-grade, then stubbed/scaffold/all-true-smoke diagnostics must cause a fail-closed result.
