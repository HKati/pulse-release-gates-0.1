# PULSEmech compute binding and transition efficiency design v0

## WORKMARK

```text
document_role:
design_and_implementation_state_record

workstream:
compute_binding_and_transition_efficiency

state_date:
2026-09-06

canonical_system_state_source:
PULSEMECH_TECHNICAL_OVERVIEW.md

merged_compute_state_recorded_through:
PR #2861

merged_compute_state_basis:
7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9

implementation_status:
current_run_automation_through_3G_and_historical_capture_4A_complete

current_run_automation_terminal_pr:
2826

current_run_automation_terminal_basis:
9bf7fab95dbcc3532238723d0cf76500263106f5

fixed_source_connected_proof:
completed

portable_subject_input_contract:
implemented_and_hardened

machine_produced_observed_subject_input_proof:
implemented_and_replay_proven

immutable_subject_input_analyzer_bridge:
implemented_and_proven

reusable_analyzer_core:
implemented_and_proven

reusable_subject_input_producer_core:
implemented_and_proven

wrapper_pre_execution_core_binding:
implemented_and_proven

current_run_export_expectation_schema:
implemented

current_run_export_expectation_example:
implemented

current_run_export_expectation_validator:
implemented_and_hardened

current_run_export_expectation_validator_regression:
implemented_registered_and_proven

current_run_export_expectation_builder:
implemented_hardened_and_regression_proven

current_run_export_expectation_builder_regression:
implemented_registered_and_execution_contract_proven

current_run_export_carrier_component:
implemented_and_regression_proven

current_run_subject_input_wrapper:
implemented_and_regression_proven

current_run_candidate_workflow:
implemented_and_regression_proven_manual_non_active

current_run_candidate_bundle_intake:
implemented_and_regression_proven

current_run_artifact_observed_proof_builder:
implemented_and_regression_proven

current_run_artifact_observed_candidate_workflow:
implemented_and_regression_proven_manual_non_active

current_run_manually_dispatched_public_proof_record:
not_claimed_by_this_record

post_run_producer_input_capture_step:
4A

post_run_producer_input_capture_work_order:
2856

post_run_producer_input_capture_lane:
historical_reference

post_run_capture_implementation_basis:
22d14088ae21f84d94c6a6951c0f70ab1bdf0895

post_run_capture_data_basis:
7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9

post_run_capture_reference_state:
exact_five_member_observed_capture_preserved

post_run_capture_technical_acceptance:
supported_by_post_merge_replay_reconstruction_and_mutation_review

runtime_observation_contract:
implemented

runtime_observation_producer:
not_implemented

runtime_observed_connected_proof:
not_implemented

resource_measurement:
not_implemented

compute_budget:
not_defined

candidate_gate_activation:
none

release_required_compute_enforcement:
none

release_authority_effect:
none
```

This document defines the PULSEmech compute-binding workstream and records its
merged implementation, completed reference evidence and remaining work.

It remains the detailed workstream record beneath the canonical system-level
source, [PULSEMECH_TECHNICAL_OVERVIEW.md](../../PULSEMECH_TECHNICAL_OVERVIEW.md).

The recorded state is bound to data merge
`7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9`. It does not claim that the
subsequent documentation PR has already passed its own CI or post-merge review.

Two completed results must remain distinct:

```text
Step 3G:
current-run artifact-observed automation implementation
+ permanent registered regression proof
+ manual, non-active candidate workflows

Step 4A:
one actual historical #6066 producer-input capture
+ exact preserved response and exchange bytes
+ independent offline replay
+ deterministic manifest reconstruction
+ capture-specific disposable-copy mutation evidence
```

Step 4A records an actual acquisition execution. It is not a manually dispatched
Step 3F or Step 3G proof instance, and it is not completion of the future
runtime-observation packet producer.

The former open-builder state is superseded by the merged builder and its
registered regressions. Sections 24–27 record the completed implementation and
reference capture; the runtime producer, runtime-observed connected proof,
resource measurement and any policy promotion remain separate later work.

This documentation changes no workflow, schema, normative contract, producer,
validator, test registration, policy, gate, status, release-authority mechanism,
Device Ledger source, DOI, citation, tag, release or publication metadata.

---

## 1. Current system boundary

PULSEmech contains an implemented and exercised artifact-bound
release-transition mechanism:

```text
recorded current-run release evidence
→ evidence and artifact binding verification
→ canonical candidate production and replay
→ recorded-evidence verification
→ canonical verifier replay
→ declared release policy
→ workflow-effective materialized required gate set
→ final status.json
→ strict fail-closed gate enforcement
→ explicit ALLOW or BLOCK release-transition result
```

The compute-binding workstream observes and reconstructs how executed compute
relates to this transition.

The merged compute surface now contains:

```text
strict compute-binding report contract
fixed-source artifact-observed report builder
runtime-observation packet contract
strict planned-observed relation contract
deterministic planned-observed relation builder
non-active candidate gate identities
relation-to-candidate-status materializer
policy-derived generic candidate check
connected fixed-source #6066 proof
strict portable subject-input packet contract
exact historical #6066 example packet
strict subject-input packet validator
deterministic fixed-source packet producer
machine-produced observed #6066 packet
pinned historical producer replay
immutable packet and carrier capture
one reusable analyzer implementation core
one reusable subject-input producer core
verified fixed-source wrapper-to-core bootstrap
strict current-run export expectation contract
canonical current-run expectation example
strict current-run expectation validator
closed schema-reference boundary
reviewed schema-byte binding
permanent registered expectation-validator regression
machine current-run expectation builder and authoritative regression
finalized current-run export carrier component
current-run subject-input wrapper using the existing producer core
manual non-active Step 3F export candidate workflow
independent Step 3G candidate-bundle intake
artifact-observed proof builder and manual candidate workflow
post-run producer-input capture schema and normative contract
separate networked capture tool and independent offline validator
manual fixed-subject capture workflow
exact preserved #6066 run-attempt and jobs-response capture
```

The current analyzer ownership relation is:

```text
tools/pulsemech_compute_binding_analyzer_core_v0.py
→ single graph and report implementation

tools/build_pulsemech_compute_binding_report_v0.py
→ stable fixed-source analyzer compatibility wrapper

tools/build_pulsemech_compute_binding_report_from_subject_input_v0.py
→ immutable portable-input analyzer bridge
```

The current subject-input producer ownership relation is:

```text
tools/pulsemech_compute_subject_input_packet_producer_core_v0.py
→ single packet-construction implementation

tools/build_pulsemech_compute_subject_input_packet_v0.py
→ stable fixed-source producer compatibility wrapper
```

The merged current-run expectation relation is:

```text
schemas/pulsemech_compute_current_run_export_expectation_v0.schema.json
→ exact current-run expectation contract

examples/compute/
pulsemech_compute_current_run_export_expectation_example_v0.json
→ canonical checked-in example

tools/check_pulsemech_compute_current_run_export_expectation_v0.py
→ strict semantic validator

tests/test_check_pulsemech_compute_current_run_export_expectation_v0.py
→ permanent registered validator regression

tools/build_pulsemech_compute_current_run_export_expectation_v0.py
→ merged machine expectation producer

tests/test_build_pulsemech_compute_current_run_export_expectation_v0.py
→ permanent registered producer and execution-contract regression
```

The completed current-run construction and workflow relation is described in
Sections 24–26. The historical Step 4A acquisition and its exact evidence are
recorded separately in Section 26.

The repository does not yet contain a merged and complete:

```text
runtime-observation producer
runtime-observed connected proof
per-axis compute-resource measurement surface
compute budget
active compute-related release enforcement
```

The current-run automation implementation and permanent regression surface are
complete through Step 3G. The separate Step 4A historical input capture has also
been preserved and replayed.

```text
current-run contract and machine construction:
implemented and regression-proven

current-run candidate workflows:
implemented; manual and non-active

manually dispatched public Step 3F/3G execution record:
not claimed by this state record

historical Step 4A acquisition and offline replay:
completed for exact #6066 attempt 1

release-authority effect:
none
```

---

## 2. Purpose

The purpose of this workstream is to determine whether executed compute has an
explicit, verifiable relation to a completed PULSEmech state transition.

The core question is not:

```text
How much compute was available?
```

The core relation is:

```text
executed compute
→ identified source
→ recorded subject-run inputs
→ recorded outputs
→ observed downstream consumption
→ declared transition, evidence, preservation, advisory or observer role
→ permitted mutation authority
→ mechanical consequence
```

The intended output is a deterministic record that distinguishes compute that
is mechanically bound to the transition from compute whose relation is:

```text
complete
partial
absent
unknown
duplicated
advisory only
observer only
outside the subject transition
```

The workstream separates three questions:

```text
Did compute execute?

What exact relation did it have to the transition?

Was that relation permitted to affect authority-bearing state?
```

Execution alone answers only the first question.

---

## 3. Core proposition

A compute execution is not part of the release-authority mechanism merely
because it ran inside the same workflow.

```text
workflow presence
≠
transition binding

step success
≠
transition binding

artifact production
≠
transition binding

report publication
≠
transition binding

model invocation
≠
transition binding

AI involvement
≠
transition binding
```

A complete compute binding requires:

```text
compute identity
+ exact source identity
+ source digest
+ exact subject-run binding
+ exact input identities and digests
+ exact output identities and digests
+ observed downstream consumption
+ declared role
+ permitted mutation authority
→ mechanically bound compute
```

A declaration alone is insufficient.

A report that states that a node is required is not proof that the node
contributed to the transition.

A filename or display label is not an exact source identity.

An artifact existing in the same package is not proof that its value was
consumed downstream.

A passing process exit code is not proof that the produced state was admitted
into the authority path.

---

## 4. AI-native operation and anti-bureaucracy rule

The compute workstream is machine-operable by design.

Its schemas, packets, artifact graphs, source identities, digests, validators,
diagnostics and state relations are intended to be traversed by an AI-native
operator.

The operating relation is:

```text
machine-readable compute state
→ AI traversal
→ exact relation reconstruction
→ exact finding or bounded next action
→ human policy and consequence control
```

Mechanical detail does not imply that a human must manually read and operate
every file.

```text
large machine-readable proof surface
≠
large human administrative burden
```

The AI-native operator may:

```text
locate canonical contracts
resolve merged and open implementation state
traverse packet and carrier identities
compare declared and observed relations
identify missing binding axes
prepare deterministic validation commands
isolate exact failing relations
prepare bounded code or documentation changes
```

The human remains responsible for:

```text
policy selection
authority-boundary changes
promotion decisions
external consequence
review of unresolved or conflicting state
```

This preserves:

```text
AI operation
≠
AI self-authority
```

The AI operator cannot replace missing evidence with an assertion.

It cannot promote:

```text
example
→ observed

candidate
→ active

open PR
→ merged

diagnostic
→ authority
```

The primary evidence source must not be a hand-maintained operational form.

The analyzer derives state from machine surfaces:

```text
workflow source
run metadata
policy
materialized gate-set records
status artifacts
decision artifacts
evidence manifests
verifier reports
artifact inventories
artifact-provenance bindings
preservation manifests
runtime packets
exact file digests
```

Any additional declaration must remain:

```text
small
versioned
digest-bound
machine-readable
reviewable
consumed by the analyzer
```

A declaration with no observed downstream relation remains partial or
unresolved.

---

## 5. Authority and non-activation rule

The compute-binding report, analyzer, packet, expectation, relation record and
candidate materializer observe or reconstruct the existing authority path.

They do not replace:

```text
declared release policy
workflow-effective required-gate materialization
final status.json
PULSE_safe_pack_v0/tools/check_gates.py
the primary ALLOW or BLOCK result
```

The following do not independently create release authority:

```text
compute-binding report
subject-input packet
current-run expectation
runtime-observation packet
planned-observed relation
candidate materializer report
candidate-only gate check
preservation record
reader surface
audit surface
AI operator output
```

No compute-related gate may become active implicitly.

Gate registration and gate activation are separate operations.

The currently registered compute candidate set remains absent from:

```text
required
core_required
release_required
advisory
```

The fixed-source candidate-only exit result does not alter the historical
PULSE CI #6066 ALLOW decision.

The current-run expectation contract fixes:

```text
expectation_is_release_authority:
false

produced_packet_is_release_authority:
false

activates_compute_gate:
false

creates_compute_budget:
false
```

---

## 6. Analysis identity and observer boundary

Every analysis preserves two separate identities:

```text
subject run
→ the completed run being analyzed

analysis run
→ the separate execution that constructs the compute-binding record
```

The subject identity includes:

```text
repository
workflow identity
workflow run ID
workflow run number
workflow run attempt
source commit
source ref
release candidate
run mode
active policy sets
policy identity and digest
materialized gate-set digest, when available
final-status digest
release-decision digest
terminal decision
```

The analyzer must not silently substitute current repository state for the
exact source state of the subject run.

The fixed-source implementation uses an explicit offline observer identity:

```text
completed subject run
→ separate offline analysis
→ compute-binding report
```

Observer compute is outside subject transition totals.

If a later analyzer executes after the terminal decision inside the same
workflow, it remains observer compute unless exact evidence proves another
role.

This prevents recursive self-accounting.

The current-run expectation additionally separates:

```text
subject repository revision
≠
protected control-plane revision
```

The subject must not select the protected control-plane revision.

---

## 7. Graph model

The compute-binding report represents a directed graph of compute nodes, state
nodes and exact observed relations.

### Compute-node types

```text
workflow_job
workflow_step
local_tool_execution
github_action
verifier_execution
materializer_execution
external_service_call
model_inference
artifact_builder
report_builder
package_verifier
observer_execution
unknown
```

### State-node types

```text
policy
materialized_gate_set
release_evidence
candidate_state
verifier_report
status_artifact
decision_artifact
attestation
manifest
package
preservation_record
reader_surface
publication_surface
```

### Edge types

```text
reads
produces
verifies
derives
materializes
folds
enforces
references
preserves
publishes
```

Every observed edge binds exact identities and digests where the source format
permits them.

Missing identities remain missing.

The analyzer must not manufacture:

```text
source identity
run identity
timing
input relation
output relation
downstream consumption
resource measurement
```

---

## 8. Binding mechanics

### Compute-node identity

A compute node may record:

```text
node_id
node_type

workflow_name
job_name
step_name
step_index

tool identity
tool version
source path or URI
source revision
source SHA-256

action repository
action ref
action commit SHA

command identity
execution environment

subject run key
analysis run key
started UTC
completed UTC
exit code
```

A mutable action tag is not equivalent to an immutable action commit.

An absent source digest remains absent or unknown.

### State-node identity

A state node may record:

```text
state_id
state_type
path_or_uri
sha256
size_bytes
schema identity
producer node identity
subject run key
release candidate identity
policy relation
gate relation
authority-bearing state
```

A path alone is insufficient when a digest is available.

A filename reused across runs is not a current-run binding.

### Declared and observed relations

```text
declared relation
→ what workflow, policy, plan, manifest or contract says should occur

observed relation
→ what exact recorded state and downstream references show occurred
```

A complete relation requires both when both are expected.

```text
declared execution
+ exact source
+ exact run binding
+ exact output
+ observed downstream consumption
→ observed execution binding
```

```text
declared required execution
+ no exact output or consumer evidence
→ partial or unresolved relation
```

```text
observed execution
+ no matching plan expectation
→ observed_but_not_planned
```

### Binding roles

```text
transition
evidence
preservation
advisory
observer
unknown
```

A transition node directly contributes to:

```text
gate-set materialization
final-status construction
strict enforcement
terminal ALLOW or BLOCK production
```

An evidence node produces or verifies evidence required by an active
materialized gate.

A preservation node preserves state required for reconstruction or independent
verification.

An advisory node produces a reader, diagnostic, publication or
non-authoritative analysis surface.

An observer analyzes an already completed subject run.

### Binding status

```text
complete
partial
none
unknown
```

`complete` requires all role-applicable links.

`partial` means that a relevant relation is declared or partly observed but one
or more required links are absent.

`none` means that no qualifying relation was found and the available evidence
is sufficient to establish absence.

`unknown` means that evidence is insufficient to classify safely.

Unknown remains distinct from none.

### Primary classes

```text
transition_bound
evidence_bound
preservation_bound
advisory_bound
observer
unbound
unknown
```

### Mutation-authority classes

```text
none
advisory_output
preservation_output
release_evidence
candidate_state
verifier_state
materialized_gate_set
final_status
release_decision
```

A node must not mutate above its permitted authority class.

---

## 9. Unbound authoritative mutation

The strongest authority-integrity condition in this workstream is the absence
of unbound decision-state mutation.

```text
compute node
+ writes authority-bearing state
+ lacks complete authority binding
→ unbound authoritative mutation
```

This differs from ordinary unbound or unresolved read-only compute.

```text
unbound read-only compute
→ architecture or efficiency finding

unbound authoritative mutation
→ authority-integrity finding
```

The registered non-active candidate gate:

```text
compute_transition_unbound_mutation_absent
```

materializes this distinction.

In the fixed-source #6066 proof it evaluates to literal `true`.

That result does not activate release enforcement.

---

## 10. Analysis levels

Every report declares an analysis level.

### `structural_declared`

```text
workflow structure
+ policy structure
+ manifests
→ declared graph only
```

This level may identify expected relations.

It must not claim observed digest consumption.

### `artifact_observed`

```text
declared graph
+ exact state-artifact digests
+ observed cross-artifact references
→ artifact-level observed graph
```

This level is implemented and proven against the preserved PULSE CI #6066
subject.

### `runtime_observed`

```text
artifact-observed graph
+ recorded execution identity
+ job and step timing
+ runtime input/output relations
+ external-call records
+ model-use records
→ runtime-observed graph
```

The runtime-observation contract is implemented.

A runtime-observation producer and complete runtime-observed subject chain are
not yet implemented.

A lower analysis level must not claim a higher-confidence classification.

The current-run expectation is metadata-only and does not by itself raise the
analysis level. The Step 4A platform-response capture likewise remains an exact
producer input; its job and step fields are not a runtime-observed graph.

---

## 11. Compute-binding report contract

The implemented report identity is:

```text
schema_version:
pulsemech_compute_binding_report_v0

report_type:
pulsemech_compute_binding_report
```

Implemented files include:

```text
schemas/pulsemech_compute_binding_report_v0.schema.json
examples/compute/pulsemech_compute_binding_report_6066_example_v0.json
tools/check_pulsemech_compute_binding_report_v0.py
tools/pulsemech_compute_binding_analyzer_core_v0.py
tools/build_pulsemech_compute_binding_report_v0.py
tests/test_pulsemech_compute_binding_report_schema_v0.py
tests/test_check_pulsemech_compute_binding_report_v0.py
tests/test_build_pulsemech_compute_binding_report_v0.py
tests/test_pulsemech_compute_binding_analyzer_core_v0.py
```

The contract preserves:

```text
tool identity
analysis boundary
exact subject identity
input artifact identities
compute nodes
state nodes
edges
resource axes
summary counts
findings
errors
record construction status
```

The report is deterministic for identical canonical inputs.

```text
report ok = true
```

means:

```text
the report was constructed and validated successfully
```

It does not mean:

```text
release allowed
all compute bound
comparison complete
workflow efficient
resource measurement complete
no findings
```

The terminal release decision remains a separate recorded subject value.

---

## 12. Fixed-source artifact-observed implementation

The first builder is intentionally fixed to the preserved PULSE CI #6066
subject.

It verifies exact immutable carrier identities including:

```text
preservation archive SHA-256
preservation archive size
visible preservation manifest
visible README
visible SHA256SUMS
outer GitHub artifact identities
complete-package member inventory
package-completeness report
independent package-verification report
subject-run identity
source commit
policy identity
final status
release decision
```

Canonical fixed-source carrier:

```text
file:
PULSE_CI_6066_release_grade_artifact_preservation_v0.zip

SHA-256:
7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966

size:
44660 bytes
```

Subject identity:

```text
repository:
HKati/pulse-release-gates-0.1

workflow:
PULSE CI

workflow run ID:
29249887581

workflow run number:
6066

workflow run attempt:
1

subject run key:
GITHUB_RUN_ID=29249887581|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI

source commit:
46b639706e23f80fe296a8893be18e2b5ab21f7e

release candidate:
main

run mode:
prod

historical decision:
ALLOW
```

The builder is:

```text
offline-capable
read-only
deterministic
strictly validated
fixed-source
artifact-observed
non-active
non-authorizing
```

It refuses subject mutation and unsafe output paths.

---

## 13. Portable subject-input contract

The implemented portable packet identity is:

```text
schema_version:
pulsemech_compute_subject_input_packet_v0

packet_type:
pulsemech_compute_subject_input_packet
```

Implemented files include:

```text
schemas/pulsemech_compute_subject_input_packet_v0.schema.json
examples/compute/pulsemech_compute_subject_input_packet_6066_example_v0.json
examples/compute/pulsemech_compute_subject_input_packet_6066_observed_v0.json
tools/check_pulsemech_compute_subject_input_packet_v0.py
tools/pulsemech_compute_subject_input_packet_producer_core_v0.py
tools/build_pulsemech_compute_subject_input_packet_v0.py
tests/test_pulsemech_compute_subject_input_packet_schema_v0.py
tests/test_check_pulsemech_compute_subject_input_packet_v0.py
tests/test_build_pulsemech_compute_subject_input_packet_v0.py
tests/test_pulsemech_compute_subject_input_packet_producer_core_v0.py
tests/test_pulsemech_compute_subject_input_packet_6066_observed_v0.py
ci/tools-tests.list
```

The contract separates three identities:

```text
packet-record construction status
≠
referenced subject-data origin
≠
immutable external-carrier class
```

The checked-in historical-data fixture is:

```text
record_status:
example

fixture source-data status:
historical_observed

carrier kind:
preservation_archive

packet producer:
absent

packet-producer execution claimed:
false
```

The machine-produced proof is:

```text
record_status:
observed

production mode:
fixed_source_adapter

packet scope:
fixed_source_adapter

producer source revision:
3cd57dc9e88e6f804dbb134c864f4207688bddc2

producer source SHA-256:
152e9ed67bf10389726ab7e27d59005afe62d23488e8cd13ffa58443bee13d18

packet ID:
subject-input:pulse-ci-6066/fixed-source-adapter/851cffe9ebee9399/v0

carrier kind:
preservation_archive

fixture provenance:
absent
```

The example and observed packet carry the same producer-independent subject,
carrier, authority-source, artifact, role, coverage, content-boundary and
authority-boundary surfaces.

Their difference is packet-record provenance.

```text
example fixture
→ fixture_provenance present
→ producer absent

observed proof
→ fixture_provenance absent
→ exact producer execution present
```

The packet is:

```text
metadata-only
digest-bound
carrier-dependent
artifact-observed
read-only
non-authoritative
```

It is not:

```text
a compute-binding report
a runtime-observation packet
a release decision
a gate result
a hand-maintained authority form
```

The strict validator reconstructs:

```text
packet provenance branch
exact subject-run identity
exact workflow, policy and registry source bytes
exact immutable carrier SHA-256 and size
nested ZIP membership
artifact SHA-256 values and byte sizes
provider bindings
role bindings
package inventory
preservation SHA256SUMS
subject, decision, authority and artifact-binding relations
coverage counters
deterministic diagnostics
```

---

## 14. Reusable subject-input producer core and trusted bootstrap

PR #2778 extracted one reusable producer core while preserving the established
fixed-source CLI path.

The merged structure is:

```text
tools/pulsemech_compute_subject_input_packet_producer_core_v0.py
→ one packet-construction implementation

tools/build_pulsemech_compute_subject_input_packet_v0.py
→ fixed-source compatibility wrapper

FIXED_SOURCE_6066_PROFILE
→ explicit fixed-source production profile
```

The reusable core owns:

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

The equivalence proof is:

```text
fixed-source wrapper
→ reusable producer core
→ packet A

direct reusable producer core
+ FIXED_SOURCE_6066_PROFILE
+ identical source and execution bindings
→ packet B

packet A bytes
=
packet B bytes
```

Merged implementation:

```text
PR:
#2778

commit:
951dd5c968a72ba86ae8cde2e1fa3d36434832b8
```

PR #2783 then moved committed core verification into the wrapper's
pre-execution trust bootstrap.

The verified path is:

```text
literal wrapper invocation path
→ wrapper and parent-component symlink checks
→ approved absolute Git selection
→ exact repository HEAD
→ exact committed wrapper blob
→ exact committed producer-core blob
→ one secure producer-core byte capture
→ digest calculation
→ compilation
→ execution
```

The same byte buffer is used for:

```text
committed-byte comparison
SHA-256 calculation
compilation
execution
```

Merged implementation:

```text
PR:
#2783

commit:
04d5b03007ce01435f4ec83345ff6e1aa76d6d7e
```

The hardened path rejects:

```text
uncommitted top-level core code
wrapper symlink aliases
parent-path symlink aliases
core symlinks
fake Git on caller PATH
caller PATHEXT executable substitution
```

This establishes one verified producer implementation.

This fixed-source bootstrap predates the separately completed current-run
wrapper recorded in Sections 25–27. Both retain one reusable producer core.

---

## 15. Runtime-observation contract

Implemented files include:

```text
schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json
examples/compute/pulsemech_compute_runtime_observation_packet_example_v0.json
tools/check_pulsemech_compute_runtime_observation_packet_v0.py
tests/test_pulsemech_compute_runtime_observation_packet_schema_v0.py
tests/test_check_pulsemech_compute_runtime_observation_packet_v0.py
```

The contract can represent:

```text
packet identity and predecessor chain
subject and run binding
execution observations
runtime state observations
external-service calls
model inferences
capture status
source identity
timing
resource axes
downstream consumers
coverage
```

The packet contract is strict and fail closed.

Metadata-only or absent capture must not become complete body capture.

Raw prompt or raw output absence remains explicit.

The contract alone does not produce runtime evidence.

Current state:

```text
runtime packet schema:
implemented

runtime packet validator:
implemented

runtime packet producer:
not implemented

live runtime capture:
not active
```

---

## 16. Planned-observed relation

Implemented files include:

```text
schemas/pulsemech_compute_planned_observed_relation_v0.schema.json
examples/compute/pulsemech_compute_planned_observed_relation_example_v0.json
tools/check_pulsemech_compute_planned_observed_relation_v0.py
tools/build_pulsemech_compute_planned_observed_relation_v0.py
tests/test_pulsemech_compute_planned_observed_relation_schema_v0.py
tests/test_check_pulsemech_compute_planned_observed_relation_v0.py
tests/test_build_pulsemech_compute_planned_observed_relation_v0.py
```

The builder consumes:

```text
one exact integration plan
one exact compute-binding report
zero or more runtime-observation packets
optional ID-keyed explicit expectations
```

It emits:

```text
exact plan binding
exact compute-report binding
runtime-packet bindings
expectations
observations
relations
coverage
findings
summary
non-authoritative boundary
```

Possible relation statuses include:

```text
planned_presence_only
planned_and_observed
planned_but_not_observed
observed_but_not_planned
execution_identity_mismatch
source_digest_mismatch
run_binding_mismatch
declared_role_mismatch
authority_class_mismatch
downstream_consumption_missing
ambiguous_observation_match
unresolved_due_to_coverage
```

Every observation remains visible and classified.

An observation without a matching expectation is not discarded.

Incomplete coverage prevents a complete comparison.

A relation record does not create a gate result or release decision.

---

## 17. Fixed-source #6066 plan and expectation binding

The connected fixed-source proof uses:

```text
examples/compute/
pulsemech_compute_fixed_source_6066_component_manifest_v0.json

examples/compute/
pulsemech_compute_fixed_source_6066_integration_plan_v0.json

examples/compute/
pulsemech_compute_subject_run_expectations_6066_v0.json
```

The component manifest declares one execution-planning anchor:

```text
pulse_check_gates_v0
→ PULSE_safe_pack_v0/tools/check_gates.py
```

Exact component-manifest SHA-256:

```text
6c2fdf3b01388b82f19f20e3da4a2985b8802fa3a4c9957441969ca025af7b50
```

The plan binds:

```text
historical source commit:
46b639706e23f80fe296a8893be18e2b5ab21f7e

historical policy SHA-256:
7160c37e5e04099c1b6960229d944076503380ae7d2a712c00da459a275d3c31

check_gates.py SHA-256:
3a85ed757d5569e87364bd5de511dc1985c60d97e29ee3f782e08197fa4f5c8f

check_gates.py size:
2535 bytes

plan operation SHA-256:
8226cc8235ed3f7a4262326232cf5a374b2d57b90f4e48538b164d6a116a762e
```

Exact integration-plan SHA-256:

```text
28f254edd341f2d98aea1b8c297019fd664d4a97bb17347be902f93b8bb99127
```

The explicit expectation binds:

```text
expectation:
expectation:execute-check-gates-consumed

expected role:
transition

expected mutation authority:
release_decision

execution required:
true

downstream consumption required:
true
```

The evidence responsibilities remain separate:

```text
integration_plan_operation
→ component presence and source identity

workflow_execution_declaration
→ execution expectation, role and mutation authority

recorded_manifest
→ downstream consumption expectation
```

Exact historical workflow SHA-256:

```text
0d74133efdbe7c06672cc691d17ed5cdeec3c04df3e0ba465accfd187fd3c649
```

Exact recorded artifact-provenance binding SHA-256:

```text
eeedae701541f34841d74d0ad12a37e4c6ebdf2f24260616c9cc356e241d87ff
```

Exact expectations-file SHA-256:

```text
a48cb7831c623afc53fbb082adb08edd56cdfee26a5ec399bc2c27dfb2b68736
```

---

## 18. Non-active candidate policy surface

The canonical policy is:

```text
policy ID:
pulse-gate-policy-v0

policy version:
0.1.7
```

The registered candidate set is:

```text
compute_planned_observed_relation_candidate
```

It contains:

```text
compute_transition_path_complete
compute_transition_authority_binding_ok
compute_transition_unbound_mutation_absent
```

The candidate identities are:

```text
category:
compute

stability:
experimental

default normative:
false
```

They remain absent from active and advisory sets.

Candidate materializer:

```text
tools/
fold_pulsemech_compute_planned_observed_relation_into_status_v0.py
```

The materializer:

```text
strictly validates the relation
requires the non-authoritative relation boundary
derives three literal booleans independently
rejects conflicting existing candidate values
writes only a separate folded candidate status
preserves the base status
distinguishes successful materialization from candidate all-true
```

The enforcement proof uses:

```text
tools/policy_to_require_args.py
→ policy-derived candidate require-list

PULSE_safe_pack_v0/tools/check_gates.py
→ unchanged generic strict checker
```

No compute gate identity is hardcoded into the generic checker.

---

## 19. Connected fixed-source #6066 proof

The connected proof is implemented in:

```text
tests/test_pulsemech_compute_fixed_source_candidate_chain_v0.py
```

The complete generated chain is:

```text
preserved PULSE CI #6066 subject
→ fixed-source compute-binding report builder
→ strict compute-report validation
→ exact historical integration plan
→ explicit check-gates subject-run expectation
→ planned-observed relation builder
→ strict relation validation
→ candidate materializer
→ separate folded candidate status
→ policy-derived candidate require-list
→ unchanged generic check_gates.py
```

### Generated compute-binding report

```text
record status:
observed

analysis level:
artifact_observed

subject compute nodes:
18

observer nodes:
1

transition-bound nodes:
2

evidence-bound nodes:
4

preservation-bound nodes:
0

advisory-bound nodes:
0

unbound nodes:
0

unknown nodes:
12

unbound authoritative mutation count:
0

decision closure complete:
false

authority binding complete:
false

resource measurement status:
none
```

### Generated planned-observed relation

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

decisive relations:
6

unresolved relations:
13

identity coverage:
unknown

execution coverage:
partial

comparison status:
unknown

comparison complete:
false
```

The exact planned relation is:

```text
expectation:execute-check-gates-consumed
→ compute:check-gates
```

Its evaluation is:

```text
source identity:
match

execution identity:
match

subject-run binding:
match

declared role:
match

authority class:
match

downstream consumption:
observed

coverage:
complete

decisive:
true

relation status:
planned_and_observed
```

### Derived candidate result

```text
compute_transition_path_complete:
false

compute_transition_authority_binding_ok:
false

compute_transition_unbound_mutation_absent:
true
```

Materializer result:

```text
relation validated:
true

materializer ok:
true

folded status written:
true

candidate all-true:
false
```

Policy-derived candidate check:

```text
two literal false candidate gates
→ exit 1
```

Missing candidate gate:

```text
one required candidate gate absent
→ exit 2
```

This is a candidate-only fail-closed result.

It is not a release-authority result.

### Negative and safety proof

The regression verifies fail-closed behavior for:

```text
subject-run-key mismatch
subject-source-commit mismatch
release-candidate mismatch
plan-operation identity mismatch
same-size preservation-archive corruption
attempted preserved-subject overwrite
invalid generated relation
missing candidate gate
```

It also verifies:

```text
byte-deterministic generated relation
byte-deterministic folded candidate status
byte-identical base status
byte-identical protected inputs
no subject-package mutation
```

Post-merge audit:

```text
review result:
PASS

actionable findings:
none

targeted regressions:
207 passed
```

---

## 20. Meaning of the fixed-source result

The fixed-source result proves that the mechanism can:

```text
identify one exact transition execution
bind its source and subject run
bind its declared role
bind its mutation authority
bind its downstream consumption
retain every other observation
preserve incomplete coverage
derive candidate state without inventing completion
fail closed without altering release authority
```

The result:

```text
false
false
true
```

is not an implementation failure.

It is the exact artifact-observed boundary of the preserved #6066 subject.

The first two candidate gates remain false because the preserved package does
not provide complete source and execution coverage for the entire transition
and authority path.

The third remains true because the evidence contains no unbound
authority-bearing mutation.

The proof does not claim:

```text
that PULSE CI #6066 was inefficient
that unresolved nodes were unbound
that all observed-but-unplanned compute was unnecessary
that runtime execution was invalid
that resource consumption was excessive
```

Artifact-observed incompleteness identifies a recording boundary.

It does not substitute a judgment for missing evidence.

---

## 21. Resource vector and transition efficiency

The workstream must not force different resource units into one synthetic
number.

Possible resource axes include:

```text
runner_wall_seconds
job_wall_seconds
step_wall_seconds

cpu_seconds
gpu_seconds
memory_gb_seconds

network_bytes_sent
network_bytes_received
storage_bytes_written
artifact_bytes_uploaded

external_api_calls
model_input_tokens
model_output_tokens

retry_count
rerun_count
```

Unavailable values remain unavailable.

Different units must not be added together.

For an axis `a`:

```text
measured_total_a
=
sum of recorded values for nodes with a known value on axis a
```

Per-axis distributions may later include:

```text
transition_bound_ratio_a
evidence_bound_ratio_a
preservation_bound_ratio_a
advisory_bound_ratio_a
unbound_ratio_a
unknown_ratio_a
```

Each ratio is relative only to measured coverage on that axis.

A ratio with incomplete coverage must not be represented as total-system
consumption.

Transition efficiency is:

```text
compute resource vector
↔
verified binding-role distribution
```

It is not one scalar.

No compute budget is defined.

No resource-measurement gate is registered or active.

A budget must not be introduced before:

```text
units are stable
coverage is explicit
classification is reproducible
current-run production is available
runtime-observed proof is complete
fixed-run replay is preserved
false and missing states are tested
```

---

## 22. Current-run export expectation contract

The current-run artifact-observed lane now has a merged expectation contract.

The completed sequence is:

```text
PR #2784
→ strict current-run expectation schema

PR #2785
→ canonical checked-in expectation example

PR #2786
→ strict semantic validator

PR #2787
→ validator trust-boundary hardening

PR #2788
→ permanent registered validator regression
```

Merged commits:

```text
PR #2784:
b010d52bffa9a5fc43b157dac7e9f5863cf008dc

PR #2785:
6f4f66c159604bce2e45889d46958651610cd958

PR #2786:
bf2c7886529a45286bb61bae552a292e7619eeeb

PR #2787:
57b2c3bc2ac3582e1956c1e3a109fcb71f827ca2

PR #2788:
031e0f2b009993e549b7831baf37cf3a990baf39
```

The expectation identity is:

```text
schema_version:
pulsemech_compute_current_run_export_expectation_v0

document_type:
pulsemech_compute_current_run_export_expectation
```

The contract binds:

```text
one exact current workflow-run subject
one exact subject source revision
one separate protected control plane
one exact protected control-plane revision
one expected current-run packet-producer profile
one finalized current-run export carrier identity
one archive-layout contract
one authority-source set
one downstream observed packet contract
one closed content boundary
one closed authority boundary
```

### Example and observed branches

The checked-in example requires:

```text
record_status:
example

fixture_provenance:
present

expectation_producer:
absent

expectation scope:
example

carrier kind:
example_archive

carrier producer:
null
```

The machine-produced branch requires:

```text
record_status:
observed

fixture_provenance:
absent

expectation_producer:
present

expectation scope:
current_run_export

carrier kind:
current_run_export_archive

carrier producer:
present
```

The sole authoritative finalized-carrier digest is:

```text
carrier.sha256
```

The expectation identity does not carry a second competing carrier digest.

### Subject identity

The subject carries:

```text
repository
workflow name
workflow path
workflow ref
workflow run ID
workflow run number
workflow run attempt
subject run key
source commit
source ref
event name
release candidate
run mode
active policy sets
policy ID
policy SHA-256
materialized gate-set SHA-256 or null
final-status SHA-256
release-decision SHA-256
ALLOW or BLOCK decision
```

### Protected control plane

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

The contract fixes:

```text
trust_mode:
protected_exact_revision

checkout_role:
protected_control_plane

separate_from_subject_checkout:
true

subject_may_select_revision:
false
```

### Packet producer profile

The profile binds:

```text
expected producer source path
expected production mode
expected packet scope
expected packet identity mode
expected carrier ID namespace
expected carrier kind
expected carrier media type
expected artifact payload mode
expected subject repository
expected subject revision
expected subject run key
expected signer policy path
expected archive-layout ID
```

### Content boundary

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

### Authority boundary

```text
write_mode:
expectation_only

writes_subject_run:
false

writes_target_repository:
false

mutates_carrier:
false

changes_release_authority:
false

changes_gate_policy:
false

changes_gate_semantics:
false

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

## 23. Strict current-run expectation validator and regression

The strict validator verifies the expectation as a complete cross-contract
relation.

Its verification surface includes:

```text
strict UTF-8 JSON
BOM rejection
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
preserves an independent deny-all runtime resolver
walks only schema-valued Draft 2020-12 positions
follows internal references into reached schema objects
separates canonical path identity from reviewed blob identity
calculates schema identity from descriptor-captured bytes
keeps expectation and downstream schema states independent
validates a complete downstream observed packet witness
converts resolver and schema failures into deterministic diagnostics
```

The reviewed contract-stage Git blob identities recorded through PR #2788 are:

```text
expectation schema:
c0bc5a21f5bf46c529341d2e805f26525c70c7f4

subject-input schema:
e1f982ffaf900c6c17745624d80f9f38b374448b

expectation validator:
16b75b7df2524515146bf3472e0191a52cfad037
```

The validator distinguishes:

```text
supplied contract validity
≠
canonical reviewed-contract verification
```

The permanent regression is registered in:

```text
ci/tools-tests.list
```

It covers:

```text
deterministic raw diagnostic bytes
CRLF normalization rejection
strict parser failures
canonical serialization
symlinked input rejection
invalid repository-root rejection
closed modern Registry resolution
closed RefResolver compatibility resolution
network retrieval denial
local-file retrieval denial
internal JSON Pointer and anchor handling
dirty canonical schema rejection
alternate-path schema rejection
complete observed expectation construction
expectation-producer mismatch rejection
carrier-producer mismatch rejection
POSIX descriptor-chain state
path-based fallback state
```

The merged boundary establishes:

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

This contract-and-validator stage alone did not establish a machine producer.
The subsequently merged producer and its permanent regression are recorded in
Section 24; the remaining current-run components are recorded in Sections 25–27.

---

## 24. Completed current-run expectation builder and regression

The machine current-run expectation builder is merged, hardened and
regression-proven. The former open PR #2789 status is historical, not the
current implementation state.

```text
builder implementation PR:
2789

builder implementation merge:
cafd0338f413522b5609465eaaaf25cf49f1423d

builder path:
tools/build_pulsemech_compute_current_run_export_expectation_v0.py

permanent regression:
tests/test_build_pulsemech_compute_current_run_export_expectation_v0.py

regression sequence:
PR #2814 → PR #2818 → PR #2819

canonical registration:
ci/tools-tests.list

authority effect:
none
```

At the recorded `7444c12...` source basis, the registered regression pins the
builder identity to:

```text
lines:
4306

bytes:
144793

SHA-256:
56893caab8f5198a5e4d64dc55638f2d7365ed1660b85514eabc7461cc15b767

Git blob SHA-1:
f7b22613c759d32d5de0b30c7e86989a0c85bb10
```

These identities replace the earlier open-review candidate identity; they are
not identities of a newly changed tool in this documentation update.

The builder consumes:

```text
canonical builder-input metadata
+ separately supplied trusted current-run identity
+ exact subject repository revision
+ exact current-run final artifacts
+ exact subject authority-source files
+ verified policy and committed schema bytes
+ separate protected control-plane checkout
+ exact protected control-plane revision
→ machine-produced observed current-run expectation
```

The subject, protected control plane, release-target projection and
workflow-effective policy-set relation remain separately bound. The record
must not collapse the release target into the workflow's active-set identity.

The permanent suite includes explicit controls for:

```text
reviewed builder source identity
isolated execution and deferred validation-dependency loading
complete protected CLI surface
exact dimension-preserving current-run binding
release-target projection separate from workflow sets
observed artifact time ordering
canonical unique external signer-policy path
closed non-authority output boundary
trusted absolute Git selection and local-only object access
bounded Git configuration and object reads
promisor and repository SSH-command rejection
verified tree modes and rehashed object identities
separate Git storage
protected output paths
bounded authority-payload retention
canonical deterministic diagnostics
complete synthetic current-run CLI byte determinism
mandatory real-Git prerequisites without skip-based success
exact completed-test and terminal early-exit launcher controls
```

The post-merge Tools smoke execution at the recorded data basis ran all
44 direct-script cases successfully. That suite is permanent implementation
and synthetic-execution evidence. It is not a claim that a public manually
dispatched Step 3F or Step 3G artifact has been produced.

Builder presence does not remove the contract's complete nine-role protected
control-plane requirement. Every execution still has to verify its actual
source revision and required components before producing an expectation.

Sources: [merged builder PR #2789](https://github.com/HKati/pulse-release-gates-0.1/pull/2789),
[builder regression](../../tests/test_build_pulsemech_compute_current_run_export_expectation_v0.py),
and the [recorded post-merge Tools smoke run](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/33996343943/job/101387579869).

---

## 25. Contract-complete protected control plane

The current-run expectation contract and merged builder require one exact
protected control-plane revision containing:

```text
tools/load_pulsemech_compute_current_run_export_carrier_v0.py

.github/workflows/
pulsemech_compute_current_run_export_candidate.yml

tools/build_pulsemech_compute_current_run_export_expectation_v0.py

schemas/
pulsemech_compute_current_run_export_expectation_v0.schema.json

tools/check_pulsemech_compute_current_run_export_expectation_v0.py

tools/pulsemech_compute_subject_input_packet_producer_core_v0.py

tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py

schemas/pulsemech_compute_subject_input_packet_v0.schema.json

tools/check_pulsemech_compute_subject_input_packet_v0.py
```

All nine component paths are present at the recorded merged basis. The carrier
loader, current-run wrapper and Step 3F workflow are completed implementations,
not remaining missing components.

The Step 3G extension also contains:

```text
tools/load_pulsemech_compute_current_run_export_candidate_bundle_v0.py
tests/test_load_pulsemech_compute_current_run_export_candidate_bundle_v0.py

tools/build_pulsemech_compute_current_run_artifact_observed_proof_v0.py
tests/test_build_pulsemech_compute_current_run_artifact_observed_proof_v0.py

.github/workflows/pulsemech_compute_current_run_artifact_observed_candidate.yml
tests/test_pulsemech_compute_current_run_artifact_observed_candidate_workflow_v0.py
```

The complete protected component set remains mandatory at execution time:

```text
missing, dirty or incorrectly bound component at the selected revision
→ fail closed
```

Merged implementation completeness and acceptance of a particular run-bound
input are distinct. Component presence is not an authority promotion or a
substitute for validating an actual carrier and its subject bindings.

Both candidate workflows remain manual and non-active. No public manually
dispatched Step 3F/3G execution record is claimed by this document.

---

## 26. Completed and remaining implementation plan

### Completed Step 1 — portable subject-input contract

Completed:

```text
packet schema
historical example
strict validator
schema regression
validator regression
CI registration
Git source isolation
trusted Git selection
exact carrier verification
nested artifact reconstruction
provider and role reconstruction
coverage reconstruction
```

### Completed Step 1A — fixed-source producer and observed proof

Completed:

```text
deterministic fixed-source producer
carrier size before hashing
carrier SHA-256 before ZIP reads
machine-produced observed packet
pinned historical producer replay
fail-closed replay cleanup
```

### Completed Step 1B — immutable analyzer bridge

Completed:

```text
single packet capture
single carrier capture
same-revision validation and analysis
same-revision carrier verification and reconstruction
stdout-only report
repository-clean execution
```

### Completed Step 2 — reusable analyzer core

Completed:

```text
one analyzer implementation
fixed-source compatibility wrapper
portable-input bridge to the same core
producer identity separated from analyzer identity
regression-identical #6066 report
```

### Completed Step 2A — reusable packet producer core

Completed:

```text
one packet-construction implementation
fixed-source compatibility wrapper
explicit fixed-source profile
wrapper/core byte equivalence
```

### Completed Step 2B — trusted wrapper bootstrap

Completed:

```text
literal invocation-path verification
wrapper and core committed-blob verification
one verified core byte buffer
pre-execution source binding
fake-PATH Git rejection
```

### Completed Step 3A — current-run expectation contract

Completed:

```text
strict expectation schema
canonical example
strict validator
closed schema-reference boundary
reviewed schema-byte binding
permanent registered validator regression
```

### Completed Step 3B — expectation builder

The merged builder produces canonical observed expectations from exact subject
and protected-control-plane inputs. Section 24 records its source identity,
input relation and completed implementation status.

### Completed Step 3C — permanent builder regression

The builder regression and its authoritative direct-script execution contract
are implemented and registered. They distinguish complete executed proof from
collection-only, filtered, skipped or terminal early-exit outcomes.

### Completed Step 3D — current-run carrier component

The finalized-carrier component is implemented and regression-proven:

```text
tools/load_pulsemech_compute_current_run_export_carrier_v0.py
tests/test_load_pulsemech_compute_current_run_export_carrier_v0.py
```

It retains the exact carrier, producer, subject and protected-control-plane
relations. The finalized carrier has one authoritative SHA-256 identity;
downstream consumers still verify its actual payload bytes.

### Completed Step 3E — current-run subject-input wrapper

The current-run wrapper reuses the existing packet producer core:

```text
tools/build_pulsemech_compute_subject_input_packet_current_run_v0.py
tests/test_build_pulsemech_compute_subject_input_packet_current_run_v0.py
```

The wrapper binds the current-run production profile, exact expectation and
verified carrier. It does not introduce a second packet implementation.

### Completed Step 3F — non-active export candidate workflow

The manually dispatched candidate workflow and registered regression are:

```text
.github/workflows/pulsemech_compute_current_run_export_candidate.yml
tests/test_pulsemech_compute_current_run_export_candidate_workflow_v0.py
```

The implemented construction consumes exact subject inputs and an independently
selected protected control plane, producing the finalized carrier, observed
expectation and observed subject-input packet in a non-active candidate bundle.

### Completed Step 3G — artifact-observed proof automation

The terminal implementation merge is PR #2826 at:

```text
9bf7fab95dbcc3532238723d0cf76500263106f5
```

The implemented dependency and reconstruction relation is:

```text
checksum-closed Step 3F candidate bundle
+ exact current-run subject
+ independently selected protected control plane
→ independently verified candidate-bundle intake
→ immutable carrier and packet reconstruction
→ existing subject-input analyzer bridge
→ single reusable analyzer core
→ artifact-observed compute-binding report
→ deterministic current-run integration plan
→ planned-observed relation
→ separate non-active candidate materialization
→ checksum-closed artifact-observed proof bundle
```

This is completed construction capability and permanent regression proof.
It is not a claim of an already produced public manually dispatched Step 3G
proof-bundle instance. The arrows describe dependencies and reconstruction;
they do not replace PULSEmech's primary relational release-authority object.

At the recorded data-merge CI execution, the three Step 3G direct-script suites
passed 30, 32 and 28 cases respectively: 90 total.

The implementation preserves actual false, missing, partial, ambiguous and
unresolved states. Exactly the three existing non-active candidate gates are
materialized into a separate candidate status; the subject status is unchanged.

### Completed Step 4A — exact post-run producer-input capture

This is the historical-reference input boundary defined by
[work order #2856](https://github.com/HKati/pulse-release-gates-0.1/issues/2856).
Its implementation and observed-reference acceptance are complete. The
work-order documentation closure still requires the complete documentation PR
and its own final checks; this record does not predeclare that merge.

#### Implementation and observed-data identities

| Stage | PR | Exact merged commit |
|---|---:|---|
| Capture contract and implementation | #2857 | `c01a00458735178ee5ed8884996d3a6c3a0e29dc` |
| Independent timestamp-range correction and matching regressions | #2860 | `22d14088ae21f84d94c6a6951c0f70ab1bdf0895` |
| Five exact observed capture members | #2861 | `7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9` |

The #2857 merge alone did not close implementation acceptance. Both tools'
canonical UTC range enforcement and their dependent identity regressions were
corrected through #2860 before the reference acquisition.

The completed source surface is:

```text
schemas/pulsemech_compute_post_run_producer_input_capture_manifest_v0.schema.json
contracts/pulsemech_compute_post_run_producer_input_capture_v0.json

tools/capture_pulsemech_compute_post_run_producer_input_v0.py
tools/check_pulsemech_compute_post_run_producer_input_capture_v0.py

.github/workflows/pulsemech_compute_post_run_producer_input_capture_v0.yml

tests/test_pulsemech_compute_post_run_producer_input_capture_contract_v0.py
tests/test_capture_pulsemech_compute_post_run_producer_input_v0.py
tests/test_check_pulsemech_compute_post_run_producer_input_capture_v0.py
```

The networked capture implementation, network-free independent validator and
future runtime-packet producer have distinct roles. The validator does not
import the capture implementation or accept its verdict as proof.

#### Historical subject and separate acquisition

```text
historical repository:
HKati/pulse-release-gates-0.1

historical repository ID:
1061766508

historical workflow:
PULSE CI

historical workflow ID:
191471316

historical workflow path:
.github/workflows/pulse_ci.yml

historical run ID / number / attempt:
29249887581 / 6066 / 1

historical source commit:
46b639706e23f80fe296a8893be18e2b5ab21f7e

historical state:
completed / success

separate capture workflow ID:
350887354

separate capture run ID / attempt:
33986538130 / 1

capture implementation and workflow source:
22d14088ae21f84d94c6a6951c0f70ab1bdf0895

original acquisition artifact ID:
9975323320

observed jobs pages / unique jobs / step records:
1 / 8 / 171
```

The historical run was not rerun. The data-preservation merge is not the
acquisition source revision.

The exact requests are attempt-specific:

```text
GET /repos/HKati/pulse-release-gates-0.1/actions/runs/29249887581/attempts/1
GET /repos/HKati/pulse-release-gates-0.1/actions/runs/29249887581/attempts/1/jobs?per_page=100&page=1
```

The exchange records retain the selected response metadata and explicit
absence states, including final Link-header absence. Reported job count equals
the reconstructed count of eight unique jobs.

#### Exact preserved capture

All five paths below are relative to:

```text
preservation/pulse_ci_6066/post_run_producer_input_capture_v0/
```

| Member | Bytes | SHA-256 | Git blob SHA-1 |
|---|---:|---|---|
| `metadata/run_attempt_exchange_v0.json` | 2886 | `b3510e10f86904888b5c2d120270f6cadfe2086db65c18e5c699acb31fbaa018` | `b6eff652b27c9ad6313d4b25589dacde2e15f788` |
| `metadata/jobs_page_0001_exchange_v0.json` | 3036 | `1866b86cb6449f85fe5a1c6d5138f6583385bffd9ddc1b1246858bba7b7bc566` | `2043b48ab9a583469c0887f9ff586e72c35e5ab2` |
| `pulsemech_compute_post_run_producer_input_capture_manifest_6066_v0.json` | 17905 | `4642546646fc7c78f8b65bce40c3db72fb6847c4e3d454db97b164f1fc14f238` | `3e623150e254f9383c1cec23fa68e714092a3b98` |
| `raw/run_attempt_response.json` | 15097 | `d9e16eb8d68f35ede5019e6138474ae552b966e40fc920fc357ac57e6077fe19` | `84109eb1e163c3ee1021678a4effa6ef2d13f727` |
| `raw/jobs_page_0001_response.json` | 38004 | `ba263d508f2c6893fe4d21056c5e7ee2f993ad5ccacf0476000c159815041a43` | `7d729f6748fccbab3cc9a7722ab63a50a6acfe2d` |

The two raw responses retain the exact entity-body bytes observed by the
capture implementation before parsing or reserialization: no BOM, CR, LF or
trailing newline. Metadata and manifest retain compact sorted UTF-8 canonical
JSON with exactly one terminal LF. The manifest excludes its own final hash
from its inventory.

This new producer-input capture is distinct from the earlier release-grade
preservation carrier described in Section 12. Its five-file merge did not
rewrite that carrier or the previous #6066 preservation records.

The acquisition carrier identities recorded at intake are:

| Carrier | Bytes | SHA-256 |
|---|---:|---|
| Original artifact ZIP | 93589 | `b4a8330ec1bec65110a6d61d9c175345ddd6e9e95c52f1a48ded328cf713bef9` |
| Original inner TAR | 92160 | `a560ae0e47890366171bb0be11d1e4761ea11bc1355bb3d55fc9799ffadc0a1e` |

The cloud post-merge review did not independently reopen those original
carriers. Its execution evidence came from the authentic merged Git objects.
The carrier identities above remain separately recorded acquisition evidence.

#### Completed observed-capture verification

The read-only cloud Codex report titled
“PULSEmech PR #2861 Post-Merge Verification” inspected the exact merge,
its sole parent and tree `b4da3d6ebf567c6e80d3a539e8fc2d1010610213`.
It reported no actionable findings and supported PR 2 technical acceptance.

The report records execution under CPython 3.14.4, jsonschema 4.26.0 and
pytest 9.0.3:

| Executed check | Recorded result |
|---|---|
| Complete inventory and Git/checkout byte comparison | All five members matched exactly; no extra member |
| Independent offline validator on two separate restorations | Both exit 0; stderr empty; complete stdout byte-identical |
| Producer-side input-to-manifest reconstruction, repeated twice | Both reproduced the exact 17905-byte manifest and both exchange metadata files |
| Original capture and tracked-source preservation | Byte-identical before and after; worktree and index clean |
| Complete contract / producer / offline-validator regression suites | 60 / 143 / 151 passed; 354 total |

Each disposable capture used directory modes 0700 and regular-file modes 0600.
Tracked checkout modes were not rewritten; Git's stored file mode does not
reproduce the private filesystem permissions of the acquisition TAR.

The independent CLI used the unchanged validator with isolated Python:

```text
python -I tools/check_pulsemech_compute_post_run_producer_input_capture_v0.py --repository-root <exact-checkout> --capture-root <private-restored-capture>
```

The placeholders denote the review's actual checkout and newly created
private capture directory, not repository files to add.

The returned record included:

```text
record_status: observed
result: validated_offline
ok: true
page_count: 1
job_count: 8
step_record_count: 171
authority_effect: none

manifest_sha256:
4642546646fc7c78f8b65bce40c3db72fb6847c4e3d454db97b164f1fc14f238

complete stdout SHA-256, identical in both runs:
aa589f61760374ce294821c2f21f82475893ea5cf082cd888c7253ed629a2a57
```

Reconstruction used the unchanged producer at `22d14088...`, including
`_load_sources`, `_validate_run_response`, `_run_exchange`,
`_validate_jobs_page`, `_jobs_exchange`, `PageCapture`, `_construct_manifest`
and `_validate_constructed_manifest`.

Subject, byte identities, summaries, counts and exchange wrappers were
recomputed. Original acquisition timestamps, selected HTTP headers and
acquisition provenance were retained as acquisition facts. Parsing and
reserializing the finished manifest alone was not counted as reconstruction.

#### Capture-specific negative evidence

Ten disposable-copy cases covered the nine requested mutation categories.
Each began from a passing restored original and exited 2 on the unchanged
validator.

| Case | Deliberate mutation | Actual rejection |
|---|---|---|
| A1 | Append LF to raw run response | `raw_response_identity_mismatch` at `member_identity` |
| A2 | Append LF to raw jobs response | `raw_response_identity_mismatch` at `member_identity` |
| B | Truncate raw jobs response | `raw_response_identity_mismatch` at `member_identity` |
| C | Remove run exchange metadata | `missing_declared_member` at `inventory` |
| D | Add an undeclared file | `undeclared_extra_member` at `capture_root` |
| E | Change a job attempt from 1 to 2 | `job_run_attempt_mismatch` at `jobs_binding` |
| F | Duplicate a job ID | `duplicate_job_id` at `jobs_binding` |
| G | Set a job timestamp to `2026-07-13T24:00:00Z` | `job_0_started_at_invalid` at `jobs_binding` |
| H | Use a non-attempt-specific jobs endpoint | `manifest_schema_validation_failed` at `schema` |
| I | Set `active_gate_eligible` to true | `manifest_schema_validation_failed` at `schema` |

Cases E–G repaired the temporary raw-body and metadata size/digest/blob
bindings and manifest wrappers before validation. They therefore reached the
intended job/attempt/identity/timestamp checks rather than failing only on a
stale checksum. Cases H and I were rejected by the schema and are not described
as deeper jobs-binding rejections.

These are executed review probes, not new permanently registered tests. The
three existing registered suites cover implementation and fixtures; no
permanent test directly consuming this exact five-member observed directory
was found in that review. The review reported no demonstrated violation of an
existing permanent-test requirement. Documentation does not reclassify the
probes as CI regressions or introduce an extra test requirement.

#### Separate post-merge GitHub execution evidence

The repository-side CI record is distinct from the cloud review execution:

```text
PULSE CI run:
33996343943

run number:
6763

event:
push

head commit:
7444c12c3c9a86591f0aa7f5cef759ec55e6f9e9

Tools smoke job:
101387579869

Python / pytest / jsonschema:
3.11.16 / 9.1.1 / 4.26.0

contract / producer / offline-validator direct suites:
60 / 143 / 151 passed

targeted pytest suite:
94 passed

Tools smoke and complete PULSE CI run:
success

Quality Ledger / status parity step:
success
```

The [actual run](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/33996343943)
and [Tools smoke log](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/33996343943/job/101387579869)
were inspected separately through the repository connection after the cloud
review. The cloud environment could not authenticate to those remote logs;
its report did not claim to have inspected them. The skipped release-grade
jobs remain skipped, not newly established release-grade execution proof.

CI regression success and exact observed-capture replay are separate evidence
relations. The former does not replace the latter.

#### Temporal, availability and authority boundary

The completed historical relation is:

```text
completed historical #6066 attempt
→ platform-response snapshot observed at capture time
→ exact preserved producer input
→ deterministic reconstruction and independent offline validation
→ later reference runtime-packet production, still unimplemented
```

Determinism begins after preservation. A later API request is neither required
nor expected to return the same bytes. Internal reconstruction does not
independently authenticate every external platform fact; raw JSON, selected
transport facts and acquisition provenance retain their distinct evidence roles.

The captured fields do not establish unavailable command bytes, external
calls, model use, resource consumption or downstream state consumption.
Unknown remains distinct from absent; unavailable remains distinct from zero;
platform timestamps remain distinct from measured compute-resource use.

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

The future operational relation remains a different, pre-decision requirement:

```text
current subject run
→ pre-decision exact source capture
→ runtime-observation packet
→ planned–observed transition relation
→ transition-path verification
→ policy-bound authority decision
```

The Step 4A post-run reference cannot retroactively authorize its completed
subject run. It supplies exact preserved inputs for the next producer task;
it neither implements that producer nor promotes any compute gate.

### Step 4 — runtime-observation producer

Still unimplemented. Step 4A above closes its historical producer-input
prerequisite, not runtime-packet production itself.

Produce strict runtime packets from recorded execution while preserving the
historical-reference versus current-run pre-decision distinction:

```text
job and step identity
exact source identity
timing
runtime inputs
runtime outputs
downstream consumers
external-service calls
model inferences
resource axes
```

### Step 5 — runtime-observed connected proof

```text
current artifact-observed report
+ complete runtime packet chain
→ runtime-observed relation
→ candidate materialization
→ fixed-source versus runtime-observed comparison
```

### Step 6 — resource measurement

Add measured per-axis resource coverage without synthetic cross-unit
aggregation.

### Step 7 — promotion decision

Any movement from candidate to advisory, required or release-required remains a
separate policy decision.

```text
successful example
≠ promotion

successful fixed-source replay
≠ promotion

successful portable-input replay
≠ promotion

successful current-run expectation
≠ promotion

successful current-run artifact proof
≠ promotion

successful runtime proof
≠ automatic promotion
```

Promotion requires:

```text
explicit evidence
policy review
negative-path coverage
stable measurement semantics
separate PR
```

---

## 27. Completed implementation sequence

### Design and report foundation

```text
PR #2734
→ compute-to-transition design

PR #2735
→ report schema, example, validator and tests

PR #2736
→ fixed-source report builder

PR #2737
→ fixed-source builder hardening

PR #2738
→ runtime-observation contract
```

### Planned-observed relation and candidate surface

```text
PR #2741
→ relation schema, example, validator and tests

PR #2743
→ relation builder

PR #2744
→ workflow-only cross-source anchor correction

PR #2745
→ candidate gate identities, policy set and materializer
```

### Connected fixed-source proof

```text
PR #2749

merge:
b6149dbd464f7f01760ab5fa80487f7e94e475e7

status:
complete

post-merge review:
PASS
```

### Portable subject-input contract and hardening

```text
PR #2752
→ portable packet contract

PR #2754
→ Git environment isolation

PR #2755
→ active-policy-set order preservation

PR #2756
→ container-cycle diagnostic alignment

PR #2757
→ trusted absolute cross-platform Git selection
```

Final contract-hardening commit:

```text
5e3908a9129f009977d5a6e94a3f8d4fca4e8da5
```

### Fixed-source packet producer and observed proof

```text
PR #2759
→ deterministic fixed-source producer

PR #2760
→ carrier pre-read identity boundary

PR #2761
→ checked-in observed packet and historical replay

PR #2762
→ fail-closed replay cleanup
```

Final observed-proof head:

```text
f5ff95ea78d3d79f2deab0b4647c27b5137e6db5
```

Proof state:

```text
producer regression:
61 passed

observed replay regression:
24 passed

combined subject-input suite:
172 passed

post-merge review:
PASS
```

### Immutable analyzer bridge

```text
PR #2773

merge:
a93359444e13771eb932744dd22b4477a5096019

bridge version:
0.2.0

focused regression:
17 passed

direct manifest execution:
17 passed

historical pre-core report SHA-256:
656459e7fb835814a05a7cc5b8150959d32ed3a0e9ed272c2733038bd441ec4c

post-merge review:
PASS
```

### Reusable analyzer core

```text
PR #2776

merge:
e06acbbcd0beec7846da01322659079171e24562
```

Source identities retained from the completed analyzer-core proof:

```text
fixed-source wrapper SHA-256:
d20cb7fed3d8c1ddc10abc23882ce0cbe17d277498016a580f875614fe47becc

reusable analyzer core SHA-256:
cd108bc70494203f95a3f379f6e0d953331d10357676d553d6858f44729988dd
```

Proof state:

```text
fixed-source regression:
33 passed

analyzer-core regression:
10 passed

subject-input bridge regression:
18 passed

wrapper and bridge report bytes:
identical

post-merge review:
PASS
```

### Reusable subject-input producer core

```text
PR #2778

merge:
951dd5c968a72ba86ae8cde2e1fa3d36434832b8
```

Status:

```text
complete
one producer implementation
fixed-source wrapper/core output:
byte-identical
```

### Pre-execution wrapper-to-core verification

```text
PR #2783

merge:
04d5b03007ce01435f4ec83345ff6e1aa76d6d7e
```

Status:

```text
complete
committed wrapper verified
committed core verified
one verified core byte buffer executed
```

### Current-run expectation contract

```text
PR #2784
→ schema

PR #2785
→ example

PR #2786
→ validator

PR #2787
→ validator hardening

PR #2788
→ permanent validator regression
```

Historical expectation-contract completion basis:

```text
031e0f2b009993e549b7831baf37cf3a990baf39
```

Status:

```text
contract:
complete

validator:
complete and hardened

validator regression:
complete, registered and proven

builder:
subsequently completed; see the sequence below
```

### Current-run automation through Step 3G

```text
PR #2789
→ machine current-run expectation builder

PR #2814
→ permanent builder regression

PR #2818 and PR #2819
→ authoritative regression execution and terminal early-exit boundary

PR #2822
→ finalized current-run export carrier loader

PR #2823
→ current-run subject-input wrapper

PR #2825
→ manual non-active Step 3F export candidate workflow

PR #2826
→ Step 3G candidate-bundle intake, artifact-observed proof builder and workflow

terminal Step 3G implementation merge:
9bf7fab95dbcc3532238723d0cf76500263106f5
```

The completed implementation and registered regressions are distinct from a
public manually dispatched Step 3F/3G proof instance. No such execution
instance is claimed here.

### Historical Step 4A capture

```text
PR #2857
→ capture contract and implementation

PR #2860
→ timestamp correction in both independent tools and matching regressions
→ implementation acceptance

capture execution 33986538130, attempt 1
→ exact historical #6066 response acquisition at source 22d14088...

PR #2861
→ preserve five exact capture members at merge 7444c12...

read-only post-merge verification
→ exact Git-object audit
→ two independent offline replays
→ two input-to-manifest reconstructions
→ ten negative probes
→ observed-reference acceptance
```

Section 26 records full commit, run, member and diagnostic identities and keeps
cloud review evidence separate from GitHub CI execution.

### Historical canonical state synchronization

```text
PR #2795

merge:
575570b8ee3659f9190514e3b561f0df7a980681
```

This synchronized the system-level Technical Overview.

It did not modify compute mechanics.

---

## 28. Interaction with existing PULSE boundaries

The compute-binding workstream preserves:

```text
check_gates.py remains generic
policy remains the source of gate-set identity
gate-list materialization remains policy-derived
status remains the complete gate-state carrier
ALLOW and BLOCK remain terminal release-transition results
preservation remains non-authoritative
reader surfaces remain non-authoritative
candidate materialization remains separate from release authority
```

The analyzer observes these relations.

It does not redefine them.

The current-run expectation records the required protected relation.

It does not create that relation merely by describing it.

The candidate gates are not a parallel release-authority mechanism.

---

## 29. Interaction with SLSA and VSA

The compute-binding workstream remains separate from the SLSA/VSA workstream.

```text
SLSA/VSA:
authenticated upstream evidence statements
→ downstream PULSEmech admission and transition

compute binding:
executed compute
→ exact relation to evidence, state, preservation and transition
```

The workstreams may share:

```text
source identity
artifact digest
policy digest
run binding
verifier identity
attestation digest
```

They must not be merged merely because they share binding fields.

A provenance statement may be an input to PULSEmech.

It does not replace the downstream transition decision.

A compute-binding report may observe that input and its consumer path.

It does not become the release decision.

---

## 30. Non-goals and claim boundary

This workstream does not provide or claim:

```text
carbon accounting
electricity-consumption certification
hardware power certification
cost accounting
global infrastructure utilization
human productivity scoring
employee monitoring
compliance status
certification
a universal workflow-efficiency scalar
a single cross-unit efficiency number
```

It does not claim:

```text
that every unknown node is unbound
that every unbound node is useless
that repeated verification is automatically duplicate work
that advisory output is unnecessary
that trust-separated verifiers are duplicates
that a fixed percentage of compute is unbound
that PULSE CI #6066 was inefficient
that energy or carbon impact has been measured
```

The fixed-source proof establishes:

```text
one exact planned-and-observed transition execution
five observed but unplanned executions
thirteen artifact-level unresolved relations
no observed unbound authoritative mutation
```

These are relation and coverage results.

They are not resource-efficiency conclusions.

The current-run expectation contract establishes a machine contract.

It is not evidence that a current-run carrier or packet has already been
produced.

The builder and current-run automation are merged and regression-proven.
That construction capability is distinct from a public manually dispatched
Step 3F/3G artifact instance.

The Step 4A capture has an actual acquisition and replay record. Its completed
proof remains a historical producer-input proof, not runtime-observed
transition evidence or a resource-efficiency conclusion.

---

## 31. Current non-activation statement

```text
compute-binding report schema:
implemented

compute-binding report validator:
implemented

fixed-source #6066 artifact-observed report:
implemented and proven

runtime-observation contract:
implemented

runtime-observation producer:
not implemented

planned-observed relation:
implemented

compute candidate gate identities:
registered

compute candidate policy set:
declared and non-active

relation-to-candidate-status materializer:
implemented

fixed-source connected candidate proof:
implemented and proven

portable subject-input packet schema:
implemented

historical #6066 example packet:
implemented

strict subject-input validator:
implemented and hardened

fixed-source packet producer:
implemented and proven

machine-produced observed packet:
implemented and replay-proven

immutable subject-input analyzer bridge:
implemented and proven

reusable analyzer core:
implemented and proven

reusable subject-input producer core:
implemented and proven

wrapper pre-execution core binding:
implemented and proven

current-run expectation schema:
implemented

current-run expectation example:
implemented

current-run expectation validator:
implemented and hardened

current-run expectation validator regression:
implemented, registered and proven

current-run expectation builder:
implemented, hardened and regression-proven

current-run expectation builder regression:
implemented, registered and execution-contract proven

current-run carrier component:
implemented and regression-proven

current-run subject-input wrapper:
implemented and regression-proven

current-run candidate workflow:
implemented and regression-proven; manual and non-active

current-run candidate-bundle intake:
implemented and regression-proven

current-run artifact-observed proof automation:
implemented and regression-proven through Step 3G

public manually dispatched Step 3F/3G proof instance:
not claimed by this record

historical post-run producer-input capture:
implemented; exact #6066 observed reference preserved and replay-proven

post-run capture authority effect:
none

runtime-observed connected proof:
not implemented

compute resource measurement:
not implemented

compute budget:
not defined

compute release-required enforcement:
not active

release-authority effect:
none
```

The existing PULSEmech release-authority mechanism remains unchanged.

The reusable cores, wrappers, packets, expectations, validators and relations
remain analysis and evidence-control surfaces.

They do not activate a compute gate, alter an active required-gate set or
produce a release decision.

---

## 32. Mechanical result

The implemented fixed-source relation is:

```text
completed PULSE CI #6066 subject
+ exact source state
+ exact preserved artifacts
+ exact policy
+ exact workflow identity
+ exact terminal decision
+ one explicit check-gates expectation
→ generated compute-to-transition graph
→ generated planned-observed relation
→ candidate materialization
```

The completed portable input boundary is:

```text
exact subject and carrier metadata
+ explicit fixture or producer provenance
+ exact authority-source identities
+ nested content-addressed artifact inventory
+ strict independent reconstruction
→ portable analyzer-input contract
```

The completed packet-production relation is:

```text
fixed-source wrapper
→ verified reusable producer core
→ observed packet

direct reusable core
+ explicit fixed-source profile
→ byte-identical observed packet
```

The completed analyzer relation is:

```text
fixed-source inputs
→ fixed-source analyzer wrapper
→ reusable analyzer core
→ compute-binding report

observed portable packet
→ immutable packet and carrier bridge
→ same reusable analyzer core
→ byte-identical compute-binding report
```

The merged current-run contract relation is:

```text
exact current-run subject
+ exact subject revision
+ separate protected control plane
+ exact protected revision
+ finalized carrier identity
+ authority-source identities
+ expected packet profile
→ strict current-run expectation contract
→ strict validator
→ permanent regression
```

The completed current-run automation extends this contract through:

```text
merged expectation builder and permanent regression
→ finalized current-run carrier component
→ observed subject-input wrapper using the existing producer core
→ non-active Step 3F candidate workflow
→ independent candidate-bundle intake
→ immutable analyzer bridge and single reusable core
→ artifact-observed report and planned-observed relation
→ separate non-active candidate state
→ checksum-closed Step 3G proof-bundle construction
```

The completed historical Step 4A relation is:

```text
exact #6066 run attempt
+ exact capture-time platform responses
+ exact exchange records
+ exact contract, schema and implementation identities
→ five checksum-bound preserved members
→ repeated independent offline validation
→ repeated byte-identical manifest reconstruction
→ rejected disposable-copy mutations
→ historical reference producer input
```

This reference input does not replace the future current-run pre-decision
capture requirement. Runtime-packet production, runtime-observed connected
proof, resource measurement and policy promotion remain later work.

The fixed-source #6066 candidate result remains:

```text
transition path complete:
false

transition authority binding complete:
false

unbound authoritative mutation absent:
true
```

When compute has a complete observed relation:

```text
complete binding
→ transition, evidence, preservation, advisory or observer role is explicit
```

When evidence is sufficient to establish absence:

```text
no qualifying binding
→ unbound
```

When evidence is incomplete:

```text
insufficient evidence
→ partial or unknown
```

When a node mutates authority-bearing state without complete authority binding:

```text
unbound authoritative mutation
→ authority-integrity finding
```

The central rule is:

```text
No authoritative compute without an observed transition binding.
```

The evidence rule is:

```text
Do not convert missing recording into a positive or negative claim.
```

The AI-native operation rule is:

```text
Machine complexity is operated by the machine.
Authority remains bound to evidence.
```

The efficiency rule is:

```text
Do not scale or budget compute before measuring where the existing compute is
bound, in explicit units, under explicit coverage.
```
