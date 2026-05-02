# Release Authority Boundary v1

## Purpose

This document freezes the PULSE release-authority boundary for the PULSE-REF hardening track.

PULSE-REF converts the existing PULSE artifact trail and core release-decision mechanics into an externally verifiable release-grade reference path.

The goal is not to create a second decision engine. The goal is to preserve a narrow, deterministic, fail-closed release-decision path while strengthening the surrounding audit, provenance, publication, and verification surfaces.

## Normative release-decision path

The normative release-decision path is intentionally narrow:

recorded evidence -> status.json -> declared gate policy -> materialized required gate set -> strict gate checking.

The normative release decision is produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

A release decision is valid only when the applicable required gates are present, materialized, policy-bound, and passing under the declared gate semantics.

## PASS semantics

PULSE uses strict fail-closed PASS semantics.

A required gate passes only when its value is literal boolean `true`.

The following values do not pass:

- `false`
- `null`
- missing key
- string values such as `"true"`
- numeric values such as `1`
- malformed evidence
- stale evidence
- unsigned evidence where signer requirements apply
- advisory evidence not promoted by declared policy
- non-materialized evidence in release-grade paths

## Required gates

Required gates are policy-defined and release-blocking.

Required gate sets must be materialized from declared policy. They must not be manually reinterpreted by dashboards, ledgers, manifests, summaries, or publication surfaces.

For PULSE-REF, release-grade paths may use an effective required set such as:

required + release_required

The exact effective set must be recorded and reconstructible from policy and run artifacts.

## Advisory gates

Advisory gates may inform review.

Advisory gates do not authorize or block release unless explicitly promoted by declared policy.

Advisory evidence cannot silently become release authority.

## Diagnostic and preservation surfaces

The following surfaces are diagnostic, explanatory, audit, or preservation surfaces by default:

- Quality Ledger
- dashboards
- rendered Pages
- summaries
- review views
- release-authority manifests
- audit bundles
- publication surfaces
- benchmark summaries
- verification reports

These surfaces may preserve, explain, reproduce, or reconstruct the release decision.

They do not authorize, block, override, reinterpret, or create a second release-decision path.

## Release-authority manifests

Release-authority manifests preserve the decision trace.

They may record:

- run identifier
- git SHA
- status artifact hash
- gate policy hash
- required gate set
- CI outcome
- evidence artifact references
- audit-bundle references
- provenance or attestation references

They do not generate the release decision.

## Audit bundles

Audit bundles preserve the evidence and decision trace.

They may contain:

- status.json
- gate policy snapshot
- materialized required gate set
- release-authority manifest
- detector summaries
- JUnit / SARIF reports
- benchmark summaries
- provenance / attestation artifacts
- publication snapshot manifest

They do not generate the release decision.

## Quality Ledger

The Quality Ledger is a human-readable audit surface over the release state.

The Quality Ledger must not become a separate decision engine.

If a Ledger view and the normative artifacts disagree, the declared-policy gate-enforcement path and CI outcome are authoritative.

## Publication surfaces

Publication surfaces exist for visibility and review.

Publication surfaces must remain non-normative.

PULSE-REF publication hardening should ensure that public surfaces are atomically tied to the same run, but publication consistency does not create an independent release decision.

## Non-interference rule

Diagnostic, audit, and publication surfaces must satisfy non-interference:

They may preserve, explain, reproduce, and audit the release decision.

They must not change the release decision.

They must not introduce a second path that can authorize, block, override, or reinterpret release.

## Evidence presence rule

Release-grade paths must not infer PASS from missing evidence.

In release-grade paths:

- required evidence must be present
- required evidence must be materialized
- required evidence must be valid under schema
- external evidence must satisfy signer / identity requirements where applicable
- missing required evidence must produce explicit missing / fail state
- implicit PASS fallback is not allowed

## External evidence rule

External detector, evaluation, and review summaries may enter the release decision only after validation.

Release-grade external evidence should be:

- canonical
- schema-valid
- metric-key stable
- threshold-bound
- tool-identity bound
- versioned
- subject- or dataset-digest bound
- signer- or identity-verified where applicable

Malformed, stale, unsigned, unversioned, or signer-mismatched release-grade evidence must fail closed.

## Agent-produced work evidence

Agent-produced work evidence may include:

- plans
- tool traces
- intermediate outputs
- code changes
- review notes
- self-checks
- detector outputs
- CI evidence

These artifacts may be useful for diagnosis and review.

They do not become release authority unless explicitly promoted by declared policy and materialized as required gates.

## Prohibited authority expansions

The following are prohibited in PULSE-REF:

- treating a dashboard as release authority
- treating a Quality Ledger view as release authority
- treating a release-authority manifest as a decision engine
- treating an audit bundle as a decision engine
- treating advisory evidence as release-blocking without policy promotion
- treating missing evidence as PASS
- treating a publication snapshot as release authorization
- treating agent-produced diagnostic work as release authority without declared policy promotion
- adding a parallel decision path outside the declared-policy gate-enforcement path

## PULSE-REF hardening implications

The release-authority boundary implies the following PULSE-REF hardening targets:

- non-stubbed release-grade reference run
- explicit evidence presence checks
- zero implicit PASS fallback in release-grade paths
- external evidence schema and signer requirements
- provenance / attestation for release artifacts
- atomic publication snapshots
- benchmark fixtures for evidence failure modes
- external verification pack

Each hardening target strengthens the release-decision trace without replacing the normative decision path.

## Acceptance criteria

PASS if:

- the normative decision path remains narrow and explicit
- required gates are policy-defined and materialized
- required gates pass only on literal boolean `true`
- missing required evidence fails closed
- Ledger / manifest / audit bundle / publication surfaces do not alter the decision
- release-grade paths reject stubbed, unsigned, stale, malformed, or non-materialized required evidence
- the release decision can be reconstructed from archived artifacts

FAIL if:

- any explanatory surface can authorize, block, override, or reinterpret release
- advisory evidence becomes release authority without declared policy
- missing required evidence can produce PASS
- release-grade PASS can occur through stubbed or non-materialized evidence
- public surfaces can drift without detection
- verification requires hidden state or maintainer explanation

## Summary

PULSE-REF strengthens the existing PULSE release-authority system by making the release-grade path externally verifiable.

The authority boundary remains unchanged:

the release decision is produced by declared-policy gate enforcement and recorded through CI outcome.

Everything else preserves, explains, verifies, or reconstructs that decision.
