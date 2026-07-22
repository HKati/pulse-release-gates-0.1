# PULSEmech compute binding and transition efficiency design v0

## WORKMARK

```text
document_role:
design_and_implementation_state_record

implementation_status:
fixed_source_artifact_observed_v0_complete

completed_connected_proof:
PULSE CI #6066

completed_connected_proof_merge:
b6149dbd464f7f01760ab5fa80487f7e94e475e7

runtime_observation_contract:
implemented

runtime_observation_producer:
not_implemented

runtime_observed_chain:
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

This document defines the PULSEmech compute-binding workstream and records the
implementation state reached through the fixed-source PULSE CI #6066
artifact-observed proof.

The original design sequence is complete through:

```text
compute-binding report contract
→ fixed-source offline builder
→ runtime-observation contract
→ planned-observed relation contract and builder
→ non-active candidate policy surface
→ connected fixed-source candidate-boundary proof
```

This document does not itself modify workflow behavior, policy behavior, gate
registry behavior, verifier or materializer semantics, status authority,
release authority, SLSA/VSA behavior, DOI, citation, Zenodo, tags, releases, or
release metadata.

Any current-run integration, runtime-observation production, resource
measurement, compute budget, or active promotion remains separate work.

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

PULSEmech also contains a deterministic, read-only integration planner that can
resolve declared component dependency closure and emit a machine-readable
target-repository plan.

The compute-binding workstream now contains:

```text
strict compute-binding report contract
fixed-source artifact-observed report builder
runtime-observation packet contract
strict planned-observed relation contract
deterministic planned-observed relation builder
non-active candidate gate identities and policy set
relation-to-candidate-status materializer
policy-derived generic candidate check
connected fixed-source #6066 proof
```

The repository does not yet contain:

```text
a portable current-run subject-input producer
a reusable current-run compute-binding lane
a runtime-observation packet producer
a complete runtime-observed reference chain
complete per-node compute-resource measurement
a compute budget
active compute-related release enforcement
```

The fixed-source implementation proves the mechanism and exposes the exact
recording boundary of the preserved subject. It does not convert incomplete
artifact-level evidence into runtime-level evidence.

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
→ declared transition, evidence, preservation, advisory, or observer role
→ permitted mutation authority
→ mechanical consequence
```

The intended result is a deterministic record that distinguishes compute that
is mechanically bound to the transition from compute whose relation is
partial, absent, unknown, duplicated, advisory only, or outside the subject
transition.

---

## 3. Core proposition

A compute execution is not part of the release-authority mechanism merely
because it ran inside the same workflow.

```text
workflow presence
≠ transition binding

step success
≠ transition binding

artifact production
≠ transition binding

report publication
≠ transition binding
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

A declaration alone is not sufficient.

A report that states that a node is required is not proof that the node
contributed to the transition.

A filename or display label is not an exact source identity.

An artifact existing in the same package is not proof that its value was
consumed downstream.

---

## 4. Authority and non-activation rule

The compute-binding report, analyzer, relation record, and candidate
materializer observe or reconstruct the existing authority path.

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
runtime-observation packet
planned-observed relation
candidate materializer report
candidate-only gate check
preservation record
reader or audit surface
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
PULSE CI #6066 ALLOW decision and does not create a current release BLOCK.

---

## 5. Analysis identity and observer boundary

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
release candidate
run mode
active policy sets
policy identity and digest
materialized gate-set digest, when available
final status digest
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
workflow, it must remain separately classified as observer compute.

This prevents recursive self-accounting.

---

## 6. Graph model

The compute-binding report represents a directed graph of compute nodes, state
nodes, and exact observed relations.

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

The analyzer must not manufacture source, run, timing, input, output, or
consumption evidence.

---

## 7. Binding mechanics

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

An absent source digest must remain absent or unknown.

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

A path alone is not sufficient when a digest is available.

A filename reused across runs is not a current-run binding.

### Declared and observed relations

```text
declared relation
→ what workflow, policy, plan, manifest, or contract says should occur

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
final status construction
strict enforcement
terminal ALLOW or BLOCK production
```

An evidence node produces or verifies evidence required by an active
materialized gate.

A preservation node preserves state required for reconstruction or independent
verification.

An advisory node produces a reader, diagnostic, publication, or
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
is sufficient to make that determination.

`unknown` means that the evidence is insufficient to classify safely.

Unknown remains distinct from none.

### Derived primary classes

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

## 8. Unbound authoritative mutation

The strongest authority-integrity condition in this workstream is the absence
of unbound decision-state mutation.

```text
compute node
+ writes authority-bearing state
+ lacks complete authority binding
→ unbound authoritative mutation
```

This differs mechanically from ordinary unbound or unresolved read-only
compute.

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

## 9. Analysis levels

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

A runtime-observation producer and a complete runtime-observed subject chain
are not yet implemented.

A lower analysis level must not claim a higher-confidence classification.

---

## 10. Implemented compute-binding report contract

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
tools/build_pulsemech_compute_binding_report_v0.py
tests/test_pulsemech_compute_binding_report_schema_v0.py
tests/test_check_pulsemech_compute_binding_report_v0.py
tests/test_build_pulsemech_compute_binding_report_v0.py
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

## 11. Fixed-source artifact-observed builder

The first builder is intentionally fixed to the preserved PULSE CI #6066
subject.

It verifies exact immutable carrier identities, including:

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
subject run identity
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

## 12. Runtime-observation contract

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

Raw prompt or raw output absence must remain explicit.

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

## 13. Implemented planned-observed relation

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
an optional ID-keyed explicit expectation map
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

An observation that does not belong to an expectation is not discarded.

An incomplete coverage axis prevents a complete comparison.

A relation record does not create a gate result or release decision.

---

## 14. Fixed-source #6066 plan and expectation binding

The connected fixed-source proof uses:

```text
examples/compute/
pulsemech_compute_fixed_source_6066_component_manifest_v0.json

examples/compute/
pulsemech_compute_fixed_source_6066_integration_plan_v0.json

examples/compute/
pulsemech_compute_subject_run_expectations_6066_v0.json
```

The component manifest declares exactly one execution-planning anchor:

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
→ component presence
→ source identity

workflow_execution_declaration
→ execution expectation
→ declared role
→ mutation authority

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

## 15. Non-active candidate policy surface

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

It contains exactly:

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

## 16. Connected fixed-source #6066 proof

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

The proof does not use the illustrative checked-in relation as the materializer
input.

### Generated compute-binding report result

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

### Generated planned-observed relation result

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

Every other observation remains visible.

No positive-path relation is classified as:

```text
planned_but_not_observed
execution_identity_mismatch
source_digest_mismatch
run_binding_mismatch
declared_role_mismatch
authority_class_mismatch
downstream_consumption_missing
ambiguous_observation_match
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

Post-merge audit result:

```text
Review result:
PASS

actionable findings:
none

targeted regressions:
207 passed
```

---

## 17. Meaning of the fixed-source result

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
that the PULSE CI #6066 runtime was inefficient
that unresolved nodes were unbound
that all observed-but-unplanned compute was unnecessary
that runtime execution was not valid
that resource consumption was excessive
```

Artifact-observed incompleteness identifies the missing recording boundary.

It does not substitute a judgment for missing evidence.

---

## 18. Resource vector and transition efficiency

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

Unavailable values must remain unavailable.

Different units must not be added together.

For an axis `a`:

```text
measured_total_a
= sum of recorded values for nodes with a known value on axis a
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

Transition efficiency is therefore:

```text
compute resource vector
↔ verified binding-role distribution
```

It is not currently a single scalar.

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

## 19. Anti-bureaucracy and evidence-source rule

The primary evidence source must not be a hand-maintained form.

The analyzer derives state from recorded machine surfaces:

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

A manually asserted label such as:

```text
required: true
```

is not proof of binding.

Any additional declaration must be:

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

The next portable subject input must be machine-produced and digest-bound.

It must not become a new manually curated authority surface.

---

## 20. Remaining implementation plan

### Step 1 — portable subject-input contract

Create a strict machine-readable subject packet carrying:

```text
subject repository
workflow identity
workflow run identity
subject run key
source commit
release candidate
run mode

outer carrier identity
outer carrier SHA-256 and size
preservation-manifest identity
artifact-role map
artifact file names
artifact digests and sizes
complete-package identity
policy identity and digest
workflow identity and digest
```

The packet must be produced mechanically.

### Step 2 — reusable analyzer core

Extract the reusable analysis mechanics from the fixed-source builder:

```text
portable subject packet
→ common read-only analyzer core
```

Preserve the existing #6066 builder as a compatibility wrapper.

The #6066 output and semantics must remain regression-locked.

Do not create a second parallel analyzer.

### Step 3 — current-run artifact-observed reference lane

```text
current run
→ machine-produced portable subject packet
→ common analyzer
→ generated artifact-observed report
→ generated planned-observed relation
→ candidate materialization
```

This lane remains non-active.

### Step 4 — runtime-observation producer

Produce strict runtime packets from recorded execution:

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

Only this stage can determine whether the current artifact-level false gates
become true under complete runtime evidence.

### Step 6 — resource measurement

Add measured per-axis resource coverage without synthetic cross-unit
aggregation.

### Step 7 — promotion decision

Any movement from candidate to advisory, required, or release-required remains
a separate policy decision.

```text
successful example
≠ promotion

successful fixed-source replay
≠ promotion

successful current-run artifact proof
≠ promotion

successful runtime proof
≠ automatic promotion
```

Promotion requires explicit evidence, policy review, negative-path coverage,
and a separate PR.

---

## 21. Completed implementation sequence

### PR 1 — design

```text
PR #2734
docs(compute):
define compute-to-transition binding v0
```

Status:

```text
complete
```

### PR 2 — report contract

```text
PR #2735
compute-binding report schema
example
validator
schema and validator tests
CI registration
```

Status:

```text
complete
```

### PR 3 — fixed-source offline builder

```text
PR #2736
fixed-source #6066 report builder

PR #2737
fixed-source builder hardening and regression closure
```

Status:

```text
complete
```

### PR 4 — runtime-observation contract

```text
PR #2738
runtime-observation packet schema
example
validator
tests
CI registration
```

Status:

```text
contract complete
producer pending
```

### PR 5 — planned-observed relation

```text
PR #2741
relation schema
example
validator
tests

PR #2743
relation builder

PR #2744
workflow-only cross-source anchor correction
```

Status:

```text
complete
```

### PR 6 — candidate policy surface

```text
PR #2745
candidate gate identities
policy set
relation-to-status materializer
candidate proof
CI registration
```

Status:

```text
complete
non-active
```

### Connected fixed-source proof

```text
PR #2749
merged commit:
b6149dbd464f7f01760ab5fa80487f7e94e475e7
```

Status:

```text
complete
post-merge Codex review:
PASS
```

The original implementation sequence is therefore complete.

The next work begins at the portable/current-run boundary.

---

## 22. Interaction with existing PULSE boundaries

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

The candidate gates are not a parallel release-authority mechanism.

---

## 23. Interaction with SLSA and VSA

The compute-binding workstream remains separate from the SLSA/VSA workstream.

```text
SLSA/VSA:
authenticated upstream evidence statements
→ downstream PULSEmech admission and transition

compute binding:
executed compute
→ exact relation to evidence, state, preservation, and transition
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

## 24. Non-goals and claim boundary

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

---

## 25. Current non-activation statement

```text
compute-binding report schema:
implemented

compute-binding report validator:
implemented

fixed-source compute-binding builder:
implemented

fixed-source #6066 artifact-observed report:
implemented and proven

runtime-observation packet contract:
implemented

runtime-observation packet producer:
not implemented

planned-observed relation schema and validator:
implemented

planned-observed relation builder:
implemented

compute candidate gate identities:
registered

compute candidate policy set:
declared and non-active

relation-to-candidate-status materializer:
implemented

fixed-source connected candidate proof:
implemented and proven

portable current-run subject input:
not implemented

reusable current-run analyzer lane:
not implemented

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

---

## 26. Mechanical result

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

The exact candidate result is:

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
→ transition, evidence, preservation, advisory, or observer role is explicit
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

The efficiency rule is:

```text
Do not scale or budget compute before measuring where the existing compute is
bound, in explicit units, under explicit coverage.
```
