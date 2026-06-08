#!/usr/bin/env python3
"""Build a fail-closed release_evidence_verifier_report_v0 artifact.

This is the first trusted release-evidence verifier skeleton.

It intentionally never emits VERIFIED.
It does not materialize gates.
It does not write status.json.
It does not replace check_gates.py.
It does not reopen --release-grade-materialized.

The output is a FAILED verifier report that can be schema-validated and
relation-integrity checked.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PULSE_safe_pack_v0.tools.check_release_evidence_verifier_report_v0 import (  # noqa: E402
    check_release_evidence_verifier_report,
)


SCHEMA_VERSION = "release_evidence_verifier_report_v0"
VERIFIER_ID = "pulse_release_evidence_verifier_v0"
VERIFIER_VERSION = "0.1.0"

VALID_EVIDENCE_KINDS = {
    "detector_evidence",
    "detector_materialization_report",
    "external_detector_summary",
    "refusal_delta_evidence",
    "provenance_record",
    "policy_reference",
    "registry_reference",
}


def _utc_now() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_relative_or_input(path: pathlib.Path, raw: str) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return raw


def _git_sha() -> str | None:
    env_sha = os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA")
    if isinstance(env_sha, str) and env_sha.strip():
        candidate = env_sha.strip()
        if len(candidate) == 40 and all(c in "0123456789abcdefABCDEF" for c in candidate):
            return candidate

    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None

    if len(out) == 40 and all(c in "0123456789abcdefABCDEF" for c in out):
        return out
    return None


def _run_key() -> str | None:
    parts: list[str] = []
    for key in (
        "GITHUB_RUN_ID",
        "GITHUB_RUN_NUMBER",
        "GITHUB_WORKFLOW",
        "CI_PIPELINE_ID",
        "BUILD_BUILDID",
    ):
        value = os.getenv(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key}={value.strip()}")
    return "|".join(parts) if parts else None


def _load_json_schema_hint(path: pathlib.Path) -> str | None:
    if path.suffix.lower() not in {".json", ".jsonl"}:
        return None

    if path.suffix.lower() == ".jsonl":
        return None

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(obj, dict):
        return None

    for key in ("schema_version", "schema"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _parse_evidence_arg(raw: str) -> tuple[str, pathlib.Path, str]:
    if "=" not in raw:
        raise ValueError(
            "evidence arguments must use KIND=PATH format, "
            "for example detector_evidence=artifacts/detectors/report.json"
        )

    kind, path_raw = raw.split("=", 1)
    kind = kind.strip()
    path_raw = path_raw.strip()

    if kind not in VALID_EVIDENCE_KINDS:
        allowed = ", ".join(sorted(VALID_EVIDENCE_KINDS))
        raise ValueError(f"unsupported evidence kind {kind!r}; expected one of: {allowed}")

    if not path_raw:
        raise ValueError("evidence path must be non-empty")

    path = pathlib.Path(path_raw)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()

    return kind, path, path_raw


def _evidence_input(
    *,
    kind: str,
    path: pathlib.Path,
    raw_path: str,
    git_sha: str | None,
    run_key: str | None,
) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"candidate evidence file not found: {path}")

    return {
        "kind": kind,
        "path": _repo_relative_or_input(path, raw_path),
        "sha256": _sha256_file(path),
        "schema_version": _load_json_schema_hint(path),
        "subject_binding": {
            "git_sha": git_sha,
            "run_key": run_key,
        },
        "provenance": {
            "observed_by": VERIFIER_ID,
            "trusted": False,
            "verification_status": "not_verified",
            "note": "candidate input recorded by fail-closed verifier skeleton",
        },
    }


def build_report(
    *,
    policy_path: pathlib.Path,
    registry_path: pathlib.Path,
    repository: str | None,
    commit_sha: str | None,
    run_key: str | None,
    release_candidate: str | None,
    evidence_args: list[str],
) -> dict[str, Any]:
    evidence_inputs: list[dict[str, Any]] = []

    for raw in evidence_args:
        kind, evidence_path, raw_path = _parse_evidence_arg(raw)
        evidence_inputs.append(
            _evidence_input(
                kind=kind,
                path=evidence_path,
                raw_path=raw_path,
                git_sha=commit_sha,
                run_key=run_key,
            )
        )

    failed_checks = [
        "trusted release-evidence verifier skeleton does not verify evidence yet",
        "no verified relation bindings present",
        "no gate materialization performed",
    ]
    if not evidence_inputs:
        failed_checks.append("no candidate evidence inputs were supplied")
    else:
        failed_checks.append(
            "candidate evidence inputs are recorded only; verification is not implemented"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "created_utc": _utc_now(),
        "verifier_id": VERIFIER_ID,
        "verifier_version": VERIFIER_VERSION,
        "verifier_decision": "FAILED",
        "run_identity": {
            "run_mode": "prod",
            "run_key": run_key,
            "git_sha": commit_sha,
        },
        "subject": {
            "repository": repository,
            "commit_sha": commit_sha,
            "release_candidate": release_candidate,
        },
        "policy_binding": {
            "policy_path": _repo_relative_or_input(policy_path, str(policy_path)),
            "policy_sha256": _sha256_file(policy_path) if policy_path.exists() else None,
            "policy_set": "required+release_required",
        },
        "registry_binding": {
            "registry_path": _repo_relative_or_input(registry_path, str(registry_path)),
            "registry_sha256": _sha256_file(registry_path) if registry_path.exists() else None,
        },
        "evidence_inputs": evidence_inputs,
        "verified_artifacts": [],
        "relation_bindings": [],
        "gate_materialization": {},
        "failed_checks": failed_checks,
        "warnings": [],
    }


def write_json(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed release_evidence_verifier_report_v0 artifact."
    )
    parser.add_argument(
        "--out",
        default="PULSE_safe_pack_v0/artifacts/release_evidence_verifier_report_v0.json",
        help="Output path for release_evidence_verifier_report_v0.json.",
    )
    parser.add_argument(
        "--policy",
        default="pulse_gate_policy_v0.yml",
        help="Declared gate policy path.",
    )
    parser.add_argument(
        "--registry",
        default="pulse_gate_registry_v0.yml",
        help="Gate registry path.",
    )
    parser.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY"),
        help="Repository subject, if known.",
    )
    parser.add_argument(
        "--commit-sha",
        default=_git_sha(),
        help="Subject commit SHA. Defaults to CI/git discovery when available.",
    )
    parser.add_argument(
        "--run-key",
        default=_run_key(),
        help="Run identity key. Defaults to CI environment discovery when available.",
    )
    parser.add_argument(
        "--release-candidate",
        default=None,
        help="Optional release candidate identifier.",
    )
    parser.add_argument(
        "--evidence",
        action="append",
        default=[],
        metavar="KIND=PATH",
        help=(
            "Candidate evidence input to record without trusting it. "
            "May be supplied multiple times."
        ),
    )

    args = parser.parse_args()

    try:
        report = build_report(
            policy_path=(REPO_ROOT / args.policy).resolve()
            if not pathlib.Path(args.policy).is_absolute()
            else pathlib.Path(args.policy).resolve(),
            registry_path=(REPO_ROOT / args.registry).resolve()
            if not pathlib.Path(args.registry).is_absolute()
            else pathlib.Path(args.registry).resolve(),
            repository=args.repository,
            commit_sha=args.commit_sha,
            run_key=args.run_key,
            release_candidate=args.release_candidate,
            evidence_args=list(args.evidence or []),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out_path = pathlib.Path(args.out)
    if not out_path.is_absolute():
        out_path = (REPO_ROOT / out_path).resolve()

    write_json(out_path, report)

    errors = check_release_evidence_verifier_report(out_path)
    if errors:
        print("ERRORS (fail-closed):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"OK: wrote fail-closed release evidence verifier report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
