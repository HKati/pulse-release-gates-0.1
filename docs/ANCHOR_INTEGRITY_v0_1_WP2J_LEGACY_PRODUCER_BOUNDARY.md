# Anchor Integrity WP2J — legacy JSON producer boundary

**Status:** diagnostic-only correction of the existing v0 producer.  
**Preparation base:** `3768fd08b28c61c5e06a16c29b4dfa6c67b340a0`.  
**Producer profile:** `legacy-v0-unmeasured-boundary-v1`.  
**Authority effect:** `none`.

## 1. Purpose and intentional compatibility change

[WP2I](ANCHOR_INTEGRITY_v0_1_WP2I_LEGACY_READER_BOUNDARY.md) corrected the Markdown
reader but deliberately left the JSON producer unchanged. WP2J changes the
existing [JSON producer](../scripts/anchor_integrity_adapter_v0.py) itself.
The old default could turn five heterogeneous gate declarations into
`anchor_coverage`, `ANCHORED`, `ANSWER` and `OPEN`; Paradox metadata alone could
produce `loop_risk=low`. Those are not claim/evidence or cycle measurements.

Retain the `anchor_integrity_v0` wire shape and CLI paths, but intentionally
change the meaning of newly generated values to a conservative, unmeasured
compatibility diagnostic. This is not a complete WP1 adapter, automatic claim
extraction, source authentication, semantic verification or response enforcement.

This is **not a deployment**. Old JSON/Markdown artifacts and published copies
are not rewritten or rehashed. External consumers and dynamic callers are not
claimed to have been exhaustively inventoried or migrated.

## 2. Exact new producer behavior

Every successfully written output has:

```text
schema = anchor_integrity_v0
invariants.anchor_presence = null
invariants.anchor_coverage = null
invariants.loop_risk = null
invariants.contradiction_risk = null
state = UNKNOWN
recommendation.response_mode = SILENCE
recommendation.gate_action = CLOSED
```

The last three values are the existing schema's conservative compatibility
placeholders. They do not establish missing/false anchors, force model silence,
block a normative release, or attest that any evidence check ran. The rationale
states this limitation explicitly. `invariants.notes` carries the producer
profile and diagnostic/non-authorizing meaning. An `evidence` entry of kind
`producer_profile` also records the exact profile string; it is not a signature.
The v0 schema does not contain structured execution states. A textual `not_run`
note does not invent that structure or claim the v0.1 output contract is complete.

Only literal Boolean values for the five known signal IDs are retained as
`operational_signal` notes, marked as unverified gate declarations. Do not
interpret strings, integers, numeric percentages, nested `passed`/`status`
objects or additional success fields. All-false signals do not prove anchor loss.

There is **no gate ratio** computation or numeric proxy output in this profile.
The unchanged v0 schema has no separate typed operational-proxy field, so its
`anchor_coverage` slot must not be reused for that purpose. Per-gate notes remain
informational; they are not machine-readable claim-support evidence. This
intentionally retires the legacy aggregate rather than encoding a hidden ratio
inside another field. No new output schema is introduced.

A parsed Paradox metadata object is noted as present, including an empty object.
No value, source name, transition path or alleged result can become a cycle or
risk finding. Missing metadata cannot become an empty successfully checked graph.
Untrusted free-text notes, rationale, instructions and claim-like fields are not
copied into the output. Selected CLI/environment identity fields are only
caller-supplied metadata, not authenticated identities.

For actual bound inventory, structural-cycle and signature diagnostics, use
[WP2H](ANCHOR_INTEGRITY_v0_1_WP2H_DIAGNOSTIC_INTEGRATION.md) with real explicit
selection and evidence inputs. This adapter neither invokes WP2H nor fabricates
claim/evidence packets from gate flags. It does not use saved success reports.

## 3. Parsing, output and exit boundaries

Read at most 8 MiB per selected input. Accept a strict UTF-8 JSON object, reject
duplicate keys, NaN/infinities (including exponent overflow), malformed JSON,
non-object roots, nesting beyond 64 containers, symlinks and non-regular inputs.
The depth precheck ignores quoted/escaped delimiters and does not replace the
standard JSON grammar parser. Interpreter recursion settings cannot enlarge it.
Use a nonblocking input open on POSIX to avoid waiting on a FIFO, and compare
file metadata before/after the bounded read. These are local input checks, not
source authenticity or a filesystem snapshot. Missing/non-object `gates` are
reported explicitly, without a percentage or a count-derived decision.

Missing, malformed or unavailable input still permits writing an explicitly
unknown diagnostic with fixed input-diagnostic codes. Do not echo OS exceptions
or source text as findings. This is format admission, not validation of all
PULSE status semantics. The optional `--paradox-source ''` disables that input.

Preserve `--status`, `--paradox-source`, `--out`, `--run-id`, `--commit` and their
original default paths. `SOURCE_DATE_EPOCH`, when set, must contain an unsigned
ASCII decimal integer in `[0, 2**63 - 1]`; it is metadata, not a trusted clock.
Invalid metadata or unsafe/unavailable output returns 2 without intentional
source modification. Successful serialization returns 0, even for unknown
input; **exit 0 is not an evidence PASS**. There is no automatic retry.

Protect both status and Paradox input roles against output aliasing. Reject a
same/resolved path even when missing, existing output symlinks, hard-linked
outputs and non-regular output targets. A separate ordinary output file may be
explicitly replaced, as before. The parent directory is not created implicitly.
A failed write may leave partial output; consumers must check exit status and
must not admit a previous output after a failed invocation. No atomic publication,
crash-safe replacement, hostile-host or concurrent-writer containment is claimed.
The local host, filesystem and output directory are trusted assumptions.

The existing [v0 schema](../schemas/anchor_integrity_v0.schema.json) and
[contract checker](../scripts/check_anchor_integrity_v0_contract.py) stay unchanged.
They still accept historical shapes and do not certify that an arbitrary v0
file was produced by WP2J. A forged old file is not newly authenticated by this
change. The corrected WP2I reader continues to handle historical values as
reported proxies; a new null value is displayed as unavailable, never zero.

## 4. Historical reproduction and explicit test replacement

The exact original producer already exists in the source-bound
[historical fixture](../tests/fixtures/anchor_integrity_v0_1/adapter_v0_34431ec8.source.json):

```text
historical source commit: 34431ec8ebe305a83273ffd39b78f083219f03e6
Git blob: 3f4afe26be361fddda153f72dd20803183a85a8e
bytes: 11457
SHA-256: 3ceb60e9ca0a5d3a7d142bc91f5f51ca0376f54a37f33c3f359774f25c42f1d0
```

The live preimage at this preparation base has that same Git-blob identity.
Do not modify the historical inventory, encoded fixture, old example digests
or previous output artifacts. Runtime never loads or executes the fixture.
Tests may replay that reviewed historical program in a temporary directory on
synthetic data; the exact old `1.0 / low / ANCHORED / ANSWER / OPEN` behavior
remains reproducible without keeping a permissive legacy runtime switch.

Change **one preservation guard** deliberately:
`test_wp2i_raw_v0_producer_remains_exactly_preserved` becomes
`test_wp2i_raw_v0_producer_remains_historically_preserved_after_wp2j`.
It verifies the existing fixture's pinned source, length, Git blob and SHA-256
instead of requiring the live producer to remain defective. Retain all other
previous definitions/decorators and add regressions for the new active behavior.
This is an explicit preservation-boundary change, not a claim that every old
assertion is byte-identical.

## 5. Example and validation scope

The synthetic [status](../examples/anchor_integrity_v0_1/wp2j_legacy_producer/status.json)
sets all five signals true. The [Paradox metadata](../examples/anchor_integrity_v0_1/wp2j_legacy_producer/paradox.json)
is present. From that example directory, in a reviewed checkout:

```sh
SOURCE_DATE_EPOCH=0 python ../../../scripts/anchor_integrity_adapter_v0.py \
  --status status.json --paradox-source paradox.json --out actual.json \
  --run-id synthetic-wp2j --commit fixture-not-a-source-commit
```

The output must match [expected.json](../examples/anchor_integrity_v0_1/wp2j_legacy_producer/expected.json).
All four measurements remain null and the state stays UNKNOWN despite the
positive gates. No live observer, verifier or model is run by this example.
The old historical program on the same inputs demonstrates the previous behavior.

Extend the already-registered Anchor test module only. Both CI manifests are
unchanged: 177 tools / 33 targeted-pytest entries at this preparation base.
The source-tree counts are not taken from an older delivery or a failure log.
No workflow, dependency, required gate, status/policy, release checker, WP2A-H
runtime/schema/example, WP2I renderer or repository setting is changed.

Regression cases cover positive/negative/missing Boolean signals, non-Boolean
coercion, alleged support, malformed/duplicate/non-finite inputs, file limits,
read changes, metadata, both input/output alias roles, deterministic output,
historical replay, unchanged v0 shape and WP2I rendering. Actual execution
results belong to the delivery report; no hosted CI, full repository-suite,
Windows qualification, independent audit or production accuracy is inferred.
