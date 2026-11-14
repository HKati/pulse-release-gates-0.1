# Selected idempotence observation adapter v0

## Status and claim

**Implemented: offline verification of selected bytes and recorded application
relationships. B2 remains incomplete.** This continuation of the
[selected protocol proposal](PULSEMECH_REQUIRED_GATE_IDEMPOTENCE_PROTOCOL_v0.md)
adds a strict capture-record adapter, a distinct standalone runtime profile, and
per-application derived-input verification. It runs no sanitizer, worker,
collector, model or workflow and supplies no actual reference observation.

The adapter can establish that a complete selected record says each second
application consumed its own first application's exact output state. It cannot
authenticate that a physical process executed or read those bytes. Source-byte
agreement, schema validity, recorded consumption, property calculation and
release authority remain separate claims.

The actual worker and collector, enforceable acquisition limits, recoverable
implementation/runtime closure and their review remain outstanding. B3 still
requires the property-specific producer and independent reconstruction; B4
requires coordinated release intake and admission; B5 requires a separately
selected and owner-authorized actual reference. A successful replay authorizes
none of those steps. The candidate association `psf_idempotence_ok` is unchanged;
production-gate applicability is not established.

## Implemented surfaces

| Surface | Responsibility |
| --- | --- |
| [Observation contract schema](../../schemas/required_gate_idempotence_observation_v0.schema.json) | Closed selection, acquisition context, per-application receipt and inventory records. |
| [Offline checker and adapter](../../tools/check_required_gate_idempotence_observation_v0.py) | Bind independently selected bytes, verify the carrier and receipts, project packets and reconstruct all twelve case paths. |
| [Standalone runtime profile](../../tools/pulsemech_compute_standalone_runtime_v0.py) | Validate truthful standalone fields and exact source admissions using the existing runtime vocabulary and common semantic checks. |
| [Existing compute analyzer](../../tools/pulsemech_compute_binding_analyzer_core_v0.py) | Reuse runtime indexing, source qualification and required-output consumption with an explicit standalone branch. |
| [Existing relation evaluator](../../tools/build_pulsemech_compute_planned_observed_relation_v0.py) | Reuse `full_relation_evaluation` for application-specific expectations and observations. |
| [Synthetic regressions](../../tests/test_required_gate_idempotence_observation_v0.py) | Exercise valid records and substitutions without executing the selected source. |

The historical subject/runtime schemas and their CLI validators are unchanged.
They intentionally reject the new standalone packet shape. This profile is
supported through the new adapter and is not automatically admitted by legacy
binding-report, candidate, gate or release commands. B1 v0's schema, checker,
fixtures and corrected per-occurrence static-input rule remain unchanged.

The existing analyzer's runtime-index implementation pin is updated explicitly
for the reviewed profile branch. The other historical function pins are
retained. Default legacy indexing and its conservative treatment of unverified
observed repository-source declarations are covered by existing regressions.

## Independent selection and exact source bytes

The caller supplies exact selection bytes and their expected SHA-256 separately
from the carrier. The carrier contains a byte-identical copy; it cannot nominate
its own trusted selection digest. The carrier SHA-256 is also a mandatory caller
argument. A digest selects bytes; it does not establish who selected them, when
the selection was made, or whether the acquisition was authentic.

The selection fixes the original protocol, input catalog and proposed mapping
from the proposal merged in
[#3019](https://github.com/HKati/pulse-release-gates-0.1/pull/3019), including all
twelve cases and 24 first/second application identities. The three original
companion files retain their exact bytes. The fixed configuration uses the
selected integer values; numerically equal floating representations cannot
substitute for them.

Sources have separate roles: the selected sanitizer and its three repository
imports retain their original `97ab500bb9936c27632e1f40ab891d2442476786`
selection, while the actual worker and collector must identify their own
implementation revision. Each source has an exact path, revision, SHA-256, byte
count and carrier member. The worker and collector are distinct nonempty source
files. Explicit implementation dependencies may include empty initialization
files. The source roster is limited to 32 entries and does not prove that all
runtime dependencies have been recovered.

In `observed` mode, each supplied source also has to match its regular-file Git
blob at the selected commit in the independently supplied repository. Missing
objects reject; lookup cannot fetch them or invoke repository-configured remote
or credential helpers. The checker never imports acquired source bytes.
Synthetic examples use explicit example identities and cannot become an
observed input by changing only status fields and recomputing their own hashes.

## Per-application recorded consumption

Each receipt identifies one application, a distinct execution occurrence, its
worker process, implementation source, fixed configuration and environment,
invocation binding, lifecycle, input read, snapshot, metadata and stderr.

For every case, the checker requires:

1. Exactly one first and one second application from the selected roster.
2. Twenty-four distinct subject execution and process identities, with the
   collector retained separately.
3. The first input's exact original UTF-8 bytes, including the selected LF.
4. A distinct first snapshot state produced by that first execution.
5. The second input's **same state ID, member, digest and byte count** as the
   first snapshot; the receipt must record a complete read of those bytes.
6. A distinct second snapshot state produced by the second execution.
7. Invocation digests incorporating the selected application ID, worker source,
   configuration and exact input state descriptor.
8. Complete successful receipt lifecycles, ordered first/second intervals and
   containment within the selected suite bounds.

The narrow runtime projection gives each subject execution exactly one payload
input. Source/runtime context is separately bound. Adding the original input
decoratively cannot mask an unrelated consumed payload.

State identity is independent of content identity. Original, intermediate and
final bytes may be identical; their occurrence/state roles must still be
distinct. Conversely, unequal first and second snapshots can have a fully valid
recorded consumption relation. This checker deliberately leaves `metric_pass`
null in both cases.

Snapshot bytes must be canonical under the selected JSON codec and belong to
its declared domain: objects containing nested objects and finite numeric
leaves. Boolean, string, array and null leaves reject; booleans are not admitted
through Python's integer subtype rule. Preserve signed zero and integer/float
representation. No numerical tolerance or object-equality shortcut is used.

Metadata and stderr are preserved with exact bindings and size limits. They are
not snapshot input or equality projections. Only the first snapshot requires
the second subject application as downstream consumer. Terminal snapshots and
diagnostics do not need a fabricated observer-as-subject consumption edge.

The shared `assess_runtime_output_consumption` must find the specifically
required second execution for every intermediate state. Its source admission
is reconstructed from independently supplied immutable bytes. A serialized
index or a `source_verified=true` assertion cannot recreate that admission.

## Standalone context and visibility

The explicit `standalone_operator_v0` context contains an acquisition identity,
single attempt, subject run key, repository and implementation revision,
protocol identity and selection digest. Workflow/job identifiers and the release
candidate are null; authority inputs and applicable policy sets are empty.
Subject states are non-authoritative advisory states. The separate collector is
excluded from subject totals.

The new profile uses the existing execution/state vocabulary through a narrow
in-memory schema projection. The installed historical runtime schema is captured
once and checked against its fixed original byte count and digest. The installed
checker, shared analyzer and relation evaluator remain verifier dependencies;
the selected subject-source inventory does not authenticate the installed
verifier or establish a full runtime closure.

The 24-case-path application records can be complete while host/runtime coverage
remains partial. Environment fingerprints and timestamps are retained as recorded
facts; no complete host identity or resource measurement is invented. Recorded
wall/monotonic bounds are checked, but enforcement of CPU, memory, isolation and
execution limits belongs to the outstanding acquisition implementation.

## Versioned carrier layout

`standalone_operator_acquisition_v0` is an implemented offline intake layout.
It explicitly extends the earlier 95-member **proposal** to preserve worker and
collector sources. The proposal is not rewritten or claimed to be an executed
archive. This profile has **91 + selected source count** members, with a minimum
of 97 and a maximum of 123:

| Members | Count |
| --- | ---: |
| Original protocol, catalog and mapping; exact external selection copy | 4 |
| Acquisition context, application receipts and member inventory | 3 |
| Selected original input bytes | 12 |
| First/second snapshots, metadata and diagnostics | 72 |
| Four selected operator/import files, worker, collector, optional dependencies | 6–32 |

The member inventory covers every other member and excludes itself. The raw
carrier does not embed its own digest, the runtime packet, the subject packet or
the verification report. Generated packets bind the exact carrier; generated
reports contain those projections. No containing archive/manifest hash cycle is
introduced.

The checker admits one ordinary stored/deflated non-ZIP64 archive with no data
descriptors, prefixes, trailers, concatenated archives, comments, extra fields,
unindexed local members, symlinks, path aliases, encryption or unused deflate
payload. Local records, central-directory offsets and the final end record must
cover the complete physical archive. Indexed logical membership alone is
insufficient.

Limits are 4 MiB encoded, 2 MiB total uncompressed, 512 KiB per generic member,
1 KiB per initial input, and 4 KiB each for a snapshot, metadata or diagnostics.
Unknown, missing, duplicate, excess or mismatched members reject. Failed or
incomplete receipts remain unusable as a complete observation; this checker
does not retry, repair or delete them. The original privacy/retention proposal
still governs any future acquisition/publication.

## Offline invocation and result

Use CPython 3.11.16 / Unicode 14.0.0 on Linux/POSIX. The command reads existing
selected files; it does not launch the operator or acquire evidence. Expected
digests must be supplied from the separately retained selection:

```bash
python tools/check_required_gate_idempotence_observation_v0.py \
  --selection /absolute/path/selection.json \
  --selection-sha256 SELECTED_SELECTION_SHA256 \
  --carrier /absolute/path/acquisition.zip \
  --carrier-sha256 SELECTED_CARRIER_SHA256 \
  --repository-root /absolute/path/repository \
  --output /absolute/path/new-observation-report.json
```

`--repository-root` is required for observed records. The output is optional;
canonical JSON is always printed. Existing outputs, symlink components and
authority-surface output names are refused. The output directory must exist.
Exit 0 means accepted recorded-relation integrity; exit 1 reports a deterministic
rejection code without echoing untrusted payload content.

Accepted reports retain these boundaries:

```json
{
  "verification_scope": "selected_bytes_and_recorded_consumption",
  "binding_complete": true,
  "packet_semantics_verified": true,
  "property_semantics_verified": false,
  "metric_pass": null,
  "anchor_authentication": "not_established",
  "runtime_closure_verified": false,
  "actual_reference_claimed": false,
  "execution_ready": false,
  "execution_authorized": false,
  "production_gate_eligible": false,
  "authority_effect": "none"
}
```

Rejection retains the same non-authority boundaries and sets binding/packet
verification false. A reported `observed` source record is never relabeled as an
example to bypass source qualification. A synthetic accepted regression remains
a synthetic regression, not a real sanitizer result.

## Validation and preserved boundaries

The new regression module is registered once in `ci/tools-tests.list`, without
targeted-pytest duplication. The Tools manifest is 184 entries; targeted pytest
remains 40. All 26 dependent count references are updated together. Tests cover
every cross-case substitution with identical snapshot bytes, missing/reused
identities, receipt/read/source substitutions, malformed carriers, strict JSON,
source-admission replay, deterministic reports and safe output handling.

The original verification artifact from run `43514702328`, attempt 1, the
historical Q2 FAIL result (49/50 with one UNKNOWN), all twelve unsupported gates,
the existing release authority chain and the prior Q3 acquisition lineage remain
unchanged. Keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879)
open. No workflow, policy, dispatcher, candidate intake or required gate is
activated by this package.
