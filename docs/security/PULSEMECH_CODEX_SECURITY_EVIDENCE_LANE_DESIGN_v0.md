# PULSEmech Codex Security Evidence Lane Design v0

## Document state

```yaml
document_id: pulsemech_codex_security_evidence_lane_design_v0
document_type: design
revision: v0
revision_state: review_hardened
status: design_only
authority_effect: none
gate_effect: none
policy_effect: none
schema_effect: none
ci_effect: none
release_effect: none
raw_public_artifact_effect: forbidden
```

This document defines a future PULSEmech evidence lane for importing,
verifying, normalizing, and optionally materializing completed Codex Security
scan evidence.

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
  public repository.

Implementation and activation require separate pull requests.

---

## 1. Purpose

Codex Security can inspect a repository and produce structured security
findings together with a record of:

- the reviewed target;
- the executed scan recipe;
- the achieved coverage;
- the findings produced by that observation.

PULSEmech can use that output only after the output becomes a verified,
artifact-bound evidence carrier.

The intended relation is:

```text
Codex Security
produces a security observation

PULSEmech
verifies the carrier, producer, subject, run, recipe, coverage, and policy
relation

PULSEmech release authority
remains the only mechanism that may produce an enforced ALLOW or BLOCK state
```

The lane separates:

```text
security analysis
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
- an unverified adapter summary.

A Codex Security observation may participate in release-state evaluation only
through this path:

```text
exact subject revision
→ isolated Codex Security producer
→ completed canonical source bundle
→ same-runner source-bundle packaging
→ protected PULSEmech control-plane verifier
→ exact subject and run binding
→ exact producer and recipe binding
→ exact schema-snapshot binding
→ complete declared coverage
→ deterministic findings-policy evaluation
→ verifier-issued intake report
→ intake-report-bound normalized summary
→ inactive candidate gate set
→ separately approved promotion
→ strict PULSEmech enforcement
```

No earlier element in the path has release authority.

---

## 3. Design position

The lane is a dedicated security evidence path.

It must not be flattened into the existing generic external-detector scalar
interface.

A Codex Security result contains several independent authority-relevant
relations:

```text
source-bundle integrity
trusted control-plane identity
upstream schema-snapshot identity
producer identity
subject identity
workflow-run identity
scan recipe
coverage completeness
explicit exclusions
deferred work
finding identity
finding severity
findings-policy evaluation
intake-report identity
```

A single numeric `rate` cannot preserve those relations.

The initial integration must therefore use:

```text
dedicated canonical source bundle
dedicated producer receipt
dedicated source-bundle index
dedicated trusted control plane
dedicated intake packet
dedicated verifier
dedicated intake report
dedicated normalized summary
dedicated candidate gate set
```

The generic `external_all_pass` path must not be used as the initial authority
carrier.

---

## 4. Scope

### 4.1 Included in the v0 design

This design covers:

- an exact Git revision as the scan subject;
- a clean subject checkout;
- a separate protected trusted control-plane checkout;
- a completed Codex Security canonical scan bundle;
- a separately recorded producer receipt;
- immutable component digests;
- a deterministic source-bundle identity;
- trusted per-carrier size limits;
- duplicate-key rejection for every JSON carrier;
- duplicate-mapping-key rejection for trusted YAML;
- a PULSEmech subject-input packet;
- offline upstream schema validation;
- source-bundle integrity validation;
- protected verifier and policy identity validation;
- upstream schema-snapshot identity validation;
- current-workflow-run binding;
- exact Git revision binding;
- declared scan-recipe binding;
- coverage completeness validation;
- deterministic finding classification;
- deterministic severity-policy evaluation;
- a verifier-issued intake report;
- a normalized PULSEmech security summary bound to that intake report;
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
- raw findings in normal public-repository Actions artifacts;
- release-gate activation.

These functions require separate designs and separate authority boundaries.

---

## 5. Initial operating profile

The first executable lane should use this profile:

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
  output_location: outside_subject_and_control_plane_worktrees
  patch_command_allowed: false

raw_results:
  public_actions_artifact_allowed: false
  retention_mode:
    - ephemeral_delete
    - access_controlled_private_storage
  default_candidate_mode: ephemeral_delete

sanitized_results:
  public_actions_artifact_allowed: true

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

The exact package version, plugin version, runtime version, model, reasoning
effort, expected paths, trusted verifier identity, trusted policy identity,
upstream schema snapshot, and per-carrier size limits must be bound by the
candidate policy and protected control-plane revision created during
implementation.

They must not be inferred from the source bundle.

---

## 6. Canonical Codex Security source contract

A completed Codex Security scan produces three canonical machine-readable
documents:

```text
scan-manifest.json
findings.json
coverage.json
```

The initial PULSEmech intake must use these three documents as its semantic
source.

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

The adapter must not recover missing semantic data by parsing `report.md`.

The adapter must not recover missing semantic data by parsing SARIF.

The adapter must not interpret the absence of text in a readable report as the
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
- provenance.

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
- receipt references when present.

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

The scanner execution mode and the coverage mode are different fields.

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

The verifier must not compare:

```text
execution_mode
```

directly with:

```text
coverage.mode
```

The required relations are:

```text
producer receipt requested_execution_mode
==
candidate policy execution_mode
==
standard
```

and:

```text
coverage.mode
==
candidate policy expected_coverage_mode
==
repository
```

and:

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
- the summary builder;
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
- no trusted expected digest.

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
- their expected digests;
- the protected workflow revision.

### 7.4 Executable-source boundary

The verifier must be invoked by an absolute path from the trusted
control-plane checkout.

The verifier must not import Python modules from the subject checkout.

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
verification phase.

---

## 8. Trust boundaries

The lane crosses the following trust boundaries:

```text
protected workflow revision
→ trusted control-plane checkout

selected subject revision
→ isolated subject checkout

subject checkout
→ Codex Security runtime

Codex Security runtime
→ generated canonical source bundle

generated source bundle
→ same-runner packaging boundary

packaged source bundle
→ trusted PULSEmech intake verifier

verified intake report
→ trusted PULSEmech summary builder

intake-report-bound summary
→ inactive candidate gate state
```

Each transition must be explicit.

### 8.1 Untrusted inputs

The verifier must treat all of the following as untrusted input:

- subject repository content;
- generated JSON;
- generated filenames;
- manifest paths;
- artifact references;
- timestamps;
- target identity declared by the producer;
- producer version declared by the producer;
- finding severity;
- finding identifiers;
- coverage completeness;
- include paths;
- exclude paths;
- deferred entries;
- receipt references;
- human-readable reports;
- SARIF;
- console output;
- workflow annotations;
- the source-bundle index;
- the producer receipt;
- the intake packet as a data carrier.

No field becomes trusted because it was generated by a security tool.

No field becomes trusted because it appears in an intake packet.

Trust is established through a successful relation with independently resolved
protected control-plane inputs.

---

## 9. Threat model

The design must defend against at least the following failures.

### 9.1 Subject substitution

A valid scan bundle may describe:

- a previous commit;
- another branch;
- another repository;
- a dirty worktree;
- a different pull-request head;
- an unrecorded local modification;
- a partial directory snapshot.

A valid bundle for the wrong subject is not valid release evidence.

### 9.2 Stale evidence

A completed scan may be old while the repository has advanced.

Wall-clock recency alone does not solve this problem.

The primary freshness binding is:

```text
exact current workflow run
+
exact current subject Git revision
```

### 9.3 Bundle mutation

A findings or coverage document may be modified after finalization.

Every canonical input must be digest-verified.

### 9.4 Producer substitution

A different package, plugin, wrapper, model, or runtime may produce a
structurally similar bundle.

Producer identity must be checked against an independent expected identity.

### 9.5 Recipe drift

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

### 9.6 Coverage collapse

A scan may complete after reviewing only part of the required surface.

The absence of findings under partial or unknown coverage must fail closed.

### 9.7 Exclusion injection

An attacker or configuration error may exclude a security-sensitive path.

The actual exclusions must exactly match the declared exclusion policy.

### 9.8 Deferred-work collapse

A scan may defer required work while still producing readable output.

Deferred required work must not be converted into a passing result.

### 9.9 Path traversal and symlink substitution

A source-bundle path may:

- escape its staging root;
- traverse through `..`;
- use an absolute path;
- use a symlink;
- point to a replaced file;
- point to a non-regular file.

All input paths must remain inside the authorized staging root and resolve to
regular, non-symlink files.

### 9.10 Duplicate-key ambiguity

A JSON object may contain the same key more than once.

Different parsers may retain:

- the first value;
- the last value;
- all values;
- no value because parsing fails.

Conflicting duplicate values for fields such as:

```text
revision
severity
sha256
document_type
result
policy_sha256
```

must not be interpreted by different components.

Every JSON carrier must reject duplicate object keys before schema validation.

Trusted YAML must reject duplicate mapping keys.

### 9.11 Resource exhaustion

An untrusted carrier may declare or contain an arbitrarily large document.

The verifier must enforce trusted per-carrier size limits from filesystem
metadata before:

- reading;
- hashing;
- decoding;
- parsing.

The untrusted bundle index cannot define its own accepted maximum.

### 9.12 Control-plane substitution

A subject revision may attempt to replace:

- the verifier;
- the expected verifier digest;
- the policy;
- the expected policy digest;
- the schema snapshot;
- the packet builder;
- the summary builder.

The trusted control plane must come from a separately resolved protected
revision.

A subject revision cannot approve itself by changing the checker and the
expected checker digest together.

### 9.13 Schema-snapshot substitution

A structurally valid but changed schema may accept fields that the reviewed
contract did not permit.

The policy, packet, report, and summary must preserve the exact reviewed
schema-snapshot identity and per-schema digests.

### 9.14 Summary substitution

A fabricated normalized summary may claim:

```text
verified_pass
```

while reusing valid source-bundle and policy digests.

The summary must be bound to the exact verifier-issued intake report by digest.

### 9.15 Credential exposure

The scanning process may inherit unrelated environment credentials.

The producer job must receive only the credentials required for the scan.

### 9.16 Mutable triage substitution

A mutable local workbench may classify a finding as a false positive.

Mutable triage state is not part of the v0 authority carrier.

### 9.17 Report projection substitution

A readable report or exported SARIF file may differ from the canonical JSON
bundle.

Only the verified canonical documents may drive the normalized summary.

### 9.18 Raw-finding publication

Raw findings may contain:

- source excerpts;
- vulnerable locations;
- attack paths;
- reproduction details;
- internal architecture details.

The raw bundle must not be uploaded as a normal Actions artifact of the public
repository.

---

## 10. End-to-end machine

The complete proposed machine is:

```text
protected exact control-plane revision
→ trusted control-plane checkout

exact selected subject Git revision
→ clean isolated subject checkout

trusted candidate policy
+
trusted verifier
+
trusted upstream schema snapshot
+
subject checkout
→ isolated Codex Security producer
→ completed canonical source bundle
→ producer receipt
→ same-runner source-bundle index
→ same-runner bundle identity
→ trusted intake packet
→ trusted intake verifier
→ verifier-issued intake report
→ intake-report-bound normalized summary
→ raw bundle private retention or deletion
→ sanitized candidate artifacts
→ inactive candidate gate fold-in
→ candidate proof
→ separate promotion review
```

The release-authority path remains:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ ALLOW or BLOCK
```

The Codex Security lane may connect to that path only after promotion.

---

## 11. Producer job design

### 11.1 Isolation

The producer must run in a dedicated ephemeral job.

The job must not reuse a long-lived development workspace.

The recommended first execution environment is a GitHub-hosted ephemeral
runner.

The job must use:

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
- cloud credentials unrelated to the scan;
- signing keys unrelated to the scan;
- release tokens;
- mutable production credentials.

### 11.2 Same-runner packaging requirement

The producer writes its state and results to runner-local storage.

A later GitHub-hosted job cannot read that runner-local storage.

The following operations must therefore complete in the same ephemeral job
before the producer runner exits:

```text
run scan
→ create producer receipt
→ verify expected source files exist
→ enforce trusted size limits
→ reject symlinks and path escape
→ calculate component digests
→ create source-bundle index
→ calculate bundle identity
→ build intake packet
→ verify intake
→ emit intake report
→ build normalized summary
→ privately retain or delete raw bundle
→ expose only sanitized outputs
```

A separate packaging job is forbidden unless an explicit access-controlled
secure transfer occurs before the producer job ends.

The first implementation must use the same-runner model.

### 11.3 Directory layout

Illustrative same-runner layout:

```text
${RUNNER_TEMP}/pulsemech-codex-security/
├── trusted-control-plane/
├── subject/
├── codex-state/
├── codex-results/
├── producer-receipts/
├── intake/
├── sanitized/
└── private-transfer/
```

Codex state and result directories must be outside:

```text
trusted-control-plane/
subject/
```

### 11.4 Package installation

The implementation must use a package version pinned by an exact dependency
lock.

A floating install is forbidden:

```text
@openai/codex-security@latest
```

The producer wrapper must record:

- package name;
- exact package version;
- package-lock digest;
- package integrity value when available;
- bundled plugin version;
- Codex runtime version;
- selected model;
- selected reasoning effort;
- Node.js version;
- Python version.

The expected values must come from the trusted candidate policy.

### 11.5 Scan command boundary

The producer should run Codex Security in report-producing mode.

The initial PULSEmech lane must not delegate release severity policy to the CLI.

The producer must not use the CLI process exit code as the release result.

The lane separately records:

```text
producer process completion
canonical bundle completion
canonical bundle verification
coverage verification
findings-policy result
```

A successful producer process may still contain blocking findings.

A failed producer process may leave partial files.

Partial files must not become accepted evidence.

### 11.6 Forbidden producer commands

The automated producer lane must not execute:

```text
codex-security patch
codex-security install-hook
automatic fix application
automatic git commit
automatic git push
automatic pull-request creation
```

A future repair workflow requires a separate design and authority boundary.

---

## 12. Producer receipt

The canonical Codex Security bundle does not by itself carry every
PULSEmech-required producer expectation.

A PULSEmech-controlled wrapper must produce:

```text
codex_security_producer_receipt_v0.json
```

The receipt should contain at least:

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
  scan_manifest_path: relative_path
  findings_path: relative_path
  coverage_path: relative_path
```

The receipt must not contain:

- API keys;
- access tokens;
- cookie values;
- credential paths containing secret material;
- full environment dumps;
- unrelated runner metadata;
- private-storage access URLs;
- private-storage credentials.

The receipt is a carrier.

It is not trusted merely because it exists.

Duplicate JSON keys in the receipt must be rejected.

---

## 13. Source-bundle index

The PULSEmech wrapper must produce an immutable source-bundle index before the
producer job ends:

```text
codex_security_source_bundle_index_v0.json
```

The index must identify:

```text
scan-manifest.json
findings.json
coverage.json
codex_security_producer_receipt_v0.json
```

For each file it must record:

- relative path;
- byte size;
- SHA-256;
- media type;
- regular-file result;
- symlink result.

The index is untrusted input to the later verifier.

Its own size, path, digest, JSON structure, and duplicate-key state must be
validated.

### 13.1 Deterministic bundle identity

The initial bundle identity should be calculated as:

```text
sha256(
  "pulsemech-codex-security-source-bundle-v0\n"
  + scan_manifest_sha256 + "\n"
  + findings_sha256 + "\n"
  + coverage_sha256 + "\n"
  + producer_receipt_sha256 + "\n"
)
```

The component order is fixed.

The digest strings use lowercase hexadecimal SHA-256.

The input paths do not participate in the bundle identity.

The index records both:

```text
component digests
bundle identity
```

---

## 14. Raw-bundle lifecycle and storage boundary

The raw source bundle contains:

```text
scan-manifest.json
findings.json
coverage.json
producer receipt
source-bundle index
scan-local evidence referenced by the canonical documents
```

### 14.1 Public Actions artifact prohibition

The raw source bundle must not be uploaded as a normal artifact of the public
PULSEmech repository.

The prohibition includes:

- direct raw-file upload;
- ZIP archives;
- TAR archives;
- unencrypted bundles;
- bundles renamed to appear non-sensitive;
- raw reports;
- raw SARIF;
- raw finding details.

### 14.2 Allowed initial retention modes

The initial candidate lane may use one of two modes.

#### `ephemeral_delete`

```text
raw bundle
→ same-runner verification
→ sanitized summary generation
→ raw bundle deletion before runner termination
```

This mode does not provide later raw-bundle replay.

#### `access_controlled_private_storage`

```text
raw bundle
→ same-runner verification
→ transfer to access-controlled private storage
→ transfer verification
→ sanitized storage receipt
→ local raw bundle deletion
```

Acceptable storage classes may include:

- an access-controlled private object store;
- a separate private repository;
- another explicitly access-controlled private evidence store.

The storage mechanism must not expose the raw bundle through the public
repository.

### 14.3 Fixed-source proof requirement

A fixed real-source proof intended for later independent replay requires:

```text
access_controlled_private_storage
```

An ephemeral-only real run may demonstrate execution.

It cannot demonstrate later raw-bundle replay.

### 14.4 Sanitized storage receipt

A private-storage transfer may produce a sanitized receipt containing:

- storage class;
- transfer completion state;
- encrypted object identity or non-secret object identifier;
- raw bundle identity;
- retention policy identity;
- deletion state for the runner-local copy.

The receipt must not contain:

- credentials;
- signed access URLs;
- encryption keys;
- secret bucket names when those names are sensitive;
- raw finding contents.

---

## 15. Intake staging boundary

The PULSEmech verifier must operate on a dedicated staging root on the same
runner that produced the raw source bundle.

Illustrative layout:

```text
${RUNNER_TEMP}/pulsemech-codex-security/intake/
├── source/
│   ├── scan-manifest.json
│   ├── findings.json
│   ├── coverage.json
│   ├── codex_security_producer_receipt_v0.json
│   └── codex_security_source_bundle_index_v0.json
├── packet/
│   └── codex_security_intake_packet_v0.json
└── reports/
```

The staging root must not be inside either Git checkout.

### 15.1 Trusted carrier limits

The initial trusted maximum sizes are:

```yaml
scan_manifest_max_bytes: 16777216
findings_max_bytes: 134217728
coverage_max_bytes: 33554432
producer_receipt_max_bytes: 1048576
source_bundle_index_max_bytes: 1048576
intake_packet_max_bytes: 1048576
intake_report_max_bytes: 4194304
normalized_summary_max_bytes: 4194304
source_record_max_bytes: 1048576
individual_schema_max_bytes: 4194304
candidate_policy_max_bytes: 1048576
```

These values must come from the protected candidate policy.

The bundle index cannot increase them.

The intake packet cannot independently increase them.

### 15.2 Pre-read validation order

Before reading or hashing a carrier, the verifier must establish:

```text
1. expected path supplied by trusted configuration
2. path normalization
3. staging-root containment
4. lstat result
5. regular-file status
6. symlink rejection
7. trusted maximum size
8. non-empty file
9. only then read bytes
10. calculate digest
11. decode
12. parse
```

The verifier must also establish:

- no duplicate resolved path exists;
- every calculated digest matches the source-bundle index where applicable.

A file exceeding its trusted limit must be rejected before hashing or parsing.

---

## 16. PULSEmech intake packet

The PULSEmech-controlled packet must be:

```text
codex_security_intake_packet_v0.json
```

The packet supplies recorded expectations.

The trust root is the protected control-plane checkout and workflow
configuration.

The packet is not permitted to authenticate itself.

### 16.1 Required packet fields

```yaml
document_type: pulsemech.codex-security-intake-packet
schema_version: "0.1"
record_status: example_or_observed
packet_scope: example_or_current_run

trusted_control_plane:
  repository_identity: string
  revision: full_commit_sha
  checkout_role: protected_control_plane
  policy_path: repository_relative_path
  policy_sha256: sha256
  verifier_path: repository_relative_path
  verifier_sha256: sha256
  verifier_version: string
  packet_builder_path: repository_relative_path
  packet_builder_sha256: sha256
  summary_builder_path: repository_relative_path
  summary_builder_sha256: sha256

schema_snapshot_binding:
  upstream_repository_identity: openai/codex-security
  upstream_revision: full_commit_sha
  source_record_path: repository_relative_path
  source_record_sha256: sha256
  aggregate_snapshot_sha256: sha256
  schemas:
    scan_manifest:
      path: repository_relative_path
      sha256: sha256
    findings:
      path: repository_relative_path
      sha256: sha256
    coverage:
      path: repository_relative_path
      sha256: sha256

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

carrier_limits:
  scan_manifest_max_bytes: integer
  findings_max_bytes: integer
  coverage_max_bytes: integer
  producer_receipt_max_bytes: integer
  source_bundle_index_max_bytes: integer
  intake_packet_max_bytes: integer
  intake_report_max_bytes: integer
  normalized_summary_max_bytes: integer

findings_policy_binding:
  policy_id: string
  policy_version: string
  policy_sha256: sha256

source_bundle:
  bundle_index_path: staged_relative_path
  bundle_index_sha256: sha256
  bundle_identity: sha256
```

### 16.2 Trusted-root resolution

Before reading the packet, the workflow must independently resolve:

- the trusted control-plane checkout root;
- the trusted control-plane repository identity;
- the trusted control-plane exact revision;
- the candidate policy path;
- the verifier absolute path.

The verifier must calculate its own:

- control-plane revision;
- policy digest;
- verifier digest;
- schema-snapshot digests.

The verifier then compares those calculated values with the packet.

It must not use packet-supplied paths to discover the trust root.

### 16.3 Expected-value independence

These values must come from the protected workflow or trusted candidate policy:

- expected subject Git revision;
- expected package version;
- expected plugin version;
- expected runtime version;
- expected model;
- expected reasoning effort;
- expected execution mode;
- expected coverage mode;
- expected paths;
- expected coverage state;
- expected policy identity;
- expected verifier identity;
- expected schema-snapshot identity;
- trusted carrier limits.

The packet builder must reject a mode that derives these expectations from:

- `scan-manifest.json`;
- `findings.json`;
- `coverage.json`;
- producer receipt;
- source-bundle index;
- report text;
- command output;
- subject-checkout policy files;
- subject-checkout verifier files.

A source artifact cannot supply its own expected identity.

### 16.4 Duplicate-key rejection

The packet must be parsed with duplicate-key rejection.

A packet containing a duplicate field is invalid even if both values are
identical.

---

## 17. Upstream schema-snapshot handling

PULSEmech verification must not depend on a live schema download.

The implementation should vendor a reviewed snapshot of the relevant upstream
Codex Security schemas inside the trusted control-plane checkout.

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

`SOURCE.json` should record:

- upstream repository identity;
- upstream commit;
- package version associated with the snapshot when known;
- retrieval date;
- individual file digests;
- license identity;
- reviewer note.

### 17.1 Deterministic schema-snapshot identity

The aggregate snapshot identity should be calculated as:

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

The order is fixed.

### 17.2 Required binding path

The exact schema-snapshot identity and per-schema digests must be preserved in:

```text
trusted candidate policy
→ intake packet
→ intake report
→ normalized summary
```

The verifier must calculate the digests from the trusted control-plane
checkout.

A package upgrade must not silently replace these files.

A subject checkout must not supply a schema used for verification.

### 17.3 Schema carrier validation

Before using a vendored schema, the verifier must establish:

- path containment inside the trusted control-plane checkout;
- regular-file status;
- symlink rejection;
- trusted maximum size;
- exact digest;
- UTF-8 validity;
- duplicate JSON key rejection;
- JSON parseability.

---

## 18. Intake verifier

The proposed verifier is:

```text
tools/check_codex_security_intake_packet_v0.py
```

The verifier must be sourced from the protected trusted control-plane
checkout.

The verifier must be offline and deterministic.

The same:

```text
trusted control-plane revision
+
trusted candidate policy
+
trusted schema snapshot
+
source bundle
+
intake packet
+
verifier version
```

must produce the same intake report.

### 18.1 Filesystem checks

The verifier must check:

- trusted control-plane-root containment;
- staging-root containment;
- regular-file status;
- symlink rejection;
- path normalization;
- duplicate resolved-path rejection;
- trusted maximum file sizes before reading;
- expected file presence;
- non-empty files;
- exact SHA-256 values;
- exact source-bundle identity.

### 18.2 Strict JSON and YAML checks

Every JSON carrier must be parsed with duplicate-key rejection.

The required sequence is:

```text
UTF-8 decode
→ strict duplicate-key-rejecting JSON parse
→ top-level type validation
→ schema validation
→ cross-document validation
```

The verifier must reject duplicate keys in:

```text
scan-manifest.json
findings.json
coverage.json
codex_security_producer_receipt_v0.json
codex_security_source_bundle_index_v0.json
codex_security_intake_packet_v0.json
SOURCE.json
vendored JSON schemas
```

Generated intake reports and summaries must be tested to ensure that their
serializers cannot emit duplicate keys.

Trusted YAML policy parsing must reject duplicate mapping keys.

### 18.3 Cross-document checks

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

The verifier must require:

```text
manifest findings reference == findings.json
manifest coverage reference == coverage.json
```

The verifier must independently calculate the findings and coverage digests.

Those digests must match the manifest artifact records.

### 18.4 Manifest checks

The verifier must require:

```text
manifest scan status == completed
```

The manifest target kind must equal:

```text
git_revision
```

The manifest target revision must equal:

```text
intake packet expected subject revision
```

A shortened SHA is insufficient.

A missing revision is insufficient.

A branch name is insufficient.

A tag name without resolved commit identity is insufficient.

### 18.5 Trusted control-plane checks

The verifier must independently establish:

```text
actual trusted repository identity
actual trusted revision
actual policy path and digest
actual verifier path and digest
actual verifier version
actual packet-builder path and digest
actual summary-builder path and digest
actual schema-snapshot identity
```

Those values must match:

- the protected workflow expectation;
- the trusted candidate policy;
- the intake packet.

A mismatch makes the evidence unverified.

The subject checkout must not be consulted for these values.

### 18.6 Producer identity checks

The verifier must compare:

```text
manifest producer identity
producer receipt identity
trusted candidate policy
intake packet expected producer identity
```

At minimum:

```text
manifest plugin version
==
producer receipt plugin version
==
expected plugin version
```

The package version, lock digest, runtime version, model, and reasoning effort
must match the trusted expectation.

Unknown or missing required producer identity fails closed.

### 18.7 Current-run checks

The producer receipt must match the current intake packet for:

- repository identity;
- workflow name;
- protected workflow revision;
- workflow run identifier;
- workflow run attempt;
- event name;
- ref;
- subject Git SHA.

A bundle from another workflow run must not satisfy the current-run lane.

A previous-run bundle must not be accepted because it evaluates the same path.

### 18.8 Recipe checks

The verifier must compare the actual scan recipe with the declared expected
recipe.

The following relations must match separately:

```text
producer requested execution mode
==
policy execution mode
```

```text
producer requested target scope
==
policy target scope
```

```text
coverage mode
==
policy expected coverage mode
```

```text
coverage inventory strategy
==
policy inventory strategy
```

The verifier must also compare:

- target kind;
- target revision;
- include paths;
- exclude paths.

Path-array comparison must use declared deterministic semantics.

The first implementation should require exact array equality after a declared
normalization step.

The normalization step must:

- reject absolute paths;
- reject `..`;
- normalize separators;
- reject duplicates;
- sort only if the policy declares order-insensitive semantics.

### 18.9 Coverage checks

The initial candidate policy must require:

```text
coverage.completeness == complete
```

It must also require:

```text
coverage.mode == repository
coverage.inventoryStrategy == repository
coverage.deferred is empty
```

Actual explicit exclusions must exactly match the policy allowlist.

An extra exclusion fails closed.

A missing required exclusion record fails closed if the policy expects it.

A reviewed surface with an unresolved or follow-up disposition must not be
treated as complete passing coverage.

The verifier must preserve:

- reviewed surface identifiers;
- surface dispositions;
- explicit exclusions;
- deferred units;
- open questions when present.

### 18.10 Findings checks

The verifier must validate:

- finding identifiers;
- occurrence identifiers;
- fingerprints;
- rule identifiers;
- severity structure;
- confidence structure when present;
- location structures;
- duplicate finding identity;
- supported severity values.

Supported severity values are:

```text
critical
high
medium
low
informational
```

The following conditions make the complete observation unverified:

- missing severity;
- malformed severity object;
- missing severity level;
- unsupported severity value;
- malformed finding;
- schema-invalid finding.

These conditions do not produce `verified_block`.

They produce:

```text
unverified
```

The verifier must not discard a finding because:

- confidence is low;
- remediation is missing;
- a readable report omits it;
- an exported SARIF file omits it;
- a mutable workbench classified it differently.

### 18.11 Findings-policy evaluation

The initial candidate policy is:

```yaml
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
triage_override: unsupported
```

The policy result is:

```text
findings_policy_pass == true
```

only when:

```text
canonical findings document is schema-valid
+
all findings use supported severity values
+
zero critical findings
+
zero high findings
```

Medium, low, and informational findings remain recorded.

They do not disappear from the summary.

### 18.12 No implicit pass

The verifier must never derive a passing findings policy from:

- an empty directory;
- a missing findings file;
- an empty findings file;
- malformed JSON;
- duplicate JSON keys;
- an unsupported schema version;
- a producer error;
- partial coverage;
- unknown coverage;
- missing surfaces;
- unapproved exclusions;
- deferred work;
- a missing severity;
- a malformed severity;
- an unsupported severity;
- absence of a readable report;
- process exit code zero;
- an untrusted policy;
- an untrusted verifier;
- an unverified schema snapshot;
- a file exceeding its trusted size limit.

Zero findings can contribute to a passing result only after every required
integrity, control-plane, schema, producer, subject, run, recipe, and coverage
check passes.

---

## 19. Intake report

The verifier must emit:

```text
codex_security_intake_report_v0.json
```

The report must be serialized deterministically.

The report should have one of three result classes:

```text
verified_pass
verified_block
unverified
```

### 19.1 `verified_pass`

This means:

- source bundle valid;
- source-bundle integrity valid;
- trusted control-plane identity valid;
- schema-snapshot identity valid;
- expected producer matched;
- current run matched;
- exact subject matched;
- expected recipe matched;
- coverage requirements passed;
- findings document valid;
- findings policy passed.

### 19.2 `verified_block`

This means:

- source bundle is valid and attributable;
- trusted control-plane identity passed;
- schema-snapshot identity passed;
- subject, producer, run, recipe, and coverage checks passed;
- the canonical findings document is valid;
- one or more supported blocking-severity findings are present.

Example:

```text
one verified high-severity finding
```

The evidence is valid.

Its policy result is blocking.

### 19.3 `unverified`

This means the evidence could not be accepted as a valid observation.

Examples:

- missing canonical file;
- oversized carrier;
- duplicate JSON key;
- digest mismatch;
- wrong revision;
- wrong producer;
- wrong run;
- wrong protected control-plane revision;
- verifier digest mismatch;
- policy digest mismatch;
- schema-snapshot mismatch;
- partial coverage;
- malformed JSON;
- unsupported schema;
- unexpected exclusion;
- deferred required work;
- missing severity;
- malformed severity;
- unsupported severity.

An unverified result must not be rewritten as:

```text
no vulnerabilities found
```

### 19.4 Required report bindings

The intake report must preserve:

```yaml
trusted_control_plane:
  repository_identity: string
  revision: full_commit_sha
  policy_path: string
  policy_sha256: sha256
  verifier_path: string
  verifier_sha256: sha256
  verifier_version: string
  packet_builder_path: string
  packet_builder_sha256: sha256
  summary_builder_path: string
  summary_builder_sha256: sha256

schema_snapshot_binding:
  upstream_repository_identity: string
  upstream_revision: full_commit_sha
  source_record_sha256: sha256
  aggregate_snapshot_sha256: sha256
  scan_manifest_schema_sha256: sha256
  findings_schema_sha256: sha256
  coverage_schema_sha256: sha256

intake_packet:
  path: string
  sha256: sha256

source_bundle:
  bundle_identity: sha256
  bundle_index_sha256: sha256
  scan_manifest_sha256: sha256
  findings_sha256: sha256
  coverage_sha256: sha256
  producer_receipt_sha256: sha256
```

The intake report cannot contain its own digest.

Its digest is calculated after serialization and recorded by the normalized
summary.

---

## 20. Reason codes

The intake report must use stable machine-readable reason codes.

Initial reason-code families should include:

```text
source_bundle_missing
source_bundle_path_escape
source_bundle_symlink
source_bundle_non_regular_file
source_bundle_empty_file
source_bundle_digest_mismatch
source_bundle_identity_mismatch

scan_manifest_size_limit_exceeded
findings_size_limit_exceeded
coverage_size_limit_exceeded
producer_receipt_size_limit_exceeded
source_bundle_index_size_limit_exceeded
intake_packet_size_limit_exceeded
schema_size_limit_exceeded
policy_size_limit_exceeded

manifest_parse_error
manifest_duplicate_json_key
manifest_schema_error
manifest_status_not_completed
manifest_artifact_record_missing
manifest_artifact_record_duplicate
manifest_artifact_digest_mismatch

findings_parse_error
findings_duplicate_json_key
findings_schema_error
findings_scan_id_mismatch
findings_duplicate_identity
findings_missing_severity
findings_malformed_severity
findings_unsupported_severity
findings_blocking_severity_present

coverage_parse_error
coverage_duplicate_json_key
coverage_schema_error
coverage_scan_id_mismatch
coverage_mode_mismatch
coverage_not_complete
coverage_inventory_strategy_mismatch
coverage_include_paths_mismatch
coverage_exclude_paths_mismatch
coverage_unapproved_exclusion
coverage_deferred_work_present
coverage_required_surface_unresolved

producer_receipt_parse_error
producer_receipt_duplicate_json_key
producer_receipt_schema_error
producer_package_mismatch
producer_plugin_mismatch
producer_runtime_mismatch
producer_model_mismatch
producer_reasoning_effort_mismatch

source_bundle_index_parse_error
source_bundle_index_duplicate_json_key
source_bundle_index_schema_error

intake_packet_parse_error
intake_packet_duplicate_json_key
intake_packet_schema_error

trusted_control_plane_repository_mismatch
trusted_control_plane_revision_mismatch
trusted_policy_path_mismatch
trusted_policy_digest_mismatch
trusted_policy_duplicate_mapping_key
trusted_verifier_path_mismatch
trusted_verifier_digest_mismatch
trusted_verifier_version_mismatch
trusted_packet_builder_digest_mismatch
trusted_summary_builder_digest_mismatch

schema_source_record_parse_error
schema_source_record_duplicate_json_key
schema_source_record_digest_mismatch
schema_snapshot_revision_mismatch
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

policy_identity_mismatch
policy_digest_mismatch

intake_report_binding_missing
intake_report_digest_mismatch
summary_verifier_identity_mismatch
summary_schema_snapshot_mismatch
```

Human-readable text may accompany the codes.

Human-readable text is not the machine decision surface.

---

## 21. Normalized PULSEmech summary

A verifier execution must support generation of:

```text
codex_security_summary_v0.json
```

The proposed builder is:

```text
tools/build_codex_security_summary_v0.py
```

The builder must come from the trusted control-plane checkout.

The builder must consume:

```text
verifier-issued intake report
+
calculated intake-report digest
+
verified canonical source documents when the report permits their use
+
trusted findings policy
```

It must not independently reinterpret unverified source files.

### 21.1 Intake-report binding

Before building the summary, the builder must:

- verify the intake report path;
- enforce the trusted intake-report size limit;
- reject symlinks;
- reject duplicate JSON keys;
- calculate the intake-report SHA-256;
- verify the report's control-plane identity;
- verify the report's schema-snapshot identity;
- verify the report's policy identity.

The summary must preserve the calculated intake-report digest.

### 21.2 Proposed summary shape

```json
{
  "document_type": "pulsemech.codex-security-summary",
  "schema_version": "0.1",
  "record_status": "observed",
  "subject": {
    "repository_identity": "HKati/pulse-release-gates-0.1",
    "target_kind": "git_revision",
    "revision": "<full-sha>"
  },
  "run_binding": {
    "workflow_name": "<name>",
    "workflow_revision": "<full-sha>",
    "run_id": "<id>",
    "run_attempt": 1,
    "event_name": "workflow_dispatch",
    "ref": "<ref>"
  },
  "producer": {
    "package_name": "@openai/codex-security",
    "package_version": "<exact>",
    "plugin_name": "<exact>",
    "plugin_version": "<exact>",
    "runtime_version": "<exact>",
    "model": "<exact>",
    "reasoning_effort": "<exact>"
  },
  "source_bundle": {
    "bundle_identity": "<sha256>",
    "scan_manifest_sha256": "<sha256>",
    "findings_sha256": "<sha256>",
    "coverage_sha256": "<sha256>",
    "producer_receipt_sha256": "<sha256>"
  },
  "coverage": {
    "mode": "repository",
    "completeness": "complete",
    "inventory_strategy": "repository",
    "include_paths": [],
    "exclude_paths": [],
    "explicit_exclusion_count": 0,
    "deferred_count": 0,
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
    "intake_report_path": "codex_security_intake_report_v0.json",
    "intake_report_sha256": "<sha256>",
    "trusted_control_plane_repository": "<identity>",
    "trusted_control_plane_revision": "<full-sha>",
    "verifier_path": "<path>",
    "verifier_sha256": "<sha256>",
    "verifier_version": "<version>",
    "summary_builder_path": "<path>",
    "summary_builder_sha256": "<sha256>"
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
  "raw_bundle_retention": {
    "mode": "ephemeral_delete",
    "public_actions_artifact_created": false,
    "private_storage_receipt_sha256": null
  },
  "authority": {
    "mode": "candidate_advisory",
    "release_effect": "none"
  }
}
```

The exact schema becomes normative only in the schema implementation pull
request.

### 21.3 Unverified summary behavior

If the intake report result is:

```text
unverified
```

the builder may emit a sanitized unverified summary.

It must not claim verified finding counts from a document that failed
validation.

Fields that cannot be established must be:

- omitted when the schema permits;
- explicitly `null`;
- marked unavailable by stable reason codes.

An unverified summary cannot contain:

```text
findings_policy_pass: true
```

### 21.4 Summary restrictions

The summary must not embed:

- complete source excerpts;
- complete attack-path narratives;
- credentials;
- access tokens;
- private workbench data;
- mutable triage state;
- generated patches;
- large raw logs;
- private-storage access URLs.

The summary may preserve:

- source digests;
- intake-report digest;
- non-secret storage receipt digest;
- severity counts;
- coverage state;
- stable reason codes.

---

## 22. Artifact publication boundary

### 22.1 Publicly uploadable sanitized artifacts

The public candidate workflow may upload:

```text
codex_security_intake_report_v0.json
codex_security_summary_v0.json
sanitized private-storage receipt when present
non-sensitive digest inventory
```

Before upload, each sanitized artifact must pass:

- schema validation;
- duplicate-key rejection;
- secret-pattern review;
- forbidden-field review;
- maximum-size enforcement;
- symlink rejection.

### 22.2 Forbidden public artifacts

The public candidate workflow must not upload:

```text
raw findings.json
raw report.md
raw SARIF
raw attack paths
raw source excerpts
raw scan-local evidence
raw complete source bundle
private-storage credentials
private-storage signed URLs
```

### 22.3 Workflow guard

The implementation should include a workflow guard that fails when a public
artifact upload path includes:

- the raw Codex results directory;
- `findings.json`;
- `report.md`;
- raw SARIF;
- the raw bundle directory;
- a broad parent directory containing raw results.

---

## 23. Candidate gate design

The proposed inactive gate-set identity is:

```text
codex_security_recorded_intake_candidate
```

The proposed gate members are:

```text
codex_security_evidence_present
codex_security_bundle_integrity_ok
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
codex_security_intake_verified
```

### 23.1 Gate semantics

#### `codex_security_evidence_present`

Literal `true` only when every required source-bundle component exists as a
regular non-symlink file and satisfies its trusted size limit.

#### `codex_security_bundle_integrity_ok`

Literal `true` only when every expected digest, manifest artifact relation,
and source-bundle identity passes.

#### `codex_security_trusted_control_plane_ok`

Literal `true` only when the protected control-plane repository, revision,
policy, verifier, packet builder, and summary builder match the independently
resolved trusted identities.

#### `codex_security_schema_snapshot_ok`

Literal `true` only when the upstream revision, source record, aggregate
snapshot identity, and all per-schema digests match the trusted policy.

#### `codex_security_producer_identity_ok`

Literal `true` only when package, plugin, runtime, model, and reasoning effort
match the independently declared expectation.

#### `codex_security_subject_binding_ok`

Literal `true` only when the canonical target is the exact expected repository
revision.

#### `codex_security_run_binding_ok`

Literal `true` only when the producer receipt belongs to the expected current
workflow run and attempt.

#### `codex_security_recipe_binding_ok`

Literal `true` only when execution mode, target scope, coverage mode,
inventory strategy, include paths, and exclude paths match the declared
recipe.

#### `codex_security_coverage_complete`

Literal `true` only when required coverage is complete, required surfaces are
resolved, exclusions are approved, and no required work is deferred.

#### `codex_security_findings_document_valid`

Literal `true` only when the canonical findings document is schema-valid,
duplicate-key-free, and every finding has a supported severity.

#### `codex_security_findings_policy_pass`

Literal `true` only when the valid canonical findings document passes the
declared blocking-severity policy.

#### `codex_security_intake_report_binding_ok`

Literal `true` only when the normalized summary is bound to the exact
verifier-issued intake report by digest and matching verifier identity.

#### `codex_security_intake_verified`

Literal `true` when the intake report result is:

```text
verified_pass
```

or:

```text
verified_block
```

A valid bundle containing a blocking finding may have:

```text
codex_security_intake_verified = true
codex_security_findings_document_valid = true
codex_security_findings_policy_pass = false
```

This preserves the distinction between:

```text
invalid evidence
```

and:

```text
valid evidence proving a blocking security state
```

### 23.2 Candidate-set boundary

The candidate set must not appear in:

- `core_required`;
- `required`;
- `release_required`;
- production blocking sets;
- stage blocking sets;
- tag-release required sets.

Tests must prove that the candidate set remains inactive.

Promotion requires a separate pull request.

---

## 24. Status fold-in boundary

The initial design does not select a final `status.json` namespace.

The later fold-in pull request must create a dedicated mapping.

It must not reduce the evidence to one generic scalar.

The folded state must preserve at least:

- evidence presence;
- source-bundle integrity;
- trusted control-plane identity;
- schema-snapshot identity;
- producer identity;
- subject binding;
- run binding;
- recipe binding;
- coverage completeness;
- finding counts;
- informational finding count;
- blocking finding count;
- findings-document validity;
- intake verification result;
- findings-policy result;
- intake-report digest;
- verifier identity;
- source-bundle identity;
- stable reason codes.

The fold-in must be deterministic.

The fold-in must independently validate:

```text
summary intake_report_sha256
==
calculated recorded intake-report SHA-256
```

The fold-in must also validate that:

- the report verifier identity matches the summary;
- the schema-snapshot identity matches the summary;
- the policy identity matches the summary;
- the trusted control-plane revision matches the declared lane.

The fold-in must not parse readable reports.

The fold-in must not accept unknown fields as success.

The fold-in must not create a literal passing gate from the absence of known
failures.

---

## 25. CLI exit-code boundary

The producer process exit code must be recorded.

It must not be treated as the PULSEmech gate result.

The lane distinguishes:

```text
process completed
canonical bundle completed
canonical bundle verified
trusted control plane verified
schema snapshot verified
coverage complete
findings document valid
findings policy passed
```

A report-only scan may complete while containing high-severity findings.

A runtime or incomplete-coverage failure may produce partial output.

Therefore:

```text
exit code 0
```

does not prove:

```text
codex_security_findings_policy_pass = true
```

and:

```text
output files exist
```

does not prove:

```text
codex_security_intake_verified = true
```

---

## 26. Findings-transition boundary

Codex Security may support comparison of findings across scans.

The initial authority lane must not depend on mutable comparison state.

The v0 lane evaluates one current, exact-revision source bundle.

A later transition design may represent:

```text
new
persisting
reopened
resolved
unknown
```

That later design must preserve this rule:

```text
a finding missing from a later incomplete scan is not proven resolved
```

Cross-scan comparison requires:

- both source bundles;
- both exact subject identities;
- both coverage states;
- both intake-report identities;
- deterministic matching evidence;
- explicit handling of ambiguous matches;
- a separate transition artifact;
- a separate verifier;
- a separate promotion boundary.

---

## 27. Public and private artifact boundary

Raw Codex Security findings may contain:

- source excerpts;
- vulnerable locations;
- attack paths;
- reproduction details;
- internal architecture details;
- remediation details.

The raw source bundle must remain:

```text
ephemeral on the producer runner
```

or:

```text
inside access-controlled private storage
```

The public repository may retain only:

- sanitized intake reports;
- sanitized normalized summaries;
- immutable digests;
- non-secret private-storage receipts;
- candidate proof records that do not expose raw findings.

Public artifacts must not expose:

- secrets;
- live credentials;
- private source;
- exploitable unpatched details;
- sensitive runner paths;
- unrelated environment metadata;
- private-storage access mechanisms.

The public summary may expose:

- subject revision;
- producer identity;
- source-bundle digests;
- intake-report digest;
- trusted control-plane identity;
- schema-snapshot identity;
- coverage state;
- severity counts;
- policy result;
- verification result;
- stable non-sensitive reason codes.

---

## 28. Failure matrix

| Condition | Evidence state | Candidate result |
|---|---|---|
| All source files absent | Not present | False |
| One canonical file missing | Unverified | False |
| Empty canonical file | Unverified | False |
| Carrier exceeds trusted size limit | Unverified | False |
| JSON parse failure | Unverified | False |
| Duplicate JSON key | Unverified | False |
| Trusted YAML duplicate mapping key | Unverified | False |
| Schema mismatch | Unverified | False |
| Manifest not completed | Unverified | False |
| Findings digest mismatch | Unverified | False |
| Coverage digest mismatch | Unverified | False |
| Source-bundle identity mismatch | Unverified | False |
| Symlinked input | Unverified | False |
| Path escapes staging root | Unverified | False |
| Trusted control-plane revision mismatch | Unverified | False |
| Policy digest mismatch | Unverified | False |
| Verifier digest mismatch | Unverified | False |
| Packet-builder digest mismatch | Unverified | False |
| Summary-builder digest mismatch | Unverified | False |
| Schema-snapshot identity mismatch | Unverified | False |
| Per-schema digest mismatch | Unverified | False |
| Producer package mismatch | Unverified | False |
| Plugin version mismatch | Unverified | False |
| Model mismatch | Unverified | False |
| Reasoning-effort mismatch | Unverified | False |
| Wrong repository | Unverified | False |
| Wrong subject revision | Unverified | False |
| Previous workflow run | Unverified | False |
| Wrong execution mode | Unverified | False |
| Wrong target scope | Unverified | False |
| Wrong coverage mode | Unverified | False |
| Wrong inventory strategy | Unverified | False |
| Wrong include paths | Unverified | False |
| Extra exclusion | Unverified | False |
| Coverage `partial` | Unverified | False |
| Coverage `unknown` | Unverified | False |
| Deferred required work | Unverified | False |
| Missing severity | Unverified | False |
| Malformed severity | Unverified | False |
| Unsupported severity | Unverified | False |
| Valid complete scan with critical finding | Verified block | False |
| Valid complete scan with high finding | Verified block | False |
| Valid complete scan with medium finding only | Verified pass under initial policy | True |
| Valid complete scan with low finding only | Verified pass under initial policy | True |
| Valid complete scan with informational finding only | Verified pass under initial policy | True |
| Valid complete scan with no findings | Verified pass | True |
| No findings with incomplete coverage | Unverified | False |
| Process exit zero with malformed bundle | Unverified | False |
| Readable report says pass but canonical finding blocks | Verified block | False |
| SARIF omits canonical high finding | Verified block | False |
| Summary missing intake-report digest | Unverified fold-in | False |
| Summary intake-report digest mismatch | Unverified fold-in | False |
| Raw bundle configured for public Actions upload | Invalid workflow boundary | False |

The candidate result in this table has no release effect before promotion.

---

## 29. Required tests

### 29.1 Schema tests

Tests must cover:

- valid source-bundle index;
- valid producer receipt;
- valid intake packet;
- valid intake report;
- valid normalized summary;
- required-field omission;
- unsupported schema version;
- wrong document type;
- invalid digest shape;
- invalid path shape;
- invalid Git revision shape.

### 29.2 Duplicate-key tests

Negative tests must cover duplicate JSON keys in:

- manifest;
- findings;
- coverage;
- producer receipt;
- source-bundle index;
- intake packet;
- source record;
- each vendored schema fixture;
- intake report input to the summary builder.

Authority-relevant duplicate-key fixtures should include:

```text
revision
severity
sha256
document_type
result
policy_sha256
verifier_sha256
aggregate_snapshot_sha256
```

Trusted policy tests must reject duplicate YAML mapping keys.

### 29.3 Filesystem and size-limit tests

Tests must cover:

- regular files;
- symlink rejection;
- path traversal;
- absolute paths;
- duplicate resolved paths;
- missing files;
- empty files;
- oversized manifest;
- oversized findings;
- oversized coverage;
- oversized receipt;
- oversized bundle index;
- oversized packet;
- replacement after index construction.

Tests must prove that an oversized file is rejected before:

- hashing;
- decoding;
- parsing.

### 29.4 Bundle-integrity tests

Tests must cover:

- correct component digests;
- modified manifest;
- modified findings;
- modified coverage;
- modified producer receipt;
- incorrect bundle identity;
- duplicate manifest artifact records;
- missing findings artifact record;
- missing coverage artifact record.

### 29.5 Cross-document tests

Tests must cover:

- matching scan identifiers;
- findings scan-ID mismatch;
- coverage scan-ID mismatch;
- receipt scan-ID mismatch;
- wrong findings reference;
- wrong coverage reference.

### 29.6 Trusted control-plane tests

Tests must cover:

- exact protected control-plane revision;
- wrong control-plane repository;
- wrong control-plane revision;
- verifier loaded from subject checkout;
- policy loaded from subject checkout;
- schema loaded from subject checkout;
- verifier digest mismatch;
- policy digest mismatch;
- packet-builder digest mismatch;
- summary-builder digest mismatch;
- subject replacing verifier and expected digest together;
- absolute trusted verifier path enforcement;
- sanitized executable environment.

### 29.7 Schema-snapshot tests

Tests must cover:

- exact upstream revision;
- exact source-record digest;
- exact aggregate snapshot identity;
- manifest-schema digest mismatch;
- findings-schema digest mismatch;
- coverage-schema digest mismatch;
- replaced schema with unchanged path;
- live schema download forbidden;
- subject-supplied schema rejected.

### 29.8 Subject-binding tests

Tests must cover:

- exact revision match;
- previous revision;
- shortened revision;
- branch name used as revision;
- missing revision;
- different repository;
- `git_worktree` rejected for candidate lane;
- `git_diff` rejected for candidate lane;
- `directory_snapshot` rejected for candidate lane.

### 29.9 Producer-binding tests

Tests must cover:

- exact package match;
- package mismatch;
- lock-digest mismatch;
- plugin mismatch;
- runtime mismatch;
- model mismatch;
- reasoning-effort mismatch;
- missing producer field.

### 29.10 Run-binding tests

Tests must cover:

- exact current run;
- previous run identifier;
- wrong run attempt;
- wrong workflow name;
- wrong protected workflow revision;
- wrong event;
- wrong ref;
- wrong subject Git SHA.

### 29.11 Recipe tests

Tests must cover:

- `standard` execution mode;
- execution-mode mismatch;
- repository target scope;
- target-scope mismatch;
- repository coverage mode;
- coverage-mode mismatch;
- repository inventory strategy;
- inventory-strategy mismatch;
- include-path mismatch;
- exclude-path mismatch.

### 29.12 Coverage tests

Tests must cover:

- complete repository coverage;
- partial coverage;
- unknown coverage;
- extra exclusion;
- missing declared exclusion;
- deferred unit;
- unresolved required surface.

### 29.13 Findings-policy tests

Tests must cover:

- zero findings;
- critical finding;
- high finding;
- medium finding;
- low finding;
- informational finding;
- mixed severities;
- missing severity;
- malformed severity;
- unsupported severity;
- duplicate finding identity;
- malformed finding;
- low-confidence high finding;
- report projection contradicting canonical findings;
- SARIF projection contradicting canonical findings.

Missing, malformed, and unsupported severity fixtures must produce:

```text
unverified
```

They must not produce:

```text
verified_block
```

### 29.14 Intake-report binding tests

Tests must cover:

- exact intake-report digest;
- missing intake-report digest;
- replaced intake report;
- summary built from another report;
- verifier identity mismatch between report and summary;
- schema-snapshot mismatch between report and summary;
- policy mismatch between report and summary.

### 29.15 Raw-artifact publication tests

Tests must prove that:

- raw findings are not uploaded;
- the raw results directory is not uploaded;
- broad parent-directory upload is rejected;
- sanitized report upload is allowed;
- sanitized summary upload is allowed;
- optional private-storage receipt contains no secret access data.

### 29.16 Same-runner lifecycle tests

Tests or workflow checks must prove that:

- scan output packaging occurs before the producer job exits;
- raw source files are not expected in a later ephemeral job;
- verification occurs before raw deletion;
- private transfer, when configured, completes before raw deletion;
- only sanitized outputs cross into later public jobs.

### 29.17 Deterministic replay tests

The same fixed:

```text
trusted control-plane revision
trusted policy
trusted schema snapshot
source bundle
intake packet
verifier
```

must produce:

- byte-identical machine result where timestamps are input-bound;
- identical reason codes;
- identical gate values;
- identical finding counts;
- identical source-bundle identity;
- identical schema-snapshot identity.

### 29.18 Activation-guard tests

Tests must prove that:

- the candidate set is registered only as candidate;
- it is absent from all active required sets;
- no workflow makes it a required release check;
- no release decision reads it as active authority;
- no generic external summary path implicitly promotes it.

---

## 30. Initial fixtures

The implementation should include fixed synthetic fixtures.

### 30.1 Positive fixture

```text
exact protected control-plane revision
exact trusted verifier and policy
exact schema snapshot
exact subject Git revision
valid completed manifest
valid findings document
valid complete coverage
zero critical findings
zero high findings
matching producer receipt
matching intake packet
```

Expected result:

```text
verified_pass
all candidate gates true
authority effect none
```

### 30.2 Blocking fixture

```text
exact protected control-plane revision
exact schema snapshot
exact subject Git revision
valid completed manifest
valid complete coverage
one high-severity finding
matching producer receipt
matching intake packet
```

Expected result:

```text
verified_block
integrity and binding gates true
findings-policy gate false
authority effect none
```

### 30.3 Subject-mismatch fixture

```text
valid-looking bundle
manifest revision differs from expected subject revision
```

Expected result:

```text
unverified
subject-binding gate false
candidate set not satisfied
authority effect none
```

### 30.4 Coverage-collapse fixture

```text
zero findings
coverage completeness partial
```

Expected result:

```text
unverified
coverage gate false
findings absence does not create pass
```

### 30.5 Control-plane-substitution fixture

```text
subject checkout contains modified verifier
subject checkout contains matching modified expected digest
trusted control-plane verifier remains unchanged
```

Expected result:

```text
subject verifier ignored
trusted verifier used
subject cannot approve itself
```

### 30.6 Duplicate-key fixture

```json
{
  "revision": "expected-sha",
  "revision": "attacker-sha"
}
```

Expected result:

```text
unverified
duplicate-key reason code emitted
```

### 30.7 Schema-snapshot mismatch fixture

```text
findings schema replaced
schema path unchanged
digest differs from trusted policy
```

Expected result:

```text
unverified
schema-snapshot gate false
```

### 30.8 Missing-severity fixture

```text
canonical finding has no severity.level
```

Expected result:

```text
unverified
not verified_block
```

### 30.9 Summary-substitution fixture

```text
valid source-bundle digests
fabricated summary claims verified_pass
summary does not bind the verifier-issued intake report
```

Expected result:

```text
intake-report-binding gate false
candidate set not satisfied
```

---

## 31. Candidate policy

A separate candidate policy file should be introduced during implementation.

Proposed path:

```text
policies/security/codex_security_candidate_policy_v0.yml
```

Proposed conceptual structure:

```yaml
policy:
  id: pulsemech_codex_security_candidate_policy
  version: "0.1"

trusted_control_plane:
  repository_identity: "HKati/pulse-release-gates-0.1"
  source: protected_workflow_revision
  require_separate_checkout_from_subject: true
  subject_may_select_revision: false

  policy_path: policies/security/codex_security_candidate_policy_v0.yml

  verifier:
    path: tools/check_codex_security_intake_packet_v0.py
    version: "0.1"

  packet_builder:
    path: tools/build_codex_security_intake_packet_v0.py

  summary_builder:
    path: tools/build_codex_security_summary_v0.py

schema_snapshot:
  upstream_repository_identity: openai/codex-security
  upstream_revision: "<full-sha>"
  source_record_path: "vendor/openai/codex-security/<full-sha>/SOURCE.json"
  source_record_sha256: "<sha256>"
  aggregate_snapshot_sha256: "<sha256>"

  schemas:
    scan_manifest:
      path: "vendor/openai/codex-security/<full-sha>/schemas/scan-manifest.schema.json"
      sha256: "<sha256>"

    findings:
      path: "vendor/openai/codex-security/<full-sha>/schemas/findings.schema.json"
      sha256: "<sha256>"

    coverage:
      path: "vendor/openai/codex-security/<full-sha>/schemas/coverage.schema.json"
      sha256: "<sha256>"

producer:
  package_name: "@openai/codex-security"
  package_version: "<exact>"
  package_lock_sha256: "<sha256>"
  plugin_name: "<exact>"
  plugin_version: "<exact>"
  runtime_version: "<exact>"
  model: "<exact>"
  reasoning_effort: "<exact>"

target:
  allowed_kind: git_revision
  require_full_revision: true
  require_clean_checkout: true

recipe:
  execution_mode: standard
  target_scope: repository
  expected_coverage_mode: repository
  inventory_strategy: repository
  include_paths: []
  exclude_paths: []

coverage:
  required_completeness: complete
  allowed_explicit_exclusions: []
  deferred_allowed: false
  unresolved_required_surfaces_allowed: false

carrier_limits:
  scan_manifest_max_bytes: 16777216
  findings_max_bytes: 134217728
  coverage_max_bytes: 33554432
  producer_receipt_max_bytes: 1048576
  source_bundle_index_max_bytes: 1048576
  intake_packet_max_bytes: 1048576
  intake_report_max_bytes: 4194304
  normalized_summary_max_bytes: 4194304
  source_record_max_bytes: 1048576
  individual_schema_max_bytes: 4194304
  candidate_policy_max_bytes: 1048576

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
  triage_override: unsupported

raw_bundle:
  public_actions_artifact_allowed: false
  allowed_retention_modes:
    - ephemeral_delete
    - access_controlled_private_storage

authority:
  mode: candidate_advisory
  release_effect: none
```

The policy digest must be calculated from the trusted control-plane checkout.

It must be recorded in:

```text
intake packet
intake report
normalized summary
```

The policy file must be parsed with duplicate-mapping-key rejection.

---

## 32. Workflow design

The initial workflow should be:

```text
.github/workflows/codex_security_candidate.yml
```

The first workflow must be manual.

It must run from a protected control-plane revision.

It must not run automatically on untrusted pull requests.

It must not expose a secret to untrusted fork code.

### 32.1 Conceptual workflow

```text
resolve-subject
→ codex-security-produce-package-verify
→ publish-sanitized-result
```

Raw files must not cross from the middle job into the final public job.

### 32.2 `resolve-subject`

Responsibilities:

- run from the protected workflow revision;
- record the trusted control-plane repository and exact revision;
- resolve the selected subject ref to a full commit;
- require an allowed subject repository;
- emit the expected subject identity;
- emit the expected workflow-run identity;
- reject subject selection that changes the control-plane revision.

This job emits only non-sensitive identifiers.

### 32.3 `codex-security-produce-package-verify`

This single ephemeral job performs every raw-data operation.

Responsibilities:

```text
1. checkout the protected trusted control plane

2. verify the trusted control-plane revision

3. load the trusted policy, verifier, builders, and schemas

4. checkout the subject into a separate root

5. verify the exact subject revision and clean state

6. install the pinned Codex Security package outside both worktrees

7. run the declared scan recipe

8. write Codex state and output outside both worktrees

9. create the producer receipt

10. enforce trusted carrier limits

11. reject symlinks and path escape

12. calculate component digests

13. create the source-bundle index

14. calculate the source-bundle identity

15. create the independently expected intake packet

16. run the trusted verifier

17. emit the intake report

18. calculate the intake-report digest

19. build the intake-report-bound sanitized summary

20. privately retain or delete the raw source bundle

21. upload only sanitized outputs for the next job
```

This job must never apply a patch.

### 32.4 `publish-sanitized-result`

Responsibilities:

- download only sanitized outputs;
- verify sanitized artifact digests;
- validate schemas;
- enforce sanitized size limits;
- run secret and forbidden-field checks;
- publish the intake report;
- publish the normalized summary;
- publish a non-secret storage receipt when present.

This job must never receive the raw source bundle.

### 32.5 Raw-bundle transfer prohibition

The workflow must not use a normal public-repository Actions artifact to move
the raw source bundle between jobs.

A future multi-job raw-data design requires:

- an access-controlled private transfer;
- explicit encryption and key boundaries where applicable;
- a separate design review.

### 32.6 Workflow status

The candidate workflow may fail when:

- the producer fails;
- the bundle is incomplete;
- verification fails;
- a blocking finding exists;
- private retention was required but failed;
- a public raw-artifact upload path is detected.

Its workflow conclusion is not a PULSEmech release decision before promotion.

---

## 33. Cost and interruption boundary

A scan may be interrupted by:

- cost limit;
- timeout;
- cancellation;
- rate limit;
- authentication failure;
- model-access failure;
- runtime error.

An interrupted scan may leave partial results.

The intake verifier must require completed canonical state.

A partial bundle is not accepted because it contains some findings.

A cost limit is an operational control.

It is not a coverage proof.

If a cost limit stops the required scan before completion:

```text
coverage requirement not established
→ evidence unverified
→ candidate result false
```

The raw partial bundle must follow the same private-or-delete lifecycle as a
completed raw bundle.

---

## 34. Package and contract upgrades

The package currently has a pre-1.0 public interface.

Every package or upstream contract upgrade must use a separate pull request.

The upgrade pull request must include:

- previous expected package version;
- new expected package version;
- previous plugin version;
- new plugin version;
- previous runtime version;
- new runtime version;
- previous model and reasoning effort;
- new model and reasoning effort when changed;
- previous vendored schema commit;
- new vendored schema commit;
- previous aggregate schema-snapshot digest;
- new aggregate schema-snapshot digest;
- per-schema digest changes;
- candidate-policy change;
- adapter compatibility review;
- verifier compatibility review;
- duplicate-key test replay;
- size-limit review;
- positive fixture replay;
- negative fixture replay;
- candidate proof regeneration.

The workflow must never follow a floating package version.

An upgrade must not silently change the scan recipe.

An upgrade must not silently replace the trusted schema snapshot.

---

## 35. Proposed implementation files

The implementation is expected to introduce files similar to:

```text
docs/security/
└── PULSEMECH_CODEX_SECURITY_EVIDENCE_LANE_DESIGN_v0.md

vendor/openai/codex-security/
└── <upstream-commit>/
    ├── LICENSE
    ├── SOURCE.json
    └── schemas/
        ├── scan-manifest.schema.json
        ├── findings.schema.json
        └── coverage.schema.json

policies/security/
└── codex_security_candidate_policy_v0.yml

schemas/security/
├── codex_security_producer_receipt_v0.schema.json
├── codex_security_source_bundle_index_v0.schema.json
├── codex_security_intake_packet_v0.schema.json
├── codex_security_intake_report_v0.schema.json
├── codex_security_summary_v0.schema.json
└── codex_security_private_storage_receipt_v0.schema.json

tools/
├── build_codex_security_source_bundle_index_v0.py
├── build_codex_security_intake_packet_v0.py
├── check_codex_security_intake_packet_v0.py
├── build_codex_security_summary_v0.py
└── check_codex_security_sanitized_publication_v0.py

ci/
├── check_codex_security_no_public_raw_artifact_v0.py
└── check_codex_security_candidate_activation_guard_v0.py

examples/security/
├── codex_security_producer_receipt_example_v0.json
├── codex_security_source_bundle_index_example_v0.json
├── codex_security_intake_packet_example_v0.json
├── codex_security_intake_report_example_v0.json
├── codex_security_summary_example_v0.json
└── codex_security_private_storage_receipt_example_v0.json

tests/
├── test_codex_security_source_bundle_index_v0.py
├── test_codex_security_intake_packet_v0.py
├── test_codex_security_duplicate_json_keys_v0.py
├── test_codex_security_trusted_control_plane_v0.py
├── test_codex_security_schema_snapshot_binding_v0.py
├── test_codex_security_carrier_size_limits_v0.py
├── test_codex_security_intake_verifier_v0.py
├── test_codex_security_summary_intake_report_binding_v0.py
├── test_codex_security_no_public_raw_artifact_v0.py
├── test_codex_security_candidate_gate_set_v0.py
└── test_codex_security_candidate_activation_guard_v0.py

.github/workflows/
└── codex_security_candidate.yml
```

Final filenames may change only through explicit implementation review.

---

## 36. Implementation sequence

### PR 1 — Design record

Add the initial design record.

Authority effect:

```text
none
```

### PR 1A — Review hardening

Correct the design to require:

- no raw findings in public Actions artifacts;
- same-runner producer packaging and verification;
- separate execution-mode and coverage-mode fields;
- duplicate-key rejection;
- a separate protected control-plane checkout;
- unverified classification for invalid severity;
- intake-report binding in the summary;
- trusted schema-snapshot bindings;
- trusted pre-read carrier-size limits.

Authority effect:

```text
none
```

### PR 2 — Upstream contract snapshot

Add:

- upstream source record;
- license record;
- vendored schemas;
- aggregate schema-snapshot identity;
- per-schema digest checks;
- duplicate-key checks;
- trusted-size checks;
- schema-source tests.

Authority effect:

```text
none
```

### PR 3 — PULSEmech carrier schemas

Add:

- producer receipt schema;
- source-bundle index schema;
- intake packet schema;
- synthetic examples;
- positive and negative schema tests;
- duplicate-key negative fixtures;
- size-limit policy fields.

Authority effect:

```text
none
```

### PR 4 — Trusted intake verifier

Add:

- protected control-plane binding;
- offline verifier;
- filesystem checks;
- pre-read size checks;
- duplicate-key rejection;
- bundle-integrity checks;
- cross-document checks;
- producer checks;
- subject checks;
- current-run checks;
- schema-snapshot checks;
- coverage checks;
- finding checks;
- reason codes;
- fixed fixtures.

Authority effect:

```text
none
```

### PR 5 — Intake report and normalized summary

Add:

- intake report schema;
- normalized summary schema;
- deterministic summary builder;
- intake-report digest binding;
- verifier-identity binding;
- schema-snapshot binding;
- sanitized output tests;
- replay tests.

Authority effect:

```text
none
```

### PR 6 — Inactive candidate registration

Add:

- candidate policy;
- candidate gate definitions;
- candidate gate-set registration;
- activation guards;
- proof that active required sets remain unchanged.

Authority effect:

```text
none
```

### PR 7 — Manual same-runner producer workflow

Add:

- protected workflow trigger;
- separate trusted and subject checkouts;
- exact-revision subject target;
- pinned package installation;
- minimal permissions;
- external state and result paths;
- same-runner packaging;
- same-runner intake verification;
- raw private-or-delete lifecycle;
- sanitized-only public artifacts;
- public raw-artifact guards.

Authority effect:

```text
none
```

### PR 8 — Fixed-source candidate proof

Record:

- exact trusted control-plane revision;
- exact subject revision;
- workflow run identity;
- producer identity;
- schema-snapshot identity;
- source-bundle identity;
- intake packet digest;
- intake report digest;
- normalized summary digest;
- expected candidate gate state;
- deterministic replay result;
- private raw-bundle retention receipt when replay is claimed.

Authority effect:

```text
none
```

### PR 9 — Promotion criteria

Define:

- operational stability threshold;
- package update process;
- schema-snapshot update process;
- coverage policy;
- cost policy;
- secret boundary;
- private-storage boundary;
- retention policy;
- required scan cadence;
- failure handling;
- exact promotion prerequisites.

Authority effect:

```text
none
```

### PR 10 — Separate promotion

Only this pull request may propose moving the candidate set into a required
release policy.

The promotion pull request must be independently reviewable.

The promotion pull request must not contain unrelated implementation work.

---

## 37. Promotion prerequisites

Promotion must not occur until all of the following are proven.

### 37.1 Trusted control-plane proof

- protected control-plane repository identity recorded;
- protected exact revision recorded;
- subject cannot select the control-plane revision;
- trusted and subject checkouts are separate;
- verifier sourced only from the trusted checkout;
- policy sourced only from the trusted checkout;
- schema snapshot sourced only from the trusted checkout;
- subject-supplied executable code excluded from verification;
- executable and module-loading environment sanitized.

### 37.2 Producer proof

- exact package identity recorded;
- exact plugin identity recorded;
- exact runtime identity recorded;
- exact model and reasoning effort recorded;
- package lock verified;
- minimal environment established;
- no unrelated credential inheritance;
- output outside both worktrees;
- no patch application.

### 37.3 Carrier proof

- every source file digest verified;
- source-bundle identity deterministic;
- duplicate JSON keys rejected;
- trusted size limits enforced before reading;
- source bundle retained privately when replay is claimed;
- raw bundle never exposed through public Actions artifacts.

### 37.4 Schema proof

- exact upstream repository identity recorded;
- exact upstream revision recorded;
- source-record digest recorded;
- aggregate snapshot identity recorded;
- per-schema digests recorded;
- schema snapshot preserved through packet, report, and summary;
- live schema download absent from verification.

### 37.5 Subject proof

- exact Git revision binding;
- current workflow-run binding;
- previous-run reuse rejected;
- wrong-revision fixture rejected;
- dirty-worktree substitution rejected.

### 37.6 Coverage proof

- complete required coverage;
- declared coverage mode;
- declared inventory strategy;
- exact include/exclude relation;
- unapproved exclusions rejected;
- deferred work rejected;
- incomplete coverage never converted into no-findings success.

### 37.7 Findings-policy proof

- critical finding blocks;
- high finding blocks;
- medium, low, and informational findings remain visible;
- missing severity produces unverified;
- malformed severity produces unverified;
- unsupported severity produces unverified;
- malformed finding produces unverified;
- readable projections cannot override canonical findings.

### 37.8 Intake-report binding proof

- summary records the exact intake-report digest;
- replaced report rejected;
- independently constructed summary rejected;
- verifier identity preserved through report and summary;
- schema-snapshot identity preserved through report and summary;
- fold-in validates the report-to-summary relation.

### 37.9 Workflow lifecycle proof

- producer, packaging, and raw verification occur on the same runner;
- no later job expects runner-local raw files;
- raw deletion occurs only after verification and summary generation;
- private transfer completes before deletion when enabled;
- only sanitized outputs cross into public publication jobs.

### 37.10 Determinism proof

- fixed bundle replay;
- fixed policy replay;
- fixed schema-snapshot replay;
- fixed verifier replay;
- identical gate output;
- identical reason-code output;
- no live network dependency in verification.

### 37.11 Authority proof

- only declared materialized gates affect release;
- candidate set inactive before promotion;
- no alternate release path;
- no scanner exit code used as release authority;
- no workflow name used as release authority;
- no report text used as release authority;
- no raw artifact presence used as release authority;
- `check_gates.py` remains the strict final evaluator.

---

## 38. Acceptance criteria for the completed candidate lane

The candidate lane is complete only when:

```text
1. A real Codex Security scan runs against an exact subject repository
   revision.

2. The workflow runs from an exact protected control-plane revision.

3. The trusted control-plane checkout is separate from the subject checkout.

4. The scan produces the three canonical JSON documents.

5. The producer wrapper records its independently reviewable identity.

6. The source bundle is indexed and digest-bound before the producer job ends.

7. Every JSON carrier rejects duplicate object keys.

8. Trusted YAML rejects duplicate mapping keys.

9. Trusted per-carrier size limits are enforced before reading, hashing, or
   parsing.

10. The intake packet supplies expectations independently of the source
    bundle.

11. The verifier validates the trusted policy, verifier, builders, and schema
    snapshot from the protected control-plane checkout.

12. The verifier rejects stale, mismatched, malformed, oversized, partial,
    substituted, and duplicate-key evidence.

13. The verifier distinguishes valid blocking evidence from invalid evidence.

14. Missing, malformed, and unsupported severity values produce unverified
    state.

15. The normalized summary preserves subject, producer, coverage, findings,
    policy, schema-snapshot, control-plane, and source-bundle identities.

16. The normalized summary binds the exact verifier-issued intake report by
    digest.

17. Raw findings never enter a normal public-repository Actions artifact.

18. Raw findings are deleted on the runner or transferred to access-controlled
    private storage.

19. Public artifacts contain only sanitized intake reports, summaries, and
    non-sensitive receipts.

20. The candidate gate set is fully materializable.

21. The candidate gate set remains absent from every active required set.

22. Positive, blocking, unverified, duplicate-key, control-plane-substitution,
    schema-mismatch, and summary-substitution fixtures reproduce
    deterministically.

23. A fixed real-run proof records its private retention state accurately.

24. No release authority changes occur.
```

---

## 39. Final boundary

The completed relation is intended to be:

```text
Codex Security
finds and records repository security observations

Protected PULSEmech control plane
supplies the trusted verifier, policy, builders, and schema snapshot

PULSEmech intake
proves which producer, run, subject, recipe, coverage state, and trusted
control plane produced and verified the observation

PULSEmech summary
binds its result to the exact verifier-issued intake report

PULSEmech policy
determines whether the verified findings satisfy the declared security rule

PULSEmech authority
remains the only mechanism that may convert materialized evidence into an
enforced release state
```

The security scanner does not replace PULSEmech.

PULSEmech does not replace the security scanner.

The connection between them is the verified evidence carrier.

Without that carrier:

```text
there is a scan
```

With the complete carrier, protected verifier, exact schema snapshot, complete
coverage relation, and intake-report-bound summary:

```text
there is reviewable, subject-bound security evidence
```

Only a later explicit promotion may make that evidence release-required.
