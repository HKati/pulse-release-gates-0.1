#!/usr/bin/env python3
"""Consume one bounded checker result into a new non-authoritative reference state.

This deliberately separate, standard-library-only process reads the exact
sealed result/stream/pending-state inputs. It neither executes the checker nor
turns its own successful completion into a release ALLOW.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys

VERSION = 'pulsemech_compute_bounded_execution_evidence_v0'
LIMIT = 2 * 1024 * 1024
CASES = ('allow', 'block_false', 'missing_required')


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('invalid_json_number')
    if not isinstance(raw, bytes) or len(raw) > LIMIT:
        raise ValueError('input_limit')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                       parse_constant=invalid, parse_float=invalid)
    if not isinstance(value, dict) or canonical(value) != raw:
        raise ValueError('noncanonical_object')
    return value


def read_sealed(path: str) -> bytes:
    # Only descriptors passed by the fixed supervisor are accepted. Never open
    # an arbitrary filesystem input to silently replace the sealed-input path.
    if not re.fullmatch(r'/proc/self/fd/[3-9][0-9]*|/proc/self/fd/[12][0-9]+', path):
        raise ValueError('sealed_descriptor_required')
    fd = int(path.rsplit('/', 1)[1])
    import fcntl
    required = (fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW |
                fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_size > LIMIT:
        raise ValueError('input_limit_or_type')
    if fcntl.fcntl(fd, fcntl.F_GET_SEALS) & required != required:
        raise ValueError('input_not_sealed')
    raw = os.pread(fd, st.st_size + 1, 0)
    if len(raw) != st.st_size:
        raise ValueError('input_size_changed')
    return raw


def consume(*, result_raw: bytes, stdout_raw: bytes, stderr_raw: bytes,
            pending_raw: bytes, context_sha256: str, prelaunch_sha256: str,
            case_id: str, checker_execution_id: str) -> bytes:
    if checker_execution_id != f'execution:{case_id}:checker':
        raise ValueError('expected_checker_occurrence')
    if case_id not in CASES or not all(re.fullmatch('[0-9a-f]{64}', x)
                                     for x in (context_sha256, prelaunch_sha256)):
        raise ValueError('expected_identity_invalid')
    result, pending = parse(result_raw), parse(pending_raw)
    result_keys = {'schema_version','record_type','context_sha256','prelaunch_sha256',
                   'case_id','execution_id','invocation_sha256','exit_code','stdout',
                   'stderr','authority_effect'}
    pending_expected = {'schema_version':VERSION,'record_type':'pending_state',
                        'context_sha256':context_sha256,'case_id':case_id,
                        'state':'pending','authority_effect':'none'}
    if pending != pending_expected or set(result) != result_keys:
        raise ValueError('state_or_result_contract')
    for key, expected in {'schema_version':VERSION,'record_type':'process_result',
                          'context_sha256':context_sha256,
                          'prelaunch_sha256':prelaunch_sha256,'case_id':case_id,
                          'execution_id':checker_execution_id,
                          'authority_effect':'none'}.items():
        if result[key] != expected:
            raise ValueError('result_occurrence_mismatch:' + key)
    if not re.fullmatch('[0-9a-f]{64}', result['invocation_sha256']):
        raise ValueError('invocation_digest_invalid')
    for name, raw in [('stdout',stdout_raw),('stderr',stderr_raw)]:
        expected = {'member':f'results/{case_id}/checker.{name}',
                    'sha256':digest(raw),'size_bytes':len(raw)}
        if result[name] != expected:
            raise ValueError('consumed_stream_mismatch:' + name)
    code = result['exit_code']
    if type(code) is not int or code not in (0,1,2):
        raise ValueError('non_decision_result')
    return canonical({'schema_version':VERSION,'record_type':'terminal_state',
                      'context_sha256':context_sha256,'prelaunch_sha256':prelaunch_sha256,
                      'case_id':case_id,'checker_execution_id':checker_execution_id,
                      'state':'ready' if code == 0 else 'held',
                      'reason':('all_required_true','required_value_not_true',
                                'missing_or_invalid_required_input')[code],
                      'checker_exit_code':code,'result_sha256':digest(result_raw),
                      'pending_state_sha256':digest(pending_raw),
                      'checker_stdout_sha256':digest(stdout_raw),
                      'checker_stderr_sha256':digest(stderr_raw),'authority_effect':'none'})


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('result','stdout','stderr','pending','context-sha256','prelaunch-sha256',
                 'case-id','checker-execution-id'):
        p.add_argument('--' + name, required=True)
    args = p.parse_args(argv)
    try:
        output = consume(result_raw=read_sealed(args.result),stdout_raw=read_sealed(args.stdout),
                         stderr_raw=read_sealed(args.stderr),pending_raw=read_sealed(args.pending),
                         context_sha256=args.context_sha256,prelaunch_sha256=args.prelaunch_sha256,
                         case_id=args.case_id,checker_execution_id=args.checker_execution_id)
        sys.stdout.buffer.write(output)
        return 0
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as exc:
        # No input bytes or environment values are copied into diagnostics.
        print('bounded_result_rejected: ' + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
