"""Synthetic v1 verification regressions; no native tokenizer/model/provider calls.

All host, runtime, token and historical artifact observations are explicit TEST
DOUBLES. Test-local monkeypatches replace historical pins only inside these tests;
there is no production flag, request field or CLI override for those pins.
"""
import base64
import copy
import io
import json
from pathlib import Path
import stat
import sys
import types
import zipfile

import pytest
from jsonschema import Draft202012Validator
from test_q3_native_capture_contract_v1 import C, ROOT, module, request
from test_q3_native_capture_protocol_v1 import effective_generation
import test_q3_native_capture_v0 as V0

K = module('check_q3_native_capture_v1')
H = K.H


def load_composite():
    import importlib.util
    spec = importlib.util.spec_from_file_location('synthetic_composite_check_v1',
                                                 ROOT / 'tools/check_q3_continuation_composite_v1.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    # Both functions still execute the real v1 validators; use the same test-local
    # historical pin namespace rather than a second imported contract instance.
    mod.K = K; mod.H = H; mod.C = K.C
    return mod


def archive(data):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, body in sorted(data.items()):
            info = zipfile.ZipInfo(name); info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED; z.writestr(info, body)
    return stream.getvalue()


def carrier(data, req, version='v1', status='complete'):
    result = {'record_type': 'q3_native_capture_result_' + version, 'mode': req['mode'],
        'status': status, 'error_code': None if status == 'complete' else 'TOKEN_LIMIT_TERMINATION',
        'source_commit': req['source_commit'], 'request_sha256': C.digest(data['request.json']),
        'inventory': {name: H.pin(body) for name, body in sorted(data.items())}, 'claims': dict(C.CLAIMS)}
    return archive({**data, 'result.json': C.encode(result)}), result


def mutate(data, name, callback):
    value = C.strict_json(data[name]); callback(value); data[name] = C.encode(value)


def _image_archive(history, outer_request_sha, controller_sha):
    binding = {'job_key': 'acquire', 'repository': C.REPOSITORY,
        'request_sha256': outer_request_sha, 'run_id': history['run_id'], 'run_attempt': 1,
        'source_commit': history['source_commit'], 'workflow': '.github/workflows/q3_reference_acquisition_v0.yml'}
    observation = {'environment': {'image_os': 'ubuntu24', 'image_version': 'synthetic-test-only'},
        'errors': [], 'worker': {'pid': 1234, 'start_ticks': 12, 'executable': '/synthetic/Runner.Worker'}}
    for name in ('imagedata', 'setup_info'):
        observation[name] = {'error': None, 'image': 'ubuntu-24.04', 'version': 'synthetic-test-only',
                             'sha256': 'e' * 64, 'size_bytes': 1}
    data = {}; previous = None
    for index, phase in enumerate(('initial', 'pre-sudo', 'root-entry')):
        data[phase + '.json'] = C.encode({'record_type': 'q3_runner_image_observation_v0',
            'authority_effect': 'none', 'binding': binding, 'observation': observation,
            'observed_at': f'2026-10-24T00:00:0{index}+00:00', 'observer_sha256': controller_sha,
            'phase': phase, 'previous_sha256': previous})
        previous = C.digest(data[phase + '.json'])
    data['comparison.json'] = C.encode({'record_type': 'q3_runner_image_comparison_v0',
        'authority_effect': 'none', 'binding': binding, 'capture_handoff_approved': False,
        'conflicts': [], 'errors': [], 'native_execution_started_at_comparison': False,
        'observer_sha256': controller_sha,
        'observation_sha256': {phase: C.digest(data[phase + '.json']) for phase in ('initial', 'pre-sudo', 'root-entry')},
        'status': 'consistent'})
    return archive(data)


def synthetic_history(monkeypatch):
    source, original, req = V0.evidence('capture', 'github-release-assets-v0')
    first = V0.FRAME[0]; task_id = first['task_id']; stem = 'calls/' + task_id
    generation = effective_generation()
    mutate(original, 'model-ready.json', lambda obj: obj.__setitem__('effective_generation', generation))
    mutate(original, 'subject.json', lambda obj: obj.__setitem__('model_ready_sha256', C.digest(original['model-ready.json'])))
    full = {**C.strict_json(original['subject.json'])['binding'], 'subject_sha256': C.digest(original['subject.json'])}
    mutate(original, 'bound.json', lambda obj: obj.__setitem__('binding', full))
    for suffix in ('.intent.json', '.ready.json', '.response.json'):
        mutate(original, stem + suffix, lambda obj: obj.__setitem__('binding', full))
    for suffix in ('.ready.json', '.response.json'):
        mutate(original, stem + suffix, lambda obj: obj.__setitem__('effective_generation', generation))
    mutate(original, stem + '.response.json', lambda obj: obj.update(new_token_ids=[4] * 256,
                                                                   stop_reason='token_limit'))
    old_terminal = C.strict_json(original['terminal.json'])
    old_terminal.update(complete=False, error_code='TOKEN_LIMIT_TERMINATION', attempted_calls=1,
                        stdout_eof=False, worker_exit_code=None, worker_exit_observed_ns=None, ended_at=None)
    old_terminal['occurrences'][0]['status'] = 'length_terminated'
    old_terminal['occurrences'][1:] = [{'task_id': t['task_id'], 'ordinal': t['ordinal'],
                                      'attempt': 1, 'status': 'not_started'} for t in V0.FRAME[1:]]
    original['terminal.json'] = C.encode(old_terminal)
    old_life = C.strict_json(original['lifecycle.json'])
    old_life.update(cleanup_complete=False, errors=['service_cleanup_unverified'], private_tree_removed=False,
                    services=old_life['services'][:2] + [None], timers=old_life['timers'][:1])
    original['lifecycle.json'] = C.encode(old_life)
    missing = ['token-check.json', 'decodecheck-sandbox.json', 'decodecheck-cleanup.json',
               'worker-cleanup.json', 'examples.jsonl', 'session-end.json']
    for name in list(original):
        if name in missing or (name.startswith('calls/') and not name.startswith(stem + '.')):
            del original[name]
    native_raw, native_result = carrier(original, req, 'v0', 'incomplete')
    native_receipt = {'record_type': 'q3_native_capture_receipt_v0', 'status': 'incomplete',
        'mode': 'capture', 'archive_sha256': C.digest(native_raw), 'archive_size_bytes': len(native_raw),
        'result_sha256': C.digest(C.encode(native_result)), 'request_sha256': C.digest(original['request.json']),
        'source_commit': req['source_commit'], 'token_map_sha256': C.digest(original['token-map.json']),
        'claims': dict(C.CLAIMS)}
    entry = {'capture_source_commit': req['source_commit'], 'native_request_utf8': original['request.json'].decode(),
             'native_request_sha256': C.digest(original['request.json']), 'handoff_source_files': {}}
    handoff = {'request.json': C.encode(entry), 'native/evidence.zip': native_raw,
               'native/receipt.json': C.encode(native_receipt),
               'native/failure.json': C.encode({'error_code': 'TOKEN_LIMIT_TERMINATION'})}
    bundle = {'status': 'incomplete', 'error_code': 'HANDOFF_NATIVE_INCOMPLETE',
              'inventory': {name: H.pin(body) for name, body in sorted(handoff.items())}}
    handoff['bundle.json'] = C.encode(bundle); handoff_raw = archive(handoff)
    receipt = {'archive_size_bytes': len(handoff_raw), 'archive_sha256': C.digest(handoff_raw),
        'bundle_sha256': C.digest(handoff['bundle.json']), 'status': 'incomplete',
        'source_commit': req['source_commit'], 'capture_run_id': '12345', 'run_attempt': 1,
        'entry_request_sha256': C.digest(handoff['request.json'])}
    outer = {'evidence.zip': handoff_raw, 'receipt.json': C.encode(receipt),
             'failure.json': C.encode({'error_code': 'HANDOFF_NATIVE_INCOMPLETE'})}
    outer_raw = archive(outer)
    plan = json.loads((ROOT / C.AMENDMENT_PATH).read_bytes()); history = plan['historical_capture']
    history.update(run_id='12345', source_commit=req['source_commit'], recorded_runner_image='synthetic-test-only')
    history['capture_artifact'].update(H.pin(outer_raw))
    image_raw = _image_archive(history, C.digest(handoff['request.json']), C.digest(source[V0.A.SELF]))
    history['runner_image_artifact'].update(H.pin(image_raw))
    history['outer_artifact_members'] = [{'member': name, **H.pin(body)} for name, body in outer.items()]
    history['handoff_members'] = [{'member': name, **H.pin(body)} for name, body in handoff.items()]
    history['native_members'] = [{'member': name, **H.pin(body)} for name, body in original.items() if not name.startswith('source/')]
    history['native_source_members'] = [{'member': 'source/' + name, **H.pin(body)} for name, body in source.items()]
    history['original_terminal_summary'] = {key: old_terminal[key] for key in history['original_terminal_summary']}
    history['retained_observation']['original_timing'] = {key: value for key, value in old_terminal['occurrences'][0].items()
                                                          if key.endswith('_ns')}
    monkeypatch.setattr(H.C, 'HISTORICAL_ARTIFACT_SHA256', C.digest(outer_raw))
    monkeypatch.setattr(H.C, 'HISTORICAL_ARTIFACT_SIZE', len(outer_raw))
    monkeypatch.setattr(H.C, 'HISTORICAL_NATIVE_SHA256', C.digest(native_raw))
    monkeypatch.setattr(H.C, 'HISTORICAL_NATIVE_SIZE', len(native_raw))
    monkeypatch.setattr(H.C, 'HISTORICAL_TOKEN_MAP_SHA256', C.digest(original['token-map.json']))
    monkeypatch.setattr(H.C, 'load_amendment', lambda root: copy.deepcopy(plan))
    return {'original': original, 'outer_raw': outer_raw, 'image_raw': image_raw, 'plan': plan,
            'history': history, 'old_request': req, 'native_raw': native_raw}


def synthetic_current(monkeypatch, mode='capture'):
    history = synthetic_history(monkeypatch)
    p = C.load_profile(ROOT)
    source = {name: (ROOT / name).read_bytes() for name in p['source_files']}
    data = {'source/' + name: body for name, body in source.items()}
    data.update(V0.installation_data(source))
    mutate(data, 'installation.json', lambda obj: obj.__setitem__('record_type', 'q3_native_installation_check_v1'))
    req = request(mode); req['source_commit'] = 'c' * 40
    mapping = C.strict_json(history['original']['token-map.json'])
    mapping.update(record_type='q3_token_map_v1', profile_sha256=C.PROFILE_SHA256)
    if mode == 'capture':
        req['approved_token_map_sha256'] = C.digest(C.encode(mapping)); req['historical_verification_sha256'] = 'f' * 64
    data['request.json'] = C.encode(req)
    platform = C.strict_json(history['original']['platform.json'])
    plane = {'run_id': '67890', 'run_attempt': 1, 'source_commit': req['source_commit'], 'repository': C.REPOSITORY,
             'repository_private': False, 'event': 'workflow_dispatch', 'workflow': C.WORKFLOW,
             'head_branch': 'main', 'actor': 'HKati', 'triggering_actor': 'HKati', 'clock_relation': 'not_verified'}
    data['platform.json'] = C.encode(platform); data['control-plane.json'] = C.encode(plane)
    old_history = history['history']
    run = {'id': 12345, 'run_attempt': 1, 'head_sha': history['old_request']['source_commit'],
           'head_branch': 'main', 'event': 'workflow_dispatch', 'status': 'completed', 'conclusion': 'failure',
           'actor': {'login': 'HKati'}, 'triggering_actor': {'login': 'HKati'},
           'path': '.github/workflows/q3_reference_acquisition_v0.yml'}
    jobs = {'total_count': 1, 'jobs': [{'id': old_history['job_id'], 'run_id': 12345, 'run_attempt': 1,
            'head_sha': run['head_sha'], 'status': 'completed', 'conclusion': 'failure'}]}
    def metadata(selected):
        return {'id': selected['artifact_id'], 'name': selected['name'], 'size_in_bytes': selected['size_bytes'],
                'digest': 'sha256:' + selected['sha256'], 'expired': False,
                'workflow_run': {'id': 12345, 'head_sha': run['head_sha'], 'head_branch': 'main',
                                 'repository_id': 1061766508, 'head_repository_id': 1061766508}}
    for stem, value in [('run', run), ('jobs', jobs), ('artifact', metadata(old_history['capture_artifact'])),
                         ('image-artifact', metadata(old_history['runner_image_artifact']))]:
        for suffix in ('before', 'after'):
            data['historical/' + stem + '.' + suffix + '.json'] = C.encode(value)
    data['historical/capture-artifact.zip'] = history['outer_raw']
    data['historical/runner-image-artifact.zip'] = history['image_raw']
    acquisition = {'record_type': 'q3_historical_acquisition_v1', 'current_binding': {},
        'selection': {'run_id': '12345', 'run_attempt': 1, 'job_id': old_history['job_id'],
                      'source_commit': run['head_sha'], 'artifact_id': old_history['capture_artifact']['artifact_id'],
                      'image_artifact_id': old_history['runner_image_artifact']['artifact_id']},
        'inventory': {name: H.pin(data[name]) for name in sorted(H.ACQUISITION_MEMBERS)}, 'claims': dict(C.CLAIMS)}
    def bind_request():
        data['request.json'] = C.encode(req)
        acquisition['current_binding'] = {'request_sha256': C.digest(data['request.json']),
            'source_commit': req['source_commit'], 'run_id': plane['run_id'], 'run_attempt': 1,
            'controller_sha256': C.digest(source[K.RUNTIME_CONTROLLER])}
        data['historical/current-acquisition.json'] = C.encode(acquisition)
    bind_request()
    context = H.verify_historical_static(source, data, checker=K)
    data['historical-verification.json'] = C.encode(H.expected_receipt(context))
    if mode == 'capture':
        req['historical_verification_sha256'] = C.digest(data['historical-verification.json']); bind_request()
    history_sb = V0.sandbox('decodecheck')
    history_sb.update(stage='historicalcheck', unit=history_sb['unit'].replace('-decodecheck.', '-historicalcheck.'))
    history_close = V0.closure('decodecheck'); history_close['unit'] = history_sb['unit']
    data['historicalcheck-sandbox.json'] = C.encode(history_sb)
    data['historicalcheck-cleanup.json'] = C.encode(history_close)
    transport = C.strict_json(history['original']['runtime-transport.json'])
    transport['binding'] = {'request_sha256': C.digest(data['request.json']), 'source_commit': req['source_commit'],
                            'run_id': plane['run_id'], 'run_attempt': 1,
                            'controller_sha256': C.digest(source[K.RUNTIME_CONTROLLER])}
    data['runtime-transport.json'] = C.encode(transport)
    pre = {'record_type': 'q3_native_prelaunch_v1', 'request': req, 'source_commit': req['source_commit'],
        'run_id': plane['run_id'], 'run_attempt': 1, 'source_files': {name: C.digest(body) for name, body in source.items()},
        'platform_sha256': C.digest(data['platform.json']), 'control_plane_sha256': C.digest(data['control-plane.json']),
        'installation_sha256': C.digest(data['installation.json']), 'runtime_transport_sha256': C.digest(data['runtime-transport.json']),
        'historical_verification_sha256': C.digest(data['historical-verification.json']),
        'historical_phase_cleanup_sha256': C.digest(data['historicalcheck-cleanup.json']),
        'historical_acquisition_sha256': C.digest(data['historical/current-acquisition.json']),
        'started_at': '2026-10-24T00:00:00+00:00', 'clock_relation': 'not_verified'}
    data['prelaunch.json'] = C.encode(pre)
    binding = {'prelaunch_sha256': C.digest(data['prelaunch.json']), 'source_commit': req['source_commit'],
               'run_id': plane['run_id'], 'run_attempt': 1}
    data['worker-ready.json'] = C.encode({'record_type': 'q3_worker_ready_v1', 'binding': binding, 'mode': mode})
    data['token-map.json'] = C.encode(mapping); map_sha = C.digest(data['token-map.json'])
    for row in mapping['rows']:
        data['tokens/' + row['task_id'] + '.json'] = C.encode({'record_type': 'q3_token_row_v1', 'binding': binding, 'row': row})
    data['token-map-end.json'] = C.encode({'record_type': 'q3_token_map_end_v1', 'binding': binding,
                                         'token_map_sha256': map_sha, 'task_count': 204})
    frame = C.task_frame(source, p); generation = effective_generation(); runtime = K.expected_runtime(p)
    full = binding; occurrences = []; timers = []; examples = []
    if mode == 'capture':
        data['model-ready.json'] = C.encode({'record_type': 'q3_model_ready_v1', 'binding': binding,
            'token_map_sha256': map_sha, 'effective_generation': generation, 'runtime': runtime})
        data['subject.json'] = C.encode({'record_type': 'q3_capture_subject_v1', 'binding': binding,
            'model_ready_sha256': C.digest(data['model-ready.json']), 'token_map_sha256': map_sha,
            'historical_verification_sha256': C.digest(data['historical-verification.json'])})
        full = {**binding, 'subject_sha256': C.digest(data['subject.json'])}
        data['bound.json'] = C.encode({'record_type': 'q3_bound_v1', 'binding': full})
    selected = C.continuation_frame(source, p) if mode == 'capture' else frame
    for task in selected:
        row = mapping['rows'][task['ordinal'] - 1]
        slot = {'task_id': task['task_id'], 'ordinal': task['ordinal'], 'attempt': 1}
        if mode == 'token-preflight':
            occurrences.append({**slot, 'status': 'not_requested'}); continue
        slot['continuation_ordinal'] = task['continuation_ordinal']
        stem = 'calls/' + task['task_id']; moment = task['ordinal'] * 100_000_000_000
        ready = {'record_type': 'q3_slot_ready_v1', 'binding': full, 'slot': slot, 'input_ids': row['input_ids'],
                 'effective_generation': generation, 'runtime': runtime}
        capped = task['continuation_ordinal'] % 2 == 1
        text = 'synthetic capped response' if capped else 'synthetic eos response'
        response = {**ready, 'record_type': 'q3_response_v1', 'new_token_ids': [4] * 256 if capped else [4, 2],
                    'text': text, 'text_utf8_base64': base64.b64encode(text.encode()).decode(),
                    'stop_reason': 'token_limit' if capped else 'eos'}
        data[stem + '.ready.json'] = C.encode(ready); data[stem + '.response.json'] = C.encode(response)
        data[stem + '.utf8'] = text.encode(); data[stem + '.intent.json'] = C.encode({**slot, 'binding': full, 'intent': 'before_GO'})
        occurrences.append({**slot, 'status': 'length_terminated' if capped else 'completed',
            'intent_saved_ns': moment, 'watchdog_arm_begin_ns': moment + 1, 'generation_start_ns': moment + 2,
            'generation_deadline_ns': moment + 2 + 60_000_000_000,
            'response_received_ns': moment + 3, 'watchdog_closed_ns': moment + 4})
        prefix = 'pulse-q3-' + 'a' * 24 + f"-call-{task['ordinal']:03d}"
        timers.append({'prefix': prefix, 'closure': {'units': [{'unit': prefix + '-watchdog' + suffix,
            'LoadState': 'not-found', 'ActiveState': 'inactive'} for suffix in ('.timer', '.service')], 'closed_ns': moment + 4}})
        examples.append({'example_id': task['task_id'], 'prompt': task['prompt'], 'response': text,
                         'context': task['context'], 'metadata': {'task_form': task['task_form']}})
    if mode == 'capture': data['examples.jsonl'] = b''.join(C.encode(item) for item in examples)
    data['session-end.json'] = C.encode({'record_type': 'q3_session_end_v1', 'binding': full,
                                        'completed_calls': 203 if mode == 'capture' else 0})
    data['terminal.json'] = C.encode({'record_type': 'q3_capture_terminal_v1', 'mode': mode, 'binding': binding,
        'complete': True, 'error_code': None, 'attempted_calls': 203 if mode == 'capture' else 0,
        'occurrences': occurrences, 'worker_exit_code': 0, 'stdout_eof': True,
        'worker_deadline_ns': 30_000_000_000_000, 'worker_exit_observed_ns': 29_000_000_000_000,
        'ended_at': '2026-10-24T00:30:00+00:00'})
    data['token-check.json'] = C.encode({'record_type': 'q3_native_token_check_v1',
        'request_sha256': C.digest(data['request.json']), 'prelaunch_sha256': C.digest(data['prelaunch.json']),
        'token_map_sha256': map_sha, 'checked_tasks': 204, 'checked_responses': 203 if mode == 'capture' else 0,
        'tokenization_reperformed': True, 'generation_executed': False,
        'historical_verification_sha256': C.digest(data['historical-verification.json']),
        'examples_sha256': C.digest(data['examples.jsonl']) if mode == 'capture' else None, 'claims': dict(C.CLAIMS)})
    data['input-check.json'] = C.encode({'record_type': 'q3_runtime_input_check_v1', 'archive_sha256': K.ARCHIVE_SHA,
        'archive_size': K.ARCHIVE_SIZE, 'member_count': 78, 'wheel_count': 30, 'claims': dict(C.CLAIMS)})
    services = []
    for stage in ('installer', 'installcheck', 'historicalcheck', 'captureworker' if mode == 'capture' else 'preflight', 'decodecheck'):
        if stage == 'historicalcheck': services.append(history_close); continue
        stem = 'worker' if stage in ('captureworker', 'preflight') else stage
        data[stem + '-sandbox.json'] = C.encode(V0.sandbox(stage))
        data[stem + '-cleanup.json'] = C.encode(V0.closure(stage)); services.append(V0.closure(stage))
    data['lifecycle.json'] = C.encode({'cleanup_complete': True, 'private_tree_removed': True,
                                      'errors': [], 'services': services, 'timers': timers})
    return source, data, req, history


@pytest.mark.parametrize('mode', ['token-preflight', 'capture'])
def test_complete_synthetic_v1_carrier(monkeypatch, mode):
    source, data, req, history = synthetic_current(monkeypatch, mode)
    result = K.validate_complete(source, data)
    assert result['complete'] is True and result['historical_verification_sha256'] == C.digest(data['historical-verification.json'])
    raw, record = carrier(data, req)
    assert K.check_carrier_bytes(raw, source, C.digest(raw), C.digest(data['request.json']), req['source_commit']) == result
    schema = json.loads((ROOT / 'schemas/metrics/q3_native_capture_result_v1.schema.json').read_bytes())
    Draft202012Validator.check_schema(schema); Draft202012Validator(schema).validate(record)
    for name in ('terminal', 'token_map', 'token_check'):
        member = {'terminal': 'terminal.json', 'token_map': 'token-map.json', 'token_check': 'token-check.json'}[name]
        Draft202012Validator(schema['$defs'][name]).validate(C.strict_json(data[member]))


@pytest.mark.parametrize('fault', [
    'missing_history', 'changed_history_zip', 'metadata_identity', 'receipt_promotion',
    'history_cleanup', 'history_prelaunch', 'copied_old_map', 'changed_token_row',
    'wrong_ordinal', 'wrong_continuation_ordinal', 'repeated_old_task', 'duplicate_task',
    'early_non_eos', 'embedded_eos', 'false_stop_reason', 'late_response',
    'previous_watchdog_open', 'missing_eof', 'nonzero_exit', 'cleanup_failed',
    'wrong_timer_name', 'partial_response', 'extra_call', 'changed_generation',
])
def test_rejects_changed_or_incomplete_synthetic_v1_evidence(monkeypatch, fault):
    source, data, req, _ = synthetic_current(monkeypatch)
    frame = C.continuation_frame(source, C.load_profile(source)); first = 'calls/' + frame[0]['task_id']
    if fault == 'missing_history': del data['historical-verification.json']
    elif fault == 'changed_history_zip': data['historical/capture-artifact.zip'] += b'x'
    elif fault == 'metadata_identity': mutate(data, 'historical/run.after.json', lambda x: x.__setitem__('head_sha', 'f' * 40))
    elif fault == 'receipt_promotion': mutate(data, 'historical-verification.json', lambda x: x.__setitem__('original_run_complete', True))
    elif fault == 'history_cleanup': mutate(data, 'historicalcheck-cleanup.json', lambda x: x.__setitem__('client_reaped', False))
    elif fault == 'history_prelaunch': mutate(data, 'prelaunch.json', lambda x: x.__setitem__('historical_phase_cleanup_sha256', '0' * 64))
    elif fault == 'copied_old_map': data['token-map.json'] = H.verify_historical_static(source, data, checker=K)['native']['token-map.json']
    elif fault == 'changed_token_row': mutate(data, 'token-map.json', lambda x: x['rows'][0]['input_ids'].append(4))
    elif fault == 'wrong_ordinal': mutate(data, 'terminal.json', lambda x: x['occurrences'][0].__setitem__('ordinal', 1))
    elif fault == 'wrong_continuation_ordinal': mutate(data, 'terminal.json', lambda x: x['occurrences'][0].__setitem__('continuation_ordinal', 2))
    elif fault == 'repeated_old_task': mutate(data, 'terminal.json', lambda x: x['occurrences'][0].__setitem__('task_id', C.HISTORICAL_TASK_ID))
    elif fault == 'duplicate_task': mutate(data, 'terminal.json', lambda x: x['occurrences'][1].__setitem__('task_id', x['occurrences'][0]['task_id']))
    elif fault == 'early_non_eos': mutate(data, first + '.response.json', lambda x: x.__setitem__('new_token_ids', [4]))
    elif fault == 'embedded_eos': mutate(data, first + '.response.json', lambda x: x['new_token_ids'].__setitem__(10, 2))
    elif fault == 'false_stop_reason': mutate(data, first + '.response.json', lambda x: x.__setitem__('stop_reason', 'eos'))
    elif fault == 'late_response': mutate(data, 'terminal.json', lambda x: x['occurrences'][0].__setitem__('response_received_ns', x['occurrences'][0]['generation_deadline_ns'] + 1))
    elif fault == 'previous_watchdog_open': mutate(data, 'terminal.json', lambda x: x['occurrences'][0].__setitem__('watchdog_closed_ns', x['occurrences'][1]['intent_saved_ns'] + 1))
    elif fault == 'missing_eof': mutate(data, 'terminal.json', lambda x: x.__setitem__('stdout_eof', False))
    elif fault == 'nonzero_exit': mutate(data, 'terminal.json', lambda x: x.__setitem__('worker_exit_code', 1))
    elif fault == 'cleanup_failed': mutate(data, 'lifecycle.json', lambda x: x.__setitem__('cleanup_complete', False))
    elif fault == 'wrong_timer_name': mutate(data, 'lifecycle.json', lambda x: x['timers'][0].__setitem__('prefix', 'pulse-q3-' + 'a' * 24 + '-call-001'))
    elif fault == 'partial_response': data[first + '.response.json'] = data[first + '.response.json'][:-10]
    elif fault == 'extra_call': data['calls/' + C.HISTORICAL_TASK_ID + '.utf8'] = b'extra generated response'
    elif fault == 'changed_generation': mutate(data, first + '.response.json', lambda x: x['effective_generation'].__setitem__('temperature', 0.5))
    with pytest.raises((ValueError, KeyError)):
        K.validate_complete(source, data)


def test_live_response_rejects_full_configuration_drift(monkeypatch):
    source, data, _, _ = synthetic_current(monkeypatch)
    task = C.continuation_frame(source, C.load_profile(source))[0]; stem = 'calls/' + task['task_id']
    response = C.strict_json(data[stem + '.response.json']); ready = C.strict_json(data[stem + '.ready.json'])
    assert K.check_live_response(response, ready, C.load_profile(source), ready['binding'], ready['slot'], ready['input_ids']) is False
    response['effective_generation']['temperature'] = ready['effective_generation']['temperature'] = 0.5
    with pytest.raises(ValueError, match='resolved_generation_identity'):
        K.check_live_response(response, ready, C.load_profile(source), ready['binding'], ready['slot'], ready['input_ids'])


def test_composite_preserves_both_sessions_and_exact_projection(monkeypatch):
    source, data, req, history = synthetic_current(monkeypatch); Q = load_composite()
    monkeypatch.setattr(K.C, 'HISTORICAL_ARTIFACT_SHA256', H.C.HISTORICAL_ARTIFACT_SHA256)
    monkeypatch.setattr(K.C, 'HISTORICAL_NATIVE_SHA256', H.C.HISTORICAL_NATIVE_SHA256)
    raw, _ = carrier(data, req); anchors = (C.digest(raw), C.digest(data['request.json']), req['source_commit'])
    manifest, examples = Q.build_composite(source, raw, *anchors)
    assert manifest['runtime_identity'] is None and manifest['all_contributing_sessions_complete'] is False
    assert [row['original_ordinal'] for row in manifest['rows']] == list(range(1, 205))
    assert [s['session_complete'] for s in manifest['source_sessions']] == [False, True]
    records = [C.strict_json(line) for line in examples.splitlines()]
    assert all(set(row) == {'example_id', 'prompt', 'response', 'context', 'metadata'} for row in records)
    assert records[0]['response'].encode() == history['original']['calls/' + C.HISTORICAL_TASK_ID + '.utf8']
    assert b''.join(C.encode(row) for row in records[1:]) == data['examples.jsonl']
    assert Q.check_composite(source, raw, C.encode(manifest), examples, *anchors)['complete_observation_coverage'] is True
    forged = copy.deepcopy(manifest); forged['source_sessions'][0]['session_complete'] = True
    with pytest.raises(ValueError, match='composite_reconstruction_mismatch'):
        Q.check_composite(source, raw, C.encode(forged), examples, *anchors)
    forged = copy.deepcopy(manifest); forged['rows'][1]['original_task_id'] = C.HISTORICAL_TASK_ID
    with pytest.raises(ValueError): Q.check_composite(source, raw, C.encode(forged), examples, *anchors)
    with pytest.raises(ValueError): Q.check_composite(source, raw, C.encode(manifest), examples + b'{}\n', *anchors)


def test_incomplete_continuation_cannot_be_composited(monkeypatch):
    source, data, req, _ = synthetic_current(monkeypatch); Q = load_composite()
    raw, _ = carrier(data, req, status='incomplete')
    with pytest.raises(ValueError, match='composite_requires_complete_continuation'):
        Q.build_composite(source, raw, C.digest(raw), C.digest(data['request.json']), req['source_commit'])


def test_history_receipt_stable_across_separate_current_modes(monkeypatch):
    _, preflight, _, _ = synthetic_current(monkeypatch, 'token-preflight')
    _, capture, _, _ = synthetic_current(monkeypatch, 'capture')
    assert preflight['request.json'] != capture['request.json']
    assert preflight['historical/current-acquisition.json'] != capture['historical/current-acquisition.json']
    assert preflight['historical-verification.json'] == capture['historical-verification.json']


@pytest.mark.parametrize('fault', [None, 'prompt', 'decode', 'generation', 'model_bytes'])
def test_historical_native_verification_with_only_synthetic_tokenizer(monkeypatch, tmp_path, fault):
    """Execute a fake tokenizer seam, never the installed native tokenizer/model."""
    source, data, _, _ = synthetic_current(monkeypatch, 'token-preflight')
    context = H.verify_historical_static(source, data, checker=K)
    payload = b'synthetic tokenizer input\n'; model = tmp_path / 'model'; model.mkdir()
    (model / 'tokenizer.json').write_bytes(payload)
    context['model_map'] = {'files': [{'path': 'model/tokenizer.json', 'size': len(payload), 'sha256': C.digest(payload)}]}
    if fault == 'model_bytes': (model / 'tokenizer.json').write_bytes(b'changed')
    monkeypatch.setattr(H, 'verify_historical_static', lambda *args, **kwargs: context)
    observations = {'prompts': 0, 'decodes': 0, 'loads': 0}
    class SyntheticTokenizer:
        is_fast = True; bos_token_id = 1; eos_token_id = 2; pad_token_id = 2
        def apply_chat_template(self, messages, **kwargs):
            index = observations['prompts']; observations['prompts'] += 1
            assert messages == context['frame'][index]['messages']
            assert kwargs == {'tokenize': True, 'add_generation_prompt': True, 'truncation': False}
            result = list(context['token_map']['rows'][index]['input_ids'])
            return result + [4] if fault == 'prompt' else result
        def decode(self, ids, **kwargs):
            observations['decodes'] += 1
            assert ids == context['response']['new_token_ids']
            assert kwargs == {'skip_special_tokens': True, 'clean_up_tokenization_spaces': False}
            return 'wrong decode' if fault == 'decode' else context['response']['text']
    class SyntheticLoader:
        @staticmethod
        def from_pretrained(path, **kwargs):
            observations['loads'] += 1
            assert Path(path) == model
            assert kwargs == {'local_files_only': True, 'trust_remote_code': False, 'use_fast': True}
            return SyntheticTokenizer()
    class SyntheticGeneration:
        def __init__(self, **kwargs):
            assert kwargs == {**context['profile']['generation'], 'disable_compile': True}
        def to_dict(self):
            result = effective_generation()
            if fault == 'generation': result['temperature'] = 0.5
            return result
    fake = types.ModuleType('transformers'); fake.__version__ = '4.57.6'
    fake.__file__ = str(Path(sys.prefix) / 'synthetic-transformers/__init__.py')
    fake.AutoTokenizer = SyntheticLoader; fake.GenerationConfig = SyntheticGeneration
    monkeypatch.setitem(sys.modules, 'transformers', fake)
    if fault is None:
        receipt = H.verify_historical_live(source, tmp_path, data, checker=K)
        assert observations == {'prompts': 204, 'decodes': 1, 'loads': 1}
        assert receipt['checked_prompt_rows'] == 204 and receipt['checked_historical_responses'] == 1
        assert receipt['generation_executed'] is False and receipt['original_worker_cleanup_verified'] is False
    else:
        with pytest.raises(ValueError): H.verify_historical_live(source, tmp_path, data, checker=K)
        assert observations['decodes'] <= 1 and observations['prompts'] <= 204


def test_native_partial_protocol_cannot_skip_completion(monkeypatch):
    source, data, _, _ = synthetic_current(monkeypatch)
    with pytest.raises(ValueError, match='partial_native_protocol_not_supported'):
        K.validate_protocol(source, data, require_complete=False)
