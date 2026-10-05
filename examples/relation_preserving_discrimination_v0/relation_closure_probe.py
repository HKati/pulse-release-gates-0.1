#!/usr/bin/env python3
"""Finite, exact relation-preservation probe for a Workshop measurement model.

Local research witness only. No quantum model, production adapter, security
sandbox, statistical estimator, or release gate is implemented here.

Python standard library only. Run: python relation_closure_probe.py --output results.json
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import combinations, product
import json
from pathlib import Path
from typing import Callable, Iterable, Sequence

EVALUATOR_ID = 'finite_joint_histogram_consistency_v0'
TARGET_ID = 'empirical_odd_parity_fraction_v0'
AUTHORITY_EFFECT = 'none'


class EvidenceError(ValueError):
    """Malformed or mutually unbound evidence, not an absent physical effect."""


@dataclass(frozen=True)
class Domain:
    n_bits: int = 3
    n_records: int = 4

    def __post_init__(self) -> None:
        if type(self.n_bits) is not int or not 1 <= self.n_bits <= 4:
            raise ValueError('Exhaustive histogram domain supports 1..4 bits.')
        if type(self.n_records) is not int or not 1 <= self.n_records <= 4:
            raise ValueError('Exhaustive histogram domain supports 1..4 records.')

    @property
    def width(self) -> int:
        return 1 << self.n_bits


@dataclass(frozen=True)
class Histogram:
    domain: Domain
    counts: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.counts) != self.domain.width:
            raise ValueError('Histogram has the wrong number of outcomes.')
        if any(type(c) is not int or c < 0 for c in self.counts):
            raise ValueError('Histogram counts must be nonnegative exact integers.')
        if sum(self.counts) != self.domain.n_records:
            raise ValueError('Histogram counts must sum to the declared record count.')


def validate_scope(scope: tuple[int, ...], n_bits: int) -> None:
    if not scope or any(type(i) is not int or not 0 <= i < n_bits for i in scope):
        raise EvidenceError('Invalid component scope.')
    if scope != tuple(sorted(set(scope))):
        raise EvidenceError('A scope must have unique components in ascending order.')


def all_scopes(n_bits: int, max_order: int | None = None) -> tuple[tuple[int, ...], ...]:
    upper = n_bits if max_order is None else min(max_order, n_bits)
    return tuple(s for k in range(1, upper + 1) for s in combinations(range(n_bits), k))


def bit_rows(n_bits: int) -> tuple[tuple[int, ...], ...]:
    return tuple(product((0, 1), repeat=n_bits))


def histogram_from_rows(rows: Iterable[Sequence[int]], n_bits: int = 3) -> Histogram:
    normalized = tuple(tuple(row) for row in rows)
    domain = Domain(n_bits, len(normalized))
    counts = [0] * domain.width
    for row in normalized:
        if len(row) != n_bits or any(type(bit) is not int or bit not in (0, 1) for bit in row):
            raise ValueError('Rows must contain exactly the declared number of binary integers.')
        index = 0
        for bit in row:
            index = (index << 1) | bit
        counts[index] += 1
    return Histogram(domain, tuple(counts))


def weak_compositions(total: int, slots: int) -> Iterable[tuple[int, ...]]:
    if slots == 1:
        yield (total,)
    else:
        for first in range(total + 1):
            for rest in weak_compositions(total - first, slots - 1):
                yield (first,) + rest


@lru_cache(maxsize=None)
def enumerate_histograms(domain: Domain) -> tuple[Histogram, ...]:
    return tuple(Histogram(domain, counts) for counts in weak_compositions(domain.n_records, domain.width))


@lru_cache(maxsize=None)
def marginal(histogram: Histogram, scope: tuple[int, ...]) -> tuple[int, ...]:
    validate_scope(scope, histogram.domain.n_bits)
    counts = [0] * (1 << len(scope))
    for row, weight in zip(bit_rows(histogram.domain.n_bits), histogram.counts):
        index = 0
        for i in scope:
            index = (index << 1) | row[i]
        counts[index] += weight
    return tuple(counts)


def odd_fraction(histogram: Histogram) -> Fraction:
    odd = sum(c for row, c in zip(bit_rows(histogram.domain.n_bits), histogram.counts) if sum(row) % 2)
    return Fraction(odd, histogram.domain.n_records)


def first_bit_fraction(histogram: Histogram) -> Fraction:
    return Fraction(marginal(histogram, (0,))[1], histogram.domain.n_records)


@dataclass(frozen=True)
class Observation:
    domain: Domain
    scope: tuple[int, ...]
    counts: tuple[int, ...]
    context_id: str

    def __post_init__(self) -> None:
        validate_scope(self.scope, self.domain.n_bits)
        if len(self.counts) != 1 << len(self.scope):
            raise EvidenceError('Observation has the wrong number of bins.')
        if any(type(c) is not int or c < 0 for c in self.counts):
            raise EvidenceError('Observation counts must be nonnegative exact integers.')
        if sum(self.counts) != self.domain.n_records:
            raise EvidenceError('Observation size disagrees with the domain.')
        if not isinstance(self.context_id, str) or not self.context_id:
            raise EvidenceError('A nonempty shared context binding is required.')


@dataclass(frozen=True)
class Assessment:
    status: str
    compatible_histogram_count: int
    possible_target_values: tuple[Fraction, ...]

    def as_json(self) -> dict:
        return {'status': self.status,
                'compatible_histogram_count': self.compatible_histogram_count,
                'possible_target_values': [str(v) for v in self.possible_target_values]}


def infer(domain: Domain, observations: Sequence[Observation], *,
          target: Callable[[Histogram], Fraction] = odd_fraction,
          count_tolerance: int = 0) -> Assessment:
    """Compute the exact compatible set on the declared finite domain.

    A positive count_tolerance is a declared per-bin bound, NOT an estimated
    statistical confidence level or a measurement calibration.
    """
    if type(count_tolerance) is not int or count_tolerance < 0:
        raise ValueError('Count tolerance must be a nonnegative exact integer.')
    if any(o.domain != domain for o in observations):
        raise EvidenceError('Evidence belongs to different witness domains.')
    if len({o.context_id for o in observations}) > 1:
        raise EvidenceError('Cannot pool measurements from unbound contexts.')
    compatible = []
    for candidate in enumerate_histograms(domain):
        if all(all(abs(a - b) <= count_tolerance for a, b in zip(marginal(candidate, o.scope), o.counts))
               for o in observations):
            compatible.append(candidate)
    values = tuple(sorted({target(candidate) for candidate in compatible}))
    status = ('incompatible' if not compatible else 'identified' if len(values) == 1 else 'unresolved')
    return Assessment(status, len(compatible), values)


@dataclass(frozen=True)
class Binding:
    binding_id: str
    scope: tuple[int, ...]


@dataclass(frozen=True)
class Machine:
    bindings: tuple[Binding, ...]
    evaluator_id: str = EVALUATOR_ID
    target_id: str = TARGET_ID

    def __post_init__(self) -> None:
        if self.evaluator_id != EVALUATOR_ID or self.target_id != TARGET_ID:
            raise ValueError('This comparison has a fixed evaluator and target.')
        ids = tuple(b.binding_id for b in self.bindings)
        if len(ids) != len(set(ids)) or any(not b for b in ids):
            raise ValueError('Binding identities must be distinct and nonempty.')
        for b in self.bindings:
            validate_scope(b.scope, 3)

    def ablate(self, disabled_ids: frozenset[str]) -> Machine:
        ids = {b.binding_id for b in self.bindings}
        if not disabled_ids <= ids:
            raise ValueError('Cannot ablate a binding that is not in the machine.')
        return Machine(tuple(b for b in self.bindings if b.binding_id not in disabled_ids))


class EvidenceSource:
    """Scoped accessor with a read trace; logical test boundary, not a security sandbox.

    All machines retain the same ambient source type and state. Only active
    binding participation changes. No carrier-removal claim is made.
    """
    def __init__(self, histogram: Histogram, permitted_bindings: Sequence[Binding],
                 context_id: str = 'synthetic_same_trial_cohort_v0') -> None:
        self.__histogram = histogram
        self.domain = histogram.domain
        self.context_id = context_id
        self.__permitted = {b.binding_id: b.scope for b in permitted_bindings}
        self.read_trace: list[tuple[str, tuple[int, ...]]] = []

    def read(self, binding: Binding) -> Observation:
        if self.__permitted.get(binding.binding_id) != binding.scope:
            raise PermissionError('This measurement relation is not enabled.')
        self.read_trace.append((binding.binding_id, binding.scope))
        return Observation(self.domain, binding.scope, marginal(self.__histogram, binding.scope), self.context_id)


@dataclass(frozen=True)
class Response:
    definedness: str
    semantic_state: str
    output: Assessment
    consequence: str

    def as_json(self) -> dict:
        return {'definedness': self.definedness, 'semantic_state': self.semantic_state,
                'output': self.output.as_json(), 'consequence': self.consequence}


def evaluate(machine: Machine, source: EvidenceSource) -> Response:
    """Same evaluator for before, after, ablated, and alternative-path machines."""
    if source.domain != Domain():
        raise ValueError('The operational witness profile fixes three bits and four records.')
    evidence = tuple(source.read(binding) for binding in machine.bindings)
    assessment = infer(source.domain, evidence)
    return Response('defined', 'assessed:' + assessment.status, assessment, 'diagnostic_only_no_external_effect')


def run_machine(machine: Machine, histogram: Histogram) -> tuple[Response, EvidenceSource]:
    source = EvidenceSource(histogram, machine.bindings)
    return evaluate(machine, source), source


EVEN_ROWS = ((0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0))
ODD_ROWS = ((0, 0, 1), (0, 1, 0), (1, 0, 0), (1, 1, 1))
EVEN = histogram_from_rows(EVEN_ROWS)
ODD = histogram_from_rows(ODD_ROWS)
PROPER_BINDINGS = tuple(Binding('marginal_' + ''.join(map(str, s)), s) for s in all_scopes(3, 2))
JOINT = Binding('joint_primary', (0, 1, 2))
JOINT_BACKUP = Binding('joint_backup', (0, 1, 2))
BEFORE = Machine(PROPER_BINDINGS)
AFTER = Machine(PROPER_BINDINGS + (JOINT,))
ABLATED = AFTER.ablate(frozenset({JOINT.binding_id}))
WITH_BACKUP = Machine(PROPER_BINDINGS + (JOINT, JOINT_BACKUP))


def parity_family_check(max_n: int = 8) -> dict:
    """Check all nonempty proper marginals in finite parity ensembles, n=2..max_n."""
    checked = 0
    cases = []
    for n in range(2, max_n + 1):
        even_rows = tuple(row for row in bit_rows(n) if sum(row) % 2 == 0)
        odd_rows = tuple(row for row in bit_rows(n) if sum(row) % 2 == 1)
        for scope in all_scopes(n, n - 1):
            assignments = tuple(product((0, 1), repeat=len(scope)))
            left = tuple(sum(tuple(row[i] for i in scope) == a for row in even_rows) for a in assignments)
            right = tuple(sum(tuple(row[i] for i in scope) == a for row in odd_rows) for a in assignments)
            if left != right or len(set(left)) != 1:
                raise AssertionError((n, scope, left, right))
            checked += 1
        cases.append({'n': n, 'rows_per_ensemble': len(even_rows), 'proper_scopes': (1 << n) - 2})
    return {'max_n': max_n, 'proper_projection_checks': checked, 'cases': cases}


def make_report() -> dict:
    machine_cases = {}
    for label, machine in [('before', BEFORE), ('after', AFTER), ('ablated', ABLATED),
                           ('primary_ablated_backup_present', WITH_BACKUP.ablate(frozenset({JOINT.binding_id}))),
                           ('both_joint_paths_ablated', WITH_BACKUP.ablate(frozenset({JOINT.binding_id, JOINT_BACKUP.binding_id})))]:
        machine_cases[label] = {}
        for fixture_name, histogram in [('even', EVEN), ('odd', ODD)]:
            response, source = run_machine(machine, histogram)
            machine_cases[label][fixture_name] = {'response': response.as_json(),
                'read_trace': [{'binding_id': b, 'scope': list(s)} for b, s in source.read_trace]}
    pairs = [Observation(Domain(), s, marginal(EVEN, s), 'same') for s in all_scopes(3, 2)]
    incompatible = [Observation(Domain(), (0, 1), (2, 0, 0, 2), 'same'),
                    Observation(Domain(), (1, 2), (2, 0, 0, 2), 'same'),
                    Observation(Domain(), (0, 2), (0, 2, 2, 0), 'same')]
    return {'artifact_role': 'finite_synthetic_research_probe', 'authority_effect': AUTHORITY_EFFECT,
            'evaluator_id': EVALUATOR_ID, 'target_id': TARGET_ID,
            'domain': {'n_bits': 3, 'n_records': 4, 'candidate_histograms': len(enumerate_histograms(Domain()))},
            'population_inference': False, 'quantum_experiment': False,
            'fixtures': {'even': EVEN_ROWS, 'odd': ODD_ROWS},
            'target_truth': {'even': str(odd_fraction(EVEN)), 'odd': str(odd_fraction(ODD))},
            'machine_cases': machine_cases,
            'controls': {'no_evidence': infer(Domain(), []).as_json(),
                         'incompatible_joint_model': infer(Domain(), incompatible).as_json(),
                         'per_bin_tolerance_one': infer(Domain(), pairs, count_tolerance=1).as_json(),
                         'narrow_first_bit_target': infer(Domain(), [pairs[0]], target=first_bit_fraction).as_json()},
            'parity_family': parity_family_check()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results.json'))
    args = parser.parse_args()
    report = make_report()
    args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'candidate_histograms': report['domain']['candidate_histograms'],
                      'proper_projection_checks': report['parity_family']['proper_projection_checks'],
                      'output': str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
