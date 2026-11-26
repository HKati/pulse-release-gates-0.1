#!/usr/bin/env python3
"""Instrumented W1 runtime, entered only by the external containment controller.

Never imports the old launcher. Compile the frozen UTF-8 source unchanged.
The candidate has only its fixed primitive namespace. Monitor and collector are
separate processes; instrumentation never reads predicted outcomes.
"""
from __future__ import annotations
import argparse
import ast
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import resource
import select
import selectors
import signal
import sys
import time

MAX_PIPE_FRAME = 4096

class RuntimeFailure(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def require(ok, code):
    if not ok: raise RuntimeFailure(code)

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def regular(path, limit):
    import stat
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        require(stat.S_ISREG(st.st_mode) and st.st_size <= limit, 'input_not_regular_or_large')
        with os.fdopen(fd, 'rb', closefd=False) as f: raw = f.read(limit + 1)
        require(len(raw) <= limit, 'input_size')
        return raw
    finally: os.close(fd)

def read_line(fd, timeout=5.0, maximum=4096):
    raw = bytearray(); deadline = time.monotonic() + timeout
    while not raw.endswith(b'\n'):
        left = deadline-time.monotonic()
        require(left > 0 and select.select([fd], [], [], left)[0], 'pipe_timeout')
        b = os.read(fd, 1)
        require(bool(b), 'pipe_eof'); raw.extend(b)
        require(len(raw) <= maximum, 'pipe_frame_limit')
    return bytes(raw)

def output(frame):
    raw = canonical(frame) + b'\n'
    require(len(raw) <= 65536, 'output_frame_limit')
    view = memoryview(raw)
    while view:
        n = os.write(1, view); require(n > 0, 'stdout_short_write'); view = view[n:]

class Emitter:
    def __init__(self, fd, run_id, case_id, role):
        self.fd, self.run_id, self.case_id, self.role = fd, run_id, case_id, role
        self.sequence = 0
    def frame(self, value):
        raw = canonical(value) + b'\n'
        require(len(raw) <= MAX_PIPE_FRAME, 'event_frame_limit')
        require(os.write(self.fd, raw) == len(raw), 'event_pipe_short_write')
    def event(self, kind, operation, data):
        self.sequence += 1
        event = {'event_id': self.role + '_' + str(self.sequence), 'run_id': self.run_id,
                 'case_id': self.case_id, 'attempt': 1, 'process': self.role,
                 'sequence': self.sequence, 'operation_index': operation, 'kind': kind, 'data': data}
        self.frame({'frame':'event', 'pid':os.getpid(), 'event':event})
        return event


def parse_source(raw, row, profile):
    """Parse independently; do not compile a bytes object or rewrite its AST."""
    require(sha(raw) == row['candidate_raw_sha256'] and raw == row['candidate_source'].encode('utf-8'), 'candidate_binding')
    require(len(raw) <= profile['candidate_language']['max_source_bytes'] and raw.endswith(b'\n')
            and not raw.startswith(b'\xef\xbb\xbf'), 'candidate_encoding')
    text = raw.decode('utf-8'); module = ast.parse(text)
    require(len(module.body)==1 and type(module.body[0]) is ast.FunctionDef, 'module_shape')
    f = module.body[0]; a=f.args
    require(f.name=='candidate' and not f.decorator_list and f.returns is None and
            not getattr(f,'type_params',[]) and not a.posonlyargs and not a.args and not a.vararg
            and not a.kwonlyargs and not a.kw_defaults and not a.kwarg and not a.defaults, 'function_shape')
    aliases={}; ops=[]; primitives=profile['candidate_language']['primitives']
    for st in f.body:
        if type(st) is ast.Assign:
            require(len(st.targets)==1 and type(st.targets[0]) is ast.Name and
                    type(st.value) is ast.Constant and type(st.value.value) is str, 'assignment_shape')
            name=st.targets[0].id
            require(name not in primitives and name not in aliases and not name.startswith('__'), 'alias_shadow')
            aliases[name]=st.value.value; continue
        require(type(st) is ast.Expr and type(st.value) is ast.Call, 'statement_shape')
        c=st.value
        require(type(c.func) is ast.Name and c.func.id in primitives and not c.keywords, 'call_shape')
        spec=primitives[c.func.id]; args=[]
        for arg in c.args:
            if type(arg) is ast.Constant and type(arg.value) is str: args.append(arg.value)
            elif type(arg) is ast.Name and arg.id in aliases: args.append(aliases[arg.id])
            else: raise RuntimeFailure('call_argument')
        require(len(args)==spec['arity'] and all(v in profile['domains'][domain] for v,domain in zip(args,spec['arg_domains'])), 'call_domain')
        ops.append({'index':len(ops), 'primitive':c.func.id,'args':args,'kind':spec['kind'],
                    'line':c.lineno,'column':c.col_offset,
                    'source_fragment_sha256':sha((ast.get_source_segment(text,st) or '').encode())})
    require(ops==row['operations'], 'operation_binding')
    return text


class Primitives:
    """Healthy-scenario primitive correspondence, with observed I/O telemetry.

    No ACK/audit/single-use guards are added to append_sink. Test backends may
    replace I/O in unit tests; there is no CLI backend or bypass parameter.
    """
    def __init__(self, row, profile, emitter, scratch, protocol):
        self.row=row; self.profile=profile; self.e=emitter; self.scratch=Path(scratch); self.O=protocol
        self.actor_name=None; self.request=None; self.used=set(); self.reserved=set()
        self.ack=None; self.audit=None; self.monitor_pid=None; self.operation=None
        self.sink=self.scratch/'sink.bin'; self.audit_path=self.scratch/'audit.jsonl'
        self.closure=set(row['context']['evidence']['facts'])
        while True:
            new=self.closure | {r['conclusion'] for r in row['context']['evidence']['rules'] if set(r['premises']) <= self.closure}
            if new==self.closure: break
            self.closure=new
    def actor(self, name): self.actor_name=name
    def bind_request(self, rid, target, payload):
        require(self.request is None, 'runtime_duplicate_request')
        self.request={'request_id':rid,'target':target,'payload':payload}
    def require_source(self, obligation): require(obligation in self.closure, 'runtime_source_not_justified')
    def require_request_match(self, rid):
        expected={k:self.row['context']['binding'][k] for k in ('request_id','target','payload')}
        require(self.request==expected and rid==expected['request_id'], 'runtime_request_mismatch')
    def require_unused(self, rid):
        require(self.request is not None and self.request['request_id']==rid, 'runtime_request_id')
        require(rid not in self.used, 'runtime_request_used')
    def reserve(self, rid):
        require(self.request is not None and self.request['request_id']==rid, 'runtime_reservation_request')
        self.used.add(rid); self.reserved.add(rid)
    def _monitor(self, reqfd, ackfd):
        em=Emitter(self.e.fd,self.e.run_id,self.e.case_id,'monitor')
        try:
            raw=read_line(reqfd); req=self.O.strict(raw)
            em.event('request_receive',self.operation,{'payload_hex':raw.hex()})
            intent=canonical({'event':'INTENT','request':req,'request_sha256':sha(canonical(req))})+b'\n'
            fd=os.open(self.audit_path,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
            try:
                n=os.write(fd,intent)
                require(n==len(intent),'audit_short_write')
                os.fsync(fd)
            finally: os.close(fd)
            em.frame({'frame':'io','pid':os.getpid(),'operation_index':self.operation,
                      'surface':'audit','bytes_hex':intent[:n].hex(),'write_return':n,'fsync_return':0})
            em.event('intent_persisted',self.operation,{'record_hex':intent.hex(),'write_return':n,'fsync_return':0})
            ack=canonical({'recorded':True,'request_sha256':sha(canonical(req))})+b'\n'
            count=os.write(ackfd,ack)
            em.event('ack_send',self.operation,{'payload_hex':ack[:count].hex()})
            os._exit(0)
        except BaseException:
            os._exit(90)
    def broker_request(self, actor, rid):
        require(self.monitor_pid is None,'runtime_monitor_capacity')
        require(self.actor_name==actor,'runtime_actor_binding')
        require(self.request is not None and self.request['request_id']==rid,'runtime_request_id')
        rr,rw=os.pipe(); ar,aw=os.pipe(); pid=os.fork()
        if pid==0:
            os.close(rw); os.close(ar); self._monitor(rr,aw)
        os.close(rr); os.close(aw)
        self.e.frame({'frame':'spawn','role':'monitor','pid':pid,'parent_pid':os.getpid()})
        try:
            raw=canonical(self.request)+b'\n'; count=os.write(rw,raw)
            self.e.event('request_send',self.operation,{'payload_hex':raw[:count].hex()})
            os.close(rw);rw=-1
            ack=read_line(ar)
            self.e.event('ack_receive',self.operation,{'payload_hex':ack.hex()})
            self.ack=self.O.strict(ack)
            child,status=os.waitpid(pid,0); self.monitor_pid=pid
            self.e.frame({'frame':'monitor_wait','pid':os.getpid(),'child_pid':child,'wait_status':status})
            require(os.WIFEXITED(status) and os.WEXITSTATUS(status)==0,'runtime_monitor_failed')
            records=[self.O.strict(line+b'\n') for line in self.audit_path.read_bytes().splitlines()]
            self.audit=records[0]['request'] if len(records)==1 else None
        finally:
            if rw>=0: os.close(rw)
            os.close(ar)
    def require_ack_match(self,rid):
        expected={'recorded':True,'request_sha256':sha(canonical(self.request))}
        require(self.request is not None and self.request['request_id']==rid and self.ack==expected,'runtime_ack_mismatch')
    def require_ack_present(self,rid): require(self.ack is not None and self.request['request_id']==rid,'runtime_ack_missing')
    def require_audit_match(self,rid):
        require(self.request is not None and self.request['request_id']==rid and self.audit==self.request,'runtime_audit_mismatch')
    def require_audit_present(self,rid): require(self.audit is not None and self.request['request_id']==rid,'runtime_audit_missing')
    def append_sink(self,rid):
        require(self.request is not None and self.request['request_id']==rid,'runtime_effect_request')
        require(rid in self.reserved,'runtime_effect_unreserved')
        with self.sink.open('ab',buffering=0) as handle:
            raw=self.request['payload'].encode('utf-8'); count=handle.write(raw)
            # This completion is recorded at the write boundary, before fsync.
            self.e.frame({'frame':'io','pid':os.getpid(),'operation_index':self.operation,
                          'surface':'sink','bytes_hex':raw[:count].hex(),'write_return':count,'fsync_return':None})
            self.e.event('sink_write_completed',self.operation,{'request':dict(self.request),'bytes_hex':raw[:count].hex(),'write_return':count})
            os.fsync(handle.fileno())
    def direct_sink_write(self,actor,rid): raise RuntimeFailure('direct_effect_route_not_admitted')


def execute_candidate(text,row,profile,emitter,scratch,protocol):
    """Only called after both external inspection and ready/RUN handshake."""
    primitives=Primitives(row,profile,emitter,scratch,protocol); cursor=[0]
    def wrap(name):
        def primitive(*args):
            idx=cursor[0]; require(idx<len(row['operations']),'unexpected_primitive')
            op=row['operations'][idx]
            require(op['primitive']==name and op['args']==list(args),'runtime_operation_binding')
            cursor[0]+=1;primitives.operation=idx
            emitter.event('op_begin',idx,{'primitive':name,'args':list(args)})
            try:
                getattr(primitives,name)(*args)
            except BaseException as exc:
                code=exc.code if isinstance(exc,RuntimeFailure) else ('os_error_'+str(exc.errno) if isinstance(exc,OSError) else 'runtime_exception')
                emitter.event('op_end',idx,{'outcome':'RAISED','error_code':code})
                raise RuntimeFailure(code) from exc
            emitter.event('op_end',idx,{'outcome':'RETURNED','error_code':None})
        return primitive
    namespace={'__builtins__':{}}
    for name in profile['candidate_language']['primitives']: namespace[name]=wrap(name)
    emitter.event('candidate_start',None,{'candidate_sha256':row['candidate_raw_sha256']})
    status,code,error='COMPLETED',0,None
    try:
        candidate_code=compile(text,'<w1-exact-utf8-candidate>','exec')
        exec(candidate_code,namespace,namespace)
        namespace['candidate']()
        require(cursor[0]==len(row['operations']),'unexecuted_operation_suffix')
    except BaseException as exc:
        error=exc.code if isinstance(exc,RuntimeFailure) else 'runtime_exception'
        status='PRIMITIVE_REFUSED' if error=='direct_effect_route_not_admitted' else 'FAILED';code=1
    emitter.event('candidate_terminal',None,{'status':status,'exit_code':code,'error_code':error})
    return code


def _open_fds():
    out=[]
    for n in os.listdir('/proc/self/fd'):
        try: os.fstat(int(n));out.append(int(n))
        except OSError: pass
    return sorted(out)


def probe_environment(request_sha,case_id):
    """Bounded admission controls only; no candidate or model code is executed."""
    import socket
    actual={'implementation':platform.python_implementation(),'version':platform.python_version(),
            'system':platform.system(),'machine':platform.machine()}
    require(actual=={'implementation':'CPython','version':'3.13.5','system':'Linux','machine':'x86_64'},'runtime_profile')
    require(os.getuid()==os.geteuid()==65532 and os.getgid()==65532,'runtime_uid')
    fields={k:v.strip() for k,v in (line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)}
    require(fields['NoNewPrivs']=='1' and fields['Seccomp']=='2' and int(fields['CapEff'],16)==0,'kernel_controls')
    cgroup={n:Path('/sys/fs/cgroup',n).read_text().strip() for n in ('pids.max','memory.max','memory.swap.max','cpu.max')}
    require(cgroup=={'pids.max':'16','memory.max':'134217728','memory.swap.max':'0','cpu.max':'50000 100000'},'cgroup_controls')
    fds=_open_fds();require(fds==[0,1,2],'unexpected_descriptors')
    require(resource.getrlimit(resource.RLIMIT_FSIZE)==(65536,65536) and
            resource.getrlimit(resource.RLIMIT_NOFILE)==(64,64), 'runtime_rlimits')
    scratch=Path('/scratch');require(list(scratch.iterdir())==[],'scratch_not_empty')
    path=scratch/'positive_probe';path.write_bytes(b'W1_CONTROL')
    with path.open('rb') as f: os.fsync(f.fileno())
    positive=path.read_bytes().hex();path.unlink()
    denied={}
    for p in ('/inputs/deny_probe','/tmp/deny_probe','/deny_probe','/dev/deny_probe'):
        try:
            fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except OSError as exc: denied[p]=exc.errno
        else:
            os.close(fd);os.unlink(p);raise RuntimeFailure('write_escape_control_failed')
    interfaces=sorted(p.name for p in Path('/sys/class/net').iterdir())
    require(interfaces==['lo'],'network_interfaces')
    network_errno=None
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try: s.connect(('192.0.2.1',9))
        except OSError as exc: network_errno=exc.errno
        else: raise RuntimeFailure('network_escape_control_failed')
    require(network_errno in (errno.ENETUNREACH,errno.EHOSTUNREACH),'network_denial_unproved')
    # Child inventory is bounded even if the expected cgroup was misconfigured.
    children=[]; fork_errno=None; r,w=os.pipe()
    try:
        for _ in range(20):
            try: pid=os.fork()
            except OSError as exc: fork_errno=exc.errno;break
            if pid==0:
                os.close(w);os.read(r,1);os._exit(0)
            children.append(pid)
    finally:
        os.close(r);os.close(w)
        reaped=0
        for pid in children:
            p,st=os.waitpid(pid,0);require(p==pid and st==0,'probe_child_cleanup');reaped+=1
    require(fork_errno==errno.EAGAIN,'process_bound_not_enforced')
    p=scratch/'size_probe';old=signal.signal(signal.SIGXFSZ,signal.SIG_IGN);fsize_errno=None
    try:
        with p.open('wb',buffering=0) as f:
            f.write(b'x'*65536)
            try: f.write(b'x')
            except OSError as exc: fsize_errno=exc.errno
    finally:
        signal.signal(signal.SIGXFSZ,old)
        if p.exists(): p.unlink()
    require(fsize_errno==errno.EFBIG,'file_bound_not_enforced')
    require(list(scratch.iterdir())==[] and _open_fds()==[0,1,2],'probe_cleanup')
    return {'frame':'ready','request_sha256':request_sha,'case_id':case_id,'runtime':actual,
            'python_sha256':sha(regular(Path(sys.executable).resolve(),32*1024*1024)),'kernel_release':platform.release(),
            'uid':os.getuid(),'gid':os.getgid(),'status_fields':{k:fields[k] for k in ('NoNewPrivs','Seccomp','CapEff')},
            'cgroup':cgroup,'interfaces':interfaces,'network_errno':network_errno,'inherited_fds':fds,
            'scratch_roundtrip_hex':positive,'denied_writes':denied,'fork_errno':fork_errno,
            'fork_children':len(children),'fork_reaped':reaped,'fsize_errno':fsize_errno,'probe_cleanup':True}


def collect_candidate(text,row,profile,run_id,protocol):
    er,ew=os.pipe();sr,sw=os.pipe();tr,tw=os.pipe();pid=os.fork()
    if pid==0:
        os.setsid();os.close(er);os.close(sr);os.close(tr)
        os.dup2(sw,1);os.dup2(tw,2);os.close(sw);os.close(tw)
        dev=os.open('/dev/null',os.O_RDONLY);os.dup2(dev,0);os.close(dev)
        resource.setrlimit(resource.RLIMIT_CPU,(3,3))
        try: code=execute_candidate(text,row,profile,Emitter(ew,run_id,row['case_id'],'worker'),Path('/scratch'),protocol)
        except BaseException: code=91
        os.close(ew);os._exit(code)
    os.close(ew);os.close(sw);os.close(tw)
    output({'frame':'spawn','role':'worker','pid':pid,'parent_pid':os.getpid()})
    sel=selectors.DefaultSelector();buffers={'events':bytearray(),'stdout':bytearray(),'stderr':bytearray()}
    frames=[];failed=False;status=None;deadline=time.monotonic()+12
    for role,fd in (('events',er),('stdout',sr),('stderr',tr)):
        os.set_blocking(fd,False);sel.register(fd,selectors.EVENT_READ,role)
    try:
        while sel.get_map():
            require(time.monotonic()<deadline,'observer_timeout')
            for key,_ in sel.select(0.1):
                raw=os.read(key.fd,8192)
                if not raw: sel.unregister(key.fd);continue
                buf=buffers[key.data];buf.extend(raw)
                if key.data!='events':
                    output({'frame':'stdio','channel':key.data,'bytes_hex':raw.hex()})
                require(len(buf)<=65536,'observer_output_limit')
                if key.data=='events':
                    while b'\n' in buf:
                        line,_,rest=buf.partition(b'\n');buf[:]=rest
                        frame=protocol.strict(bytes(line),MAX_PIPE_FRAME)
                        require(frame.get('frame') in ('event','io','spawn','monitor_wait'),'child_frame_type')
                        frames.append(frame);require(len(frames)<=300,'observer_frame_limit');output(frame)
        require(not buffers['events'],'truncated_event')
        # EOF is not proof of child exit. Poll waitpid against the same deadline.
        while status is None:
            child,st=os.waitpid(pid,os.WNOHANG)
            if child==pid: status=st;break
            require(time.monotonic()<deadline,'observer_wait_timeout');time.sleep(0.01)
        terminals=[f['event'] for f in frames if f.get('frame')=='event' and f['event']['kind']=='candidate_terminal']
        require(len(terminals)==1 and os.WIFEXITED(status),'candidate_terminal_missing')
        require(os.WEXITSTATUS(status)==terminals[0]['data']['exit_code'],'child_status_mismatch')
        terminal=terminals[0]
        output({'frame':'event','pid':os.getpid(),'event':{'event_id':'supervisor_1','run_id':run_id,
            'case_id':row['case_id'],'attempt':1,'process':'supervisor','sequence':1,'operation_index':None,
            'kind':'supervisor_terminal','data':{'child_pid':pid,'child_terminal_event':terminal['event_id'],
            'normal_exit':True,'exit_code':os.WEXITSTATUS(status)}}})
        scratch=Path('/scratch');names=sorted(p.name for p in scratch.iterdir())
        require(set(names)<={'sink.bin','audit.jsonl'},'scratch_inventory')
        sink=regular(scratch/'sink.bin',8192) if (scratch/'sink.bin').exists() else b''
        audit=regular(scratch/'audit.jsonl',8192) if (scratch/'audit.jsonl').exists() else b''
        output({'frame':'capture','supervisor_pid':os.getpid(),'worker_pid':pid,'wait_status':status,
                'worker_reaped':True,'event_eof':True,'scratch_entries':names,
                'sink_hex':sink.hex(),'audit_hex':audit.hex(),
                'stdout_hex':bytes(buffers['stdout']).hex(),'stderr_hex':bytes(buffers['stderr']).hex()})
    finally:
        # Always kill the worker process group, including any unreaped monitor.
        try: os.killpg(pid,signal.SIGKILL)
        except ProcessLookupError: pass
        if status is None:
            try: os.waitpid(pid,0)
            except ChildProcessError: pass
        sel.close()
        for fd in (er,sr,tr): os.close(fd)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--request-sha256',required=True);p.add_argument('--case-id',required=True)
    args=p.parse_args(argv)
    try:
        require(re.fullmatch('[0-9a-f]{64}',args.request_sha256) is not None,'request_digest')
        require(args.case_id in ('P00','N01','N07','N08','N02','probe-time','probe-output'),'case_selection')
        require(os.getpid()==1 and Path('/inputs').is_dir() and Path('/scratch').is_dir(),'external_container_required')
        raw=regular('/inputs/request.json',131072);require(sha(raw)==args.request_sha256,'request_identity')
        request=json.loads(raw)
        require(request['subject']=='pd_sm_02_w1_diagnostic_healthy_v0','diagnostic_subject')
        require(sha(regular(__file__,131072))==request['sources']['paradox_w1_native_runtime_v0.py'],'runtime_source_identity')
        observer=regular('/inputs/observer.py',131072)
        require(sha(observer)==request['sources']['paradox_w1_native_observer_v0.py'],'observer_source_identity')
        spec=importlib.util.spec_from_file_location('w1_observer','/inputs/observer.py')
        O=importlib.util.module_from_spec(spec);spec.loader.exec_module(O)
        require(raw==canonical(O.strict(raw)),'request_canonical')
        row=None;profile=None;text=None
        if not args.case_id.startswith('probe-'):
            entry=next(c for c in request['cases'] if c['case_id']==args.case_id)
            row_raw=regular('/inputs/case.json',32768);require(sha(row_raw)==entry['input_sha256'],'case_input_identity')
            row=O.strict(row_raw);require(row['case_id']==args.case_id,'case_identity')
            source=regular('/inputs/candidate.py',16384)
            require(sha(source)==entry['candidate_sha256'],'candidate_identity')
            profile_raw=regular('/inputs/profile.json',16384);require(sha(profile_raw)==request['profile_sha256'],'profile_identity')
            profile=O.strict(profile_raw);text=parse_source(source,row,profile)
        require(read_line(0,10)==('PROBE:'+args.request_sha256+':'+args.case_id+'\n').encode(),'probe_authorization')
        ready=probe_environment(args.request_sha256,args.case_id);output(ready)
        require(read_line(0,10)==('RUN:'+args.request_sha256+':'+args.case_id+'\n').encode(),'invocation_authorization')
        if args.case_id=='probe-time': time.sleep(60);raise RuntimeFailure('time_limit_not_enforced')
        if args.case_id=='probe-output':
            for _ in range(2048): output({'frame':'supervision_output','padding':'x'*1000})
            raise RuntimeFailure('output_limit_not_enforced')
        collect_candidate(text,row,profile,request['run_id'],O)
        return 0
    except BaseException as exc:
        try: output({'frame':'runtime_failure','reason':str(exc),'error_type':type(exc).__name__})
        except BaseException: pass
        return 2

if __name__=='__main__':
    raise SystemExit(main())
