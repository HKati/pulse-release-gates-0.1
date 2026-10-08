"""Post-decision Transition Meter observation, without authority side effects.

This report reads the completed input/status/decision/replay graph. It never
edits status or decides a certificate. Its source digest is recorded separately
because a post-decision report cannot be an input of its own earlier decision.
"""
from __future__ import annotations
import argparse
import datetime as dt
from pathlib import Path
import sys

try:
    from .common import AuditError, canonical_bytes, sha256_bytes, sha256_file, strict_loads, secure_read, write_json
    from .authority import _compute
except ImportError:
    from common import AuditError, canonical_bytes, sha256_bytes, sha256_file, strict_loads, secure_read, write_json
    from authority import _compute


def _offline_execution_verified(fresh):
    """A repeatable decision is not evidence that both primitives completed."""
    materialized = fresh['materialized']
    decision = fresh['decision']
    parser = materialized.get('policy_parser', {})
    checker = decision.get('checker', {})
    if not isinstance(parser, dict) or not isinstance(checker, dict):
        return False
    verified = fresh['verified']
    required = verified['anchor']['required_sets'][verified['profile_kind']]
    parser_exit = parser.get('exit_code')
    checker_exit = checker.get('exit_code')
    return (materialized.get('policy_materialization_verified') is True
            and materialized.get('ordered_gate_ids') == required
            and decision.get('required_gate_ids') == required
            and parser.get('attempted') is True
            and type(parser_exit) is int and parser_exit == 0
            and parser.get('timeout') is False
            and parser.get('exact_required_set_verified') is True
            and checker.get('attempted') is True
            and type(checker_exit) is int and checker_exit in (0, 1)
            and checker.get('timeout') is False)


def report(bundle, anchor, decision_dir, replay_dir, pulse_root=None):
    if pulse_root is None:
        pulse_root = Path(__file__).absolute().parents[1] / 'reference/pulse_runtime'
    fresh = _compute(bundle, anchor, pulse_root=pulse_root)
    verified = fresh['verified']
    if verified is None:
        raise AuditError('QRH003_TRANSITION_INPUT_ADMISSION_FAILED')
    d_raw = secure_read(decision_dir, 'decision.json')
    s_raw = secure_read(decision_dir, 'status.json')
    m_raw = secure_read(decision_dir, 'materialized_required.json')
    d = strict_loads(d_raw)
    replay = strict_loads(secure_read(replay_dir, 'replay_receipt.json'))
    digest = sha256_bytes(d_raw)
    if (d_raw != fresh['decision_bytes']
            or d['evidence_manifest_sha256'] != verified['snapshot']['evidence_manifest_sha256']
            or d['anchor_sha256'] != verified['anchor_sha256']
            or d['status_sha256'] != sha256_bytes(s_raw)
            or s_raw != canonical_bytes(verified['status_expected'])
            or d['materialized_required_sha256'] != sha256_bytes(m_raw)
            or m_raw != fresh['materialized_bytes']
            or replay['previous_decision_sha256'] != digest
            or replay['fresh_decision_sha256'] != digest
            or secure_read(replay_dir, 'recomputed_decision.json') != d_raw
            or secure_read(replay_dir, 'recomputed_status.json') != s_raw
            or secure_read(replay_dir, 'recomputed_materialized_required.json') != m_raw
            or replay['replay_status'] != 'MATCH'):
        raise AuditError('QRH003_TRANSITION_REPORT_ENDPOINT_MISMATCH')
    snapshot = verified['snapshot']
    files = snapshot['files']
    tests = strict_loads(files['observations/authority_boundary_tests.json'])
    passed = {t['id'] for t in tests['tests'] if t['outcome'] == 'PASS'}
    # Match an exact final method component, allowing the declared unittest
    # class name to remain part of the evidence rather than assuming its name.
    control = lambda name: any(t.endswith('.' + name) for t in passed)
    parse_time = lambda text: dt.datetime.fromisoformat(text.replace('Z', '+00:00'))
    timestamps = [parse_time(r['created_utc']) for r in snapshot['receipts']]
    sealed = parse_time(snapshot['manifest']['created_utc'])
    local_order = bool(timestamps) and max(timestamps) <= sealed
    if not timestamps:
        time_state = 'NOT_OBSERVED'
        time_scope = 'No authenticated observation timestamps are available for local ordering'
    elif local_order:
        time_state = 'LOCAL_ORDER_CONSISTENT_EXTERNALLY_UNVERIFIED'
        time_scope = 'All signed observation timestamps are not later than the final manifest seal timestamp'
    else:
        time_state = 'LOCAL_ORDER_CONFLICT'
        time_scope = 'At least one signed observation timestamp is later than the final manifest seal timestamp'
    gate_map = verified['evaluation']['gates']
    bound = gate_map['qrh003_subject_bound'] and gate_map['qrh003_scope_bound']
    controls = gate_map['qrh003_certificate_boundary_verified']
    execution_verified = _offline_execution_verified(fresh)
    relation = ('Signed TEST fixture -> evaluated TEST artifact relations'
                if snapshot['manifest']['trust_domain'] == 'TEST' else
                'Pinned released claim -> independently collected artifact relations')
    def axis(state, scope, refs, limitation):
        return {'state': state, 'scope': scope, 'evidence_refs': refs, 'limitation': limitation}
    axes = {
        'relation_change_observation_status': axis(
            'RECORDED' if bound else 'PARTIAL',
            relation + ' -> ' + d['result'] + ' decision',
            ['bundle/observations/source_identity.json', 'bundle/observations/scope_binding.json', 'decision/decision.json'],
            'No change in mathematical truth or community acceptance is asserted.'),
        'transition_path_verification_status': axis(
            'VERIFIED_FOR_DECLARED_OFFLINE_DECISION' if execution_verified else 'INCOMPLETE_OFFLINE_PRIMITIVE_EXECUTION',
            ('Authenticated inputs, regenerated status, completed policy materializer and checker, matching replay'
             if execution_verified else
             'Authenticated inputs, regenerated status and matching replay; policy/checker execution is incomplete'),
            ['decision/materialized_required.json', 'decision/decision.json', 'replay/replay_receipt.json'],
            ('Native proof and semantic-review paths remain incomplete.' if execution_verified else
             'Exact decision replay does not establish completed policy/checker execution. Native proof and semantic-review paths remain incomplete.')),
        'endpoint_binding_status': axis(
            'VERIFIED_FOR_ARTIFACT_AND_DECISION_ENDPOINTS',
            'Exact manifest, external anchor, status, required set, decision and replay digests',
            ['bundle/manifest.signature.json', 'decision/decision.json', 'replay/replay_receipt.json'],
            'No endpoint representing mathematical acceptance is bound.'),
        'time_order_status': axis(
            time_state,
            time_scope,
            ['bundle/manifest.json'] + ['bundle/' + r['payload_path'] for r in snapshot['manifest']['receipts']],
            'Local collector timestamps are not independently trusted time attestations.'),
        'alternative_path_closure_status': axis(
            'PARTIAL_LOCAL_EMITTER_CONTROLS_OBSERVED' if controls else 'NOT_VERIFIED',
            'Offline command admission, stale-output, signature, policy and replay rejection controls',
            ['bundle/observations/authority_boundary_tests.json'],
            'Untrusted native builder write attempts, external publisher paths and complete runtime closure are not tested.'),
        'reconstruction_reproducibility_status': axis(
            'VERIFIED_DECISION_REPLAY_ONLY',
            'New verifier process reconstructed identical status, materialized required set and decision bytes',
            ['replay/replay_receipt.json'],
            'This is neither a second source-to-proof build nor an independent host reproduction.'),
        'causal_sufficiency_status': axis(
            'TEST_POLICY_CONTROL_OBSERVED_MATH_NOT_APPLICABLE' if control('test_positive_TEST_only_emission_and_exact_replay') else 'NOT_ASSESSED',
            'The TEST authority control passes all declared gates and observes TEST-only emission',
            ['bundle/observations/authority_boundary_tests.json'],
            'The TEST evaluator is controlled; production proof sufficiency and mathematical truth are not established.'),
        'causal_necessity_status': axis(
            'ONE_REQUIRED_GATE_MUTATION_OBSERVED_MATH_NOT_APPLICABLE' if control('test_real_pulse_blocks_false_gate_and_preserves_diagnostic') else 'NOT_ASSESSED',
            'A controlled TEST false-gate mutation causes the actual pinned PULSE checker to block',
            ['bundle/observations/authority_boundary_tests.json'],
            'This is a program-policy intervention, not a mathematical causal or independence claim.'),
    }
    return {'schema_version': 'qrh003_transition_observation_v1', 'artifact_role': 'post_decision_observation',
            'trust_domain': snapshot['manifest']['trust_domain'],
            'authority_effect': 'NONE', 'decision_sha256': digest,
            'evidence_manifest_sha256': snapshot['evidence_manifest_sha256'],
            'observer_source_sha256': sha256_file(Path(__file__).absolute()),
            'decision_result': d['result'], 'axes': axes,
            'logical_roots': {'bundle': str(bundle), 'decision': str(decision_dir), 'replay': str(replay_dir)},
            'earlier_status_is_not_modified': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'anchor', 'decision-dir', 'replay-dir', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--pulse-root', type=Path)
    args = parser.parse_args(argv)
    result = report(args.bundle, args.anchor, args.decision_dir, args.replay_dir, args.pulse_root)
    write_json(args.output, result)
    print(result['decision_result'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
