# Documentation index

This page is the fuller index of repository documentation.

The README documentation map is intentionally curated and entrypoint-first.

This index separates:

```text
current implementation
current operational target
legacy diagnostic surface
historical design record
reader / audit surface
future or staged work
```

If a document is added, renamed, superseded, or changes implementation status, update this index.

## Status labels

- **Current implementation** — describes checked-in mechanics that are implemented and testable.
- **Current operational reference** — defines the present release-grade path and its completion boundary.
- **Pending operational target** — describes work required before the first completed public reference run.
- **Legacy diagnostic surface** — remains implemented and tested, but is not the current authority or admission path.
- **Historical design record** — preserves earlier design reasoning but is not the current implementation source of truth.
- **Reader / audit surface** — renders, preserves, or explains state without independently creating release authority.

---

## Start here

- Running the Core PULSE lane: [QUICKSTART_CORE_v0.md](QUICKSTART_CORE_v0.md)
- Current release-grade operational reference: [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md)
- Current recorded evidence verifier: [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md)
- Understanding the source of truth: [status_json.md](status_json.md)
- External PULSE review entrypoint: [PULSE_EXTERNAL_REVIEW_ENTRYPOINT_v0.md](PULSE_EXTERNAL_REVIEW_ENTRYPOINT_v0.md)
- PULSE risk-to-hardening map: [PULSE_RISK_TO_HARDENING_MAP_v0.md](PULSE_RISK_TO_HARDENING_MAP_v0.md)
- Operational triage and reruns: [RUNBOOK.md](RUNBOOK.md)

---

## Current release-grade evidence path

The current implemented PULSEmech path is:

```text
recorded current-run release evidence
→ non-stubbed candidate release state
→ canonical candidate production
→ canonical candidate replay
→ recorded release-evidence verification
→ canonical verifier replay
→ policy-derived release-required gate materialization
→ final status.json
→ workflow-effective materialized required gate set
→ PULSE_safe_pack_v0/tools/check_gates.py
→ primary CI allow/block release decision
```

Read these documents in this order:

1. [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md)  
   **Current operational reference.** Defines the implemented release-grade path, advisory qualification boundary, baseline bundle boundary, complete target package, and completed-run acceptance criteria.

2. [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md)  
   **Current implementation.** Defines canonical candidate replay, recorded evidence verification, relation verification, manifest-declared gate admissibility, canonical verifier replay, and materializer coverage boundaries.

3. [release_reference_external_evidence_integration_v1.md](release_reference_external_evidence_integration_v1.md)  
   External-summary schema, envelope, signer-policy, verification-before-fold-in, and failure-mode contract.

4. [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md)  
   **Pending operational target.** Target record to be completed from the first real public non-stubbed release-grade run. It is not proof that the run already exists.

5. [PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md](PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md)  
   Operational plan for the remaining path toward exact signer identity, current-run attested evidence, complete packaging, controlled execution, and the completed public record.

6. [PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md](PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md)  
   **Historical design record and legacy diagnostic boundary.** Not the current verifier implementation entrypoint.

---

## Orientation and contracts

- [STATE_v0.md](STATE_v0.md) — Broad repository-state snapshot. For the current release-grade evidence path, use the release-grade reference and recorded-verifier documents above.
- [QUICKSTART_CORE_v0.md](QUICKSTART_CORE_v0.md) — Minimal steps for the Core pipeline.
- [RUNBOOK.md](RUNBOOK.md) — Operational runbook for triage and reruns.
- [STATUS_CONTRACT.md](STATUS_CONTRACT.md) — Contract for `status.json` shape and semantics.
- [status_json.md](status_json.md) — How to read the normative release-state artifact.
- [GATE_SETS.md](GATE_SETS.md) — Human-readable gate-set orientation.
- [GLOSSARY_v0.md](GLOSSARY_v0.md) — Canonical terminology used across repository documentation.
- [WORKFLOW_MAP.md](WORKFLOW_MAP.md) — Workflow structure and lane orientation.
- [PULSEMECH_ARCHITECTURE_MAP_v0_1.md](PULSEMECH_ARCHITECTURE_MAP_v0_1.md) — PULSEmech architecture map and release-authority boundary.
- [release_authority_manifest_v0.md](release_authority_manifest_v0.md) — Audit-manifest contract for preserving the release-authority chain without becoming a second decision engine.
- [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md) — Current release-grade operational definition and completion boundary.
- [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md) — Current recorded evidence verifier, replay, admissibility, and materializer boundary.
- [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md) — Target public run record to be completed from an actual controlled run.
- [PULSE_TITLE_CONTINUITY_v0.md](PULSE_TITLE_CONTINUITY_v0.md) — Title-continuity provenance across repository and publication surfaces.

---

## Documentation-to-core role map

This map connects documentation to the current release-authority mechanism.

It is orienting only.

It does not create authority beyond the artifact-bound path defined by the linked contracts.

| Bucket | Core role | Primary documents |
|---|---|---|
| Core mechanics | Explains the connected evidence-to-decision path. | [PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md](PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md), [PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md](PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md), [PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md](PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md), [PULSE_RELEASE_STATE_TRANSFORMATION_v0.md](PULSE_RELEASE_STATE_TRANSFORMATION_v0.md) |
| Authority boundary | Separates execution, approval, reader surfaces, manifests, attestations, and audit sidecars from the normative authority carrier. | [PULSEMECH_ARCHITECTURE_MAP_v0_1.md](PULSEMECH_ARCHITECTURE_MAP_v0_1.md), [PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md](PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md), [PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md](PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md), [release_authority_boundary_v1.md](release_authority_boundary_v1.md), [MAINTAINER_AUTHORITY_BOUNDARY_v0.md](MAINTAINER_AUTHORITY_BOUNDARY_v0.md) |
| Status, policy, gate-set, and workflow contracts | Defines the normative carrier tuple for final state, declared policy, workflow-effective gates, strict enforcement, and primary CI outcome. | [status_json.md](status_json.md), [STATUS_CONTRACT.md](STATUS_CONTRACT.md), [GATE_SETS.md](GATE_SETS.md), [WORKFLOW_MAP.md](WORKFLOW_MAP.md), [RELEASE_DECISION_v0.md](RELEASE_DECISION_v0.md), [PULSE_RELEASE_GRADE_MATERIALIZED_LANE_v0.md](PULSE_RELEASE_GRADE_MATERIALIZED_LANE_v0.md) |
| Current verifier and evidence admission | Defines current-run candidate replay, recorded evidence verification, relation verification, gate admissibility, canonical verifier replay, and verifier-bound materialization. | [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md), [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md), [release_reference_external_evidence_integration_v1.md](release_reference_external_evidence_integration_v1.md), [PULSE_EXTERNAL_EVIDENCE_MATERIALIZATION_BOUNDARY_v0.md](PULSE_EXTERNAL_EVIDENCE_MATERIALIZATION_BOUNDARY_v0.md) |
| Legacy verifier diagnostics and historical prerequisites | Preserves the earlier failure-only verifier-report line, expectation summaries, schema drafts, and relation-promotion prerequisites without presenting them as the current admission path. | [PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md](PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md), [PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md](PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md), [PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md](PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md), [PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_ONLY_DRAFT_BOUNDARY_v0.md](PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_ONLY_DRAFT_BOUNDARY_v0.md), [PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md](PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md), [PULSE_EVIDENCE_FOLD_IN_ADMISSIBILITY_v0.md](PULSE_EVIDENCE_FOLD_IN_ADMISSIBILITY_v0.md) |
| Release-grade reference and public record | Defines what a completed public run must contain and where its concrete run identity is recorded. | [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md), [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md), [PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md](PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md) |
| Reader surfaces | Shows recorded state without allowing dashboards, summaries, notebooks, or Pages to become authority carriers. | [quality_ledger.md](quality_ledger.md), [PULSE_PUBLIC_SURFACE_CONTRACT_v0.md](PULSE_PUBLIC_SURFACE_CONTRACT_v0.md), [PULSE_PUBLIC_PRIVATE_ARTIFACT_BOUNDARY_v0.md](PULSE_PUBLIC_PRIVATE_ARTIFACT_BOUNDARY_v0.md), [PULSE_NATIVE_REVIEW_FRAME_v0.md](PULSE_NATIVE_REVIEW_FRAME_v0.md) |
| Audit and provenance sidecars | Preserves digest-backed decision, binding, manifest, attestation-subject, and cryptographic-verification state around the normative path. | [ARTIFACT_PROVENANCE_BINDING_v0.md](ARTIFACT_PROVENANCE_BINDING_v0.md), [release_authority_manifest_v0.md](release_authority_manifest_v0.md), [RELEASE_AUTHORITY_ATTESTATION_SUBJECT_v0.md](RELEASE_AUTHORITY_ATTESTATION_SUBJECT_v0.md), [RELEASE_AUTHORITY_CRYPTOGRAPHIC_BINDING_v0.md](RELEASE_AUTHORITY_CRYPTOGRAPHIC_BINDING_v0.md), [ANCHOR_INTEGRITY_v0.md](ANCHOR_INTEGRITY_v0.md) |
| Diagnostic and shadow surfaces | Keeps EPF, paradox, topology, field, overlay, and shadow inventory outputs diagnostic unless explicitly admitted through declared policy and strict enforcement. | [OPTIONAL_LAYERS.md](OPTIONAL_LAYERS.md), [NORMATIVE_SHADOW_INVENTORY_MODEL_v0.md](NORMATIVE_SHADOW_INVENTORY_MODEL_v0.md), [SHADOW_ARTIFACT_COMMON_v0.md](SHADOW_ARTIFACT_COMMON_v0.md), [PULSE_epf_shadow_quickstart_v0.md](PULSE_epf_shadow_quickstart_v0.md), [PULSE_paradox_core_v0.md](PULSE_paradox_core_v0.md), [PULSE_topology_overview_v0.md](PULSE_topology_overview_v0.md), [PULSE_decision_field_v0_overview.md](PULSE_decision_field_v0_overview.md) |
| Pending operational work | Collects the remaining exact-signer, current-run attested-evidence, complete-package, controlled-run, and portability work. | [PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md](PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md), [FUTURE_LIBRARY.md](FUTURE_LIBRARY.md), [FUTURE_READY_WORKMODE.md](FUTURE_READY_WORKMODE.md), [PULSE_HARDENING_BOUNDARY_MAP_v0.md](PULSE_HARDENING_BOUNDARY_MAP_v0.md), [UNREALIZED_DOCUMENTATION_PLANS_AUDIT_2026-06-05.md](UNREALIZED_DOCUMENTATION_PLANS_AUDIT_2026-06-05.md) |
| Adoption and external review | Supports operator handoff, external review, governance packets, and challenge packets while preserving the authority boundary. | [PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md](PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md), [EXTERNAL_VERIFICATION_PATH_v0.md](EXTERNAL_VERIFICATION_PATH_v0.md), [EXTERNAL_VERIFICATION_PACKET_v0.md](EXTERNAL_VERIFICATION_PACKET_v0.md), [GOVERNANCE_PACK_v0.md](GOVERNANCE_PACK_v0.md), [OPERATOR_HANDOFF_v0.md](OPERATOR_HANDOFF_v0.md), [OUTSIDE_REVIEW_RESPONSE.md](OUTSIDE_REVIEW_RESPONSE.md), [AUTHORITY_IMPACT_AUDIT_CHECKLIST_v0.md](AUTHORITY_IMPACT_AUDIT_CHECKLIST_v0.md) |

---

## Status, ledger, and external evidence

- [status_json.md](status_json.md) — Reading final release state, metrics, gates, and consumers.
- [quality_ledger.md](quality_ledger.md) — Quality Ledger structure and non-authorizing reader role.
- [refusal_delta_gate.md](refusal_delta_gate.md) — Refusal-delta evidence and fail-closed semantics.
- [EXTERNAL_DETECTORS.md](EXTERNAL_DETECTORS.md) — External detector policy and advisory/gating modes.
- [external_detector_summaries.md](external_detector_summaries.md) — External detector summary integration.
- [release_reference_external_evidence_integration_v1.md](release_reference_external_evidence_integration_v1.md) — External summary schema, envelope, signer-policy, and verification-before-fold-in contract.
- [AGENT_ORCHESTRATION_EVIDENCE_BRIDGE_v0.md](AGENT_ORCHESTRATION_EVIDENCE_BRIDGE_v0.md) — Boundary for agent-orchestration evidence without independent release authority.

---

## Release evidence verification

### Current implementation

- [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md) — Current recorded evidence verifier, canonical replay, per-entry admissibility, materializer coverage, and authority boundary.
- [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md) — Current release-grade operational reference and complete-package boundary.
- [release_reference_external_evidence_integration_v1.md](release_reference_external_evidence_integration_v1.md) — External evidence contract and verification-before-fold-in surface.

### Pending operational target

- [PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md](PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md) — Remaining path toward exact signer identity, current-run attested evidence, complete packaging, and the controlled strict run.
- [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md) — Target record to be completed from the first real public non-stubbed run.

### Historical and legacy surfaces

- [PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md](PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md) — Superseded as the current implementation entrypoint; retained as a historical verifier design and legacy diagnostic-surface record.
- [PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md](PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md) — Reader-only diagnostic summary for legacy pre-materialization gaps.
- [PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md](PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md) — Historical relation-binding promotion prerequisites.
- [PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md](PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md) — Historical verifier schema-delta map.
- [PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_ONLY_DRAFT_BOUNDARY_v0.md](PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_ONLY_DRAFT_BOUNDARY_v0.md) — Historical schema-only draft boundary.

---

## Release-state transformation

- [PULSE_RELEASE_STATE_TRANSFORMATION_v0.md](PULSE_RELEASE_STATE_TRANSFORMATION_v0.md) — PULSEmech as a closed release-state transformation path.
- [PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md](PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md) — Pre-materialization mechanics and relation-bearing pre-state hooks.
- [PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md](PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md) — Mechanical bridge between recorded evidence and release authority.

---

## Paradox field and edges

- [PULSE_paradox_field_v0_walkthrough.md](PULSE_paradox_field_v0_walkthrough.md) — Reading `paradox_field_v0`.
- [Pulse_paradox_edges_v0_status.md](Pulse_paradox_edges_v0_status.md) — Status and roadmap for `paradox_edges_v0.jsonl`.
- [paradox_edges_case_studies.md](paradox_edges_case_studies.md) — Fixture and non-fixture case studies.
- [PARADOX_RUNBOOK.md](PARADOX_RUNBOOK.md) — Triage when the EPF shadow disagrees with baseline.
- [paradox_gate_triage_svg_v0.md](paradox_gate_triage_svg_v0.md) — Shadow-only Paradox Gate triage SVG flow.
- [paradox_diagram_v0.md](paradox_diagram_v0.md) — Mermaid topology generation and reading.
- [PULSE_paradox_core_v0.md](PULSE_paradox_core_v0.md) — Deterministic Paradox Core projection and reviewer summary.

---

## EPF shadow and hazard diagnostics

- [PULSE_epf_shadow_quickstart_v0.md](PULSE_epf_shadow_quickstart_v0.md) — Command-level EPF shadow quickstart.
- [epf_relational_grail.md](epf_relational_grail.md) — Relational hazard overview and calibration examples.
- [epf_hazard_inspect.md](epf_hazard_inspect.md) — Inspecting `epf_hazard_log.jsonl`.

---

## Topology and field-first interpretation

- [PULSE_topology_overview_v0.md](PULSE_topology_overview_v0.md) — Diagnostic topology layer.
- [PULSE_decision_field_v0_overview.md](PULSE_decision_field_v0_overview.md) — Decision-field overview.
- [PULSE_decision_engine_v0.md](PULSE_decision_engine_v0.md) — Decision Engine outputs and semantics.
- [FIELD_FIRST_INTERPRETATION.md](FIELD_FIRST_INTERPRETATION.md) — Field-first interpretation and projection.

---

## Examples and contributing

- [examples/README.md](examples/README.md) — Reproducible examples index.
- [examples/transitions_case_study_v0/README.md](examples/transitions_case_study_v0/README.md) — Transitions to paradox field/edges case study.
- [PR_SUMMARY_TOOLS.md](PR_SUMMARY_TOOLS.md) — Canonical PR summary tooling.
- [../CONTRIBUTING.md](../CONTRIBUTING.md) — Contribution and workflow conventions.

---

## Theory and measurement protocols

- [theory_overlay_v0.md](theory_overlay_v0.md) — Theory Overlay v0 diagnostic contract.
- [time_as_consequence_v0_1.md](time_as_consequence_v0_1.md) — Workshop paper on time as consequence.
- [time_as_consequence_one_pager_v0_1.md](time_as_consequence_one_pager_v0_1.md) — One-page summary.
- [gravity_record_protocol_appendix_v0_1.md](gravity_record_protocol_appendix_v0_1.md) — Gravity Record Protocol appendix.
- [gravity_record_protocol_inputs_v0_1.md](gravity_record_protocol_inputs_v0_1.md) — Raw producer input contract.
- [gravity_record_protocol_decodability_wall_v0_1.md](gravity_record_protocol_decodability_wall_v0_1.md) — Decodability threshold and critical-radius specification.

---

## Optional layers and research surfaces

- [OPTIONAL_LAYERS.md](OPTIONAL_LAYERS.md) — Shadow workflows, overlays, experiments, and publication surfaces that do not define release outcomes by default.

### External challenge companions

- [../parameter_golf_v0/README.md](../parameter_golf_v0/README.md) — Parameter Golf v0 shadow-only evidence companion.
- [parameter_golf_submission_evidence_v0.md](parameter_golf_submission_evidence_v0.md) — Parameter Golf submission-evidence contract and reviewer receipt surface.

---

## Terminology and language rules

- [PULSE_MECHANICAL_TRANSITION_LANGUAGE_v0.md](PULSE_MECHANICAL_TRANSITION_LANGUAGE_v0.md) — Wording and review rule for preserving transition-bearing PULSEmech language.
