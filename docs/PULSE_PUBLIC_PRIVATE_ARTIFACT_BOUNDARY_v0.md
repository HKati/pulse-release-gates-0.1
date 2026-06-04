# PULSE Public / Private Artifact Boundary v0

## Purpose

This document defines the v0 public / private artifact boundary for PULSE.

It classifies how release-state artifacts, reader surfaces, audit materials,
external verification carriers, and operational metadata may be exposed or
withheld.

It does not change PULSEmech release authority.

It does not add gates.

It does not change policy.

It does not change schemas.

It does not change CI behavior.

It does not modify `check_gates.py`.

It defines review concepts for deciding whether an artifact may be public,
public with constraints, private to audit/review, or restricted.

## Authority boundary

The PULSEmech authority path remains unchanged:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

Publication status does not create release authority.

A public artifact is not authoritative because it is public.

A private artifact is not non-authoritative because it is private.

Release authority is determined only by the PULSEmech authority path.

## Scope

This v0 document is definitional.

It may be used for review, hardening planning, release-surface classification,
publication review, and future implementation alignment.

It does not assert that any current public artifact set is complete,
incomplete, compliant, or non-compliant.

It defines the boundary to be used when evaluating future artifact publication
and public/private release-surface behavior.

## Core distinction

PULSE separates:

```text
release-authority role
```

from:

```text
publication exposure
```

An artifact may be release-relevant and public.

An artifact may be release-relevant and private.

An artifact may be public and non-authoritative.

An artifact may be private and non-authoritative.

The release-authority role is determined by evidence binding, declared policy,
materialized gates, and strict CI enforcement.

Publication exposure is determined by artifact content, operational metadata,
security sensitivity, privacy sensitivity, reproducibility value, and reader
surface risk.

The two classifications must not be collapsed.

## Artifact boundary model

The v0 boundary model is:

```text
artifact source
→ artifact role
→ release-state relation
→ evidence binding
→ publication class
→ redaction / withholding decision
→ public, private, or restricted exposure
```

This model does not replace PULSEmech.

It defines how artifacts are classified before publication or withholding.

## Definitions

### Artifact

An artifact is a recorded file, generated output, report, summary, manifest,
binding, package, or verification result associated with a PULSE run, release
review, audit path, or reader surface.

### Recorded authority artifact

A recorded authority artifact is an artifact that participates in the
PULSEmech authority path.

Examples may include:

- `status.json`;
- declared gate policy;
- materialized required gate set;
- strict gate enforcement output;
- recorded release evidence;
- release decision artifact when produced by the declared path.

A recorded authority artifact may be public or private depending on publication
classification.

Publication does not determine authority.

### Reader surface

A reader surface is an artifact that presents, summarizes, renders, explains, or
links release-state information.

Reader surfaces may include:

- Quality Ledger output;
- rendered HTML reports;
- Markdown summaries;
- badges;
- dashboards;
- SARIF/JUnit output;
- Pages output;
- status summaries;
- audit summaries;
- external verification packet reports;
- RA1 reports.

Reader surfaces do not authorize release.

A reader surface may participate in review only when explicitly bound into the
recorded release-state relation and its mechanical effect is defined by declared
policy, materialized gates, and strict CI enforcement.

### Audit bundle

An audit bundle is a collection of artifacts retained for review, replay,
debugging, reconstruction, provenance analysis, or incident analysis.

An audit bundle may include artifacts that are not suitable for public exposure.

An audit bundle does not become release authority by being complete, retained,
uploaded, archived, or published.

### External verification carrier

An external verification carrier is an artifact or package intended to allow a
third party to review or reconstruct recorded release-state relations.

External verification carriers are not release authority unless explicitly bound
through the PULSEmech authority path.

They may support external review, provenance review, or release-state
reconstruction.

### Operational metadata

Operational metadata is metadata about the environment, run, workflow, branch,
commit, artifact path, tool version, timestamp, or execution context.

Operational metadata may be necessary for reproducibility.

Operational metadata may also expose unnecessary local paths, runner details,
operator context, environment structure, or review context.

Operational metadata must be classified before publication.

### Sensitive material

Sensitive material includes secrets, credentials, tokens, keys, private URLs,
private repository information, personal data, private prompts, private model
outputs, unredacted logs, undisclosed vulnerability details, private operator
notes, and environment data that should not be publicly exposed.

Sensitive material must not be published unless explicitly reviewed,
sanitized, and intended for public release.

## Publication classes

### 1. Public source artifact

A public source artifact is intended to be visible in the public repository.

Examples may include:

- source code;
- tests;
- public documentation;
- schemas;
- declared public policy files;
- public examples;
- public fixtures that contain no sensitive material.

Public source artifacts may be reviewed directly in the repository.

### 2. Public reader surface

A public reader surface is intended to present release-state or project-state
information to readers.

Examples may include:

- public Pages output;
- Quality Ledger HTML;
- public status summary;
- public badges;
- public Markdown summaries;
- public documentation index pages.

A public reader surface must not claim independent release authority.

It must not present advisory, diagnostic, scaffold, stale, or incomplete
information as release permission.

### 3. Public recorded artifact

A public recorded artifact is a recorded artifact exposed publicly because it is
needed for reproducibility, review, citation, or external verification.

Examples may include:

- public `status.json`;
- public release-decision artifact;
- public artifact binding;
- public digest manifest;
- public release reference package;
- public external verification packet.

A public recorded artifact must be reviewed for sensitive content before
publication.

Public exposure does not change its authority role.

### 4. Public reference package

A public reference package is a bounded package of artifacts intended to support
third-party reconstruction or verification.

A public reference package should prefer repository-relative paths or sanitized
paths.

Absolute workspace paths may be valid for verification when they resolve inside
the reviewed root, but public packages should avoid exposing unnecessary local or
runner-specific path material when a repository-relative representation is
available.

A public reference package must not include secrets, credentials, private logs,
private prompts, private model outputs, or unredacted sensitive material.

### 5. Private audit material

Private audit material is retained for review, investigation, debugging,
incident analysis, or internal reconstruction but is not intended for public
publication.

Examples may include:

- raw detector output containing sensitive content;
- unredacted CI logs;
- operator notes;
- private artifact stores;
- private review packets;
- incident reproduction material;
- local environment traces;
- unredacted security scan output.

Private audit material may support review.

It does not become public reader material unless classified and sanitized.

### 6. Restricted material

Restricted material must not be published through normal public artifacts or
reader surfaces.

Examples include:

- secrets;
- tokens;
- credentials;
- signing keys;
- private keys;
- private repository URLs;
- private personal data;
- private vulnerability details before coordinated handling;
- local credential paths;
- unredacted environment variables;
- unredacted private prompts or model outputs.

Restricted material requires explicit handling outside the normal public
artifact path.

## Public exposure requirements

An artifact may be published only when all applicable conditions are satisfied.

### 1. Artifact role is identified

The artifact role must be identified before publication.

The review must distinguish at least:

```text
recorded authority artifact
reader surface
audit bundle
external verification carrier
source artifact
diagnostic artifact
advisory artifact
private audit material
restricted material
```

### 2. Release-state relation is identified

If the artifact is release-relevant, its release-state relation must be
identified.

The review must determine whether the artifact is:

- bound into the recorded release-state relation;
- diagnostic context only;
- advisory context only;
- stale;
- unmatched;
- external reconstruction material;
- reader surface only.

Repository presence alone is not release-state relation.

### 3. Sensitive material is excluded

The artifact must not contain secrets, credentials, tokens, private keys,
private URLs, private personal data, or other restricted material.

If sensitive material is present, the artifact must not be published unless it is
sanitized and re-reviewed.

### 4. Operational metadata is minimized

Operational metadata should be included only when needed for reproducibility,
artifact binding, release-state reconstruction, or reader interpretation.

The following metadata may be acceptable when required and already public or
non-sensitive:

- commit identity;
- run identity;
- created timestamp;
- repository-relative artifact path;
- digest;
- tool version;
- schema identifier;
- release tag;
- public workflow identity.

The following metadata requires review before public exposure:

- absolute runner paths;
- local operator paths;
- private filesystem paths;
- private artifact store paths;
- environment variables;
- private runner details;
- private operator identifiers;
- unredacted workflow inputs.

### 5. Reader surface boundary is explicit

A public reader surface must not imply that it is release authority.

A reader surface must preserve the distinction between:

```text
recorded release state
```

and:

```text
release permission
```

### 6. Staleness and identity are reviewable

A public artifact that represents a release-state snapshot should include enough
identity to evaluate whether it is stale or current for its intended purpose.

Useful identity may include:

- commit identity;
- run identity;
- created timestamp;
- artifact digest;
- release tag;
- source artifact path;
- package manifest identity.

Missing identity does not automatically make an artifact private.

Missing identity may make the artifact unsuitable for release-state publication
or external verification.

### 7. Publication does not bypass CI

No publication path may bypass the PULSEmech authority path.

Pages output, release notes, badges, dashboards, summaries, reports, manifests,
or external packets must not create release permission without declared policy,
materialized gates, and strict CI enforcement.

## Private / withheld conditions

An artifact must remain private, withheld, or restricted if any of the following
conditions apply:

```text
contains secrets, tokens, credentials, or keys
contains private personal data
contains private prompts or model outputs
contains unredacted CI logs with sensitive data
contains local operator environment details not required for reproducibility
contains private repository or artifact-store references
contains undisclosed vulnerability details requiring controlled handling
contains raw detector output not classified for public release
contains external evidence that has not been reviewed for public exposure
contains stale release-state material that could mislead readers
contains diagnostic-only or scaffold-only material presented as release-grade
contains advisory-only evidence presented as release permission
contains absolute paths that expose unnecessary local or runner structure
contains untrusted HTML or rendered content without escaping or review
```

If classification is unclear, the artifact defaults to non-public until reviewed.

This is a publication boundary.

It does not change release-authority semantics.

## Public status artifact requirements

A public `status.json` or status-derived public artifact must be reviewed under
the following requirements.

### Required classification

The review must determine whether the public status artifact is:

- recorded authority artifact;
- public reader artifact;
- public summary artifact;
- stale snapshot;
- diagnostic/core/demo artifact;
- release-grade materialized lane artifact.

### Required identity

A public status artifact should include or be linkable to:

- commit identity;
- run identity;
- created timestamp;
- schema version;
- gate state;
- run mode or lane context;
- artifact source.

### Required boundary

A public status artifact must not be treated as release permission by presence
alone.

A public status artifact supports release review only when connected to the
declared policy, materialized gates, and strict CI enforcement of the same
release-state path.

### Scaffold / diagnostic exposure

Scaffold, demo, core, smoke, diagnostic, shadow, or advisory-only public status
artifacts may be useful for transparency.

They must not be presented as release-grade materialized lanes.

If they are public, the reader boundary must remain clear.

## Public Pages requirements

Pages output is a public reader surface unless explicitly bound into the
PULSEmech authority path.

Pages output must not override:

- recorded evidence;
- `status.json`;
- declared policy;
- materialized gates;
- strict CI enforcement;
- release decision artifact.

Pages output should avoid presenting stale, scaffold, diagnostic, or advisory
data as release-grade release permission.

Pages output should identify the source run, commit, or artifact set when it
represents a specific release-state snapshot.

## External verification packet requirements

An external verification packet may be public when it has been reviewed for
sensitive content and is intended for external reconstruction.

An external verification packet must preserve the following boundary:

```text
external verification carrier; not release authority
```

The packet may record artifact identity, digest coverage, reviewer commands,
binding verification, and known missing artifacts.

The packet must not create release permission.

The packet must not execute verifier code from reviewed roots.

The packet must not expose restricted material.

## RA1 / reference package requirements

A public RA1 or release reference package may support third-party
reconstruction.

It must preserve package-root and reviewed-root boundaries.

It must reject or mark invalid:

- traversal paths;
- symlink escape;
- digest mismatch;
- untracked files when prohibited;
- inconsistent identity;
- package-root escape;
- executable verifier selection from reviewed roots.

A public RA1 or reference package does not authorize release by existence.

It supports reconstruction and review.

## Artifact binding requirements

Artifact binding material may be public when it is needed for reproducibility or
external verification and contains no restricted material.

Binding and package verification tools must treat reviewed repository roots and
package roots as untrusted input boundaries.

File paths may be relative or absolute only if they resolve inside the
applicable reviewed repository root or package root.

Traversal, symlink escape, non-portable path syntax, outside-root reads, and
executable-code selection from reviewed roots are high-risk findings.

Public binding artifacts should avoid unnecessary local or runner-specific path
exposure when a repository-relative representation is available.

## Review sequence v0

A public / private artifact boundary review follows this sequence.

### 1. Identify artifact source

Identify where the artifact came from.

Examples:

- repository source file;
- CI output;
- generated report;
- release artifact;
- Pages artifact;
- audit bundle;
- external verifier packet;
- RA1 package;
- local reproduction material.

### 2. Identify artifact role

Classify the artifact as authority, reader, audit, diagnostic, advisory,
external verification, reference package, private audit, or restricted material.

If the role is unclear, do not publish until classified.

### 3. Identify release-state relation

Determine whether the artifact is bound to a specific release-state relation.

Review run identity, commit identity, artifact source, digest, policy source, and
gate relation where applicable.

### 4. Inspect sensitive content

Check for secrets, credentials, private data, unredacted logs, private prompts,
private model outputs, private URLs, local credential paths, and restricted
security material.

If present, withhold or sanitize before publication.

### 5. Review operational metadata

Determine whether operational metadata is necessary for reproducibility or
release-state reconstruction.

Remove or avoid unnecessary local path, environment, runner, or operator detail
when possible.

### 6. Assign publication class

Assign one of the following classes:

```text
public source artifact
public reader surface
public recorded artifact
public reference package
private audit material
restricted material
```

### 7. Verify reader-surface boundary

If public, ensure the artifact does not present itself as release authority
unless it is actually bound through declared policy, materialized gates, and
strict CI enforcement.

### 8. Verify staleness and identity handling

Ensure stale snapshots, diagnostic runs, scaffold states, demo/core states, or
advisory-only artifacts are not presented as current release-grade permission.

### 9. Publish, withhold, or sanitize

Publish only if classification, sensitive-content review, metadata review, and
reader-surface boundary review are complete.

Otherwise withhold or sanitize.

## Fail-closed publication conditions

Publication must stop until review or sanitization if any of the following
conditions hold:

```text
artifact role is unknown
release-state relation is claimed but not reviewable
artifact contains secrets, credentials, tokens, or keys
artifact contains private personal data
artifact contains unredacted private prompts or model outputs
artifact contains sensitive CI logs
artifact contains private operator notes
artifact contains unreviewed raw detector output
artifact contains undisclosed vulnerability details
artifact contains unnecessary local or runner path exposure
artifact contains untrusted rendered content without escaping or review
reader surface presents diagnostic or advisory data as release permission
reader surface presents stale data as current release-grade status
public package contains path traversal or symlink escape
public package contains executable verifier code selected from reviewed root
classification is unclear
```

This fail-closed behavior applies to publication.

It does not alter PULSEmech release-authority behavior.

## Non-goals

This document does not define a production release policy.

It does not define required gates.

It does not change artifact schemas.

It does not change CI workflows.

It does not change Pages publication workflows.

It does not modify renderers.

It does not modify `check_gates.py`.

It does not define secret-scanning implementation.

It does not define legal or regulatory publication rules.

It does not create a second authority path.

## Relationship to release-grade materialized lane

The release-grade materialized lane defines when a recorded run is structurally
eligible for release-grade review.

The public / private artifact boundary defines whether artifacts associated with
a run may be public, private, or restricted.

A release-grade materialized lane may produce public artifacts.

A release-grade materialized lane may also require private audit artifacts.

Publication classification does not create or remove lane eligibility.

Lane eligibility and publication exposure must be reviewed separately.

## Relationship to relational state transition layer

The relational state transition layer defines how state, relation, evidence
binding, mechanical effect, and decision transition remain connected above the
PULSEmech authority path.

The public / private artifact boundary defines which connected artifacts may be
exposed publicly and which must remain private or restricted.

A connected artifact is not automatically public.

A public artifact is not automatically connected to a release-state transition.

Connection and exposure must be reviewed separately.

## Future implementation notes

Future PRs may implement machine-readable checks for this boundary only if they
preserve the PULSEmech authority boundary.

Possible future work includes:

- public/private artifact classifier;
- public status redaction review;
- public Pages artifact manifest;
- private audit bundle manifest;
- restricted-material detection;
- raw detector output classification;
- external evidence publication envelope;
- reference package public-exposure check;
- public artifact staleness marker;
- local path exposure scanner;
- reader-surface authority wording check.

Executable implementations must include regression tests.

Publication checks must fail closed when classification or sensitive-content
review is unclear.

## Summary

The public / private artifact boundary separates release-authority role from
publication exposure.

Release authority is determined by the PULSEmech authority path.

Publication exposure is determined by artifact role, release-state relation,
sensitive content, operational metadata, reproducibility value, and reader
surface risk.

Public artifacts do not become authority by being public.

Private artifacts do not lose release relevance by being private.

Reader surfaces do not authorize release.

Unclear publication classification remains non-public until reviewed.
