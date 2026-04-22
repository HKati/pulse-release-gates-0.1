# PULSEmech Break-glass Override v0

## Purpose

`break_glass_override_v0` defines the audited exception mechanism for rare
situations where a human operator authorizes an operational release despite a
non-passing release decision.

Break-glass is not a hidden pass.

Break-glass is not a shadow signal.

Break-glass is not a rewrite of `release_decision_v0`.

It is a separate governance artifact that records:

- what failed,
- who requested the exception,
- who reviewed it when review has occurred,
- why it was accepted or rejected,
- how long it is valid when accepted,
- what follow-up work is required,
- and which release-decision artifact it was attached to.

## Core rule

A break-glass override must never rewrite the gate verdict.

The release decision remains what it was:

```text
FAIL
STAGE-PASS
PROD-PASS
```

If the release decision is `FAIL` and an override is accepted, the system records
two facts:

```text
release_level = FAIL
break_glass_status = accepted
```

It must not silently convert that into:

```text
release_level = PROD-PASS
```

or:

```text
release_level = STAGE-PASS
```

## Authority boundary

The normal release-authority path remains:

```text
status.json
+ materialized required gates
+ check_gates.py
+ release_decision_v0.json
```

Break-glass is a separate audited exception path:

```text
release_decision_v0.json
+ break_glass_override_v0.json
+ human review when applicable
+ exception ledger rendering
```

Break-glass may authorize an operational exception, but it must not mutate the
underlying release-decision artifact.

## Non-goals

`break_glass_override_v0` does not:

- change `check_gates.py`,
- change `status.json`,
- change `pulse_gate_policy_v0.yml`,
- change the meaning of required gates,
- promote shadow layers,
- reinterpret missing evidence as pass,
- turn `FAIL` into `PASS`,
- hide risk,
- remove the need for follow-up remediation.

## When break-glass is allowed

Break-glass is reserved for rare, critical situations.

Examples may include:

- urgent mitigation release,
- critical security fix,
- production incident containment,
- time-sensitive rollback or forward-fix,
- externally required emergency change.

Break-glass must not be used for convenience, routine release pressure, or
normal detector/evidence gaps.

## Required relationship to release_decision_v0

Every break-glass record must reference a concrete release-decision artifact.

Minimum reference:

```text
release_decision_path
release_decision_sha256
release_level_before_override
target
```

If the release decision artifact is missing, the override record is incomplete.

If the referenced release decision cannot be validated, the override record is
incomplete.

## Override statuses

The override status vocabulary is:

```text
requested
accepted
rejected
expired
revoked
```

### requested

An override request exists but has not been approved or rejected.

A requested override is a pre-decision artifact. It must not claim review
approval or rejection before review occurs.

### accepted

A reviewer accepted the exception with justification, scope, expiry, and
follow-up requirements.

### rejected

A reviewer rejected the exception.

### expired

The override validity window has elapsed.

### revoked

The override was manually withdrawn before expiry.

## Required fields

The required field set is state-dependent.

A break-glass artifact always has a common request identity surface, but review
fields are not required while the override is still only requested.

This prevents the `requested` state from inventing fake reviewer decisions before
a review has happened.

### Common required fields

Every break-glass artifact must contain at minimum:

```text
schema
version
created_utc
override_id
status
target
release_decision_path
release_decision_sha256
release_level_before_override
requested_by
request_reason
```

### State-specific required fields

For `status = requested`:

```text
review is not required
risk_acceptance is not required
expires_utc is not required
followups may be omitted or recorded as proposed follow-ups
```

A requested override is a pre-decision artifact.

It must not claim review approval or rejection before review occurs.

For `status = accepted`:

```text
review is required
review.decision = accepted
risk_acceptance is required
expires_utc is required
followups is required and must contain at least one item
```

For `status = rejected`:

```text
review is required
review.decision = rejected
expires_utc should be null or omitted
followups may be included when remediation is required before re-requesting
```

For `status = expired`:

```text
review is required from the original accepted override
expires_utc is required
status records that the accepted override is no longer active
```

For `status = revoked`:

```text
review is required from the original accepted override
risk_acceptance is required
expires_utc is required and must preserve the original accepted override expiry
revocation is required
followups is required and must contain at least one item
status records that the accepted override was withdrawn before expiry
```

## Review requirements

A `requested` override is allowed to exist without a review block.

This is intentional.

A requested override represents a submitted exception request that has not yet
been approved or rejected.

Once an override leaves the `requested` state, review information is required.

For an accepted override:

```text
status = accepted
review.decision = accepted
review.reviewed_by is required
review.reviewed_utc is required
review.decision_reason is required
```

For a rejected override:

```text
status = rejected
review.decision = rejected
review.reviewed_by is required
review.reviewed_utc is required
review.decision_reason is required
```

For revoked or expired overrides, the artifact must preserve enough review,
expiry, or revocation context to reconstruct why the override is no longer
active.

A break-glass artifact must not fabricate review data merely to satisfy a schema.

The schema and validators should encode the same rule:

```text
requested => review optional
accepted/rejected/revoked/expired => review or equivalent decision record required
```

## Expiry rule

Accepted break-glass overrides must expire.

`expires_utc` is required for accepted overrides.

An accepted override without expiry is invalid.

Expired overrides must not be treated as active operational authorization.

Requested and rejected overrides do not represent active operational
authorization and therefore do not require an expiry timestamp.

## Follow-up rule

Accepted break-glass overrides must include at least one follow-up item.

Examples:

```text
restore missing external evidence
rerun release-grade detector pipeline
file post-release incident review
tighten policy or detector coverage
re-run PULSEmech release decision after remediation
```

Follow-ups are part of the governance record.

Requested overrides may include proposed follow-ups, but proposed follow-ups do
not become mandatory remediation until the override is accepted or the reviewer
records them as required after rejection.

Rejected overrides may include follow-ups when remediation is required before a
new request is submitted.

## Ledger rendering rule

The Quality Ledger may render break-glass information, but it must do so as an
exception record.

It must not render an accepted break-glass override as a normal pass.

Correct rendering:

```text
Release decision: FAIL
Break-glass override: accepted
Operational exception: active until <expires_utc>
Reason: <decision_reason>
Follow-ups: ...
```

Incorrect rendering:

```text
Release decision: PROD-PASS
```

when the underlying release decision was `FAIL`.

A requested override should render as a pending request, not as an accepted
exception.

Correct requested rendering:

```text
Release decision: FAIL
Break-glass override: requested
Operational exception: not active
Review: pending
```

## Shadow-layer rule

Break-glass is not a shadow layer.

Shadow outputs may inform human review, but they do not authorize break-glass by
themselves.

A shadow diagnostic can be cited as supporting evidence only when the review
record explicitly references it.

## Audit rule

Every accepted break-glass override must preserve:

- the referenced release-decision artifact,
- the override artifact,
- the reviewer decision,
- the expiry,
- the follow-up list,
- and the final Ledger view.

Requested break-glass artifacts must preserve:

- the referenced release-decision artifact,
- the request identity,
- the request reason,
- and the fact that review has not yet occurred.

The artifact chain should make it possible to reconstruct why the normal release
path did not pass and why an exception was requested, accepted, rejected,
expired, or revoked.

## Suggested artifact path

The default artifact path is:

```text
PULSE_safe_pack_v0/artifacts/break_glass_override_v0.json
```

## Suggested schema path

The planned schema path is:

```text
schemas/break_glass_override_v0.schema.json
```

## Suggested validator path

The planned validator path is:

```text
PULSE_safe_pack_v0/tools/validate_break_glass_override.py
```

## Suggested renderer path

The planned Ledger renderer path is:

```text
PULSE_safe_pack_v0/tools/render_break_glass_ledger_section.py
```

## Minimal requested example

A requested override has not been approved or rejected yet.

It does not need a review block.

```json
{
  "schema": "pulse_break_glass_override_v0",
  "version": "0.1.0",
  "created_utc": "2026-04-21T00:00:00Z",
  "override_id": "BG-2026-04-21-000",
  "status": "requested",
  "target": "prod",
  "release_decision_path": "PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
  "release_decision_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "release_level_before_override": "FAIL",
  "requested_by": "maintainer",
  "request_reason": "Emergency mitigation release requested for review."
}
```

This artifact records a request only.

It is not an accepted operational exception.

It must not be rendered as an active break-glass authorization.

## Minimal accepted example

```json
{
  "schema": "pulse_break_glass_override_v0",
  "version": "0.1.0",
  "created_utc": "2026-04-21T00:00:00Z",
  "override_id": "BG-2026-04-21-001",
  "status": "accepted",
  "target": "prod",
  "release_decision_path": "PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
  "release_decision_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "release_level_before_override": "FAIL",
  "requested_by": "maintainer",
  "request_reason": "Emergency mitigation release for active production incident.",
  "review": {
    "reviewed_by": "release-owner",
    "reviewed_utc": "2026-04-21T00:10:00Z",
    "decision": "accepted",
    "decision_reason": "Risk accepted temporarily to mitigate active incident."
  },
  "risk_acceptance": {
    "scope": "single emergency release",
    "known_risks": [
      "external detector evidence incomplete"
    ],
    "mitigations": [
      "manual review completed",
      "post-release detector rerun required"
    ]
  },
  "expires_utc": "2026-04-22T00:00:00Z",
  "followups": [
    {
      "id": "BG-FU-001",
      "owner": "maintainer",
      "due_utc": "2026-04-22T12:00:00Z",
      "action": "rerun release-grade external detector evidence pipeline"
    }
  ]
}
```

## Minimal rejected example

```json
{
  "schema": "pulse_break_glass_override_v0",
  "version": "0.1.0",
  "created_utc": "2026-04-21T00:00:00Z",
  "override_id": "BG-2026-04-21-002",
  "status": "rejected",
  "target": "prod",
  "release_decision_path": "PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
  "release_decision_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "release_level_before_override": "FAIL",
  "requested_by": "maintainer",
  "request_reason": "Release requested despite incomplete evidence.",
  "review": {
    "reviewed_by": "release-owner",
    "reviewed_utc": "2026-04-21T00:10:00Z",
    "decision": "rejected",
    "decision_reason": "No emergency justification and missing external evidence."
  },
  "risk_acceptance": {
    "scope": "none",
    "known_risks": [
      "external detector evidence incomplete"
    ],
    "mitigations": []
  },
  "expires_utc": null,
  "followups": [
    {
      "id": "BG-FU-001",
      "owner": "maintainer",
      "due_utc": "2026-04-22T12:00:00Z",
      "action": "provide release-grade evidence before requesting release again"
    }
  ]
}
```

## Minimal revoked example

```json
{
  "schema": "pulse_break_glass_override_v0",
  "version": "0.1.0",
  "created_utc": "2026-04-21T00:00:00Z",
  "override_id": "BG-2026-04-21-003",
  "status": "revoked",
  "target": "prod",
  "release_decision_path": "PULSE_safe_pack_v0/artifacts/release_decision_v0.json",
  "release_decision_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "release_level_before_override": "FAIL",
  "requested_by": "maintainer",
  "request_reason": "Emergency mitigation release for active production incident.",
  "review": {
    "reviewed_by": "release-owner",
    "reviewed_utc": "2026-04-21T00:10:00Z",
    "decision": "accepted",
    "decision_reason": "Risk accepted temporarily to mitigate active incident."
  },
  "risk_acceptance": {
    "scope": "single emergency release",
    "known_risks": [
      "external detector evidence incomplete"
    ],
    "mitigations": [
      "manual review completed",
      "post-release detector rerun required"
    ]
  },
  "expires_utc": "2026-04-22T00:00:00Z",
  "revocation": {
    "revoked_by": "release-owner",
    "revoked_utc": "2026-04-21T06:00:00Z",
    "revocation_reason": "Emergency condition resolved before deployment."
  },
  "followups": [
    {
      "id": "BG-FU-001",
      "owner": "maintainer",
      "due_utc": "2026-04-22T12:00:00Z",
      "action": "rerun release-grade external detector evidence pipeline"
    }
  ]
}
```

## Implementation sequence

Recommended implementation order:

```text
1. docs/BREAK_GLASS_OVERRIDE_v0.md
2. schemas/break_glass_override_v0.schema.json
3. PULSE_safe_pack_v0/tools/validate_break_glass_override.py
4. tests/test_break_glass_override_v0_smoke.py
5. PULSE_safe_pack_v0/tools/render_break_glass_ledger_section.py
6. CI artifact publication
7. Quality Ledger integration
```

## Maintenance rule

Any change to break-glass semantics must update:

- this document,
- the JSON Schema,
- validator tests,
- Ledger rendering,
- and any workflow that publishes or consumes break-glass artifacts.

Break-glass must remain explicit, audited, temporary, and separate from normal
release-decision semantics.
