# PULSEmech — Artifact-Bound Release Authority for AI Release Decisions

## Primary public technical source

```text
document_role:
primary_public_technical_source

system:
PULSEmech

system_class:
artifact-bound_release_authority

canonical_repository:
HKati/pulse-release-gates-0.1

canonical_concept_doi:
10.5281/zenodo.17214908

canonical_path:
PULSEMECH_TECHNICAL_OVERVIEW.md

canonical_url:
https://github.com/HKati/pulse-release-gates-0.1/blob/main/PULSEMECH_TECHNICAL_OVERVIEW.md

machine_readable_url:
https://raw.githubusercontent.com/HKati/pulse-release-gates-0.1/main/PULSEMECH_TECHNICAL_OVERVIEW.md

latest_verified_state_url:
https://github.com/HKati/pulse-release-gates-0.1/blob/main/PULSEMECH_TECHNICAL_OVERVIEW.md#current-verified-state-and-latest-results
```

This document is the canonical entry point for technical analysis of PULSEmech.

It presents:

```text
system identity
complete release-transition machine within the declared policy scope
authority carriers
evidence and artifact bindings
policy materialization
deterministic verifier replay
terminal transition semantics
verified implementation state
reference proofs
external interoperability status
current development boundary
canonical source map
```

The stable link for the latest verified implementation state and completed
results is:

**[Current verified state and latest results](#current-verified-state-and-latest-results)**

---

## 1. System identity

PULSEmech is the canonical mechanical implementation of PULSE.

PULSE is one continuously evolving project identity carried through:

```text
one GitHub repository
→ one canonical concept DOI
→ successive implementation states
→ preserved proof history
```

PULSEmech is an artifact-bound release-authority mechanism for AI release
decisions.

It carries a complete downstream release-transition machine within its declared
policy scope:

```text
recorded current-run release evidence
→ exact subject, run, evidence and artifact binding
→ declared release policy
→ workflow-effective required-gate materialization
→ deterministic verifier replay
→ final gate state
→ strict fail-closed evaluation
→ ALLOW or BLOCK
```

The behavior evidence remains bound to the exact run in which it was produced.

The release permission becomes deterministic relative to:

```text
the exact recorded evidence
the exact subject and artifact identities
the exact declared policy
the exact materialized required-gate set
the exact verifier implementation and replay
the exact final status
```

The terminal result is produced before deployment and is carried as an exact
release-transition record.

---

## 2. The technical value: downstream authority closure

The technical value of PULSEmech is **downstream authority closure**.

PULSEmech supplies the decision-bearing carrier that joins evaluation,
provenance, verification and policy state to an actual release transition.

AI evaluations, detector outputs, provenance records, attestations and verifier
reports can each describe one part of a release state. PULSEmech binds those
parts into one complete transition relation.

The complete PULSEmech release-transition tuple is:

```text
R = ⟨S, E, A, P, G, V, F, D⟩
```

where:

```text
S:
exact subject and run identity

E:
recorded release evidence

A:
exact artifact and carrier identities

P:
declared release-policy identity

G:
workflow-effective materialized required-gate state

V:
verifier identity and deterministic replay state

F:
final gate-state carrier

D:
terminal ALLOW or BLOCK decision
```

PULSEmech natively carries this tuple through linked, digest-bound artifacts.

The verified path is the authority carrier:

```text
S + E + A + P + G + V + F
→ D
```

This closes the relation from recorded evidence to an enforceable release
transition.

---

## 3. The PULSEmech release-transition machine

The PULSEmech mechanism can be read as one simple machine.

### Input

```text
recorded current-run release evidence
release-candidate identity
subject-run identity
source revision
artifact inventory
declared release policy
gate registry
verifier identities
```

### Binding

```text
subject
↔ workflow run
↔ source commit
↔ release candidate
↔ evidence
↔ artifacts
↔ policy
↔ verifier
```

Every binding is carried through exact identities, paths, digests, sizes,
revisions and run keys.

### State

```text
candidate state
recorded evidence state
verified evidence state
materialized required-gate state
final status state
release-decision state
```

### Transition

```text
evidence production
→ candidate construction
→ candidate replay
→ evidence verification
→ verifier replay
→ policy-derived gate materialization
→ strict gate evaluation
```

### Output

```text
ALLOW
or
BLOCK
```

### Consequence

```text
ALLOW
→ the declared release conditions are satisfied by the bound evidence state

BLOCK
→ the declared release conditions are unsatisfied, unavailable, stale,
   mismatched, conflicting or unverifiable
```

The complete path records the reason for the terminal state.

---

## 4. Native release-authority closure

PULSEmech carries every relation required to construct, verify and replay a
terminal release transition within its declared policy scope.

The closure consists of:

```text
recorded evidence
+ exact carriers
+ exact bindings
+ declared policy
+ materialized required conditions
+ deterministic verification
+ final status
+ terminal transition
```

The mechanism contains distinct stages for:

```text
production
recording
binding
materialization
validation
reconstruction
replay
enforcement
```

Each produced record enters a separate validation and reconstruction path
before it can influence final state.

The exact implementation identity of the relevant producer, validator,
materializer and verifier is preserved beside the evidence it processes.

The complete transition can be independently replayed from its recorded
carriers.

This is the PULSEmech self-validation relation:

```text
claim
→ exact carrier
→ exact binding
→ independent reconstruction
→ verifier replay
→ policy evaluation
→ final state
→ reproduced transition
```

The completed mechanical path determines the terminal release transition.

---

## 5. Evidence, artifacts and carriers

PULSEmech treats evidence as recorded state carried by exact artifacts.

A release-evidence record contains or references:

```text
producer identity
subject-run identity
release-candidate identity
source revision
evidence type
artifact path or URI
artifact digest
artifact size
creation state
verification state
policy relation
gate relation
```

The artifact relation is explicit:

```text
evidence statement
→ exact artifact
→ exact carrier
→ exact subject run
```

Nested carriers preserve the complete package structure:

```text
preservation archive
→ provider artifact archive
→ release-grade package
→ evidence artifacts
→ status artifacts
→ decision artifacts
→ verifier reports
→ attestation records
→ reader surfaces
```

The carrier graph preserves immediate parent relations, safe member paths,
content digests, byte sizes and semantic roles.

The artifact graph enables independent reconstruction of the exact state used
by the decision path.

---

## 6. Policy and workflow-effective gate materialization

The declared policy defines which gate sets participate in a release decision.

The workflow materializes the effective required-gate set for the exact run:

```text
declared policy identity
+ active policy sets
+ gate registry
+ workflow execution context
→ workflow-effective required-gate set
```

The materialized set is carried by an exact digest and remains bound to:

```text
policy ID
policy digest
registry identity
workflow identity
subject run
release candidate
```

The final status carries the literal state of every required gate.

The strict evaluator consumes:

```text
final status
+ policy-derived require list
```

and produces the terminal result.

This preserves a direct relation:

```text
declared condition
→ materialized gate identity
→ recorded gate value
→ terminal transition
```

The policy, materialized gate set and final status therefore form one connected
state machine.

---

## 7. Deterministic verifier replay

PULSEmech records verifier identity as part of the release state.

The replay path binds:

```text
verifier source
verifier revision
verifier digest
input evidence identities
subject-run identity
policy identity
expected verification level
verification result
```

The verifier reconstructs the relevant state from exact recorded carriers.

The replay produces the same typed result for the same canonical inputs.

Required evidence states include:

```text
verified
unavailable
stale
mismatched
conflicting
untrusted
policy-inadmissible
```

The active policy determines the transition consequence of each state.

A required state outside the verified path produces `BLOCK`.

This gives PULSEmech a fail-closed terminal transition over explicit evidence
states.

---

## 8. Release authority as an artifact-bound relation

PULSEmech release authority is carried by the complete connected relation:

```text
recorded current-run evidence
→ final status
→ declared policy
→ workflow-effective materialized required-gate set
→ strict gate evaluation
→ primary CI ALLOW or BLOCK result
```

The authority-bearing transition is reproduced through exact artifact and
policy identities.

Organizational roles can define policy, supply evidence, review artifacts and
operate the workflow.

The verified mechanical path carries the final transition state.

A position can therefore participate in the system through an explicit,
reviewable and replaceable evidence path.

---

## 9. Reader, audit and publication surfaces

PULSEmech produces reader and audit surfaces from recorded state.

These surfaces include:

```text
Quality Ledger
report cards
JUnit
SARIF
Pages
workflow summaries
audit bundles
reference-run notes
package-completeness reports
package-verification reports
```

Their role is:

```text
review
reconstruction
diagnostics
traceability
publication
independent inspection
```

The release-transition tuple is carried by the evidence, policy,
materialization, verifier, final-status and decision artifacts.

Reader surfaces present selected views of that tuple.

---

## 10. Self-contained operation

PULSEmech supports a self-contained evidence floor built from its own
artifact-bound mechanics.

The controlled Tier 0 path is:

```text
required-gate evidence
→ fully produced candidate status
→ self-contained PULSE evidence floor
→ final status summary
→ release-grade artifact postconditions
→ audit sidecars
```

The completed controlled run is:

```text
workflow:
PULSE CI

run:
#5830

branch:
main

mode:
strict_external_evidence=true
llamaguard_evidence_mode=tier0_not_required

result:
PASS
```

This run proves a complete self-contained evidence floor under its declared
Tier 0 policy surface.

PULSEmech also supports a hosted external-evidence lane as a separate,
policy-selected path.

The two paths share the same downstream release-authority mechanism.

---

## 11. External evidence admission

PULSEmech exposes a policy-bound admission boundary for authenticated upstream
evidence.

An incoming record can carry:

```text
provenance
attestation
verification result
producer identity
artifact identity
subject identity
run identity
timestamp
trust identity
```

The PULSEmech admission path is:

```text
authenticated upstream record
→ exact subject and artifact binding
→ producer and verifier binding
→ trust-policy evaluation
→ active-policy admissibility
→ recorded PULSEmech evidence state
→ downstream release-transition evaluation
```

An admitted external record becomes one bound element of the complete
PULSEmech tuple `R`.

The downstream transition remains a PULSEmech policy evaluation over the full
materialized required state.

This makes external interoperability additive:

```text
external evidence source
→ PULSEmech admission
→ PULSEmech binding
→ PULSEmech policy
→ PULSEmech terminal transition
```

---

## 12. SLSA, VSA and in-toto interoperability status

PULSEmech natively carries the complete downstream release-transition tuple
within its declared policy scope:

```text
subject
+ evidence
+ artifacts
+ policy
+ materialized required gates
+ verifier replay
+ final status
+ terminal decision
```

Interoperability with another system exists when a normative carrier, or a
lossless normative mapping, preserves the complete downstream
release-transition tuple.

The current SLSA/in-toto relation is recorded as:

```text
interoperability_status:
hypothetical

interoperability_condition:
a normative carrier or lossless normative mapping that preserves the complete
downstream release-transition tuple

observed_standard_surface:
authenticated upstream provenance and verification statements

open_interoperability_surface:
the complete downstream release-transition carrier

current_exchange_state:
the complete downstream carrier or lossless mapping remains unidentified
```

The current SLSA/in-toto relation remains hypothetical because no such carrier
or lossless mapping has yet been established in the recorded exchange.

The PULSEmech implementation path proceeds through its native artifact,
policy, verifier and transition carriers.

The repository also contains an implemented SLSA/VSA evidence-intake and
trusted-producer construction-validation path.

Its current policy position is:

```text
implementation:
implemented and tested

proof:
candidate path proven

activation:
candidate-only

transition role:
policy-bound upstream evidence admission
```

This preserves the exact relationship between external evidence and downstream
PULSEmech authority.

---

## 13. Proven release-grade reference execution

The first completed public release-grade reference execution with fully produced
current-run evidence and candidate state is:

```text
workflow:
PULSE CI

run:
#6066

workflow run ID:
29249887581

run attempt:
1

source commit:
46b639706e23f80fe296a8893be18e2b5ab21f7e

source ref:
refs/heads/main

run mode:
prod

active policy sets:
required
release_required

primary gate result:
ALLOW

release decision:
PROD-PASS

workflow result:
Success
```

The completed execution preserves:

```text
current-run evidence
candidate records
recorded verifier report
final status
materialized required-gate identity
release decision
release-authority reader record
artifact-provenance binding
external evidence
attestation records
complete package
package inventory
structural completeness proof
independent package verification
```

The preserved proof includes:

```text
structural package completeness:
135 / 135

independent package verification:
157 / 157
```

The complete run is bound to one repository, source commit, workflow run,
attempt, current-run key, policy, materialized gate set, strict decision,
artifact inventory and verifier path.

Canonical record:

[Release-grade Reference Run Note v0](docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md)

---

## 14. Compute binding and transition analysis

The compute-binding workstream maps executed compute to the state transitions
it supports.

Its analysis relation is:

```text
executed compute
→ consumed input state
→ produced output state
→ downstream consumer
→ declared role
→ mutation authority
→ release-transition relation
```

The current compute classifications include:

```text
transition-bound
evidence-bound
preservation-bound
advisory-bound
unbound
unknown
observer
```

Coverage is carried explicitly for:

```text
execution identity
source identity
run binding
declared role
authority class
downstream consumption
runtime observation
resource observation
```

The fixed-source PULSE CI #6066 proof produced:

```text
expectations:
1

observations:
19

relations:
19

planned_and_observed:
1

observed_but_not_planned:
5

unresolved_due_to_coverage:
13

unbound_authoritative_mutation:
0
```

The candidate transition state derived from that exact proof is:

```text
compute_transition_path_complete:
false

compute_transition_authority_binding_ok:
false

compute_transition_unbound_mutation_absent:
true
```

These values preserve the exact available evidence and coverage.

The current compute work establishes the portable input boundary:

```text
exact subject and run identity
+ exact authority-source identities
+ immutable carrier identity
+ nested content-addressed artifact graph
+ explicit analyzer-role bindings
+ explicit coverage
→ portable compute subject-input packet
```

---

## 15. Machine-produced observed subject-input proof

The portable subject-input contract has a deterministic machine producer.

The completed proof path is:

```text
exact preserved PULSE CI #6066 carrier
→ deterministic fixed_source_adapter producer
→ record_status=observed packet
→ strict schema validation
→ strict semantic reconstruction
→ pinned historical producer replay
→ generated stdout
  = generated output
  = checked-in packet bytes
→ fail-closed replay cleanup
```

The observed packet binds:

```text
packet ID:
subject-input:pulse-ci-6066/fixed-source-adapter/851cffe9ebee9399/v0

producer revision:
3cd57dc9e88e6f804dbb134c864f4207688bddc2

producer SHA-256:
152e9ed67bf10389726ab7e27d59005afe62d23488e8cd13ffa58443bee13d18

carrier SHA-256:
7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966

carrier size:
44660 bytes

artifact records:
32

provider bindings:
3

resolved role bindings:
28
```

Completed verification:

```text
producer regression:
61 passed

observed replay regression:
24 passed

combined subject-input suite:
172 passed

strict observed-packet semantic checks:
19 / 19 true
```

The machine-produced packet is the current portable analyzer-input proof.

---

## 16. Current verified state and latest results

```text
state_date:
2026-07-25

mechanical_state_recorded_through:
PR #2763

implementation_state_basis:
f9e69485917c2a9928281f60882821b4e4606c0d

release_authority_core:
implemented, exercised and terminal

tier0_self_contained_evidence_floor:
completed and proven through PULSE CI #5830

release_grade_reference_execution:
completed and preserved through PULSE CI #6066

release_grade_package_completeness:
135 / 135

independent_package_verification:
157 / 157

slsa_vsa_recorded_intake:
implemented, tested and candidate-only

slsa_vsa_trusted_producer_chain:
implemented and tested

compute_binding_report_contract:
implemented

fixed_source_compute_binding_builder:
implemented and proven

runtime_observation_contract:
implemented

planned_observed_relation:
implemented and proven

compute_candidate_policy_surface:
implemented and candidate-only

fixed_source_candidate_chain:
implemented and proven

portable_subject_input_contract:
implemented and hardened

subject_input_packet_producer:
implemented and proven

machine_produced_observed_subject_input_packet:
implemented and replay-proven

current_development_boundary:
reusable read-only analyzer core
```

The stable URL for this state section is:

https://github.com/HKati/pulse-release-gates-0.1/blob/main/PULSEMECH_TECHNICAL_OVERVIEW.md#current-verified-state-and-latest-results

The machine-readable document URL is:

https://raw.githubusercontent.com/HKati/pulse-release-gates-0.1/main/PULSEMECH_TECHNICAL_OVERVIEW.md

### Latest completed compute proof sequence

- [PR #2749 — connect fixed-source #6066 candidate chain](https://github.com/HKati/pulse-release-gates-0.1/pull/2749)
- [PR #2752 — add portable subject-input packet contract](https://github.com/HKati/pulse-release-gates-0.1/pull/2752)
- [PR #2759 — add subject-input packet producer](https://github.com/HKati/pulse-release-gates-0.1/pull/2759)
- [PR #2760 — verify carrier identity before ZIP reads](https://github.com/HKati/pulse-release-gates-0.1/pull/2760)
- [PR #2761 — add observed #6066 subject-input packet proof](https://github.com/HKati/pulse-release-gates-0.1/pull/2761)
- [PR #2762 — fail closed on observed replay cleanup](https://github.com/HKati/pulse-release-gates-0.1/pull/2762)
- [PR #2763 — record completed observed subject-input proof](https://github.com/HKati/pulse-release-gates-0.1/pull/2763)

---

## 17. Current development path

The current mechanical transition is:

```text
portable observed subject-input packet
→ reusable read-only analyzer core
→ regression-identical subject-derived #6066 compute-binding result
```

The development sequence continues through:

```text
reusable analyzer core
→ current-run artifact-observed reference lane
→ runtime-observation producer
→ runtime-observed connected proof
→ per-axis resource measurement
→ stable measurement coverage
→ separate policy promotion decision
```

The reusable analyzer core will become the single compute-analysis implementation.

The existing #6066 fixed-source builder will become a compatibility entry point
over that core.

This preserves one analysis mechanism across:

```text
historical fixed-source subjects
current-run subjects
future runtime-observed subjects
```

---

## 18. System records and their subjects

PULSEmech records carry explicit subjects.

### System identity record

This document carries the stable technical identity and complete machine model.

```text
subject:
PULSEmech system
```

### Repository implementation-state record

The current `main` state carries the implementation presently available in the
repository.

```text
subject:
repository implementation
```

### Run-bound state record

A run `status.json` carries the gate state of one exact workflow run.

```text
subject:
one workflow run
```

### Preserved reference record

A preserved run package carries one exact historical proof.

```text
subject:
one completed historical run
```

### Reader record

A reader surface carries a selected view of recorded evidence and state.

```text
subject:
one derived presentation
```

### Candidate record

A candidate workstream record carries testable pre-activation state.

```text
subject:
one candidate policy surface
```

The subject identity determines the meaning and scope of every record.

---

## 19. Canonical source order for technical analysis

Technical analysis begins with the complete system identity, then follows the
exact state and proof carriers.

```text
1. PULSEMECH_TECHNICAL_OVERVIEW.md
   → complete system identity and current verified state

2. current main repository state
   → present implementation

3. exact workflow, policy and registry
   → active release-transition configuration

4. exact schemas, producers, validators, materializers and tests
   → machine contracts and executable mechanics

5. exact run-bound artifacts
   → state of one workflow run

6. preserved reference packages and run notes
   → historical proof

7. reader and publication surfaces
   → derived views
```

This order preserves the subject and time relation of every source.

---

## 20. Canonical source map

### System and repository entry points

- [README](README.md)
- [Documentation index](docs/INDEX.md)
- [PULSE CI workflow](.github/workflows/pulse_ci.yml)
- [Gate policy](pulse_gate_policy_v0.yml)
- [Gate registry](pulse_gate_registry_v0.yml)

### Release-authority proof

- [Release-grade Reference Run Note v0](docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md)
- [Recorded release-evidence verifier](docs/recorded_release_evidence_verifier_v0.md)
- [Release-evidence verifier design](docs/PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md)
- [Release-grade reference proof plan](docs/PULSEMECH_RELEASE_GRADE_REFERENCE_PROOF_PLAN_v0.md)

### Self-contained evidence floor

- [Tier 0 self-contained PULSE run](docs/TIER0_SELF_CONTAINED_PULSE_RUN_2026-06-27.md)
- [Tier 0 external review recalibration](docs/TIER0_EXTERNAL_REVIEW_RECALIBRATION_v0.md)

### SLSA and VSA evidence admission

- [VSA trusted evidence producer design](docs/slsa/VSA_TRUSTED_EVIDENCE_PRODUCER_DESIGN_v0.md)
- [VSA release-required promotion boundary](docs/slsa/VSA_RELEASE_REQUIRED_PROMOTION_BOUNDARY_v0.md)
- [VSA release-required promotion criteria](docs/slsa/VSA_RELEASE_REQUIRED_PROMOTION_CRITERIA_v0.md)
- [SLSA/VSA recorded-intake candidate proof](tests/test_slsa_vsa_recorded_intake_candidate_v0.py)
- [SLSA/VSA trusted-producer generated chain proof](tests/test_slsa_vsa_trusted_producer_generated_packet_report_chain_v0.py)

### Compute binding

- [Compute binding and transition efficiency design](docs/compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md)
- [Compute-binding report schema](schemas/pulsemech_compute_binding_report_v0.schema.json)
- [Compute-binding report validator](tools/check_pulsemech_compute_binding_report_v0.py)
- [Fixed-source compute-binding builder](tools/build_pulsemech_compute_binding_report_v0.py)
- [Planned-observed relation builder](tools/build_pulsemech_compute_planned_observed_relation_v0.py)
- [Runtime-observation packet schema](schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json)

### Portable subject input

- [Subject-input packet schema](schemas/pulsemech_compute_subject_input_packet_v0.schema.json)
- [Strict subject-input validator](tools/check_pulsemech_compute_subject_input_packet_v0.py)
- [Subject-input packet producer](tools/build_pulsemech_compute_subject_input_packet_v0.py)
- [Observed PULSE CI #6066 subject-input packet](examples/compute/pulsemech_compute_subject_input_packet_6066_observed_v0.json)
- [Observed packet replay proof](tests/test_pulsemech_compute_subject_input_packet_6066_observed_v0.py)

### Registered machine-test surface

- [Tools test manifest](ci/tools-tests.list)

---

## 21. State-update rule

This document carries a stable URL and an advancing verified-state section.

A completed mechanical boundary updates:

```text
current verified state
exact proof references
current development boundary
canonical source map
```

Historical proof identities remain attached to their original runs, commits,
artifacts and digests.

The stable overview therefore preserves:

```text
one system identity
+ advancing implementation state
+ immutable historical proofs
```

---

## 22. Mechanical summary

PULSEmech is a complete artifact-bound release-transition machine within its
declared policy scope.

```text
input:
recorded current-run release evidence

binding:
subject + run + artifacts + policy + verifier

state:
candidate + verified evidence + materialized required gates + final status

transition:
deterministic replay + strict fail-closed evaluation

output:
ALLOW or BLOCK

proof:
exact carriers + exact identities + independent reconstruction
```

Its technical value is the closure of the downstream authority relation:

```text
evidence
→ bound state
→ declared policy
→ materialized requirement
→ verified final state
→ enforceable release transition
```

The current implementation has completed the release-authority core, the
self-contained evidence floor, the public release-grade reference execution, the
SLSA/VSA candidate evidence path, the fixed-source compute relation, the
portable subject-input contract, the deterministic packet producer and the
machine-produced observed replay proof.

The next development boundary is the reusable read-only analyzer core.

The latest verified state remains available at the stable URL recorded at the
top of this document.
