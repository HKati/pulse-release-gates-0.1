"""Synthetic continuation-controller regressions. No native generation or API use."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import types

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'PULSE_safe_pack_v0/tools'


def module(name):
    spec = importlib.util.spec_from_file_location('test_v1_' + name, TOOLS / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


C = module('q3_native_capture_contract_v1')
A = module('acquire_q3_reference_inputs_v1')
K = module('check_q3_native_capture_v1')
R = module('q3_native_runtime_v1')
W = module('run_q3_reference_subject_v1')
P = C.load_profile(ROOT)
FULL = C.task_frame(ROOT, P)
FRAME = C.continuation_frame(ROOT, P)
EFFECTIVE = json.loads((ROOT / 'tests/fixtures/q3_continuation_v1/effective-generation.json').read_bytes())
BINDING = {'prelaunch_sha256': 'a' * 64, 'source_commit': 'b' * 40,
           'run_id': '12345', 'run_attempt': 1}
PREFIX = 'pulse-q3-' + 'a' * 24


class Clock:
    def __init__(self):
        self.value = 1_000_000_000

    def ns(self):
        self.value += 1_000_000
        return self.value

    def seconds(self):
        return self.ns() / 1e9


class Tokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return [1, 4]


class Life:
    def __init__(self, clock, fail=False):
        self.clock = clock
        self.fail = fail
        self.active = None
        self.closed = []

    def arm(self, timer, unit):
        assert self.active is None
        self.active = timer

    def disarm(self, timer, deadline):
        assert timer == self.active
        if self.fail:
            raise ValueError('TEST_WATCHDOG_UNCLOSED')
        self.active = None
        self.closed.append(timer)
        return {'closed_ns': self.clock.ns()}


class Service:
    """A protocol test double. It never imports torch/transformers or starts a process."""
    def __init__(self, clock, life, mapping, mutation=None, model_mutation=None):
        self.clock = clock
        self.life = life
        self.mapping = mapping
        self.mutation = mutation
        self.model_mutation = model_mutation
        self.queue = []
        self.commands = []
        self.generated = []
        self.binding = BINDING
        self.deadline = 10**9
        self.runtime_deadline_ns = 10**15
        self.unit = PREFIX + '-captureworker.service'
        self.reader = types.SimpleNamespace(buffer=b'', selector=types.SimpleNamespace(select=lambda _: []), line=self.line)

    def line(self, deadline):
        assert self.clock.seconds() < deadline
        assert self.queue
        return C.encode(self.queue.pop(0))

    def send(self, command):
        self.commands.append(command)
        op, _, arg = command.decode().strip().partition(' ')
        stamp = self.clock.ns()
        if op == 'LOAD':
            value = {'record_type': 'q3_model_ready_v1', 'binding': BINDING,
                     'token_map_sha256': arg, 'effective_generation': copy.deepcopy(EFFECTIVE),
                     'runtime': copy.deepcopy(P['runtime'])}
            if self.model_mutation:
                self.model_mutation(value)
            self.queue.append(value)
        elif op == 'BIND':
            self.binding = {**BINDING, 'subject_sha256': arg}
            self.queue.append({'record_type': 'q3_bound_v1', 'binding': self.binding})
        elif op == 'PREPARE':
            assert self.life.active is None, 'next task started before watchdog closure'
            task = next(t for t in FRAME if t['task_id'] == arg)
            self.slot = {k: task[k] for k in ('task_id', 'ordinal', 'continuation_ordinal', 'attempt')}
            self.queue.append({'record_type': 'q3_slot_ready_v1', 'binding': self.binding,
                               'slot': self.slot, 'input_ids': [1, 4],
                               'effective_generation': EFFECTIVE, 'runtime': P['runtime']})
        elif op == 'GENERATE':
            assert arg != FULL[0]['task_id']
            self.generated.append(arg)
            text = '' if len(self.generated) % 2 == 0 else 'synthetic bounded response'
            ids = [2] if len(self.generated) % 2 == 0 else [4] * 256
            value = {'record_type': 'q3_response_v1', 'binding': self.binding, 'slot': self.slot,
                     'input_ids': [1, 4], 'new_token_ids': ids, 'text': text,
                     'text_utf8_base64': base64.b64encode(text.encode()).decode(),
                     'stop_reason': 'eos' if ids[-1] == 2 else 'token_limit',
                     'effective_generation': EFFECTIVE, 'runtime': P['runtime']}
            if self.mutation and len(self.generated) == 1:
                self.mutation(value)
            self.queue.append(value)
        elif op == 'FINISH':
            self.queue.append({'record_type': 'q3_session_end_v1', 'binding': self.binding,
                               'completed_calls': 203})
        else:
            raise AssertionError(command)
        return stamp


def run_synthetic(tmp_path, monkeypatch, mutation=None, fail_watchdog=False, model_mutation=None):
    clock = Clock()
    monkeypatch.setattr(A.time, 'monotonic', clock.seconds)
    monkeypatch.setattr(A.time, 'monotonic_ns', clock.ns)
    life = Life(clock, fail_watchdog)
    mapping = W.tokenize_frame(Tokenizer(), FULL, P)
    service = Service(clock, life, mapping, mutation, model_mutation)
    terminal = {'attempted_calls': 0, 'occurrences': [
        {**{k: t[k] for k in ('task_id', 'ordinal', 'continuation_ordinal', 'attempt')}, 'status': 'not_started'}
        for t in FRAME]}
    def invoke():
        return A.exchange_capture(C, R, K, life, service, P, FRAME, mapping,
                                  BINDING, tmp_path, terminal, PREFIX, 'c' * 64)
    return invoke, service, terminal, life


def test_caps_continue_only_after_closure_and_exact_203_suffix(tmp_path, monkeypatch):
    invoke, service, terminal, life = run_synthetic(tmp_path, monkeypatch)
    invoke()
    assert service.generated == [t['task_id'] for t in FRAME]
    assert len(service.generated) == terminal['attempted_calls'] == len(life.closed) == 203
    assert service.generated[0] == 'Q3P2-043-A' and service.generated[-1] == 'Q3P2-063-L'
    assert FULL[0]['task_id'] not in service.generated
    assert terminal['occurrences'][0]['status'] == 'length_terminated'
    assert terminal['occurrences'][1]['status'] == 'completed'
    assert [o['ordinal'] for o in terminal['occurrences']] == list(range(2, 205))
    assert [o['continuation_ordinal'] for o in terminal['occurrences']] == list(range(1, 204))
    assert life.closed[0].endswith('-call-002') and life.closed[-1].endswith('-call-204')
    assert json.loads((tmp_path / 'session-end.json').read_bytes())['completed_calls'] == 203
    assert json.loads((tmp_path / 'subject.json').read_bytes())['historical_verification_sha256'] == 'c' * 64
    assert (tmp_path / ('calls/' + FRAME[1]['task_id'] + '.utf8')).read_bytes() == b''


@pytest.mark.parametrize('fault', ['early_cap', 'embedded_eos', 'bad_base64', 'wrong_binding',
                                  'first_task', 'bad_ordinal', 'bad_continuation', 'changed_input',
                                  'changed_runtime', 'extra_field', 'noninteger_token'])
def test_invalid_response_is_preserved_without_second_attempt(tmp_path, monkeypatch, fault):
    def mutation(value):
        if fault == 'early_cap': value['new_token_ids'] = [4] * 255
        elif fault == 'embedded_eos': value['new_token_ids'][5] = 2
        elif fault == 'bad_base64': value['text_utf8_base64'] = 'AAAA'
        elif fault == 'wrong_binding': value['binding'] = {**value['binding'], 'source_commit': 'f' * 40}
        elif fault == 'first_task': value['slot'] = {**value['slot'], 'task_id': FULL[0]['task_id']}
        elif fault == 'bad_ordinal': value['slot'] = {**value['slot'], 'ordinal': 1}
        elif fault == 'bad_continuation': value['slot'] = {**value['slot'], 'continuation_ordinal': 2}
        elif fault == 'changed_input': value['input_ids'] = [1, 5]
        elif fault == 'changed_runtime': value['runtime'] = {**value['runtime'], 'threads': 2}
        elif fault == 'extra_field': value['override'] = True
        elif fault == 'noninteger_token': value['new_token_ids'][0] = True
    invoke, service, terminal, life = run_synthetic(tmp_path, monkeypatch, mutation)
    with pytest.raises(ValueError): invoke()
    assert service.generated == [FRAME[0]['task_id']]
    assert terminal['attempted_calls'] == 1
    assert (tmp_path / ('calls/' + FRAME[0]['task_id'] + '.response.json')).is_file()
    assert not (tmp_path / 'session-end.json').exists()


def test_uncertain_watchdog_closure_blocks_next_occurrence(tmp_path, monkeypatch):
    invoke, service, terminal, life = run_synthetic(tmp_path, monkeypatch, fail_watchdog=True)
    with pytest.raises(ValueError, match='WATCHDOG_UNCLOSED'): invoke()
    assert len(service.generated) == terminal['attempted_calls'] == 1
    assert life.active and not life.closed
    assert (tmp_path / ('calls/' + FRAME[0]['task_id'] + '.response.json')).is_file()


@pytest.mark.parametrize('fault', ['config', 'runtime'])
def test_changed_subject_rejected_before_first_generate(tmp_path, monkeypatch, fault):
    def mutation(value):
        if fault == 'config': value['effective_generation']['renormalize_logits'] = True
        else: value['runtime']['threads'] = 2
    invoke, service, terminal, life = run_synthetic(tmp_path, monkeypatch, model_mutation=mutation)
    with pytest.raises(ValueError): invoke()
    assert service.generated == [] and terminal['attempted_calls'] == 0 and life.active is None


def synthetic_metadata():
    plan = C.load_amendment(ROOT)
    old = plan['historical_capture']
    run = {'id': int(old['run_id']), 'run_attempt': 1, 'head_sha': old['source_commit'],
           'head_branch': 'main', 'event': 'workflow_dispatch', 'status': 'completed',
           'conclusion': 'failure', 'path': '.github/workflows/q3_reference_acquisition_v0.yml',
           'actor': {'login': 'HKati'}, 'triggering_actor': {'login': 'HKati'},
           'repository': {'full_name': C.REPOSITORY}}
    jobs = {'total_count': 1, 'jobs': [{'id': old['job_id'], 'run_id': int(old['run_id']),
             'run_attempt': 1, 'head_sha': old['source_commit'], 'name': 'acquire',
             'status': 'completed', 'conclusion': 'failure'}]}
    def artifact(key):
        fixed = old[key]
        return {'id': fixed['artifact_id'], 'name': fixed['name'], 'expired': False,
                'size_in_bytes': fixed['size_bytes'], 'digest': 'sha256:' + fixed['sha256'],
                'workflow_run': {'id': int(old['run_id']), 'head_sha': old['source_commit']},
                'expires_at': '2099-01-01T00:00:00Z'}
    return plan, run, jobs, artifact('capture_artifact'), artifact('runner_image_artifact')


def test_selected_historical_failure_is_expected_not_promoted():
    plan, *rows = synthetic_metadata()
    result = A.historical_metadata(C, plan, *(C.encode(x) for x in rows))
    assert result['run_conclusion'] == result['job_conclusion'] == 'failure'
    assert result['run_id'] == '42928275426'


@pytest.mark.parametrize('fault', ['retried', 'expired', 'other_source', 'other_job', 'other_artifact', 'extra_job', 'success'])
def test_wrong_history_rejected_before_download(fault):
    plan, run, jobs, artifact, image = synthetic_metadata()
    if fault == 'retried': run['run_attempt'] = 2
    elif fault == 'expired': artifact['expired'] = True
    elif fault == 'other_source': run['head_sha'] = 'a' * 40
    elif fault == 'other_job': jobs['jobs'][0]['id'] += 1
    elif fault == 'other_artifact': artifact['digest'] = 'sha256:' + 'a' * 64
    elif fault == 'extra_job': jobs['total_count'] = 2
    elif fault == 'success': run['conclusion'] = 'success'
    with pytest.raises(ValueError):
        A.historical_metadata(C, plan, *(C.encode(x) for x in (run, jobs, artifact, image)))


def test_versioned_runtime_keeps_bounds_and_adds_only_zero_generation_stage():
    old = module('q3_native_runtime_v0')
    assert R.PROPERTIES == old.PROPERTIES
    assert R.STAGES == {**old.STAGES, 'historicalcheck': 300}
    assert R.CAPTURE_STAGES == old.CAPTURE_STAGES == {}


def test_new_workflow_manual_only_shared_concurrency_no_retries_or_write_token():
    workflow = yaml.safe_load((ROOT / C.WORKFLOW).read_text())
    old = yaml.safe_load((ROOT / '.github/workflows/q3_reference_acquisition_v0.yml').read_text())
    trigger = workflow.get('on', workflow.get(True))
    assert set(trigger) == {'workflow_dispatch'}
    assert workflow['concurrency'] == old['concurrency']
    job = workflow['jobs']['acquire']
    assert job['timeout-minutes'] == 270
    assert job['permissions'] == {'contents': 'read', 'actions': 'read'}
    runsteps = [x['run'] for x in job['steps'] if 'run' in x]
    text = '\n'.join(runsteps)
    assert 'acquire_q3_reference_inputs_v1.py' in text
    assert 'acquire_q3_reference_inputs_v0.py' not in text
    for guard in ['GITHUB_ACTOR', 'GITHUB_TRIGGERING_ACTOR', 'GITHUB_RUN_ATTEMPT', 'GITHUB_REF', 'GITHUB_WORKFLOW_SHA']:
        assert guard in text
    for step in job['steps']:
        if 'uses' in step:
            assert len(step['uses'].rsplit('@', 1)[1]) == 40
        if step.get('uses', '').startswith('actions/upload-artifact@'):
            assert step['with']['overwrite'] is False
            assert step['with']['retention-days'] == 30
