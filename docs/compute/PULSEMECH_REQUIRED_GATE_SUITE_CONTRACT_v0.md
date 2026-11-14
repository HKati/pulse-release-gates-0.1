# Required-gate suite contract v0 — B1

## Implemented scope

B1 implements a closed declaration and evidence-obligation companion for a
finite metric suite. Its offline checker verifies the declaration's consistency
with a separately selected set of source, protocol, input and compute-packet
bytes. It does not execute the declared subject or calculate a metric.

The accepted [coverage plan](PULSEMECH_COMPUTE_REFERENCE_READINESS_v0.md#18-required-gate-coverage-plan-after-accepted-rejection-verification)
separates this structural unit from the later selection of a real protocol,
substantive calculation, independent reconstruction and release integration.
The [machine-readable plan](required_gate_coverage_plan_v0/coverage_plan_v0.json)
retains the original nineteen-gate inventory and its unresolved decisions.

Implementation preparation used main
`e9298e534c8ebdcb0a6e21b00f4c774970074bfa`, after PR #3017. That commit is the
preparation baseline. The new checker and schema are identified by their actual
content digests in the selected manifest; they are not represented as files that
already existed at that baseline commit.

## Files and dependencies

| File | Responsibility |
| --- | --- |
| [Schema](../../schemas/required_gate_suite_contract_v0.schema.json) | Closed declaration, external selection and protocol shapes; explicit draft and complete states. |
| [Checker](../../tools/check_required_gate_suite_contract_v0.py) | Strict parsing, selected-byte verification, finite coverage and packet-reference integrity. |
| [Tests](../../tests/test_required_gate_suite_contract_v0.py) | Positive structural cases, malformed input, coherent substitutions, reference failures and output protection. |
| [Synthetic fixtures](../../tests/fixtures/required_gate_suite_contract_v0/) | A fixed inventory of declarations and their separately selected synthetic dependencies. |

The checker uses the Python standard library, `jsonschema` and PyYAML, already
present in the repository's [requirements](../../requirements.txt). It adds no
runtime dependency, model, service, workflow, observer or generic relation
analyzer.

The supported runtime is Linux/POSIX with descriptor-relative, no-follow file
operations. Unsupported platforms return `platform_not_supported`; this checker
does not provide a weaker filesystem fallback. The repository CI and the local
validation use CPython 3.11.16.

## Trust direction and selected bytes

The caller supplies the expected SHA-256 of a separate selection manifest. The
checker first verifies the selected manifest's exact bytes. That manifest binds
the contract, the checker and schema, the known policy and registry, and the
referenced protocol/source/input/packet files.

This direction is deliberate: the declaration cannot nominate replacement
expectations for its own validation. A declaration changed under the original
selection is rejected. A changed selection is rejected under the original
caller-supplied digest. Recomputing a digest inside an untrusted bundle does not
replace the caller's independent selection.

The selection is a trust input, not an authentication service. A party that can
replace both the manifest and the caller's trusted digest can choose a different
selection. B1 reports that authentication is not established. Matching selected
source bytes does not prove a Git commit, signer identity, acquisition event or
actual execution.

Inputs are local, bounded regular files. The checker does not fetch a URL,
execute a selected source file or import the selected operator. JSON parsing
rejects duplicate keys, nonfinite values and unsupported shapes before a
declaration can be accepted. YAML aliases and merge keys are rejected before
construction, so they cannot expand ahead of the resource limits. Schema
references remain local; schema validation
does not retrieve remote references.

## Draft and complete declarations

A valid draft can retain explicitly unresolved decisions. Its populated
identities and references must still agree with the external selection. A draft
does not become complete because it parses, satisfies the JSON schema or has a
successful structural-check exit status.

A complete declaration resolves the selected subject/source, operator,
comparison, privacy/retention and observation mapping. It has a nonempty finite
case roster and complete per-selected-gate obligations. A declaration claiming
to be complete while retaining missing decisions or omitted expected cases is
rejected.

The selected gate set is checked against the actual selected policy and
registry. It cannot silently introduce an unknown gate or drop a selected
requirement. A suite may declare obligations for a selected subset of gates;
that subset does not replace the policy's complete `required` set or its separate
`release_required` obligations.

The separately selected protocol fixes cases and expected occurrences before
the companion is checked. Obligations identify the cases needed by each gate.
Different gates can legitimately refer to the same case; each retains its own
obligation. Reusing one execution as two distinct occurrences, omitting an
expected occurrence or presenting an unchanged baseline input as a perturbation is
rejected by the structural checks.

The supplied examples are permanently identified as synthetic fixtures. Their
source documents and comparison descriptions exercise the declaration
mechanics only. They do not select an operative PSF/control algebra, a real
subject, a production privacy policy or a native acquisition.

## Existing compute contracts and reference checks

B1 uses the existing
[subject-input schema](../../schemas/pulsemech_compute_subject_input_packet_v0.schema.json)
and [runtime-observation schema](../../schemas/pulsemech_compute_runtime_observation_packet_v0.schema.json).
It schema-validates the selected packet bytes and checks the companion's
execution and state references against them.

The implemented subject-reference projection is the schema's legacy subject
shape, including its explicit source-ref and event identity. The separate
bounded-reference subject shape requires an explicit future mapping and is
rejected with `packet_profile_unsupported`. Schema validity alone does not
silently enable an unsupported reference profile.

Reference checking includes unique identifiers before lookup, existence of
selected executions/states, matching subject/source/run/candidate identities,
and membership of selected input/output states in their named execution. An
observer execution cannot stand in for a subject occurrence. A referenced
output must agree with its declared producer.

Every occurrence must reference at least one input state with `exact_digest`
status and the selected case input's SHA-256 and byte count. When a case has
multiple occurrences, each occurrence is checked independently; a matching
input in one occurrence cannot satisfy another occurrence's input obligation.

These checks do not reconstruct an arbitrary runtime graph or prove event
ordering, timing, process closure, actual private reads or metric semantics.
The packets' own success fields are not used as evidence of those properties.
The existing full packet validators, binding analyzer and planned-observed
relation tools retain their responsibilities. B1 explicitly reports that full
packet semantics have not been verified.

Raw prompts, responses and other private payloads are not added to the generic
runtime packet schema. Real measurement payloads require a separately reviewed
carrier and privacy/retention contract in the subsequent protocol work.

## CLI and frozen synthetic examples

Run the following from the repository root to check the frozen complete
synthetic declaration. The literal selection hash below is a reviewed fixture
pin, not a hash inferred from the file during validation:

```bash
python tools/check_required_gate_suite_contract_v0.py \
  --root . \
  --contract tests/fixtures/required_gate_suite_contract_v0/complete.json \
  --selection tests/fixtures/required_gate_suite_contract_v0/complete_selection.json \
  --selection-sha256 d75577f91cc7c63984a4a9e7ad0cb70c17bc00c094b86483bda016f7eacba9b4
```

The unresolved example uses `unresolved.json`, `unresolved_selection.json` and
the independently frozen selection hash
`de84befb3090426026b899c28e151b26a40dae4cc6c5d3b0446a15b39c552b9a`.
Both hashes are also literal constants in the test module. Updating a selected
file requires an explicit reviewed selection change; it is not repaired by the
checker.

| Exit code | Meaning |
| --- | --- |
| `0` | Valid structural declaration, either draft or complete; inspect `declaration_complete` and `unresolved_decisions`. |
| `1` | Rejected contract or selected input, with a coded non-authoritative report. |
| `2` | CLI usage or output-path/publication refusal. |

Canonical report bytes are written to standard output. Optional `--out PATH`
publishes the same bytes to a fresh file; the parent directory must already
exist. An existing destination, unsafe path or authority basename is refused.
A safely selected report path can preserve a coded validation rejection as
well as a valid declaration result.

The Python API is
`validate_contract(contract_path, selection_path, selection_sha256, root)`.
It returns a valid report or raises `ContractError` with a stable `.code`.
`canonical_bytes(report)` produces the same deterministic JSON encoding used
by the CLI.

The fixed fixture inventory contains exactly 17 files:

| Files | Purpose |
| --- | --- |
| `complete.json`, `unresolved.json` | A complete synthetic declaration and a valid unresolved draft. |
| `missing_obligation.json`, `duplicate_case.json`, `substituted_binding.json` | Three deliberately invalid declarations exercised by the tests. |
| `complete_selection.json`, `unresolved_selection.json` | Independently pinned positive selections. |
| `synthetic_protocol.json` | The finite case/occurrence/obligation roster and explicit synthetic decisions. |
| `synthetic_source.txt`, `synthetic_operator.txt`, `synthetic_comparison.txt`, `synthetic_privacy.txt`, `synthetic_reconstruction.txt` | Selected synthetic source and decision text; none is executed or interpreted as a real protocol. |
| `baseline_input.json`, `variant_input.json` | Two distinct synthetic input byte sequences. |
| `subject_packet.json`, `runtime_packet.json` | Synthetic packets in the existing schemas, with partial coverage and unknown execution lifecycle retained. |

The positive example declares two selected gates, two cases, two occurrences and
two obligations. Both obligations use the same selected observations. The
report contains no gate verdict for either `effect_present` or
`psf_idempotence_ok`.

## Result and authority boundaries

A successful structural check records its input bindings and whether the
declaration is complete. The following limits apply to both valid drafts and
complete declarations:

| Result field | Fixed boundary |
| --- | --- |
| `execution_ready` | `false` |
| `execution_authorized` | `false` |
| `semantic_verification` | `not_run` |
| `packet_semantics_verified` | `false` |
| `metric_pass` | `null` |
| `production_gate_eligible` | `false` |
| `anchor_authentication` | `not_established` |
| `authority_effect` | `none` |

These are structural reports, not gate-result records. A valid negative metric
calculation belongs to the later substantive producer/checker work; structural
acceptance does not recalculate or relabel it.

The report is deterministic and includes no run timestamp or machine-specific
path. Optional file output is a fresh diagnostic report. Existing files,
protected decision basenames and symlink paths are rejected; selected inputs
and original evidence are never overwritten.

## Registration and preservation

The new test is registered exactly once in
[`ci/tools-tests.list`](../../ci/tools-tests.list). Its addition changes that
manifest from 182 to 183 entries. The 26 current-count expectations in 15
existing tests are updated together, including source-inspection strings and
regular expressions. Historical stale-count rejection cases are retained.
[`ci/pytest-tests.list`](../../ci/pytest-tests.list) remains at 40 entries.

The historical readiness document, coverage-plan JSON, original verification
archive and preservation record retain their original bytes. This implementation
does not modify gate policy, registry, required-gate dispatch, independent
candidate admission, thresholds or workflows. The existing twelve unsupported
classifications remain in force, and the historical Q2 result remains FAIL with
49 eligible groups against 50 required.

## Next boundary

B2 must select a real finite subject/operator/case protocol and its observation
mapping, comparison rules, source applicability and privacy/retention contract.
The synthetic B1 fixtures do not make those selections. B3 and B4 retain the
separate obligations for substantive calculation, independent reconstruction
and coordinated release admission.

The completed Q3 preflight and capture are not repeated by this change. Q3 input
selection, accepted response-bound labels, specification migration and release
admission remain explicit work items in the existing plan.

Keep [#2879](https://github.com/HKati/pulse-release-gates-0.1/issues/2879) open.
`authority_effect=none`.
