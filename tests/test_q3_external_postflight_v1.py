#!/usr/bin/env python3
"""Synthetic v1 preflight/handoff controls; no retained response or live service.

The native reconstruction callback is a test double. These tests exercise the
real source, request, metadata, acquisition and immediate-admission bindings;
the native/historical checker suites own their independent protocol tests.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import zipfile

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMPARATOR = 'tools/check_q3_external_postflight_v1.py'
ACQUIRER = 'tools/acquire_q3_external_postflight_v1.py'
HANDOFF = 'tools/q3_capture_handoff_v2.py'
CONTRACT = 'PULSE_safe_pack_v0/tools/q3_native_capture_contract_v1.py'
NOW = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
COMMIT = 'c' * 40
PREFLIGHT_ID = '91001'
CAPTURE_ID = '91004'
WORKFLOW_ID = 91005  # Explicitly synthetic; not the new workflow's real ID.


def load(name):
    spec = importlib.util.spec_from_file_location('synthetic_' + Path(name).stem, ROOT / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def archive(data):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, value in sorted(data.items()):
            z.writestr(name, value)
    return out.getvalue()


def request(c, profile, mode, historical_sha=None, map_sha=None):
    value = {'record_type': 'q3_native_capture_request_v1', 'mode': mode,
        'repository': c.REPOSITORY, 'source_commit': COMMIT, 'profile_sha256': c.PROFILE_SHA256,
        'task_file_sha256': profile['fixed_inputs'][c.FRAME + 'TASKS_DRAFT.jsonl'],
        'authorization': c.AUTHORIZATIONS[mode], 'approved_token_map_sha256': map_sha,
        'amendment_sha256': c.AMENDMENT_SHA256,
        'historical_verification_sha256': historical_sha,
        'limits': profile['limits'], 'claims': dict(c.CLAIMS), 'new_spend_authorized': 0}
    c.validate_request(c.encode(value), profile)
    return value


def carrier(f, native_request, run_id):
    """Minimal fabricated carrier, accepted only by the explicit test double."""
    c = f['c']; raw_request = c.encode(native_request)
    data = {'request.json': raw_request, 'token-map.json': f['token_map'],
        'historical-verification.json': f['historical'],
        'result.json': c.encode({'synthetic_only': True}),
        'control-plane.json': c.encode({'repository': c.REPOSITORY, 'run_id': run_id,
            'run_attempt': 1, 'source_commit': COMMIT, 'workflow': f['h'].WORKFLOW,
            'head_branch': 'main', 'actor': 'HKati', 'triggering_actor': 'HKati',
            'event': 'workflow_dispatch'}),
        'platform.json': c.encode({'runner_image': 'synthetic-image-1'})}
    data.update({'source/' + n: b for n, b in f['source'].items()})
    inner = archive(data)
    receipt = {'record_type': 'q3_native_capture_receipt_v1', 'status': 'complete',
        'mode': native_request['mode'], 'source_commit': COMMIT,
        'archive_sha256': c.digest(inner), 'archive_size_bytes': len(inner),
        'request_sha256': c.digest(raw_request), 'token_map_sha256': c.digest(f['token_map']),
        'result_sha256': c.digest(data['result.json']), 'claims': dict(c.CLAIMS)}
    return {'evidence.zip': inner, 'receipt.json': c.encode(receipt)}


@pytest.fixture
def case(monkeypatch):
    m, a, h, c = (load(n) for n in (COMPARATOR, ACQUIRER, HANDOFF, CONTRACT))
    profile = c.load_profile(ROOT)
    source = {name: (ROOT / name).read_bytes() for name in profile['source_files']}
    historical = c.encode({'synthetic_only': True, 'amendment_sha256': c.AMENDMENT_SHA256,
        'verifier_source_commit': COMMIT, 'verifier_profile_sha256': c.PROFILE_SHA256})
    token_map = c.encode({'synthetic_only': True, 'profile_sha256': c.PROFILE_SHA256})
    f = {'m': m, 'a': a, 'h': h, 'c': c, 'p': profile, 'source': source,
         'historical': historical, 'token_map': token_map}
    preflight = request(c, profile, 'token-preflight')
    outer = archive(carrier(f, preflight, PREFLIGHT_ID))
    extra = {name: source[name] for name in h.EXTRA_SOURCES}
    selected = {'record_type': 'q3_external_postflight_acquisition_request_v1',
        'repository': m.REPOSITORY, 'source_commit': COMMIT, 'workflow_id': WORKFLOW_ID,
        'run_id': PREFLIGHT_ID, 'run_attempt': 1, 'job_id': 91002, 'artifact_id': 91003,
        'request_sha256': m.digest(c.encode(preflight)), 'token_map_sha256': m.digest(token_map),
        'amendment_sha256': c.AMENDMENT_SHA256,
        'historical_verification_sha256': m.digest(historical),
        'archive': {'size_bytes': len(outer), 'sha256': m.digest(outer)},
        'source_files': {name: h.pin(b) for name, b in source.items()},
        'acquirer_sha256': m.digest(source[ACQUIRER]),
        'comparator_sha256': m.digest(source[COMPARATOR])}
    api = 'https://api.github.com/repos/' + m.REPOSITORY
    repo = {'id': m.REPOSITORY_ID, 'full_name': m.REPOSITORY, 'fork': False,
            'owner': {'login': 'HKati', 'id': m.OWNER_ID}}
    actor = {'login': 'HKati', 'id': m.OWNER_ID}
    run = {'id': int(PREFLIGHT_ID), 'run_attempt': 1, 'head_sha': COMMIT,
        'head_commit': {'id': COMMIT}, 'path': h.WORKFLOW, 'workflow_id': WORKFLOW_ID,
        'status': 'completed', 'conclusion': 'success', 'head_branch': 'main',
        'event': 'workflow_dispatch', 'url': api + '/actions/runs/' + PREFLIGHT_ID,
        'repository': repo, 'head_repository': repo, 'actor': actor, 'triggering_actor': actor,
        'run_started_at': '2026-11-11T10:00:00Z', 'updated_at': '2026-11-11T11:00:00Z'}
    job = {'id': selected['job_id'], 'run_id': int(PREFLIGHT_ID), 'run_attempt': 1,
        'head_sha': COMMIT, 'head_branch': 'main', 'name': 'acquire', 'status': 'completed',
        'conclusion': 'success', 'run_url': run['url'], 'url': api + '/actions/jobs/91002',
        'labels': ['ubuntu-24.04'], 'started_at': '2026-11-11T10:00:01Z',
        'completed_at': '2026-11-11T11:00:00Z',
        'steps': [{'name': 'Set up job', 'number': 1, 'status': 'completed',
                   'conclusion': 'success', 'started_at': '2026-11-11T10:00:02Z',
                   'completed_at': '2026-11-11T10:00:04Z'}]}
    art = {'id': selected['artifact_id'], 'name': 'q3-reference-capture-' + PREFLIGHT_ID + '-1',
        'size_in_bytes': len(outer), 'digest': 'sha256:' + m.digest(outer), 'expired': False,
        'url': api + '/actions/artifacts/91003',
        'workflow_run': {'id': int(PREFLIGHT_ID), 'repository_id': m.REPOSITORY_ID,
            'head_repository_id': m.REPOSITORY_ID, 'head_branch': 'main', 'head_sha': COMMIT},
        'created_at': '2026-11-11T10:59:00Z', 'updated_at': '2026-11-11T10:59:00Z',
        'expires_at': '2026-12-11T10:59:00Z'}
    lines = ['##[group]Runner Image', 'Image: ubuntu-24.04', 'Version: synthetic-image-1',
        '##[endgroup]', 'EXPECTED_SOURCE_SHA: ' + COMMIT,
        'Q3_NATIVE_REQUEST_SHA256: ' + selected['request_sha256'], 'Complete job name: acquire',
        'Uploaded bytes ' + str(len(outer)),
        'SHA256 digest of uploaded artifact is ' + m.digest(outer),
        'Artifact q3-reference-capture-' + PREFLIGHT_ID + '-1 successfully finalized. Artifact ID 91003',
        'Artifact q3-reference-capture-' + PREFLIGHT_ID + '-1 has been successfully uploaded!'
        ' Final size is ' + str(len(outer)) + ' bytes. Artifact ID is 91003']
    raw = {'artifact.zip': outer, 'run.json': m.encode(run),
        'jobs.json': m.encode({'total_count': 1, 'jobs': [job]}), 'artifact.json': m.encode(art),
        'job.log': ''.join('2026-11-11T10:00:03Z ' + line + '\n' for line in lines).encode()}
    nr = request(c, profile, 'capture', m.digest(historical), m.digest(token_map))
    sr = a.encode(selected); nb = c.encode(nr)
    envelope = {'record_type': h.REQUEST_TYPE, 'repository': h.REPOSITORY,
        'capture_source_commit': COMMIT, 'native_request_utf8': nb.decode(),
        'native_request_sha256': h.digest(nb), 'postflight_selection_utf8': sr.decode(),
        'postflight_selection_sha256': h.digest(sr),
        'handoff_source_files': {n: h.pin(b) for n, b in extra.items()},
        'authorization': h.AUTHORIZATION}
    current = {'id': int(CAPTURE_ID), 'run_attempt': 1, 'head_sha': COMMIT,
        'head_branch': 'main', 'event': 'workflow_dispatch', 'status': 'in_progress',
        'conclusion': None, 'path': h.WORKFLOW, 'workflow_id': WORKFLOW_ID,
        'actor': actor, 'triggering_actor': actor}
    f.update(s=selected, raw=raw, extra=extra, envelope=envelope, nr=nr, current=current)

    def synthetic_replay(inner, sources, expectation):
        assert sources == source
        d = m.unzip(inner)
        assert m.strict_json(d['result.json']) == {'synthetic_only': True}
        r = c.validate_request(d['request.json'], profile)
        assert r['source_commit'] == expectation['source_commit']
        assert m.digest(d['request.json']) == expectation['request_sha256']
        assert d['historical-verification.json'] == historical
        return {'record_type': 'q3_carrier_reconstruction_v1', 'complete': True,
            'mode': r['mode'], 'request_sha256': m.digest(d['request.json']),
            'token_map_sha256': m.digest(d['token-map.json']),
            'historical_verification_sha256': m.digest(historical),
            'amendment_sha256': c.AMENDMENT_SHA256, 'claims': dict(c.CLAIMS)}

    monkeypatch.setattr(m, 'native_replay', synthetic_replay)
    monkeypatch.setattr(a, 'utc_now', lambda: NOW)
    monkeypatch.setattr(h, 'now', lambda: '2026-11-11T12:00:00Z')
    return f


class FakeReader:
    def __init__(self, f):
        self.f = f; self.transfers = []; self.calls = []
        self.routes = {route: name for name, route in f['a'].paths(f['s']).items()}

    def _record(self, route, body, storage):
        self.calls.append(route)
        self.transfers.append({'endpoint': route, 'sha256': self.f['m'].digest(body),
            'size_bytes': len(body), 'download_host': 'synthetic.blob.core.windows.net' if storage else None})
        return body

    def json(self, route):
        current = self.f['a'].API_PREFIX + 'runs/' + CAPTURE_ID + '/attempts/1'
        body = self.f['m'].encode(self.f['current']) if route == current else self.f['raw'][self.routes[route]]
        return self._record(route, body, False)

    def download(self, route, maximum):
        body = self.f['raw'][self.routes[route]]
        assert len(body) <= maximum
        return self._record(route, body, True)


def compare(f):
    e = f['m'].encode(f['a'].expectation(f['s'], f['raw'], f['m']))
    return f['m'].compare(e, f['m'].digest(e), f['raw'])


def validate(f):
    raw = f['h'].encode(f['envelope'])
    return f['h'].validate(raw, f['h'].digest(raw), f['c'].encode(f['nr']),
        f['source'], f['extra'], ROOT, f['a'], f['m'])


def reselect(f, **updates):
    f['s'].update(updates)
    raw = f['a'].encode(f['s'])
    f['envelope'].update(postflight_selection_utf8=raw.decode(), postflight_selection_sha256=f['h'].digest(raw))


def execute_handoff(f, tmp_path, monkeypatch, *, native_error=False):
    h, a, c = f['h'], f['a'], f['c']
    reader = FakeReader(f); calls = []
    monkeypatch.setattr(h, 'components', lambda *args: (a, f['m']))
    monkeypatch.setattr(a, 'GitHubReader', lambda token: reader)
    output = tmp_path / 'published'; output.mkdir()
    runner = tmp_path / 'runner'; runner.mkdir()

    def native(c, p, r, sources, root, raw, env):
        calls.append(copy.deepcopy(r))
        assert r['historical_verification_sha256'] == f['s']['historical_verification_sha256']
        assert r['limits']['max_attempts'] == 203
        if native_error:
            raise OSError('synthetic private error')
        out = Path(env['RUNNER_TEMP']) / 'q3-reference-capture' / (CAPTURE_ID + '-1')
        out.mkdir(parents=True)
        for name, body in carrier(f, r, CAPTURE_ID).items():
            (out / name).write_bytes(body)
        return 0

    env = {'GITHUB_SHA': COMMIT, 'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_RUN_ID': CAPTURE_ID,
           'GITHUB_TOKEN': 'synthetic-token', 'RUNNER_TEMP': str(runner)}
    rc = h.run(c, f['p'], f['nr'], f['source'], ROOT, h.encode(f['envelope']), env,
        f['extra'], native, lambda *args: {'run_id': CAPTURE_ID, 'source_commit': COMMIT},
        lambda *args: (output, os.getuid(), os.getgid()))
    return rc, calls, reader, output


def test_final_pins_and_source_closure_match_exact_files(case):
    f = case; m, a, h = f['m'], f['a'], f['h']
    assert m.PROFILE_SHA256 == f['c'].PROFILE_SHA256 == m.digest(f['source'][m.PROFILE])
    assert m.SOURCE_FILE_COUNT == len(f['source'])
    assert a.COMPARATOR_SHA256 == h.COMPARATOR_SHA == m.digest(f['source'][COMPARATOR])
    assert h.ACQUIRER_SHA == m.digest(f['source'][ACQUIRER])
    pins = m.reviewed_checker_pins(f['source'])
    assert all(m.digest(f['source'][name]) == sha for name, sha in pins.items())
    a0, m0 = h.components(ROOT, f['extra'])
    assert a0.COMPARATOR_SHA256 == m.digest(f['source'][COMPARATOR])
    assert m0.AMENDMENT_SHA256 == f['c'].AMENDMENT_SHA256
    assert a.load_comparator().PROFILE_SHA256 == f['c'].PROFILE_SHA256


def test_synthetic_fresh_preflight_compares_without_granting_permission(case):
    result = compare(case)
    assert result['disposition'] == 'CONSISTENT_OFFLINE'
    assert result['historical_verification_sha256'] == case['s']['historical_verification_sha256']
    assert result['amendment_sha256'] == case['c'].AMENDMENT_SHA256
    assert result['capture_handoff_approved'] is False and result['new_execution_authorized'] is False
    assert result['model_executed'] is False and result['tokenization_reperformed'] is False


def upload_log(case, progress, size=19828736):
    """Use the actual multi-block byte totals without fabricating a native run."""
    m = case['m']
    expected = case['a'].expectation(case['s'], case['raw'], m)
    old_size = expected['inputs']['artifact.zip']['size_bytes']
    expected['inputs']['artifact.zip']['size_bytes'] = size
    log = case['raw']['job.log'].replace(
        ('2026-11-11T10:00:03Z Uploaded bytes ' + str(old_size) + '\n').encode(),
        ''.join('2026-11-11T10:00:03Z ' + line + '\n' for line in progress).encode())
    log = log.replace(('Final size is ' + str(old_size) + ' bytes.').encode(),
                      ('Final size is ' + str(size) + ' bytes.').encode())
    startup = json.loads(case['raw']['jobs.json'])['jobs'][0]['steps'][0]
    return log, expected, startup


@pytest.mark.parametrize('totals', [
    [19828736],
    [8388608, 16777216, 19828736],  # Observed preflight 43136688284/1.
    [3051520, 11440128, 19828736],  # Final partial block may finish first.
])
def test_upload_progress_accepts_single_or_multiple_cumulative_totals(case, totals):
    log, expected, startup = upload_log(case, ['Uploaded bytes ' + str(n) for n in totals])
    result = case['m'].inspect_log(log, expected, startup)
    assert result['value'] == 'synthetic-image-1'
    assert result['sha256'] == case['m'].digest(log)


@pytest.mark.parametrize('progress', [
    [],
    ['Uploaded bytes 8388608', 'Uploaded bytes 16777216'],
    ['Uploaded bytes 8388608', 'Uploaded bytes 19828737', 'Uploaded bytes 19828736'],
    ['Uploaded bytes 16777216', 'Uploaded bytes 8388608', 'Uploaded bytes 19828736'],
    ['Uploaded bytes 8388608', 'Uploaded bytes 8388608', 'Uploaded bytes 19828736'],
    ['Uploaded bytes 19828736', 'Uploaded bytes 19828736'],
    ['Uploaded bytes 0', 'Uploaded bytes 19828736'],
    ['Uploaded bytes -1', 'Uploaded bytes 19828736'],
    ['Uploaded bytes 8.0', 'Uploaded bytes 19828736'],
    ['Uploaded bytes +8', 'Uploaded bytes 19828736'],
    ['Uploaded bytes 08', 'Uploaded bytes 19828736'],
    ['Uploaded bytes 8388608 extra', 'Uploaded bytes 19828736'],
    ['Uploaded bytes malformed', 'Uploaded bytes 19828736'],
    [' Uploaded bytes 8388608', 'Uploaded bytes 19828736'],
    ['Uploaded bytes 8388608 ', 'Uploaded bytes 19828736'],
    ['Uploaded bytes ٨', 'Uploaded bytes 19828736'],
    ['Uploaded bytes' + '9' * 100, 'Uploaded bytes 19828736'],
    ['Uploaded bytes ' + '9' * 100, 'Uploaded bytes 19828736'],
])
def test_upload_progress_rejects_incomplete_conflicting_or_malformed_totals(case, progress):
    log, expected, startup = upload_log(case, progress)
    with pytest.raises(ValueError, match='^LOG_ARTIFACT_SIZE$'):
        case['m'].inspect_log(log, expected, startup)


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'size', 'name', 'id', 'malformed'])
def test_upload_summary_binds_final_size_name_and_id(case, fault):
    log, expected, startup = upload_log(case, ['Uploaded bytes 8388608', 'Uploaded bytes 19828736'])
    summary = ('2026-11-11T10:00:03Z Artifact q3-reference-capture-' + PREFLIGHT_ID + '-1'
        ' has been successfully uploaded! Final size is 19828736 bytes. Artifact ID is 91003\n').encode()
    replacement = {'missing': b'', 'duplicate': summary + summary,
        'size': summary.replace(b'19828736', b'19828735'),
        'name': summary.replace(b'q3-reference-capture-', b'wrong-artifact-'),
        'id': summary.replace(b'91003', b'91009'),
        'malformed': summary.replace(b'19828736', b'not-a-size')}[fault]
    log = log.replace(summary, replacement)
    with pytest.raises(ValueError, match='^LOG_ARTIFACT_FINAL_SIZE$'):
        case['m'].inspect_log(log, expected, startup)


def test_upload_progress_multi_block_comparison_preserves_other_bindings(case):
    size = len(case['raw']['artifact.zip'])
    log, _, _ = upload_log(case, ['Uploaded bytes 1', 'Uploaded bytes ' + str(size // 2),
                                'Uploaded bytes ' + str(size)], size)
    case['raw']['job.log'] = log
    result = compare(case)
    assert result['disposition'] == 'CONSISTENT_OFFLINE'
    assert result['capture_handoff_approved'] is False
    case['raw']['job.log'] = log.replace(
        b'SHA256 digest of uploaded artifact is ', b'SHA256 digest of uploaded artifact is 0')
    with pytest.raises(ValueError, match='^LOG_ARTIFACT_DIGEST$'):
        compare(case)


def test_synthetic_acquisition_rechecks_metadata_without_saved_comparison(case, tmp_path):
    f = case; a = f['a']; reader = FakeReader(f)
    selection = a.encode(f['s'])
    a.select(selection, a.digest(selection), f['m'])
    store = a.EvidenceDirectory(tmp_path / 'acquired')
    try:
        result, comparison = a.acquire(f['s'], reader, store, f['m'])
        store.finish()
    finally:
        store.close()
    assert result['disposition'] == 'CONSISTENT_OFFLINE'
    assert comparison == f['m'].encode(compare(f))
    assert len(reader.calls) == 8
    assert reader.calls[:3] == reader.calls[-3:]


def test_fresh_matching_handoff_invokes_native_exactly_once(case, tmp_path, monkeypatch):
    validate(case)
    rc, calls, reader, output = execute_handoff(case, tmp_path, monkeypatch)
    assert rc == 0 and len(calls) == 1
    receipt = json.loads((output / 'receipt.json').read_bytes())
    assert receipt['record_type'] == 'q3_capture_handoff_receipt_v2'
    assert receipt['status'] == 'complete' and receipt['authority_effect'] == 'none'
    assert len(reader.calls) == 10
    data = case['h'].unzip((output / 'evidence.zip').read_bytes())
    admission = json.loads(data['admission.json'])
    assert admission['new_generation_call_count'] == 203
    assert admission['historical_verification_sha256'] == case['s']['historical_verification_sha256']
    assert admission['reuse_of_saved_approval_allowed'] is False
    assert not any(output.parent.joinpath('runner').iterdir())


@pytest.mark.parametrize('key,value,code', [
    ('historical_verification_sha256', '0' * 64, 'HANDOFF_HISTORICAL_RECEIPT_BINDING'),
    ('source_commit', 'a' * 40, 'HANDOFF_PREFLIGHT_SOURCE'),
    ('token_map_sha256', '0' * 64, 'HANDOFF_APPROVED_MAP'),
    ('amendment_sha256', '0' * 64, 'EXPECTATION_AMENDMENT'),
    ('record_type', 'q3_external_postflight_acquisition_request_v0', 'SELECTION_IDENTITY'),
    ('workflow_id', True, 'EXPECTATION_EXECUTION'),
])
def test_incompatible_selection_rejected_before_provider(case, key, value, code):
    reselect(case, **{key: value})
    with pytest.raises(ValueError, match=code):
        validate(case)


@pytest.mark.parametrize('field', ['saved_approval', 'comparison', 'historical_receipt'])
def test_saved_verdict_is_not_an_envelope_input(case, field):
    case['envelope'][field] = {'approved': True}
    with pytest.raises(ValueError, match='HANDOFF_REQUEST_FIELDS'):
        validate(case)


def test_copied_historical_token_map_is_rejected(case):
    f = case
    f['nr']['approved_token_map_sha256'] = f['c'].HISTORICAL_TOKEN_MAP_SHA256
    nr = f['c'].encode(f['nr'])
    f['envelope'].update(native_request_utf8=nr.decode(), native_request_sha256=f['h'].digest(nr))
    reselect(f, token_map_sha256=f['c'].HISTORICAL_TOKEN_MAP_SHA256)
    with pytest.raises(ValueError, match='PREFLIGHT_ANCHOR_REQUIRED'):
        validate(f)


@pytest.mark.parametrize('field,value', [
    ('workflow_id', WORKFLOW_ID + 1), ('id', int(PREFLIGHT_ID)), ('head_sha', 'a' * 40),
    ('run_attempt', 2), ('event', 'pull_request'), ('path', '.github/workflows/q3_reference_acquisition_v0.yml'),
])
def test_current_context_mismatch_never_invokes_native(case, tmp_path, monkeypatch, field, value):
    case['current'][field] = value
    rc, calls, _, output = execute_handoff(case, tmp_path, monkeypatch)
    assert rc == 2 and calls == []
    receipt = json.loads((output / 'receipt.json').read_bytes())
    assert receipt['status'] == 'rejected'


def test_preflight_workflow_id_must_match_selected_id(case, tmp_path, monkeypatch):
    run = json.loads(case['raw']['run.json']); run['workflow_id'] += 1
    case['raw']['run.json'] = case['m'].encode(run)
    rc, calls, reader, _ = execute_handoff(case, tmp_path, monkeypatch)
    assert rc == 2 and calls == []
    assert not any(route.endswith('/zip') for route in reader.calls)


def test_image_disagreement_is_not_normalized_into_admission(case, tmp_path, monkeypatch):
    case['raw']['job.log'] = case['raw']['job.log'].replace(b'Version: synthetic-image-1', b'Version: synthetic-image-2')
    rc, calls, _, _ = execute_handoff(case, tmp_path, monkeypatch)
    assert rc == 2 and calls == []


def test_replay_receipt_mismatch_cannot_become_admission(case, tmp_path, monkeypatch):
    replay = case['m'].native_replay
    def wrong(*args):
        return {**replay(*args), 'historical_verification_sha256': 'f' * 64}
    monkeypatch.setattr(case['m'], 'native_replay', wrong)
    rc, calls, _, _ = execute_handoff(case, tmp_path, monkeypatch)
    assert rc == 2 and calls == []


def test_selected_historical_hash_must_match_actual_carrier(case):
    case['s']['historical_verification_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='HISTORICAL_RECEIPT_BINDING'):
        compare(case)


def test_native_failure_is_preserved_without_retry(case, tmp_path, monkeypatch):
    rc, calls, _, output = execute_handoff(case, tmp_path, monkeypatch, native_error=True)
    assert rc == 1 and len(calls) == 1
    assert json.loads((output / 'receipt.json').read_bytes())['status'] == 'incomplete'
    assert (output / 'failure.json').exists()
    assert b'synthetic private error' not in (output / 'failure.json').read_bytes()


def test_historical_helper_is_part_of_reviewed_native_replay(case):
    source = dict(case['source'])
    source['tools/check_q3_historical_observation_v1.py'] += b'\n# substituted\n'
    with pytest.raises(ValueError, match='UNREVIEWED_NATIVE_CHECKER'):
        case['m'].reviewed_checker_pins(source)


def test_real_native_replay_imports_only_pinned_repository_shaped_helpers(case):
    m = load(COMPARATOR)
    with pytest.raises(ValueError, match='NATIVE_CARRIER_REJECTED'):
        m.native_replay(b'not a native carrier', case['source'],
            {'request_sha256': '0' * 64, 'source_commit': COMMIT})


def test_v2_schema_is_closed_and_requires_new_explicit_authorization(case):
    from jsonschema import Draft202012Validator
    schema = json.loads((ROOT / case['h'].SCHEMA).read_bytes())
    validator = Draft202012Validator(schema)
    validator.validate(case['envelope'])
    old = copy.deepcopy(case['envelope'])
    old['authorization'] = 'AUTHORIZE_ONE_OWNER_CAPTURE_DISPATCH_WITH_FRESH_POSTFLIGHT_AND_30_DAY_RETENTION'
    assert list(validator.iter_errors(old))
    old = copy.deepcopy(case['envelope']); old['saved_approval'] = True
    assert list(validator.iter_errors(old))

