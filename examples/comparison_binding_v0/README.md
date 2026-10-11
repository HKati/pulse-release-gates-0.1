# Comparison binding v0 — synthetic companion

This offline example accompanies
[the field comparison contract](../../docs/PULSEMECH_FIELD_COMPARISON_BINDING_v0.md).
It evaluates a finite geometric target and compares rational scalar samples
under identity transport. Every result has `authority_effect: none`.

The schema is
[pulsemech_comparison_binding_v0.schema.json](../../schemas/pulsemech_comparison_binding_v0.schema.json).
It is a reference-based carrier draft; shape and digest checks do not establish
measurement validity or trusted producer identity.

## Reproduce

Python 3.10 or later; standard library only. From the repository root:

```sh
python examples/comparison_binding_v0/run_review.py --output-dir /tmp/pulsemech-comparison-binding-v0
python tests/test_comparison_binding_v0.py
```

The first command runs 32 companion test methods and writes `results.json` and
`TEST_RESULTS.txt` to the selected directory. The second runs two integration
tests, including a fresh companion execution and reference-result comparison.
The comparison permits different interpreter-version metadata; every semantic
result and source digest must match. Reference execution was performed on
Python 3.12.14; the repository CI uses its existing runtime configuration.

The integration module is registered once in `ci/pytest-tests.list`. No new
workflow, required gate, policy or release-authority path is introduced.

For companion tests without writing reports:

```sh
python -m unittest discover -s examples/comparison_binding_v0 -p 'test_*.py' -v
```

## Included files

| File | Purpose |
|---|---|
| `comparison_probe.py` | Bound synthetic adapter, fixed geometry evaluator, scalar comparison and target-scoped six-axis diagnostic views. |
| `schema_subset.py` | Offline checker for the schema subset used by this draft; no general Draft 2020-12 conformance claim. |
| `make_fixtures.py` | Deterministic generator of the three supplied fixtures. |
| `fixtures/*.json` | Expansion, fixed-support contraction and reduced-support examples. |
| `test_comparison_probe.py` | T01–T12: twelve original geometric/binding tests. |
| `test_missing_domain.py` | Z01–Z09: nine missing-data and support-boundary tests. |
| `test_independent_review.py` | R01–R05: independent counterexamples and strict internal packet checks. |
| `test_status_binding.py` | S01–S06: keep target identification separate from binding completeness, observation, cause and authority. |
| `run_review.py` | Executes the fixed inventory and writes reference-shaped reports. |
| `results.json`, `TEST_RESULTS.txt` | Actual offline reference execution and test log. |

Artifacts use sorted compact UTF-8 JSON for their SHA-256 payload digests, with
non-finite numbers forbidden. This is a declared local encoding, not RFC 8785
JCS. A digest binds those encoded payload bytes, not the measurement or producer.

## Missingness and proof scope

Missing observations retain `unobserved` and `value: null`. Unknown support or
coverage produces `UNBOUND` for scalar comparison; unknown source support also
keeps geometric replay `UNBOUND`. An omitted or null binding is rejected. A measured
zero remains numeric: target 0 minus source 1 is `"-1"`. Verified removed support
is reported separately and receives no numerical field extension.

Two known empty system supports produce an `INCOMPATIBLE` scalar comparison
under the declared nonempty rule, with unresolved identity and no numeric deltas.

`global_scalar_field_identity` concerns only the finite scalar field on its
declared support. It does not assert metric, full-configuration or transition
identity. Diagnostic status views serialize all six canonical status groups,
but identify only their named comparison claim. They perform same-model bounded
replay and leave causal evaluation unperformed. Canonical `authority_status`
remains `none`; `record_status: synthetic_diagnostic` carries the diagnostic role.

The candidate set contains four scale/support combinations. Its closure is not
exhaustive physical-path closure. The primary and backup paths reach the same
receipt; they are not independent physical measurements. General tensor
transport, nontrivial charts, physical calibration and path reconstruction remain
outside this example.

```text
Mezőminta ≠ mezőazonosság. Azonos vetület ≠ azonos átmenet.
A hiányzó minta, az ismeretlen lefedettség, az eltávolított támaszrész és a
ténylegesen mért nulla külön eset. A geometriai cél azonosítása nem pótolja
a hiányzó skalármintát, és nem emeli igazolttá az utat vagy az okságot.
```
