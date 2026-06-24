#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools import (  # noqa: E402
    run_llamaguard_current_evidence_v0 as producer,
)


REPOSITORY = "HKati/pulse-release-gates-0.1"
GIT_SHA = "a" * 40
RUN_KEY = (
    "GITHUB_RUN_ID=12345|"
    "GITHUB_RUN_ATTEMPT=2|"
    "GITHUB_WORKFLOW=PULSE CI"
)
WORKFLOW_REF = (
    "HKati/pulse-release-gates-0.1/"
    ".github/workflows/pulse_ci.yml@refs/heads/main"
)
RELEASE_CANDIDATE = "main"
CREATED_UTC = "2026-06-24T20:00:00Z"
TOKEN_ENV = "TEST_HF_TOKEN"


class _FakeTorch:
    def __init__(self) -> None:
        self.threads: int | None = None
        self.seed: int | None = None

    def set_num_threads(self, value: int) -> None:
        self.threads = value

    def manual_seed(self, value: int) -> None:
        self.seed = value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _copy(repo: Path, relative: str) -> Path:
    source = REPO_ROOT / relative
    assert source.is_file(), f"missing checked-in file: {relative}"

    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _fixture(tmp_path: Path) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()

    tool = _copy(repo, producer.TOOL_REL)
    dataset = _copy(repo, producer.DATASET_REL)
    schema = _copy(repo, producer.MANIFEST_SCHEMA_REL)

    return {
        "repo": repo,
        "tool": tool,
        "dataset": dataset,
        "schema": schema,
        "raw": repo / producer.RAW_REL,
        "manifest": repo / producer.MANIFEST_REL,
        "status": (
            repo
            / "PULSE_safe_pack_v0"
            / "artifacts"
            / "status.json"
        ),
    }


def _arguments(repo: Path, **overrides: str) -> list[str]:
    values = {
        "repository": REPOSITORY,
        "git_sha": GIT_SHA,
        "run_key": RUN_KEY,
        "workflow_ref": WORKFLOW_REF,
        "release_candidate": RELEASE_CANDIDATE,
        "created_utc": CREATED_UTC,
        "model_revision": producer.MODEL_REVISION,
        "token_env": TOKEN_ENV,
    }
    values.update(overrides)

    return [
        "--repo-root",
        str(repo),
        "--repository",
        values["repository"],
        "--git-sha",
        values["git_sha"],
        "--run-key",
        values["run_key"],
        "--workflow-ref",
        values["workflow_ref"],
        "--release-candidate",
        values["release_candidate"],
        "--created-utc",
        values["created_utc"],
        "--model-revision",
        values["model_revision"],
        "--token-env",
        values["token_env"],
        "--torch-threads",
        "2",
        "--max-new-tokens",
        "20",
    ]


def _patch_success_runtime(
    monkeypatch: pytest.MonkeyPatch,
    fixture: dict[str, Path],
) -> _FakeTorch:
    fake_torch = _FakeTorch()

    monkeypatch.setattr(
        producer,
        "__file__",
        str(fixture["tool"]),
    )
    monkeypatch.setattr(
        producer,
        "_git_head",
        lambda _repo: GIT_SHA,
    )
    monkeypatch.setattr(
        producer,
        "_runtime",
        lambda: (
            fake_torch,
            object(),
            object(),
            object(),
        ),
    )
    monkeypatch.setattr(
        producer,
        "_verify_remote_revision",
        lambda _api, _token, revision: revision,
    )
    monkeypatch.setattr(
        producer,
        "_load_model",
        lambda *_args: (object(), object()),
    )
    monkeypatch.setattr(
        producer,
        "_classify_case",
        lambda _torch, _model, _tokenizer, _case, _limit: (
            "safe",
            [],
            "safe",
            12,
            1,
        ),
    )
    monkeypatch.setattr(
        producer,
        "_package_version",
        lambda package: {
            "torch": "2.9.1+cpu",
            "transformers": "4.57.6",
            "huggingface-hub": "0.36.0",
            "tokenizers": "0.22.1",
            "safetensors": "0.7.0",
        }[package],
    )
    monkeypatch.setenv(TOKEN_ENV, "test-token")

    return fake_torch


def test_case_set_preserves_input_and_output_text(
    tmp_path: Path,
) -> None:
    path = tmp_path / "cases.jsonl"
    record = {
        "case_id": "whitespace_case",
        "input": "  prompt with leading space\n",
        "output": "response with trailing space  ",
    }
    path.write_text(
        json.dumps(record, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    cases = producer._load_cases(path)

    assert cases == [record]


@pytest.mark.parametrize(
    "payload, expected",
    [
        (
            '{"case_id":"x","input":"a","input":"b",'
            '"output":"c"}\n',
            "duplicate JSON key",
        ),
        (
            '{"case_id":"x","input":"a","output":"c",'
            '"extra":1e999}\n',
            "non-finite number",
        ),
    ],
)
def test_case_set_rejects_ambiguous_or_nonfinite_json(
    tmp_path: Path,
    payload: str,
    expected: str,
) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(producer.RunnerError, match=expected):
        producer._load_cases(path)


def test_model_output_parser_is_strict() -> None:
    assert producer._parse_model_output("safe") == (
        "safe",
        [],
        "safe",
    )
    assert producer._parse_model_output(
        "unsafe\nS12, S2, S2"
    ) == (
        "unsafe",
        ["S2", "S12"],
        "unsafe\nS12, S2, S2",
    )

    with pytest.raises(
        producer.RunnerError,
        match="safe LlamaGuard output must not contain",
    ):
        producer._parse_model_output("safe\nS1")

    with pytest.raises(
        producer.RunnerError,
        match="at least one S1-S13 category",
    ):
        producer._parse_model_output("unsafe")

    with pytest.raises(
        producer.RunnerError,
        match="unsupported category text",
    ):
        producer._parse_model_output("unsafe\nS1 and other")


def test_mocked_current_run_writes_schema_valid_bound_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    fake_torch = _patch_success_runtime(
        monkeypatch,
        fixture,
    )

    result = producer.main(
        _arguments(fixture["repo"])
    )

    assert result == 0
    assert fake_torch.threads == 2
    assert fake_torch.seed == 0
    assert fixture["raw"].is_file()
    assert fixture["manifest"].is_file()
    assert not fixture["raw"].is_symlink()
    assert not fixture["manifest"].is_symlink()
    assert not fixture["status"].exists()

    records = [
        json.loads(line)
        for line in fixture["raw"]
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    source_cases = [
        json.loads(line)
        for line in fixture["dataset"]
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]

    assert len(records) == len(source_cases) == 6
    assert [item["input"] for item in records] == [
        item["input"] for item in source_cases
    ]
    assert [item["output"] for item in records] == [
        item["output"] for item in source_cases
    ]
    assert all(
        item["llamaguard"] == {
            "label": "safe",
            "categories": [],
            "raw_output": "safe",
        }
        for item in records
    )
    assert all(
        item["run"]["run_key"] == RUN_KEY
        and item["run"]["run_id"] == 12345
        and item["run"]["run_attempt"] == 2
        and item["run"]["workflow_ref"] == WORKFLOW_REF
        and item["run"]["git_sha"] == GIT_SHA
        for item in records
    )

    manifest = json.loads(
        fixture["manifest"].read_text(encoding="utf-8")
    )
    schema = json.loads(
        fixture["schema"].read_text(encoding="utf-8")
    )
    validation_errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(manifest)
    )

    assert validation_errors == []
    assert manifest["schema_version"] == (
        "llamaguard_current_run_evaluator_v0"
    )
    assert manifest["producer"]["path"] == producer.TOOL_REL
    assert manifest["producer"]["sha256"] == _sha256(
        fixture["tool"]
    )
    assert manifest["run"] == {
        "repository": REPOSITORY,
        "git_sha": GIT_SHA,
        "run_key": RUN_KEY,
        "run_id": 12345,
        "run_attempt": 2,
        "workflow_name": "PULSE CI",
        "workflow_ref": WORKFLOW_REF,
        "workflow_path": ".github/workflows/pulse_ci.yml",
        "release_candidate": RELEASE_CANDIDATE,
        "created_utc": CREATED_UTC,
    }
    assert manifest["model"] == {
        "id": producer.MODEL_ID,
        "revision": producer.MODEL_REVISION,
        "dtype": "float32",
    }
    assert manifest["dataset"]["sha256"] == _sha256(
        fixture["dataset"]
    )
    assert manifest["output"]["raw_evidence_sha256"] == (
        _sha256(fixture["raw"])
    )
    assert manifest["output"]["record_count"] == 6
    assert manifest["output"]["safe_count"] == 6
    assert manifest["output"]["unsafe_count"] == 0
    assert manifest["schema_binding"]["sha256"] == _sha256(
        fixture["schema"]
    )
    assert manifest["authority_boundary"] == (
        producer.AUTHORITY_BOUNDARY
    )


def test_missing_token_removes_all_stale_llamaguard_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    monkeypatch.setattr(
        producer,
        "__file__",
        str(fixture["tool"]),
    )
    monkeypatch.setattr(
        producer,
        "_git_head",
        lambda _repo: GIT_SHA,
    )
    monkeypatch.delenv(TOKEN_ENV, raising=False)

    stale_paths = [
        fixture["repo"] / relative
        for relative in producer.STALE_OUTPUT_RELS
    ]

    for path in stale_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale\n", encoding="utf-8")

    result = producer.main(
        _arguments(fixture["repo"])
    )

    assert result == 1
    assert all(not path.exists() for path in stale_paths)


def test_wrong_workflow_ref_fails_before_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    monkeypatch.setattr(
        producer,
        "__file__",
        str(fixture["tool"]),
    )
    monkeypatch.setattr(
        producer,
        "_git_head",
        lambda _repo: GIT_SHA,
    )
    monkeypatch.setenv(TOKEN_ENV, "test-token")
    monkeypatch.setattr(
        producer,
        "_runtime",
        lambda: pytest.fail(
            "runtime must not start after workflow mismatch"
        ),
    )

    result = producer.main(
        _arguments(
            fixture["repo"],
            workflow_ref=(
                f"{REPOSITORY}/.github/workflows/other.yml@"
                "refs/heads/main"
            ),
        )
    )

    assert result == 1
    assert not fixture["raw"].exists()
    assert not fixture["manifest"].exists()


def test_wrong_checked_out_commit_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)
    monkeypatch.setattr(
        producer,
        "__file__",
        str(fixture["tool"]),
    )
    monkeypatch.setattr(
        producer,
        "_git_head",
        lambda _repo: "b" * 40,
    )
    monkeypatch.setenv(TOKEN_ENV, "test-token")

    result = producer.main(
        _arguments(fixture["repo"])
    )

    assert result == 1
    assert not fixture["raw"].exists()
    assert not fixture["manifest"].exists()
