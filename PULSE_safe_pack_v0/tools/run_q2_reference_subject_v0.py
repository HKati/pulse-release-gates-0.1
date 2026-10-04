#!/usr/bin/env python3
"""One fixed, unscored local Q2 diagnostic. Not the 150-call acquisition.

Only the external supervisor may supply the fixed prelaunch record and send GO.
No model imports happen when this module is imported for offline protocol tests.
The separate checker re-tokenizes and decodes; it never invokes this worker.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import stat
import sys

PACK = 'PULSE_safe_pack_v0/'
SELECTION = PACK + 'profiles/q2_reference_subject_v0.json'
MODEL_MAP = PACK + 'profiles/q2_reference_model_files_v0.json'
DIAGNOSTIC = PACK + 'profiles/q2_reference_diagnostic_v0.json'
SELF = PACK + 'tools/run_q2_reference_subject_v0.py'
PINNED_SELECTION = 'e81a9dd0a5080d84dae8c4bbfc843b46510f580e74254c1aed0dddbe76375f3e'
PINNED_MAP = '7df82db50a623326e12c333b69e5ef621c169bdddc663425fd8ed8e4be307de2'
DEFINITION_SHA = '688773b81fcf4f105b8770bc2dde9a68baf78aa76224e5c544cd0656109b07a5'
GENERATION = {'do_sample': False, 'num_beams': 1, 'num_return_sequences': 1,
              'max_new_tokens': 32, 'min_new_tokens': 0, 'use_cache': True,
              'repetition_penalty': 1.0, 'length_penalty': 1.0,
              'no_repeat_ngram_size': 0, 'bos_token_id': 1, 'eos_token_id': 2, 'pad_token_id': 2}
MESSAGES = [
    {'role': 'system', 'content': 'Read the short record. Return only the requested value, copied exactly from the record. Do not explain your answer.'},
    {'role': 'user', 'content': 'Record: diagnostic_marker=quartz.\nRequested field: diagnostic_marker.'}]
MODEL_NAMES = {'config.json', 'generation_config.json', 'merges.txt', 'model.safetensors',
               'special_tokens_map.json', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json'}


class WorkerError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise WorkerError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def serialize(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def file_bytes(path, maximum=512 * 1024 * 1024):
    path = path.absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'linked_input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        a = os.fstat(fd)
        require(stat.S_ISREG(a.st_mode) and a.st_nlink == 1 and a.st_size <= maximum, 'file_bound')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(maximum + 1)
        b = os.fstat(fd)
        require(len(raw) == a.st_size and (a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns) ==
                (b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns), 'file_changed')
        return raw
    finally:
        os.close(fd)


def json_value(raw):
    require(len(raw) <= 16 * 1024 * 1024 and not raw.startswith(b'\xef\xbb\xbf'), 'json_bound')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate_json_key')
            result[key] = value
        return result
    def invalid(_):
        raise WorkerError('invalid_number')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
    def walk(v, depth=0):
        require(depth <= 64, 'json_depth')
        if type(v) is str:
            v.encode('utf-8')
        elif type(v) is float:
            require(math.isfinite(v), 'invalid_number')
        elif type(v) is list:
            for item in v: walk(item, depth + 1)
        elif type(v) is dict:
            for k, item in v.items(): walk(k, depth + 1); walk(item, depth + 1)
    walk(value)
    return value


def bind_inputs(source, bundle, prelaunch_raw, expected_digest):
    require(digest(prelaunch_raw) == expected_digest, 'prelaunch_digest')
    pre = json_value(prelaunch_raw)
    require(pre['record_type'] == 'q2_native_prelaunch_v0' and pre['scored_call_count'] == 0
            and pre['production_gate_eligible'] is False and pre['authority_effect'] == 'none', 'wrong_phase')
    rows = {r['path']: r for r in pre['source_files']}
    require(SELF in rows, 'worker_source_missing')
    for name in (SELF, SELECTION, MODEL_MAP, DIAGNOSTIC):
        raw = file_bytes(source / name)
        require(len(raw) == rows[name]['size'] and digest(raw) == rows[name]['sha256'], 'source_replaced')
    require(digest(file_bytes(source / SELECTION)) == PINNED_SELECTION
            and digest(file_bytes(source / MODEL_MAP)) == PINNED_MAP, 'fixed_input_changed')
    selected = json_value(file_bytes(source / SELECTION))
    diagnostic = json_value(file_bytes(source / DIAGNOSTIC))
    require(serialize(diagnostic['messages']) == serialize(MESSAGES)
            and serialize(diagnostic['generation']) == serialize(GENERATION)
            and diagnostic['call_id'] == 'diagnostic-0001' and diagnostic['attempt'] == 1
            and diagnostic['scored'] is False and diagnostic['retries'] == 0
            and diagnostic['generation_seed'] == 1729, 'diagnostic_changed')
    model_map = json_value(file_bytes(source / MODEL_MAP))
    require({p.name for p in (bundle / 'model').iterdir()} == MODEL_NAMES, 'model_directory_scope')
    for row in model_map['files']:
        require(row['path'] in {'model/' + name for name in MODEL_NAMES}, 'model_path')
        raw = file_bytes(bundle / row['path'])
        require(digest(raw) == row['sha256'] and len(raw) == row['size'], 'model_file_changed')
    for name in ('config.json', 'generation_config.json'):
        cfg = json_value(file_bytes(bundle / 'model' / name))
        for key, number in (('bos_token_id', 1), ('eos_token_id', 2), ('pad_token_id', 2)):
            require(type(cfg.get(key)) is int and cfg[key] == number, 'staged_token_configuration')
    return selected, diagnostic, {
        'prelaunch_sha256': expected_digest, 'source_commit': pre['context']['source_commit'],
        'run_id': pre['context']['run_id'], 'run_attempt': 1}


def split_continuation(input_ids, sequence):
    require(type(sequence) is list and sequence[:len(input_ids)] == input_ids, 'generated_prefix_changed')
    new = sequence[len(input_ids):]
    require(1 <= len(new) <= 32 and all(type(i) is int and 0 <= i < 49152 for i in new), 'generated_token_bounds')
    if new[-1] == 2:
        require(2 not in new[:-1], 'multiple_eos')
        return new, 'eos'
    require(len(new) == 32 and 2 not in new, 'incomplete_generation')
    return new, 'token_limit'


def generate_once(model, tokenizer, torch, generation_config, input_tensor, attention_mask, binding, runtime):
    """Pure execution seam for synthetic offline doubles, never a CLI bypass."""
    import random
    random.seed(1729)
    torch.manual_seed(1729)
    input_ids = input_tensor[0].tolist()
    with torch.inference_mode():
        output = model.generate(input_ids=input_tensor, attention_mask=attention_mask,
                                generation_config=generation_config, use_model_defaults=False)
    require(len(output.shape) == 2 and output.shape[0] == 1, 'generated_batch')
    new, stop = split_continuation(input_ids, output[0].tolist())
    text = tokenizer.decode(new, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    require(type(text) is str, 'decoded_text_type')
    return {'record_type': 'q2_native_diagnostic_response_v0', 'binding': binding,
            'call_id': 'diagnostic-0001', 'attempt': 1, 'scored': False,
            'input_ids': input_ids, 'new_token_ids': new, 'text': text,
            'text_utf8_base64': base64.b64encode(text.encode('utf-8')).decode('ascii'),
            'stop_reason': stop, 'effective_generation': generation_config.to_dict(), 'runtime': runtime}


def run(source, bundle, prelaunch, expected):
    require(platform.python_implementation() == 'CPython' and platform.python_version() == '3.11.16', 'python_target')
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'machine_target')
    osr = platform.freedesktop_os_release()
    require(osr.get('ID') == 'ubuntu' and osr.get('VERSION_ID') == '24.04', 'os_target')
    require(sys.flags.isolated and sys.prefix != sys.base_prefix and os.getuid() == 65534, 'isolated_venv_required')
    selected, diagnostic, binding = bind_inputs(source, bundle, file_bytes(prelaunch), expected)
    # Imports are downstream of immutable local-byte verification and the external
    # sandbox barrier. Neither imports nor model generation occur on PR/push tests.
    import importlib.metadata
    import random
    import torch
    import transformers
    import rfc8785
    from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
    for module in (torch, transformers, rfc8785):
        require(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), 'module_outside_venv')
    require(torch.__version__ == '2.8.0+cpu' and transformers.__version__ == '4.57.6'
            and importlib.metadata.version('rfc8785') == '0.1.4' and torch.version.cuda is None, 'runtime_versions')
    require(digest(rfc8785.dumps(selected['release_subject']['definition'])) == DEFINITION_SHA, 'selected_definition')
    require(rfc8785.dumps({'a': 1.0, 'b': -0.0}) == b'{"a":1,"b":0}', 'jcs_runtime')
    require(rfc8785.dumps({'\ue000': 1, '\U00010000': 2}) == '{"\U00010000":2,"\ue000":1}'.encode(), 'jcs_utf16_order')
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(1729); torch.manual_seed(1729)
    tokenizer = AutoTokenizer.from_pretrained(str(bundle / 'model'), local_files_only=True,
                                              trust_remote_code=False, use_fast=True)
    require(tokenizer.is_fast and (tokenizer.bos_token_id, tokenizer.eos_token_id, tokenizer.pad_token_id) == (1, 2, 2),
            'loaded_tokenizer_configuration')
    model = AutoModelForCausalLM.from_pretrained(str(bundle / 'model'), local_files_only=True,
        trust_remote_code=False, use_safetensors=True, torch_dtype=torch.float32,
        attn_implementation='eager', device_map=None)
    model.to('cpu'); model.eval()
    require(type(model).__name__ == 'LlamaForCausalLM' and not model.training
            and model.config._attn_implementation == 'eager'
            and not getattr(model, 'is_quantized', False)
            and all(p.device.type == 'cpu' and p.dtype == torch.float32 for p in model.parameters()), 'loaded_model_configuration')
    require(torch.get_num_threads() == torch.get_num_interop_threads() == 1
            and torch.are_deterministic_algorithms_enabled(), 'effective_thread_configuration')
    config = GenerationConfig(**GENERATION, disable_compile=True)
    ids = tokenizer.apply_chat_template(diagnostic['messages'], tokenize=True, add_generation_prompt=True)
    require(type(ids) is list and 1 <= len(ids) <= 4096 and all(type(i) is int for i in ids), 'prompt_token_bounds')
    input_tensor = torch.tensor([ids], dtype=torch.long, device='cpu')
    attention_mask = torch.ones_like(input_tensor)
    runtime = {'torch': torch.__version__, 'transformers': transformers.__version__, 'device': 'cpu',
               'dtype': str(torch.float32), 'attention': model.config._attn_implementation,
               'threads': torch.get_num_threads(), 'interop_threads': torch.get_num_interop_threads(),
               'deterministic': torch.are_deterministic_algorithms_enabled(), 'evaluation': not model.training,
               'model_class': type(model).__name__, 'seed': 1729,
               'model_defaults': False, 'compile': False, 'quantization': 'none'}
    ready = {'record_type': 'q2_native_model_ready_v0', 'binding': binding, 'input_ids': ids,
             'effective_generation': config.to_dict(), 'runtime': runtime}
    sys.stdout.buffer.write(serialize(ready)); sys.stdout.buffer.flush()
    # The external supervisor arms the independent systemd timer before this GO.
    require(sys.stdin.buffer.readline(64) == b'GENERATE diagnostic-0001\n', 'generation_not_authorized')
    result = generate_once(model, tokenizer, torch, config, input_tensor, attention_mask, binding, runtime)
    sys.stdout.buffer.write(serialize(result)); sys.stdout.buffer.flush()
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
        # Runtime error is incompleteness, never a model-produced UNKNOWN.
        print('Q2 diagnostic worker failed; no completed occurrence', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
