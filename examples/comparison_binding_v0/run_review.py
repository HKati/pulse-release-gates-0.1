"""Run the synthetic checks and emit a non-authoritative reference report."""
import argparse
import hashlib
from copy import deepcopy
from collections import Counter
import io
import json
from pathlib import Path
import platform
import sys
import unittest

from comparison_probe import (FIXTURE_NAMES, MODEL, SCHEMA_PATH, compare_field,
    field_status_view, geometry_evidence, geometry_status_view, load_fixture, replay, resolve)
from make_fixtures import rewrite_artifact
from test_comparison_probe import BaseTwelveChecks
from test_missing_domain import (MissingDomainChecks, with_endpoint_support,
                                with_missing_target_sample)
from test_independent_review import IndependentReviewChecks, with_sensor_loss
from test_status_binding import StatusBindingChecks


def main(argv=None):
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=root,
                        help='Report directory; fixtures and schema are never rewritten.')
    args = parser.parse_args(argv)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    suites = [('base_twelve', BaseTwelveChecks, 12), ('missing_domain', MissingDomainChecks, 9),
              ('independent_review', IndependentReviewChecks, 5), ('status_binding', StatusBindingChecks, 6)]
    stream = io.StringIO()
    totals = {}
    passed = True
    for label, case, required_count in suites:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(case)
        if suite.countTestCases() != required_count:
            raise RuntimeError(f'{label}: test inventory changed')
        stream.write(f'[{label}]\n')
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        totals[label] = {'run': result.testsRun, 'failures': len(result.failures),
                         'errors': len(result.errors), 'skipped': len(result.skipped)}
        passed = passed and result.wasSuccessful() and not result.skipped
    fixtures = [load_fixture(name) for name in FIXTURE_NAMES]
    fixture_reports = []
    for name, fixture in zip(FIXTURE_NAMES, fixtures):
        field = compare_field(fixture)
        fixture_reports.append({'file': 'fixtures/' + name,
            'curvature_only_response': replay(fixture),
            'primary_support_response': replay(fixture, ('primary_support',)),
            'backup_support_response': replay(fixture, ('backup_support',)),
            'both_support_routes_response': replay(fixture, ('primary_support', 'backup_support')),
            'all_support_routes_ablated_response': replay(fixture),
            'field_status': field['status'], 'global_scalar_field_identity': field['global_scalar_field_identity'],
            'delta_status_counts': dict(Counter(item['status'] for item in field['deltas'].values())),
            'geometry_status_views': {
                'curvature_only': geometry_status_view(geometry_evidence(fixture)),
                'support_bound': geometry_status_view(geometry_evidence(fixture, ('primary_support',)))},
            'scalar_field_status_view': field_status_view(fixture)})
    missing = compare_field(with_missing_target_sample(fixtures[0]))
    unknown_source = deepcopy(fixtures[0])
    unknown_source['comparison_binding']['source']['system_support'] = {
        'status': 'unknown', 'reason': 'source membership receipt unavailable'}
    empty_supports = with_endpoint_support(fixtures[0], 'source', ())
    empty_supports = with_endpoint_support(empty_supports, 'target', ())
    zero_fixture = deepcopy(fixtures[0])
    zero_state = deepcopy(zero_fixture['artifacts']['target_state']['payload'])
    zero_state['field_observations']['cell:063'] = '0'
    rewrite_artifact(zero_fixture, 'target_state', zero_state)
    zero = compare_field(zero_fixture)
    removed = compare_field(fixtures[2])
    sensor_loss_fixture = with_sensor_loss(fixtures[0])
    sensor_loss = compare_field(sensor_loss_fixture)
    target_states = [resolve(f, f['comparison_binding']['target']['state_ref'])
                     for f in (sensor_loss_fixture, fixtures[2])]
    report = {'package_status': 'OFFLINE_SYNTHETIC_REFERENCE',
        'test_result': 'PASS' if passed else 'FAIL', 'python_version': platform.python_version(),
        'authority_effect': 'none', 'release_authority_activation': False,
        'implementation_scope': 'offline_synthetic_comparison_with_diagnostic_status_views',
        'schema_sha256': hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest(),
        'evaluator_sha256': hashlib.sha256((root / 'comparison_probe.py').read_bytes()).hexdigest(),
        'fixture_sha256': {name: hashlib.sha256((root / 'fixtures' / name).read_bytes()).hexdigest()
                           for name in FIXTURE_NAMES},
        'physical_validation': 'not_performed', 'geometric_candidate_count': len(MODEL),
        'materialized_fixture_count': len(fixtures),
        'schema_validation': 'strict_supported_subset_plus_bounded_semantic_adapter',
        'general_json_schema_conformance': 'not_claimed',
        'tests': totals, 'fixture_results': fixture_reports,
        'missingness_examples': {
            'missing_target_sample': missing['deltas']['cell:063'],
            'missing_target_sample_global_scalar_field_identity': missing['global_scalar_field_identity'],
            'measured_target_zero': zero['deltas']['cell:063'],
            'removed_target_support': removed['deltas']['cell:063'],
            'unknown_source_support_geometry_status_view': geometry_status_view(
                geometry_evidence(unknown_source, ('primary_support',))),
            'known_empty_supports_scalar_status_view': field_status_view(empty_supports)},
        'sensor_loss_example': {
            'same_observed_projection_as_fixture_c': all(target_states[0][key] == target_states[1][key]
                for key in ('curvature_observation', 'field_observations')),
            'bound_volume_change_response': replay(sensor_loss_fixture, ('primary_support',)),
            'fixture_c_bound_volume_change_response': replay(fixtures[2], ('primary_support',)),
            'missing_target_sample': sensor_loss['deltas']['cell:063'],
            'global_scalar_field_identity': sensor_loss['global_scalar_field_identity']},
        'limits': ['finite synthetic model only', 'identity transport only',
                  'no physical transition-path or causal-necessity proof',
                  'support backup is an independent enabled read path to the same receipt',
                  'no adversarial process-isolation proof or release-authority activation']}
    (output / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                     encoding='utf-8', newline='\n')
    (output / 'TEST_RESULTS.txt').write_text(stream.getvalue(), encoding='utf-8', newline='\n')
    print(f"12 base + 9 missing-domain + 5 review + 6 status-binding checks: {'PASS' if passed else 'FAIL'}")
    print('3 fixtures; diagnostic only; authority_effect=none')
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
