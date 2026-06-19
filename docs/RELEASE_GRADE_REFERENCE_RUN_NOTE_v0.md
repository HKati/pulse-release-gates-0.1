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

- date:
- workflow path: version tag push / workflow_dispatch
- ref:
- git_sha:
- run_key:
- run_mode:
- active policy set: required + release_required

## Qualification summary

- release-grade reference checker result:
- stubbed/scaffolded evidence absent:
- external evidence required:
- external summaries present:
- required gates evaluated fail-closed:
- release authority manifest produced:
- Quality Ledger produced:
- audit bundle produced:

## Public artifacts

- status.json:
- report_card.html:
- release_authority_v0.json:
- release-authority-audit-bundle:
- external summaries:
- junit:
- sarif:

## Boundary reminder

This note documents a candidate reference run.
It does not replace status.json.
It does not replace check_gates.py.
It does not create a second release-decision engine.
It does not promote reader, dashboard, Pages, or shadow surfaces into authority.

## Reviewer checklist

- Which workflow path produced the run?
- Was the run release-grade or only Core?
- Was the effective enforce set required + release_required?
- Was diagnostics.gates_stubbed absent/false?
- Were external summaries present when required?
- Was release_authority_v0.json produced?
- Was the audit bundle uploaded?
- Are all public reader surfaces clearly non-authoritative?
