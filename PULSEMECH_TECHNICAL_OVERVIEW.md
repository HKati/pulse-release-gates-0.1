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
AI-native operator model
complete release-transition machine within the declared policy scope
authority carriers
evidence and artifact bindings
policy materialization
deterministic verifier replay
terminal transition semantics
verified implementation state
reference proofs
compute-binding implementation state
current-run compute automation state
completed historical post-run producer-input capture
Device Ledger bounded proof, deterministic Reproduction Capsule, and runnable demonstrator state
foundational transition-measurement architecture
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
CI enforcement outcome.

A passing strict gate evaluation continues into exact release-decision and
proof carriers.

A gate-closing evaluation is terminal at the primary CI enforcement step.

---

## 2. The technical value: downstream authority closure

The technical value of PULSEmech is **downstream authority closure**.

PULSEmech supplies the decision-bearing carrier that joins evaluation,
provenance, verification and policy state to an actual release transition.

AI evaluations, detector outputs, provenance records, attestations and verifier
reports can each describe one part of a release state.

PULSEmech binds those parts into one complete transition relation.

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
artifacts.

`D` is carried by the primary CI terminal result.

The current `hosted_full_runtime` release-grade workflow carries the two
terminal paths as:

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

## 2A. AI-native operator model

PULSEmech is not designed around the assumption that one human operator must
manually traverse, memorize and operate its complete contract surface.

The repository carries:

```text
machine-readable schemas
exact artifact identities
exact source revisions
policy-defined gate sets
deterministic validators
reconstructable evidence graphs
machine-readable diagnostics
explicit authority boundaries
```

These surfaces are suitable for AI-native operation.

The intended operating relation is:

```text
machine-readable PULSEmech state
→ AI traversal and reconstruction
→ exact finding or next mechanical action
→ human review of policy, boundary and consequence
```

The AI-native operator may:

```text
locate the canonical contract
resolve the current implementation state
traverse the artifact graph
compare declared and observed identities
reconstruct policy-derived requirements
run or prepare deterministic verification
identify the exact broken relation
prepare bounded corrective work
preserve the distinction between merged, open and hypothetical state
```

The human does not need to replace this machine traversal with manual
administration.

The human role remains:

```text
define or approve policy
define the governed consequence
review changes to authority-bearing mechanics
review unresolved or conflicting evidence
control external execution and promotion
```

This separates two concepts:

```text
mechanical detail
≠
human manual-operational burden
```

and:

```text
AI-native operation
≠
AI self-authority
```

The AI operator does not become release authority merely because it can read,
reconstruct or operate the mechanism.

Release authority remains bound to:

```text
exact evidence
+ exact subject and run
+ exact artifacts
+ declared policy
+ materialized required gates
+ verifier replay
+ strict terminal enforcement
```

A machine or AI may operate the proof surface.

It cannot replace the proof surface with its own declaration.

The current repository implements the machine-readable contracts,
deterministic tools and evidence relations required for this operating model.

This section does not claim that a separate autonomous AI control-plane
component has been implemented.

```text
AI-native operator model:
architectural and operational model

autonomous AI release authority:
absent

release-authority effect of this model:
none
```

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

The final gate checker accepts only literal JSON `true` for every required gate.

```text
required gate missing
→ fail closed

required gate present but not literal true
→ fail closed

all required gates literal true
→ gate check passes
```

This preserves a direct relation:

```text
declared condition
→ materialized gate identity
→ recorded gate value
→ terminal transition
```

The policy, materialized gate set and final status therefore form one connected
state machine.

Measurement and terminal enforcement remain separate layers:

```text
measurement or evidence production
≠
terminal gate enforcement
```

The terminal checker does not create a measurement result.

It evaluates the already materialized required state.

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
field-level verification results.

These diagnostics identify conditions such as:

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

The active policy consumes the verified admissibility result.

A required `failed` result closes the transition and produces `BLOCK`.

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

AI-native operators can traverse, reconstruct and prepare the same relation.

The verified mechanical path carries the final transition state.

A person, role or AI process can therefore participate only through an
explicit, reviewable and replaceable evidence path.

No position or process can substitute its own status for the verified
mechanical relation.

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
carry `S` through `F`.

The primary CI terminal result carries `D`.

In the current `hosted_full_runtime` release-grade workflow, a passing strict
gate evaluation continues into `release_decision_v0.json` and the later
digest-bound proof carriers.

Reader surfaces present selected views of that relation.

They do not independently create release authority.

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

The linked artifact chain carries the relation through final status.

The primary CI terminal result carries the decision.

On the current fully materialized release-grade ALLOW path, the same decision is
also preserved in `release_decision_v0.json` and the subsequent proof carriers.

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

The first completed public release-grade reference execution with fully
produced current-run evidence and candidate state is:

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
surface.

Delegated code therefore consumes captured bytes instead of reopening the
mutable packet or carrier pathname.

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
identity.

It is retained as a historical proof identity and is not reused as the current
wrapper-plus-core report identity.

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

The proven compute-binding implementation is carried by one reusable analyzer
core.

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

The extraction boundary is single implementation ownership.

The reusable core retains the established fixed-source input and CLI support
required by the compatibility path.

No claim is made that a separate pure-function kernel has also been created.

The post-merge reviewer could not run:

```text
git cat-file -t c6236512b52d7a0dbf5152421766e3008a8be9bf
```

because the superseded PR-head object was not present in that local checkout and
no Git remote was configured.

This was not a merged-artifact failure.

`git cat-file` inspects only the local Git object database.

The canonical review target was the squash-merge commit
`e06acbbcd0beec7846da01322659079171e24562`, whose exact six-file boundary and
merged relations were independently verified.

---

## 15C. Reusable subject-input producer core

The fixed-source subject-input packet producer now delegates to one reusable
producer core.

The completed PR #2778 structure is:

```text
tools/pulsemech_compute_subject_input_packet_producer_core_v0.py
→ single packet-construction implementation

tools/build_pulsemech_compute_subject_input_packet_v0.py
→ stable fixed-source compatibility wrapper

FIXED_SOURCE_6066_PROFILE
→ explicit historical fixed-source producer profile
```

The reusable producer core remains the single implementation location for:

```text
carrier verification
artifact reconstruction
role binding
subject reconstruction
authority-source reconstruction
coverage derivation
packet construction
canonical rendering
semantic validation
output writing
```

The fixed-source wrapper does not carry a second packet-production
implementation.

The completed relation is:

```text
fixed-source compatibility wrapper
→ reusable producer core
→ packet A

direct reusable producer core
+ explicit FIXED_SOURCE_6066_PROFILE
+ identical source and execution bindings
→ packet B

packet A bytes
=
packet B bytes
```

The merged implementation is:

```text
implementation PR:
#2778

squash-merge commit:
951dd5c968a72ba86ae8cde2e1fa3d36434832b8
```

The historical PULSE CI #6066 observed packet and its original producer revision
remain preserved.

The producer-core extraction does not implement current-run production,
workflow activation, runtime observation, compute budgeting, candidate-gate
activation or release authority.

---

## 15D. Pre-execution wrapper-to-core trust bootstrap

PR #2783 moved committed producer-core verification into the stable wrapper's
pre-execution bootstrap.

The completed trust path is:

```text
literal wrapper invocation path
→ wrapper and parent-component symlink checks
→ approved absolute Git selection
→ exact repository HEAD
→ exact committed wrapper blob
→ exact committed producer-core blob
→ one secure producer-core byte capture
→ SHA-256
→ compilation
→ execution
```

The same verified core byte buffer is used for:

```text
committed-byte comparison
SHA-256 calculation
compilation
execution
```

This prevents the wrapper from verifying one core revision and executing
another mutable pathname revision.

The merged implementation is:

```text
implementation PR:
#2783

squash-merge commit:
04d5b03007ce01435f4ec83345ff6e1aa76d6d7e
```

The hardened path rejects:

```text
uncommitted top-level core code
wrapper symlink aliases
parent-path symlink aliases
core symlinks
caller-PATH Git substitution
caller-PATHEXT Git substitution
```

This boundary preserves one producer implementation and one exact committed
execution identity.

It does not implement current-run production or release authority.

---

## 15E. Current-run export expectation contract

The current-run artifact-observed lane now contains a merged expectation
contract.

The contract sequence is:

```text
PR #2784
→ strict current-run export expectation schema

PR #2785
→ canonical checked-in expectation example

PR #2786
→ strict semantic validator

PR #2787
→ validator trust-boundary hardening

PR #2788
→ permanent registered validator regression
```

The exact merged implementation bases are:

```text
schema:
PR #2784
b010d52bffa9a5fc43b157dac7e9f5863cf008dc

example:
PR #2785
6f4f66c159604bce2e45889d46958651610cd958

validator:
PR #2786
bf2c7886529a45286bb61bae552a292e7619eeeb

validator hardening:
PR #2787
57b2c3bc2ac3582e1956c1e3a109fcb71f827ca2

validator regression:
PR #2788
031e0f2b009993e549b7831baf37cf3a990baf39
```

The current-run expectation contract binds:

```text
one exact current workflow-run subject
one exact subject source revision
one separate protected control plane
one exact protected control-plane revision
one expected current-run producer profile
one finalized current-run export carrier identity
one archive-layout contract
one complete authority-source set
one downstream observed subject-input packet contract
```

The schema separates:

```text
checked-in example
≠
machine-produced observed expectation
```

The example branch requires:

```text
record_status:
example

fixture_provenance:
present

expectation_producer:
absent

carrier producer:
null
```

The observed branch requires:

```text
record_status:
observed

fixture_provenance:
absent

expectation_producer:
present

carrier producer:
present

expectation scope:
current_run_export
```

The sole authoritative finalized-carrier digest is:

```text
carrier.sha256
```

The expectation identity does not carry a second competing carrier digest.

The protected control plane carries nine required roles:

```text
carrier_loader
control_plane_workflow
expectation_builder
expectation_schema
expectation_validator
subject_input_producer_core
subject_input_producer_wrapper
subject_input_schema
subject_input_validator
```

The contract states:

```text
subject_may_select_revision:
false

separate_from_subject_checkout:
true

trust_mode:
protected_exact_revision
```

The content boundary remains:

```text
expectation_payload_mode:
metadata_only

contains_artifact_payloads:
false

contains_runtime_observation:
false

contains_resource_measurement:
false

contains_secret_material:
false

consumer_must_verify_carrier_bytes:
true
```

The authority boundary remains:

```text
write_mode:
expectation_only

creates_release_decision:
false

creates_gate_result:
false

activates_compute_gate:
false

creates_compute_budget:
false

expectation_is_release_authority:
false

produced_packet_is_release_authority:
false
```

---

## 15F. Strict current-run expectation validation

The strict validator verifies the current-run expectation as a complete
cross-contract relation.

Its validation surface includes:

```text
strict UTF-8 JSON
duplicate-key rejection
non-finite-number rejection
canonical serialization
expectation-schema validity
expectation-instance validity
subject-input-schema validity
closed schema-reference policy
downstream observed-branch realizability
subject-run identity
workflow reference
policy and registry binding
authority-source identity
protected control-plane component relations
producer-profile binding
carrier identity relations
archive-layout relations
content boundary
authority boundary
deterministic diagnostic output
```

The hardened validator:

```text
rejects external schema references before validator construction
preserves a deny-all runtime resolver boundary
follows internal references into reached schema objects
separates canonical path identity from reviewed blob identity
calculates schema identity from captured bytes
keeps expectation and downstream schema states independent
validates a complete downstream observed packet witness
converts resolver and schema failures into deterministic diagnostics
```

The validator distinguishes:

```text
supplied contract validity
≠
canonical reviewed-contract verification
```

It reports the stronger canonical verification state only when both canonical
path identity and reviewed schema-blob identity match.

The permanent regression is registered in:

```text
ci/tools-tests.list
```

The regression covers:

```text
deterministic raw diagnostic bytes
CRLF normalization rejection
strict parser failures
canonical serialization
symlinked input rejection
invalid repository-root rejection
closed modern Registry resolution
closed RefResolver compatibility resolution
network and local-file retrieval denial
internal JSON Pointer and anchor handling
dirty canonical schema rejection
alternate-path schema rejection
complete observed expectation construction
producer-binding mismatch rejection
POSIX descriptor-chain state
path-based fallback state
```

This merged boundary establishes:

```text
strict current-run expectation contract
+
canonical example
+
strict validator
+
closed schema-resolution boundary
+
reviewed schema-byte binding
+
permanent registered regression
```

That contract-and-validator milestone did not itself implement a machine
producer. The current-run expectation builder and its permanent regression
were subsequently completed within the Step 3G implementation sequence recorded
in Sections 16–17. The historical contract boundary above is not a claim that
the current merged builder is absent.

---

## 15G. Foundational Transition Meter relation

The PULSEmech Transition Meter is the broader foundational architecture within
which artifact-bound AI release authority is the first concrete implementation
domain.

The foundational relation is:

```text
measured source state
→ changed relation
→ opened, closed or redirected path
→ measured target state
```

bound to:

```text
state identity
relation identity
path identity
time binding
boundary binding
measurement provenance
evidence binding
verifier binding
alternative paths
unresolved links
reproduction state
authority state
```

The central distinctions are:

```text
measured state
≠
measured transition

measured state difference
≠
transition identity

observed consequence
≠
measured initiating transition

measured endpoints
≠
verified transition path
```

The foundational architecture was merged through:

```text
PR #2790:
PULSEmech Transition Meter
44ac739196eeac75996040a335bb6e79a9132a70

PR #2794:
README transition-measurement positioning
b324e733296c200c7d9b799463414c82e533a921

PR #2816:
Transition-bounded computation architecture
3bb6a8cce2c88ae1495639d9e85c95a07b295f1e

PR #2817:
Reviewed transition-bounded computation architecture
fbfa9b0c03003eef93b23489ab7cb6cc72a9edeb
```

The Transition Meter preserves separate status axes for:

```text
observation
binding
consistency
reproduction
causal state
authority
```

No one scalar record status may silently replace those dimensions.

The Transition Meter does not supersede the current Technical Overview.

```text
PULSEMECH_TRANSITION_METER.md
→ foundational transition-measurement architecture

PULSEMECH_TECHNICAL_OVERVIEW.md
→ canonical checked-in implementation and verified-state overview
```

The generalized cross-domain Transition Meter remains foundational
architecture.

It does not independently create release authority.

---

## 15H. Device Ledger bounded proof, deterministic Reproduction Capsule, and runnable iPhone demonstrator

The repository contains a completed bounded Device Ledger proof for one exact
synthetic reference relation and a completed deterministic reproduction layer
around that proof.

The closed mechanical relation is:

```text
bounded observed relation
→ exact evidence records
→ predecessor-bound record chain
→ terminal checkpoint
→ canonical ledger
→ checkpoint signature
→ exact payload inventory
→ canonical manifest
→ package signature
→ deterministic .pulseledger
→ separately implemented verifier reconstruction
→ reproducible PASS or fail-closed rejection
→ minimal runnable iPhone result surface
→ exact artifact export
→ exact Capsule-manifest schema and normative contract
→ deterministic four-member ZIP_STORED Reproduction Capsule
→ two isolated byte-identical Capsule constructions
→ two exact positive standalone-verifier executions
→ isolated CRC-consistent package-signature mutation
→ exact package_signature_valid rejection
→ canonical reproduction result
→ protected-source preservation
```

The canonical detailed proof record is:

[PULSEmech Device Ledger Bounded Mechanical Proof v0](docs/PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md)

The distinct reviewer and operator procedure is:

[External Verification Path v0](docs/EXTERNAL_VERIFICATION_PATH_v0.md)

The proof record defines what the completed relation proves.

The External Verification Path defines how a reviewer or operator may inspect,
replay, or reproduce that relation without becoming an input to its mechanical
validity and without creating a second verifier or authority path.

This overview records the synchronized implementation state. It does not replace
the canonical proof record or the executable contracts.

### Merged proof chain

| Layer | Pull request | Merged commit |
|---|---:|---|
| Minimal runnable iPhone bounded proof demonstrator | [#2847](https://github.com/HKati/pulse-release-gates-0.1/pull/2847) | [`6a358187d8fde7321963b76cc50cc77fad695dd0`](https://github.com/HKati/pulse-release-gates-0.1/commit/6a358187d8fde7321963b76cc50cc77fad695dd0) |
| Canonical bounded mechanical proof record | [#2848](https://github.com/HKati/pulse-release-gates-0.1/pull/2848) | [`d2be905bbdf281cb4adff97b98618340d5ca5c39`](https://github.com/HKati/pulse-release-gates-0.1/commit/d2be905bbdf281cb4adff97b98618340d5ca5c39) |
| Exact Reproduction Capsule contract | [#2851](https://github.com/HKati/pulse-release-gates-0.1/pull/2851) | [`722fe4e85acfaac67c283862645ac9e42c831236`](https://github.com/HKati/pulse-release-gates-0.1/commit/722fe4e85acfaac67c283862645ac9e42c831236) |
| Deterministic Reproduction Capsule execution | [#2852](https://github.com/HKati/pulse-release-gates-0.1/pull/2852) | [`21837e1e54f898a131d3a9bff89527209ddae711`](https://github.com/HKati/pulse-release-gates-0.1/commit/21837e1e54f898a131d3a9bff89527209ddae711) |

The reviewed final PR #2852 head was:

```text
5d8792ffb5c1f555b50f01bb34fa9757e20af5ec
```

Its final recorded state was:

```text
successful checks:
28

conditionally skipped checks:
6

failed checks:
0

Codex final-head review:
no major issues found
```

### Exact bounded Device Ledger subject

The deterministic reference materialization produces:

```text
record count:
14

session count:
2

clock-epoch count:
2

session-boundary count:
3

continuous coverage count:
1

interrupted coverage count:
1

event-bound transition count:
1

endpoint-difference-only transition count:
1
```

Its exact internal identities include:

```text
terminal checkpoint SHA-256:
16f309c033f43a4b80d5cd0be3e0685af977ab510a0813c5fb32631b3334b2ff

canonical ledger SHA-256:
360de3b74e2c0ec33525426cd0598b5a8d382e8017295900f0ef5600ae9a4f77

canonical manifest SHA-256:
47e6adc3afe8c295ec207a23545a3a1df5f043799106f67c093a19da5ab641a1

.pulseledger member count:
10
```

Its primary proof-object identities are:

| Object | Size | SHA-256 |
|---|---:|---|
| Canonical `.pulseledger` | `133568` bytes | `a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3` |
| Standalone verifier | `126419` bytes | `0a828490f93ce684ab50625c23a19c870f813c3bcdef7034f5c88a0c6aa494e7` |
| Canonical positive verifier report | `15328` bytes | `5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4` |
| Device Canonical JSON contract | `2719` bytes | `ddc0e677e04c8678c32e36d21dc79ad509fe6c4a5507322abb6187c6e88c7550` |

The expected observer fingerprint is:

```text
f2880825cd3caa7272d01042829e5b02e8a168db11225477b039e6ec9a7d09c6
```

The unchanged standalone verifier reconstructs:

```text
result:
verified_with_declared_unavailability

checkpoint signature_status:
verified

package signature_status:
verified

checks:
49 / 49 passed

producer_code_imported:
false

producer_verdict_trusted:
false

verifier_implementation_relation:
separate_from_producer_code
```

The verifier boundary remains:

```text
separately implemented verifier
≠ external validating authority
≠ institutional approval
```

The operator's identity, title, organization, reputation, or institutional
status is not an input to the verification result.

### Deterministic Reproduction Capsule

The Reproduction Capsule contract fixes an acyclic relation from the exact
manifest schema, normative contract, canonical manifest, and protected payloads
to the deterministic Capsule and the canonical result carried outside it.

The canonical outputs are:

| Object | Size | SHA-256 | Git blob SHA-1 |
|---|---:|---|---|
| Reproduction Capsule | `285144` bytes | `49e02cf3daa466170b7ffee681ceb06c23410010b64e23137022541ec7691678` | `5b2647823e59bde24cf9125851c1490e3149dfab` |
| Reproduction result | `31188` bytes | `d0a659c572dcde11315f518d350361f6fc7690027c7e2682111f88a519b34ad1` | `9b5a240495b357c64a510e6019e4d7189c29152e` |

The implementation roles remain distinct:

```text
Capsule builder
≠
reproduction runner
≠
standalone verifier
```

The Capsule contains exactly four `ZIP_STORED` members in this order:

```text
1.
manifest/
pulsemech_device_ledger_reproduction_capsule_manifest_v0.json

2.
artifact/
pulsemech_device_transition_ledger_reference_v0.pulseledger

3.
verifier/
verify_pulsemech_device_ledger_v0.py

4.
expected/
pulsemech_device_transition_ledger_reference_verification_v0.json
```

The exact reference environment is:

```text
container image:
docker.io/library/python:3.11.9-slim-bookworm@sha256:
2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050

platform:
linux/amd64

Python:
CPython 3.11.9

Unicode data:
14.0.0

dependency policy:
Python standard library only

network during bounded execution:
none

runtime downloads or package installation:
none

repository and attestation mounts:
read-only

output mount:
separate writable directory
```

The outer launcher verifies the required container RepoDigest before exact-digest
launch and produces the exact 843-byte reference-environment attestation:

```text
SHA-256:
9d20cf6ea118ab8e01768e42a7636923f69945545f01a52904851a717442b9ca
```

The runner creates Capsule A and Capsule B through separate builder processes,
isolated workspaces, and separate output paths.

```text
Capsule A bytes
=
Capsule B bytes
=
checked-in canonical Capsule bytes
```

The unchanged standalone verifier then executes as a separate process against
the `.pulseledger` from each Capsule.

```text
positive verifier stdout A bytes
=
positive verifier stdout B bytes
=
canonical expected verifier-report bytes
```

Both positive processes exit `0`, emit empty stderr, reconstruct
`verified_with_declared_unavailability`, and pass all `49 / 49` checks.

The targeted negative proof mutates only:

```text
signatures/package-signature-v0.json
→ signature_base64
→ first character O → P
```

It repairs both ZIP CRC32 fields, preserves the earlier ZIP, document, and
signature-subject checks, reaches the package-signature equation, and exits `2`
with exactly:

```text
result:
rejected

failure_stage:
package_signature

failed_check_ids:
[
  "package_signature_valid"
]

error_code:
signature_verification_failed

member_path:
signatures/package-signature-v0.json
```

The canonical reproduction result records orchestration evidence for these
completed construction, process, equality, mutation, rejection, and
source-preservation relations.

```text
reproduction_result_role:
orchestration_evidence_not_verifier_verdict

protected source count:
10

all protected source bytes and Git blob identities unchanged:
true

repository source write attempted:
false
```

The result does not replace the standalone-verifier report.

### Reproduction entrypoints

The complete pinned reference-environment operator entrypoint is:

```bash
gh workflow run \
  pulsemech_device_ledger_reproduction_capsule_v0.yml \
  --repo HKati/pulse-release-gates-0.1 \
  --ref main
```

This dispatches the dedicated workflow asynchronously. Completion requires the
workflow to finish successfully and its exact proof outputs to satisfy the
workflow checks.

The portable local proof replay is:

```bash
python3 \
  tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py
```

The local entrypoint runs the sanitized, completion-guarded 15-test permanent
regression on the current host. It does not represent pinned
reference-container artifact regeneration.

The bounded inner runner, direct standalone verifier, Swift proof suite, and
runnable iPhone demonstrator remain separately classified entrypoints in the
canonical proof record and External Verification Path.

The minimal iPhone demonstrator:

```text
executes the deterministic reference materialization
→ checks the exact generated identities
→ admits only the exact pinned canonical verifier-report bytes
→ binds the report subject to the current exact carrier
→ displays the bounded result read-only
→ exports the current exact .pulseledger bytes
```

The app does not execute or import the Python verifier and does not claim that
it verified itself.

### Implementation, claim, and authority boundaries

```text
record_status:
synthetic_reference

identity_scope:
fixture_installation

key_origin_profile:
fixture_software_p256

runner_role:
orchestration_only

verifier_execution:
separate_process

existing_verifier_modification:
forbidden

new_verifier:
none

verification_semantics_change:
none

producer_verdict_trusted:
false

reproduction_result_role:
orchestration_evidence_not_verifier_verdict

authority_effect:
none

capsule_is_release_authority:
false

reproduction_result_is_release_authority:
false

verifier_report_is_release_authority:
false

creates_gate_result:
false

creates_release_decision:
false

changes_release_authority:
false

creates_device_control_authority:
false

external_validation_claim:
none
```

The completed proof does not claim live production monitoring, production
Keychain or Secure Enclave identity, platform attestation, physical-device
identity, device-security status, malware absence, complete causal observation,
production readiness, universal cross-platform reproducibility, external
approval, or release authority.

The bounded mechanical self-proof, exact `.pulseledger` export, deterministic
Reproduction Capsule, canonical reproduction result, and minimal runnable iPhone
demonstrator are closed.

General-purpose iPhone product development, live production callbacks,
production observation sessions, persistence, production key lifecycle, Secure
Enclave integration, platform attestation, physical-device identity, App Store
qualification, external certification, and release-authority integration remain
separate wider claims.

Their absence does not reopen the completed bounded proof.

---

## 15I. Completed historical post-run producer-input capture

Step 4A closes the exact historical producer-input boundary required before
runtime-observation packet production. It is distinct from the completed
Step 3G current-run artifact-observed automation and from the earlier
release-grade #6066 preservation package.

The detailed evidence record remains in the existing
[compute workstream document — completed Step 4A](docs/compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md#completed-step-4a--exact-post-run-producer-input-capture).
The scope is defined by
[work order #2856](https://github.com/HKati/pulse-release-gates-0.1/issues/2856).
This overview does not create a second canonical compute document.

### Implementation and exact observed subject

| Stage | Pull request | Merged commit |
|---|---:|---|
| Capture contract, networked capture and independent offline validation | [#2857](https://github.com/HKati/pulse-release-gates-0.1/pull/2857) | `c01a00458735178ee5ed8884996d3a6c3a0e29dc` |
| Independent timestamp-range correction and matching regressions | [#2860](https://github.com/HKati/pulse-release-gates-0.1/pull/2860) | `22d14088ae21f84d94c6a6951c0f70ab1bdf0895` |
| Five exact observed capture members | [#2861](https://github.com/HKati/pulse-release-gates-0.1/pull/2861) | `7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9` |

The #2857 merge alone did not complete implementation acceptance. The timestamp
correction in both independent tools and their matching regressions was closed
through #2860 before the actual acquisition.

```text
historical repository:
HKati/pulse-release-gates-0.1

historical workflow:
PULSE CI

historical run ID / number / attempt:
29249887581 / 6066 / 1

historical source commit:
46b639706e23f80fe296a8893be18e2b5ab21f7e

separate acquisition workflow ID:
350887354

separate acquisition run ID / attempt:
33986538130 / 1

capture implementation and workflow source:
22d14088ae21f84d94c6a6951c0f70ab1bdf0895

original acquisition artifact ID:
9975323320

capture data merge:
7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9

observed jobs pages / unique jobs / step records:
1 / 8 / 171
```

The historical run was not rerun. Acquisition source, historical subject source,
data-preservation merge and this later documentation update are distinct
identities. The [acquisition execution](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/33986538130)
records a capture-time platform snapshot, not a Step 3F or Step 3G proof run.

### Exact preserved input and independent replay

The [preserved capture directory](preservation/pulse_ci_6066/post_run_producer_input_capture_v0/)
contains exactly:

```text
metadata/run_attempt_exchange_v0.json
metadata/jobs_page_0001_exchange_v0.json
pulsemech_compute_post_run_producer_input_capture_manifest_6066_v0.json
raw/run_attempt_response.json
raw/jobs_page_0001_response.json
```

The raw members preserve the HTTP entity-body bytes returned to the capture
implementation before JSON parsing or reserialization. They contain no BOM,
CR, LF or appended newline. The metadata and manifest retain compact sorted
UTF-8 canonical JSON with exactly one terminal LF.

The exchange records preserve exact attempt-specific requests, selected HTTP
response metadata and explicit absence states. Final Link-header absence and
matching reported/reconstructed counts close the single eight-job page.

```text
manifest size:
17905 bytes

manifest SHA-256:
4642546646fc7c78f8b65bce40c3db72fb6847c4e3d454db97b164f1fc14f238

manifest Git blob SHA-1:
3e623150e254f9383c1cec23fa68e714092a3b98
```

The full five-member identity table belongs to the detailed Step 4A record.
The manifest excludes its own final hash from its inventory.

The read-only cloud report titled “PULSEmech PR #2861 Post-Merge Verification”
inspected the authentic `7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9` merge and
recorded the following execution under CPython 3.14.4, jsonschema 4.26.0 and
pytest 9.0.3:

| Check | Recorded result |
|---|---|
| Complete inventory and committed/checkout byte comparison | All five members matched; no extra member |
| Independent validator on two separately restored private captures | Both exit 0; empty stderr; byte-identical complete stdout |
| Producer-side reconstruction, repeated twice | Exact committed 17905-byte manifest and both exchange metadata files reproduced |
| Ten disposable-copy probes across nine mutation categories | All rejected at the recorded integrity, inventory, jobs-binding or schema layer |
| Contract / producer / offline-validator direct-script suites | 60 / 143 / 151 passed |
| Capture, tracked implementation and index after review | Unchanged; worktree and index clean |

The complete offline-validator stdout had the same SHA-256 in both executions:

```text
aa589f61760374ce294821c2f21f82475893ea5cf082cd888c7253ed629a2a57
```

Replay restored exact committed bytes into temporary directories with mode
0700 and regular files with mode 0600. It did not change tracked checkout modes.
The unchanged independent validator ran with isolated Python and did not import
the capture implementation or use the manifest's stored success flag as proof.

Reconstruction used the unchanged producer at the acquisition revision.
Subject identity, raw-member identities, counts, summaries and exchange wrappers
were recalculated from the preserved inputs. Original capture timestamps,
selected transport metadata and acquisition provenance were retained as
acquisition facts. Parsing and rewriting the finished manifest alone was not
counted as reconstruction.

The job-attempt, duplicate-job and `24:00:00` probes repaired their temporary
checksum and wrapper bindings before reaching `jobs_binding`. The forbidden
endpoint and active-gate expansion probes were rejected by the schema; they are
not described as deeper jobs-binding rejections.

### Evidence classification and accepted boundary

The three permanent suites are registered in [ci/tools-tests.list](ci/tools-tests.list)
and cover the implementation and fixtures. The exact observed-capture replay,
reconstruction and ten mutation probes above are review executions on temporary
copies, not new permanent tests opening the committed capture directory.
The review found no demonstrated violation of an existing permanent-test
requirement and reported no actionable findings in the inspected merged scope.

The separately inspected [post-merge PULSE CI run](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/33996343943)
was bound to `7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9`.
Its [Tools smoke execution](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/33996343943/job/101387579869)
under Python 3.11.16 passed the 60, 143 and 151 direct-script cases, and its
separate targeted pytest suite passed 94 cases. The PULSE CI run, Tools smoke
job and Quality Ledger/status-parity step completed successfully. Conditionally
skipped jobs remain skipped.

The cloud reviewer could not authenticate to those remote logs and did not
reopen the original acquisition ZIP/TAR. Those evidence sources remain
separate from the cloud's direct execution against authentic merged Git objects.
Internal reconstruction does not independently authenticate every external
platform fact recorded at acquisition time.

PR 2 technical acceptance is supported by the exact preserved objects,
independent replay, deterministic reconstruction, negative evidence and
unchanged implementation. The documentation PR has its own final-head CI and
post-merge review; this record does not predeclare their completion or close
work order #2856.

### Temporal and non-authority separation

```text
completed historical #6066 attempt
→ platform-response snapshot observed at capture time
→ exact preserved producer input
→ independent offline validation and deterministic reconstruction
```

Determinism begins after preservation. A later API request is neither required
nor expected to return the same bytes.

```text
capture_subject_class: post_run_platform_response_snapshot
capture_time_relation: observed_at_capture_time
reference_producer_input_eligible: true
capture_is_original_runtime_byte_stream: false
capture_is_runtime_observation: false
capture_is_runtime_observation_packet: false
capture_is_transition_measurement: false
same_run_release_authority_eligible: false
active_gate_eligible: false
authority_effect: none
```

This is not runtime-packet production, transition measurement, resource-use
measurement or a retroactive release-authority input. Unknown remains distinct
from absent; unavailable remains distinct from zero; platform timestamps are
not measured compute-resource consumption.

The future operational path separately requires exact current-run source
capture before its authority decision. That requirement is not satisfied by
reclassifying this post-run historical snapshot. The runtime-observation packet
producer and runtime-observed connected proof remain unimplemented.

---

<a id="current-verified-state-and-latest-results"></a>

## 16. Current verified state and latest results

```text
state_date:
2026-09-06

merged_repository_state_recorded_through:
PR #2861

merged_repository_state_basis:
7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9

merged_repository_state_tree:
b4da3d6ebf567c6e80d3a539e8fc2d1010610213

documentation_closure_scope:
records completed Step 3G automation and Step 4A historical producer-input
capture without changing implementation, verification semantics, policy or
authority; the documentation PR's own final checks are separate

executable_compute_state_recorded_through:
PR #2860

executable_compute_state_basis:
22d14088ae21f84d94c6a6951c0f70ab1bdf0895

foundational_architecture_state_recorded_through:
PR #2817

foundational_architecture_state_basis:
fbfa9b0c03003eef93b23489ab7cb6cc72a9edeb

relational_release_authority_interpretation_recorded_through:
PR #2820

relational_release_authority_interpretation_state_basis:
934109c89bb5787832f8e2952c2919fc06ee854e

current_run_compute_automation_plan:
completed through Step 3G

current_run_compute_automation_terminal_merge:
PR #2826

current_run_compute_automation_terminal_basis:
9bf7fab95dbcc3532238723d0cf76500263106f5

step3g_post_merge_implementation_audit:
no actionable P0-P3 implementation or regression findings; no Step 3G
implementation correction PR was required

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

device_ledger_implementation_recorded_through:
PR #2852

device_ledger_implementation_basis:
21837e1e54f898a131d3a9bff89527209ddae711

device_ledger_bounded_proof_record:
PR #2848 / d2be905bbdf281cb4adff97b98618340d5ca5c39

device_ledger_reproduction_capsule_contract:
PR #2851 / 722fe4e85acfaac67c283862645ac9e42c831236

device_ledger_reproduction_capsule_execution:
PR #2852 / 21837e1e54f898a131d3a9bff89527209ddae711

device_ledger_reproduction_capsule_reviewed_head:
5d8792ffb5c1f555b50f01bb34fa9757e20af5ec

device_ledger_reproduction_capsule_final_pr_state:
28 successful checks / 6 conditionally skipped checks / 0 failed checks /
Codex final-head review found no major issues

device_ledger_bounded_mechanical_self_proof:
completed, regression-proven and post-merge reviewed with no P1, P2 or
lower-severity correctness findings

device_ledger_reference_record_status:
synthetic_reference

device_ledger_reference_identity_scope:
fixture_installation

device_ledger_reference_key_origin_profile:
fixture_software_p256

device_ledger_reference_carrier:
133568 bytes / a31388c7bf574040893d1d923d684d23318e5d2109a0d72a923888b95d5d42b3

device_ledger_standalone_verifier:
126419 bytes / 0a828490f93ce684ab50625c23a19c870f813c3bcdef7034f5c88a0c6aa494e7

device_ledger_standalone_verifier_result:
verified_with_declared_unavailability / 49 of 49 exact checks passed

device_ledger_canonical_verifier_report:
15328 bytes / 5e93539099e99dd5bfa835ba56c401608a5b5c015209812ebb5f9c31142a74f4

device_ledger_base_relevant_negative_proof:
CRC-consistent package-signature mutation rejected at the package-signature
equation boundary

device_ledger_reproduction_capsule_manifest_contract:
schema + normative contract + canonical manifest closed through PR #2851

device_ledger_reproduction_capsule:
285144 bytes / 49e02cf3daa466170b7ffee681ceb06c23410010b64e23137022541ec7691678 /
Git blob 5b2647823e59bde24cf9125851c1490e3149dfab

device_ledger_reproduction_capsule_member_profile:
4 exact ZIP_STORED members in one fixed order

device_ledger_repeated_construction:
2 isolated builder processes and workspaces; Capsule A bytes = Capsule B bytes =
checked-in canonical Capsule bytes

device_ledger_capsule_positive_reproduction:
2 separate standalone-verifier processes; both exit 0 and emit the exact
15328-byte canonical verifier-report bytes

device_ledger_capsule_targeted_negative_reproduction:
O → P package-signature mutation with repaired local-header and
central-directory CRC32; exact rejection at package_signature_valid

device_ledger_capsule_mutated_carrier:
133568 bytes / 4712365d309df49bc42e5cb73d98e37f2bbfc98ef7522b87320612d106157cab

device_ledger_canonical_reproduction_result:
31188 bytes / d0a659c572dcde11315f518d350361f6fc7690027c7e2682111f88a519b34ad1 /
Git blob 9b5a240495b357c64a510e6019e4d7189c29152e

device_ledger_reproduction_result_role:
orchestration_evidence_not_verifier_verdict

device_ledger_reference_environment:
digest-pinned Python 3.11.9 slim Bookworm / linux-amd64 / Unicode 14.0.0 /
standard-library-only / network disabled during bounded execution

device_ledger_reference_environment_attestation:
843 bytes / 9d20cf6ea118ab8e01768e42a7636923f69945545f01a52904851a717442b9ca

device_ledger_protected_source_preservation:
10 exact repository source objects unchanged before and after execution; no
repository source write attempted

device_ledger_capsule_execution_regression:
15 proof tests with sanitized, completion-guarded no-argument launcher

device_ledger_reference_workflow:
.github/workflows/pulsemech_device_ledger_reproduction_capsule_v0.yml

device_ledger_portable_local_replay:
python3 tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py

device_ledger_minimal_runnable_iphone_demonstrator:
completed and post-merge reviewed through PR #2847

device_ledger_exact_pulseledger_export:
completed

device_ledger_demonstrator_carrier_class:
diagnostic_shadow

device_ledger_existing_verifier_modification:
forbidden / unchanged

device_ledger_verification_semantics_change:
none

device_ledger_producer_verdict_trusted:
false

device_ledger_authority_effect:
none

device_ledger_external_validation_claim:
none

device_ledger_broader_iphone_product_development:
separate and not required by the bounded proof or deterministic Reproduction
Capsule claim

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

runtime_observation_producer:
not implemented

planned_observed_relation:
implemented and proven

compute_candidate_policy_surface:
implemented and candidate-only

fixed_source_candidate_chain:
implemented and proven

portable_subject_input_contract:
implemented and hardened

subject_input_packet_fixed_source_producer:
implemented and proven

machine_produced_observed_subject_input_packet:
implemented and replay-proven

immutable_subject_input_analyzer_bridge:
implemented and post-merge proven

historical_pre_core_bridge_report_sha256:
656459e7fb835814a05a7cc5b8150959d32ed3a0e9ed272c2733038bd441ec4c

reusable_analyzer_core:
implemented and post-merge proven

fixed_source_analyzer_compatibility_wrapper:
implemented and proven

subject_input_bridge_to_reusable_analyzer_core:
implemented and proven

fixed_source_analyzer_regression:
33 passed

analyzer_core_regression:
10 passed

subject_input_bridge_regression:
18 passed

fixed_source_analyzer_wrapper_sha256:
d20cb7fed3d8c1ddc10abc23882ce0cbe17d277498016a580f875614fe47becc

analyzer_core_sha256:
cd108bc70494203f95a3f379f6e0d953331d10357676d553d6858f44729988dd

reusable_subject_input_producer_core:
implemented and proven

fixed_source_subject_input_compatibility_wrapper:
implemented and proven

wrapper_pre_execution_core_binding:
implemented and proven

current_run_export_expectation_schema:
implemented

current_run_export_expectation_example:
implemented

current_run_export_expectation_validator:
implemented and hardened

current_run_export_expectation_validator_regression:
implemented, registered and proven

current_run_export_expectation_builder:
implemented, hardened and regression-proven

current_run_export_expectation_builder_regression:
implemented, registered and execution-contract proven

current_run_export_carrier_component:
implemented and regression-proven

current_run_subject_input_wrapper:
implemented and regression-proven

current_run_export_candidate_workflow:
implemented and regression-proven; manual, non-active and candidate-only

current_run_export_candidate_workflow_authority_effect:
none

current_run_export_candidate_workflow_execution_record:
no manually dispatched public execution record is claimed by this state

current_run_candidate_bundle_intake:
implemented and regression-proven

current_run_artifact_observed_proof_builder:
implemented and regression-proven

current_run_artifact_observed_candidate_workflow:
implemented and regression-proven; manual, diagnostic_shadow, non-active and
candidate-only

current_run_artifact_observed_candidate_workflow_authority_effect:
none

current_run_artifact_observed_workflow_execution_record:
no manually dispatched public execution record is claimed by this state

current_run_artifact_observed_reference_lane:
implementation and permanent regression surface completed through Step 3G;
runtime-observed and authority claims remain absent

step3g_candidate_bundle_loader_regression:
30 passed, 0 skipped

step3g_artifact_observed_proof_builder_regression:
32 passed, 0 skipped

step3g_artifact_observed_workflow_regression:
28 passed, 0 skipped

step3g_authoritative_regression_total:
90 passed, 0 skipped

post_run_producer_input_capture_step:
4A / work order #2856 / historical_reference

post_run_capture_contract_and_workflow:
implemented; manual fixed-subject acquisition; no authority effect

post_run_capture_implementation_basis:
PR #2860 / 22d14088ae21f84d94c6a6951c0f70ab1bdf0895

post_run_capture_data_basis:
PR #2861 / 7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9

post_run_capture_acquisition:
run 33986538130 / attempt 1 / workflow 350887354

post_run_capture_historical_subject:
PULSE CI #6066 / run 29249887581 / attempt 1

post_run_capture_preservation:
5 exact members / 1 jobs page / 8 unique jobs / 171 step records

post_run_capture_manifest:
17905 bytes / 4642546646fc7c78f8b65bce40c3db72fb6847c4e3d454db97b164f1fc14f238

post_run_capture_independent_offline_validation:
2 separate private restorations / exit 0 / byte-identical diagnostics

post_run_capture_manifest_reconstruction:
2 exact input-to-manifest reconstructions / both metadata records reproduced

post_run_capture_negative_review_evidence:
10 disposable-copy probes across 9 categories / all rejected

post_run_capture_permanent_regression:
3 registered implementation/fixture suites / 60 + 143 + 151 cases passed

post_run_capture_observed_byte_coverage:
executed post-merge review; not a permanent test opening the captured directory

post_run_capture_technical_acceptance:
supported by exact merged-object verification, replay, reconstruction and
mutation review; no actionable findings in the inspected merged scope

post_run_capture_post_merge_ci:
run 33996343943 / Tools smoke job 101387579869 / success on 7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9

post_run_capture_authority_boundary:
same_run_release_authority_eligible=false / active_gate_eligible=false /
authority_effect=none

tools_test_manifest:
152 active entries / 152 unique active entries

compute_resource_measurement:
not implemented

compute_budget:
not defined

active_compute_enforcement:
none

release_required_compute_enforcement:
none

AI_native_operator_model:
architectural operating model; no independent authority effect

transition_meter_general_domain_extension:
foundational architecture

current_development_boundary:
compute — Step 3G automation and Step 4A historical input capture are complete;
Step 4 runtime-observation packet production, Step 5 runtime-observed connected
proof, per-axis resource measurement and compute-gate promotion remain separate
later boundaries; current-run operational capture must precede its decision

Device Ledger — bounded mechanical self-proof, exact .pulseledger export,
deterministic Reproduction Capsule, canonical reproduction result and minimal
runnable iPhone demonstrator are closed; live production observation, production
key lifecycle, platform attestation, universal cross-platform reproduction,
external certification and broader iPhone product development remain separate
wider claims
```

The stable URL for this state section is:

https://github.com/HKati/pulse-release-gates-0.1/blob/main/PULSEMECH_TECHNICAL_OVERVIEW.md#current-verified-state-and-latest-results

The machine-readable document URL is:

https://raw.githubusercontent.com/HKati/pulse-release-gates-0.1/main/PULSEMECH_TECHNICAL_OVERVIEW.md

### Latest completed Device Ledger bounded proof and reproduction sequence

- [PR #2842 — materialize the canonical Device Ledger package manifest](https://github.com/HKati/pulse-release-gates-0.1/pull/2842)
- [PR #2843 — materialize the Device Ledger package signature](https://github.com/HKati/pulse-release-gates-0.1/pull/2843)
- [PR #2844 — materialize the deterministic `.pulseledger` carrier](https://github.com/HKati/pulse-release-gates-0.1/pull/2844)
- [PR #2845 — verify the Swift carrier with the standalone verifier](https://github.com/HKati/pulse-release-gates-0.1/pull/2845)
- [PR #2846 — close the final verifier-trigger diff-hygiene finding](https://github.com/HKati/pulse-release-gates-0.1/pull/2846)
- [PR #2847 — add the minimal runnable bounded proof demonstrator](https://github.com/HKati/pulse-release-gates-0.1/pull/2847)
- [PR #2848 — record the completed bounded mechanical proof](https://github.com/HKati/pulse-release-gates-0.1/pull/2848)
- [PR #2851 — define the exact Reproduction Capsule manifest contract](https://github.com/HKati/pulse-release-gates-0.1/pull/2851)
- [PR #2852 — execute the deterministic Reproduction Capsule proof](https://github.com/HKati/pulse-release-gates-0.1/pull/2852)
- [Canonical Device Ledger bounded mechanical proof record](docs/PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md)
- [External verification and reproduction procedure](docs/EXTERNAL_VERIFICATION_PATH_v0.md)

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
- [PR #2778 — extract reusable subject-input producer core](https://github.com/HKati/pulse-release-gates-0.1/pull/2778)
- [PR #2783 — verify subject-input producer core before execution](https://github.com/HKati/pulse-release-gates-0.1/pull/2783)
- [PR #2784 — define current-run export expectation contract](https://github.com/HKati/pulse-release-gates-0.1/pull/2784)
- [PR #2785 — add current-run export expectation example](https://github.com/HKati/pulse-release-gates-0.1/pull/2785)
- [PR #2786 — add current-run export expectation validator](https://github.com/HKati/pulse-release-gates-0.1/pull/2786)
- [PR #2787 — close expectation-validator trust boundaries](https://github.com/HKati/pulse-release-gates-0.1/pull/2787)
- [PR #2788 — add current-run expectation-validator regression](https://github.com/HKati/pulse-release-gates-0.1/pull/2788)
- [PR #2789 — add current-run export expectation builder](https://github.com/HKati/pulse-release-gates-0.1/pull/2789)
- [PR #2814 — add current-run expectation-builder regression](https://github.com/HKati/pulse-release-gates-0.1/pull/2814)
- [PR #2818 — enforce the builder-regression execution contract](https://github.com/HKati/pulse-release-gates-0.1/pull/2818)
- [PR #2819 — close the pytest terminal early-exit boundary](https://github.com/HKati/pulse-release-gates-0.1/pull/2819)
- [PR #2822 — add the current-run export carrier loader](https://github.com/HKati/pulse-release-gates-0.1/pull/2822)
- [PR #2823 — add the current-run subject-input wrapper](https://github.com/HKati/pulse-release-gates-0.1/pull/2823)
- [PR #2825 — add the non-active current-run export candidate workflow](https://github.com/HKati/pulse-release-gates-0.1/pull/2825)
- [PR #2826 — complete the current-run artifact-observed proof chain](https://github.com/HKati/pulse-release-gates-0.1/pull/2826)
- [PR #2857 — define the post-run producer-input capture](https://github.com/HKati/pulse-release-gates-0.1/pull/2857)
- [PR #2860 — close independent timestamp-range admission and regression binding](https://github.com/HKati/pulse-release-gates-0.1/pull/2860)
- [PR #2861 — preserve the exact observed #6066 capture](https://github.com/HKati/pulse-release-gates-0.1/pull/2861)
- [Completed Step 4A evidence and temporal boundary](docs/compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md#completed-step-4a--exact-post-run-producer-input-capture)

### Latest foundational architecture sequence

- [PR #2790 — add the PULSEmech Transition Meter](https://github.com/HKati/pulse-release-gates-0.1/pull/2790)
- [PR #2794 — position PULSEmech as a transition-measurement architecture](https://github.com/HKati/pulse-release-gates-0.1/pull/2794)
- [PR #2816 — define the transition-bounded computation architecture](https://github.com/HKati/pulse-release-gates-0.1/pull/2816)
- [PR #2817 — integrate and close the reviewed transition-bounded computation architecture](https://github.com/HKati/pulse-release-gates-0.1/pull/2817)

### Latest relational release-authority interpretation

- [PR #2820 — add the relational release-authority interpretation](https://github.com/HKati/pulse-release-gates-0.1/pull/2820)

---

## 17. Current development path

The completed Device Ledger bounded proof and deterministic reproduction
relation is:

```text
bounded synthetic reference relation
→ exact evidence records
→ predecessor-bound record chain
→ terminal checkpoint
→ canonical ledger
→ checkpoint signature
→ exact payload inventory
→ canonical manifest
→ package signature
→ deterministic .pulseledger
→ separately implemented verifier reconstruction
→ reproducible PASS or fail-closed rejection
→ minimal runnable iPhone result surface
→ exact artifact export
→ exact Reproduction Capsule contract
→ deterministic four-member ZIP_STORED construction
→ two isolated byte-identical Capsule constructions
→ two exact positive standalone-verifier executions
→ one targeted CRC-consistent package-signature mutation
→ exact package_signature_valid rejection
→ canonical reproduction result
→ protected-source preservation
```

This Device Ledger path is closed for its declared bounded claim.

```text
bounded mechanical self-proof:
closed

exact .pulseledger export:
closed

Reproduction Capsule contract:
closed

deterministic reference execution:
closed

canonical reproduction result:
closed

minimal runnable iPhone demonstrator:
closed

broader iPhone product development:
separate
```

The canonical reproduction result remains orchestration evidence.

The existing standalone verifier remains the verifier.

No external validating authority, production key lifecycle, platform
attestation, universal cross-platform reproduction, release-decision
integration, or general-purpose product layer is required to preserve this
bounded closure.

The separate compute workstream continues from completed Step 3G automation
and the completed historical Step 4A producer-input prerequisite recorded in
Section 15I. Neither result implements the runtime-observation packet producer.

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

The completed subject-input producer relation is:

```text
fixed-source compatibility wrapper
→ verified reusable producer core
→ observed fixed-source packet

direct reusable producer core
+ FIXED_SOURCE_6066_PROFILE
→ byte-identical observed fixed-source packet
```

The completed current-run compute automation relation is:

```text
strict current-run expectation contract
→ machine-produced observed expectation
→ finalized current-run export carrier
→ observed current-run subject-input packet
→ checksum-closed non-active Step 3F candidate artifact
→ independently verified Step 3G candidate-bundle intake
→ exact current-run subject
+ independently selected protected control plane
→ immutable carrier and packet reconstruction
→ existing subject-input analyzer bridge
→ single reusable analyzer core
→ artifact-observed compute-binding report
→ deterministic current-run integration plan
→ planned-observed relation
→ separate non-active candidate materialization
→ artifact-observed proof-bundle builder with a checksum-closed output contract
```

This sequence records merged construction capability and permanent regression
coverage. It does not claim that a manually dispatched Step 3G run or a
run-bound proof-bundle instance has been produced.

The arrows above describe the implemented dependency and reconstruction order.

They do not replace the primary PULSEmech relational object with a generic
pipeline ontology.


The Step 3G proof-construction implementation preserves the actual relation
state:

```text
false
missing
partial
ambiguous
unresolved
```

It does not convert absent or incomplete evidence into a successful complete
transition.

It does not force every candidate gate to `true`.

Exactly three non-active candidate identities are derived:

```text
compute_transition_path_complete

compute_transition_authority_binding_ok

compute_transition_unbound_mutation_absent
```

Their literal Boolean values are written only to a separate folded candidate
status.

The source subject `status.json` remains unchanged.

The completed Step 3G authority boundary is:

```text
manual
candidate-only
non-active
artifact-observed
pre-authority
authority_effect = none
```

The merged implementation and permanent regression surface are complete through
Step 3G.

A manually dispatched Step 3F or Step 3G candidate artifact is a separate
run-bound execution record. This document does not claim that such a public
execution record has already been produced.

The completed Step 4A historical-reference relation is:

```text
completed historical #6066 attempt
→ separate capture-time platform-response snapshot
→ five exact preserved producer-input members
→ independent offline validation
+ deterministic manifest reconstruction
+ targeted mutation evidence
authority_effect = none
```

This actual acquisition is not a manually dispatched Step 3F/3G artifact proof.
It closes the historical input prerequisite, not runtime-packet production.

The future operational relation has a different temporal requirement:

```text
current subject run
→ pre-decision exact source capture
→ runtime-observation packet
→ planned–observed transition relation
→ transition-path verification
→ policy-bound authority decision
```

The historical post-run snapshot cannot be admitted retroactively as authority
for its completed subject. Unexposed commands, calls, resource values and
consumption relations remain unavailable rather than inferred.

The next implementation boundary remains Step 4, after this completed
historical input prerequisite:

```text
runtime-observation producer

→ job and step identity
→ exact source identity
→ timing
→ runtime inputs
→ runtime outputs
→ downstream consumers
→ external-service calls
→ model inferences
→ resource axes
```

The later sequence remains:

```text
Step 4 runtime-observation producer
→ Step 5 runtime-observed connected proof
→ Step 6 per-axis resource measurement
→ Step 7 separate policy promotion decision
```

Any movement from candidate to advisory, required or release-required remains a
separate policy decision.

Promotion requires:

```text
explicit evidence
policy review
negative-path coverage
stable measurement semantics
separate PR
```

Therefore:

```text
successful artifact-observed proof
≠
runtime-observed proof

successful runtime-observed proof
≠
automatic promotion
```

The current-run compute lane remains non-active and has no release-authority
effect.

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

### Open-workstream record

A pull request carries a proposed implementation state under review.

```text
subject:
one unmerged proposed repository transition
```

An open-workstream record must not be collapsed into the merged repository
implementation state.

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

### Historical producer-input capture record

A post-run platform-response capture carries a later acquisition of exact
response bodies and selected exchange facts for an already completed subject.

```text
subject:
one exact completed historical workflow-run attempt

observation:
platform responses observed at the separately recorded capture time

record_role:
historical_reference_producer_input

authority_effect:
none
```

The acquisition event is distinct from the original execution. This record is
neither its original runtime stream nor a same-run authority input. Its later
repository preservation and documentation commits do not replace its recorded
acquisition source.

### Reproduction Capsule contract record

The Capsule-manifest schema, normative contract, and canonical manifest carry
one exact construction and execution contract.

```text
subject:
one exact Reproduction Capsule contract surface

authority_effect:
none
```

### Canonical reproduction result record

The canonical reproduction result carries the completed deterministic Capsule
execution relation.

```text
subject:
one completed bounded Reproduction Capsule execution

record_role:
orchestration_evidence_not_verifier_verdict

authority_effect:
none
```

The result records execution and equality relations after the standalone
verifier processes complete.

It does not replace the standalone verifier report, create a gate result, or
create a release decision.

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

### Foundational architecture record

The Transition Meter carries a cross-domain mechanical principle and reference
architecture.

```text
subject:
transition-measurement architecture
```

It does not by itself assert generalized implementation or create authority.

The subject identity determines the meaning and scope of every record.

---

## 19. Canonical source order for technical analysis

Technical analysis begins with the complete system identity, then follows the
exact merged state, proof records, workstream records, executable carriers, and
run-bound evidence.

```text
1. PULSEMECH_TECHNICAL_OVERVIEW.md
   → complete system identity and current verified state

2. current main repository state
   → present merged implementation

3. docs/PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md
   → completed bounded Device Ledger proof and exact reproduction relation

   docs/EXTERNAL_VERIFICATION_PATH_v0.md
   → distinct reviewer and operator procedures for direct verification and
     deterministic reproduction

4. docs/compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md
   → detailed compute contracts, completed proofs, current-run boundary, and
     remaining sequence

5. docs/slsa/PULSEMECH_WITNESS_INTEROPERABILITY_AND_RELEASE_AUTHORITY_BOUNDARY_v0.md
   → reviewed Witness relation, structured-carrier gap, and authority boundary

6. exact open pull request, when open work is being evaluated
   → proposed but unmerged implementation or documentation state

7. exact workflow, policy and registry
   → active release-transition configuration or declared bounded execution

8. exact schemas, contracts, producers, builders, runners, validators,
   materializers, verifiers and tests
   → machine contracts and executable mechanics

9. exact run-bound artifacts, canonical proof artifacts, reproduction results,
   preserved reference packages and run notes
   → one workflow run, completed proof, orchestration evidence, or historical
     record

10. PULSEMECH_TRANSITION_METER.md
    → broader foundational transition-measurement architecture

11. reader and publication surfaces
    → derived views
```

The Device Ledger proof record and External Verification Path have different
roles:

```text
proof record:
what the completed relation proves

external path:
how a reviewer or operator inspects, replays, or reproduces it
```

Neither document becomes a verifier verdict or release-authority carrier.

This order preserves the subject and time relation of every source.

An AI-native operator must preserve the same ordering.

It must not use a later reader summary to overwrite an earlier authority
carrier, use an orchestration result to replace a verifier report, or use an
open pull request to overwrite merged implementation state.

---

## 20. Canonical source map

### System and repository entry points

- [README](README.md)
- [PULSEmech Transition Meter](PULSEMECH_TRANSITION_METER.md)
- [Documentation index](docs/INDEX.md)
- [PULSE CI workflow](.github/workflows/pulse_ci.yml)
- [Gate policy](pulse_gate_policy_v0.yml)
- [Gate registry](pulse_gate_registry_v0.yml)

### Release-authority proof

- [Release-grade Reference Run Note v0](docs/RELEASE_GRADE_REFERENCE_RUN_NOTE_v0.md)
- [Recorded release-evidence verifier](docs/recorded_release_evidence_verifier_v0.md)
- [Release-evidence verifier design](docs/PULSE_RELEASE_EVIDENCE_VERIFIER_v0.md)
- [Release-grade reference proof plan](docs/PULSEMECH_RELEASE_GRADE_REFERENCE_PROOF_PLAN_v0.md)
- [Strict terminal gate checker](PULSE_safe_pack_v0/tools/check_gates.py)
- [Policy-to-require-list materializer](tools/policy_to_require_args.py)
- [Release-decision schema](schemas/release_decision_v0.schema.json)

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
- [Fixed-source analyzer compatibility wrapper](tools/build_pulsemech_compute_binding_report_v0.py)
- [Immutable subject-input analyzer bridge](tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py)
- [Analyzer-core regression](tests/test_pulsemech_compute_binding_analyzer_core_v0.py)
- [Immutable bridge regression](tests/test_build_pulsemech_compute_binding_report_from_subject_input_v0.py)
- [Planned-observed relation builder](tools/build_pulsemech_compute_planned_observed_relation_v0.py)
- [Runtime-observation packet schema](schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json)

### Portable subject input

- [Subject-input packet schema](schemas/pulsemech_compute_subject_input_packet_v0.schema.json)
- [Strict subject-input validator](tools/check_pulsemech_compute_subject_input_packet_v0.py)
- [Reusable subject-input producer core](tools/pulsemech_compute_subject_input_packet_producer_core_v0.py)
- [Fixed-source subject-input compatibility wrapper](tools/build_pulsemech_compute_subject_input_packet_v0.py)
- [Subject-input producer-core regression](tests/test_pulsemech_compute_subject_input_packet_producer_core_v0.py)
- [Observed PULSE CI #6066 subject-input packet](examples/compute/pulsemech_compute_subject_input_packet_6066_observed_v0.json)
- [Observed packet replay proof](tests/test_pulsemech_compute_subject_input_packet_6066_observed_v0.py)
- [Packet-to-analyzer equivalence proof](tests/test_build_pulsemech_compute_binding_report_from_subject_input_v0.py)

### Current-run compute automation

#### Expectation contract and producer

- [Current-run export expectation schema](schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json)
- [Current-run export expectation example](examples/compute/pulsemech_compute_current_run_export_expectation_example_v0.json)
- [Strict current-run expectation validator](tools/check_pulsemech_compute_current_run_export_expectation_v0.py)
- [Current-run expectation validator regression](tests/test_check_pulsemech_compute_current_run_export_expectation_v0.py)
- [Current-run expectation builder](tools/build_pulsemech_compute_current_run_export_expectation_v0.py)
- [Current-run expectation builder regression](tests/test_build_pulsemech_compute_current_run_export_expectation_v0.py)

#### Finalized carrier and current-run subject input

- [Current-run export carrier loader](tools/load_pulsemech_compute_current_run_export_carrier_v0.py)
- [Current-run export carrier regression](tests/test_load_pulsemech_compute_current_run_export_carrier_v0.py)
- [Current-run subject-input wrapper](tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py)
- [Current-run subject-input wrapper regression](tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py)

#### Step 3F non-active export candidate

- [Current-run export candidate workflow](.github/workflows/pulsemech_compute_current_run_export_candidate.yml)
- [Current-run export candidate workflow regression](tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py)

#### Step 3G artifact-observed proof

- [Current-run candidate-bundle intake loader](tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py)
- [Candidate-bundle intake regression](tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py)
- [Current-run artifact-observed proof builder](tools/build_pulsemech_compute_current_run_artifact_observed_proof_v0.py)
- [Artifact-observed proof-builder regression](tests/test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py)
- [Artifact-observed candidate workflow](.github/workflows/pulsemech_compute_current_run_artifact_observed_candidate.yml)
- [Artifact-observed candidate workflow regression](tests/test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py)

The Step 3F and Step 3G workflows remain manual, candidate-only, non-active and
pre-authority.

They do not activate compute gates or create release authority.

### Historical post-run producer-input capture — Step 4A

- [Completed capture evidence and claim boundary](docs/compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md#completed-step-4a--exact-post-run-producer-input-capture)
- [Capture-manifest schema](schemas/pulsemech_compute_post_run_producer_input_capture_manifest_v0.schema.json)
- [Normative capture contract](contracts/pulsemech_compute_post_run_producer_input_capture_v0.json)
- [Networked fixed-subject capture tool](tools/capture_pulsemech_compute_post_run_producer_input_v0.py)
- [Independent network-free offline validator](tools/check_pulsemech_compute_post_run_producer_input_capture_v0.py)
- [Manual fixed-subject capture workflow](.github/workflows/pulsemech_compute_post_run_producer_input_capture_v0.yml)
- [Contract regression](tests/test_pulsemech_compute_post_run_producer_input_capture_contract_v0.py)
- [Capture producer regression](tests/test_capture_pulsemech_compute_post_run_producer_input_v0.py)
- [Offline-validator and TAR regression](tests/test_check_pulsemech_compute_post_run_producer_input_capture_v0.py)
- [Five-member observed capture](preservation/pulse_ci_6066/post_run_producer_input_capture_v0/)
- [Observed capture manifest](preservation/pulse_ci_6066/post_run_producer_input_capture_v0/pulsemech_compute_post_run_producer_input_capture_manifest_6066_v0.json)

This is a completed historical-reference input and offline-replay record, not
runtime-observation packet production or current-run release authority.

### Device Ledger bounded proof and deterministic reproduction

#### Canonical records

- [Canonical Device Ledger bounded mechanical proof record](docs/PULSEMECH_DEVICE_LEDGER_BOUNDED_MECHANICAL_PROOF_v0.md)
- [External verification and reproduction procedure](docs/EXTERNAL_VERIFICATION_PATH_v0.md)

#### Core implementation and direct verification

- [Device Ledger Swift core](apps/ios/Packages/PULSEmechLedgerCore/)
- [Canonicalization contract](contracts/pulsemech_device_canonical_json_v0.json)
- [iOS observation contract](contracts/pulsemech_ios_observation_contract_v0.json)
- [Standalone Device Ledger verifier](tools/verify_pulsemech_device_ledger_v0.py)
- [Reference `.pulseledger` carrier](examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_v0.pulseledger)
- [Canonical verifier report](examples/device_transition_ledger/pulsemech_device_transition_ledger_reference_verification_v0.json)

#### Reproduction Capsule contract

- [Capsule-manifest schema](schemas/pulsemech_device_ledger_reproduction_capsule_manifest_v0.schema.json)
- [Normative Reproduction Capsule contract](contracts/pulsemech_device_ledger_reproduction_capsule_v0.json)
- [Canonical Capsule manifest](examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_manifest_reference_v0.json)
- [Capsule contract regression](tests/test_pulsemech_device_ledger_reproduction_capsule_contract_v0.py)

#### Reproduction Capsule execution

- [Deterministic Capsule builder](tools/build_pulsemech_device_ledger_reproduction_capsule_v0.py)
- [Reproduction-result schema](schemas/pulsemech_device_ledger_reproduction_result_v0.schema.json)
- [Orchestration-only reproduction runner](tools/run_pulsemech_device_ledger_reproduction_capsule_v0.py)
- [Canonical Reproduction Capsule](examples/device_transition_ledger/pulsemech_device_ledger_reproduction_capsule_v0.zip)
- [Canonical reproduction result](examples/device_transition_ledger/pulsemech_device_ledger_reproduction_result_reference_v0.json)
- [Permanent Capsule execution regression](tests/test_pulsemech_device_ledger_reproduction_capsule_execution_v0.py)
- [Dedicated Capsule reference workflow](.github/workflows/pulsemech_device_ledger_reproduction_capsule_v0.yml)
- [Registered tools-test surface](ci/tools-tests.list)

#### Runnable demonstrator

- [Minimal runnable iPhone demonstrator](apps/ios/PULSEmechProofApp/)
- [iPhone demonstrator workflow](.github/workflows/pulsemech_ios_proof_app.yml)

The proof record, External Verification Path, Capsule, canonical reproduction
result, permanent regressions, dedicated workflow, and demonstrator remain
non-authorizing proof, orchestration, review, transport, or presentation
surfaces.

```text
reproduction_result_role = orchestration_evidence_not_verifier_verdict
producer_verdict_trusted = false
authority_effect = none
external_validation_claim = none
```

### Foundational transition measurement

- [PULSEmech Transition Meter](PULSEMECH_TRANSITION_METER.md)
- [Transition-bounded computation architecture](docs/PULSEMECH_TRANSITION_BOUNDED_COMPUTATION_ARCHITECTURE_v0.md)
- [README transition-measurement positioning](README.md#pulsemech-transition-meter--the-missing-instrument-between-measured-states)

### Relational release-authority interpretation

- [Canonical relational release-authority interpretation](docs/PULSEMECH_RELATIONAL_RELEASE_AUTHORITY_INTERPRETATION_v0.md)

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

An open workstream is recorded separately as:

```text
pull-request identity
exact observed head
review state
unresolved mechanical boundary
non-merged status
```

Historical proof identities remain attached to their original runs, commits,
artifacts and digests.

Foundational architecture remains separate from implemented repository state.

The stable overview therefore preserves:

```text
one system identity
+ advancing merged implementation state
+ explicit open-workstream state
+ immutable historical proofs
+ separately identified foundational architecture
```

An AI-native operator must use these status distinctions as machine-operable
constraints.

It must not silently promote:

```text
open
→ merged

example
→ observed

candidate
→ active

diagnostic
→ authority

foundational architecture
→ completed implementation
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

The system is AI-native at the operator layer:

```text
machine-readable contracts and artifacts
→ AI traversal, reconstruction and diagnosis
→ human policy and consequence control
```

The AI operator does not replace the artifact-bound authority path.

The current merged implementation has completed:

```text
release-authority core
self-contained evidence floor
public release-grade reference execution
SLSA/VSA candidate evidence path
fixed-source compute relation
portable subject-input contract
deterministic fixed-source packet producer
machine-produced observed replay proof
immutable subject-input analyzer bridge
reusable analyzer core
reusable subject-input producer core
pre-execution wrapper-to-core verification
current-run export expectation schema
current-run export expectation example
strict current-run expectation validator
validator trust-boundary hardening
permanent current-run expectation-validator regression
machine-produced current-run expectation builder
permanent expectation-builder regression and launcher hardening
finalized current-run export carrier component
current-run subject-input wrapper
manual non-active Step 3F export candidate workflow
verified current-run candidate-bundle intake
current-run artifact-observed proof builder
manual non-active Step 3G artifact-observed candidate workflow
artifact-observed proof-bundle builder with a checksum-closed output contract
post-run producer-input capture contract and manual fixed-subject workflow
separate networked capture and independent network-free validator
exact five-member historical #6066 producer-input capture
repeated observed-capture offline validation and manifest reconstruction
capture-specific disposable-copy negative evidence

Device Ledger canonical record chain
Device Ledger terminal checkpoint closure
Device Ledger checkpoint and package signatures
Device Ledger deterministic ten-member .pulseledger carrier
Device Ledger separately implemented standalone verifier
Swift-to-standalone-verifier positive and relevant negative proof
exact canonical 49-check verifier report
minimal runnable iPhone bounded proof demonstrator
exact .pulseledger artifact export
canonical Device Ledger bounded mechanical proof record

strict Reproduction Capsule manifest schema
normative Reproduction Capsule contract
canonical four-member Capsule manifest
fixed ZIP_STORED Capsule profile
deterministic Capsule builder
strict reproduction-result schema
orchestration-only reproduction runner
exact digest-pinned reference-environment boundary
exact outer-launcher attestation
two isolated deterministic Capsule constructions
Capsule A/B/canonical byte identity
two exact positive standalone-verifier processes
targeted CRC-consistent package-signature mutation
exact package_signature_valid rejection
canonical machine-readable reproduction result
protected-source before/after preservation
permanent Capsule contract regression
permanent 15-test Capsule execution regression
dedicated Capsule reference workflow
152-entry registered tools-test surface
```

The broader Transition Meter is recorded as foundational architecture.

The current implementation boundaries are:

```text
compute:
completed Step 3G artifact-observed proof automation
+ completed Step 4A historical producer-input capture prerequisite
→ Step 4 runtime-observation producer
→ Step 5 runtime-observed connected proof
→ Step 6 per-axis resource measurement
→ stable measurement coverage
→ Step 7 separate policy promotion decision

Device Ledger bounded mechanical self-proof:
closed

Device Ledger exact .pulseledger export:
closed

Device Ledger Reproduction Capsule contract:
closed

Device Ledger deterministic reference execution:
closed

Device Ledger canonical reproduction result:
closed

minimal runnable iPhone demonstrator:
closed

live production observation:
separate

production key lifecycle and Secure Enclave integration:
separate

platform attestation and physical-device identity:
separate

universal cross-platform reproduction:
not claimed

external certification or validating authority:
not required and not claimed

release-decision integration or release-authority mutation:
absent

broader iPhone product development:
separate
```

The Reproduction Capsule boundary remains:

```text
record_status = synthetic_reference
identity_scope = fixture_installation
key_origin_profile = fixture_software_p256
runner_role = orchestration_only
verifier_execution = separate_process
existing_verifier_modification = forbidden
producer_verdict_trusted = false
reproduction_result_role = orchestration_evidence_not_verifier_verdict
authority_effect = none
external_validation_claim = none
```

The completed Step 3G compute surface remains:

```text
manual
candidate-only
non-active
artifact-observed
pre-authority
authority_effect = none
```

It preserves false, missing, partial, ambiguous and unresolved relation state.

It does not activate compute gates, modify source `status.json`, create a
compute budget, produce runtime observation, create a release decision or
change release authority.

```text
successful artifact-observed proof
≠
runtime-observed proof
≠
automatic promotion
```

The completed Step 4A input capture remains:

```text
historical-reference producer input
post-run platform-response snapshot
exact preserved bytes
independent offline validation
deterministic reconstruction
same_run_release_authority_eligible = false
active_gate_eligible = false
authority_effect = none
```

It does not supply original runtime telemetry, perform transition measurement
or change the historical release decision. Any future operational capture must
occur before its current-run authority decision.

Runtime observation production, resource measurement, compute budgeting, active
compute enforcement and release-required compute promotion remain separate,
later boundaries.

The latest verified state remains available at the stable URL recorded at the
top of this document.
