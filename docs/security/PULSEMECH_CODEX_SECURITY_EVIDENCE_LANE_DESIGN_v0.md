# PULSEmech Codex Security Evidence Lane Design v0

## Document state

```yaml
document_id: pulsemech_codex_security_evidence_lane_design_v0
document_type: design
revision: v0
revision_state: report_lifecycle_bound
status: design_only
authority_effect: none
gate_effect: none
policy_effect: none
schema_effect: none
ci_effect: none
release_effect: none
raw_public_artifact_effect: forbidden
private_intake_report_effect: required
public_summary_effect: sanitized_projection_only
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
  public repository;
- permit the verifier-issued intake report to be uploaded as a public artifact;
- permit a public normalized summary to create release state by itself.

Implementation and activation require separate pull requests.

---

## 1. Purpose

Codex Security can inspect a repository and produce structured security
findings together with a record of:

- the reviewed target;
- the executed scan recipe;
- the achieved coverage;
- the findings produced by that observation;
- scan-local evidence referenced by the canonical documents.

PULSEmech can use that output only after the output becomes a verified,
artifact-bound evidence carrier.

The intended relation is:

```text
Codex Security
produces a security observation

protected PULSEmech control plane
verifies the carrier, producer, subject, run, recipe, coverage, reference
closure, policy, and lifecycle relation

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
- an unverified adapter summary;
- an unverified intake report;
- a public summary;
- an unverified raw-bundle retention statement.

A Codex Security observation may participate in release-state evaluation only
through this path:

```text
exact subject revision
→ isolated Codex Security producer
→ completed canonical source documents
→ complete referenced-evidence closure
→ same-runner source-bundle packaging
→ protected PULSEmech control-plane verifier
→ exact subject and run binding
→ exact producer and recipe binding
→ exact schema-snapshot binding
→ complete declared coverage
→ deterministic findings-policy evaluation
→ private verifier-issued intake report
→ complete machine decision projection
→ completed raw-bundle lifecycle action
→ private lifecycle receipt
→ trusted sanitized-summary projection
→ private fold-in regeneration and equality check
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
referenced-evidence closure
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
raw-bundle lifecycle completion
summary-projection identity
```

A single numeric `rate` cannot preserve those relations.

The initial integration must therefore use:

```text
dedicated canonical source documents
dedicated referenced-evidence closure
dedicated producer receipt
dedicated source-bundle index
dedicated trusted control plane
dedicated intake packet
dedicated verifier
dedicated private intake report
dedicated private lifecycle receipt
dedicated public sanitized summary
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
- complete enumeration of supported local evidence references;
- exact binding of every retained raw-bundle component;
- a separately recorded producer receipt;
- immutable component digests;
- a deterministic source-bundle identity;
- trusted per-carrier size limits;
- trusted raw-bundle entry-count and total-size limits;
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
- a private machine-only intake report;
- a complete decision projection inside that intake report;
- a private raw-bundle lifecycle receipt;
- a public normalized summary built only after lifecycle completion;
- a normalized summary bound to the intake report and lifecycle receipt;
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
- raw findings in normal public-repository Actions artifacts;
- public summaries acting as release-authority inputs;
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

private_authority_carriers:
  intake_report_publication_allowed: false
  lifecycle_receipt_publication_allowed: false

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

The exact package version, plugin version, runtime version, model, reasoning
effort, expected paths, trusted verifier identity, trusted policy identity,
upstream schema snapshot, per-carrier size limits, raw-bundle total-size limit,
and raw-bundle entry-count limit must be bound by the candidate policy and
protected control-plane revision created during implementation.

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
- the source-bundle closure extractor;
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
- no trusted expected digest;
- no trusted source-bundle closure rules.

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
→ generated canonical source documents

canonical source documents
→ referenced-evidence closure extraction

generated source closure
→ same-runner packaging boundary

packaged source bundle
→ trusted PULSEmech intake verifier

verified bytes and parsed structures
→ private machine decision projection

private intake report
→ raw-bundle lifecycle action

completed lifecycle action
→ private lifecycle receipt

private intake report + private lifecycle receipt
→ trusted public-summary builder

private authority carriers
→ private fold-in regeneration

regenerated projection
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

A canonical document or referenced evidence file may be modified after
finalization.

Every retained raw-bundle component must be digest-verified.

### 9.4 Referenced-evidence substitution

A canonical document may reference scan-local evidence.

If that evidence is omitted from the source-bundle identity, it may be:

- replaced;
- removed;
- truncated;
- redirected;
- substituted through a symlink.

Every supported local evidence reference required for replay or validation must
resolve into the indexed source-bundle closure.

### 9.5 Producer substitution

A different package, plugin, wrapper, model, or runtime may produce a
structurally similar bundle.

Producer identity must be checked against an independent expected identity.

### 9.6 Recipe drift

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

### 9.7 Coverage collapse

A scan may complete after reviewing only part of the required surface.

The absence of findings under partial or unknown coverage must fail closed.

### 9.8 Exclusion injection

An attacker or configuration error may exclude a security-sensitive path.

The actual exclusions must exactly match the declared exclusion policy.

### 9.9 Deferred-work collapse

A scan may defer required work while still producing readable output.

Deferred required work must not be converted into a passing result.

### 9.10 Path traversal and symlink substitution

A source-bundle path may:

- escape its staging root;
- traverse through `..`;
- use an absolute path;
- use a symlink;
- point to a replaced file;
- point to a non-regular file.

All input paths must remain inside the authorized scan root or staging root and
resolve to regular, non-symlink files.

### 9.11 Duplicate-key ambiguity

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

### 9.12 Resource exhaustion

An untrusted carrier may declare or contain an arbitrarily large document or
an excessive number of referenced files.

The verifier must enforce trusted limits from filesystem metadata before:

- reading;
- hashing;
- decoding;
- parsing.

The verifier must also enforce:

- maximum source-bundle entry count;
- maximum individual referenced-evidence file size;
- maximum total source-bundle size.

The untrusted bundle index cannot define or increase those limits.

### 9.13 Control-plane substitution

A subject revision may attempt to replace:

- the verifier;
- the expected verifier digest;
- the policy;
- the expected policy digest;
- the schema snapshot;
- the packet builder;
- the summary builder;
- the reference-closure extractor.

The trusted control plane must come from a separately resolved protected
revision.

A subject revision cannot approve itself by changing the checker and the
expected checker digest together.

### 9.14 Schema-snapshot substitution

A structurally valid but changed schema may accept fields that the reviewed
contract did not permit.

The policy, packet, report, and summary must preserve the exact reviewed
schema-snapshot identity and per-schema digests.

### 9.15 Intake-report publication

A verifier-issued intake report may contain private machine state and
diagnostic relations.

The intake report must not be uploaded as a public artifact.

Public artifact guards must reject its path and filename.

### 9.16 Summary substitution

A fabricated normalized summary may preserve the original intake-report digest
while modifying:

- `verification.result`;
- finding counts;
- coverage state;
- `findings_policy_pass`;
- reason codes;
- lifecycle state.

The public summary cannot be trusted by metadata comparison alone.

The fold-in must regenerate the complete summary projection from the private
intake report and private lifecycle receipt.

### 9.17 Verification-use time gap

A verifier may check `findings.json` and a later summary builder may reopen a
replaced file.

The trusted summary builder must not read canonical source documents.

The verifier must produce the complete decision projection from the exact byte
buffers it verified.

### 9.18 Lifecycle-state fabrication

A summary may claim that raw evidence was privately retained or deleted before
that action completed.

The final public summary must be generated only after:

- the selected lifecycle action completes;
- its postconditions are checked;
- the private lifecycle receipt is finalized.

### 9.19 Credential exposure

The scanning process may inherit unrelated environment credentials.

The producer job must receive only the credentials required for the scan.

### 9.20 Mutable triage substitution

A mutable local workbench may classify a finding as a false positive.

Mutable triage state is not part of the v0 authority carrier.

### 9.21 Report projection substitution

A readable report or exported SARIF file may differ from the canonical JSON
bundle.

Only the verified canonical documents may drive the private decision
projection.

### 9.22 Raw-finding publication

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
trusted reference-closure extractor
+
trusted upstream schema snapshot
+
subject checkout
→ isolated Codex Security producer
→ completed canonical source documents
→ complete referenced-evidence closure
→ producer receipt
→ same-runner source-bundle index
→ same-runner bundle identity
→ trusted intake packet
→ trusted intake verifier
→ private machine-only intake report
→ private decision projection
→ raw-bundle lifecycle action
→ verified lifecycle postconditions
→ private lifecycle receipt
→ trusted sanitized-summary builder
→ public allowlisted summary
→ private fold-in regeneration
→ exact projection equality
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

A public normalized summary alone cannot connect to that path.

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

### 11.2 Same-runner requirement

The producer writes its state and results to runner-local storage.

A later GitHub-hosted job cannot read that runner-local storage.

The following operations must therefore complete in the same ephemeral job
before the producer runner exits:

```text
run scan
→ create producer receipt
→ identify canonical source documents
→ extract referenced-evidence closure
→ enforce trusted limits
→ reject symlinks and path escape
→ calculate component digests
→ create source-bundle index
→ calculate bundle identity
→ build intake packet
→ verify intake
→ emit private intake report
→ execute raw-bundle lifecycle action
→ verify lifecycle postconditions
→ emit private lifecycle receipt
→ build public sanitized summary
→ expose only public summary outputs
```

A separate raw-data packaging job is forbidden unless an explicit
access-controlled secure transfer occurs before the producer job ends.

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
├── private-authority/
├── public-summary/
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
reference-closure verification
coverage verification
findings-policy result
lifecycle completion
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
  scan_root: relative_identifier
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
- private-storage credentials;
- absolute runner paths.

The receipt is a carrier.

It is not trusted merely because it exists.

Duplicate JSON keys in the receipt must be rejected.

---

## 13. Complete source-bundle closure

The raw source bundle is the exact indexed set of files used for verification
or retained for replay.

No unindexed retained file may be described as part of the source bundle.

### 13.1 Required core entries

The source bundle must contain:

```text
scan-manifest.json
findings.json
coverage.json
codex_security_producer_receipt_v0.json
```

### 13.2 Referenced-evidence closure

The trusted reference-closure extractor must inspect the validated canonical
documents using rules bound to the vendored upstream schema snapshot.

It must enumerate every supported local path reference required for:

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

The initial candidate lane must reject:

- unresolved local references;
- unsupported authority-relevant reference forms;
- non-local references required for verification;
- missing referenced files;
- duplicate resolved paths with conflicting roles;
- references escaping the scan root;
- referenced directories;
- referenced sockets, devices, or other non-regular files.

### 13.3 Exact closure rule

The verifier must independently recompute the referenced-evidence closure.

The recomputed closure must exactly equal the source-bundle index entry set.

This means:

```text
required core entries
+
every supported referenced-evidence entry
==
indexed entry set
```

An indexed extra file fails closed in v0.

An omitted referenced file fails closed.

A later design may permit explicitly declared optional private diagnostic
entries.

### 13.4 Readable projections

Readable projections such as:

```text
report.md
SARIF
CSV
```

are not included merely because they exist.

If a canonical document contains an authority-relevant local reference to one
of them, that referenced file must be indexed and remains private.

If no canonical authority-relevant reference requires it, the projection must
not be added to the v0 source bundle.

---

## 14. Source-bundle index and identity

The PULSEmech wrapper must produce:

```text
codex_security_source_bundle_index_v0.json
```

before the producer job ends.

### 14.1 Index entry shape

Each indexed entry must record:

```yaml
path: normalized_posix_relative_path
role: canonical_document_or_producer_receipt_or_referenced_evidence
media_type: string
size_bytes: integer
sha256: lowercase_sha256
```

The index may separately record:

```yaml
referenced_by:
  - canonical_document_and_field_identifier
```

`referenced_by` is review metadata.

The canonical source documents already bind the reference relation.

### 14.2 Path normalization

Every indexed path must:

- be relative;
- use `/` separators;
- contain no empty segment;
- contain no `.` segment;
- contain no `..` segment;
- contain no backslash;
- contain no NUL;
- remain inside the authorized scan root;
- resolve to one regular non-symlink file.

Path strings must be normalized before sorting and comparison.

### 14.3 Deterministic entry ordering

Entries must be sorted by:

```text
normalized path UTF-8 bytes
then role UTF-8 bytes
```

No filesystem enumeration order may affect the index.

### 14.4 Canonical identity payload

The source-bundle identity must be calculated from this conceptual payload:

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
- object keys in lexicographic order;
- no insignificant whitespace;
- JSON string escaping;
- decimal integers without leading zeros;
- entries in the required deterministic order.

The source-bundle identity is:

```text
sha256(canonical_identity_payload_bytes)
```

### 14.5 Index self-boundary

The source-bundle index must not include itself as an entry.

This avoids recursive identity.

The index digest is calculated separately and recorded in:

```text
intake packet
intake report
normalized summary
private lifecycle receipt
```

### 14.6 Reference-closure record

The index must record:

```yaml
closure:
  required_core_entry_count: integer
  referenced_evidence_entry_count: integer
  total_entry_count: integer
  total_size_bytes: integer
  unresolved_reference_count: 0
  closure_complete: true
```

The verifier must recompute these values.

The index is untrusted input.

Its claims cannot replace recomputation.

---

## 15. Raw-bundle lifecycle and storage boundary

The raw source bundle contains exactly the files represented by the verified
source-bundle index.

The private authority package may additionally contain:

```text
codex_security_source_bundle_index_v0.json
codex_security_intake_packet_v0.json
codex_security_intake_report_v0.json
codex_security_raw_bundle_lifecycle_receipt_v0.json
```

### 15.1 Public Actions artifact prohibition

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
- raw finding details;
- the private intake report;
- the private lifecycle receipt;
- a broad parent directory containing any of those files.

### 15.2 Allowed initial retention modes

The initial candidate lane may use one of two modes.

#### `ephemeral_delete`

```text
raw bundle
→ same-runner verification
→ private intake report
→ raw bundle deletion
→ deletion postcondition verification
→ private lifecycle receipt
→ public sanitized summary
```

This mode does not provide later raw-bundle replay.

It may support only same-run candidate evaluation before the private carriers
are deleted.

#### `access_controlled_private_storage`

```text
raw bundle
→ same-runner verification
→ private intake report
→ transfer to access-controlled private storage
→ transferred bundle identity verification
→ runner-local raw bundle deletion
→ lifecycle postcondition verification
→ private lifecycle receipt
→ public sanitized summary
```

Acceptable storage classes may include:

- an access-controlled private object store;
- a separate private repository;
- another explicitly access-controlled private evidence store.

The storage mechanism must not expose the raw bundle through the public
repository.

### 15.3 Replay requirement

A fixed real-source proof intended for later independent replay requires:

```text
access_controlled_private_storage
```

The privately retained replay package must preserve:

- every indexed source-bundle entry;
- the source-bundle index;
- the intake packet;
- the intake report;
- the lifecycle receipt;
- their calculated digests.

An ephemeral-only real run may demonstrate execution.

It cannot demonstrate later raw-bundle replay.

### 15.4 Lifecycle completion boundary

A final public summary must not be created before the selected lifecycle action
has completed.

The required order is:

```text
verify intake
→ emit private intake report
→ calculate intake-report digest
→ execute lifecycle action
→ verify lifecycle postconditions
→ emit private lifecycle receipt
→ calculate lifecycle-receipt digest
→ build final public summary
```

If the lifecycle action fails:

```text
no final public summary
workflow fails closed
```

### 15.5 Storage information restrictions

No public artifact may contain:

- credentials;
- signed access URLs;
- encryption keys;
- secret object-store names;
- private repository access tokens;
- raw finding contents;
- absolute local storage paths.

---

## 16. Intake staging and trusted limits

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
│   ├── referenced-evidence/
│   └── codex_security_source_bundle_index_v0.json
├── packet/
│   └── codex_security_intake_packet_v0.json
└── private-reports/
```

The staging root must not be inside either Git checkout.

### 16.1 Trusted carrier limits

The initial trusted maximum sizes are:

```yaml
scan_manifest_max_bytes: 16777216
findings_max_bytes: 134217728
coverage_max_bytes: 33554432
producer_receipt_max_bytes: 1048576
source_bundle_index_max_bytes: 4194304
intake_packet_max_bytes: 1048576
intake_report_max_bytes: 8388608
lifecycle_receipt_max_bytes: 1048576
public_summary_max_bytes: 4194304
source_record_max_bytes: 1048576
individual_schema_max_bytes: 4194304
candidate_policy_max_bytes: 1048576
referenced_evidence_file_max_bytes: 67108864
raw_bundle_total_max_bytes: 536870912
raw_bundle_entry_max_count: 10000
```

These values must come from the protected candidate policy.

The bundle index cannot increase them.

The intake packet cannot independently increase them.

A later change to these values requires a reviewed policy update.

### 16.2 Pre-read validation order

Before reading or hashing a carrier, the verifier must establish:

```text
1. expected root supplied by trusted configuration
2. path normalization
3. authorized-root containment
4. no-follow open or equivalent symlink-safe open
5. file-descriptor metadata
6. regular-file status
7. trusted maximum size
8. non-empty file where required
9. only then read bytes from the same descriptor
10. calculate digest from those exact bytes
11. decode those exact bytes
12. parse those exact bytes
13. recheck descriptor metadata
14. reject replacement or mutation indicators
```

The verifier must also establish:

- no duplicate resolved path exists;
- total entry count is within the trusted maximum;
- total bundle size is within the trusted maximum;
- every calculated digest matches the recomputed index relation.

A file exceeding its trusted limit must be rejected before hashing or parsing.

### 16.3 Immutable verifier buffers

The verifier must calculate:

```text
digest
parsed object
decision projection
```

from the same immutable byte buffer for each file.

The verifier must not validate one read and derive the decision from another
read.

---

## 17. PULSEmech intake packet

The PULSEmech-controlled packet must be:

```text
codex_security_intake_packet_v0.json
```

The packet supplies recorded expectations.

The trust root is the protected control-plane checkout and workflow
configuration.

The packet is not permitted to authenticate itself.

### 17.1 Required packet fields

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
  reference_extractor_path: repository_relative_path
  reference_extractor_sha256: sha256
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
  lifecycle_receipt_max_bytes: integer
  public_summary_max_bytes: integer
  referenced_evidence_file_max_bytes: integer
  raw_bundle_total_max_bytes: integer
  raw_bundle_entry_max_count: integer

findings_policy_binding:
  policy_id: string
  policy_version: string
  policy_sha256: sha256

source_bundle:
  bundle_index_path: staged_relative_path
  bundle_index_sha256: sha256
  bundle_identity: sha256
  expected_entry_count: integer
  expected_total_size_bytes: integer

lifecycle_expectation:
  mode: ephemeral_delete_or_access_controlled_private_storage
  public_raw_artifact_allowed: false
  intake_report_publication_allowed: false
  lifecycle_receipt_publication_allowed: false
```

### 17.2 Trusted-root resolution

Before reading the packet, the workflow must independently resolve:

- the trusted control-plane checkout root;
- the trusted control-plane repository identity;
- the trusted control-plane exact revision;
- the candidate policy path;
- the verifier absolute path;
- the reference extractor absolute path.

The verifier must calculate its own:

- control-plane revision;
- policy digest;
- verifier digest;
- reference-extractor digest;
- schema-snapshot digests.

The verifier then compares those calculated values with the packet.

It must not use packet-supplied paths to discover the trust root.

### 17.3 Expected-value independence

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
- expected reference-extractor identity;
- expected schema-snapshot identity;
- trusted carrier limits;
- expected lifecycle mode.

The packet builder must reject a mode that derives these expectations from:

- `scan-manifest.json`;
- `findings.json`;
- `coverage.json`;
- producer receipt;
- source-bundle index;
- report text;
- command output;
- subject-checkout policy files;
- subject-checkout verifier files;
- subject-checkout reference-extractor files.

A source artifact cannot supply its own expected identity.

### 17.4 Duplicate-key rejection

The packet must be parsed with duplicate-key rejection.

A packet containing a duplicate field is invalid even if both values are
identical.

---

## 18. Upstream schema-snapshot handling

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

### 18.1 Deterministic schema-snapshot identity

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

### 18.2 Required binding path

The exact schema-snapshot identity and per-schema digests must be preserved in:

```text
trusted candidate policy
→ intake packet
→ private intake report
→ public normalized summary
```

The verifier must calculate the digests from the trusted control-plane
checkout.

A package upgrade must not silently replace these files.

A subject checkout must not supply a schema used for verification.

### 18.3 Schema carrier validation

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

## 19. Intake verifier

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

must produce the same private intake report.

### 19.1 Filesystem checks

The verifier must check:

- trusted control-plane-root containment;
- scan-root containment;
- staging-root containment;
- regular-file status;
- symlink rejection;
- path normalization;
- duplicate resolved-path rejection;
- trusted maximum file sizes before reading;
- trusted total bundle size;
- trusted maximum entry count;
- expected file presence;
- non-empty files where required;
- exact SHA-256 values;
- exact source-bundle identity;
- exact reference-closure equality.

### 19.2 Strict JSON and YAML checks

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

Generated private intake reports, lifecycle receipts, and public summaries must
be tested to ensure that their serializers cannot emit duplicate keys.

Trusted YAML policy parsing must reject duplicate mapping keys.

### 19.3 Cross-document checks

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

### 19.4 Reference-closure checks

The verifier must:

1. validate the canonical documents;
2. execute the trusted reference extractor;
3. normalize every supported local reference;
4. resolve each reference inside the scan root;
5. reject missing, escaping, symlinked, or non-regular targets;
6. calculate size and digest from the opened target;
7. rebuild the complete ordered index entry set;
8. compare the rebuilt set with the supplied source-bundle index;
9. recalculate the source-bundle identity.

The supplied index must not determine which references are checked.

The canonical documents and trusted extractor determine the required closure.

### 19.5 Manifest checks

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

### 19.6 Trusted control-plane checks

The verifier must independently establish:

```text
actual trusted repository identity
actual trusted revision
actual policy path and digest
actual verifier path and digest
actual verifier version
actual packet-builder path and digest
actual reference-extractor path and digest
actual summary-builder path and digest
actual schema-snapshot identity
```

Those values must match:

- the protected workflow expectation;
- the trusted candidate policy;
- the intake packet.

A mismatch makes the evidence unverified.

The subject checkout must not be consulted for these values.

### 19.7 Producer identity checks

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

### 19.8 Current-run checks

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

### 19.9 Recipe checks

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

### 19.10 Coverage checks

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

The verifier must preserve in its private decision projection:

- reviewed-surface count;
- unresolved-surface count;
- explicit-exclusion count;
- deferred-unit count;
- required-coverage result.

### 19.11 Findings checks

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

### 19.12 Findings-policy evaluation

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

They do not disappear from the private decision projection or public summary.

### 19.13 No implicit pass

The verifier must never derive a passing findings policy from:

- an empty directory;
- a missing findings file;
- an empty findings file;
- malformed JSON;
- duplicate JSON keys;
- an unsupported schema version;
- a producer error;
- an incomplete reference closure;
- a missing referenced file;
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
- an untrusted reference extractor;
- an unverified schema snapshot;
- a file exceeding its trusted size limit;
- a bundle exceeding its trusted entry or total-size limit.

Zero findings can contribute to a passing result only after every required
integrity, closure, control-plane, schema, producer, subject, run, recipe, and
coverage check passes.

### 19.14 Single-read decision construction

The verifier must construct the private decision projection from the same
in-memory parsed objects whose bytes were:

- read through validated descriptors;
- size-checked;
- hashed;
- duplicate-key checked;
- schema-validated.

The verifier must not reopen canonical source documents to calculate decision
fields.

---

## 20. Private intake report

The verifier must emit:

```text
codex_security_intake_report_v0.json
```

The report is a private authority carrier.

It must not be uploaded as a public Actions artifact.

The report must be serialized deterministically.

### 20.1 Machine-only report boundary

The intake report must use an exhaustive schema with:

```text
additionalProperties: false
```

at every authority-relevant object level.

It must not contain:

- source excerpts;
- vulnerable source paths intended for human display;
- attack narratives;
- remediation prose;
- arbitrary human-readable messages;
- arbitrary notes;
- free-form explanations;
- raw model responses;
- private-storage access data.

The report may contain:

- fixed identifiers;
- digests;
- enums;
- booleans;
- integers;
- bounded arrays of stable reason codes;
- normalized relative carrier paths required for private replay.

Human-readable security details remain in the privately controlled raw bundle.

### 20.2 Result classes

The report has one of three result classes:

```text
verified_pass
verified_block
unverified
```

#### `verified_pass`

This means:

- source bundle valid;
- source-bundle integrity valid;
- referenced-evidence closure complete;
- trusted control-plane identity valid;
- schema-snapshot identity valid;
- expected producer matched;
- current run matched;
- exact subject matched;
- expected recipe matched;
- coverage requirements passed;
- findings document valid;
- findings policy passed.

#### `verified_block`

This means:

- source bundle is valid and attributable;
- referenced-evidence closure is complete;
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

#### `unverified`

This means the evidence could not be accepted as a valid observation.

Examples:

- missing canonical file;
- missing referenced evidence;
- incomplete reference closure;
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

### 20.3 Required report bindings

The intake report must preserve:

```yaml
trusted_control_plane:
  repository_identity: string
  revision: full_commit_sha
  policy_sha256: sha256
  verifier_sha256: sha256
  verifier_version: string
  packet_builder_sha256: sha256
  reference_extractor_sha256: sha256
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
  sha256: sha256

source_bundle:
  bundle_identity: sha256
  bundle_index_sha256: sha256
  entry_count: integer
  total_size_bytes: integer
  referenced_evidence_count: integer
  scan_manifest_sha256: sha256
  findings_sha256: sha256
  coverage_sha256: sha256
  producer_receipt_sha256: sha256
```

The intake report cannot contain its own digest.

Its digest is calculated after serialization.

### 20.4 Complete decision projection

The intake report must contain a complete machine decision projection.

Conceptual shape:

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

The projection must contain every field required to:

- build the public normalized summary;
- compare a regenerated summary;
- derive future candidate gate state.

The public-summary builder must not obtain these values by reopening raw source
documents.

---

## 21. Reason codes

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
trusted_reference_extractor_digest_mismatch
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
intake_report_publication_forbidden

lifecycle_action_incomplete
lifecycle_postcondition_failed
lifecycle_receipt_missing
lifecycle_receipt_digest_mismatch
private_transfer_incomplete
private_transfer_bundle_identity_mismatch
local_raw_copy_not_deleted
public_raw_artifact_detected

summary_projection_mismatch
summary_decision_field_mismatch
summary_verifier_identity_mismatch
summary_schema_snapshot_mismatch
summary_lifecycle_binding_mismatch
summary_public_schema_error
summary_forbidden_field
summary_free_form_text_forbidden
```

The public summary may expose only reason codes allowed by its explicit public
schema.

It must not expose human-readable reason text.

---

## 22. Private raw-bundle lifecycle receipt

After the lifecycle action and postcondition checks complete, the trusted
control plane must emit:

```text
codex_security_raw_bundle_lifecycle_receipt_v0.json
```

The receipt is private.

It must not be uploaded as a public Actions artifact.

### 22.1 Receipt binding

The lifecycle receipt must bind:

```yaml
document_type: pulsemech.codex-security-raw-bundle-lifecycle-receipt
schema_version: "0.1"

source_bundle:
  bundle_identity: sha256
  bundle_index_sha256: sha256

intake_report:
  sha256: sha256

lifecycle:
  mode: ephemeral_delete_or_access_controlled_private_storage
  action_completed: boolean
  postconditions_passed: boolean
  public_raw_artifact_created: false
  runner_local_raw_copy_deleted: boolean
  private_transfer_completed: boolean
  private_storage_receipt_sha256: sha256_or_null
  retained_bundle_identity: sha256_or_null
  retention_policy_id: fixed_identifier_or_null
```

### 22.2 Ephemeral-delete postconditions

For:

```text
ephemeral_delete
```

the receipt may state success only when:

```text
runner-local indexed raw paths no longer exist
private transfer was not requested
public raw artifact was not created
```

### 22.3 Private-storage postconditions

For:

```text
access_controlled_private_storage
```

the receipt may state success only when:

```text
private transfer completed
retained bundle identity equals verified source-bundle identity
private storage receipt exists
runner-local indexed raw paths no longer exist
public raw artifact was not created
```

### 22.4 Receipt restrictions

The receipt must not contain:

- storage credentials;
- signed URLs;
- encryption keys;
- raw source paths;
- raw finding paths;
- raw finding details;
- free-form human text.

The receipt must use an exhaustive schema.

---

## 23. Public normalized summary

A completed lifecycle receipt permits generation of:

```text
codex_security_summary_v0.json
```

The proposed builder is:

```text
tools/build_codex_security_summary_v0.py
```

The builder must come from the trusted control-plane checkout.

### 23.1 Builder inputs

The builder may consume only:

```text
private verifier-issued intake report
+
calculated intake-report digest
+
private lifecycle receipt
+
calculated lifecycle-receipt digest
+
trusted public-summary schema
```

The builder must not read:

```text
scan-manifest.json
findings.json
coverage.json
referenced scan-local evidence
report.md
SARIF
```

The decision values come exclusively from:

```text
intake_report.decision_projection
```

The lifecycle values come exclusively from the verified private lifecycle
receipt.

### 23.2 Intake-report validation

Before building the public summary, the builder must:

- enforce the trusted intake-report size limit;
- reject symlinks;
- reject duplicate JSON keys;
- calculate the intake-report SHA-256;
- validate the private report schema;
- verify the report's control-plane identity;
- verify the report's schema-snapshot identity;
- verify the report's policy identity;
- verify the complete decision projection.

### 23.3 Lifecycle-receipt validation

Before building the public summary, the builder must:

- enforce the trusted lifecycle-receipt size limit;
- reject symlinks;
- reject duplicate JSON keys;
- calculate the lifecycle-receipt SHA-256;
- validate the private receipt schema;
- require completed lifecycle action;
- require passed postconditions;
- verify intake-report binding;
- verify source-bundle binding;
- require `public_raw_artifact_created: false`.

### 23.4 Public-summary allowlist

The public summary schema must use:

```text
additionalProperties: false
```

at every object level.

The public summary may contain only:

- fixed document identity;
- subject repository identity;
- exact subject revision;
- workflow identity;
- producer names and versions;
- source-bundle identity and counts;
- trusted control-plane identity and digests;
- schema-snapshot identity and digests;
- verification booleans;
- coverage counts and enums;
- finding counts;
- policy result;
- stable reason codes;
- intake-report digest;
- lifecycle-receipt digest;
- non-sensitive lifecycle result;
- authority mode and release effect.

The public summary must not contain:

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
- absolute runner paths;
- private report paths;
- raw evidence paths.

### 23.5 Proposed public-summary shape

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
    "bundle_index_sha256": "<sha256>",
    "entry_count": 4,
    "referenced_evidence_count": 0,
    "total_size_bytes": 0,
    "scan_manifest_sha256": "<sha256>",
    "findings_sha256": "<sha256>",
    "coverage_sha256": "<sha256>",
    "producer_receipt_sha256": "<sha256>"
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
    "lifecycle_receipt_sha256": "<sha256>",
    "trusted_control_plane_repository": "<identity>",
    "trusted_control_plane_revision": "<full-sha>",
    "verifier_sha256": "<sha256>",
    "verifier_version": "<version>",
    "reference_extractor_sha256": "<sha256>",
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
  "raw_bundle_lifecycle": {
    "mode": "ephemeral_delete",
    "action_completed": true,
    "postconditions_passed": true,
    "public_raw_artifact_created": false,
    "runner_local_raw_copy_deleted": true,
    "private_transfer_completed": false,
    "private_storage_receipt_sha256": null
  },
  "authority": {
    "mode": "candidate_advisory",
    "release_effect": "none",
    "public_summary_is_authority": false
  }
}
```

The exact schema becomes normative only in the schema implementation pull
request.

### 23.6 Unverified-summary behavior

If the private intake report result is:

```text
unverified
```

the builder may emit a sanitized public unverified summary only after the raw
lifecycle action succeeds.

It must not claim verified finding counts from a document that failed
validation.

Fields that cannot be established must be:

- omitted when the public schema permits;
- explicitly `null`;
- marked unavailable by stable reason codes.

An unverified summary cannot contain:

```text
findings_policy_pass: true
```

### 23.7 Deterministic public projection

The same:

```text
private intake report
+
private lifecycle receipt
+
trusted summary builder
+
trusted public-summary schema
```

must produce byte-identical canonical summary bytes.

The builder must use a declared canonical JSON serialization.

---

## 24. Artifact publication boundary

### 24.1 Publicly uploadable artifacts

The public candidate workflow may upload only:

```text
codex_security_summary_v0.json
detached digest or signature for that summary
```

A separate explicitly reviewed public attestation may be added later.

### 24.2 Publicly forbidden artifacts

The public candidate workflow must not upload:

```text
codex_security_intake_report_v0.json
codex_security_raw_bundle_lifecycle_receipt_v0.json
codex_security_intake_packet_v0.json
codex_security_source_bundle_index_v0.json
raw findings.json
raw report.md
raw SARIF
raw attack paths
raw source excerpts
raw scan-local evidence
raw complete source bundle
private-storage credentials
private-storage signed URLs
a broad parent directory containing any forbidden file
```

### 24.3 Publication checks

Before public upload, the final summary must pass:

- strict public schema validation;
- duplicate-key rejection;
- exhaustive field allowlist;
- forbidden-field review;
- free-form-text prohibition;
- maximum-size enforcement;
- symlink rejection;
- canonical serialization check;
- summary digest calculation.

Generic secret-pattern scanning may be an additional check.

It is not a substitute for the exhaustive public schema.

### 24.4 Workflow guard

The implementation must include a workflow guard that fails when a public
artifact upload path includes:

- the raw Codex results directory;
- `findings.json`;
- `report.md`;
- raw SARIF;
- the raw bundle directory;
- the private intake report;
- the private lifecycle receipt;
- the source-bundle index;
- a broad parent directory containing private or raw files.

---

## 25. Candidate gate design

The proposed inactive gate-set identity is:

```text
codex_security_recorded_intake_candidate
```

The proposed gate members are:

```text
codex_security_evidence_present
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
codex_security_raw_lifecycle_complete
codex_security_summary_projection_ok
codex_security_intake_verified
```

### 25.1 Gate semantics

#### `codex_security_evidence_present`

Literal `true` only when every required core component and referenced-evidence
component exists as a regular non-symlink file and satisfies trusted limits.

#### `codex_security_bundle_integrity_ok`

Literal `true` only when every expected digest, manifest artifact relation,
indexed entry, and source-bundle identity passes.

#### `codex_security_reference_closure_complete`

Literal `true` only when the trusted extractor's recomputed reference closure
exactly equals the indexed source-bundle entry set and no required reference is
unresolved.

#### `codex_security_trusted_control_plane_ok`

Literal `true` only when the protected control-plane repository, revision,
policy, verifier, packet builder, reference extractor, and summary builder
match the independently resolved trusted identities.

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

Literal `true` only when the recorded intake-report digest and trusted verifier
identity match the private verifier-issued report.

#### `codex_security_raw_lifecycle_complete`

Literal `true` only when:

- the selected raw-bundle lifecycle action completed;
- lifecycle postconditions passed;
- the lifecycle receipt binds the source bundle and intake report;
- no public raw artifact was created.

#### `codex_security_summary_projection_ok`

Literal `true` only when the trusted summary builder regenerates the expected
public summary from the private intake report and lifecycle receipt and the
canonical bytes exactly match the recorded public summary.

#### `codex_security_intake_verified`

Literal `true` when the private intake report result is:

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

### 25.2 Candidate-set boundary

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

## 26. Status fold-in boundary

The initial design does not select a final `status.json` namespace.

The later fold-in pull request must create a dedicated mapping.

It must not reduce the evidence to one generic scalar.

### 26.1 Private authority inputs

A release-capable fold-in must receive:

```text
private intake report
private lifecycle receipt
recorded public summary
trusted summary builder
trusted candidate policy
trusted public-summary schema
```

A public summary without the private report and lifecycle receipt is:

```text
advisory display only
```

It cannot create candidate or release state.

### 26.2 Required fold-in validation

The fold-in must:

1. validate the private intake report;
2. calculate the intake-report digest;
3. validate the private lifecycle receipt;
4. calculate the lifecycle-receipt digest;
5. verify report-to-receipt bindings;
6. regenerate the canonical public summary with the trusted builder;
7. compare regenerated bytes with the recorded public summary;
8. derive gate inputs from the private report decision projection;
9. reject any mismatch.

The fold-in must not trust decision values read only from the public summary.

### 26.3 Decision-field equality

The regeneration check must cover every public decision field, including:

```text
verification.result
all verification booleans
coverage mode
coverage completeness
coverage counts
all finding counts
blocking count
findings_policy_pass
reason codes
source-bundle identity
intake-report digest
lifecycle-receipt digest
lifecycle result
authority mode
```

A summary that preserves correct metadata but changes one decision field must
fail closed.

### 26.4 Source re-reading prohibition

The fold-in and summary builder must not reopen raw canonical source documents.

Authority-relevant values come from the private intake report decision
projection.

Independent replay from privately retained raw evidence must rerun the trusted
verifier and produce a new intake report before fold-in.

### 26.5 Folded state

The folded state must preserve at least:

- evidence presence;
- source-bundle integrity;
- reference-closure completeness;
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
- lifecycle-receipt digest;
- lifecycle completion;
- summary-regeneration result;
- verifier identity;
- source-bundle identity;
- stable reason codes.

The fold-in must be deterministic.

The fold-in must not parse readable reports.

The fold-in must not accept unknown fields as success.

The fold-in must not create a literal passing gate from the absence of known
failures.

---

## 27. CLI exit-code boundary

The producer process exit code must be recorded.

It must not be treated as the PULSEmech gate result.

The lane distinguishes:

```text
process completed
canonical source documents completed
reference closure completed
canonical bundle verified
trusted control plane verified
schema snapshot verified
coverage complete
findings document valid
findings policy passed
raw lifecycle completed
summary projection matched
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

## 28. Findings-transition boundary

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

- both complete source bundles;
- both exact subject identities;
- both reference closures;
- both coverage states;
- both private intake-report identities;
- both lifecycle receipts;
- deterministic matching evidence;
- explicit handling of ambiguous matches;
- a separate transition artifact;
- a separate verifier;
- a separate promotion boundary.

---

## 29. Failure matrix

| Condition | Evidence state | Candidate result |
|---|---|---|
| All source files absent | Not present | False |
| One canonical file missing | Unverified | False |
| Required referenced evidence missing | Unverified | False |
| Referenced evidence unindexed | Unverified | False |
| Indexed entry not required by closure | Unverified | False |
| Reference closure incomplete | Unverified | False |
| Empty canonical file | Unverified | False |
| Carrier exceeds trusted size limit | Unverified | False |
| Bundle entry count exceeds trusted limit | Unverified | False |
| Bundle total size exceeds trusted limit | Unverified | False |
| JSON parse failure | Unverified | False |
| Duplicate JSON key | Unverified | False |
| Trusted YAML duplicate mapping key | Unverified | False |
| Schema mismatch | Unverified | False |
| Manifest not completed | Unverified | False |
| Findings digest mismatch | Unverified | False |
| Coverage digest mismatch | Unverified | False |
| Referenced-evidence digest mismatch | Unverified | False |
| Source-bundle identity mismatch | Unverified | False |
| Symlinked input | Unverified | False |
| Path escapes authorized root | Unverified | False |
| Trusted control-plane revision mismatch | Unverified | False |
| Policy digest mismatch | Unverified | False |
| Verifier digest mismatch | Unverified | False |
| Reference-extractor digest mismatch | Unverified | False |
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
| Public intake-report upload configured | Invalid workflow boundary | False |
| Public lifecycle-receipt upload configured | Invalid workflow boundary | False |
| Raw bundle configured for public Actions upload | Invalid workflow boundary | False |
| Lifecycle action fails after verification | No final summary | False |
| Private transfer identity mismatch | No final summary | False |
| Local raw copy remains after required deletion | No final summary | False |
| Summary built before lifecycle completion | Invalid lifecycle ordering | False |
| Summary builder reopens changed findings file | Forbidden implementation path | False |
| Public summary changes `verified_block` to `verified_pass` | Projection mismatch | False |
| Public summary changes a finding count | Projection mismatch | False |
| Public summary changes `findings_policy_pass` | Projection mismatch | False |
| Public summary available without private report | Advisory only | No authority |
| Public summary available without lifecycle receipt | Advisory only | No authority |

The candidate result in this table has no release effect before promotion.

---

## 30. Required tests

### 30.1 Schema tests

Tests must cover:

- valid source-bundle index;
- valid producer receipt;
- valid intake packet;
- valid private intake report;
- valid private lifecycle receipt;
- valid public normalized summary;
- required-field omission;
- unsupported schema version;
- wrong document type;
- invalid digest shape;
- invalid path shape;
- invalid Git revision shape;
- `additionalProperties: false` enforcement.

### 30.2 Duplicate-key tests

Negative tests must cover duplicate JSON keys in:

- manifest;
- findings;
- coverage;
- producer receipt;
- source-bundle index;
- intake packet;
- source record;
- each vendored schema fixture;
- private intake report input;
- private lifecycle receipt input;
- public summary input.

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
findings_policy_pass
blocking_count
action_completed
```

Trusted policy tests must reject duplicate YAML mapping keys.

### 30.3 Filesystem and size-limit tests

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
- oversized referenced evidence;
- oversized receipt;
- oversized bundle index;
- oversized packet;
- excessive entry count;
- excessive total bundle size;
- replacement during read;
- replacement after index construction.

Tests must prove that an oversized file is rejected before:

- hashing;
- decoding;
- parsing.

### 30.4 Reference-closure tests

Tests must cover:

- zero referenced-evidence files;
- one valid referenced file;
- multiple deterministically ordered referenced files;
- missing referenced file;
- referenced symlink;
- referenced path escape;
- unsupported required reference;
- unindexed referenced file;
- indexed extra file;
- duplicate reference to the same file;
- conflicting roles for the same resolved file;
- modified referenced evidence with unchanged canonical documents;
- complete closure replay.

### 30.5 Bundle-integrity tests

Tests must cover:

- correct component digests;
- modified manifest;
- modified findings;
- modified coverage;
- modified producer receipt;
- modified referenced evidence;
- incorrect bundle identity;
- nondeterministic input order;
- duplicate manifest artifact records;
- missing findings artifact record;
- missing coverage artifact record;
- bundle index self-entry rejection.

### 30.6 Cross-document tests

Tests must cover:

- matching scan identifiers;
- findings scan-ID mismatch;
- coverage scan-ID mismatch;
- receipt scan-ID mismatch;
- wrong findings reference;
- wrong coverage reference.

### 30.7 Trusted control-plane tests

Tests must cover:

- exact protected control-plane revision;
- wrong control-plane repository;
- wrong control-plane revision;
- verifier loaded from subject checkout;
- policy loaded from subject checkout;
- schema loaded from subject checkout;
- reference extractor loaded from subject checkout;
- verifier digest mismatch;
- policy digest mismatch;
- packet-builder digest mismatch;
- reference-extractor digest mismatch;
- summary-builder digest mismatch;
- subject replacing verifier and expected digest together;
- absolute trusted verifier path enforcement;
- sanitized executable environment.

### 30.8 Schema-snapshot tests

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

### 30.9 Subject-binding tests

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

### 30.10 Producer-binding tests

Tests must cover:

- exact package match;
- package mismatch;
- lock-digest mismatch;
- plugin mismatch;
- runtime mismatch;
- model mismatch;
- reasoning-effort mismatch;
- missing producer field.

### 30.11 Run-binding tests

Tests must cover:

- exact current run;
- previous run identifier;
- wrong run attempt;
- wrong workflow name;
- wrong protected workflow revision;
- wrong event;
- wrong ref;
- wrong subject Git SHA.

### 30.12 Recipe tests

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

### 30.13 Coverage tests

Tests must cover:

- complete repository coverage;
- partial coverage;
- unknown coverage;
- extra exclusion;
- missing declared exclusion;
- deferred unit;
- unresolved required surface.

### 30.14 Findings-policy tests

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

### 30.15 Single-read verifier tests

Tests must prove that:

- digest and parse use the same bytes;
- decision projection uses the validated parsed object;
- file replacement after verification cannot change the report;
- the verifier does not reopen canonical files for decision construction;
- post-read metadata mismatch fails closed.

### 30.16 Private intake-report tests

Tests must prove that:

- report schema is exhaustive;
- arbitrary message fields are rejected;
- source excerpts are rejected;
- attack narratives are rejected;
- free-form notes are rejected;
- complete decision projection is present;
- report publication through public artifact configuration is rejected.

### 30.17 Lifecycle tests

Tests must cover:

- successful ephemeral deletion;
- failed ephemeral deletion;
- successful private transfer;
- failed private transfer;
- transferred bundle identity mismatch;
- missing private storage receipt;
- local raw copy remaining after transfer;
- public raw artifact detected;
- lifecycle receipt generated before action completion;
- lifecycle receipt generated after verified postconditions.

### 30.18 Public-summary builder tests

Tests must prove that:

- builder consumes only the private intake report and lifecycle receipt;
- builder does not open canonical source documents;
- builder does not open referenced evidence;
- builder rejects report-digest mismatch;
- builder rejects lifecycle-receipt mismatch;
- builder rejects incomplete lifecycle state;
- builder emits no free-form text;
- builder emits only allowlisted fields;
- canonical output is byte-deterministic.

### 30.19 Summary-regeneration tests

Tests must cover:

- exact regenerated summary;
- changed `verification.result`;
- changed critical count;
- changed high count;
- changed blocking count;
- changed coverage state;
- changed `findings_policy_pass`;
- changed reason codes;
- changed lifecycle state;
- changed intake-report digest;
- changed lifecycle-receipt digest;
- changed control-plane identity;
- changed schema-snapshot identity.

Every changed decision field must make:

```text
codex_security_summary_projection_ok = false
```

### 30.20 Publication tests

Tests must prove that:

- the public summary may be uploaded;
- the private intake report may not be uploaded;
- the private lifecycle receipt may not be uploaded;
- the source-bundle index may not be uploaded;
- raw findings may not be uploaded;
- the raw results directory may not be uploaded;
- broad parent-directory upload is rejected;
- arbitrary public summary fields are rejected;
- free-form public summary text is rejected.

### 30.21 Same-runner lifecycle tests

Tests or workflow checks must prove that:

- scan output packaging occurs before the producer job exits;
- raw source files are not expected in a later ephemeral job;
- verification occurs before lifecycle action;
- lifecycle postconditions occur before final summary creation;
- private transfer completes before local deletion when configured;
- only the final public summary crosses into later public jobs.

### 30.22 Deterministic replay tests

The same fixed:

```text
trusted control-plane revision
trusted policy
trusted schema snapshot
source bundle
source-bundle index
intake packet
verifier
lifecycle receipt
summary builder
```

must produce:

- byte-identical private intake-report decision projection;
- identical reason codes;
- identical gate inputs;
- identical finding counts;
- identical source-bundle identity;
- identical schema-snapshot identity;
- byte-identical public normalized summary.

### 30.23 Activation-guard tests

Tests must prove that:

- the candidate set is registered only as candidate;
- it is absent from all active required sets;
- no workflow makes it a required release check;
- no release decision reads the public summary as active authority;
- no generic external summary path implicitly promotes it.

---

## 31. Initial fixtures

### 31.1 Positive fixture

```text
exact protected control-plane revision
exact trusted verifier, extractor, and policy
exact schema snapshot
exact subject Git revision
valid completed manifest
valid findings document
valid complete coverage
complete reference closure
zero critical findings
zero high findings
matching producer receipt
matching intake packet
successful lifecycle action
```

Expected result:

```text
verified_pass
public summary projection exact
all inactive candidate gates true
authority effect none
```

### 31.2 Blocking fixture

```text
exact protected control-plane revision
exact schema snapshot
exact subject Git revision
valid completed manifest
valid complete coverage
complete reference closure
one high-severity finding
matching producer receipt
matching intake packet
successful lifecycle action
```

Expected result:

```text
verified_block
integrity and binding gates true
findings-policy gate false
public summary records blocking state
authority effect none
```

### 31.3 Subject-mismatch fixture

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

### 31.4 Coverage-collapse fixture

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

### 31.5 Control-plane-substitution fixture

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

### 31.6 Duplicate-key fixture

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

### 31.7 Schema-snapshot mismatch fixture

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

### 31.8 Missing-severity fixture

```text
canonical finding has no severity.level
```

Expected result:

```text
unverified
not verified_block
```

### 31.9 Referenced-evidence substitution fixture

```text
canonical coverage document references artifacts/receipt-1.json
source-bundle identity recorded
referenced file replaced before replay
```

Expected result:

```text
referenced-evidence digest mismatch
source-bundle identity mismatch
unverified
```

### 31.10 Incomplete-closure fixture

```text
canonical document references artifacts/receipt-1.json
source-bundle index omits the referenced file
```

Expected result:

```text
reference_closure_incomplete
candidate set not satisfied
```

### 31.11 Intake-report publication fixture

```text
public artifact path includes codex_security_intake_report_v0.json
```

Expected result:

```text
workflow guard fails
no publication
```

### 31.12 Lifecycle-ordering fixture

```text
summary is built before raw deletion or private transfer completes
```

Expected result:

```text
invalid lifecycle ordering
no final summary publication
```

### 31.13 Source-replacement fixture

```text
verifier emits intake report
findings.json is replaced
summary builder runs
```

Expected result:

```text
summary builder does not read findings.json
public summary remains derived from intake_report.decision_projection
```

### 31.14 Summary-substitution fixture

```text
valid private intake report
valid lifecycle receipt
fabricated public summary changes verified_block to verified_pass
```

Expected result:

```text
regenerated summary mismatch
summary-projection gate false
candidate set not satisfied
```

---

## 32. Candidate policy

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

  reference_extractor:
    path: tools/extract_codex_security_reference_closure_v0.py

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
  source_bundle_index_max_bytes: 4194304
  intake_packet_max_bytes: 1048576
  intake_report_max_bytes: 8388608
  lifecycle_receipt_max_bytes: 1048576
  public_summary_max_bytes: 4194304
  source_record_max_bytes: 1048576
  individual_schema_max_bytes: 4194304
  candidate_policy_max_bytes: 1048576
  referenced_evidence_file_max_bytes: 67108864
  raw_bundle_total_max_bytes: 536870912
  raw_bundle_entry_max_count: 10000

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

private_authority_carriers:
  intake_report_publication_allowed: false
  lifecycle_receipt_publication_allowed: false

public_summary:
  free_form_text_allowed: false
  additional_properties_allowed: false
  authority_effect: none

authority:
  mode: candidate_advisory
  release_effect: none
```

The policy digest must be calculated from the trusted control-plane checkout.

It must be recorded in:

```text
intake packet
private intake report
public normalized summary
```

The policy file must be parsed with duplicate-mapping-key rejection.

---

## 33. Workflow design

The initial workflow should be:

```text
.github/workflows/codex_security_candidate.yml
```

The first workflow must be manual.

It must run from a protected control-plane revision.

It must not run automatically on untrusted pull requests.

It must not expose a secret to untrusted fork code.

### 33.1 Conceptual workflow

```text
resolve-subject
→ codex-security-produce-verify-lifecycle-summarize
→ publish-public-summary
```

Raw files and private authority carriers must not cross into the final public
job.

### 33.2 `resolve-subject`

Responsibilities:

- run from the protected workflow revision;
- record the trusted control-plane repository and exact revision;
- resolve the selected subject ref to a full commit;
- require an allowed subject repository;
- emit the expected subject identity;
- emit the expected workflow-run identity;
- reject subject selection that changes the control-plane revision.

This job emits only non-sensitive identifiers.

### 33.3 `codex-security-produce-verify-lifecycle-summarize`

This single ephemeral job performs every raw-data and private-authority
operation.

Responsibilities:

```text
1. checkout the protected trusted control plane

2. verify the trusted control-plane revision

3. load the trusted policy, verifier, builders, extractor, and schemas

4. checkout the subject into a separate root

5. verify the exact subject revision and clean state

6. install the pinned Codex Security package outside both worktrees

7. run the declared scan recipe

8. write Codex state and output outside both worktrees

9. create the producer receipt

10. validate canonical source-document paths and limits

11. extract the complete referenced-evidence closure

12. enforce per-file, entry-count, and total-size limits

13. reject symlinks, path escape, and non-regular files

14. calculate every source-bundle entry digest

15. create the complete source-bundle index

16. calculate the source-bundle identity

17. create the independently expected intake packet

18. run the trusted verifier

19. emit the private machine-only intake report

20. calculate the intake-report digest

21. execute the selected raw-bundle lifecycle action

22. verify lifecycle postconditions

23. emit the private lifecycle receipt

24. calculate the lifecycle-receipt digest

25. build the final public sanitized summary from the private report and receipt

26. validate the public summary against the exhaustive public schema

27. upload only the public summary for the next job
```

This job must never apply a patch.

### 33.4 `publish-public-summary`

Responsibilities:

- download only the public normalized summary;
- verify its digest;
- validate the exhaustive public schema;
- reject duplicate keys;
- enforce the public size limit;
- verify canonical serialization;
- publish the public summary and its detached digest or signature.

This job must never receive:

- the raw source bundle;
- the source-bundle index;
- the intake packet;
- the private intake report;
- the private lifecycle receipt.

### 33.5 Raw and private transfer prohibition

The workflow must not use a normal public-repository Actions artifact to move:

- the raw source bundle;
- the source-bundle index;
- the intake packet;
- the private intake report;
- the private lifecycle receipt.

A future multi-job private-data design requires:

- an access-controlled private transfer;
- explicit encryption and key boundaries where applicable;
- a separate design review.

### 33.6 Workflow status

The candidate workflow must fail when:

- the producer fails;
- the bundle is incomplete;
- the reference closure is incomplete;
- verification fails;
- a blocking finding exists under a workflow policy configured to fail on
  candidate block;
- private retention was required but failed;
- local raw deletion failed;
- lifecycle postconditions failed;
- a public raw or private-carrier upload path is detected;
- the public-summary projection fails validation.

Its workflow conclusion is not a PULSEmech release decision before promotion.

---

## 34. Cost and interruption boundary

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

A lifecycle failure after an interrupted scan still prevents public summary
publication.

---

## 35. Package and contract upgrades

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
- reference-extractor compatibility review;
- candidate-policy change;
- verifier compatibility review;
- public-summary compatibility review;
- duplicate-key test replay;
- size-limit review;
- reference-closure fixture replay;
- positive fixture replay;
- negative fixture replay;
- candidate proof regeneration.

The workflow must never follow a floating package version.

An upgrade must not silently change the scan recipe.

An upgrade must not silently replace the trusted schema snapshot.

An upgrade must not silently change supported evidence-reference fields.

---

## 36. Proposed implementation files

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
├── codex_security_raw_bundle_lifecycle_receipt_v0.schema.json
└── codex_security_summary_v0.schema.json

tools/
├── extract_codex_security_reference_closure_v0.py
├── build_codex_security_source_bundle_index_v0.py
├── build_codex_security_intake_packet_v0.py
├── check_codex_security_intake_packet_v0.py
├── build_codex_security_raw_bundle_lifecycle_receipt_v0.py
├── build_codex_security_summary_v0.py
└── check_codex_security_public_summary_v0.py

ci/
├── check_codex_security_no_public_private_artifact_v0.py
├── check_codex_security_summary_projection_v0.py
└── check_codex_security_candidate_activation_guard_v0.py

examples/security/
├── codex_security_producer_receipt_example_v0.json
├── codex_security_source_bundle_index_example_v0.json
├── codex_security_intake_packet_example_v0.json
├── codex_security_intake_report_example_v0.json
├── codex_security_raw_bundle_lifecycle_receipt_example_v0.json
└── codex_security_summary_example_v0.json

tests/
├── test_codex_security_reference_closure_v0.py
├── test_codex_security_source_bundle_index_v0.py
├── test_codex_security_intake_packet_v0.py
├── test_codex_security_duplicate_json_keys_v0.py
├── test_codex_security_trusted_control_plane_v0.py
├── test_codex_security_schema_snapshot_binding_v0.py
├── test_codex_security_carrier_size_limits_v0.py
├── test_codex_security_single_read_verifier_v0.py
├── test_codex_security_intake_verifier_v0.py
├── test_codex_security_private_intake_report_v0.py
├── test_codex_security_raw_bundle_lifecycle_v0.py
├── test_codex_security_public_summary_v0.py
├── test_codex_security_summary_projection_v0.py
├── test_codex_security_no_public_private_artifact_v0.py
├── test_codex_security_candidate_gate_set_v0.py
└── test_codex_security_candidate_activation_guard_v0.py

.github/workflows/
└── codex_security_candidate.yml
```

Final filenames may change only through explicit implementation review.

---

## 37. Implementation sequence

### PR 1 — Design record

Add the initial design record.

Authority effect:

```text
none
```

### PR 1A — Initial review hardening

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

### PR 1B — Report, closure, projection, and lifecycle binding

Correct the design to require:

- private intake reports;
- public-summary-only publication;
- complete binding of referenced scan-local evidence;
- a deterministic complete source-bundle identity;
- complete decision projection inside the private intake report;
- summary construction without reopening raw source documents;
- lifecycle completion before final summary generation;
- a private lifecycle receipt;
- fold-in regeneration of every public decision field.

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
- schema-source tests;
- supported-reference-field inventory.

Authority effect:

```text
none
```

### PR 3 — Carrier schemas

Add:

- producer receipt schema;
- source-bundle index schema;
- intake packet schema;
- private intake-report schema;
- private lifecycle-receipt schema;
- public-summary schema;
- synthetic examples;
- positive and negative schema tests;
- duplicate-key negative fixtures;
- exhaustive public allowlist.

Authority effect:

```text
none
```

### PR 4 — Reference closure and trusted intake verifier

Add:

- protected control-plane binding;
- trusted reference extractor;
- offline verifier;
- filesystem checks;
- pre-read size checks;
- total-size and entry-count checks;
- duplicate-key rejection;
- complete closure verification;
- bundle-integrity checks;
- cross-document checks;
- producer checks;
- subject checks;
- current-run checks;
- schema-snapshot checks;
- coverage checks;
- finding checks;
- single-read decision projection;
- reason codes;
- fixed fixtures.

Authority effect:

```text
none
```

### PR 5 — Private intake report and lifecycle receipt

Add:

- deterministic private intake report;
- complete machine decision projection;
- raw-bundle lifecycle execution boundary;
- lifecycle postcondition checker;
- private lifecycle receipt;
- private-carrier publication guards.

Authority effect:

```text
none
```

### PR 6 — Public normalized summary and projection checker

Add:

- public-summary schema;
- trusted summary builder;
- report-and-lifecycle-only input boundary;
- public field allowlist;
- no-free-form-text guard;
- deterministic summary regeneration;
- projection equality tests.

Authority effect:

```text
none
```

### PR 7 — Inactive candidate registration

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

### PR 8 — Manual same-runner producer workflow

Add:

- protected workflow trigger;
- separate trusted and subject checkouts;
- exact-revision subject target;
- pinned package installation;
- minimal permissions;
- external state and result paths;
- same-runner closure and packaging;
- same-runner intake verification;
- raw private-or-delete lifecycle;
- private intake report and lifecycle receipt;
- public-summary-only artifact publication;
- public raw/private-artifact guards.

Authority effect:

```text
none
```

### PR 9 — Fixed-source candidate proof

Record:

- exact trusted control-plane revision;
- exact subject revision;
- workflow run identity;
- producer identity;
- schema-snapshot identity;
- source-bundle identity;
- complete reference-closure identity;
- intake packet digest;
- private intake-report digest;
- private lifecycle-receipt digest;
- public summary digest;
- expected candidate gate state;
- deterministic projection result;
- private retention state when replay is claimed.

Authority effect:

```text
none
```

### PR 10 — Promotion criteria

Define:

- operational stability threshold;
- package update process;
- schema-snapshot update process;
- reference-extractor update process;
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

### PR 11 — Separate promotion

Only this pull request may propose moving the candidate set into a required
release policy.

The promotion pull request must be independently reviewable.

The promotion pull request must not contain unrelated implementation work.

---

## 38. Promotion prerequisites

Promotion must not occur until all of the following are proven.

### 38.1 Trusted control-plane proof

- protected control-plane repository identity recorded;
- protected exact revision recorded;
- subject cannot select the control-plane revision;
- trusted and subject checkouts are separate;
- verifier sourced only from the trusted checkout;
- policy sourced only from the trusted checkout;
- schema snapshot sourced only from the trusted checkout;
- reference extractor sourced only from the trusted checkout;
- subject-supplied executable code excluded from verification;
- executable and module-loading environment sanitized.

### 38.2 Producer proof

- exact package identity recorded;
- exact plugin identity recorded;
- exact runtime identity recorded;
- exact model and reasoning effort recorded;
- package lock verified;
- minimal environment established;
- no unrelated credential inheritance;
- output outside both worktrees;
- no patch application.

### 38.3 Carrier and closure proof

- every source file digest verified;
- every required referenced-evidence file indexed;
- reference closure deterministic;
- source-bundle identity deterministic;
- duplicate JSON keys rejected;
- trusted size limits enforced before reading;
- total-size and entry-count limits enforced;
- source bundle retained privately when replay is claimed;
- raw bundle never exposed through public Actions artifacts.

### 38.4 Schema proof

- exact upstream repository identity recorded;
- exact upstream revision recorded;
- source-record digest recorded;
- aggregate snapshot identity recorded;
- per-schema digests recorded;
- schema snapshot preserved through packet, report, and summary;
- live schema download absent from verification.

### 38.5 Subject proof

- exact Git revision binding;
- current workflow-run binding;
- previous-run reuse rejected;
- wrong-revision fixture rejected;
- dirty-worktree substitution rejected.

### 38.6 Coverage proof

- complete required coverage;
- declared coverage mode;
- declared inventory strategy;
- exact include/exclude relation;
- unapproved exclusions rejected;
- deferred work rejected;
- incomplete coverage never converted into no-findings success.

### 38.7 Findings-policy proof

- critical finding blocks;
- high finding blocks;
- medium, low, and informational findings remain visible;
- missing severity produces unverified;
- malformed severity produces unverified;
- unsupported severity produces unverified;
- malformed finding produces unverified;
- readable projections cannot override canonical findings.

### 38.8 Single-read proof

- verifier hashes and parses the same bytes;
- decision projection is created from the validated parsed objects;
- source replacement after verification cannot alter the intake report;
- summary builder never reopens raw source documents.

### 38.9 Private intake-report proof

- report uses an exhaustive machine-only schema;
- no arbitrary human-readable messages;
- no source excerpts;
- no attack narratives;
- complete decision projection present;
- report cannot enter public artifact uploads.

### 38.10 Lifecycle proof

- selected lifecycle action completes before final summary generation;
- lifecycle postconditions are verified;
- private transfer identity matches the source bundle when used;
- runner-local raw copy is deleted when required;
- lifecycle receipt binds the intake report and source bundle;
- lifecycle receipt cannot enter public artifact uploads.

### 38.11 Summary-projection proof

- public summary is built only from the private intake report and lifecycle
  receipt;
- public summary has an exhaustive allowlist;
- public summary contains no free-form text;
- fold-in regenerates the canonical public summary;
- every decision-field mismatch is rejected;
- public summary alone cannot create candidate or release state.

### 38.12 Workflow lifecycle proof

- producer, closure extraction, packaging, verification, lifecycle action, and
  summary generation occur on the same runner;
- no later job expects runner-local raw files;
- private transfer completes before local deletion when enabled;
- only the public normalized summary crosses into public publication jobs.

### 38.13 Determinism proof

- fixed bundle replay;
- fixed reference-closure replay;
- fixed policy replay;
- fixed schema-snapshot replay;
- fixed verifier replay;
- fixed lifecycle receipt replay;
- identical gate inputs;
- identical reason-code output;
- byte-identical public summary;
- no live network dependency in verification or projection.

### 38.14 Authority proof

- only declared materialized gates affect release;
- candidate set inactive before promotion;
- no alternate release path;
- no scanner exit code used as release authority;
- no workflow name used as release authority;
- no report text used as release authority;
- no public summary used as release authority;
- no raw artifact presence used as release authority;
- `check_gates.py` remains the strict final evaluator.

---

## 39. Acceptance criteria for the completed candidate lane

The candidate lane is complete only when:

```text
1. A real Codex Security scan runs against an exact subject repository
   revision.

2. The workflow runs from an exact protected control-plane revision.

3. The trusted control-plane checkout is separate from the subject checkout.

4. The scan produces the three canonical JSON documents.

5. Every supported authority-relevant local evidence reference is resolved.

6. Every required referenced-evidence file is included in the source-bundle
   index.

7. The source-bundle identity covers the normalized path, role, media type,
   size, and digest of every indexed component.

8. The producer wrapper records its independently reviewable identity.

9. The complete source bundle is indexed and digest-bound before the producer
   job ends.

10. Every JSON carrier rejects duplicate object keys.

11. Trusted YAML rejects duplicate mapping keys.

12. Trusted per-carrier, total-size, and entry-count limits are enforced before
    unsafe processing.

13. The intake packet supplies expectations independently of the source
    bundle.

14. The verifier validates the trusted policy, verifier, extractor, builders,
    and schema snapshot from the protected control-plane checkout.

15. The verifier rejects stale, mismatched, malformed, oversized, partial,
    substituted, unindexed, and duplicate-key evidence.

16. The verifier hashes, parses, and evaluates the same immutable bytes.

17. The verifier distinguishes valid blocking evidence from invalid evidence.

18. Missing, malformed, and unsupported severity values produce unverified
    state.

19. The private intake report contains the complete machine decision
    projection.

20. The private intake report contains no arbitrary human-readable security
    detail.

21. The private intake report is never uploaded through public Actions
    artifacts.

22. The selected raw-bundle lifecycle action completes before final summary
    creation.

23. Lifecycle postconditions are verified and recorded in a private receipt.

24. The private lifecycle receipt is never uploaded through public Actions
    artifacts.

25. The public summary builder reads only the private intake report and private
    lifecycle receipt.

26. The public summary builder never reopens canonical source documents or
    referenced evidence.

27. The public summary uses an exhaustive allowlist and contains no free-form
    text.

28. The normalized summary preserves subject, producer, coverage, findings,
    policy, schema-snapshot, control-plane, source-bundle, intake-report, and
    lifecycle identities.

29. Raw findings never enter a normal public-repository Actions artifact.

30. Raw findings are deleted on the runner or transferred to access-controlled
    private storage.

31. Public artifacts contain only the normalized public summary and its
    detached digest or signature.

32. Fold-in regenerates the complete public summary from private authority
    carriers.

33. Any changed public decision field fails the summary-projection check.

34. The public summary alone cannot create candidate or release state.

35. The candidate gate set is fully materializable.

36. The candidate gate set remains absent from every active required set.

37. Positive, blocking, unverified, duplicate-key, control-plane-substitution,
    schema-mismatch, closure-mismatch, lifecycle-failure, source-replacement,
    and summary-substitution fixtures reproduce deterministically.

38. A fixed real-run proof records its private retention state accurately.

39. No release authority changes occur.
```

---

## 40. Final boundary

The completed relation is intended to be:

```text
Codex Security
finds and records repository security observations

protected PULSEmech control plane
supplies the trusted verifier, policy, reference extractor, builders, and
schema snapshot

PULSEmech source-bundle closure
binds every canonical document and every required referenced evidence file

PULSEmech intake
proves which producer, run, subject, recipe, coverage state, reference closure,
and trusted control plane produced and verified the observation

private intake report
carries the complete machine decision projection

private lifecycle receipt
proves the completed handling of confidential raw evidence

public PULSEmech summary
is a strict sanitized projection built after lifecycle completion

private PULSEmech fold-in
regenerates that projection and derives gate state from private authority
carriers

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

With the complete source closure, protected verifier, exact schema snapshot,
complete coverage relation, private decision projection, completed lifecycle
receipt, and regenerated sanitized summary:

```text
there is reviewable, subject-bound security evidence
```

Only a later explicit promotion may make that evidence release-required.
