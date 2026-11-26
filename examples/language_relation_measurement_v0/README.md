# Language Relation Measurement v0 — contract fixtures

## 1. Status and purpose

These fixtures belong to **LRM-01**, the profile and contract work package.
They record synthetic language examples, proposed reference representations,
expected future behavior, and examples of the four artifact schemas.

No automatic language extraction, source-to-representation verification,
relation comparison, impact measurement, or replay runtime is delivered here.
Passing the current tests establishes the tested structural and contract
properties. It does not establish language-understanding accuracy, a completed
measurement, or release authority.

The controlling documents are:

- [Development plan](../../docs/PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_PLAN.md).
- [Technical contract](../../docs/PULSEMECH_LANGUAGE_RELATION_MEASUREMENT_v0_CONTRACT.md).
- [Finite language profile](../../contracts/language_relation_profile_v0.json).
- [Historical source baseline](../../contracts/language_relation_measurement_v0_baseline.json).

## 2. File roles

| File | Intended consumer and role | Claim boundary |
| --- | --- | --- |
| `cases.json` | Frozen synthetic utterances, reference representations, and selected measurement targets for contract tests and later runtime evaluation. | Reference input authored for this suite; no result label is supplied to a future comparator through this file. |
| `expected.json` | Test-controller oracle, kept physically separate from evaluator input. | Intended behavior under the recorded fixture premises; not an observed runtime result. |
| `contract_examples.json` | Candidate and synthetic examples of input, verification, measurement, and manifest records. | Illustrates schema shapes and prohibited combinations; example status values are not execution evidence. |

The initial corpus contains **23 input cases**, **23 conditional oracle entries**,
and **11 synthetic contract examples** spanning the four artifact roles. Each
case is a full `language_relation_input_v0` instance with
`provenance: "synthetic_reference"`. Both submitted representation bases remain
`candidate_only`. The corpus wrapper records
`reference_status: "draft_synthetic_references"`.

The oracle's semantic classifications are conditional on independent acceptance
of the exact supplied reference interpretation, correspondence, and stated
coverage. They are proposed requirements for later evaluation, not measured
results or an owner-acceptance record. A submitted `fulfilled` coverage state is
an authored annotation; it does not establish verified coverage.

The synthetic provenance of each example remains explicit. A hypothetical
completed check shown in a schema example must not be imported as an actual
verification receipt. An accepted-reference example illustrates the acceptance
contract; it does not allow a submitted package to create its own trust root.

Case identifiers are addressing labels. They must not choose a stored answer in
a future evaluator. The test controller may match a computed result with its
oracle by identifier only after evaluation. The automatic extractor must not
receive the reference representation or expected label as hidden input.

### Initial case inventory

| Case ID | Controlled question or reference role |
| --- | --- |
| `LRM_REF_01` | Identity preservation control in English. |
| `LRM_REF_02` | Hungarian paraphrase with a recorded common request context. |
| `LRM_REF_03` | Sender/recipient role reversal. |
| `LRM_REF_04` | Positive assertion versus negation. |
| `LRM_REF_05` | AND versus inclusive OR, with a selected-condition witness. |
| `LRM_REF_06` | Only-if versus if direction. |
| `LRM_REF_07` | Not-all versus none over a declared two-person domain. |
| `LRM_REF_08` | De Morgan equivalence for a selected Boolean condition. |
| `LRM_REF_09` | Explicit permission versus an explicit observation-record claim; no independent event evidence. |
| `LRM_REF_10` | Quoted content versus direct assertion. |
| `LRM_REF_11` | Giver/item/recipient roles in a ternary relation. |
| `LRM_REF_12` | One conjunction mapped to a group of two statements. |
| `LRM_REF_13` | Incomplete extraction from unchanged source text. |
| `LRM_REF_14` | Omitted selected relation under the stated complete comparison scope. |
| `LRM_REF_15` | Preserved approval relation plus an unsupported winning claim. |
| `LRM_REF_16` | Explicit statement of a consequence requiring its own checked derivation. |
| `LRM_REF_17` | Different ternary relations with equal pairwise projections. |
| `LRM_REF_18` | Loss of a reported-winner alternative plus a stable approval target. |
| `LRM_REF_19`–`LRM_REF_21` | Unknown, empty, and truncated interpretation-family controls. |
| `LRM_REF_22` | Unchanged implication structure with an unsupported support cycle. |
| `LRM_REF_23` | Withdrawal of one base while an alternative route can retain derived support. |

The general reference model admits more than the controlled source grammar.
Only the exact productions in the profile are controlled-language candidates;
the other cases are explicit reference-annotation controls. None currently
carries a completed grammar-checker receipt.

## 3. Reference interpretation and verification

The v0 distinguishes three representation bases:

- `candidate_only`: diagnosis concerns submitted candidate structures only.
- `accepted_reference`: results are conditional on the named, independently
  accepted reference interpretation and its exact content binding.
- `profile_verified`: a separate checker has verified the source/representation
  mapping within the admitted controlled-language profile.

The fixture author's interpretation is not independent proof of automatic
extraction correctness. Content hashes bind bytes and versions; they do not
establish semantic truth. The accepted profile/reference inventory must be fixed
independently of the package being evaluated.

Every future target result and exported view retains both
`representation_basis` and `claim_scope`. A candidate-structure diagnosis cannot
be promoted to a source-semantic finding by dropping those fields.

Faithful representation of an utterance is separate from the real-world truth
of what it asserts. A preserved false statement may still be faithfully
preserved. Permission and quoted claims remain distinct from observed events.

## 4. Controls to preserve when extending the suite

Preserve positive controls as well as counterexamples. A comparator that returns
`UNDETERMINED` for every case does not satisfy the plan. Later runtime checks must
cover the obligations in the plan's A01–A24 matrix, including:

- Paraphrase, supported renaming, and sentence splitting that preserve a selected
  relation under checked correspondence.
- Role reversal despite matching vocabulary; event identity separate from role
  pattern equality.
- AND/OR, only-if/if, negation scope, and finite quantifier differences.
- Quotation, permission, obligation, assertion, and observation distinctions.
- Missing extraction versus a sufficiently covered broken relation.
- New content, separately supported additions, and explicit restatement of a
  consequence already derivable from the original premises.
- Higher-arity relations that differ despite matching pairwise projections.
- Coupled referent/context alternatives, alternative loss, and useful local
  findings under broader ambiguity.
- Unknown, actually empty, and truncated compatible families.
- Grounded support, unsupported cycles, alternative routes, and withdrawal.
- Common-configuration impact witnesses and separately bound observed events.
- Actual recomputation, oracle exclusion, representation-error detection, and
  preservation of the release-authority boundary.

A resource-limited search cannot establish complete preservation or absence of
impact. An already checked counterexample may still refute universal
preservation. Its validity and scope must remain separate from the uncompleted
search.

## 5. Running the contract checks

From the repository root, with the repository's test dependencies installed:

```bash
python -m pytest -q tests/test_language_relation_contract_v0.py
```

The direct entrypoint runs the same contract checks:

```bash
python tests/test_language_relation_contract_v0.py
```

The test is registered exactly once in each of `ci/pytest-tests.list` and
`ci/tools-tests.list`. The delivered validation report records which commands
actually ran. This README contains no assertion that a test run occurred.

The current tests validate schemas, fixture structure, declared contract
invariants, source/profile bindings that can be checked from the preserved
package, and manifest registration. They do not substitute a small test-local
parser or comparator for the separately planned LRM-02–04 implementations.

Schema validity is one layer. Duplicate-key rejection, identifier uniqueness,
reference resolution, exact source/locator binding, accepted-reference
resolution, and semantic correctness have their own obligations. A JSON Schema
pass alone does not establish them.

## 6. Extending or using these examples

Freeze a case set before reporting an adapter evaluation. Retain failures and
unsupported cases in the result inventory. Add new cases as an explicit versioned
extension rather than silently replacing difficult examples. Keep expected
results separated from candidate input and record any change to the reference
interpretation or profile.

For an observed processing-change claim, bind the original and processed sources
to the same identified processing operation. Two unrelated utterances may be
compared structurally, but their difference is not by itself evidence of an
observed processing event.

The future artifact bundle contains preserved source/context/profile bytes,
`input.json`, `verification.json`, `measurement.json`, and `manifest.json`.
Replay recomputes the deterministic core and issues a separate
`replay_receipt.json`; equality of two saved reports is not replay.

All examples and future LRM v0 artifacts remain diagnostic:

```text
authority_status = none
authority_effect = none
release_authority_activation = false
```

They do not write `status.json`, materialize a required gate set, or supply a
hidden normative release input. The owner separately authorizes repository
application and any live experiment; the owner opens the PR and merges.
