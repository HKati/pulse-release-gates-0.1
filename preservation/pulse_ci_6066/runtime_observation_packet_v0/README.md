# PULSEmech #6066 historical runtime-packet preservation v0

## Scope and provenance

This directory preserves a new runtime-observation packet **constructed offline
from the accepted historical #6066 platform capture**, its exact construction
record, and the observed local construction/verification results.

It is the data-preservation handoff under **#2864**, following implementation
**#2867**. It is not a new implementation, validator, workflow, capture acquisition,
release decision, or canonical documentation synchronization.

Producer source commit:
`d7def834e8aa63911426550cf41b05f81c0b56b0`

Producer root tree:
`7ef7a119556d4dc69280ccd451ed41b5272fdeaa`

The unchanged producer was executed directly through its isolated CLI in two
separate complete source checkouts at that commit. Both consumed the same
construction-record bytes and preserved inputs. Their complete packet bytes
were identical, and both outputs passed the separate runtime-validator CLI.
No temporary test commit was substituted as the preservation producer revision.

The packet's `record_status: observed` concerns the verified historical
platform-export data. It does not independently authenticate every platform
assertion, the local collector declaration, or local clock readings.

## Exact preserved objects

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `construction_record_v0.json` | 1250 | `877347d5e22410888614ac55698d4ebe82378d496ae5ee31fec945195a1a55e6` |
| `pulsemech_compute_runtime_observation_packet_6066_observed_v0.json` | 484234 | `76418f3a7374cf12127031b15806af1e80605ad07031b3b10308c3a30b795a88` |
| `verification_record_v0.json` | 24105 | `aa225628594d5c5ef29764cde69e96d88da5942289b1603532710846b1ad3796` |

The JSON objects use the existing producer's canonical representation:
UTF-8, sorted keys, two-space indentation, no non-finite values, and one final LF.
Do not rewrite, prettify, or regenerate the construction record during replay.
The packet includes the construction-record digest; this README records that
external input digest explicitly. The verification report is a factual execution
record, not an additional verifier or a grant of authority.

The README does not contain its own hash. No circular identity or self-attestation
is introduced by this inventory.

## Historical inputs and source roles

The original five-member capture remains at
[post_run_producer_input_capture_v0](../post_run_producer_input_capture_v0/).
The exact file inventory and identities are recorded in
[verification_record_v0.json](verification_record_v0.json).

Historical subject: PULSE CI #6066, run `29249887581`, attempt `1`.
Historical subject source: `46b639706e23f80fe296a8893be18e2b5ab21f7e`.

Original platform acquisition: run `33986538130`, attempt `1`.
Acquisition implementation/source: `22d14088ae21f84d94c6a6951c0f70ab1bdf0895`.

The [observed subject-input context](../../../examples/compute/pulsemech_compute_subject_input_packet_6066_observed_v0.json)
is the verified source of the historical release-candidate, run-mode and ordered
policy-set identity. Its producer source is
`3cd57dc9e88e6f804dbb134c864f4207688bddc2`.

The required [earlier release-grade carrier](../../../PULSE_CI_6066_release_grade_artifact_preservation_v0.zip)
is 44,660 bytes, SHA-256
`7949bfd00468e6f9347fddaae732bdcebff5527e87ecb379a6c84a47176db966`.
It is not the later Step 4A acquisition ZIP/TAR or a cloud source-export archive.

All inputs and exact declared historical `commit:path` objects were available
locally and verified before use. No response was reacquired, no historical
workflow rerun was dispatched, and no current file replaced a historical source.
The complete required snapshots and their root-tree identities are recorded in
the verification report. Full ancestry beyond those snapshots is not required.

## Time and collector-identity boundary

The construction record is a **fixed local declaration**, not an externally
attested execution receipt. Its new `LOCAL_PRESERVATION=...` identity explicitly
does not name a GitHub Actions run or the earlier acquisition workflow.

Its `capture_started_utc` and `capture_completed_utc` values describe local
source/input inventory preparation. `packet_created_utc` is the declared logical
creation time at record finalization. The local system clock was sampled to
prepare those values; their recorded precision is one second. All three values
fall in the same second in this instance. This is not evidence of zero process
runtime, zero resource consumption, or instantaneous packet publication.

These declarations precede the producer invocations. **They are not the measured
start/end interval of either producer CLI and are not file-publication times.**
The report's `executions` array separately records each actual local CLI start,
completion, elapsed interval, exit status, stdout and stderr. Those diagnostics
are not used to rewrite the immutable reconstruction input during replay.

The unchanged producer verifies the record's exact content/source bindings and
temporal consistency; it does not independently authenticate collector identity
or clock accuracy. No live production collector attestation is claimed.

## Recorded construction and checks

The two direct constructions generated the same **484,234-byte** packet.
Both separate runtime-validator invocations completed with exit `0`,
`schema_valid: true`, `ok: true`, no errors, and all 34 listed semantic checks true.
Their complete stdout bytes were also identical; all four command stderr streams
were empty. Full commands, results and stream digests are preserved in the report.

The output contains **8 historical job records, 171 step records and 1 separately
identified collector**: 180 execution records in total. Job/step identifiers,
parent relationships, platform outcomes and timestamp spellings were compared
with the preserved raw response. Skipped outcomes remain skipped.

Historical policy order remains `required`, `release_required`. Process exit
codes, executed command bytes, runtime input/output consumption and unobserved
resource use are not fabricated. External-call, model-inference and
resource-measurement arrays remain empty: no such observations are provided,
not proof that no historical activity occurred. Overall coverage remains
**partial**, and the collector is excluded from historical subject totals.

Fresh complete direct-script regressions in this local session:

| Suite | Passed | Exit |
| --- | ---: | ---: |
| Historical runtime-packet producer | 74 | 0 |
| Observed subject-input context | 24 | 0 |
| Runtime-packet validator | 90 | 0 |
| Total across these three complete suites | 188 | |

Environment: CPython 3.13.5, pytest 9.0.2, jsonschema 4.26.0, PyYAML 6.0.3,
on Linux. No dependencies were installed or changed. These are local execution
results, not Python 3.11/3.14 results, GitHub CI, or a fresh run of all 153 registered
programs. The producer regression uses explicitly temporary test commits and
records; those fixture executions are separate from the direct source-bound
preservation commands above.

The previous cloud review could not perform historical-source-dependent replay
because `46b639...` was unavailable there. It reported no actionable source defect
and bounded implementation acceptance. The missing snapshot is present here;
these fresh results are **new evidence**, not a revision of the cloud report's
recorded limitations or an assertion that its skipped producer suite passed.

## Reproduce without changing the preserved bytes

Use Linux, an installed Python environment with the required dependencies, and
a clean source checkout at the fixed producer commit. That checkout must also
contain the exact required historical source objects. Do not substitute the
moving `main` tree for the fixed source, create replacement source commits, or
alter source pins to compensate for missing objects.

Set `SOURCE_REPO` to that checkout and `PRESERVED_DIR` to a separate copy of this
four-file directory. The new output directory must be outside the source
repository. The producer refuses existing output replacement.

```bash
set -eu
SOURCE_REPO=/absolute/path/to/source-at-d7def834
PRESERVED_DIR=/absolute/path/to/runtime_observation_packet_v0
M=d7def834e8aa63911426550cf41b05f81c0b56b0
EXPECTED_RECORD=877347d5e22410888614ac55698d4ebe82378d496ae5ee31fec945195a1a55e6

test "$(git --no-replace-objects -C "$SOURCE_REPO" rev-parse HEAD)" = "$M"
OUT=$(mktemp -d /tmp/pulsemech-runtime-replay.XXXXXXXX)

python3 -I "$SOURCE_REPO/tools/build_pulsemech_compute_runtime_observation_packet_from_capture_v0.py" \
  --repository-root "$SOURCE_REPO" \
  --construction-record "$PRESERVED_DIR/construction_record_v0.json" \
  --construction-sha256 "$EXPECTED_RECORD" \
  --output "$OUT/packet.json"

python3 -I "$SOURCE_REPO/tools/check_pulsemech_compute_runtime_observation_packet_v0.py" \
  --packet "$OUT/packet.json"

cmp -- "$OUT/packet.json" \
  "$PRESERVED_DIR/pulsemech_compute_runtime_observation_packet_6066_observed_v0.json"
sha256sum "$OUT/packet.json"
```

Expected packet SHA-256:
`76418f3a7374cf12127031b15806af1e80605ad07031b3b10308c3a30b795a88`.

The standalone runtime checker verifies packet schema and semantic relationships.
It does not independently acquire the original platform responses or authenticate
external collector declarations. Source/input fidelity is assessed through the
full producer/input-validator chain and exact reconstruction comparison.

## Unchanged authority and remaining handoff

```text
authority_effect: none
same_run_release_authority_eligible: false
active_gate_eligible: false
```

These are the preserved producer/report boundary, not newly added runtime-schema
fields. This handoff does not activate a gate, authorize a historical run,
measure resources, supply complete connected runtime proof, change policy, or
implement current-run pre-decision acquisition.

The four new preservation files do not modify existing producers, validators,
tests, schemas, contracts, capture members, workflows, CI registration, policy,
release-authority enforcement, Quality Ledger, Transition Meter, Device Ledger,
iPhone code, Zenodo metadata or any DOI relationship.

The source and data-preservation commits are different evidence identities.
A later upload or merge does not become this local construction's source revision
or its earlier platform acquisition identity. No future CI or reviewer verdict
is predeclared here. Canonical documentation synchronization remains the next
separate planned handoff under #2864. The issue is not closed by this record.
