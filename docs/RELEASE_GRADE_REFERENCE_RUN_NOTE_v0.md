# Release-grade reference run note v0

## Purpose

This note records one public, non-stubbed release-grade PULSE reference run.

It is a review and provenance note.
It does not create release authority.
Release authority remains the normal PULSE path:

```text
status.json
→ declared gate policy
→ workflow-effective required gate set
→ check_gates.py
→ primary CI workflow
```

## Run identity

- date: 2026-07-13
- workflow: PULSE CI
- workflow run number: 6066
- workflow path: workflow_dispatch
- event: workflow_dispatch
- ref: refs/heads/main
- git_sha: 46b639706e23f80fe296a8893be18e2b5ab21f7e
- run_key: PULSE CI #6066 / refs/heads/main / 46b639706e23f80fe296a8893be18e2b5ab21f7e
- run_mode: release-grade reference run
- active policy set: required + release_required

## Qualification summary

- workflow result: Success
- duration: 5m 29s
- artifact count: 15
- release-grade reference checker result: Success
- stubbed/scaffolded evidence absent: true
- external evidence required: true
- strict_external_evidence: true
- external summaries present: true
- required gates evaluated fail-closed: true
- release authority manifest produced: true
- Quality Ledger produced: true
- audit bundle produced: true
- LlamaGuard evidence mode: hosted_full_runtime
- LlamaGuard access preflight: #8 — Success
- LlamaGuard preflight artifact digest: sha256:8d4f7c4f058ce6c84daf45c90cffe086f1dfd223d835c41e4e6b60b22ac071a6
- visible LlamaGuard attestation: 35064328

## Public artifacts

- total public artifact count: 15
- status.json: produced
- report_card.html: produced
- release_authority_v0.json: produced
- release-authority-audit-bundle: produced
- external summaries: produced
- junit: produced
- sarif: produced
- LlamaGuard preflight artifact digest: sha256:8d4f7c4f058ce6c84daf45c90cffe086f1dfd223d835c41e4e6b60b22ac071a6
- visible LlamaGuard attestation: 35064328

## Boundary reminder

This note documents a candidate reference run.
It does not replace status.json.
It does not replace check_gates.py.
It does not create a second release-decision engine.
It does not promote reader, dashboard, Pages, or shadow surfaces into authority.

## Reviewer checklist

- Which workflow path produced the run? PULSE CI #6066 via workflow_dispatch.
- Was the run release-grade or only Core? Release-grade reference run.
- Was the effective enforce set required + release_required? Yes.
- Was diagnostics.gates_stubbed absent/false? Yes; stubbed/scaffolded evidence is recorded absent.
- Were external summaries present when required? Yes; strict external evidence was enabled and external summaries are recorded present.
- Was release_authority_v0.json produced? Yes.
- Was the audit bundle uploaded? Yes.
- Are all public reader surfaces clearly non-authoritative? Yes; the boundary reminder preserves release authority in the normal PULSE path. 
