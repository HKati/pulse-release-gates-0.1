# Documentation index

This page is the fuller index of repository documentation.

The README documentation map is intentionally curated and entrypoint-first.

This index separates:

```text
current implementation
completed bounded proof
AI-native operating model
foundational architecture
interoperability boundary record
current operational reference
completed operational record
open implementation workstream
pending operational target
legacy diagnostic surface
historical design record
reader / audit surface
future or staged work
```

If a document is added, renamed, superseded, changes implementation status, or
moves between merged and open work, update this index.

## Status labels

- **Current implementation** — describes checked-in mechanics that are implemented and testable on the merged repository state.
- **Completed bounded proof** — records a closed, regression-proven and post-merge-reviewed mechanical relation with exact artifacts, verifier behavior, negative-path evidence and explicit claim boundaries; it does not independently create release authority.
- **AI-native operating model** — defines machine-operated traversal, reconstruction and bounded work preparation while preserving human policy and consequence control; it does not independently create release authority.
- **Foundational architecture** — defines a cross-cutting mechanical principle and reference architecture without by itself claiming completed implementation or creating release authority.
- **Interoperability boundary record** — records an exact upstream source review, lossless mapping requirement, carrier gap and authority boundary without by itself claiming implemented integration, candidate registration or release activation.
- **Current operational reference** — defines the present release-grade path and its completion boundary.
- **Completed operational record** — records an actual completed execution with concrete run identity, artifacts and verification results.
- **Open implementation workstream** — describes proposed code under review in an open pull request; it is not merged implementation, not a completed proof and not release authority.
- **Pending operational target** — describes work that has not yet been completed.
- **Legacy diagnostic surface** — remains implemented and tested, but is not the current authority or admission path.
- **Historical design record** — preserves earlier design or execution reasoning but is not the current implementation source of truth.
- **Reader / audit surface** — renders, preserves or explains state without independently creating release authority.

---

## Start here

- Canonical PULSEmech technical overview and current verified state:
  [PULSEMECH_TECHNICAL_OVERVIEW.md](../PULSEMECH_TECHNICAL_OVERVIEW.md)
- Completed Device Ledger bounded mechanical proof:
  [PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md](PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md)
  **Current implementation and completed bounded proof.** Records the exact
  Device Ledger v0 path from bounded evidence through the canonical ledger,
  signatures, deterministic `.pulseledger`, separately implemented verifier,
  positive reproduction, relevant fail-closed rejection, minimal runnable
  iPhone demonstrator, and exact artifact export. The verifier is a
  reconstruction mechanism rather than an external validating authority;
  `authority_effect = none` and `external_validation_claim = none`.
- Canonical relational release-authority interpretation:
  [PULSEMECH_RELATIONAL_RELEASE_AUTHORITY_INTERPRETATION_v0.md](PULSEMECH_RELATIONAL_RELEASE_AUTHORITY_INTERPRETATION_v0.md)
  **Canonical interpretation anchor.** Defines the specified release-state transition `τ`, the bound relation `Rτ`, the terminal transition-authority state `Dτ`, the current primary-CI carrier and enforcement role, and the reconstruction question used for external technical analysis.
- AI-native operator model:
  [PULSEMECH_TECHNICAL_OVERVIEW.md — AI-native operator model](../PULSEMECH_TECHNICAL_OVERVIEW.md#2a-ai-native-operator-model)
  **AI-native operating model.** Defines machine-readable PULSEmech state as an AI-operable proof surface while preserving human policy and consequence control and keeping release authority evidence-bound.
- Foundational transition-measurement architecture:
  [PULSEMECH_TRANSITION_METER.md](../PULSEMECH_TRANSITION_METER.md)
  **Foundational architecture.** Defines the evidence-bound transition between measured states as a separate measurement object and positions artifact-bound AI release authority as its first concrete PULSEmech implementation domain.
- Detailed compute-binding and current-run workstream state:
  [compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md](compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md)
  **Current implementation and open-workstream record.** Records the merged compute implementation through the current-run expectation validator regression and keeps the open expectation builder separate from merged state.
- Witness interoperability and release-authority boundary:
  [slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md](slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md)
  **Interoperability boundary record.** Maps the reviewed in-toto Witness mechanics into PULSEmech upstream evidence, separates Witness SLSA export from full Witness policy verification, specifies the missing structured carrier and preserves authority effect `none`.
- Running the Core PULSE lane: [QUICKSTART_CORE_v0.md](QUICKSTART_CORE_v0.md)
- Completed public Core execution record: [PULSEMECH_CORE_EXECUTION_RECORD_v0.md](PULSEMECH_CORE_EXECUTION_RECORD_v0.md)
- Completed hosted release-grade execution record: [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md)
- Current release-grade operational reference: [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md)
- Current recorded evidence verifier: [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md)
- Understanding the source of truth: [status_json.md](status_json.md)
- External PULSE review entrypoint: [PULSE_EXTERNAL_REVIEW_ENTRYPOINT_v0.md](PULSE_EXTERNAL_REVIEW_ENTRYPOINT_v0.md)
- PULSE risk-to-hardening map: [PULSE_RISK_TO_HARDENING_MAP_v0.md](PULSE_RISK_TO_HARDENING_MAP_v0.md)
- Operational triage and reruns: [RUNBOOK.md](RUNBOOK.md)

The [PULSEmech Technical Overview](../PULSEMECH_TECHNICAL_OVERVIEW.md) is the
canonical source for the checked-in implementation, current verified state,
completed proofs, open-workstream separation and present development boundary.

The
[Device Ledger bounded mechanical proof](PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md)
records the completed exact `.pulseledger` proof, separately implemented
verifier reconstruction, positive and relevant negative proof, minimal runnable
iPhone demonstrator and exact export boundary. It is a current implementation
and completed bounded proof record. It does not create release authority,
device-control authority or an external-validation claim.

The detailed
[compute-binding workstream record](compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md)
preserves the exact compute implementation sequence, current-run expectation
contract, validator proof, open builder review boundary and remaining
implementation order.

The [PULSEmech Transition Meter](../PULSEMECH_TRANSITION_METER.md) defines the
broader foundational measurement architecture. It does not supersede the
Technical Overview, claim completed cross-domain implementation or independently
create release authority.

The
[Witness interoperability and release-authority boundary](slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md)
records the exact reviewed Witness source relation merged through PR #2797 and
commit `aba0c7513ac4b99ee40fc7fb5c8a711387aa5cea`. It specifies upstream
evidence admission and the missing lossless structured carrier. It does not
claim a completed adapter, registered candidate set, workflow integration or
release-required activation.

---

## AI-native operation and implementation-state navigation

PULSEmech is not organized around the assumption that one human operator must
manually traverse and memorize the complete repository contract surface.

The operating relation is:

```text
machine-readable PULSEmech state
→ AI traversal and reconstruction
→ exact finding or bounded next mechanical action
→ human policy and consequence control
```

The machine-operable surfaces include:

```text
schemas
artifact and carrier identities
source revisions and digests
policy-defined gate sets
validators
replay records
machine-readable diagnostics
explicit authority boundaries
```

Preserve these distinctions during AI-assisted review and development:

```text
merged
≠
open

example
≠
observed

candidate
≠
active

diagnostic
≠
authority

foundational architecture
≠
completed generalized implementation
```

Use this source order:

1. [PULSEMECH_TECHNICAL_OVERVIEW.md](../PULSEMECH_TECHNICAL_OVERVIEW.md)
   Canonical system identity, merged verified state, open-workstream state and
   current development boundary.

2. Current `main` repository state
   Exact merged implementation.

3. [Device Ledger bounded mechanical proof](PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md)
   Completed bounded proof from exact evidence records through the deterministic
   `.pulseledger`, separately implemented verifier reconstruction, relevant
   fail-closed rejection, minimal runnable iPhone demonstrator and exact
   artifact export.

4. [Compute-binding workstream record](compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md)
   Detailed compute contracts, proofs, current-run expectation boundary and
   remaining sequence.

5. [Witness interoperability and release-authority boundary](slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md)
   Exact upstream Witness source review, two-lane interoperability mapping,
   structured-carrier gap and authority separation.

6. Exact open pull request, only when evaluating proposed work
   Open work remains separate from merged implementation.

7. Exact schemas, producers, validators, regressions and run-bound artifacts
   Executable contracts and concrete evidence subjects.

The AI operator may traverse, reconstruct, compare and prepare bounded work.

```text
AI-native operation
≠
AI self-authority
```

Release authority remains bound to the complete evidence, subject, artifact,
policy, verifier, materialized-gate and terminal-enforcement relation.

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
   **Current operational reference.** Defines the implemented release-grade path, advisory qualification boundary, baseline bundle boundary, complete target package and completed-run acceptance criteria.

2. [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md)
   **Current implementation.** Defines canonical candidate replay, recorded evidence verification, relation verification, manifest-declared gate admissibility, canonical verifier replay and materializer coverage boundaries.

3. [release_reference_external_evidence_integration_v1.md](release_reference_external_evidence_integration_v1.md)
   External-summary schema, envelope, signer-policy, verification-before-fold-in and failure-mode contract.

4. [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md)
   **Completed operational record.** Records PULSE CI #6066, its exact fixed-source identity, current-run hosted evidence, attestations, policy and gate bindings, public artifacts, SHA-256 digests, complete-package inventory, structural completeness and independent package verification.

5. [PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md](PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md)
   **Historical completed execution plan.** Preserves the operational path that led to PULSE CI #6066 and records that the controlled hosted-run and public-record milestones are complete.

6. [PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md](PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md)
   **Historical design record and legacy diagnostic boundary.** Not the current verifier implementation entrypoint.

---

## Orientation and contracts

- [PULSEMECH_TRANSITION_METER.md](../PULSEMECH_TRANSITION_METER.md) — **Foundational architecture.** Defines evidence-bound transition identity as the missing measurement object between measured states; the Technical Overview remains canonical for current implementation and verified state.
- [PULSEMECH_TECHNICAL_OVERVIEW.md](../PULSEMECH_TECHNICAL_OVERVIEW.md) — **Current implementation and AI-native operating model.** Canonical system identity, verified state, open-workstream separation and current development path.
- [PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md](PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md) — **Current implementation and completed bounded proof.** Records the exact Device Ledger evidence-to-carrier path, separately implemented verifier reconstruction, positive and relevant fail-closed proof, minimal runnable iPhone demonstrator, exact `.pulseledger` export, and the preserved `authority_effect = none` / `external_validation_claim = none` boundary.
- [compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md](compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md) — **Current implementation and open-workstream record.** Detailed compute contracts, completed proofs, current-run expectation contract and open builder boundary.
- [slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md](slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md) — **Interoperability boundary record.** Exact in-toto Witness source review, SLSA-export versus full-policy-verification split, proposed structured carrier and preserved PULSE release-authority boundary.
- [STATE_v0.md](STATE_v0.md) — Broad repository-state snapshot. For current release-grade and compute state, use the Technical Overview and current workstream records above.
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
- [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md) — Current recorded evidence verifier, replay, admissibility and materializer boundary.
- [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md) — Completed public hosted release-grade run record for PULSE CI #6066.
- [PULSE_TITLE_CONTINUITY_v0.md](PULSE_TITLE_CONTINUITY_v0.md) — Title-continuity provenance across repository and publication surfaces.

---

## Documentation-to-core role map

This map connects documentation to the current release-authority mechanism.

It is orienting only.

It does not create authority beyond the artifact-bound path defined by the linked contracts.

| Bucket | Core role | Primary documents |
|---|---|---|
| AI-native operation | Defines machine-operated traversal, reconstruction and bounded work preparation while preserving human policy and consequence control. AI operation does not independently create release authority. | [PULSEMECH_TECHNICAL_OVERVIEW.md](../PULSEMECH_TECHNICAL_OVERVIEW.md), [compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md](compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md) |
| Foundational transition measurement | Defines the evidence-bound transition between measured states as a separate measurement object and locates the current release-authority machine within that broader architecture. It does not itself create authority or claim generalized implementation. | [PULSEMECH_TRANSITION_METER.md](../PULSEMECH_TRANSITION_METER.md), [PULSEMECH_TECHNICAL_OVERVIEW.md](../PULSEMECH_TECHNICAL_OVERVIEW.md) |
| Device Ledger bounded mechanical proof | Records the exact bounded relation from evidence records through the canonical ledger, signatures, deterministic `.pulseledger`, separately implemented verifier reconstruction, reproducible PASS, relevant fail-closed rejection, minimal runnable iPhone demonstrator and exact artifact export. The demonstrator remains diagnostic/shadow and does not create release authority or external validation. | [PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md](PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md), [PULSEMECH_TECHNICAL_OVERVIEW.md](../PULSEMECH_TECHNICAL_OVERVIEW.md) |
| Core mechanics | Explains the connected evidence-to-decision path. | [PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md](PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md), [PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md](PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md), [PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md](PULSE_PRE_MATERIALIZATION_GATE_MECHANICS_v0.md), [PULSE_RELEASE_STATE_TRANSFORMATION_v0.md](PULSE_RELEASE_STATE_TRANSFORMATION_v0.md) |
| Authority boundary | Separates execution, approval, reader surfaces, manifests, attestations and audit sidecars from the normative authority carrier. | [PULSEMECH_ARCHITECTURE_MAP_v0_1.md](PULSEMECH_ARCHITECTURE_MAP_v0_1.md), [PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md](PULSE_RELEASE_AUTHORITY_MECHANICS_BRIDGE_v0.md), [PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md](PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md), [release_authority_boundary_v1.md](release_authority_boundary_v1.md), [MAINTAINER_AUTHORITY_BOUNDARY_v0.md](MAINTAINER_AUTHORITY_BOUNDARY_v0.md) |
| Status, policy, gate-set and workflow contracts | Defines the normative carrier tuple for final state, declared policy, workflow-effective gates, strict enforcement and primary CI outcome. | [status_json.md](status_json.md), [STATUS_CONTRACT.md](STATUS_CONTRACT.md), [GATE_SETS.md](GATE_SETS.md), [WORKFLOW_MAP.md](WORKFLOW_MAP.md), [RELEASE_DECISION_v0.md](RELEASE_DECISION_v0.md), [PULSE_RELEASE_GRADE_MATERIALIZED_LANE_v0.md](PULSE_RELEASE_GRADE_MATERIALIZED_LANE_v0.md) |
| Current verifier and evidence admission | Defines current-run candidate replay, recorded evidence verification, relation verification, gate admissibility, canonical verifier replay and verifier-bound materialization. | [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md), [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md), [release_reference_external_evidence_integration_v1.md](release_reference_external_evidence_integration_v1.md), [PULSE_EXTERNAL_EVIDENCE_MATERIALIZATION_BOUNDARY_v0.md](PULSE_EXTERNAL_EVIDENCE_MATERIALIZATION_BOUNDARY_v0.md) |
| Compute binding and current-run expectation | Maps executed compute to transition roles and preserves the merged current-run expectation contract, strict validator and registered regression while keeping the open builder separate from merged state. | [compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md](compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md), [PULSEMECH_TECHNICAL_OVERVIEW.md](../PULSEMECH_TECHNICAL_OVERVIEW.md) |
| Witness interoperability | Maps signed Witness attestations, signed Witness policy, verified functionaries, required-attestation and Rego results, and `artifactsFrom` continuity into upstream PULSE evidence. A dedicated structured carrier is specified but not implemented; Witness verification does not become PULSE release authority. | [slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md](slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md), [slsa/VSA_RELEASE_REQUIRED_PROMOTION_BOUNDARY_v0.md](slsa/VSA_RELEASE_REQUIRED_PROMOTION_BOUNDARY_v0.md), [slsa/VSA_TRUSTED_EVIDENCE_PRODUCER_DESIGN_v0.md](slsa/VSA_TRUSTED_EVIDENCE_PRODUCER_DESIGN_v0.md) |
| Legacy verifier diagnostics and historical prerequisites | Preserves the earlier failure-only verifier-report line, expectation summaries, schema drafts and relation-promotion prerequisites without presenting them as the current admission path. | [PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md](PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md), [PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md](PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md), [PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md](PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md), [PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_ONLY_DRAFT_BOUNDARY_v0.md](PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_ONLY_DRAFT_BOUNDARY_v0.md), [PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md](PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md), [PULSE_EVIDENCE_FOLD_IN_ADMISSIBILITY_v0.md](PULSE_EVIDENCE_FOLD_IN_ADMISSIBILITY_v0.md) |
| Release-grade reference and public record | Defines the completed-run contract and records the concrete first completed hosted execution. | [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md), [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md), [PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md](PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md) |
| Reader surfaces | Shows recorded state without allowing dashboards, summaries, notebooks or Pages to become authority carriers. | [quality_ledger.md](quality_ledger.md), [PULSE_PUBLIC_SURFACE_CONTRACT_v0.md](PULSE_PUBLIC_SURFACE_CONTRACT_v0.md), [PULSE_PUBLIC_PRIVATE_ARTIFACT_BOUNDARY_v0.md](PULSE_PUBLIC_PRIVATE_ARTIFACT_BOUNDARY_v0.md), [PULSE_NATIVE_REVIEW_FRAME_v0.md](PULSE_NATIVE_REVIEW_FRAME_v0.md) |
| Audit and provenance sidecars | Preserves digest-backed decision, binding, manifest, attestation-subject and cryptographic-verification state around the normative path. | [ARTIFACT_PROVENANCE_BINDING_v0.md](ARTIFACT_PROVENANCE_BINDING_v0.md), [release_authority_manifest_v0.md](release_authority_manifest_v0.md), [RELEASE_AUTHORITY_ATTESTATION_SUBJECT_v0.md](RELEASE_AUTHORITY_ATTESTATION_SUBJECT_v0.md), [RELEASE_AUTHORITY_CRYPTOGRAPHIC_BINDING_v0.md](RELEASE_AUTHORITY_CRYPTOGRAPHIC_BINDING_v0.md), [ANCHOR_INTEGRITY_v0.md](ANCHOR_INTEGRITY_v0.md) |
| Diagnostic and shadow surfaces | Keeps EPF, paradox, topology, field, overlay and shadow inventory outputs diagnostic unless explicitly admitted through declared policy and strict enforcement. | [OPTIONAL_LAYERS.md](OPTIONAL_LAYERS.md), [NORMATIVE_SHADOW_INVENTORY_MODEL_v0.md](NORMATIVE_SHADOW_INVENTORY_MODEL_v0.md), [SHADOW_ARTIFACT_COMMON_v0.md](SHADOW_ARTIFACT_COMMON_v0.md), [PULSE_epf_shadow_quickstart_v0.md](PULSE_epf_shadow_quickstart_v0.md), [PULSE_paradox_core_v0.md](PULSE_paradox_core_v0.md), [PULSE_topology_overview_v0.md](PULSE_topology_overview_v0.md), [PULSE_decision_field_v0_overview.md](PULSE_decision_field_v0_overview.md) |
| Future operational work | Collects portability, independent reproduction, HPC, later hardening and separately governed future promotion work. | [FUTURE_LIBRARY.md](FUTURE_LIBRARY.md), [FUTURE_READY_WORKMODE.md](FUTURE_READY_WORKMODE.md), [PULSE_HARDENING_BOUNDARY_MAP_v0.md](PULSE_HARDENING_BOUNDARY_MAP_v0.md), [UNREALIZED_DOCUMENTATION_PLANS_AUDIT_2026-06-05.md](UNREALIZED_DOCUMENTATION_PLANS_AUDIT_2026-06-05.md) |
| Adoption and external review | Supports operator handoff, external review, governance packets and challenge packets while preserving the authority boundary. | [PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md](PULSE_REVIEWABLE_MECHANICS_CHECKLIST_v0.md), [EXTERNAL_VERIFICATION_PATH_v0.md](EXTERNAL_VERIFICATION_PATH_v0.md), [EXTERNAL_VERIFICATION_PACKET_v0.md](EXTERNAL_VERIFICATION_PACKET_v0.md), [GOVERNANCE_PACK_v0.md](GOVERNANCE_PACK_v0.md), [OPERATOR_HANDOFF_v0.md](OPERATOR_HANDOFF_v0.md), [OUTSIDE_REVIEW_RESPONSE.md](OUTSIDE_REVIEW_RESPONSE.md), [AUTHORITY_IMPACT_AUDIT_CHECKLIST_v0.md](AUTHORITY_IMPACT_AUDIT_CHECKLIST_v0.md) |

---

## Status, ledger and external evidence

- [status_json.md](status_json.md) — Reading final release state, metrics, gates and consumers.
- [quality_ledger.md](quality_ledger.md) — Quality Ledger structure and non-authorizing reader role.
- [refusal_delta_gate.md](refusal_delta_gate.md) — Refusal-delta evidence and fail-closed semantics.
- [EXTERNAL_DETECTORS.md](EXTERNAL_DETECTORS.md) — External detector policy and advisory/gating modes.
- [external_detector_summaries.md](external_detector_summaries.md) — External detector summary integration.
- [release_reference_external_evidence_integration_v1.md](release_reference_external_evidence_integration_v1.md) — External summary schema, envelope, signer-policy and verification-before-fold-in contract.
- [AGENT_ORCHESTRATION_EVIDENCE_BRIDGE_v0.md](AGENT_ORCHESTRATION_EVIDENCE_BRIDGE_v0.md) — Boundary for agent-orchestration evidence without independent release authority.
- [slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md](slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md) — Exact Witness upstream-evidence mapping and downstream PULSE release-authority boundary.

---

## Release evidence verification

### Current implementation

- [recorded_release_evidence_verifier_v0.md](recorded_release_evidence_verifier_v0.md) — Current recorded evidence verifier, canonical replay, per-entry admissibility, materializer coverage and authority boundary.
- [release_grade_reference_run_v0.md](release_grade_reference_run_v0.md) — Current release-grade operational reference and complete-package boundary.
- [release_reference_external_evidence_integration_v1.md](release_reference_external_evidence_integration_v1.md) — External evidence contract and verification-before-fold-in surface.

### Completed operational record

- [RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md](RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md) — Completed public non-stubbed hosted release-grade run record for PULSE CI #6066, run ID `29249887581`, source commit `46b639706e23f80fe296a8893be18e2b5ab21f7e`.
- [PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md](PULSE_RELEASE_GRADE_NEXT_RUN_PLAN_v0.md) — Completed operational execution plan and preserved historical work path leading to PULSE CI #6066.

### Historical and legacy surfaces

- [PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md](PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md) — Superseded as the current implementation entrypoint; retained as a historical verifier design and legacy diagnostic-surface record.
- [PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md](PULSE_RELEASE_EVIDENCE_EXPECTATION_SUMMARY_v0.md) — Reader-only diagnostic summary for legacy pre-materialization gaps.
- [PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md](PULSE_RELEASE_EVIDENCE_RELATION_BINDING_PROMOTION_PREREQUISITES_v0.md) — Historical relation-binding promotion prerequisites.
- [PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md](PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_DELTA_MAP_v0.md) — Historical verifier schema-delta map.
- [PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_ONLY_DRAFT_BOUNDARY_v0.md](PULSE_RELEASE_EVIDENCE_TRUSTED_VERIFIER_SCHEMA_ONLY_DRAFT_BOUNDARY_v0.md) — Historical schema-only draft boundary.

---

## Witness interoperability and supply-chain verification

### Merged boundary record

- [PULSEmech Witness interoperability and release-authority boundary v0](slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md) — **Interoperability boundary record.** Merged through PR #2797 and commit `aba0c7513ac4b99ee40fc7fb5c8a711387aa5cea`.
- [SLSA/VSA release-required promotion boundary](slsa/VSA_RELEASE_REQUIRED_PROMOTION_BOUNDARY_v0.md) — Existing non-active candidate promotion boundary.
- [SLSA/VSA trusted evidence producer design](slsa/VSA_TRUSTED_EVIDENCE_PRODUCER_DESIGN_v0.md) — Existing producer identity, freshness, artifact, policy and verifier-binding design.

Reviewed upstream identities:

```text
Witness CLI:
in-toto/witness

reviewed main revision:
69402a9a630bb0a06fe969786f7f7db30d0a01a0

go-witness:
in-toto/go-witness

reviewed ref:
v0.12.0

Witness CLI dependency:
github.com/in-toto/go-witness v0.12.0
```

The Witness relation is split into two lanes:

```text
Witness SLSA export
→ possible input to the existing PULSE SLSA/VSA candidate lane
→ mapping not proven by the boundary document

full Witness policy verification
→ dedicated structured PULSEmech Witness carrier required
→ carrier specified but not implemented
```

Current state:

```text
upstream Witness attestation and policy mechanics:
reviewed and mechanically mapped

pulsemech_witness_verification_evidence_v0 schema:
not implemented

strict Witness carrier validator:
not implemented

trusted structured go-witness adapter:
not implemented

machine-produced observed proof:
not implemented

Witness candidate set:
not registered

workflow integration:
none

release-required activation:
none

release-authority effect:
none
```

Preserve the terminal distinction:

```text
Witness VerificationSummary PASSED
≠
PULSE final status

witness verify exit 0
≠
PULSE primary CI ALLOW
```

The first future implementation item, only when the Witness workstream is
explicitly selected, is:

```text
schemas/
pulsemech_witness_verification_evidence_v0.schema.json
```

---

## Compute binding and current-run export expectation

### Current merged implementation

- [Compute-binding design and implementation-state record](compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md) — Detailed workstream state synchronized through PR #2796 and merge commit `8f5f83309c920991a5223925e6084f5273a824c6`.
- [Compute-binding report schema](../schemas/pulsemech_compute_binding_report_v0.schema.json) — Strict report contract.
- [Compute-binding report validator](../tools/check_pulsemech_compute_binding_report_v0.py) — Strict report validation.
- [Reusable analyzer core](../tools/pulsemech_compute_binding_analyzer_core_v0.py) — Single graph and report implementation.
- [Fixed-source analyzer wrapper](../tools/build_pulsemech_compute_binding_report_v0.py) — Stable fixed-source compatibility path.
- [Immutable subject-input analyzer bridge](../tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py) — Same-revision packet and carrier capture over the reusable analyzer core.
- [Planned-observed relation builder](../tools/build_pulsemech_compute_planned_observed_relation_v0.py) — Deterministic relation construction.
- [Portable subject-input packet schema](../schemas/pulsemech_compute_subject_input_packet_v0.schema.json) — Exact subject, carrier, artifact, role and coverage contract.
- [Strict subject-input packet validator](../tools/check_pulsemech_compute_subject_input_packet_v0.py) — Independent reconstruction and trust-boundary enforcement.
- [Reusable subject-input producer core](../tools/pulsemech_compute_subject_input_packet_producer_core_v0.py) — Single packet-construction implementation.
- [Fixed-source subject-input wrapper](../tools/build_pulsemech_compute_subject_input_packet_v0.py) — Verified compatibility wrapper over the reusable producer core.
- [Observed #6066 subject-input packet](../examples/compute/pulsemech_compute_subject_input_packet_6066_observed_v0.json) — Machine-produced and replay-proven historical packet.
- [Current-run export expectation schema](../schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json) — Strict contract for one exact current-run subject and separate protected control plane.
- [Current-run export expectation example](../examples/compute/pulsemech_compute_current_run_export_expectation_example_v0.json) — Canonical example branch with no producer-execution claim.
- [Strict current-run expectation validator](../tools/check_pulsemech_compute_current_run_export_expectation_v0.py) — Closed schema-resolution, reviewed-byte and cross-contract validation.
- [Current-run expectation-validator regression](../tests/test_check_pulsemech_compute_current_run_export_expectation_v0.py) — Permanent registered regression for the merged validator boundary.

The merged current-run boundary is:

```text
expectation schema
+
canonical example
+
strict validator
+
validator hardening
+
permanent registered validator regression
```

It does not yet include a merged expectation builder or an active workflow.

### Open implementation workstream

- [PR #2789 — current-run export expectation builder](https://github.com/HKati/pulse-release-gates-0.1/pull/2789)
  **Open implementation workstream.** Proposed machine producer for observed current-run export expectations. It is not merged, not regression-proven, non-active and non-authoritative.

Current review boundary:

```text
protected release-target binding
release-decision schema validation
gate-registry semantic identity binding
Windows trusted-Git fail-closed or complete ACL boundary
```

Remaining sequence:

```text
builder finding closure
→ builder merge
→ permanent builder regression
→ current-run carrier component
→ current-run subject-input wrapper
→ non-active candidate workflow
→ first current-run artifact-observed connected proof
→ runtime-observation producer
→ per-axis resource measurement
→ separate promotion decision
```

A successful proof does not automatically promote a compute gate.

```text
successful proof
≠
promotion
```

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

## External analytical case studies

- [PULSEMECH_EXTERNAL_CASE_STUDY_OPENAI_HUGGING_FACE_RESTART_AUTHORITY_AND_ALTERNATIVE_PATH_CLOSURE_v0.md](PULSEMECH_EXTERNAL_CASE_STUDY_OPENAI_HUGGING_FACE_RESTART_AUTHORITY_AND_ALTERNATIVE_PATH_CLOSURE_v0.md) — **Reader / audit surface.** Primary-source-bound, non-normative external case study separating source facts, retrospective reconstruction, PULSEmech structural classification, and fail-closed counterfactual. Maps current-run evidence, transition-path verification, alternative-path closure, restart authority, and the unauthenticated `GO` operation-authority break while preserving `authority_effect: none`.

---

## Theory and measurement protocols

- [PULSEMECH_RELATION_HALF_PARADOX_MATHEMATICAL_PHYSICAL_QUANTUM_FORMULATION_v0.md](PULSEMECH_RELATION_HALF_PARADOX_MATHEMATICAL_PHYSICAL_QUANTUM_FORMULATION_v0.md) — **Reader / audit surface.** Target-relative technical formulation across mathematical systems, classical mechanics, control theory, information theory, finite-dimensional quantum mechanics and PULSEmech decision mechanics; non-normative and non-authorizing.
- [theory_overlay_v0.md](theory_overlay_v0.md) — Theory Overlay v0 diagnostic contract.
- [time_as_consequence_v0_1.md](time_as_consequence_v0_1.md) — Workshop paper on time as consequence.
- [time_as_consequence_one_pager_v0_1.md](time_as_consequence_one_pager_v0_1.md) — One-page summary.
- [gravity_record_protocol_appendix_v0_1.md](gravity_record_protocol_appendix_v0_1.md) — Gravity Record Protocol appendix.
- [gravity_record_protocol_inputs_v0_1.md](gravity_record_protocol_inputs_v0_1.md) — Raw producer input contract.
- [gravity_record_protocol_decodability_wall_v0_1.md](gravity_record_protocol_decodability_wall_v0_1.md) — Decodability threshold and critical-radius specification.

---

## Optional layers and research surfaces

- [OPTIONAL_LAYERS.md](OPTIONAL_LAYERS.md) — Shadow workflows, overlays, experiments and publication surfaces that do not define release outcomes by default.

### External challenge companions

- [../parameter_golf_v0/README.md](../parameter_golf_v0/README.md) — Parameter Golf v0 shadow-only evidence companion.
- [parameter_golf_submission_evidence_v0.md](parameter_golf_submission_evidence_v0.md) — Parameter Golf submission-evidence contract and reviewer receipt surface.

---

## Terminology and language rules

- [PULSE_MECHANICAL_TRANSITION_LANGUAGE_v0.md](PULSE_MECHANICAL_TRANSITION_LANGUAGE_v0.md) — Wording and review rule for preserving transition-bearing PULSEmech language.
