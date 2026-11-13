# PULSEmech / Paradoxon Diagram — Cyclic evaluator v0

**Status:** bounded research implementation with local regression checks.
**Checking semantics:** `PD-CYCLIC-DETERMINISTIC-v0`.
**Preparation baseline:** `24fa97fb9dd4d69b52d9e6ce3e3b0ccb311b4ce0`.
**Authority effect:** `none`.
**Production-gate eligible:** `false`.

## 1. Purpose and source boundary

This implementation evaluates the six questions in the merged
[cyclic case contract](PULSEMECH_PARADOX_CYCLIC_CASE_CONTRACT_v0.md)
and checks the resulting proof obligations against the exact input bytes.
The supported profile covers all five frozen cases. It distinguishes a
removed direct relation, a feasible indirect failure route, one return to
a mode, complete-state return, counter projection and unbounded repetition.

The four source files introduced by PR #3012 remain unchanged:

- [Contract](PULSEMECH_PARADOX_CYCLIC_CASE_CONTRACT_v0.md).
- [Structural schema](../schemas/paradox_cyclic_case_contract_v0.schema.json).
- [Case inputs](../examples/paradox_cyclic_case_v0/cases.json).
- [Hand-derived reference](../examples/paradox_cyclic_case_v0/expected.json).

They are preserved in the [preparation baseline](https://github.com/HKati/pulse-release-gates-0.1/tree/24fa97fb9dd4d69b52d9e6ce3e3b0ccb311b4ce0).
The input's own `source_baseline` remains
`1fbc52660cb1085b6cd419ff733000e7afe163f7`: it identifies the earlier contract
source context and is not rewritten to pretend that those bytes were newly
acquired with this implementation.

The evaluator and checker read no reference file. Only regression tests
compare computed claims with the hand-derived reference, after checking its
raw input digest, baseline and exact unique case correspondence. Reference
reasoning strings are not executable premises.

## 2. Measurement objects and workstream placement

This continues the operational recurrence workstream defined by the cyclic
contract. H1's measurement-target distinction is retained by making the
object of each question explicit:

| Question | Inspected object |
|---|---|
| Q1: direct relation removed | Same subject, initial mode and failure target in both complete inventories. |
| Q2: displayed failure route feasible | The selected subject's exact after-route steps and guards at their actual counters. |
| Q3: failure then mode return | Complete deterministic continuation and jointly enabled guards through failure and back to the initial mode. |
| Q4: complete-state return | The strict counter increment of every admitted transition. |
| Q5: counter projection sound | Enabled projected successors at every declared mode and counter for the selected subject. |
| Q6: structural pattern repeatable | Each guard on every counter progression of the returning rule word. |

This checks the declared modeled objects. It does not independently establish
that an external measurement target is relevant, useful-operation conditions
are preserved, or an external causal mechanism has been repaired. The
[H1 case](PULSEMECH_PARADOX_MEASUREMENT_TARGET_AND_REPAIR_CASE_v0.md)
remains the research basis for that wider distinction.

The [W1 assessment](experiments/PD_SM_02_W1_RELATION_AND_PROVENANCE_ASSESSMENT_v0.md)
and original W1 acquisition retain their existing scope. This implementation
does not rerun W1, resolve its historical runner-image discrepancy, attest
native acquisition, extend the LRM grammar, or modify release authority.

## 3. Supported input profile and processing outcomes

All admitted states, guards and meanings are those of the frozen contract.
The implementation adds explicit limits:

- Each phase has at most one outgoing rule for each `(subject_id, from_mode)`.
- The initial mode differs from the declared failure mode.
- Every rule preserves its subject and increments the nonnegative integer
  counter by exactly one.
- Guards are unconditional, `counter_below(limit)`, or a declared predicate
  of `(subject_id, mode, counter)` with a fixed total Boolean interpretation.
- Supplied predicate facts are finite, exact and jointly consistent. An absent
  fact remains unknown; interpretation does not vary during a course.

Parallel rules are outside this implementation even if their guards appear
mutually exclusive or one is disabled. They are not silently pruned or
translated into another grammar. The broader input contract remains intact.

| Processing outcome | Meaning |
|---|---|
| `COMPLETED` | All six scoped judgments and their obligations were produced for every admitted case. |
| `INPUT_INVALID` | JSON, exact shape, declared meaning, identity or cross-reference checks failed. |
| `INPUT_UNSUPPORTED` | The bounded implementation cannot admit the requested scope or resource size. |
| `REPORT_REJECTED` | Submitted report bytes, bindings, obligations or claimed judgments failed checking. |
| `VERIFIED` | Every submitted obligation and judgment was checked against the exact admitted input. |

These processing outcomes differ from the three model judgments:
`ESTABLISHED_IN_MODEL`, `REFUTED_IN_MODEL`, and `UNRESOLVED`. A malformed
input or proof never becomes evidence that a model claim is false. A
completed report may contain refuted and unresolved claims.

### Resource limits

| Item | Bound |
|---|---:|
| Input bundle | 1 MiB |
| Report / shared JSON parser / file read | 4 MiB |
| Nested JSON objects and arrays | 32 |
| Numeric token length | 128 characters |
| Parsed integer magnitude | `10^18` |
| Supplied counters, limits and fact counters | `10^12` |
| Cases | 16 |
| Subjects per case | 16 |
| Modes per case | 64 |
| Predicates per case | 32 |
| Rules per phase | 128 |
| Facts across all predicates in one case | 4096 |
| Displayed route positions | 256 |

These bounds limit input representation and computation. The modeled counter
domain remains all nonnegative integers; the recurrence argument is not cut
off at the largest accepted input value. Resource checks can stop processing
before full semantic admission; an unsupported result does not certify that
all unchecked parts of the input are valid.

JSON duplicate keys, including escaped aliases, are rejected. Numbers are
parsed exactly using decimal arithmetic; integral forms such as `1.0` and
`1e3` retain their mathematical integer values. Fractional numbers, nonfinite
values and Boolean substitutes for integers are rejected. UTF-8 decoding is
strict, and unpaired Unicode surrogates are rejected.

## 4. Evaluation arguments

For a selected subject, admitted rules define a partial function from mode
to the next structural rule. Starting at the initial mode, its structural
walk ends at a terminal or the first repeated mode. Guards can stop that
walk but cannot redirect it. This gives complete continuation coverage in
the supported profile, without an arbitrary exploration-depth cutoff.

The recorded structural walk is a proof proposal, not an observed execution.
Its feasibility is checked separately. For finite conjunctions, a known
false necessary guard or absent edge refutes the course even if an earlier
guard is unknown. Otherwise missing guard facts produce `UNRESOLVED`.

Q1 compares inventory membership by relation meaning, independent of guard
truth and rule spelling. Q2 evaluates the supplied after-route. Its name
does not by itself establish that the route is newly introduced: before and
after rule IDs for every displayed edge are checked separately.

Q3 requires the unique returning word to visit failure and then return to
the initial mode, with all necessary guards jointly supported. A terminal,
a cycle around another mode, or a return that never visits failure refutes
that particular existential claim under the complete deterministic inventory.

Q4 is refuted by the admitted invariant: after any nonempty course of length
`j`, the counter is `n0 + j`, so the complete initial state cannot recur.
Unknown guards do not weaken this conditional invariant.

For Q5, the failure condition is counter-independent by the admitted
language. At each declared mode, the projected successor set is empty or
contains the sole target. No rule, an unconditional rule, and a zero-limit
rule have constant successor sets. A positive finite limit gives unequal
successor sets at counters `0` and `limit`. A predicate with supplied true
and false values at the same subject/mode also gives a counterexample.
Other finite predicate inventories leave compatible constant and varying
completions, so Q5 remains unresolved unless another mode refutes it.

For Q6, let the returning word have length `L`. Position `i` is visited at
exactly `n0 + i + kL` for every repetition `k >= 0`. An unconditional guard
supports all these occurrences. Every finite strict counter limit eventually
fails. A supplied false predicate fact refutes repetition exactly when its
counter lies on that position's progression. Otherwise a predicate remains
unresolved: finitely many true facts cannot fix the infinite progression.

Q6 is derived independently from Q5. A false fact at a counter outside the
reachable progression can refute all-state projection while leaving
trajectory repetition unresolved. A reachable unconditional pattern can
repeat even if an unrelated, unreachable mode has a counter-dependent guard.

## 5. Report and proof encoding

The report format is `PULSEMECH-PARADOX-CYCLIC-EVALUATION-v0`. It binds the
raw input SHA-256, the input baseline, the checking semantics, and an exact
case inventory. Each case contains all six claims and these obligations:

| Certificate field | Checked obligation |
|---|---|
| `direct_rule_ids` | Matching before/after direct rules for the selected subject and target, or exact absence. |
| `displayed_route_before_rule_ids` | Matching before rule or exact absence for every displayed edge. |
| `displayed_route_rule_ids` | Matching after rule or exact absence for every displayed edge; the bound start and position derive exact counters. |
| `mode_walk_rule_ids`, `mode_walk_stop` | Complete structural walk through the first terminal or repeated mode. |
| `counter_increment` | Exact integer `1`, backed by admission of every rule. |
| `projection` | One obligation for every declared mode, with actual true/false representatives where applicable. |
| `repeatability` | One obligation for every position of a returning word through failure, or an empty list when that topology is absent. |

Projection kinds are `absent`, `unconditional`, `zero_limit`, `finite_limit`,
`predicate_conflict` and `predicate_unfixed`. Repetition kinds are
`unconditional`, `finite_limit`, `predicate_false` and `predicate_unfixed`.
Finite-limit repetition witnesses identify a counter on the required
arithmetic progression at or beyond the limit.

The checker accepts alternative valid representatives and later valid
finite-limit witnesses. It does not require byte equality with evaluator
output. It rejects omitted, duplicated, fabricated or misbound obligations,
including Boolean values where integer witnesses are required.

### Symbolic interpretation witnesses for unresolved claims

The bound input, route/word obligations and `predicate_unfixed` kinds encode
the following explicit completion constructions. Each construction describes
one immutable total interpretation, preserves every supplied fact globally,
and assigns all otherwise unspecified keys a fixed default value. These are
logical alternatives, not additional observed facts.

- **Q2/Q3:** The positive interpretation makes every missing predicate key
  required by the finite course true. The negative interpretation makes its
  first missing key false while retaining the other required assignments.
  Strict counter growth prevents incompatible assignments to a repeated
  exact key. Deterministic topology rules out bypassing the blocked step for Q3.
- **Q5:** With no known varying mode, complete each relevant predicate bucket
  constantly using its sole supplied Boolean value, or false if it has no
  facts. This preserves projection. For the contrary interpretation, choose
  an unresolved bucket and flip its constant value at a fresh counter larger
  than all its supplied counters, retaining the constant value at another
  counter. Mode is part of the predicate key, so these completions coexist
  across modes and preserve all other buckets' facts.
- **Q6:** With no known blocker, set all missing keys on every obligated
  progression true. For the contrary interpretation, choose one unresolved
  predicate progression and assign false at a fresh progression counter
  beyond all its supplied facts. The fixed input facts are retained in both
  interpretations, including false facts outside the obligated progressions.

The checker independently verifies the premises of these constructions.
An unknown tag alone cannot establish a verdict if the supplied facts,
topology or another guard contradict the claimed pair of interpretations.

## 6. Independent checker and trust boundary

The [evaluator](../tools/paradox_cyclic_v0/evaluator.py) and
[checker](../tools/paradox_cyclic_v0/checker.py) independently derive the
model claims. The checker neither imports nor calls the evaluator, and its
CLI operates when the evaluator module is absent. They share only the
[contract layer](../tools/paradox_cyclic_v0/contract.py): constants, bounded
parsing, structural/semantic admission, digest and I/O helpers.

Each API call admits its own immutable raw bytes. The checker reconstructs
topology, guard support and all proof obligations from that input before
comparing the submitted verdicts. Altering even input whitespace breaks a
previous report's binding. The returned verification record also identifies
the exact submitted report bytes by SHA-256.

Shared admission, Python, the local host and these source implementations
remain in the trusted computing base. Independent semantic code is an
internal checking separation; it is not independent external validation,
authentication, a general theorem prover, or a claim of hostile-code
containment. No candidate code is loaded or executed.

CLI readers require bounded regular files and check descriptor metadata
before and after reading. On platforms exposing `O_NOFOLLOW`, the final
path component cannot be a symlink. Parent-directory and host integrity
remain assumptions; this is not an atomic hostile-filesystem snapshot.

## 7. Local use

Both tools use the Python standard library. From the repository root:

```sh
python tools/evaluate_paradox_cyclic_v0.py \
  --input examples/paradox_cyclic_case_v0/cases.json \
  > /tmp/paradox-cyclic-report.json
```

```sh
python tools/check_paradox_cyclic_result_v0.py \
  --input examples/paradox_cyclic_case_v0/cases.json \
  --report /tmp/paradox-cyclic-report.json
```

Reports and verification records are JSON on standard output. Expected
input/proof errors produce bounded JSON on standard error with `error`,
`code`, `authority_effect` and `production_gate_eligible`; standard output
is empty. Exit `0` means completed evaluation or verification, `1` means
input/proof rejection, and `2` is command-line usage error. Help exits `0`.
Neither successful exit nor `VERIFIED` authorizes a release.

Public byte APIs are `evaluate_bytes(input_raw)` and
`verify_bytes(input_raw, report_raw)`. The command-line tools do not write
result files themselves, dispatch workflows, or acquire new native evidence.

## 8. Regression coverage and CI registration

The [regression module](../tests/test_paradox_cyclic_evaluator_v0.py) supports
both direct `unittest` execution and pytest. It covers the frozen thirty
claims, opaque identifier renaming, changed meanings under unchanged IDs,
inventory order, strict admission, resource exclusions, independent checker
operation, malformed proofs and noncanonical valid witnesses.

Targeted semantic controls include unknown guards followed by a known false
or missing edge; finite true facts; on/off-progression false facts; nonzero
initial counters; zero and very large finite limits; another-mode cycles;
unreachable counter-dependent modes; and a route that already existed before.
Small-limit cases use independently derived expected outcomes. Tests do not
establish unbounded recurrence by repeatedly sampling a cycle.

```sh
python tests/test_paradox_cyclic_evaluator_v0.py
```

```sh
python -m pytest -q tests/test_paradox_cyclic_evaluator_v0.py \
  tests/test_tools_tests_list_smoke.py::test_paradox_cyclic_evaluator_is_registered_in_both_suites
```

The new test is appended exactly once to both existing manifests:
[tools tests](../ci/tools-tests.list), 181 to 182 entries, and
[targeted pytest](../ci/pytest-tests.list), 39 to 40 entries at the preparation
baseline. The existing list-smoke module gains a focused guard for this dual
registration, including its direct-script entry point.

No existing test registration is removed or reordered. Workflow files, G3
tests, W1 runners, frozen evidence and the normative release-authority chain
are unchanged. Local regression completion is an implementation check; this
document does not claim a GitHub CI result for a future PR or a new W1/native
experiment. All outputs retain `authority_effect: none` and
`production_gate_eligible: false`.
