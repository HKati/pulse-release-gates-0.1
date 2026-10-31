#!/usr/bin/env python3
"""Bounded W1 wire protocol and record assembly. No candidate execution.

Records originate in trusted primitive instrumentation and a separate collector.
This module validates their bindings; it is not a platform attestation verifier.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from typing import Any

MAX_FRAME = 65536
MAX_TRANSCRIPT = 512 * 1024
MAX_FRAMES = 384
ORDER = ('P00', 'N01', 'N07', 'N08', 'N02')
SUBJECT = 'pd_sm_02_w1_diagnostic_healthy_v0'
RUNTIME = {'implementation': 'CPython', 'version': '3.13.5', 'system': 'Linux', 'machine': 'x86_64'}

class CaptureError(ValueError):
    pass

def need(ok: bool, code: str) -> None:
    if not ok:
        raise CaptureError(code)

def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')

def strict(raw: bytes, maximum: int = MAX_TRANSCRIPT) -> Any:
    need(type(raw) is bytes and len(raw) <= maximum and not raw.startswith(b'\xef\xbb\xbf'), 'json_size_or_bom')
    def pairs(items):
        out = {}
        for k, v in items:
            need(k not in out, 'duplicate_json_key')
            out[k] = v
        return out
    def walk(v, depth=0):
        need(depth <= 48, 'json_depth')
        if type(v) is float:
            need(math.isfinite(v), 'nonfinite_json')
        elif type(v) is str:
            v.encode('utf-8')
        elif type(v) is list:
            for x in v: walk(x, depth + 1)
        elif type(v) is dict:
            for k, x in v.items(): k.encode('utf-8'); walk(x, depth + 1)
    try:
        v = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(CaptureError('nonfinite_json')))
        walk(v)
        return v
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CaptureError('invalid_json') from exc

def keys(value, expected, code):
    need(type(value) is dict and set(value) == set(expected), code)

def number(v, lo, hi, code):
    need(type(v) is int and lo <= v <= hi, code)

def hex_bytes(s, maximum, code):
    need(type(s) is str and len(s) <= 2 * maximum and re.fullmatch(r'(?:[0-9a-f]{2})*', s) is not None, code)
    return bytes.fromhex(s)

def not_run(row):
    return {'case_id': row['case_id'], 'candidate_sha256': row['candidate_raw_sha256'],
            'context_sha256': row['context_canonical_sha256'], 'scenario': 'healthy',
            'attempt': 1, 'status': 'NOT_RUN', 'processes': None, 'events': [],
            'message_links': [], 'sink_hex': None, 'audit_hex': None}

def input_case(row):
    """A runtime sees source, context and operations, never expected verdicts."""
    return {k: row[k] for k in ('case_id', 'candidate_source', 'candidate_raw_sha256',
                               'context', 'context_canonical_sha256', 'operations')}

def observation(selection, run_id, identities):
    return {'schema_version': 'pd_sm_02_w1_observation_record_v0', 'subject': SUBJECT,
            'evidence_origin': 'unverified_observation_record', 'run_id': run_id,
            'attempt': 1, 'selection_sha256': 'a04ff29eba4fda99e575f1984bfa9e91622fdd02d4ddfb2e01966e25967d5620',
            'source_binding_sha256': 'b43c3995b0661d828b5e433c1041c28ee5a9bf4d99ebe095b1d1f0bd892010c3',
            'runtime': dict(RUNTIME), 'identities': identities,
            'cases': [not_run(row) for row in selection['cases']]}

def parse_frames(raw: bytes) -> list[dict]:
    need(type(raw) is bytes and len(raw) <= MAX_TRANSCRIPT, 'transcript_size')
    need(not raw or raw.endswith(b'\n'), 'truncated_frame')
    lines = raw.splitlines()
    need(len(lines) <= MAX_FRAMES and all(lines), 'frame_inventory')
    return [strict(line, MAX_FRAME) for line in lines]

def assemble_case(frames: list[dict], row: dict, run_id: str) -> dict:
    """Require actual-operation telemetry and collector wait/file closure.

    This is syntactic/protocol correspondence, not independent kernel attestation.
    The unchanged W1 checker performs semantic/prefix evaluation afterwards.
    """
    need(type(frames) is list and 0 < len(frames) <= MAX_FRAMES, 'frame_inventory')
    events, io_rows, spawns, waits = [], [], [], []
    capture = None
    stdio = {'stdout':bytearray(), 'stderr':bytearray()}
    for i, f in enumerate(frames):
        need(type(f) is dict and type(f.get('frame')) is str, 'frame_shape')
        kind = f['frame']
        if kind == 'spawn':
            keys(f, {'frame', 'role', 'pid', 'parent_pid'}, 'spawn_shape')
            need(f['role'] in ('worker', 'monitor'), 'spawn_role')
            number(f['pid'], 1, 2**31-1, 'spawn_pid'); number(f['parent_pid'], 1, 2**31-1, 'spawn_parent')
            need(not any(x['role'] == f['role'] for x in spawns), 'duplicate_spawn')
            spawns.append(f)
        elif kind == 'event':
            keys(f, {'frame', 'pid', 'event'}, 'event_frame_shape')
            number(f['pid'], 1, 2**31-1, 'event_pid')
            e = f['event']
            keys(e, {'event_id', 'run_id', 'case_id', 'attempt', 'process', 'sequence', 'operation_index', 'kind', 'data'}, 'event_shape')
            need(e['run_id'] == run_id and e['case_id'] == row['case_id'] and type(e['attempt']) is int and e['attempt'] == 1, 'event_subject')
            events.append(f)
        elif kind == 'io':
            keys(f, {'frame', 'pid', 'operation_index', 'surface', 'bytes_hex', 'write_return', 'fsync_return'}, 'io_shape')
            number(f['pid'], 1, 2**31-1, 'io_pid')
            number(f['operation_index'], 0, len(row['operations']) - 1, 'io_operation')
            need(f['surface'] in ('sink', 'audit'), 'io_surface')
            raw = hex_bytes(f['bytes_hex'], 4096, 'io_bytes')
            number(f['write_return'], 0, 4096, 'io_write_return')
            need(len(raw) == f['write_return'], 'io_byte_count')
            need(f['fsync_return'] is None or type(f['fsync_return']) is int and f['fsync_return'] == 0, 'io_fsync')
            io_rows.append(f)
        elif kind == 'monitor_wait':
            keys(f, {'frame', 'pid', 'child_pid', 'wait_status'}, 'monitor_wait_shape')
            number(f['pid'], 1, 2**31-1, 'wait_pid'); number(f['child_pid'], 1, 2**31-1, 'wait_child')
            number(f['wait_status'], 0, 65535, 'wait_status'); waits.append(f)
        elif kind == 'stdio':
            keys(f, {'frame','channel','bytes_hex'}, 'stdio_shape')
            need(f['channel'] in stdio, 'stdio_channel')
            stdio[f['channel']].extend(hex_bytes(f['bytes_hex'],8192,'stdio_bytes'))
            need(len(stdio[f['channel']])<=65536, 'stdio_limit')
        elif kind == 'capture':
            keys(f, {'frame', 'supervisor_pid', 'worker_pid', 'wait_status', 'sink_hex', 'audit_hex',
                     'worker_reaped', 'event_eof', 'scratch_entries', 'stdout_hex', 'stderr_hex'}, 'capture_shape')
            need(capture is None and i == len(frames)-1, 'capture_position')
            capture = f
        else:
            raise CaptureError('unknown_runtime_frame')
    need(capture is not None, 'missing_capture')
    hex_bytes(capture['stdout_hex'], 65536, 'candidate_stdout')
    hex_bytes(capture['stderr_hex'], 65536, 'candidate_stderr')
    number(capture['supervisor_pid'], 1, 2**31-1, 'supervisor_pid')
    need(capture['worker_reaped'] is True and capture['event_eof'] is True, 'collector_incomplete')
    need(type(capture['scratch_entries']) is list and set(capture['scratch_entries']) <= {'sink.bin', 'audit.jsonl'}
         and len(capture['scratch_entries']) == len(set(capture['scratch_entries'])), 'scratch_inventory')
    proc = {'worker': None, 'monitor': None, 'supervisor': capture['supervisor_pid']}
    for f in spawns: proc[f['role']] = f['pid']
    need(proc['worker'] == capture['worker_pid'] and proc['worker'] is not None, 'worker_spawn_binding')
    need(len([v for v in proc.values() if v is not None]) == len(set(v for v in proc.values() if v is not None)), 'pid_collision')
    for f in spawns:
        need(f['parent_pid'] == proc['supervisor' if f['role'] == 'worker' else 'worker'], 'spawn_parent_binding')
    number(capture['wait_status'], 0, 65535, 'worker_wait_type')
    number(capture['worker_pid'], 1, 2**31-1, 'capture_worker_pid')
    need(capture['wait_status'] in (0, 256), 'abnormal_worker_exit')
    need(all(bytes(raw).hex()==capture[name+'_hex'] for name,raw in stdio.items()), 'stdio_capture_binding')
    need(not any(stdio.values()), 'unexpected_candidate_stdio')
    for f in events: need(f['event']['process'] in proc and f['pid'] == proc[f['event']['process']], 'event_process_binding')
    if proc['monitor'] is not None:
        need(len(waits) == 1 and waits[0]['pid'] == proc['worker'] and waits[0]['child_pid'] == proc['monitor']
             and waits[0]['wait_status'] == 0, 'monitor_wait_binding')
    else: need(not waits, 'unexpected_monitor_wait')
    es = [f['event'] for f in events]
    terminals = [e for e in es if e['kind'] == 'candidate_terminal']
    need(len(terminals) == 1 and terminals[0]['data']['exit_code'] == capture['wait_status'] >> 8, 'wait_terminal_binding')
    # Exactly one I/O telemetry row must justify each recorded write, in operation order.
    writes = [e for e in es if e['kind'] in ('sink_write_completed', 'intent_persisted')]
    need(len(writes) == len(io_rows), 'io_inventory')
    unmatched = list(io_rows)
    for e in writes:
        surface = 'sink' if e['kind'] == 'sink_write_completed' else 'audit'
        candidates = [f for f in unmatched if f['surface'] == surface and f['operation_index'] == e['operation_index'] and f['pid'] == proc[e['process']]]
        need(len(candidates) == 1, 'io_operation_binding')
        f = candidates[0]; unmatched.remove(f)
        field = 'bytes_hex' if surface == 'sink' else 'record_hex'
        need(f['bytes_hex'] == e['data'][field] and f['write_return'] == e['data']['write_return'], 'io_event_binding')
        if surface == 'audit': need(f['fsync_return'] == e['data']['fsync_return'] == 0, 'audit_persistence_binding')
    links = []
    for channel in ('request', 'ack'):
        send = [e for e in es if e['kind'] == channel + '_send']
        recv = [e for e in es if e['kind'] == channel + '_receive']
        need(len(send) == len(recv) and len(send) <= 1, 'message_pair_inventory')
        if send:
            raw = hex_bytes(send[0]['data']['payload_hex'], 2048, 'message_bytes')
            need(recv[0]['data']['payload_hex'] == raw.hex(), 'message_byte_match')
            links.append({'channel': channel, 'send': send[0]['event_id'], 'receive': recv[0]['event_id'], 'payload_sha256': digest(raw)})
    case = not_run(row)
    case.update(status='COMPLETE', processes=proc, events=es, message_links=links,
                sink_hex=capture['sink_hex'], audit_hex=capture['audit_hex'])
    return case
