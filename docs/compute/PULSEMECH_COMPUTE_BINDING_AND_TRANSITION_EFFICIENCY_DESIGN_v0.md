# PULSEmech compute binding and transition efficiency design v0

## WORKMARK

```text
document_role:
design_and_implementation_state_record

workstream:
compute_binding_and_transition_efficiency

state_date:
2026-09-11

canonical_system_state_source:
PULSEMECH_TECHNICAL_OVERVIEW.md

merged_compute_state_recorded_through:
PR #2877

merged_compute_state_basis:
12b42736a9f8a1da16e3659a2d2099058207129b

merged_compute_state_tree:
b44c9f7cfa24c0dafbc8c38973fbbca37295f7d1

implementation_status:
current_run_automation_3G_historical_4A_4B_runtime_binding_5A_and_bounded_observed_reference_5B_complete

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
implemented_historical_post_run_platform_export_only

runtime_packet_producer_basis:
d7def834e8aa63911426550cf41b05f81c0b56b0

runtime_packet_preservation_basis:
55c6180dfbfd4055a558cf6b3e3883461a423f86

runtime_packet_preservation_acceptance:
supported_with_explicit_reconstruction_and_remote_evidence_limits

runtime_packet_coverage:
partial

live_current_run_runtime_observation_producer:
not_implemented_as_general_whole_runtime_producer

runtime_bound_report_and_relation_step5a:
implemented_and_accepted_under_2870

runtime_bound_report_and_relation_basis:
5afb4404719fb04d3ee32a007cdbb8b47c220118

historical_partial_source_aware_runtime_chain:
executed_successfully_in_post_merge_CI_34170196053_attempt_1

bounded_observed_execution_step:
5B

bounded_observed_execution_work_order:
2875

bounded_observed_execution_scope:
six_declared_direct_processes_and_their_bound_io

bounded_observed_execution_implementation_basis:
c32508f8afb58381225fec0b426b85b00e32fe11

bounded_observed_execution_implementation_tree:
74dd65d82124170b7d8f459925962bb8bc09fe2b

bounded_observed_execution_reference_run:
34402387728 / attempt 1 / job 102637163024 / artifact 10123984621

bounded_observed_execution_preservation_basis:
12b42736a9f8a1da16e3659a2d2099058207129b

bounded_observed_execution_preservation_tree:
b44c9f7cfa24c0dafbc8c38973fbbca37295f7d1

bounded_observed_execution_result:
checker 0 → ready / checker 1 → held / checker 2 → held

bounded_observed_execution_predicates:
I complete / E complete / R complete / C true / M unavailable

bounded_observed_execution_replay:
two separate processes reproduced the 322567-byte 12-member output byte-for-byte

bounded_observed_execution_negative_preservation_review:
10 scenarios reproduced at their intended rejection or preservation boundaries

bounded_observed_execution_candidate_state:
compute_transition_path_complete=true /
compute_transition_authority_binding_ok=true /
compute_transition_unbound_mutation_absent=true

bounded_observed_execution_generic_runtime_state:
authority_binding_complete=false / decision_closure_complete=false /
whole runtime packet partial

bounded_observed_execution_authority_boundary:
same_run_release_authority_eligible=false / active_gate_eligible=false /
authority_effect=none

tools_test_manifest:
154 active unique program paths

runtime_observed_connected_proof:
partial historical chain proven and bounded Step 5B six-process reference
complete at its declared scope; complete whole-runtime Step 5 proof not completed

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

The recorded implementation state includes accepted Step 5A at
`5afb4404719fb04d3ee32a007cdbb8b47c220118`, the bounded Step 5B implementation
at `c32508f8afb58381225fec0b426b85b00e32fe11`, and its exact preservation at
`12b42736a9f8a1da16e3659a2d2099058207129b`.

Historical Step 4B packet preservation remains bound to
`55c6180dfbfd4055a558cf6b3e3883461a423f86`, and its producer remains fixed at
`d7def834e8aa63911426550cf41b05f81c0b56b0`. The later Step 5A and Step 5B
records do not replace those historical identities.

This documentation synchronization has its own final-head checks and review.
None is predeclared here.

Five completed results must remain distinct:

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

Step 4B:
bounded offline historical runtime-packet producer
+ exact packet, construction record and execution report preserved
+ recorded local deterministic reconstruction
+ separate direct validation of the preserved packet in post-merge review
+ explicit partial coverage and review-access limits

Step 5A:
source-bound runtime report and planned-observed comparison implementation
+ separate source-aware report/relation validation and candidate materialization
+ successful partial historical connected-chain execution in post-merge CI
+ bounded acceptance under #2870
+ complete whole-runtime Step 5 proof remains open

Step 5B:
bounded checker/consumer observation implementation
+ actual owner-dispatched run 34402387728 / attempt 1
+ artifact 10123984621
+ exact preservation through PR #2877
+ source-bound capture validation
+ two separate byte-identical reconstruction processes
+ ten reproduced negative or preservation scenarios
+ bounded I/E/R/C completion with M unavailable
```

Step 4A records an actual historical acquisition execution. It is not a
manually dispatched Step 3F or Step 3G proof instance and is not itself a
runtime packet.

Step 4B uses that unchanged input to construct the separate bounded historical
packet. Step 5A connects the authentic partial packet to source-aware
report/relation processing without inventing missing observations.

Step 5B is a distinct actual execution. It observes three checker occurrences
and three matching downstream consumers within
`six_declared_direct_processes_and_their_bound_io`. It does not convert the
partial historical packet or its projection collector into complete
whole-runtime observation.

Sections 24–27 record completed automation, historical capture and packet
preservation, accepted Step 5A and completed bounded Step 5B. General
live/current-run whole-runtime observation, complete Step 5 closure, resource
measurement and policy promotion remain separate later work.

This documentation changes no workflow, schema, normative contract, producer,
validator, test registration, policy, gate, status, release-authority mechanism,
preserved evidence, Device Ledger source, DOI, citation, tag, release or
publication metadata.

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
bounded offline historical runtime-packet producer and permanent regression
four-file #6066 runtime-packet preservation and direct validation record
runtime-bound report and versioned planned-observed comparison profiles
separate source-aware report/relation validation and candidate publication
partial historical runtime connected-chain regression and bounded Step 5A acceptance
bounded-execution evidence schema and normative contract
sealed-source checker and consumer execution capture
distinct downstream result consumer
independent bounded-execution checker and reconstruction entrypoint
manual non-active bounded-reference workflow
actual owner-dispatched reference run 34402387728
five-file exact preservation and source-bound replay record
two separate byte-identical 12-member reconstruction processes
six-process planned-observed closure with I/E/R complete and C true
resource coverage unavailable
one new permanent regression and 154-program current tools-test manifest
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
Sections 24–26. Section 26 separately records the historical Step 4A
acquisition, bounded Step 4B packet production and preservation, accepted
Step 5A runtime processing, and the actual Step 5B bounded checker/consumer
reference.

The repository does not yet contain a merged and complete:

```text
general live/current-run whole-runtime observation producer
complete whole-runtime Step 5 observed proof
remaining wider fixed-source/runtime comparison
per-axis compute-resource measurement surface
compute budget
active compute-related release enforcement
```

The current-run automation implementation and permanent regression surface are
complete through Step 3G.

The Step 4A historical input capture is preserved and independently replayed.
The Step 4B historical packet is produced, preserved and directly validated
with its stated evidence limits. Step 5A processes that partial historical input
through the connected source-aware report/relation/candidate path.

Step 5B separately records one actual owner-dispatched execution with verified
source and inputs, predeclared finite extent, three distinct checker results,
three matching downstream consumers, exact preservation and independent replay.
Its complete bounded extent does not supply complete whole-runtime observation.

```text
current-run contract and machine construction:
implemented and regression-proven

current-run candidate workflows:
implemented; manual and non-active

manually dispatched public Step 3F/3G execution record:
not claimed by this state record

historical Step 4A acquisition and offline replay:
completed for exact #6066 attempt 1

bounded historical Step 4B production and preservation:
completed for the post_run_platform_export profile; partial coverage

Step 5A runtime-bound construction and partial historical chain:
implemented, reviewed and accepted

Step 5B bounded checker/consumer observation:
implemented, owner-dispatched, preserved and independently replayed

Step 5B finite scope:
six_declared_direct_processes_and_their_bound_io

Step 5B predicate state:
I complete / E complete / R complete / C true / M unavailable

whole runtime packet:
partial

complete whole-runtime Step 5 proof:
pending

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

A bounded historical post-run runtime-packet producer is implemented and its
partial packet is preserved. Step 5A constructs a genuine runtime-bound report
through the existing analyzer and validates the exact upstream sources. Its
analysis level can be `runtime_observed` while coverage remains partial. The
complete actually observed subject proof and live/current-run observation producer
are not implemented. Changing an analysis-level label or supplying the historical
packet alone does not establish a complete runtime-observed graph.

A lower analysis level must not claim a higher-confidence classification.

The current-run expectation is metadata-only and does not by itself raise the
analysis level. The Step 4A platform-response capture likewise remains an exact
producer input; its job and step fields are not a runtime-observed graph. The
separate Step 4B packet preserves those fields without inventing the missing
runtime input/output and consumption relations.

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

Step 5A adds the closed `pulsemech_runtime_report_binding_v0` section to this
existing report contract. It binds an identifiable artifact-observed baseline,
exact runtime inputs, correspondence, evidence origins and construction-source
identities. The existing validators check the upstream byte-bound reconstruction.
See the [Step 5A implementation and evidence record](#completed-step-5a--runtime-bound-report-and-relation).

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
implemented for bounded historical post_run_platform_export

historical #6066 runtime packet:
preserved and directly validated; partial coverage

live runtime capture:
not active
```

---

## 16. Planned-observed relation

Step 5A extends the existing relation with `pulsemech_runtime_comparison_v0` for
runtime-bound reports. Existing overall `runtime_observation_status` retains its
resource-inclusive meaning; extent and resource-independent relational coverage
are represented separately. Source-aware replay derives plan/report locators
from captured bytes. Artifact-only admission is not broadened to accept raw runtime
packets without a newly constructed bound report.

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
Its implementation and observed-reference acceptance are complete. The separate
Step 4A documentation closure was accepted through
[PR #2862](https://github.com/HKati/pulse-release-gates-0.1/pull/2862), merge
`bfa674582b17c7b1a0c238a1f0d2051ac0c847c9`. Work order #2856 remains technically
complete. Later documentation synchronization does not reopen that accepted scope.

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
Step 4B runtime-packet producer have distinct roles. The validator does not
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
→ separate bounded Step 4B reference runtime-packet production, completed below
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
subject run. It supplies exact preserved inputs to the separate Step 4B producer;
the capture itself neither implements that producer nor promotes any compute gate.

### Step 4 — runtime-observation producer

Step 4B completes the bounded historical `post_run_platform_export` producer and
its four-file preservation handoff, as recorded below. Step 5A adds connected
processing of that partial input, not the missing live/current-run observation
producer or the complete actually observed runtime proof.

The broader runtime work must populate only evidenced fields, while preserving
the historical-reference versus current-run pre-decision distinction:

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

### Completed Step 4B — historical runtime-packet production and preservation

[Work order #2864](https://github.com/HKati/pulse-release-gates-0.1/issues/2864)
has completed implementation and preservation handoffs for the bounded historical
`post_run_platform_export` profile. It does not complete the broader live or
current-run runtime-observation lane.

#### Implementation and preservation identities

| Role | Merged PR | Exact commit | Root tree |
| --- | --- | --- | --- |
| Offline producer, matching runtime validator and permanent regressions | [#2867](https://github.com/HKati/pulse-release-gates-0.1/pull/2867) | `d7def834e8aa63911426550cf41b05f81c0b56b0` | `7ef7a119556d4dc69280ccd451ed41b5272fdeaa` |
| Four-file historical packet preservation | [#2868](https://github.com/HKati/pulse-release-gates-0.1/pull/2868) | `55c6180dfbfd4055a558cf6b3e3883461a423f86` | `a1cfd8e333c138815eebc89fa20623b1a1dc5b06` |

The implementation commit remains the packet's producer revision. The later
preservation commit identifies where the four objects were stored; neither it
nor this documentation update replaces a construction or acquisition identity.

The [offline producer](../../tools/build_pulsemech_compute_runtime_observation_packet_from_capture_v0.py)
and its [permanent regression](../../tests/test_build_pulsemech_compute_runtime_observation_packet_from_capture_v0.py)
are separate from the accepted Step 4A capture tools. The existing
[runtime validator](../../tools/check_pulsemech_compute_runtime_observation_packet_v0.py)
and its [regression](../../tests/test_check_pulsemech_compute_runtime_observation_packet_v0.py)
handle historical timing and recorded policy order only for the matching
observed post-run producer/collector profile. The runtime schema and illustrative
example remain unchanged.

| Implementation object at the producer revision | Bytes | SHA-256 |
| --- | ---: | --- |
| Offline runtime-packet producer | 45122 | `b59cfc97d5b44bbd2393e5588b4b1180bd165b2b467ba1f9317b5e64ee91bbb1` |
| Separate runtime-packet validator | 49528 | `edc8f795043f656ffa8599dfae9555f38970790f1096cf080e9049f218d512d9` |

The producer admits its actually invoked canonical path and source bytes,
checks the declared committed source and construction-record digest, and pins
its matching validator. It uses the unchanged independent capture and
subject-input validation paths before constructing output. The packet is then
checked by the separate runtime validator, which does not import the producer.
Publication is outside the source repository, does not replace an existing
output, and retains source rechecks and ownership-bound failure cleanup.

The final implementation delta was eight files: the original six-file candidate
plus two existing workflow-regression count assertions corrected from `152` to
`153`. Each of those two corrections changed only the expected manifest count.
The [tools-test inventory](../../ci/tools-tests.list) has **153 unique active
program entries**, including the producer regression exactly once. This is not
153 individual pytest cases or evidence that every program ran in a given review.

#### Exact historical input-to-packet relation

```text
Step 4A: five exact capture members for #6066 / attempt 1
+ verified observed subject-input context
+ exact earlier release-grade preservation carrier
+ original historical commit:path sources
+ immutable, explicitly SHA-256-bound local construction record
→ unchanged offline producer at d7def834...
→ 8 historical jobs + 171 historical steps + 1 separate collector
→ separate runtime-packet validation
→ canonical packet preserved at 55c6180...
```

The subject remains run `29249887581`, attempt `1`, source
`46b639706e23f80fe296a8893be18e2b5ab21f7e`. Original acquisition remains run
`33986538130`, attempt `1`, source
`22d14088ae21f84d94c6a6951c0f70ab1bdf0895`. The observed context's producer is
`3cd57dc9e88e6f804dbb134c864f4207688bddc2`. These identities have different roles.

The context supplies the historical release-candidate and run-mode fields and
the ordered policy-set identity `required`, `release_required`; the producer does
not infer them from a job's success or the current branch. The complete input
paths, sizes and digests are preserved in the
[execution record](../../preservation/pulse_ci_6066/runtime_observation_packet_v0/verification_record_v0.json).
No new network acquisition or historical workflow rerun is part of this relation.

#### Preserved output and reproduction input

All four objects are in
[preservation/pulse_ci_6066/runtime_observation_packet_v0](../../preservation/pulse_ci_6066/runtime_observation_packet_v0/).
They are new derived/output records, not replacements for the Step 4A originals.

| Object | Bytes | Git blob | SHA-256 |
| --- | ---: | --- | --- |
| [Construction record](../../preservation/pulse_ci_6066/runtime_observation_packet_v0/construction_record_v0.json) | 1250 | `bc4944dec23eebe15df0e1634b5ed9cbfcacc5be` | `877347d5e22410888614ac55698d4ebe82378d496ae5ee31fec945195a1a55e6` |
| [Historical runtime packet](../../preservation/pulse_ci_6066/runtime_observation_packet_v0/pulsemech_compute_runtime_observation_packet_6066_observed_v0.json) | 484234 | `cef7f1cb0386c977eb0cddc2e63f57c2813d60c7` | `76418f3a7374cf12127031b15806af1e80605ad07031b3b10308c3a30b795a88` |
| [Verification record](../../preservation/pulse_ci_6066/runtime_observation_packet_v0/verification_record_v0.json) | 24105 | `24136a2a39b904585d36d10f003a1a3ce25b2936` | `aa225628594d5c5ef29764cde69e96d88da5942289b1603532710846b1ad3796` |
| [Local preservation README](../../preservation/pulse_ci_6066/runtime_observation_packet_v0/README.md) | 10602 | `82055e1f4c2fa44d90515b70ce5debc84407d529` | `de2f67b8e44db24df5493a743f568b1f423eefa8035c40339a482bec2ef82c92` |

The README gives the replay procedure using an exact implementation checkout,
the preserved construction record and a fresh external output location. Replay
must keep the construction bytes unchanged, run the separate validator and
compare the complete result with the preserved packet. Parsing and reserializing
that packet is not input-to-packet reconstruction.

#### Evidence classes and completed checks

The committed verification record and the owner-supplied read-only post-merge
reports are different evidence sources. The reports are titled “Consolidated
post-merge review — PR #2867 / Step 4B” and “Read-only post-merge review — PR #2868 /
Step 4B”. Their targets are the respective implementation and preservation
commits above. Review results below are attributed to those supplied reports;
this documentation update does not rerun them or make them remote CI results.

| Evidence source | Actual scope recorded | Limit |
| --- | --- | --- |
| Committed local preservation execution record; CPython 3.13.5, pytest 9.0.2, jsonschema 4.26.0, PyYAML 6.0.3 | Two isolated producer CLI executions from separate exact implementation checkouts produced identical 484234-byte packets; each passed a separate runtime-validator invocation. Producer, historical context and runtime-validator suites passed `74 + 24 + 90 = 188` cases. | Same local environment; not an external attestation, GitHub run or fresh full 153-program campaign. Regression fixture commits are distinct from the direct preservation constructions. |
| Supplied #2867 post-merge implementation review; CPython 3.14.4 | Exact eight-file merge, both prior P1 corrections mechanically addressed, and no actionable findings in the inspected scope; bounded implementation acceptance. | Historical source `46b639...` was absent there. The producer suite/direct replay did not run; the complete subject-context suite was not PASS. |
| Supplied #2868 post-merge preservation review; CPython 3.14.4, pytest 9.0.3, jsonschema 4.26.0, PyYAML 6.0.3 | All four committed identities exact; an actual byte-exact preserved packet passed the unchanged standalone validator, exit `0`, valid schema, no errors and all **34 semantic checks true**. Separately, the full runtime-validator regression passed **90 cases**. | Direct packet validation is not producer reconstruction. That cloud environment also lacked `46b639...`, so fresh producer replay and the 74/24 source-dependent suites were not run. |

The #2868 review compared the actual packet with the committed raw responses:
all 8 jobs, 171 steps, exact parent/run/time relationships and **44 skipped step
outcomes** matched. It also checked every recorded input descriptor available at
the preservation commit and all **14 embedded stdout/stderr stream** sizes and
hashes. Consistent stored logs are not independent authentication of all reported
historical executions. The fresh standalone execution separately corroborated
the preserved packet's current schema and semantic validity.

The same preservation review reported these temporary-copy negative probes:

| Mutation | Observed enforcement |
| --- | --- |
| Reformat the same packet data into compact JSON | Complete-byte comparison returned `1` and SHA-256 changed; this is an exact-object rejection, not an asserted semantic-validator failure. |
| Replace a step parent with a nonexistent execution | Runtime validator returned `1` with schema still valid; `execution_parent_references_resolve` and `workflow_job_step_shape_ok` failed. |
| Rebind one execution to another subject run | Runtime validator returned `1` with schema still valid; `subject_execution_run_binding_ok` and `subject_run_binding_consistent` failed. |
| Claim `complete` coverage while retaining unobserved reasons | Existing schema rejected the packet before semantic checks. |

These are review probes, not newly registered permanent tests. The producer-side
changed-construction-record probe was not run in that cloud environment because
its historical source prerequisite was incomplete; a setup failure is not counted
as a successful rejection.

Pre-merge GitHub evidence remains separate: implementation run `34067210741`,
Tools smoke job `101578031826`, was associated with PR head
`9bbda256a43d767681231ed4af8411dda9ac1962`; preservation run `34114319317`, job
`101717710093`, was associated with `f0a19b045469fee8525611379edbcf7574de7c16`.
The supplied final-head records report successful Tools smoke and targeted
pytest steps. They are not execution against either later merge commit, and no
remote test count or interpreter version is inferred from them. Both supplied
cloud reviews lacked authenticated post-merge CI access. Skipped jobs remain
skipped, and implementation-fixture CI is not substituted for direct inspection
of the newly preserved packet.

#### Time, observation and authority limits

The construction record's local collector key begins with
`LOCAL_PRESERVATION=step4b-6066-20260907T002403Z`. Its three declared times are
`2026-09-07T00:24:03Z`: input preparation and logical creation at record
finalization, not the measured process interval or file-publication time of a
later CLI invocation. The committed report separately retains actual CLI
intervals. Equal one-second declarations prove neither zero runtime nor zero
resource use. No independently authenticated collector identity or clock is
claimed; replay does not refresh these declarations.

`record_status: observed` concerns the verified historical platform-export data.
Overall coverage remains `partial`. Unknown executed-command bytes, argument
identity, process exit codes, historical runtime input/output consumption,
individual external calls, model inferences and resource use remain unavailable.
Empty collections do not establish absence of historical activity. The collector
is excluded from subject totals. Job/step timestamps and derived elapsed times
are not CPU, GPU, memory, network or token measurements.

```text
Step 4A captured source remains:
historical-reference producer input; not a runtime packet

Step 4B derived packet:
implemented and preserved historical post-run profile; partial coverage

complete runtime-observed connected proof:
not implemented

same_run_release_authority_eligible: false
active_gate_eligible: false
authority_effect: none
```

The last three labels describe the existing producer/report boundary; this
record does not add runtime-schema fields. Neither the source capture nor its
derived packet authorizes the completed subject retroactively. Current-run
operational use still requires exact source capture before the authority decision.

#### Bounded acceptance and documentation endpoint

Implementation acceptance is supported within the #2867 review's source and
execution limits. Preservation acceptance is supported for exact object
integrity, direct packet validity, available historical mapping, internal report
consistency and local reproduction documentation. The preserved local record
supplies the earlier exact reconstruction result; the #2868 cloud review did not
independently repeat that reconstruction. Its missing Git object is an
access limitation, not a demonstrated implementation or preservation defect.

The Step 4B documentation handoff was subsequently completed through
[PR #2869](https://github.com/HKati/pulse-release-gates-0.1/pull/2869), merge
`5a9660878a04dde2505586ad4c9e09ce479203bb`, and the
[final completion record](https://github.com/HKati/pulse-release-gates-0.1/issues/2864#issuecomment-5572375868).
Work order #2864 is complete. Later source-aware Step 5A execution is recorded
separately below; it does not retroactively rerun the earlier cloud review.
Live/current-run observation, full runtime proof, resource measurement and policy
promotion are not extra acceptance conditions added to the closed historical work.

### Completed Step 5A — runtime-bound report and relation

The source mapping and bounded implementation under
[work order #2870](https://github.com/HKati/pulse-release-gates-0.1/issues/2870)
were accepted in the
[completion record](https://github.com/HKati/pulse-release-gates-0.1/issues/2870#issuecomment-5577131873).
The issue is closed as completed for that scope. The implementation decision is
[comment 5573580286](https://github.com/HKati/pulse-release-gates-0.1/issues/2870#issuecomment-5573580286).
This acceptance does not complete the full Step 5 observed proof.

#### Accepted implementation identity

| Role | Exact identity |
| --- | --- |
| Implementation PR | [#2872](https://github.com/HKati/pulse-release-gates-0.1/pull/2872) |
| Actual squash-merge commit | `5afb4404719fb04d3ee32a007cdbb8b47c220118` |
| Root tree | `de0548855c4679dc86601963f0775639388e7bdc` |
| Parent / implementation baseline | `5a9660878a04dde2505586ad4c9e09ce479203bb` |
| Corrected pre-merge head | `a67a3f24b058f2de06410ce64362dbfb2ead5755` |

The implementation changed 18 existing files: two schemas, six implementation,
validator or materializer programs, and ten permanent regression programs.
The three review corrections changed six files within that set, not six extra
files. No file, workflow, dependency, policy set or test program was added.

#### Implemented construction and validation

```text
exact subject-input packet + carrier + required historical Git sources
→ existing immutable bridge and single analyzer core
→ identifiable artifact-observed baseline

+ separately captured and validated runtime-packet bytes
→ newly constructed runtime-bound report
→ source-aware report validation
→ existing planned-observed relation engine
→ source-aware relation validation
→ separate non-active candidate materialization
```

The report's closed `pulsemech_runtime_report_binding_v0` section binds baseline,
subject-input and carrier identities, exact packet bytes and predecessor links,
original ordered policy context, execution/state correspondence, evidence origin,
collector identity and actual construction-source identities. The relation uses
`pulsemech_runtime_comparison_v0`. Both are extensions of existing contracts,
not parallel analyzers or replacement authority mechanisms.

Artifact-derived edges retain their origin. Names, source hashes or equal state
content alone do not collapse execution occurrences. Conflicting repeated
records are rejected; identical repeated records retain their source references.
Applicable production and consumption links require their own evidence. An
observer read, producer self-read, skipped execution or unrelated consumer does
not establish required subject consumption.

The report and relation validators receive the required upstream bytes and
perform source-aware reconstruction and replay. The historical artifact baseline
still requires genuine original Git objects. Candidate materialization forwards
those inputs, publishes separately without replacing an existing output, and
keeps unrelated replacement files safe during failed-recheck cleanup.
Artifact-only invocations retain their existing input contract and semantics.

#### Coverage and corrected qualification

Five distinct predicates remain visible: supplied packet-set integrity,
observation extent, runtime relational coverage, planned-observed comparison
completeness and per-axis resource coverage. Existing overall
`runtime_observation_status` semantics are unchanged. A contiguous supplied
prefix does not prove terminal observation closure. Complete synthetic extent
is restricted to the `example` profile, not historical or live observed evidence.

All three original review findings were corrected:

| Finding | Merged behavior |
| --- | --- |
| Non-qualifying collector/observer records | Skipped, cancelled, unknown or insufficiently recorded execution cannot remain decisively complete merely because capture status is complete. Valid partial evidence remains representable and independently validatable. |
| Self-declared runtime repository-file identity | Unsupported observed source identity remains partial through report and relation normalization. Raw packet declarations remain intact; syntactically valid revision/path/digest fields do not authenticate the source or qualify unsupported runtime edges. |
| Replay provenance locators | Construction and source-aware replay derive plan/report `sha256:<digest>` locators from captured bytes. Individual and jointly consistent forged locators are rejected before candidate publication. |

The source-identity correction is conservative qualification, not a new arbitrary
runtime Git/blob authenticator. It is separate from the existing historical
source verification used to reconstruct the artifact baseline.

#### Evidence events and bounded acceptance

The owner-supplied report **“Post-merge review — PR #2872 / Step 5A”** inspected
exactly the merge above, confirmed the 18-file scope and unchanged protected
inputs, and demonstrated no new implementation defect. Its focused correction
selection passed 15 cases. Its recommendation was conditional because its own
checkout lacked historical commit `46b639706e23f80fe296a8893be18e2b5ab21f7e`
and remote GitHub access; it did not claim a complete all-pass campaign.

The later completion record supplements that review with separately retrieved
GitHub CI evidence and the manifest-count correction. It does not rewrite the
review's original results or treat a green CI status as the source review.

| Evidence event | Actual result | Boundary |
| --- | --- | --- |
| Cloud review; CPython 3.14.4, pytest 9.0.3 | Ten affected programs: 407 passed, 11 failed, 0 skipped; direct-script totals agreed. | Eight bridge tests, two core equivalence tests and the mandatory historical runtime chain failed at the missing historical-source boundary. Not an all-pass result. |
| Same cloud review; unchanged runtime/registration selection | 140 passed, 74 setup errors. | The historical producer fixture could not initialize without the original Git object. These errors are not successful negative tests. |
| Post-merge PULSE CI `34170196053`, run number `6794`, attempt `1`, event `push` | `completed / success` on `5afb4404719fb04d3ee32a007cdbb8b47c220118`; `pulse` and `Tools smoke tests` succeeded. | Separate GitHub execution, not tests rerun by the cloud reviewer or this documentation update. |
| Same run, Tools smoke job `101888978377` | Registered 153-program path completed; ten affected direct-script programs reported 418 passed in total. | The log identifies the actual checkout and successful terminal smoke message. Program count is not pytest case count. |
| Same job, unchanged historical runtime-packet producer suite | 74 passed. | Separate from the 418 affected cases. |
| Same job, targeted pytest step | 94 passed. | Separate selection, not a combined rerun of the ten affected programs. |

The affected direct-script counts were:

| Program | Passed |
| --- | ---: |
| Subject-input report bridge | 22 |
| Binding report builder | 35 |
| Planned-observed relation builder | 41 |
| Binding report validator | 31 |
| Planned-observed relation validator | 66 |
| Analyzer core | 136 |
| Binding report schema | 25 |
| Fixed-source candidate chain | 14 |
| Planned-observed candidate | 12 |
| Relation schema | 36 |
| **Affected-case total** | **418** |

The 14-case fixed-source program includes
`test_runtime_historical_full_source_bridge_report_relation_candidate`.
It requires the historical source-aware chain to reach relation validation and
separate candidate materialization while retaining partial runtime coverage,
incomplete comparison and a non-all-true candidate. The CI execution passes
that test without replacing source pins or weakening the historical prerequisite.

Sources: [post-merge PULSE CI run](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/34170196053),
[Tools smoke job](https://github.com/HKati/pulse-release-gates-0.1/actions/runs/34170196053/job/101888978377),
[permanent connected-chain regression](../../tests/test_pulsemech_compute_fixed_source_candidate_chain_v0.py),
and the [owner's acceptance and evidence reconciliation](https://github.com/HKati/pulse-release-gates-0.1/issues/2870#issuecomment-5577131873).
The supplied cloud report is an attributed review source, not a newly committed
repository artifact or an independently fetched report at those links.

#### Registration-count correction

The unchanged `ci/tools-tests.list`, Git blob
`cc9f991c12a034a0736e5505f485cabe283cd5a9`, contains 162 physical lines:
five blank lines, four comment lines and **153 unique program paths**.
The manifest, workflow and registration checker explicitly filter comments and
blank lines. The review's 157 non-empty textual entries included four comments.
The completion record corrects that interpretation, not repository code.
The GitHub log separately reports `tools-tests manifest (153 entries):`.

#### Historical, synthetic and bounded observed profiles

The authentic historical #6066 packet remains exactly **484234 bytes**, SHA-256
`76418f3a7374cf12127031b15806af1e80605ad07031b3b10308c3a30b795a88`.

Successful connected processing does not supply missing commands, consumption
records, resource measurements or terminal observation extent. The historical
capture, runtime-packet schema, validator, producer, construction record and
preserved carrier remain unchanged.

The cloud review's separate-process synthetic probe recorded:

```text
overall runtime_observation_status: partial
synthetic extent_status: complete
synthetic relational_coverage_status: complete
comparison_complete: true
candidate values: false / true / true
candidate_all_true: false
```

The candidate order is:

```text
compute_transition_path_complete
compute_transition_authority_binding_ok
compute_transition_unbound_mutation_absent
```

A complete comparison can expose a mismatch. This synthetic result neither
changes the historical fixed-source candidate `false / false / true` nor
establishes an actually observed complete runtime proof. Unavailable resources
remain unavailable, not fabricated zeroes.

Step 5B is a third and separately identified evidence profile. It is neither a
synthetic example nor a relabelling of historical #6066. It uses its own
implementation revision, workflow-run identity, artifact, source-bound capture,
preservation and reconstruction evidence.

<a id="completed-step-5b--bounded-observed-checker-and-consumer-reference"></a>

### Completed Step 5B — bounded observed checker and consumer reference

The source mapping and implementation decision were recorded under
[work order #2875](https://github.com/HKati/pulse-release-gates-0.1/issues/2875)
before implementation and acquisition.

The bounded implementation, owner-dispatched reference, exact preservation and
independent replay are complete at their declared scope. The
[acceptance record](https://github.com/HKati/pulse-release-gates-0.1/issues/2875#issuecomment-5609641514)
authorizes canonical documentation synchronization.

It does not predeclare the separate final #2875 work-order closure event.

#### Implementation identity and scope

| Role | Exact identity |
| --- | --- |
| Implementation PR | [#2876](https://github.com/HKati/pulse-release-gates-0.1/pull/2876) |
| Implementation merge | `c32508f8afb58381225fec0b426b85b00e32fe11` |
| Implementation tree | `74dd65d82124170b7d8f459925962bb8bc09fe2b` |
| Work order | [#2875](https://github.com/HKati/pulse-release-gates-0.1/issues/2875) |
| Declared finite scope | `six_declared_direct_processes_and_their_bound_io` |

The implementation changed:

```text
31 existing paths modified
8 new paths added
0 paths deleted
39 paths total
```

One new permanent test program was registered:

```text
153 → 154 unique tools-test program paths
```

The historical Step 5A 153-program execution record remains a record of its own
earlier revision. It is not retroactively rewritten.

The Step 5B implementation reuses:

```text
existing subject-input producer core
existing immutable subject-input bridge
existing single analyzer core
existing report and relation contracts
existing source-aware validators
existing planned-observed relation engine
existing separate candidate materializer
```

It does not introduce a second analyzer or a parallel release-authority
mechanism.

The main Step 5B implementation surface is:

```text
schemas/pulsemech_compute_bounded_execution_evidence_v0.schema.json
docs/compute/PULSEMECH_COMPUTE_BOUNDED_EXECUTION_CONTRACT_v0.md
tools/build_pulsemech_compute_bounded_execution_inputs_v0.py
tools/capture_pulsemech_compute_bounded_execution_v0.py
tools/consume_pulsemech_compute_bounded_result_v0.py
tools/check_pulsemech_compute_bounded_execution_v0.py
.github/workflows/pulsemech_compute_bounded_execution_reference.yml
tests/test_pulsemech_compute_bounded_execution_v0.py
```

The unchanged strict checker remains:

```text
PULSE_safe_pack_v0/tools/check_gates.py
```

#### Prelaunch and observed-process boundary

Requirement-list derivation is an independently validated prelaunch
prerequisite:

```text
exact policy bytes
+ exact registry bytes
+ selected core_required set
+ unchanged policy_to_require_args.py
→ ordered required-gate arguments
```

It is not one of the six observed subject processes.

The integration plan, case identities, expected occurrence slots, input roles
and terminal roles are created before execution. They are not reconstructed
from observed results.

The actual observed relation is:

```text
exact committed checker source
+ exact committed consumer source
+ exact controlled candidate-status inputs
+ exact ordered required-gate arguments
→ three sealed checker process occurrences
→ three distinct occurrence-bound consumer process occurrences
→ exact ready or held terminal reference states
→ bounded capture
→ source-bound independent validation
→ existing report/relation path
→ separate non-active candidate materialization
```

Verified source and input bytes reach child processes through sealed Linux file
descriptors. There is no mutable-path reopening, shell-command string or
arbitrary-command mode.

The trusted acquisition boundary includes the reviewed supervisor,
interpreter/runtime, host kernel and GitHub control-plane metadata. Sealed input
descriptors and later replay do not independently prove correctness against a
compromised privileged host or recorder.

#### Actual owner-dispatched reference

| Field | Value |
| --- | --- |
| Workflow | `PULSEmech bounded execution reference` |
| Event / branch | `workflow_dispatch` / `main` |
| Run ID | `34402387728` |
| Run number / attempt | `1 / 1` |
| Job | `102637163024` |
| Artifact | `10123984621` |
| Source commit | `c32508f8afb58381225fec0b426b85b00e32fe11` |
| Source tree | `74dd65d82124170b7d8f459925962bb8bc09fe2b` |

The acquisition used CPython 3.11.16.

This is an actual controlled reference execution. The controlled candidate
status inputs are not production AI-evaluation evidence, and the resulting
reference states are not production deployment admission.

#### Actual checker and consumer outcomes

| Case | Actual checker exit | Consumer terminal state | Expected relation matched |
| --- | ---: | --- | --- |
| `allow` | `0` | `ready` | true |
| `block_false` | `1` | `held` | true |
| `missing_required` | `2` | `held` | true |

Exactly six checker/consumer occurrences remain distinct.

The consumer reads the matching occurrence's actual streams and recorder-owned
process-result envelope. A successful consumer execution does not replace the
checker's result.

Therefore:

```text
checker exit 0
→ ready

checker exit 1
→ held
≠ ALLOW

checker exit 2
→ held
≠ ALLOW
```

A correctly observed BLOCK is a positive observation result. Launch failure,
timeout, interruption or unavailable status cannot be relabelled as a completed
checker decision.

#### Exact preservation

The acquired evidence is preserved through:

| Role | Exact identity |
| --- | --- |
| Preservation PR | [#2877](https://github.com/HKati/pulse-release-gates-0.1/pull/2877) |
| Preservation merge | `12b42736a9f8a1da16e3659a2d2099058207129b` |
| Preservation tree | `b44c9f7cfa24c0dafbc8c38973fbbca37295f7d1` |
| Preservation directory | [`preservation/compute_bounded_execution_reference_v0/run_34402387728_attempt_1/`](../../preservation/compute_bounded_execution_reference_v0/run_34402387728_attempt_1/) |

The preservation directory contains exactly:

```text
pulsemech-bounded-reference-34402387728-1.zip
verification_record_v0.json
verification_evidence_v0.zip
preservation_manifest_v0.json
README.md
```

The primary byte objects are:

| Object | Bytes | SHA-256 |
| --- | ---: | --- |
| Downloaded GitHub artifact | `3270026` | `2601a68b864779b8cf99a6a2bc0fdb48c994b95067f098354d35e86e7ff178f6` |
| Inner reference capsule | `3269864` | `f726c9c240512e6f13d34bebbcfa549696adff560ee718abae84f4f121d2bc7a` |
| Prepared input carrier | `1456425` | `8b3300fc928259155e7966d1618b9629ff73a99defcfac502d643c6b622e6aa5` |
| Captured evidence carrier | `1489242` | `8097b20f4ae41686d81f113f1a06cb5eb8289b4e6ccc19a4a1e38fc09c82ab8c` |
| Acquired reconstruction ZIP | `322567` | `2d54aba44975111e38abcf010819dce160006742243a7f46930cd86f42747cf1` |

The prepared carrier contains 39 members. The captured evidence carrier
contains 55 members. The reconstruction ZIP contains 12 members.

The capture's prepared inputs exactly equal the separately preserved
preparation.

#### Independent source-bound validation and replay

The independent local review used CPython 3.13.5, jsonschema 4.26.0 and
PyYAML 6.0.3.

All 28 source-inventory files matched:

```text
the authenticated source commit
the clean installed source tree
the prepared carrier
the captured carrier
```

The preparation recipe was rerun from exact source objects and independently
established GitHub context. It reproduced the complete 1456425-byte preparation
carrier.

Fresh review executed:

```text
independent capture validator process 1
→ exit 0

independent capture validator process 2
→ exit 0

reconstruction process 1
→ exit 0

reconstruction process 2
→ exit 0
```

Both completed reconstruction processes reproduced the exact acquired
322567-byte, 12-member output ZIP byte-for-byte.

The reconstructed report diagnostic contains:

```text
10 / 10 true checks
```

The reconstructed relation diagnostic contains:

```text
34 / 34 true checks
```

These are diagnostic checks, not pytest case counts.

One earlier local reconstruction was interrupted by the execution tool's
wall-clock limit. It is explicitly retained as interrupted and is not counted
as PASS.

The evidence archive includes a source-object snapshot containing the actual
source commit and its complete tree/blob closure:

```text
1569 Git objects
1396 tracked files
```

A fresh repository import matched all object bodies and the complete tree. The
snapshot is not a full-history clone and is not sufficient for an unrelated
historical #6066 reconstruction campaign.

GitHub reported the source commit's PGP signature valid. The local review did
not independently perform PGP verification.

#### Bounded predicate and relation result

Within:

```text
six_declared_direct_processes_and_their_bound_io
```

the accepted state is:

```text
I — bounded packet integrity: complete
E — bounded observation extent: complete
R — bounded relational coverage: complete
C — comparison_complete: true
M — resource coverage: unavailable
```

The planned-observed relation contains:

```text
expectations:
6

observations:
6

decisive relations:
6

unresolved relations:
0
```

Whole-runtime-packet coverage remains:

```text
partial
```

The projection collector remains an explicitly partial collector. It is not a
seventh fully observed subject process.

No resource-measurement record has been introduced.

#### Negative and preservation review

All ten preserved scenarios met their intended rejection or preservation
assertion:

| Scenario | Observed rejection or preservation result |
| --- | --- |
| `cross_run_context` | `acquisition_context_mismatch` |
| `wrong_prelaunch_digest` | `prelaunch_digest_mismatch` |
| `altered_committed_source_bytes` | `source_bytes_mismatch` |
| `missing_execution` | `evidence_schema_rejected` |
| `wrong_occurrence_order` | `execution_extent_mismatch` |
| `cross_case_consumer_input` | `execution_input_binding_mismatch` |
| `forged_execution_source_digest` | `execution_source_mismatch` |
| `block_promoted_to_ready` | `terminal_consumption_or_state_mismatch` |
| `connected_reconstruction_rejects_wrong_consumer` | `bounded_input_rejected: execution_input_binding_mismatch` |
| `existing_output_preserved` | `bounded_input_rejected: output_already_exists` |

The wrong-consumer reconstruction produced no output.

A complete valid reconstruction directed at an unrelated pre-existing file
rejected publication and left the existing file byte-identical.

Manifest and ZIP repairs in mutation probes prevented accidental CRC corruption
from replacing the intended semantic rejection boundary.

The preservation review found no actionable preservation, replay or
bounded-claim defect.

#### Candidate and generic runtime-state separation

The three non-active compute candidate values are true for this bounded
reference only:

```text
compute_transition_path_complete: true
compute_transition_authority_binding_ok: true
compute_transition_unbound_mutation_absent: true
```

They do not replace the differently scoped generic runtime-report state:

```text
authority_binding_complete: false
decision_closure_complete: false
```

They also do not replace the historical fixed-source #6066 candidate:

```text
compute_transition_path_complete: false
compute_transition_authority_binding_ok: false
compute_transition_unbound_mutation_absent: true
```

These are different subjects and different evidence scopes.

#### Evidence and authority limits

Repository workflow and check records exist against preservation SHA
`12b42736a9f8a1da16e3659a2d2099058207129b`.

A reviewer environment's inability to retrieve remote workflow details is a
network-access limitation. It is not absence of the repository-side workflow
records. Remote workflow evidence remains distinct from the local source-bound
replay.

The exact preparation timestamp reused during deterministic reconstruction is
not an independent pre-acquisition timestamp attestation.

The preserved boundary remains:

```text
authority_effect: none
same_run_release_authority_eligible: false
active_gate_eligible: false
```

Step 5B does not:

```text
activate a compute gate
modify production release policy
authorize deployment
create a production release decision
define a compute budget
supply resource measurement
complete whole-runtime observation
complete the wider Step 5 comparison
promote Step 7 policy
```

### Remaining Step 5 — whole-runtime observed connected proof

Step 5A supplies the reusable runtime-bound construction, source-aware
validation and comparison mechanism.

Step 5B proves one actual finite checker/consumer observation boundary:

```text
three checker occurrences
+ three matching consumer occurrences
+ their exact bound inputs and outputs
```

The remaining Step 5 target is larger:

```text
current artifact-observed report
+ complete broader runtime packet chain
+ supported whole-runtime observation extent
+ remaining source and consumption evidence
→ whole-runtime observed relation
→ candidate materialization
→ wider fixed-source versus runtime-observed comparison
```

The complete Step 5 target must not be declared from the Step 5B bounded
reference alone.

A public manually dispatched Step 3F/3G proof instance remains separately
unclaimed. That does not reopen the completed Step 3G implementation.

Whole-runtime live/current-run observation, remaining comparison obligations,
Step 6 measurement, budgeting and Step 7 policy promotion remain separate.

```text
authority_effect: none
same_run_release_authority_eligible: false
active_gate_eligible: false
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

### Historical Step 4B runtime-packet handoffs

```text
PR #2867 / d7def834...
→ bounded offline producer and matching independent validator
→ permanent regression and executed-source correction

PR #2868 / 55c6180...
→ exact packet, construction record, local execution record and README
→ independent direct validation of the preserved packet
→ bounded preservation acceptance with explicit replay-access limits
```

Section 26 separates recorded local reconstruction from fresh cloud packet
validation. PR #2869 completed the canonical synchronization and #2864 is closed.

### Accepted Step 5A runtime-bound implementation

```text
#2870 / implementation-decision comment 5573580286
→ source mapping, coverage distinctions and complete implementation scope

PR #2872 / 5afb4404719fb04d3ee32a007cdbb8b47c220118
→ 18 existing-file runtime-report/relation implementation
→ three corrected review findings within that file set

post-merge PULSE CI 34170196053 / attempt 1
→ 418 affected-suite cases passed, including the historical connected chain

#2870 / acceptance comment 5577131873
→ source review plus separate CI evidence; 153-program count reconciled
→ bounded Step 5A accepted and closed; full Step 5 remains separate
```

### Completed Step 5B bounded observed reference

```text
#2875 / implementation-decision comment 5590191931
→ source-to-consumer mapping
→ finite observation extent
→ source, input, closure and consumption obligations
→ coordinated implementation scope

PR #2876 / c32508f8afb58381225fec0b426b85b00e32fe11
→ bounded evidence schema and normative contract
→ sealed-source checker/consumer capture
→ independent checker and reconstruction entrypoint
→ existing-core report/relation integration
→ manual non-active reference workflow
→ one new permanent regression
→ 154 unique registered tools-test programs

owner-dispatched run 34402387728 / attempt 1
→ job 102637163024
→ artifact 10123984621
→ source c32508f8afb58381225fec0b426b85b00e32fe11

PR #2877 / 12b42736a9f8a1da16e3659a2d2099058207129b
→ exact acquisition preservation
→ source-bound validation
→ two separate byte-identical 12-member reconstruction processes
→ ten negative or preservation probes
→ bounded preservation acceptance

#2875 / acceptance comment 5609641514
→ canonical synchronization authorized
→ final bounded work-order closure remains a separate issue event
```

This sequence establishes an observed-complete claim only within
`six_declared_direct_processes_and_their_bound_io`.

It does not establish complete whole-runtime observation, resource measurement,
compute budgeting or policy promotion. This canonical documentation handoff has
its own checks and review.

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
proof remains a historical producer-input proof, not original runtime telemetry
or a resource-efficiency conclusion.

Step 4B adds the bounded historical packet and its preserved reconstruction
evidence. Step 5A adds genuine source-aware runtime processing of that partial
input.

Step 5B adds one actual owner-dispatched six-process checker/consumer
observation, exact preservation and independent source-bound replay. It
establishes complete I/E/R/C state only within its declared finite boundary;
M remains unavailable.

Step 5B is not whole-runtime observation, a resource-efficiency measurement,
a compute budget, active compute enforcement or a production release decision.

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
implemented for bounded historical post_run_platform_export

historical runtime-packet preservation:
complete within declared object, mapping and direct-validation limits

general live/current-run whole-runtime observation producer:
not implemented; Step 5B supplies only the bounded six-process reference observer

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

Step 5A runtime-bound report and relation:
implemented and accepted under #2870

partial historical source-aware runtime chain:
passed in post-merge GitHub CI

Step 5B bounded observer implementation:
PR #2876 / c32508f8afb58381225fec0b426b85b00e32fe11

Step 5B owner-dispatched reference:
run 34402387728 / attempt 1 / job 102637163024 / artifact 10123984621

Step 5B preservation:
PR #2877 / 12b42736a9f8a1da16e3659a2d2099058207129b

Step 5B observed scope:
six_declared_direct_processes_and_their_bound_io

Step 5B checker and consumer outcomes:
0 → ready / 1 → held / 2 → held

Step 5B relation:
6 expectations / 6 observations / 6 decisive relations / 0 unresolved

Step 5B predicate state:
I complete / E complete / R complete / C true / M unavailable

Step 5B reconstruction:
2 separate processes / 322567-byte 12-member output / byte-identical

Step 5B negative and preservation review:
10 scenarios reproduced at intended semantic boundaries

Step 5B candidate state:
compute_transition_path_complete=true /
compute_transition_authority_binding_ok=true /
compute_transition_unbound_mutation_absent=true

Step 5B generic runtime state:
authority_binding_complete=false / decision_closure_complete=false /
whole runtime packet partial

current tools-test manifest:
154 active unique program paths

runtime-observed connected proof:
bounded Step 5B six-process proof complete at its declared scope;
complete whole-runtime Step 5 proof not completed

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

Step 4B adds a separate completed historical relation:

```text
exact preserved capture and verified context/carrier
+ exact historical Git sources
+ fixed construction record
→ offline producer at d7def834...
→ partial runtime packet preserved at 55c6180...
→ separate direct packet validation
```

The committed local execution record supplies repeated exact reconstruction;
the separate cloud review directly validated the preserved packet but could not
repeat producer replay without the historical subject Git object. This distinction
does not reopen the accepted capture or turn a reported run into fresh execution.

Step 5A adds the accepted runtime-bound relation:

```text
verified subject/carrier/historical sources
→ identifiable artifact-observed baseline
+ exact separately validated runtime packets
→ new runtime-bound report
→ source-aware report and relation verification
→ separate candidate materialization
```

The authentic partial #6066 input traverses that source-aware chain in the
merge-bound CI execution.

Step 5B adds a separate actual bounded relation:

```text
exact policy and registry
+ three exact candidate-status inputs
+ exact committed checker and consumer sources
+ predeclared six-process expectation set
→ checker exit 0 / 1 / 2
→ consumer ready / held / held
→ exact bounded capture
→ source-bound validation
→ runtime-bound report and planned-observed relation
→ two byte-identical reconstruction processes
→ separate non-active candidate materialization
```

Within `six_declared_direct_processes_and_their_bound_io`, the Step 5B result is:

```text
packet integrity:
complete

observation extent:
complete

relational coverage:
complete

comparison_complete:
true

resource coverage:
unavailable
```

The Step 5B candidate result is:

```text
transition path complete:
true

transition authority binding complete:
true

unbound authoritative mutation absent:
true
```

That candidate belongs only to the bounded Step 5B reference.

The synthetic complete-comparison case remains a separate example. The
historical #6066 packet remains partial, and its fixed-source candidate remains
unchanged.

Step 4A, Step 4B, Step 5A and Step 5B do not replace future operational
current-run pre-decision source capture. Whole-runtime observation, the remaining
wider comparison, complete Step 5 closure, resource measurement and policy
promotion remain later work.

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
