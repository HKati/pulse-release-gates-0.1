"""Synthetic v1 request/frame tests; no native tokenizer, model or dispatch."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket

import pytest
from jsonschema import Draft202012Validator, ValidationError


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'PULSE_safe_pack_v0/tools'


def module(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


C = module('q3_native_capture_contract_v1')


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def reject(*args, **kwargs):
        raise AssertionError('synthetic test attempted network')
    monkeypatch.setattr(socket, 'create_connection', reject)
    monkeypatch.setattr(socket.socket, 'connect', reject)


def request(mode='token-preflight'):
    p = C.load_profile(ROOT)
    return {
        'record_type': 'q3_native_capture_request_v1', 'mode': mode,
        'repository': C.REPOSITORY, 'source_commit': 'a' * 40,
        'profile_sha256': C.PROFILE_SHA256, 'amendment_sha256': C.AMENDMENT_SHA256,
        'task_file_sha256': p['fixed_inputs'][C.FRAME + 'TASKS_DRAFT.jsonl'],
        'authorization': C.AUTHORIZATIONS[mode],
        'approved_token_map_sha256': 'b' * 64 if mode == 'capture' else None,
        'historical_verification_sha256': 'c' * 64 if mode == 'capture' else None,
        'limits': copy.deepcopy(p['limits']), 'claims': dict(C.CLAIMS),
        'new_spend_authorized': 0,
    }


def schema():
    return json.loads((ROOT / 'schemas/metrics/q3_native_capture_request_v1.schema.json').read_bytes())


@pytest.mark.parametrize('mode', ['token-preflight', 'capture'])
def test_closed_v1_request_matches_its_schema(mode):
    p = C.load_profile(ROOT)
    value = request(mode)
    definition = schema()
    Draft202012Validator.check_schema(definition)
    Draft202012Validator(definition).validate(value)
    assert C.validate_request(C.encode(value), p) == value
    assert value['limits']['max_attempts'] == 203
    assert value['limits']['aggregate_max_attempts'] == 204
    assert value['limits']['external_per_call_watchdog_seconds'] == 65


@pytest.mark.parametrize('fault', [
    'v0_request', 'old_authorization', 'old_map', 'missing_historical_receipt',
    'malformed_historical_receipt', 'amendment', 'profile', 'frame',
    'subset', 'historical_locator', 'budget', 'new_call_count', 'aggregate_count',
    'retry', 'warmup', 'claim', 'spend', 'mode',
])
def test_capture_cannot_reinterpret_v0_or_override_the_accepted_plan(fault):
    value = request('capture')
    if fault == 'v0_request':
        value['record_type'] = 'q3_native_capture_request_v0'
    elif fault == 'old_authorization':
        value['authorization'] = 'AUTHORIZE_204_SINGLE_ATTEMPT_CALLS_AND_30_DAY_ACTIONS_RAW_RETENTION'
    elif fault == 'old_map':
        value['approved_token_map_sha256'] = C.HISTORICAL_TOKEN_MAP_SHA256
    elif fault == 'missing_historical_receipt':
        value['historical_verification_sha256'] = None
    elif fault == 'malformed_historical_receipt':
        value['historical_verification_sha256'] = 'accepted'
    elif fault == 'amendment':
        value['amendment_sha256'] = '0' * 64
    elif fault == 'profile':
        value['profile_sha256'] = C.HISTORICAL_PROFILE_SHA256
    elif fault == 'frame':
        value['task_file_sha256'] = '0' * 64
    elif fault == 'subset':
        value['task_ids'] = ['Q3P2-098-L']
    elif fault == 'historical_locator':
        value['historical_archive_url'] = 'https://example.invalid/replacement.zip'
    elif fault == 'budget':
        value['limits']['max_new_tokens'] = 512
    elif fault == 'new_call_count':
        value['limits']['max_attempts'] = 204
    elif fault == 'aggregate_count':
        value['limits']['aggregate_max_attempts'] = 205
    elif fault == 'retry':
        value['limits']['automatic_retries'] = 1
    elif fault == 'warmup':
        value['limits']['warmup_or_diagnostic_generation_calls'] = 1
    elif fault == 'claim':
        value['claims']['production_gate_eligible'] = True
    elif fault == 'spend':
        value['new_spend_authorized'] = 1
    elif fault == 'mode':
        value['mode'] = 'resume'
    with pytest.raises(ValueError):
        C.validate_request(C.encode(value), C.load_profile(ROOT))
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(value)


@pytest.mark.parametrize('field', ['approved_token_map_sha256', 'historical_verification_sha256'])
def test_preflight_cannot_carry_capture_approval(field):
    value = request()
    value[field] = 'b' * 64
    with pytest.raises(ValueError, match='PREFLIGHT_IS_NOT_CAPTURE'):
        C.validate_request(C.encode(value), C.load_profile(ROOT))
    with pytest.raises(ValidationError):
        Draft202012Validator(schema()).validate(value)


@pytest.mark.parametrize('field,value', [
    ('new_spend_authorized', False), ('new_spend_authorized', 0.0),
])
def test_numeric_authorization_fields_are_not_truthiness(field, value):
    r = request()
    r[field] = value
    with pytest.raises(ValueError):
        C.validate_request(C.encode(r), C.load_profile(ROOT))


def test_mutated_profile_cannot_authorize_correspondingly_mutated_limits():
    p = C.load_profile(ROOT)
    p['limits']['max_attempts'] = 204
    r = request('capture')
    r['limits'] = copy.deepcopy(p['limits'])
    with pytest.raises(ValueError, match='UNSUPPORTED_PROFILE_VALUE'):
        C.validate_request(C.encode(r), p)


def test_full_frame_and_only_supported_suffix_match_frozen_occurrence_plan():
    p = C.load_profile(ROOT)
    plan = C.load_amendment(ROOT)
    full = C.task_frame(ROOT, p)
    suffix = C.continuation_frame(ROOT, p)
    assert len(full) == 204 and len(suffix) == 203
    assert [t['task_id'] for t in full] == [o['task_id'] for o in plan['selection']['occurrences']]
    assert [t['ordinal'] for t in full] == list(range(1, 205))
    assert [t['ordinal'] for t in suffix] == list(range(2, 205))
    assert [t['continuation_ordinal'] for t in suffix] == list(range(1, 204))
    assert suffix[0]['task_id'] == 'Q3P2-043-A'
    assert suffix[-1]['task_id'] == 'Q3P2-063-L'
    assert C.HISTORICAL_TASK_ID not in {t['task_id'] for t in suffix}
    assert all(t['attempt'] == 1 for t in full)
    assert all({k: v for k, v in s.items() if k != 'continuation_ordinal'} == t
               for s, t in zip(suffix, full[1:]))
    assert C.digest(C.encode([t['task_id'] for t in suffix])) == C.CONTINUATION_TASK_IDS_SHA256


@pytest.mark.parametrize('path', [C.AMENDMENT_PATH, C.FRAME + 'TASK_ORDER.json',
                                 C.FRAME + 'TASKS_DRAFT.jsonl', C.FRAME + 'COMMON_INSTRUCTIONS.txt'])
def test_fixed_plan_and_stimulus_changes_reject_before_request_construction(path):
    p = C.load_profile(ROOT)
    source = {name: (ROOT / name).read_bytes() for name in p['fixed_inputs']}
    source[C.PROFILE] = (ROOT / C.PROFILE).read_bytes()
    assert C.task_frame(source, p) == C.task_frame(ROOT, p)
    source[path] += b'\n'
    with pytest.raises(ValueError):
        C.task_frame(source, p)


def test_profile_binds_all_new_execution_components_without_rewriting_v0():
    p = C.load_profile(ROOT)
    required = {
        C.PROFILE, C.WORKFLOW, C.AMENDMENT_PATH,
        'PULSE_safe_pack_v0/tools/q3_native_capture_contract_v1.py',
        'PULSE_safe_pack_v0/tools/run_q3_reference_subject_v1.py',
        'PULSE_safe_pack_v0/tools/q3_native_runtime_v1.py',
        'PULSE_safe_pack_v0/tools/acquire_q3_reference_inputs_v1.py',
        'PULSE_safe_pack_v0/tools/check_q3_native_capture_v1.py',
        'tools/check_q3_historical_observation_v1.py',
        'tools/check_q3_continuation_composite_v1.py',
        'tools/acquire_q3_external_postflight_v1.py',
        'tools/check_q3_external_postflight_v1.py',
        'tools/q3_capture_handoff_v2.py',
        'schemas/metrics/q3_native_capture_request_v1.schema.json',
        'schemas/metrics/q3_native_capture_result_v1.schema.json',
        'schemas/metrics/q3_capture_handoff_request_v2.schema.json',
    }
    assert required <= set(p['source_files'])
    assert p['source_files'] == sorted(set(p['source_files']))
    old = json.loads((ROOT / 'PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json').read_bytes())
    assert set(old['source_files']) <= set(p['source_files'])
    assert p['generation'] == old['generation']
    assert p['runtime_archive'] == old['runtime_archive']
    assert hashlib.sha256((ROOT / 'PULSE_safe_pack_v0/profiles/q3_native_capture_v0.json').read_bytes()).hexdigest() == C.HISTORICAL_PROFILE_SHA256


def test_constructor_preserves_separate_capture_anchors_and_never_dispatches(monkeypatch):
    seen = []
    monkeypatch.setattr(C, 'source_snapshot', lambda root, commit, p: seen.append((root, commit)) or {})
    raw = C.make_request(ROOT, 'a' * 40, 'capture', C.AUTHORIZATIONS['capture'], 'b' * 64, 'c' * 64)
    r = C.validate_request(raw, C.load_profile(ROOT))
    assert seen == [(ROOT, 'a' * 40)]
    assert r['approved_token_map_sha256'] == 'b' * 64
    assert r['historical_verification_sha256'] == 'c' * 64
    assert r['amendment_sha256'] == C.AMENDMENT_SHA256


def test_source_snapshot_compares_every_v1_path_to_selected_git_blob(tmp_path, monkeypatch):
    p = C.load_profile(ROOT)
    originals = {}
    for name in p['source_files']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        originals[name] = ('synthetic inert source: ' + name + '\n').encode()
        target.write_bytes(originals[name])
    calls = []
    def git(root, args):
        calls.append(args)
        if args == ['rev-parse', '--verify', 'HEAD']:
            return b'a' * 40 + b'\n'
        assert args[:2] == ['cat-file', 'blob']
        assert args[2].startswith('a' * 40 + ':')
        return originals[args[2].split(':', 1)[1]]
    monkeypatch.setattr(C, 'git_bytes', git)
    assert C.source_snapshot(tmp_path, 'a' * 40, p) == originals
    assert len(calls) == 1 + len(p['source_files'])
    changed = 'tools/check_q3_historical_observation_v1.py'
    (tmp_path / changed).write_bytes(originals[changed] + b'changed')
    with pytest.raises(ValueError, match='DIRTY_SOURCE'):
        C.source_snapshot(tmp_path, 'a' * 40, p)
