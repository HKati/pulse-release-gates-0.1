#!/usr/bin/env python3
"""Verify the one pinned historical Q3 observation; never execute a model.

Static reconstruction is deliberately separate from new native token verification.
The original v0 session and its unverified cleanup remain incomplete permanently.
No archived Python helper is imported or executed.
"""
from __future__ import annotations

import argparse
import base64
import datetime
import importlib.util
import io
from pathlib import Path
import re
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = 'PULSE_safe_pack_v0/tools/q3_native_capture_contract_v1.py'
CHECKER = 'PULSE_safe_pack_v0/tools/check_q3_native_capture_v1.py'
SELF = 'tools/check_q3_historical_observation_v1.py'
CONTROLLER = 'PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v1.py'
OLD_CONTROLLER = 'PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v0.py'
OLD_PROFILE = 'PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json'
MODEL_MAP = 'PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json'
_spec = importlib.util.spec_from_file_location('historical_contract_v1', ROOT / CONTRACT)
C = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(C)
check = C.require
sha = C.digest
encode = C.encode
parse = C.strict_json
ACQUISITION_MEMBERS = frozenset({
    'historical/' + name for name in (
        'run.before.json', 'run.after.json', 'jobs.before.json', 'jobs.after.json',
        'artifact.before.json', 'artifact.after.json', 'image-artifact.before.json',
        'image-artifact.after.json', 'capture-artifact.zip', 'runner-image-artifact.zip')})


def _checker():
    spec = importlib.util.spec_from_file_location('historical_native_checker_v1', ROOT / CHECKER)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def pin(raw):
    return {'size_bytes': len(raw), 'sha256': sha(raw)}


def equal(actual, expected, code):
    check(encode(actual) == encode(expected), code)


def archive_members(raw):
    check(type(raw) is bytes and 0 < len(raw) <= 256 * 1024 * 1024, 'historical_archive_bound')
    out = {}; total = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        check(0 < len(infos) <= 2000, 'historical_archive_count')
        for info in infos:
            C.relative(info.filename)
            check(info.filename not in out and not info.is_dir() and not info.flag_bits & 1
                  and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
                  and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                  'historical_archive_member_type')
            C.integer(info.file_size, 0, 16 * 1024 * 1024)
            total += info.file_size
            check(total <= 256 * 1024 * 1024, 'historical_archive_total')
            out[info.filename] = archive.read(info)
    return out


def check_inventory(data, record_name):
    record = parse(data[record_name])
    equal(record['inventory'], {name: pin(raw) for name, raw in sorted(data.items())
                                if name != record_name}, 'historical_inventory')
    return record


def _member_pins(rows, data, code):
    check(type(rows) is list and len({r['member'] for r in rows}) == len(rows), code)
    for row in rows:
        C.fields(row, {'member', 'size_bytes', 'sha256'})
        check(row['member'] in data, code)
        equal(pin(data[row['member']]), {k: row[k] for k in ('size_bytes', 'sha256')}, code)


def _stamp(value, code):
    check(type(value) is str and re.fullmatch(
        r'[0-9]{4}-[0-9]{2}-[0-9]{2}T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{6})?\+00:00', value), code)
    return datetime.datetime.fromisoformat(value)


def _run_identity(value, history):
    check(value['id'] == int(history['run_id']) and value['run_attempt'] == 1
          and value['head_sha'] == history['source_commit'] and value['head_branch'] == 'main'
          and value['event'] == 'workflow_dispatch' and value['status'] == 'completed'
          and value['conclusion'] == 'failure' and value['actor']['login'] == 'HKati'
          and value['triggering_actor']['login'] == 'HKati'
          and value['path'] == '.github/workflows/q3_reference_acquisition_v0.yml',
          'historical_run_identity')
    return {key: value[key] for key in ('id', 'run_attempt', 'head_sha', 'head_branch', 'event',
                                       'status', 'conclusion', 'path')}


def _job_identity(value, history):
    check(type(value['total_count']) is int and value['total_count'] == 1
          and type(value['jobs']) is list and len(value['jobs']) == 1, 'historical_job_extent')
    job = value['jobs'][0]
    check(job['id'] == history['job_id'] and job['run_id'] == int(history['run_id'])
          and job['run_attempt'] == 1 and job['head_sha'] == history['source_commit']
          and job['status'] == 'completed' and job['conclusion'] == 'failure', 'historical_job_identity')
    return {key: job[key] for key in ('id', 'run_id', 'run_attempt', 'head_sha', 'status', 'conclusion')}


def _artifact_identity(value, selected, history):
    run = value['workflow_run']
    check(value['id'] == selected['artifact_id'] and value['name'] == selected['name']
          and value['size_in_bytes'] == selected['size_bytes']
          and value['digest'] == 'sha256:' + selected['sha256'] and value['expired'] is False
          and run['id'] == int(history['run_id']) and run['head_sha'] == history['source_commit']
          and run['head_branch'] == 'main' and run['repository_id'] == 1061766508
          and run['head_repository_id'] == 1061766508, 'historical_artifact_identity')
    return {key: value[key] for key in ('id', 'name', 'size_in_bytes', 'digest', 'expired', 'workflow_run')}


def verify_acquisition(source, data, p, request, history):
    check(ACQUISITION_MEMBERS <= set(data), 'historical_acquisition_members')
    acquisition = parse(data['historical/current-acquisition.json'])
    C.fields(acquisition, {'record_type', 'current_binding', 'selection', 'inventory', 'claims'})
    check(acquisition['record_type'] == 'q3_historical_acquisition_v1', 'historical_acquisition_type')
    plane = parse(data['control-plane.json'])
    equal(acquisition['current_binding'], {
        'request_sha256': sha(data['request.json']), 'source_commit': request['source_commit'],
        'run_id': plane['run_id'], 'run_attempt': 1,
        'controller_sha256': sha(C.source_read(source, CONTROLLER))}, 'historical_current_binding')
    check(plane['source_commit'] == request['source_commit'] and plane['run_attempt'] == 1
          and plane['repository'] == C.REPOSITORY and plane['repository_private'] is False
          and plane['head_branch'] == 'main' and plane['event'] == 'workflow_dispatch'
          and plane['workflow'] == C.WORKFLOW and plane['actor'] == plane['triggering_actor'] == 'HKati',
          'historical_current_control_plane')
    equal(acquisition['selection'], {
        'run_id': history['run_id'], 'run_attempt': 1, 'job_id': history['job_id'],
        'source_commit': history['source_commit'],
        'artifact_id': history['capture_artifact']['artifact_id'],
        'image_artifact_id': history['runner_image_artifact']['artifact_id']}, 'historical_selection')
    equal(acquisition['inventory'], {name: pin(data[name]) for name in sorted(ACQUISITION_MEMBERS)},
          'historical_acquisition_inventory')
    equal(acquisition['claims'], C.CLAIMS, 'historical_acquisition_claims')
    for stem, projector in (
        ('run', lambda x: _run_identity(x, history)),
        ('jobs', lambda x: _job_identity(x, history)),
        ('artifact', lambda x: _artifact_identity(x, history['capture_artifact'], history)),
        ('image-artifact', lambda x: _artifact_identity(x, history['runner_image_artifact'], history)),
    ):
        before = projector(parse(data['historical/' + stem + '.before.json']))
        after = projector(parse(data['historical/' + stem + '.after.json']))
        equal(before, after, 'historical_metadata_identity_changed')
    for name, selected in [('capture-artifact.zip', history['capture_artifact']),
                           ('runner-image-artifact.zip', history['runner_image_artifact'])]:
        equal(pin(data['historical/' + name]), {k: selected[k] for k in ('size_bytes', 'sha256')},
              'historical_selected_archive')
    return acquisition


def verify_original_image(raw, history, outer_request_sha, native):
    data = archive_members(raw)
    check(set(data) == {'initial.json', 'pre-sudo.json', 'root-entry.json', 'comparison.json'},
          'historical_image_scope')
    binding = {'job_key': 'acquire', 'repository': C.REPOSITORY, 'request_sha256': outer_request_sha,
               'run_id': history['run_id'], 'run_attempt': 1, 'source_commit': history['source_commit'],
               'workflow': '.github/workflows/q3_reference_acquisition_v0.yml'}
    observer = sha(native['source/' + OLD_CONTROLLER]); previous = None; last_stamp = None
    prior_observation = None
    for stage in ('initial', 'pre-sudo', 'root-entry'):
        record = parse(data[stage + '.json'])
        C.fields(record, {'record_type', 'authority_effect', 'binding', 'observation', 'observed_at',
                          'observer_sha256', 'phase', 'previous_sha256'})
        equal(record['binding'], binding, 'historical_image_binding')
        check(record['record_type'] == 'q3_runner_image_observation_v0' and record['phase'] == stage
              and record['authority_effect'] == 'none' and record['observer_sha256'] == observer
              and record['previous_sha256'] == previous, 'historical_image_chain')
        stamp = _stamp(record['observed_at'], 'historical_image_time')
        check(last_stamp is None or stamp >= last_stamp, 'historical_image_time_order')
        observation = record['observation']
        check(observation['errors'] == [] and observation['environment'] == {
            'image_os': 'ubuntu24', 'image_version': history['recorded_runner_image']}, 'historical_image_environment')
        for name in ('imagedata', 'setup_info'):
            item = observation[name]
            check(item['error'] is None and item['image'] == 'ubuntu-24.04'
                  and item['version'] == history['recorded_runner_image']
                  and C.sha256_string(item['sha256']) and type(item['size_bytes']) is int
                  and item['size_bytes'] > 0, 'historical_image_observation')
        worker = observation['worker']
        check(type(worker['pid']) is int and worker['pid'] > 1
              and type(worker['start_ticks']) is int and worker['start_ticks'] > 0
              and type(worker['executable']) is str and worker['executable'].endswith('/Runner.Worker'),
              'historical_image_worker')
        if prior_observation is not None:
            equal(observation, prior_observation, 'historical_image_observation_changed')
        previous = sha(data[stage + '.json']); last_stamp = stamp; prior_observation = observation
    comparison = parse(data['comparison.json'])
    equal(comparison, {'record_type': 'q3_runner_image_comparison_v0', 'authority_effect': 'none',
        'binding': binding, 'capture_handoff_approved': False, 'conflicts': [], 'errors': [],
        'native_execution_started_at_comparison': False, 'observer_sha256': observer,
        'observation_sha256': {name: sha(data[name + '.json']) for name in ('initial', 'pre-sudo', 'root-entry')},
        'status': 'consistent'}, 'historical_image_comparison')


def _old_response(response, ready, task, row, binding, model_ready, p):
    slot = {'task_id': task['task_id'], 'ordinal': 1, 'attempt': 1}
    ready_expected = {'record_type': 'q3_slot_ready_v0', 'binding': binding, 'slot': slot,
        'input_ids': row['input_ids'], 'effective_generation': model_ready['effective_generation'],
        'runtime': model_ready['runtime']}
    equal(ready, ready_expected, 'historical_ready_frame')
    C.fields(response, set(ready_expected) | {'new_token_ids', 'text', 'text_utf8_base64', 'stop_reason'})
    for key in ready_expected:
        equal(response[key], 'q3_response_v0' if key == 'record_type' else ready_expected[key],
              'historical_response_binding')
    ids = response['new_token_ids']
    check(type(ids) is list and len(ids) == 256 and all(type(i) is int and 0 <= i < 49152 for i in ids)
          and 2 not in ids and response['stop_reason'] == 'token_limit', 'historical_response_termination')
    text = response['text']
    check(type(text) is str and len(text.encode()) <= p['limits']['max_response_utf8_bytes'],
          'historical_response_text_bound')
    check(response['text_utf8_base64'] == base64.b64encode(text.encode()).decode('ascii'),
          'historical_response_text_encoding')


def _closure(data, stem, stage, checker):
    sandbox = parse(data[stem + '-sandbox.json']); checker.verify_sandbox(sandbox, stage)
    closed = parse(data[stem + '-cleanup.json'])
    C.fields(closed, {'unit', 'launch_attempted', 'properties', 'cgroup_empty_or_removed', 'client_reaped'})
    props = closed['properties']; C.fields(props, {'LoadState', 'ActiveState', 'ControlGroup'})
    check(closed['unit'] == sandbox['unit'] and closed['launch_attempted'] is True
          and closed['cgroup_empty_or_removed'] is True and closed['client_reaped'] is True
          and props['LoadState'] in ('loaded', 'not-found') and props['ActiveState'] == 'inactive'
          and props['ControlGroup'] in ('', '/system.slice/' + closed['unit']), 'historical_service_closure')
    return closed


def verify_current_historical_closure(data, *, checker=None):
    checker = _checker() if checker is None else checker
    return _closure(data, 'historicalcheck', 'historicalcheck', checker)


def verify_historical_static(source, data, *, checker=None):
    """Reconstruct the selected singleton, not merely its archive inventory."""
    checker = _checker() if checker is None else checker
    p = C.load_profile(source); plan = C.load_amendment(source); history = plan['historical_capture']
    request = C.validate_request(data['request.json'], p)
    source_hashes = {}
    for name in p['source_files']:
        raw = C.source_read(source, name)
        check(data['source/' + name] == raw, 'historical_current_source_binding')
        source_hashes[name] = sha(raw)
    verify_acquisition(source, data, p, request, history)
    raw = data['historical/capture-artifact.zip']
    check(len(raw) == C.HISTORICAL_ARTIFACT_SIZE and sha(raw) == C.HISTORICAL_ARTIFACT_SHA256,
          'historical_fixed_artifact')
    outer = archive_members(raw)
    check(set(outer) == {'evidence.zip', 'receipt.json', 'failure.json'}, 'historical_outer_scope')
    _member_pins(history['outer_artifact_members'], outer, 'historical_outer_pins')
    receipt = parse(outer['receipt.json']); handoff = archive_members(outer['evidence.zip'])
    bundle = check_inventory(handoff, 'bundle.json')
    equal(pin(outer['evidence.zip']), {'size_bytes': receipt['archive_size_bytes'],
                                    'sha256': receipt['archive_sha256']}, 'historical_handoff_receipt')
    check(receipt['bundle_sha256'] == sha(handoff['bundle.json']) and receipt['status'] == 'incomplete'
          and receipt['source_commit'] == history['source_commit']
          and receipt['capture_run_id'] == history['run_id'] and receipt['run_attempt'] == 1,
          'historical_handoff_binding')
    _member_pins(history['handoff_members'], handoff, 'historical_handoff_pins')
    entry = parse(handoff['request.json'])
    check(receipt['entry_request_sha256'] == sha(handoff['request.json'])
          and entry['capture_source_commit'] == history['source_commit'], 'historical_entry_request')
    for name, descriptor in entry['handoff_source_files'].items():
        body = handoff['handoff-source/' + name]
        equal(pin(body), {k: descriptor[k] for k in ('size_bytes', 'sha256')}, 'historical_handoff_source')
        check(C.blob_id(body) == descriptor['git_blob_sha1'], 'historical_handoff_blob')
    check(bundle['status'] == 'incomplete' and bundle['error_code'] == 'HANDOFF_NATIVE_INCOMPLETE',
          'historical_handoff_status')
    native_raw = handoff['native/evidence.zip']; native = archive_members(native_raw)
    check(len(native_raw) == C.HISTORICAL_NATIVE_SIZE and sha(native_raw) == C.HISTORICAL_NATIVE_SHA256,
          'historical_fixed_native')
    nr = parse(handoff['native/receipt.json']); result = check_inventory(native, 'result.json')
    equal(pin(native_raw), {'size_bytes': nr['archive_size_bytes'], 'sha256': nr['archive_sha256']},
          'historical_native_receipt')
    check(nr['result_sha256'] == sha(native['result.json']) and nr['status'] == result['status'] == 'incomplete'
          and result['error_code'] == 'TOKEN_LIMIT_TERMINATION', 'historical_native_result')
    _member_pins(history['native_members'], native, 'historical_native_pins')
    _member_pins(history['native_source_members'], native, 'historical_native_source_pins')
    old_source = {name[7:]: body for name, body in native.items() if name.startswith('source/')}
    old_p = parse(old_source[OLD_PROFILE]); old_request = parse(native['request.json'])
    check(sha(old_source[OLD_PROFILE]) == C.HISTORICAL_PROFILE_SHA256
          and old_request['profile_sha256'] == C.HISTORICAL_PROFILE_SHA256
          and old_request['source_commit'] == history['source_commit'] and old_request['mode'] == 'capture'
          and old_request['authorization'] == 'AUTHORIZE_204_SINGLE_ATTEMPT_CALLS_AND_30_DAY_ACTIONS_RAW_RETENTION'
          and old_request['new_spend_authorized'] == 0, 'historical_request_profile')
    equal(old_request['limits'], old_p['limits'], 'historical_request_limits')
    equal(old_request['claims'], C.CLAIMS, 'historical_request_claims')
    check(entry['native_request_utf8'].encode() == native['request.json']
          and entry['native_request_sha256'] == nr['request_sha256'] == sha(native['request.json'])
          and result['request_sha256'] == nr['request_sha256'], 'historical_native_request_binding')
    check(set(old_source) == set(old_p['source_files']), 'historical_source_extent')
    for name, digest in old_p['fixed_inputs'].items():
        check(sha(old_source[name]) == digest and C.source_read(source, name) == old_source[name],
              'historical_stimulus_or_runtime_drift')
    for name in ('model_repository', 'model_revision', 'seed', 'system_message', 'generation'):
        equal(old_p[name], p[name], 'historical_model_generation_drift')
    frame = C.task_frame(source, p)
    pre = parse(native['prelaunch.json']); plane = parse(native['control-plane.json'])
    platform = parse(native['platform.json'])
    equal(pre['request'], old_request, 'historical_prelaunch_request')
    check(pre['record_type'] == 'q3_native_prelaunch_v0' and pre['source_commit'] == history['source_commit']
          and pre['run_id'] == history['run_id'] and pre['run_attempt'] == 1
          and pre['clock_relation'] == plane['clock_relation'] == 'not_verified', 'historical_prelaunch_identity')
    _stamp(pre['started_at'], 'historical_started_at')
    equal(pre['source_files'], {name: sha(body) for name, body in old_source.items()}, 'historical_source_binding')
    for name, key in [('platform.json', 'platform_sha256'), ('control-plane.json', 'control_plane_sha256'),
                      ('installation.json', 'installation_sha256')]:
        check(pre[key] == sha(native[name]), 'historical_prelaunch_records')
    check(plane['run_id'] == history['run_id'] and plane['run_attempt'] == 1
          and plane['source_commit'] == history['source_commit'] and plane['repository'] == C.REPOSITORY
          and plane['repository_private'] is False and plane['event'] == 'workflow_dispatch'
          and plane['workflow'] == '.github/workflows/q3_reference_acquisition_v0.yml'
          and plane['head_branch'] == 'main' and plane['actor'] == plane['triggering_actor'] == 'HKati',
          'historical_control_plane')
    for key, expected in old_p['platform'].items():
        equal(platform[key], expected, 'historical_platform_contract')
    check(platform['runner_image'] == history['recorded_runner_image']
          and C.sha256_string(platform['bootstrap_python_sha256']), 'historical_platform_identity')
    checker.validate_runtime_transport(old_source, native, old_request, pre, controller_path=OLD_CONTROLLER)
    checker.validate_installation_record(native, record_type='q3_native_installation_check_v0')
    equal(parse(native['input-check.json']), {
        'record_type': 'q3_runtime_input_check_v0', 'archive_sha256': old_p['runtime_archive']['sha256'],
        'archive_size': old_p['runtime_archive']['size_bytes'], 'member_count': 78, 'wheel_count': 30,
        'claims': dict(C.CLAIMS)}, 'historical_runtime_input_check')
    for stem, stage in [('installer', 'installer'), ('installcheck', 'installcheck'), ('worker', 'captureworker')]:
        checker.verify_sandbox(parse(native[stem + '-sandbox.json']), stage)
    binding = {'prelaunch_sha256': sha(native['prelaunch.json']), 'source_commit': history['source_commit'],
               'run_id': history['run_id'], 'run_attempt': 1}
    equal(parse(native['worker-ready.json']), {'record_type': 'q3_worker_ready_v0', 'binding': binding,
                                             'mode': 'capture'}, 'historical_worker_ready')
    token_map = parse(native['token-map.json'])
    C.fields(token_map, {'record_type', 'profile_sha256', 'model_revision', 'task_file_sha256', 'rows'})
    check(sha(native['token-map.json']) == C.HISTORICAL_TOKEN_MAP_SHA256
          and native['token-map.json'] == encode(token_map) and token_map['record_type'] == 'q3_token_map_v0'
          and token_map['profile_sha256'] == C.HISTORICAL_PROFILE_SHA256
          and token_map['model_revision'] == p['model_revision']
          and token_map['task_file_sha256'] == p['fixed_inputs'][C.FRAME + 'TASKS_DRAFT.jsonl']
          and old_request['approved_token_map_sha256'] == C.HISTORICAL_TOKEN_MAP_SHA256
          and len(token_map['rows']) == 204, 'historical_token_map')
    for task, row in zip(frame, token_map['rows']):
        C.fields(row, {'task_id', 'ordinal', 'input_ids', 'messages_sha256', 'logical_request_sha256'})
        check(row['task_id'] == task['task_id'] and type(row['ordinal']) is int and row['ordinal'] == task['ordinal']
              and row['messages_sha256'] == sha(encode(task['messages']))
              and row['logical_request_sha256'] == sha(task['logical_request_text'].encode()), 'historical_token_input')
        ids = row['input_ids']
        check(type(ids) is list and 1 <= len(ids) <= p['limits']['max_prompt_tokens']
              and all(type(i) is int and 0 <= i < 49152 for i in ids), 'historical_prompt_token_bound')
        equal(parse(native['tokens/' + task['task_id'] + '.json']), {
            'record_type': 'q3_token_row_v0', 'binding': binding, 'row': row}, 'historical_original_token_row')
    equal(parse(native['token-map-end.json']), {'record_type': 'q3_token_map_end_v0', 'binding': binding,
        'task_count': 204, 'token_map_sha256': C.HISTORICAL_TOKEN_MAP_SHA256}, 'historical_token_end')
    mr = parse(native['model-ready.json'])
    check(mr['record_type'] == 'q3_model_ready_v0' and mr['binding'] == binding
          and mr['token_map_sha256'] == C.HISTORICAL_TOKEN_MAP_SHA256
          and sha(encode(mr['effective_generation'])) == p['effective_generation_sha256'], 'historical_model_ready')
    equal(mr['runtime'], p['runtime'], 'historical_runtime_configuration')
    equal(parse(native['subject.json']), {'record_type': 'q3_capture_subject_v0', 'binding': binding,
        'model_ready_sha256': sha(native['model-ready.json']), 'token_map_sha256': C.HISTORICAL_TOKEN_MAP_SHA256},
        'historical_subject')
    full_binding = {**binding, 'subject_sha256': sha(native['subject.json'])}
    equal(parse(native['bound.json']), {'record_type': 'q3_bound_v0', 'binding': full_binding}, 'historical_bound')
    first = frame[0]; stem = 'calls/' + first['task_id']; response = parse(native[stem + '.response.json'])
    _old_response(response, parse(native[stem + '.ready.json']), first, token_map['rows'][0], full_binding, mr, p)
    equal(parse(native[stem + '.intent.json']), {'task_id': first['task_id'], 'ordinal': 1, 'attempt': 1,
        'binding': full_binding, 'intent': 'before_GO'}, 'historical_intent')
    check(native[stem + '.utf8'] == response['text'].encode(), 'historical_original_text')
    terminal = parse(native['terminal.json']); occurrences = terminal['occurrences']
    equal({key: terminal[key] for key in history['original_terminal_summary']},
          history['original_terminal_summary'], 'historical_terminal_summary')
    check(terminal['record_type'] == 'q3_capture_terminal_v0' and terminal['mode'] == 'capture'
          and terminal['binding'] == binding and len(occurrences) == 204, 'historical_terminal_binding')
    for task, occurrence in zip(frame, occurrences):
        identity = {'task_id': task['task_id'], 'ordinal': task['ordinal'], 'attempt': 1}
        if task['ordinal'] == 1:
            equal(occurrence, {**identity, 'status': 'length_terminated',
                **history['retained_observation']['original_timing']}, 'historical_first_occurrence')
        else:
            equal(occurrence, {**identity, 'status': 'not_started'}, 'historical_unstarted_suffix')
    check({name for name in native if name.startswith('calls/')} == {
        stem + suffix for suffix in ('.intent.json', '.ready.json', '.response.json', '.utf8')}, 'historical_call_inventory')
    timing = occurrences[0]
    for key in history['retained_observation']['original_timing']:
        C.integer(timing[key], 1, 2**63 - 1)
    check(timing['intent_saved_ns'] <= timing['watchdog_arm_begin_ns'] <= timing['generation_start_ns']
          <= timing['response_received_ns'] <= timing['generation_deadline_ns'] <= terminal['worker_deadline_ns']
          and timing['generation_deadline_ns'] - timing['generation_start_ns'] == 60 * 1000000000
          and timing['response_received_ns'] <= timing['watchdog_closed_ns'], 'historical_call_timing')
    life = parse(native['lifecycle.json'])
    C.fields(life, {'cleanup_complete', 'errors', 'services', 'timers', 'private_tree_removed'})
    check(life['cleanup_complete'] is False and life['private_tree_removed'] is False
          and life['errors'] == ['service_cleanup_unverified']
          and len(life['services']) == 3 and life['services'][2] is None, 'historical_cleanup_disposition')
    for index, stage in enumerate(('installer', 'installcheck')):
        equal(life['services'][index], _closure(native, stage, stage, checker), 'historical_earlier_service_cleanup')
    check(len(life['timers']) == 1, 'historical_watchdog_count')
    worker_unit = parse(native['worker-sandbox.json'])['unit']
    prefix = worker_unit.rsplit('-', 1)[0] + '-call-001'
    equal(life['timers'][0], {'prefix': prefix, 'closure': {
        'closed_ns': timing['watchdog_closed_ns'], 'units': [
            {'unit': prefix + '-watchdog' + suffix, 'LoadState': 'not-found', 'ActiveState': 'inactive'}
            for suffix in ('.timer', '.service')]}}, 'historical_watchdog_closure')
    check(not set(history['missing_original_native_members']) & set(native), 'historical_absent_verification')
    verify_original_image(data['historical/runner-image-artifact.zip'], history, sha(handoff['request.json']), native)
    # Current dependencies are independently installed before this phase. Their
    # per-run observations stay in the current carrier, outside the stable receipt.
    checker.validate_installation_record(data)
    model_map = parse(C.source_read(source, MODEL_MAP))
    return {'profile': p, 'request': request, 'plan': plan, 'history': history, 'native': native,
            'outer': outer, 'handoff': handoff, 'frame': frame, 'token_map': token_map,
            'response': response, 'source_hashes': source_hashes, 'model_map': model_map}


def expected_receipt(context):
    """Deterministic receipt shape; only live verification may publish this claim."""
    native = context['native']; history = context['history']; task = C.HISTORICAL_TASK_ID
    return {
        'record_type': 'q3_historical_observation_verification_v1',
        'amendment_sha256': C.AMENDMENT_SHA256,
        'verifier_source_commit': context['request']['source_commit'],
        'verifier_profile_sha256': C.PROFILE_SHA256,
        'verifier_source_files': context['source_hashes'],
        'historical_artifact_id': C.HISTORICAL_ARTIFACT_ID,
        'historical_artifact_sha256': C.HISTORICAL_ARTIFACT_SHA256,
        'historical_native_sha256': C.HISTORICAL_NATIVE_SHA256,
        'historical_run_id': history['run_id'], 'historical_run_attempt': 1,
        'historical_source_commit': history['source_commit'],
        'historical_request_sha256': sha(native['request.json']),
        'historical_subject_sha256': sha(native['subject.json']),
        'historical_token_map_sha256': sha(native['token-map.json']),
        'historical_response_sha256': sha(native['calls/' + task + '.response.json']),
        'historical_text_sha256': sha(native['calls/' + task + '.utf8']),
        'historical_terminal_sha256': sha(native['terminal.json']),
        'historical_lifecycle_sha256': sha(native['lifecycle.json']),
        'runtime_archive_sha256': context['profile']['runtime_archive']['sha256'],
        'model_files': context['model_map']['files'],
        'checked_prompt_rows': 204, 'checked_historical_responses': 1,
        'tokenization_reperformed': True, 'generation_executed': False,
        'historical_observation_admitted': True,
        'original_run_complete': False, 'original_worker_exit_verified': False,
        'original_worker_cleanup_verified': False, 'original_private_tree_removal_verified': False,
        'native_origin_reacquired': False, 'claims': dict(C.CLAIMS),
    }


def verify_historical_live(source, bundle, data, *, checker=None):
    """Fresh isolated tokenizer verification: 204 prompts and one saved response."""
    context = verify_historical_static(source, data, checker=checker)
    files = context['model_map']['files']
    check({item.name for item in (bundle / 'model').iterdir()} == {Path(row['path']).name for row in files},
          'historical_tokenizer_scope')
    for row in files:
        raw = C.safe_read(bundle / C.relative(row['path']), 512 * 1024 * 1024)
        check(len(raw) == row['size'] and sha(raw) == row['sha256'], 'historical_tokenizer_bytes')
    import transformers
    from transformers import AutoTokenizer, GenerationConfig
    check(transformers.__version__ == '4.57.6'
          and Path(transformers.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()),
          'historical_tokenizer_runtime')
    tokenizer = AutoTokenizer.from_pretrained(str(bundle / 'model'), local_files_only=True,
                                             trust_remote_code=False, use_fast=True)
    check(tokenizer.is_fast and (tokenizer.bos_token_id, tokenizer.eos_token_id, tokenizer.pad_token_id) == (1, 2, 2),
          'historical_tokenizer_configuration')
    generation = GenerationConfig(**context['profile']['generation'], disable_compile=True).to_dict()
    check(sha(encode(generation)) == context['profile']['effective_generation_sha256'],
          'historical_effective_generation')
    for task, row in zip(context['frame'], context['token_map']['rows']):
        ids = tokenizer.apply_chat_template(task['messages'], tokenize=True, add_generation_prompt=True,
                                           truncation=False)
        equal(ids, row['input_ids'], 'historical_prompt_token_mismatch')
    text = tokenizer.decode(context['response']['new_token_ids'], skip_special_tokens=True,
                            clean_up_tokenization_spaces=False)
    check(type(text) is str and text == context['response']['text']
          and text.encode() == context['native']['calls/' + C.HISTORICAL_TASK_ID + '.utf8'],
          'historical_native_decode_mismatch')
    return expected_receipt(context)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True, choices=['verify-tokens'])
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        checker = _checker()
        result = verify_historical_live(args.source_root, args.bundle,
                                        checker.read_evidence(args.evidence), checker=checker)
        C.write_new(args.output, encode(result), 0o644)
        return 0
    except Exception:
        print('Q3 historical verification rejected; no admission receipt claimed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
