# PULSEmech developer-first positioning v0

## Status

Technical positioning note.

This document defines the primary audience and adoption order for PULSEmech.

It does not change workflow behavior, runtime code, gate policy, verifier behavior, materializer behavior, schema behavior, fail-closed CI enforcement, or release-authority semantics.

## Position

PULSEmech is developer-first, evidence-first, and open-mechanism-first.

It should be evaluated first as a developer-side release responsibility mechanism, not as a downstream compliance product.

The primary validation question is not whether PULSEmech can produce an administrative report.

The primary validation question is whether developers and release engineers can use it to bind release transitions to recorded evidence, declared policy, materialized required gates, verifier replay, and fail-closed CI enforcement.

## Primary audience

The first audience for PULSEmech is:

```text
developers
release engineers
AI-agent workflow builders
open-source maintainers
security engineers
evidence-path practitioners
maintainers of automation-heavy repositories
teams that have already seen uncontrolled automation create release risk
```

These users are close to the transition point.

They build, review, merge, package, and release software artifacts.

If they cannot inspect and operate the mechanism, then later organizational adoption will reduce it to a surface-level control.

## Secondary audience

The secondary audience is:

```text
compliance teams
risk-management teams
audit teams
governance teams
procurement reviewers
organizational release-approval groups
```

These groups may consume PULSEmech outputs later.

They are not the first validation layer.

A compliance or audit team can read a PULSEmech decision record, but the mechanism must first be understandable and useful where release transitions are actually created.

## Problem statement

AI-assisted development increases the speed and volume of generated software artifacts.

Automated systems can produce:

```text
code
patches
configuration changes
tests
summaries
release notes
documentation
deployment suggestions
review comments
```

Artifact production is not release authorization.

PULSEmech separates production from transition authorization.

A generated artifact may exist.

A workflow may complete.

A report may be rendered.

A summary may be written.

A publication or reader surface may be visible.

None of these is sufficient by itself to open a release transition.

## PULSEmech operating model

PULSEmech evaluates release transitions through a connected evidence path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ materialized required gate set
→ verifier replay
→ fail-closed CI enforcement
→ allow/block release-transition decision
```

The mechanism is intended to make the transition boundary explicit.

The release decision is not derived from a narrative claim, model self-report, dashboard, reader surface, or administrative declaration.

It is derived from recorded artifacts and deterministic enforcement.

## Developer-side responsibility mechanism

PULSEmech is designed to make release responsibility visible at the development boundary.

A developer-side responsibility mechanism should allow maintainers to answer:

```text
What evidence exists?
Which policy was applied?
Which gates were required?
Which gates passed?
Which gates failed or were missing?
Which verifier replay was used?
Which CI path enforced the decision?
Was the release transition allowed or blocked?
```

The answer should be reproducible from artifacts.

The answer should not depend on trust in a summary page.

## What PULSEmech is

PULSEmech is:

```text
artifact-bound
policy-driven
fail-closed
developer-visible
evidence-based
CI-enforced
reviewable
reproducible from recorded artifacts
```

It is a release-transition mechanism for AI-assisted and automation-heavy software workflows.

## What PULSEmech is not

PULSEmech is not:

```text
a runtime model guardrail
a model behavior guarantee
a dashboard-only status layer
a model self-evaluation claim
a downstream compliance form
a replacement for human code review
a replacement for software supply-chain provenance
a replacement for security review
a generic approval comment
```

It may integrate with other systems, but it does not replace them.

## Relation to compliance

Compliance may later consume PULSEmech outputs.

That is a secondary use.

The first use is operational:

```text
prevent a release transition from opening when required evidence is missing, stale, unverifiable, or policy-incomplete
```

If PULSEmech is introduced first as a compliance artifact, the mechanism can be flattened into a form, checklist, or administrative wrapper.

The adoption order should therefore be:

```text
developer proof
→ repository operation
→ failure-mode examples
→ reproducible evidence path
→ release-transition boundary
→ compliance translation
```

Compliance language should be derived from working developer-side evidence.

It should not replace the mechanism.

## Developer proof path

A developer-facing PULSEmech demonstration should show at least four cases.

### 1. Passing evidence path

```text
evidence present
policy known
required gates materialized
verifier replay passes
CI enforcement passes
transition decision: allow
```

### 2. Missing evidence path

```text
required evidence missing
verifier replay incomplete
required gate fails or is absent
transition decision: block
```

### 3. Reader-surface non-authority

```text
report exists
summary exists
metadata exists
decision artifact missing or incomplete
transition decision: block or not authorized
```

### 4. Automation boundary

```text
AI-assisted workflow produces output
evidence path is incomplete
release transition remains closed
```

These cases should be understandable without organizational compliance interpretation.

## Relation to SLSA and provenance

PULSEmech can consume provenance evidence.

SLSA / in-toto-style provenance can describe artifact construction and artifact path.

PULSEmech evaluates release-transition authorization from provenance, recorded release evidence, declared policy, materialized gates, verifier replay, and CI enforcement.

The two layers are complementary:

```text
provenance layer:
artifact path and build context

PULSEmech layer:
release-transition evaluation
```

The provenance layer can provide evidence.

The PULSEmech layer decides whether the transition may open.

## Relation to open source maintainers

Open-source maintainers often operate with limited time, high automation pressure, and many external contributions.

For them, PULSEmech should be valuable only if it reduces ambiguity at the transition point.

A maintainer should be able to inspect:

```text
the evidence packet
the required gate set
the verifier output
the CI decision
the boundary between informational surfaces and release authority
```

A PULSEmech adoption path that increases administrative burden without clarifying the release transition is a failed adoption path.

## Relation to AI-agent workflows

AI-agent workflows make this boundary more important.

An agent can generate a patch, run tests, summarize results, and propose release actions.

PULSEmech does not evaluate the agent as a personality or authority.

It evaluates the recorded artifacts and transition conditions.

The relevant question is:

```text
Does the recorded evidence satisfy the release-transition policy?
```

not:

```text
Did the agent sound confident?
```

## Minimum developer-facing documentation set

Before compliance-oriented positioning, the repository should provide:

```text
quickstart evidence path
pass example
block example
reader-surface non-authority example
required checks / workflow authority map
recovery ledger
provenance-to-transition alignment
```

These documents make the mechanism reviewable by technical users before it is translated into governance language.

## Adoption order

The recommended adoption order is:

```text
1. developer inspection
2. repository-local evidence path
3. CI-enforced fail-closed transition checks
4. concrete pass/block examples
5. maintainer review practice
6. provenance and supply-chain alignment
7. compliance translation
```

This order prevents the mechanism from being introduced as a surface-level approval system.

## Evaluation criterion

PULSEmech should be evaluated by whether a technical reviewer can answer:

```text
Can I reproduce the transition decision from recorded artifacts?

Can I identify which evidence was required?

Can I identify which gate passed, failed, or was missing?

Can I see where CI enforces the allow/block decision?

Can I distinguish informational surfaces from release authority?

Can I verify that automation did not open a transition without evidence?
```

If the answer is yes, the mechanism is moving in the right direction.

If the answer depends on trust in a report, claim, or organizational statement, the mechanism is not yet sufficiently artifact-bound.

## Summary

PULSEmech should be positioned first as a developer-side release responsibility mechanism.

Its first validation layer is not compliance.

Its first validation layer is reproducible developer operation:

```text
recorded evidence
declared policy
materialized gates
verifier replay
fail-closed CI enforcement
allow/block transition decision
```

Compliance may consume this later.

It should not define it first.
