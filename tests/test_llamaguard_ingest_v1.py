#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(REPO_ROOT),
    )

from PULSE_safe_pack_v0.tools.adapters import (  # noqa: E402
    llamaguard_ingest as producer,
)


ROOT_SCHEMA_REL = (
    "schemas/external_summary_v1.schema.json"
)
BUNDLED_SCHEMA_REL = (
    "PULSE_safe_pack_v0/schemas/"
    "external_summary_v1.schema.json"
)
THRESHOLDS_REL = (
    "PULSE_safe_pack_v0/profiles/"
    "external_thresholds.yaml"
)
EXTERNAL_DIR_REL = (
    "PULSE_safe_pack_v0/artifacts/external"
)
RAW_REL = (
    f"{EXTERNAL_DIR_REL}/"
    "llamaguard_raw.jsonl"
)
SUMMARY_REL = (
    f"{EXTERNAL_DIR_REL}/"
    "llamaguard_summary.json"
)
STATUS_REL = (
    "PULSE_safe_pack_v0/artifacts/status.json"
)
EVALUATOR_MANIFEST_REL = (
    "PULSE_safe_pack_v0/profiles/"
    "llamaguard_test_evaluator.json"
)
AUGMENT_STATUS = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "tools"
    / "augment_status.py"
)

REPOSITORY = "HKati/pulse-release-gates-0.1"
SIGNER_IDENTITY = (
    "repo:HKati/pulse-release-gates-0.1:"
    "workflow:.github/workflows/"
    "pulse_external_evidence.yml"
)
GIT_SHA = "a" * 40
RUN_ID = (
    "GITHUB_RUN_ID=123|"
    "GITHUB_RUN_ATTEMPT=1|"
    "GITHUB_WORKFLOW=pulse_external_evidence"
)
GENERATED_AT = "2026-06-24T00:00:00Z"
RELEASE_CANDIDATE = "pulse-ref-release-candidate"
TOOL_VERSION = "llamaguard-test-v1"

AUTHORITY_BOUNDARY = (
    "This external summary does not define "
    "release authority. It is recorded evidence "
    "that may be folded into status.json only "
    "after schema, identity, signer, and policy "
    "validation."
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        text,
        encoding="utf-8",
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )
    assert isinstance(payload, dict)
    return payload


def _copy_contract(
    repo: Path,
    relative: str,
) -> Path:
    source = REPO_ROOT / relative
    assert source.is_file(), (
        "missing checked-in contract: "
        f"{relative}"
    )

    target = repo / relative
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    shutil.copy2(source, target)
    return target


def _record(
    index: int,
    *,
    label: str = "safe",
    categories: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "input": f"prompt-{index}",
        "output": f"completion-{index}",
        "llamaguard": {
            "label": label,
            "categories": (
                categories
                if categories is not None
                else []
            ),
        },
    }

    if extra:
        record.update(extra)

    return record


def _write_jsonl(
    path: Path,
    records: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        "".join(
            json.dumps(
                record,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
            for record in records
        ),
        encoding="utf-8",
    )


def _fixture(
    tmp_path: Path,
    *,
    records: list[dict[str, Any]] | None = None,
    threshold: float = 0.01,
) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()

    bundled_schema = _copy_contract(
        repo,
        BUNDLED_SCHEMA_REL,
    )

    thresholds = repo / THRESHOLDS_REL
    _write_text(
        thresholds,
        (
            "llamaguard_violation_rate_max: "
            f"{threshold}\n"
            'external_overall_policy: "all"\n'
        ),
    )

    evaluator_manifest = (
        repo / EVALUATOR_MANIFEST_REL
    )
    _write_json(
        evaluator_manifest,
        {
            "schema_version": (
                "llamaguard_test_evaluator_v0"
            ),
            "tool": "llamaguard",
            "tool_version": TOOL_VERSION,
            "configuration": {
                "classification_mode": "safe_unsafe",
            },
        },
    )

    external_dir = repo / EXTERNAL_DIR_REL
    external_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    raw = repo / RAW_REL
    _write_jsonl(
        raw,
        (
            records
            if records is not None
            else [_record(0)]
        ),
    )

    return {
        "repo": repo,
        "schema": bundled_schema,
        "thresholds": thresholds,
        "evaluator_manifest": evaluator_manifest,
        "external_dir": external_dir,
        "raw": raw,
        "summary": repo / SUMMARY_REL,
        "status": repo / STATUS_REL,
    }


def _arguments(
    fixture: dict[str, Path],
    *,
    raw: str = RAW_REL,
    output: str = SUMMARY_REL,
    dataset: str | None = None,
    evaluator_manifest: str | None = (
        EVALUATOR_MANIFEST_REL
    ),
    generated_at: str = GENERATED_AT,
    signer_identity: str = SIGNER_IDENTITY,
    repository: str = REPOSITORY,
    tool_version: str = TOOL_VERSION,
) -> list[str]:
    args = [
        "--repo-root",
        str(fixture["repo"]),
        "--in",
        raw,
        "--out",
        output,
        "--schema",
        BUNDLED_SCHEMA_REL,
        "--thresholds",
        THRESHOLDS_REL,
        "--run-id",
        RUN_ID,
        "--generated-at",
        generated_at,
        "--release-candidate",
        RELEASE_CANDIDATE,
        "--git-sha",
        GIT_SHA,
        "--repository",
        repository,
        "--signer-identity",
        signer_identity,
        "--tool-version",
        tool_version,
        "--adapter-version",
        "1.0.0",
    ]

    if dataset is not None:
        args.extend(["--dataset", dataset])

    if evaluator_manifest is not None:
        args.extend(
            [
                "--evaluator-manifest",
                evaluator_manifest,
            ]
        )

    return args


def _run(
    fixture: dict[str, Path],
    **overrides: Any,
) -> int:
    return producer.main(
        _arguments(
            fixture,
            **overrides,
        )
    )


def _schema_errors(
    fixture: dict[str, Path],
    summary: dict[str, Any],
) -> list[str]:
    schema = _read_json(
        fixture["schema"]
    )
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    return [
        error.message
        for error in validator.iter_errors(summary)
    ]


def _run_augment(
    fixture: dict[str, Path],
) -> dict[str, Any]:
    _write_json(
        fixture["status"],
        {
            "version": "1.0.0-test",
            "gates": {},
            "metrics": {},
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(AUGMENT_STATUS),
            "--status",
            str(fixture["status"]),
            "--thresholds",
            str(fixture["thresholds"]),
            "--external_dir",
            str(fixture["external_dir"]),
            "--require_external_summaries",
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        result.stderr or result.stdout
    )
    return _read_json(fixture["status"])


def test_bundled_schema_matches_repo_contract() -> None:
    root_schema = _read_json(
        REPO_ROOT / ROOT_SCHEMA_REL
    )
    bundled_schema = _read_json(
        REPO_ROOT / BUNDLED_SCHEMA_REL
    )
    assert bundled_schema == root_schema


def test_valid_current_run_summary_is_schema_valid_and_bound(
    tmp_path: Path,
) -> None:
    records = [
        _record(
            0,
            label="unsafe",
            categories=["S1", "S1"],
        )
    ]
    records.extend(
        _record(index)
        for index in range(1, 100)
    )

    fixture = _fixture(
        tmp_path,
        records=records,
    )

    assert _run(fixture) == 0
    assert fixture["summary"].is_file()

    summary = _read_json(
        fixture["summary"]
    )
    assert _schema_errors(
        fixture,
        summary,
    ) == []

    assert summary["schema_version"] == (
        "external_summary_v1"
    )
    assert summary["tool"] == {
        "name": "llamaguard",
        "version": TOOL_VERSION,
        "adapter": "llamaguard_ingest",
        "adapter_version": "1.0.0",
    }
    assert summary["run"]["run_id"] == RUN_ID
    assert summary["run"]["generated_at"] == (
        GENERATED_AT
    )
    assert summary["run"]["model_id"] == (
        RELEASE_CANDIDATE
    )
    assert summary["run"]["dataset_digest"] == (
        _sha256(fixture["raw"])
    )
    assert len(
        summary["run"]["evaluator_digest"]
    ) == 64

    expected_subject_digest = hashlib.sha256(
        GIT_SHA.encode("utf-8")
    ).hexdigest()
    assert summary["subject"] == {
        "kind": "release_candidate",
        "id": RELEASE_CANDIDATE,
        "digest_algorithm": "sha256",
        "digest": expected_subject_digest,
    }

    metric = summary["metrics"][0]
    assert metric["key"] == (
        "llamaguard_violation_rate"
    )
    assert metric["value"] == pytest.approx(0.01)
    assert metric["threshold"] == pytest.approx(0.01)
    assert metric["comparator"] == "lte"
    assert metric["passed"] is True

    assert summary["threshold_ref"] == {
        "key": "llamaguard_violation_rate_max",
        "version": "v0",
        "uri": THRESHOLDS_REL,
    }
    assert summary["evidence"][
        "raw_artifact_uri"
    ] == RAW_REL
    assert summary["evidence"][
        "raw_artifact_digest"
    ] == _sha256(fixture["raw"])
    assert summary["signing"] == {
        "mode": "github-attestation",
        "identity": SIGNER_IDENTITY,
    }
    assert summary["result"]["passed"] is True
    assert summary["result"][
        "release_contribution"
    ] == "required"
    assert summary["authority_boundary"] == (
        AUTHORITY_BOUNDARY
    )

    counts = summary["extensions"][
        "classification_counts"
    ]
    assert counts == {
        "total": 100,
        "safe": 99,
        "unsafe": 1,
        "by_category": {"S1": 1},
    }


def test_canonical_summary_metrics_fold_into_augment_status(
    tmp_path: Path,
) -> None:
    fixture = _fixture(
        tmp_path,
        records=[_record(0)],
        threshold=0.01,
    )
    assert _run(fixture) == 0

    status = _run_augment(fixture)
    assert status["gates"][
        "external_summaries_present"
    ] is True
    assert status["gates"][
        "external_all_pass"
    ] is True

    metrics = status["external"]["metrics"]
    assert len(metrics) == 1
    assert metrics[0] == {
        "name": "llamaguard_violation_rate",
        "value": 0.0,
        "threshold": 0.01,
        "pass": True,
    }


def test_canonical_declared_failure_cannot_fold_as_pass(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    assert _run(fixture) == 0

    summary = _read_json(fixture["summary"])
    summary["metrics"][0]["passed"] = False
    summary["result"]["passed"] = False
    _write_json(fixture["summary"], summary)

    status = _run_augment(fixture)
    assert status["gates"][
        "external_all_pass"
    ] is False
    assert status["external"][
        "metrics"
    ][0]["pass"] is False


def test_repeated_current_run_production_is_deterministic(
    tmp_path: Path,
) -> None:
    fixture = _fixture(
        tmp_path,
        records=[_record(0), _record(1)],
    )
    assert _run(fixture) == 0
    first_bytes = fixture["summary"].read_bytes()
    assert _run(fixture) == 0
    assert fixture["summary"].read_bytes() == (
        first_bytes
    )


def test_threshold_failure_writes_failed_summary_and_returns_nonzero(
    tmp_path: Path,
) -> None:
    fixture = _fixture(
        tmp_path,
        records=[
            _record(
                0,
                label="unsafe",
                categories=["S1"],
            ),
            _record(1),
        ],
    )
    assert _run(fixture) == 1
    assert fixture["summary"].is_file()

    summary = _read_json(fixture["summary"])
    assert _schema_errors(fixture, summary) == []
    assert summary["metrics"][0]["value"] == (
        pytest.approx(0.5)
    )
    assert summary["metrics"][0]["passed"] is False
    assert summary["result"]["passed"] is False


@pytest.mark.parametrize(
    "signer_identity",
    [
        (
            "repo:HKati/pulse-release-gates-0.1:"
            "workflow:*"
        ),
        (
            "repo:someone-else/pulse-release-gates-0.1:"
            "workflow:.github/workflows/"
            "pulse_external_evidence.yml"
        ),
        (
            "repo:HKati/pulse-release-gates-0.1:"
            "workflow:../external.yml"
        ),
        (
            "repo:HKati/pulse-release-gates-0.1:"
            "workflow:external-eval"
        ),
    ],
)
def test_invalid_signer_identity_fails_closed(
    tmp_path: Path,
    signer_identity: str,
) -> None:
    fixture = _fixture(tmp_path)
    _write_text(
        fixture["summary"],
        "stale-summary\n",
    )
    assert _run(
        fixture,
        signer_identity=signer_identity,
    ) == 1
    assert not fixture["summary"].exists()


def test_duplicate_raw_json_key_fails_closed(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _write_text(
        fixture["raw"],
        (
            '{"input":"first",'
            '"input":"second",'
            '"output":"completion",'
            '"llamaguard":{'
            '"label":"safe",'
            '"categories":[]}}\n'
        ),
    )
    assert _run(fixture) == 1
    assert not fixture["summary"].exists()


def test_overflowed_raw_json_number_fails_closed(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _write_text(
        fixture["raw"],
        (
            '{"input":"prompt",'
            '"output":"completion",'
            '"llamaguard":{'
            '"label":"safe",'
            '"categories":[]},'
            '"ignored_metadata":1e999}\n'
        ),
    )
    assert _run(fixture) == 1
    assert not fixture["summary"].exists()


@pytest.mark.parametrize(
    "raw_text",
    [
        "",
        "\n\n",
        (
            '{"input":"prompt",'
            '"output":"completion",'
            '"llamaguard":{'
            '"label":"unknown",'
            '"categories":[]}}\n'
        ),
        (
            '{"input":"prompt",'
            '"output":"completion",'
            '"llamaguard":{'
            '"label":"safe",'
            '"categories":"S1"}}\n'
        ),
        (
            '{"input":"prompt",'
            '"output":"completion",'
            '"llamaguard":{'
            '"label":"safe",'
            '"categories":[1]}}\n'
        ),
        (
            '{"input":"prompt",'
            '"output":"completion",'
            '"llamaguard":{'
            '"label":"safe",'
            '"categories":[]},'
            '"score":NaN}\n'
        ),
    ],
)
def test_malformed_or_empty_raw_evidence_fails_closed(
    tmp_path: Path,
    raw_text: str,
) -> None:
    fixture = _fixture(tmp_path)
    _write_text(fixture["raw"], raw_text)
    assert _run(fixture) == 1
    assert not fixture["summary"].exists()


def test_stale_generated_outputs_are_cleared_but_raw_is_preserved(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    raw_digest_before = _sha256(fixture["raw"])

    for filename in producer.STALE_OUTPUTS:
        _write_text(
            fixture["external_dir"] / filename,
            "stale\n",
        )

    stale_temp = (
        fixture["external_dir"]
        / ".llamaguard_summary.stale.tmp"
    )
    _write_text(stale_temp, "stale-temp\n")

    assert _run(fixture) == 0
    assert fixture["summary"].is_file()
    assert _sha256(fixture["raw"]) == (
        raw_digest_before
    )

    for filename in producer.STALE_OUTPUTS:
        path = fixture["external_dir"] / filename
        if filename == "llamaguard_summary.json":
            assert path.is_file()
        else:
            assert not path.exists()

    assert not stale_temp.exists()


def test_noncanonical_output_is_rejected_without_deleting_canonical_file(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    sentinel = '{"sentinel":"preserve-me"}\n'
    _write_text(fixture["summary"], sentinel)

    alternative_output = (
        f"{EXTERNAL_DIR_REL}/other_summary.json"
    )
    assert _run(
        fixture,
        output=alternative_output,
    ) == 1
    assert fixture["summary"].read_text(
        encoding="utf-8"
    ) == sentinel
    assert not (
        fixture["repo"] / alternative_output
    ).exists()


def test_noncanonical_raw_input_is_rejected_and_stale_summary_is_cleared(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    alternative_raw_rel = (
        f"{EXTERNAL_DIR_REL}/"
        "other_llamaguard_raw.jsonl"
    )
    _write_jsonl(
        fixture["repo"] / alternative_raw_rel,
        [_record(0)],
    )
    _write_text(
        fixture["summary"],
        "stale-summary\n",
    )

    assert _run(
        fixture,
        raw=alternative_raw_rel,
    ) == 1
    assert not fixture["summary"].exists()
    assert fixture["raw"].is_file()


def test_dataset_path_escape_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    outside_dataset = tmp_path / "outside.jsonl"
    _write_text(
        outside_dataset,
        '{"dataset":"outside"}\n',
    )
    assert _run(
        fixture,
        dataset=str(outside_dataset),
    ) == 1
    assert not fixture["summary"].exists()


def test_generated_at_without_timezone_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    assert _run(
        fixture,
        generated_at="2026-06-24T00:00:00",
    ) == 1
    assert not fixture["summary"].exists()


def test_duplicate_threshold_yaml_key_fails_closed(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _write_text(
        fixture["thresholds"],
        (
            "llamaguard_violation_rate_max: 0.01\n"
            "llamaguard_violation_rate_max: 0.02\n"
            'external_overall_policy: "all"\n'
        ),
    )
    assert _run(fixture) == 1
    assert not fixture["summary"].exists()


def test_generated_summary_schema_failure_leaves_no_canonical_output(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    _write_json(
        fixture["schema"],
        {
            "$schema": (
                "https://json-schema.org/"
                "draft/2020-12/schema"
            ),
            "type": "object",
            "required": [
                "impossible_required_field",
            ],
        },
    )
    assert _run(fixture) == 1
    assert not fixture["summary"].exists()


def test_atomic_write_failure_leaves_no_summary_or_temp_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _fixture(tmp_path)

    def _fail_replace(
        _source: Any,
        _destination: Any,
    ) -> None:
        raise OSError(
            "synthetic atomic replace failure"
        )

    monkeypatch.setattr(
        producer.os,
        "replace",
        _fail_replace,
    )
    assert _run(fixture) == 1
    assert not fixture["summary"].exists()
    assert list(
        fixture["external_dir"].glob(
            ".llamaguard_summary.*.tmp"
        )
    ) == []


def test_symlinked_raw_evidence_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    target = (
        fixture["external_dir"]
        / "llamaguard_raw_target.jsonl"
    )
    _write_jsonl(target, [_record(0)])
    fixture["raw"].unlink()

    try:
        fixture["raw"].symlink_to(target.name)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    assert _run(fixture) == 1
    assert not fixture["summary"].exists()


def test_missing_tool_version_fails_closed(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    assert _run(
        fixture,
        tool_version="",
    ) == 1
    assert not fixture["summary"].exists()


def main() -> int:
    return pytest.main([__file__, "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
