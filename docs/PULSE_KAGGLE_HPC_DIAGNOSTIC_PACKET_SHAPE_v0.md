# Kaggle / HPC Diagnostic Evidence Packet Shape v0

- Status: packet-shape note
- Normative status: non-normative clarification
- Scope: future Kaggle / HPC diagnostic evidence packets mapped onto `hpc_evidence_bundle_v0`

## Core statement

A Kaggle / HPC diagnostic packet is review and reproducibility material.

It does not create release authority.

The current compatible packet schema is:

```text
hpc_evidence_bundle_v0
```

The current compatible non-authority status literal is:

```text
authority_status = diagnostic_non_normative
creates_release_authority = false
```

The packet may make an external run reviewable.

It must not make an external run release-authoritative.

## Core boundary

```text
Kaggle notebook output ≠ verified evidence
HPC benchmark result ≠ gate materialization
diagnostic packet ≠ relation satisfaction
reproducibility packet ≠ release authority
```

A Kaggle / HPC diagnostic packet must not create or enable:

- `VERIFIED`;
- trusted evidence;
- verified evidence;
- `verified_artifacts`;
- `relation_bindings`;
- relation satisfaction;
- gate materialization;
- `status.json` writing;
- policy changes;
- registry changes;
- `check_gates.py` changes;
- CI allow/block changes;
- release authority.

## Current schema mapping

Use the existing `hpc_evidence_bundle_v0` schema.

Do not add new top-level schema fields in current v0.

Kaggle-specific values should remain nested diagnostic metadata.

The current v0 packet should use:

```text
schema = hpc_evidence_bundle_v0
authority_status = diagnostic_non_normative
creates_release_authority = false
```

Every evidence item should default to:

```text
folded_into_status = false
```

A future fold-in must be reviewed separately.

A fold-in requires declared policy, a workflow-effective materialized required gate set, and strict fail-closed CI enforcement.

## Minimal packet shape

A minimal v0 packet should include:

- packet identity;
- external source metadata;
- execution metadata;
- input artifact references;
- output artifact references;
- diagnostic metrics;
- reproducibility instructions;
- explicit non-authority notes.

The packet should be small enough to review and replay.

The packet should not become a new release-authority surface.

## Packet identity

The packet should identify itself as diagnostic and non-authoritative.

Recommended packet identity metadata:

- packet ID;
- packet version;
- created UTC timestamp;
- producer;
- purpose;
- authority status;
- release-authority flag.

Current-compatible values:

```text
authority_status = diagnostic_non_normative
creates_release_authority = false
```

The purpose should state that the packet is for diagnostic reproducibility and review only.

The packet identity does not create trust.

The packet identity does not make the producer trusted.

The packet identity does not verify evidence.

## External source metadata

Kaggle-specific fields may include:

- competition ID;
- dataset ID;
- notebook ID;
- notebook version;
- source URL;
- observed timestamp;
- producer / author metadata;
- license / terms note;
- external-state warning.

These fields are diagnostic metadata.

They do not create trust.

They do not verify evidence.

They do not satisfy relations.

They do not materialize gates.

A Kaggle public URL may be useful as metadata or external reference.

A Kaggle public URL is not sufficient as evidence by itself.

A screenshot is not artifact-bound evidence.

A public score is not release authority.

## Execution metadata

Execution metadata may include:

- runtime environment;
- Python version;
- package versions;
- hardware / accelerator class;
- run command;
- notebook execution path;
- seed / determinism note;
- external-state note.

Runtime metadata is not a trusted verifier.

Accelerator class is not release authority.

Notebook execution success is not verified evidence.

A notebook pass is not release authority.

## Input artifact references

Input artifact references should record:

- local input artifact path;
- source dataset reference;
- downloaded input artifact SHA-256;
- input manifest reference;
- mutable external-state warning;
- unavailable input behavior.

An external URL is not recorded evidence.

A downloaded artifact without SHA-256 is not diagnostic evidence.

If an input artifact cannot be downloaded, restored, or hash-verified, the packet should mark that input as incomplete, missing, failed, or unverified.

Unavailable Kaggle state remains unavailable external state.

Unavailable Kaggle state does not become verified evidence.

## Output artifacts

Output artifacts should record:

- output artifact path;
- output artifact SHA-256;
- output kind;
- generated plots;
- generated tables;
- logs;
- metrics;
- result summary.

A present output artifact must be SHA-256-bound before it can serve as diagnostic evidence.

An output artifact is not verified evidence by itself.

A metric is not a gate pass.

A benchmark result is not gate materialization.

A reproduced plot is not release authority.

## Diagnostic metrics

Diagnostic metrics should record:

- metric name;
- metric value;
- unit, if applicable;
- threshold, if applicable;
- source artifact;
- computation command;
- diagnostic interpretation.

Metric thresholds are diagnostic unless a later declared policy promotes them into workflow-effective materialized required gates and strict fail-closed CI enforcement.

A metric threshold is not a declared gate by itself.

A score is not release authority.

A benchmark success does not materialize `detectors_materialized_ok`.

## Reproducibility instructions

A packet should include:

- replay command or notebook replay instructions;
- environment reconstruction notes;
- input acquisition notes;
- expected output files;
- expected hashes where deterministic;
- nondeterminism / external-state caveats.

Replayable output is not a verified relation.

A reproducibility packet is not release authority.

Reproducibility supports review.

Reproducibility does not replace the artifact-bound PULSEmech release-authority path.

## Non-authority section

Every Kaggle / HPC diagnostic packet should carry explicit non-authority text.

Required boundary text, or equivalent:

```text
This packet is diagnostic.
This packet does not create release authority.
This packet does not verify evidence.
This packet does not satisfy relation bindings.
This packet does not materialize gates.
This packet does not write status.json.
This packet does not affect check_gates.py.
```

This text is not decorative.

It prevents the packet from being misread as a decision engine.

## Fold-in boundary

Current v0 default:

```text
folded_into_status = false
```

Folded-out diagnostic evidence remains outside status authority.

If a future policy proposes fold-in, that must be a separate staged review requiring:

- declared policy;
- workflow-effective materialized required gate set;
- strict fail-closed CI enforcement.

A folded-in diagnostic must not silently create release authority.

A folded-in diagnostic must not bypass policy.

A folded-in diagnostic must not bypass `check_gates.py`.

## Provenance / attestation placeholders

The following are future hardening items, not current authority:

- producer identity;
- artifact attestation;
- notebook provenance;
- dataset provenance;
- environment capture;
- reproducible run logs;
- hash chains;
- in-toto / SLSA-style evidence chains;
- GitHub artifact attestations;
- Kaggle external-state drift handling.

These may strengthen future reproducibility and traceability.

They do not create current release authority.

An attestation placeholder is not trusted evidence.

A future provenance field is not release authority.

## Existing HPC bundle compatibility

The existing `hpc_evidence_bundle_v0` surface can represent a minimal Kaggle / HPC diagnostic packet if Kaggle-specific fields remain nested metadata and present artifacts are SHA-256-bound.

Direct mappings:

```text
schema
→ hpc_evidence_bundle_v0

authority_status
→ diagnostic_non_normative

creates_release_authority
→ false

run identity and timestamps
→ run_identity

repository and git SHA
→ code_identity

input manifest path and digest
→ input_manifest.path / input_manifest.sha256

runtime and accelerator context
→ environment

output artifacts
→ evidence_items

metrics
→ summary_metrics

command / seed / notes
→ provenance

replay instructions
→ reconstruction.instructions

diagnostic completeness
→ result

non-authority prose
→ notes
```

Kaggle-specific fields should remain metadata only:

- competition ID;
- dataset ID;
- notebook ID;
- notebook version;
- source URL;
- observed timestamp;
- producer / author;
- license / terms note;
- notebook execution path;
- external-state / availability note.

A new schema is not needed for the smallest safe v0 packet-shape note.

A local example packet should come before a Kaggle notebook.

A Kaggle notebook should come after a local packet fixture proves the diagnostic-only shape.

## Unsafe current-v0 transitions

The following transitions are out of scope for current v0:

```text
Kaggle notebook → verified_artifact
HPC bundle → relation_binding
benchmark success → detector_materialized_ok
external run → trusted verifier
public result → release gate
```

A Kaggle / HPC packet must not currently:

- add required gates;
- change policy;
- change registry;
- materialize `detectors_materialized_ok`;
- satisfy `external_summaries_present`;
- satisfy `refusal_delta_evidence_present`;
- affect `check_gates.py`;
- affect CI allow/block decision.

## Minimal v0 field table

| Packet field / section | Required in v0? | Role | Authority risk | Existing repo analogue | Recommendation |
| --- | --- | --- | --- | --- | --- |
| `schema = hpc_evidence_bundle_v0` | yes | packet identity | low | `hpc_evidence_bundle_v0` schema | Use existing schema identifier. |
| `authority_status` | yes | non-authority boundary | low | required schema field | Use `diagnostic_non_normative`. |
| `creates_release_authority = false` | yes | non-authority boundary | low | required schema field | Required. |
| packet ID | yes as metadata | packet identity | low | reference packet metadata | Store as packet metadata. |
| packet version | yes | packet identity | low | reference packet metadata | Use `kaggle_hpc_diagnostic_packet_v0` as metadata, not a new schema. |
| created UTC | yes | packet identity | low | reference packet metadata | Include separately from run timestamps. |
| producer | yes | packet identity | medium | diagnostic producer metadata | Required for review orientation, not trust. |
| purpose | yes | packet identity | low | diagnostic notes | Must say diagnostic reproducibility / review only. |
| Kaggle competition ID | optional | external source metadata | medium | metadata field | Metadata only. |
| Kaggle dataset ID | required when Kaggle input is used | external source metadata | medium | dataset identity metadata | Store as metadata plus digest-bound downloaded input. |
| Kaggle notebook ID | optional | external source metadata | medium | metadata field | Metadata only. |
| notebook version | optional | external source metadata | medium | metadata field | Include if available. |
| source URL | optional | external source metadata | high | metadata field | URL is not evidence by itself. |
| observed timestamp | required for mutable source | external source metadata | medium | run/source timestamp | Required for external-state review. |
| producer / author | optional | external source metadata | medium | metadata field | Not an attestation. |
| license / terms note | recommended | external source metadata | medium | metadata field | Include as review note. |
| runtime environment | yes | execution metadata | low | `environment` | Required. |
| Python version | yes | execution metadata | low | environment metadata | Include for replay. |
| package versions | yes if needed | execution metadata | low | environment or evidence item | Include where reproducibility depends on them. |
| hardware / accelerator class | optional | execution metadata | medium | `environment.accelerator_class` | Context only, not authority. |
| run command | yes | execution metadata | low | `provenance.command` | Required replay anchor. |
| notebook execution path | required for notebook run | execution metadata | medium | provenance metadata | Metadata only. |
| seed / determinism note | recommended | execution metadata | low | `provenance.seed` | Include nondeterminism caveat. |
| external-state note | required for Kaggle | execution metadata | medium | notes/provenance metadata | Required for drift / availability review. |
| local input artifact path | yes | input artifact reference | low | `input_manifest.path` | Required. |
| downloaded input artifact SHA-256 | yes | input artifact reference | low | `input_manifest.sha256` | Required. |
| input manifest reference | yes | input artifact reference | low | `input_manifest` | Required. |
| mutable external-state warning | yes for external source | input artifact reference | medium | notes/provenance metadata | Required. |
| unavailable input behavior | yes | input artifact reference | medium | incomplete result / missing item | Mark incomplete or unavailable, not verified. |
| output artifact path | yes | output artifact reference | low | `evidence_items[].path` | Required. |
| output artifact SHA-256 | yes when present | output artifact reference | low | `evidence_items[].sha256` | Required for present output artifacts. |
| output kind | recommended | output artifact reference | low | evidence item role / metadata | Add as metadata if role is too coarse. |
| generated plots | optional | output artifact reference | medium | evidence item | Digest-bind if present. |
| generated tables | optional | output artifact reference | medium | evidence item | Digest-bind if present. |
| logs | recommended | output artifact reference | low | raw trace evidence item | Include SHA-256 if present. |
| metrics | yes if reported | diagnostic metric | medium | `summary_metrics` | Descriptive only. |
| result summary | yes | output artifact reference | medium | `result` | Diagnostic completeness only. |
| replay command | yes | reproducibility instruction | low | `reconstruction.instructions` | Required. |
| environment reconstruction notes | yes | reproducibility instruction | low | reconstruction notes | Required. |
| input acquisition notes | yes | reproducibility instruction | medium | reconstruction notes | Required. |
| expected output files | yes | reproducibility instruction | low | evidence item paths | Required. |
| expected hashes | recommended where deterministic | reproducibility instruction | low | evidence item SHA-256 | Include when deterministic. |
| nondeterminism caveats | yes | reproducibility instruction | medium | notes | Required for Kaggle / HPC runs. |
| metric name | yes for each metric | diagnostic metric | low | `summary_metrics` key | Required. |
| metric value | yes for each metric | diagnostic metric | medium | `summary_metrics` value | Required. |
| unit | recommended | diagnostic metric | low | metadata | Include where possible. |
| threshold | optional diagnostic metadata | diagnostic metric | high | `threshold_ref` / metadata | Must not become a declared gate by itself. |
| source artifact for metric | yes | diagnostic metric | medium | evidence item reference | Required. |
| computation command | yes | diagnostic metric | low | `provenance.command` | Required. |
| diagnostic interpretation | recommended | diagnostic metric | medium | notes | Must not say release pass. |
| producer identity attestation | no | future hardening only | medium | future roadmap | Future only. |
| artifact attestation | no | future hardening only | medium | future roadmap | Future only. |
| notebook provenance | no | future hardening only | medium | future roadmap | Future only. |
| dataset provenance | no | future hardening only | medium | future roadmap | Future only. |
| in-toto / SLSA chain | no | future hardening only | high | future roadmap | Staged hardening only. |
| GitHub artifact attestation | no | future hardening only | high | future roadmap | Staged hardening only. |
| explicit non-authority text | yes | non-authority boundary | low | notes/docs boundary | Required. |
| `folded_into_status = false` | yes | non-authority boundary | low | evidence item field | Default false. |
| policy route | no for v0 | unsafe / out of scope | high | policy route field when folded | Avoid in current v0. |
| `verified_artifacts` | no | unsafe / out of scope | unsafe | verifier report field | Not allowed. |
| `relation_bindings` | no | unsafe / out of scope | unsafe | verifier report field | Not allowed. |
| gate materialization / status write | no | unsafe / out of scope | unsafe | authority path field | Not allowed. |

## Recommended order

```text
1. docs-only packet-shape note
2. local minimal diagnostic packet fixture
3. local checker / contract confirmation
4. Kaggle notebook skeleton
5. Kaggle run
6. downloaded/local artifacts with SHA-256
7. non-authoritative HPC evidence bundle
8. optional future candidate-evidence reference
```

The local packet fixture should come before a Kaggle notebook.

The Kaggle notebook should come before a real Kaggle run only after the local packet shape is stable.

The Kaggle run should not be treated as a verifier.

## Future hardening only

Future work may evaluate:

- producer identity;
- artifact attestation;
- notebook provenance;
- dataset provenance;
- environment capture;
- reproducible run logs;
- hash chains;
- in-toto / SLSA-style evidence chains;
- GitHub artifact attestations;
- Kaggle external-state drift handling.

These are staged hardening items.

They are not current release authority.

## Relation to the PULSEmech path

Release authority remains only on the PULSEmech path:

```text
recorded release evidence
→ status.json
→ declared gate policy
→ workflow-effective materialized required gate set
→ strict fail-closed CI enforcement
→ CI allow/block release decision
```

A Kaggle / HPC packet can later become release-relevant only if it is recorded, bound, checked, policy-routed, materialized as a required gate, and enforced by strict fail-closed CI.

Until that path exists, the packet remains diagnostic.

## Non-goals

This packet-shape note does not change:

- schemas;
- tools;
- builder behavior;
- checker behavior;
- workflows;
- `check_gates.py`;
- `run_all.py`;
- release policy;
- gate registry;
- CI authority path;
- `--release-grade-materialized`.

This packet-shape note does not create or enable:

- `VERIFIED`;
- trusted evidence;
- verified evidence;
- `verified_artifacts`;
- `relation_bindings`;
- relation satisfaction;
- gate materialization;
- `status.json` writing;
- release authority.

## Mechanical anchor

A Kaggle / HPC packet can make an external run reviewable.

It cannot make an external run release-authoritative.

Current v0 accepts diagnostic visibility only.

Current v0 does not accept release authority from Kaggle / HPC material.
