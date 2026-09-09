#!/usr/bin/env python3
"""Observe only the three predeclared checker/consumer reference cases.

No arbitrary-command mode is provided. Sources and input states are verified
before use and passed through sealed Linux descriptors. Capture is an actual
local execution event; it is not a production release or host-wide observer.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack

# Isolated CLI operation must use this exact local verifier module, not a
# similarly named installed package or a working-directory shadow module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_pulsemech_compute_bounded_execution_v0 as verify

PROCESS_TIMEOUT_SECONDS = 10.0
STREAM_LIMIT_BYTES = verify.MEMBER_LIMIT


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def sealed_buffer(role: str, data: bytes) -> int:
    verify.need(sys.platform == 'linux' and hasattr(os,'memfd_create'), 'sealed_platform_unavailable')
    verify.need(isinstance(data,bytes) and len(data) <= verify.MEMBER_LIMIT, 'sealed_input_limit')
    fd = os.memfd_create('pulse-bounded-'+role, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd,view)
            verify.need(count > 0,'sealed_write_failed')
            view = view[count:]
        fcntl.fcntl(fd,fcntl.F_ADD_SEALS,
                    fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
        verify.need(fcntl.fcntl(fd,fcntl.F_GET_SEALS) == verify.SEALS, 'sealed_state_mismatch')
        os.lseek(fd,0,os.SEEK_SET)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_bounded_process(process: subprocess.Popen, deadline: float) -> tuple[bytes,bytes,int]:
    streams = {'stdout':bytearray(),'stderr':bytearray()}
    try:
        with selectors.DefaultSelector() as selector:
            for name in streams:
                pipe = getattr(process,name)
                os.set_blocking(pipe.fileno(),False)
                selector.register(pipe,selectors.EVENT_READ,name)
            while selector.get_map():
                remaining = deadline-time.monotonic()
                verify.need(remaining > 0, 'execution_timeout')
                for key,_ in selector.select(min(remaining,0.1)):
                    block = os.read(key.fileobj.fileno(),65536)
                    if not block:
                        selector.unregister(key.fileobj)
                        continue
                    streams[key.data].extend(block)
                    verify.need(len(streams[key.data]) <= STREAM_LIMIT_BYTES, 'execution_stream_limit')
            remaining = deadline-time.monotonic()
            verify.need(remaining > 0,'execution_timeout')
            try:
                code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise verify.EvidenceError('execution_timeout') from exc
            verify.need(0 <= code <= 255, 'execution_signal_termination')
            return bytes(streams['stdout']),bytes(streams['stderr']),code
    finally:
        if process.poll() is None:
            # Kill only the private session started for this owned child.
            try:
                os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        for name in streams:
            pipe = getattr(process,name)
            if pipe:
                pipe.close()


def interpreter_record() -> dict:
    verify.need(sys.implementation.name == 'cpython' and platform.system() == 'Linux',
                'interpreter_platform_unsupported')
    path = Path(sys.executable).resolve()
    raw = verify.read_regular(path,128*1024*1024)
    return {'path':str(path),'sha256':verify.sha(raw),'size_bytes':len(raw),
            'implementation':'cpython','version':platform.python_version(),
            'os':'Linux','architecture':platform.machine(),
            'environment':{'LC_ALL':'C.UTF-8','TZ':'UTC'},'flags':['-I','-S','-B']}


def run_execution(*, spec: dict, prelaunch_sha256: str, kind: str, case_id: str,
                  logical_inputs: dict[str,bytes], interpreter: dict, cwd: Path) -> tuple[dict,bytes,bytes]:
    verify.need(kind in ('checker','consumer') and case_id in verify.CASES,'execution_slot_invalid')
    with ExitStack() as stack:
        fds = {}
        for role,raw in sorted(logical_inputs.items()):
            fd = sealed_buffer(role,raw)
            stack.callback(os.close,fd)
            fds[role] = fd
        sealed = [{'logical_role':role,'fd':fd,'sha256':verify.sha(logical_inputs[role]),
                   'size_bytes':len(logical_inputs[role]),'seal_mask':fcntl.fcntl(fd,fcntl.F_GET_SEALS)}
                  for role,fd in sorted(fds.items())]
        row = {'execution_id':f'execution:{case_id}:{kind}','case_id':case_id,'kind':kind,
               'source_path':verify.CHECKER if kind=='checker' else verify.CONSUMER,
               'source_sha256':verify.sha(logical_inputs['source']),'sealed_inputs':sealed}
        row['arguments'] = verify._expected_arguments(spec,prelaunch_sha256,row)
        row['started_at_utc'] = utc_now()
        row['start_monotonic_ns'] = time.monotonic_ns()
        deadline = time.monotonic()+PROCESS_TIMEOUT_SECONDS
        try:
            child = subprocess.Popen([interpreter['path'],*row['arguments']],
                                     stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,env=interpreter['environment'],
                                     cwd=cwd,pass_fds=tuple(fds.values()),close_fds=True,
                                     shell=False,start_new_session=True)
        except OSError as exc:
            raise verify.EvidenceError('execution_launch_failed') from exc
        row['pid'] = child.pid
        out,err,code = _read_bounded_process(child,deadline)
        row['end_monotonic_ns'] = time.monotonic_ns()
        row['completed_at_utc'] = utc_now()
        row['exit_code'] = code
        row['stdout_eof'] = row['stderr_eof'] = True
        outpath = 'checker.stdout' if kind=='checker' else 'terminal_state.json'
        errpath = 'checker.stderr' if kind=='checker' else 'consumer.stderr'
        row['stdout'] = verify.descriptor(f'results/{case_id}/'+outpath,out)
        row['stderr'] = verify.descriptor(f'results/{case_id}/'+errpath,err)
        return row,out,err


def capture(prepared_bytes: bytes, *, repository_root: Path, expected_context: dict,
            expected_prelaunch_sha256: str) -> bytes:
    members = verify.unpack(prepared_bytes)
    spec = verify.verify_prelaunch(members,repository_root=repository_root,
        expected_context=expected_context,expected_prelaunch_sha256=expected_prelaunch_sha256)
    expected_names = {'prelaunch.json'} | {'sources/'+p for p in verify.SOURCE_PATHS}
    expected_names |= {x['member'] for x in spec['input_inventory']}
    verify.need(set(members) == expected_names,'preparation_unexpected_member')
    verify.need(Path(__file__).absolute() == Path(repository_root).absolute()/verify.CAPTURE,
                'capture_entrypoint_path_mismatch')
    verify.need(verify.read_regular(Path(__file__),verify.MEMBER_LIMIT) == members['sources/'+verify.CAPTURE],
                'capture_entrypoint_source_mismatch')
    runtime = interpreter_record()
    started = utc_now()
    executions = []
    with tempfile.TemporaryDirectory(prefix='pulse-bounded-execution-') as directory:
        for case in spec['cases']:
            caseid = case['case_id']
            checkrow,out,err = run_execution(spec=spec,prelaunch_sha256=expected_prelaunch_sha256,
                kind='checker',case_id=caseid,interpreter=runtime,cwd=Path(directory),
                logical_inputs={'source':members['sources/'+verify.CHECKER],
                                'status':members[case['status']['member']]})
            members[case['checker_outputs']['stdout']] = out
            members[case['checker_outputs']['stderr']] = err
            envelope = verify.canonical(verify.process_result(spec,expected_prelaunch_sha256,checkrow))
            members[case['checker_outputs']['result_envelope']] = envelope
            executions.append(checkrow)
            consrow,term,diag = run_execution(spec=spec,prelaunch_sha256=expected_prelaunch_sha256,
                kind='consumer',case_id=caseid,interpreter=runtime,cwd=Path(directory),
                logical_inputs={'source':members['sources/'+verify.CONSUMER],
                    'result':envelope,'stdout':out,'stderr':err,'pending':members[case['pending_state']['member']]})
            members[case['consumer_outputs']['terminal_state']] = term
            members[case['consumer_outputs']['stderr']] = diag
            executions.append(consrow)
    verify.need(interpreter_record() == runtime,'interpreter_changed_during_capture')
    record = {'schema_version':verify.VERSION,'record_type':'capture','context':spec['context'],
              'prelaunch_sha256':expected_prelaunch_sha256,'started_at_utc':started,
              'completed_at_utc':utc_now(),'interpreter':runtime,'executions':executions,
              'member_inventory':[verify.descriptor(n,b) for n,b in sorted(members.items())],
              'terminal_roles':sorted(name for c in spec['cases'] for name in c['consumer_outputs'].values()),
              'capture_status':'closed','authority_effect':'none'}
    members['capture.json'] = verify.canonical(record)
    carrier = verify.pack(members)
    # Publication requires independent offline reconstruction of this same byte
    # set. No recorder-side flag substitutes for that call.
    verify.verify_capture(carrier,repository_root=repository_root,expected_context=expected_context,
                          expected_prelaunch_sha256=expected_prelaunch_sha256)
    return carrier


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepared', required=True,type=Path)
    ap.add_argument('--expected-context',required=True,type=Path)
    ap.add_argument('--expected-prelaunch-sha256',required=True)
    ap.add_argument('--repository-root',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args = ap.parse_args(argv)
    try:
        carrier = capture(verify.read_regular(args.prepared),repository_root=args.repository_root,
                          expected_context=verify.parse(verify.read_regular(args.expected_context)),
                          expected_prelaunch_sha256=args.expected_prelaunch_sha256)
        verify.publish_new(args.output,carrier,repository_root=args.repository_root)
        print(verify.sha(carrier))
        return 0
    except (verify.EvidenceError,OSError,ValueError,KeyError,TypeError) as exc:
        code = str(exc) if isinstance(exc,verify.EvidenceError) else type(exc).__name__
        print('bounded_capture_rejected: '+code,file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
