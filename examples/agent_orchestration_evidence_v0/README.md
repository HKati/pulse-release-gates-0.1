# Agent orchestration evidence v0 examples

This directory contains example payloads for the PULSE agent orchestration
evidence bridge.

Agent orchestration systems may produce useful proof-of-work evidence, such as
task identity, agent-run metadata, PR links, CI status, review state,
walkthroughs, and handoff records.

PULSE can preserve that evidence as diagnostic context.

This example package is non-normative.

It does not define release semantics, create gates, change `status.json`,
replace `check_gates.py`, or grant release authority to agent-produced work.

---

## Files

```text
symphony_work_evidence.example.json
```

### `symphony_work_evidence.example.json`

Example Symphony-style proof-of-work evidence payload.

It records:

- task identity,
- isolated agent run metadata,
- workspace identity,
- PR / CI / review context,
- walkthrough artifact reference,
- task-level human review context,
- recommended PULSE fold-in target,
- explicit non-normative authority status.

The payload declares:

```json
{
  "evidence_role": "diagnostic",
  "normative": false,
  "release_authority": false
}
```

and recommends diagnostic fold-in under:

```text
status.meta.agent_work_evidence
```

not under:

```text
status.gates
```

unless a future policy explicitly promotes a specific signal.

---

## How to inspect the example

From the repository root:

```console
python -m json.tool examples/agent_orchestration_evidence_v0/symphony_work_evidence.example.json
```

This only checks JSON shape / parseability.

It does not validate release authority and does not compute a release decision.

---

## Authority boundary

Agent orchestration evidence can describe work that happened.

Examples:

```text
an issue was assigned
an isolated agent run completed
a PR was produced
CI passed
review feedback was attached
a walkthrough artifact exists
a human accepted the task-level handoff
```

These facts may be useful release context.

They are not release authority by default.

The PULSE release-authority path remains:

```text
status.json
+ declared gate policy
+ workflow-effective required gate set
+ check_gates.py
+ primary CI workflow
= release authority
```

Agent orchestration evidence remains diagnostic / advisory unless explicitly
promoted by policy.

---

## Relation to the bridge document

For the architectural boundary, see:

```text
docs/AGENT_ORCHESTRATION_EVIDENCE_BRIDGE_v0.md
```

That document defines the separation between:

```text
agent work orchestration
```

and:

```text
release authority / release governance
```

---

## Future implementation path

Possible future steps:

1. Add `schemas/agent_orchestration_evidence_v0.schema.json`.
2. Add a conservative contract checker for the evidence payload.
3. Add a diagnostic fold-in tool under `status.meta.agent_work_evidence`.
4. Add non-interference tests proving the fold-in does not change release
   outcomes.
5. Add optional Quality Ledger rendering for agent-work evidence.
6. Consider policy promotion only through explicit gate-policy and registry
   changes.

No promotion is implied by this example package.
