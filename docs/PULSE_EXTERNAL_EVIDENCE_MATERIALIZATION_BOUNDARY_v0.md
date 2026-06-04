# PULSE External Evidence Materialization Boundary v0

## Purpose

This document defines the v0 materialization boundary for detector and external
evidence in PULSE.

It defines when detector output, external summaries, external evidence packets,
or third-party verification material may be reviewed as materialized release
evidence.

It does not change PULSEmech release authority.

It does not add gates.

It does not change policy.

It does not change schemas.

It does not change CI behavior.

It does not modify `check_gates.py`.

It does not make detector or external evidence normative by itself.

It defines review requirements for determining whether external evidence may
participate in a release-grade materialized lane.

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

External evidence does not authorize release by presence.

Detector output does not authorize release by presence.

External summaries do not authorize release by filename, metric key, directory
location, dashboard visibility, Pages publication, or report inclusion.

External evidence can participate in release review only when it is recorded,
parseable, subject-bound, freshness-bound, mapped through declared rules, and
connected to the PULSEmech authority path through declared policy, materialized
gates, and strict CI enforcement.

## Scope

This v0 document is definitional.

It may be used for review, hardening planning, external evidence boundary
classification, detector materialization planning, and future implementation
alignment.

It does not assert that current detector or external evidence handling satisfies
release-grade materialization requirements.

It does not define a production external evidence policy.

It does not select required detectors.

It does not select required external evidence sources.

It does not define signer requirements.

It does not define attestation requirements.

It defines the boundary conditions that future executable checks must preserve.

## Core distinction

PULSE separates:

```text
external evidence presence
```

from:

```text
external evidence materialization
```

Presence means that a file, summary, report, metric, detector output, or external
packet exists.

Materialization means that the evidence is recorded, parseable, subject-bound,
freshness-bound, mapped through declared rules, and folded into release-state
review through the declared PULSE path.

Presence is not materialization.

Materialization is not release permission.

Release permission remains produced only by strict fail-closed CI enforcement
under the PULSEmech authority path.

## Evidence materialization model

The v0 model is:

```text
external evidence source
→ recorded evidence artifact
→ parseable evidence structure
→ evidence identity
→ subject binding
→ freshness / run binding
→ declared mapping rule
→ status or gate fold-in
→ materialized required gate
→ strict fail-closed CI enforcement
→ allow/block release decision
```

This model is a review model.

It does not replace PULSEmech.

It defines when external evidence may support release-grade lane eligibility.

## Definitions

### Detector evidence

Detector evidence is output produced by a detector, checker, analyzer, scan,
model evaluation, external validation process, or release-adjacent tool.

Detector evidence may be internal or external.

Detector evidence may be advisory, diagnostic, shadow, experimental, or
release-required depending on declared policy and materialization state.

### External evidence

External evidence is evidence produced outside the immediate PULSE authority
path or imported into it from an external tool, package, verifier, scanner,
detector, artifact store, or third-party review process.

External evidence may include:

- detector summaries;
- external scan summaries;
- artifact verification packets;
- package verification outputs;
- signed attestations;
- external metrics;
- third-party review results;
- external reproducibility reports;
- release reference package verification output.

External evidence is not release authority by presence.

### Evidence artifact

An evidence artifact is the recorded file or package carrying detector or
external evidence.

An evidence artifact may be JSON, JSONL, Markdown, HTML, SARIF, JUnit XML,
attestation, package manifest, digest file, or another recorded form.

Only structured and reviewable evidence may support materialization.

### Evidence identity

Evidence identity is the recorded identity of an evidence artifact or source.

Evidence identity may include:

- source name;
- source type;
- schema identifier;
- producer;
- tool version;
- run identity;
- commit identity;
- artifact digest;
- created timestamp;
- subject artifact path;
- subject artifact digest;
- package identity;
- attestation subject;
- signer or issuer identity when required.

### Subject binding

Subject binding is the connection between evidence and the artifact, run,
commit, package, model, release candidate, or release-state relation that the
evidence claims to evaluate.

Evidence without subject binding is diagnostic context only.

Subject binding may be established through recorded identifiers such as commit
identity, run identity, artifact digest, package manifest identity, release tag,
or attestation subject.

### Freshness binding

Freshness binding is the connection between evidence time and the release-state
context it claims to support.

Freshness may be established through created timestamps, run identity, commit
identity, release tag, workflow identity, attestation timestamp, package
timestamp, or other declared freshness mechanism.

Freshness requirements must be declared before they can be enforced.

Stale evidence cannot support release-grade materialization when freshness is
required by policy or review rule.

### Declared mapping rule

A declared mapping rule defines how recorded detector or external evidence maps
into PULSE status, gates, summaries, or release-state review.

A mapping rule must identify:

- accepted evidence source or class;
- accepted schema or structure;
- subject binding requirement;
- freshness requirement when applicable;
- success / failure interpretation;
- fail-closed behavior;
- target status or gate field when folded into release state.

A filename pattern alone is not a declared mapping rule.

### Fold-in

Fold-in is the deterministic process by which recorded external evidence is
mapped into a status field, gate value, evidence inventory, release-state
relation, or materialized lane review.

Fold-in must be deterministic and reviewable.

Fold-in must not convert unrecognized, malformed, stale, unbound, or
advisory-only evidence into release permission.

### Materialized external evidence

External evidence is materialized only when it satisfies all required identity,
structure, subject binding, freshness, mapping, and fold-in requirements for the
declared lane.

Materialized external evidence may support a materialized gate or release-grade
lane review.

Materialized external evidence does not authorize release by itself.

### Advisory external evidence

Advisory external evidence may inform review but does not satisfy required
release evidence unless declared policy, materialized gates, and strict CI
enforcement bind it into the release-authority path.

Advisory evidence cannot create release permission.

### Diagnostic external evidence

Diagnostic external evidence may help explain state, mismatch, drift, stale
output, detector behavior, or review context.

Diagnostic evidence cannot satisfy release-required gates.

## Minimum materialization requirements

Detector or external evidence may be reviewed as materialized release evidence
only when all of the following requirements are satisfied.

### 1. Recorded evidence artifact

The evidence must exist as a recorded artifact.

The artifact must be addressable and reviewable.

The artifact must not be inferred from prose, dashboard state, badge state,
filename presence, directory presence, or report text alone.

### 2. Parseable structure

The evidence artifact must parse according to its expected structure.

If a schema is declared, the evidence must satisfy the schema.

If no schema is declared, the evidence remains diagnostic or advisory unless a
review rule explicitly permits the structure.

Malformed evidence fails closed when it is release-required.

### 3. Recognized source or declared source class

The evidence source must be recognized or explicitly declared.

A file matching a broad summary pattern is not sufficient.

An unrecognized external file must remain diagnostic context until mapped by a
declared rule.

### 4. Evidence identity

The evidence must carry enough identity to be reviewed.

At minimum, release-grade external evidence should identify:

- evidence source;
- evidence subject;
- run, commit, package, or artifact identity;
- created timestamp or equivalent freshness marker;
- success / failure semantics;
- artifact digest or equivalent subject binding when required.

Missing identity fails closed when the evidence is release-required.

### 5. Subject binding

The evidence must be bound to the release-state subject it evaluates.

The subject may be a commit, run, release candidate, artifact, package, model,
detector input, or release-state relation.

Evidence whose subject cannot be matched to the release context remains
diagnostic context only.

Subject mismatch fails closed when the evidence is release-required.

### 6. Freshness or run binding

The evidence must be fresh enough for the declared release context.

Freshness may be determined by run identity, commit identity, created timestamp,
release tag, package identity, attestation timestamp, or declared policy.

Missing or stale freshness binding fails closed when freshness is required.

### 7. Declared mapping rule

The evidence must be mapped by a declared rule before it can affect status or
gate state.

The rule must define what counts as pass, fail, missing, stale, malformed, or
inconclusive.

The rule must define fail-closed behavior.

Filename presence alone is not a mapping rule.

### 8. Deterministic fold-in

Fold-in must be deterministic.

The same recorded evidence and declared rule must produce the same status or
gate result.

Fold-in must not depend on uncontrolled order, arbitrary filenames, ambiguous
metric keys, or implicit success defaults.

### 9. Literal gate value when release-required

If external evidence supports a required gate, the resulting gate value must be a
literal boolean value in the recorded status state.

Only literal `true` can satisfy a required gate.

Missing, null, non-boolean, false, string, numeric, object, array, stale,
malformed, or inconclusive values do not satisfy required gates.

### 10. Strict CI enforcement

If detector or external evidence is release-required, strict CI must enforce the
materialized result.

CI must not ignore missing, malformed, stale, unbound, inconclusive, or failed
external evidence when the evidence is required.

## Non-materialized conditions

Detector or external evidence is not materialized when any of the following
conditions hold:

```text
evidence exists only as prose
evidence exists only as dashboard state
evidence exists only as badge state
evidence exists only as filename presence
evidence exists only as directory presence
evidence artifact is missing
evidence artifact is malformed
evidence artifact has no recognized source
evidence artifact has no declared mapping rule
evidence artifact has no subject binding
evidence artifact has stale or missing freshness binding when freshness is required
evidence artifact is advisory-only
evidence artifact is diagnostic-only
evidence artifact has ambiguous metric semantics
evidence artifact has unrecognized metric keys
evidence artifact is not folded into status or gate state by a declared rule
fold-in depends on uncontrolled filename order
fold-in treats unknown summaries as success
fold-in creates success from absence of known failures
fold-in creates `external_all_pass=true` without recognized materialized evidence
required evidence does not produce literal boolean true for the required gate
CI does not enforce the materialized result
```

Non-materialized evidence may remain useful for diagnostics or audit.

It cannot support release permission.

## External summary boundary

External summary files may support release review only when their source,
schema, subject, freshness, and mapping rule are declared.

A summary filename pattern such as:

```text
*_summary.json
*_summary.jsonl
```

is not sufficient by itself.

A summary file must not satisfy a release-required external evidence gate merely
because it exists.

A summary file with generic metric keys must not be treated as release-grade
evidence unless the keys are recognized by a declared mapping rule.

Unknown summary files must not produce success by default.

Malformed summary files fail closed when external evidence is required.

Recognized summary files may be advisory, diagnostic, shadow, or
release-required depending on declared policy and fold-in rules.

## External all-pass boundary

A gate or status field representing aggregate external evidence success must not
be set to literal `true` unless recognized required evidence has been
materialized.

An aggregate external pass value must not be inferred from:

```text
presence of at least one summary file
absence of recognized detector rows
absence of known failures
unknown metric keys
unrecognized detector names
advisory-only evidence
diagnostic-only evidence
```

An aggregate external pass value may be literal `true` only when the declared
required evidence set is known, each required evidence item is materialized, and
the declared fold-in rule evaluates all required evidence as passing.

If the required evidence set is unknown, empty by error, unresolved, or
unmaterialized, the aggregate value must fail closed.

## Detector materialization boundary

Detector evidence may support release-grade materialization only when the
detector output is recorded, parseable, source-identified, subject-bound,
freshness-bound when required, and mapped into gate or status state by a declared
rule.

A detector run is not materialized merely because:

```text
a detector tool exists
a detector summary file exists
a detector name appears in a report
a detector dashboard shows success
a detector result is mentioned in prose
a detector output is present but unmapped
```

Detector materialization requires evidence-to-release-state binding.

## Required external evidence failure modes

Required external evidence fails closed under the following conditions:

```text
required external evidence artifact missing
required external evidence artifact malformed
required external evidence source unrecognized
required external evidence schema missing when schema is required
required external evidence schema invalid
required external evidence subject missing
required external evidence subject mismatch
required external evidence freshness missing when freshness is required
required external evidence stale
required external evidence signer or issuer missing when signer is required
required external evidence digest missing when digest is required
required external evidence digest mismatch
required external evidence declared mapping missing
required external evidence fold-in inconclusive
required external evidence advisory-only
required external evidence diagnostic-only
required external evidence not folded into status or required gate state
```

Any unclear required external evidence state remains fail-closed.

## Advisory and diagnostic handling

Advisory and diagnostic external evidence may be recorded and reviewed.

Advisory and diagnostic evidence may appear in reports, ledgers, audit bundles,
external verification packets, or reader surfaces.

Advisory and diagnostic evidence must not be treated as satisfying required
release evidence.

Advisory and diagnostic evidence may become release-relevant only if a future
declared policy explicitly binds it through materialized gates and strict CI
enforcement.

## Public / private exposure boundary

External evidence may contain sensitive material.

Before publication, external evidence must be classified under the public /
private artifact boundary.

External evidence must remain private, withheld, or sanitized if it contains:

- secrets;
- credentials;
- tokens;
- private URLs;
- private personal data;
- private prompts;
- private model outputs;
- unredacted logs;
- private artifact-store references;
- undisclosed vulnerability details;
- operational metadata not required for public reproducibility.

Publication status does not create materialization.

Private retention does not remove release relevance.

## Relationship to release-grade materialized lane

The release-grade materialized lane defines when a recorded run is structurally
eligible for release-grade review.

External evidence materialization defines when detector or external evidence may
support that eligibility.

A release-grade materialized lane cannot rely on external evidence that is
missing, malformed, stale, subject-mismatched, advisory-only, diagnostic-only, or
unmapped.

If external evidence is required by policy, missing or non-materialized external
evidence fails closed.

## Relationship to relational state transition layer

The relational state transition layer defines how state, relation, evidence
binding, mechanical effect, and decision transition remain connected above the
PULSEmech authority path.

External evidence materialization supplies review requirements for the evidence
binding part of that relation when the evidence comes from detector or external
sources.

External evidence must be connected to the recorded release-state relation
before it can participate in a decision transition.

## Relationship to public / private artifact boundary

The public / private artifact boundary defines whether artifacts may be public,
private, or restricted.

External evidence materialization defines whether detector or external evidence
is sufficiently recorded, bound, fresh, and mapped to support release-state
review.

Publication exposure and materialization are separate classifications.

A public external evidence artifact is not materialized by being public.

A private external evidence artifact may still be materialized if it is recorded,
bound, mapped, and enforced through the PULSEmech authority path.

## Relationship to security threat model

The security threat model classifies external evidence, verifier trust
boundaries, path traversal, symlink escape, supply-chain compromise, forged
verified packets, and semantic bypass as relevant PULSE security risks.

This document defines the materialization boundary that prevents semantic bypass
through filename presence, generic metrics, unknown summaries, advisory
evidence, or unmapped external input.

## Review sequence v0

A detector or external evidence materialization review follows this sequence.

### 1. Identify evidence source

Identify the detector, scanner, verifier, package, third-party process, or
external system that produced the evidence.

If the source is unknown and no declared rule maps it, the evidence remains
diagnostic context only.

### 2. Identify evidence artifact

Identify the recorded evidence artifact.

If no recorded artifact exists, the evidence is not materialized.

### 3. Parse evidence

Parse the evidence according to the expected structure.

If parsing fails and the evidence is release-required, the review fails closed.

### 4. Validate schema when declared

If a schema is declared, validate the evidence against that schema.

If schema validation fails and the evidence is release-required, the review
fails closed.

### 5. Verify subject binding

Verify that the evidence subject matches the release-state subject.

If the subject is missing, mismatched, or unreviewable and the evidence is
release-required, the review fails closed.

### 6. Verify freshness binding

Verify freshness or run binding when required.

If freshness is missing, stale, or unreviewable and the evidence is
release-required, the review fails closed.

### 7. Resolve mapping rule

Resolve the declared mapping rule for the evidence source and lane.

If no declared mapping rule exists, the evidence remains diagnostic or advisory
context only.

### 8. Apply deterministic fold-in

Apply the declared fold-in rule.

The rule must not treat unknown, missing, malformed, stale, advisory-only, or
diagnostic-only evidence as pass.

### 9. Verify gate materialization

If the evidence supports a required gate, verify that the gate value is present
in recorded status state and is literal boolean `true`.

If not, the review fails closed.

### 10. Verify strict CI enforcement

Confirm that strict CI enforcement checks the materialized required gate.

If CI does not enforce the result, the evidence does not support release
permission.

## Fail-closed conditions

External evidence materialization fails closed when any of the following
conditions hold for release-required evidence:

```text
evidence artifact missing
evidence artifact malformed
evidence schema invalid when schema is declared
evidence source unrecognized
subject binding missing
subject binding mismatched
freshness binding missing when required
evidence stale
declared mapping rule missing
fold-in rule missing
fold-in result inconclusive
fold-in treats unknown evidence as success
fold-in treats absence of failure as success
required evidence set unresolved
required evidence set empty by error
aggregate pass computed from filename presence only
aggregate pass computed from advisory-only evidence
aggregate pass computed from diagnostic-only evidence
required gate missing
required gate not literal boolean true
CI does not enforce the required gate
```

Any unclear release-required external evidence state remains fail-closed.

## Non-goals

This document does not define a detector registry.

It does not select required detectors.

It does not define a production external evidence policy.

It does not define signer or attestation requirements.

It does not define external summary schemas.

It does not change existing external summary ingestion.

It does not change `augment_status.py`.

It does not change `check_external_summaries_present.py`.

It does not change CI workflows.

It does not add gates.

It does not change schemas.

It does not create a second release-decision engine.

## Future implementation notes

Future PRs may implement machine-readable checks for this boundary only if they
preserve the PULSEmech authority path.

Possible future work includes:

- external evidence source registry;
- external evidence envelope schema;
- external summary schema;
- subject-binding validation;
- freshness validation;
- signer or issuer verification when required;
- deterministic fold-in rule registry;
- known detector source mapping;
- aggregate external pass guard;
- advisory / diagnostic / release-required classification;
- external evidence inventory artifact;
- release-grade external evidence checker.

Executable implementations must include regression tests.

Checks must fail closed for release-required evidence when materialization is
missing, malformed, stale, unbound, unresolved, advisory-only, diagnostic-only,
or inconclusive.

## Summary

External evidence materialization requires more than file presence.

Detector output, external summaries, external packets, and third-party review
material may support release-grade review only when they are recorded,
parseable, source-identified, subject-bound, freshness-bound when required,
mapped by declared rules, folded into status or gate state deterministically, and
enforced by strict CI when release-required.

Presence is not materialization.

Materialization is not release permission.

Release permission remains produced only by the PULSEmech authority path.
