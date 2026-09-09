# Bounded execution evidence v0

This contract defines the finite, non-active checker/result-consumer observation
under work order #2875. It does not change the generic checker or release policy.

## Subject and inputs

A single genuine reference-workflow context contains the `allow`, `block_false`
and `missing_required` cases. Each case has one unchanged checker execution and
one distinct reference-state consumer. Test captures are explicitly `example`;
`observed` contexts require an independently supplied workflow/run/attempt/source
identity. Neither an environment variable nor a self-declared JSON context alone
is cryptographic workflow authentication.

Before any subject execution, the existing policy helper emits `core_required`
in its original order. An independent policy/registry read checks that output.
The existing integration planner runs in plan-only mode over a verified sparse
source view and an empty disposable target. Its request, component manifest and
plan are preserved. This preparation is not counted as observed subject work.

The controlled statuses set every required value to literal true, set the first
required value to literal false, or omit that first required gate, respectively.
These are controlled test inputs, not production model-evaluation evidence.

## Byte and process boundary

The capture verifies the committed source and input bytes before execution.
Only the fixed checker and consumer commands are supported. Source and input
buffers are Linux anonymous files sealed against write, growth and truncation;
the seal set itself is sealed. The exact descriptor/role/hash mapping and argument
vector are recorded. Children run under the recorded CPython interpreter with
`-I -S -B`, a private working directory and only the allowlisted environment.
There is no mutable-path fallback and no arbitrary shell-command mode.

The supervisor records raw stdout/stderr through bounded pipes, observes EOF,
and waits for the actual process result. Each process has a ten-second deadline;
each stream is at most 2 MiB. A signal, timeout, launch failure or missing EOF is
an acquisition error, not an exit-code-2 checker decision. No closed carrier is
published after such an error. Partial diagnostics are not accepted evidence.

The trusted boundary includes the reviewed supervisor, interpreter, runtime and
host kernel. The recorded interpreter digest is an identity measurement within
that boundary, not a proof against a privileged host. There is no claim of
host-wide tracing, external-call absence, model-use absence or resource usage.

## Result consumption and terminal roles

The checker produces its stdout/stderr and process outcome. The recorder, not
the checker, produces the JSON process-result envelope. This binds the exact
checker occurrence, invocation, prelaunch digest, context and stream bytes.
The separate consumer reads those sealed inputs and the case's pending state.
Its output is a new non-authoritative reference state: ready for code 0, held for
code 1 or 2, retaining the original code and distinct reason. The consumer's own
successful completion never changes BLOCK to ALLOW.

Checker stdout, stderr and the envelope must reach that case's designated
consumer. Equal bytes in different occurrences remain distinct logical states.
Consumer stdout (the final reference state) and stderr are explicitly terminal
roles declared before observation. They do not need an invented infinite chain
of downstream consumers. Removing an unresolved consumption requirement does
not make it terminal.

## Carrier, verification and reconstruction

The UTF-8 JSON representation is sorted-key, two-space-indented JSON with a final
LF, no duplicate keys or non-finite numbers. The closed schema has distinct
prelaunch, pending-state, process-result, terminal-state and capture kinds.
The prelaunch spec binds all source/input members but never future outputs.
The capture inventory binds all members except its own manifest. A deterministic
ZIP_STORED carrier sorts members, fixes timestamp/mode and contains no directories,
links, encryption, comments or extra fields. Limits are 128 members, 2 MiB per
member and 16 MiB total uncompressed content. Verification never extracts it.

Independent validation requires both an expected context and expected prelaunch
digest supplied outside the carrier, plus genuine matching Git source objects.
It verifies the closed inventory, exact committed source bytes, input recipes,
policy order, planner contracts, all six execution slots, ordering, descriptor
bindings, waited results, actual consumer input identities and terminal states.
It does not import the capture or consumer implementation, and it does not
re-execute subject programs to pretend it has repeated the original acquisition.
A wholly self-declared package can establish internal relations, not authentic
acquisition provenance. Reference acceptance also needs the separate workflow
provenance checked by the owner/reviewer.

Fresh acquisition may produce different times, PIDs and descriptor numbers.
Deterministic replay begins from one fixed preserved capture; it must not invent
new observations, silently normalize raw stream bytes or replace historical pins.

Publication is external to the source repository and must not replace any
existing output. Publication stages an anonymous `O_TMPFILE` inode and atomically links it to
the absent destination. Closing an unlinked descriptor is rollback; no visible
pathname is ever deleted, including after a competing writer wins the destination.
This requires Linux/filesystem support, without a mutable named-file fallback.
Atomic visibility is claimed; post-crash directory-entry durability is not.

## Integration and claim limits

The Step 5B evidence is intended for a narrowly discriminated profile in the
existing subject producer, immutable bridge, analyzer and report/relation
validators. This contract alone does not establish that integration is complete.
The historical #6066 profile and its partial packet remain unchanged. The
example-only extent allowance cannot serve as observed extent evidence.

Keep packet integrity, observation extent, relational coverage, comparison
completeness and resource coverage distinct. A complete comparison can find a
mismatch. Resources remain unavailable. No candidate result is release authority.

```text
authority_effect: none
same_run_release_authority_eligible: false
active_gate_eligible: false
```

The wider Step 5 proof, actual preserved reference acquisition, Step 6 measurement
and Step 7 promotion remain separate evidence/decision handoffs.

## Reference profile through existing processing

`bounded_execution_reference_v0` discriminates the new subject-input, report and
comparison documents from their legacy alternatives. Legacy required fields and
historical source pins are unchanged. The reference subject has no fabricated
production final-status or release-decision object. The report first represents
stored artifacts without claiming executed edges, then separately represents the
six source-bound, recorded direct processes and their applicable state relations.

A report requires `bounded_binding` and an independent expected acquisition
context, prelaunch digest, subject packet and exact carrier. A runtime report also
requires the independently checked original-v0 runtime packet. Its artifact
baseline hash is reconstructed from those same inputs. Report and relation replay
verify the installed dependency revision/path/bytes before executing dependencies.
The closed bounded profile is not enabled by changing `analysis_level` alone.

The runtime packet's producer identity names the analyzer core's deterministic
projection implementation. Its required collector record describes that projection
with explicitly unknown outcome/timing/command, not a fictitious seventh observed
subject process. Whole-packet coverage stays partial and resources unavailable.
The separate validated bounded evidence establishes source/extent/relational
coverage only for the six direct processes; it does not declare this projection
collector or the entire host completely observed. Legacy partial-collector rules
continue to apply to the legacy comparison profile without modification.

The existing integration planner supplies two component operations; the prelaunch
case slots expand them into six exact execution expectations. `bounded_execution_id`
is a mandatory occurrence selector only in this comparison profile. It is checked
before source/name scoring, so three checker invocations of identical source cannot
merge. Expectation bytes are derived from the prelaunch plan/case records, never
from observed records. The owner-run procedure fixes these bytes before acquisition.

Source-aware relation checking rebuilds the report and relation from exact input
bytes and requires byte-derived plan/report locators. An individually or jointly
forged locator, substituted occurrence, raw packet, context, or source dependency
cannot be accepted solely because its surrounding hashes are internally coherent.
Consumer terminal states are declared boundary endpoints, not invented reads by
additional processes. Recorder-produced result envelopes retain recorder ownership.

The existing candidate materializer applies its unchanged three boolean
derivations after strict bounded relation validation. A fully bound controlled
reference can produce three true values while retaining checker exits 1 and 2.
Those candidate values describe the recorded path/authority-binding/mutation
relations; they are not assertions that every checker returned ALLOW, that the
reference inputs are production evidence, or that a release is authorized.
Actual versus expected checker outcomes remain visible in `case_outcomes`.

## Manual reference procedure and outer preservation carrier

The new workflow is `workflow_dispatch` only. It requires the owner's reviewed
40-hex source commit to equal the triggering checkout and control-plane workflow
revision. The repository, workflow path/name, branch, run ID/number and attempt
must agree with the independently supplied GitHub context. Environment fields
remain within the stated control-plane trust boundary, not signed attestations.
The workflow has read-only contents permission and no deployment/policy write.
Its identity and exact source are included in the prelaunch source inventory.

The `run-reference` adapter prepares inputs and expectations, launches the fixed
capture entrypoint, then invokes `reconstruct` in two separate processes over the
same saved capture. It compares all derived bytes, not timestamps from new subject
executions. Reconstruction uses the existing bridge/core, separate report and
relation validators, and existing non-active candidate derivations.

Only after successful comparison does it publish `reference_capsule_v0.zip`.
Its five payload members are `prepared.zip`, `capture.zip`,
`expected_context.json`, `expected_prelaunch.sha256` and `reconstruction.zip`.
A sixth member, `SHA256SUMS`, lists the five finalized payload hashes in filename
order and does not contain its own hash. The outer capsule is an export carrier,
not a replacement evidence schema or a verifier verdict. Its members still require
independent source-aware verification and separately checked acquisition provenance.
The inner capture remains the exact bounded evidence carrier used in reports.

Ordinary tests use `example` contexts. The implementation, its local examples and
this contract do not predeclare a public dispatch, preserved observed reference,
future artifact digest or completed Step 5B acceptance.
