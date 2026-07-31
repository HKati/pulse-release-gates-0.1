# PULSEmech Codex Security Evidence Lane Design v0

## Document state

```yaml
document_id: pulsemech_codex_security_evidence_lane_design_v0
document_type: design
revision: v0
revision_state: private_identity_presence_cleanup_retention_bound
status: design_only
authority_effect: none
gate_effect: none
policy_effect: none
schema_effect: none
ci_effect: none
release_effect: none
raw_public_artifact_effect: forbidden
private_intake_report_effect: required
private_lifecycle_carrier_effect: required
public_summary_effect: sanitized_projection_only
public_summary_authority_effect: none
```

This document defines a future PULSEmech evidence lane for importing,
verifying, privately retaining or deleting, sanitizing, and optionally
materializing completed Codex Security scan evidence.

This document does not:

- run Codex Security;
- add a GitHub Actions workflow;
- add schemas;
- add tools;
- add or activate gates;
- change `status.json`;
- change `check_gates.py`;
- modify any active required gate set;
- make Codex Security release-required;
- permit Codex Security to authorize a release;
- accept a report, SARIF file, command exit code, workflow conclusion, or
  dashboard state as release evidence by itself;
- permit raw security findings to be uploaded as a normal artifact of this
  public repository;
- permit a verifier-issued intake report to be uploaded as a public artifact;
- permit a private lifecycle carrier to be uploaded as a public artifact;
- permit a public normalized summary to create release state by itself;
- claim later replay when the private authority carriers were not retained.

Implementation and activation require separate pull requests.

---

## 1. Purpose

Codex Security can inspect a repository and produce structured security
findings together with records of:

- the reviewed target;
- the executed scan recipe;
- the achieved coverage;
- the findings produced by that observation;
- scan-local evidence referenced by canonical documents;
- readable or machine projections generated beside the canonical documents;
- private runtime and workbench state created during the scan.

PULSEmech can use the security observation only after the authority-relevant
part of that output becomes a verified, subject-bound evidence carrier.

The intended relation is:

```text
Codex Security
produces a security observation and controlled producer output

protected PULSEmech control plane
verifies the subject, producer, run, recipe, canonical documents, reference
closure, coverage, findings policy, evidence presence at verification, raw
output lifecycle, and retained private-carrier set

PULSEmech release authority
remains the only mechanism that may produce an enforced ALLOW or BLOCK state
```

The lane separates:

```text
security analysis
```

from:

```text
evidence verification
```

from:

```text
confidential-output lifecycle
```

from:

```text
release authority
```

Codex Security is an external evidence producer.

Codex Security is not a PULSEmech release decision engine.

---

## 2. Core authority invariant

The core invariant is:

```text
Codex Security output ≠ release permission
```

A positive Codex Security result cannot authorize release by:

- command completion;
- process exit code;
- absence of reported findings;
- presence of a report;
- presence of SARIF;
- presence of a scan directory;
- presence of an uploaded file;
- a human-readable statement;
- a workflow check name;
- an artifact name;
- a severity threshold configured only inside the scanner;
- a mutable workbench classification;
- an unverified adapter summary;
- an unverified intake report;
- a public summary;
- an unverified retention statement;
- current absence of raw files after deletion;
- current presence of a privately retained object;
- a storage-provider success message by itself.

A Codex Security observation may participate in release-state evaluation only
through this path:

```text
exact subject revision
→ isolated Codex Security producer
→ controlled producer-output roots
→ completed canonical source documents
→ complete authority-relevant reference closure
→ deterministic authority source-bundle identity
→ protected PULSEmech verifier
→ exact subject, run, producer, recipe, and schema bindings
→ recorded evidence presence at verification
→ complete coverage and deterministic findings-policy evaluation
→ private verifier-issued intake report
→ complete public-identity projection
→ complete machine decision projection
→ confidential producer-output lifecycle action
→ private lifecycle or cleanup carrier
→ private retention completion when replay is claimed
→ trusted sanitized-summary projection
→ private fold-in regeneration and equality check
→ inactive candidate gate set
→ separately approved promotion
→ strict PULSEmech enforcement
```

No earlier element in the path has release authority.

---

## 3. Carrier and surface separation

The lane distinguishes four different surfaces.

### 3.1 Authority source bundle

The authority source bundle contains only the exact files required to verify
the security observation:

```text
canonical source documents
+
producer receipt
+
authority-relevant referenced scan-local evidence
```

Every authority source-bundle entry participates in the deterministic bundle
identity.

### 3.2 Controlled producer-output surface

The controlled producer-output surface contains every confidential output
created by the scan or its wrapper inside declared controlled roots.

It may include:

```text
authority source-bundle files
report.md
SARIF
CSV
scan logs
scan-local temporary files
workbench state
model-generated write-ups
unreferenced projections
producer-wrapper temporary files
private packaging copies
```

A file may belong to the controlled producer-output surface without belonging
to the authority source bundle.

The complete controlled producer-output surface is subject to lifecycle
cleanup.

### 3.3 Private authority carriers

Private authority carriers include:

```text
intake packet
private intake report
indexed-bundle lifecycle receipt
pre-index cleanup receipt
private raw-source package metadata
private control-package metadata
private retention completion receipt
```

They must not be published through normal public-repository Actions artifacts.

### 3.4 Public sanitized projection

The public sanitized projection is:

```text
codex_security_summary_v0.json
```

It contains only explicitly permitted non-sensitive fields.

It is a projection.

It is not release authority.

---

## 4. Scope

### 4.1 Included in the v0 design

This design covers:

- an exact Git revision as the scan subject;
- a clean subject checkout;
- a separate protected trusted control-plane checkout;
- a completed Codex Security canonical scan bundle;
- complete enumeration of supported authority-relevant local references;
- exact binding of every authority source-bundle component;
- complete lifecycle handling of indexed and unindexed confidential outputs;
- a separately recorded producer receipt;
- immutable component digests;
- a deterministic authority source-bundle identity;
- trusted per-carrier size limits;
- trusted authority-bundle total-size and entry-count limits;
- duplicate-key rejection for every JSON carrier;
- duplicate-mapping-key rejection for trusted YAML;
- a PULSEmech intake packet;
- offline upstream schema validation;
- source-bundle integrity validation;
- protected verifier and policy identity validation;
- upstream schema-snapshot identity validation;
- current-workflow-run binding;
- exact Git revision binding;
- declared scan-recipe binding;
- evidence presence recorded at verification;
- coverage completeness validation;
- deterministic finding classification;
- deterministic severity-policy evaluation;
- a private machine-only intake report;
- complete public-identity and decision projections inside the private report;
- an indexed-bundle lifecycle receipt;
- a separate pre-index cleanup receipt;
- a two-package private retention model;
- an independently verifiable private retention completion receipt;
- a public normalized summary built only after lifecycle completion;
- a summary bound to its private report and lifecycle carriers;
- fold-in regeneration from private authority carriers;
- an inactive candidate gate set;
- negative fixtures and replay proof;
- a later, separate promotion boundary.

### 4.2 Excluded from the first implementation

The following are excluded from the first implementation:

- automatic scanning of untrusted pull-request code with a secret;
- scanning arbitrary external repositories;
- automatic application of generated patches;
- automatic commits;
- automatic pull requests;
- automatic merge;
- scanner-controlled release decisions;
- human workbench triage as release evidence;
- mutable false-positive state as release evidence;
- `git_worktree` targets in a release-capable lane;
- `git_diff` targets in a release-capable lane;
- `directory_snapshot` targets in a release-capable lane;
- cross-scan lifecycle classification as authority evidence;
- organization-wide bulk scanning;
- public publication of raw security findings;
- public publication of verifier-issued intake reports;
- public publication of private lifecycle carriers;
- raw findings in normal public-repository Actions artifacts;
- public summaries acting as release-authority inputs;
- replay claims for ephemeral-only runs;
- release-gate activation.

These functions require separate designs and separate authority boundaries.

---

## 5. Initial operating profiles

### 5.1 Shared scan profile

```yaml
trigger: workflow_dispatch

subject:
  target_kind: git_revision
  target_revision: exact_full_commit_sha
  repository_state: clean
  target_scope: repository

scan:
  execution_mode: standard
  expected_coverage_mode: repository
  inventory_strategy: repository

control_plane:
  source: protected_exact_revision
  checkout: separate_from_subject
  subject_may_select_control_plane: false

producer:
  location: isolated_ephemeral_job
  output_location: controlled_roots_outside_both_worktrees
  patch_command_allowed: false

public_results:
  normalized_summary_allowed: true
  normalized_summary_is_authority: false
  free_form_text_allowed: false

authority:
  mode: candidate_advisory
  release_effect: none

findings:
  blocking_severities:
    - critical
    - high
  non_blocking_recorded_severities:
    - medium
    - low
    - informational
  missing_severity: unverified
  malformed_severity: unverified
  unsupported_severity: unverified
  triage_override_supported: false
```

### 5.2 Ephemeral-delete profile

```yaml
raw_lifecycle_mode: ephemeral_delete
public_raw_artifact_allowed: false
private_replay_claim_allowed: false
later_release_fold_in_allowed: false
same_run_candidate_evaluation_allowed: true
```

The ephemeral-delete profile may support same-run candidate evaluation while
the private intake report and cleanup carrier still exist on the isolated
runner.

After those private carriers are deleted, the public summary remains advisory
display only.

### 5.3 Access-controlled private-storage profile

```yaml
raw_lifecycle_mode: access_controlled_private_storage
public_raw_artifact_allowed: false
private_replay_claim_allowed: true
later_release_fold_in_allowed: true
retention_set_commit_required: true
```

The private-storage profile is required for:

- fixed-source replay proof;
- later independent verification;
- release-capable fold-in;
- promotion evidence.

The exact package version, plugin version, runtime version, model, reasoning
effort, expected paths, trusted verifier identity, trusted policy identity,
upstream schema snapshot, carrier limits, authority-bundle total-size limit,
and authority-bundle entry-count limit must come from the protected candidate
policy.

They must not be inferred from producer output.

---

## 6. Canonical Codex Security source contract

A completed Codex Security scan produces three canonical machine-readable
documents:

```text
scan-manifest.json
findings.json
coverage.json
```

The initial PULSEmech intake must use these three documents as its primary
semantic source.

The following outputs are projections and must not be treated as primary
authority evidence:

```text
report.md
SARIF
CSV
console output
workflow log
human summary
dashboard state
```

The verifier must not recover missing semantic data by parsing `report.md`.

The verifier must not recover missing semantic data by parsing SARIF.

The verifier must not interpret the absence of text in a readable report as the
absence of a finding.

### 6.1 `scan-manifest.json`

The manifest is expected to carry the completed scan identity, including:

- document type;
- schema version;
- scan identifier;
- producer name;
- producer version;
- completed status;
- start time;
- completion time;
- seal time;
- target kind;
- target identity;
- target revision or snapshot identity;
- included paths;
- excluded paths;
- reference to `findings.json`;
- reference to `coverage.json`;
- recorded artifact digests.

The PULSEmech verifier must calculate the digest of `scan-manifest.json`
independently.

The verifier must not expect a manifest to contain a self-digest.

### 6.2 `findings.json`

The findings document is expected to carry:

- document type;
- schema version;
- scan identifier;
- finding identifiers;
- occurrence identifiers;
- rule identifiers;
- semantic anchors;
- fingerprints;
- severity;
- confidence;
- taxonomy;
- affected locations;
- remediation data;
- validation data when present;
- attack-path data when present;
- provenance;
- local evidence references when present.

PULSEmech must evaluate the canonical finding records.

A rendered finding table is not a substitute for the canonical records.

### 6.3 `coverage.json`

The coverage document is expected to carry:

- document type;
- schema version;
- scan identifier;
- requested coverage mode;
- coverage completeness;
- inventory strategy;
- included paths;
- excluded paths;
- reviewed surfaces;
- explicit exclusions;
- deferred units;
- local receipt references when present.

Coverage remains a separate decision dimension.

This distinction is mandatory:

```text
no finding was observed
```

is not equivalent to:

```text
the required surface was completely scanned and no blocking finding was found
```

### 6.4 Execution mode and coverage mode

The scanner execution mode and coverage mode are different fields.

The initial execution mode is:

```text
standard
```

The expected coverage mode is:

```text
repository
```

The expected inventory strategy is:

```text
repository
```

The required relations are:

```text
producer receipt requested_execution_mode
==
candidate policy execution_mode
==
standard
```

```text
coverage.mode
==
candidate policy expected_coverage_mode
==
repository
```

```text
coverage.inventoryStrategy
==
candidate policy inventory_strategy
==
repository
```

---

## 7. Trusted control-plane and subject separation

The subject under review and the code that verifies the subject must not share
the same trust role.

The lane requires two separate checkouts:

```text
trusted control-plane checkout
subject checkout
```

### 7.1 Trusted control-plane checkout

The trusted control-plane checkout supplies:

- the workflow implementation;
- the candidate policy;
- the intake-packet builder;
- the intake verifier;
- the reference-closure extractor;
- the source-bundle index builder;
- the lifecycle controller;
- the cleanup controller;
- the summary builder;
- the projection checker;
- the vendored upstream schema snapshot;
- activation-guard checks.

It must be resolved to an exact protected revision.

The subject cannot select or modify this revision.

The control-plane revision must be established before any subject-produced
carrier is interpreted.

### 7.2 Subject checkout

The subject checkout supplies:

- the repository content to be scanned;
- the exact subject Git revision;
- no trusted verifier code;
- no trusted policy;
- no trusted schema snapshot;
- no trusted expected digest;
- no trusted reference-closure rules;
- no trusted lifecycle logic.

The subject checkout is data from the verifier's perspective.

### 7.3 Same repository, separate roles

The trusted control plane and the subject may have the same repository
identity.

They must still use:

- distinct checkout roots;
- independently resolved exact revisions;
- distinct trust roles.

A subject revision must not be able to replace:

- the verifier;
- the policy;
- the schema snapshot;
- the reference extractor;
- the lifecycle controller;
- their expected digests;
- the protected workflow revision.

### 7.4 Executable-source boundary

Trusted tools must be invoked by absolute path from the trusted control-plane
checkout.

Trusted tools must not import Python modules from the subject checkout.

The workflow must sanitize executable lookup and module-loading variables,
including applicable forms of:

```text
PATH
PYTHONPATH
PYTHONHOME
GIT_DIR
GIT_WORK_TREE
GIT_INDEX_FILE
GIT_OBJECT_DIRECTORY
GIT_ALTERNATE_OBJECT_DIRECTORIES
```

The subject checkout must not become an executable-code source for the
verification or lifecycle phase.

---

## 8. Controlled roots and output confinement

Before the scan begins, the protected workflow must create exact controlled
roots under runner-local temporary storage.

Illustrative layout:

```text
${RUNNER_TEMP}/pulsemech-codex-security/
├── trusted-control-plane/
├── subject/
├── controlled/
│   ├── codex-results/
│   ├── codex-state/
│   ├── producer-receipts/
│   ├── authority-staging/
│   ├── raw-package-staging/
│   └── private-transfer-staging/
├── private-authority/
└── public-summary/
```

### 8.1 Controlled confidential roots

The following are controlled confidential roots:

```text
controlled/codex-results
controlled/codex-state
controlled/producer-receipts
controlled/authority-staging
controlled/raw-package-staging
controlled/private-transfer-staging
```

Every Codex Security result, projection, temporary file, state file, and raw
packaging copy must remain inside these roots.

### 8.2 Private-authority root

The private-authority root may contain:

```text
intake packet
private intake report
indexed-bundle lifecycle receipt
pre-index cleanup receipt
private control-package staging
private retention completion receipt
```

It must not enter a public artifact.

### 8.3 Public-summary root

The public-summary root may contain only:

```text
codex_security_summary_v0.json
detached digest or signature
```

### 8.4 Root integrity

Before use, every controlled root must be:

- created by the trusted workflow;
- located below the trusted runner-temporary parent;
- a real directory;
- non-symlinked;
- outside both Git worktrees;
- initially empty.

A producer output outside the controlled roots is a lane failure.

---

## 9. Trust boundaries

The lane crosses the following trust boundaries:

```text
protected workflow revision
→ trusted control-plane checkout

selected subject revision
→ isolated subject checkout

subject checkout
→ Codex Security runtime

Codex Security runtime
→ controlled producer-output roots

canonical source documents
→ authority-reference closure extraction

authority source closure
→ deterministic source-bundle identity

source bundle
→ trusted PULSEmech intake verifier

verified immutable buffers
→ private identity and decision projections

private intake report
→ controlled-output lifecycle action

completed lifecycle action
→ private lifecycle or cleanup carrier

raw package + private control package
→ private retention-set commit

private report + lifecycle carriers
→ trusted public-summary builder

private authority carriers
→ private fold-in regeneration

regenerated projection
→ inactive candidate gate state
```

Each transition must be explicit.

---

## 10. Threat model

The design must defend against at least the following failures.

### 10.1 Subject substitution

A valid scan bundle may describe:

- a previous commit;
- another branch;
- another repository;
- a dirty worktree;
- a different pull-request head;
- an unrecorded local modification;
- a partial directory snapshot.

A valid bundle for the wrong subject is not valid release evidence.

### 10.2 Stale evidence

A completed scan may be old while the repository has advanced.

The primary freshness binding is:

```text
exact current workflow run
+
exact current subject Git revision
```

### 10.3 Bundle mutation

A canonical document or referenced evidence file may be modified after
finalization.

Every authority source-bundle component must be digest-verified.

### 10.4 Referenced-evidence substitution

A canonical document may reference scan-local evidence.

If that evidence is omitted from the source-bundle identity, it may be:

- replaced;
- removed;
- truncated;
- redirected;
- substituted through a symlink.

Every supported authority-relevant local reference must resolve into the
indexed source-bundle closure.

### 10.5 Unindexed confidential-output survival

Codex Security may produce:

- unreferenced `report.md`;
- SARIF;
- CSV;
- logs;
- write-ups;
- temporary data;
- workbench state.

These files may be excluded from the authority source bundle and still contain
confidential finding information.

Lifecycle success must therefore be based on cleanup of the complete
controlled confidential roots, not only indexed authority paths.

### 10.6 Producer substitution

A different package, plugin, wrapper, model, or runtime may produce a
structurally similar bundle.

Producer identity must be checked against an independent trusted expectation.

### 10.7 Recipe drift

A scan may silently change:

- execution mode;
- target scope;
- coverage mode;
- inventory strategy;
- included paths;
- excluded paths;
- model;
- reasoning effort;
- plugin version;
- package version.

A changed recipe is a different observation process.

### 10.8 Coverage collapse

A scan may complete after reviewing only part of the required surface.

The absence of findings under partial or unknown coverage must fail closed.

### 10.9 Exclusion injection

An attacker or configuration error may exclude a security-sensitive path.

Actual exclusions must exactly match the declared exclusion policy.

### 10.10 Deferred-work collapse

A scan may defer required work while still producing readable output.

Deferred required work must not be converted into a passing result.

### 10.11 Path traversal and symlink substitution

A path may:

- escape an authorized root;
- traverse through `..`;
- use an absolute path;
- use a symlink;
- point to a replaced file;
- point to a non-regular file.

All authority source-bundle paths must remain inside the authorized scan root
and resolve to regular non-symlink files.

Lifecycle deletion must remove symlinks themselves and must never follow them
outside a controlled root.

### 10.12 Duplicate-key ambiguity

Every JSON carrier must reject duplicate object keys before schema validation.

Trusted YAML must reject duplicate mapping keys.

### 10.13 Resource exhaustion

The verifier must enforce trusted limits before reading, hashing, decoding, or
parsing.

The verifier must also enforce:

- maximum authority source-bundle entry count;
- maximum individual referenced-evidence file size;
- maximum total authority source-bundle size.

Untrusted producer output cannot increase these limits.

### 10.14 Control-plane substitution

The subject revision may attempt to replace:

- the verifier;
- the policy;
- the schema snapshot;
- the packet builder;
- the summary builder;
- the reference extractor;
- the lifecycle controller.

Trusted control-plane identity must come from a separately resolved protected
revision.

### 10.15 Schema-snapshot substitution

The policy, packet, private report, and public summary must preserve the exact
reviewed schema-snapshot identity and per-schema digests.

### 10.16 Missing public identities

A summary builder restricted to private carriers cannot construct the public
summary if the private intake report omits:

- subject identity;
- workflow-run identity;
- producer identity;
- policy ID;
- policy version;
- policy digest.

The private report must carry every dynamic identity required by the public
projection.

### 10.17 Evidence-presence collapse after deletion

Successful `ephemeral_delete` removes the raw evidence.

Evidence presence must therefore mean:

```text
verified presence at the time of intake verification
```

It must not mean:

```text
current filesystem existence during later fold-in
```

### 10.18 Pre-index lifecycle contradiction

An intake may fail before a valid source-bundle index or bundle identity
exists.

A lifecycle record must not require non-null identities that could not be
established.

Pre-index failures require a separate cleanup carrier.

### 10.19 Incomplete private retention

A raw source package may be transferred before the lifecycle receipt exists.

A completed replay set must also retain the later private control package that
contains the lifecycle receipt.

Private retention completion must be independently committed after both
packages exist.

### 10.20 Summary substitution

A fabricated public summary may preserve correct report digests while changing:

- verification result;
- finding counts;
- coverage state;
- policy result;
- reason codes;
- lifecycle state.

The fold-in must regenerate the complete projection from private authority
carriers.

### 10.21 Verification-use time gap

The summary builder must not reopen canonical source documents.

Decision values come from the private report constructed from the exact
verified immutable buffers.

### 10.22 Lifecycle-state fabrication

A final public summary must be generated only after the selected lifecycle
action completes and its postconditions pass.

### 10.23 Credential exposure

The producer job must receive only the credentials required for the scan and
declared private storage operation.

### 10.24 Mutable triage substitution

Mutable local workbench triage is not part of the v0 authority carrier.

### 10.25 Raw-finding publication

Raw findings and private carriers must not enter public-repository Actions
artifacts.

---

## 11. End-to-end machines

### 11.1 Indexed ephemeral-delete run

```text
protected control plane
→ exact subject scan
→ controlled producer outputs
→ canonical document validation
→ complete reference closure
→ source-bundle index and identity
→ trusted intake verification
→ private intake report
→ recorded evidence presence at verification
→ complete controlled-root cleanup
→ indexed-bundle lifecycle receipt
→ public sanitized summary
→ optional same-run candidate fold-in
→ private carrier deletion before runner termination
```

Later release-capable fold-in is not available after private carrier deletion.

### 11.2 Indexed private-retention run

```text
protected control plane
→ exact subject scan
→ controlled producer outputs
→ canonical document validation
→ complete reference closure
→ source-bundle index and identity
→ trusted intake verification
→ private intake report
→ private raw-source package
→ raw-source package transfer and verification
→ complete controlled-root cleanup
→ indexed-bundle lifecycle receipt
→ private control package
→ private control-package transfer and verification
→ private retention-set commit
→ private retention completion receipt
→ public sanitized summary
→ later private-carrier fold-in and replay
```

### 11.3 Pre-index failure run

```text
controlled producer outputs
→ intake failure before valid index identity
→ private unverified intake report when report construction remains possible
→ complete controlled-root cleanup
→ pre-index cleanup receipt
→ public sanitized unverified summary
```

A pre-index failure cannot claim:

```text
valid source-bundle identity
private replay package completeness
release-capable evidence
```

If no valid private intake report can be emitted, no public summary is
permitted.

---

## 12. Producer job design

### 12.1 Isolation

The producer must run in a dedicated ephemeral job with:

```yaml
permissions:
  contents: read
```

Every checkout must use:

```yaml
persist-credentials: false
fetch-depth: 0
```

The job must not receive:

- repository write permission;
- package publish permission;
- deployment permission;
- unrelated cloud credentials;
- unrelated signing keys;
- release tokens;
- mutable production credentials.

### 12.2 Same-runner requirement

All raw-data operations must complete on the same ephemeral runner:

```text
run scan
→ enumerate controlled outputs
→ create producer receipt
→ validate canonical documents
→ extract reference closure
→ create source-bundle index when possible
→ verify intake
→ emit private intake report when possible
→ perform lifecycle action
→ emit private lifecycle or cleanup carrier
→ complete private retention when selected
→ build public summary
```

A later public job must never receive raw files or private authority carriers.

### 12.3 Package installation

The implementation must use an exact package version and lock.

A floating install is forbidden:

```text
@openai/codex-security@latest
```

The producer wrapper must record:

- package name;
- package version;
- package-lock digest;
- package integrity when available;
- plugin version;
- Codex runtime version;
- selected model;
- selected reasoning effort;
- Node.js version;
- Python version.

### 12.4 Scan command boundary

The lane records separately:

```text
producer process completion
canonical document completion
reference-closure completion
source-bundle verification
coverage verification
findings-policy result
controlled-output cleanup
private retention completion
```

A process exit code is not a release result.

### 12.5 Forbidden producer commands

The automated lane must not execute:

```text
codex-security patch
codex-security install-hook
automatic fix application
automatic git commit
automatic git push
automatic pull-request creation
```

---

## 13. Producer receipt

The wrapper must produce:

```text
codex_security_producer_receipt_v0.json
```

Conceptual shape:

```yaml
document_type: pulsemech.codex-security-producer-receipt
schema_version: "0.1"

workflow:
  name: string
  repository: string
  run_id: string
  run_attempt: integer
  event_name: string
  ref: string
  workflow_revision: full_commit_sha
  subject_revision: full_commit_sha

producer:
  package_name: "@openai/codex-security"
  package_version: exact_version
  package_lock_sha256: sha256
  package_integrity: string_or_null
  plugin_name: string
  plugin_version: exact_version
  runtime_version: exact_version
  model: exact_model
  reasoning_effort: exact_effort
  node_version: exact_version
  python_version: exact_version

scan:
  requested_target_kind: git_revision
  requested_revision: full_commit_sha
  requested_execution_mode: standard
  requested_target_scope: repository
  requested_include_paths: array
  requested_exclude_paths: array
  started_at: date_time
  completed_at: date_time_or_null
  process_exit_code: integer
  scan_id: string_or_null

outputs:
  controlled_results_root_id: fixed_identifier
  controlled_state_root_id: fixed_identifier
  scan_manifest_path: relative_path_or_null
  findings_path: relative_path_or_null
  coverage_path: relative_path_or_null
```

The receipt must not contain:

- credentials;
- signed URLs;
- absolute runner paths;
- full environment dumps;
- raw finding details;
- arbitrary human prose.

---

## 14. Complete authority source-bundle closure

### 14.1 Required core entries

The authority source bundle must contain:

```text
scan-manifest.json
findings.json
coverage.json
codex_security_producer_receipt_v0.json
```

### 14.2 Referenced-evidence closure

The trusted reference extractor must enumerate every supported local path
reference required for:

- canonical-document validation;
- coverage validation;
- finding validation;
- later independent replay.

The closure may include:

- manifest artifact paths;
- coverage receipt references;
- finding-local evidence paths;
- finding write-up paths;
- other local evidence paths explicitly supported by the reviewed upstream
  contract.

Every authority-relevant reference must resolve to:

```text
a regular non-symlink file
inside the authorized scan root
```

### 14.3 Exact closure rule

The verifier must independently recompute the reference closure.

The recomputed closure must exactly equal the authority source-bundle index
entry set:

```text
required core entries
+
every supported authority-relevant referenced entry
==
indexed authority entry set
```

An omitted referenced file fails closed.

An indexed extra file fails closed in v0.

### 14.4 Readable and unreferenced projections

Readable or machine projections such as:

```text
report.md
SARIF
CSV
logs
write-ups
```

are not added to the authority source bundle merely because they exist.

If a canonical authority-relevant reference points to one of them, that file
must be indexed.

If no authority-relevant reference requires it, the file remains outside the
authority source bundle.

It still remains inside the controlled producer-output surface and must be
removed by the lifecycle action.

---

## 15. Source-bundle index and identity

The wrapper must produce:

```text
codex_security_source_bundle_index_v0.json
```

when a complete index can be established.

### 15.1 Index entry shape

```yaml
path: normalized_posix_relative_path
role: canonical_document_or_producer_receipt_or_referenced_evidence
media_type: string
size_bytes: integer
sha256: lowercase_sha256
```

Optional private review metadata may include:

```yaml
referenced_by:
  - canonical_document_and_field_identifier
```

### 15.2 Path normalization

Every indexed path must:

- be relative;
- use `/` separators;
- contain no empty segment;
- contain no `.` segment;
- contain no `..` segment;
- contain no backslash;
- contain no NUL;
- remain inside the authorized scan root;
- resolve to a regular non-symlink file.

### 15.3 Deterministic ordering

Entries must be sorted by:

```text
normalized path UTF-8 bytes
then role UTF-8 bytes
```

### 15.4 Canonical identity payload

```json
{
  "domain": "pulsemech-codex-security-source-bundle-v1",
  "entries": [
    {
      "path": "normalized/relative/path",
      "role": "canonical_document",
      "media_type": "application/json",
      "size_bytes": 123,
      "sha256": "lowercase-sha256"
    }
  ]
}
```

The payload must be serialized as:

- UTF-8;
- lexicographically ordered object keys;
- no insignificant whitespace;
- deterministic JSON escaping;
- decimal integers without leading zeros;
- entries in required deterministic order.

The source-bundle identity is:

```text
sha256(canonical_identity_payload_bytes)
```

### 15.5 Index self-boundary

The index must not include itself.

Its digest is calculated separately.

### 15.6 Closure record

```yaml
closure:
  required_core_entry_count: integer
  referenced_evidence_entry_count: integer
  total_entry_count: integer
  total_size_bytes: integer
  unresolved_reference_count: 0
  closure_complete: true
```

The verifier must recompute every value.

---

## 16. Controlled producer-output surface

The lifecycle controller must handle the complete controlled producer-output
surface, not only the indexed authority source bundle.

### 16.1 Controlled surface contents

The controlled surface includes every file or directory created under:

```text
controlled/codex-results
controlled/codex-state
controlled/producer-receipts
controlled/authority-staging
controlled/raw-package-staging
controlled/private-transfer-staging
```

This includes:

- indexed authority files;
- unindexed report projections;
- unindexed SARIF or CSV;
- scan logs;
- temporary evidence;
- workbench state;
- abandoned partial files;
- failed package copies.

### 16.2 Authority extraction before cleanup

In private-retention mode, the trusted controller must first construct and
transfer the private raw-source package from verified indexed authority
entries.

After that extraction succeeds, the entire controlled confidential surface
must be cleaned.

### 16.3 Whole-root cleanup

Lifecycle cleanup must:

- reject unexpected controlled-root replacement;
- remove entries without following symlinks outside the root;
- remove all files and subdirectories below each controlled confidential root;
- remove the controlled roots themselves when declared by policy;
- verify that each declared root is absent after cleanup;
- fail if any confidential controlled root remains populated.

Checking only indexed raw paths is insufficient.

### 16.4 Output escape detection

Before lifecycle success, the workflow must also verify that producer output
did not appear in known forbidden locations, including:

- either Git worktree;
- the public-summary root;
- the public artifact staging root;
- the runner home outside declared state paths.

A producer output escape fails closed.

---

## 17. Trusted limits and immutable reads

### 17.1 Initial trusted limits

```yaml
scan_manifest_max_bytes: 16777216
findings_max_bytes: 134217728
coverage_max_bytes: 33554432
producer_receipt_max_bytes: 1048576
source_bundle_index_max_bytes: 4194304
intake_packet_max_bytes: 1048576
intake_report_max_bytes: 8388608
indexed_lifecycle_receipt_max_bytes: 1048576
preindex_cleanup_receipt_max_bytes: 1048576
private_control_package_manifest_max_bytes: 1048576
retention_completion_receipt_max_bytes: 1048576
public_summary_max_bytes: 4194304
source_record_max_bytes: 1048576
individual_schema_max_bytes: 4194304
candidate_policy_max_bytes: 1048576
referenced_evidence_file_max_bytes: 67108864
authority_bundle_total_max_bytes: 536870912
authority_bundle_entry_max_count: 10000
```

### 17.2 Pre-read order

Before reading or hashing a carrier:

```text
1. trusted root resolution
2. path normalization
3. root containment
4. no-follow open or equivalent
5. descriptor metadata
6. regular-file verification
7. trusted size limit
8. non-empty requirement
9. read bytes from the same descriptor
10. calculate digest from those bytes
11. decode those bytes
12. parse those bytes
13. recheck descriptor metadata
14. reject mutation indicators
```

### 17.3 Immutable verifier buffers

The verifier must calculate:

```text
digest
parsed object
identity projection
decision projection
```

from the same immutable byte buffers.

---

## 18. Intake packet

The protected control plane must create:

```text
codex_security_intake_packet_v0.json
```

### 18.1 Required packet fields

```yaml
document_type: pulsemech.codex-security-intake-packet
schema_version: "0.1"
record_status: example_or_observed
packet_scope: example_or_current_run

trusted_control_plane:
  repository_identity: string
  revision: full_commit_sha
  policy_path: repository_relative_path
  policy_sha256: sha256
  verifier_path: repository_relative_path
  verifier_sha256: sha256
  verifier_version: string
  packet_builder_path: repository_relative_path
  packet_builder_sha256: sha256
  reference_extractor_path: repository_relative_path
  reference_extractor_sha256: sha256
  lifecycle_controller_path: repository_relative_path
  lifecycle_controller_sha256: sha256
  summary_builder_path: repository_relative_path
  summary_builder_sha256: sha256
  projection_checker_path: repository_relative_path
  projection_checker_sha256: sha256

schema_snapshot_binding:
  upstream_repository_identity: openai/codex-security
  upstream_revision: full_commit_sha
  source_record_sha256: sha256
  aggregate_snapshot_sha256: sha256
  scan_manifest_schema_sha256: sha256
  findings_schema_sha256: sha256
  coverage_schema_sha256: sha256

subject_expectation:
  repository_identity: string
  target_kind: git_revision
  revision: full_commit_sha

run_expectation:
  workflow_name: string
  workflow_revision: full_commit_sha
  workflow_run_id: string
  workflow_run_attempt: integer
  event_name: workflow_dispatch
  ref: string

producer_expectation:
  package_name: "@openai/codex-security"
  package_version: exact_version
  package_lock_sha256: sha256
  plugin_name: exact_name
  plugin_version: exact_version
  runtime_version: exact_version
  model: exact_model
  reasoning_effort: exact_effort

scan_recipe_expectation:
  execution_mode: standard
  target_scope: repository
  expected_coverage_mode: repository
  inventory_strategy: repository
  include_paths: exact_array
  exclude_paths: exact_array
  required_coverage_completeness: complete
  allowed_explicit_exclusions: exact_array
  deferred_allowed: false
  unresolved_required_surfaces_allowed: false

findings_policy_binding:
  policy_id: string
  policy_version: string
  policy_sha256: sha256

source_bundle_expectation:
  index_path: staged_relative_path
  index_sha256: sha256_or_null
  bundle_identity: sha256_or_null
  expected_entry_count: integer_or_null
  expected_total_size_bytes: integer_or_null

lifecycle_expectation:
  mode: ephemeral_delete_or_access_controlled_private_storage
  public_raw_artifact_allowed: false
  private_carrier_publication_allowed: false
```

### 18.2 Expected-value independence

Expected values must not be derived from:

- canonical source documents;
- producer receipt;
- source-bundle index;
- report text;
- command output;
- subject-checkout tools or policies.

### 18.3 Nullable bundle expectation

The packet may record null bundle identities only when index construction
failed before a valid source-bundle identity could be established.

Null bundle identity does not mean a valid empty bundle.

It requires an unverified report result and the pre-index cleanup path.

---

## 19. Upstream schema snapshot

PULSEmech verification must use a vendored reviewed snapshot.

Illustrative layout:

```text
vendor/openai/codex-security/
└── <upstream-commit>/
    ├── LICENSE
    ├── SOURCE.json
    └── schemas/
        ├── scan-manifest.schema.json
        ├── findings.schema.json
        └── coverage.schema.json
```

The aggregate identity is:

```text
sha256(
  "pulsemech-codex-security-schema-snapshot-v0\n"
  + upstream_revision + "\n"
  + source_record_sha256 + "\n"
  + scan_manifest_schema_sha256 + "\n"
  + findings_schema_sha256 + "\n"
  + coverage_schema_sha256 + "\n"
)
```

The schema identity must be preserved through:

```text
candidate policy
→ intake packet
→ private intake report
→ public summary
```

---

## 20. Intake verifier

The proposed verifier is:

```text
tools/check_codex_security_intake_packet_v0.py
```

It must be offline and deterministic.

### 20.1 Filesystem checks

The verifier must check:

- trusted control-plane containment;
- scan-root containment;
- staging-root containment;
- regular-file status;
- symlink rejection;
- path normalization;
- duplicate resolved-path rejection;
- trusted file-size limits;
- authority-bundle total-size and entry-count limits;
- expected file presence;
- exact digests;
- exact reference-closure equality;
- exact source-bundle identity when available.

### 20.2 Strict JSON and YAML checks

Every JSON carrier must reject duplicate keys.

Trusted YAML must reject duplicate mapping keys.

### 20.3 Cross-document checks

The verifier must require:

```text
manifest scan id
==
findings scan id
==
coverage scan id
==
producer-receipt scan id
```

Manifest references and artifact digests must match independently calculated
values.

### 20.4 Reference-closure checks

The supplied index must not determine what references are checked.

The canonical documents and trusted extractor determine the required closure.

### 20.5 Trusted control-plane checks

The verifier must independently establish and bind:

- control-plane repository;
- control-plane revision;
- policy digest;
- verifier digest and version;
- packet-builder digest;
- reference-extractor digest;
- lifecycle-controller digest;
- summary-builder digest;
- projection-checker digest;
- schema-snapshot identity.

### 20.6 Producer, subject, and run checks

The verifier must compare actual producer and target identities with the
trusted expectations.

### 20.7 Recipe and coverage checks

Execution mode, target scope, coverage mode, inventory strategy, include paths,
exclude paths, exclusions, deferred work, and unresolved surfaces must be
verified separately.

### 20.8 Findings checks

Supported severity values are:

```text
critical
high
medium
low
informational
```

Missing, malformed, or unsupported severity produces:

```text
unverified
```

A valid critical or high finding produces:

```text
verified_block
```

### 20.9 Evidence presence at verification

The verifier must record evidence presence from the exact filesystem and byte
state observed during verification.

The record must not depend on later filesystem existence.

Conceptual shape:

```yaml
evidence_presence_at_verification:
  recorded: true
  required_core_entry_count: integer
  required_core_entries_present: integer
  referenced_entry_count: integer_or_null
  referenced_entries_present: integer_or_null
  complete_required_presence: boolean
```

For a complete indexed bundle:

```text
complete_required_presence == true
```

requires every required core and referenced authority entry to have been
present and successfully opened during verification.

For a pre-index failure, the report may record partial observed counts, but:

```text
complete_required_presence == false
```

### 20.10 Single-read projection construction

The verifier must construct all private report projections from the same
validated immutable buffers.

It must not reopen source files to calculate projected fields.

---

## 21. Private intake report

The verifier must emit:

```text
codex_security_intake_report_v0.json
```

when deterministic report construction remains possible.

The report is private.

It must not enter public Actions artifacts.

### 21.1 Exhaustive machine-only schema

The report schema must use:

```text
additionalProperties: false
```

at every authority-relevant object level.

The report must not contain:

- source excerpts;
- vulnerable source paths intended for human display;
- attack narratives;
- remediation prose;
- arbitrary messages;
- arbitrary notes;
- free-form explanations;
- raw model responses;
- private-storage access data.

### 21.2 Report result classes

```text
verified_pass
verified_block
unverified
```

### 21.3 Complete public-identity projection

The private report must contain every identity needed to construct or
regenerate the public summary.

Conceptual shape:

```yaml
public_identity_projection:
  subject:
    repository_identity: string
    target_kind: git_revision
    revision: full_commit_sha
    identity_state: verified_or_expected_only

  run_binding:
    workflow_name: string
    workflow_revision: full_commit_sha
    run_id: string
    run_attempt: integer
    event_name: string
    ref: string
    identity_state: verified_or_expected_only

  producer:
    package_name: string_or_null
    package_version: string_or_null
    plugin_name: string_or_null
    plugin_version: string_or_null
    runtime_version: string_or_null
    model: string_or_null
    reasoning_effort: string_or_null
    identity_state: verified_or_expected_only_or_unavailable

  policy:
    policy_id: string
    policy_version: string
    policy_sha256: sha256
```

For `verified_pass` and `verified_block`:

- subject identity must be verified;
- run identity must be verified;
- producer fields must be non-null and verified;
- policy identity must be present.

For `unverified`:

- trusted subject and run expectations may be recorded with
  `identity_state: expected_only`;
- unavailable producer fields must be null;
- the summary must preserve the identity state and must not present an
  expected-only value as a verified producer observation.

### 21.4 Required technical bindings

```yaml
trusted_control_plane:
  repository_identity: string
  revision: full_commit_sha
  policy_sha256: sha256
  verifier_sha256: sha256
  verifier_version: string
  packet_builder_sha256: sha256
  reference_extractor_sha256: sha256
  lifecycle_controller_sha256: sha256
  summary_builder_sha256: sha256
  projection_checker_sha256: sha256

schema_snapshot_binding:
  upstream_repository_identity: string
  upstream_revision: full_commit_sha
  source_record_sha256: sha256
  aggregate_snapshot_sha256: sha256
  scan_manifest_schema_sha256: sha256
  findings_schema_sha256: sha256
  coverage_schema_sha256: sha256

intake_packet:
  sha256: sha256

source_bundle:
  identity_available: boolean
  bundle_identity: sha256_or_null
  bundle_index_sha256: sha256_or_null
  entry_count: integer_or_null
  total_size_bytes: integer_or_null
  referenced_evidence_count: integer_or_null
  scan_manifest_sha256: sha256_or_null
  findings_sha256: sha256_or_null
  coverage_sha256: sha256_or_null
  producer_receipt_sha256: sha256_or_null
```

A pre-index unverified report may contain null bundle identities.

It must record stable reason codes explaining why those identities are
unavailable.

### 21.5 Evidence-presence projection

```yaml
evidence_presence_at_verification:
  recorded: true
  required_core_entry_count: integer
  required_core_entries_present: integer
  referenced_entry_count: integer_or_null
  referenced_entries_present: integer_or_null
  complete_required_presence: boolean
```

This is the only evidence-presence input accepted by later candidate gates.

Current filesystem existence after lifecycle cleanup is not an evidence-presence
gate input.

### 21.6 Complete decision projection

```yaml
decision_projection:
  verification:
    result: verified_pass_or_verified_block_or_unverified
    bundle_integrity_ok: boolean
    reference_closure_complete: boolean
    trusted_control_plane_ok: boolean
    schema_snapshot_ok: boolean
    producer_identity_ok: boolean
    subject_binding_ok: boolean
    run_binding_ok: boolean
    recipe_binding_ok: boolean
    coverage_complete: boolean
    findings_document_valid: boolean

  coverage:
    mode: repository_or_null
    completeness: complete_or_partial_or_unknown_or_null
    inventory_strategy: repository_or_null
    explicit_exclusion_count: integer_or_null
    deferred_count: integer_or_null
    unresolved_surface_count: integer_or_null
    required_coverage_pass: boolean

  findings:
    total: integer_or_null
    critical: integer_or_null
    high: integer_or_null
    medium: integer_or_null
    low: integer_or_null
    informational: integer_or_null
    blocking_count: integer_or_null

  policy:
    findings_policy_pass: boolean
    reason_codes: stable_reason_code_array
```

The private report must carry every value needed to:

- build the public summary;
- regenerate the public summary;
- derive future candidate gate state.

The summary builder must not reopen source carriers.

---

## 22. Lifecycle carrier classes

The lane uses two distinct lifecycle carriers.

### 22.1 Indexed-bundle lifecycle receipt

Path:

```text
codex_security_raw_bundle_lifecycle_receipt_v0.json
```

This receipt is permitted only when a valid source-bundle index digest and
bundle identity were established.

Conceptual shape:

```yaml
document_type: pulsemech.codex-security-raw-bundle-lifecycle-receipt
schema_version: "0.1"
receipt_kind: indexed_bundle_lifecycle

source_bundle:
  bundle_identity: sha256
  bundle_index_sha256: sha256

intake_report:
  sha256: sha256

controlled_output_cleanup:
  controlled_root_count: integer
  cleanup_attempted: true
  cleanup_completed: boolean
  postconditions_passed: boolean
  all_controlled_confidential_roots_absent: boolean
  public_raw_artifact_created: false

lifecycle:
  mode: ephemeral_delete_or_access_controlled_private_storage
  raw_source_package_created: boolean
  raw_source_transfer_completed: boolean
  raw_source_transfer_verified: boolean
  retained_raw_source_package_identity: sha256_or_null
  runner_local_controlled_outputs_deleted: boolean
```

### 22.2 Pre-index cleanup receipt

Path:

```text
codex_security_controlled_output_cleanup_receipt_v0.json
```

This receipt is used when no valid source-bundle identity could be established.

Conceptual shape:

```yaml
document_type: pulsemech.codex-security-controlled-output-cleanup-receipt
schema_version: "0.1"
receipt_kind: preindex_cleanup

intake_report:
  sha256: sha256

unavailable_source_bundle_identity:
  bundle_identity_available: false
  bundle_index_digest_available: false

cleanup:
  trigger_stage: preindex_failure
  controlled_root_count: integer
  cleanup_attempted: true
  cleanup_completed: boolean
  postconditions_passed: boolean
  all_controlled_confidential_roots_absent: boolean
  public_raw_artifact_created: false

reason_codes:
  - stable_reason_code
```

The pre-index receipt must not invent:

- a bundle identity;
- a bundle-index digest;
- an entry count;
- a replay claim.

### 22.3 Report requirement

A sanitized public unverified summary may be built only when:

```text
valid private unverified intake report
+
valid pre-index cleanup receipt
```

If no deterministic private intake report exists, cleanup may still occur, but
no public summary is permitted.

---

## 23. Controlled-output lifecycle

### 23.1 Ephemeral-delete lifecycle

For an indexed bundle:

```text
private intake report
→ complete controlled-root cleanup
→ cleanup postcondition verification
→ indexed-bundle lifecycle receipt
→ public summary
→ optional same-run candidate evaluation
→ private carrier cleanup before runner termination
```

For a pre-index failure:

```text
private unverified intake report
→ complete controlled-root cleanup
→ cleanup postcondition verification
→ pre-index cleanup receipt
→ public unverified summary
```

### 23.2 Private-retention lifecycle

Private retention uses two non-recursive packages and a final storage-side
commit receipt.

#### Package A — private raw-source package

```text
private_raw_source_package_v0
```

It contains:

- every verified authority source-bundle entry;
- the source-bundle index;
- a package manifest binding the source-bundle identity.

It does not contain:

- the intake report;
- a lifecycle receipt that does not yet exist;
- unindexed readable projections;
- unindexed workbench state.

Package A is transferred to access-controlled private storage and its stored
identity is verified.

#### Controlled-root cleanup

After Package A transfer verification:

- every controlled confidential root is deleted;
- unindexed reports, SARIF, CSV, logs, state, and temporary files are removed;
- cleanup postconditions are checked;
- the indexed-bundle lifecycle receipt is created.

#### Package B — private control package

```text
private_control_package_v0
```

It contains:

- the intake packet;
- the private intake report;
- the indexed-bundle lifecycle receipt;
- a control-package manifest with component digests.

Package B is then transferred to access-controlled private storage and its
stored identity is verified.

#### Retention-set commit

After both package transfers verify, the private storage control plane must
commit a retention set containing:

```text
Package A identity
+
Package B identity
+
retention policy identity
```

The storage or independently trusted retention controller must issue:

```text
codex_security_private_retention_completion_receipt_v0.json
```

Conceptual shape:

```yaml
document_type: pulsemech.codex-security-private-retention-completion-receipt
schema_version: "0.1"

retention_set:
  retention_set_id: fixed_non_secret_identifier
  raw_source_package_identity: sha256
  private_control_package_identity: sha256
  raw_source_transfer_verified: true
  private_control_transfer_verified: true
  retention_policy_id: fixed_identifier
  retention_set_committed: true

bindings:
  source_bundle_identity: sha256
  intake_report_sha256: sha256
  indexed_lifecycle_receipt_sha256: sha256
```

The retention completion receipt is the non-recursive final commit record.

It is not required to be inside Package A or Package B.

It must be independently retrievable from the private retention system.

### 23.3 Complete private replay set

The replay set is complete only when all three are available:

```text
Package A — private raw-source package
Package B — private control package
Retention completion receipt
```

The lifecycle receipt required for replay is preserved inside Package B.

No package identity is mutated after verification.

### 23.4 Public summary ordering

The final public summary may be built only after:

- indexed lifecycle receipt or pre-index cleanup receipt exists;
- all lifecycle postconditions pass;
- private retention completion receipt exists when private retention is
  selected.

If any required operation fails:

```text
no final public summary
workflow fails closed
```

---

## 24. Public summary builder

The proposed builder is:

```text
tools/build_codex_security_summary_v0.py
```

### 24.1 Exclusive inputs

The builder may consume only:

```text
private verifier-issued intake report
+
calculated intake-report digest
+
one private lifecycle carrier
+
calculated lifecycle-carrier digest
+
private retention completion receipt when private retention is selected
+
calculated retention-completion-receipt digest when present
+
trusted public-summary schema
```

The builder must not read:

```text
scan-manifest.json
findings.json
coverage.json
producer receipt
source-bundle index
referenced scan-local evidence
report.md
SARIF
CSV
workbench state
untrusted previously recorded public summary
```

### 24.2 Identity source

Every public identity must come from:

```text
intake_report.public_identity_projection
```

This includes:

- subject identity;
- workflow-run identity;
- producer identity;
- policy ID;
- policy version;
- policy digest.

### 24.3 Decision source

Every public decision value must come from:

```text
intake_report.decision_projection
```

### 24.4 Evidence-presence source

Public evidence-presence state must come from:

```text
intake_report.evidence_presence_at_verification
```

### 24.5 Lifecycle source

Lifecycle state must come from the verified lifecycle or cleanup carrier.

Private-retention state must come from the verified retention completion
receipt.

### 24.6 Public allowlist

The public summary schema must use:

```text
additionalProperties: false
```

at every object level.

Free-form text is forbidden.

---

## 25. Proposed public summary

Conceptual verified shape:

```json
{
  "document_type": "pulsemech.codex-security-summary",
  "schema_version": "0.1",
  "record_status": "observed",
  "subject": {
    "repository_identity": "HKati/pulse-release-gates-0.1",
    "target_kind": "git_revision",
    "revision": "<full-sha>",
    "identity_state": "verified"
  },
  "run_binding": {
    "workflow_name": "<name>",
    "workflow_revision": "<full-sha>",
    "run_id": "<id>",
    "run_attempt": 1,
    "event_name": "workflow_dispatch",
    "ref": "<ref>",
    "identity_state": "verified"
  },
  "producer": {
    "package_name": "@openai/codex-security",
    "package_version": "<exact>",
    "plugin_name": "<exact>",
    "plugin_version": "<exact>",
    "runtime_version": "<exact>",
    "model": "<exact>",
    "reasoning_effort": "<exact>",
    "identity_state": "verified"
  },
  "source_bundle": {
    "identity_available": true,
    "bundle_identity": "<sha256>",
    "bundle_index_sha256": "<sha256>",
    "entry_count": 4,
    "referenced_evidence_count": 0,
    "total_size_bytes": 0,
    "scan_manifest_sha256": "<sha256>",
    "findings_sha256": "<sha256>",
    "coverage_sha256": "<sha256>",
    "producer_receipt_sha256": "<sha256>"
  },
  "evidence_presence_at_verification": {
    "recorded": true,
    "required_core_entry_count": 4,
    "required_core_entries_present": 4,
    "referenced_entry_count": 0,
    "referenced_entries_present": 0,
    "complete_required_presence": true
  },
  "coverage": {
    "mode": "repository",
    "completeness": "complete",
    "inventory_strategy": "repository",
    "explicit_exclusion_count": 0,
    "deferred_count": 0,
    "unresolved_surface_count": 0,
    "required_coverage_pass": true
  },
  "findings": {
    "total": 0,
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "informational": 0,
    "blocking_count": 0
  },
  "verification": {
    "result": "verified_pass",
    "bundle_integrity_ok": true,
    "reference_closure_complete": true,
    "trusted_control_plane_ok": true,
    "schema_snapshot_ok": true,
    "producer_identity_ok": true,
    "subject_binding_ok": true,
    "run_binding_ok": true,
    "recipe_binding_ok": true,
    "coverage_complete": true,
    "findings_document_valid": true
  },
  "verification_binding": {
    "intake_report_sha256": "<sha256>",
    "lifecycle_carrier_kind": "indexed_bundle_lifecycle",
    "lifecycle_carrier_sha256": "<sha256>",
    "retention_completion_receipt_sha256": null,
    "trusted_control_plane_repository": "<identity>",
    "trusted_control_plane_revision": "<full-sha>",
    "verifier_sha256": "<sha256>",
    "verifier_version": "<version>",
    "reference_extractor_sha256": "<sha256>",
    "lifecycle_controller_sha256": "<sha256>",
    "summary_builder_sha256": "<sha256>",
    "projection_checker_sha256": "<sha256>"
  },
  "schema_snapshot_binding": {
    "upstream_repository_identity": "openai/codex-security",
    "upstream_revision": "<full-sha>",
    "source_record_sha256": "<sha256>",
    "aggregate_snapshot_sha256": "<sha256>",
    "scan_manifest_schema_sha256": "<sha256>",
    "findings_schema_sha256": "<sha256>",
    "coverage_schema_sha256": "<sha256>"
  },
  "policy_evaluation": {
    "policy_id": "<id>",
    "policy_version": "<version>",
    "policy_sha256": "<sha256>",
    "findings_policy_pass": true,
    "reason_codes": []
  },
  "controlled_output_lifecycle": {
    "mode": "ephemeral_delete",
    "cleanup_completed": true,
    "postconditions_passed": true,
    "all_controlled_confidential_roots_absent": true,
    "public_raw_artifact_created": false
  },
  "private_retention": {
    "required": false,
    "retention_set_committed": false,
    "raw_source_package_identity": null,
    "private_control_package_identity": null
  },
  "authority": {
    "mode": "candidate_advisory",
    "release_effect": "none",
    "public_summary_is_authority": false
  }
}
```

### 25.1 Pre-index unverified summary

For a pre-index failure:

- `source_bundle.identity_available` must be `false`;
- bundle identity and index digest must be `null`;
- evidence presence must show incomplete required presence;
- lifecycle carrier kind must be `preindex_cleanup`;
- verification result must be `unverified`;
- findings policy pass must not be `true`;
- private replay must not be claimed.

### 25.2 No free-form text

The summary must not contain:

- arbitrary messages;
- notes;
- explanations;
- source excerpts;
- finding titles;
- finding summaries;
- vulnerable paths;
- attack paths;
- remediation text;
- storage locations;
- signed URLs;
- private report paths;
- raw evidence paths.

---

## 26. Publication boundary

### 26.1 Publicly uploadable artifacts

Only:

```text
codex_security_summary_v0.json
detached digest or signature
```

may enter a normal public-repository Actions artifact.

### 26.2 Publicly forbidden artifacts

The public workflow must reject upload of:

```text
codex_security_intake_report_v0.json
codex_security_raw_bundle_lifecycle_receipt_v0.json
codex_security_controlled_output_cleanup_receipt_v0.json
codex_security_private_retention_completion_receipt_v0.json
codex_security_intake_packet_v0.json
codex_security_source_bundle_index_v0.json
private raw-source package
private control package
raw findings.json
raw report.md
raw SARIF
raw CSV
raw scan logs
raw workbench state
broad parent directories containing any forbidden file
```

### 26.3 Publication checks

The final public summary must pass:

- strict public schema validation;
- duplicate-key rejection;
- exhaustive field allowlist;
- free-form-text prohibition;
- maximum-size enforcement;
- canonical serialization check;
- digest calculation.

---

## 27. Candidate gate design

The proposed inactive gate-set identity is:

```text
codex_security_recorded_intake_candidate
```

Proposed gates:

```text
codex_security_evidence_present_at_verification
codex_security_bundle_integrity_ok
codex_security_reference_closure_complete
codex_security_trusted_control_plane_ok
codex_security_schema_snapshot_ok
codex_security_producer_identity_ok
codex_security_subject_binding_ok
codex_security_run_binding_ok
codex_security_recipe_binding_ok
codex_security_coverage_complete
codex_security_findings_document_valid
codex_security_findings_policy_pass
codex_security_intake_report_binding_ok
codex_security_controlled_output_cleanup_complete
codex_security_private_retention_complete
codex_security_summary_projection_ok
codex_security_intake_verified
```

### 27.1 Evidence-presence gate

`codex_security_evidence_present_at_verification` is literal `true` only when
the private intake report records:

```text
evidence_presence_at_verification.recorded == true
complete_required_presence == true
```

The gate does not inspect current filesystem existence.

### 27.2 Bundle and closure gates

Bundle integrity and reference closure are true only when a valid indexed
bundle was established.

A pre-index unverified summary cannot satisfy them.

### 27.3 Cleanup gate

`codex_security_controlled_output_cleanup_complete` is true only when the
verified lifecycle or cleanup carrier records:

```text
cleanup_completed == true
postconditions_passed == true
all_controlled_confidential_roots_absent == true
public_raw_artifact_created == false
```

### 27.4 Private-retention gate

`codex_security_private_retention_complete` is:

- not required for same-run ephemeral candidate evaluation;
- required for replay proof, later fold-in, and any future release-capable lane.

It is true only when the private retention completion receipt records a
committed retention set containing both private packages.

### 27.5 Summary-projection gate

The trusted builder must regenerate the public summary from private carriers.

Canonical bytes must exactly match the recorded public summary.

### 27.6 Candidate-set boundary

The candidate set must remain absent from every active required or blocking
set until a separate promotion PR.

---

## 28. Fold-in boundary

### 28.1 Public-summary-only input

A public summary without private carriers is:

```text
advisory display only
```

It cannot create candidate or release state.

### 28.2 Same-run ephemeral fold-in

Ephemeral mode may evaluate candidate state on the same runner while:

- the private intake report;
- the lifecycle or cleanup carrier;
- the public summary;

remain available to the trusted fold-in.

After private carrier deletion, later fold-in is impossible.

### 28.3 Private-retention fold-in

A later release-capable fold-in requires:

```text
private raw-source package
private control package
private retention completion receipt
recorded public summary
trusted verifier
trusted summary builder
trusted projection checker
trusted candidate policy
trusted schemas
```

### 28.4 Required validation

The fold-in must:

1. verify the retention completion receipt;
2. retrieve and verify Package B;
3. validate the private intake report;
4. validate the indexed lifecycle receipt;
5. verify Package A identity and source-bundle binding;
6. regenerate the public summary;
7. compare canonical bytes;
8. derive gate inputs from the private report;
9. reject every mismatch.

The fold-in must not trust decision values read only from the public summary.

### 28.5 Replay

Independent raw replay must rerun the trusted verifier against Package A and
produce a new private intake report.

The new report may then be compared with the retained report from Package B.

---

## 29. Reason-code families

The design requires stable codes including:

```text
source_bundle_missing
source_bundle_index_missing
source_bundle_index_parse_error
source_bundle_identity_unavailable
source_bundle_digest_mismatch
source_bundle_identity_mismatch
source_bundle_entry_set_mismatch
source_bundle_entry_count_exceeded
source_bundle_total_size_exceeded

referenced_evidence_missing
referenced_evidence_path_escape
referenced_evidence_symlink
referenced_evidence_non_regular_file
referenced_evidence_size_limit_exceeded
referenced_evidence_digest_mismatch
referenced_evidence_unindexed
referenced_evidence_unresolved
reference_closure_incomplete

controlled_output_escape_detected
controlled_output_cleanup_incomplete
controlled_output_root_not_removed
unindexed_confidential_output_remaining
public_raw_artifact_detected

manifest_parse_error
manifest_duplicate_json_key
manifest_schema_error
manifest_status_not_completed
manifest_artifact_digest_mismatch

findings_parse_error
findings_duplicate_json_key
findings_schema_error
findings_missing_severity
findings_malformed_severity
findings_unsupported_severity
findings_blocking_severity_present

coverage_parse_error
coverage_duplicate_json_key
coverage_schema_error
coverage_not_complete
coverage_unapproved_exclusion
coverage_deferred_work_present
coverage_required_surface_unresolved

producer_receipt_parse_error
producer_receipt_duplicate_json_key
producer_package_mismatch
producer_plugin_mismatch
producer_runtime_mismatch
producer_model_mismatch
producer_reasoning_effort_mismatch

trusted_control_plane_repository_mismatch
trusted_control_plane_revision_mismatch
trusted_policy_digest_mismatch
trusted_verifier_digest_mismatch
trusted_reference_extractor_digest_mismatch
trusted_lifecycle_controller_digest_mismatch
trusted_summary_builder_digest_mismatch
trusted_projection_checker_digest_mismatch

schema_snapshot_identity_mismatch
scan_manifest_schema_digest_mismatch
findings_schema_digest_mismatch
coverage_schema_digest_mismatch

subject_repository_mismatch
subject_kind_mismatch
subject_revision_mismatch

run_workflow_mismatch
run_workflow_revision_mismatch
run_id_mismatch
run_attempt_mismatch
run_event_mismatch
run_ref_mismatch
run_subject_sha_mismatch

execution_mode_mismatch
target_scope_mismatch
recipe_include_paths_mismatch
recipe_exclude_paths_mismatch

evidence_presence_incomplete_at_verification
evidence_presence_record_missing

intake_report_binding_missing
intake_report_digest_mismatch
intake_report_publication_forbidden
public_identity_projection_incomplete
decision_projection_incomplete

indexed_lifecycle_receipt_missing
preindex_cleanup_receipt_missing
lifecycle_carrier_digest_mismatch
lifecycle_action_incomplete
lifecycle_postcondition_failed

raw_source_package_transfer_incomplete
raw_source_package_identity_mismatch
private_control_package_transfer_incomplete
private_control_package_identity_mismatch
retention_set_commit_missing
retention_set_commit_incomplete
retention_completion_receipt_mismatch

summary_projection_mismatch
summary_decision_field_mismatch
summary_identity_field_mismatch
summary_lifecycle_binding_mismatch
summary_public_schema_error
summary_forbidden_field
summary_free_form_text_forbidden
```

The public summary may expose only explicitly allowed codes.

---

## 30. Failure matrix

| Condition | Evidence state | Candidate result |
|---|---|---|
| Canonical file missing | Unverified | False |
| Bundle index missing | Pre-index unverified | False |
| Bundle index malformed | Pre-index unverified | False |
| Bundle identity unavailable | Pre-index unverified | False |
| Required referenced evidence missing | Unverified | False |
| Reference closure incomplete | Unverified | False |
| Unindexed confidential projection remains after cleanup | Lifecycle failure | False |
| Controlled results root remains | Lifecycle failure | False |
| Controlled state root remains | Lifecycle failure | False |
| Duplicate JSON key | Unverified | False |
| Schema mismatch | Unverified | False |
| Wrong subject revision | Unverified | False |
| Previous workflow run | Unverified | False |
| Partial coverage | Unverified | False |
| Missing or unsupported severity | Unverified | False |
| Valid high finding | Verified block | False |
| Valid no-blocking-finding scan | Verified pass | True |
| Evidence deleted after verified presence | Recorded presence remains true | Possible same-run candidate |
| Current filesystem has no raw evidence | Not used as presence gate | No contradiction |
| Pre-index cleanup succeeds | Sanitized unverified summary allowed | False |
| Pre-index cleanup fails | No public summary | False |
| Raw source Package A retained, Package B missing | Retention incomplete | False |
| Package B retained, retention commit missing | Retention incomplete | False |
| Public summary identity differs from private report | Projection mismatch | False |
| Public summary decision differs from private report | Projection mismatch | False |
| Public summary used without private carriers | Advisory only | No authority |
| Ephemeral summary used in later fold-in | Forbidden | No authority |

---

## 31. Required tests

### 31.1 Private identity-projection tests

Tests must cover:

- complete verified subject identity;
- complete workflow-run identity;
- complete producer identity;
- policy ID and version;
- missing dynamic public identity;
- expected-only identity in unverified state;
- null unavailable producer fields;
- summary builder using only report identities.

### 31.2 Evidence-presence tests

Tests must prove:

- complete presence recorded during verification;
- missing core evidence records incomplete presence;
- missing referenced evidence records incomplete presence;
- successful deletion does not rewrite historical presence;
- later gate derives presence only from the private report;
- current filesystem absence is ignored by the presence gate.

### 31.3 Pre-index cleanup tests

Tests must cover:

- missing index;
- malformed index;
- duplicate-key index;
- oversized index;
- unavailable bundle identity;
- truthful cleanup receipt with null unavailable identities;
- no invented bundle digest;
- sanitized unverified summary after successful cleanup;
- no summary after cleanup failure.

### 31.4 Controlled-output lifecycle tests

Tests must cover:

- unreferenced `report.md`;
- unreferenced SARIF;
- unreferenced CSV;
- scan log;
- workbench state;
- abandoned temporary file;
- whole-root deletion;
- root absence postcondition;
- symlink removal without target traversal;
- output escape detection;
- indexed files removed;
- unindexed confidential files removed.

### 31.5 Private-retention tests

Tests must cover:

- Package A construction;
- Package A identity;
- Package A transfer verification;
- lifecycle receipt creation after raw transfer and cleanup;
- Package B construction containing the lifecycle receipt;
- Package B identity;
- Package B transfer verification;
- retention-set commit;
- retention completion receipt;
- missing Package B;
- changed Package B after transfer;
- missing retention commit;
- replay set containing A, B, and completion receipt.

### 31.6 Builder-exclusive-input tests

Tests must prove that the builder:

- reads the private intake report;
- reads one lifecycle carrier;
- reads the retention completion receipt when required;
- reads the trusted public schema;
- does not open canonical source documents;
- does not open the producer receipt;
- does not open the source-bundle index;
- does not open raw projections;
- does not copy values from an existing public summary.

### 31.7 Projection-regeneration tests

Change each field independently:

- subject revision;
- workflow run ID;
- producer version;
- policy ID;
- policy version;
- verification result;
- evidence presence;
- critical count;
- blocking count;
- coverage result;
- findings-policy result;
- lifecycle mode;
- retention completion state;
- reason codes.

Every change must produce projection mismatch.

### 31.8 Existing boundary tests

Tests must continue to cover:

- duplicate keys;
- size limits;
- path traversal;
- symlink rejection;
- schema snapshot;
- subject binding;
- run binding;
- producer binding;
- recipe binding;
- coverage;
- findings policy;
- public artifact prohibition;
- inactive candidate registration.

---

## 32. Initial fixtures

### 32.1 Verified ephemeral fixture

```text
complete indexed bundle
complete presence at verification
no blocking findings
complete root cleanup
indexed lifecycle receipt
public summary
```

Expected:

```text
verified_pass
evidence_present_at_verification = true
controlled_output_cleanup_complete = true
same-run candidate possible
later fold-in unavailable
```

### 32.2 Verified private-retention fixture

```text
complete indexed bundle
Package A retained
controlled roots cleaned
lifecycle receipt created
Package B retained
retention set committed
public summary generated
```

Expected:

```text
verified_pass
private_retention_complete = true
later replay and fold-in possible
```

### 32.3 Pre-index failure fixture

```text
source-bundle index missing
private unverified report emitted
controlled roots cleaned
pre-index cleanup receipt emitted
```

Expected:

```text
unverified
bundle identity null
no replay claim
sanitized unverified summary allowed
```

### 32.4 Unindexed projection fixture

```text
valid authority bundle
unreferenced report.md exists in controlled results root
```

Expected:

```text
report.md excluded from authority identity
report.md removed by whole-root cleanup
lifecycle succeeds only after root absence
```

### 32.5 Identity-projection fixture

```text
private report contains subject, run, producer, policy ID and version
raw source files deleted
```

Expected:

```text
summary builder constructs every public identity from private report
no raw source reopen
```

### 32.6 Evidence-presence fixture

```text
evidence present and verified
ephemeral deletion succeeds
```

Expected:

```text
evidence_present_at_verification remains true
current filesystem presence is not consulted
```

### 32.7 Incomplete private-retention fixture

```text
Package A retained
lifecycle receipt created
Package B transfer missing
```

Expected:

```text
retention set not committed
no private-retention-complete claim
no replay-capable summary
```

---

## 33. Candidate policy

Proposed path:

```text
policies/security/codex_security_candidate_policy_v0.yml
```

Conceptual additions:

```yaml
private_report:
  exhaustive_schema: true
  public_identity_projection_required: true
  decision_projection_required: true
  evidence_presence_at_verification_required: true
  public_upload_allowed: false

controlled_output:
  whole_root_cleanup_required: true
  unindexed_confidential_outputs_allowed_to_remain: false
  output_escape_allowed: false

preindex_failure:
  cleanup_receipt_required: true
  bundle_identity_may_be_null: true
  replay_claim_allowed: false

private_retention:
  raw_source_package_required: true
  private_control_package_required: true
  retention_set_commit_required: true
  lifecycle_receipt_must_be_in_control_package: true

public_summary:
  exclusive_private_inputs: true
  free_form_text_allowed: false
  additional_properties_allowed: false
  authority_effect: none
```

The full policy must also retain all previously defined producer, schema,
subject, recipe, coverage, carrier-limit, and findings-policy bindings.

---

## 34. Workflow design

The initial workflow should be:

```text
.github/workflows/codex_security_candidate.yml
```

### 34.1 Conceptual workflow

```text
resolve-subject
→ codex-security-produce-verify-lifecycle-summarize
→ publish-public-summary
```

### 34.2 Raw and private job

The central same-runner job performs:

```text
1. verify protected control plane

2. checkout exact subject separately

3. create controlled roots

4. run Codex Security

5. create producer receipt

6. validate canonical source documents

7. extract reference closure

8. build source-bundle index when possible

9. run trusted verifier

10. emit private intake report when possible

11. branch by lifecycle mode and index availability

12A. indexed ephemeral:
     clean all controlled roots
     verify cleanup
     emit indexed lifecycle receipt

12B. indexed private retention:
     create and transfer Package A
     verify Package A
     clean all controlled roots
     verify cleanup
     emit indexed lifecycle receipt
     create and transfer Package B
     verify Package B
     commit retention set
     obtain retention completion receipt

12C. pre-index failure:
     clean all controlled roots
     verify cleanup
     emit pre-index cleanup receipt

13. build final public summary from private carriers only

14. optionally perform same-run private fold-in

15. remove remaining local private carriers before runner termination

16. expose only the public summary
```

### 34.3 Public job

The public job receives only:

```text
codex_security_summary_v0.json
detached digest or signature
```

It must never receive raw or private carriers.

---

## 35. Cost and interruption boundary

An interrupted scan may leave:

- partial canonical files;
- no source-bundle index;
- unindexed reports;
- temporary data;
- state files.

The cleanup controller must still remove the complete controlled confidential
surface.

A partial run may emit a sanitized unverified summary only when:

- a deterministic private unverified report exists;
- cleanup completes;
- a valid pre-index cleanup receipt exists.

---

## 36. Proposed implementation files

```text
docs/security/
└── PULSEMECH_CODEX_SECURITY_EVIDENCE_LANE_DESIGN_v0.md

policies/security/
└── codex_security_candidate_policy_v0.yml

schemas/security/
├── codex_security_producer_receipt_v0.schema.json
├── codex_security_source_bundle_index_v0.schema.json
├── codex_security_intake_packet_v0.schema.json
├── codex_security_intake_report_v0.schema.json
├── codex_security_raw_bundle_lifecycle_receipt_v0.schema.json
├── codex_security_controlled_output_cleanup_receipt_v0.schema.json
├── codex_security_private_raw_source_package_manifest_v0.schema.json
├── codex_security_private_control_package_manifest_v0.schema.json
├── codex_security_private_retention_completion_receipt_v0.schema.json
└── codex_security_summary_v0.schema.json

tools/
├── extract_codex_security_reference_closure_v0.py
├── build_codex_security_source_bundle_index_v0.py
├── build_codex_security_intake_packet_v0.py
├── check_codex_security_intake_packet_v0.py
├── run_codex_security_controlled_output_cleanup_v0.py
├── build_codex_security_raw_bundle_lifecycle_receipt_v0.py
├── build_codex_security_controlled_output_cleanup_receipt_v0.py
├── build_codex_security_private_raw_source_package_v0.py
├── build_codex_security_private_control_package_v0.py
├── check_codex_security_private_retention_completion_v0.py
├── build_codex_security_summary_v0.py
└── check_codex_security_summary_projection_v0.py

ci/
├── check_codex_security_controlled_roots_v0.py
├── check_codex_security_no_public_private_artifact_v0.py
└── check_codex_security_candidate_activation_guard_v0.py

tests/
├── test_codex_security_public_identity_projection_v0.py
├── test_codex_security_evidence_presence_at_verification_v0.py
├── test_codex_security_preindex_cleanup_receipt_v0.py
├── test_codex_security_controlled_output_cleanup_v0.py
├── test_codex_security_private_raw_source_package_v0.py
├── test_codex_security_private_control_package_v0.py
├── test_codex_security_private_retention_completion_v0.py
├── test_codex_security_summary_exclusive_inputs_v0.py
├── test_codex_security_summary_projection_v0.py
└── test_codex_security_candidate_activation_guard_v0.py

.github/workflows/
└── codex_security_candidate.yml
```

---

## 37. Implementation sequence

### PR 1 — Design record

Initial design only.

### PR 1A — Trust and public-artifact hardening

Add protected verifier, schema, size, duplicate-key, and private raw-output
boundaries.

### PR 1B — Report, closure, projection, and lifecycle binding

Add private report, complete reference closure, lifecycle receipt, and summary
regeneration.

### PR 1C — Identity, presence, cleanup, and retention closure

Add:

- complete public identities in the private report;
- recorded evidence presence at verification;
- pre-index cleanup receipt;
- whole controlled-output-root cleanup;
- two-package private retention;
- retention-set completion receipt.

Authority effect:

```text
none
```

### PR 2 — Upstream contract snapshot

Add vendored schemas, source record, digests, and supported-reference-field
inventory.

### PR 3 — Carrier schemas

Add all public and private carrier schemas.

### PR 4 — Verifier and closure extractor

Add immutable reads, reference closure, identity projection, decision
projection, and presence-at-verification recording.

### PR 5 — Lifecycle and cleanup carriers

Add whole-root cleanup, indexed lifecycle receipt, and pre-index cleanup
receipt.

### PR 6 — Private retention packages

Add Package A, Package B, transfer verification, and retention-set commit.

### PR 7 — Public summary and projection checker

Add exclusive-input summary builder and deterministic regeneration.

### PR 8 — Inactive candidate registration

Add candidate gates with no active authority effect.

### PR 9 — Manual producer workflow

Add the complete same-runner execution and public-summary-only publication.

### PR 10 — Fixed-source candidate proof

Require private retention and replay proof.

### PR 11 — Promotion criteria

Define stability, retention, cost, failure, and update requirements.

### PR 12 — Separate promotion

Only this PR may activate required release authority.

---

## 38. Promotion prerequisites

Promotion requires proof of:

### 38.1 Complete private identities

The private report carries every subject, run, producer, and policy identity
required for deterministic public projection.

### 38.2 Recorded evidence presence

Evidence presence is recorded during verification and remains distinct from
post-verification filesystem state.

### 38.3 Pre-index failure handling

A truthful cleanup receipt can be issued without invented bundle identities.

### 38.4 Whole-surface confidentiality cleanup

All indexed and unindexed confidential producer output is removed from
controlled local roots.

### 38.5 Complete private retention

The private raw-source package, private control package, and retention
completion receipt are all retained and independently verifiable.

### 38.6 Exclusive summary inputs

The summary builder uses only private reports, lifecycle carriers, retention
completion data, and the trusted public schema.

### 38.7 Projection equality

Every public identity and decision field is regenerated and compared.

### 38.8 Authority isolation

The public summary alone cannot create release state.

---

## 39. Acceptance criteria

The candidate lane is complete only when:

```text
1. The exact subject revision is scanned.

2. The protected control-plane revision is independently bound.

3. Every authority-relevant reference is indexed.

4. Every indexed component participates in the source-bundle identity.

5. Every producer output remains inside controlled roots.

6. Unindexed report, SARIF, CSV, log, state, and temporary outputs are removed
   by whole-root cleanup.

7. The private intake report carries complete public subject, run, producer,
   and policy identities.

8. The private intake report records evidence presence at verification.

9. Evidence presence does not depend on later filesystem existence.

10. Pre-index failures use a separate cleanup receipt with unavailable bundle
    identities represented truthfully.

11. Package A preserves the authority source bundle and index.

12. The indexed lifecycle receipt is created only after raw transfer and local
    controlled-root cleanup.

13. Package B preserves the intake packet, private report, and lifecycle
    receipt.

14. Both private packages are transferred and verified.

15. A separate retention-set commit receipt binds both packages.

16. No retained package is mutated after identity verification.

17. The public summary is generated only after lifecycle completion.

18. The public summary builder does not reopen raw source carriers.

19. Every public identity comes from the private report.

20. Every public decision field comes from the private decision projection.

21. Every lifecycle field comes from a verified lifecycle carrier.

22. Every retention claim comes from the retention completion receipt.

23. The public summary uses an exhaustive schema without free-form text.

24. Public artifacts contain only the summary and its detached digest or
    signature.

25. Public-summary-only fold-in is rejected.

26. Ephemeral mode supports only same-run candidate evaluation.

27. Later replay and release-capable fold-in require complete private
    retention.

28. Every changed public identity or decision field fails deterministic
    projection comparison.

29. The candidate gate set remains inactive.

30. No release authority changes occur.
```

---

## 40. Final boundary

The completed relation is:

```text
Codex Security
produces a security observation and confidential producer-output surface

protected PULSEmech control plane
confines every output to controlled roots

PULSEmech authority source-bundle closure
binds every canonical and authority-relevant referenced evidence file

private PULSEmech intake report
records complete public identities, evidence presence at verification, and the
complete machine decision projection

PULSEmech lifecycle controller
removes the complete controlled confidential surface, including unindexed raw
projections and state

private lifecycle carriers
truthfully distinguish indexed-bundle handling from pre-index cleanup

private retention set
preserves both the raw-source package and the later control package containing
the lifecycle receipt

public PULSEmech summary
is a strict projection created only from private verified carriers

private PULSEmech fold-in
regenerates the projection and derives gate state from private authority
carriers

PULSEmech authority
remains the only mechanism that may convert materialized evidence into an
enforced release state
```

Without the verified carriers:

```text
there is a scan
```

With complete identities, recorded verification-time presence, complete
confidential-output cleanup, complete private retention where required, and
deterministic projection regeneration:

```text
there is reviewable, subject-bound security evidence
```

Only a later explicit promotion may make that evidence release-required.
