"""Explicit-interpreter E0 compatibility runner; no network, repository writes or installs.

The historical evaluator, checks and expectations are copied byte-for-byte.
Only the copied coordinator's environment gate and environment description are
adapted, with an exact diff. Missing versions never produce matrix MATCH.
"""
from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

HERE = Path(__file__).resolve().parent
SOURCE_SNAPSHOT = '102145d1f1c321811c52d9d20f92cc7289127b2b'
VERSIONS = ('3.11.14', '3.12.12', '3.13.5', '3.14.3')
SCENARIOS = ('E00', 'E10', 'E11', 'E12', 'E13', 'E20', 'E30', 'E40')
CONTROLS = ('G01', 'G02', 'G03', 'G04', 'G05', 'G06')
STAGES = ('field_checker', 'edge_checker', 'example_acceptance')
VIEW_KEYS = ('reference_relation_assessment', 'reference_source_assessment',
             'proof_applicability_assessment', 'carrier_assessment',
             'semantic_projection_sha256', 'selected_subject', 'missing_source_premises',
             'source_differences', 'certificate_reuse', 'link_checks', 'witnesses',
             'certificate', 'evidence_view_identity', 'accepted_source_sha256',
             'semantic_preserved', 'unresolved_obligations')
CLEAN_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
             'TERM': 'dumb', 'NO_COLOR': '1'}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_hash(path: Path) -> str:
    return digest(path.read_bytes())


def blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def strict_json(raw: bytes) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('non-finite JSON number: ' + value)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False,
                                sort_keys=True, allow_nan=False).encode('utf-8') + b'\n')


def regular_under(root: Path, relative: str) -> Path:
    """No traversal or symlink components, even when a link points within root."""
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(x in ('.', '..') for x in rel.parts):
        raise ValueError('invalid relative path: ' + relative)
    candidate = root
    for component in rel.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise ValueError('symlink in input: ' + relative)
    if not candidate.is_file() or not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError('missing/nonregular input: ' + relative)
    return candidate


def verify_package(package: Path) -> dict:
    contract = strict_json((package / 'matrix_contract.json').read_bytes())
    if (contract.get('schema_version') != 'pd_sm_01_compatibility_v0'
            or contract.get('required_versions') != list(VERSIONS)
            or contract.get('source_snapshot') != SOURCE_SNAPSHOT
            or contract.get('scenario_ids') != list(SCENARIOS)
            or contract.get('control_ids') != list(CONTROLS)
            or contract.get('regression_test_methods') != 18
            or contract.get('authority_effect') != 'none'):
        raise ValueError('matrix contract mismatch')
    expected_names = {'README.md', 'case_expectations.json', 'independent_reference.py',
                      'run_cases.py', 'test_harness.py'}
    if set(contract['core_sha256']) != expected_names:
        raise ValueError('core inventory mismatch')
    for name, wanted in contract['core_sha256'].items():
        if file_hash(regular_under(package, 'core/' + name)) != wanted:
            raise ValueError('changed historical core: ' + name)
    for name, key in [('SOURCE_BINDINGS.json', 'source_manifest_sha256'),
                      ('ENVIRONMENT_PROFILE_REVISION.json', 'environment_revision_sha256')]:
        if file_hash(regular_under(package, name)) != contract[key]:
            raise ValueError('changed historical input: ' + name)
    return contract


def verify_sources(source: Path, manifest: dict) -> list[dict]:
    if manifest.get('selected_snapshot') != SOURCE_SNAPSHOT or len(manifest.get('files', [])) != 12:
        raise ValueError('source manifest scope mismatch')
    records, seen = [], set()
    for row in manifest['files']:
        path = row['path']
        if path in seen or row.get('snapshot') != SOURCE_SNAPSHOT:
            raise ValueError('duplicate/wrong-snapshot source')
        seen.add(path)
        raw = regular_under(source, path).read_bytes()
        if blob(raw) != row['expected_git_blob_sha1']:
            raise ValueError('SOURCE_MISMATCH: ' + path)
        records.append({'path': path, 'bytes': len(raw), 'git_blob_sha1': blob(raw),
                        'sha256': digest(raw)})
    return records


def adapt_runner(original: str, version: str) -> str:
    if version not in VERSIONS:
        raise ValueError('version outside declared profile')
    edits = {
        "platform.python_version()!='3.13.5'": 'platform.python_version()!=' + repr(version),
        'this run profile requires CPython 3.13.5 Linux':
            'this separate compatibility profile requires CPython ' + version + ' Linux',
        'Only CPython 3.13.5 Linux executed; no cross-version equivalence claim.':
            'This individual record covers only CPython ' + version +
            ' Linux; the cross-record comparison is separate.',
    }
    for old, new in edits.items():
        if original.count(old) != 1:
            raise ValueError('historical environment-gate template changed')
        original = original.replace(old, new)
    return original


def version_probe(executable: Path, folder: Path) -> tuple[dict, dict]:
    code = ('import json,platform,sys,sysconfig; print(json.dumps({'
            '"version":platform.python_version(),"implementation":platform.python_implementation(),'
            '"platform":platform.system(),"machine":platform.machine(),"sys_version":sys.version,'
            '"executable":sys.executable,"cache_tag":sys.implementation.cache_tag,'
            '"soabi":sysconfig.get_config_var("SOABI"),"compiler":platform.python_compiler()}))')
    argv = [str(executable), '-I', '-S', '-B', '-c', code]
    started = datetime.now(timezone.utc).isoformat()
    try:
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              stdin=subprocess.DEVNULL, timeout=10, env=CLEAN_ENV, cwd=folder)
    except subprocess.TimeoutExpired as error:
        (folder / 'probe.stdout').write_bytes(error.stdout or b'')
        (folder / 'probe.stderr').write_bytes(error.stderr or b'')
        raise ValueError('INTERPRETER_PROBE_TIMEOUT') from error
    (folder / 'probe.stdout').write_bytes(proc.stdout)
    (folder / 'probe.stderr').write_bytes(proc.stderr)
    receipt = {'argv': argv, 'started_utc': started, 'returncode': proc.returncode,
               'stdout_sha256': digest(proc.stdout), 'stderr_sha256': digest(proc.stderr)}
    write_json(folder / 'probe.json', receipt)
    if proc.returncode != 0:
        raise ValueError('INTERPRETER_PROBE_FAILED')
    return strict_json(proc.stdout), receipt


def validate_probe(info: dict, expected: str) -> None:
    if info.get('version') != expected:
        raise ValueError('INTERPRETER_VERSION_MISMATCH')
    if info.get('implementation') != 'CPython' or info.get('platform') != 'Linux' or info.get('machine') != 'x86_64':
        raise ValueError('OUTSIDE_DECLARED_PLATFORM')


def stop_tree(root_pid: int) -> list[int]:
    """Best-effort cleanup of this trusted experiment's current process subtree.

    This is a timeout cleanup measure, not a confinement/security claim.
    Each PID is rechecked against /proc start ticks before signalling.
    """
    table = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            stat = (entry / 'stat').read_text()
            fields = stat[stat.rfind(')') + 2:].split()
            table[int(entry.name)] = (int(fields[1]), fields[19])
        except (OSError, ValueError, IndexError):
            continue
    selected = {root_pid}
    while True:
        enlarged = selected | {pid for pid, (parent, _) in table.items() if parent in selected}
        if enlarged == selected:
            break
        selected = enlarged
    killed = []
    for pid in sorted(selected - {root_pid}, reverse=True) + [root_pid]:
        try:
            stat = Path('/proc', str(pid), 'stat').read_text()
            ticks = stat[stat.rfind(')') + 2:].split()[19]
            if pid in table and ticks == table[pid][1]:
                os.kill(pid, signal.SIGKILL)
                killed.append(pid)
        except (OSError, ValueError, IndexError):
            continue
    return killed


def file_references(value: Any):
    if isinstance(value, dict):
        if {'path', 'sha256', 'bytes'} <= set(value):
            yield value
        for item in value.values():
            yield from file_references(item)
    elif isinstance(value, list):
        for item in value:
            yield from file_references(item)


def verify_references(value: Any, folder: Path) -> int:
    count = 0
    for record in file_references(value):
        p = Path(record['path'])
        if not p.is_absolute() or not p.resolve().is_relative_to(folder.resolve()):
            raise ValueError('OUT_OF_SCOPE_OBSERVATION')
        rel = str(p.relative_to(folder))
        p = regular_under(folder, rel)
        raw = p.read_bytes()
        if type(record['bytes']) is not int or len(raw) != record['bytes'] or digest(raw) != record['sha256']:
            raise ValueError('OBSERVATION_DIGEST_MISMATCH')
        count += 1
    return count


def validate_observation(record: dict, allow_expected_abnormal: bool = False) -> None:
    if not isinstance(record.get('stdout'), dict) or not isinstance(record.get('stderr'), dict):
        raise ValueError('MISSING_LOG_REFERENCE')
    if not allow_expected_abnormal and (record.get('execution') != 'COMPLETED'
            or record.get('normal_completion') is not True
            or type(record.get('returncode')) is not int or record['returncode'] < 0):
        raise ValueError('ABNORMAL_REQUIRED_STAGE')


def semantic_view(data: dict) -> dict:
    """Reject missing/failed evidence before constructing a comparison projection."""
    if (data.get('execution_status') != 'COMPLETED' or data.get('experiment_comparison') != 'MATCH'
            or data.get('selected_snapshot') != SOURCE_SNAPSHOT
            or data.get('authority_effect') != 'none'
            or data.get('sources_unchanged') is not True
            or data.get('harness_and_expectations_unchanged_since_freeze') is not True):
        raise ValueError('INCOMPLETE_OR_FAILED_EXECUTION')
    if set(data.get('all_scenarios', {})) != set(SCENARIOS) or set(data.get('scenario_results', {})) != set(SCENARIOS):
        raise ValueError('SCENARIO_COVERAGE_MISMATCH')
    if set(data.get('controls', {})) != set(CONTROLS):
        raise ValueError('CONTROL_COVERAGE_MISMATCH')
    for group in data['controls'].values():
        if group.get('result') != 'MATCH' or group.get('execution') != 'COMPLETED' or not isinstance(group.get('evidence'), dict):
            raise ValueError('FAILED_OR_MISSING_CONTROL')
    regression = data.get('regressions', {})
    records = regression.get('records', [])
    names = [row.get('test') for row in records]
    if (regression.get('successful') is not True or type(regression.get('tests_run')) is not int
            or regression['tests_run'] != 18 or len(records) != 18 or len(set(names)) != 18
            or regression.get('errors') != 0 or regression.get('failures') != 0
            or any(row.get('result') != 'MATCH' for row in records)
            or not isinstance(regression.get('log'), dict)):
        raise ValueError('REGRESSION_COVERAGE_MISMATCH')
    view = {}
    for sid in SCENARIOS:
        value = data['all_scenarios'][sid]
        if (value.get('scenario_id') != sid or value.get('expected_vs_observed') != 'MATCH'
                or data['scenario_results'][sid] != 'MATCH'
                or value.get('coverage_status') != 'COMPLETE_FOR_DECLARED_CASE'
                or value.get('authority_effect') != 'none'
                or value.get('mutation_manifest', {}).get('verified') is not True
                or not value.get('comparison_details')
                or any(x != 'MATCH' for x in value['comparison_details'].values())):
            raise ValueError('FAILED_SCENARIO: ' + sid)
        programs = value.get('program_observations', {})
        if set(programs) != set(STAGES):
            raise ValueError('MISSING_PROGRAM_STAGE: ' + sid)
        for observation in programs.values():
            validate_observation(observation)
        validate_observation(value.get('reference_observation', {}))
        if value['reference_observation']['returncode'] != 0 or not isinstance(value.get('reference_result_file'), dict):
            raise ValueError('FAILED_REFERENCE_STAGE: ' + sid)
        # The unchanged reference only emits source_differences after source
        # reconstruction. Absence is meaningful, and must not become [].
        if 'source_differences' not in value:
            if (value.get('reference_source_assessment') != 'UNRESOLVED'
                    or not value.get('missing_source_premises')
                    or value.get('proof_applicability_assessment') != 'NOT_JUSTIFIED'
                    or value.get('certificate') is not None):
                raise ValueError('UNEXPLAINED_MISSING_SOURCE_DIFFERENCES')
        view[sid] = {key: copy.deepcopy(value[key]) for key in VIEW_KEYS if key != 'source_differences'}
        view[sid]['source_differences'] = {
            'present': 'source_differences' in value,
            'value': copy.deepcopy(value.get('source_differences')),
        }
        view[sid]['program_returncodes'] = {key: programs[key]['returncode'] for key in STAGES}
        view[sid]['control_results'] = {key: data['controls'][key]['result'] for key in CONTROLS}
        view[sid]['regression_names'] = sorted(names)
    return view


def finalize(rows: list[dict], required: tuple[str, ...] = VERSIONS) -> dict:
    versions = [row.get('requested_version') for row in rows]
    structure_ok = len(versions) == len(required) and len(set(versions)) == len(required) and set(versions) == set(required)
    good = structure_ok and all(
        row.get('status') == 'MATCH'
        and isinstance(row.get('observed'), dict)
        and row['observed'].get('version') == row['requested_version']
        and row['observed'].get('implementation') == 'CPython'
        and row['observed'].get('platform') == 'Linux'
        and row['observed'].get('machine') == 'x86_64'
        and isinstance(row.get('semantic_view_sha256'), str)
        and re.fullmatch(r'[0-9a-f]{64}', row['semantic_view_sha256']) is not None
        and row.get('sources_unchanged') is True
        and row.get('frozen_core_unchanged') is True
        and row.get('completed_scenarios') == 8
        and row.get('controls') == 6
        and row.get('regression_test_methods') == 18
        and row.get('program_invocations') == 48
        for row in rows)
    completed = [row for row in rows if row.get('status') == 'MATCH' and isinstance(row.get('observed'), dict) and isinstance(row['observed'].get('version'), str)]
    minor_versions = sorted({'.'.join(row['observed']['version'].split('.')[:2]) for row in completed})
    comparable = good and len(minor_versions) == len(required) and len(required) >= 2
    # Hashes summarize retained, locally verified views, not producer assertions.
    equal = comparable and len({row.get('semantic_view_sha256') for row in rows}) == 1
    if not comparable:
        status = 'INCOMPLETE'
    else:
        status = 'MATCH' if equal else 'MISMATCH'
    return {'profile_id': 'PD-SM-01-E2-compat-v0', 'status': status,
            'required_versions': list(required), 'distinct_completed_minor_versions': minor_versions,
            'all_required_runtime_results_present': good, 'cross_version_comparison_performed': comparable,
            'all_required_semantic_views_equal': equal if comparable else None,
            'cross_version_compatibility_established_for_declared_profile': status == 'MATCH',
            'results': rows, 'authority_effect': 'none',
            'scope': 'E0 cases and controls on the exact named Linux x86_64 CPython interpreters only; not E1/MON-1, Windows, physical causality or all future Python releases.'}


def run_one(package: Path, source: Path, output: Path, version: str, executable: str,
            contract: dict, manifest: dict) -> dict:
    folder = output / ('py' + version)
    folder.mkdir()
    row = {'requested_version': version, 'status': 'NOT_RUN', 'observed': None,
           'authority_effect': 'none', 'result_directory': folder.name}
    try:
        if not executable:
            row['reason'] = 'INTERPRETER_UNAVAILABLE'
            return row
        python = Path(executable).resolve(strict=True)
        if not python.is_file() or not os.access(python, os.X_OK):
            raise ValueError('INTERPRETER_UNAVAILABLE')
        info, _ = version_probe(python, folder)
        row.update(observed=info, interpreter_sha256=file_hash(python))
        validate_probe(info, version)
        bundle = folder / 'bundle'
        shutil.copytree(package / 'core', bundle / 'pd_sm_01_e0')
        (bundle / 'preparation').mkdir()
        shutil.copyfile(package / 'SOURCE_BINDINGS.json', bundle / 'preparation/SOURCE_BINDINGS.json')
        shutil.copyfile(package / 'core/case_expectations.json', bundle / 'preparation/case_expectations.json')
        for source_row in manifest['files']:
            target = bundle / 'source' / source_row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(regular_under(source, source_row['path']), target)
            target.chmod(0o444)
        sources_before = verify_sources(bundle / 'source', manifest)
        revision = strict_json((package / 'ENVIRONMENT_PROFILE_REVISION.json').read_bytes())
        revision['profile_id'] = 'PD-SM-01-E2-compat-' + version
        revision['change']['selected_value'] = version
        revision['authorization_basis'] = 'Explicit interpreter-matrix execution; scratch-copy gate revision only. No production authority or repository write.'
        write_json(bundle / 'ENVIRONMENT_PROFILE_REVISION.json', revision)
        runner = bundle / 'pd_sm_01_e0/run_cases.py'
        old = runner.read_text(encoding='utf-8')
        new = adapt_runner(old, version)
        runner.write_text(new, encoding='utf-8')
        (folder / 'environment_gate.diff').write_text(''.join(difflib.unified_diff(
            old.splitlines(True), new.splitlines(True), fromfile='historical/run_cases.py',
            tofile='scratch/run_cases.py')), encoding='utf-8')
        core = {name: file_hash(bundle / 'pd_sm_01_e0' / name) for name in contract['core_sha256']}
        for name, sha256 in core.items():
            if name != 'run_cases.py' and sha256 != contract['core_sha256'][name]:
                raise ValueError('CHANGED_REFERENCE_OR_EXPECTATION')
        freeze = {'observed_interpreter': info, 'interpreter_sha256': row['interpreter_sha256'],
                  'sources': sources_before, 'core_sha256': core,
                  'original_core_sha256': contract['core_sha256'], 'authority_effect': 'none'}
        write_json(folder / 'PREFLIGHT.json', freeze)
        argv = [str(python), '-I', '-S', '-B', str(runner), '--bundle-root', str(bundle),
                '--output', str(folder / 'execution')]
        started = datetime.now(timezone.utc).isoformat()
        timeout = contract['runtime_timeout_seconds']
        killed = []
        with (folder / 'run.stdout').open('xb') as out, (folder / 'run.stderr').open('xb') as err:
            child = subprocess.Popen(argv, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                     cwd=folder, env=CLEAN_ENV, close_fds=True, start_new_session=True)
            try:
                returncode = child.wait(timeout=timeout)
                execution = 'COMPLETED' if returncode >= 0 else 'PROCESS_ERROR'
            except subprocess.TimeoutExpired:
                killed = stop_tree(child.pid)
                child.wait(timeout=10)
                returncode, execution = None, 'TIMEOUT'
        receipt = {'argv': argv, 'cwd': str(folder), 'environment': CLEAN_ENV,
                   'started_utc': started, 'ended_utc': datetime.now(timezone.utc).isoformat(),
                   'returncode': returncode, 'execution': execution, 'timeout_seconds': timeout,
                   'timeout_cleanup_pids': killed,
                   'stdout_sha256': file_hash(folder / 'run.stdout'),
                   'stderr_sha256': file_hash(folder / 'run.stderr')}
        write_json(folder / 'RUN.json', receipt)
        row.update(returncode=returncode, execution=execution)
        if execution != 'COMPLETED' or returncode != 0:
            row.update(status='INCOMPLETE', reason='EXPERIMENT_DID_NOT_COMPLETE_SUCCESSFULLY')
            return row
        data = strict_json((folder / 'execution/RESULTS.json').read_bytes())
        view = semantic_view(data)
        checked = verify_references(data, folder)
        # Include evidence referenced by control records, not only their top-level logs.
        for control in data['controls'].values():
            checked += verify_references(strict_json(Path(control['evidence']['path']).read_bytes()), folder)
        logs = sorted((folder / 'execution/logs').rglob('*.json'))
        if len(logs) != data.get('program_invocations') or len(logs) != 48:
            raise ValueError('INVOCATION_COVERAGE_MISMATCH')
        for log in logs:
            checked += verify_references(strict_json(log.read_bytes()), folder)
        environment = strict_json((folder / 'execution/environment.json').read_bytes())
        if (environment['executable_sha256'] != row['interpreter_sha256']
                or environment['profile_revision']['change']['selected_value'] != version
                or environment['isolation']['socket_probe'] != 'EPERM'):
            raise ValueError('EXECUTION_ENVIRONMENT_MISMATCH')
        if sources_before != verify_sources(bundle / 'source', manifest):
            raise ValueError('SOURCE_CHANGED_DURING_RUN')
        if core != {name: file_hash(bundle / 'pd_sm_01_e0' / name) for name in core}:
            raise ValueError('HARNESS_CHANGED_DURING_RUN')
        if row['interpreter_sha256'] != file_hash(python):
            raise ValueError('INTERPRETER_CHANGED_DURING_RUN')
        write_json(folder / 'SEMANTIC_VIEW.json', view)
        row.update(status='MATCH', semantic_view_sha256=file_hash(folder / 'SEMANTIC_VIEW.json'),
                   completed_scenarios=len(data['all_scenarios']), controls=len(data['controls']),
                   regression_test_methods=data['regressions']['tests_run'],
                   program_invocations=len(logs), verified_file_references=checked,
                   sources_unchanged=True, frozen_core_unchanged=True,
                   record_sha256=file_hash(folder / 'execution/RESULTS.json'),
                   core_sha256=core,
                   carrier_digests={sid: data['all_scenarios'][sid]['carrier_digests'] for sid in SCENARIOS})
        return row
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        row.update(status='INCOMPLETE', reason=type(error).__name__ + ': ' + str(error))
        return row
    finally:
        write_json(folder / 'ROW.json', row)


def parse_interpreters(items: list[str]) -> dict[str, str]:
    result = {}
    for item in items:
        version, separator, path = item.partition('=')
        if not separator or version not in VERSIONS or version in result or not path or not Path(path).is_absolute():
            raise ValueError('expected unique declared VERSION=/absolute/interpreter')
        result[version] = path
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--interpreter', action='append', default=[], help='VERSION=/absolute/path; repeat')
    args = parser.parse_args()
    source, output = args.source_root.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(HERE) or output.is_relative_to(source):
        parser.error('output must be a new directory outside code and source inputs')
    interpreters = parse_interpreters(args.interpreter)
    output.mkdir(parents=True)
    code_identity = {p.name: file_hash(p) for p in (HERE / 'matrix.py', HERE / 'matrix_contract.json')}
    metadata = {key: os.environ[key] for key in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT',
                'GITHUB_WORKFLOW_SHA', 'GITHUB_REF', 'GITHUB_REPOSITORY', 'ImageOS', 'ImageVersion') if key in os.environ}
    write_json(output / 'INVOCATION.json', {'interpreter_arguments': interpreters,
               'controller_version': sys.version, 'controller_executable_sha256': file_hash(Path(sys.executable).resolve()),
               'code_identity': code_identity, 'hosted_metadata': metadata, 'authority_effect': 'none'})
    try:
        contract = verify_package(HERE)
        manifest = strict_json((HERE / 'SOURCE_BINDINGS.json').read_bytes())
        records = verify_sources(source, manifest)
        write_json(output / 'SOURCE_CHECK.json', {'snapshot': SOURCE_SNAPSHOT, 'files': records})
        rows = []
        for version in VERSIONS:
            print('START', version, flush=True)
            row = run_one(HERE, source, output, version, interpreters.get(version, ''), contract, manifest)
            rows.append(row)
            print('END', version, row['status'], row.get('reason', ''), flush=True)
        report = finalize(rows)
        verify_package(HERE)
        if code_identity != {p.name: file_hash(p) for p in (HERE / 'matrix.py', HERE / 'matrix_contract.json')} or records != verify_sources(source, manifest):
            report.update(status='INCOMPLETE', failure='INPUT_CHANGED_DURING_MATRIX',
                          cross_version_compatibility_established_for_declared_profile=False)
        write_json(output / 'MATRIX.json', report)
        print('MATRIX', report['status'], flush=True)
        return 0 if report['status'] == 'MATCH' else 1
    except (OSError, ValueError, TypeError, KeyError) as error:
        write_json(output / 'MATRIX.json', {'status': 'INCOMPLETE', 'failure': type(error).__name__ + ': ' + str(error),
                   'cross_version_compatibility_established_for_declared_profile': False, 'authority_effect': 'none'})
        return 2
    finally:
        lines = []
        for path in sorted(output.rglob('*')):
            if path.is_symlink():
                continue
            if path.is_file():
                lines.append(file_hash(path) + '  ' + str(path.relative_to(output)))
        (output / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
