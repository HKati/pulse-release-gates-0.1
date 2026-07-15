# PULSEmech compute binding and transition efficiency design v0

## WORKMARK

Status: design document only.

This document defines a separate PULSEmech workstream for binding executed
compute to the artifact-bound release-transition mechanism.

This document does not implement a compute-binding analyzer.

This document does not add or activate compute-related gates.

This document does not modify workflow, policy, gate registry, verifier,
materializer, status semantics, release authority, SLSA/VSA behavior, DOI,
citation, Zenodo, tag, release, or release-metadata behavior.

Any implementation, CI integration, candidate gate registration, resource
budget, or release-required activation remains separate work.

---

## 1. Current state

PULSEmech already contains an implemented and exercised artifact-bound
release-authority path.

Its authority relation is:

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
resolve a declared component dependency closure and produce a machine-readable
target-repository plan.

The repository does not currently contain:

```text
a compute-binding report schema
a compute-binding analyzer
an observed compute-to-transition graph
a compute resource vector
a compute-binding candidate gate set
a compute budget
active compute-related release enforcement
```

This workstream begins from that boundary.

---

## 2. Purpose

The purpose of this workstream is to determine whether executed compute has an
explicit, verifiable relation to the completed PULSEmech state transition.

The core question is not:

```text
How much compute was available?
```

The core relation is:

```text
executed compute
→ identified source
→ recorded current-run inputs
→ recorded outputs
→ observed downstream consumption
→ declared transition, evidence, preservation, or advisory role
→ mechanical consequence
```

The intended result is a deterministic report that distinguishes compute that
is bound to the transition mechanism from compute whose relation is absent,
partial, duplicated, unknown, or advisory only.

---

## 3. Core proposition

A compute execution is not part of the release-authority mechanism merely
because it ran inside the same workflow.

A complete compute binding requires an observed relation.

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

The complete relation is:

```text
compute identity
+ exact source identity
+ source digest
+ current-run binding
+ exact input digests
+ exact output digests
+ observed downstream consumption
+ declared role
+ permitted mutation authority
→ mechanically bound compute
```

A declaration alone is not sufficient.

A report that merely states that a node is required is not proof that the node
contributed to the transition.

---

## 4. Non-activation rule

The existence of this design does not create release authority.

A future compute-binding report does not create release authority.

A future compute-binding analyzer does not create release authority.

A future report may observe or reconstruct the existing authority path.

It must not replace:

```text
declared release policy
workflow-effective required-gate materialization
final status.json
PULSE_safe_pack_v0/tools/check_gates.py
the primary ALLOW or BLOCK result
```

No compute-related gate may become active implicitly.

Any future gate registration and any future activation remain separate,
explicit policy decisions.

---

## 5. Scope of the first implementation

The first implementation must be:

```text
read-only
offline-capable
deterministic
schema-bound
artifact-first
run-bound
digest-bound
non-active
non-blocking
```

The first proof target should be a completed, fixed-source, preserved PULSE run.

The initial analyzer should operate over:

```text
a completed subject run
+ exact source revision
+ preserved evidence package
+ exact package inventory
+ exact policy
+ final status and decision artifacts
→ compute-binding report
```

The first implementation must not require modification of the subject run.

---

## 6. Non-goals

This workstream does not initially provide:

```text
carbon accounting
electricity-consumption certification
hardware power measurement
cost accounting
global infrastructure utilization
universal workflow optimization
human productivity scoring
employee monitoring
compliance status
certification
a single cross-unit efficiency score
```

It does not claim that every unbound node is useless.

It does not claim that every unknown node is unbound.

It does not convert an estimated percentage into a policy fact.

It provides the evidence required to measure the relation rather than assuming
the relation.

---

## 7. Anti-bureaucracy rule

This workstream must not create a new hand-maintained form as its primary
evidence source.

The analyzer must derive as much state as possible from existing recorded
surfaces:

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
preservation manifests
exact file digests
```

A manually asserted label such as:

```text
required: true
```

is not sufficient evidence of binding.

Any required declaration introduced later must be:

```text
small
versioned
digest-bound
machine-readable
reviewable
consumed by the analyzer
```

A declaration that has no observed downstream relation must remain partial.

---

## 8. Analysis boundary

Every report must define two separate identities:

```text
subject run
→ the completed run being analyzed

analysis run
→ the execution that creates the compute-binding report
```

The subject run must be identified by at least:

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
policy digest
materialized required gate-set digest, when available
final status digest
terminal decision
```

The analyzer must not silently substitute current repository state for the
exact source state of the subject run.

---

## 9. Observer boundary

The analyzer cannot include its own report digest inside the report being
constructed.

The first implementation must therefore preserve an explicit observer boundary.

Preferred form:

```text
completed subject run
→ separate offline analysis
→ compute-binding report
```

If a future analyzer executes after the terminal decision inside the same
workflow, its compute must be classified separately as:

```text
post_decision_observer
```

Observer compute must not be counted as part of the subject transition closure.

Its resource use may be recorded separately as:

```text
observer_overhead
```

This prevents recursive self-accounting.

---

## 10. Graph model

The analyzer constructs a directed graph containing state and compute nodes.

### Compute-node types

```text
workflow_job
workflow_step
local_tool_execution
verifier_execution
materializer_execution
external_service_call
model_inference
artifact_builder
report_builder
package_verifier
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

Every observed edge should bind exact identities and digests where the source
format permits them.

---

## 11. Compute-node identity

Each compute node should record:

```text
node_id
node_type

workflow_name
job_name
step_name
step_index, when available

tool_identity
tool_version
source_path
source_revision
source_sha256

action_repository, when applicable
action_ref, when applicable
action_commit_sha, when available

command_identity
execution_environment

subject_run_key
started_utc, when available
completed_utc, when available
exit_code, when available
```

Missing source identity must not be silently replaced by a display name.

A mutable action tag is not equivalent to an exact action commit identity.

The report must preserve what is known and classify missing fields as unknown.

---

## 12. State-node identity

Each state node should record:

```text
state_id
state_type
path_or_uri
sha256
size_bytes
schema_identity, when applicable
producer_node_id
subject_run_key
release_candidate_id, when applicable
policy_relation, when applicable
gate_relation, when applicable
```

A path alone is not sufficient when a digest is available.

A filename reused across runs is not a current-run binding.

---

## 13. Declared and observed relations

The analyzer distinguishes:

```text
declared relation
→ what the workflow, policy, manifest, or contract says should occur

observed relation
→ what exact recorded outputs and downstream inputs show occurred
```

A complete relation requires both when both are expected.

Examples:

```text
declared required gate
+ exact evidence digest consumed by the verifier
+ exact verifier output consumed by status construction
→ observed evidence binding
```

```text
workflow comment says "required"
+ no output digest
+ no downstream consumer
→ declared-only partial binding
```

```text
output artifact exists
+ no policy, gate, preservation, or advisory relation
→ unbound or unknown, depending on evidence completeness
```

---

## 14. Analysis levels

Every report must declare its analysis level.

### structural_declared

```text
workflow structure
+ policy structure
+ manifests
→ declared graph only
```

This level may identify expected relations.

It must not claim observed digest consumption.

### artifact_observed

```text
declared graph
+ exact state-artifact digests
+ observed cross-artifact references
→ artifact-level observed graph
```

This is the minimum target for the first implementation proof.

### runtime_observed

```text
artifact-observed graph
+ recorded execution identity
+ step timing
+ runtime input/output relations
+ external-call or model-use records
→ runtime-observed graph
```

This remains later work.

A lower analysis level must not claim a higher confidence classification.

---

## 15. Binding roles

A compute node may have one declared primary role.

```text
transition
evidence
preservation
advisory
observer
unknown
```

### transition role

The node directly contributes to:

```text
gate-set materialization
final status construction
strict enforcement
terminal ALLOW or BLOCK production
```

### evidence role

The node produces or verifies evidence required by an active materialized gate.

### preservation role

The node preserves state required to reconstruct or independently verify the
completed transition.

Preservation does not create release authority.

### advisory role

The node produces a reader, diagnostic, dashboard, publication, or
non-authoritative analysis surface.

Advisory output does not create release authority.

### observer role

The node analyzes an already completed subject run.

### unknown role

The available evidence does not establish a role.

---

## 16. Binding status

Each compute node receives one binding status:

```text
complete
partial
none
unknown
```

### complete

A complete binding requires all fields applicable to the role:

```text
exact compute identity
exact subject-run binding
exact source identity or digest
exact input identity and digest
exact output identity and digest
observed downstream consumption
declared role
permitted mutation authority
```

### partial

A partial binding exists when a relevant relation is declared or partly
observed, but one or more required links are absent.

### none

No transition, evidence, preservation, advisory, or observer relation is found,
and the analyzed evidence is sufficient to make that determination.

### unknown

The available evidence is insufficient to classify the node safely.

Unknown must remain distinct from none.

---

## 17. Derived primary classes

From role and binding status, the analyzer derives one primary class:

```text
transition_bound
evidence_bound
preservation_bound
advisory_bound
observer
unbound
unknown
```

A node may also carry non-exclusive flags:

```text
duplicate_candidate
mutation_authority_present
cross_run_input_present
mutable_source_reference
resource_measurement_partial
```

Flags must not cause resource use to be counted twice.

---

## 18. Authority-bearing state

Authority-bearing state includes at least:

```text
admitted required evidence
canonical candidate state
canonical verifier result
workflow-effective materialized required gate set
final status.json
release-decision artifact
primary ALLOW or BLOCK result
```

Policy source is an immutable authority input for the subject run.

A runtime mutation of the policy source or of its effective digest must be
treated as an authority-bound event.

---

## 19. Mutation-authority classes

Each compute node should declare or derive its maximum permitted write class:

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

A node must not write above its permitted class.

Examples:

```text
reader-surface builder
→ may write advisory_output
→ must not write final_status
```

```text
evidence producer
→ may write release_evidence
→ must not directly write release_decision
```

```text
generic gate checker
→ may produce the terminal decision
→ must not rewrite the declared policy
```

---

## 20. Unbound authoritative mutation

The strongest future control in this workstream is not an efficiency ratio.

It is the absence of unbound decision-state mutation.

```text
compute node
+ writes authority-bearing state
+ missing complete authority binding
→ unbound authoritative mutation
```

This condition is mechanically distinct from ordinary unbound read-only
compute.

```text
unbound read-only compute
→ efficiency or architecture finding

unbound authoritative mutation
→ release-authority integrity finding
```

A future policy may treat the second condition as blocking.

The v0 design document and first report remain non-blocking.

---

## 21. Decision closure

The analyzer builds the decision closure backward from the terminal result.

```text
ALLOW or BLOCK
← enforcement invocation
← final status
← workflow-effective materialized required gate set
← required gate states
← verifier outputs
← admitted evidence
← evidence producers
← exact inputs and source identities
```

For each active required gate, the analyzer must attempt to identify:

```text
gate identity
gate value
materialized-set membership
status location
deriving verifier output
verifier output digest
accepted evidence input
evidence digest
producer identity
producer source digest
subject-run binding
```

An unresolved required-gate source must remain an explicit finding.

---

## 22. Preservation closure

Preservation is analyzed separately from release authority.

```text
completed decision
→ exact artifacts required for reconstruction
→ digest inventory
→ structural completeness
→ independent verification
→ preservation record
```

A preservation node may be completely bound without being part of the primary
decision path.

The report must not represent preservation as release authority.

---

## 23. Advisory closure

Advisory surfaces may include:

```text
dashboards
reader reports
publication records
visualizations
diagnostic summaries
non-authoritative audits
```

An advisory node is not automatically unbound.

To qualify as advisory-bound, it must have:

```text
an explicit advisory purpose
an identified output
an exact output digest
no undeclared authority-bearing mutation
a named publication, reader, audit, or diagnostic relation
```

A label alone remains partial.

---

## 24. Duplicate compute

Compute may be bound and still duplicated.

A future analyzer may flag a duplicate candidate when two or more nodes share:

```text
equivalent input digests
equivalent policy binding
equivalent declared function
equivalent output role
no distinct trust-domain requirement
```

Duplicate detection must remain advisory until semantic equivalence is proven.

Two independent verifiers are not duplicates merely because they inspect the
same artifact.

Trust separation may require repeated computation.

---

## 25. Resource vector

The workstream must not force different resource units into one synthetic
number.

Resource use is represented as a vector.

Possible axes include:

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

Not every platform exposes every axis.

Unavailable values must be represented as unavailable, not estimated silently.

---

## 26. Per-axis ratios

For each measured axis `a`:

```text
measured_total_a
= sum of recorded values for nodes with a known value on axis a
```

The report may calculate:

```text
transition_bound_ratio_a
evidence_bound_ratio_a
preservation_bound_ratio_a
advisory_bound_ratio_a
unbound_ratio_a
unknown_ratio_a
```

Each ratio is relative only to `measured_total_a`.

The report must also record measurement coverage:

```text
nodes_with_measurement_a
total_subject_nodes
measurement_coverage_ratio_a
```

A ratio with incomplete coverage must not be presented as total-system
consumption.

No values from different units may be added together.

---

## 27. Transition efficiency

Transition efficiency is not defined as a single universal scalar.

It is the relation between:

```text
compute resource vector
and
verified transition-role distribution
```

A report may state:

```text
on runner_wall_seconds:
X% transition-bound
Y% evidence-bound
Z% preservation-bound
...

on model_output_tokens:
...
```

It must not claim:

```text
overall efficiency = one number
```

unless a future declared policy defines and justifies an explicit weighting
model.

---

## 28. Human compute boundary

Human compute is real but remains a separate measurement domain.

It must not be added numerically to machine resource units.

The first compute-binding implementation does not require a human-filled form.

A later, separate workstream may observe machine-recorded interaction events
such as:

```text
manual workflow dispatches
manual approvals
manual reruns
manual retries
manual exception records
```

Any future human-time record must preserve its own unit and evidence source.

This document does not define that contract.

---

## 29. Initial input surfaces

A first analyzer may consume exact, read-only copies of:

```text
workflow source at the subject commit
pulse_gate_policy_v0.yml at the subject commit
policy-derived materialized gate-set record
final status.json
release-decision record
recorded evidence manifests
recorded verifier reports
candidate records
artifact-provenance bindings
release package inventory
package-completeness report
independent package-verification report
preservation manifest
workflow run and job metadata
```

Optional later input:

```text
pulsemech_integration_plan_v0.json
```

The integration plan may describe an expected component closure.

It does not prove that the planned compute was executed or consumed.

---

## 30. Planned graph and observed graph

A later phase may compare:

```text
planned compute graph
↔ observed compute graph
```

Possible results:

```text
planned and observed
→ expected execution

planned but not observed
→ missing execution

observed but not planned
→ undeclared execution

observed with different source digest
→ source substitution

observed with different authority class
→ authority mismatch
```

This comparison remains separate from the first offline report proof.

---

## 31. Report identity

The proposed report identity is:

```text
schema_version:
pulsemech_compute_binding_report_v0

report_type:
pulsemech_compute_binding_report
```

The report filename is:

```text
pulsemech_compute_binding_report_v0.json
```

The report must be deterministic for identical canonical inputs.

---

## 32. Proposed report shape

The design does not yet introduce a normative schema.

A future schema should preserve at least:

```json
{
  "schema_version": "pulsemech_compute_binding_report_v0",
  "report_type": "pulsemech_compute_binding_report",
  "tool": {
    "id": "build_pulsemech_compute_binding_report_v0",
    "version": "0.1.0",
    "source_sha256": "<sha256>"
  },
  "analysis_boundary": {
    "analysis_level": "artifact_observed",
    "subject_run_key": "<exact subject run key>",
    "analysis_run_key": "<separate analysis run key or offline identity>",
    "observer_in_subject_totals": false
  },
  "subject": {
    "repository": "HKati/pulse-release-gates-0.1",
    "workflow": "PULSE CI",
    "workflow_run_id": 29249887581,
    "workflow_run_number": 6066,
    "workflow_run_attempt": 1,
    "source_commit": "46b639706e23f80fe296a8893be18e2b5ab21f7e",
    "release_candidate_id": "main",
    "run_mode": "prod",
    "active_policy_sets": [
      "required",
      "release_required"
    ],
    "policy_sha256": "<sha256>",
    "materialized_gate_set_sha256": "<sha256-or-null>",
    "final_status_sha256": "<sha256>",
    "decision": "ALLOW"
  },
  "inputs": [
    {
      "role": "<input role>",
      "path_or_uri": "<path or URI>",
      "sha256": "<sha256>",
      "size_bytes": 0
    }
  ],
  "compute_nodes": [],
  "state_nodes": [],
  "edges": [],
  "resource_summary": {
    "axes": {}
  },
  "summary": {
    "subject_compute_nodes": 0,
    "transition_bound_nodes": 0,
    "evidence_bound_nodes": 0,
    "preservation_bound_nodes": 0,
    "advisory_bound_nodes": 0,
    "unbound_nodes": 0,
    "unknown_nodes": 0,
    "unbound_authoritative_mutation_count": 0,
    "decision_closure_complete": false,
    "authority_binding_complete": false,
    "resource_measurement_status": "partial"
  },
  "findings": [],
  "errors": [],
  "ok": true
}
```

`ok: true` means that the report was constructed and validated successfully.

It does not mean:

```text
release allowed
workflow efficient
all compute bound
no findings
```

The terminal release decision remains a separate recorded value.

---

## 33. Finding identities

The first contract should support explicit findings such as:

```text
subject_run_identity_missing
subject_source_commit_mismatch

policy_binding_missing
policy_digest_mismatch
materialized_gate_set_binding_missing

decision_root_missing
decision_status_binding_missing
required_gate_source_unresolved

compute_source_identity_missing
compute_source_digest_missing
compute_run_binding_missing

declared_binding_not_observed
observed_binding_not_declared
downstream_consumer_missing

unbound_compute
unknown_compute_binding
duplicate_compute_candidate

undeclared_authoritative_writer
authority_class_mismatch
cross_run_input_reuse

resource_measurement_missing
resource_measurement_partial

observer_boundary_violation
subject_artifact_mutation_attempt
```

Findings must be deterministic and machine-readable.

---

## 34. Severity boundary

The v0 report remains read-only and non-blocking.

Findings may be categorized as:

```text
information
advisory
authority_integrity_candidate
```

A future blocking policy must not treat ordinary resource inefficiency as
equivalent to authority corruption.

Potential future distinction:

```text
unbound read-only node
→ advisory

unknown resource measurement
→ advisory

unbound authority-bearing writer
→ blocking candidate

source digest substitution on authority path
→ blocking candidate

cross-run evidence reuse on required path
→ blocking candidate
```

Activation remains separate.

---

## 35. Possible future candidate gates

The following names are placeholders only.

They are not registered by this document.

```text
compute_transition_path_complete
compute_transition_authority_binding_ok
compute_transition_unbound_mutation_absent
compute_transition_resource_usage_recorded
```

A later efficiency gate might be considered only after stable measurement:

```text
compute_transition_unbound_ratio_within_budget
```

No budget gate should be introduced before:

```text
measurement units are stable
coverage is reported
classification is reproducible
fixed-run replay is proven
false and missing states are tested
```

---

## 36. First fixed-source proof target

The first implementation proof should analyze the preserved PULSE CI #6066
release-grade reference artifacts.

The proof must remain offline and read-only.

The analyzer should:

```text
verify the preserved outer artifact digests
verify the complete package inventory
identify the exact subject run
bind the source commit
bind the active policy identity and digest
locate the final status and decision state
reconstruct as much of the evidence-to-decision graph as the preserved package permits
classify unresolved relations as unknown
classify preservation nodes separately
emit a deterministic report
perform zero mutation of the preserved package
```

The proof must not invent missing workflow-step evidence.

The proof should expose exactly where the current package already supports
artifact-observed binding and where additional runtime recording would be
required.

---

## 37. Determinism requirements

For identical canonical inputs, the analyzer must emit byte-identical output.

Required properties:

```text
strict JSON parsing
duplicate-key rejection
non-finite number rejection
stable node ordering
stable edge ordering
stable finding ordering
stable path normalization
stable JSON key ordering
newline-terminated UTF-8 output
no hidden wall-clock fields in deterministic mode
```

Any generated timestamp must be supplied explicitly or excluded from the
deterministic comparison surface.

---

## 38. Read-only requirements

The analyzer must refuse to:

```text
rewrite subject artifacts
rewrite the preservation manifest
write into the preserved ZIP archives
modify status.json
modify the release decision
modify policy
modify workflow files
modify the gate registry
```

Output must be written outside the subject package or to an explicitly separate
analysis directory.

A path inside the immutable subject package must be rejected.

---

## 39. Expected implementation files

A future contract PR may introduce:

```text
schemas/pulsemech_compute_binding_report_v0.schema.json
examples/compute/pulsemech_compute_binding_report_6066_example_v0.json
tools/check_pulsemech_compute_binding_report_v0.py
tests/test_pulsemech_compute_binding_report_schema_v0.py
```

A later implementation PR may introduce:

```text
tools/build_pulsemech_compute_binding_report_v0.py
tests/test_build_pulsemech_compute_binding_report_v0.py
```

A separate runtime-observation PR may introduce additional input surfaces.

The exact filenames may change, but the work must remain narrowly scoped.

---

## 40. Required first-contract tests

The report contract must test:

```text
valid report passes schema validation
duplicate JSON key fails
non-finite number fails
unknown binding remains distinct from unbound
decision value remains distinct from report ok state
resource units remain separate
observer overhead remains outside subject totals
finding identities are stable
```

---

## 41. Required first-builder tests

The first builder must test:

```text
identical inputs produce byte-identical output
exact subject run identity is preserved
exact source commit is preserved
exact input digests are preserved
preserved package is not modified
output inside subject package is rejected

declared-only relation does not become complete
observed digest relation is recorded
missing downstream consumer remains explicit
missing relation becomes unknown when evidence is incomplete

preservation-bound state remains distinct from release authority
advisory state remains distinct from required state

unbound read-only compute is reported
unbound authoritative mutation is distinguished
cross-run input is reported

per-axis resource values are not added across units
partial measurement coverage is reported
```

---

## 42. Implementation sequence

### PR 1 — design only

```text
docs/compute/PULSEMECH_COMPUTE_BINDING_AND_TRANSITION_EFFICIENCY_DESIGN_v0.md
```

No behavior change.

### PR 2 — report contract

```text
schema
example
schema validator
schema tests
```

No live analyzer.

No workflow integration.

### PR 3 — fixed-source offline builder

```text
PULSE CI #6066 preserved package
→ deterministic artifact-observed report
```

No live workflow mutation.

No active gate.

### PR 4 — runtime observation contract

```text
job and step identity
runtime timing
runtime input/output bindings
external-call records
```

Still non-active.

### PR 5 — planned-versus-observed relation

```text
integration plan
↔ observed compute graph
```

Separate from the planner mechanism itself.

### PR 6 — candidate policy surface

Only after the previous proofs are complete:

```text
non-active candidate gate set
candidate-only materialization
candidate-only generic check_gates.py proof
```

Any active promotion remains later and separate.

---

## 43. Interaction with existing PULSE boundaries

The compute-binding workstream must preserve:

```text
check_gates.py remains generic
policy remains the source of required gate identities
materialization remains policy-derived
status remains the complete gate-state carrier
ALLOW and BLOCK remain the terminal transition results
preservation remains non-authoritative
reader surfaces remain non-authoritative
```

The analyzer observes those relations.

It does not redefine them.

---

## 44. Interaction with SLSA and VSA

This workstream is separate from the SLSA/VSA workstream.

SLSA/VSA concerns:

```text
authenticated upstream evidence statements
→ downstream PULSEmech admission and transition
```

Compute binding concerns:

```text
executed compute
→ exact relation to evidence, state, preservation, and transition
```

The workstreams may later share:

```text
source identity
artifact digest
policy digest
run binding
verifier identity
attestation digest
```

They must not be bundled merely because they share binding fields.

---

## 45. Claim boundary

This document does not claim:

```text
that 80% or 90% of compute is currently unbound
that all bureaucracy is machine waste
that all repeated verification is duplicate work
that all advisory output is unnecessary
that a global efficiency scalar exists
that energy consumption has been measured
that carbon impact has been measured
that the PULSE CI #6066 runtime was inefficient
```

It defines the mechanism required to measure the relation.

The hypothesis does not become a result until the report is produced from
recorded evidence.

---

## 46. Forbidden bundling

Do not combine this design or its first implementation with:

```text
SLSA VSA activation
release-required promotion
workflow cleanup
policy reorganization
gate registry cleanup
unrelated adoption-planner expansion
DOI changes
Zenodo changes
citation changes
README title changes
tag creation
release creation
release-metadata changes
```

Do not combine the initial read-only report with a blocking budget gate.

---

## 47. Current non-activation statement

At the time of this design:

```text
compute-binding report schema:
not implemented

compute-binding analyzer:
not implemented

fixed-source compute-binding proof:
not implemented

runtime-observed compute graph:
not implemented

compute candidate gate set:
not registered

compute release-required enforcement:
not active

compute budget:
not defined
```

The existing PULSEmech release-authority mechanism remains unchanged.

---

## 48. Mechanical result

The intended relation is:

```text
completed subject run
+ exact source state
+ exact recorded artifacts
+ exact policy and materialized gates
+ exact terminal decision
→ compute-to-transition graph
→ binding classification
→ per-unit resource relation
→ deterministic report
```

When compute has a complete observed relation:

```text
complete binding
→ transition, evidence, preservation, advisory, or observer role is explicit
```

When the relation is absent:

```text
no binding
→ unbound
```

When the available evidence is incomplete:

```text
insufficient evidence
→ unknown
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

The efficiency rule is:

```text
Do not scale compute before measuring where the existing compute is bound.
```
