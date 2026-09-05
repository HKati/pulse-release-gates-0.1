#!/usr/bin/env python3
from __future__ import annotations

import ast
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
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import pytest


ROOT = Path(__file__).resolve().parents[1]
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
CAPTURE_TOOL_PATH = (
    ROOT / "tools" / "capture_pulsemech_compute_post_run_producer_input_v0.py"
)
VALIDATOR_PATH = (
    ROOT
    / "tools"
    / "check_pulsemech_compute_post_run_producer_input_capture_v0.py"
)
CONTRACT_REGRESSION_PATH = (
    ROOT
    / "tests"
    / "test_pulsemech_compute_post_run_producer_input_capture_contract_v0.py"
)
CAPTURE_REGRESSION_PATH = (
    ROOT / "tests" / "test_capture_pulsemech_compute_post_run_producer_input_v0.py"
)

EXAMPLE_MANIFEST_NAME = (
    "pulsemech_compute_post_run_producer_input_capture_manifest_example_v0.json"
)
RUN_BODY_PATH = "raw/run_attempt_response.json"
RUN_METADATA_PATH = "metadata/run_attempt_exchange_v0.json"
JOBS_BODY_PATH = "raw/jobs_page_0001_response.json"
JOBS_METADATA_PATH = "metadata/jobs_page_0001_exchange_v0.json"
TOKEN = "ghp_" + ("A" * 36)
CAPTURE_BASE = dt.datetime(2026, 8, 1, 18, 0, 0, tzinfo=dt.timezone.utc)

EXPECTED_SOURCE_IDENTITIES = (
    (
        SCHEMA_PATH,
        71861,
        "65a29a18f1b9090f3dd338f9c4c1484b4d851df68ff19758670a4c53c58057bb",
        "f7256747704e87a4df312af6d20dad1c8bea6148",
    ),
    (
        CONTRACT_PATH,
        38745,
        "ec3e31c9526f3bf931c633292bbff77efdf9cfbc61a0be634b6239c4acaccfbe",
        "66e03ebe4b7571888e0a8ac5322561353be2e892",
    ),
    (
        EXAMPLE_PATH,
        16980,
        "8539975490b8e42321d2a32f9003cbc6030e12bfceaed3f7683215edcf57000a",
        "bdde78e902d4a670cf6ac857f737486d321a80d2",
    ),
    (
        CAPTURE_TOOL_PATH,
        105455,
        "c6bfc6c721fa6c6513977a068e3149c954d50526de3c539a044725ed580dfc74",
        "cd8063c7b5ef0f2cd4d09e854358e428138bb714",
    ),
    (
        VALIDATOR_PATH,
        110820,
        "ae5f608cb773ccf541ad1f703713773c59750b4f3997899b8c00f0a2b0d835ca",
        "94c6f2ed4a8e2150ad1c6121b3f5f7c376029760",
    ),
    (
        CONTRACT_REGRESSION_PATH,
        80337,
        "9bc4a14321ab755e3fc76d9d7045a73b84bd0445deb71e38af5aa452ee44ab45",
        "4059de48190b12a3e6ab75dc442a398f78621ffa",
    ),
    (
        CAPTURE_REGRESSION_PATH,
        104959,
        "63a959e90a41e6814c1cef27223cae26ea807475c1bdbd28a8a7050bbe18f795",
        "047df9e35ea39f0413645285a06573e2b4e1e0b2",
    ),
)



EXPECTED_TEST_ITEM_COUNTS = {
    "test_validator_time_ranges_reject_before_permissive_parser": 3,
    "test_timestamp_calendar_and_valid_boundaries": 1,
    "test_rebound_job_step_time_ranges_fail_closed": 8,
    "test_tar_archive_does_not_replace_existing_output": 2,
    "test_tar_archive_is_deterministic_for_same_capture_bytes": 1,
    "test_tar_archive_path_replacement_is_rejected_without_deleting_replacement": 1,
    "test_tar_archive_rejects_failed_or_different_validator_result": 2,
    "test_tar_archive_rejects_incorrect_source_permissions": 8,
    "test_tar_archive_rejects_unadmitted_filesystem_members": 4,
    "test_tar_payload_survives_outer_zip_permission_normalization": 1,
    "test_tar_roundtrip_preserves_exact_bytes_modes_and_validator_invocation": 1,
    "test_tar_roundtrip_with_real_validator_on_synthetic_observed_shape": 1,
    "test_tar_upload_requires_successful_roundtrip_and_exact_transport_members": 1,
    "test_tar_validator_exception_cleans_temporary_restoration": 1,
    "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract": 1,
    "test_capture_before_subject_completion_fails_closed": 1,
    "test_capture_permission_mutations_fail_closed": 6,
    "test_claim_and_authority_expansion_fails_closed": 18,
    "test_cli_failure_diagnostic_is_byte_identical": 1,
    "test_cli_requires_isolated_python": 1,
    "test_compact_raw_jobs_json_is_accepted_when_exactly_rebound": 1,
    "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit": 1,
    "test_exact_one_page_capture_validates_offline": 1,
    "test_exact_prior_repository_object_identities": 7,
    "test_exchange_metadata_bom_fails_closed": 1,
    "test_exchange_metadata_relation_false_fails_closed": 1,
    "test_failure_diagnostic_is_canonical_and_deterministic": 1,
    "test_final_rel_next_presence_fails_closed": 1,
    "test_hard_linked_member_fails_closed": 1,
    "test_invalid_cli_argument_never_echoes_secret": 1,
    "test_isolated_cli_validates_exact_capture": 1,
    "test_jobs_exchange_time_order_fails_closed": 1,
    "test_jobs_request_query_order_mismatch_fails_closed": 1,
    "test_jobs_summary_mismatch_fails_closed": 1,
    "test_link_header_mutations_fail_closed": 4,
    "test_manifest_bom_fails_closed": 1,
    "test_manifest_count_relation_mismatch_fails_closed": 1,
    "test_manifest_duplicate_key_fails_closed": 1,
    "test_manifest_pagination_relation_mismatch_fails_closed": 1,
    "test_manifest_top_level_array_fails_closed": 1,
    "test_missing_manifest_fails_closed": 1,
    "test_missing_second_jobs_page_fails_closed": 1,
    "test_network_audit_guard_rejects_socket_creation": 1,
    "test_non_regular_fifo_member_fails_closed": 1,
    "test_noncanonical_manifest_fails_closed": 1,
    "test_pagination_relation_mismatch_fails_closed": 1,
    "test_raw_response_bom_and_crlf_are_exact_not_canonicalized": 1,
    "test_rebound_invalid_utf8_raw_body_fails_closed": 1,
    "test_rebound_job_and_step_mutations_fail_closed": 12,
    "test_rebound_raw_duplicate_key_fails_closed": 1,
    "test_rebound_raw_top_level_array_fails_closed": 1,
    "test_rebound_run_subject_mutations_fail_closed": 13,
    "test_reported_job_count_mismatch_fails_closed": 1,
    "test_repository_root_without_git_fails_closed": 1,
    "test_response_metadata_mutations_fail_closed": 6,
    "test_response_received_before_capture_start_fails_closed": 1,
    "test_run_request_record_mismatch_fails_closed": 1,
    "test_run_summary_mismatch_fails_closed": 1,
    "test_same_exact_capture_produces_byte_identical_diagnostics": 1,
    "test_schema_binding_digest_mismatch_fails_closed": 1,
    "test_schema_contract_revision_mismatch_fails_closed": 1,
    "test_second_page_total_count_disagreement_fails_closed": 1,
    "test_secret_material_in_rebound_raw_body_fails_closed": 1,
    "test_symlinked_member_fails_closed": 1,
    "test_two_page_capture_validates_exact_pagination": 1,
    "test_unbound_exchange_metadata_mutation_fails_closed": 1,
    "test_unbound_raw_response_byte_mutation_fails_closed": 1,
    "test_undeclared_root_member_fails_closed": 1,
    "test_unresolved_example_revision_requires_canonical_checked_in_example": 1,
    "test_validation_does_not_modify_repository_or_capture": 1,
    "test_validator_source_is_separate_and_network_free": 1,
}
EXPECTED_COLLECTED_TEST_ITEMS = sum(EXPECTED_TEST_ITEM_COUNTS.values())
CRITICAL_TEST_FUNCTIONS = frozenset(
    {
        "test_validator_time_ranges_reject_before_permissive_parser",
        "test_timestamp_calendar_and_valid_boundaries",
        "test_rebound_job_step_time_ranges_fail_closed",
        "test_tar_archive_does_not_replace_existing_output",
        "test_tar_archive_is_deterministic_for_same_capture_bytes",
        "test_tar_archive_path_replacement_is_rejected_without_deleting_replacement",
        "test_tar_archive_rejects_failed_or_different_validator_result",
        "test_tar_archive_rejects_incorrect_source_permissions",
        "test_tar_archive_rejects_unadmitted_filesystem_members",
        "test_tar_payload_survives_outer_zip_permission_normalization",
        "test_tar_roundtrip_preserves_exact_bytes_modes_and_validator_invocation",
        "test_tar_roundtrip_with_real_validator_on_synthetic_observed_shape",
        "test_tar_upload_requires_successful_roundtrip_and_exact_transport_members",
        "test_tar_validator_exception_cleans_temporary_restoration",
        "test_authoritative_launcher_sanitizes_pytest_environment_and_requires_completed_contract",
        "test_capture_permission_mutations_fail_closed",
        "test_direct_authoritative_launcher_rejects_terminal_pytest_early_exit",
        "test_exact_one_page_capture_validates_offline",
        "test_exact_prior_repository_object_identities",
        "test_hard_linked_member_fails_closed",
        "test_isolated_cli_validates_exact_capture",
        "test_network_audit_guard_rejects_socket_creation",
        "test_same_exact_capture_produces_byte_identical_diagnostics",
        "test_symlinked_member_fails_closed",
        "test_two_page_capture_validates_exact_pagination",
        "test_validation_does_not_modify_repository_or_capture",
        "test_validator_source_is_separate_and_network_free",
    }
)
_AUTHORITATIVE_PYTEST_ENVIRONMENT_KEYS = (
    "PYTEST_ADDOPTS",
    "PYTEST_CURRENT_TEST",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
    "PYTEST_PLUGINS",
)
_AUTHORITATIVE_LAUNCH_PROBE_CHILD = (
    "PULSEMECH_POST_RUN_OFFLINE_VALIDATOR_LAUNCH_PROBE_CHILD"
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
                "authoritative_offline_validator_collection_mismatch: "
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
                "authoritative offline-validator execution failed",
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
        "authoritative_offline_validator_session_not_completed: "
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
    def remaining(self) -> int:
        return len(self._values) - self._index


class ScriptedTransport:
    def __init__(self, script: Sequence[tuple[str, Any]]) -> None:
        self._script = list(script)
        self._index = 0
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
        if isinstance(response, BaseException):
            raise response
        return response

    @property
    def remaining(self) -> int:
        return len(self._script) - self._index


def _load_module(path: Path, *, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def capture() -> Any:
    return _load_module(
        CAPTURE_TOOL_PATH,
        name="pulsemech_post_run_capture_for_validator_regression",
    )


@pytest.fixture(scope="module")
def validator() -> Any:
    return _load_module(
        VALIDATOR_PATH,
        name="pulsemech_post_run_offline_validator_under_test",
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
    status: str = "completed",
    conclusion: str = "success",
    started_at: str | None = "2026-07-13T12:27:00Z",
    completed_at: str | None = "2026-07-13T12:27:01Z",
) -> dict[str, Any]:
    return {
        "number": number,
        "name": f"fixture-step-{number}",
        "status": status,
        "conclusion": conclusion,
        "started_at": started_at,
        "completed_at": completed_at,
    }


def _job_document(
    capture: Any,
    job_id: int,
    *,
    steps: Sequence[dict[str, Any]] | None = None,
    status: str = "completed",
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
        "status": status,
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
    etag: str = '"fixture-etag"',
    request_id: str = "fixture-request-id",
) -> tuple[tuple[str, str], ...]:
    headers: list[tuple[str, str]] = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("ETag", etag),
    ]
    if link is not None:
        headers.append(("Link", link))
    headers.extend(
        [
            ("X-GitHub-Request-Id", request_id),
            ("Content-Length", str(len(body))),
            ("Date", "fixture-transport-date-not-recorded"),
        ]
    )
    return tuple(headers)


def _transport_response(
    capture: Any,
    body: bytes,
    *,
    link: str | None = None,
    etag: str = '"fixture-etag"',
    request_id: str = "fixture-request-id",
) -> Any:
    return capture.TransportResponse(
        status=200,
        headers=_headers_for_body(
            body,
            link=link,
            etag=etag,
            request_id=request_id,
        ),
        body=body,
        clean_eof=True,
        redirect_observed=False,
    )


def _scripted_fixture(
    capture: Any,
    *,
    pages: Sequence[tuple[Mapping[str, Any], str | None]] | None = None,
) -> tuple[ScriptedTransport, SequenceClock]:
    run_body = _json_body(_run_document(capture))
    page_values = (
        list(pages)
        if pages is not None
        else [
            (
                _jobs_document(
                    capture,
                    list(range(86815582001, 86815582009)),
                ),
                None,
            )
        ]
    )
    script: list[tuple[str, Any]] = [
        (
            capture.RUN_REQUEST_PATH,
            _transport_response(
                capture,
                run_body,
                etag='"run-etag"',
                request_id="fixture-run-request",
            ),
        )
    ]
    for page_number, (page_document, link) in enumerate(page_values, start=1):
        body = _json_body(page_document)
        script.append(
            (
                f"{capture.JOBS_REQUEST_PATH}?per_page=100&page={page_number}",
                _transport_response(
                    capture,
                    body,
                    link=link,
                    etag=f'"jobs-page-{page_number}-etag"',
                    request_id=f"fixture-jobs-page-{page_number}-request",
                ),
            )
        )
    values = [
        CAPTURE_BASE + dt.timedelta(microseconds=index)
        for index in range(2 * len(script))
    ]
    return ScriptedTransport(script), SequenceClock(values)


@pytest.fixture(scope="module")
def base_capture_root(
    tmp_path_factory: pytest.TempPathFactory,
    capture: Any,
) -> Path:
    root = tmp_path_factory.mktemp("post-run-offline-validator") / "one-page"
    transport, clock = _scripted_fixture(capture)
    result = capture.capture_with_injected_dependencies_for_test(
        repository_root=ROOT,
        output_directory=root,
        token=TOKEN,
        transport=transport,
        clock=clock,
    )
    assert result.record_status == "example"
    assert result.page_count == 1
    assert result.job_count == 8
    assert result.step_record_count == 8
    assert result.authority_effect == "none"
    assert transport.remaining == 0
    assert clock.remaining == 0
    return root


@pytest.fixture(scope="module")
def base_two_page_capture_root(
    tmp_path_factory: pytest.TempPathFactory,
    capture: Any,
) -> Path:
    root = tmp_path_factory.mktemp("post-run-offline-validator") / "two-page"
    first_ids = list(range(86815583001, 86815583101))
    second_ids = [86815583101]
    next_url = (
        "https://api.github.com"
        + capture.JOBS_REQUEST_PATH
        + "?per_page=100&page=2"
    )
    pages = [
        (_jobs_document(capture, first_ids, total_count=101), f'<{next_url}>; rel="next"'),
        (_jobs_document(capture, second_ids, total_count=101), None),
    ]
    transport, clock = _scripted_fixture(capture, pages=pages)
    result = capture.capture_with_injected_dependencies_for_test(
        repository_root=ROOT,
        output_directory=root,
        token=TOKEN,
        transport=transport,
        clock=clock,
    )
    assert result.page_count == 2
    assert result.job_count == 101
    assert result.step_record_count == 101
    assert transport.remaining == 0
    assert clock.remaining == 0
    return root


def _copy_capture(source: Path, tmp_path: Path, name: str = "capture") -> Path:
    target = tmp_path / name
    shutil.copytree(source, target)
    return target


def _assert_expected_capture_modes(capture_root: Path) -> None:
    assert stat.S_IMODE(capture_root.stat().st_mode) == 0o700
    assert stat.S_IMODE((capture_root / "raw").stat().st_mode) == 0o700
    assert stat.S_IMODE((capture_root / "metadata").stat().st_mode) == 0o700
    for path in capture_root.rglob("*"):
        if path.is_file():
            assert stat.S_IMODE(path.stat().st_mode) == 0o600


def _manifest_path(capture_root: Path) -> Path:
    return capture_root / EXAMPLE_MANIFEST_NAME


def _load_manifest(capture_root: Path) -> dict[str, Any]:
    value = json.loads(_manifest_path(capture_root).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_manifest(capture_root: Path, manifest: Mapping[str, Any]) -> None:
    _manifest_path(capture_root).write_bytes(_canonical_json_bytes(manifest))


def _update_member_identity(member: dict[str, Any], payload: bytes) -> None:
    member.update(
        {
            "size_bytes": len(payload),
            "sha256": _sha256(payload),
            "git_blob_sha1": _git_blob_sha1(payload),
            "utf8_bom_present": payload.startswith(b"\xef\xbb\xbf"),
            "cr_count": payload.count(b"\r"),
            "lf_count": payload.count(b"\n"),
            "final_byte_hex": f"{payload[-1]:02x}",
            "trailing_newline_present": payload.endswith(b"\n"),
        }
    )


def _exchange_wrapper(
    manifest: dict[str, Any],
    *,
    kind: str,
    page_number: int = 1,
) -> dict[str, Any]:
    if kind == "run":
        return manifest["run_attempt_exchange"]
    if kind == "jobs":
        return manifest["jobs_page_exchanges"][page_number - 1]
    raise AssertionError(f"unknown exchange kind: {kind}")


def _rebind_exchange(
    capture_root: Path,
    manifest: dict[str, Any],
    *,
    kind: str,
    page_number: int = 1,
) -> None:
    wrapper = _exchange_wrapper(manifest, kind=kind, page_number=page_number)
    record = wrapper["record"]
    body_member = record["response"]["body_member"]
    body_path = capture_root / body_member["path"]
    body_payload = body_path.read_bytes()
    _update_member_identity(body_member, body_payload)

    metadata_member = wrapper["metadata_member"]
    metadata_payload = _canonical_json_bytes(record)
    metadata_path = capture_root / metadata_member["path"]
    metadata_path.write_bytes(metadata_payload)
    _update_member_identity(metadata_member, metadata_payload)
    metadata_member["canonicalization"] = "json-sort-keys-utf8-newline"
    metadata_member["canonical_reserialization_matches"] = True
    metadata_member["media_type"] = "application/json"
    wrapper["metadata_record_canonical_bytes_equal_record"] = True
    _write_manifest(capture_root, manifest)


def _replace_raw_json(
    capture_root: Path,
    manifest: dict[str, Any],
    *,
    kind: str,
    mutate: Callable[[dict[str, Any]], None],
    page_number: int = 1,
    compact: bool = False,
    bom: bool = False,
    crlf: bool = False,
) -> None:
    wrapper = _exchange_wrapper(manifest, kind=kind, page_number=page_number)
    body_path = capture_root / wrapper["record"]["response"]["body_member"]["path"]
    payload = body_path.read_bytes()
    if payload.startswith(b"\xef\xbb\xbf"):
        payload = payload[3:]
    value = json.loads(payload.decode("utf-8"))
    assert isinstance(value, dict)
    mutate(value)
    if compact:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8") + b"\n"
    else:
        rendered = _json_body(value)
    if crlf:
        rendered = rendered.replace(b"\n", b"\r\n")
    if bom:
        rendered = b"\xef\xbb\xbf" + rendered
    body_path.write_bytes(rendered)
    _rebind_exchange(
        capture_root,
        manifest,
        kind=kind,
        page_number=page_number,
    )


def _rewrite_exchange_record(
    capture_root: Path,
    manifest: dict[str, Any],
    *,
    kind: str,
    mutate: Callable[[dict[str, Any]], None],
    page_number: int = 1,
) -> None:
    wrapper = _exchange_wrapper(manifest, kind=kind, page_number=page_number)
    mutate(wrapper["record"])
    _rebind_exchange(
        capture_root,
        manifest,
        kind=kind,
        page_number=page_number,
    )


def _validate_without_process_audit(
    validator: Any,
    *,
    repository_root: Path,
    capture_root: Path,
) -> Any:
    original = validator._install_network_audit_guard
    validator._install_network_audit_guard = lambda: None
    try:
        return validator.validate_capture(
            repository_root=repository_root,
            capture_root=capture_root,
        )
    finally:
        validator._install_network_audit_guard = original


def _assert_rejected(
    validator: Any,
    *,
    capture_root: Path,
    error_code: str,
    stage: str | None = None,
    member_path: str | None | object = ...,
    repository_root: Path = ROOT,
) -> Any:
    with pytest.raises(validator.ValidationError) as captured:
        _validate_without_process_audit(
            validator,
            repository_root=repository_root,
            capture_root=capture_root,
        )
    error = captured.value
    assert error.error_code == error_code
    if stage is not None:
        assert error.stage == stage
    if member_path is not ...:
        assert error.member_path == member_path
    return error


def _subprocess_environment() -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "PYTHONHOME",
            "PYTHONPATH",
            "PYTHONSTARTUP",
            "PYTHONINSPECT",
            "PYTEST_ADDOPTS",
            "PYTEST_PLUGINS",
            "PYTEST_CURRENT_TEST",
        }
    }
    environment.update(
        {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONHASHSEED": "0",
        }
    )
    return environment


def _run_validator_cli(
    capture_root: Path,
    *,
    isolated: bool,
    extra_arguments: Sequence[str] = (),
    repository_root: Path = ROOT,
) -> subprocess.CompletedProcess[bytes]:
    command = [sys.executable]
    if isolated:
        command.append("-I")
    command.extend(
        [
            str(VALIDATOR_PATH),
            "--repository-root",
            str(repository_root),
            "--capture-root",
            str(capture_root),
            *extra_arguments,
        ]
    )
    return subprocess.run(
        command,
        cwd=ROOT,
        env=_subprocess_environment(),
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )


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


@pytest.mark.parametrize(
    ("path", "expected_size", "expected_sha256", "expected_blob"),
    EXPECTED_SOURCE_IDENTITIES,
)
def test_exact_prior_repository_object_identities(
    path: Path,
    expected_size: int,
    expected_sha256: str,
    expected_blob: str,
) -> None:
    payload = path.read_bytes()
    assert len(payload) == expected_size
    assert _sha256(payload) == expected_sha256
    assert _git_blob_sha1(payload) == expected_blob
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert payload.endswith(b"\n")


def test_validator_source_is_separate_and_network_free() -> None:
    source = VALIDATOR_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    assert not any(
        name == "capture_pulsemech_compute_post_run_producer_input_v0"
        or name.startswith("capture_pulsemech_compute_post_run_producer_input_v0.")
        for name in imported
    )
    assert "http.client" not in imported
    assert "urllib.request" not in imported
    assert "requests" not in imported
    assert "socket" not in imported
    assert "_install_network_audit_guard" in source
    assert "network_access_forbidden" in source
    assert "offline_validator_network_access" in source
    assert "capture_tool_verdict_trusted" in source
    assert "EXPECTED_CAPTURE_DIRECTORY_MODE = 0o700" in source
    assert "EXPECTED_CAPTURE_FILE_MODE = 0o600" in source
    assert "capture_root_mode_mismatch" in source
    assert "capture_directory_mode_mismatch" in source
    assert "capture_member_mode_mismatch" in source


def test_exact_one_page_capture_validates_offline(
    validator: Any,
    base_capture_root: Path,
) -> None:
    _assert_expected_capture_modes(base_capture_root)
    result = _validate_without_process_audit(
        validator,
        repository_root=ROOT,
        capture_root=base_capture_root,
    )
    assert result.record_status == "example"
    assert result.manifest_file_name == EXAMPLE_MANIFEST_NAME
    assert result.page_count == 1
    assert result.job_count == 8
    assert result.step_record_count == 8
    assert result.authority_effect == "none"
    expected_digest = _sha256(_manifest_path(base_capture_root).read_bytes())
    assert result.manifest_sha256 == expected_digest
    diagnostic = validator._success_diagnostic(result)
    assert diagnostic == _canonical_json_bytes(json.loads(diagnostic))
    parsed = json.loads(diagnostic)
    assert parsed["result"] == "validated_offline"
    assert parsed["ok"] is True
    assert parsed["authority_effect"] == "none"


def test_same_exact_capture_produces_byte_identical_diagnostics(
    validator: Any,
    base_capture_root: Path,
) -> None:
    first = _validate_without_process_audit(
        validator,
        repository_root=ROOT,
        capture_root=base_capture_root,
    )
    second = _validate_without_process_audit(
        validator,
        repository_root=ROOT,
        capture_root=base_capture_root,
    )
    assert first == second
    assert validator._success_diagnostic(first) == validator._success_diagnostic(second)


def test_two_page_capture_validates_exact_pagination(
    validator: Any,
    base_two_page_capture_root: Path,
) -> None:
    result = _validate_without_process_audit(
        validator,
        repository_root=ROOT,
        capture_root=base_two_page_capture_root,
    )
    assert result.page_count == 2
    assert result.job_count == 101
    assert result.step_record_count == 101
    assert result.authority_effect == "none"


def test_raw_response_bom_and_crlf_are_exact_not_canonicalized(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _replace_raw_json(
        root,
        manifest,
        kind="run",
        mutate=lambda value: None,
        bom=True,
        crlf=True,
    )
    result = _validate_without_process_audit(
        validator,
        repository_root=ROOT,
        capture_root=root,
    )
    assert result.job_count == 8
    rebound = _load_manifest(root)["run_attempt_exchange"]["record"]["response"]["body_member"]
    assert rebound["utf8_bom_present"] is True
    assert rebound["cr_count"] > 0
    assert rebound["lf_count"] > 0
    assert rebound["exact_bytes_preserved"] is True
    assert rebound["json_normalized"] is False


def test_compact_raw_jobs_json_is_accepted_when_exactly_rebound(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _replace_raw_json(
        root,
        manifest,
        kind="jobs",
        mutate=lambda value: None,
        compact=True,
    )
    result = _validate_without_process_audit(
        validator,
        repository_root=ROOT,
        capture_root=root,
    )
    assert result.job_count == 8
    assert result.step_record_count == 8


def test_cli_requires_isolated_python(base_capture_root: Path) -> None:
    completed = _run_validator_cli(base_capture_root, isolated=False)
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert completed.stderr == (
        b'{"authority_effect":"none",'
        b'"error_code":"isolated_python_runtime_required",'
        b'"member_path":null,'
        b'"ok":false,'
        b'"stage":"runtime",'
        b'"tool":"check_pulsemech_compute_post_run_producer_input_capture_v0",'
        b'"tool_version":"0.1.0"}\n'
    )


def test_isolated_cli_validates_exact_capture(
    validator: Any,
    base_capture_root: Path,
) -> None:
    completed = _run_validator_cli(base_capture_root, isolated=True)
    assert completed.returncode == 0
    assert completed.stderr == b""
    parsed = json.loads(completed.stdout)
    assert completed.stdout == _canonical_json_bytes(parsed)
    assert parsed["ok"] is True
    assert parsed["result"] == "validated_offline"
    assert parsed["record_status"] == "example"
    assert parsed["page_count"] == 1
    assert parsed["job_count"] == 8
    assert parsed["step_record_count"] == 8
    assert parsed["authority_effect"] == "none"
    in_process = _validate_without_process_audit(
        validator,
        repository_root=ROOT,
        capture_root=base_capture_root,
    )
    assert completed.stdout == validator._success_diagnostic(in_process)


def test_invalid_cli_argument_never_echoes_secret(base_capture_root: Path) -> None:
    secret = "ghp_" + ("Z" * 36)
    completed = _run_validator_cli(
        base_capture_root,
        isolated=True,
        extra_arguments=("--unexpected", secret),
    )
    assert completed.returncode == 2
    assert completed.stdout == b""
    assert secret.encode("ascii") not in completed.stderr
    parsed = json.loads(completed.stderr)
    assert parsed == {
        "authority_effect": "none",
        "error_code": "command_line_invalid",
        "member_path": None,
        "ok": False,
        "stage": "runtime",
        "tool": "check_pulsemech_compute_post_run_producer_input_capture_v0",
        "tool_version": "0.1.0",
    }


def test_network_audit_guard_rejects_socket_creation() -> None:
    code = f"""
import importlib.util
import socket
import sys
from pathlib import Path
path = Path({str(VALIDATOR_PATH)!r})
spec = importlib.util.spec_from_file_location('validator_guard_probe', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module._install_network_audit_guard()
try:
    socket.socket()
except module.ValidationError as exc:
    assert exc.error_code == 'network_access_forbidden'
    assert exc.stage == 'runtime'
    sys.stdout.write(exc.error_code + '\\n')
    raise SystemExit(0)
raise SystemExit(9)
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=ROOT,
        env=_subprocess_environment(),
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert completed.returncode == 0
    assert completed.stdout == b"network_access_forbidden\n"
    assert completed.stderr == b""


def test_repository_root_without_git_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    repository = tmp_path / "not-a-repository"
    repository.mkdir()
    _assert_rejected(
        validator,
        capture_root=base_capture_root,
        repository_root=repository,
        error_code="repository_git_directory_unavailable",
        stage="repository_binding",
    )


def test_missing_manifest_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    _manifest_path(root).unlink()
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="capture_manifest_count_invalid",
        stage="capture_root",
    )



CAPTURE_MODE_MUTATIONS: tuple[
    tuple[str, str | None, int, str, str | None], ...
] = (
    (
        "capture-root-0755",
        None,
        0o755,
        "capture_root_mode_mismatch",
        None,
    ),
    (
        "raw-directory-0755",
        "raw",
        0o755,
        "capture_directory_mode_mismatch",
        "raw",
    ),
    (
        "metadata-directory-0755",
        "metadata",
        0o755,
        "capture_directory_mode_mismatch",
        "metadata",
    ),
    (
        "manifest-0644",
        EXAMPLE_MANIFEST_NAME,
        0o644,
        "capture_member_mode_mismatch",
        EXAMPLE_MANIFEST_NAME,
    ),
    (
        "raw-response-0644",
        RUN_BODY_PATH,
        0o644,
        "capture_member_mode_mismatch",
        RUN_BODY_PATH,
    ),
    (
        "exchange-metadata-0644",
        RUN_METADATA_PATH,
        0o644,
        "capture_member_mode_mismatch",
        RUN_METADATA_PATH,
    ),
)


@pytest.mark.parametrize(
    ("case_name", "relative_path", "mode", "error_code", "member_path"),
    CAPTURE_MODE_MUTATIONS,
    ids=[case[0] for case in CAPTURE_MODE_MUTATIONS],
)
def test_capture_permission_mutations_fail_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
    case_name: str,
    relative_path: str | None,
    mode: int,
    error_code: str,
    member_path: str | None,
) -> None:
    del case_name
    root = _copy_capture(base_capture_root, tmp_path)
    target = root if relative_path is None else root / relative_path
    expected_mode = 0o700 if target.is_dir() else 0o600
    target.chmod(mode)
    assert stat.S_IMODE(target.stat().st_mode) == mode
    try:
        _assert_rejected(
            validator,
            capture_root=root,
            error_code=error_code,
            stage="capture_root",
            member_path=member_path,
        )
    finally:
        target.chmod(expected_mode)
    _assert_expected_capture_modes(root)


def test_undeclared_root_member_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    (root / "undeclared.json").write_bytes(b"{}\n")
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="undeclared_extra_member",
        stage="capture_root",
    )


def test_symlinked_member_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    target = tmp_path / "outside.json"
    target.write_bytes((root / RUN_BODY_PATH).read_bytes())
    (root / RUN_BODY_PATH).unlink()
    (root / RUN_BODY_PATH).symlink_to(target)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="symlinked_member",
        stage="capture_root",
        member_path=RUN_BODY_PATH,
    )


def test_hard_linked_member_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    member = root / RUN_BODY_PATH
    outside = tmp_path / "outside-hardlink.json"
    outside.write_bytes(member.read_bytes())
    member.unlink()
    os.link(outside, member)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="hard_linked_member",
        stage="capture_root",
        member_path=RUN_BODY_PATH,
    )


def test_non_regular_fifo_member_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("mkfifo unavailable")
    root = _copy_capture(base_capture_root, tmp_path)
    member = root / RUN_BODY_PATH
    member.unlink()
    os.mkfifo(member, 0o600)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="non_regular_member",
        stage="capture_root",
        member_path=RUN_BODY_PATH,
    )


def test_noncanonical_manifest_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    path = _manifest_path(root)
    payload = path.read_bytes()
    path.write_bytes(payload[:-1] + b" \n")
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="manifest_canonicalization_failure",
        stage="manifest",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_manifest_bom_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    path = _manifest_path(root)
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="utf8_bom_forbidden",
        stage="manifest",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_manifest_duplicate_key_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    path = _manifest_path(root)
    payload = path.read_bytes()
    assert payload.startswith(b"{")
    path.write_bytes(b'{"ok":true,' + payload[1:])
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="invalid_json",
        stage="manifest",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_manifest_top_level_array_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    _manifest_path(root).write_bytes(b"[]\n")
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="top_level_not_object",
        stage="manifest",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_unbound_raw_response_byte_mutation_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    path = root / RUN_BODY_PATH
    payload = bytearray(path.read_bytes())
    payload[-2] = 0x20 if payload[-2] != 0x20 else 0x09
    path.write_bytes(bytes(payload))
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="raw_response_identity_mismatch",
        stage="member_identity",
        member_path=RUN_BODY_PATH,
    )


def test_unbound_exchange_metadata_mutation_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    path = root / RUN_METADATA_PATH
    path.write_bytes(path.read_bytes() + b" ")
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="exchange_metadata_canonical_bytes_mismatch",
        stage="exchange_metadata",
        member_path=RUN_METADATA_PATH,
    )


def test_exchange_metadata_bom_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    path = root / RUN_METADATA_PATH
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="exchange_metadata_canonical_bytes_mismatch",
        stage="exchange_metadata",
        member_path=RUN_METADATA_PATH,
    )


def test_rebound_invalid_utf8_raw_body_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    (root / RUN_BODY_PATH).write_bytes(b"{\xff}\n")
    _rebind_exchange(root, manifest, kind="run")
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="invalid_utf8",
        stage="raw_response",
        member_path=RUN_BODY_PATH,
    )


def test_rebound_raw_top_level_array_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    (root / RUN_BODY_PATH).write_bytes(b"[]\n")
    _rebind_exchange(root, manifest, kind="run")
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="top_level_not_object",
        stage="raw_response",
        member_path=RUN_BODY_PATH,
    )


def test_rebound_raw_duplicate_key_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    (root / RUN_BODY_PATH).write_bytes(b'{"id":1,"id":2}\n')
    _rebind_exchange(root, manifest, kind="run")
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="invalid_json",
        stage="raw_response",
        member_path=RUN_BODY_PATH,
    )


def test_secret_material_in_rebound_raw_body_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    secret = "ghp_" + ("Q" * 36)
    _replace_raw_json(
        root,
        manifest,
        kind="run",
        mutate=lambda value: value.__setitem__("secret_probe", secret),
    )
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="secret_value_in_output",
        stage="privacy",
        member_path=RUN_BODY_PATH,
    )


RUN_MUTATIONS: tuple[
    tuple[str, Callable[[dict[str, Any]], None], str], ...
] = (
    ("run_id", lambda value: value.__setitem__("id", 1), "wrong_run_id"),
    (
        "run_number",
        lambda value: value.__setitem__("run_number", 1),
        "wrong_run_number",
    ),
    (
        "run_attempt",
        lambda value: value.__setitem__("run_attempt", 2),
        "wrong_run_attempt",
    ),
    (
        "workflow_name",
        lambda value: value.__setitem__("name", "Other CI"),
        "wrong_workflow_name",
    ),
    (
        "workflow_id",
        lambda value: value.__setitem__("workflow_id", 1),
        "wrong_workflow_id",
    ),
    (
        "workflow_path",
        lambda value: value.__setitem__("path", ".github/workflows/other.yml"),
        "wrong_workflow_path",
    ),
    (
        "event",
        lambda value: value.__setitem__("event", "push"),
        "wrong_event",
    ),
    (
        "head_branch",
        lambda value: value.__setitem__("head_branch", "other"),
        "wrong_head_branch",
    ),
    (
        "source_commit",
        lambda value: value.__setitem__("head_sha", "0" * 40),
        "wrong_source_commit",
    ),
    (
        "status",
        lambda value: value.__setitem__("status", "in_progress"),
        "non_completed_run",
    ),
    (
        "conclusion",
        lambda value: value.__setitem__("conclusion", "failure"),
        "non_success_reference_run",
    ),
    (
        "repository_id",
        lambda value: value["repository"].__setitem__("id", 1),
        "wrong_repository_identity",
    ),
    (
        "head_repository",
        lambda value: value["head_repository"].__setitem__(
            "full_name", "other/repository"
        ),
        "wrong_head_repository_identity",
    ),
)


@pytest.mark.parametrize(
    ("case_name", "mutate", "error_code"),
    RUN_MUTATIONS,
    ids=[case[0] for case in RUN_MUTATIONS],
)
def test_rebound_run_subject_mutations_fail_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
    case_name: str,
    mutate: Callable[[dict[str, Any]], None],
    error_code: str,
) -> None:
    del case_name
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _replace_raw_json(root, manifest, kind="run", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code=error_code,
        stage="run_subject",
        member_path=RUN_BODY_PATH,
    )


def test_capture_before_subject_completion_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)

    def mutate(record: dict[str, Any]) -> None:
        record["response"]["timing"]["capture_started_utc"] = (
            "2026-07-13T12:30:00Z"
        )
        record["response"]["timing"]["response_received_utc"] = (
            "2026-07-13T12:30:01Z"
        )

    _rewrite_exchange_record(root, manifest, kind="run", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="capture_started_before_subject_run_completed",
        stage="temporal",
        member_path=RUN_BODY_PATH,
    )


JOB_MUTATIONS: tuple[
    tuple[str, Callable[[dict[str, Any]], None], str], ...
] = (
    (
        "duplicate_job_id",
        lambda value: value["jobs"][1].__setitem__("id", value["jobs"][0]["id"]),
        "duplicate_job_id",
    ),
    (
        "job_run_id",
        lambda value: value["jobs"][0].__setitem__("run_id", 1),
        "job_run_id_mismatch",
    ),
    (
        "job_run_attempt",
        lambda value: value["jobs"][0].__setitem__("run_attempt", 2),
        "job_run_attempt_mismatch",
    ),
    (
        "job_workflow_name",
        lambda value: value["jobs"][0].__setitem__("workflow_name", "Other CI"),
        "job_workflow_name_mismatch",
    ),
    (
        "job_head_sha",
        lambda value: value["jobs"][0].__setitem__("head_sha", "0" * 40),
        "job_head_sha_mismatch",
    ),
    (
        "job_status",
        lambda value: value["jobs"][0].__setitem__("status", "in_progress"),
        "job_0_status_invalid",
    ),
    (
        "job_conclusion",
        lambda value: value["jobs"][0].__setitem__("conclusion", "failure"),
        "job_0_conclusion_invalid",
    ),
    (
        "duplicate_step_number",
        lambda value: value["jobs"][0].__setitem__(
            "steps", [_step_document(1), _step_document(1)]
        ),
        "duplicate_step_number",
    ),
    (
        "step_order",
        lambda value: value["jobs"][0].__setitem__(
            "steps", [_step_document(2), _step_document(1)]
        ),
        "step_order_invalid",
    ),
    (
        "step_status",
        lambda value: value["jobs"][0]["steps"][0].__setitem__(
            "status", "in_progress"
        ),
        "job_0_step_0_status_invalid",
    ),
    (
        "step_conclusion",
        lambda value: value["jobs"][0]["steps"][0].__setitem__(
            "conclusion", "failure"
        ),
        "job_0_step_0_conclusion_invalid",
    ),
    (
        "step_timestamp_order",
        lambda value: value["jobs"][0]["steps"][0].update(
            {
                "started_at": "2026-07-13T12:27:02Z",
                "completed_at": "2026-07-13T12:27:01Z",
            }
        ),
        "job_0_step_0_timestamp_order_invalid",
    ),
)


@pytest.mark.parametrize(
    ("case_name", "mutate", "error_code"),
    JOB_MUTATIONS,
    ids=[case[0] for case in JOB_MUTATIONS],
)
def test_rebound_job_and_step_mutations_fail_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
    case_name: str,
    mutate: Callable[[dict[str, Any]], None],
    error_code: str,
) -> None:
    del case_name
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _replace_raw_json(root, manifest, kind="jobs", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code=error_code,
        stage="jobs_binding",
        member_path=JOBS_BODY_PATH,
    )



@pytest.mark.parametrize(
    ("component", "limit"), ((0, 24), (1, 60), (2, 60)),
    ids=("hour", "minute", "second"),
)
def test_validator_time_ranges_reject_before_permissive_parser(
    validator: Any, monkeypatch: pytest.MonkeyPatch, component: int, limit: int,
) -> None:
    parser_calls: list[str] = []
    sentinel = dt.datetime(2026, 7, 14, tzinfo=dt.timezone.utc)

    class PermissiveDatetime:
        @staticmethod
        def fromisoformat(text: str) -> dt.datetime:
            parser_calls.append(text)
            return sentinel

    monkeypatch.setattr(
        validator, "dt",
        SimpleNamespace(datetime=PermissiveDatetime, timedelta=dt.timedelta),
    )
    # Prove the injected parser is active for each valid two-digit value,
    # then require every invalid value to be rejected before reaching it.
    for value in range(100):
        for fraction in ("", ".0"):
            fields = [0, 0, 0]
            fields[component] = value
            text = (
                f"2026-07-13T{fields[0]:02d}:{fields[1]:02d}:"
                f"{fields[2]:02d}{fraction}Z"
            )
            parser_calls.clear()
            if value < limit:
                assert validator._parse_utc(
                    text, error_code="timestamp_invalid", stage="timestamp_test",
                ) is sentinel
                assert parser_calls == [text[:-1] + "+00:00"]
            else:
                with pytest.raises(validator.ValidationError) as failure:
                    validator._parse_utc(
                        text, error_code="timestamp_invalid", stage="timestamp_test",
                    )
                assert failure.value.error_code == "timestamp_invalid"
                assert parser_calls == []



def test_timestamp_calendar_and_valid_boundaries(validator: Any) -> None:
    valid = (
        ("0001-01-01T00:00:00Z", dt.datetime(1, 1, 1, tzinfo=dt.timezone.utc)),
        ("2000-02-29T23:59:59Z", dt.datetime(2000, 2, 29, 23, 59, 59, tzinfo=dt.timezone.utc)),
        ("2024-02-29T12:34:56.1Z", dt.datetime(2024, 2, 29, 12, 34, 56, 100000, tzinfo=dt.timezone.utc)),
        ("2026-07-13T12:27:00.123456789Z", dt.datetime(2026, 7, 13, 12, 27, 0, 123456, tzinfo=dt.timezone.utc)),
        ("9999-12-31T23:59:59.999999Z", dt.datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=dt.timezone.utc)),
    )
    for text, expected in valid:
        assert validator._parse_utc(
            text, error_code="timestamp_invalid", stage="timestamp_test",
        ) == expected
    invalid = (
        "0000-01-01T00:00:00Z", "1900-02-29T00:00:00Z",
        "2026-02-29T00:00:00Z", "2026-04-31T00:00:00Z",
        "2026-00-01T00:00:00Z", "2026-13-01T00:00:00Z",
        "2026-07-00T00:00:00Z", "2026-07-32T00:00:00Z",
        "2026-07-13T24:00:00Z", "2026-07-13T24:00:00.0Z",
        "2026-07-13T12:60:00Z", "2026-07-13T12:27:60Z",
    )
    for text in invalid:
        with pytest.raises(validator.ValidationError) as failure:
            validator._parse_utc(
                text, error_code="timestamp_invalid", stage="timestamp_test",
            )
        assert failure.value.error_code == "timestamp_invalid"
        assert failure.value.stage == "timestamp_test"


@pytest.mark.parametrize(
    ("path", "error_code"),
    (
        (("started_at",), "job_0_started_at_invalid"),
        (("completed_at",), "job_0_completed_at_invalid"),
        (("steps", 0, "started_at"), "job_0_step_0_started_at_invalid"),
        (("steps", 0, "completed_at"), "job_0_step_0_completed_at_invalid"),
    ),
    ids=("job-start", "job-end", "step-start", "step-end"),
)
@pytest.mark.parametrize("conclusion", ("success", "skipped"))
def test_rebound_job_step_time_ranges_fail_closed(
    validator: Any, base_capture_root: Path, tmp_path: Path,
    path: tuple[Any, ...], error_code: str, conclusion: str,
) -> None:
    invalid = (
        "2026-07-13T24:00:00Z", "2026-07-13T24:00:00.0Z",
        "2026-07-13T25:00:00Z", "2026-07-13T12:60:00Z",
        "2026-07-13T12:27:60Z", "2026-02-29T12:27:00Z",
    )
    for index, timestamp in enumerate(invalid):
        root = _copy_capture(base_capture_root, tmp_path, f"bad-time-{index}")
        manifest = _load_manifest(root)

        def mutate(value: dict[str, Any]) -> None:
            job = value["jobs"][0]
            job["conclusion"] = conclusion
            job["steps"][0]["conclusion"] = conclusion
            target = job
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = timestamp

        # Repair the raw-body and metadata identities so the rejection must
        # come from timestamp semantics, not an earlier checksum mismatch.
        _replace_raw_json(root, manifest, kind="jobs", mutate=mutate)
        before = {
            p.relative_to(root): p.read_bytes()
            for p in root.rglob("*") if p.is_file()
        }
        _assert_rejected(
            validator, capture_root=root, error_code=error_code,
            stage="jobs_binding", member_path=JOBS_BODY_PATH,
        )
        after = {
            p.relative_to(root): p.read_bytes()
            for p in root.rglob("*") if p.is_file()
        }
        assert before == after


def test_run_request_record_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _rewrite_exchange_record(
        root,
        manifest,
        kind="run",
        mutate=lambda record: record["request"].__setitem__("method", "POST"),
    )
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="manifest_schema_validation_failed",
        stage="schema",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_jobs_request_query_order_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)

    def mutate(record: dict[str, Any]) -> None:
        record["request"]["query_parameters"].reverse()
        record["request"]["request_target"] = (
            record["request"]["path"] + "?page=1&per_page=100"
        )

    _rewrite_exchange_record(root, manifest, kind="jobs", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="manifest_schema_validation_failed",
        stage="schema",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


RESPONSE_METADATA_MUTATIONS: tuple[
    tuple[str, Callable[[dict[str, Any]], None], str, str], ...
] = (
    (
        "content_type_absent",
        lambda record: record["response"]["selected_headers"]["content_type"].update(
            {"status": "absent", "value": None}
        ),
        "manifest_schema_validation_failed",
        "schema",
    ),
    (
        "wrong_content_type",
        lambda record: record["response"]["selected_headers"]["content_type"].update(
            {"status": "present", "value": "text/plain"}
        ),
        "manifest_schema_validation_failed",
        "schema",
    ),
    (
        "unsupported_encoding",
        lambda record: record["response"]["selected_headers"][
            "content_encoding"
        ].update({"status": "present", "value": "gzip"}),
        "manifest_schema_validation_failed",
        "schema",
    ),
    (
        "non_200_declaration",
        lambda record: record["response"].__setitem__("http_status", 500),
        "manifest_schema_validation_failed",
        "schema",
    ),
    (
        "redirect_declaration",
        lambda record: record["response"].__setitem__("redirect_observed", True),
        "manifest_schema_validation_failed",
        "schema",
    ),
    (
        "truncated_declaration",
        lambda record: record["response"].__setitem__("body_truncated", True),
        "manifest_schema_validation_failed",
        "schema",
    ),
)


@pytest.mark.parametrize(
    ("case_name", "mutate", "error_code", "stage"),
    RESPONSE_METADATA_MUTATIONS,
    ids=[case[0] for case in RESPONSE_METADATA_MUTATIONS],
)
def test_response_metadata_mutations_fail_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
    case_name: str,
    mutate: Callable[[dict[str, Any]], None],
    error_code: str,
    stage: str,
) -> None:
    del case_name
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _rewrite_exchange_record(root, manifest, kind="run", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code=error_code,
        stage=stage,
        member_path=(EXAMPLE_MANIFEST_NAME if stage == "schema" else RUN_METADATA_PATH),
    )


def test_response_received_before_capture_start_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)

    def mutate(record: dict[str, Any]) -> None:
        record["response"]["timing"].update(
            {
                "capture_started_utc": "2026-08-01T18:00:00.000010Z",
                "response_received_utc": "2026-08-01T18:00:00.000009Z",
            }
        )

    _rewrite_exchange_record(root, manifest, kind="run", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="response_received_before_capture_start",
        stage="temporal",
        member_path=RUN_METADATA_PATH,
    )


def test_jobs_exchange_time_order_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)

    def mutate(record: dict[str, Any]) -> None:
        record["response"]["timing"].update(
            {
                "capture_started_utc": "2026-08-01T17:59:59Z",
                "response_received_utc": "2026-08-01T18:00:00Z",
            }
        )

    _rewrite_exchange_record(root, manifest, kind="jobs", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="capture_exchange_time_order_invalid",
        stage="temporal",
        member_path=JOBS_METADATA_PATH,
    )


def test_run_summary_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _rewrite_exchange_record(
        root,
        manifest,
        kind="run",
        mutate=lambda record: record["response"]["summary"].__setitem__(
            "workflow_run_number", 1
        ),
    )
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="run_attempt_summary_mismatch",
        stage="run_subject",
        member_path=RUN_METADATA_PATH,
    )


def test_jobs_summary_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _rewrite_exchange_record(
        root,
        manifest,
        kind="jobs",
        mutate=lambda record: record["response"]["summary"].__setitem__(
            "jobs_on_page", 7
        ),
    )
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="jobs_page_summary_mismatch",
        stage="jobs_binding",
        member_path=JOBS_METADATA_PATH,
    )


def test_exchange_metadata_relation_false_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    manifest["run_attempt_exchange"]["metadata_record_canonical_bytes_equal_record"] = False
    _write_manifest(root, manifest)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="manifest_schema_validation_failed",
        stage="schema",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_final_rel_next_presence_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    next_target = (
        "https://api.github.com/repos/HKati/pulse-release-gates-0.1/"
        "actions/runs/29249887581/attempts/1/jobs?per_page=100&page=2"
    )

    def mutate(record: dict[str, Any]) -> None:
        record["response"]["selected_headers"]["link"] = {
            "status": "present",
            "value": f'<{next_target}>; rel="next"',
        }
        record["pagination_relation"] = {
            "is_final_page": False,
            "link_header_status": "present",
            "next_page_number": 2,
            "next_relation_status": "present",
            "next_request_target": (
                "/repos/HKati/pulse-release-gates-0.1/"
                "actions/runs/29249887581/attempts/1/jobs?per_page=100&page=2"
            ),
            "page_number": 1,
            "relation_source": "selected_link_header",
        }

    _rewrite_exchange_record(root, manifest, kind="jobs", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="final_next_link_still_present",
        stage="pagination",
        member_path=JOBS_METADATA_PATH,
    )


LINK_MUTATIONS: tuple[
    tuple[str, str, str], ...
] = (
    (
        "malformed",
        "<https://api.github.com/incomplete; rel=\"next\"",
        "link_header_syntax_invalid",
    ),
    (
        "cross_host",
        (
            "<https://example.invalid/repos/HKati/pulse-release-gates-0.1/"
            "actions/runs/29249887581/attempts/1/jobs?per_page=100&page=2>; rel=\"next\""
        ),
        "link_next_origin_mismatch",
    ),
    (
        "wrong_query_order",
        (
            "<https://api.github.com/repos/HKati/pulse-release-gates-0.1/"
            "actions/runs/29249887581/attempts/1/jobs?page=2&per_page=100>; rel=\"next\""
        ),
        "link_next_query_mismatch",
    ),
    (
        "wrong_path",
        (
            "<https://api.github.com/repos/HKati/pulse-release-gates-0.1/"
            "actions/runs/29249887581/jobs?per_page=100&page=2>; rel=\"next\""
        ),
        "link_next_path_mismatch",
    ),
)


@pytest.mark.parametrize(
    ("case_name", "link_value", "error_code"),
    LINK_MUTATIONS,
    ids=[case[0] for case in LINK_MUTATIONS],
)
def test_link_header_mutations_fail_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
    case_name: str,
    link_value: str,
    error_code: str,
) -> None:
    del case_name
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)

    def mutate(record: dict[str, Any]) -> None:
        record["response"]["selected_headers"]["link"] = {
            "status": "present",
            "value": link_value,
        }

    _rewrite_exchange_record(root, manifest, kind="jobs", mutate=mutate)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code=error_code,
        stage="pagination",
        member_path=JOBS_METADATA_PATH,
    )


def test_pagination_relation_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _rewrite_exchange_record(
        root,
        manifest,
        kind="jobs",
        mutate=lambda record: record["pagination_relation"].__setitem__(
            "relation_source", "other"
        ),
    )
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="manifest_schema_validation_failed",
        stage="schema",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_reported_job_count_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)

    def mutate_raw(value: dict[str, Any]) -> None:
        value["total_count"] = 9

    _replace_raw_json(root, manifest, kind="jobs", mutate=mutate_raw)
    manifest = _load_manifest(root)
    manifest["jobs_page_exchanges"][0]["record"]["response"]["summary"][
        "reported_total_count"
    ] = 9
    _rebind_exchange(root, manifest, kind="jobs")
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="reported_total_count_mismatch",
        stage="pagination",
    )


def test_second_page_total_count_disagreement_fails_closed(
    validator: Any,
    base_two_page_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_two_page_capture_root, tmp_path)
    manifest = _load_manifest(root)

    def mutate_raw(value: dict[str, Any]) -> None:
        value["total_count"] = 100

    _replace_raw_json(
        root,
        manifest,
        kind="jobs",
        page_number=2,
        mutate=mutate_raw,
    )
    manifest = _load_manifest(root)
    manifest["jobs_page_exchanges"][1]["record"]["response"]["summary"][
        "reported_total_count"
    ] = 100
    _rebind_exchange(root, manifest, kind="jobs", page_number=2)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="page_total_count_disagreement",
        stage="pagination",
        member_path="raw/jobs_page_0002_response.json",
    )


def test_missing_second_jobs_page_fails_closed(
    validator: Any,
    base_two_page_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_two_page_capture_root, tmp_path)
    (root / "raw/jobs_page_0002_response.json").unlink()
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="missing_jobs_page",
        stage="inventory",
        member_path="raw/jobs_page_0002_response.json",
    )


def test_manifest_count_relation_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    manifest["counts"]["reconstructed_step_record_count"] = 7
    _write_manifest(root, manifest)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="manifest_count_relation_mismatch",
        stage="pagination_counts",
    )


def test_manifest_pagination_relation_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    manifest["pagination"]["page_sequence"] = [2]
    _write_manifest(root, manifest)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="manifest_pagination_relation_mismatch",
        stage="pagination_counts",
    )


BOUNDARY_MUTATIONS: tuple[
    tuple[str, Sequence[str], Any], ...
] = (
    ("runtime_observation", ("authority_boundary", "capture_is_runtime_observation"), True),
    (
        "runtime_packet",
        ("authority_boundary", "capture_is_runtime_observation_packet"),
        True,
    ),
    (
        "transition_measurement",
        ("authority_boundary", "capture_is_transition_measurement"),
        True,
    ),
    ("compute_report", ("authority_boundary", "capture_is_compute_report"), True),
    ("gate_result", ("authority_boundary", "capture_is_gate_result"), True),
    ("release_decision", ("authority_boundary", "capture_is_release_decision"), True),
    ("release_authority", ("authority_boundary", "capture_is_release_authority"), True),
    ("active_gate", ("authority_boundary", "activates_compute_gate"), True),
    (
        "same_run_authority",
        ("authority_boundary", "same_run_release_authority_eligible"),
        True,
    ),
    (
        "producer_verdict",
        ("authority_boundary", "producer_verdict_trusted"),
        True,
    ),
    (
        "validator_network",
        ("implementation_boundary", "offline_validator_network_access"),
        "allowed",
    ),
    (
        "capture_import",
        ("implementation_boundary", "offline_validator_imports_capture_implementation"),
        True,
    ),
    (
        "partial_publication",
        ("publication_boundary", "partial_publication_accepted"),
        True,
    ),
    (
        "warning_success",
        ("publication_boundary", "warning_only_success_allowed"),
        True,
    ),
    (
        "best_effort",
        ("publication_boundary", "best_effort_success_allowed"),
        True,
    ),
    (
        "secret_material",
        ("privacy_boundary", "secret_material_included"),
        True,
    ),
    (
        "runtime_packet_content",
        ("content_boundary", "contains_runtime_observation_packet"),
        True,
    ),
    (
        "resource_measurement",
        ("content_boundary", "contains_resource_measurement"),
        True,
    ),
)


def _set_nested(value: dict[str, Any], path: Sequence[str], replacement: Any) -> None:
    cursor: dict[str, Any] = value
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = replacement


@pytest.mark.parametrize(
    ("case_name", "path", "replacement"),
    BOUNDARY_MUTATIONS,
    ids=[case[0] for case in BOUNDARY_MUTATIONS],
)
def test_claim_and_authority_expansion_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
    case_name: str,
    path: Sequence[str],
    replacement: Any,
) -> None:
    del case_name
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    _set_nested(manifest, path, replacement)
    _write_manifest(root, manifest)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="manifest_schema_validation_failed",
        stage="schema",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_schema_binding_digest_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    manifest["contract_bindings"]["manifest_schema"]["sha256"] = "0" * 64
    _write_manifest(root, manifest)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="schema_binding_mismatch",
        stage="repository_binding",
    )


def test_schema_contract_revision_mismatch_fails_closed(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    manifest["contract_bindings"]["normative_contract"]["source_revision"] = "0" * 40
    _write_manifest(root, manifest)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="schema_contract_source_revision_mismatch",
        stage="repository_binding",
    )


def test_unresolved_example_revision_requires_canonical_checked_in_example(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    manifest = _load_manifest(root)
    for binding in manifest["contract_bindings"].values():
        binding["source_revision"] = "0" * 40
    _write_manifest(root, manifest)
    _assert_rejected(
        validator,
        capture_root=root,
        error_code="example_unresolved_revision_not_canonical",
        stage="repository_binding",
        member_path=EXAMPLE_MANIFEST_NAME,
    )


def test_failure_diagnostic_is_canonical_and_deterministic(
    validator: Any,
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    path = root / RUN_BODY_PATH
    path.write_bytes(path.read_bytes() + b" ")
    first = _assert_rejected(
        validator,
        capture_root=root,
        error_code="raw_response_identity_mismatch",
        stage="member_identity",
        member_path=RUN_BODY_PATH,
    )
    second = _assert_rejected(
        validator,
        capture_root=root,
        error_code="raw_response_identity_mismatch",
        stage="member_identity",
        member_path=RUN_BODY_PATH,
    )
    first_bytes = validator._failure_diagnostic(first)
    second_bytes = validator._failure_diagnostic(second)
    assert first_bytes == second_bytes
    assert first_bytes == _canonical_json_bytes(json.loads(first_bytes))
    assert str(ROOT).encode("utf-8") not in first_bytes
    assert TOKEN.encode("ascii") not in first_bytes


def test_cli_failure_diagnostic_is_byte_identical(
    base_capture_root: Path,
    tmp_path: Path,
) -> None:
    root = _copy_capture(base_capture_root, tmp_path)
    path = root / RUN_BODY_PATH
    path.write_bytes(path.read_bytes() + b" ")
    first = _run_validator_cli(root, isolated=True)
    second = _run_validator_cli(root, isolated=True)
    assert first.returncode == second.returncode == 2
    assert first.stdout == second.stdout == b""
    assert first.stderr == second.stderr
    parsed = json.loads(first.stderr)
    assert first.stderr == _canonical_json_bytes(parsed)
    assert parsed["error_code"] == "raw_response_identity_mismatch"
    assert parsed["stage"] == "member_identity"
    assert parsed["member_path"] == RUN_BODY_PATH
    assert parsed["authority_effect"] == "none"
    assert str(ROOT).encode("utf-8") not in first.stderr


def test_validation_does_not_modify_repository_or_capture(
    validator: Any,
    base_capture_root: Path,
) -> None:
    repository_paths = [item[0] for item in EXPECTED_SOURCE_IDENTITIES]
    repository_before = {path: path.read_bytes() for path in repository_paths}
    capture_before = {
        path.relative_to(base_capture_root).as_posix(): (
            path.read_bytes(), stat.S_IMODE(path.stat().st_mode)
        )
        for path in base_capture_root.rglob("*")
        if path.is_file()
    }
    _validate_without_process_audit(
        validator,
        repository_root=ROOT,
        capture_root=base_capture_root,
    )
    repository_after = {path: path.read_bytes() for path in repository_paths}
    capture_after = {
        path.relative_to(base_capture_root).as_posix(): (
            path.read_bytes(), stat.S_IMODE(path.stat().st_mode)
        )
        for path in base_capture_root.rglob("*")
        if path.is_file()
    }
    assert repository_after == repository_before
    assert capture_after == capture_before


# Transport-only probes execute the workflow's actual archive code. Their small
# payloads and oracle are deliberately not presented as semantic capture proof.
# The separate real-validator test below exercises the complete offline boundary.
_TAR_WORKFLOW_PATH = (
    ROOT / ".github" / "workflows"
    / "pulsemech_compute_post_run_producer_input_capture_v0.yml"
)
_TAR_CAPTURE_NAME = "pulsemech-compute-post-run-producer-input-capture-v0"
_TAR_CAPTURE_DIAGNOSTIC = "pulsemech-compute-post-run-capture-diagnostic-v0.json"
_TAR_VALIDATION_DIAGNOSTIC = "pulsemech-compute-post-run-validation-diagnostic-v0.json"
_TAR_MANIFEST_NAME = (
    "pulsemech_compute_post_run_producer_input_capture_manifest_6066_v0.json"
)
_TAR_DIRECTORIES = ("", "raw", "metadata")
_TAR_FILES = (
    "metadata/jobs_page_0001_exchange_v0.json",
    "metadata/run_attempt_exchange_v0.json",
    _TAR_MANIFEST_NAME,
    "raw/jobs_page_0001_response.json",
    "raw/run_attempt_response.json",
)
_TAR_ORACLE_DIAGNOSTIC = b'{"fixture_transport_only":true}\n'


def _tar_workflow_job() -> dict[str, Any]:
    import yaml

    workflow = yaml.safe_load(_TAR_WORKFLOW_PATH.read_text(encoding="utf-8"))
    return workflow["jobs"]["capture-fixed-reference-input"]


def _tar_archive_code() -> Any:
    steps = _tar_workflow_job()["steps"]
    candidates = [step for step in steps if step.get("id") == "archive"]
    assert len(candidates) == 1
    script = candidates[0]["run"]
    marker = "python -I - <<'PY'\n"
    assert script.count(marker) == 1
    prefix, body = script.split(marker, 1)
    for command in (
        "set -euo pipefail", "umask 077", "unset GH_TOKEN",
        "unset PULSEMECH_CAPTURE_WORKFLOW_ID",
    ):
        assert command in prefix.splitlines()
    source, suffix = body.rsplit("\nPY", 1)
    assert not suffix.strip()
    return compile(source, str(_TAR_WORKFLOW_PATH) + ":archive", "exec")


def _tar_fixture(tmp_path: Path) -> tuple[Path, dict[str, bytes]]:
    root = tmp_path / _TAR_CAPTURE_NAME
    root.mkdir(mode=0o700)
    for name in _TAR_DIRECTORIES[1:]:
        (root / name).mkdir(mode=0o700)
    contents = {
        name: b'{"fixture_transport_only":true,"member":'
        + json.dumps(name).encode("ascii") + b'}\n'
        for name in _TAR_FILES
    }
    contents[RUN_BODY_PATH] = b'\xef\xbb\xbf{ "z": 1, "a": "raw" }\r\n'
    contents[JOBS_BODY_PATH] = '{"text":"árvíz","jobs":[]}\n'.encode("utf-8")
    for name, payload in contents.items():
        path = root / name
        path.write_bytes(payload)
        path.chmod(0o600)
    (tmp_path / _TAR_VALIDATION_DIAGNOSTIC).write_bytes(_TAR_ORACLE_DIAGNOSTIC)
    (tmp_path / _TAR_CAPTURE_DIAGNOSTIC).write_bytes(b'{"fixture_only":true}\n')
    return root, contents


def _tar_assert_restoration(root: Path, contents: Mapping[str, bytes]) -> None:
    assert root.is_dir() and not root.is_symlink()
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*")}
    assert actual == set(contents) | {"raw", "metadata"}
    for name in _TAR_DIRECTORIES:
        metadata = (root / name).lstat()
        assert stat.S_ISDIR(metadata.st_mode)
        assert stat.S_IMODE(metadata.st_mode) == 0o700
    for name, payload in contents.items():
        path = root / name
        metadata = path.lstat()
        assert stat.S_ISREG(metadata.st_mode)
        assert stat.S_IMODE(metadata.st_mode) == 0o600
        assert metadata.st_nlink == 1
        assert path.read_bytes() == payload


def _tar_assert_package(path: Path, contents: Mapping[str, bytes]) -> None:
    import tarfile

    expected_dirs = {
        _TAR_CAPTURE_NAME + ("/" + name if name else "")
        for name in _TAR_DIRECTORIES
    }
    expected_files = {_TAR_CAPTURE_NAME + "/" + name for name in contents}
    with tarfile.open(path, "r:") as package:
        members = package.getmembers()
        assert len(members) == len(expected_dirs) + len(expected_files)
        assert {member.name for member in members} == expected_dirs | expected_files
        for member in members:
            assert member.uid == member.gid == 0
            assert member.uname == member.gname == ""
            assert member.mtime == 0
            assert not member.linkname
            if member.name in expected_dirs:
                assert member.isdir() and member.mode == 0o700
            else:
                assert member.isreg() and member.mode == 0o600
                name = member.name[len(_TAR_CAPTURE_NAME) + 1:]
                stream = package.extractfile(member)
                assert stream is not None
                with stream:
                    assert stream.read() == contents[name]


def _tar_transport_oracle(
    contents: Mapping[str, bytes], calls: list[Path],
    *, after_read: Callable[[Path], None] | None = None,
    returncode: int = 0, stdout: bytes = _TAR_ORACLE_DIAGNOSTIC,
) -> Callable[..., subprocess.CompletedProcess[bytes]]:
    def run(command: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert list(command[:5]) == [
            sys.executable, "-I", str(VALIDATOR_PATH), "--repository-root", str(ROOT),
        ]
        assert len(command) == 7 and command[5] == "--capture-root"
        assert kwargs == {
            "stdin": subprocess.DEVNULL, "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL, "check": False,
        }
        assert "GH_TOKEN" not in os.environ
        assert "PULSEMECH_CAPTURE_WORKFLOW_ID" not in os.environ
        restored = Path(command[6])
        assert restored.name == _TAR_CAPTURE_NAME
        assert restored.parent.name.startswith("pulsemech-capture-tar-roundtrip-")
        _tar_assert_restoration(restored, contents)
        calls.append(restored)
        if after_read is not None:
            after_read(restored)
        return subprocess.CompletedProcess(command, returncode, stdout=stdout)
    return run


def _tar_execute_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    *, validator_runner: Callable[..., Any] | None = None,
) -> None:
    code = _tar_archive_code()
    with monkeypatch.context() as patch:
        for key, value in {
            "RUNNER_TEMP": str(tmp_path), "GITHUB_WORKSPACE": str(ROOT),
            "CAPTURE_DIRECTORY_NAME": _TAR_CAPTURE_NAME,
            "CAPTURE_DIAGNOSTIC_NAME": _TAR_CAPTURE_DIAGNOSTIC,
            "VALIDATION_DIAGNOSTIC_NAME": _TAR_VALIDATION_DIAGNOSTIC,
        }.items():
            patch.setenv(key, value)
        patch.delenv("GH_TOKEN", raising=False)
        patch.delenv("PULSEMECH_CAPTURE_WORKFLOW_ID", raising=False)
        if validator_runner is not None:
            patch.setattr(subprocess, "run", validator_runner)
        previous_umask = os.umask(0o077)
        try:
            exec(code, {"__name__": "__main__"})
        finally:
            os.umask(previous_umask)


def _tar_assert_temporary_restoration_removed(tmp_path: Path) -> None:
    assert not list(tmp_path.glob("pulsemech-capture-tar-roundtrip-*"))


def test_tar_upload_requires_successful_roundtrip_and_exact_transport_members() -> None:
    job = _tar_workflow_job()
    steps = job["steps"]
    by_id = {step["id"]: step for step in steps if "id" in step}
    assert sum(step.get("id") == "archive" for step in steps) == 1
    assert sum(step.get("id") == "upload" for step in steps) == 1
    archive, upload = by_id["archive"], by_id["upload"]
    assert steps.index(by_id["validate"]) < steps.index(archive) < steps.index(upload)
    assert archive["shell"] == "bash"
    assert archive.get("if") in (None, "${{ success() }}")
    assert archive.get("continue-on-error", False) is False
    assert upload.get("continue-on-error", False) is False
    assert upload["if"] == "${{ success() && steps.archive.outcome == 'success' }}"
    assert upload["uses"] == (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    )
    options = upload["with"]
    assert options["path"].splitlines() == [
        "${{ runner.temp }}/" + _TAR_CAPTURE_NAME + ".tar",
        "${{ runner.temp }}/" + _TAR_CAPTURE_DIAGNOSTIC,
        "${{ runner.temp }}/" + _TAR_VALIDATION_DIAGNOSTIC,
    ]
    assert options["if-no-files-found"] == "error"
    assert options["overwrite"] is False
    assert options["include-hidden-files"] is False
    assert job["env"]["CAPTURE_DIRECTORY_NAME"] == _TAR_CAPTURE_NAME
    assert job["env"]["CAPTURE_DIAGNOSTIC_NAME"] == _TAR_CAPTURE_DIAGNOSTIC
    assert job["env"]["VALIDATION_DIAGNOSTIC_NAME"] == _TAR_VALIDATION_DIAGNOSTIC
    _tar_archive_code()


def test_tar_roundtrip_preserves_exact_bytes_modes_and_validator_invocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, contents = _tar_fixture(tmp_path)
    calls: list[Path] = []
    _tar_execute_archive(
        tmp_path, monkeypatch, validator_runner=_tar_transport_oracle(contents, calls),
    )
    assert len(calls) == 1 and not calls[0].exists()
    _tar_assert_restoration(root, contents)
    _tar_assert_package(tmp_path / (_TAR_CAPTURE_NAME + ".tar"), contents)
    _tar_assert_temporary_restoration_removed(tmp_path)


def test_tar_archive_is_deterministic_for_same_capture_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    archives: list[bytes] = []
    for index in range(2):
        parent = tmp_path / str(index)
        parent.mkdir()
        root, contents = _tar_fixture(parent)
        for path in (root, *root.rglob("*")):
            os.utime(path, (1000 + index, 1000 + index))
        calls: list[Path] = []
        _tar_execute_archive(
            parent, monkeypatch, validator_runner=_tar_transport_oracle(contents, calls),
        )
        assert len(calls) == 1
        archives.append((parent / (_TAR_CAPTURE_NAME + ".tar")).read_bytes())
    assert archives[0] == archives[1]


@pytest.mark.parametrize("relative_path", (*_TAR_DIRECTORIES, *_TAR_FILES))
def test_tar_archive_rejects_incorrect_source_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative_path: str,
) -> None:
    root, contents = _tar_fixture(tmp_path)
    target = root / relative_path
    mode = 0o755 if relative_path in _TAR_DIRECTORIES else 0o644
    target.chmod(mode)
    calls: list[Path] = []
    with pytest.raises(SystemExit, match="capture_archive_.*mode_or_type_mismatch"):
        _tar_execute_archive(
            tmp_path, monkeypatch, validator_runner=_tar_transport_oracle(contents, calls),
        )
    assert not calls
    assert stat.S_IMODE(target.lstat().st_mode) == mode
    _tar_assert_temporary_restoration_removed(tmp_path)


@pytest.mark.parametrize("case", ("file_symlink", "directory_symlink", "hardlink", "extra"))
def test_tar_archive_rejects_unadmitted_filesystem_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    root, contents = _tar_fixture(tmp_path)
    member = root / RUN_BODY_PATH
    outside = tmp_path / "outside"
    if case == "file_symlink":
        member.rename(outside)
        member.symlink_to(outside)
    elif case == "directory_symlink":
        (root / "raw").rename(outside)
        (root / "raw").symlink_to(outside, target_is_directory=True)
    elif case == "hardlink":
        os.link(member, outside)
    else:
        (root / "extra.json").write_bytes(b"{}\n")
    calls: list[Path] = []
    with pytest.raises(SystemExit, match="capture_archive_"):
        _tar_execute_archive(
            tmp_path, monkeypatch, validator_runner=_tar_transport_oracle(contents, calls),
        )
    assert not calls
    if case == "directory_symlink":
        assert (outside / "run_attempt_response.json").read_bytes() == contents[RUN_BODY_PATH]
    elif case != "extra":
        assert outside.read_bytes() == contents[RUN_BODY_PATH]
    _tar_assert_temporary_restoration_removed(tmp_path)


@pytest.mark.parametrize("case", ("file", "broken_symlink"))
def test_tar_archive_does_not_replace_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str,
) -> None:
    _, contents = _tar_fixture(tmp_path)
    archive = tmp_path / (_TAR_CAPTURE_NAME + ".tar")
    if case == "file":
        archive.write_bytes(b"existing-output")
    else:
        archive.symlink_to(tmp_path / "nonexistent-target")
    before = archive.lstat()
    calls: list[Path] = []
    with pytest.raises(FileExistsError):
        _tar_execute_archive(
            tmp_path, monkeypatch, validator_runner=_tar_transport_oracle(contents, calls),
        )
    after = archive.lstat()
    assert (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
    assert not calls
    if case == "file":
        assert archive.read_bytes() == b"existing-output"
    else:
        assert archive.is_symlink() and not archive.exists()
    _tar_assert_temporary_restoration_removed(tmp_path)


@pytest.mark.parametrize(
    ("returncode", "stdout", "error_code"),
    (
        (2, b"", "capture_archive_offline_validation_failed"),
        (0, b"different-diagnostic\n", "capture_archive_validation_diagnostic_mismatch"),
    ),
)
def test_tar_archive_rejects_failed_or_different_validator_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    returncode: int, stdout: bytes, error_code: str,
) -> None:
    _, contents = _tar_fixture(tmp_path)
    calls: list[Path] = []
    with pytest.raises(SystemExit, match=error_code):
        _tar_execute_archive(
            tmp_path, monkeypatch,
            validator_runner=_tar_transport_oracle(
                contents, calls, returncode=returncode, stdout=stdout,
            ),
        )
    assert len(calls) == 1 and not calls[0].exists()
    _tar_assert_temporary_restoration_removed(tmp_path)


def test_tar_validator_exception_cleans_temporary_restoration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, contents = _tar_fixture(tmp_path)
    calls: list[Path] = []

    def interrupt(_root: Path) -> None:
        raise RuntimeError("fixture-validator-interruption")

    with pytest.raises(RuntimeError, match="fixture-validator-interruption"):
        _tar_execute_archive(
            tmp_path, monkeypatch,
            validator_runner=_tar_transport_oracle(contents, calls, after_read=interrupt),
        )
    assert len(calls) == 1 and not calls[0].exists()
    _tar_assert_temporary_restoration_removed(tmp_path)


def test_tar_archive_path_replacement_is_rejected_without_deleting_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, contents = _tar_fixture(tmp_path)
    archive = tmp_path / (_TAR_CAPTURE_NAME + ".tar")
    calls: list[Path] = []

    def replace(_root: Path) -> None:
        archive.rename(tmp_path / "original-open-archive.tar")
        archive.write_bytes(b"replacement-not-owned-by-archive-step")

    with pytest.raises(SystemExit, match="capture_archive_changed_during_roundtrip"):
        _tar_execute_archive(
            tmp_path, monkeypatch,
            validator_runner=_tar_transport_oracle(contents, calls, after_read=replace),
        )
    assert archive.read_bytes() == b"replacement-not-owned-by-archive-step"
    assert len(calls) == 1
    _tar_assert_temporary_restoration_removed(tmp_path)


def test_tar_payload_survives_outer_zip_permission_normalization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import zipfile

    _, contents = _tar_fixture(tmp_path)
    calls: list[Path] = []
    _tar_execute_archive(
        tmp_path, monkeypatch, validator_runner=_tar_transport_oracle(contents, calls),
    )
    name = _TAR_CAPTURE_NAME + ".tar"
    payload = (tmp_path / name).read_bytes()
    zip_path = tmp_path / "simulated-github-artifact.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as package:
        package.writestr(name, payload)
    downloaded = tmp_path / "downloaded"
    downloaded.mkdir(mode=0o755)
    downloaded.chmod(0o755)
    with zipfile.ZipFile(zip_path) as package:
        assert package.namelist() == [name]
        output = downloaded / name
        output.write_bytes(package.read(name))
        output.chmod(0o644)
    assert stat.S_IMODE(output.stat().st_mode) == 0o644
    assert output.read_bytes() == payload
    _tar_assert_package(output, contents)


def test_tar_roundtrip_with_real_validator_on_synthetic_observed_shape(
    capture: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # This is a temporary synthetic witness of the observed branch, NOT a live
    # GitHub response capture or the canonical #6066 preservation record.
    # No production CLI, token, workflow dispatch, or network transport is used.
    root = tmp_path / _TAR_CAPTURE_NAME
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=_subprocess_environment(), timeout=30,
    ).stdout.decode("ascii").strip()
    sources = capture._load_sources(ROOT, revision=head, include_workflow=True)
    identity = capture.WorkflowExecutionIdentity(
        workflow_id=123456,
        workflow_run_id=987654321,
        workflow_run_attempt=1,
        workflow_run_key=(
            "GITHUB_RUN_ID=987654321|GITHUB_RUN_ATTEMPT=1|"
            "GITHUB_WORKFLOW=PULSEmech compute post-run producer-input capture"
        ),
    )
    transport, clock = _scripted_fixture(capture)
    result = capture._capture_core(
        sources=sources, output_directory=root, token=TOKEN,
        transport=transport, clock=clock, record_status="observed",
        workflow_execution=identity,
    )
    assert result.manifest_file_name == _TAR_MANIFEST_NAME
    assert result.job_count == 8 and result.authority_effect == "none"
    assert transport.remaining == clock.remaining == 0
    original = _run_validator_cli(root, isolated=True)
    assert original.returncode == 0, original.stderr.decode("utf-8", errors="replace")
    assert original.stderr == b""
    diagnostic = json.loads(original.stdout)
    assert diagnostic["ok"] is True and diagnostic["result"] == "validated_offline"
    assert diagnostic["authority_effect"] == "none"
    assert original.stdout == _canonical_json_bytes(diagnostic)
    (tmp_path / _TAR_VALIDATION_DIAGNOSTIC).write_bytes(original.stdout)
    contents = {name: (root / name).read_bytes() for name in _TAR_FILES}
    # No monkeypatch of subprocess.run: the unchanged workflow code launches the
    # actual isolated offline validator against its separate TAR reconstruction.
    _tar_execute_archive(tmp_path, monkeypatch)
    _tar_assert_package(tmp_path / (_TAR_CAPTURE_NAME + ".tar"), contents)
    _tar_assert_restoration(root, contents)
    _tar_assert_temporary_restoration_removed(tmp_path)


if __name__ == "__main__":
    raise SystemExit(_run_authoritative_regression())
