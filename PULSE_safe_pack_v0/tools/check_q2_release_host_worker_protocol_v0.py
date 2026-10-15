#!/usr/bin/env python3
"""Q2-2/Q2-3 protocol reconstruction component, not a native-run dispatcher.

Consumes the unchanged worker/capture wire records under a separate context.
The independent old token/text and sandbox checks retain their original code.
No producer, worker, model, transport or installer is imported by this module.
A successful return is evidence reconstruction, never release authorization or
proof that a supplied observer record was actually acquired from a kernel.
The caller must separately establish source, capsule, observer and input origin.
"""
from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Callable, Any

SCOPE = 'q2_capsule_worker_protocol_v0'
REPOSITORY = 'HKati/pulse-release-gates-0.1'
# Separate manually dispatched native integration target.
WORKFLOW = '.github/workflows/q2_release_host_worker_verification_v0.yml'
PACK = 'PULSE_safe_pack_v0/'
OLD_CHECKER = PACK + 'tools/check_q2_reference_capture_v0.py'
NATIVE_CHECKER = PACK + 'tools/check_q2_reference_qualification_v0.py'
WORKER = PACK + 'tools/run_q2_reference_subject_v0.py'
WORKLOAD = PACK + 'examples/q2_reference_field_extraction_v0/requests.json'
WORKLOAD_SHA256 = 'fa0412c6a702e220e5d0c8b09a5e854fe35ac89d4801977eeee0f2a6e5cae997'
WORKER_SHA256 = '37c932272da1579c3e1bf821fb5bde671ae756ede99aceb7deac58c85ee4b172'
DEFINITION_SHA256 = '688773b81fcf4f105b8770bc2dde9a68baf78aa76224e5c544cd0656109b07a5'
# Filled from the restored, source-bound immutable helper bytes, not evidence.
PINNED_HELPERS = {'PULSE_safe_pack_v0/tools/check_q2_reference_capture_v0.py': '4264684325e511af668a3b4062336060dbbc07715cfd186dcc000655015b513f', 'PULSE_safe_pack_v0/tools/check_q2_reference_qualification_v0.py': '25a09b19baae853344e2e656c261267dda8514c484f8477e59d1b60897bf34cc'}
LIMITS = {'generation_seconds': 15, 'phase_seconds': 1200,
          'memory_bytes': 4294967296, 'tasks': 64, 'retries': 0}
RUNTIME = {'torch': '2.8.0+cpu', 'transformers': '4.57.6', 'device': 'cpu',
           'dtype': 'torch.float32', 'attention': 'eager', 'threads': 1,
           'interop_threads': 1, 'deterministic': True, 'evaluation': True,
           'model_class': 'LlamaForCausalLM', 'seed': 1729, 'model_defaults': False,
           'compile': False, 'quantization': 'none'}
NON_AUTHORITY = {'authority_effect': 'none', 'production_gate_eligible': False,
                 'active_gate_eligible': False, 'same_run_release_authority_eligible': False}
CONFIGURATION_SHA256 = '1c9bf603f74f0f616f3abfa452b4725921534ca3afbced3ad4d46abc5ec6ddc4'
CAPSULE_SHA256 = '3625a975b4794442fe47b7f5eceb8bee5ff4150ff30b495b1d2a609e8a165734'
MAX_JSON = 16 * 1024 * 1024
SHA = re.compile(r'[0-9a-f]{64}')
COMMIT = re.compile(r'[0-9a-f]{40}')
RUN = re.compile(r'[1-9][0-9]{0,23}')


class ProtocolError(ValueError):
    """A closed error code. Original evidence is not repaired or retried."""


def require(value: bool, code: str) -> None:
    if not value:
        raise ProtocolError(code)


def encode(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def same(actual: Any, expected: Any, code: str) -> None:
    # Python equality alone accepts True == 1 and False == 0.
    require(encode(actual) == encode(expected), code)


def integer(value: Any, lower: int, upper: int, code: str) -> None:
    require(type(value) is int and lower <= value <= upper, code)


def fields(value: Any, names: str, code: str) -> None:
    require(type(value) is dict and set(value) == set(names.split()), code)


def parse(raw: bytes, maximum: int = MAX_JSON) -> Any:
    require(type(raw) is bytes and 0 < len(raw) <= maximum and
            not raw.startswith(b'\xef\xbb\xbf'), 'json_bound')
    def pairs(items):
        out = {}
        for key, val in items:
            require(key not in out, 'duplicate_json_key')
            out[key] = val
        return out
    def bad(_):
        raise ProtocolError('nonfinite_json')
    try:
        result = json.loads(raw.decode('utf-8', 'strict'),
                            object_pairs_hook=pairs, parse_constant=bad)
        def visit(value, depth=0):
            require(depth <= 64, 'json_depth')
            if type(value) is str:
                value.encode('utf-8', 'strict')
            elif type(value) is float:
                require(math.isfinite(value), 'nonfinite_json')
            elif type(value) is list:
                for item in value: visit(item, depth + 1)
            elif type(value) is dict:
                for key, item in value.items():
                    visit(key, depth + 1); visit(item, depth + 1)
        visit(result)
        return result
    except ProtocolError:
        raise
    except (ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        raise ProtocolError('invalid_json') from exc


def held_read(path: Path, maximum: int = MAX_JSON) -> bytes:
    """No-follow ancestor walk; bounded, singly linked, stable regular file."""
    path = Path(path).absolute()
    require('..' not in path.parts and maximum > 0, 'file_path')
    dfd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    fd = None
    try:
        for part in path.parts[1:-1]:
            nfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                          dir_fd=dfd)
            os.close(dfd); dfd = nfd
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=dfd)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                0 <= before.st_size <= maximum, 'file_bound')
        out = bytearray()
        while len(out) <= maximum:
            chunk = os.read(fd, min(65536, maximum + 1 - len(out)))
            if not chunk: break
            out.extend(chunk)
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(len(out) == before.st_size and stamp(before) == stamp(os.fstat(fd)),
                'file_changed')
        return bytes(out)
    except OSError as exc:
        raise ProtocolError('file_unavailable') from exc
    finally:
        if fd is not None: os.close(fd)
        os.close(dfd)


def load_independent_helpers(source: Path):
    """Compile exactly held, independently pinned checker bytes; no sys.path edit."""
    modules = []
    for relative in (OLD_CHECKER, NATIVE_CHECKER):
        raw = held_read(Path(source) / relative)
        require(digest(raw) == PINNED_HELPERS[relative], 'helper_source_changed')
        spec = importlib.util.spec_from_file_location(
            '_q2_worker_protocol_' + Path(relative).stem, Path(source) / relative)
        require(spec is not None, 'helper_unavailable')
        module = importlib.util.module_from_spec(spec)
        exec(compile(raw, str(Path(source) / relative), 'exec'), module.__dict__)
        modules.append(module)
    return tuple(modules)


def fixed_slots(workload_raw: bytes) -> tuple[dict, list[dict]]:
    require(digest(workload_raw) == WORKLOAD_SHA256, 'workload_changed')
    workload = parse(workload_raw)
    require(len(workload['groups']) == 50 and len(workload['occurrence_inventory']) == 150,
            'workload_extent')
    slots = []
    for index, item in enumerate(workload['occurrence_inventory'], 1):
        number, repeat = (index - 1) // 3 + 1, (index - 1) % 3 + 1
        group = workload['groups'][number - 1]
        expected = {'ordinal': index, 'call_id': f'q2fx-{number:03d}-r{repeat:02d}',
                    'group_id': f'q2fx-{number:03d}', 'repeat_index': repeat,
                    'request_sha256': group['request_sha256']}
        same(item, expected, 'slot_inventory')
        slots.append({**expected, 'attempt': 1})
    return workload, slots


def check_admission(admission: dict, expected: dict) -> None:
    """An assertion of consent is not authorization; caller binds its origin."""
    fields(admission, 'scope repository workflow source_commit run_id run_attempt '
           'request_sha256 prelaunch_sha256 subject_sha256 transcript_sha256 '
           'effective_generation_sha256 capsule_sha256 observer_contract_sha256 lifecycle_sha256',
           'admission_fields')
    same(admission, expected, 'external_binding_mismatch')
    require(admission['scope'] == SCOPE and admission['repository'] == REPOSITORY and
            admission['workflow'] == WORKFLOW, 'admission_scope')
    require(type(admission['source_commit']) is str and
            COMMIT.fullmatch(admission['source_commit']) is not None, 'source_shape')
    require(type(admission['run_id']) is str and RUN.fullmatch(admission['run_id']) is not None,
            'run_shape')
    integer(admission['run_attempt'], 1, 1, 'run_attempt')
    for key in ('request_sha256', 'prelaunch_sha256', 'subject_sha256', 'transcript_sha256',
                'effective_generation_sha256', 'capsule_sha256', 'observer_contract_sha256', 'lifecycle_sha256'):
        require(type(admission[key]) is str and SHA.fullmatch(admission[key]) is not None,
                'digest_shape')


def check_lifecycle(life: dict, pre: dict, terminal: dict, ready: dict,
                    subject_raw: bytes, slots: list[dict], old, native, require_private_cleanup: bool = True) -> None:
    fields(life, 'record_type observation_basis launch_ns isolation_observed_ns exec_ns '
           'model_ready_received_ns bound_frame_base64 bound_received_ns commands stdout_eof_ns exit_observed_ns '
           'process_reaped_ns cleanup_completed_ns exit_code client_reaped '
           'sandbox cleanup source_recheck input_recheck private_tree_cleanup', 'lifecycle_fields')
    require(life['record_type'] == 'q2_worker_protocol_lifecycle_v0' and
            life['observation_basis'] == 'supplied_external_observer_records', 'lifecycle_type')
    ordered = [pre['phase_start_ns'], life['launch_ns'], life['isolation_observed_ns'],
               life['exec_ns'], life['model_ready_received_ns']]
    for left, right in zip(ordered, ordered[1:]):
        integer(right, left, pre['phase_deadline_ns'], 'pre_exec_order')
    require(life['launch_ns'] == terminal['worker_launch_ns'], 'launch_binding')
    require(type(life['bound_frame_base64']) is str and len(life['bound_frame_base64']) <= 4096, 'bound_frame_bound')
    try:
        bound_raw = base64.b64decode(life['bound_frame_base64'], validate=True)
    except (ValueError, TypeError) as exc:
        raise ProtocolError('bound_frame_invalid') from exc
    same(parse(bound_raw, 3072), {'record_type': 'q2_capture_bound_v0', 'binding': terminal['binding']}, 'bound_acknowledgement')
    integer(life['bound_received_ns'], life['model_ready_received_ns'], terminal['worker_deadline_ns'], 'bound_clock')
    old.capture_sandbox(life['sandbox'], 'captureworker', native)
    same(life['sandbox'], terminal['sandbox'], 'sandbox_binding')
    old.capture_cleanup_check(life['cleanup'], life['sandbox']['unit'])
    same(life['cleanup'], terminal['cleanup'], 'cleanup_binding')
    integer(life['exit_code'], 0, 0, 'worker_exit')
    require(life['client_reaped'] is True and life['source_recheck'] == 'unchanged' and
            life['input_recheck'] == 'unchanged' and life['private_tree_cleanup'] ==
            ('verified_removed' if require_private_cleanup else 'pending'),
            'terminal_evidence_missing')
    # The unchanged exchange stamps session_end_ns AFTER complete()/reap.
    # It is a closure-observation timestamp, not the frame-arrival time.
    tail = [life['stdout_eof_ns'], life['exit_observed_ns'], life['process_reaped_ns'],
            terminal['session_end_ns'], life['cleanup_completed_ns']]
    for left, right in zip(tail, tail[1:]):
        integer(right, left, pre['phase_deadline_ns'] + 180_000_000_000, 'terminal_order')
    require(life['process_reaped_ns'] <= terminal['worker_deadline_ns'], 'reap_late')
    commands = life['commands']
    require(type(commands) is list and len(commands) == 303, 'command_extent')
    expected_commands = ['EXEC\n', 'BIND ' + digest(subject_raw) + '\n']
    for slot in slots:
        expected_commands.extend(['PREPARE ' + slot['call_id'] + '\n',
                                  'GENERATE ' + slot['call_id'] + '\n'])
    expected_commands.append('FINISH\n')
    previous = life['isolation_observed_ns']
    for index, (command, text) in enumerate(zip(commands, expected_commands)):
        fields(command, 'command written_ns', 'command_fields')
        require(command['command'] == text, 'command_order')
        integer(command['written_ns'], previous, terminal['worker_deadline_ns'], 'command_clock')
        previous = command['written_ns']
        if index == 0: require(previous == life['exec_ns'], 'exec_binding')
        if index == 1: require(life['model_ready_received_ns'] <= previous <= life['bound_received_ns'], 'bind_before_ready')
        if index == 2: require(previous >= life['bound_received_ns'], 'prepare_before_bound')
    for index, occurrence in enumerate(terminal['occurrences']):
        prepare, generate = commands[2 + 2 * index:4 + 2 * index]
        require(prepare['written_ns'] <= occurrence['ready_received_ns'] <= generate['written_ns'] and
                generate['written_ns'] == occurrence['generation_start_ns'], 'go_receipt_binding')
    require(commands[-1]['written_ns'] >= terminal['occurrences'][-1]['watchdog_closed']['closed_ns'] and
            commands[-1]['written_ns'] <= life['stdout_eof_ns'], 'finish_order')


def verify_protocol(*, source: Path, workload_raw: bytes, admission: dict,
                    expected_admission: dict, prelaunch_raw: bytes, subject_raw: bytes,
                    model_ready_raw: bytes, transcript_raw: bytes, lifecycle: dict,
                    records: list[tuple[bytes, bytes]], configuration: dict,
                    tokenize: Callable[[list], list[int]], decode: Callable[[list[int]], str],
                    require_private_cleanup: bool = True) -> dict:
    """Reconstruct a complete protocol using independently supplied token functions.

    `records` order is (response bytes, slot-ready bytes), as in the existing
    independent capture checker. No native origin or actual tokenizer execution
    is inferred merely from passing Python callbacks or a successful result.
    The native adapter separately establishes source/capsule/observer origin.
    Pre-cleanup checking is explicitly incomplete and cannot imply final cleanup.
    """
    try:
        require(type(require_private_cleanup) is bool, 'cleanup_mode')
        check_admission(admission, expected_admission)
        for raw, key in ((prelaunch_raw, 'prelaunch_sha256'), (subject_raw, 'subject_sha256'),
                         (transcript_raw, 'transcript_sha256')):
            require(digest(raw) == admission[key], 'selected_evidence_changed')
        require(digest(encode(configuration)) == admission['effective_generation_sha256'] == CONFIGURATION_SHA256, 'configuration_changed')
        require(admission['capsule_sha256'] == CAPSULE_SHA256, 'capsule_changed')
        require(digest(encode(lifecycle)) == admission['lifecycle_sha256'], 'selected_lifecycle_changed')
        require(callable(tokenize) and callable(decode), 'tokenizer_unavailable')
        old, native = load_independent_helpers(source)
        workload, slots = fixed_slots(workload_raw)
        pre, subject, ready, terminal = map(parse, (prelaunch_raw, subject_raw, model_ready_raw, transcript_raw))
        fields(pre, 'record_type record_status scope context source_files slots planned_calls limits '
               'phase_start_ns phase_deadline_ns started_at request_sha256 capsule_sha256 '
               'observer_contract_sha256 authority_effect production_gate_eligible', 'prelaunch_fields')
        require(pre['record_type'] == 'q2_capture_prelaunch_v0' and pre['record_status'] == 'native' and
                pre['scope'] == SCOPE and pre['authority_effect'] == 'none' and
                pre['production_gate_eligible'] is False, 'prelaunch_scope')
        fields(pre['context'], 'repository workflow source_commit run_id run_attempt actor event origin', 'context_fields')
        for key in ('repository', 'workflow', 'source_commit', 'run_id', 'run_attempt'):
            same(pre['context'][key], admission[key], 'context_binding')
        require(pre['context']['actor'] == 'HKati' and pre['context']['event'] == 'workflow_dispatch' and
                pre['context']['origin'] == 'owner_dispatched_github_q2_capture', 'owner_context')
        for key in ('request_sha256', 'capsule_sha256', 'observer_contract_sha256'):
            same(pre[key], admission[key], 'input_binding')
        same(pre['limits'], LIMITS, 'limits_changed'); same(pre['slots'], slots, 'prelaunch_slots')
        integer(pre['planned_calls'], 150, 150, 'planned_calls')
        integer(pre['phase_start_ns'], 1, 2**63 - 1, 'phase_start')
        integer(pre['phase_deadline_ns'], pre['phase_start_ns'] + 1200_000_000_000,
                pre['phase_start_ns'] + 1200_000_000_000, 'phase_deadline')
        rows = pre['source_files']
        require(type(rows) is list and len(rows) == 4 and len({r['path'] for r in rows}) == 4,
                'worker_source_extent')
        required_sources = {WORKER: WORKER_SHA256, WORKLOAD: WORKLOAD_SHA256,
            PACK + 'profiles/q2_reference_subject_v0.json': 'e81a9dd0a5080d84dae8c4bbfc843b46510f580e74254c1aed0dddbe76375f3e',
            PACK + 'profiles/q2_reference_model_files_v0.json': '7df82db50a623326e12c333b69e5ef621c169bdddc663425fd8ed8e4be307de2'}
        require({r['path'] for r in rows} == set(required_sources), 'worker_source_scope')
        for row in rows:
            fields(row, 'path size sha256', 'worker_source_fields')
            raw = held_read(Path(source) / row['path'])
            integer(row['size'], len(raw), len(raw), 'worker_source_size')
            require(digest(raw) == row['sha256'] == required_sources[row['path']], 'worker_source_changed')
        fields(ready, 'record_type binding effective_generation runtime', 'ready_fields')
        identity = {key: admission[key] for key in ('prelaunch_sha256', 'source_commit', 'run_id', 'run_attempt')}
        require(ready['record_type'] == 'q2_capture_model_ready_v0', 'ready_type')
        same(ready['binding'], identity, 'ready_binding'); same(ready['runtime'], RUNTIME, 'ready_runtime')
        same(ready['effective_generation'], configuration, 'ready_configuration')
        fields(subject, 'record_type prelaunch_sha256 definition_sha256 worker_sha256 ready_sha256 '
               'effective_generation runtime authority_effect production_gate_eligible', 'subject_fields')
        require(subject['record_type'] == 'q2_capture_subject_v0' and
                subject['prelaunch_sha256'] == admission['prelaunch_sha256'] and
                subject['definition_sha256'] == DEFINITION_SHA256 and subject['worker_sha256'] == WORKER_SHA256 and
                subject['ready_sha256'] == digest(model_ready_raw) and subject['authority_effect'] == 'none' and
                subject['production_gate_eligible'] is False, 'subject_binding')
        same(subject['effective_generation'], configuration, 'subject_configuration')
        same(subject['runtime'], RUNTIME, 'subject_runtime')
        identity['subject_sha256'] = admission['subject_sha256']
        fields(terminal, 'record_type record_status status error_code binding occurrences worker_launch_ns '
               'worker_deadline_ns worker_exit_code session_end session_end_ns cleanup sandbox ended_at '
               'authority_effect production_gate_eligible', 'transcript_fields')
        require(terminal['record_type'] == 'q2_capture_transcript_v0' and terminal['record_status'] == 'native' and
                terminal['status'] == 'completed' and terminal['error_code'] is None and
                terminal['authority_effect'] == 'none' and terminal['production_gate_eligible'] is False,
                'protocol_incomplete')
        same(terminal['binding'], identity, 'transcript_binding')
        require(type(records) is list and len(records) == 150 and
                type(terminal['occurrences']) is list and len(terminal['occurrences']) == 150, 'record_extent')
        integer(terminal['worker_exit_code'], 0, 0, 'worker_exit')
        integer(terminal['worker_launch_ns'], pre['phase_start_ns'], pre['phase_deadline_ns'], 'worker_launch')
        integer(terminal['worker_deadline_ns'], terminal['worker_launch_ns'] + 1, pre['phase_deadline_ns'], 'worker_deadline')
        seconds = terminal['sandbox']['capture_runtime_seconds']; integer(seconds, 1, 1200, 'worker_seconds')
        require(terminal['worker_deadline_ns'] - terminal['worker_launch_ns'] == seconds * 1_000_000_000,
                'worker_duration')
        integer(terminal['session_end_ns'], terminal['worker_launch_ns'], terminal['worker_deadline_ns'], 'session_clock')
        same(terminal['session_end'], {'record_type': 'q2_capture_session_end_v0', 'binding': identity,
                                     'completed_calls': 150}, 'session_end')
        begin, end = datetime.fromisoformat(pre['started_at']), datetime.fromisoformat(terminal['ended_at'])
        require(begin.tzinfo is not None and end.tzinfo is not None and begin <= end, 'wall_clock')
        previous = lifecycle['model_ready_received_ns']
        groups = []
        prefix = terminal['sandbox']['unit'].removesuffix('-captureworker.service')
        for index, (slot, occurrence, pair) in enumerate(zip(slots, terminal['occurrences'], records)):
            fields(occurrence, 'slot status ready_received_ns generation_start_ns generation_deadline_ns '
                   'response_received_ns watchdog_arm_begin_ns watchdog_armed watchdog_unit watchdog_closed '
                   'ready response', 'occurrence_fields')
            require(occurrence['status'] == 'completed', 'incomplete_slot')
            same(occurrence['slot'], slot, 'slot_order')
            integer(occurrence['ready_received_ns'], previous, terminal['worker_deadline_ns'], 'ready_clock')
            integer(occurrence['generation_start_ns'], occurrence['ready_received_ns'], terminal['worker_deadline_ns'], 'go_clock')
            start = occurrence['generation_start_ns']; deadline = occurrence['generation_deadline_ns']
            integer(deadline, start + 15_000_000_000, start + 15_000_000_000, 'generation_window')
            require(deadline < min(terminal['worker_deadline_ns'], pre['phase_deadline_ns']), 'phase_window')
            integer(occurrence['response_received_ns'], start, deadline, 'late_response')
            integer(occurrence['watchdog_arm_begin_ns'], occurrence['ready_received_ns'], start, 'watchdog_clock')
            require(occurrence['watchdog_armed'] is True and
                    deadline < occurrence['watchdog_arm_begin_ns'] + 20_000_000_000, 'watchdog_window')
            timer = prefix + f'-call-{index + 1:03d}'
            require(occurrence['watchdog_unit'] == timer + '-watchdog.timer', 'watchdog_identity')
            next_at = terminal['occurrences'][index + 1]['ready_received_ns'] if index < 149 else terminal['session_end_ns']
            old.capture_watchdog_check(occurrence['watchdog_closed'], timer, occurrence['response_received_ns'], next_at)
            previous = occurrence['watchdog_closed']['closed_ns']
            require(type(pair) is tuple and len(pair) == 2, 'record_pair')
            response_raw, slot_ready_raw = pair
            for role, raw in (('response', response_raw), ('ready', slot_ready_raw)):
                binding = occurrence[role]
                fields(binding, 'path size sha256', 'record_binding_fields')
                require(binding['path'] == 'calls/' + slot['call_id'] + '.' + role + '.json', 'record_path')
                integer(binding['size'], len(raw), len(raw), 'record_size')
                require(binding['sha256'] == digest(raw), 'record_digest')
            response, slot_ready = parse(response_raw, 128 * 1024), parse(slot_ready_raw, 128 * 1024)
            request = workload['groups'][index // 3]['request']
            derived = old.capture_target_response(response, slot_ready, slot, identity,
                        tokenize, decode, request['messages'], configuration)
            if index % 3 == 0: groups.append({'group_id': slot['group_id'], 'responses': []})
            groups[-1]['responses'].append(derived)
        check_lifecycle(lifecycle, pre, terminal, ready, subject_raw, slots, old, native, require_private_cleanup)
        groups_raw = encode({'schema_version': 'q2_consistency_input_v0', 'record_status': 'archived_response_records',
            'extraction_profile': 'typed_final_answer_or_refusal_v0', 'grouping': {'method_id': 'exact_request_repeats_v0',
            'method_version': 'v0', 'seed': 0, 'sampling_parameters': {'repeats': 3}}, 'groups': groups})
        return {'record_type': 'q2_worker_protocol_reconstruction_v0', 'scope': SCOPE,
                'protocol_reconstructed': True, 'private_tree_cleanup_verified': require_private_cleanup, 'verified_slots': 150, 'groups_sha256': digest(groups_raw),
                'groups_bytes': groups_raw, 'native_origin_verified': False, 'release_authorized': False,
                'model_execution_reperformed': False, 'metric_pass': None,
                'clock_relation': 'not_verified', 'resource_measurement': 'unavailable',
                'claim_boundary': 'reconstruction_from_supplied_observer_records_and_token_functions', **NON_AUTHORITY}
    except ProtocolError:
        raise
    except Exception as exc:
        # No artifact text, tokens, model output or raw filesystem paths in errors.
        raise ProtocolError('protocol_evidence_rejected') from exc


def main(argv=None):
    """Do not expose an accidental successful no-op as native verification."""
    import sys
    sys.stderr.write('q2_worker_protocol_library_use_check_q2_release_host_worker_v0\n')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
