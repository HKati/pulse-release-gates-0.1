"""Observe real signed TEST decisions without asserting production QRH results.

The shared authority fixture is composed, not inherited or imported as a test
class, so its 57 cases are not rediscovered here. Only the TEST evaluator is
controlled in successful paths; signatures, policy/checker subprocesses and
decision replay are real. Fault cases identify any replaced TEST tool or
injected subprocess timeout explicitly.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).absolute().parents[1]
try:
    from . import test_authority as authority_fixtures
except ImportError:
    import test_authority as authority_fixtures
from tools import audit, authority, common, transition_report

PULSE_ROOT = authority_fixtures.PULSE_ROOT
VERIFIED = 'VERIFIED_FOR_DECLARED_OFFLINE_DECISION'
INCOMPLETE = 'INCOMPLETE_OFFLINE_PRIMITIVE_EXECUTION'


class TransitionReportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = authority_fixtures.AuthorityBoundaryTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.fixture.anchor['verifier_files']['tools/transition_report.py'] = (
            common.sha256_bytes(common.secure_read(ROOT, 'tools/transition_report.py')))
        for name in ('source_identity', 'scope_binding', 'authority_boundary_tests'):
            self.fixture.files['observations/' + name + '.json'] = common.canonical_bytes({
                'record_role': 'TEST_OBSERVER_FIXTURE_ONLY',
                'does_not_assert_QRH': True, 'tests': [],
            })
        self.fixture.rebind()

    def evaluator(self, failed_gate=None):
        def only_test(snapshot, anchor, profile_kind):
            self.assertEqual(anchor['trust_domain'], 'TEST')
            self.assertEqual(snapshot['manifest']['trust_domain'], 'TEST')
            evaluation = self.fixture.evaluation()
            if failed_gate is not None:
                evaluation['gates'][failed_gate] = False
                evaluation['evaluations'][failed_gate]['state'] = 'NOT_RUN'
            return evaluation
        return mock.patch.object(audit, 'evaluate', side_effect=only_test)

    def capture(self, *, label='observed', pulse_root=PULSE_ROOT, failed_gate=None):
        fixture = self.fixture
        decision_dir = fixture.home / (label + '-decision')
        replay_dir = fixture.home / (label + '-replay')
        with self.evaluator(failed_gate):
            decision = authority.decide(fixture.bundle, fixture.anchor_path,
                                        decision_dir, pulse_root=pulse_root)
            receipt = authority.replay(fixture.bundle, fixture.anchor_path,
                                      decision_dir, replay_dir, pulse_root=pulse_root)
            before = {name: common.secure_read(decision_dir, name) for name in
                      ('decision.json', 'status.json', 'materialized_required.json')}
            observation = transition_report.report(fixture.bundle, fixture.anchor_path,
                                                    decision_dir, replay_dir,
                                                    pulse_root=pulse_root)
        self.assertEqual(receipt['replay_status'], 'MATCH')
        self.assertEqual(observation['trust_domain'], 'TEST')
        self.assertEqual(observation['authority_effect'], 'NONE')
        self.assertFalse((decision_dir / 'production_certificates').exists())
        self.assertFalse(list(replay_dir.rglob('certificate.json')))
        for name, raw in before.items():
            self.assertEqual(common.secure_read(decision_dir, name), raw)
        return decision, receipt, observation, decision_dir, replay_dir

    def assert_incomplete_replay(self, captured):
        decision, receipt, report, _, _ = captured
        self.assertEqual(decision['result'], 'BLOCK')
        self.assertEqual(receipt['fresh_result'], 'BLOCK')
        self.assertEqual(receipt['replay_status'], 'MATCH')
        self.assertEqual(report['axes']['transition_path_verification_status']['state'], INCOMPLETE)
        self.assertEqual(report['axes']['reconstruction_reproducibility_status']['state'],
                         'VERIFIED_DECISION_REPLAY_ONLY')
        self.assertEqual(report['axes']['endpoint_binding_status']['state'],
                         'VERIFIED_FOR_ARTIFACT_AND_DECISION_ENDPOINTS')

    def runtime_with_TEST_tool(self, kind, replacement):
        """Pin one explicit TEST replacement; retain the other upstream tool."""
        fixture = self.fixture
        runtime = fixture.home / ('runtime-with-TEST-' + kind)
        for current, relative, stem in (
                ('parser', fixture.parser_path, 'existing_pulse_policy_parser'),
                ('checker', fixture.checker_path, 'existing_pulse_checker')):
            raw = replacement if current == kind else common.secure_read(PULSE_ROOT, relative)
            destination = runtime / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            fixture.profile['trusted_anchor'][stem + '_sha256'] = common.sha256_bytes(raw)
        fixture.files['profile.json'] = common.canonical_bytes(fixture.profile)
        fixture.rebind()
        return runtime

    def timeout_at_process_boundary(self, kind):
        actual_run = authority.subprocess.run
        def run(command, **kwargs):
            if Path(command[2]).name == kind + '.py':
                raise subprocess.TimeoutExpired(command, kwargs['timeout'],
                                                output=b'', stderr=b'TEST timeout injection')
            return actual_run(command, **kwargs)
        return mock.patch.object(authority.subprocess, 'run', side_effect=run)

    def test_real_TEST_allow_verifies_execution_and_uses_actual_result(self):
        decision, _, report, decision_dir, _ = self.capture()
        self.assertEqual(decision['result'], 'ALLOW')
        self.assertIs(type(decision['checker']['exit_code']), int)
        self.assertEqual(decision['checker']['exit_code'], 0)
        self.assertEqual(report['axes']['transition_path_verification_status']['state'], VERIFIED)
        relation = report['axes']['relation_change_observation_status']['scope']
        self.assertIn('TEST', relation)
        self.assertTrue(relation.endswith(' -> ALLOW decision'))
        certificate = common.read_json(decision_dir / 'test_only/certificate.json')
        self.assertEqual(certificate['trust_domain'], 'TEST')
        self.assertFalse(certificate['mathematical_or_community_acceptance_asserted'])

    def test_real_required_gate_BLOCK_still_verifies_completed_execution(self):
        failed = common.GATE_IDS[2]
        decision, _, report, decision_dir, _ = self.capture(failed_gate=failed)
        self.assertEqual(decision['result'], 'BLOCK')
        self.assertEqual(decision['failed_required_gates'], [failed])
        self.assertEqual(decision['checker']['exit_code'], 1)
        self.assertEqual(report['axes']['transition_path_verification_status']['state'], VERIFIED)
        self.assertTrue(report['axes']['relation_change_observation_status']['scope'].endswith(
            ' -> BLOCK decision'))
        self.assertIn(failed.encode(), common.secure_read(decision_dir, 'checker.stdout'))
        self.assertFalse(list(decision_dir.rglob('certificate.json')))

    def test_in_process_replay_claims_only_fresh_recomputation(self):
        # The supported Python API can decide, replay and observe in this
        # single process. Real primitive subprocesses do not supply process
        # provenance for the enclosing verifier's decision recomputation.
        compute = authority._compute
        compute_pids = []

        def observed_compute(*args, **kwargs):
            compute_pids.append(os.getpid())
            return compute(*args, **kwargs)

        with mock.patch.object(authority, '_compute', side_effect=observed_compute), \
                mock.patch.object(transition_report, '_compute', side_effect=observed_compute):
            _, receipt, report, _, _ = self.capture()
        self.assertEqual(compute_pids, [os.getpid()] * 3)
        self.assertEqual(receipt['replay_status'], 'MATCH')
        axis = report['axes']['reconstruction_reproducibility_status']
        self.assertEqual(axis['state'], 'VERIFIED_DECISION_REPLAY_ONLY')
        self.assertIn('Fresh recomputation', axis['scope'])
        self.assertNotIn('new verifier process', axis['scope'].lower())
        self.assertIn('process provenance is not recorded', axis['limitation'])

    def test_missing_runtime_replays_BLOCK_without_verifying_execution(self):
        captured = self.capture(pulse_root=self.fixture.home / 'missing-runtime')
        self.assert_incomplete_replay(captured)
        self.assertFalse(captured[0]['checker']['attempted'])

    def test_runtime_digest_mismatch_replays_BLOCK_without_verifying_execution(self):
        fixture = self.fixture
        fixture.profile['trusted_anchor']['existing_pulse_checker_sha256'] = '0' * 64
        fixture.files['profile.json'] = common.canonical_bytes(fixture.profile)
        fixture.rebind()
        captured = self.capture()
        self.assert_incomplete_replay(captured)
        self.assertIn('QRH003_PULSE_PRIMITIVE_DIGEST_MISMATCH', captured[0]['reason_codes'])
        self.assertFalse(captured[0]['checker']['attempted'])

    def test_checker_process_error_is_incomplete_despite_exact_replay(self):
        # The parser is the actual pinned PULSE parser; only this TEST checker
        # is replaced by a process that exits with the error code 2.
        runtime = self.runtime_with_TEST_tool('checker', b'raise SystemExit(2)\n')
        captured = self.capture(pulse_root=runtime)
        self.assert_incomplete_replay(captured)
        self.assertEqual(captured[0]['checker']['exit_code'], 2)
        materialized = common.read_json(captured[3] / 'materialized_required.json')
        self.assertTrue(materialized['policy_materialization_verified'])
        self.assertEqual(materialized['policy_parser']['exit_code'], 0)

    def test_parser_wrong_required_set_is_incomplete_despite_exact_replay(self):
        runtime = self.runtime_with_TEST_tool('parser', b"print('qrh003_subject_bound')\n")
        captured = self.capture(pulse_root=runtime)
        self.assert_incomplete_replay(captured)
        materialized = common.read_json(captured[3] / 'materialized_required.json')
        self.assertTrue(materialized['policy_parser']['attempted'])
        self.assertEqual(materialized['policy_parser']['exit_code'], 0)
        self.assertFalse(materialized['policy_parser']['exact_required_set_verified'])
        self.assertFalse(materialized['policy_materialization_verified'])

    def test_parser_timeout_is_incomplete_despite_exact_replay(self):
        with self.timeout_at_process_boundary('parser'):
            captured = self.capture()
        self.assert_incomplete_replay(captured)
        materialized = common.read_json(captured[3] / 'materialized_required.json')
        self.assertTrue(materialized['policy_parser']['timeout'])
        self.assertFalse(captured[0]['checker']['attempted'])

    def test_checker_timeout_is_incomplete_despite_exact_replay(self):
        with self.timeout_at_process_boundary('checker'):
            captured = self.capture()
        self.assert_incomplete_replay(captured)
        self.assertTrue(captured[0]['checker']['timeout'])
        materialized = common.read_json(captured[3] / 'materialized_required.json')
        self.assertTrue(materialized['policy_materialization_verified'])

    def test_nonliteral_or_incomplete_execution_summaries_never_verify(self):
        with self.evaluator():
            fresh = authority._compute(self.fixture.bundle, self.fixture.anchor_path,
                                       pulse_root=PULSE_ROOT)
        self.assertTrue(transition_report._offline_execution_verified(fresh))
        locations = {
            'materialized': ('materialized',),
            'parser': ('materialized', 'policy_parser'),
            'checker': ('decision', 'checker'),
        }
        invalid = (
            ('materialized', 'policy_materialization_verified', (False, None, 1, 'true')),
            ('parser', 'attempted', (False, None, 1, 'true')),
            ('parser', 'exit_code', (False, None, '0', 1)),
            ('parser', 'timeout', (True, None, 0, 'false')),
            ('parser', 'exact_required_set_verified', (False, None, 1, 'true')),
            ('checker', 'attempted', (False, None, 1, 'true')),
            ('checker', 'exit_code', (False, True, '0', 2)),
            ('checker', 'timeout', (True, None, 0, 'false')),
        )
        for location, field, values in invalid:
            for value in values:
                with self.subTest(location=location, field=field, value=repr(value)):
                    changed = copy.deepcopy(fresh)
                    target = changed
                    for component in locations[location]:
                        target = target[component]
                    target[field] = value
                    self.assertFalse(transition_report._offline_execution_verified(changed))
        for record, field in (('materialized', 'ordered_gate_ids'),
                              ('decision', 'required_gate_ids')):
            with self.subTest(required_set=record):
                changed = copy.deepcopy(fresh)
                changed[record][field] = changed[record][field][:-1]
                self.assertFalse(transition_report._offline_execution_verified(changed))

    def test_each_decision_and_replay_endpoint_rejects_byte_tampering(self):
        _, _, _, decision_dir, replay_dir = self.capture()
        endpoints = [(decision_dir, name) for name in
                     ('decision.json', 'status.json', 'materialized_required.json')]
        endpoints += [(replay_dir, name) for name in
                      ('recomputed_decision.json', 'recomputed_status.json',
                       'recomputed_materialized_required.json')]
        for directory, name in endpoints:
            path = directory / name
            original = path.read_bytes()
            with self.subTest(endpoint=name):
                try:
                    path.write_bytes(original + b'\n')
                    with self.evaluator(), self.assertRaises(common.AuditError) as error:
                        transition_report.report(self.fixture.bundle, self.fixture.anchor_path,
                                                 decision_dir, replay_dir, pulse_root=PULSE_ROOT)
                    self.assertEqual(error.exception.code, 'QRH003_TRANSITION_REPORT_ENDPOINT_MISMATCH')
                finally:
                    path.write_bytes(original)

    def test_replay_receipt_endpoint_or_status_mismatch_is_rejected(self):
        _, _, _, decision_dir, replay_dir = self.capture()
        path = replay_dir / 'replay_receipt.json'
        original = path.read_bytes()
        for field, value in (('previous_decision_sha256', '0' * 64),
                             ('fresh_decision_sha256', '0' * 64),
                             ('replay_status', 'MISMATCH')):
            with self.subTest(field=field):
                changed = common.strict_loads(original)
                changed[field] = value
                try:
                    path.write_bytes(common.canonical_bytes(changed))
                    with self.evaluator(), self.assertRaises(common.AuditError) as error:
                        transition_report.report(self.fixture.bundle, self.fixture.anchor_path,
                                                 decision_dir, replay_dir, pulse_root=PULSE_ROOT)
                    self.assertEqual(error.exception.code, 'QRH003_TRANSITION_REPORT_ENDPOINT_MISMATCH')
                finally:
                    path.write_bytes(original)

    def test_local_timestamp_order_distinguishes_equality_from_conflict(self):
        for label, timestamp, state, scope_fragment in (
                ('earlier', '2026-10-07T11:59:00Z',
                 'LOCAL_ORDER_CONSISTENT_EXTERNALLY_UNVERIFIED', 'not later than'),
                ('equal', '2026-10-07T12:00:00Z',
                 'LOCAL_ORDER_CONSISTENT_EXTERNALLY_UNVERIFIED', 'not later than'),
                ('later', '2026-10-07T12:01:00Z',
                 'LOCAL_ORDER_CONFLICT', 'is later than')):
            with self.subTest(label=label):
                self.fixture.payload['created_utc'] = timestamp
                self.fixture.files['evidence/control.json'] = common.canonical_bytes(self.fixture.payload)
                self.fixture.rebind()
                _, _, report, _, _ = self.capture(label=label)
                axis = report['axes']['time_order_status']
                self.assertEqual(axis['state'], state)
                self.assertIn(scope_fragment, axis['scope'])
                self.assertIn('not independently trusted', axis['limitation'])

    def test_absent_observation_timestamps_are_not_a_reported_time_conflict(self):
        self.fixture.manifest['receipts'] = []
        self.fixture.write_manifest()
        _, _, report, _, _ = self.capture()
        axis = report['axes']['time_order_status']
        self.assertEqual(axis['state'], 'NOT_OBSERVED')
        self.assertIn('No authenticated observation timestamps', axis['scope'])


if __name__ == '__main__':
    unittest.main()
