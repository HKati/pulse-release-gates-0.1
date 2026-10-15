#!/usr/bin/env python3
"""Independent Q2 worker input, token/text, metric and carrier checks.

No collector or worker module is imported. Native phase entry points require
an externally prepared immutable projection and a UID-65534 capsule/verifier
service. Offline carrier reconstruction does not reacquire kernel observations.
"""
from __future__ import annotations
import argparse
import importlib
import importlib.metadata
import os
import re
import stat
import zipfile
import io as byte_io
from pathlib import Path
import platform
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q2_release_host_worker_contract_v0 as C
import check_q2_release_host_worker_protocol_v0 as P
import check_q2_release_host_tokenizer_v0 as T
import q2_intake_io_v0 as io


def execution_plan(root: Path) -> dict:
    """Exact commands and static input/output roles, fixed before model load."""
    root = Path(root)
    command = [str(root / 'capsule/runtime/bin/python'), '-I', '-B',
               str(root / 'capsule/source' / C.WORKER), '--mode', 'capture-reference',
               '--source-root', str(root / 'capsule/source'), '--bundle', str(root / 'capsule'),
               '--prelaunch', str(root / 'control/capture-prelaunch.json'),
               '--expected-prelaunch-sha256', '<bound-prelaunch-sha256>',
               '--subject', str(root / 'control/capture-subject.json')]
    return {'phase_order': list(C.PHASES), 'worker_argv_template': command,
            'worker_stage': 'captureworker', 'worker_required_exit': 0,
            'checker_stages': {'input_check': 'capturecheck', 'tokenizer_check': 'capturecheck',
                               'reduction_check': 'reduction'},
            'checker_limit_seconds': 180, 'worker_limits': P.LIMITS,
            'reduction_builder_exit_rule': '0_if_metric_pass_else_1',
            'reduction_checker_required_exit': 0,
            'retries': 0, 'cleanup_grace_seconds': 180}


def control_inputs(root: Path, expected_plan: str, expected_request: str):
    source = root / 'source'; p = C.load_profile(source)
    raw = C.held_read(root / 'control/plan.json')
    C.require(C.digest(raw) == expected_plan, 'plan_digest_changed')
    plan = C.parse(raw)
    C.require(C.encode(plan) == raw, 'plan_serialization_changed')
    C.validate_json(source, 'plan', plan)
    C.same(plan['execution'], execution_plan(root), 'execution_plan_changed')
    req = C.held_read(root / 'control/request.json', 32768)
    C.require(plan['request_sha256'] == expected_request, 'request_binding_changed')
    C.check_request(source, req, expected_request, plan['binding']['source_commit'])
    C.require(plan['scope'] == C.SCOPE and plan['binding']['workflow'] == C.WORKFLOW and
              plan['binding']['repository'] == C.REPOSITORY and plan['binding']['run_attempt'] == 1,
              'plan_context')
    C.same(plan['host'], p['native_requirements'], 'strict_platform_mismatch')
    C.same(plan['execution']['worker_limits'], P.LIMITS, 'limit_contract_changed')
    C.require(plan['observer_contract_sha256'] == C.digest(C.encode({'source_bindings': plan['source_bindings'],
              'execution': plan['execution']})), 'observer_contract_binding')
    C.require(plan['phase_deadline_ns'] == plan['phase_start_ns'] + 1200_000_000_000, 'phase_deadline')
    C.require([r['path'] for r in plan['source_bindings']] == p['source_paths'], 'source_extent')
    for row in plan['source_bindings']:
        data = C.held_read(source / row['path'], 2 * 1024 * 1024)
        C.require(len(data) == row['size_bytes'] and C.digest(data) == row['sha256'], 'source_projection_changed')
    projection_raw = C.held_read(root / 'control/projection.json')
    C.require(C.digest(projection_raw) == plan['projection_sha256'], 'projection_digest_changed')
    projection = C.parse(projection_raw)
    T.check_projection(root, projection, p, T.Budget(180))
    T.check_source_projection(projection, plan['source_bindings'])
    C.require(T.verify_bootstrap(root / 'inputs/bootstrap.tar.gz', p, T.Budget(180)) == plan['bootstrap_lib_sha256'],
              'bootstrap_changed')
    return source, p, plan, projection


def input_check(root: Path, source: Path, p: dict, plan: dict, projection: dict) -> dict:
    """Check original archive-to-projection bytes independently of the writer."""
    b = T.Budget(180)
    docs, _ = T.verify_archives(source, root / 'inputs', p, b)
    ip = T.intake.load_profile(source)
    with T.archived.capture_archive(root / 'inputs/capture.zip', ip, b) as capture, io.Archive(
            root / 'inputs/capsule.zip', maximum_bytes=p['inputs']['capsule']['archive_size_bytes'],
            max_members=p['capsule_members'], member_bytes=ip['limits']['capsule_member_bytes'],
            expanded_bytes=p['capsule_expanded_bytes'], deadline=b, allow_runtime_link=True,
            expected_sha256=p['inputs']['capsule']['archive_sha256']) as capsule:
        for tree, archive in (('capsule', capsule), ('historical', capture)):
            rows = projection['trees'][tree]
            C.require(len(rows) == len(archive.members) and {r['path'] for r in rows} == set(archive.members), 'archive_extent')
            for row in rows:
                d = archive.inspect(row['path'])
                C.require(row['origin'] == tree + ':' + row['path'] and row['archive_mode'] == d['mode'] and
                          row['kind'] == d['kind'], 'archive_origin')
                if d['kind'] == 'file':
                    C.require((row['size_bytes'], row['sha256']) == (d['size'], d['sha256']), 'archive_projection_changed')
        for name in (C.WORKER, C.WORKLOAD, C.PACK + 'profiles/q2_reference_subject_v0.json',
                     C.PACK + 'profiles/q2_reference_model_files_v0.json'):
            C.require(capsule.read('source/' + name) == C.held_read(source / name), 'frozen_worker_source_changed')
    rows = {r['path']: r for r in projection['trees']['inputs']}
    C.require(set(rows) == set(T.ARCHIVE_FILES.values()) | {'bootstrap.tar.gz'}, 'input_projection_extent')
    for role, filename in {**T.ARCHIVE_FILES, 'bootstrap': 'bootstrap.tar.gz'}.items():
        expected = p['bootstrap'] if role == 'bootstrap' else p['inputs'][role]
        row = rows[filename]
        C.require(row['origin'] == 'input:' + role and row['archive_mode'] is None and
                  row['sha256'] == expected['archive_sha256'] and row['size_bytes'] == expected['archive_size_bytes'],
                  'input_projection_changed')
    return {'record_type': 'q2_worker_input_check_v0', 'plan_sha256': C.digest(C.encode(plan)),
            'projection_sha256': plan['projection_sha256'], 'request_sha256': plan['request_sha256'],
            'original_inputs_verified': True, 'worker_bytes_verified': True,
            'historical_metric_pass': False, **P.NON_AUTHORITY}


def read_protocol(evidence: Path):
    read = lambda n: C.held_read(evidence / n)
    pre, subject, ready, transcript = [read(n) for n in
        ('capture-prelaunch.json', 'capture-subject.json', 'capture-model-ready.json', 'transcript.json')]
    life = C.parse(read('lifecycle-before-cleanup.json'))
    terminal = C.parse(transcript)
    records = []
    for occurrence in terminal['occurrences']:
        slot = occurrence['slot']; stem = 'calls/' + slot['call_id']
        response, slot_ready = read(stem + '.response.json'), read(stem + '.ready.json')
        obj = C.parse(response)
        C.require(read(stem + '.utf8') == obj['text'].encode('utf-8'), 'original_text_changed')
        C.same(C.parse(read(stem + '.intent.json')), {'slot': slot, 'binding': terminal['binding'],
                   'generation_seconds': 15, 'retries': 0, 'intent': 'before_GO'}, 'original_intent_changed')
        records.append((response, slot_ready))
    return pre, subject, ready, transcript, life, records


def admission(plan, pre, subject, transcript, life, config):
    b = plan['binding']
    return {'scope': P.SCOPE, 'repository': P.REPOSITORY, 'workflow': P.WORKFLOW,
        'source_commit': b['source_commit'], 'run_id': b['run_id'], 'run_attempt': 1,
        'request_sha256': plan['request_sha256'], 'prelaunch_sha256': C.digest(pre),
        'subject_sha256': C.digest(subject), 'transcript_sha256': C.digest(transcript),
        'effective_generation_sha256': C.digest(C.encode(config)), 'capsule_sha256': P.CAPSULE_SHA256,
        'observer_contract_sha256': plan['observer_contract_sha256'], 'lifecycle_sha256': C.digest(C.encode(life))}


def dataset_manifest(groups: bytes, pre: dict, terminal: dict) -> bytes:
    return C.encode({'manifest_version': '1.0.0', 'dataset_id': 'q2-capsule-worker-' + pre['context']['run_id'],
        'time_range': {'from': pre['started_at'], 'to': terminal['ended_at']},
        'source': {'kind': 'artifact', 'uri': 'github-actions:' + C.REPOSITORY + '/' + pre['context']['run_id'] + '/1',
                   'description': 'Separate fixed capsule worker verification; trusted owner observer, no release authority.'},
        'sampling': {'strategy': 'full', 'n': 50, 'seed': 0},
        'hashes': {'input_sha256': C.digest(groups), 'code_sha': pre['context']['source_commit']},
        'pii_handling': {'scrubbed': False, 'notes': 'Fixed authored workload; separate owner-authorized original evidence retention.'}})


def reconstruct(source, plan, data, configuration, tokenize, decode):
    pre, subject, ready, transcript, life, records = data
    selected = admission(plan, pre, subject, transcript, life, configuration)
    return P.verify_protocol(source=source, workload_raw=C.held_read(source / C.WORKLOAD),
        admission=selected, expected_admission=selected, prelaunch_raw=pre, subject_raw=subject,
        model_ready_raw=ready, transcript_raw=transcript, lifecycle=life, records=records,
        configuration=configuration, tokenize=tokenize, decode=decode, require_private_cleanup=False)


def tokenizer_check(root, source, p, plan, output):
    runtime = root / 'capsule/runtime'
    T.native_target(runtime, p)
    import rfc8785
    import transformers
    import torch
    import tokenizers
    from transformers import AutoTokenizer, GenerationConfig
    versions = {name: importlib.metadata.version(name) for name in p['runtime_versions']}
    C.same(versions, p['runtime_versions'], 'tokenizer_runtime_changed')
    for module in (rfc8785, transformers, torch, tokenizers):
        C.require(Path(module.__file__).resolve().is_relative_to(runtime.resolve()), 'tokenizer_module_origin')
    C.require(torch.version.cuda is None and rfc8785.dumps({'a': 1.0, 'b': -0.0}) == b'{"a":1,"b":0}', 'tokenizer_runtime')
    tok = AutoTokenizer.from_pretrained(str(root / 'capsule/model'), local_files_only=True,
                                       trust_remote_code=False, use_fast=True)
    module = sys.modules[type(tok).__module__]
    C.require(tok.is_fast and (tok.bos_token_id, tok.eos_token_id, tok.pad_token_id) == (1, 2, 2) and
              Path(module.__file__).resolve().is_relative_to(runtime.resolve()), 'tokenizer_origin')
    frozen = P.load_independent_helpers(source)[1]
    config = GenerationConfig(**frozen.GENERATION, disable_compile=True).to_dict()
    C.require(C.digest(C.encode(config)) == P.CONFIGURATION_SHA256, 'configuration_changed')
    token_rows, decode_rows = [], []
    def tokenize(messages):
        ids = tok.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
        token_rows.append({'messages_sha256': C.digest(C.encode(messages)), 'input_ids': ids})
        return ids
    def decode(ids):
        text = tok.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        decode_rows.append({'token_ids': ids, 'text': text})
        return text
    data = read_protocol(root / 'evidence')
    reconstructed = reconstruct(source, plan, data, config, tokenize, decode)
    groups = reconstructed['groups_bytes']
    manifest = dataset_manifest(groups, C.parse(data[0]), C.parse(data[3]))
    token_map = C.encode({'record_type': 'q2_worker_independent_token_map_v0', 'input_tokens': token_rows,
                         'decoded_continuations': decode_rows})
    for name, raw in [('groups.json', groups), ('dataset-manifest.json', manifest), ('token-map.json', token_map)]:
        io.write_new(output / name, raw)
    return {'record_type': 'q2_worker_tokenizer_check_v0', 'plan_sha256': C.digest(C.encode(plan)),
        'transcript_sha256': C.digest(data[3]), 'lifecycle_before_cleanup_sha256': C.digest(C.encode(data[4])),
        'groups_sha256': C.digest(groups), 'manifest_sha256': C.digest(manifest), 'token_map_sha256': C.digest(token_map),
        'configuration_sha256': C.digest(C.encode(config)), 'verified_calls': 150,
        'runtime_versions': versions, 'tokenizer_module': Path(module.__file__).resolve().relative_to(runtime).as_posix(),
        'private_tree_cleanup': 'pending', 'native_origin_reacquired': False, **P.NON_AUTHORITY}


def reduction_check(root, source, p, plan, output):
    """The two frozen CLIs run within this separately isolated reduction service."""
    evidence = root / 'evidence'
    groups = C.held_read(evidence / 'groups.json'); manifest = C.held_read(evidence / 'dataset-manifest.json')
    checker = C.parse(C.held_read(evidence / 'tokenizer-check.json'))
    C.require(checker['groups_sha256'] == C.digest(groups) and checker['manifest_sha256'] == C.digest(manifest), 'reducer_input_changed')
    argv = [sys.executable, '-I', '-B']
    args = ['--groups', str(evidence / 'groups.json'), '--dataset-manifest', str(evidence / 'dataset-manifest.json'),
            '--expected-groups-sha256', C.digest(groups), '--expected-manifest-sha256', C.digest(manifest)]
    clean = {'PATH': '/usr/bin:/bin', 'HOME': str(output), 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
             'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
    def run(command, stem):
        # Native service RLIMIT_FSIZE bounds these files; only closed checked JSON
        # crosses the handoff. A timeout rejects and outer cgroup cleanup follows.
        out, err = output / (stem + '.stdout'), output / (stem + '.stderr')
        with out.open('xb') as stdout, err.open('xb') as stderr:
            result = subprocess.run(command, cwd=output, env=clean, stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr, timeout=80, check=False)
        stdout = C.held_read(out, 128 * 1024); stderr = C.held_read(err, 128 * 1024)
        out.unlink(); err.unlink()
        C.require(stderr == b'', 'metric_stderr')
        return result.returncode, stdout
    builder_argv = argv + [str(source / T.io.REDUCER)] + args + ['--out', str(output / 'summary.json')]
    builder_exit, builder_stdout = run(builder_argv, 'builder')
    summary_raw = C.held_read(output / 'summary.json'); summary = C.parse(summary_raw)
    C.require(type(summary.get('pass')) is bool, 'metric_result_type')
    C.require(builder_exit == (0 if summary['pass'] else 1) and builder_stdout == b'', 'metric_builder_exit')
    checker_argv = argv + [str(source / T.io.CHECKER)] + args + ['--summary', str(output / 'summary.json'),
                                                                            '--expected-summary-sha256', C.digest(summary_raw)]
    checker_exit, checker_raw = run(checker_argv, 'checker')
    checked = C.parse(checker_raw)
    C.same(checked, {'ok': True, 'recomputed_pass': summary['pass'], 'authority_effect': 'none',
                    'production_gate_eligible': False}, 'metric_checker_result')
    C.require(checker_exit == 0, 'metric_checker_exit')
    io.write_new(output / 'summary-check.json', checker_raw)
    return {'record_type': 'q2_worker_reduction_check_v0', 'plan_sha256': C.digest(C.encode(plan)),
        'groups_sha256': C.digest(groups), 'manifest_sha256': C.digest(manifest),
        'summary_sha256': C.digest(summary_raw), 'summary_check_sha256': C.digest(checker_raw),
        'builder_exit': builder_exit, 'builder_stdout_sha256': C.digest(builder_stdout),
        'checker_exit': checker_exit, 'metric_pass': summary['pass'], **P.NON_AUTHORITY}


def verify_carrier(source: Path, buffers: dict[str, bytes], expected_result: str) -> dict:
    """Offline metadata/protocol reconstruction, not another native observation.

    The selected final result digest must come from the owner's chosen receipt.
    Token maps are preserved outputs of the observed independent checker, not
    proof that this invocation has re-tokenized anything.
    """
    C.require(set(buffers) == C.evidence_names(), 'carrier_extent')
    C.require(C.digest(buffers['result.json']) == expected_result, 'result_selection_changed')
    result = C.parse(buffers['result.json']); C.validate_json(source, 'result', result)
    without_result = {k: v for k, v in buffers.items() if k != 'result.json'}
    C.same(C.inventory(without_result), result['evidence_inventory'], 'carrier_inventory_changed')
    plan = C.parse(buffers['plan.json']); C.validate_json(source, 'plan', plan)
    C.require(result['plan_sha256'] == C.digest(buffers['plan.json']), 'carrier_plan_binding')
    C.same(result['binding'], plan['binding'], 'carrier_run_binding')
    p = C.load_profile(source)
    C.check_request(source, buffers['request.json'], plan['request_sha256'], result['binding']['source_commit'])
    C.same(plan['host'], p['native_requirements'], 'carrier_host')
    C.require(C.encode(plan) == buffers['plan.json'], 'carrier_plan_serialization')
    command = plan['execution']['worker_argv_template']
    planned_root = Path(command[0]).parents[3]
    C.require(re.fullmatch(r'/var/lib/pulse-q2-worker-[a-z0-9_]{8}/projection', str(planned_root)) is not None,
              'carrier_projection_root')
    C.same(plan['execution'], execution_plan(planned_root), 'carrier_execution_changed')
    C.require(plan['phase_deadline_ns'] == plan['phase_start_ns'] + 1200_000_000_000 and
              plan['observer_contract_sha256'] == C.digest(C.encode({'source_bindings': plan['source_bindings'],
                  'execution': plan['execution']})), 'carrier_observer_contract')
    C.require([r['path'] for r in plan['source_bindings']] == p['source_paths'], 'carrier_source_extent')
    for row in plan['source_bindings']:
        raw = C.held_read(source / row['path'], 2 * 1024 * 1024)
        C.require(row['size_bytes'] == len(raw) and row['sha256'] == C.digest(raw), 'carrier_source_bytes')
    C.require(plan['projection_sha256'] == C.digest(buffers['projection.json']), 'carrier_projection_binding')
    projection = C.parse(buffers['projection.json'])
    T.check_source_projection(projection, plan['source_bindings'])
    input_report = C.parse(buffers['input-check.json']); C.validate_json(source, 'input_check', input_report)
    C.require(input_report['plan_sha256'] == result['plan_sha256'] and
              input_report['projection_sha256'] == plan['projection_sha256'] and
              input_report['request_sha256'] == plan['request_sha256'], 'carrier_input_check_binding')
    life = C.parse(buffers['lifecycle.json']); before = C.parse(buffers['lifecycle-before-cleanup.json'])
    C.require(before['private_tree_cleanup'] == 'pending' and life['private_tree_cleanup'] == 'verified_removed', 'carrier_cleanup')
    C.same({**before, 'private_tree_cleanup': 'verified_removed'}, life, 'cleanup_rebinding')
    pre, subject, ready, transcript = (buffers[n] for n in
        ('capture-prelaunch.json', 'capture-subject.json', 'capture-model-ready.json', 'transcript.json'))
    terminal = C.parse(transcript); configuration = C.parse(ready)['effective_generation']
    pre_obj = C.parse(pre)
    C.require(pre_obj['phase_start_ns'] == plan['phase_start_ns'] and
              pre_obj['phase_deadline_ns'] == plan['phase_deadline_ns'], 'carrier_phase_clock')
    C.validate_json(source, 'worker_prelaunch', pre_obj)
    C.validate_json(source, 'worker_lifecycle', life)
    C.validate_json(source, 'worker_lifecycle_before_cleanup', before)

    token_check = C.parse(buffers['tokenizer-check.json'])
    C.validate_json(source, 'tokenizer_check', token_check)
    C.require(token_check['plan_sha256'] == result['plan_sha256'] and
        token_check['lifecycle_before_cleanup_sha256'] == C.digest(buffers['lifecycle-before-cleanup.json']) and
        token_check['transcript_sha256'] == C.digest(transcript) and
        token_check['token_map_sha256'] == C.digest(buffers['token-map.json']) and
        token_check['groups_sha256'] == C.digest(buffers['groups.json']) and
        token_check['manifest_sha256'] == C.digest(buffers['dataset-manifest.json']), 'token_check_binding')
    maps = C.parse(buffers['token-map.json']); C.validate_json(source, 'token_map', maps)
    index_t = iter(maps['input_tokens']); index_d = iter(maps['decoded_continuations'])
    def tokenize(messages):
        row = next(index_t); C.require(row['messages_sha256'] == C.digest(C.encode(messages)), 'token_map_request'); return row['input_ids']
    def decode(ids):
        row = next(index_d); C.same(row['token_ids'], ids, 'token_map_continuation'); return row['text']
    records = []
    for occurrence in terminal['occurrences']:
        stem = 'calls/' + occurrence['slot']['call_id']
        response = buffers[stem + '.response.json']
        C.require(buffers[stem + '.utf8'] == C.parse(response)['text'].encode('utf-8'), 'carrier_original_text')
        C.same(C.parse(buffers[stem + '.intent.json']), {'slot': occurrence['slot'], 'binding': terminal['binding'],
            'generation_seconds': 15, 'retries': 0, 'intent': 'before_GO'}, 'carrier_intent')
        records.append((response, buffers[stem + '.ready.json']))
    selected = admission(plan, pre, subject, transcript, life, configuration)
    protocol = P.verify_protocol(source=source, workload_raw=C.held_read(source / C.WORKLOAD),
        admission=selected, expected_admission=selected, prelaunch_raw=pre, subject_raw=subject,
        model_ready_raw=ready, transcript_raw=transcript, lifecycle=life, records=records,
        configuration=configuration, tokenize=tokenize, decode=decode)
    C.require(next(index_t, None) is None and next(index_d, None) is None, 'token_map_extent')
    C.require(protocol['groups_bytes'] == buffers['groups.json'] and
        dataset_manifest(buffers['groups.json'], C.parse(pre), terminal) == buffers['dataset-manifest.json'], 'carrier_derivation')
    reduction = C.parse(buffers['reduction-check.json']); C.validate_json(source, 'reduction_check', reduction)
    summary = C.parse(buffers['summary.json']); checked = C.parse(buffers['summary-check.json'])
    C.require(type(summary.get('pass')) is bool and reduction['metric_pass'] is summary['pass'] and
              result['metric_pass'] is summary['pass'], 'carrier_metric_claim')
    C.same(checked, {'ok': True, 'recomputed_pass': summary['pass'], 'authority_effect': 'none', 'production_gate_eligible': False}, 'carrier_metric_checker')
    for role, name in [('groups', 'groups.json'), ('manifest', 'dataset-manifest.json'), ('summary', 'summary.json'), ('summary_check', 'summary-check.json')]:
        C.require(reduction[role + '_sha256'] == C.digest(buffers[name]), 'carrier_metric_binding')
    C.require(reduction['plan_sha256'] == result['plan_sha256'] and
              reduction['builder_stdout_sha256'] == C.digest(b''), 'carrier_reducer_origin')
    C.require(reduction['builder_exit'] == (0 if summary['pass'] else 1) and reduction['checker_exit'] == 0,
              'carrier_metric_exit')
    # Validate every separately observed service, not just the worker transcript.
    old, native = P.load_independent_helpers(source)
    phases = result['phases']; C.require([r['id'] for r in phases] == list(C.PHASES), 'carrier_phases')
    previous = plan['phase_start_ns']; units = set()
    expected_outputs = {'input_check': ('input-check.json',),
        'worker': ('transcript.json',),
        'tokenizer_check': ('groups.json', 'dataset-manifest.json', 'token-map.json', 'tokenizer-check.json'),
        'reduction_check': ('summary.json', 'summary-check.json', 'reduction-check.json')}
    for phase in phases:
        stage = 'captureworker' if phase['id'] == 'worker' else ('reduction' if phase['id'] == 'reduction_check' else 'capturecheck')
        old.capture_sandbox(phase['isolation'], stage, native)
        old.capture_cleanup_check(phase['cleanup'], phase['isolation']['unit'])
        C.require(phase['isolation']['unit'] not in units, 'carrier_phase_reuse')
        units.add(phase['isolation']['unit'])
        C.same(phase['outputs'], {n: C.digest(buffers[n]) for n in expected_outputs[phase['id']]}, 'carrier_phase_outputs')
        seconds = phase['isolation'].get('capture_runtime_seconds', 180)
        C.require(phase['exit_observed_ns'] <= min(phase['launch_ns'] + seconds * 1_000_000_000,
                                                 plan['phase_deadline_ns']), 'carrier_phase_timeout')
        if phase['id'] == 'worker':
            for name in ('launch_ns', 'isolation_observed_ns', 'exec_ns', 'stdout_eof_ns', 'exit_observed_ns', 'exit_code'):
                C.same(phase[name], life[name], 'carrier_worker_lifecycle')
            C.same(phase['isolation'], life['sandbox'], 'carrier_worker_isolation')
            C.same(phase['cleanup'], life['cleanup'], 'carrier_worker_cleanup')
            C.require(phase['cleanup_ns'] >= life['cleanup_completed_ns'], 'carrier_worker_cleanup_clock')
        C.require(phase['launch_ns'] >= previous and phase['launch_ns'] <= phase['isolation_observed_ns'] <=
                  phase['exec_ns'] <= phase['stdout_eof_ns'] <= phase['exit_observed_ns'] <= phase['cleanup_ns'] <= plan['phase_deadline_ns'] + 180_000_000_000,
                  'carrier_phase_order')
        C.require(phase['exit_code'] == 0 and phase['input_recheck'] == 'unchanged', 'carrier_phase_exit')
        previous = phase['cleanup_ns']
    C.require(result['private_cleanup_completed_ns'] >= previous and result['source_recheck'] == 'unchanged' and
              result['private_cleanup_completed_ns'] <= plan['phase_deadline_ns'] + 180_000_000_000, 'carrier_final_cleanup')
    return {'record_type': 'q2_worker_carrier_reconstruction_v0', 'evidence_reconstructed': True,
        'native_origin_reacquired': False, 'tokenization_reperformed': False, 'metric_recomputed': False,
        'historical_metric_pass': False, **P.NON_AUTHORITY}



def read_carrier(root: Path, expected_archive: str | None = None) -> dict[str, bytes]:
    """Read a closed inner evidence ZIP without extraction, or a held directory."""
    if root.is_file():
        C.require(type(expected_archive) is str and re.fullmatch('[0-9a-f]{64}', expected_archive), 'archive_selection_missing')
        raw = C.held_read(root, 64 * 1024 * 1024)
        C.require(C.digest(raw) == expected_archive, 'archive_selection_changed')
        with zipfile.ZipFile(byte_io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            C.require(len(entries) == len(C.evidence_names()) and {e.filename for e in entries} == C.evidence_names(), 'carrier_extent')
            C.require(sum(e.file_size for e in entries) <= 64 * 1024 * 1024 and
                      all(0 <= e.file_size <= 16 * 1024 * 1024 and not e.flag_bits & 1 and
                          e.create_system == 3 and stat.S_ISREG(e.external_attr >> 16) for e in entries), 'carrier_archive_bound')
            buffers = {e.filename: archive.read(e) for e in entries}
    else:
        C.require(expected_archive is None and root.is_dir(), 'carrier_arguments')
        entries = list(root.rglob('*'))
        physical = {p.relative_to(root).as_posix() for p in entries if not p.is_dir()}
        directories = {p.relative_to(root).as_posix() for p in entries if p.is_dir()}
        C.require(physical == C.evidence_names() and directories == {'calls'} and
                  not any(p.is_symlink() for p in (root, *root.parents, *entries)), 'carrier_extent')
        buffers = {n: C.held_read(root / n) for n in physical}
    C.inventory(buffers)
    return buffers


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--phase', choices=['input_check', 'tokenizer_check', 'reduction_check', 'check-evidence'], required=True)
    a.add_argument('--root', type=Path, required=True)
    a.add_argument('--expected-plan-sha256')
    a.add_argument('--expected-request-sha256')
    a.add_argument('--output', type=Path)
    a.add_argument('--source', type=Path)
    a.add_argument('--expected-result-sha256')
    a.add_argument('--expected-archive-sha256')
    args = a.parse_args(argv)
    try:
        if args.phase == 'check-evidence':
            C.require(args.source is not None and args.expected_result_sha256 is not None and args.output is None, 'carrier_arguments')
            buffers = read_carrier(args.root, args.expected_archive_sha256)
            result = verify_carrier(args.source, buffers, args.expected_result_sha256)
        else:
            C.require(os.getuid() == 65534 and sys.flags.isolated and sys.flags.dont_write_bytecode and
                      platform.python_version() == '3.11.16' and args.output is not None and
                      args.expected_plan_sha256 is not None and args.expected_request_sha256 is not None,
                      'native_checker_context')
            source, p, plan, projection = control_inputs(args.root, args.expected_plan_sha256, args.expected_request_sha256)
            if args.phase == 'input_check':
                result = input_check(args.root, source, p, plan, projection); name = 'input-check.json'
            elif args.phase == 'tokenizer_check':
                result = tokenizer_check(args.root, source, p, plan, args.output); name = 'tokenizer-check.json'
            else:
                result = reduction_check(args.root, source, p, plan, args.output); name = 'reduction-check.json'
            C.validate_json(source, args.phase, result)
            io.write_new(args.output / name, C.encode(result))
        print('q2_worker_evidence_checked')
        return 0
    except Exception:
        print('q2_worker_evidence_rejected', file=sys.stderr); return 2

if __name__ == '__main__':
    raise SystemExit(main())
