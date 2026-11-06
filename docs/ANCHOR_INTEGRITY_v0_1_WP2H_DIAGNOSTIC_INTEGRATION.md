# Anchor Integrity v0.1 WP2H — fresh diagnostic integration

**Status:** offline diagnostic candidate, not the complete WP1 adapter or release authority.  
**Preparation base:** `625aa536ab1f5e3adc695c1a2d2ed9d11ca74101`.  
**Profile:** `fresh-anchor-diagnostic-v1`.  
**Deployment:** separate JSON/Markdown output; existing v0 producers, renderers and publication paths are not replaced.

## 1. Purpose and output boundary

[WP1](ANCHOR_INTEGRITY_v0_1_CONTRACT.md) distinguishes a gate-signal proxy from
claim-level evidence coverage, and an unperformed check from a measured result.
WP2H combines the executable checks already available into one scope-labelled
view. It neither invents missing checks nor accepts saved success reports.

The new [adapter](../tools/build_anchor_integrity_diagnostic_v0_1.py) emits
`anchor_integrity_diagnostic_report_v0_1`, **not** the frozen
`anchor_integrity_output_v0_1` contract. The latter includes independent-anchor
and supported-claim meanings which this increment cannot establish. The new
report makes `wp1_output_emitted=false` explicit.

```text
reported legacy gate ratio
!= referenced-anchor presence in a declared claim set
!= authenticated source identity
!= verified binding coverage
!= verified semantic support
!= independent-anchor classification
!= execution admission
!= release authority
```

## 2. Selection, trust roots and fixed pipelines

Use an externally retained expected hash for a
[closed-shape selection](../schemas/anchor_integrity_diagnostic_selection_v0_1.schema.json).
The selection contains the exact path/hash expectations and profiles for the
chosen fixed pipeline. The caller provides the directory roots separately; the
selection cannot name a Python module, executable, network URL or saved report.

| Pipeline | Fresh stages | Policy roots |
|---|---|---|
| `local-records` | WP2A/WP2B and WP2C | Not accepted |
| `receipt-signatures` | WP2A/WP2B, WP2C, WP2E, WP2F and WP2G | Explicit verifier and observer roots required |

The cycle choice is also explicit: `typed-dependencies-v1` or `not_requested`.
There is no fallback from a failed signature pipeline to the local pipeline.
A missing profile is an invalid selection, not a default trust decision.

Pin the selection independently of the candidate at admission. Its three or
nine nested file hashes are transitive caller expectations, not signatures or
authenticated policy provenance. The fixture commands below contain fixed pins;
do not replace a failed expected hash with the candidate's observed hash.

Selection, evidence and any policy roots must be pairwise disjoint by resolved
path and opened directory identity. They use the existing bounded POSIX reader.
This is structural role separation, not proof of independent people, custody,
policy acquisition or a hostile-host isolation boundary.

## 3. One retained evidence reader

All evidence stages share one `BundleReader`. The adapter invokes the existing
review methods without modifying their implementations or reports. In the
receipt pipeline, the binding check runs once through WP2G/WP2F/WP2E/WP2C.

When cycles are selected, [WP2D](ANCHOR_INTEGRITY_v0_1_WP2D_DEPENDENCY_CYCLES.md)
uses the same freshly executed `RecordReview` and the same retained graph and
packet bytes. It performs its own graph schema, subject, packet and typed-edge
checks before actual SCC analysis. It does not reopen a second evidence root,
merge reports from separate runs or infer that a saved report was executed.

Each invoked stage receives an outcome and an exact deterministic JSON-report
fingerprint in `stage_receipts`. An uninvoked stage has `executed=false` and null
outcome/hash. These fingerprints describe current checker results, not external
attestations. Previous reports are not rewritten to promote their scope.

Retained bytes are not an atomic filesystem snapshot or a promise about later
path contents. A path modification after capture does not change the bytes
being analyzed; a new invocation checks the changed path against its pins.

## 4. Coverage and claim diagnostics

Only a fresh `LOCAL_BINDINGS_CONSISTENT` result permits claim inventory
aggregation. Let D be the number of unique claims in the explicitly materialized
claim set, and N the number with at least one checked claim-to-evidence reference.
The presence metric is computed as N / D. Multiple references from one claim
count once. `references`, `supports` and other relation labels do not change
presence into support. Per-claim evidence IDs and recorded relation declarations
are retained separately.

This is coverage **of the declared claim inventory**, not independently proved
coverage of every claim in the original natural-language response. Automatic
claim extraction and independent inventory completeness are not implemented.
The report fixes `whole_response_completeness_established=false`.

The existing WP1 schemas require a legacy-overlay descriptor and at least one
claim in a `complete` or `partial` set. WP2H does not relax those contracts:
a null legacy descriptor and an empty `complete` set are invalid. Missing
material files are incomplete. A valid `partial` or `invalid` materialization
keeps all three coverage metrics `not_applicable`, with null counts and value.
Other failed prerequisites leave unmeasured coverage null, not zero.

`verified_binding_coverage` remains unmeasured because source-identity
authentication is not implemented. `verified_support_coverage` remains
unmeasured because semantic support has not been verified. Valid source bytes,
matching verifier records and authorized signatures cannot populate those
metrics. Every claim disposition remains `unresolved`; recorded `supported`
and `contradicted` declarations are not accepted dispositions.

The adapter reconciles numerator, denominator, unique claim IDs, referenced
IDs and division arithmetically. JSON Schema validation alone is not an
arithmetic proof.

## 5. Legacy proxy isolation

After fresh byte binding, the adapter may display the numeric
`invariants.anchor_coverage` from a correctly tagged legacy v0 object **only** as
`legacy_operational_proxy.reported_value`. It is a reported historical signal,
not a newly performed gate measurement. No normalization or percentage coercion
is used. Booleans, strings, out-of-range numbers or other malformed values are
not numeric observations. An absent numeric value is unavailable, not zero.

The original v0 `state`, `response_mode`, `gate_action` and risk labels do not
supply claim dispositions, support coverage or recommendations. Even a v0
`ANCHORED` / `ANSWER` / `OPEN` / `low` declaration cannot promote the new result.
The new example deliberately displays proxy 1.0 alongside presence 1 / 2,
unmeasured verified coverage and an actual structural cycle.

## 6. Cycles and conservative recommendations

A selected, valid WP2D stage exposes `cycle_detected` or
`no_cycle_detected_in_declared_graph`, plus its concrete cyclic components and
witnesses. The projection remains `declared_edges_only`. Missing graphs or
invalid graph bindings never become an empty successful graph.

When the cycle stage is not selected it remains `not_run` with a null result,
even if the old input's requested-check flags name a cycle check. Both the
selected profiles and those original flags are visible; the diagnostic does
not claim all original requests are fulfilled. `requested_checks_complete`
is always false. `LOCAL_DIAGNOSTIC_BUILT` describes only this selected diagnostic
construction, not complete WP1 verification.

`cycle_anchor_classification` is still `not_run` / null. The compatibility risk
slot `loop_risk` is always null; a structural observation is not a low/medium/high
risk measurement. Neither a valid signature nor absence of a declared cycle
establishes independent grounding or whole-response cycle freedom.

The adapter offers only two non-enforcing recommendations. A valid, nonempty
checked claim inventory with no referenced anchors yields `ASK_FOR_ANCHOR`.
All other cases yield `BOUNDARY`: in particular missing/invalid prerequisites,
recorded support/contradiction without accepted semantic verification, and
otherwise locally consistent input. It does not infer `ALLOW_SUPPORTED`,
`BOUNDARY_CONTRADICTION`, `PARTIAL_BOUNDARY` or `SILENCE` from legacy labels or
unimplemented methods. Recommendation authority is `diagnostic_only`, enforced
is false, and the legacy numeric proxy is not its decision input.

## 7. Signature and execution scopes

The optional receipt pipeline retains [WP2G](ANCHOR_INTEGRITY_v0_1_WP2G_RECEIPT_SIGNATURES.md)'s
TEST/OPERATOR distinction, exact scope, separate keys and policy-bound receipt
signature. The report records the selected record/execution/observer, challenge,
caller-supplied evaluation epoch and observation basis. This selected receipt
does not cover every claim or establish that an observer or verifier ran.

All upstream required record signatures are checked, but the receipt contract
still concerns one explicitly selected execution. An authenticated synthetic
receipt remains synthetic. The time is not a trusted clock and the policy
snapshot is not a freshness/rollback oracle. Keep all of the following false:

```text
accepted_as_execution_evidence
accepted_as_semantic_support
accepted_as_independent_anchor
release_authority_activation
whole_response_completeness_established
whole_response_cycle_freedom_established
```

A valid lower-level observation may remain visible when another selected stage
fails. For example, consistent local bytes do not disappear when a receipt
signature is invalid. The aggregate stays invalid and the recommendation stays
`BOUNDARY`; partial rows are not aggregate approval.

## 8. Output, exits and resource boundary

| Exit | Status | Meaning |
|---|---|---|
| 0 | `LOCAL_DIAGNOSTIC_BUILT` | Selected diagnostic stages and local aggregation completed, even when a cycle exists or semantic support is unmeasured. |
| 1 | `LOCAL_DIAGNOSTIC_INVALID` | An observed schema, identity, byte, policy or signature conflict. |
| 2 | `LOCAL_DIAGNOSTIC_INCOMPLETE` | Required material is missing. CLI/installation failures also return 2, without success-shaped JSON. |

Invalid takes precedence over incomplete findings actually observed. A stage
may stop early; this is not an exhaustive inventory of inaccessible later faults.
There is no release allow/block decision. Tests of this code are not activation
of its output as a required gate.

JSON is the default stdout format. `--format markdown` executes the same fresh
pipeline and renders its validated result with a distinct WP2H heading and
explicit unmeasured labels. It is not a CLI for ingesting a saved report. The
renderer does not interpolate evidence prose or legacy recommendation text.
It emits no old v0 filename and has no output-file overwrite option.

The inherited reader and graph limits remain. A selection is additionally
limited to 64 KiB. Only fixed trusted code is loaded, with bytecode writes
disabled during loading. There is no new network access, arbitrary command,
model call, operational capture, signing/private-key API, workflow or dependency.
The receipt mode retains OpenSSL 3.x at `/usr/bin/openssl` and its per-backend
budgets. Local-record mode does not invoke the cryptographic backend.
The host, installed schemas/modules and roots remain explicit trust assumptions.

## 9. Existing v0 surface inventory and migration boundary

Inspection at the preparation base identified:

| Surface | Existing behavior | WP2H treatment |
|---|---|---|
| `scripts/anchor_integrity_adapter_v0.py`, `_anchor_signals_from_status`, lines 100–142 | Computes a heterogeneous gate ratio called `anchor_coverage`. | Unchanged; an admitted legacy value is labelled reported operational proxy only. |
| Same file, `_loop_risk_from_paradox_source`, lines 145–166 | Returns `low` without a cycle computation. | Unchanged historical source; the new risk slot is null and actual WP2D observations are separate. |
| Same file, `main` | Default JSON output is `anchor_integrity_v0.json`; reads baseline status and optional Paradox metadata. | Not invoked or replaced. |
| `scripts/check_anchor_integrity_v0_contract.py` | Existing v0 contract checker. | Not replaced by this report's different schema. |
| `scripts/render_anchor_integrity_overlay_v0_md.py`, `main` | Default input is `PULSE_safe_pack_v0/artifacts/anchor_integrity_v0.json`; output is `PULSE_safe_pack_v0/artifacts/anchor_integrity_overlay_v0.md`. | No overwrite or silent reinterpretation. |

GitHub source searches for the adapter name and its JSON filename located the
producer, contract checker, renderer and documentation/fixture references.
The roadmap-named `.github/workflows/anchor_integrity_overlay.yml` returned 404
at the pinned base. These scoped searches are **not** a full-checkout scan,
proof of all dynamic callers, or an audit of a deployed website.

The adapter blob is `3f4afe26be361fddda153f72dd20803183a85a8e`; the renderer blob
is `73ec5aeabeb05d6018be62fa79954e1c73dfe0a9`. Neither is part of this change.
The historical baseline and its reproduction fixtures remain unchanged.

**This package does not remove the two legacy behaviors from existing v0 output.**
It provides a separate correctly scoped candidate output. Production/publication
migration still needs an explicit caller inventory, compatibility decision and
owner-authorized change. Do not feed this report to the v0 renderer or replace a
v0 artifact under its old filename/schema.

## 10. Reproduce the two synthetic diagnostics

Run from a reviewed repository checkout with the preceding Anchor increments.
The [cycle selection](../examples/anchor_integrity_v0_1/wp2h_diagnostic_integration/selection/cycle.json)
uses a new synthetic bundle; earlier examples are unchanged.

```sh
python tools/build_anchor_integrity_diagnostic_v0_1.py \
  --selection-root examples/anchor_integrity_v0_1/wp2h_diagnostic_integration/selection \
  --selection cycle.json \
  --expected-selection-sha256 4d457524a1e66899d9f7b7e4ee8f2223906b0c1feaf31833295cceef447439a0 \
  --bundle-root examples/anchor_integrity_v0_1/wp2h_diagnostic_integration/cycle-bundle
```

Expected: proxy 1.0, referenced-anchor presence 1 / 2, a concrete structural
cycle, `BOUNDARY`, null verified coverage and null loop risk. Add
`--format markdown` for the human-readable view. Both formats run the checks.

The [receipt selection](../examples/anchor_integrity_v0_1/wp2h_diagnostic_integration/selection/receipt.json)
reuses the unchanged earlier WP2G bundle and its two public TEST-key policies:

```sh
python tools/build_anchor_integrity_diagnostic_v0_1.py \
  --selection-root examples/anchor_integrity_v0_1/wp2h_diagnostic_integration/selection \
  --selection receipt.json \
  --expected-selection-sha256 9ece72adc945874751039b495a82a885de0bb230ddb91ff53799471326746d69 \
  --bundle-root examples/anchor_integrity_v0_1/wp2g_receipt_signatures/bundle \
  --trust-root examples/anchor_integrity_v0_1/wp2g_receipt_signatures/trust \
  --observer-trust-root examples/anchor_integrity_v0_1/wp2g_receipt_signatures/observer-trust
```

Expected: a freshly verified TEST-key receipt statement, the same 1 / 2 declared
presence, no cycle stage selected, and no execution, semantic or anchor admission.
These are authored fixtures, not operational captures. No production key is added.

## 11. Tests and integration

Extend the already registered `tests/test_anchor_integrity_v0_1_contract.py`.
Both manifests and their preparation-base counts (175 tools / 31 targeted
pytest entries) remain unchanged. No new count assertion is introduced.

Regressions exercise numeric/proxy isolation, exact arithmetic, duplicate
references, declared support/contradiction non-promotion, partial/invalid/empty
claim sets, graph prerequisites and witnesses, fresh signature-chain reuse,
combined receipt-and-cycle observation, retained bytes, raw and rehashed
substitution, strict selections, links/aliases/roots, CLI exits and both formats.
Recorded local results are separate delivery evidence, not a hosted-CI claim.

All earlier runtime modules, schemas, examples, workflows, status/policy files,
required gates, release authority, Pages/OG/History/SARIF, Q3/W1 and DOI/SWH remain
unchanged. No native experiment or operational collector/verifier execution is
authorized by this delivery. A new PR head requires CI and review.
