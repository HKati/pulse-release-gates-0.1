# PULSE-COMPUTE Pre-Comparison Admission Boundary v0

- Status: boundary note
- Normative status: non-normative clarification
- Implementation status: research / shadow-only direction
- Scope: learned labels, classifier outputs, pattern matches, compute-admission research boundaries, future routing, future escalation, future blocking, and future decision-authority safeguards

## Current status boundary

This document is not a current compute-admission contract.

This document does not implement compute admission.

This document does not implement routing.

This document does not implement escalation.

This document does not implement blocking.

This document does not create policy.

This document does not materialize compute gates.

This document does not change release authority.

This document records a future PULSE-COMPUTE boundary: learned labels and classifier outputs may be diagnostic signals, but they must not be treated as decision authority without comparison against the actual mechanism and a separately declared, implemented, tested, and reviewed compute-admission path.

Any future normative implementation requires separate schema, checker, policy, gate, enforcement, and review work.

This document uses boundary language such as `must`, `must not`, and `required path` to describe the intended future PULSE-COMPUTE safety boundary. Those words do not mean that this document is already an implemented compute-admission contract.

## Core statement

PULSE-COMPUTE treats learned labels as diagnostic signals only.

A learned label is not truth.

A trained classification is not evidence.

A familiar pattern is not authority.

No learned label may create compute admission, routing, escalation, blocking, or decision authority before comparison against the actual mechanism and a separately declared implementation path.

## Boundary

```text
learned pattern ≠ truth
trained classification ≠ evidence
familiar label ≠ authority
classifier output ≠ compute-admission decision
model confidence ≠ verified mechanism
text similarity ≠ compute decision
jailbreak label ≠ jailbreak proof
```

A learned label may be useful.

A learned label may be a warning.

A learned label may be a diagnostic signal.

A learned label may trigger inspection.

A learned label may request evidence.

The label must not be treated as decision authority.

## Pre-comparison exclusion rule

Before comparison, a learned label must not create or enable:

- compute admission;
- compute routing;
- escalation;
- blocking;
- priority assignment;
- rejection;
- access removal;
- release authority;
- access authority;
- trust;
- trusted evidence;
- verified evidence;
- relation satisfaction;
- gate materialization;
- policy execution;
- final decision authority.

This applies even when the learned label looks familiar, high-confidence, repeated, inherited, or historically accepted.

## Required transition path

The intended future PULSE-COMPUTE path is:

```text
learned pattern
→ label
→ comparison
→ recorded evidence
→ declared compute policy
→ materialized compute gates
→ allow / block / escalate / route
```

A label that has not passed through comparison remains diagnostic.

It is not a compute-admission decision.

## Comparison requirement

Comparison means the learned label must be checked against the actual operational mechanism.

The system must ask:

- What artifact, behavior, state, or relation produced the label?
- What evidence records the observed mechanism?
- What policy defines the compute-admission consequence?
- What gate materializes that policy?
- What enforcement path applies the allow / block / escalate / route outcome?
- Is the label still valid after relation to the actual mechanism is checked?

Without this comparison, the system may repeat a learned error as if it were knowledge.

## Text-to-label shortcut boundary

The primary failure path this boundary prevents is:

```text
text / prompt
→ learned label
→ decision
```

This shortcut is forbidden as a future compute-admission design pattern.

A model may label a prompt, artifact, user action, tool path, or output as:

```text
sharp
unsafe
jailbreakable
not authorized
not suitable
approved
trusted
untrusted
```

The label may be useful as a diagnostic signal.

The label may trigger inspection.

The label may request evidence.

The label must not be treated as decision authority.

The required PULSE-COMPUTE path is:

```text
text / prompt / pattern
→ learned label
→ comparison against mechanism
→ recorded evidence
→ declared compute policy
→ materialized compute gates
→ allow / block / escalate / route
```

Without comparison, the system may repeat a learned error as if it were knowledge.

A learned label can become usable only after it has been compared with the actual mechanism and bound to a declared decision path.

## Jailbreak-label boundary

A `jailbreakable` label is not proof of jailbreak.

A `jailbreak` suspicion is not verified evidence.

A prompt that resembles a known jailbreak pattern is not automatically an unauthorized transition.

A jailbreak label may trigger review, but it must not directly create:

- compute blocking;
- access removal;
- escalation;
- routing denial;
- trust removal;
- release authority;
- final decision authority.

The safe path is:

```text
prompt / text / interaction
→ jailbreak label
→ mechanism comparison
→ artifact-bound evidence
→ declared compute policy
→ materialized compute gate
→ allow / block / escalate / route
```

The system must ask:

- What actual mechanism was crossed?
- What artifact records the behavior?
- What boundary was violated?
- What evidence proves the violation?
- What policy applies?
- What gate materializes the consequence?
- What fail-closed enforcement path applies the decision?

If those links are missing, the label remains diagnostic.

It cannot become a decision.

## Reported access-cutoff pattern

A reported access-cutoff pattern can be summarized mechanically as:

```text
model is said to be jailbreakable
→ learned or asserted risk label
→ access / compute decision
```

PULSE-COMPUTE treats that as an unsafe shortcut.

The safer interpretation is:

```text
model is said to be jailbreakable
→ diagnostic risk label
→ comparison against actual mechanism
→ artifact-bound evidence
→ declared compute policy
→ materialized compute gates
→ decision
```

The failure is not that a model can learn a bad pattern.

The failure is allowing a learned or asserted pattern to become a decision without comparison.

PULSE-COMPUTE blocks that shortcut as an intended future compute-admission boundary.

## Learned labels covered by this boundary

This boundary applies to labels such as:

```text
sharp
unsafe
not authorized
not suitable
approved
jailbreakable
high risk
low risk
benign
malicious
trusted
untrusted
safe
blocked
allowed
```

The exact label name does not matter.

If the label is learned, inferred, pattern-matched, classifier-produced, or inherited from training, it must remain diagnostic until compared with the actual mechanism and bound to a declared decision path.

## Learned truth is not truth

PULSE-COMPUTE does not treat learned truth as truth.

A learned statement may become usable only after it has been compared to the actual mechanism and attached to the verified decision path.

Until then, it remains:

```text
diagnostic signal only
```

It may inform review.

It may trigger inspection.

It may request evidence.

It may not decide.

## Decision problem

If inherited authority is enough to permit a trial operation, then decision-makers do not need to understand the operation; they only guard the gate.

This is a mechanical decision failure.

In slower systems, time could hide non-understanding because consequences arrived later.

In AI systems, time increasingly behaves as impact: the consequence of a misclassified or unexamined decision can propagate quickly through compute, routing, automation, and downstream trust.

Therefore:

```text
decision timestamp ≠ decision authority
learned label ≠ decision authority
comparison path → evidence → policy → gate → decision
```

## PULSE-COMPUTE relation to time / impact

This note does not make a physical claim about time.

It records a PULSE-COMPUTE operational boundary.

Clock time measures when a label appeared.

Impact shows what the label does in the system.

A classifier label can become dangerous when it is treated as reality before comparison.

The operational boundary is:

```text
clock timestamp ≠ compute-admission authority
label appearance ≠ verified mechanism
impact must be checked through relation
```

## Compute-admission rule

Compute admission must be based on a declared and materialized path, not on a raw learned label.

Allowed diagnostic path:

```text
classifier output
→ diagnostic signal
→ evidence request
→ comparison against mechanism
→ policy evaluation
→ materialized compute gate
→ allow / block / escalate / route
```

Forbidden shortcut:

```text
classifier output
→ allow / block / escalate / route
```

The shortcut is forbidden because it bypasses comparison.

## Examples

### Example: `unsafe`

A model may label content or behavior as `unsafe`.

That label is diagnostic.

Before compute admission or blocking, the system must compare the label to the actual mechanism:

- what behavior was observed;
- what artifact records it;
- what boundary was crossed;
- what policy applies;
- what gate materializes the consequence.

Without that comparison, the system may block a valid path or allow an invalid one.

### Example: `approved`

A system may learn that a source, actor, artifact, or workflow is `approved`.

That learned approval is not authority.

Approval must still be bound to:

```text
recorded evidence
→ declared compute policy
→ materialized compute gates
→ fail-closed enforcement
```

### Example: `jailbreakable`

A system may label a prompt, output, tool path, or artifact as `jailbreakable`.

That label is not proof.

It may trigger inspection.

It may not become blocking authority unless it is compared to the actual transition path and bound to declared policy.

## Non-authority boundary

This boundary note does not create or enable:

- compute admission;
- compute blocking;
- compute routing;
- escalation authority;
- release authority;
- trusted evidence;
- verified evidence;
- relation satisfaction;
- gate materialization;
- status writing;
- policy changes;
- registry changes;
- CI allow/block changes.

This note does not replace any PULSEmech authority path.

This note does not replace a future compute-admission schema.

This note does not replace a future compute-admission checker.

This note does not replace a future compute policy.

This note does not replace future materialized compute gates.

This note does not replace future fail-closed enforcement.

## Relation to PULSEmech

The PULSEmech release-authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ CI allow/block release decision
```

The PULSE-COMPUTE admission path must follow the same principle:

```text
recorded compute evidence
→ declared compute policy
→ materialized compute gates
→ strict fail-closed enforcement
→ allow / block / escalate / route
```

A learned label can enter this path only as diagnostic input.

It cannot replace the path.

## Implementation staging

Any future normative implementation must be staged separately.

A future implementation must define:

- compute-admission schema;
- learned-label diagnostic schema;
- comparison evidence schema;
- compute policy;
- compute gate materialization rules;
- fail-closed enforcement;
- checker behavior;
- builder behavior, if applicable;
- tests proving no label-to-decision shortcut;
- tests proving non-authority boundaries remain closed.

This document alone does not provide those mechanisms.

## Hungarian workshop anchor

```text
A tanult igazság nem igazság.

A tanult címke nem bizonyíték.

A szöveges hasonlóság nem jogosultság.

A jailbreak-címke nem jailbreak-bizonyíték.

Viszonyítás nélkül nem mehet döntésbe.
```

A PULSE-COMPUTE nem azt akadályozza meg, hogy a rendszer rossz mintát tanuljon.

A PULSE-COMPUTE azt akadályozza meg, hogy a rossz minta igazolt döntési úttá váljon.

## Mechanical anchor

```text
The machine must compare before it admits compute.

Learning is not enough.

Comparison binds the learned signal to reality.
```

```text
learned label
→ comparison
→ evidence
→ policy
→ gate
→ decision
```

Without comparison, the system has no verified relation to the mechanism it is acting on.
