# Release Reference Fixtures v1

## Purpose

This fixture set defines initial PULSE-REF release-grade reference cases.

The goal is to test whether the PULSE release-authority path remains deterministic, fail-closed, policy-bound, and externally verifiable under realistic evidence conditions.

These fixtures are not a second decision engine. They are test inputs for exercising the declared-policy gate-enforcement path.

## Authority boundary

The normative release decision is produced by the declared-policy gate-enforcement path and recorded through the CI outcome.

Release-authority manifests, audit bundles, ledgers, dashboards, summaries, benchmark reports, and publication surfaces preserve, explain, and reconstruct the decision. They do not authorize, block, override, reinterpret, or create a second release-decision path.

## Fixture categories

### pass

Expected outcome: PASS.

Represents a release-grade candidate with:

- non-stubbed release profile
- materialized detector evidence
- external summaries present
- valid required gates
- valid release_required gates
- release-authority manifest present
- audit bundle present
- publication snapshot consistent

### missing_external

Expected outcome: FAIL.

Represents a release-grade candidate where external summaries are missing.

Release-grade paths must not infer PASS from absent external evidence.

### stubbed

Expected outcome: FAIL.

Represents a release-grade candidate where gates or detector outputs are stubbed.

Release-grade paths must not pass when `gates_stubbed=true` or equivalent stub indicators are present.

### scaffolded

Expected outcome: FAIL.

Represents a release-grade candidate where diagnostics mark the state as scaffolded.

Release-grade paths must not pass when `diagnostics.scaffold=true` or equivalent scaffold indicators are present.

### malformed_summary

Expected outcome: FAIL.

Represents a release-grade candidate where an external detector / evaluation summary is present but malformed.

Release-grade paths must fail closed on malformed evidence.

### unsigned_summary

Expected outcome: FAIL.

Represents a release-grade candidate where an external summary is present but lacks required signer / identity verification.

Release-grade paths must not fold unsigned or signer-mismatched evidence into release authority when signer requirements apply.

### stale_artifact

Expected outcome: FAIL.

Represents a release-grade candidate where evidence exists but is stale, mismatched to the run, or not bound to the current subject / dataset digest.

### false_gate

Expected outcome: FAIL.

Represents a release-grade candidate where a required or release_required gate is explicitly false.

### publication_mismatch

Expected outcome: FAIL.

Represents a case where the public Ledger, status artifact, release-authority manifest, or audit bundle point to different run IDs, git SHAs, or hashes.

Publication surfaces are non-normative, but publication inconsistency must be detected in release-grade reference validation.

### implicit_fallback_attempt

Expected outcome: FAIL.

Represents a release-grade candidate where missing evidence attempts to produce PASS through a default, fallback, or absence of summary.

Release-grade paths require explicit evidence presence.

### agent_diagnostic_promoted

Expected outcome: FAIL.

Represents a case where agent-produced diagnostic evidence is incorrectly treated as release authority without declared policy promotion.

Agent-produced work may be diagnostic evidence. It does not become release authority unless explicitly promoted by policy and materialized as a required gate.

## Initial directory layout

```text
tests/fixtures/release_reference_v1/
  README.md
  pass/
  missing_external/
  stubbed/
  malformed_summary/
  unsigned_summary/
  stale_artifact/
  false_gate/
  publication_mismatch/
  implicit_fallback_attempt/
  agent_diagnostic_promoted/
```

## Expected runner behavior

A future PULSE-REF fixture runner should:

- load each fixture;
- identify the expected outcome;
- run the declared-policy gate-enforcement path;
- compare actual outcome against expected outcome;
- fail if any negative fixture produces release-grade PASS;
- fail if any explanatory or preservation surface changes the decision.

## Non-goals

This fixture set does not replace upstream safety evaluations, detector systems, CI workflows, or review processes.

This fixture set does not define release authority.

This fixture set only exercises whether recorded evidence, declared policy, and materialized gate sets produce the expected deterministic fail-closed release decision.
