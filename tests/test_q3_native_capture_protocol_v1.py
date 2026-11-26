"""Explicitly synthetic 204-token/203-generation protocol tests.

No real tokenizer, model, downloaded package, native service or workflow runs.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import io
import json
import types

import pytest

from test_q3_native_capture_contract_v1 import ROOT, TOOLS, C, module, offline, request


W = module('run_q3_reference_subject_v1')
P = C.load_profile(ROOT)
FRAME = C.task_frame(ROOT, P)


def effective_generation():
    return json.loads((ROOT / 'tests/fixtures/q3_continuation_v1/effective-generation.json').read_bytes())


class Tokenizer:
    def __init__(self, length=7):
        self.length = length
        self.calls = []

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs == dict(tokenize=True, add_generation_prompt=True, truncation=False)
        self.calls.append(copy.deepcopy(messages))
        return [] if self.length == 0 else [1] + [4] * (self.length - 1)

    def decode(self, ids, **kwargs):
        assert kwargs == dict(skip_special_tokens=True, clean_up_tokenization_spaces=False)
        return '' if ids == [2] else 'synthetic response'


class Tensor:
    def __init__(self, rows):
        self.rows = copy.deepcopy(rows)
        self.shape = (len(rows), len(rows[0]))

    def __getitem__(self, index):
        return types.SimpleNamespace(tolist=lambda: list(self.rows[index]))


class Torch:
    long = 'synthetic-long'

    def __init__(self):
        self.tensors = []
        self.seeds = []

    def tensor(self, rows, **kwargs):
        assert kwargs == dict(dtype=self.long, device='cpu')
        value = Tensor(rows)
        self.tensors.append(value)
        return value

    def ones_like(self, tensor):
        return Tensor([[1] * tensor.shape[1]])

    def manual_seed(self, seed):
        self.seeds.append(seed)

    def inference_mode(self):
        return contextlib.nullcontext()


class Config:
    def __init__(self, **kwargs):
        self.value = effective_generation()
        self.value.update(kwargs)

    def to_dict(self):
        return copy.deepcopy(self.value)


class Model:
    def __init__(self, new=None):
        self.new = [4, 2] if new is None else new
        self.calls = []

    def generate(self, **kwargs):
        assert set(kwargs) == {'input_ids', 'attention_mask', 'generation_config', 'use_model_defaults'}
        assert kwargs['use_model_defaults'] is False
        self.calls.append(kwargs)
        new = self.new(len(self.calls)) if callable(self.new) else self.new
        return Tensor([kwargs['input_ids'][0].tolist() + list(new)])


def commands(rows):
    for row in rows:
        yield ('PREPARE ' + row['task_id'] + '\n').encode()
        yield ('GENERATE ' + row['task_id'] + '\n').encode()
    yield b'FINISH\n'


def session(new=None, change_commands=None, change_map=None, effective=None, tokenizer=None):
    tok = tokenizer or Tokenizer()
    mapping = W.tokenize_frame(tok, FRAME, P)
    if change_map:
        change_map(mapping)
    command_list = list(commands(mapping['rows'][1:]))
    if change_commands:
        change_commands(command_list)
    incoming = iter(command_list)
    model = Model(new)
    torch = Torch()
    wire = []
    args = (model, tok, torch, Config,
            effective if effective is not None else effective_generation(),
            copy.deepcopy(P['runtime']), mapping, P,
            {'explicitly_synthetic_binding': True}, lambda: next(incoming, b''), wire.append)
    return args, model, torch, wire, mapping


def test_tokenization_covers_original_204_before_generation_and_keeps_old_ordinals():
    tok = Tokenizer()
    mapping = W.tokenize_frame(tok, FRAME, P)
    assert mapping['record_type'] == 'q3_token_map_v1'
    assert mapping['profile_sha256'] == C.PROFILE_SHA256 != C.HISTORICAL_PROFILE_SHA256
    assert len(tok.calls) == len(mapping['rows']) == 204
    assert tok.calls == [task['messages'] for task in FRAME]
    assert [row['ordinal'] for row in mapping['rows']] == list(range(1, 205))
    assert mapping['rows'][0]['task_id'] == C.HISTORICAL_TASK_ID
    assert C.digest(C.encode(mapping)) != C.HISTORICAL_TOKEN_MAP_SHA256


@pytest.mark.parametrize('frame', [FRAME[1:], FRAME[:-1], [FRAME[1], FRAME[0], *FRAME[2:]]])
def test_preflight_cannot_tokenize_a_selected_subset_or_reordered_frame(frame):
    tok = Tokenizer()
    with pytest.raises(ValueError, match='TOKENIZE_FULL_FRAME'):
        W.tokenize_frame(tok, frame, P)
    assert tok.calls == []


@pytest.mark.parametrize('length', [0, 7937, 8192])
def test_overflow_rejects_without_prompt_truncation(length):
    tok = Tokenizer(length)
    with pytest.raises(ValueError, match='PROMPT_TOKENS'):
        W.tokenize_frame(tok, FRAME, P)


@pytest.mark.parametrize('ids', [[True], [49152], [-1], [1.0], None])
def test_non_token_values_rejected(ids):
    tok = Tokenizer()
    tok.apply_chat_template = lambda *args, **kwargs: ids
    with pytest.raises(ValueError, match='PROMPT_TOKENS'):
        W.tokenize_frame(tok, FRAME, P)


@pytest.mark.parametrize('pattern', ['eos', 'first_cap', 'all_cap', 'mixed'])
def test_exact_203_suffix_continues_after_complete_caps_without_first_task_regeneration(pattern):
    def new(index):
        if pattern == 'all_cap' or pattern == 'first_cap' and index == 1 or pattern == 'mixed' and index % 3 == 1:
            return [4] * 256
        return [4, 2]
    args, model, torch, wire, mapping = session(new=new)
    W.capture_session(*args)
    records = [C.strict_json(raw) for raw in wire]
    responses = [r for r in records if r['record_type'] == 'q3_response_v1']
    assert len(model.calls) == len(torch.tensors) == len(responses) == 203
    assert len({id(t) for t in torch.tensors}) == 203
    assert len({id(call['generation_config']) for call in model.calls}) == 203
    assert torch.seeds == [1729] * 203
    assert [r['slot']['task_id'] for r in responses] == [row['task_id'] for row in mapping['rows'][1:]]
    assert [r['slot']['ordinal'] for r in responses] == list(range(2, 205))
    assert [r['slot']['continuation_ordinal'] for r in responses] == list(range(1, 204))
    assert all(r['slot']['attempt'] == 1 for r in responses)
    assert C.HISTORICAL_TASK_ID not in {r['slot']['task_id'] for r in responses}
    assert records[-1] == {'record_type': 'q3_session_end_v1',
                           'binding': {'explicitly_synthetic_binding': True}, 'completed_calls': 203}
    assert len(records) == 407
    for index, response in enumerate(responses, 1):
        assert response['new_token_ids'] == new(index)
        assert response['stop_reason'] == ('token_limit' if new(index)[-1] != 2 else 'eos')


@pytest.mark.parametrize('fault', [
    'v0_map', 'old_profile', 'missing_first', 'missing_last', 'duplicate',
    'reordered', 'wrong_ordinal', 'bool_ordinal', 'invalid_input_ids',
])
def test_bad_full_map_cannot_start_any_generation(fault):
    def change(mapping):
        if fault == 'v0_map':
            mapping['record_type'] = 'q3_token_map_v0'
        elif fault == 'old_profile':
            mapping['profile_sha256'] = C.HISTORICAL_PROFILE_SHA256
        elif fault == 'missing_first':
            mapping['rows'].pop(0)
        elif fault == 'missing_last':
            mapping['rows'].pop()
        elif fault == 'duplicate':
            mapping['rows'][3] = copy.deepcopy(mapping['rows'][2])
        elif fault == 'reordered':
            mapping['rows'][1], mapping['rows'][2] = mapping['rows'][2], mapping['rows'][1]
        elif fault == 'wrong_ordinal':
            mapping['rows'][1]['ordinal'] = 1
        elif fault == 'bool_ordinal':
            mapping['rows'][0]['ordinal'] = True
        elif fault == 'invalid_input_ids':
            mapping['rows'][203]['input_ids'] = [True]
    args, model, torch, wire, mapping = session(change_map=change)
    with pytest.raises(ValueError):
        W.capture_session(*args)
    assert model.calls == torch.tensors == wire == []


@pytest.mark.parametrize('fault', ['historical_prepare', 'early_generate', 'missing_go',
                                  'repeated_generate', 'missing_finish'])
def test_missing_or_reordered_supervisor_commands_never_trigger_retries(fault):
    def change(cmds):
        if fault == 'historical_prepare':
            cmds[0] = b'PREPARE Q3P2-098-L\n'
        elif fault == 'early_generate':
            cmds[0] = cmds[1]
        elif fault == 'missing_go':
            cmds[1] = b''
        elif fault == 'repeated_generate':
            cmds[2] = cmds[1]
        elif fault == 'missing_finish':
            cmds[-1] = b''
    args, model, torch, wire, mapping = session(change_commands=change)
    with pytest.raises(ValueError):
        W.capture_session(*args)
    assert not any(C.strict_json(raw)['record_type'] == 'q3_session_end_v1' for raw in wire)
    if fault in ('historical_prepare', 'early_generate', 'missing_go'):
        assert model.calls == []
    elif fault == 'repeated_generate':
        assert len(model.calls) == 1
    else:
        assert len(model.calls) == 203


@pytest.mark.parametrize('new', [[], [4], [2, 4], [2, 2], [4] * 255, [4] * 257,
                               [49152, 2], [-1, 2], [True, 2], [1.0, 2]])
def test_invalid_or_incomplete_generated_sequence_stops_without_later_calls(new):
    args, model, torch, wire, mapping = session(new=new)
    with pytest.raises(ValueError):
        W.capture_session(*args)
    assert len(model.calls) == 1
    assert [C.strict_json(raw)['record_type'] for raw in wire] == ['q3_slot_ready_v1']


def test_eos_at_256_is_eos_and_genuine_empty_text_remains_observed():
    assert W.continuation([1, 4], [1, 4] + [4] * 255 + [2], 256)[1] == 'eos'
    args, model, torch, wire, mapping = session(new=[2])
    W.capture_session(*args)
    responses = [C.strict_json(raw) for raw in wire if C.strict_json(raw)['record_type'] == 'q3_response_v1']
    assert len(responses) == 203
    assert all(r['text'] == '' and r['text_utf8_base64'] == '' and r['stop_reason'] == 'eos' for r in responses)


def test_prefix_substitution_or_boolean_prefix_is_rejected():
    with pytest.raises(ValueError, match='GENERATED_PREFIX'):
        W.continuation([1, 4], [1, 5, 2], 256)
    with pytest.raises(ValueError, match='GENERATED_SEQUENCE'):
        W.continuation([1, 4], [True, 4, 2], 256)


def test_changed_generation_configuration_blocks_model_call():
    args, model, torch, wire, mapping = session(effective={'changed': True})
    with pytest.raises(ValueError, match='ORIGINAL_GENERATION_RUNTIME_MISMATCH'):
        W.capture_session(*args)
    assert model.calls == []


def synthetic_source_and_prelaunch(tmp_path, mode):
    """Files are inert test data; no captured helper is imported or executed."""
    source = tmp_path / 'source'
    inventory = {}
    for name in P['source_files']:
        actual = ROOT / name
        raw = actual.read_bytes() if actual.exists() else b'# explicit inert synthetic source\n'
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        inventory[name] = C.digest(raw)
    r = request(mode)
    mapping = W.tokenize_frame(Tokenizer(), FRAME, P)
    if mode == 'capture':
        r['approved_token_map_sha256'] = C.digest(C.encode(mapping))
    pre = {'record_type': 'q3_native_prelaunch_v1', 'request': r,
           'source_commit': r['source_commit'], 'run_id': '12345', 'run_attempt': 1,
           'source_files': inventory, 'historical_verification_sha256': 'c' * 64,
           'historical_phase_cleanup_sha256': 'd' * 64,
           'historical_acquisition_sha256': 'e' * 64}
    return source, pre


@pytest.mark.parametrize('fault', ['none', 'wrong_map', 'missing_load', 'missing_history',
                                  'mismatched_history', 'missing_history_cleanup', 'missing_acquisition'])
def test_actual_worker_entry_with_synthetic_runtime_never_loads_model_before_all_barriers(tmp_path, monkeypatch, fault):
    mode = 'token-preflight' if fault in ('none', 'missing_history', 'missing_history_cleanup', 'missing_acquisition') else 'capture'
    source, pre = synthetic_source_and_prelaunch(tmp_path, mode)
    if fault == 'wrong_map':
        pre['request']['approved_token_map_sha256'] = '0' * 64
    elif fault == 'missing_history':
        pre.pop('historical_verification_sha256')
    elif fault == 'mismatched_history':
        pre['historical_verification_sha256'] = 'f' * 64
    elif fault == 'missing_history_cleanup':
        pre.pop('historical_phase_cleanup_sha256')
    elif fault == 'missing_acquisition':
        pre.pop('historical_acquisition_sha256')
    raw = C.encode(pre)
    path = tmp_path / 'prelaunch.json'
    path.write_bytes(raw)
    incoming = io.BytesIO(b'TOKENIZE\nFINISH\n' if mode == 'token-preflight' else b'TOKENIZE\n')
    outgoing = io.BytesIO()
    with monkeypatch.context() as m:
        m.setattr(W.platform, 'python_implementation', lambda: 'CPython')
        m.setattr(W.platform, 'python_version', lambda: '3.11.16')
        m.setattr(W.platform, 'system', lambda: 'Linux')
        m.setattr(W.platform, 'machine', lambda: 'x86_64')
        m.setattr(W.platform, 'freedesktop_os_release', lambda: {'ID': 'ubuntu', 'VERSION_ID': '24.04'})
        m.setattr(W.os, 'getuid', lambda: 65534)
        m.setattr(W.sys, 'prefix', 'synthetic-venv-never-executed')
        m.setattr(W.sys, 'flags', types.SimpleNamespace(isolated=1))
        m.setattr(W.sys, 'stdin', types.SimpleNamespace(buffer=incoming))
        m.setattr(W.sys, 'stdout', types.SimpleNamespace(buffer=outgoing))
        m.setattr(W, 'load_tokenizer', lambda *args: Tokenizer())
        m.setattr(W, 'load_model', lambda *args: pytest.fail('model load before verified capture boundary'))
        if fault == 'none':
            assert W.run(source, tmp_path, path, C.digest(raw)) == 0
        else:
            with pytest.raises(ValueError):
                W.run(source, tmp_path, path, C.digest(raw))
    records = [C.strict_json(line) for line in outgoing.getvalue().splitlines()]
    assert not [r for r in records if r['record_type'] == 'q3_response_v1']
    if fault in ('none', 'wrong_map', 'missing_load'):
        assert len([r for r in records if r['record_type'] == 'q3_token_row_v1']) == 204
    else:
        assert records == []
    if fault == 'none':
        assert records[-1]['completed_calls'] == 0


def test_worker_import_contains_no_native_model_or_tokenizer_import():
    tree = ast.parse((TOOLS / 'run_q3_reference_subject_v1.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all(alias.name not in ('torch', 'transformers') for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module not in ('torch', 'transformers')


def test_actual_worker_complete_capture_binds_historical_receipt_before_exact_suffix(tmp_path, monkeypatch):
    source, pre = synthetic_source_and_prelaunch(tmp_path, 'capture')
    raw = C.encode(pre)
    path = tmp_path / 'prelaunch.json'
    path.write_bytes(raw)
    mapping = W.tokenize_frame(Tokenizer(), FRAME, P)
    map_sha = C.digest(C.encode(mapping))
    binding = {'prelaunch_sha256': C.digest(raw), 'run_id': pre['run_id'],
               'source_commit': pre['source_commit'], 'run_attempt': 1}
    effective = effective_generation()
    model_ready = C.encode({'record_type': 'q3_model_ready_v1', 'binding': binding,
                           'token_map_sha256': map_sha, 'effective_generation': effective,
                           'runtime': P['runtime']})
    subject = {'record_type': 'q3_capture_subject_v1', 'binding': binding,
               'model_ready_sha256': C.digest(model_ready), 'token_map_sha256': map_sha,
               'historical_verification_sha256': pre['historical_verification_sha256']}
    subject_sha = C.digest(C.encode(subject))
    incoming = io.BytesIO(b'TOKENIZE\n' + ('LOAD ' + map_sha + '\nBIND ' + subject_sha + '\n').encode()
                         + b''.join(commands(mapping['rows'][1:])))
    outgoing = io.BytesIO()
    model = Model(lambda index: [4] * 256 if index == 1 else [4, 2])
    torch = Torch()
    tok = Tokenizer()
    with monkeypatch.context() as m:
        m.setattr(W.platform, 'python_implementation', lambda: 'CPython')
        m.setattr(W.platform, 'python_version', lambda: '3.11.16')
        m.setattr(W.platform, 'system', lambda: 'Linux')
        m.setattr(W.platform, 'machine', lambda: 'x86_64')
        m.setattr(W.platform, 'freedesktop_os_release', lambda: {'ID': 'ubuntu', 'VERSION_ID': '24.04'})
        m.setattr(W.os, 'getuid', lambda: 65534)
        m.setattr(W.sys, 'prefix', 'synthetic-venv-never-executed')
        m.setattr(W.sys, 'flags', types.SimpleNamespace(isolated=1))
        m.setattr(W.sys, 'stdin', types.SimpleNamespace(buffer=incoming))
        m.setattr(W.sys, 'stdout', types.SimpleNamespace(buffer=outgoing))
        m.setattr(W, 'load_tokenizer', lambda *args: tok)
        m.setattr(W, 'load_model', lambda *args: (model, torch, Config, effective, copy.deepcopy(P['runtime'])))
        assert W.run(source, tmp_path, path, C.digest(raw)) == 0
    records = [C.strict_json(line) for line in outgoing.getvalue().splitlines()]
    assert len(tok.calls) == 204 and len(model.calls) == 203
    assert [r for r in records if r['record_type'] == 'q3_bound_v1'] == [
        {'record_type': 'q3_bound_v1', 'binding': {**binding, 'subject_sha256': subject_sha}}]
    responses = [r for r in records if r['record_type'] == 'q3_response_v1']
    assert [r['slot']['task_id'] for r in responses] == P['task_ids'][1:]
    assert responses[0]['stop_reason'] == 'token_limit'
    assert all(r['binding']['subject_sha256'] == subject_sha for r in responses)
    assert records[-1]['completed_calls'] == 203
