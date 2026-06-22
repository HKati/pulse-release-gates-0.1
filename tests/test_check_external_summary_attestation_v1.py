#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(REPO_ROOT),
    )

from PULSE_safe_pack_v0.tools.check_external_summary_attestation_v1 import (
    AUTHORITY_BOUNDARY,
    GITHUB_OIDC_ISSUER,
    SIGNER_POLICY_PATH,
    SLSA_PROVENANCE_V1,
    THRESHOLD_POLICY_PATH,
    verify_external_summary_attestation,
)


EXPECTED_REPOSITORY = (
    "HKati/pulse-release-gates-0.1"
)
EXPECTED_SOURCE_DIGEST = "a" * 40
SIGNER_IDENTITY = (
    "repo:HKati/pulse-release-gates-0.1:"
    "workflow:.github/workflows/"
    "external-eval.yml"
)
EXPECTED_SIGNER_WORKFLOW = (
    "github.com/HKati/"
    "pulse-release-gates-0.1/"
    ".github/workflows/"
    "external-eval.yml"
)

SUMMARY_RELATIVE = (
    "PULSE_safe_pack_v0/artifacts/"
    "external/llamaguard_summary.json"
)
RAW_RELATIVE = (
    "PULSE_safe_pack_v0/artifacts/"
    "external/llamaguard_raw.json"
)
ENVELOPE_RELATIVE = (
    "PULSE_safe_pack_v0/artifacts/"
    "external/"
    "llamaguard_summary.envelope.json"
)
BUNDLE_RELATIVE = (
    "PULSE_safe_pack_v0/artifacts/"
    "external/"
    "llamaguard_summary.bundle.json"
)

SUMMARY_SCHEMA_RELATIVE = (
    "schemas/external_summary_v1.schema.json"
)
ENVELOPE_SCHEMA_RELATIVE = (
    "schemas/"
    "external_summary_envelope_v1.schema.json"
)

SUMMARY_AUTHORITY_BOUNDARY = (
    "This external summary does not define "
    "release authority. It is recorded evidence "
    "that may be folded into status.json only "
    "after schema, identity, signer, and policy "
    "validation."
)
ENVELOPE_AUTHORITY_BOUNDARY = (
    "This external summary envelope does not "
    "define release authority. It records digest, "
    "signer, verification, and policy context for "
    "external evidence before any "
    "policy-controlled fold-in to status.json."
)


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _write_json(
    path: Path,
    payload: Any,
) -> None:
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


def _write_yaml(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        yaml.safe_dump(
            payload,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _copy_contract(
    repo: Path,
    relative: str,
) -> None:
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

    shutil.copy2(
        source,
        target,
    )


def _signer_policy(
    *,
    identity_pattern: str = SIGNER_IDENTITY,
    signing_mode: str = "github-attestation",
) -> dict[str, Any]:
    return {
        "schema_version": (
            "external_signers_v1"
        ),
        "policy_id": (
            "pulse_ref_external_signers_v1"
        ),
        "release_grade_defaults": {
            "require_schema_valid_summary": True,
            "require_schema_valid_envelope": True,
            "require_summary_digest": True,
            "require_subject_digest": True,
            "require_tool_identity": True,
            "require_tool_version": True,
            "require_threshold_ref": True,
            "require_signer_identity": True,
            (
                "require_verification_before_"
                "fold_in"
            ): True,
            "allow_unsigned_release_grade": False,
            "allow_unverified_fold_in": False,
        },
        "allowed_signing_modes": {
            "release_grade": [
                "github-attestation",
            ],
        },
        "allowed_identities": {
            "pulse_external_eval": {
                "identities": [
                    {
                        "pattern": (
                            identity_pattern
                        ),
                        "modes": [
                            signing_mode,
                        ],
                        "release_contributions": [
                            "required",
                        ],
                    }
                ],
            }
        },
        "tool_policies": {
            "llamaguard": {
                (
                    "release_grade_"
                    "contribution_allowed"
                ): True,
                "allowed_identity_groups": [
                    "pulse_external_eval",
                ],
                "require_dataset_digest": True,
                "require_subject_digest": True,
                "require_threshold_ref": True,
            }
        },
    }


def _summary_payload(
    *,
    signing_mode: str = "github-attestation",
    identity: str = SIGNER_IDENTITY,
) -> dict[str, Any]:
    return {
        "schema_version": (
            "external_summary_v1"
        ),
        "summary_id": (
            "llamaguard-summary-test"
        ),
        "tool": {
            "name": "llamaguard",
            "version": "test-v1",
            "adapter": (
                "llamaguard_to_"
                "external_summary_v1"
            ),
            "adapter_version": "v1",
        },
        "run": {
            "run_id": (
                "GITHUB_RUN_ID=123|"
                "GITHUB_RUN_ATTEMPT=1|"
                "GITHUB_WORKFLOW=external-eval"
            ),
            "generated_at": (
                "2026-06-22T00:00:00Z"
            ),
            "dataset_digest": "b" * 64,
            "evaluator_digest": "c" * 64,
            "model_id": "v-test",
        },
        "subject": {
            "kind": "release_candidate",
            "id": "v-test",
            "digest_algorithm": "sha256",
            "digest": "d" * 64,
        },
        "metrics": [
            {
                "key": (
                    "llamaguard_"
                    "violation_rate"
                ),
                "value": 0.0,
                "unit": "rate",
                "threshold": 0.10,
                "comparator": "lte",
                "passed": True,
                "severity": "critical",
            }
        ],
        "threshold_ref": {
            "key": (
                "llamaguard_"
                "violation_rate_max"
            ),
            "version": "v0",
            "uri": THRESHOLD_POLICY_PATH,
        },
        "evidence": {
            "raw_artifact_uri": (
                RAW_RELATIVE
            ),
            "raw_artifact_digest": (
                "0" * 64
            ),
        },
        "signing": {
            "mode": signing_mode,
            "identity": identity,
        },
        "result": {
            "passed": True,
            "reason": (
                "Synthetic canonical passing "
                "external summary."
            ),
            "release_contribution": (
                "required"
            ),
        },
        "authority_boundary": (
            SUMMARY_AUTHORITY_BOUNDARY
        ),
    }


def _envelope_payload(
    *,
    summary_digest: str,
    signing_mode: str = "github-attestation",
    identity: str = SIGNER_IDENTITY,
    bundle_uri: str = BUNDLE_RELATIVE,
    verified: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": (
            "external_summary_envelope_v1"
        ),
        "envelope_id": (
            "llamaguard-summary-"
            "envelope-test"
        ),
        "summary_ref": {
            "uri": SUMMARY_RELATIVE,
            "schema_version": (
                "external_summary_v1"
            ),
            "summary_id": (
                "llamaguard-summary-test"
            ),
        },
        "summary_digest": {
            "algorithm": "sha256",
            "value": summary_digest,
        },
        "signing": {
            "mode": signing_mode,
            "identity": identity,
            "issuer": GITHUB_OIDC_ISSUER,
            "bundle_uri": bundle_uri,
        },
        "verification": {
            "verified": verified,
            "verified_at": (
                "2026-06-22T00:01:00Z"
            ),
            "verifier": {
                "name": (
                    "gh-attestation"
                ),
                "version": "test-v1",
            },
            "result_reason": (
                "Synthetic verification fixture."
            ),
        },
        "policy_context": {
            "signer_policy_ref": (
                SIGNER_POLICY_PATH
            ),
            "threshold_policy_ref": (
                THRESHOLD_POLICY_PATH
            ),
            "release_contribution": (
                "required"
            ),
            "fold_in_allowed": True,
        },
        "authority_boundary": (
            ENVELOPE_AUTHORITY_BOUNDARY
        ),
    }


def _fake_gh(
    root: Path,
    *,
    returncode: int,
    stdout_payload: Any | None = None,
    stderr_text: str = "",
) -> tuple[Path, Path]:
    args_path = root / "fake-gh-args.json"
    executable = root / "gh"

    output = (
        stdout_payload
        if stdout_payload is not None
        else [
            {
                "attestation": {},
                "verificationResult": {},
            }
        ]
    )

    script = f"""#!{sys.executable}
import json
import sys
from pathlib import Path

Path({str(args_path)!r}).write_text(
    json.dumps(sys.argv[1:]),
    encoding="utf-8",
)

sys.stdout.write(
    json.dumps({output!r})
)
sys.stderr.write({stderr_text!r})
raise SystemExit({returncode})
"""

    executable.write_text(
        script,
        encoding="utf-8",
    )

    executable.chmod(
        executable.stat().st_mode
        | stat.S_IXUSR
        | stat.S_IXGRP
        | stat.S_IXOTH
    )

    return executable, args_path


def _fixture(
    tmp_path: Path,
    *,
    identity_pattern: str = SIGNER_IDENTITY,
    signing_mode: str = "github-attestation",
    identity: str = SIGNER_IDENTITY,
    envelope_verified: bool = True,
) -> dict[str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()

    _copy_contract(
        repo,
        SUMMARY_SCHEMA_RELATIVE,
    )
    _copy_contract(
        repo,
        ENVELOPE_SCHEMA_RELATIVE,
    )

    threshold_path = (
        repo / THRESHOLD_POLICY_PATH
    )

    threshold_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    threshold_path.write_text(
        (
            "external_overall_policy: all\n"
            "llamaguard_violation_rate_max: "
            "0.10\n"
        ),
        encoding="utf-8",
    )

    policy_path = (
        repo / SIGNER_POLICY_PATH
    )

    _write_yaml(
        policy_path,
        _signer_policy(
            identity_pattern=(
                identity_pattern
            ),
            signing_mode=signing_mode,
        ),
    )

    raw_path = repo / RAW_RELATIVE

    _write_json(
        raw_path,
        {
            "schema_version": (
                "llamaguard_raw_v0"
            ),
            "violation_rate": 0.0,
        },
    )

    summary_path = repo / SUMMARY_RELATIVE
    summary = _summary_payload(
        signing_mode=signing_mode,
        identity=identity,
    )

    summary[
        "evidence"
    ][
        "raw_artifact_digest"
    ] = _sha256(raw_path)

    _write_json(
        summary_path,
        summary,
    )

    bundle_path = repo / BUNDLE_RELATIVE

    _write_json(
        bundle_path,
        {
            "synthetic_bundle": True,
        },
    )

    envelope_path = (
        repo / ENVELOPE_RELATIVE
    )

    _write_json(
        envelope_path,
        _envelope_payload(
            summary_digest=(
                _sha256(summary_path)
            ),
            signing_mode=signing_mode,
            identity=identity,
            verified=envelope_verified,
        ),
    )

    return {
        "repo": repo,
        "summary": summary_path,
        "envelope": envelope_path,
        "bundle": bundle_path,
        "summary_schema": (
            repo / SUMMARY_SCHEMA_RELATIVE
        ),
        "envelope_schema": (
            repo / ENVELOPE_SCHEMA_RELATIVE
        ),
        "policy": policy_path,
    }


def _verify(
    fixture: dict[str, Path],
    gh_executable: Path,
) -> dict[str, Any]:
    return verify_external_summary_attestation(
        repo_root=fixture["repo"],
        summary_path=fixture["summary"],
        envelope_path=fixture["envelope"],
        summary_schema_path=(
            fixture["summary_schema"]
        ),
        envelope_schema_path=(
            fixture["envelope_schema"]
        ),
        signer_policy_path=(
            fixture["policy"]
        ),
        expected_repository=(
            EXPECTED_REPOSITORY
        ),
        expected_source_digest=(
            EXPECTED_SOURCE_DIGEST
        ),
        gh_executable=str(
            gh_executable
        ),
    )


def test_valid_attestation_verifies_with_exact_command_contract(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)

    fake_gh, args_path = _fake_gh(
        tmp_path,
        returncode=0,
    )

    report = _verify(
        fixture,
        fake_gh,
    )

    assert report["status"] == "verified"
    assert report["errors"] == []

    assert (
        report["attestation"]["verified"]
        is True
    )

    assert (
        report["authority_boundary"]
        == AUTHORITY_BOUNDARY
    )

    args = json.loads(
        args_path.read_text(
            encoding="utf-8",
        )
    )

    assert args[:2] == [
        "attestation",
        "verify",
    ]

    assert str(
        fixture["summary"]
    ) in args

    expected_pairs = {
        "--repo": EXPECTED_REPOSITORY,
        "--bundle": str(
            fixture["bundle"]
        ),
        "--signer-workflow": (
            EXPECTED_SIGNER_WORKFLOW
        ),
        "--source-digest": (
            EXPECTED_SOURCE_DIGEST
        ),
        "--predicate-type": (
            SLSA_PROVENANCE_V1
        ),
        "--cert-oidc-issuer": (
            GITHUB_OIDC_ISSUER
        ),
        "--format": "json",
    }

    for flag, value in expected_pairs.items():
        index = args.index(flag)
        assert args[index + 1] == value


def test_self_asserted_verified_envelope_cannot_replace_failed_gh_verification(
    tmp_path: Path,
) -> None:
    fixture = _fixture(
        tmp_path,
        envelope_verified=True,
    )

    fake_gh, args_path = _fake_gh(
        tmp_path,
        returncode=1,
        stderr_text=(
            "synthetic attestation failure"
        ),
    )

    report = _verify(
        fixture,
        fake_gh,
    )

    assert args_path.is_file()
    assert report["status"] == "failed"

    assert (
        report["attestation"]["verified"]
        is False
    )

    assert any(
        (
            "GitHub attestation verification "
            "failed"
        )
        in error
        for error in report["errors"]
    )


def test_summary_digest_mismatch_fails_before_gh_execution(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)

    envelope = json.loads(
        fixture["envelope"].read_text(
            encoding="utf-8",
        )
    )

    envelope[
        "summary_digest"
    ][
        "value"
    ] = "f" * 64

    _write_json(
        fixture["envelope"],
        envelope,
    )

    fake_gh, args_path = _fake_gh(
        tmp_path,
        returncode=0,
    )

    report = _verify(
        fixture,
        fake_gh,
    )

    assert report["status"] == "failed"
    assert not args_path.exists()

    assert any(
        "summary digest mismatch"
        in error
        for error in report["errors"]
    )


def test_wildcard_signer_policy_fails_closed_before_gh_execution(
    tmp_path: Path,
) -> None:
    fixture = _fixture(
        tmp_path,
        identity_pattern=(
            "repo:HKati/"
            "pulse-release-gates-0.1:"
            "workflow:*"
        ),
    )

    fake_gh, args_path = _fake_gh(
        tmp_path,
        returncode=0,
    )

    report = _verify(
        fixture,
        fake_gh,
    )

    assert report["status"] == "failed"
    assert not args_path.exists()

    assert any(
        (
            "signer identity patterns must "
            "be exact"
        )
        in error
        for error in report["errors"]
    )


def test_unsigned_release_grade_summary_fails_closed_before_gh_execution(
    tmp_path: Path,
) -> None:
    fixture = _fixture(
        tmp_path,
        signing_mode="unsigned",
        identity="unsigned",
        identity_pattern="unsigned",
    )

    fake_gh, args_path = _fake_gh(
        tmp_path,
        returncode=0,
    )

    report = _verify(
        fixture,
        fake_gh,
    )

    assert report["status"] == "failed"
    assert not args_path.exists()

    assert any(
        (
            "signing mode 'unsigned' is not "
            "allowed"
        )
        in error
        for error in report["errors"]
    )


def test_unverified_envelope_fails_closed_before_gh_execution(
    tmp_path: Path,
) -> None:
    fixture = _fixture(
        tmp_path,
        envelope_verified=False,
    )

    fake_gh, args_path = _fake_gh(
        tmp_path,
        returncode=0,
    )

    report = _verify(
        fixture,
        fake_gh,
    )

    assert report["status"] == "failed"
    assert not args_path.exists()

    assert any(
        (
            "verification.verified must be "
            "literal true"
        )
        in error
        for error in report["errors"]
    )


def test_empty_success_output_fails_closed(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)

    fake_gh, args_path = _fake_gh(
        tmp_path,
        returncode=0,
        stdout_payload=[],
    )

    report = _verify(
        fixture,
        fake_gh,
    )

    assert args_path.is_file()
    assert report["status"] == "failed"

    assert any(
        (
            "must return a non-empty "
            "JSON array"
        )
        in error
        for error in report["errors"]
    )


def main() -> int:
    return pytest.main(
        [
            __file__,
            "-q",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
