## Text-to-label shortcut boundary

The primary failure path this boundary prevents is:

```text
text / prompt
→ learned label
→ decision
```

This shortcut is forbidden.

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

The label must not decide.

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

PULSE-COMPUTE blocks that shortcut.

## Core rule

```text
learned label ≠ truth
trained classification ≠ evidence
familiar pattern ≠ authority
jailbreak label ≠ jailbreak proof
text similarity ≠ compute decision
```

No learned label may enter compute admission, routing, escalation, blocking, or decision authority without comparison.

## Mechanical anchor

PULSE-COMPUTE does not prevent the system from learning wrong patterns.

PULSE-COMPUTE prevents wrong patterns from becoming authorized decision paths.

```text
wrong learned pattern
→ diagnostic label only
→ no decision without comparison
```

## workshop anchor

```text
A tanult igazság nem igazság.

A tanult címke nem bizonyíték.

A szöveges hasonlóság nem jogosultság.

A jailbreak-címke nem jailbreak-bizonyíték.

Viszonyítás nélkül nem mehet döntésbe.
```

A PULSE-COMPUTE nem azt akadályozza meg, hogy a rendszer rossz mintát tanuljon.

A PULSE-COMPUTE azt akadályozza meg, hogy a rossz minta igazolt döntési úttá váljon.

## English workshop anchor

```text
Learned truth is not truth.

A learned label is not evidence.

Textual similarity is not authority.

A jailbreak label is not jailbreak proof.

Without comparison, nothing may enter decision.
```

PULSE-COMPUTE does not prevent the system from learning a wrong pattern.

PULSE-COMPUTE prevents the wrong pattern from becoming a verified decision path.
