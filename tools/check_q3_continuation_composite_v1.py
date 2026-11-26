#!/usr/bin/env python3
"""Independently reconstruct a 1+203 Q3 composite from selected original bytes.

This offline adapter executes no model or tokenizer and creates no labels, score,
or release authority. Coverage never upgrades the historical session's status.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('q3_composite_native_checker_v1',
    ROOT / 'PULSE_safe_pack_v0/tools/check_q3_native_capture_v1.py')
K = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(K)
C = K.C
H = K.H


def _row(task, response, native, source_kind, carrier, verification_sha256):
    stem = 'calls/' + task['task_id']
    binding = response['binding']
    return {
        'original_task_id': task['task_id'], 'original_ordinal': task['ordinal'],
        'attempt': 1, 'source_kind': source_kind, 'source_repository': C.REPOSITORY,
        'source_commit': binding['source_commit'], 'run_id': binding['run_id'],
        'run_attempt': binding['run_attempt'], 'artifact_id_or_selected_original_carrier': carrier,
        'carrier_sha256': carrier['native_archive_sha256'],
        'response_member': stem + '.response.json',
        'response_sha256': C.digest(native[stem + '.response.json']),
        'text_member': stem + '.utf8', 'text_sha256': C.digest(native[stem + '.utf8']),
        'stop_reason': response['stop_reason'], 'subject_binding': binding,
        'verification_receipt_sha256': verification_sha256,
    }


def build_composite(source, continuation_raw, expected_archive_sha256,
                    expected_request_sha256, expected_source_commit):
    """Return a freshly derived manifest and five-field JSONL, never raw rewriting."""
    checked = K.check_carrier_bytes(continuation_raw, source, expected_archive_sha256,
                                    expected_request_sha256, expected_source_commit)
    C.require(checked['complete'] is True and checked['mode'] == 'capture', 'composite_requires_complete_continuation')
    archive = H.archive_members(continuation_raw)
    data = {name: body for name, body in archive.items() if name != 'result.json'}
    request, token_map, continuation_examples = K.validate_protocol(source, data)
    historical = H.verify_historical_static(source, data, checker=K)
    expected_history = H.expected_receipt(historical)
    C.require(data['historical-verification.json'] == C.encode(expected_history), 'composite_historical_admission')
    history_sha = C.digest(data['historical-verification.json'])
    C.require(history_sha == request['historical_verification_sha256'], 'composite_selected_history')
    p = C.load_profile(source); frame = C.task_frame(source, p)
    old = historical['native']; old_response = historical['response']; new_pre = C.strict_json(data['prelaunch.json'])
    old_carrier = {
        'artifact_id': C.HISTORICAL_ARTIFACT_ID, 'artifact_sha256': C.HISTORICAL_ARTIFACT_SHA256,
        'native_archive_sha256': C.HISTORICAL_NATIVE_SHA256,
    }
    new_carrier = {
        'artifact_id': None, 'artifact_sha256': None,
        'native_archive_sha256': expected_archive_sha256,
    }
    rows = [_row(frame[0], old_response, old, 'historical_incomplete_session', old_carrier, history_sha)]
    examples = [{'example_id': frame[0]['task_id'], 'prompt': frame[0]['prompt'],
                 'response': old_response['text'], 'context': frame[0]['context'],
                 'metadata': {'task_form': frame[0]['task_form']}}]
    new_check_sha = C.digest(C.encode(checked))
    for task in frame[1:]:
        response = C.strict_json(data['calls/' + task['task_id'] + '.response.json'])
        rows.append(_row(task, response, data, 'complete_continuation_session', new_carrier, new_check_sha))
        examples.append({'example_id': task['task_id'], 'prompt': task['prompt'],
            'response': response['text'], 'context': task['context'], 'metadata': {'task_form': task['task_form']}})
    C.require(len(rows) == 204 and len({row['original_task_id'] for row in rows}) == 204
              and [row['original_task_id'] for row in rows] == [task['task_id'] for task in frame]
              and [row['original_ordinal'] for row in rows] == list(range(1, 205))
              and all(row['attempt'] == 1 for row in rows), 'composite_exact_coverage')
    C.require(all(row['source_kind'] == 'complete_continuation_session' for row in rows[1:])
              and all(row['original_task_id'] != C.HISTORICAL_TASK_ID for row in rows[1:]),
              'composite_disjoint_partition')
    lines = [C.encode(example) for example in examples]
    C.require(b''.join(lines[1:]) == continuation_examples == data['examples.jsonl'],
              'composite_continuation_projection')
    projection = b''.join(lines)
    old_pre = C.strict_json(old['prelaunch.json'])
    manifest = {
        'record_type': 'q3_continuation_composite_v1',
        'amendment_sha256': C.AMENDMENT_SHA256,
        'status': 'complete_observation_coverage',
        'observation_count': 204, 'historical_observation_count': 1, 'continuation_observation_count': 203,
        'runtime_identity': None, 'all_contributing_sessions_complete': False,
        'single_completed_204_call_session_claimed': False,
        'historical_verification': expected_history,
        'historical_verification_sha256': history_sha,
        'continuation_verification': checked,
        'continuation_verification_sha256': new_check_sha,
        'continuation_carrier': H.pin(continuation_raw),
        'source_sessions': [
            {'source_kind': 'historical_incomplete_session', 'repository': C.REPOSITORY,
             'source_commit': old_pre['source_commit'], 'run_id': old_pre['run_id'], 'run_attempt': 1,
             'subject_sha256': C.digest(old['subject.json']), 'platform_sha256': C.digest(old['platform.json']),
             'native_archive_sha256': C.HISTORICAL_NATIVE_SHA256, 'session_complete': False,
             'worker_exit_verified': False, 'worker_cleanup_verified': False},
            {'source_kind': 'complete_continuation_session', 'repository': C.REPOSITORY,
             'source_commit': new_pre['source_commit'], 'run_id': new_pre['run_id'], 'run_attempt': 1,
             'subject_sha256': C.digest(data['subject.json']), 'platform_sha256': C.digest(data['platform.json']),
             'native_archive_sha256': expected_archive_sha256, 'session_complete': True,
             'worker_exit_verified': True, 'worker_cleanup_verified': True},
        ],
        'rows': rows,
        'projection': {
            'format': 'q3_archived_examples_five_fields_v0',
            'serialization': 'UTF-8 JSON; sorted keys; compact separators; one LF per row; original order.',
            **H.pin(projection), 'lines': [
                {'original_ordinal': ordinal, 'example_id': example['example_id'], **H.pin(line)}
                for ordinal, (example, line) in enumerate(zip(examples, lines), 1)],
        },
        'labels_created': False, 'metric_recomputed': False,
        'native_origin_reacquired': False, 'tokenization_reperformed': False,
        'claims': dict(C.CLAIMS),
    }
    return manifest, projection


def check_composite(source, continuation_raw, manifest_raw, examples_raw,
                    expected_archive_sha256, expected_request_sha256, expected_source_commit):
    manifest, examples = build_composite(source, continuation_raw, expected_archive_sha256,
                                        expected_request_sha256, expected_source_commit)
    C.require(manifest_raw == C.encode(manifest) and examples_raw == examples, 'composite_reconstruction_mismatch')
    return {'record_type': 'q3_continuation_composite_check_v1', 'complete_observation_coverage': True,
            'manifest_sha256': C.digest(manifest_raw), 'examples_sha256': C.digest(examples_raw),
            'observation_count': 204, 'all_contributing_sessions_complete': False,
            'labels_created': False, 'metric_recomputed': False, 'claims': dict(C.CLAIMS)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True, choices=['build', 'check'])
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--continuation-archive', type=Path, required=True)
    parser.add_argument('--expected-archive-sha256', required=True)
    parser.add_argument('--expected-request-sha256', required=True)
    parser.add_argument('--expected-source-commit', required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--examples', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        C.source_snapshot(args.source_root, args.expected_source_commit, C.load_profile(args.source_root))
        raw = C.safe_read(args.continuation_archive, 256 * 1024 * 1024)
        anchors = (args.expected_archive_sha256, args.expected_request_sha256, args.expected_source_commit)
        if args.phase == 'build':
            manifest, examples = build_composite(args.source_root, raw, *anchors)
            C.require(not args.manifest.exists() and not args.examples.exists(), 'composite_output_exists')
            C.write_new(args.examples, examples, 0o644)
            C.write_new(args.manifest, C.encode(manifest), 0o644)
        else:
            C.require(args.output is not None, 'composite_check_output_required')
            report = check_composite(args.source_root, raw, C.safe_read(args.manifest),
                                     C.safe_read(args.examples), *anchors)
            C.write_new(args.output, C.encode(report), 0o644)
        return 0
    except Exception:
        print('Q3 composite reconstruction rejected; no measurement claimed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
