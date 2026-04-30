# Agent Orchestration Evidence Bridge v0

## Purpose

This document defines how agent-orchestration systems can provide work evidence
to PULSE without becoming release authority.

Agent orchestration systems may coordinate coding agents, issue trackers,
isolated workspaces, pull requests, CI feedback, review packets, and other
proof-of-work surfaces.

PULSE does not orchestrate agents.

PULSE evaluates recorded release evidence at the release boundary.

This bridge defines the boundary between:

```text
agent work orchestration
```

and:

```text
release authority / release governance
```

## Status

- stage: bridge definition  
- normative: false  
- authority role: diagnostic / evidence-ingress guidance  

This document is an architectural bridge.

It does not change release semantics, gate policy, status.json semantics,
check_gates.py behavior, primary release-decision authority, or shadow-layer
authority.

---

## Core distinction

Agent orchestration answers:

```text
How is work assigned, executed, reviewed, and handed off?
```

PULSE answers:

```text
Can the resulting state pass the release boundary under declared policy?
```

Compact distinction:

```text
Agent orchestrator = work execution / proof-of-work producer
PULSE = release authority / evidence-to-decision layer
```

---

## Example: Symphony-style work evidence

Symphony is an example of an agent-orchestration surface.

In a Symphony-style flow:

```text
issue / task
→ isolated agent workspace
→ implementation run
→ PR / review packet / CI feedback / walkthrough
→ human acceptance or follow-up
```

That output may become useful PULSE evidence.

However:

```text
Symphony proof-of-work present ≠ release PASS
agent task accepted ≠ release authority
PR merged by an agent system ≠ PULSE release decision
```

PULSE must still evaluate the recorded evidence under declared policy.

---

## Bridge principle

Agent-orchestration evidence may be recorded by PULSE.

It must not silently become release authority.

Default bridge rule:

```text
agent work evidence
→ diagnostic / advisory evidence surface
→ optional future policy promotion only by explicit gate-set change
```

The first integration layer should record evidence under diagnostic metadata, for
example:

```json
status.json["meta"]["agent_work_evidence"]
```

not under:

```json
status.json["gates"]
```

unless a future policy explicitly promotes a specific signal into the required
gate set.

---

## Evidence shape

A minimal agent work evidence record may include:

```json
{
  "schema_version": "agent_orchestration_evidence_v0",
  "source": "symphony",
  "task_id": "TASK-123",
  "agent_run_id": "agent-run-001",
  "workspace_id": "workspace-001",
  "pr_url": "https://example.invalid/pr/123",
  "ci_status": "pass",
  "review_status": "approved",
  "proof_of_work_present": true,
  "human_accepted": true,
  "created_utc": "2026-04-27T00:00:00Z"
}
```

This evidence is descriptive unless policy explicitly promotes it.

---

## Suggested fields

Recommended fields:

- schema_version  
- source  
- task_id  
- agent_run_id  
- workspace_id  
- pr_url  
- ci_status  
- review_status  
- proof_of_work_present  
- human_accepted  
- created_utc  
- optional complexity_summary  
- optional walkthrough_artifact  
- optional logs_artifact  
- optional risk_notes  
- optional reviewer_notes  

---

## PULSE ingestion boundary

A first PULSE bridge should ingest agent evidence as diagnostic metadata only.

Recommended first fold-in target:

```json
status.json["meta"]["agent_work_evidence"]
```

The fold-in should preserve:

- source  
- task identity  
- agent run identity  
- proof-of-work references  
- review state  
- CI state  
- timestamps  

The fold-in must not:

- change required gates  
- change check_gates.py  
- change release decision state  
- rewrite status.json["gates"]  
- promote the evidence into release authority  
- or reinterpret diagnostic evidence as PASS  

---

## Possible future gates

Future policy may explicitly promote selected agent-work signals into gates.

Examples:

- agent_work_evidence_present  
- agent_work_ci_pass  
- agent_work_review_accepted  
- agent_work_handoff_recorded  

These must remain future promotions until explicitly added to:

- pulse_gate_policy_v0.yml  
- pulse_gate_registry_v0.yml  
- docs/STATUS_CONTRACT.md  
- tests / fixtures  

No promotion should happen through documentation language alone.

---

## Authority boundary

Normative release authority remains:

```text
status.json
+ declared gate policy
+ workflow-effective required gate set
+ check_gates.py
+ primary CI workflow
= release authority
```

Agent orchestration evidence is upstream evidence.

It may help explain:

- what work was performed  
- which agent produced it  
- what proof-of-work was attached  
- whether CI/review/handoff happened  

It does not decide release outcome by default.

---

## Relationship to release_authority_v0

`release_authority_v0.json` records the release-authority chain for a run.

Agent orchestration evidence can appear as diagnostic context in that chain, for
example:

```text
diagnostics.agent_work_evidence_present = true
```

or:

```text
status_meta_foldins includes meta.agent_work_evidence
```

But the manifest must continue to distinguish:

```text
release authority
```

from:

```text
diagnostic context
```

---

## Relationship to Quality Ledger

The Quality Ledger may render agent-work evidence for human review.

That rendering is a reader / renderer surface.

It must not compute or redefine release decisions.

If agent-work evidence is missing, stale, malformed, or incomplete, the Ledger may
show:

```text
MISSING
UNKNOWN
INCOMPLETE
```

but must not silently reinterpret absence as PASS.

---

## Non-goals

This bridge does not:

- add Symphony as a PULSE dependency  
- require Linear  
- require Codex  
- start or supervise agents  
- define an agent runtime  
- define a PR merge policy  
- replace check_gates.py  
- replace status.json  
- or create a second release-decision engine  

---

## Implementation path

Recommended staged implementation:

1. Document the bridge boundary.  
2. Add an example agent-orchestration evidence JSON.  
3. Add a schema for `agent_orchestration_evidence_v0`.  
4. Add a diagnostic fold-in tool under `status.json["meta"]`.  
5. Add tests proving non-interference with release outcome.  
6. Add optional Quality Ledger rendering.  
7. Consider future policy promotion only after evidence semantics are stable.  

---

## Summary

Agent orchestration systems can produce valuable work evidence.

PULSE can preserve and audit that evidence at the release boundary.

The bridge is useful only if the boundary stays clear:

```text
orchestration produces work evidence
PULSE evaluates release evidence
policy defines release authority
check_gates.py enforces required gates
```
