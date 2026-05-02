# PULSE-REF Gap Inventory v1

## Purpose

This document records the initial PULSE-REF gap inventory after the OpenAI Safety Fellowship submission.

PULSE already has an existing public artifact trail and core release-decision mechanics. The active PULSE-REF track converts that existing system into an externally verifiable release-grade reference path.

This inventory is not a redesign plan. It lists the concrete release-grade blockers that must be closed so that the existing PULSE normative core can be demonstrated through a non-stubbed, materialized-evidence reference run.

## Current state

PULSE currently has:

- public GitHub repository
- commit history
- CI workflows
- status/evidence contract
- gate policy and gate registry
- strict fail-closed required-gate semantics
- Quality Ledger
- status.json publication surface
- release authority manifest structure
- audit-bundle structure
- release-grade reference-run documentation
- external detector summary documentation

The existing normative release-decision path remains intentionally narrow:

recorded evidence -> status.json -> declared gate policy -> materialized required gate set -> strict gate checking.

The normative release decision is produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

Release-authority manifests, audit bundles, ledgers, dashboards, summaries, and publication surfaces preserve, explain, and reconstruct that decision. They do not authorize, block, override, or create a second release-decision path.

## Current release-grade blockers

### 1. Non-stubbed release-grade reference run

Current gap:

A fully non-stubbed, materialized-evidence release-grade reference run is not yet complete as the public reference artifact.

Target state:

A release-grade reference run exists with:

- non-stubbed release profile
- materialized detector evidence
- required + release_required gate evaluation
- CI outcome
- release-authority manifest
- audit bundle
- verification instructions

Acceptance:

PASS if the reference run uses materialized evidence and no stubbed gate state contributes to release-grade PASS.

FAIL if gates_stubbed=true, detectors_materialized_ok=false, missing external summaries, or implicit fallback behavior contributes to release-grade PASS.

### 2. External evidence schema and signer requirements

Current gap:

External detector and evaluation summaries are documented, but release-grade evidence needs a stricter canonical schema and signer / identity requirements.

Target state:

External summaries are validated before fold-in using:

- canonical external_summary_v1 schema
- stable metric keys
- threshold references
- tool identity
- tool version
- dataset or subject digest
- signer identity
- verification before release-decision fold-in

Acceptance:

PASS if release-grade external evidence is schema-valid, identity-bound, and verified before entering status.json.

FAIL if malformed, unsigned, stale, signer-mismatched, or unversioned evidence is folded into a release-grade decision.

### 3. Provenance and attestation

Current gap:

The current artifact trail is audit-ready, but not yet fully strengthened with provenance / attestation for release-grade reference artifacts.

Target state:

Release-grade artifacts have verifiable provenance / attestation, including:

- artifact hashes
- expected signer or workflow identity
- release bundle verification
- offline verification notes where appropriate

Acceptance:

PASS if a reviewer can verify that the release-grade artifacts came from the expected workflow and match the recorded hashes.

FAIL if artifact identity, signer identity, workflow identity, or bundle hash cannot be verified.

### 4. Atomic publication snapshot

Current gap:

Public surfaces can drift if Ledger, status.json, manifest, and audit bundle are not tied to the same immutable run.

Target state:

Publication uses an atomic snapshot model:

- versioned run path
- run_id
- git_sha
- created_utc
- status hash
- ledger hash
- manifest hash
- audit bundle hash
- latest pointer as pointer only, not authority

Acceptance:

PASS if Ledger, status artifact, release-authority manifest, and audit bundle all point to the same run.

FAIL if public surfaces show mismatched run IDs, hashes, git SHAs, or timestamps.

### 5. Zero implicit PASS fallback

Current gap:

Release-grade paths must not infer PASS from missing evidence.

Target state:

Release-grade mode requires explicit evidence presence:

- no missing required evidence can become PASS
- no implicit refusal-delta PASS fallback in release-grade paths
- external summaries required in release-grade paths
- evidence presence gates are explicit

Acceptance:

PASS if missing required evidence produces explicit missing / fail state.

FAIL if any missing required evidence becomes release-grade PASS through fallback, default, or absence of summary.

### 6. Benchmark fixtures

Current gap:

The system needs a repeatable fixture layer for evidence-to-decision failure modes.

Target state:

Benchmark fixtures cover:

- valid evidence
- missing evidence
- malformed evidence
- stale artifacts
- false gates
- unsigned summaries
- signer mismatch
- dashboard/status disagreement
- publication mismatch
- implicit fallback attempt
- agent-produced diagnostic artifact promoted incorrectly

Acceptance:

PASS if the fixture suite produces expected pass/fail outcomes and can be run repeatedly in CI.

FAIL if false-green, missing-evidence, or publication-mismatch cases pass release-grade gates.

### 7. External verification pack

Current gap:

A reviewer should be able to reconstruct the release decision from artifacts without trusting a rendered dashboard or maintainer explanation.

Target state:

A public verification pack exists with:

- verification playbook
- one-command or documented verification steps
- status artifact
- release-authority manifest
- audit bundle
- hashes
- provenance / attestation notes
- benchmark summary

Acceptance:

PASS if a third party can reconstruct the release decision from archived artifacts.

FAIL if verification requires hidden state, private explanation, or trusting a visual surface.

## Priority order

1. Non-stubbed release-grade reference run
2. Zero implicit PASS fallback
3. External evidence schema and signer requirements
4. Atomic publication snapshot
5. Provenance and attestation
6. Benchmark fixtures
7. External verification pack

## First implementation targets

Initial files / work items:

- docs/release_authority_boundary_v1.md
- PULSE_safe_pack_v0/profiles/release_grade_reference_v1.yml
- tests/fixtures/release_reference_v1/
- schemas/external_summary_v1.schema.json
- docs/evidence_presence_policy_v1.md
- docs/publication_consistency_v1.md
- docs/verification_playbook_v1.md

## Non-goals

This inventory does not create a second release-decision engine.

This inventory does not make the Quality Ledger, release-authority manifest, audit bundle, dashboard, Pages surface, or publication surface normative.

This inventory does not replace upstream safety evaluations, detectors, review processes, or CI workflows.

PULSE-REF consumes recorded evidence from those upstream processes, binds it to declared policy, and validates whether the resulting release decision remains deterministic, fail-closed, auditable, and externally verifiable.

## Review-period target

By the review period, the target public artifact trail should include:

- non-stubbed release-grade reference run
- materialized detector evidence
- external_summary_v1 schema
- signer / identity requirements
- no-implicit-PASS release-grade tests
- atomic publication snapshot
- verification playbook
- benchmark fixtures
- release-authority manifest and audit bundle tied to the same run
