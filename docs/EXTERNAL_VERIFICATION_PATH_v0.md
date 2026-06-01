# External Verification Path v0

## Purpose

External Verification Path v0 defines how an external reviewer can inspect and reproduce the PULSE release-authority artifact relationship without becoming part of the release-authority path.

The goal is to make the PULSE authority model externally readable, replayable, and mechanically checkable through recorded artifacts, declared policy, materialized gate sets, provenance binding, and attestation subject boundaries.

## Verification boundary

External verification is a review carrier.

It inspects the recorded release-authority artifact relationship.

It does not create an independent release decision function.

## Carrier roles

| Carrier | Artifact / path | Mechanical role |
|---|---|---|
| Authority carrier | `status.json` → declared gate policy → workflow-effective materialized required gate set → strict fail-closed CI enforcement | Carries release authority |
| Binding carrier | `artifact_provenance_binding_v0.json` | Carries digest-backed artifact relation |
| Verification carrier | `verify_artifact_provenance_binding_v0.py` | Recomputes and checks artifact relation |
| Reader carrier | Quality Ledger | Presents recorded state |
| Trace carrier | release authority manifest / release decision artifact | Preserves reconstruction and decision trace |
| Attestation subject | `artifact_provenance_binding_v0.json` | Primary subject for cryptographic attestation |
| External verification carrier | reviewer checklist / reproduction commands / verification packet | Reviews the recorded artifact relationship |

## External verification target

The external verification target is the recorded PULSE release-authority artifact relationship:

```text
recorded run identity
+ source commit identity
+ status.json
+ declared gate policy
+ workflow-effective materialized required gate set
+ strict CI gate-enforcement result
+ release-decision materialization artifact
+ Quality Ledger reader artifact
+ release authority manifest / trace artifact
+ artifact_provenance_binding_v0.json
+ binding_hash
+ optional attestation over the binding carrier
```

## Minimum artifact set

A reviewer should receive or locate the following artifacts:

```text
status.json
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
release_decision_v0.json
release_authority_v0.json
report_card.html
artifact_provenance_binding_v0.json
```

When available, the reviewer should also inspect:

```text
status_summary.json
status_summary.md
release_decision_v0_ledger_section.html
report_card.with_release_decision.html
release_authority_audit_bundle/
attestation record for artifact_provenance_binding_v0.json
```

## Verification profiles

External verification can be performed at different depths.

| Profile | Purpose | Required artifacts |
|---|---|---|
| Reader parity review | Check that public reader surfaces do not overstate authority | `status.json`, Quality Ledger |
| Authority path review | Check release decision inputs and gate enforcement path | `status.json`, policy, required gate set, `check_gates.py` semantics |
| Binding verification | Check digest-backed artifact relation | `artifact_provenance_binding_v0.json`, bound artifacts |
| Attestation review | Check attested binding carrier | binding artifact + attestation record |
| Reproducibility review | Re-run targeted tests and artifact verifiers | repo checkout + test commands |
| Release-grade review | Verify prod/materialized release-grade admissibility | status contract overlay + release-grade gates |

## External verification phases

### Phase 1 — Repository and commit identity

Verify:

```text
repository identity
source commit identity
run identity
run key
run mode
```

Expected fields may appear in:

```text
status.json
artifact_provenance_binding_v0.json
release_authority_v0.json
CI metadata
```

Mechanical boundary:

```text
external reviewer checks identity alignment
external reviewer does not redefine the release decision
```

### Phase 2 — Authority carrier inspection

Verify that the PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

Review these authority-impacting elements:

```text
pulse_gate_policy_v0.yml
pulse_gate_registry_v0.yml
required gate selection
workflow-effective required gate set
check_gates.py true-only behavior
missing required gate behavior
status schema / release-grade overlay
release-decision materialization
```

### Phase 3 — Status and policy replay

A reviewer should inspect:

```text
status.json
gates.*
metrics.run_mode
diagnostics.gates_stubbed
diagnostics.scaffold
detectors_materialized_ok
external_summaries_present
external_all_pass
required gate set
```

Mechanical checks:

```text
required gates are present
required gate values are literal true for allow
missing required gates fail closed
false / null / string / number values are not PASS
release-grade run requires prod/materialized/non-stubbed/non-scaffolded state
```

### Phase 4 — Release-decision materialization review

Verify that release-level labels come from release-decision materialization.

Expected labels:

```text
FAIL
STAGE-PASS
PROD-PASS
```

Mechanical split:

```text
check_gates.py
= strict CI gate-enforcement carrier

release_decision_v0.json / materialize_release_decision.py
= release-decision materialization carrier
```

### Phase 5 — Binding carrier verification

The binding carrier is:

```text
artifact_provenance_binding_v0.json
```

Verifier:

```text
PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
```

Expected command when artifacts are available:

```bash
python PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py \
  --binding PULSE_safe_pack_v0/artifacts/artifact_provenance_binding_v0.json
```

The verifier recomputes:

```text
status.json digest
declared policy digest
Quality Ledger digest
release-decision artifact digest
release-authority manifest digest
workflow-effective required gate-set digest
strict CI gate-enforcement digest
binding subject digests
binding_hash
```

Verification accepts only when the recorded artifact relationship matches the current artifact set.

### Phase 6 — Attestation subject review

Primary attestation subject:

```text
artifact_provenance_binding_v0.json
```

Mechanical role:

```text
artifact_provenance_binding_v0.json
= compact attestation subject for the recorded release-authority artifact relationship
```

Attestation review checks:

```text
attestation subject path
subject digest
binding_hash
attestation issuer / workflow identity
attestation event context
attestation occurs after binding verification
```

The attestation carrier verifies the binding carrier.

The binding carrier records the artifact relationship.

The authority carrier remains the PULSEmech path.

### Phase 7 — Public reader surface parity review

Review public reader surfaces for parity with recorded artifacts.

Reader surfaces include:

```text
Quality Ledger
public status URL
Pages rendering
badges
public release-decision display
```

Boundary:

```text
reader carrier ≠ authority carrier
publication carrier ≠ recorded authority artifact
trace carrier ≠ decision engine
audit bundle ≠ release decision
```

Public reader surfaces must preserve:

```text
run mode
evidence materialization state
stub/scaffold state
required gate decision display
authority carrier path
traceability fields
```

## Suggested external reviewer commands

For a repository checkout:

```bash
python -m py_compile \
  PULSE_safe_pack_v0/tools/check_gates.py \
  PULSE_safe_pack_v0/tools/render_quality_ledger.py \
  PULSE_safe_pack_v0/tools/build_artifact_provenance_binding_v0.py \
  PULSE_safe_pack_v0/tools/verify_artifact_provenance_binding_v0.py
```

Targeted tests:

```bash
python -m pytest -q tests/test_artifact_provenance_binding_v0.py
```

```bash
python -m pytest -q \
  tests/test_artifact_provenance_binding_ci_wiring_smoke.py \
  tests/test_artifact_provenance_binding_attestation_wiring_smoke.py
```

```bash
python -m pytest -q \
  tests/test_render_quality_ledger.py::test_q1_reference_shadow_section_renders_when_present \
  tests/test_render_quality_ledger_public_surface_state.py
```

Tools manifest coherence:

```bash
python tests/test_tools_tests_list_smoke.py
```

These commands are reviewer aids.

They do not replace the recorded CI run.

## External verification checklist

A reviewer should answer:

```text
Repository / commit identity aligned: yes / no
Run identity aligned: yes / no
status.json present and parseable: yes / no
Declared gate policy present: yes / no
Workflow-effective required gate set reconstructable: yes / no
Required gates literal true for allow: yes / no
Release-decision artifact present: yes / no
Release label valid: yes / no
Quality Ledger parity preserved: yes / no
Release authority manifest present: yes / no
Artifact provenance binding present: yes / no
Binding verifier passes: yes / no
Attestation subject is artifact_provenance_binding_v0.json: yes / no
Attestation exists when expected: yes / no
Public reader surface boundary preserved: yes / no
```

## External verification report format

A minimal external verification report should include:

```text
Reviewer:
Date:
Repository:
Commit:
Run identity:
Artifact set inspected:
Verification profile:
Commands run:
Binding verification result:
Attestation review result:
Public reader parity result:
Authority-impact findings:
Residual issues:
Conclusion:
```

## External verification status classes

| Status | Meaning |
|---|---|
| Verified | Artifact relationship verified and no blocking mismatch found |
| Partially verified | Some artifact relation verified, but artifact set or attestation incomplete |
| Reader-only verified | Public reader surface matches recorded artifacts, but authority artifact replay not completed |
| Binding mismatch | Binding digest or subject mismatch found |
| Authority mismatch | Recorded authority path cannot be reconstructed from supplied artifacts |
| Inconclusive | Required artifacts unavailable |

## Integration boundary

External verification can produce:

```text
review report
reproduction note
case study
third-party reference integration
audit finding
```

External verification does not alter:

```text
status.json
declared gate policy
materialized required gate set
check_gates.py behavior
CI allow/block result
release decision materialization
artifact_provenance_binding_v0.json
attestation record
```

## Future extension

A later PR may add a machine-readable external verification packet:

```text
external_verification_packet_v0.json
```

Potential contents:

```text
repository
commit
run identity
artifact paths
artifact digests
verification commands
expected results
binding hash
attestation subject
reviewer note
```

That future packet should remain a review carrier.

It must not become an independent release-decision engine.

## Boundary held by this document

External Verification Path v0 defines the review path for external verification.

It does not change:

```text
PULSEmech decision semantics
gate policy
required gate wiring
check_gates.py behavior
status schema
CI allow/block behavior
Quality Ledger renderer behavior
artifact provenance binding behavior
attestation workflow behavior
release tags
DOI / Zenodo path
```

The PULSEmech authority carrier remains:

```text
status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
```

The external verification carrier reviews that recorded artifact relationship.
