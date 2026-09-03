#!/usr/bin/env python3
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
CAPTURE_TOOL_PATH = (
    ROOT / "tools" / "capture_pulsemech_compute_post_run_producer_input_v0.py"
)
SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "pulsemech_compute_post_run_producer_input_capture_manifest_v0.schema.json"
)
CONTRACT_PATH = (
    ROOT
    / "contracts"
    / "pulsemech_compute_post_run_producer_input_capture_v0.json"
)
EXAMPLE_PATH = (
    ROOT
    / "examples"
    / "compute"
    / "pulsemech_compute_post_run_producer_input_capture_manifest_example_v0.json"
)
OFFLINE_VALIDATOR_PATH = (
    ROOT
    / "tools"
    / "check_pulsemech_compute_post_run_producer_input_capture_v0.py"
)

TOKEN = "ghp_" + ("A" * 36)
OTHER_TOKEN = "ghp_" + ("B" * 36)
CAPTURE_BASE = dt.datetime(2026, 8, 1, 18, 0, 0, tzinfo=dt.timezone.utc)

EXPECTED_CAPTURE_TOOL_IDENTITY = (
    105091,
    "6fd39f52f54675db0f57dc090da1fc21b12a858fde6619621043b552a7c0d2bc",
    "621b839a11471d65c7170531f600f80117b7c083",
)

SOURCE_PATHS = (
    SCHEMA_PATH,
    CONTRACT_PATH,
    CAPTURE_TOOL_PATH,
    EXAMPLE_PATH,
    OFFLINE_VALIDATOR_PATH,
)

_DELETE = object()

EXPECTED_TEST_ITEM_COUNTS = {
    "test_application_request_headers_are_exact_and_ordered": 1,
    "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract": 1,
    "test_capture_tool_exact_identity_and_linux_runtime_contract": 1,
    "test_cli_requires_isolated_python_and_never_echoes_invalid_arguments": 1,
    "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit": 1,
    "test_existing_output_is_never_replaced": 1,
    "test_explicit_source_revision_must_equal_repository_head": 1,
    "test_fixture_capture_one_page_preserves_exact_bytes_and_boundaries": 1,
    "test_full_capture_relation_failures_publish_nothing": 6,
    "test_job_and_step_binding_mutations_fail_closed": 26,
    "test_job_and_step_limits_fail_closed": 1,
    "test_numeric_response_tokens_fail_before_publication": 6,
    "test_output_inside_repository_is_rejected_and_sources_remain_exact": 1,
    "test_post_publication_readback_failure_removes_owned_output": 1,
    "test_publication_cleanup_covers_keyboard_interrupt": 1,
    "test_publication_rejects_existing_target_and_out_of_contract_member": 1,
    "test_rel_next_exact_target_and_final_absence_states": 1,
    "test_rel_next_mutations_fail_closed": 12,
    "test_request_record_rejects_floating_or_noncanonical_targets": 1,
    "test_response_admission_failures_are_deterministic": 19,
    "test_response_size_and_clock_order_limits_fail_closed": 1,
    "test_run_attempt_capture_must_occur_after_subject_completion": 1,
    "test_run_attempt_identity_mutations_fail_closed": 20,
    "test_same_fixture_produces_byte_identical_capture": 1,
    "test_skipped_jobs_and_steps_preserve_explicit_unavailability": 1,
    "test_source_drift_before_publication_fails_closed": 1,
    "test_stdlib_https_transport_network_and_size_failures_are_closed": 1,
    "test_stdlib_https_transport_sends_exact_request_without_redirect_handler": 1,
    "test_success_and_failure_diagnostics_are_canonical_and_deterministic": 1,
    "test_token_boundary_fails_closed": 6,
    "test_total_capture_and_total_step_limits_fail_closed_after_source_admission": 1,
    "test_two_page_rel_next_capture_is_exact_and_closed": 1,
    "test_valid_run_attempt_reconstructs_exact_subject": 1,
}
EXPECTED_COLLECTED_TEST_ITEMS = sum(EXPECTED_TEST_ITEM_COUNTS.values())
CRITICAL_TEST_FUNCTIONS = frozenset(
    {
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_capture_tool_exact_identity_and_linux_runtime_contract",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_fixture_capture_one_page_preserves_exact_bytes_and_boundaries",
        "test_numeric_response_tokens_fail_before_publication",
        "test_same_fixture_produces_byte_identical_capture",
        "test_source_drift_before_publication_fails_closed",
        "test_two_page_rel_next_capture_is_exact_and_closed",
    }
)
_AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS = (
    "PYTEST_ADDOPTS",
    "PYTEST_CURRENT_TEST",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
)
_AUTHORITATIVE_LAUNCH_PROBE_CHILD = (
    "PULSEMECH_POST_RUN_CAPTURE_TOOL_LAUNCH_PROBE_CHILD"
)


def _collected_test_name(item: Any) -> str:
    original_name = getattr(item, "originalname", None)
    if isinstance(original_name, str) and original_name:
        return original_name
    return str(item.name).split("[", 1)[0]


class _AuthoritativeRegressionContract:
    def __init__(self) -> None:
        self._expected_nodeids: set[str] = set()
        self._phase_outcomes: dict[str, dict[str, str]] = {}
        self._disallowed_reports: list[dict[str, str]] = []
        self._collection_validated = False
        self._session_finished = False
        self._contract_satisfied = False

    @property
    def completed_successfully(self) -> bool:
        return self._contract_satisfied

    @property
    def completion_state(self) -> dict[str, bool]:
        return {
            "collection_validated": self._collection_validated,
            "contract_satisfied": self._contract_satisfied,
            "session_finished": self._session_finished,
        }

    def pytest_collection_finish(self, session: Any) -> None:
        current_file = Path(__file__).resolve()
        collected = [
            item
            for item in session.items
            if Path(str(item.path)).resolve() == current_file
        ]
        observed_nodeids = [str(item.nodeid) for item in collected]
        observed_counts = Counter(_collected_test_name(item) for item in collected)
        expected_counts = Counter(EXPECTED_TEST_ITEM_COUNTS)
        duplicate_nodeids = sorted(
            nodeid
            for nodeid, count in Counter(observed_nodeids).items()
            if count != 1
        )
        missing_functions = sorted(set(expected_counts) - set(observed_counts))
        unexpected_functions = sorted(set(observed_counts) - set(expected_counts))
        count_mismatches = {
            name: {
                "expected": expected_counts.get(name, 0),
                "observed": observed_counts.get(name, 0),
            }
            for name in sorted(set(expected_counts) | set(observed_counts))
            if expected_counts.get(name, 0) != observed_counts.get(name, 0)
        }
        missing_critical = sorted(
            CRITICAL_TEST_FUNCTIONS - set(observed_counts)
        )
        if (
            len(collected) != EXPECTED_COLLECTED_TEST_ITEMS
            or duplicate_nodeids
            or missing_functions
            or unexpected_functions
            or count_mismatches
            or missing_critical
        ):
            raise pytest.UsageError(
                "authoritative_capture_tool_collection_mismatch: "
                + json.dumps(
                    {
                        "count_mismatches": count_mismatches,
                        "duplicate_nodeids": duplicate_nodeids,
                        "expected_items": EXPECTED_COLLECTED_TEST_ITEMS,
                        "missing_critical_functions": missing_critical,
                        "missing_functions": missing_functions,
                        "observed_items": len(collected),
                        "unexpected_functions": unexpected_functions,
                    },
                    sort_keys=True,
                )
            )
        self._expected_nodeids = set(observed_nodeids)
        self._collection_validated = True

    def pytest_runtest_logreport(self, report: Any) -> None:
        nodeid = str(report.nodeid)
        if nodeid not in self._expected_nodeids:
            return
        when = str(report.when)
        if when not in {"setup", "call", "teardown"}:
            return
        phases = self._phase_outcomes.setdefault(nodeid, {})
        if when in phases:
            self._disallowed_reports.append(
                {
                    "nodeid": nodeid,
                    "reason": "duplicate_phase_report",
                    "when": when,
                }
            )
        phases[when] = str(report.outcome)
        if report.skipped or getattr(report, "wasxfail", None) is not None:
            self._disallowed_reports.append(
                {
                    "nodeid": nodeid,
                    "reason": "skip_xfail_or_xpass_forbidden",
                    "when": when,
                }
            )

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        self._session_finished = True
        expected_phases = {"setup", "call", "teardown"}
        missing_phases: dict[str, list[str]] = {}
        nonpassing_phases: dict[str, dict[str, str]] = {}
        for nodeid in sorted(self._expected_nodeids):
            phases = self._phase_outcomes.get(nodeid, {})
            missing = sorted(expected_phases - set(phases))
            if missing:
                missing_phases[nodeid] = missing
            failed = {
                phase: outcome
                for phase, outcome in sorted(phases.items())
                if outcome != "passed"
            }
            if failed:
                nonpassing_phases[nodeid] = failed

        if (
            self._collection_validated
            and len(self._expected_nodeids) == EXPECTED_COLLECTED_TEST_ITEMS
            and not missing_phases
            and not nonpassing_phases
            and not self._disallowed_reports
            and int(exitstatus) == int(pytest.ExitCode.OK)
        ):
            self._contract_satisfied = True
            return

        terminal = session.config.pluginmanager.get_plugin("terminalreporter")
        detail = json.dumps(
            {
                "collection_validated": self._collection_validated,
                "disallowed_reports": self._disallowed_reports,
                "expected_items": EXPECTED_COLLECTED_TEST_ITEMS,
                "missing_phases": missing_phases,
                "nonpassing_phases": nonpassing_phases,
                "observed_nodeids": len(self._expected_nodeids),
            },
            sort_keys=True,
        )
        if terminal is not None:
            terminal.write_sep(
                "=",
                "authoritative capture-tool execution failed",
            )
            terminal.write_line(detail)
        if int(exitstatus) == int(pytest.ExitCode.OK):
            session.exitstatus = int(pytest.ExitCode.TESTS_FAILED)


def _run_authoritative_regression(
    *,
    pytest_main: Any | None = None,
) -> int:
    previous_environment = {
        key: os.environ.get(key)
        for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
    }
    os.environ.pop("PYTEST_ADDOPTS", None)
    os.environ.pop("PYTEST_CURRENT_TEST", None)
    os.environ.pop("PYTEST_PLUGINS", None)
    os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    contract = _AuthoritativeRegressionContract()
    runner = pytest.main if pytest_main is None else pytest_main
    arguments = [
        "-c",
        os.devnull,
        "--rootdir",
        str(ROOT),
        "-o",
        "addopts=",
        "--noconftest",
        str(Path(__file__).resolve()),
    ]
    try:
        result = runner(arguments, plugins=[contract])
    finally:
        for key, value in previous_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    exit_code = int(result)
    if exit_code != int(pytest.ExitCode.OK):
        return exit_code
    if contract.completed_successfully:
        return exit_code
    sys.stderr.write(
        "authoritative_capture_tool_session_not_completed: "
        + json.dumps(contract.completion_state, sort_keys=True)
        + "\n"
    )
    return int(pytest.ExitCode.TESTS_FAILED)


@dataclass(frozen=True)
class TransportCall:
    request_target: str
    headers: tuple[tuple[str, str], ...]
    timeout_seconds: int
    maximum_body_bytes: int


class SequenceClock:
    def __init__(self, values: Sequence[dt.datetime]) -> None:
        self._values = list(values)
        self._index = 0

    def now(self) -> dt.datetime:
        if self._index >= len(self._values):
            raise AssertionError("fixture clock exhausted")
        value = self._values[self._index]
        self._index += 1
        return value

    @property
    def consumed(self) -> int:
        return self._index

    @property
    def remaining(self) -> int:
        return len(self._values) - self._index


class ScriptedTransport:
    def __init__(
        self,
        script: Sequence[tuple[str, Any]],
        *,
        on_call: Callable[[int, str], None] | None = None,
    ) -> None:
        self._script = list(script)
        self._index = 0
        self._on_call = on_call
        self.calls: list[TransportCall] = []

    def get(
        self,
        *,
        request_target: str,
        headers: Sequence[tuple[str, str]],
        timeout_seconds: int,
        maximum_body_bytes: int,
    ) -> Any:
        if self._index >= len(self._script):
            raise AssertionError(f"unexpected request: {request_target}")
        expected_target, response = self._script[self._index]
        if request_target != expected_target:
            raise AssertionError(
                f"request target mismatch: expected={expected_target!r} "
                f"observed={request_target!r}"
            )
        self._index += 1
        self.calls.append(
            TransportCall(
                request_target=request_target,
                headers=tuple(headers),
                timeout_seconds=timeout_seconds,
                maximum_body_bytes=maximum_body_bytes,
            )
        )
        if self._on_call is not None:
            self._on_call(self._index, request_target)
        if isinstance(response, BaseException):
            raise response
        return response

    @property
    def remaining(self) -> int:
        return len(self._script) - self._index


def _load_capture_module(path: Path, *, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load capture module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def capture() -> Any:
    return _load_capture_module(
        CAPTURE_TOOL_PATH,
        name="pulsemech_compute_post_run_capture_tool_under_test",
    )


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _git_blob_sha1(payload: bytes) -> str:
    framed = f"blob {len(payload)}\0".encode("ascii") + payload
    try:
        return hashlib.sha1(framed, usedforsecurity=False).hexdigest()
    except TypeError:
        return hashlib.sha1(framed).hexdigest()


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _json_body(value: Mapping[str, Any], *, indent: int = 2) -> bytes:
    return (
        json.dumps(
            dict(value),
            ensure_ascii=False,
            indent=indent,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    value = completed.stdout.strip()
    assert len(value) == 40
    return value


def _source_snapshot(paths: Sequence[Path] = SOURCE_PATHS) -> dict[str, bytes]:
    return {
        path.relative_to(ROOT).as_posix(): path.read_bytes()
        for path in paths
    }


def _snapshot_tree(root: Path) -> dict[str, tuple[str, int, bytes | None]]:
    snapshot: dict[str, tuple[str, int, bytes | None]] = {}
    for candidate in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = candidate.relative_to(root).as_posix()
        metadata = candidate.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            raise AssertionError(f"symlink present in output: {relative}")
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISDIR(metadata.st_mode):
            snapshot[relative] = ("directory", mode, None)
        elif stat.S_ISREG(metadata.st_mode):
            snapshot[relative] = ("file", mode, candidate.read_bytes())
        else:
            raise AssertionError(f"non-regular output member: {relative}")
    return snapshot


def _assert_no_owned_staging(parent: Path, target_name: str) -> None:
    prefixes = (f".{target_name}.tmp-",)
    leftovers = [
        candidate.name
        for candidate in parent.iterdir()
        if candidate.name.startswith(prefixes)
    ]
    assert leftovers == []


def _set_path(value: dict[str, Any], path: Sequence[Any], replacement: Any) -> None:
    cursor: Any = value
    for part in path[:-1]:
        cursor = cursor[part]
    leaf = path[-1]
    if replacement is _DELETE:
        del cursor[leaf]
    else:
        cursor[leaf] = replacement


def _run_document(capture: Any) -> dict[str, Any]:
    return {
        "id": capture.SUBJECT_RUN_ID,
        "run_number": capture.SUBJECT_RUN_NUMBER,
        "run_attempt": capture.SUBJECT_RUN_ATTEMPT,
        "name": capture.SUBJECT_WORKFLOW_NAME,
        "workflow_id": capture.SUBJECT_WORKFLOW_ID,
        "path": capture.SUBJECT_WORKFLOW_PATH,
        "event": capture.SUBJECT_EVENT,
        "head_branch": capture.SUBJECT_HEAD_BRANCH,
        "head_sha": capture.SUBJECT_SOURCE_COMMIT,
        "status": "completed",
        "conclusion": "success",
        "created_at": capture.SUBJECT_RUN_CREATED_UTC,
        "run_started_at": capture.SUBJECT_RUN_STARTED_UTC,
        "updated_at": capture.SUBJECT_RUN_UPDATED_UTC,
        "repository": {
            "full_name": capture.REPOSITORY,
            "id": capture.REPOSITORY_ID,
            "fork": False,
        },
        "head_repository": {
            "full_name": capture.REPOSITORY,
            "id": capture.REPOSITORY_ID,
            "fork": False,
        },
        "ignored_transport_snapshot_field": "preserved-but-not-promoted",
    }


def _step_document(
    number: int,
    *,
    conclusion: str = "success",
    started_at: str | None = "2026-07-13T12:27:00Z",
    completed_at: str | None = "2026-07-13T12:27:01Z",
) -> dict[str, Any]:
    return {
        "number": number,
        "name": f"fixture-step-{number}",
        "status": "completed",
        "conclusion": conclusion,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def _job_document(
    capture: Any,
    job_id: int,
    *,
    steps: Sequence[dict[str, Any]] | None = None,
    conclusion: str = "success",
    started_at: str | None = "2026-07-13T12:27:00Z",
    completed_at: str | None = "2026-07-13T12:27:01Z",
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "id": job_id,
        "run_id": capture.SUBJECT_RUN_ID,
        "run_attempt": capture.SUBJECT_RUN_ATTEMPT,
        "workflow_name": capture.SUBJECT_WORKFLOW_NAME,
        "head_sha": capture.SUBJECT_SOURCE_COMMIT,
        "name": f"fixture-job-{job_id}",
        "status": "completed",
        "conclusion": conclusion,
        "started_at": started_at,
        "completed_at": completed_at,
        "runner_name": "fixture-runner",
    }
    if steps is not None:
        value["steps"] = list(steps)
    return value


def _jobs_document(
    capture: Any,
    job_ids: Sequence[int],
    *,
    total_count: int | None = None,
    steps_per_job: int = 1,
) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    for job_id in job_ids:
        steps = [_step_document(index + 1) for index in range(steps_per_job)]
        jobs.append(_job_document(capture, job_id, steps=steps))
    return {
        "total_count": len(job_ids) if total_count is None else total_count,
        "jobs": jobs,
    }


def _headers_for_body(
    body: bytes,
    *,
    link: str | None = None,
    content_type: str | None = "application/json; charset=utf-8",
    content_encoding: str | None = None,
    etag: str | None = '"fixture-etag"',
    request_id: str | None = "fixture-request-id",
    extra: Sequence[tuple[str, str]] = (),
    include_content_length: bool = True,
) -> tuple[tuple[str, str], ...]:
    headers: list[tuple[str, str]] = []
    if content_type is not None:
        headers.append(("Content-Type", content_type))
    if content_encoding is not None:
        headers.append(("Content-Encoding", content_encoding))
    if etag is not None:
        headers.append(("ETag", etag))
    if link is not None:
        headers.append(("Link", link))
    if request_id is not None:
        headers.append(("X-GitHub-Request-Id", request_id))
    if include_content_length:
        headers.append(("Content-Length", str(len(body))))
    headers.extend(extra)
    return tuple(headers)


def _transport_response(
    capture: Any,
    body: bytes,
    *,
    headers: Sequence[tuple[str, str]] | None = None,
    status: int = 200,
    clean_eof: bool = True,
    redirect_observed: bool = False,
) -> Any:
    return capture.TransportResponse(
        status=status,
        headers=(
            tuple(headers)
            if headers is not None
            else _headers_for_body(body)
        ),
        body=body,
        clean_eof=clean_eof,
        redirect_observed=redirect_observed,
    )


def _clock_for_requests(count: int) -> SequenceClock:
    return SequenceClock(
        [CAPTURE_BASE + dt.timedelta(microseconds=index) for index in range(2 * count)]
    )


def _scripted_fixture(
    capture: Any,
    *,
    run_document: Mapping[str, Any] | None = None,
    pages: Sequence[tuple[Mapping[str, Any], str | None]] | None = None,
    on_call: Callable[[int, str], None] | None = None,
) -> tuple[ScriptedTransport, SequenceClock, bytes, list[bytes]]:
    run_value = dict(run_document) if run_document is not None else _run_document(capture)
    page_values = (
        list(pages)
        if pages is not None
        else [(_jobs_document(capture, list(range(86815582001, 86815582009))), None)]
    )
    run_body = _json_body(run_value)
    script: list[tuple[str, Any]] = [
        (
            capture.RUN_REQUEST_PATH,
            _transport_response(
                capture,
                run_body,
                headers=_headers_for_body(
                    run_body,
                    etag='"run-etag"',
                    request_id="fixture-run-request",
                    extra=(
                        ("Date", "fixture-date-not-recorded"),
                        ("Server", "fixture-server-not-recorded"),
                    ),
                ),
            ),
        )
    ]
    page_bodies: list[bytes] = []
    for page_number, (page_document, link) in enumerate(page_values, start=1):
        page_body = _json_body(page_document)
        page_bodies.append(page_body)
        script.append(
            (
                f"{capture.JOBS_REQUEST_PATH}?per_page=100&page={page_number}",
                _transport_response(
                    capture,
                    page_body,
                    headers=_headers_for_body(
                        page_body,
                        link=link,
                        etag=f'"jobs-page-{page_number}-etag"',
                        request_id=f"fixture-jobs-page-{page_number}-request",
                        extra=(("Date", "fixture-date-not-recorded"),),
                    ),
                ),
            )
        )
    return (
        ScriptedTransport(script, on_call=on_call),
        _clock_for_requests(1 + len(page_values)),
        run_body,
        page_bodies,
    )


def _expected_application_headers(capture: Any) -> tuple[tuple[str, str], ...]:
    return (
        ("Accept", capture.ACCEPT),
        ("Accept-Encoding", capture.ACCEPT_ENCODING),
        ("Authorization", f"Bearer {TOKEN}"),
        ("User-Agent", capture.USER_AGENT),
        ("X-GitHub-Api-Version", capture.API_VERSION),
    )


def _manifest(output_directory: Path, capture: Any) -> dict[str, Any]:
    path = output_directory / capture.EXAMPLE_MANIFEST_NAME
    payload = path.read_bytes()
    value = json.loads(payload.decode("utf-8"))
    assert isinstance(value, dict)
    assert _canonical_json_bytes(value) == payload
    return value


def _captured_response(
    capture: Any,
    document: Mapping[str, Any],
    *,
    capture_started_utc: str = "2026-08-01T18:00:00.000000Z",
    response_received_utc: str = "2026-08-01T18:00:00.000001Z",
) -> Any:
    body = _json_body(document)
    selected, _ = capture._selected_response_headers(_headers_for_body(body))
    return capture.CapturedHttpResponse(
        status=200,
        selected_headers=selected,
        body=body,
        parsed_body=dict(document),
        capture_started_utc=capture_started_utc,
        response_received_utc=response_received_utc,
    )





def _with_top_level_numeric_probe(payload: bytes, token: str) -> bytes:
    token_bytes = token.encode("ascii", errors="strict")
    if not payload.endswith(b"\n}\n"):
        raise AssertionError("fixture JSON body shape changed")
    return (
        payload[:-3]
        + b',\n  "numeric_domain_probe": '
        + token_bytes
        + b"\n}\n"
    )

def _assert_capture_error(
    capture: Any,
    expected: str,
    operation: Callable[[], Any],
) -> None:
    with pytest.raises(capture.CaptureError) as caught:
        operation()
    assert caught.value.error_code == expected
    assert str(caught.value) == expected





def test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inherited = {
        "PYTEST_ADDOPTS": "--help",
        "PYTEST_CURRENT_TEST": "poisoned::test",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
        "PYTEST_PLUGINS": "module_that_must_not_be_imported",
    }
    for key, value in inherited.items():
        monkeypatch.setenv(key, value)

    observed: dict[str, Any] = {}

    def successful_main(
        arguments: list[str],
        *,
        plugins: list[Any],
    ) -> pytest.ExitCode:
        observed["arguments"] = list(arguments)
        observed["environment"] = {
            key: os.environ.get(key)
            for key in _AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS
        }
        assert len(plugins) == 1
        contract = plugins[0]
        assert isinstance(contract, _AuthoritativeRegressionContract)
        contract._collection_validated = True
        contract._session_finished = True
        contract._contract_satisfied = True
        return pytest.ExitCode.OK

    assert _run_authoritative_regression(pytest_main=successful_main) == 0
    assert observed["arguments"] == [
        "-c",
        os.devnull,
        "--rootdir",
        str(ROOT),
        "-o",
        "addopts=",
        "--noconftest",
        str(Path(__file__).resolve()),
    ]
    assert observed["environment"] == {
        "PYTEST_ADDOPTS": None,
        "PYTEST_CURRENT_TEST": None,
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTEST_PLUGINS": None,
    }
    for key, value in inherited.items():
        assert os.environ.get(key) == value

    def incomplete_main(
        _arguments: list[str],
        *,
        plugins: list[Any],
    ) -> pytest.ExitCode:
        assert len(plugins) == 1
        return pytest.ExitCode.OK

    assert _run_authoritative_regression(pytest_main=incomplete_main) == int(
        pytest.ExitCode.TESTS_FAILED
    )


def test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit() -> None:
    if os.environ.get(_AUTHORITATIVE_LAUNCH_PROBE_CHILD) == "1":
        assert "PYTEST_ADDOPTS" not in os.environ
        assert "PYTEST_PLUGINS" not in os.environ
        assert os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1"
        return

    environment = dict(os.environ)
    environment.update(
        {
            _AUTHORITATIVE_LAUNCH_PROBE_CHILD: "1",
            "PYTEST_ADDOPTS": "--help",
            "PYTEST_CURRENT_TEST": "poisoned::test",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "0",
            "PYTEST_PLUGINS": "module_that_must_not_be_imported",
        }
    )
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve())],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
        timeout=900,
    )
    assert result.returncode == 0, result.stderr.decode(
        "utf-8", errors="replace"
    )
    assert result.stderr == b""
    expected = str(EXPECTED_COLLECTED_TEST_ITEMS).encode("ascii")
    assert b"collected " + expected + b" items" in result.stdout
    assert expected + b" passed" in result.stdout
    assert b"usage: pytest" not in result.stdout.lower()


def test_capture_tool_exact_identity_and_linux_runtime_contract(capture: Any) -> None:
    payload = CAPTURE_TOOL_PATH.read_bytes()
    assert (
        len(payload),
        _sha256(payload),
        _git_blob_sha1(payload),
    ) == EXPECTED_CAPTURE_TOOL_IDENTITY
    assert capture.TOOL_VERSION == "0.1.0"
    assert capture.PRODUCER_ID == "pulsemech_compute_post_run_producer_input_capture_v0"
    assert capture.SUPPORTED_OS_NAME == "posix"
    assert capture.SUPPORTED_PLATFORM_PREFIX == "linux"
    capture._validate_runtime_platform()


def test_fixture_capture_one_page_preserves_exact_bytes_and_boundaries(
    capture: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_network_attempts: list[str] = []

    def forbidden_https_connection(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        live_network_attempts.append("http.client.HTTPSConnection")
        raise AssertionError("live network attempted during fixture capture")

    def forbidden_socket_connection(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        live_network_attempts.append("socket.create_connection")
        raise AssertionError("live network attempted during fixture capture")

    monkeypatch.setattr(capture.http.client, "HTTPSConnection", forbidden_https_connection)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket_connection)

    sources_before = _source_snapshot()
    transport, clock, run_body, page_bodies = _scripted_fixture(capture)
    output = tmp_path / "capture-one-page"

    result = capture.capture_with_injected_dependencies_for_test(
        repository_root=ROOT,
        output_directory=output,
        token=TOKEN,
        transport=transport,
        clock=clock,
    )

    assert result.record_status == "example"
    assert result.manifest_file_name == capture.EXAMPLE_MANIFEST_NAME
    assert result.page_count == 1
    assert result.job_count == 8
    assert result.step_record_count == 8
    assert result.authority_effect == "none"
    assert result.manifest_sha256 == _sha256(result.manifest_bytes)
    assert transport.remaining == 0
    assert clock.remaining == 0
    assert live_network_attempts == []

    assert [call.request_target for call in transport.calls] == [
        capture.RUN_REQUEST_PATH,
        capture.FIRST_JOBS_REQUEST_TARGET,
    ]
    for call in transport.calls:
        assert call.headers == _expected_application_headers(capture)
        assert call.timeout_seconds == 30
        assert call.maximum_body_bytes == 8 * 1024 * 1024

    expected_members = {
        "metadata/jobs_page_0001_exchange_v0.json",
        "metadata/run_attempt_exchange_v0.json",
        capture.EXAMPLE_MANIFEST_NAME,
        "raw/jobs_page_0001_response.json",
        "raw/run_attempt_response.json",
    }
    observed_members = {
        candidate.relative_to(output).as_posix()
        for candidate in output.rglob("*")
        if candidate.is_file()
    }
    assert observed_members == expected_members
    assert (output / capture.RUN_BODY_PATH).read_bytes() == run_body
    assert (output / (capture.JOBS_BODY_TEMPLATE % 1)).read_bytes() == page_bodies[0]

    tree = _snapshot_tree(output)
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert tree["raw"] == ("directory", 0o700, None)
    assert tree["metadata"] == ("directory", 0o700, None)
    for relative, (kind, mode, payload) in tree.items():
        if kind == "file":
            assert mode == 0o600, relative
            assert payload is not None

    manifest = _manifest(output, capture)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    assert list(validator.iter_errors(manifest)) == []
    assert result.manifest_bytes == (
        output / capture.EXAMPLE_MANIFEST_NAME
    ).read_bytes()

    assert manifest["record_status"] == "example"
    assert manifest["provenance"] == capture._example_provenance()
    assert manifest["temporal_boundary"]["capture_is_platform_response_snapshot"] is False
    assert manifest["temporal_boundary"]["reference_producer_input_eligible"] is False
    assert manifest["authority_boundary"]["capture_is_runtime_observation"] is False
    assert manifest["authority_boundary"]["capture_is_runtime_observation_packet"] is False
    assert manifest["authority_boundary"]["capture_is_release_decision"] is False
    assert manifest["authority_boundary"]["capture_is_release_authority"] is False
    assert manifest["authority_boundary"]["authority_effect"] == "none"
    assert manifest["counts"] == {
        "count_relations_verified": True,
        "declared_non_manifest_member_count": 4,
        "duplicate_job_id_count": 0,
        "duplicate_step_number_count": 0,
        "exchange_metadata_member_count": 2,
        "jobs_page_exchange_count": 1,
        "raw_response_member_count": 2,
        "reconstructed_step_record_count": 8,
        "reconstructed_unique_job_count": 8,
        "reported_job_count": 8,
        "run_attempt_exchange_count": 1,
    }
    assert manifest["pagination"]["page_sequence"] == [1]
    assert manifest["pagination"]["closure_status"] == "closed"
    assert manifest["pagination"]["final_next_link_absent"] is True

    head = _git_head(ROOT)
    assert manifest["contract_bindings"]["manifest_schema"]["source_revision"] == head
    assert manifest["contract_bindings"]["normative_contract"]["source_revision"] == head

    run_exchange = manifest["run_attempt_exchange"]
    jobs_exchange = manifest["jobs_page_exchanges"][0]
    for wrapper in (run_exchange, jobs_exchange):
        metadata_path = output / wrapper["metadata_member"]["path"]
        expected_metadata = _canonical_json_bytes(wrapper["record"])
        assert metadata_path.read_bytes() == expected_metadata
        member = wrapper["metadata_member"]
        assert member["size_bytes"] == len(expected_metadata)
        assert member["sha256"] == _sha256(expected_metadata)
        assert member["git_blob_sha1"] == _git_blob_sha1(expected_metadata)
        metadata_text = expected_metadata.decode("utf-8")
        assert TOKEN not in metadata_text
        assert OTHER_TOKEN not in metadata_text
        assert f"Bearer {TOKEN}" not in metadata_text
        request_record = wrapper["record"]["request"]
        assert request_record["authorization_header_present"] is True
        assert request_record["authorization_value_recorded"] is False

    for wrapper, raw_body in (
        (run_exchange, run_body),
        (jobs_exchange, page_bodies[0]),
    ):
        body_member = wrapper["record"]["response"]["body_member"]
        assert body_member["size_bytes"] == len(raw_body)
        assert body_member["sha256"] == _sha256(raw_body)
        assert body_member["git_blob_sha1"] == _git_blob_sha1(raw_body)
        assert body_member["exact_bytes_preserved"] is True
        assert body_member["json_normalized"] is False
        assert body_member["json_reformatted"] is False
        assert body_member["newline_rewritten"] is False
        assert body_member["whitespace_rewritten"] is False

    selected = run_exchange["record"]["response"]["selected_headers"]
    assert selected["content_type"] == {
        "status": "present",
        "value": "application/json; charset=utf-8",
    }
    assert selected["content_encoding"] == {"status": "absent", "value": None}
    assert selected["etag"] == {"status": "present", "value": '"run-etag"'}
    assert selected["link"] == {"status": "absent", "value": None}
    assert selected["x_github_request_id"] == {
        "status": "present",
        "value": "fixture-run-request",
    }

    all_output = b"".join(
        payload
        for kind, _mode, payload in tree.values()
        if kind == "file" and payload is not None
    )
    assert TOKEN.encode("ascii") not in all_output
    assert ("Bearer " + TOKEN).encode("ascii") not in all_output
    assert b"fixture-date-not-recorded" not in all_output
    assert b"fixture-server-not-recorded" not in all_output
    assert _source_snapshot() == sources_before


def test_same_fixture_produces_byte_identical_capture(
    capture: Any,
    tmp_path: Path,
) -> None:
    output_a = tmp_path / "capture-a"
    output_b = tmp_path / "capture-b"
    transport_a, clock_a, _run_a, _pages_a = _scripted_fixture(capture)
    transport_b, clock_b, _run_b, _pages_b = _scripted_fixture(capture)

    result_a = capture.capture_with_injected_dependencies_for_test(
        repository_root=ROOT,
        output_directory=output_a,
        token=TOKEN,
        transport=transport_a,
        clock=clock_a,
    )
    result_b = capture.capture_with_injected_dependencies_for_test(
        repository_root=ROOT,
        output_directory=output_b,
        token=TOKEN,
        transport=transport_b,
        clock=clock_b,
    )

    snapshot_a = _snapshot_tree(output_a)
    snapshot_b = _snapshot_tree(output_b)
    assert snapshot_a == snapshot_b
    assert result_a == result_b
    assert result_a.manifest_bytes == result_b.manifest_bytes
    assert result_a.manifest_sha256 == result_b.manifest_sha256
    all_bytes = b"".join(
        payload
        for kind, _mode, payload in snapshot_a.values()
        if kind == "file" and payload is not None
    )
    assert b".tmp-" not in all_bytes
    assert output_a.name.encode("ascii") not in all_bytes
    assert output_b.name.encode("ascii") not in all_bytes


def test_two_page_rel_next_capture_is_exact_and_closed(
    capture: Any,
    tmp_path: Path,
) -> None:
    first_ids = list(range(90000000001, 90000000101))
    second_ids = [90000000101]
    next_url = (
        "https://api.github.com"
        + capture.JOBS_REQUEST_PATH
        + "?per_page=100&page=2"
    )
    pages = [
        (
            _jobs_document(capture, first_ids, total_count=101),
            f'<{next_url}>; rel="next", <{next_url}>; rel="last"',
        ),
        (_jobs_document(capture, second_ids, total_count=101), None),
    ]
    transport, clock, run_body, page_bodies = _scripted_fixture(
        capture,
        pages=pages,
    )
    output = tmp_path / "capture-two-page"

    result = capture.capture_with_injected_dependencies_for_test(
        repository_root=ROOT,
        output_directory=output,
        token=TOKEN,
        transport=transport,
        clock=clock,
    )

    assert result.page_count == 2
    assert result.job_count == 101
    assert result.step_record_count == 101
    assert [call.request_target for call in transport.calls] == [
        capture.RUN_REQUEST_PATH,
        capture.FIRST_JOBS_REQUEST_TARGET,
        f"{capture.JOBS_REQUEST_PATH}?per_page=100&page=2",
    ]
    assert (output / capture.RUN_BODY_PATH).read_bytes() == run_body
    assert (output / (capture.JOBS_BODY_TEMPLATE % 1)).read_bytes() == page_bodies[0]
    assert (output / (capture.JOBS_BODY_TEMPLATE % 2)).read_bytes() == page_bodies[1]

    manifest = _manifest(output, capture)
    assert manifest["pagination"]["page_count"] == 2
    assert manifest["pagination"]["page_sequence"] == [1, 2]
    assert manifest["pagination"]["reported_total_count"] == 101
    assert manifest["pagination"]["reconstructed_unique_job_count"] == 101
    first_relation = manifest["jobs_page_exchanges"][0]["record"][
        "pagination_relation"
    ]
    second_relation = manifest["jobs_page_exchanges"][1]["record"][
        "pagination_relation"
    ]
    assert first_relation == {
        "is_final_page": False,
        "link_header_status": "present",
        "next_page_number": 2,
        "next_relation_status": "present",
        "next_request_target": f"{capture.JOBS_REQUEST_PATH}?per_page=100&page=2",
        "page_number": 1,
        "relation_source": "selected_link_header",
    }
    assert second_relation == {
        "is_final_page": True,
        "link_header_status": "absent",
        "next_page_number": None,
        "next_relation_status": "closed_by_absence",
        "next_request_target": None,
        "page_number": 2,
        "relation_source": "selected_link_header",
    }
    assert manifest["counts"]["declared_non_manifest_member_count"] == 6
    assert manifest["counts"]["raw_response_member_count"] == 3
    assert manifest["counts"]["exchange_metadata_member_count"] == 3


def test_existing_output_is_never_replaced(
    capture: Any,
    tmp_path: Path,
) -> None:
    output = tmp_path / "capture-existing"
    transport_a, clock_a, _run_a, _pages_a = _scripted_fixture(capture)
    capture.capture_with_injected_dependencies_for_test(
        repository_root=ROOT,
        output_directory=output,
        token=TOKEN,
        transport=transport_a,
        clock=clock_a,
    )
    before = _snapshot_tree(output)

    transport_b, clock_b, _run_b, _pages_b = _scripted_fixture(capture)
    _assert_capture_error(
        capture,
        "existing_output_replacement_forbidden",
        lambda: capture.capture_with_injected_dependencies_for_test(
            repository_root=ROOT,
            output_directory=output,
            token=TOKEN,
            transport=transport_b,
            clock=clock_b,
        ),
    )
    assert _snapshot_tree(output) == before
    _assert_no_owned_staging(tmp_path, output.name)


def test_output_inside_repository_is_rejected_and_sources_remain_exact(
    capture: Any,
) -> None:
    output = ROOT / ".pulsemech-forbidden-capture-output-v0"
    if output.exists() or output.is_symlink():
        raise AssertionError(f"test output path unexpectedly exists: {output}")
    sources_before = _source_snapshot()
    transport, clock, _run, _pages = _scripted_fixture(capture)
    try:
        _assert_capture_error(
            capture,
            "protected_repository_source_write_forbidden",
            lambda: capture.capture_with_injected_dependencies_for_test(
                repository_root=ROOT,
                output_directory=output,
                token=TOKEN,
                transport=transport,
                clock=clock,
            ),
        )
        assert not output.exists()
        assert _source_snapshot() == sources_before
    finally:
        if output.exists() and output.is_dir():
            shutil.rmtree(output)


@pytest.mark.parametrize(
    "token",
    [
        "",
        "short",
        "contains space " + ("A" * 20),
        "contains\nnewline" + ("A" * 20),
        "é" + ("A" * 30),
        "A" * 4097,
    ],
    ids=[
        "empty",
        "too-short",
        "space",
        "newline",
        "non-ascii",
        "too-large",
    ],
)
def test_token_boundary_fails_closed(capture: Any, token: str) -> None:
    _assert_capture_error(
        capture,
        "gh_token_missing_or_invalid",
        lambda: capture._validate_token(token),
    )


def test_application_request_headers_are_exact_and_ordered(capture: Any) -> None:
    assert capture._application_request_headers(TOKEN) == _expected_application_headers(
        capture
    )


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("status-bool", "response_status_type_invalid"),
        ("body-type", "response_body_type_invalid"),
        ("eof-type", "response_eof_state_invalid"),
        ("redirect-type", "response_redirect_state_invalid"),
        ("redirect-flag", "redirect_admission_rejected"),
        ("redirect-status", "redirect_admission_rejected"),
        ("non-200", "non_200_response_rejected"),
        ("truncated", "truncated_response_body"),
        ("empty", "empty_response_body"),
        ("content-type-missing", "content_type_header_missing"),
        ("content-type-wrong", "wrong_content_type"),
        ("content-encoding", "unsupported_content_encoding"),
        ("duplicate-content-type", "duplicate_allowlisted_response_header"),
        ("duplicate-content-length", "duplicate_content_length_header"),
        ("content-length-invalid", "content_length_header_invalid"),
        ("content-length-mismatch", "content_length_body_size_mismatch"),
        ("header-newline", "response_header_value_invalid"),
        ("malformed-json", "run_attempt_response_invalid_json"),
        ("top-level-array", "run_attempt_response_top_level_not_object"),
    ],
)
def test_response_admission_failures_are_deterministic(
    capture: Any,
    case: str,
    expected: str,
) -> None:
    body: Any = _json_body(_run_document(capture))
    status: Any = 200
    clean_eof: Any = True
    redirect_observed: Any = False
    headers: list[tuple[str, str]] = list(_headers_for_body(body))

    if case == "status-bool":
        status = True
    elif case == "body-type":
        body = "not-bytes"
    elif case == "eof-type":
        clean_eof = "true"
    elif case == "redirect-type":
        redirect_observed = "false"
    elif case == "redirect-flag":
        redirect_observed = True
    elif case == "redirect-status":
        status = 302
    elif case == "non-200":
        status = 503
    elif case == "truncated":
        clean_eof = False
    elif case == "empty":
        body = b""
        headers = list(_headers_for_body(body))
    elif case == "content-type-missing":
        headers = list(_headers_for_body(body, content_type=None))
    elif case == "content-type-wrong":
        headers = list(_headers_for_body(body, content_type="text/plain"))
    elif case == "content-encoding":
        headers = list(_headers_for_body(body, content_encoding="gzip"))
    elif case == "duplicate-content-type":
        headers.append(("content-type", "application/json"))
    elif case == "duplicate-content-length":
        headers.append(("content-length", str(len(body))))
    elif case == "content-length-invalid":
        headers = [
            (name, "NaN" if name.lower() == "content-length" else value)
            for name, value in headers
        ]
    elif case == "content-length-mismatch":
        headers = [
            (name, str(len(body) + 1) if name.lower() == "content-length" else value)
            for name, value in headers
        ]
    elif case == "header-newline":
        headers.append(("ETag", "bad\nvalue"))
    elif case == "malformed-json":
        body = b'{"unterminated":'
        headers = list(_headers_for_body(body))
    elif case == "top-level-array":
        body = b"[]\n"
        headers = list(_headers_for_body(body))
    else:
        raise AssertionError(f"unknown case: {case}")

    response = capture.TransportResponse(
        status=status,
        headers=tuple(headers),
        body=body,
        clean_eof=clean_eof,
        redirect_observed=redirect_observed,
    )
    transport = ScriptedTransport([(capture.RUN_REQUEST_PATH, response)])
    clock = _clock_for_requests(1)
    _assert_capture_error(
        capture,
        expected,
        lambda: capture._capture_response(
            transport=transport,
            clock=clock,
            token=TOKEN,
            request_target=capture.RUN_REQUEST_PATH,
            label="run_attempt_response",
        ),
    )





@pytest.mark.parametrize(
    "numeric_token",
    ("1.0", "1e2", "-0", "NaN", "Infinity", "-Infinity"),
    ids=(
        "fractional",
        "scientific-notation",
        "negative-zero",
        "nan",
        "positive-infinity",
        "negative-infinity",
    ),
)
def test_numeric_response_tokens_fail_before_publication(
    capture: Any,
    tmp_path: Path,
    numeric_token: str,
) -> None:
    valid_run_body = _json_body(_run_document(capture))
    valid_jobs_body = _json_body(
        _jobs_document(capture, list(range(86815582001, 86815582009)))
    )
    sources_before = _source_snapshot()

    for response_role in ("run", "jobs"):
        run_body = valid_run_body
        jobs_body = valid_jobs_body
        if response_role == "run":
            run_body = _with_top_level_numeric_probe(run_body, numeric_token)
            expected_error = "run_attempt_response_invalid_json"
        else:
            jobs_body = _with_top_level_numeric_probe(jobs_body, numeric_token)
            expected_error = "jobs_page_1_response_invalid_json"

        output = tmp_path / (
            "numeric-domain-"
            + numeric_token.replace("-", "negative-").replace(".", "-")
            + "-"
            + response_role
        )
        transport = ScriptedTransport(
            [
                (
                    capture.RUN_REQUEST_PATH,
                    _transport_response(capture, run_body),
                ),
                (
                    capture.FIRST_JOBS_REQUEST_TARGET,
                    _transport_response(capture, jobs_body),
                ),
            ]
        )
        clock = _clock_for_requests(2)
        _assert_capture_error(
            capture,
            expected_error,
            lambda: capture.capture_with_injected_dependencies_for_test(
                repository_root=ROOT,
                output_directory=output,
                token=TOKEN,
                transport=transport,
                clock=clock,
            ),
        )
        assert not output.exists()
        _assert_no_owned_staging(tmp_path, output.name)
        assert _source_snapshot() == sources_before
        if response_role == "run":
            assert len(transport.calls) == 1
            assert transport.remaining == 1
            assert clock.consumed == 2
        else:
            assert len(transport.calls) == 2
            assert transport.remaining == 0
            assert clock.consumed == 4


def test_response_size_and_clock_order_limits_fail_closed(
    capture: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized_body = b'{"value":"' + (b"x" * 128) + b'"}\n'
    response = _transport_response(capture, oversized_body)
    transport = ScriptedTransport([(capture.RUN_REQUEST_PATH, response)])
    monkeypatch.setattr(capture, "MAX_RESPONSE_BODY_BYTES", 32)
    _assert_capture_error(
        capture,
        "response_body_size_limit_exceeded",
        lambda: capture._capture_response(
            transport=transport,
            clock=_clock_for_requests(1),
            token=TOKEN,
            request_target=capture.RUN_REQUEST_PATH,
            label="run_attempt_response",
        ),
    )

    valid_body = _json_body(_run_document(capture))
    valid_response = _transport_response(capture, valid_body)
    reverse_clock = SequenceClock(
        [
            CAPTURE_BASE + dt.timedelta(microseconds=2),
            CAPTURE_BASE + dt.timedelta(microseconds=1),
        ]
    )
    _assert_capture_error(
        capture,
        "response_received_before_capture_start",
        lambda: capture._capture_response(
            transport=ScriptedTransport(
                [(capture.RUN_REQUEST_PATH, valid_response)]
            ),
            clock=reverse_clock,
            token=TOKEN,
            request_target=capture.RUN_REQUEST_PATH,
            label="run_attempt_response",
        ),
    )


@pytest.mark.parametrize(
    ("path", "replacement", "expected"),
    [
        (("id",), 1, "wrong_run_id"),
        (("run_number",), 1, "wrong_run_number"),
        (("run_attempt",), 2, "wrong_run_attempt"),
        (("name",), "Other CI", "wrong_workflow_name"),
        (("workflow_id",), 1, "wrong_workflow_id"),
        (("path",), ".github/workflows/other.yml", "wrong_workflow_path"),
        (("event",), "push", "wrong_event"),
        (("head_branch",), "feature", "wrong_head_branch"),
        (("head_sha",), "0" * 40, "wrong_source_commit"),
        (("status",), "in_progress", "non_completed_run"),
        (("conclusion",), "failure", "non_success_reference_run"),
        (("created_at",), "2026-07-13T12:26:53Z", "run_created_at_invalid"),
        (("run_started_at",), "2026-07-13T12:26:53Z", "run_started_at_invalid"),
        (("updated_at",), "2026-07-13T12:32:22Z", "run_updated_at_invalid"),
        (("repository", "full_name"), "Other/repo", "wrong_repository_identity"),
        (("repository", "id"), 1, "wrong_repository_identity"),
        (("repository", "fork"), True, "fork_subject"),
        (("head_repository", "full_name"), "Other/repo", "wrong_head_repository_identity"),
        (("head_repository", "id"), 1, "wrong_head_repository_identity"),
        (("head_repository", "fork"), True, "wrong_head_repository_identity"),
    ],
    ids=[
        "run-id",
        "run-number",
        "run-attempt",
        "workflow-name",
        "workflow-id",
        "workflow-path",
        "event",
        "head-branch",
        "source-commit",
        "run-status",
        "run-conclusion",
        "created-at",
        "started-at",
        "updated-at",
        "repository-name",
        "repository-id",
        "fork",
        "head-repository-name",
        "head-repository-id",
        "head-repository-fork",
    ],
)
def test_run_attempt_identity_mutations_fail_closed(
    capture: Any,
    path: Sequence[Any],
    replacement: Any,
    expected: str,
) -> None:
    document = _run_document(capture)
    _set_path(document, path, replacement)
    response = _captured_response(capture, document)
    _assert_capture_error(
        capture,
        expected,
        lambda: capture._validate_run_response(response),
    )


def test_run_attempt_capture_must_occur_after_subject_completion(capture: Any) -> None:
    response = _captured_response(
        capture,
        _run_document(capture),
        capture_started_utc="2026-07-13T12:32:20.999999Z",
        response_received_utc="2026-07-13T12:32:21.000000Z",
    )
    _assert_capture_error(
        capture,
        "capture_started_before_subject_run_completed",
        lambda: capture._validate_run_response(response),
    )


def test_valid_run_attempt_reconstructs_exact_subject(capture: Any) -> None:
    summary, subject = capture._validate_run_response(
        _captured_response(capture, _run_document(capture))
    )
    assert subject == capture._expected_subject()
    assert summary["workflow_run_id"] == capture.SUBJECT_RUN_ID
    assert summary["workflow_run_attempt"] == capture.SUBJECT_RUN_ATTEMPT
    assert summary["head_sha"] == capture.SUBJECT_SOURCE_COMMIT
    assert summary["same_repository_subject"] is True


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("total-count-type", "jobs_total_count_invalid"),
        ("jobs-missing", "jobs_array_missing"),
        ("job-not-object", "job_record_not_object"),
        ("job-id", "job_id_invalid"),
        ("duplicate-job", "duplicate_job_id"),
        ("run-id", "job_run_id_mismatch"),
        ("run-attempt", "job_run_attempt_mismatch"),
        ("workflow-name", "job_workflow_name_mismatch"),
        ("head-sha", "job_head_sha_mismatch"),
        ("job-name", "job_name_invalid"),
        ("job-status", "job_0_status_invalid"),
        ("job-conclusion", "job_0_conclusion_invalid"),
        ("job-started", "job_0_started_at_invalid"),
        ("job-time-order", "job_0_timestamp_order_invalid"),
        ("skipped-time-pair", "job_0_skipped_timestamp_pair_invalid"),
        ("steps-type", "job_steps_not_array"),
        ("step-not-object", "step_record_not_object"),
        ("step-number", "step_number_invalid"),
        ("duplicate-step", "duplicate_step_number"),
        ("step-order", "step_order_invalid"),
        ("step-name", "step_name_invalid"),
        ("step-status", "job_0_step_0_status_invalid"),
        ("step-conclusion", "job_0_step_0_conclusion_invalid"),
        ("step-started", "job_0_step_0_started_at_invalid"),
        ("step-time-order", "job_0_step_0_timestamp_order_invalid"),
        ("step-skipped-time-pair", "job_0_step_0_skipped_timestamp_pair_invalid"),
    ],
)
def test_job_and_step_binding_mutations_fail_closed(
    capture: Any,
    case: str,
    expected: str,
) -> None:
    document = _jobs_document(capture, [1001], total_count=1, steps_per_job=1)
    job = document["jobs"][0]
    step = job["steps"][0]

    if case == "total-count-type":
        document["total_count"] = True
    elif case == "jobs-missing":
        del document["jobs"]
    elif case == "job-not-object":
        document["jobs"] = ["not-an-object"]
    elif case == "job-id":
        job["id"] = 0
    elif case == "duplicate-job":
        document["jobs"].append(copy.deepcopy(job))
        document["total_count"] = 2
    elif case == "run-id":
        job["run_id"] = 1
    elif case == "run-attempt":
        job["run_attempt"] = 2
    elif case == "workflow-name":
        job["workflow_name"] = "Other CI"
    elif case == "head-sha":
        job["head_sha"] = "0" * 40
    elif case == "job-name":
        del job["name"]
    elif case == "job-status":
        job["status"] = "in_progress"
    elif case == "job-conclusion":
        job["conclusion"] = "failure"
    elif case == "job-started":
        job["started_at"] = None
    elif case == "job-time-order":
        job["started_at"] = "2026-07-13T12:27:02Z"
        job["completed_at"] = "2026-07-13T12:27:01Z"
    elif case == "skipped-time-pair":
        job["conclusion"] = "skipped"
        job["started_at"] = None
    elif case == "steps-type":
        job["steps"] = "not-an-array"
    elif case == "step-not-object":
        job["steps"] = ["not-an-object"]
    elif case == "step-number":
        step["number"] = 0
    elif case == "duplicate-step":
        job["steps"].append(copy.deepcopy(step))
    elif case == "step-order":
        job["steps"] = [_step_document(2), _step_document(1)]
    elif case == "step-name":
        del step["name"]
    elif case == "step-status":
        step["status"] = "in_progress"
    elif case == "step-conclusion":
        step["conclusion"] = "failure"
    elif case == "step-started":
        step["started_at"] = None
    elif case == "step-time-order":
        step["started_at"] = "2026-07-13T12:27:02Z"
        step["completed_at"] = "2026-07-13T12:27:01Z"
    elif case == "step-skipped-time-pair":
        step["conclusion"] = "skipped"
        step["started_at"] = None
    else:
        raise AssertionError(f"unknown case: {case}")

    response = _captured_response(capture, document)
    _assert_capture_error(
        capture,
        expected,
        lambda: capture._validate_jobs_page(
            response,
            page_number=1,
            subject=capture._expected_subject(),
            all_job_ids=set(),
        ),
    )


def test_skipped_jobs_and_steps_preserve_explicit_unavailability(capture: Any) -> None:
    document = {
        "total_count": 2,
        "jobs": [
            _job_document(
                capture,
                2001,
                conclusion="skipped",
                started_at=None,
                completed_at=None,
                steps=None,
            ),
            _job_document(
                capture,
                2002,
                steps=[
                    _step_document(
                        1,
                        conclusion="skipped",
                        started_at=None,
                        completed_at=None,
                    )
                ],
            ),
        ],
    }
    summary, total, steps = capture._validate_jobs_page(
        _captured_response(capture, document),
        page_number=1,
        subject=capture._expected_subject(),
        all_job_ids=set(),
    )
    assert total == 2
    assert steps == 1
    assert summary["jobs_on_page"] == 2
    assert summary["status_conclusion_relations_valid"] is True


def test_job_and_step_limits_fail_closed(
    capture: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    too_many_jobs = _jobs_document(capture, [3001, 3002], total_count=2)
    monkeypatch.setattr(capture, "MAX_JOBS_PER_PAGE", 1)
    _assert_capture_error(
        capture,
        "jobs_per_page_limit_exceeded",
        lambda: capture._validate_jobs_page(
            _captured_response(capture, too_many_jobs),
            page_number=1,
            subject=capture._expected_subject(),
            all_job_ids=set(),
        ),
    )

    monkeypatch.setattr(capture, "MAX_JOBS_PER_PAGE", 100)
    too_many_steps = _jobs_document(capture, [3003], total_count=1, steps_per_job=2)
    monkeypatch.setattr(capture, "MAX_STEP_RECORDS_PER_JOB", 1)
    _assert_capture_error(
        capture,
        "step_record_limit_exceeded",
        lambda: capture._validate_jobs_page(
            _captured_response(capture, too_many_steps),
            page_number=1,
            subject=capture._expected_subject(),
            all_job_ids=set(),
        ),
    )


@pytest.mark.parametrize(
    ("link_value", "current_page", "expected"),
    [
        ("<unterminated", 1, "link_header_syntax_invalid"),
        (
            "<https://api.github.com/x>; rel=\"next next\"",
            1,
            "duplicate_rel_next",
        ),
        (
            "<https://api.github.com/a>; rel=\"next\", "
            "<https://api.github.com/b>; rel=\"next\"",
            1,
            "duplicate_rel_next",
        ),
        (
            "<http://api.github.com"
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/"
            "29249887581/attempts/1/jobs?per_page=100&page=2>; rel=\"next\"",
            1,
            "link_next_origin_mismatch",
        ),
        (
            "<https://example.com"
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/"
            "29249887581/attempts/1/jobs?per_page=100&page=2>; rel=\"next\"",
            1,
            "link_next_origin_mismatch",
        ),
        (
            "<https://user@api.github.com"
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/"
            "29249887581/attempts/1/jobs?per_page=100&page=2>; rel=\"next\"",
            1,
            "link_next_userinfo_forbidden",
        ),
        (
            "<https://api.github.com:443"
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/"
            "29249887581/attempts/1/jobs?per_page=100&page=2>; rel=\"next\"",
            1,
            "link_next_port_forbidden",
        ),
        (
            "<https://api.github.com"
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/"
            "29249887581/attempts/1/jobs?per_page=100&page=2#fragment>; rel=\"next\"",
            1,
            "link_next_fragment_forbidden",
        ),
        (
            "<https://api.github.com/repos/HKati/pulse-release-gates-0.1/"
            "actions/runs/29249887581/jobs?per_page=100&page=2>; rel=\"next\"",
            1,
            "link_next_path_mismatch",
        ),
        (
            "<https://api.github.com"
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/"
            "29249887581/attempts/1/jobs?page=2&per_page=100>; rel=\"next\"",
            1,
            "link_next_query_mismatch",
        ),
        (
            "<https://api.github.com"
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/"
            "29249887581/attempts/1/jobs?per_page=100&page=3>; rel=\"next\"",
            1,
            "link_next_query_mismatch",
        ),
        (
            "<https://api.github.com"
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/"
            "29249887581/attempts/1/jobs?per_page=100&page=101>; rel=\"next\"",
            100,
            "maximum_page_count_exceeded",
        ),
    ],
)
def test_rel_next_mutations_fail_closed(
    capture: Any,
    link_value: str,
    current_page: int,
    expected: str,
) -> None:
    selected, _ = capture._selected_response_headers(
        (
            ("Content-Type", "application/json"),
            ("Link", link_value),
        )
    )
    _assert_capture_error(
        capture,
        expected,
        lambda: capture._link_next_target(
            selected,
            current_page=current_page,
        ),
    )


def test_rel_next_exact_target_and_final_absence_states(capture: Any) -> None:
    next_url = (
        "https://api.github.com"
        + capture.JOBS_REQUEST_PATH
        + "?per_page=100&page=2"
    )
    selected, _ = capture._selected_response_headers(
        (
            ("Content-Type", "application/json"),
            ("Link", f'<{next_url}>; rel="next"'),
        )
    )
    assert capture._link_next_target(selected, current_page=1) == (
        f"{capture.JOBS_REQUEST_PATH}?per_page=100&page=2",
        "present",
    )

    absent, _ = capture._selected_response_headers(
        (("Content-Type", "application/json"),)
    )
    assert capture._link_next_target(absent, current_page=1) == (None, "absent")

    prev_only, _ = capture._selected_response_headers(
        (
            ("Content-Type", "application/json"),
            (
                "Link",
                "<https://api.github.com"
                + capture.JOBS_REQUEST_PATH
                + "?per_page=100&page=1>; rel=\"prev\"",
            ),
        )
    )
    assert capture._link_next_target(prev_only, current_page=2) == (None, "present")


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("reported-total", "reported_total_count_mismatch"),
        ("page-total-disagreement", "page_total_count_disagreement"),
        ("duplicate-across-pages", "duplicate_job_id"),
        ("page-count-relation", "pagination_page_count_relation_mismatch"),
        ("secret-in-raw-body", "secret_value_in_output"),
        ("exchange-time-order", "capture_exchange_time_order_invalid"),
    ],
)
def test_full_capture_relation_failures_publish_nothing(
    capture: Any,
    tmp_path: Path,
    case: str,
    expected: str,
) -> None:
    run_document = _run_document(capture)
    pages: list[tuple[Mapping[str, Any], str | None]]
    clock: SequenceClock | None = None

    if case == "reported-total":
        pages = [
            (
                _jobs_document(
                    capture,
                    list(range(4001, 4009)),
                    total_count=9,
                ),
                None,
            )
        ]
    elif case == "page-total-disagreement":
        next_url = (
            "https://api.github.com"
            + capture.JOBS_REQUEST_PATH
            + "?per_page=100&page=2"
        )
        pages = [
            (
                _jobs_document(
                    capture,
                    list(range(5001, 5101)),
                    total_count=101,
                ),
                f'<{next_url}>; rel="next"',
            ),
            (_jobs_document(capture, [5101], total_count=100), None),
        ]
    elif case == "duplicate-across-pages":
        next_url = (
            "https://api.github.com"
            + capture.JOBS_REQUEST_PATH
            + "?per_page=100&page=2"
        )
        pages = [
            (
                _jobs_document(
                    capture,
                    list(range(6001, 6101)),
                    total_count=101,
                ),
                f'<{next_url}>; rel="next"',
            ),
            (_jobs_document(capture, [6001], total_count=101), None),
        ]
    elif case == "page-count-relation":
        next_url = (
            "https://api.github.com"
            + capture.JOBS_REQUEST_PATH
            + "?per_page=100&page=2"
        )
        pages = [
            (
                _jobs_document(capture, [7001, 7002, 7003, 7004], total_count=8),
                f'<{next_url}>; rel="next"',
            ),
            (
                _jobs_document(capture, [7005, 7006, 7007, 7008], total_count=8),
                None,
            ),
        ]
    elif case == "secret-in-raw-body":
        run_document["opaque_transport_note"] = TOKEN
        pages = [
            (
                _jobs_document(capture, list(range(8001, 8009)), total_count=8),
                None,
            )
        ]
    elif case == "exchange-time-order":
        pages = [
            (
                _jobs_document(capture, list(range(9001, 9009)), total_count=8),
                None,
            )
        ]
        clock = SequenceClock(
            [
                CAPTURE_BASE,
                CAPTURE_BASE + dt.timedelta(microseconds=2),
                CAPTURE_BASE + dt.timedelta(microseconds=1),
                CAPTURE_BASE + dt.timedelta(microseconds=3),
            ]
        )
    else:
        raise AssertionError(f"unknown case: {case}")

    transport, default_clock, _run, _page_bodies = _scripted_fixture(
        capture,
        run_document=run_document,
        pages=pages,
    )
    output = tmp_path / f"capture-failure-{case}"
    _assert_capture_error(
        capture,
        expected,
        lambda: capture.capture_with_injected_dependencies_for_test(
            repository_root=ROOT,
            output_directory=output,
            token=TOKEN,
            transport=transport,
            clock=default_clock if clock is None else clock,
        ),
    )
    assert not output.exists()
    _assert_no_owned_staging(tmp_path, output.name)


def test_total_capture_and_total_step_limits_fail_closed_after_source_admission(
    capture: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = _git_head(ROOT)
    sources = capture._load_sources(
        ROOT,
        revision=revision,
        include_workflow=False,
    )

    transport, clock, _run, _pages = _scripted_fixture(capture)
    monkeypatch.setattr(capture, "MAX_TOTAL_CAPTURE_BYTES", 128)
    output = tmp_path / "capture-total-size-limit"
    _assert_capture_error(
        capture,
        "total_capture_size_limit_exceeded",
        lambda: capture._capture_core(
            sources=sources,
            output_directory=output,
            token=TOKEN,
            transport=transport,
            clock=clock,
            record_status="example",
            workflow_execution=None,
        ),
    )
    assert not output.exists()

    transport, clock, _run, _pages = _scripted_fixture(capture)
    monkeypatch.setattr(capture, "MAX_TOTAL_CAPTURE_BYTES", 64 * 1024 * 1024)
    monkeypatch.setattr(capture, "MAX_TOTAL_STEP_RECORDS", 7)
    output = tmp_path / "capture-total-step-limit"
    _assert_capture_error(
        capture,
        "total_step_record_limit_exceeded",
        lambda: capture._capture_core(
            sources=sources,
            output_directory=output,
            token=TOKEN,
            transport=transport,
            clock=clock,
            record_status="example",
            workflow_execution=None,
        ),
    )
    assert not output.exists()


def test_request_record_rejects_floating_or_noncanonical_targets(capture: Any) -> None:
    invalid = (
        ("https://api.github.com" + capture.RUN_REQUEST_PATH, None, "request_target_not_origin_form"),
        (capture.RUN_REQUEST_PATH + "?latest=true", None, "run_attempt_request_target_mismatch"),
        (capture.JOBS_REQUEST_PATH + "?page=1&per_page=100", 1, "jobs_page_request_target_mismatch"),
        (capture.JOBS_REQUEST_PATH + "?per_page=100&page=01", 1, "jobs_page_request_target_mismatch"),
        (
            "/repos/HKati/pulse-release-gates-0.1/actions/runs/29249887581/jobs?per_page=100&page=1",
            1,
            "jobs_page_request_target_mismatch",
        ),
    )
    for target, page_number, expected in invalid:
        _assert_capture_error(
            capture,
            expected,
            lambda target=target, page_number=page_number: capture._request_record(
                request_target=target,
                page_number=page_number,
            ),
        )


def _simple_publish_files() -> dict[str, bytes]:
    return {
        "raw/run_attempt_response.json": b'{"fixture":"raw"}\n',
        "metadata/run_attempt_exchange_v0.json": b'{"fixture":"metadata"}\n',
        "fixture_manifest.json": b'{"fixture":"manifest"}\n',
    }


def test_publication_cleanup_covers_keyboard_interrupt(
    capture: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "interrupted-publication"
    original = capture._write_file_at
    call_count = 0

    def interrupted_write(directory_fd: int, name: str, payload: bytes) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise KeyboardInterrupt
        original(directory_fd, name, payload)

    monkeypatch.setattr(capture, "_write_file_at", interrupted_write)
    with pytest.raises(KeyboardInterrupt):
        capture._publish_capture(
            repository_root=ROOT,
            output_directory=output,
            files=_simple_publish_files(),
        )
    assert not output.exists()
    _assert_no_owned_staging(tmp_path, output.name)


def test_post_publication_readback_failure_removes_owned_output(
    capture: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "readback-failure"
    original = capture._verify_exact_directory_inventory
    call_count = 0

    def fail_second_readback(root_fd: int, files: Mapping[str, bytes]) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise capture.CaptureError("synthetic_post_publication_readback_failure")
        original(root_fd, files)

    monkeypatch.setattr(
        capture,
        "_verify_exact_directory_inventory",
        fail_second_readback,
    )
    _assert_capture_error(
        capture,
        "synthetic_post_publication_readback_failure",
        lambda: capture._publish_capture(
            repository_root=ROOT,
            output_directory=output,
            files=_simple_publish_files(),
        ),
    )
    assert not output.exists()
    _assert_no_owned_staging(tmp_path, output.name)


def test_publication_rejects_existing_target_and_out_of_contract_member(
    capture: Any,
    tmp_path: Path,
) -> None:
    existing = tmp_path / "existing-target"
    existing.mkdir()
    sentinel = existing / "sentinel"
    sentinel.write_bytes(b"unchanged")
    _assert_capture_error(
        capture,
        "existing_output_replacement_forbidden",
        lambda: capture._publish_capture(
            repository_root=ROOT,
            output_directory=existing,
            files=_simple_publish_files(),
        ),
    )
    assert sentinel.read_bytes() == b"unchanged"

    invalid = tmp_path / "invalid-member"
    _assert_capture_error(
        capture,
        "output_member_path_outside_contract",
        lambda: capture._publish_capture(
            repository_root=ROOT,
            output_directory=invalid,
            files={"nested/outside/member.json": b"{}\n"},
        ),
    )
    assert not invalid.exists()
    _assert_no_owned_staging(tmp_path, invalid.name)


def _make_minimal_repository(tmp_path: Path) -> tuple[Path, Any, str]:
    repository = tmp_path / "minimal-repository"
    for relative in (
        "schemas",
        "contracts",
        "tools",
        "examples/compute",
    ):
        (repository / relative).mkdir(parents=True, exist_ok=True)
    copies = {
        SCHEMA_PATH: repository / SCHEMA_PATH.relative_to(ROOT),
        CONTRACT_PATH: repository / CONTRACT_PATH.relative_to(ROOT),
        CAPTURE_TOOL_PATH: repository / CAPTURE_TOOL_PATH.relative_to(ROOT),
        EXAMPLE_PATH: repository / EXAMPLE_PATH.relative_to(ROOT),
        OFFLINE_VALIDATOR_PATH: repository / OFFLINE_VALIDATOR_PATH.relative_to(ROOT),
    }
    for source, destination in copies.items():
        destination.write_bytes(source.read_bytes())

    commands = (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "PULSEmech regression"],
        ["git", "config", "user.email", "regression@example.invalid"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "fixture repository"],
    )
    for command in commands:
        subprocess.run(
            command,
            cwd=repository,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    revision = _git_head(repository)
    module = _load_capture_module(
        repository / CAPTURE_TOOL_PATH.relative_to(ROOT),
        name=f"pulsemech_capture_temp_{revision}",
    )
    return repository, module, revision


def test_source_drift_before_publication_fails_closed(
    tmp_path: Path,
) -> None:
    repository, module, revision = _make_minimal_repository(tmp_path)
    contract_path = repository / CONTRACT_PATH.relative_to(ROOT)
    original_contract = contract_path.read_bytes()

    def mutate_on_second_request(call_number: int, request_target: str) -> None:
        del request_target
        if call_number == 2:
            contract_path.write_bytes(original_contract + b" ")

    transport, clock, _run, _pages = _scripted_fixture(
        module,
        on_call=mutate_on_second_request,
    )
    output = tmp_path / "drifted-source-output"
    _assert_capture_error(
        module,
        "normative_contract_drift_detected",
        lambda: module.capture_with_injected_dependencies_for_test(
            repository_root=repository,
            output_directory=output,
            token=TOKEN,
            transport=transport,
            clock=clock,
            source_revision=revision,
        ),
    )
    assert not output.exists()
    _assert_no_owned_staging(tmp_path, output.name)


def test_explicit_source_revision_must_equal_repository_head(
    capture: Any,
    tmp_path: Path,
) -> None:
    transport, clock, _run, _pages = _scripted_fixture(capture)
    _assert_capture_error(
        capture,
        "repository_head_revision_mismatch",
        lambda: capture.capture_with_injected_dependencies_for_test(
            repository_root=ROOT,
            output_directory=tmp_path / "wrong-revision",
            token=TOKEN,
            transport=transport,
            clock=clock,
            source_revision="0" * 40,
        ),
    )


class _StubHttpResponse:
    def __init__(
        self,
        *,
        status: int,
        headers: Sequence[tuple[str, str]],
        body: bytes,
    ) -> None:
        self.status = status
        self._headers = tuple(headers)
        self._body = body
        self._offset = 0
        self.closed = False

    def getheaders(self) -> list[tuple[str, str]]:
        return list(self._headers)

    def read(self, maximum: int) -> bytes:
        if self._offset >= len(self._body):
            return b""
        end = min(len(self._body), self._offset + maximum)
        value = self._body[self._offset:end]
        self._offset = end
        return value

    def close(self) -> None:
        self.closed = True


class _StubHttpsConnection:
    def __init__(
        self,
        host: str,
        *,
        timeout: int,
        context: Any,
        response: _StubHttpResponse,
        failure: BaseException | None = None,
    ) -> None:
        self.host = host
        self.timeout = timeout
        self.context = context
        self.response = response
        self.failure = failure
        self.request_call: tuple[Any, ...] | None = None
        self.closed = False

    def request(
        self,
        method: str,
        target: str,
        *,
        body: bytes | None,
        headers: Mapping[str, str],
        encode_chunked: bool,
    ) -> None:
        self.request_call = (method, target, body, dict(headers), encode_chunked)
        if self.failure is not None:
            raise self.failure

    def getresponse(self) -> _StubHttpResponse:
        return self.response

    def close(self) -> None:
        self.closed = True


def test_stdlib_https_transport_sends_exact_request_without_redirect_handler(
    capture: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = b'{"fixture":true}\n'
    response = _StubHttpResponse(
        status=200,
        headers=_headers_for_body(body),
        body=body,
    )
    observed: list[_StubHttpsConnection] = []

    def connection_factory(host: str, *, timeout: int, context: Any) -> Any:
        connection = _StubHttpsConnection(
            host,
            timeout=timeout,
            context=context,
            response=response,
        )
        observed.append(connection)
        return connection

    monkeypatch.setattr(capture.http.client, "HTTPSConnection", connection_factory)
    transport = capture.StdlibHttpsTransport()
    result = transport.get(
        request_target=capture.RUN_REQUEST_PATH,
        headers=_expected_application_headers(capture),
        timeout_seconds=30,
        maximum_body_bytes=1024,
    )

    assert len(observed) == 1
    connection = observed[0]
    assert connection.host == "api.github.com"
    assert connection.timeout == 30
    assert connection.request_call == (
        "GET",
        capture.RUN_REQUEST_PATH,
        None,
        dict(_expected_application_headers(capture)),
        False,
    )
    assert connection.closed is True
    assert response.closed is True
    assert result.status == 200
    assert result.body == body
    assert result.clean_eof is True
    assert result.redirect_observed is False


def test_stdlib_https_transport_network_and_size_failures_are_closed(
    capture: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = b"x" * 65
    response = _StubHttpResponse(status=200, headers=(), body=body)

    def oversized_factory(host: str, *, timeout: int, context: Any) -> Any:
        return _StubHttpsConnection(
            host,
            timeout=timeout,
            context=context,
            response=response,
        )

    monkeypatch.setattr(capture.http.client, "HTTPSConnection", oversized_factory)
    transport = capture.StdlibHttpsTransport()
    _assert_capture_error(
        capture,
        "response_body_size_limit_exceeded",
        lambda: transport.get(
            request_target=capture.RUN_REQUEST_PATH,
            headers=_expected_application_headers(capture),
            timeout_seconds=30,
            maximum_body_bytes=64,
        ),
    )

    response = _StubHttpResponse(status=200, headers=(), body=b"{}")

    def failing_factory(host: str, *, timeout: int, context: Any) -> Any:
        return _StubHttpsConnection(
            host,
            timeout=timeout,
            context=context,
            response=response,
            failure=OSError("fixture network failure"),
        )

    monkeypatch.setattr(capture.http.client, "HTTPSConnection", failing_factory)
    transport = capture.StdlibHttpsTransport()
    _assert_capture_error(
        capture,
        "network_request_failed",
        lambda: transport.get(
            request_target=capture.RUN_REQUEST_PATH,
            headers=_expected_application_headers(capture),
            timeout_seconds=30,
            maximum_body_bytes=64,
        ),
    )


def test_cli_requires_isolated_python_and_never_echoes_invalid_arguments(
    capture: Any,
    tmp_path: Path,
) -> None:
    non_isolated = subprocess.run(
        [
            sys.executable,
            str(CAPTURE_TOOL_PATH),
            "--output-directory",
            str(tmp_path / "non-isolated"),
        ],
        cwd=ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert non_isolated.returncode == 2
    assert non_isolated.stdout == b""
    assert non_isolated.stderr == capture._ISOLATED_PYTHON_REQUIRED_DIAGNOSTIC.encode(
        "utf-8"
    )

    secret_argument = "fixture-secret-argument-never-echoed"
    isolated_invalid = subprocess.run(
        [
            sys.executable,
            "-I",
            str(CAPTURE_TOOL_PATH),
            "--fixture-transport",
            secret_argument,
        ],
        cwd=ROOT,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert isolated_invalid.returncode == 2
    assert isolated_invalid.stdout == b""
    expected = capture._failure_diagnostic("command_line_invalid")
    assert isolated_invalid.stderr == expected
    assert secret_argument.encode("utf-8") not in isolated_invalid.stderr
    assert b"fixture" not in isolated_invalid.stderr


def test_success_and_failure_diagnostics_are_canonical_and_deterministic(
    capture: Any,
) -> None:
    result = capture.CaptureResult(
        record_status="example",
        manifest_file_name=capture.EXAMPLE_MANIFEST_NAME,
        manifest_bytes=b"{}\n",
        manifest_sha256=_sha256(b"{}\n"),
        page_count=1,
        job_count=8,
        step_record_count=8,
        authority_effect="none",
    )
    success_a = capture._success_diagnostic(result)
    success_b = capture._success_diagnostic(result)
    failure_a = capture._failure_diagnostic("fixture_failure")
    failure_b = capture._failure_diagnostic("fixture_failure")
    assert success_a == success_b
    assert failure_a == failure_b
    assert success_a == _canonical_json_bytes(json.loads(success_a))
    assert failure_a == _canonical_json_bytes(json.loads(failure_a))
    assert json.loads(success_a)["authority_effect"] == "none"
    assert json.loads(failure_a) == {
        "authority_effect": "none",
        "error_code": "fixture_failure",
        "ok": False,
        "tool": capture.TOOL_NAME,
        "tool_version": capture.TOOL_VERSION,
    }


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
