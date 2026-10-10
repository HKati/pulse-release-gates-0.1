"""Authority boundary tests; no test result is evidence that QRH is true.

Positive emission tests mock only the evaluator under an isolated TEST anchor.
All JSON, Ed25519 authentication, external/code/tool digests, policy parsing,
the pinned upstream checker, materialization, filesystem writes and replay are
real. No production ALLOW or production mathematical certificate is generated.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys

ROOT = Path(__file__).absolute().parents[1]
from tools import authority, verify, audit, common, prepare
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

PULSE_ROOT = Path(os.environ.get('QRH_PULSE_ROOT', ROOT / 'reference' / 'pulse_runtime'))


class AuthorityBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='qrh003-TEST-')
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.bundle = self.home / 'bundle'
        self.bundle.mkdir()
        self.anchor_path = self.home / 'external-TEST-anchor.json'
        self.private = Ed25519PrivateKey.generate()
        self.public = self.private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        self.checker_path = 'PULSE_safe_pack_v0/tools/check_gates.py'
        self.parser_path = 'tools/policy_to_require_args.py'
        self.checker_sha = common.sha256_bytes(common.secure_read(PULSE_ROOT, self.checker_path))
        self.parser_sha = common.sha256_bytes(common.secure_read(PULSE_ROOT, self.parser_path))
        self.profile = {
            'artifact_role': 'TEST_CONTROL_ONLY',
            'trust_domain': 'TEST',
            'trusted_anchor': {
                'existing_pulse_checker_path': self.checker_path,
                'existing_pulse_checker_sha256': self.checker_sha,
                'existing_pulse_policy_parser_path': self.parser_path,
                'existing_pulse_policy_parser_sha256': self.parser_sha,
            },
            'certificate_profiles': {
                k: {'policy_set': 'qrh003_' + k + '_certificate',
                    'trust_domain': 'TEST',
                    'certificate_type': 'qrh003_TEST_' + k + '_certificate_v1'}
                for k in ('technical', 'semantic')
            },
        }
        self.policy = 'version: qrh003_test_v1\ngates:\n' + ''.join(
            '  qrh003_' + k + '_certificate:\n' + ''.join('    - ' + g + '\n' for g in verify.expected_required(k))
            for k in ('technical', 'semantic'))
        self.payload = {
            'schema_version': 'qrh003_capture_v1', 'kind': 'TEST_AUTHORITY_CONTROL',
            'trust_domain': 'TEST', 'evidence_class': 'synthetic_fixture',
            'run_key': 'isolated-TEST-control', 'subject_commit': common.SUBJECT_COMMIT,
            'pulse_commit': common.PULSE_COMMIT,
            'collector_sha256': '1' * 64, 'capture_policy_sha256': '2' * 64,
            'created_utc': '2026-10-07T12:00:00Z',
            'body': {'scope': 'authority_control_only', 'does_not_assert_QRH': True},
        }
        self.files = {'profile.json': common.canonical_bytes(self.profile),
                      'policy.yml': self.policy.encode(),
                      'gate_registry.yml': b'version: isolated_test_registry\n',
                      'evidence/control.json': common.canonical_bytes(self.payload)}
        self.manifest = {
            'schema_version': 'qrh003_bundle_v1', 'trust_domain': 'TEST',
            'run_key': 'isolated-TEST-control', 'created_utc': '2026-10-07T12:00:00Z',
            'subject_commit': common.SUBJECT_COMMIT, 'pulse_commit': common.PULSE_COMMIT,
            'profile_kind': 'technical', 'artifacts': [], 'receipts': [],
        }
        self.anchor = {
            'schema_version': 'qrh003_anchor_v1', 'trust_domain': 'TEST',
            'subject_commit': common.SUBJECT_COMMIT, 'pulse_commit': common.PULSE_COMMIT,
            'profile_sha256': '', 'policy_sha256': '', 'registry_sha256': '',
            'verifier_files': {name: common.sha256_bytes(common.secure_read(ROOT, name))
                               for name in sorted(verify.MINIMUM_VERIFIER_FILES)},
            'collector_keys': [{'key_id': 'isolated-TEST-key', 'public_key_hex': self.public,
                                'trust_domain': 'TEST', 'collector_sha256': '1' * 64,
                                'capture_policy_sha256': '2' * 64,
                                'allowed_kinds': ['TEST_AUTHORITY_CONTROL', 'bundle_seal']}],
            'required_sets': {k: verify.expected_required(k) for k in ('technical', 'semantic')},
            'source_binding': common.source_runtime().contract(),
        }
        self.rebind()

    def rebind(self, sign=True, anchor=True):
        self.manifest['artifacts'] = []
        for name, content in self.files.items():
            path = self.bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            self.manifest['artifacts'].append({'path': name, 'sha256': common.sha256_bytes(content),
                'bytes': len(content), 'role': 'test_control', 'evidence_class': 'synthetic_fixture'})
        if sign:
            self.manifest['receipts'] = [{
                'payload_path': 'evidence/control.json', 'key_id': 'isolated-TEST-key',
                'signature_hex': self.private.sign(self.files['evidence/control.json']).hex(),
            }]
        self.write_manifest()
        if anchor:
            for filename, key in [('profile.json', 'profile_sha256'), ('policy.yml', 'policy_sha256'),
                                  ('gate_registry.yml', 'registry_sha256')]:
                self.anchor[key] = common.sha256_bytes(self.files[filename])
        self.write_anchor()

    def write_manifest(self):
        raw = common.canonical_bytes(self.manifest)
        (self.bundle / 'manifest.json').write_bytes(raw)
        seal = {'schema_version': 'qrh003_manifest_signature_v1',
                'key_id': 'isolated-TEST-key', 'manifest_sha256': common.sha256_bytes(raw),
                'signature_hex': self.private.sign(raw).hex()}
        (self.bundle / 'manifest.signature.json').write_bytes(common.canonical_bytes(seal))

    def write_anchor(self):
        self.anchor_path.write_bytes(common.canonical_bytes(self.anchor))

    def evaluation(self, gates=True):
        values = {g: bool(gates) for g in common.GATE_IDS}
        return {'gates': values,
                'evaluations': {g: {'state': 'VERIFIED' if values[g] else 'NOT_RUN',
                                   'reason_codes': [], 'evidence_refs': ['evidence/control.json']}
                                for g in common.GATE_IDS},
                'states': {name: {'state': 'NOT_ASSESSED', 'reason_codes': [], 'evidence_refs': []}
                           for name in audit.STATE_NAMES},
                'limitations': ['ISOLATED TEST MOCK; NO MATHEMATICAL CLAIM']}

    def evaluator(self, values=True):
        def only_test(snapshot, anchor, profile_kind):
            self.assertEqual(anchor['trust_domain'], 'TEST')
            self.assertEqual(snapshot['manifest']['trust_domain'], 'TEST')
            return self.evaluation(values)
        return mock.patch.object(audit, 'evaluate', side_effect=only_test)

    def assert_rejected(self, code):
        with mock.patch.object(audit, 'evaluate') as evaluator:
            with self.assertRaises(common.AuditError) as result:
                verify.verify_bundle(self.bundle, self.anchor_path)
            self.assertEqual(result.exception.code, code)
            evaluator.assert_not_called()

    def test_positive_TEST_only_emission_and_exact_replay(self):
        with self.evaluator():
            decision = authority.decide(self.bundle, self.anchor_path, self.home / 'decision', pulse_root=PULSE_ROOT)
            self.assertEqual(decision['result'], 'ALLOW')
            self.assertEqual(decision['checker']['exit_code'], 0)
            receipt = authority.replay(self.bundle, self.anchor_path, self.home / 'decision',
                                       self.home / 'replay', pulse_root=PULSE_ROOT)
        self.assertEqual(receipt['replay_status'], 'MATCH')
        certificate = common.read_json(self.home / 'decision/test_only/certificate.json')
        self.assertEqual(certificate['certificate_type'], 'qrh003_TEST_technical_certificate_v1')
        self.assertEqual(certificate['certificate_type'],
                         self.profile['certificate_profiles']['technical']['certificate_type'])
        self.assertEqual(certificate['scope'], 'TEST_AUTHORITY_CONTROL_ONLY')
        self.assertFalse(certificate['mathematical_or_community_acceptance_asserted'])
        self.assertFalse((self.home / 'decision/production_certificates').exists())
        self.assertFalse(list((self.home / 'replay').rglob('certificate.json')))

    def test_semantic_profile_materializes_all_thirteen(self):
        self.manifest['profile_kind'] = 'semantic'; self.write_manifest()
        with self.evaluator():
            decision = authority.decide(self.bundle, self.anchor_path, self.home / 'semantic', pulse_root=PULSE_ROOT)
            receipt = authority.replay(self.bundle, self.anchor_path, self.home / 'semantic',
                                       self.home / 'semantic-replay', pulse_root=PULSE_ROOT)
        self.assertEqual(decision['result'], 'ALLOW')
        record = common.read_json(self.home / 'semantic/materialized_required.json')
        self.assertEqual(record['ordered_gate_ids'], list(common.GATE_IDS))
        certificate = common.read_json(self.home / 'semantic/test_only/certificate.json')
        self.assertEqual(certificate['certificate_type'], 'qrh003_TEST_semantic_certificate_v1')
        self.assertEqual(certificate['certificate_type'],
                         self.profile['certificate_profiles']['semantic']['certificate_type'])
        self.assertEqual(certificate['scope'], 'TEST_AUTHORITY_CONTROL_ONLY')
        self.assertEqual(receipt['replay_status'], 'MATCH')
        self.assertFalse((self.home / 'semantic/production_certificates').exists())

    def test_prepared_profiles_use_the_exact_supported_v1_types(self):
        # Exercise the actual profile producer against the output-contract
        # consumer. Preparing either domain neither runs an evaluator nor
        # authorizes/emits a certificate, including for PRODUCTION.
        expected = {
            ('PRODUCTION', 'technical'): 'qrh003_technical_certificate_v1',
            ('PRODUCTION', 'semantic'): 'qrh003_semantic_certificate_v1',
            ('TEST', 'technical'): 'qrh003_TEST_technical_certificate_v1',
            ('TEST', 'semantic'): 'qrh003_TEST_semantic_certificate_v1',
        }
        with mock.patch.object(audit, 'evaluate') as evaluator:
            for domain in ('PRODUCTION', 'TEST'):
                config = self.home / ('prepared-' + domain)
                prepare.prepare(config, self.home / (domain + '.seed'), domain)
                profile_bytes = (config / 'profile.json').read_bytes()
                profile = common.strict_loads(profile_bytes)
                for kind in ('technical', 'semantic'):
                    with self.subTest(domain=domain, kind=kind):
                        verified = {'anchor': common.read_json(config / 'anchor.json'),
                                    'profile_kind': kind,
                                    'snapshot': {'files': {'profile.json': profile_bytes}}}
                        self.assertEqual(profile['certificate_profiles'][kind]['certificate_type'],
                                         expected[(domain, kind)])
                        self.assertEqual(authority._declared_certificate_type(verified),
                                         expected[(domain, kind)])
            evaluator.assert_not_called()
        self.assertFalse(list(self.home.rglob('certificate.json')))

    def assert_certificate_contract_block(self, output_name, reason_code):
        # Coherently re-sign and re-anchor the changed profile so that this
        # probes the content contract, not an earlier artifact hash failure.
        self.files['profile.json'] = common.canonical_bytes(self.profile)
        self.rebind()
        output = self.home / output_name
        with self.evaluator() as evaluator:
            decision = authority.decide(self.bundle, self.anchor_path, output, pulse_root=PULSE_ROOT)
        evaluator.assert_called_once()
        self.assertEqual(decision['result'], 'BLOCK')
        self.assertIn(reason_code, decision['reason_codes'])
        self.assertEqual(decision['failed_required_gates'], [])
        self.assertFalse(decision['checker']['attempted'])
        self.assertFalse(list(output.rglob('certificate.json')))
        self.assertTrue((output / 'primitive_error.txt').read_bytes())
        return decision

    def test_missing_certificate_type_blocks_verified_TEST_gates(self):
        del self.profile['certificate_profiles']['technical']['certificate_type']
        self.assert_certificate_contract_block('missing-type', 'QRH003_CERTIFICATE_TYPE_MISSING')

    def test_invalid_certificate_types_block_after_coherent_rebinding(self):
        invalid = [None, True, 1, [], {}, '', 'unreviewed_producer_certificate',
                   'qrh003_test_certificate_v0', 'qrh003_TEST_technical_certificate_v0',
                   'qrh003_TEST_technical_certificate_v1\n']
        for index, value in enumerate(invalid):
            with self.subTest(value=value):
                self.profile['certificate_profiles']['technical']['certificate_type'] = value
                self.assert_certificate_contract_block('invalid-type-' + str(index),
                                                       'QRH003_CERTIFICATE_TYPE_MISMATCH')

    def test_certificate_type_domain_and_kind_mismatches_block(self):
        for kind, other in [('technical', 'semantic'), ('semantic', 'technical')]:
            self.manifest['profile_kind'] = kind
            mismatches = ['qrh003_' + kind + '_certificate_v1',
                          'qrh003_TEST_' + other + '_certificate_v1',
                          'qrh003_' + other + '_certificate_v1']
            for index, value in enumerate(mismatches):
                with self.subTest(kind=kind, value=value):
                    self.profile['certificate_profiles'][kind]['certificate_type'] = value
                    self.assert_certificate_contract_block('wrong-binding-' + kind + '-' + str(index),
                                                           'QRH003_CERTIFICATE_TYPE_MISMATCH')

    def test_certificate_profile_domain_mismatch_blocks(self):
        for index, value in enumerate([None, 'PRODUCTION', 'UNVERIFIED']):
            with self.subTest(domain=value):
                self.profile['certificate_profiles']['technical']['trust_domain'] = value
                self.assert_certificate_contract_block('wrong-declaration-domain-' + str(index),
                                                       'QRH003_CERTIFICATE_PROFILE_DOMAIN_MISMATCH')
        self.profile['certificate_profiles']['technical']['trust_domain'] = 'TEST'
        self.profile['trust_domain'] = 'PRODUCTION'
        self.assert_certificate_contract_block('wrong-root-domain',
                                               'QRH003_CERTIFICATE_PROFILE_DOMAIN_MISMATCH')

    def test_replay_rejects_a_certificate_type_changed_after_emission(self):
        with self.evaluator():
            authority.decide(self.bundle, self.anchor_path, self.home / 'typed-original', pulse_root=PULSE_ROOT)
            path = self.home / 'typed-original/test_only/certificate.json'
            certificate = common.read_json(path)
            certificate['certificate_type'] = 'qrh003_TEST_semantic_certificate_v1'
            path.write_bytes(common.canonical_bytes(certificate))
            receipt = authority.replay(self.bundle, self.anchor_path, self.home / 'typed-original',
                                       self.home / 'typed-replay', pulse_root=PULSE_ROOT)
        self.assertEqual(receipt['fresh_result'], 'ALLOW')
        self.assertEqual(receipt['replay_status'], 'MISMATCH')
        self.assertEqual(receipt['reason_code'], 'QRH003_CERTIFICATE_REPLAY_MISMATCH')
        self.assertFalse(list((self.home / 'typed-replay').rglob('certificate.json')))

    def test_real_pulse_blocks_false_gate_and_preserves_diagnostic(self):
        with self.evaluator(False):
            decision = authority.decide(self.bundle, self.anchor_path, self.home / 'block', pulse_root=PULSE_ROOT)
        self.assertEqual(decision['result'], 'BLOCK')
        self.assertEqual(decision['checker']['exit_code'], 1)
        self.assertEqual(decision['failed_required_gates'], list(common.GATE_IDS[:10]))
        self.assertFalse(list((self.home / 'block').rglob('certificate.json')))
        self.assertTrue((self.home / 'block/checker.stdout').read_bytes())

    def test_missing_primitive_cannot_allow(self):
        with self.evaluator():
            decision = authority.decide(self.bundle, self.anchor_path, self.home / 'no-pulse')
        self.assertEqual(decision['result'], 'BLOCK')
        self.assertIn('QRH003_PULSE_RUNTIME_UNAVAILABLE', decision['reason_codes'])
        self.assertFalse(list((self.home / 'no-pulse').rglob('certificate.json')))

    def test_foreign_all_true_status_is_not_admission(self):
        with self.evaluator(False):
            expected = verify.verify_bundle(self.bundle, self.anchor_path)['status_expected']
            expected['gates'] = {g: True for g in common.GATE_IDS}
            status = self.home / 'foreign.json'; status.write_bytes(common.canonical_bytes(expected))
            with self.assertRaises(common.AuditError) as result:
                verify.verify_bundle(self.bundle, self.anchor_path, incoming_status=status)
        self.assertEqual(result.exception.code, 'QRH003_FOREIGN_OR_STALE_STATUS')

    def test_nonboolean_and_missing_gate_rejected(self):
        for gate in common.GATE_IDS:
            for mutation in ('true', 1, None, 'MISSING'):
                with self.subTest(gate=gate, mutation=mutation), self.evaluator():
                    expected = verify.verify_bundle(self.bundle, self.anchor_path)['status_expected']
                    if mutation == 'MISSING': del expected['gates'][gate]
                    else: expected['gates'][gate] = mutation
                    path = self.home / 'nonboolean.json'; path.write_bytes(common.canonical_bytes(expected))
                    with self.assertRaises(common.AuditError) as result:
                        verify.verify_bundle(self.bundle, self.anchor_path, incoming_status=path)
                    code = 'QRH003_GATE_SET_MISMATCH' if mutation == 'MISSING' else 'QRH003_GATE_NOT_LITERAL_BOOLEAN'
                    self.assertEqual(result.exception.code, code)

    def test_duplicate_json_key_rejected_before_evaluation(self):
        raw = (self.bundle / 'manifest.json').read_bytes()
        (self.bundle / 'manifest.json').write_bytes(raw[:-1] + b',"run_key":"replaced"}')
        self.assert_rejected('DUPLICATE_JSON_KEY')

    def test_nan_and_overflow_json_rejected_before_evaluation(self):
        for value in (b'NaN', b'Infinity', b'1e999'):
            with self.subTest(value=value):
                self.write_manifest()
                raw = (self.bundle / 'manifest.json').read_bytes()
                (self.bundle / 'manifest.json').write_bytes(raw[:-1] + b',"bad":' + value + b'}')
                with mock.patch.object(audit, 'evaluate') as evaluator:
                    with self.assertRaises(common.AuditError) as error:
                        verify.verify_bundle(self.bundle, self.anchor_path)
                    self.assertIn(error.exception.code, ('NONFINITE_JSON_NUMBER', 'NONCANONICAL_JSON_TYPE'))
                    evaluator.assert_not_called()

    def test_changed_artifact_without_rebinding(self):
        (self.bundle / 'evidence/control.json').write_bytes(b'{}')
        self.assert_rejected('QRH003_SUBJECT_DIGEST_MISMATCH')

    def test_missing_artifact(self):
        (self.bundle / 'evidence/control.json').unlink()
        self.assert_rejected('UNSAFE_OR_MISSING_ARTIFACT')

    def test_path_traversal(self):
        self.manifest['artifacts'][0]['path'] = '../escape'; self.write_manifest()
        self.assert_rejected('QRH003_UNSAFE_PATH')

    def test_symlink_artifact(self):
        target = self.home / 'target'; target.write_bytes(self.files['evidence/control.json'])
        (self.bundle / 'evidence/control.json').unlink()
        (self.bundle / 'evidence/control.json').symlink_to(target)
        self.assert_rejected('UNSAFE_OR_MISSING_ARTIFACT')

    def test_anchor_inside_bundle(self):
        path = self.bundle / 'anchor.json'; path.write_bytes(common.canonical_bytes(self.anchor))
        with self.assertRaises(common.AuditError) as result:
            verify.verify_bundle(self.bundle, path)
        self.assertEqual(result.exception.code, 'QRH003_ANCHOR_INSIDE_BUNDLE')

    def test_self_consistent_poisoned_policy_without_external_reanchor(self):
        self.files['policy.yml'] = b'version: poisoned\ngates:\n  qrh003_technical_certificate: []\n'
        self.rebind(anchor=False)
        self.assert_rejected('QRH003_POLICY_ANCHOR_MISMATCH')

    def test_reduced_anchor_required_set(self):
        self.anchor['required_sets']['technical'] = list(common.GATE_IDS[:9]); self.write_anchor()
        self.assert_rejected('QRH003_REQUIRED_SET_MISMATCH')

    def test_weak_declared_policy_reaches_materializer(self):
        self.files['policy.yml'] = self.policy.replace('    - ' + common.GATE_IDS[0] + '\n', '', 1).encode()
        self.rebind()
        with self.evaluator() as evaluator:
            decision = authority.decide(self.bundle, self.anchor_path, self.home / 'weak', pulse_root=PULSE_ROOT)
        evaluator.assert_called_once()
        self.assertEqual(decision['result'], 'BLOCK')
        self.assertIn('QRH003_REQUIRED_SET_MISMATCH', decision['reason_codes'])
        self.assertFalse(list((self.home / 'weak').rglob('certificate.json')))

    def test_duplicate_policy_mapping_reaches_strict_materializer(self):
        self.files['policy.yml'] += b'\ngates:\n  qrh003_technical_certificate: []\n'
        self.rebind()
        with self.evaluator() as evaluator:
            decision = authority.decide(self.bundle, self.anchor_path, self.home / 'duplicate-policy', pulse_root=PULSE_ROOT)
        evaluator.assert_called_once()
        self.assertIn('QRH003_DUPLICATE_MAPPING_KEY', decision['reason_codes'])

    def test_unpinned_verifier_module(self):
        del self.anchor['verifier_files']['tools/authority.py']; self.write_anchor()
        self.assert_rejected('QRH003_VERIFIER_ANCHOR_INCOMPLETE')

    def test_verifier_digest_mismatch(self):
        self.anchor['verifier_files']['tools/verify.py'] = '0' * 64; self.write_anchor()
        self.assert_rejected('QRH003_VERIFIER_ANCHOR_MISMATCH')

    def test_old_upstream_commit(self):
        self.manifest['subject_commit'] = '0' * 40; self.write_manifest()
        self.assert_rejected('QRH003_SUBJECT_COMMIT_MISMATCH')

    def test_fabricated_receipt_even_with_coherent_log_hash(self):
        self.payload['body']['fabricated_build_success'] = True
        self.files['evidence/control.json'] = common.canonical_bytes(self.payload)
        self.rebind(sign=False)
        self.assert_rejected('QRH003_RECEIPT_SIGNATURE_INVALID')

    def test_coherent_artifact_and_manifest_rewrite_without_seal_fails(self):
        # The control receipt does not reference this raw log. Previously a
        # digest-coherent rewrite of both artifact and manifest was unauthenticated.
        self.files['evidence/unreferenced.stdout'] = b'original process log'
        self.rebind()
        replacement = b'forged successful process log'
        (self.bundle / 'evidence/unreferenced.stdout').write_bytes(replacement)
        for artifact in self.manifest['artifacts']:
            if artifact['path'] == 'evidence/unreferenced.stdout':
                artifact['sha256'] = common.sha256_bytes(replacement)
                artifact['bytes'] = len(replacement)
        # Deliberately do not call the TEST-only signing helper.
        raw = common.canonical_bytes(self.manifest)
        (self.bundle / 'manifest.json').write_bytes(raw)
        self.assert_rejected('QRH003_MANIFEST_SEAL_DIGEST_MISMATCH')

    def test_rehashed_manifest_seal_without_authorized_signature_fails(self):
        self.manifest['created_utc'] = '2026-10-07T12:00:01Z'
        raw = common.canonical_bytes(self.manifest)
        (self.bundle / 'manifest.json').write_bytes(raw)
        path = self.bundle / 'manifest.signature.json'
        seal = common.read_json(path)
        seal['manifest_sha256'] = common.sha256_bytes(raw)
        path.write_bytes(common.canonical_bytes(seal))
        self.assert_rejected('QRH003_MANIFEST_SEAL_SIGNATURE_INVALID')

    def test_manifest_seal_signature_tampering(self):
        path = self.bundle / 'manifest.signature.json'
        seal = common.read_json(path)
        seal['signature_hex'] = '0' * 128
        path.write_bytes(common.canonical_bytes(seal))
        self.assert_rejected('QRH003_MANIFEST_SEAL_SIGNATURE_INVALID')

    def test_manifest_seal_role_must_be_explicitly_authorized(self):
        self.anchor['collector_keys'][0]['allowed_kinds'].remove('bundle_seal')
        self.write_anchor()
        self.assert_rejected('QRH003_MANIFEST_SEAL_ROLE_UNAUTHORIZED')

    def test_manifest_seal_signer_must_be_in_external_anchor(self):
        path = self.bundle / 'manifest.signature.json'
        seal = common.read_json(path)
        seal['key_id'] = 'unauthorized-sealer'
        path.write_bytes(common.canonical_bytes(seal))
        self.assert_rejected('QRH003_MANIFEST_SEAL_SIGNER_UNAUTHORIZED')

    def test_manifest_seal_is_mandatory(self):
        (self.bundle / 'manifest.signature.json').unlink()
        self.assert_rejected('UNSAFE_OR_MISSING_ARTIFACT')

    def test_manifest_seal_cannot_be_its_own_manifest_member(self):
        self.files['manifest.signature.json'] = b'{}'
        self.rebind()
        self.assert_rejected('QRH003_ARTIFACT_PATH_DUPLICATE_OR_RESERVED')

    def test_signature_from_unauthorized_collector(self):
        self.manifest['receipts'][0]['key_id'] = 'unauthorized'; self.write_manifest()
        self.assert_rejected('QRH003_COLLECTOR_UNAUTHORIZED')

    def test_signed_receipt_wrong_run(self):
        self.payload['run_key'] = 'other-run'
        self.files['evidence/control.json'] = common.canonical_bytes(self.payload); self.rebind()
        self.assert_rejected('QRH003_RECEIPT_SCOPE_MISMATCH')

    def test_signed_receipt_wrong_capture_boundary(self):
        self.payload['capture_policy_sha256'] = '3' * 64
        self.files['evidence/control.json'] = common.canonical_bytes(self.payload); self.rebind()
        self.assert_rejected('QRH003_CAPTURE_POLICY_ANCHOR_MISMATCH')

    def test_capture_policy_artifact_must_match_external_key_policy(self):
        self.files['capture_policy.json'] = b'{"policy":"changed"}'
        self.rebind()
        self.assert_rejected('QRH003_CAPTURE_POLICY_ARTIFACT_MISMATCH')

    def test_evaluator_gate_state_inconsistency_rejected(self):
        evaluation = self.evaluation(True)
        evaluation['evaluations'][common.GATE_IDS[0]]['state'] = 'NOT_RUN'
        with mock.patch.object(audit, 'evaluate', return_value=evaluation) as evaluator:
            with self.assertRaises(common.AuditError) as error:
                verify.verify_bundle(self.bundle, self.anchor_path)
        evaluator.assert_called_once()
        self.assertEqual(error.exception.code, 'QRH003_EVALUATOR_GATE_STATE_MISMATCH')

    def test_verified_gate_with_missing_evidence_reference_rejected(self):
        evaluation = self.evaluation(True)
        evaluation['evaluations'][common.GATE_IDS[0]]['evidence_refs'] = ['absent.json']
        with mock.patch.object(audit, 'evaluate', return_value=evaluation) as evaluator:
            with self.assertRaises(common.AuditError) as error:
                verify.verify_bundle(self.bundle, self.anchor_path)
        evaluator.assert_called_once()
        self.assertEqual(error.exception.code, 'QRH003_VERIFIED_EVIDENCE_REFERENCE_MISSING')

    def test_semantic_request_cannot_be_downgraded_to_technical_bundle(self):
        with mock.patch.object(audit, 'evaluate') as evaluator:
            with self.assertRaises(common.AuditError) as error:
                verify.verify_bundle(self.bundle, self.anchor_path, profile_kind='semantic')
        evaluator.assert_not_called()
        self.assertEqual(error.exception.code, 'QRH003_PROFILE_SCOPE_MISMATCH')

    def test_decision_cannot_be_an_input_artifact(self):
        self.files['decision.json'] = b'{"result":"ALLOW"}'
        self.rebind()
        self.assert_rejected('QRH003_ARTIFACT_PATH_DUPLICATE_OR_RESERVED')

    def test_unexpected_evaluator_failure_preserves_BLOCK_report(self):
        with mock.patch.object(audit, 'evaluate', side_effect=KeyError('missing-field')):
            decision = authority.decide(self.bundle, self.anchor_path, self.home / 'exception', pulse_root=PULSE_ROOT)
        self.assertEqual(decision['result'], 'BLOCK')
        self.assertIn('QRH003_UNEXPECTED_ADMISSION_ERROR', decision['reason_codes'])
        self.assertIn(b'KeyError', (self.home / 'exception/admission_error.txt').read_bytes())
        self.assertFalse(list((self.home / 'exception').rglob('certificate.json')))

    def test_receipt_reuse(self):
        self.manifest['receipts'].append(copy.deepcopy(self.manifest['receipts'][0])); self.write_manifest()
        self.assert_rejected('QRH003_RECEIPT_SCOPE_REUSED')

    def test_TEST_domain_rejected_by_simulated_production_admission(self):
        # Direct production admission branch in TEST harness; evaluator never runs.
        self.anchor['trust_domain'] = 'PRODUCTION'; self.write_anchor()
        self.assert_rejected('QRH003_TEST_ORIGIN_IN_PRODUCTION')

    def test_fixture_rejected_by_simulated_production_admission(self):
        self.anchor['trust_domain'] = self.manifest['trust_domain'] = 'PRODUCTION'
        # Simulated external production metadata exists only inside this TEST
        # harness. It reaches the evidence-class rejection; no evaluator runs.
        self.anchor['collector_keys'][0]['trust_domain'] = 'PRODUCTION'
        self.write_anchor(); self.write_manifest()
        self.assert_rejected('QRH003_SYNTHETIC_EVIDENCE_IN_PRODUCTION')

    def test_receipt_evidence_reclassification(self):
        for artifact in self.manifest['artifacts']:
            if artifact['path'] == 'evidence/control.json': artifact['evidence_class'] = 'actual_observation'
        self.write_manifest()
        self.assert_rejected('QRH003_EVIDENCE_CLASS_RECLASSIFIED')

    def test_exclusive_output_refuses_previous_run_and_preserves_bytes(self):
        output = self.home / 'stale'; output.mkdir()
        stale = output / 'old'; stale.write_bytes(b'previous-attempt')
        with self.assertRaises(common.AuditError) as result:
            authority.decide(self.bundle, self.anchor_path, output, pulse_root=PULSE_ROOT)
        self.assertEqual(result.exception.code, 'QRH003_OUTPUT_ALREADY_EXISTS')
        self.assertEqual(stale.read_bytes(), b'previous-attempt')

    def test_output_symlink_parent_is_rejected(self):
        (self.home / 'linked').symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(common.AuditError) as result:
            authority.decide(self.bundle, self.anchor_path, self.home / 'linked/new', pulse_root=PULSE_ROOT)
        self.assertEqual(result.exception.code, 'QRH003_SYMLINK_REJECTED')

    def test_checker_source_digest_mismatch(self):
        self.profile['trusted_anchor']['existing_pulse_checker_sha256'] = '0' * 64
        self.files['profile.json'] = common.canonical_bytes(self.profile); self.rebind()
        with self.evaluator():
            decision = authority.decide(self.bundle, self.anchor_path, self.home / 'bad-checker', pulse_root=PULSE_ROOT)
        self.assertIn('QRH003_PULSE_PRIMITIVE_DIGEST_MISMATCH', decision['reason_codes'])
        self.assertFalse(list((self.home / 'bad-checker').rglob('certificate.json')))

    def test_replay_reduced_materialized_set_is_targeted(self):
        with self.evaluator():
            authority.decide(self.bundle, self.anchor_path, self.home / 'original', pulse_root=PULSE_ROOT)
            materialized = common.read_json(self.home / 'original/materialized_required.json')
            materialized['ordered_gate_ids'] = materialized['ordered_gate_ids'][:-1]
            raw = common.canonical_bytes(materialized)
            (self.home / 'original/materialized_required.json').write_bytes(raw)
            decision = common.read_json(self.home / 'original/decision.json')
            decision['materialized_required_sha256'] = common.sha256_bytes(raw)
            (self.home / 'original/decision.json').write_bytes(common.canonical_bytes(decision))
            receipt = authority.replay(self.bundle, self.anchor_path, self.home / 'original',
                                       self.home / 'replay-reduced', pulse_root=PULSE_ROOT)
        self.assertEqual(receipt['replay_status'], 'MISMATCH')
        self.assertEqual(receipt['reason_code'], 'QRH003_REQUIRED_SET_MISMATCH')

    def test_replay_forged_allow_is_not_reused(self):
        with self.evaluator(False):
            authority.decide(self.bundle, self.anchor_path, self.home / 'blocked', pulse_root=PULSE_ROOT)
            old = common.read_json(self.home / 'blocked/decision.json'); old['result'] = 'ALLOW'
            (self.home / 'blocked/decision.json').write_bytes(common.canonical_bytes(old))
            receipt = authority.replay(self.bundle, self.anchor_path, self.home / 'blocked',
                                       self.home / 'forged-replay', pulse_root=PULSE_ROOT)
        self.assertEqual(receipt['fresh_result'], 'BLOCK')
        self.assertEqual(receipt['reason_code'], 'QRH003_DECISION_REPLAY_MISMATCH')
        self.assertFalse(list((self.home / 'forged-replay').rglob('certificate.json')))

    def test_replay_rechecks_artifact_bytes(self):
        with self.evaluator():
            authority.decide(self.bundle, self.anchor_path, self.home / 'original', pulse_root=PULSE_ROOT)
            (self.bundle / 'evidence/control.json').write_bytes(b'{}')
            receipt = authority.replay(self.bundle, self.anchor_path, self.home / 'original',
                                       self.home / 'mutated-replay', pulse_root=PULSE_ROOT)
        self.assertEqual(receipt['fresh_result'], 'BLOCK')
        self.assertEqual(receipt['reason_code'], 'QRH003_DECISION_REPLAY_MISMATCH')

    def test_replay_rejects_changed_raw_decision_bytes(self):
        with self.evaluator():
            authority.decide(self.bundle, self.anchor_path, self.home / 'original', pulse_root=PULSE_ROOT)
            path = self.home / 'original/decision.json'
            path.write_bytes(path.read_bytes() + b'\n')
            receipt = authority.replay(self.bundle, self.anchor_path, self.home / 'original',
                                       self.home / 'whitespace-replay', pulse_root=PULSE_ROOT)
        self.assertEqual(receipt['reason_code'], 'QRH003_DECISION_REPLAY_MISMATCH')

    def test_replay_rejects_stale_certificate_in_wrong_namespace(self):
        with self.evaluator(False):
            authority.decide(self.bundle, self.anchor_path, self.home / 'blocked', pulse_root=PULSE_ROOT)
            namespace = self.home / 'blocked/production_certificates'; namespace.mkdir()
            (namespace / 'certificate.json').write_bytes(b'{"result":"ALLOW"}')
            receipt = authority.replay(self.bundle, self.anchor_path, self.home / 'blocked',
                                       self.home / 'stale-replay', pulse_root=PULSE_ROOT)
        self.assertEqual(receipt['fresh_result'], 'BLOCK')
        self.assertEqual(receipt['reason_code'], 'QRH003_STALE_OR_WRONG_NAMESPACE_CERTIFICATE')

    def test_read_mutation_is_detected(self):
        path = self.home / 'changing'; path.write_bytes(b'initial')
        original_read = common.os.read
        changed = False
        def mutate_after_read(fd, size):
            nonlocal changed
            data = original_read(fd, size)
            if not changed:
                changed = True; path.write_bytes(b'changed-and-longer')
            return data
        with mock.patch.object(common.os, 'read', side_effect=mutate_after_read):
            with self.assertRaises(common.AuditError) as result:
                common.secure_read(self.home, 'changing')
        self.assertEqual(result.exception.code, 'ARTIFACT_CHANGED_DURING_READ')

    def test_fifo_rejected_without_blocking(self):
        path = self.home / 'fifo'; os.mkfifo(path)
        with self.assertRaises(common.AuditError) as result:
            common.secure_read(self.home, 'fifo')
        self.assertEqual(result.exception.code, 'NONREGULAR_ARTIFACT')


if __name__ == '__main__':
    unittest.main(verbosity=2)
