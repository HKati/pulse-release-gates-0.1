# PULSEmech / SLSA Provenance-to-Transition Alignment v0

## Status

Technical alignment note.

This document defines a technical mapping between SLSA / in-toto-style provenance statements and the PULSEmech release-transition decision model.

The document is non-normative. It does not define SLSA conformance, certification, or compliance status.

## Abstract

SLSA provenance records verifiable information about the origin and construction of a software artifact.

PULSEmech evaluates whether a release transition may proceed from a recorded evidence state.

This document describes a two-layer integration model:

```text
SLSA / in-toto provenance layer
→ artifact path, build context, input identity, and execution metadata

PULSEmech transition layer
→ evidence evaluation, policy binding, required gate materialization, verifier replay, and allow/block transition decision
```

In this model, provenance is an input to release-transition evaluation. It is not itself the release-transition decision.

## Terminology

### Artifact

A file, package, evidence bundle, manifest, model, workflow output, or other software object identified by name and digest.

### Provenance statement

An attestation describing how an artifact was produced.

For SLSA build provenance, the statement is expressed as an in-toto Statement with:

```text
_type: https://in-toto.io/Statement/v1
predicateType: https://slsa.dev/provenance/v1
```

### Release evidence

Recorded machine-readable evidence used by PULSEmech to evaluate a release transition.

Examples include:

```text
status.json
release evidence verifier report
materialized required gate set
release authority manifest
artifact provenance binding
attestation envelope
evidence packet
```

### Declared policy

The policy input that defines the required release gates and evaluation conditions for a release decision.

### Materialized required gate set

The workflow-effective set of gates derived from declared policy and the current release context.

### Verifier replay

A deterministic re-evaluation of recorded evidence and required conditions before release-transition evaluation.

### Transition decision

The PULSEmech output indicating whether the release transition is allowed or blocked.

The transition decision is computed from evidence, policy, materialized gates, verifier replay, and fail-closed enforcement.

## Integration model

The integration model has two layers.

### Layer 1: provenance

The provenance layer records artifact origin and build context.

It answers questions such as:

```text
Which artifact is described?
Which digest identifies it?
Which source revision or input artifacts were used?
Which build or workflow produced it?
Which builder identity is associated with the invocation?
Which execution metadata identifies the run?
```

This layer is represented using SLSA / in-toto-style provenance.

### Layer 2: transition evaluation

The transition layer evaluates whether the artifact and its evidence package satisfy the release policy.

It answers questions such as:

```text
Is the release evidence present?
Is the evidence bound to the expected artifacts?
Is the declared policy known?
Is the required gate set materialized?
Did verifier replay pass?
Did all required gates pass?
Should the transition be allowed or blocked?
```

This layer is represented using a PULSEmech release-transition decision predicate.

## Data flow

```text
source revision / input artifacts
→ workflow or build execution
→ artifact output
→ SLSA / in-toto provenance statement
→ PULSEmech evidence packet
→ declared policy
→ materialized required gate set
→ verifier replay
→ transition decision
```

The PULSEmech transition decision may consume a verified provenance statement as one evidence input.

The decision remains separate from the provenance statement.

## Separation of concerns

SLSA-style provenance describes the artifact path.

PULSEmech evaluates the release transition.

The two layers should remain separate for clarity and reviewability.

```text
provenance statement
≠ transition decision
```

A valid provenance statement may be necessary evidence for a release transition.

It is not sufficient by itself unless the PULSEmech policy and gate conditions also pass.

## Interface requirements

A PULSEmech / SLSA integration should preserve the following interface requirements.

### Stable artifact identity

Every evidence-bearing artifact should be identified by:

```text
name
digest
```

Digest-bearing references are preferred over free-form descriptions.

### Bound policy input

The declared policy should be treated as an input artifact where possible.

The policy should be referenced by digest when it contributes to the release decision.

### Bound evidence inputs

Evidence files used by the PULSEmech verifier should be referenced by digest.

Typical evidence inputs include:

```text
status.json
release evidence verifier report
materialized required gates
release authority manifest
artifact provenance binding
attestation envelope
```

### Explicit execution identity

Workflow or build execution should include an invocation identifier.

For GitHub Actions, this can be represented by a run URL or run identifier.

### Builder boundary

The builder identity should identify the build platform or workflow boundary used for evidence construction.

The builder boundary should be documented separately from the transition decision.

### Separate predicate namespaces

SLSA provenance and PULSEmech transition decisions should use separate predicate types.

SLSA build provenance uses:

```text
https://slsa.dev/provenance/v1
```

A PULSEmech transition predicate should use a project-specific namespace until a reviewed external predicate exists.

Example draft namespace:

```text
https://eplabsai.org/pulsemech/release-transition/v0
```

## Layer 1 example: SLSA-style provenance statement

The following JSON is an illustrative SLSA-style provenance statement.

It describes construction of an evidence-binding artifact.

It is not a complete conformance assessment.

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    {
      "name": "release-authority-artifact-binding-v0.json",
      "digest": {
        "sha256": "<full-64-hex-sha256>"
      }
    }
  ],
  "predicateType": "https://slsa.dev/provenance/v1",
  "predicate": {
    "buildDefinition": {
      "buildType": "https://eplabsai.org/buildtypes/pulsemech-release-authority/v0",
      "externalParameters": {
        "repository": "https://github.com/HKati/pulse-release-gates-0.1",
        "ref": "refs/heads/main",
        "workflow": ".github/workflows/pulse_ci.yml"
      },
      "resolvedDependencies": [
        {
          "name": "source-revision",
          "uri": "git+https://github.com/HKati/pulse-release-gates-0.1@<commit>",
          "digest": {
            "gitCommit": "<git-commit-sha>"
          }
        },
        {
          "name": "declared-gate-policy",
          "uri": "pulse_gate_policy_v0.yml",
          "digest": {
            "sha256": "<full-64-hex-sha256>"
          }
        },
        {
          "name": "recorded-release-evidence",
          "uri": "status.json",
          "digest": {
            "sha256": "<full-64-hex-sha256>"
          }
        },
        {
          "name": "release-evidence-verifier-report",
          "uri": "release_evidence_verifier_report_v0.json",
          "digest": {
            "sha256": "<full-64-hex-sha256>"
          }
        },
        {
          "name": "release-authority-manifest",
          "uri": "release_authority_manifest_v0.json",
          "digest": {
            "sha256": "<full-64-hex-sha256>"
          }
        }
      ]
    },
    "runDetails": {
      "builder": {
        "id": "<documented-builder-id>"
      },
      "metadata": {
        "invocationId": "<workflow-run-id-or-url>",
        "startedOn": "<timestamp>",
        "finishedOn": "<timestamp>"
      }
    }
  }
}
```

## Layer 1 interpretation

The provenance statement binds a concrete artifact to:

```text
source revision
declared policy
recorded release evidence
verifier report
release-authority manifest
workflow invocation
builder boundary
```

This provides a verifiable artifact path.

It does not decide the release transition.

## Layer 2 example: PULSEmech transition decision statement

The following JSON is an illustrative PULSEmech transition decision statement.

It records the decision produced after evidence, policy, gate, and verifier evaluation.

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    {
      "name": "pulse-release-candidate-evidence-packet-v0.json",
      "digest": {
        "sha256": "<full-64-hex-sha256>"
      }
    }
  ],
  "predicateType": "https://eplabsai.org/pulsemech/release-transition/v0",
  "predicate": {
    "policyId": "pulse_gate_policy_v0",
    "releaseRequired": true,
    "decision": "block",
    "transitionOpened": false,
    "decisionReason": "missing_or_incomplete_required_evidence",
    "evidenceInputs": [
      {
        "name": "status.json",
        "digest": {
          "sha256": "<full-64-hex-sha256>"
        }
      },
      {
        "name": "release_evidence_verifier_report_v0.json",
        "digest": {
          "sha256": "<full-64-hex-sha256>"
        }
      },
      {
        "name": "materialized_required_gates_v0.json",
        "digest": {
          "sha256": "<full-64-hex-sha256>"
        }
      },
      {
        "name": "release_authority_manifest_v0.json",
        "digest": {
          "sha256": "<full-64-hex-sha256>"
        }
      }
    ],
    "materializedRequiredGates": [
      "external_summaries_present",
      "recorded_release_evidence_verified",
      "release_authority_manifest_valid"
    ],
    "gateResults": {
      "external_summaries_present": "fail",
      "recorded_release_evidence_verified": "pass",
      "release_authority_manifest_valid": "pass"
    },
    "informationalSurfaces": [
      "readme",
      "dashboard",
      "doi_record",
      "release_note",
      "model_self_report",
      "compliance_form"
    ]
  }
}
```

## Layer 2 interpretation

The transition statement binds the release decision to:

```text
policy identity
required gate set
gate results
evidence inputs
verifier outputs
subject evidence packet
decision result
```

The transition output is explicit:

```text
decision = block
transitionOpened = false
```

The block state is a valid result of the mechanism.

## Allow decision example

An allow decision requires a complete passing evidence path.

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    {
      "name": "pulse-release-candidate-evidence-packet-v0.json",
      "digest": {
        "sha256": "<full-64-hex-sha256>"
      }
    }
  ],
  "predicateType": "https://eplabsai.org/pulsemech/release-transition/v0",
  "predicate": {
    "policyId": "pulse_gate_policy_v0",
    "releaseRequired": true,
    "decision": "allow",
    "transitionOpened": true,
    "decisionReason": "all_materialized_required_gates_passed",
    "materializedRequiredGates": [
      "external_summaries_present",
      "recorded_release_evidence_verified",
      "release_authority_manifest_valid"
    ],
    "gateResults": {
      "external_summaries_present": "pass",
      "recorded_release_evidence_verified": "pass",
      "release_authority_manifest_valid": "pass"
    }
  }
}
```

## Block decision example

A block decision records that the transition was not authorized.

```json
{
  "_type": "https://in-toto.io/Statement/v1",
  "subject": [
    {
      "name": "pulse-release-candidate-evidence-packet-v0.json",
      "digest": {
        "sha256": "<full-64-hex-sha256>"
      }
    }
  ],
  "predicateType": "https://eplabsai.org/pulsemech/release-transition/v0",
  "predicate": {
    "policyId": "pulse_gate_policy_v0",
    "releaseRequired": true,
    "decision": "block",
    "transitionOpened": false,
    "decisionReason": "required_gate_failed_or_missing",
    "failedOrMissingGates": [
      "external_summaries_present"
    ]
  }
}
```

## Transition evaluation semantics

A PULSEmech implementation may evaluate the transition as follows:

```text
Input:
  artifact provenance statement
  evidence packet
  declared policy
  materialized required gate set
  verifier report
  release-authority manifest

Procedure:
  verify artifact identity
  verify evidence digests
  load declared policy
  materialize required gate set
  replay verifier
  evaluate gate results
  emit transition decision

Decision:
  allow  if all required conditions pass
  block  otherwise
```

A missing, stale, unverifiable, or policy-incomplete evidence state results in a block decision.

## Provenance as evidence input

SLSA-style provenance should be treated as evidence input.

It can support release-transition evaluation by providing:

```text
artifact identity
source revision
workflow identity
build context
builder boundary
execution metadata
input artifact references
```

PULSEmech can consume this information during evidence evaluation.

The transition decision remains a separate PULSEmech output.

## Recommended artifact boundaries

The following artifacts are suitable candidates for digest-bound references.

```text
status.json
materialized_required_gates_v0.json
release_evidence_verifier_report_v0.json
release_authority_manifest_v0.json
artifact_provenance_binding_v0.json
external_summary_attestation_v1.json
pulse_release_candidate_evidence_packet_v0.json
```

The exact artifact list should be derived from the active PULSEmech implementation and policy.

## Recommended predicate separation

Use separate statements for separate claims.

```text
Statement A:
SLSA / in-toto provenance
describes artifact construction and input identity.

Statement B:
PULSEmech release-transition decision
describes evidence evaluation and allow/block result.
```

This separation improves reviewability.

It also prevents release-transition semantics from being embedded into generic build provenance fields.

## Avoiding parameter overloading

PULSE-specific policy and gate information should not be placed into SLSA `externalParameters` unless it is part of the build interface.

Prefer digest-bound artifacts in `resolvedDependencies` for:

```text
policy
gate set
evidence packet
verifier report
release-authority manifest
```

The PULSEmech transition predicate should contain the release-decision semantics.

## Consumer verification model

A consumer verifying the combined model should perform two checks.

### Provenance check

```text
verify in-toto statement envelope
verify subject digest
verify predicateType
verify builder boundary
verify source revision
verify resolved dependencies
```

### PULSEmech transition check

```text
verify evidence packet digest
verify policy identity
verify materialized required gate set
verify verifier replay output
verify gate results
verify decision field
verify transitionOpened field
```

The consumer should treat `allow` and `block` as explicit outputs.

A `block` output is not an execution failure. It is a release-transition result.

## AI-assisted workflow relevance

AI-assisted development and agent workflows can generate software artifacts, patches, summaries, tests, and release materials.

The existence of generated output is not equivalent to release-transition authorization.

PULSEmech separates artifact production from transition authorization.

```text
generated artifact
→ provenance and evidence evaluation
→ transition decision
```

This separation is especially relevant when automated systems can produce changes faster than humans can manually inspect the full evidence path.

## Informational surfaces

Informational surfaces may describe or summarize evidence.

Examples:

```text
README
dashboard
release note
publication page
status page
metadata record
summary page
```

These surfaces are not the transition decision.

They may reference the decision.

They may help readers understand the decision.

They do not replace the evidence path, verifier replay, or gate evaluation.

## Review questions for SLSA / OpenSSF practitioners

The following questions are suitable for technical review.

```text
1. Should PULSEmech be described as a provenance consumer pattern?
2. Should the transition decision be represented as a separate in-toto predicate?
3. Which PULSEmech artifacts should be referenced as SLSA resolvedDependencies?
4. Which PULSEmech artifacts should remain inside the PULSE transition predicate?
5. What builder.id boundary is appropriate for GitHub Actions-based evidence construction?
6. Should the provenance statement and transition decision statement be signed separately?
7. What consumer verification procedure should be documented for combined provenance and transition evaluation?
8. Which terminology best separates artifact provenance from release-transition authorization?
```

## Proposed community question

```text
Title:
Where should a fail-closed, artifact-bound release-transition mechanism sit relative to SLSA provenance verification?

Body:
PULSEmech is a developer-side mechanism for evaluating AI-assisted software release transitions.

It uses recorded release evidence, declared gate policy, materialized required gates, verifier replay, artifact provenance binding, and CI enforcement to produce an allow/block transition decision.

We are evaluating how to represent the relationship between:

1. SLSA / in-toto provenance for artifact construction, and
2. a PULSEmech release-transition decision predicate for policy and evidence evaluation.

The proposed model keeps these as separate layers:

SLSA provenance describes the artifact path.
PULSEmech evaluates whether the release transition may open.

We would appreciate guidance on predicate separation, builder identity, resolved dependency boundaries, and consumer verification terminology.
```

## Acknowledgement

The initial JSON bridge example that motivated this document was produced during a Lumen-assisted workshop step.

That example is treated as a conceptual input to this alignment note.

## References

```text
SLSA v1.2 — Provenance
https://slsa.dev/spec/v1.2/provenance

SLSA v1.2 — Build Provenance
https://slsa.dev/spec/v1.2/build-provenance

in-toto Attestation — Statement v1
https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md
```

## Summary

This document defines a technical alignment between artifact provenance and release-transition evaluation.

The integration model is:

```text
SLSA / in-toto provenance
→ artifact path evidence

PULSEmech
→ policy-bound transition evaluation
→ allow/block decision
```

The two layers are complementary and should remain separately reviewable.
