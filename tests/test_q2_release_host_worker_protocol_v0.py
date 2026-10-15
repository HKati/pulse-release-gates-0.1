"""Offline-only Q2 worker-protocol component regressions.

Every model/tokenizer/kernel/timer/run observation below is SYNTHETIC.
The actual frozen worker's Python protocol loop is executed with toy doubles.
No model library is imported, no weights loaded, and no kernel proof acquired.
"""
from __future__ import annotations
import base64
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'PULSE_safe_pack_v0/tools'

def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    exec(compile((TOOLS / (name + '.py')).read_bytes(), str(TOOLS / (name + '.py')), 'exec'), m.__dict__)
    return m

C = load('check_q2_release_host_worker_protocol_v0')
W = load('run_q2_reference_subject_v0')
# Configuration metadata only, from the original pinned capture subject.
# This is neither a generated response nor a replacement model/runtime.
FIXED_CONFIGURATION = {'_from_model_config': False, 'assistant_confidence_threshold': 0.4, 'assistant_early_exit': None, 'assistant_lookbehind': 10, 'bad_words_ids': None, 'begin_suppress_tokens': None, 'bos_token_id': 1, 'cache_config': None, 'cache_implementation': None, 'constraints': None, 'decoder_start_token_id': None, 'disable_compile': True, 'diversity_penalty': 0.0, 'do_sample': False, 'dola_layers': None, 'early_stopping': False, 'encoder_no_repeat_ngram_size': 0, 'encoder_repetition_penalty': 1.0, 'eos_token_id': 2, 'epsilon_cutoff': 0.0, 'eta_cutoff': 0.0, 'exponential_decay_length_penalty': None, 'force_words_ids': None, 'forced_bos_token_id': None, 'forced_eos_token_id': None, 'guidance_scale': None, 'is_assistant': False, 'length_penalty': 1.0, 'low_memory': None, 'max_length': 20, 'max_matching_ngram_size': None, 'max_new_tokens': 32, 'max_time': None, 'min_length': 0, 'min_new_tokens': 0, 'min_p': None, 'no_repeat_ngram_size': 0, 'num_assistant_tokens': 20, 'num_assistant_tokens_schedule': 'constant', 'num_beam_groups': 1, 'num_beams': 1, 'num_return_sequences': 1, 'output_attentions': False, 'output_hidden_states': False, 'output_logits': None, 'output_scores': False, 'pad_token_id': 2, 'penalty_alpha': None, 'prefill_chunk_size': None, 'prompt_lookup_num_tokens': None, 'remove_invalid_values': False, 'renormalize_logits': False, 'repetition_penalty': 1.0, 'return_dict_in_generate': False, 'return_legacy_cache': None, 'sequence_bias': None, 'stop_strings': None, 'suppress_tokens': None, 'target_lookbehind': 10, 'temperature': 1.0, 'token_healing': False, 'top_k': 50, 'top_p': 1.0, 'transformers_version': '4.57.6', 'typical_p': 1.0, 'use_cache': True, 'watermarking_config': None}

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('network is forbidden in offline protocol regressions')
    monkeypatch.setattr(socket.socket, 'connect', blocked)


def sandbox():
    return {'stage': 'captureworker', 'unit': 'pulse-q2-' + 'a' * 24 + '-captureworker.service',
        'pid': 123, 'host_netns': 'net:[1]', 'child_netns': 'net:[2]', 'uid': 65534,
        'no_new_privs': True, 'capabilities': '0000000000000000', 'ipv4_blocked': True,
        'ipv6_blocked': True, 'memory_max': '4294967296', 'memory_swap_max': '0',
        'pids_max': '64', 'cpu_max': '100000 100000', 'capture_runtime_seconds': 1100,
        'properties': {'PrivateNetwork': 'yes', 'NoNewPrivileges': 'yes', 'ProtectSystem': 'strict',
            'ProtectHome': 'yes', 'KillMode': 'control-group', 'SendSIGKILL': 'yes', 'User': '65534',
            'Group': '65534', 'CapabilityBoundingSet': '', 'RestrictAddressFamilies': 'AF_UNIX',
            'RuntimeMaxUSec': '18min 20s'},
        'run_mount': {'host_namespace': 'mnt:[1]', 'child_namespace': 'mnt:[2]',
            'host_mountinfo': '10 1 0:20 / /run rw,nosuid,nodev - tmpfs tmpfs rw\n',
            'child_mountinfo': '20 1 0:30 / /run rw,nosuid,nodev,noexec - tmpfs tmpfs rw,size=16384k\n',
            'mount_stats': {'/run': {'device': '0:30', 'inode': 1, 'uid': 0, 'gid': 0, 'mode': 0o40755}}}}


def fixture_trace(unknown_group=False):
    workload_raw = (ROOT / C.WORKLOAD).read_bytes()
    workload, slots = C.fixed_slots(workload_raw)
    names = [C.WORKER, C.WORKLOAD, C.PACK + 'profiles/q2_reference_subject_v0.json',
             C.PACK + 'profiles/q2_reference_model_files_v0.json']
    pre = {'record_type': 'q2_capture_prelaunch_v0', 'record_status': 'native', 'scope': C.SCOPE,
        'context': {'repository': C.REPOSITORY, 'workflow': C.WORKFLOW, 'source_commit': 'c' * 40,
            'run_id': '123456', 'run_attempt': 1, 'actor': 'HKati', 'event': 'workflow_dispatch',
            'origin': 'owner_dispatched_github_q2_capture'},
        'source_files': [{'path': n, 'size': len((ROOT / n).read_bytes()), 'sha256': C.digest((ROOT / n).read_bytes())}
                         for n in sorted(names)],
        'slots': slots, 'planned_calls': 150, 'limits': dict(C.LIMITS),
        'phase_start_ns': 1_000_000_000, 'phase_deadline_ns': 1201_000_000_000,
        'started_at': '2026-10-15T00:00:00+00:00', 'request_sha256': '1' * 64,
        'capsule_sha256': C.CAPSULE_SHA256, 'observer_contract_sha256': '2' * 64,
        'authority_effect': 'none', 'production_gate_eligible': False}
    raw_pre = C.encode(pre)
    config = copy.deepcopy(FIXED_CONFIGURATION)
    identity0 = {'prelaunch_sha256': C.digest(raw_pre), 'source_commit': 'c' * 40, 'run_id': '123456', 'run_attempt': 1}
    ready = {'record_type': 'q2_capture_model_ready_v0', 'binding': identity0,
             'effective_generation': config, 'runtime': dict(C.RUNTIME)}
    subject = {'record_type': 'q2_capture_subject_v0', 'prelaunch_sha256': C.digest(raw_pre),
        'definition_sha256': C.DEFINITION_SHA256, 'worker_sha256': C.WORKER_SHA256,
        'ready_sha256': C.digest(C.encode(ready)), 'effective_generation': config, 'runtime': dict(C.RUNTIME),
        'authority_effect': 'none', 'production_gate_eligible': False}
    identity = {**identity0, 'subject_sha256': C.digest(C.encode(subject))}
    state = {'model_calls': 0, 'seeds': [], 'masks': [], 'tensors': [], 'configs': [], 'commands': []}
    class Tensor:
        def __init__(self, data): self.data = data; self.shape = (len(data), len(data[0]))
        def __getitem__(self, index): return types.SimpleNamespace(tolist=lambda: list(self.data[index]))
    class Config:
        def __init__(self, **kwargs):
            self.value = copy.deepcopy(config); self.value.update(kwargs)
        def to_dict(self): return self.value
    class ToyModel:
        def generate(self, **kwargs):
            assert set(kwargs) == {'input_ids', 'attention_mask', 'generation_config', 'use_model_defaults'}
            assert kwargs['use_model_defaults'] is False
            state['model_calls'] += 1
            for dst, key in [('masks', 'attention_mask'), ('tensors', 'input_ids'), ('configs', 'generation_config')]:
                state[dst].append(kwargs[key])
            tail = [41] * 32 if unknown_group and 130 <= state['model_calls'] <= 132 else [41, 2]
            return Tensor([kwargs['input_ids'].data[0] + tail])
    class ToyTokenizer:
        def apply_chat_template(self, messages, **kwargs):
            assert kwargs == {'tokenize': True, 'add_generation_prompt': True}
            return [1, 10 + len(messages[1]['content'])]
        def decode(self, ids, **kwargs):
            assert kwargs == {'skip_special_tokens': True, 'clean_up_tokenization_spaces': False}
            return ' synthetic exact value\n' if ids == [41, 2] else ('synthetic-limit' if ids == [41] * 32 else 'wrong')
    tokenizer = ToyTokenizer()
    torch = types.SimpleNamespace(long='int64', tensor=lambda data, **kwargs: Tensor(data),
        ones_like=lambda value: Tensor([[1] * len(value.data[0])]),
        manual_seed=lambda seed: state['seeds'].append(seed), inference_mode=contextlib.nullcontext)
    wire_commands = []
    for slot in slots:
        wire_commands += [('PREPARE ' + slot['call_id'] + '\n').encode(), ('GENERATE ' + slot['call_id'] + '\n').encode()]
    wire_commands.append(b'FINISH\n')
    cursor = iter(wire_commands)
    def read_command():
        cmd = next(cursor); state['commands'].append((cmd, state['model_calls'])); return cmd
    frames = []
    # This is the actual frozen worker loop, with explicitly synthetic runtime objects.
    W.capture_session(ToyModel(), tokenizer, torch, Config, dict(C.RUNTIME), workload, slots,
                      {'identity': identity, 'effective_generation': config}, read_command, frames.append)
    records = [(frames[2 * i + 1], frames[2 * i]) for i in range(150)]
    obs = sandbox(); prefix = 'pulse-q2-' + 'a' * 24
    occurrences = []
    commands = [{'command': 'EXEC\n', 'written_ns': 1_600_000_000},
                {'command': 'BIND ' + C.digest(C.encode(subject)) + '\n', 'written_ns': 1_800_000_000}]
    for i, (slot, pair) in enumerate(zip(slots, records)):
        tick = 2_000_000_000 + i * 2_000_000_000
        tp = prefix + f'-call-{i + 1:03d}'
        occ = {'slot': slot, 'status': 'completed', 'ready_received_ns': tick,
            'generation_start_ns': tick + 200, 'generation_deadline_ns': tick + 15_000_000_200,
            'response_received_ns': tick + 1000, 'watchdog_arm_begin_ns': tick + 100,
            'watchdog_armed': True, 'watchdog_unit': tp + '-watchdog.timer',
            'watchdog_closed': {'record_type': 'q2_capture_watchdog_closed_v0', 'stop_returncode': 0,
                'units': [{'unit': tp + '-watchdog.' + suffix, 'LoadState': 'loaded', 'ActiveState': 'inactive'}
                          for suffix in ('timer', 'service')], 'closed_ns': tick + 2000}}
        for role, raw in zip(('response', 'ready'), pair):
            occ[role] = {'path': 'calls/' + slot['call_id'] + '.' + role + '.json', 'size': len(raw), 'sha256': C.digest(raw)}
        occurrences.append(occ)
        commands += [{'command': 'PREPARE ' + slot['call_id'] + '\n', 'written_ns': tick - 100},
                     {'command': 'GENERATE ' + slot['call_id'] + '\n', 'written_ns': tick + 200}]
    commands.append({'command': 'FINISH\n', 'written_ns': 304_000_000_000})
    cleanup = {'unit': obs['unit'], 'properties': {'LoadState': 'not-found', 'ActiveState': 'inactive', 'ControlGroup': ''},
               'cgroup_empty_or_removed': True, 'client_reaped': True}
    terminal = {'record_type': 'q2_capture_transcript_v0', 'record_status': 'native', 'status': 'completed',
        'error_code': None, 'binding': identity, 'occurrences': occurrences, 'worker_launch_ns': 1_500_000_000,
        'worker_deadline_ns': 1101_500_000_000, 'worker_exit_code': 0, 'session_end': C.parse(frames[-1]),
        'session_end_ns': 305_000_000_000, 'cleanup': cleanup, 'sandbox': obs,
        'ended_at': '2026-10-15T00:05:10+00:00', 'authority_effect': 'none', 'production_gate_eligible': False}
    life = {'record_type': 'q2_worker_protocol_lifecycle_v0', 'observation_basis': 'supplied_external_observer_records',
        'launch_ns': 1_500_000_000, 'isolation_observed_ns': 1_550_000_000, 'exec_ns': 1_600_000_000,
        'model_ready_received_ns': 1_700_000_000,
        'bound_frame_base64': base64.b64encode(C.encode({'record_type': 'q2_capture_bound_v0', 'binding': identity})).decode(),
        'bound_received_ns': 1_900_000_000, 'commands': commands, 'stdout_eof_ns': 304_100_000_000,
        'exit_observed_ns': 304_200_000_000, 'process_reaped_ns': 304_300_000_000,
        'cleanup_completed_ns': 305_100_000_000, 'exit_code': 0, 'client_reaped': True,
        'sandbox': copy.deepcopy(obs), 'cleanup': copy.deepcopy(cleanup), 'source_recheck': 'unchanged',
        'input_recheck': 'unchanged', 'private_tree_cleanup': 'verified_removed'}
    admission = {'scope': C.SCOPE, 'repository': C.REPOSITORY, 'workflow': C.WORKFLOW,
        'source_commit': 'c' * 40, 'run_id': '123456', 'run_attempt': 1, 'request_sha256': '1' * 64,
        'prelaunch_sha256': C.digest(raw_pre), 'subject_sha256': C.digest(C.encode(subject)),
        'transcript_sha256': C.digest(C.encode(terminal)), 'effective_generation_sha256': C.digest(C.encode(config)),
        'capsule_sha256': C.CAPSULE_SHA256, 'observer_contract_sha256': '2' * 64, 'lifecycle_sha256': C.digest(C.encode(life))}
    return {'pre': pre, 'subject': subject, 'ready': ready, 'terminal': terminal, 'life': life, 'records': records,
        'configuration': config, 'admission': admission, 'expected': copy.deepcopy(admission), 'state': state,
        'tokenizer': tokenizer, 'workload_raw': workload_raw, 'frames': frames}

@pytest.fixture(scope='module')
def base_trace():
    return fixture_trace()

@pytest.fixture
def trace(base_trace):
    # Break cross-record aliases so a mutation cannot accidentally change the prelaunch too.
    return {key: copy.deepcopy(value) for key, value in base_trace.items()}


def verify(f):
    return C.verify_protocol(source=ROOT, workload_raw=f['workload_raw'], admission=f['admission'],
        expected_admission=f['expected'], prelaunch_raw=C.encode(f['pre']), subject_raw=C.encode(f['subject']),
        model_ready_raw=C.encode(f['ready']), transcript_raw=C.encode(f['terminal']), lifecycle=f['life'],
        records=f['records'], configuration=f['configuration'],
        tokenize=lambda msgs: [1, 10 + len(msgs[1]['content'])],
        decode=lambda ids: ' synthetic exact value\n' if ids == [41, 2] else ('synthetic-limit' if ids == [41] * 32 else 'wrong'))


def rehash_terminal(f):
    f['admission']['transcript_sha256'] = C.digest(C.encode(f['terminal']))
    f['admission']['lifecycle_sha256'] = C.digest(C.encode(f['life']))
    f['expected'] = copy.deepcopy(f['admission'])


def change_response(f, index, change):
    response = C.parse(f['records'][index][0]); change(response)
    raw = C.encode(response); f['records'][index] = (raw, f['records'][index][1])
    row = f['terminal']['occurrences'][index]['response']; row['sha256'] = C.digest(raw); row['size'] = len(raw)
    rehash_terminal(f)


def test_actual_frozen_worker_150_calls_and_independent_reconstruction(trace):
    before = {name: name in sys.modules for name in ('torch', 'transformers')}
    result = verify(trace)
    assert result['protocol_reconstructed'] is True and result['verified_slots'] == 150
    assert result['native_origin_verified'] is False and result['metric_pass'] is None
    assert result['release_authorized'] is False and result['authority_effect'] == 'none'
    assert trace['state']['model_calls'] == 150
    assert trace['state']['seeds'] == [1729] * 150
    for key in ('tensors', 'masks', 'configs'):
        assert len({id(x) for x in trace['state'][key]}) == 150
    for index, (command, before_count) in enumerate(trace['state']['commands']):
        assert before_count == index // 2 if index < 300 else before_count == 150
    assert len(C.parse(result['groups_bytes'])['groups']) == 50
    assert before == {name: name in sys.modules for name in before}


@pytest.mark.parametrize('index', range(150))
def test_each_missing_or_rebound_slot_rejects(trace, index):
    trace['terminal']['occurrences'][index]['slot']['ordinal'] = 151
    rehash_terminal(trace)
    with pytest.raises(C.ProtocolError): verify(trace)

@pytest.mark.parametrize('mutation', ['missing_record', 'extra_record', 'duplicate_record', 'swapped_record',
    'missing_occurrence', 'extra_occurrence', 'unknown_status', 'retry', 'late', 'watchdog_false',
    'watchdog_active', 'window', 'wrong_timer', 'wrong_response_path', 'bad_size', 'bool_size',
    'bad_digest', 'session_absent', 'session_calls', 'session_bool', 'exit_one', 'exit_false',
    'terminal_pass_flag', 'cleanup_missing', 'source_changed', 'input_changed', 'tree_retained',
    'missing_exec', 'exec_after_ready', 'bind_before_ready', 'wrong_bind', 'missing_finish',
    'finish_early', 'extra_generate', 'reordered_generate', 'missing_eof', 'not_reaped',
    'wrong_uid', 'same_netns', 'capabilities', 'bad_run_mount', 'bad_runtime_limit',
    'missing_bound', 'wrong_bound', 'bound_after_prepare'])
def test_closed_protocol_and_terminal_negative_matrix(trace, mutation):
    f=trace; t=f['terminal']; o=t['occurrences'][0]; l=f['life']; r=f['records']
    if mutation=='missing_record': r.pop()
    elif mutation=='extra_record': r.append(r[-1])
    elif mutation=='duplicate_record': r[1]=r[0]
    elif mutation=='swapped_record': r[0],r[1]=r[1],r[0]
    elif mutation=='missing_occurrence': t['occurrences'].pop()
    elif mutation=='extra_occurrence': t['occurrences'].append(copy.deepcopy(o))
    elif mutation=='unknown_status': o['status']='unknown'
    elif mutation=='retry': o['slot']['attempt']=2
    elif mutation=='late': o['response_received_ns']=o['generation_deadline_ns']+1
    elif mutation=='watchdog_false': o['watchdog_armed']=False
    elif mutation=='watchdog_active': o['watchdog_closed']['units'][0]['ActiveState']='active'
    elif mutation=='window': o['generation_deadline_ns']+=1
    elif mutation=='wrong_timer': o['watchdog_unit']='other.timer'
    elif mutation=='wrong_response_path': o['response']['path']='calls/../response.json'
    elif mutation=='bad_size': o['response']['size']+=1
    elif mutation=='bool_size': o['response']['size']=True
    elif mutation=='bad_digest': o['response']['sha256']='0'*64
    elif mutation=='session_absent': t['session_end']=None
    elif mutation=='session_calls': t['session_end']['completed_calls']=149
    elif mutation=='session_bool': t['session_end']['completed_calls']=True
    elif mutation=='exit_one': t['worker_exit_code']=1
    elif mutation=='exit_false': t['worker_exit_code']=False
    elif mutation=='terminal_pass_flag': t['production_gate_eligible']=True
    elif mutation=='cleanup_missing': l['cleanup']=None
    elif mutation=='source_changed': l['source_recheck']='changed'
    elif mutation=='input_changed': l['input_recheck']='changed'
    elif mutation=='tree_retained': l['private_tree_cleanup']='retained'
    elif mutation=='missing_exec': l['commands'].pop(0)
    elif mutation=='exec_after_ready': l['exec_ns']=l['model_ready_received_ns']+1
    elif mutation=='bind_before_ready': l['commands'][1]['written_ns']=l['exec_ns']
    elif mutation=='wrong_bind': l['commands'][1]['command']='BIND '+'0'*64+'\n'
    elif mutation=='missing_finish': l['commands'].pop()
    elif mutation=='finish_early': l['commands'][-1]['written_ns']=2_000_000_000
    elif mutation=='extra_generate': l['commands'].append({'command':'GENERATE q2fx-050-r03\n','written_ns':305_000_000_000})
    elif mutation=='reordered_generate': l['commands'][3],l['commands'][5]=l['commands'][5],l['commands'][3]
    elif mutation=='missing_eof': l['stdout_eof_ns']=None
    elif mutation=='not_reaped': l['client_reaped']=False
    elif mutation=='wrong_uid': l['sandbox']['uid']=0; t['sandbox']['uid']=0
    elif mutation=='same_netns': l['sandbox']['child_netns']='net:[1]'; t['sandbox']['child_netns']='net:[1]'
    elif mutation=='capabilities': l['sandbox']['capabilities']='ffffffffffffffff'; t['sandbox']['capabilities']='ffffffffffffffff'
    elif mutation=='bad_run_mount': l['sandbox']['run_mount']['child_namespace']='mnt:[1]'; t['sandbox']['run_mount']['child_namespace']='mnt:[1]'
    elif mutation=='bad_runtime_limit': l['sandbox']['properties']['RuntimeMaxUSec']='30min'; t['sandbox']['properties']['RuntimeMaxUSec']='30min'
    elif mutation=='missing_bound': l['bound_frame_base64']=''
    elif mutation=='wrong_bound': l['bound_frame_base64']=base64.b64encode(C.encode({'record_type':'q2_capture_bound_v0','binding':{}})).decode()
    elif mutation=='bound_after_prepare': l['bound_received_ns']=l['commands'][2]['written_ns']+1
    else: raise AssertionError(mutation)
    rehash_terminal(f)
    with pytest.raises(C.ProtocolError): verify(f)

@pytest.mark.parametrize('mutation', ['ids', 'ids_bool', 'prefix', 'short', 'empty', 'extra', 'eos_inside',
    'stop', 'text', 'utf8', 'config', 'runtime', 'identity', 'slot', 'extra_field'])
def test_coherently_rehashed_response_cannot_replace_token_or_execution_meaning(trace, mutation):
    def change(x):
        if mutation=='ids': x['new_token_ids']=[42,2]
        elif mutation=='ids_bool': x['new_token_ids']=[True,2]
        elif mutation=='prefix': x['input_ids']=[1,12]
        elif mutation=='short': x['new_token_ids']=[41]
        elif mutation=='empty': x['new_token_ids']=[]
        elif mutation=='extra': x['new_token_ids']=[41]*33+[2]
        elif mutation=='eos_inside': x['new_token_ids']=[2,41,2]
        elif mutation=='stop': x['stop_reason']='timeout'
        elif mutation=='text': x['text']='edited'; x['text_utf8_base64']=base64.b64encode(b'edited').decode()
        elif mutation=='utf8': x['text_utf8_base64']='ZWRpdGVk'
        elif mutation=='config': x['effective_generation']['do_sample']=True
        elif mutation=='runtime': x['runtime']['device']='cuda'
        elif mutation=='identity': x['binding']['run_id']='654321'
        elif mutation=='slot': x['slot']['call_id']='q2fx-002-r01'
        elif mutation=='extra_field': x['accepted']=True
    change_response(trace,0,change)
    with pytest.raises(C.ProtocolError): verify(trace)

@pytest.mark.parametrize('key', ['source_commit','run_id','run_attempt','request_sha256','prelaunch_sha256',
    'subject_sha256','transcript_sha256','capsule_sha256','observer_contract_sha256','effective_generation_sha256','lifecycle_sha256'])
def test_selected_external_identity_cannot_be_rebound_by_artifact(trace,key):
    trace['admission'][key] = 2 if key=='run_attempt' else ('d'*40 if key=='source_commit' else ('654321' if key=='run_id' else 'd'*64))
    with pytest.raises(C.ProtocolError): verify(trace)

@pytest.mark.parametrize('raw', [b'',b'\xef\xbb\xbf{}',b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}',
    b'{"x":1e9999}',b'{"x":"\\ud800"}',b'\xff',b'[',b'['*66+b'0'+b']'*66])
def test_strict_json_rejects_ambiguous_or_unbounded_inputs(raw):
    with pytest.raises(C.ProtocolError): C.parse(raw)

@pytest.mark.parametrize('value', [True,False,0.0,'0',None,[],{}])
def test_literal_integer_contract_rejects_substitutes(value):
    with pytest.raises(C.ProtocolError): C.integer(value,0,0,'literal')

@pytest.mark.parametrize('kind', ['leaf_link','parent_link','hardlink','directory','fifo','too_large','missing'])
def test_held_file_boundary(tmp_path,kind):
    p=tmp_path/'input';p.write_bytes(b'payload');q=tmp_path/'read'
    if kind=='leaf_link':q.symlink_to(p)
    elif kind=='parent_link':(tmp_path/'link').symlink_to(tmp_path,target_is_directory=True);q=tmp_path/'link/input'
    elif kind=='hardlink':os.link(p,q)
    elif kind=='directory':q.mkdir()
    elif kind=='fifo':os.mkfifo(q)
    elif kind=='too_large':q.write_bytes(b'a'*11)
    with pytest.raises(C.ProtocolError):C.held_read(q,10)


def test_exact_empty_and_regular_file_io(tmp_path):
    p=tmp_path/'file';p.write_bytes(b'');assert C.held_read(p)==b''
    p.write_bytes(b'original');assert C.held_read(p)==b'original'


def test_fixed_configuration_and_capsule_reject_coherent_admission_change(trace):
    trace['configuration']['do_sample']=True
    trace['admission']['effective_generation_sha256']=C.digest(C.encode(trace['configuration']))
    trace['expected']=copy.deepcopy(trace['admission'])
    with pytest.raises(C.ProtocolError,match='configuration_changed'):verify(trace)


def test_unchanged_worker_default_and_full_protocol():
    raw=(ROOT/C.WORKER).read_bytes();assert C.digest(raw)==C.WORKER_SHA256
    assert b"default='diagnostic'" in raw and b"choices=['diagnostic', 'capture-reference']" in raw
    assert b"require(read_command() == b'FINISH\\n'" in raw


def test_immutable_helper_source_rejected_before_import(tmp_path):
    for name in C.PINNED_HELPERS:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
    p=tmp_path/C.OLD_CHECKER;p.write_bytes(p.read_bytes()+b'\nraise RuntimeError("must not run")\n')
    with pytest.raises(C.ProtocolError,match='helper_source_changed'):C.load_independent_helpers(tmp_path)


def test_workload_byte_binding_is_not_replaced_by_semantic_json(trace):
    trace['workload_raw']=json.dumps(C.parse(trace['workload_raw']),indent=1).encode()
    with pytest.raises(C.ProtocolError,match='workload_changed'):verify(trace)


@pytest.mark.parametrize('unknown',[False,True])
def test_real_unchanged_metric_builder_and_checker_after_synthetic_worker(tmp_path,unknown):
    f=fixture_trace(unknown);result=verify(f);groups=result['groups_bytes'];(tmp_path/'groups.json').write_bytes(groups)
    manifest={'manifest_version':'1.0.0','dataset_id':'q2-synthetic-protocol-test',
        'time_range':{'from':'2026-10-15T00:00:00+00:00','to':'2026-10-15T00:05:10+00:00'},
        'source':{'kind':'artifact','uri':'synthetic:offline-regression','description':'Synthetic test only; no native observations.'},
        'sampling':{'strategy':'full','n':50,'seed':0},'hashes':{'input_sha256':C.digest(groups),'code_sha':'c'*40},
        'pii_handling':{'scrubbed':False,'notes':'Synthetic constants only.'}}
    raw=C.encode(manifest);(tmp_path/'manifest.json').write_bytes(raw)
    common=['--groups',str(tmp_path/'groups.json'),'--dataset-manifest',str(tmp_path/'manifest.json'),
            '--expected-groups-sha256',C.digest(groups),'--expected-manifest-sha256',C.digest(raw)]
    build=subprocess.run([sys.executable,str(TOOLS/'build_q2_reference_summary.py'),*common,'--out',str(tmp_path/'summary.json')],
        capture_output=True,timeout=30)
    assert build.returncode==(1 if unknown else 0),build.stderr.decode()
    summary=(tmp_path/'summary.json').read_bytes()
    check=subprocess.run([sys.executable,str(TOOLS/'check_q2_reference_summary.py'),*common,
        '--summary',str(tmp_path/'summary.json'),'--expected-summary-sha256',C.digest(summary)],capture_output=True,timeout=30)
    assert check.returncode==0,check.stderr.decode()
    obj=C.parse(summary)
    assert obj['pass'] is (not unknown)
    assert obj['counts']['groups_eligible']==(49 if unknown else 50)
    assert result['metric_pass'] is None and result['native_origin_verified'] is False



@pytest.mark.parametrize('arguments', [[], ['--native'], ['--authorize-150-calls'], ['--help']])
def test_component_cli_does_not_claim_or_dispatch_native_work(arguments):
    run=subprocess.run([sys.executable,'-I','-B',str(TOOLS/'check_q2_release_host_worker_protocol_v0.py'),*arguments],
                       capture_output=True,timeout=5)
    assert run.returncode==2 and run.stdout==b''
    assert run.stderr==b'q2_worker_protocol_library_use_check_q2_release_host_worker_v0\n'


def test_q2_1_original_checkpoint_and_zero_inference_claims_remain_unchanged():
    folder=ROOT/'PULSE_safe_pack_v0/examples/q2_release_host_tokenizer_v0/run_38478598045'
    index=json.loads((folder/'recorded-tokenizer.json').read_bytes())
    for row in index['evidence_files']:
        raw=(folder/row['path']).read_bytes()
        assert len(raw)==row['size_bytes'] and C.digest(raw)==row['sha256']
    result=json.loads((folder/'evidence/result.json').read_bytes())
    assert result['binding']['source_commit']=='d44bf963cbac377366e95ae7ac9e3603fff894a4'
    assert result['binding']['run_id']=='38478598045' and result['binding']['run_attempt']==1
    assert result['claims']['current_inference_count']==0
    assert result['claims']['model_weights_loaded'] is False and result['claims']['worker_launch_executed'] is False
    assert result['claims']['production_gate_eligible'] is False and result['claims']['authority_effect']=='none'
    assert result['metrics']['groups_eligible']==49 and result['metrics']['groups_total']==50
    assert result['metrics']['unknown']==1 and result['claims']['historical_metric_pass'] is False
    raw=(folder/'q2-offline-replay-38478598045-1.zip').read_bytes()
    assert C.digest(raw)=='66b7bfcc5b9bbfa72e2be843ba0d541d89adac6ae14e9ca1ad56af119da091a9'


# Fresh subprocess protocol exercise. These fixtures replace platform/model input
# acquisition ONLY; the frozen run_capture/main/BIND/150-slot/FINISH/exit logic is
# not replaced. This does NOT execute a native platform qualification or a model.
TOY_CLI = r'''
import contextlib,hashlib,importlib.util,json,sys,types
from pathlib import Path
root,prepath,subjectpath,counterpath,configpath=map(Path,sys.argv[1:])
spec=importlib.util.spec_from_file_location('frozen_worker',root/'PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py')
W=importlib.util.module_from_spec(spec)
raw=(root/'PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='37c932272da1579c3e1bf821fb5bde671ae756ede99aceb7deac58c85ee4b172'
exec(compile(raw,str(root/'PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py'),'exec'),W.__dict__)
original_require=W.require
# Explicitly synthetic qualification seam; no native-host claim is made.
def require(condition,code):
    if code in ('python_target','machine_target','os_target','isolated_venv_required'):return
    original_require(condition,code)
W.require=require
pre=json.loads(prepath.read_bytes());config=json.loads(configpath.read_bytes())
workload=json.loads((root/W.CAPTURE_WORKLOAD).read_bytes())
def inputs(source,bundle,raw,expected):
    original_require(hashlib.sha256(raw).hexdigest()==expected,'synthetic_prelaunch_digest')
    return pre,{},workload
W.capture_input_binding=inputs
class Tensor:
    def __init__(self,data):self.data=data;self.shape=(len(data),len(data[0]))
    def __getitem__(self,index):return types.SimpleNamespace(tolist=lambda:list(self.data[index]))
class Config:
    def __init__(self,**kw):self.value={**config,**kw}
    def to_dict(self):return self.value
state={'calls':0}
class ToyModel:
    def generate(self,**kw):
        state['calls']+=1
        return Tensor([kw['input_ids'].data[0]+[41,2]])
class ToyTokenizer:
    def apply_chat_template(self,messages,**kw):return [1,10+len(messages[1]['content'])]
    def decode(self,ids,**kw):return ' synthetic exact value\n'
def jcs_subset(value):
    if type(value) is dict:
        return b'{'+b','.join(jcs_subset(k)+b':'+jcs_subset(value[k]) for k in sorted(value,key=lambda k:k.encode('utf-16-be')))+b'}'
    if type(value) is list:return b'['+b','.join(jcs_subset(x) for x in value)+b']'
    if type(value) is float:
        assert value.is_integer();return str(int(value)).encode()
    return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode()
runtime={'torch':'2.8.0+cpu','transformers':'4.57.6','device':'cpu','dtype':'torch.float32','attention':'eager',
    'threads':1,'interop_threads':1,'deterministic':True,'evaluation':True,'model_class':'LlamaForCausalLM',
    'seed':1729,'model_defaults':False,'compile':False,'quantization':'none'}
torch=types.SimpleNamespace(long='int64',tensor=lambda d,**kw:Tensor(d),ones_like=lambda x:Tensor([[1]*len(x.data[0])]),
    manual_seed=lambda seed:None,inference_mode=contextlib.nullcontext)
W.load_capture_runtime=lambda bundle,selected:(ToyModel(),ToyTokenizer(),torch,Config,Config(),runtime,jcs_subset)
rc=W.main(['--source-root',str(root),'--bundle',str(prepath.parent),'--prelaunch',str(prepath),
    '--expected-prelaunch-sha256',hashlib.sha256(prepath.read_bytes()).hexdigest(),'--mode','capture-reference',
    '--subject',str(subjectpath)])
counterpath.write_text(str(state['calls']))
raise SystemExit(rc)
'''


@pytest.mark.parametrize('fault,expected_calls,expected_exit', [
    ('full',150,0),('early_eof',0,1),('wrong_bind',0,1),('missing_generate',0,1),
    ('duplicate_prepare',1,1),('missing_finish',150,1),('extra_call',150,1),('wrong_subject',0,1)])
def test_fresh_process_frozen_worker_full_cli_and_failure_exit(trace,tmp_path,fault,expected_calls,expected_exit):
    f=trace;helper=tmp_path/'toy_cli.py';helper.write_text(TOY_CLI)
    pre=tmp_path/'pre.json';pre.write_bytes(C.encode(f['pre']))
    subject=tmp_path/'subject.json';subject.write_bytes(C.encode(f['subject']))
    cfg=tmp_path/'configuration.json';cfg.write_bytes(C.encode(f['configuration']))
    counts=tmp_path/'counts.txt'
    commands=[x['command'].encode() for x in f['life']['commands'][1:]]
    if fault=='early_eof':commands=[]
    elif fault=='wrong_bind':commands[0]=b'BIND '+b'0'*64+b'\n'
    elif fault=='missing_generate':commands.pop(2)
    elif fault=='duplicate_prepare':commands[3]=commands[1]
    elif fault=='missing_finish':commands.pop()
    elif fault=='extra_call':commands.insert(-1,b'GENERATE q2fx-050-r03\n')
    elif fault=='wrong_subject':subject.write_bytes(C.encode({**f['subject'],'worker_sha256':'0'*64}))
    result=subprocess.run([sys.executable,'-I','-B',str(helper),str(ROOT),str(pre),str(subject),str(counts),str(cfg)],
                          input=b''.join(commands),capture_output=True,timeout=15)
    assert result.returncode==expected_exit,result.stderr.decode()
    assert int(counts.read_text())==expected_calls
    frames=[json.loads(line) for line in result.stdout.splitlines()]
    assert frames[0]['record_type']=='q2_capture_model_ready_v0'
    if fault=='full':
        assert len(frames)==303 and frames[1]['record_type']=='q2_capture_bound_v0'
        assert frames[-1]['record_type']=='q2_capture_session_end_v0' and frames[-1]['completed_calls']==150
        assert result.stderr==b''
    else:
        assert not any(x.get('record_type')=='q2_capture_session_end_v0' for x in frames)
        assert result.stderr==b'Q2 capture worker failed; no completed occurrence\n'


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
