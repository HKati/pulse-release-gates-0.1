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
    build_llamaguard_attestation_envelope_v1 as builder,
)
from PULSE_safe_pack_v0.tools.adapters import (  # noqa: E402
    llamaguard_ingest as summary_producer,
)


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
GENERATED_AT = "2026-06-25T20:00:00Z"
VERIFIED_AT = "2026-06-25T20:01:00Z"
ATTESTATION_ID = "123456"
ATTESTATION_URL = (
    "https://github.com/"
    "HKati/pulse-release-gates-0.1/"
    "attestations/123456"
)
ATTEST_ACTION_REF = (
    "actions/attest@"
    "7c74d28b9d84cb8768d0b8ca14a4bac6ef463e6"
)
MODEL_REVISION = (
    "acf7aafa60f0410f8f42b1fa35e077d705892029"
)

BUNDLED_SUMMARY_SCHEMA_REL = (
    "PULSE_safe_pack_v0/schemas/"
    "external_summary_v1.schema.json"
)

COPY_RELS = (
    builder.TOOL_REL,
    builder.SUMMARY_SCHEMA_REL,
    BUNDLED_SUMMARY_SCHEMA_REL,
    builder.ENVELOPE_SCHEMA_REL,
    builder.SIGNER_POLICY_REL,
    builder.THRESHOLD_POLICY_REL,
    builder.VERIFIER_REL,
    builder.WORKFLOW_REL,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _write_json(
    path: Path,
    payload: Any,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _copy(repo: Path, relative: str) -> Path:
    source = REPO_ROOT / relative
    assert source.is_file(), (
        f"missing checked-in dependency: {relative}"
    )

    target = repo / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _make_repo(tmp_path: Path) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()

    for relative in COPY_RELS:
        _copy(repo, relative)

    dataset = repo / builder.DATASET_REL
    dataset.parent.mkdir(parents=True, exist_ok=True)
    dataset.write_text(
        json.dumps(
            {
                "case_id": "safe_case",
                "input": "What causes a rainbow?",
                "output": (
                    "Refraction, reflection, and dispersion "
                    "of sunlight in water droplets."
                ),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    raw = repo / builder.RAW_REL
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(
        json.dumps(
            {
                "case_id": "safe_case",
                "input": "What causes a rainbow?",
                "output": (
                    "Refraction, reflection, and dispersion "
                    "of sunlight in water droplets."
                ),
                "llamaguard": {
                    "label": "safe",
                    "categories": [],
                    "raw_output": "safe",
                },
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    evaluator_manifest = (
        repo / builder.EVALUATOR_MANIFEST_REL
    )
    _write_json(
        evaluator_manifest,
        {
            "schema_version": (
                "llamaguard_current_run_evaluator_v0"
            ),
            "run": {
                "repository": builder.EXPECTED_REPOSITORY,
                "git_sha": GIT_SHA,
                "run_key": RUN_KEY,
                "workflow_ref": WORKFLOW_REF,
                "release_candidate": RELEASE_CANDIDATE,
                "created_utc": GENERATED_AT,
            },
            "authority_boundary": {
                "creates_release_authority": False,
                "materializes_status": False,
                "materializes_release_required": False,
                "creates_attestation": False,
                "replaces_check_gates": False,
            },
        },
    )

    summary_result = summary_producer.main(
        [
            "--repo-root",
            str(repo),
            "--in",
            builder.RAW_REL,
            "--dataset",
            builder.DATASET_REL,
            "--evaluator-manifest",
            builder.EVALUATOR_MANIFEST_REL,
            "--out",
            builder.SUMMARY_REL,
            "--schema",
            BUNDLED_SUMMARY_SCHEMA_REL,
            "--thresholds",
            builder.THRESHOLD_POLICY_REL,
            "--run-id",
            RUN_KEY,
            "--generated-at",
            GENERATED_AT,
            "--release-candidate",
            RELEASE_CANDIDATE,
            "--git-sha",
            GIT_SHA,
            "--repository",
            builder.EXPECTED_REPOSITORY,
            "--signer-identity",
            builder.EXPECTED_SIGNER_IDENTITY,
            "--tool-version",
            MODEL_REVISION,
            "--adapter-version",
            "1.0.0",
        ]
    )
    assert summary_result == 0

    bundle_source = (
        tmp_path / "actions-attest-bundle.json"
    )
    _write_json(
        bundle_source,
        {
            "mediaType": (
                "application/vnd.dev.sigstore."
                "bundle.v0.3+json"
            ),
            "verificationMaterial": {
                "content": "test-only",
            },
            "dsseEnvelope": {
                "payloadType": (
                    "application/vnd.in-toto+json"
                ),
                "payload": "e30=",
                "signatures": [
                    {
                        "keyid": "",
                        "sig": "dGVzdA==",
                    }
                ],
            },
        },
    )

    return {
        "repo": repo,
        "tool": repo / builder.TOOL_REL,
        "dataset": dataset,
        "raw": raw,
        "evaluator_manifest": evaluator_manifest,
        "summary": repo / builder.SUMMARY_REL,
        "bundle_source": bundle_source,
        "bundle": repo / builder.BUNDLE_REL,
        "envelope": repo / builder.ENVELOPE_REL,
        "report": repo / builder.VERIFIER_REPORT_REL,
        "status": (
            repo
            / "PULSE_safe_pack_v0"
            / "artifacts"
            / "status.json"
        ),
        "envelope_schema": (
            repo / builder.ENVELOPE_SCHEMA_REL
        ),
    }


def _arguments(
    fixture: dict[str, Path],
    **overrides: str,
) -> list[str]:
    values = {
        "repository": builder.EXPECTED_REPOSITORY,
        "source_digest": GIT_SHA,
        "workflow_ref": WORKFLOW_REF,
        "signer_identity": (
            builder.EXPECTED_SIGNER_IDENTITY
        ),
        "verified_at": VERIFIED_AT,
        "attestation_id": ATTESTATION_ID,
        "attestation_url": ATTESTATION_URL,
        "attestation_action_ref": (
            ATTEST_ACTION_REF
        ),
    }
    values.update(overrides)

    return [
        "--repo-root",
        str(fixture["repo"]),
        "--bundle-source",
        str(fixture["bundle_source"]),
        "--repository",
        values["repository"],
        "--source-digest",
        values["source_digest"],
        "--workflow-ref",
        values["workflow_ref"],
        "--signer-identity",
        values["signer_identity"],
        "--verified-at",
        values["verified_at"],
        "--attestation-id",
        values["attestation_id"],
        "--attestation-url",
        values["attestation_url"],
        "--attestation-action-ref",
        values["attestation_action_ref"],
    ]


def _patch_canonical_execution(
    monkeypatch: pytest.MonkeyPatch,
    fixture: dict[str, Path],
) -> None:
    monkeypatch.setattr(
        builder,
        "__file__",
        str(fixture["tool"]),
    )
    monkeypatch.setattr(
        builder,
        "_git_head",
        lambda _repo: GIT_SHA,
    )


def test_valid_bundle_builds_schema_valid_exact_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_repo(tmp_path)
    _patch_canonical_execution(
        monkeypatch,
        fixture,
    )
    source_bytes = fixture[
        "bundle_source"
    ].read_bytes()

    result = builder.main(
        _arguments(fixture)
    )

    assert result == 0
    assert fixture["bundle"].is_file()
    assert fixture["envelope"].is_file()
    assert not fixture["bundle"].is_symlink()
    assert not fixture["envelope"].is_symlink()
    assert fixture["bundle"].read_bytes() == source_bytes
    assert not fixture["report"].exists()
    assert not fixture["status"].exists()

    envelope = json.loads(
        fixture["envelope"].read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        fixture["envelope_schema"].read_text(
            encoding="utf-8"
        )
    )
    errors = list(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(envelope)
    )

    assert errors == []
    assert envelope["summary_ref"]["uri"] == (
        builder.SUMMARY_REL
    )
    assert envelope["summary_ref"]["summary_id"] == (
        json.loads(
            fixture["summary"].read_text(
                encoding="utf-8"
            )
        )["summary_id"]
    )
    assert envelope["summary_digest"] == {
        "algorithm": "sha256",
        "value": _sha256(fixture["summary"]),
    }
    assert envelope["signing"] == {
        "mode": "github-attestation",
        "identity": (
            builder.EXPECTED_SIGNER_IDENTITY
        ),
        "issuer": builder.GITHUB_OIDC_ISSUER,
        "bundle_uri": builder.BUNDLE_REL,
    }
    assert envelope["verification"]["verified"] is True
    assert (
        envelope["verification"]["verified_at"]
        == VERIFIED_AT
    )
    assert envelope["policy_context"] == {
        "signer_policy_ref": (
            builder.SIGNER_POLICY_REL
        ),
        "threshold_policy_ref": (
            builder.THRESHOLD_POLICY_REL
        ),
        "release_contribution": "required",
        "fold_in_allowed": True,
    }
    extensions = envelope["extensions"]
    assert extensions["repository"] == (
        builder.EXPECTED_REPOSITORY
    )
    assert extensions["source_commit"] == GIT_SHA
    assert extensions["workflow_path"] == (
        builder.WORKFLOW_REL
    )
    assert extensions["workflow_ref"] == WORKFLOW_REF
    assert extensions["attestation_id"] == (
        ATTESTATION_ID
    )
    assert extensions["attestation_url"] == (
        ATTESTATION_URL
    )
    assert extensions["bundle_sha256"] == _sha256(
        fixture["bundle"]
    )
    assert (
        extensions["canonical_replay_verifier"][
            "required"
        ]
        is True
    )
    assert extensions["producer_boundary"] == {
        "creates_release_authority": False,
        "materializes_status": False,
        "materializes_release_required": False,
        "replaces_check_gates": False,
    }


@pytest.mark.parametrize(
    "override",
    [
        {
            "repository": (
                "other/pulse-release-gates-0.1"
            ),
        },
        {
            "workflow_ref": (
                "HKati/pulse-release-gates-0.1/"
                ".github/workflows/other.yml@"
                "refs/heads/main"
            ),
        },
        {
            "signer_identity": (
                "repo:HKati/pulse-release-gates-0.1:"
                "workflow:*"
            ),
        },
        {
            "source_digest": "b" * 40,
        },
        {
            "attestation_action_ref": (
                "actions/attest@v4"
            ),
        },
    ],
)
def test_wrong_identity_or_commit_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: dict[str, str],
) -> None:
    fixture = _make_repo(tmp_path)
    _patch_canonical_execution(
        monkeypatch,
        fixture,
    )

    for path in (
        fixture["bundle"],
        fixture["envelope"],
        fixture["report"],
    ):
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            "stale\n",
            encoding="utf-8",
        )

    result = builder.main(
        _arguments(
            fixture,
            **override,
        )
    )

    assert result == 1
    assert not fixture["bundle"].exists()
    assert not fixture["envelope"].exists()
    assert not fixture["report"].exists()


def test_tampered_raw_evidence_breaks_summary_binding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_repo(tmp_path)
    _patch_canonical_execution(
        monkeypatch,
        fixture,
    )
    fixture["raw"].write_text(
        fixture["raw"].read_text(
            encoding="utf-8"
        )
        + '{"tampered":true}\n',
        encoding="utf-8",
    )

    result = builder.main(
        _arguments(fixture)
    )

    assert result == 1
    assert not fixture["bundle"].exists()
    assert not fixture["envelope"].exists()
    assert not fixture["report"].exists()


@pytest.mark.parametrize(
    "bundle_text",
    [
        "",
        "[]\n",
        '{"x":1,"x":2}\n',
        '{"value":NaN}\n',
    ],
)
def test_malformed_bundle_is_rejected_without_partial_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundle_text: str,
) -> None:
    fixture = _make_repo(tmp_path)
    _patch_canonical_execution(
        monkeypatch,
        fixture,
    )
    fixture["bundle_source"].write_text(
        bundle_text,
        encoding="utf-8",
    )

    result = builder.main(
        _arguments(fixture)
    )

    assert result == 1
    assert not fixture["bundle"].exists()
    assert not fixture["envelope"].exists()
    assert not fixture["report"].exists()


def test_summary_generated_after_verified_at_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_repo(tmp_path)
    _patch_canonical_execution(
        monkeypatch,
        fixture,
    )

    result = builder.main(
        _arguments(
            fixture,
            verified_at="2026-06-25T19:59:59Z",
        )
    )

    assert result == 1
    assert not fixture["bundle"].exists()
    assert not fixture["envelope"].exists()
    assert not fixture["report"].exists()


if __name__ == "__main__":
    raise SystemExit(
        pytest.main([__file__])
    )
