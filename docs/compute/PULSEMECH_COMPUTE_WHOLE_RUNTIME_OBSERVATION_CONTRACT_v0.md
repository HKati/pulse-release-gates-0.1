# Whole-runtime observation evidence v0

This contract defines the prospective Step 5C current-run whole-runtime
observation mechanism under work order #2879. It does not declare that the
mechanism has already been implemented, acquired, preserved or accepted.

## R2 evidence-profile amendment and implementation status

The R1 source reconciliation and the owner-recorded R2 proposal in #2879
establish the target for the replacement mapping under this contract:

```text
evidence profile:
pulsemech_step5c_post_run_state_evidence_v1

workflow topology profile, unchanged:
pulse_ci_hosted_release_grade_v0
```

The evidence profile and workflow topology profile are different identities.
The former fixes what evidence is required; the latter fixes the selected
workflow/job/step/inference graph. Neither identity is a verification verdict.

This amendment specifies the prospective replacement implementation. This
contract-only change does not add schema support, change a runtime checker,
activate the profile, or make an old carrier valid under new requirements.
The coordinated schema, producer and verifier changes, complete regression
execution, real existing-core replay and final-head review remain necessary.
The current complete-acceptance stop remains in force during that work.

R2 explicitly changes the exact-content obligations for two legacy mapping
roles: the pre-insertion ledger and the final artifact-binding signed receipt.
It does not establish either stronger claim, repair missing historical evidence,
or prove that the original all-exact generated mapping was correct.

Every future I/E completion statement must identify this evidence profile and
retain its pre-state, signed-receipt and original-runtime-read limitations.
No completion of the stronger legacy mapping may be inferred from this profile.
An untagged, stale or differently profiled record must not be reinterpreted by
applying these requirements after acquisition.

Decision provenance:

- [R1 recovery work order](https://github.com/HKati/pulse-release-gates-0.1/issues/2879#issuecomment-5655180182).
- [R1 source reconciliation result](https://github.com/HKati/pulse-release-gates-0.1/issues/2879#issuecomment-5655489319).
- [R2 post-run evidence-profile proposal](https://github.com/HKati/pulse-release-gates-0.1/issues/2879#issuecomment-5655562448).

## Scope

`Whole-runtime` does not mean every host process, system call, network event or
provider-internal operation. In this contract it means the complete predeclared
workflow-run, job and source-declared-step extent of one current-run PULSE CI
hosted release-grade execution, together with the selected preserved state,
explicit external-operation and controlled model-inference obligations of the
named evidence profile. It does not assert that every declared intermediate
state or runtime read relationship is observed.

The scope identifier is:

```text
one_current_run_pulse_ci_hosted_release_grade_declared_workflow_graph_v0
```

The contract does not claim host-wide tracing, complete child-process tracing,
GitHub Action internals, package-manager request completeness, complete network
paths, provider-internal model execution, model-internal state or resource
measurement.

## Role separation

The subject is one exact manually dispatched PULSE CI run:

```text
workflow: PULSE CI
path: .github/workflows/pulse_ci.yml
event/ref: workflow_dispatch / main
strict_external_evidence: true
llamaguard_evidence_mode: hosted_full_runtime
```

The new Step 5C reference workflow is an acquisition supervisor and post-run
collector. It is outside subject totals.

The existing Step 3F workflow is a post-subject producer:

```text
.github/workflows/pulsemech_compute_current_run_export_candidate.yml
```

It consumes the exact completed PULSE CI run and supplies the existing
current-run carrier, expectation and subject-input packet to the existing
compute-binding path.

Step 3G remains a separate artifact-observed analysis workflow and is not
dispatched by the Step 5C reference.

```text
PULSE CI subject
≠ Step 3F export
≠ Step 3G artifact-observed analysis
≠ Step 5C supervisor or collector
≠ independent Step 5C verifier
```

Preparation, dispatch, collection, verification, reconstruction and publication
are not observed subject work.

## Permissions and authority

The acquisition job may receive only:

```text
contents: read
actions: write
```

`actions: write` is used only to dispatch the two reviewed workflows.

The independent verification job receives only:

```text
contents: read
actions: read
```

No repository-content, policy, registry, deployment, package, issue, pull
request, release or publication write permission is introduced.

The subject PULSE CI run may produce its existing release decision. The Step 5C
mechanism neither participates in nor changes that decision.

```text
authority_effect: none
same_run_release_authority_eligible: false
active_gate_eligible: false
```

## Reviewed source and dispatch identity

The reference workflow requires one owner-reviewed lowercase 40-hex
`source_commit`. Before preparation, and again immediately before each
dispatch, it requires agreement among:

```text
source_commit input
github.workflow_sha
github.sha
current main head
checked-out HEAD
```

Workflow, policy, registry, controlled LlamaGuard dataset and all other
prelaunch inputs are read from that same source commit.

The subject dispatch uses:

```text
POST repos/HKati/pulse-release-gates-0.1/actions/workflows/pulse_ci.yml/dispatches
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2026-03-10
```

```json
{
  "ref": "main",
  "inputs": {
    "strict_external_evidence": "true",
    "llamaguard_evidence_mode": "hosted_full_runtime"
  }
}
```

The request pins `X-GitHub-Api-Version: 2026-03-10`. Under that API
contract, `return_run_details` has been removed and every successful dispatch
returns HTTP 200 with one positive `workflow_run_id`, an exact API `run_url`
and an exact repository `html_url`, all naming the same run. The optional
`return_run_details: true` field applies to the older compatibility contract
and is not sent by this version-pinned request.

A `204 No Content` response under the pinned API version is rejected as
`dispatch_run_details_unavailable`. No run-list correlation fallback is
permitted.

After that exact subject reaches `completed / success`, Step 3F is dispatched:

```text
POST repos/HKati/pulse-release-gates-0.1/actions/workflows/pulsemech_compute_current_run_export_candidate.yml/dispatches
```

```json
{
  "ref": "main",
  "inputs": {
    "source_run_id": "<exact subject workflow_run_id>"
  }
}
```

The provider response has the same run-ID and URL requirements.

Latest-run lookup, timestamp correlation, run-list guessing, branch-only
selection and silent attempt substitution are forbidden. A malformed response,
URL/run-ID disagreement, changed `main`, wrong repository, workflow, ref, input
set, source commit or attempt is an acquisition error.

## Bounded acquisition

Every API call, poll, page and download is finite. The v0 implementation uses
checked-in bounds no weaker than:

```text
single API request: 60 seconds
subject wait: 90 minutes
Step 3F wait: 45 minutes
jobs: 64
platform step records: 2048
artifacts: 256
single API JSON body: 16 MiB
single downloaded artifact envelope: 768 MiB
aggregate downloaded artifact envelopes: 1536 MiB
capture members: 8192
capture uncompressed bytes: 2048 MiB
```

Pagination must close explicitly. Every response is untrusted input and is
subject to strict size, JSON-shape, duplicate-key, number, identifier and URL
validation.

Timeout, cancellation, rate-limit exhaustion, malformed data, incomplete
pagination or failed download produces no accepted carrier.

## Prelaunch plan

The expected graph is built and independently validated before subject
dispatch. The plan binds exact bytes for:

```text
PULSE CI workflow
Step 3F workflow
this contract and its schema
policy and gate registry
external signer and threshold policies
controlled LlamaGuard case dataset
selected action pins
selected dispatch inputs
reviewed source commit
```

It records the scope, workflow identity, job and step templates, raw conditions,
`needs` relations, stable occurrence IDs, state roles, required consumers,
terminal roles, external-operation classes, inference templates, privacy and
trust boundaries, finite limits and authority boundary.

It contains no future run ID, job database ID, artifact ID, timestamp, output
digest, PASS verdict or release decision.

The independent plan checker reconstructs the plan from exact source bytes. It
does not import or trust the plan builder. A plan derived from observed jobs,
steps, artifacts or outputs is invalid.

For semantic state mapping, exact-source reconstruction includes applicable
workflow variables, command arguments, called-tool defaults and read/write
behavior, state-version boundaries, upload definitions and package membership.
The builder and checker agreeing on two copies of the same semantic table is
not sufficient. Independent source-grounded checks must detect the same wrong
locator or direct-consumer edge even when both implementations contain it.

Use a bounded, reviewed source profile. Ambiguous or unsupported command forms
must fail rather than be executed, guessed, or interpreted by a general shell
interpreter. Pin every source dependency used to resolve a mapping fact in the
prelaunch source inventory. Recomputed container or plan digests do not repair
a semantic source mismatch.

The reviewed acceptance policy is a separate input to this interpretation.
Source declarations alone do not determine which evidence must close I/E;
implementation defaults do not determine the policy. No implicit all-exact
requirement or general unavailable-evidence fallback is permitted.

## Stable occurrence IDs

```text
job:
execution:step5c:job:<source-job-id>

source-declared step:
execution:step5c:step:<source-job-id>:<three-digit-source-ordinal>

collector:
execution:step5c:collector:post-run-platform-export

model inference:
inference:step5c:llamaguard:<case-id>

external operation:
call:step5c:<source-job-id>:<source-step-ordinal>:<operation-role>
```

Step ordinals come from exact workflow source order, not GitHub-generated runtime
step numbers. Duplicate identifiers are rejected.

## Reference-profile topology

The `pulse_ci_hosted_release_grade_v0` profile contains:

| Source job ID | Required result | Step templates |
| --- | --- | ---: |
| `pulse` | `success` | 83 |
| `attest_release_authority_artifact_binding` | permitted `skipped` | 2 |
| `attest_llamaguard_current_run_summary` | `success` | 8 |
| `release_grade_recorded_path` | `success` | 33 |
| `attest_release_grade_artifact_binding` | `success` | 2 |
| `assemble_release_grade_reference_package` | `success` | 6 |
| `verify_release_grade_reference_package` | `success` | 8 |
| `tools-tests` | `success` | 5 |

The selected path has:

```text
8 job templates
7 successful jobs
1 permitted skipped job
147 source-declared step templates
145 instantiated source-declared steps
101 successful step occurrences
44 permitted skipped step occurrences
2 uninstantiated steps under the skipped job
```

The core artifact-binding attestation job may be skipped only because its exact
source condition evaluates false for the selected hosted release-grade dispatch.
The later release-grade artifact-binding attestation job must succeed.

Any future topology change requires a reviewed profile decision. It is not
silently admitted because a parser can read it.

## Platform lifecycle records

GitHub-generated setup, post-action cleanup and completion records are preserved
in the raw response but excluded from the source-declared E totals.

The matcher first accounts for every planned source-declared step in source
order. Every remaining platform step must match a narrow reviewed lifecycle
allowlist derived from the action structure. Broad prefix matching is not
sufficient.

An unmatched non-lifecycle step, or a lifecycle record used to replace a missing
declared step, is an acquisition error.

## Terminal semantics

Every planned occurrence ends as one of:

```text
success
permitted skipped
failure
cancelled
timed out
launch failed
missing
unknown
```

Only `success` and a conditionally justified `permitted skipped` state satisfy
this profile. A required skipped occurrence and a permitted-skipped occurrence
that unexpectedly runs both fail closure.

The subject and provider must each use attempt 1. A rerun is a new acquisition,
not a continuation of the accepted one.

## Source and command identity

Workflow, policy, registry, dataset and repository-tool source states bind to
exact committed bytes.

A GitHub Action identity is exact only when a full immutable action commit SHA
is present in the workflow and plan.

A shell step may have an exact source command template because its complete
`run:` block is bound. That does not prove every child process, imported module
or executable byte opened later.

A directly launched repository tool has exact committed-file identity. Executed
byte identity remains partial unless a sealed-source, descriptor-bound or
equivalent mechanism proves that the verified bytes are the executed bytes.

Display names, environment values, log lines, path strings, self-declared
revisions and equal output content do not become exact execution identity.

## Observation granularity

| Layer | Step 5C state |
| --- | --- |
| workflow run | completely predeclared |
| jobs | completely predeclared |
| source-declared workflow steps | completely predeclared |
| platform lifecycle steps | retained as metadata; excluded from E |
| direct child processes | not claimed complete |
| selected states and transitions | profile-specific content obligations; original-runtime transition proof remains separately qualified |
| external operations | invocation boundary; internals may remain partial |
| controlled model inference | six exact case occurrences |
| resource measurement | unavailable |

A complete workflow/job/step graph is not complete host tracing. An action
invocation is not its internal process graph. A recorded model boundary is not
provider-internal execution.

## Run, job and step evidence

The observer preserves the exact subject run response and every jobs page for
the exact run and attempt. It verifies repository, workflow identity, event,
branch, source SHA, run ID/number/attempt, status, conclusion, URLs and times.

Each job binds its database ID, source job ID, run identity, terminal result,
times and runner labels. Each declared step binds its parent job, source ordinal,
source name and condition to the corresponding platform name, result, times and
source order.

Platform timestamps are platform metadata, not cryptographic authentication of
the hosted runner or GitHub control plane.

## States and consumption

The mapping and evidence records must distinguish four different facts:

1. A source declaration of an input, output, producer or consumer.
2. The exact content and version that survives in a preserved carrier.
3. The occurrence-bound evidence available for the particular execution.
4. The evidence obligation required by the named I/E acceptance profile.

None is interchangeable with another. A plan is not an observed read receipt.
A later collector reading equal bytes does not prove an earlier consumer read.
An upload action's success is not proof of the semantic validity of every file.

Separate content origin, canonical preservation writer, carrier publisher and
observed occurrence binding. A copying or publishing operation does not become
the semantic producer of the original content merely because it writes bytes.
Record source/platform associations at their actual strength; do not promote
them into direct-process read receipts or unobserved executed-byte identities.

Each state retains its semantic role and version, source locator, content
status, digest and size where supported, observer, subject run, candidate,
authority-bearing status, mutation class and observation basis. A source-declared
producer or consumer remains separately qualified whenever its original runtime
binding is not evidenced. An absent observation is not replaced with its planned
value. The existing generic runtime schema remains unchanged.

All 57 legacy roles and the five additional R1 roles must be accounted for in
the replacement mapping and old-to-new reconciliation. This is 62 review
obligations, not a mandatory count of generic runtime state records, 62 observed
states, or an expansion of the subject execution count. Representations must
avoid duplicate counting and packet/downstream hash cycles.

Record presence, exact-content duty, occurrence evidence and I/E completion
participation are separate requirements. `required=True` in a legacy table does
not by itself decide all four. Likewise, a schema admitting `metadata_only` or
`unavailable` does not make those states acceptable for an exact-content duty.

The following semantic corrections are required by R1 source reconciliation:

| Role | Source/configuration-based locator |
| --- | --- |
| Decision ledger section | `PULSE_safe_pack_v0/artifacts/release_decision_v0_ledger_section.html` |
| Composed decision report | `PULSE_safe_pack_v0/artifacts/report_card.with_release_decision.html` |
| JUnit | `PULSE_safe_pack_v0/artifacts/reports/junit.xml` |
| SARIF | `PULSE_safe_pack_v0/artifacts/reports/sarif.json` |
| Advisory bundle directory | `${RUNNER_TEMP}/release-grade-reference-run-v0/` |
| Pre-attestation artifact | `pulse-pre-attestation-<subject_run_id>-1` |

These are reviewed semantic anchors, not permission to trust another copied
output table. The replacement checker must verify them against the source.
Keep repository paths, run-specific paths, archive names and archive-member
selectors distinct.

The report-composition step directly reads the final ledger and rendered
HTML decision section, not the JSON status summary. The parity step reads
`status.json` and `report_card.html`, not `report_card.with_release_decision.html`.
Indirect content ancestry is not a direct input relationship. The rejected old
edges remain traceable in the migration record; do not invent reads in PULSE CI
to make an incorrect old table true.

The observer may produce only advisory, preservation and downstream derivation
outputs. Subject-produced final status, gate materialization and release decision
remain owned by the subject. No Step 5C observation changes their authority.

A consumption claim closes only when its designated consumer uses the exact
state from the exact producer occurrence. Equal bytes from another occurrence,
same filenames from another run, observer-only reads, producer self-reads or
unrelated reads are insufficient. Whole-runtime R/C completion and proof of all
original-runtime reads remain outside this profile's completion claim.

### Role-specific evidence rules

| Obligation | Required evidence and rejection boundary |
| --- | --- |
| `exact_source_content` | Exact reviewed Git/source bytes and their revision/path/digest/size binding. This is not proof of every original runtime read. |
| `exact_preserved_content` | Exact selected carrier/member bytes with closed membership, version identity and subject/run/attempt/source bindings. A matching basename alone is insufficient. |
| `exact_preserved_archive` | The exact selected archive and its identity/digest/size, not a replacement rezip or a similarly named archive. |
| `exact_preserved_tree` | A closed relative-name/size/digest inventory within its exact parent carrier. Reject missing, added, duplicate or conflicting members. |
| `exact_preserved_tree_and_carrier` | Both the selected archive and the closed inventory of the required directory contents. Directory re-zipping is not equivalent. |
| `exact_provider_content` | Exact Step 3F member and transitive carrier bindings to the selected provider and subject. Step 3F stays outside subject totals. |
| `checked_controlled_case_derivation` | Deterministic derivation from the exact preserved controlled-case evidence and source dataset, with the existing case/model/token checks. Do not expose raw prompt/output text. |
| `checked_status_policy_projection` | A named deterministic gate-value projection bound to exact parent status and policy bytes. It is not a standalone observed materialization receipt. |
| `checked_source_argv_derivation_with_runtime_receipt_gap` | Independently checked policy/source derivation with explicit absence of captured original argv. Do not relabel a later manifest as a runtime argument receipt. |
| `checked_downstream_derivation` | The real existing-core output and its validators, exact derived bytes and both independent reconstructions. No success stub or packet self-reference is permitted. |
| `required_explicit_content_gap` | The named pre-insertion ledger version remains present and unavailable; its content and transition remain unproved under the D1 rule below. |
| `required_action_metadata_with_receipt_gap` | The exact successful final binding attestation action occurrence is required; signed receipt content and independent receipt verification remain unproved under D6 below. |

These names identify semantic obligations; the schema implementation must carry
their closed, profile-bound meaning. They are not new generic-runtime enum values
and must not be inserted into the unchanged generic schema.

### D1: pre-insertion Quality Ledger

Keep the ledger produced by R13 before the R18 in-place insertion distinct from
the final ledger. This post-run profile requires an explicit content/transition
gap for the pre-R18 role; it does not require exact pre-R18 bytes for its I/E
completion. Never substitute final HTML, an earlier run, or inverse rendering
into observed pre-state fields. The stronger pre-state claim remains open.

This is the explicit R2 profile decision, not a general consequence of missing
snapshots or schema permissiveness. It does not authorize making another
required exact state optional. No subject-workflow checkpoint is introduced.

### D3: materialized values and source-derived arguments

Keep R9's materialized `status["gates"]` entries, R12's policy-derived ordered
required argument list and R17's later authority manifest distinct. Do not imply
that R9 creates a standalone gate-set file or a `status.gates.release_required`
object. The gate-value projection must bind its exact parent status/policy
content; the required-list derivation must bind its exact source/policy inputs.
Neither is evidence of a separately captured original runtime argv.

The pre-materialization status is a distinct version obtained through the exact
pre-attestation member and transfer route. Equal bytes do not by themselves
establish that two different occurrences supplied the same version.

### D5: advisory reference bundle

Require the exact existing `release-grade-reference-run-v0` artifact and its
closed content inventory on the selected successful path. Keep its source
qualification/parity conditions and expected terminal result. An unexpected skip
must not reduce the selected graph. Its advisory classification neither makes
selected evidence optional nor gives the artifact release authority.

### D6: final artifact-binding attestation

Require the exact expected successful A2 occurrence in
`attest_release_grade_artifact_binding`, its source action identity and its exact
subject run/attempt/platform result. This is platform-reported action evidence,
not independent cryptographic verification of the signed receipt. The signed
receipt content remains unavailable and its separate verification unproved.

Do not substitute the LlamaGuard attestation for that final binding receipt.
All existing mandatory LlamaGuard bundle, envelope, signature and verifier checks
remain required. An implementation finding a different unsupported mandatory
relationship must stop for an explicit decision, not invent another gap rule.

### Complete review-role obligations

The following table accounts for all R1 roles under the R2 target. It is not a
list of acquired observations. Every role must survive the migration accounting;
where a role is represented by a parent-bound projection or a downstream output,
its representation and evidence identity must remain explicit.

| Review role | Evidence obligation |
| --- | --- |
| `state:step5c:advisory-reference-bundle` | `exact_preserved_tree_and_carrier` |
| `state:step5c:artifact-binding-attestation` | `required_action_metadata_with_receipt_gap` |
| `state:step5c:artifact-provenance-binding` | `exact_preserved_content` |
| `state:step5c:complete-release-grade-reference-package` | `exact_preserved_archive` |
| `state:step5c:compute-binding-report` | `checked_downstream_derivation` |
| `state:step5c:external-signer-policy` | `exact_source_content` |
| `state:step5c:final-status` | `exact_preserved_content` |
| `state:step5c:final-status-summary` | `exact_preserved_content` |
| `state:step5c:folded-non-active-candidate-status` | `checked_downstream_derivation` |
| `state:step5c:gate-policy` | `exact_source_content` |
| `state:step5c:gate-registry` | `exact_source_content` |
| `state:step5c:llamaguard-attestation-bundle` | `exact_preserved_content` |
| `state:step5c:llamaguard-attestation-envelope` | `exact_preserved_content` |
| `state:step5c:llamaguard-attestation-verifier` | `exact_preserved_content` |
| `state:step5c:llamaguard-dataset` | `exact_source_content` |
| `state:step5c:llamaguard-evaluator-manifest` | `exact_preserved_content` |
| `state:step5c:llamaguard-input:benign_factual_response` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-input:credential_theft_refusal` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-input:hate_content_refusal` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-input:private_address_refusal` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-input:self_harm_support` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-input:violent_harm_refusal` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-output:benign_factual_response` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-output:credential_theft_refusal` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-output:hate_content_refusal` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-output:private_address_refusal` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-output:self_harm_support` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-output:violent_harm_refusal` | `checked_controlled_case_derivation` |
| `state:step5c:llamaguard-raw-evidence` | `exact_preserved_content` |
| `state:step5c:llamaguard-summary` | `exact_preserved_content` |
| `state:step5c:materialized-release-required-gate-set` | `checked_status_policy_projection` |
| `state:step5c:package-completeness-report` | `exact_preserved_archive` |
| `state:step5c:package-verification-report` | `exact_preserved_archive` |
| `state:step5c:planned-observed-relation` | `checked_downstream_derivation` |
| `state:step5c:pre-attestation-pulse-artifacts` | `exact_preserved_archive` |
| `state:step5c:quality-ledger-final` | `exact_preserved_content` |
| `state:step5c:quality-ledger-pre-authority` | `required_explicit_content_gap` |
| `state:step5c:recorded-candidate-index` | `exact_preserved_content` |
| `state:step5c:recorded-release-evidence-verifier` | `exact_preserved_content` |
| `state:step5c:release-authority-audit-bundle` | `exact_preserved_tree` |
| `state:step5c:release-authority-manifest` | `exact_preserved_content` |
| `state:step5c:release-decision` | `exact_preserved_content` |
| `state:step5c:release-decision-ledger-section` | `exact_preserved_content` |
| `state:step5c:release-decision-report` | `exact_preserved_content` |
| `state:step5c:release-evidence-input-manifest` | `exact_preserved_content` |
| `state:step5c:release-grade-junit` | `exact_preserved_content` |
| `state:step5c:release-grade-sarif` | `exact_preserved_content` |
| `state:step5c:required-gate-evidence` | `exact_preserved_content` |
| `state:step5c:runtime-observation-diagnostic` | `checked_downstream_derivation` |
| `state:step5c:runtime-observation-packet` | `checked_downstream_derivation` |
| `state:step5c:self-contained-evidence-floor` | `exact_preserved_content` |
| `state:step5c:status-baseline` | `exact_preserved_content` |
| `state:step5c:step3f-current-run-carrier` | `exact_provider_content` |
| `state:step5c:step3f-current-run-expectation` | `exact_provider_content` |
| `state:step5c:step3f-subject-input-packet` | `exact_provider_content` |
| `state:step5c:threshold-policy` | `exact_source_content` |
| `state:step5c:workflow-source` | `exact_source_content` |
| `state:step5c:pre-materialization-status` | `exact_preserved_content` |
| `state:step5c:recorded-release-candidate-envelopes` | `exact_preserved_tree` |
| `state:step5c:package-digest-inventory` | `exact_preserved_content` |
| `state:step5c:package-run-metadata` | `exact_preserved_content` |
| `state:step5c:effective-required-argument-list` | `checked_source_argv_derivation_with_runtime_receipt_gap` |

## Artifact boundary

Preserve the complete subject artifact metadata listing. The replacement
acquisition profile requires these six exact subject archives, each selected
within the exact subject run and attempt 1:

| Selected role | Expected artifact name |
| --- | --- |
| Complete release-grade package | `complete-release-grade-reference-package-<subject_run_id>-1` |
| Package completeness report | `release-grade-package-completeness-<subject_run_id>-1` |
| Package verification report | `release-grade-reference-package-verification-<subject_run_id>-1` |
| Recorded release-grade path | `release-grade-recorded-path-<subject_run_id>-1` |
| Pre-attestation subject artifacts | `pulse-pre-attestation-<subject_run_id>-1` |
| Advisory reference bundle | `release-grade-reference-run-v0` |

The exact Step 3F provider artifact remains a separate seventh acquisition input:

```text
pulsemech-compute-current-run-export-candidate-<subject_run_id>-1
```

Select that artifact from the exact provider run returned by its own dispatch
response, not from the subject run or a latest-name search. Step 3F continues to
preserve and bind the original complete package, structural completeness report
and independent package-verification report plus its existing derived inputs.
Do not change Step 3F to pretend that it already preserves the three additional
subject archives. Step 5C acquires those through their existing subject uploads.

For every selected archive verify ID, name, source run and attempt, source
revision, created/expiry time, expired state, size, GitHub SHA-256, downloaded
SHA-256 and byte count. Artifact names alone never establish identity, including
for the advisory artifact whose name does not embed a run ID.

Bind inner members and trees separately from the outer ZIP digest. Derive member
selectors from reviewed upload roots and package-copy behavior; do not copy a
repository-relative filename into a ZIP selector without checking the mapping.
Missing, added, unsafe, duplicate or conflicting required members reject.
The package digest inventory and run metadata are distinct mandatory integrity
and subject-identity inputs, not aliases for the outer archive digest.

Apply cross-copy equality only to copies of the same declared state version.
Before/after versions may intentionally differ; a later copy cannot stand in for
a missing earlier state. Content identity does not by itself prove the original
producer or downstream consumer occurrence.

Preserve the existing finite budgets and no-replacement outputs. Exceeding a
budget rejects acquisition; it does not permit skipping an archive, silently
raising a limit or relaxing the member inventory. Expired, missing, renamed,
cross-run, ambiguous or digest-mismatched selected evidence rejects.
Upload success alone is not semantic validity.

## External operations

The plan identifies explicit GitHub dispatch, run/job/artifact retrieval,
artifact upload/download, checkout, setup-python, attestation and attestation
verification boundaries, plus package installation and Hugging Face model
revision/file acquisition boundaries.

The two dispatch calls belong to the supervisor, not the subject.

Subject-side operations use the strongest supported state:

```text
exact digest
metadata only
not recorded
```

No record is not proof of no call. Package-manager requests, action-internal
calls, DNS, transport paths and provider internals remain explicit gaps unless
separate evidence supports them. Authorization material, cookies and secrets
are never included.

## Controlled model inference

The exact checked-in dataset fixes six case occurrences before dispatch:

```text
benign_factual_response
violent_harm_refusal
credential_theft_refusal
private_address_refusal
self_harm_support
hate_content_refusal
```

Each inference binds the case ID, input/output state digests, model ID and exact
revision, runtime package identities, generation parameters, token counts,
parsed label/category set, response-metadata digest and parent step.

Step 5C JSON does not copy raw prompt text or raw model output. The existing
controlled source artifact may remain an opaque exact preservation input but is
not expanded into Step 5C logs or JSON.

Per-case start/completion time remains partial unless directly recorded. Token
counts are inference-usage evidence, not complete resource measurement.

## Timing and order

The packet distinguishes GitHub platform, tool-recorded, provider-reported,
derived and unknown time. Its cross-source clock state is:

```text
not_verified
```

Exact order requires source order, `needs`, same-source platform order, exact
producer-consumer state identity or another predeclared structural dependency.
Different clock domains do not establish order by timestamp alone. Estimated
duration is never represented as exact.

### Acquisition interval and post-run collection interval

These are distinct intervals; a subject dispatch timestamp is not a post-run
collection start, and a provider run's `updated_at` is not the end of downloading
its artifact.

The acquisition tool preserves one closed, canonical observer record at
`control/collection-timing.json`. Its schema identifier is
`pulsemech_compute_whole_runtime_observation_collection_timing_v0`.
`acquisition-index.json.collection_timing` binds its exact member name, SHA-256
and byte count. Both capture construction and the independent verifier require
this record; missing evidence has no inferred-time or legacy fallback.

The record binds repository, reviewed source commit, acquisition ID, collector
run key, exact acquisition-tool source digest, subject/provider run IDs and
attempt 1, `record_status`, `clock_source = observer_utc`,
`cross_source_clock_status = not_verified`, and the unchanged authority boundary.
Its closed `anchors` list binds the exact original subject/provider dispatch
receipts, terminal run-response bodies and selected Step 3F provider archive.
No raw HTTP header, request body, prompt or model response is added to it.

The recorded UTC samples are:

- `subject_terminal_requested_utc` / `subject_terminal_received_utc`: the HTTP
  exchange that returned the retained, validated terminal subject response.
- `collection_started_utc`: sampled after that response has been preserved and
  before the first subject job-metadata collection request.
- `provider_terminal_requested_utc` / `provider_terminal_received_utc`: the
  exchange returning the retained terminal provider response.
- `final_download_started_utc` / `collection_completed_utc`: sampled immediately
  before and after the selected provider-archive download call. The latter is
  not copied from a platform run-completion field.

The required order is subject dispatch request/receipt, terminal subject
request/receipt, collection start, provider dispatch request/receipt, terminal
provider request/receipt, final download start and collection completion.
Nondecreasing order permits equal second-resolution samples. Both retained run
summaries must agree with their original response bodies; their created,
started and updated times must be ordered and not exceed the corresponding
terminal receipt time. Inconsistent clocks fail closed; they are not shifted,
clamped or relabelled as verified cross-source clock synchronization.

The outer `capture_identity.capture_started_utc` remains the original subject
**dispatch request** time. `capture_completed_utc` and the derived
`manifest_created_utc` use the recorded collection-completion anchor. This outer
interval covers subject dispatch through the final selected provider download,
not prelaunch preparation or the later capture-packaging/verification process.
The manifest timestamp is a deterministic derivation anchor, not a measurement
of the time at which replay runs.

For an **observed** `post_run_platform_export` runtime packet,
`observation_boundary.capture_started_utc` instead uses the preserved
`collection_started_utc`; its end and `packet_created_utc` use
`collection_completed_utc`. Historical subject events precede collection; state
observation timestamps remain within the collection interval. The independent
verifier re-derives these bindings both on direct packet construction and before
its final verification record. A generic-valid but freely shifted window is
not sufficient.

The unchanged generic **example** mode requires synthetic subject timestamps
inside its example interval. It therefore retains the outer acquisition start,
while using the same recorded end. Tests exercise the observed branch from
observed-mode preparation and acquisition with an in-memory transport and
scripted clock; these are synthetic test inputs, not hosted observations.

Timing records are trusted-observer evidence bound to preserved inputs, not
cryptographic clock attestations or a complete API-request trace. Rehashing a
container does not permit an anchor substitution; a compromised trusted observer
or a coordinated forgery of all original inputs is still outside the declared
trust guarantee. Verification and reconstruction never use the present-day clock
to repair or reinterpret these recorded times. This timing correction does not
activate R2, complete missing state/read evidence or remove
`declared_state_evidence_incomplete`.

## Generic runtime packet

Step 5C derives one unchanged-v0 runtime packet:

```text
record_status: observed
packet_scope: subject_run
collection_mode: post_run_platform_export
packet_sequence: 0
previous_packet_sha256: null
```

Expected counts are:

```text
subject workflow jobs: 8
subject declared steps: 145
subject execution records: 153
collector execution records: 1
total execution records: 154
model inference records: 6
resource measurement records: 0
```

All records bind:

```text
GITHUB_RUN_ID=<exact subject run ID>
|GITHUB_RUN_ATTEMPT=1
|GITHUB_WORKFLOW=PULSE CI
```

The collector remains outside subject totals and does not mutate subject
artifacts.

The generic runtime schema and validator remain unchanged. Because resource
axes are unavailable and runtime internals remain explicitly excluded, generic
`coverage_status` stays `partial`. Empty resource arrays mean unavailable, not
measured zero.

## Separate Step 5C evidence contract

The outer Step 5C schema continues to distinguish:

```text
prelaunch_plan
dispatch_receipt
capture_manifest
verification_record
```

The replacement schema and tools must bind the evidence-profile identity through
the source-bound plan, preparation, capture and final verification records.
Every record that asserts a profile identity must agree with the expected profile
fixed by the reviewed source. A carrier must not choose its own weaker policy.
Dispatch records remain bound to their exact plan, source and request/response
context; the coordinated implementation must check that identity chain rather
than infer compatibility from the workflow topology name alone.

Missing, stale, unknown and mixed evidence profiles reject. Hash recomputation
is not permission to change requiredness, evidence strength or the acceptance
rules. Do not silently upgrade or reinterpret a legacy generated plan.

The contract binds the exact plan, both dispatch receipts, raw run/job/artifact
responses, all selected artifact bytes, Step 3F output, unchanged generic runtime
packet, real existing-core derived outputs and both reconstructions.

The outer profile keeps these axes distinct:

```text
I — acquisition and packet integrity: complete, if independently verified
E — declared post-run profile extent: complete, if independently verified
R — whole-runtime relational coverage: partial
C — wider fixed-source/runtime comparison: false
M — resource coverage: unavailable
```

I/E completion must name `pulsemech_step5c_post_run_state_evidence_v1` and retain
the explicit pre-state, final signed-receipt and original-runtime-read gaps.
It never changes generic `coverage_status` to `complete`, proves the stronger
legacy all-exact mapping, or closes R/C.

## Carriers

The prepared carrier contains the validated plan, plan diagnostic, exact source
inventory and bytes, selected dispatch inputs and expected plan digest.

The capture carrier contains both dispatch requests/responses, subject and
provider run responses, paginated job/artifact responses, exact downloaded
provider envelope and a self-closing capture manifest. It contains no verifier
verdict.

Each deterministic reconstruction contains the generic runtime packet and
diagnostic, compute-binding report and diagnostic, planned-observed relation and
diagnostic, candidate-materializer report, folded non-active status and
reconstruction inventory.

The final reference capsule contains exactly:

```text
prepared.zip
capture.zip
expected_context.json
expected_plan.sha256
reconstruction-1.zip
reconstruction-2.zip
verification_record_v0.json
SHA256SUMS
```

`SHA256SUMS` lists the other seven members in filename order and not itself. The
two reconstruction ZIP payloads must be byte-identical.

All ZIPs are `ZIP_STORED`, lexicographically ordered, timestamped
`1980-01-01 00:00:00`, fixed-mode regular files with no directory entries,
links, encryption, comments, extra fields or duplicate names.

JSON is UTF-8 without BOM, duplicate-key and non-finite-number rejecting,
NFC-normalized, sorted-key, two-space-indented and final-LF terminated.

Verification never extracts an archive. Unsafe names, traversal, absolute paths,
backslashes, NULs, unsupported compression, CRC failures and size violations
are rejected.

## Independent verification and reconstruction

The plan checker does not import the plan builder. The Step 5C checker does not
import the acquisition, capture or plan-builder implementation.

It independently verifies source objects, plan reconstruction, dispatch
receipts, subject/provider identity, jobs and steps, conditions and skips,
lifecycle exclusion, artifacts, Step 3F binding, states, external visibility,
six inferences, privacy, collector separation, runtime-packet validity,
existing-core outputs, authority boundary and carrier closure.

A self-declared carrier proves internal consistency only. Original acquisition
acceptance also requires the exact GitHub reference-workflow run and its external
workflow identity to be reviewed.

Reconstruction uses one fixed prepared carrier and one fixed capture carrier. It
does not dispatch workflows, repeat model inference, invent observations,
normalize raw bytes, use the current clock, use randomness or depend on ambient
environment values.

Two separate processes reconstruct all derived bytes. Any mismatch fails the
reference.

## Terminal closure

Under `pulsemech_step5c_post_run_state_evidence_v1`, I/E completion requires all
of the following together:

- The independently source-validated plan and expected evidence profile are fixed
  before dispatch, with no stale or mixed-profile record accepted.
- Exact subject and provider dispatch identities are bound; both attempt-1 runs
  complete successfully at the expected source, ref, inputs and workflow.
- All eight jobs, 145 instantiated source-declared steps and six inference
  occurrences satisfy their predeclared results and conditions; no required
  occurrence is missing, duplicated, conflicting or replaced by lifecycle data.
- All six selected subject archives and the exact provider artifact are acquired
  and verified, including required member/tree/version and cross-copy bindings.
- Every mandatory role is accounted for and meets its explicit content,
  occurrence, derivation or specifically reviewed gap obligation. Required exact
  evidence does not fall back to unavailable, metadata-only or planned values.
- The D1 pre-R18 version and D6 signed receipt remain explicit, non-proven gaps;
  A2 action metadata is still required. R9 projections and R12 source-derived
  arguments remain distinct from original-runtime receipts.
- Collector exclusion, non-mutation, privacy and non-authority rules hold; the
  unchanged runtime validator and real existing-core validators accept the
  appropriate inputs and outputs.
- Two separate full reconstructions from the same exact preserved inputs produce
  identical derived bytes, with no success stubs or recursive packet hashes.

These are a conjunction of obligations, not a rule to accept any schema-valid
record. Workflow success, a final marker, an empty missing list, or agreement
between duplicated mapping tables cannot substitute for them.

Missing or unknown required evidence, cancellation, timeout, launch failure,
cross-run substitution, incomplete pagination/artifacts, a changed requirement
or unsupported evidence-strength promotion prevents I/E completion. Only the
named profile's expressly reviewed gaps are permitted; their stronger claims
remain open and must be retained in every completion statement.

This contract amendment alone implements none of these acceptance checks. The
current implementation cannot claim this profile until the coordinated mapping,
schema, acquisition, capture, verifier and regression work passes its review.

## Fail-closed publication

At minimum the implementation rejects source, plan, input, dispatch, run,
attempt, job, step, condition, lifecycle, action, command, authority-source,
artifact, provider, inference, model, privacy, collector, mutation, resource,
coverage, output-path, reconstruction and authority-boundary mismatches.

No failed acquisition publishes a closed reference carrier.

Publication is external to the source repository and occurs only to an absent
destination. Existing output is never overwritten, truncated, renamed away or
deleted. A no-replacement primitive is required; unsupported filesystems fail
without a mutable fallback.

## Existing-core integration

The exact Step 3F packet/carrier and Step 5C runtime packet flow through:

```text
build_pulsemech_compute_binding_report_from_subject_input_v0.py
→ pulsemech_compute_binding_analyzer_core_v0.py
→ check_pulsemech_compute_binding_report_v0.py
→ build_pulsemech_compute_planned_observed_relation_v0.py
→ check_pulsemech_compute_planned_observed_relation_v0.py
→ fold_pulsemech_compute_planned_observed_relation_into_status_v0.py
```

No second analyzer, report implementation, relation engine or candidate
derivation is introduced. The report preserves exact subject identity, collector
separation, partial generic coverage, unavailable resources and actual unresolved
relations.

An all-true candidate is not required. Step 5C output is not an active policy
input.

```text
authority_binding_complete: false
decision_closure_complete: false
```

## Privacy and trust

Step 5C JSON, diagnostics, summaries and logs exclude secrets, authorization
headers, tokens, cookies, raw environment, raw request/response bodies, raw
prompt text, raw model output, uncontrolled command strings and private or
arbitrary user content.

```text
opaque_controlled_fixture_payloads_present: true
step5c_json_exposes_raw_prompt_text: false
step5c_json_exposes_raw_model_output: false
private_or_arbitrary_user_prompt_admitted: false
```

The trusted boundary includes the reviewed supervisor, plan builder, independent
plan checker, acquisition/capture tools, independent Step 5C checker, selected
CPython runtime, hosted runner, host kernel, GitHub control plane and existing
PULSE CI and Step 3F components.

It does not prove correctness against a compromised privileged host, runner,
interpreter, recorder, GitHub control plane or provider internals. Independent
reconstruction proves deterministic derivation from preserved inputs, not a
repeat of the original execution.

## Tests and handoffs

Permanent tests use `record_status: example`, deterministic mocked API responses
and bounded local carriers. They do not dispatch live workflows and are not
observed Step 5C evidence.

Permanent replacement regressions must additionally cover source-grounded
locator/consumer/version reconstruction, common-mode errors in both mapper and
checker, all role obligations, missing/stale/mixed profile rejection, unauthorized
requirement weakening, all six subject archive selectors, closed inner-member
intake, before/after substitution, and the precise D1/D6 non-proven gaps.

The full successful offline case must execute the real existing core through
both independent reconstructions. A synthetic fixture remains synthetic even
when valid; it does not replace owner-authorized live acquisition. Register the
permanent aggregate in CI with the connected manifest-count updates before
implementation acceptance. Ordinary smoke success is not proof that an
unregistered aggregate was executed.

Keep the handoffs distinct:

```text
R1 source reconciliation
→ explicit R2 evidence-profile decision
→ source-grounded replacement mapping
→ coordinated contract/schema/implementation
→ permanent regressions
→ implementation review and merge
→ reviewed owner dispatch
→ exact acquisition
→ independent validation and two reconstructions
→ preservation
→ Step 5C acceptance
→ canonical documentation synchronization
```

The implementation PR contains no invented future run, job, artifact, time,
size, digest or PASS value. The actual reference is preserved only after a
separate acquisition review.

Step 5C does not modify PULSE CI release semantics, the generic checker,
production policy, active policy sets, gate registry, existing #6066 evidence,
Step 5B evidence, Quality Ledger, Transition Meter, Device Ledger, iPhone code,
v1.3.0 or publication metadata.

Successful accepted Step 5C evidence may establish I and E only within the
declared scope. R and C remain Step 5D work; M remains Step 6 work. It does not
declare complete Step 5, whole-host observation, compute budgeting, deployment
admission, active compute enforcement or Step 7 promotion.

Refs #2879.
Builds on #2870, #2872, #2875, #2876, #2877 and #2878.
