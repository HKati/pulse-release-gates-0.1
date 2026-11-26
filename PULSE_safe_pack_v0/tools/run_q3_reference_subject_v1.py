#!/usr/bin/env python3
"""Isolated Q3 v1 token preflight / exact 203-task continuation worker.

No model is loaded during import or token preflight. The supervisor owns EXEC,
LOAD, BIND and every GENERATE boundary. No Q2 executable is imported or patched.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys

_spec = importlib.util.spec_from_file_location('q3_capture_contract_v1', Path(__file__).with_name('q3_native_capture_contract_v1.py'))
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


def tokens(ids, low, high, code):
    C.require(type(ids) is list and low <= len(ids) <= high
              and all(type(i) is int and 0 <= i < 49152 for i in ids), code)
    return ids


def tokenize_frame(tokenizer, frame, profile):
    C.require_profile(profile)
    C.require(type(frame) is list and len(frame) == C.FRAME_COUNT
              and [task['task_id'] for task in frame] == profile['task_ids']
              and all(type(task['ordinal']) is int and task['ordinal'] == index
                      for index, task in enumerate(frame, 1)), 'TOKENIZE_FULL_FRAME')
    rows = []
    for task in frame:
        ids = tokenizer.apply_chat_template(task['messages'], tokenize=True,
                                            add_generation_prompt=True, truncation=False)
        tokens(ids, 1, profile['limits']['max_prompt_tokens'], 'PROMPT_TOKENS')
        C.require(len(ids) + profile['generation']['max_new_tokens'] <= profile['limits']['context_window_contract'], 'CONTEXT_OVERFLOW')
        rows.append({'task_id': task['task_id'], 'ordinal': task['ordinal'], 'input_ids': ids,
                     'messages_sha256': C.digest(C.encode(task['messages'])),
                     'logical_request_sha256': C.digest(task['logical_request_text'].encode('utf-8'))})
    return {'record_type': 'q3_token_map_v1', 'profile_sha256': C.PROFILE_SHA256,
            'model_revision': profile['model_revision'],
            'task_file_sha256': profile['fixed_inputs'][C.FRAME + 'TASKS_DRAFT.jsonl'], 'rows': rows}


def verify_model_files(source, bundle, profile):
    model_map = C.strict_json(C.safe_read(source / 'PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json'))
    C.require(model_map['model_repository'] == profile['model_repository']
              and model_map['model_revision'] == profile['model_revision'], 'MODEL_IDENTITY')
    C.require({p.name for p in (bundle / 'model').iterdir()} ==
              {Path(x['path']).name for x in model_map['files']}, 'MODEL_FILE_SCOPE')
    for row in model_map['files']:
        raw = C.safe_read(bundle / C.relative(row['path']), 512 * 1024 * 1024)
        C.require(len(raw) == row['size'] and C.digest(raw) == row['sha256'], 'MODEL_FILE_CHANGED')
    cfg = C.strict_json(C.safe_read(bundle / 'model/config.json'))
    C.require(cfg['max_position_embeddings'] == 8192, 'MODEL_CONTEXT')
    for name in ('config.json', 'generation_config.json'):
        cfg = C.strict_json(C.safe_read(bundle / 'model' / name))
        C.require(all(type(cfg.get(k)) is int and cfg[k] == n
                      for k, n in [('bos_token_id', 1), ('eos_token_id', 2), ('pad_token_id', 2)]), 'MODEL_SPECIAL_TOKENS')


def load_tokenizer(source, bundle, profile):
    verify_model_files(source, bundle, profile)
    import importlib.metadata
    import transformers
    from transformers import AutoTokenizer
    C.require(transformers.__version__ == '4.57.6'
              and Path(transformers.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), 'TOKENIZER_RUNTIME')
    tokenizer = AutoTokenizer.from_pretrained(str(bundle / 'model'), local_files_only=True,
                                             trust_remote_code=False, use_fast=True)
    C.require(tokenizer.is_fast and (tokenizer.bos_token_id, tokenizer.eos_token_id, tokenizer.pad_token_id)
              == (1, 2, 2), 'TOKENIZER_CONFIGURATION')
    return tokenizer


def load_model(bundle, profile):
    import random
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, GenerationConfig
    C.require(torch.__version__ == '2.8.0+cpu' and transformers.__version__ == '4.57.6'
              and torch.version.cuda is None, 'MODEL_RUNTIME')
    for module in (torch, transformers):
        C.require(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), 'FOREIGN_MODULE')
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(profile['seed']); torch.manual_seed(profile['seed'])
    model = AutoModelForCausalLM.from_pretrained(str(bundle / 'model'), local_files_only=True,
        trust_remote_code=False, use_safetensors=True, torch_dtype=torch.float32,
        attn_implementation='eager', device_map=None)
    model.to('cpu'); model.eval()
    C.require(type(model).__name__ == 'LlamaForCausalLM' and not model.training
              and model.config._attn_implementation == 'eager'
              and not getattr(model, 'is_quantized', False)
              and all(p.device.type == 'cpu' and p.dtype == torch.float32 for p in model.parameters()), 'MODEL_CONFIGURATION')
    config = GenerationConfig(**profile['generation'], disable_compile=True)
    runtime = {'torch': torch.__version__, 'transformers': transformers.__version__,
               'device': 'cpu', 'dtype': 'float32', 'attention': 'eager', 'threads': 1,
               'interop_threads': 1, 'deterministic': True, 'model_class': 'LlamaForCausalLM',
               'evaluation': True, 'seed': profile['seed'], 'compile': False, 'quantization': 'none'}
    C.require(torch.get_num_threads() == torch.get_num_interop_threads() == 1
              and torch.are_deterministic_algorithms_enabled(), 'EFFECTIVE_THREADS')
    effective = config.to_dict()
    C.require(C.digest(C.encode(effective)) == profile['effective_generation_sha256']
              and C.encode(runtime) == C.encode(profile['runtime']),
              'ORIGINAL_GENERATION_RUNTIME_MISMATCH')
    return model, torch, GenerationConfig, effective, runtime


def continuation(input_ids, sequence, maximum):
    tokens(sequence, len(input_ids) + 1, len(input_ids) + maximum, 'GENERATED_SEQUENCE')
    C.require(sequence[:len(input_ids)] == input_ids, 'GENERATED_PREFIX')
    new = tokens(sequence[len(input_ids):], 1, maximum, 'NEW_TOKEN_BOUND')
    if new[-1] == 2:
        C.require(2 not in new[:-1], 'MULTIPLE_EOS')
        return new, 'eos'
    C.require(len(new) == maximum and 2 not in new, 'INCOMPLETE_GENERATION')
    return new, 'token_limit'


def capture_session(model, tokenizer, torch, config_class, effective, runtime,
                    token_map, profile, binding, read_command, emit):
    """Full fixed frame in; only original ordinals 2..204 may generate.

    Synthetic doubles may supply tensors/configuration through this Python seam.
    The executable worker has no slice, retry, historical-regeneration or test flag.
    """
    import random
    C.require_profile(profile)
    C.require(C.digest(C.encode(effective)) == profile['effective_generation_sha256']
              and C.encode(runtime) == C.encode(profile['runtime']),
              'ORIGINAL_GENERATION_RUNTIME_MISMATCH')
    C.fields(token_map, {'record_type', 'profile_sha256', 'model_revision',
                         'task_file_sha256', 'rows'})
    C.require(token_map['record_type'] == 'q3_token_map_v1'
              and token_map['profile_sha256'] == C.PROFILE_SHA256
              and token_map['model_revision'] == profile['model_revision']
              and token_map['task_file_sha256'] ==
                  profile['fixed_inputs'][C.FRAME + 'TASKS_DRAFT.jsonl'], 'TOKEN_MAP_IDENTITY')
    rows = token_map['rows']
    C.require(type(rows) is list and len(rows) == C.FRAME_COUNT, 'TOKEN_MAP_EXTENT')
    for original_ordinal, row in enumerate(rows, 1):
        C.fields(row, {'task_id', 'ordinal', 'input_ids', 'messages_sha256',
                       'logical_request_sha256'})
        C.require(type(row['ordinal']) is int and row['ordinal'] == original_ordinal
                  and row['task_id'] == profile['task_ids'][original_ordinal - 1]
                  and C.sha256_string(row['messages_sha256'])
                  and C.sha256_string(row['logical_request_sha256']), 'TOKEN_MAP_ORDER')
        tokens(row['input_ids'], 1, profile['limits']['max_prompt_tokens'], 'PROMPT_TOKENS')
    C.require(rows[0]['task_id'] == C.HISTORICAL_TASK_ID
              and C.digest(C.encode([r['task_id'] for r in rows[1:]])) ==
                  C.CONTINUATION_TASK_IDS_SHA256, 'CONTINUATION_SELECTION')
    for continuation_ordinal, row in enumerate(rows[1:], 1):
        task_id = row['task_id']
        slot = {'task_id': task_id, 'ordinal': row['ordinal'],
                'continuation_ordinal': continuation_ordinal, 'attempt': 1}
        C.require(read_command() == ('PREPARE ' + task_id + '\n').encode(), 'PREPARE_ORDER')
        ids = list(row['input_ids'])
        tensor = torch.tensor([ids], dtype=torch.long, device='cpu'); mask = torch.ones_like(tensor)
        config = config_class(**profile['generation'], disable_compile=True)
        C.require(C.encode(config.to_dict()) == C.encode(effective), 'GENERATION_CONFIGURATION_DRIFT')
        emit(C.encode({'record_type': 'q3_slot_ready_v1', 'binding': binding, 'slot': slot,
                       'input_ids': ids, 'effective_generation': effective, 'runtime': runtime}))
        C.require(read_command() == ('GENERATE ' + task_id + '\n').encode(), 'GENERATE_ORDER')
        random.seed(profile['seed']); torch.manual_seed(profile['seed'])
        with torch.inference_mode():
            sequence = model.generate(input_ids=tensor, attention_mask=mask,
                                      generation_config=config, use_model_defaults=False)
        C.require(len(sequence.shape) == 2 and sequence.shape[0] == 1, 'GENERATED_BATCH')
        new, stop = continuation(ids, sequence[0].tolist(), profile['generation']['max_new_tokens'])
        text = tokenizer.decode(new, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        C.require(type(text) is str and len(text.encode('utf-8')) <= profile['limits']['max_response_utf8_bytes'], 'RESPONSE_BYTES')
        record = {'record_type': 'q3_response_v1', 'binding': binding, 'slot': slot,
                  'input_ids': ids, 'new_token_ids': new, 'text': text,
                  'text_utf8_base64': base64.b64encode(text.encode('utf-8')).decode('ascii'),
                  'stop_reason': stop, 'effective_generation': effective, 'runtime': runtime}
        raw = C.encode(record)
        C.require(len(raw) <= profile['limits']['max_raw_frame_bytes'], 'RESPONSE_FRAME')
        emit(raw)
        # EOS and a complete bounded token-limit response are both retained.
        # The supervisor must validate this frame and close its watchdog before
        # issuing the next PREPARE/GENERATE. No task runs without those commands.
        del tensor, mask, sequence, config
    C.require(read_command() == b'FINISH\n', 'FINISH_REQUIRED')
    emit(C.encode({'record_type': 'q3_session_end_v1', 'binding': binding,
                   'completed_calls': C.CONTINUATION_COUNT}))


def run(source, bundle, prelaunch_path, expected_prelaunch):
    C.require(platform.python_implementation() == 'CPython' and platform.python_version() == '3.11.16', 'PYTHON_TARGET')
    C.require(platform.system() == 'Linux' and platform.machine() == 'x86_64'
              and platform.freedesktop_os_release().get('ID') == 'ubuntu'
              and platform.freedesktop_os_release().get('VERSION_ID') == '24.04', 'PLATFORM_TARGET')
    C.require(sys.flags.isolated and sys.prefix != sys.base_prefix and os.getuid() == 65534, 'ISOLATED_WORKER_REQUIRED')
    pre_raw = C.safe_read(prelaunch_path)
    C.require(C.digest(pre_raw) == expected_prelaunch, 'PRELAUNCH_DIGEST')
    pre = C.strict_json(pre_raw); p = C.load_profile(source)
    request = C.validate_request(C.encode(pre['request']), p)
    C.require(pre['record_type'] == 'q3_native_prelaunch_v1'
              and pre['source_commit'] == request['source_commit'], 'PRELAUNCH_IDENTITY')
    C.require(all(C.sha256_string(pre.get(name)) for name in
                  ('historical_verification_sha256', 'historical_phase_cleanup_sha256',
                   'historical_acquisition_sha256')), 'HISTORICAL_VERIFICATION_REQUIRED')
    if request['mode'] == 'capture':
        C.require(pre['historical_verification_sha256'] ==
                  request['historical_verification_sha256'], 'HISTORICAL_VERIFICATION_BINDING')
    C.require(set(pre['source_files']) == set(p['source_files']), 'SOURCE_SCOPE')
    for path, sha in pre['source_files'].items():
        C.require(C.digest(C.safe_read(source / C.relative(path))) == sha, 'SOURCE_CHANGED')
    frame = C.task_frame(source, p)
    tokenizer = load_tokenizer(source, bundle, p)
    binding = {'prelaunch_sha256': expected_prelaunch, 'run_id': pre['run_id'],
               'source_commit': pre['source_commit'], 'run_attempt': 1}
    def command():
        return sys.stdin.buffer.readline(512)
    def emit(raw):
        sys.stdout.buffer.write(raw); sys.stdout.buffer.flush()
    emit(C.encode({'record_type': 'q3_worker_ready_v1', 'binding': binding, 'mode': request['mode']}))
    C.require(command() == b'TOKENIZE\n', 'TOKENIZATION_NOT_AUTHORIZED')
    token_map = tokenize_frame(tokenizer, frame, p)
    for row in token_map['rows']:
        emit(C.encode({'record_type': 'q3_token_row_v1', 'binding': binding, 'row': row}))
    map_sha = C.digest(C.encode(token_map))
    emit(C.encode({'record_type': 'q3_token_map_end_v1', 'binding': binding,
                   'token_map_sha256': map_sha, 'task_count': len(frame)}))
    if request['mode'] == 'token-preflight':
        C.require(command() == b'FINISH\n', 'PREFLIGHT_FINISH')
        emit(C.encode({'record_type': 'q3_session_end_v1', 'binding': binding, 'completed_calls': 0}))
        return 0
    C.require(map_sha == request['approved_token_map_sha256'], 'APPROVED_PREFLIGHT_MISMATCH')
    C.require(command() == ('LOAD ' + map_sha + '\n').encode(), 'MODEL_LOAD_NOT_AUTHORIZED')
    model, torch, config_class, effective, runtime = load_model(bundle, p)
    ready_raw = C.encode({'record_type': 'q3_model_ready_v1', 'binding': binding,
                          'token_map_sha256': map_sha, 'effective_generation': effective, 'runtime': runtime})
    emit(ready_raw)
    subject = {'record_type': 'q3_capture_subject_v1', 'binding': binding,
               'model_ready_sha256': C.digest(ready_raw), 'token_map_sha256': map_sha,
               'historical_verification_sha256': pre['historical_verification_sha256']}
    subject_sha = C.digest(C.encode(subject))
    C.require(command() == ('BIND ' + subject_sha + '\n').encode(), 'SUBJECT_BINDING')
    binding = {**binding, 'subject_sha256': subject_sha}
    emit(C.encode({'record_type': 'q3_bound_v1', 'binding': binding}))
    capture_session(model, tokenizer, torch, config_class, effective, runtime,
                    token_map, p, binding, command, emit)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--prelaunch', type=Path, required=True)
    parser.add_argument('--expected-prelaunch-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        return run(args.source_root, args.bundle, args.prelaunch, args.expected_prelaunch_sha256)
    except Exception:
        print('Q3 v1 worker rejected or incomplete; no metric or release verdict.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
