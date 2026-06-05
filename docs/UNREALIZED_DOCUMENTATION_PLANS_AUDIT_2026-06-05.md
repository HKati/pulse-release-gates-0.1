# Unrealized Documentation Plans Audit — 2026-06-05

Status: documentation audit  
Scope: repository documentation / plan-draft-gap discovery  
Authority status: non-normative review aid  

## Method

This audit searched repository documentation for explicit markers that a
document is a plan, draft, design note, backlog, gap map, skeleton, baseline, or
future implementation note.

The audit then grouped the strongest matches by whether the source text itself
indicates that the work is not yet implemented, not complete, only preparatory,
partially realized, or suitable for later research / publication handling.

Primary search terms included:

- `plan`;
- `planned`;
- `planning`;
- `draft`;
- `design note`;
- `skeleton`;
- `backlog`;
- `gap`;
- `future implementation`;
- `future PR`;
- `not implemented yet`;
- `not yet`;
- `does not build`;
- `next implementation`;
- `stub`;
- `scaffold`;
- `placeholder`.

This audit is intentionally conservative.

It does not classify every future-facing sentence as an open implementation
item.

It highlights documents where the document status or body gives a clear signal
that the work is still planned, partial, diagnostic, preparatory, or
unrealized.

## Practical triage

The useful split is not:

```text
planned word equals bug
```

The useful split is:

```text
documentation state
→ mechanical relevance
→ cleanup / warehouse / publication classification
```

The audit classifies plan-like material into three primary buckets:

1. **Real future implementation / closure work**: release-grade non-stubbed
   reference run, evidence packet, RA0/RA1 follow-on, gap inventory, and
   hardening-plan closure.
2. **Warehouse / research material**: theory notes, optional overlays, demos,
   topology, memory trace, EPF design notes, future-library material, and
   paradox math. These are later workshop materials, not urgent repository
   defects.
3. **Paper / publication planning**: `docs/papers/` manuscript and bibliography
   preparation. These belong to a separate publication track and should not be
   treated as release-mechanics gaps.

Older `refusal_delta_evidence_present` plan language appears partially stale
because policy, profile, and test evidence now exists in the repository.

That is a stale-documentation cleanup item.

It is not a new implementation demand by default.

## Operational boundary

This audit classifies documentation state.

A listed document enters active work when it affects one of the following
mechanical review surfaces:

- PULSEmech authority path;
- release-grade lane eligibility;
- stale plan language versus current repository evidence;
- current field-development direction;
- terminology or boundary misread risk.

## Bucket 1 — real future implementation / closure work

These items are the closest to actual PULSE implementation or closure work.

They should be tracked as release-grade hardening, reference-run,
evidence-packet, RA/HPC follow-on, or repository-hardening closure items.

| Document | Why it belongs here | Current signal in the document | Suggested follow-up |
|---|---|---|---|
| `docs/PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md` | Defines the next non-stubbed release-grade reference run rather than recording its completion. | Goal is to move from scaffold/core/smoke state toward the first non-stubbed release-grade reference state. | Close only after a recorded non-stubbed run exists and is linked. |
| `docs/release_grade_reference_run_v0.md` | Checker and example package exist, but the real non-stubbed reference run is still future work. | Status says checker implemented; next steps say a real non-stubbed release-grade reference run remains future work. | Produce and archive the real reference run, then update the next-steps section. |
| `docs/pulse_ref_gap_inventory_v1.md` | Inventory lists concrete release-grade blockers. | Says a fully non-stubbed, materialized-evidence release-grade reference run is not yet complete as the public reference artifact. | Use as blocker list; mark closed items as implemented or move remaining items to a current tracker. |
| `docs/PULSE_REF_EVIDENCE_PACKET_GAP_MAP_v0.md` | Gap map between current verified field state and a future release-grade evidence packet. | Says the document maps the gap to a future non-stubbed, materialized-evidence, release-grade reference packet. | Convert remaining gaps into implementation issues or update with closed gaps. |
| `docs/PULSE_REF_RELEASE_REFERENCE_EVIDENCE_PACKET_BASELINE_v0.md` | Planning baseline for moving fixture matrix toward a concrete evidence packet. | Status is `planning baseline` and relation section prepares future implementation work. | Reconcile with any packet fixtures/builders already added; leave only remaining baseline work. |
| `docs/PULSE_REF_PASS_FIXTURE_TO_EVIDENCE_PACKET_HANDOFF_PLAN_v0.md` | Handoff plan explicitly says it does not build the packet and is for the next implementation step. | Status is `planning handoff`; says the document does not build an evidence packet. | Update once the guarded pass fixture has been transformed into a packet-shaped baseline candidate. |
| `docs/PULSE_REF_RA0_RELEASE_AUTHORITY_STATUS_v0.md` | RA0 milestone record lists later RA/HPC capabilities that RA0 does not yet provide. | Says RA0 does not yet claim, provide, bind, or define several full reference-run and HPC-scale capabilities. | Treat as milestone boundary; track the next RA/HPC items elsewhere or update after RA1+ closure. |
| `HARDENING_PLAN.md` | Repository hardening operational plan with checklist / phase-plan framing. | Status is a maintainer-facing operational plan for the v0 hardening pass. | Keep as active operational plan or add completion markers for finished phases. |
| `docs/README_DEEP_TERMINOLOGY_CLEANUP_BACKLOG_2026-05-23.md` | Deferred documentation cleanup backlog. | Status is `deferred cleanup backlog` and records remaining README cleanup items. | Execute cleanup or keep as explicit deferred debt. |

## Bucket 2 — warehouse / research material, not urgent repository defects

These documents are plan-like, draft-like, or diagnostic by status, but they are
research notes, optional overlays, demos, or workshop surfaces.

They should not be escalated as release-mechanics defects unless a maintainer
explicitly opens a productization or implementation track.

| Document | Signal | Notes |
|---|---|---|
| `docs/time_as_consequence_v0_1.md` | Explicitly says `Not implemented yet`. | Theory note; keep as warehouse/research unless an implementation track is opened. |
| `docs/time_as_consequence_one_pager_v0_1.md` | Explicitly says `Not implemented yet`. | One-page companion to the theory note. |
| `docs/PULSE_paradox_resolution_v0_design_note.md` | Status says `draft / experimental — not implemented yet`. | Optional diagnostic overlay; not release authority. |
| `docs/PULSE_topology_dashboards_v0_design_note.md` | Draft / experimental design note. | Dashboard concept for the future library; optional reader surface. |
| `docs/PULSE_memory_trace_dashboard_v0_demo.md` | Working draft demo. | Demo/dashboard concept; not release authority. |
| `docs/PULSE_memory_trace_summariser_v0_design_note.md` | Draft internal design note. | Summarizer concept; should remain non-authoritative unless promoted through declared policy, materialized gates, and strict CI enforcement. |
| `docs/PULSE_decision_engine_epf_v0_design_note.md` | Draft design note only. | Design note for EPF / Decision Engine relationship. |
| `docs/PULSE_memory_trace_v0_walkthrough.md` | Working draft walkthrough. | Walkthrough/demo documentation. |
| `docs/PULSE_epf_memory_status_v0.md` | Working draft. | EPF memory/status note. |
| `docs/PULSE_topology_v0_case_study.md` | Draft case study / worked example. | Case-study draft rather than implementation gate. |
| `docs/PULSE_paradox_math_v0_intro.md` | Draft v0. | Mathematical/introductory draft. |
| `docs/gravity_record_protocol_decodability_wall_v0_1.md` | Draft, concept-to-implementation-backed spec level. | Protocol/spec note; verify before treating as implemented. |
| `docs/FUTURE_LIBRARY.md` | Future-library framing. | Catalog/future-facing documentation, not direct implementation closure. |

## Bucket 3 — paper / publication planning, separate track

The `docs/papers/` tree contains intentionally non-normative paper-planning
artifacts.

These are planning documents, but they are not release-mechanics implementation
debt.

They belong to a manuscript / publication track.

| Document | Signal |
|---|---|
| `docs/papers/PULSEMECH_BIBLIOGRAPHY_LOCK_PLAN_v0.md` | Bibliography lock plan. |
| `docs/papers/PULSEMECH_LITERATURE_SEARCH_PLAN_v0.md` | Literature search plan. |
| `docs/papers/PULSEMECH_FINAL_SOURCE_GAP_CLOSURE_PLAN_v0.md` | Final source-gap closure plan. |
| `docs/papers/PULSEMECH_RELATED_WORK_SCAFFOLD_v0.md` | Related-work scaffold. |
| `docs/papers/PULSEMECH_CS_SE_PAPER_SKELETON_v0.md` | Paper skeleton / pre-draft. |
| `docs/papers/PULSEMECH_MINIMAL_FIRST_DRAFT_OUTLINE_v0.md` | Minimal first-draft outline. |
| `docs/papers/PULSEMECH_CONTROLLED_PROSE_SKELETON_v0.md` | Controlled prose skeleton. |
| `docs/papers/PULSEMECH_FIRST_PROSE_DRAFT_v0.md` | First prose draft. |
| `docs/papers/PULSEMECH_CITATION_BOUND_PROSE_DRAFT_v0.md` | Citation-bound prose draft. |
| `docs/papers/PULSEMECH_RELATED_WORK_PROSE_v0.md` | Related-work prose draft. |
| `docs/papers/PULSEMECH_CITATION_KEYED_RELATED_WORK_DRAFT_v0.md` | Citation-keyed related-work draft. |
| `docs/papers/PULSEMECH_ARTIFACT_TO_CLAIM_MAP_v0.md` | Pre-draft support / claim map; includes some future packet-completeness boundaries. |
| `docs/papers/PULSEMECH_CLAIM_BOUNDARY_REVIEW_v0.md` | Pre-draft support; says claims are not yet marked verified for manuscript. |

## Current cleanup targets — stale or partially realized plan language

These items are current cleanup targets.

They are not new implementation demands by default.

Each item requires reconciliation between older plan language and current
repository evidence before any new implementation work is opened.

| Document | Why it may be stale or partial | Repository evidence to reconcile | Cleanup classification |
|---|---|---|---|
| `docs/refusal_delta_evidence_presence_gate_v1.md` | The document describes a planned promotion. | `docs/evidence_presence_policy_v1.md`, `PULSE_safe_pack_v0/profiles/release_grade_reference_v1.yml`, and multiple tests now reference `refusal_delta_evidence_present` as release-required or enforced in release-grade contexts. | Stale documentation cleanup; not a new implementation request by default. |
| `docs/no_implicit_pass_release_grade_v1.md` | Mentions future promotion of `refusal_delta_evidence_present`. | Same reconciliation target as above. | Stale documentation cleanup; not a new implementation request by default. |
| `docs/PULSE_REF_SCHEMA_ALIGNED_PACKET_BUILDER_CHECKPOINT_v0.md` | Checkpoint before next implementation layer; may be partially superseded by packet-builder tests. | Tests and fixtures exist for schema-aligned packet builder / package verification paths. | Reconcile before opening new work. |
| `docs/PULSE_REF_RELEASE_REFERENCE_EVIDENCE_PACKET_BASELINE_v0.md` | Prepares future implementation, but some packet baseline candidate tests exist. | Reconcile with `tests/test_pulse_ref_pass_fixture_packet_baseline_candidate_v0.py` and packet layout fixtures. | Partial implementation / stale-plan review. |

## Review use

Use this audit as a documentation-state classifier.

A listed item becomes active work through mechanical review, not through the
presence of planning language alone.

Recommended review sequence:

1. identify the document status;
2. compare older plan language against current repository evidence;
3. classify the item as closure work, current cleanup target, warehouse /
   research material, or publication-track material;
4. open implementation work only when a current mechanical gap remains;
5. keep research and publication material separate from release-mechanics debt.

## Preserved boundary

This audit does not change the PULSEmech authority path.

Release permission remains produced by:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ pre-deployment allow/block release decision
```

This audit does not add gates, change policy, change schemas, change workflow
mechanics, modify `check_gates.py`, create a second release-decision engine, or
promote warehouse / research / publication material into release authority.

## Summary

This audit separates unrealized documentation plans into operationally different
classes.

The main classification result is:

```text
real closure work
warehouse / research material
paper / publication planning
current cleanup targets for stale or partially realized plan language
```

The highest-value immediate use is stale-plan reconciliation, especially where
current repository evidence may already partially satisfy older plan language.
