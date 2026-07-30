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

The terminal result is produced before deployment and is carried by the primary
CI enforcement outcome. A passing strict gate evaluation continues into exact
release-decision and proof carriers. A gate-closing evaluation is terminal at
the primary CI enforcement step.

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
terminal primary-CI ALLOW or BLOCK enforcement result
```

PULSEmech natively carries `S` through `F` through linked, digest-bound
artifacts. `D` is carried by the primary CI terminal result.

The current `hosted_full_runtime` release-grade workflow carries the two terminal paths as:

```text
strict gate evaluation passes
→ primary CI ALLOW
→ release_decision_v0.json materialization
→ digest-bound final proof carriers

strict gate evaluation closes
→ primary CI BLOCK
→ terminal non-zero CI enforcement result
```

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
terminal primary-CI enforcement state
release-decision artifact state on fully materialized paths
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

The canonical recorded release-evidence verifier emits one of two result
states at report, evidence, relation and gate-admissibility level:

```text
verified
failed
```

A `failed` result carries exact diagnostics in its `errors` collection and
field-level verification results. These diagnostics identify conditions such
as:

```text
missing or unreadable artifact
JSON or schema failure
digest mismatch
run-identity mismatch
subject-binding mismatch
policy-binding mismatch
canonical replay mismatch
raw-evidence mismatch
relation-binding failure
gate-materialization inadmissibility
```

The active policy consumes the verified admissibility result. A required
`failed` result closes the transition and produces `BLOCK`.

This gives PULSEmech a fail-closed terminal transition over the verifier's
actual two-state result contract and its exact diagnostics.

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

The evidence, policy, materialization, verifier and final-status artifacts
carry `S` through `F`. The primary CI terminal result carries `D`. In the
current `hosted_full_runtime` release-grade workflow, a passing strict gate evaluation
continues into `release_decision_v0.json` and the later digest-bound proof
carriers.

Reader surfaces present selected views of that relation.

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

PULSEmech natively carries the complete downstream release-transition relation
within its declared policy scope:

```text
subject
+ evidence
+ artifacts
+ policy
+ materialized required gates
+ verifier replay
+ final status
+ terminal primary-CI decision
```

The linked artifact chain carries the relation through final status. The
primary CI terminal result carries the decision. On the current fully
materialized release-grade ALLOW path, the same decision is also preserved in
`release_decision_v0.json` and the subsequent proof carriers.

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

The machine-produced packet is the portable analyzer-input record used by the
immutable analyzer bridge.

---

## 15A. Immutable observed subject-input analyzer bridge

The machine-produced observed packet was first connected to the then-monolithic
compute-binding analyzer through one immutable-input bridge.

The completed PR #2773 relation was:

```text
portable observed subject-input packet
+ exact preservation carrier
→ secure immutable packet and carrier capture
→ strict packet validation over captured bytes
→ existing artifact reconstruction
→ then-current fixed-source analyzer implementation
→ strict report validation
→ deterministic stdout report
```

The bridge captures the packet, carrier, schemas and validators through POSIX
no-follow file operations.

Each captured input is bound to:

```text
exact bytes
device identity
inode identity
byte size
SHA-256
```

Validation and analysis consume the same captured packet revision.

Validation, artifact reconstruction and report construction consume the same
captured carrier revision.

The in-memory carrier view deliberately has no filesystem-path conversion
surface. Delegated code therefore consumes captured bytes instead of reopening
the mutable packet or carrier pathname.

The historical PR #2773 proof was:

```text
implementation PR:
#2773

merge commit:
a93359444e13771eb932744dd22b4477a5096019

bridge version:
0.2.0

focused regression:
17 passed

direct tools-manifest execution:
17 passed

historical pre-core-extraction report SHA-256:
656459e7fb835814a05a7cc5b8150959d32ed3a0e9ed272c2733038bd441ec4c

repeated report digest:
identical

repository state before and after replay:
clean

changed-file boundary:
exactly 3 files

tools-test registration:
exactly 1

parallel analyzer implementation:
none

post-merge review:
PASS

post-merge correction required:
none
```

The report digest above belongs to the pre-core-extraction implementation
identity. It is retained as a historical proof identity and is not reused as the
current wrapper-plus-core report identity.

The bridge has no:

```text
temporary directory
scratch-file extraction
optional file output
output rename
repository-local bytecode generation
```

PR #2773 completed the portable-input-to-existing-analyzer equivalence
boundary.

PR #2776 then separated the stable producer entry point from the reusable
analyzer implementation while preserving the immutable bridge relation.

---

## 15B. Reusable read-only analyzer core

The proven compute-binding implementation is now carried by one reusable
analyzer core.

The completed extraction is:

```text
previous monolithic fixed-source analyzer
→ repository rename preserving the analyzer implementation
→ tools/pulsemech_compute_binding_analyzer_core_v0.py

stable fixed-source path
→ thin compatibility wrapper
→ tools/build_pulsemech_compute_binding_report_v0.py

immutable observed subject-input packet
→ immutable subject-input bridge
→ the same reusable analyzer core
```

The reusable core is the only implementation location for:

```text
build_report
make_compute_node
make_state_node
make_edge
finding construction
binding classification
summary construction
deterministic report construction
```

The fixed-source compatibility wrapper and immutable subject-input bridge do
not carry a second graph or report implementation.

The current delegation relation is:

```text
fixed-source #6066 inputs
→ fixed-source compatibility wrapper
→ reusable analyzer core
→ compute-binding report

immutable observed subject-input packet
→ immutable subject-input bridge
→ reusable analyzer core
→ byte-identical compute-binding report
```

The extraction separates two exact source identities:

```text
report producer identity:
tools/build_pulsemech_compute_binding_report_v0.py

report producer SHA-256:
d20cb7fed3d8c1ddc10abc23882ce0cbe17d277498016a580f875614fe47becc

analyzer implementation identity:
tools/pulsemech_compute_binding_analyzer_core_v0.py

analyzer implementation SHA-256:
cd108bc70494203f95a3f379f6e0d953331d10357676d553d6858f44729988dd
```

The report top-level tool identity is bound to the compatibility wrapper.

The `compute:offline-observer` source identity is bound to the reusable analyzer
core.

Therefore:

```text
report producer identity
≠ analyzer implementation identity

fixed-source wrapper
+ immutable subject-input bridge
→ one analyzer implementation identity
```

The completed proof is:

```text
implementation PR:
#2776

squash-merge commit:
e06acbbcd0beec7846da01322659079171e24562

changed-file boundary:
exactly 6 files

fixed-source regression:
33 passed

analyzer-core regression:
10 passed

immutable subject-input bridge regression:
18 passed

wrapper and bridge report bytes:
identical

direct-core and wrapper analysis payload:
identical after normalizing only producer-entry-point identity

wrapper, bridge and core execution:
repository and tools tree remained clean

post-merge review:
PASS

major findings:
none

correction required:
none
```

The production subject-input validator retains its strict trusted-Git policy.

Hosted-runner ownership normalization exists only in regression code, activates
only after the exact `non_root_owned_component` diagnostic, and does not weaken
the production validation path.

The extraction boundary is single implementation ownership. The reusable core
retains the established fixed-source input and CLI support required by the
compatibility path; no claim is made that a separate pure-function kernel has
also been created.

The post-merge reviewer could not run:

```text
git cat-file -t c6236512b52d7a0dbf5152421766e3008a8be9bf
```

because the superseded PR-head object was not present in that local checkout and
no Git remote was configured.

This was not a merged-artifact failure.

`git cat-file` inspects only the local Git object database. The canonical review
target was the squash-merge commit
`e06acbbcd0beec7846da01322659079171e24562`, whose exact six-file boundary and
merged relations were independently verified.

This completed core extraction does not implement the current-run
artifact-observed reference lane, runtime-observation production, resource
measurement, a compute budget, active compute enforcement or release authority.

---

## 16. Current verified state and latest results

```text
state_date:
2026-07-30

mechanical_state_recorded_through:
PR #2776

implementation_state_basis:
e06acbbcd0beec7846da01322659079171e24562

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

fixed_source_compute_binding_path:
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

immutable_subject_input_analyzer_bridge:
implemented and post-merge proven

historical_pre_core_bridge_report_sha256:
656459e7fb835814a05a7cc5b8150959d32ed3a0e9ed272c2733038bd441ec4c

reusable_analyzer_core:
implemented and post-merge proven

fixed_source_compatibility_wrapper:
implemented and proven

subject_input_bridge_to_reusable_core:
implemented and proven

fixed_source_regression:
33 passed

analyzer_core_regression:
10 passed

subject_input_bridge_regression:
18 passed

fixed_source_wrapper_sha256:
d20cb7fed3d8c1ddc10abc23882ce0cbe17d277498016a580f875614fe47becc

analyzer_core_sha256:
cd108bc70494203f95a3f379f6e0d953331d10357676d553d6858f44729988dd

current_run_artifact_observed_reference_lane:
not implemented

current_development_boundary:
current-run artifact-observed reference lane
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
- [PR #2773 — add immutable observed subject-input analyzer bridge](https://github.com/HKati/pulse-release-gates-0.1/pull/2773)
- [PR #2776 — extract reusable analyzer core](https://github.com/HKati/pulse-release-gates-0.1/pull/2776)

---

## 17. Current development path

The completed analyzer relation is:

```text
historical fixed-source #6066 inputs
→ fixed-source compatibility wrapper
→ reusable analyzer core
→ compute-binding report

portable observed subject-input packet
→ immutable subject-input bridge
→ the same reusable analyzer core
→ byte-identical compute-binding report
```

The reusable analyzer core is now the single implementation location for graph,
node, edge, finding, classification, summary and report construction.

The current mechanical transition is:

```text
current workflow run
→ machine-produced current-run subject-input packet
→ immutable current-run carrier binding
→ reusable analyzer core
→ generated artifact-observed report
→ generated planned-observed relation
→ non-active candidate materialization
```

The current-run artifact-observed reference lane must reuse:

```text
the existing subject-input packet contract
the existing immutable capture boundary
the existing subject-input validator
the existing reusable analyzer core
the existing compute-binding report validator
the existing planned-observed relation builder
the existing non-active candidate boundary
```

It must not introduce:

```text
a second analyzer
a manually curated packet
a second graph implementation
a new release-authority path
automatic candidate promotion
runtime-observed claims without runtime evidence
```

The development sequence then continues through:

```text
current-run artifact-observed reference lane
→ runtime-observation producer
→ runtime-observed connected proof
→ per-axis resource measurement
→ stable measurement coverage
→ separate policy promotion decision
```

This preserves one analysis mechanism across:

```text
historical fixed-source subjects
portable observed subject packets
current-run subjects
future runtime-observed subjects
```

The current-run lane remains non-active and has no release-authority effect.

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
- [Reusable compute-binding analyzer core](tools/pulsemech_compute_binding_analyzer_core_v0.py)
- [Fixed-source compatibility wrapper](tools/build_pulsemech_compute_binding_report_v0.py)
- [Immutable subject-input analyzer bridge](tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py)
- [Analyzer-core regression](tests/test_pulsemech_compute_binding_analyzer_core_v0.py)
- [Immutable bridge regression](tests/test_build_pulsemech_compute_binding_report_from_subject_input_v0.py)
- [Planned-observed relation builder](tools/build_pulsemech_compute_planned_observed_relation_v0.py)
- [Runtime-observation packet schema](schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json)

### Portable subject input

- [Subject-input packet schema](schemas/pulsemech_compute_subject_input_packet_v0.schema.json)
- [Strict subject-input validator](tools/check_pulsemech_compute_subject_input_packet_v0.py)
- [Subject-input packet producer](tools/build_pulsemech_compute_subject_input_packet_v0.py)
- [Observed PULSE CI #6066 subject-input packet](examples/compute/pulsemech_compute_subject_input_packet_6066_observed_v0.json)
- [Observed packet replay proof](tests/test_pulsemech_compute_subject_input_packet_6066_observed_v0.py)
- [Packet-to-analyzer equivalence proof](tests/test_build_pulsemech_compute_binding_report_from_subject_input_v0.py)

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
portable subject-input contract, the deterministic packet producer, the
machine-produced observed replay proof, the immutable subject-input analyzer
bridge and extraction of one reusable analyzer implementation core shared by
the fixed-source and portable-input paths.

The next development boundary is the current-run artifact-observed reference
lane over the existing packet, immutable-capture, analyzer-core, report and
candidate mechanisms.

The latest verified state remains available at the stable URL recorded at the
top of this document.
