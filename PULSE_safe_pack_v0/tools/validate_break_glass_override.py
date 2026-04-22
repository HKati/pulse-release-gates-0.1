#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "artifacts"
    / "break_glass_override_v0.json"
)

DEFAULT_SCHEMA = (
    REPO_ROOT
    / "schemas"
    / "break_glass_override_v0.schema.json"
)

DEFAULT_RELEASE_DECISION_SCHEMA = (
    REPO_ROOT
    / "schemas"
    / "release_decision_v0.schema.json"
)

EXPECTED_SCHEMA = "pulse_break_glass_override_v0"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _format_error_path(error: Any) -> str:
    path = ".".join(str(part) for part in error.path)
    return path or "<root>"


def _parse_datetime(value: Any) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    text = value.strip()
    if text[-1:].lower() == "z":
        text = text[:-1] + "+00:00"

    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)

    return parsed.astimezone(dt.timezone.utc)


def _validate_with_schema(
    *,
    payload: Any,
    schema_path: Path,
    label: str,
) -> list[str]:
    errors: list[str] = []

    if not schema_path.is_file():
        return [f"{label}: schema file is missing: {_rel(schema_path)}"]

    try:
        import jsonschema
    except Exception as exc:
        return [f"{label}: jsonschema import failed: {exc}"]

    try:
        schema = _read_json(schema_path)
    except Exception as exc:
        return [f"{label}: schema file could not be read: {exc}"]

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except Exception as exc:
        return [f"{label}: schema file is not a valid JSON Schema: {exc}"]

    try:
        validator = jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        )
        validation_errors = sorted(
            validator.iter_errors(payload),
            key=lambda e: list(e.path),
        )
    except Exception as exc:
        return [f"{label}: schema validation failed to run: {exc}"]

    for error in validation_errors:
        errors.append(f"{label}: {_format_error_path(error)}: {error.message}")

    return errors


def _has_nonempty_list(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return isinstance(value, list) and len(value) > 0


def _semantic_errors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    schema = payload.get("schema")
    if schema != EXPECTED_SCHEMA:
        errors.append(f"schema must be {EXPECTED_SCHEMA!r}, got {schema!r}")

    status = payload.get("status")
    release_level_before_override = payload.get("release_level_before_override")

    if release_level_before_override != "FAIL":
        errors.append(
            "release_level_before_override must be 'FAIL'; "
            "break-glass must not attach to a passing release decision"
        )

    if status == "requested":
        for field in ("review", "risk_acceptance", "expires_utc", "revocation"):
            if field in payload:
                errors.append(
                    f"requested override must not include {field!r}; "
                    "requested is a pre-review state"
                )

    elif status == "accepted":
        review = payload.get("review")
        if isinstance(review, dict) and review.get("decision") != "accepted":
            errors.append("accepted override requires review.decision == 'accepted'")

        if payload.get("expires_utc") in (None, ""):
            errors.append("accepted override requires a non-null expires_utc")

        if not _has_nonempty_list(payload, "followups"):
            errors.append("accepted override requires at least one follow-up")

        if "revocation" in payload:
            errors.append("accepted override must not include revocation")

    elif status == "rejected":
        review = payload.get("review")
        if isinstance(review, dict) and review.get("decision") != "rejected":
            errors.append("rejected override requires review.decision == 'rejected'")

        if "revocation" in payload:
            errors.append("rejected override must not include revocation")

    elif status == "expired":
        review = payload.get("review")
        if isinstance(review, dict) and review.get("decision") != "accepted":
            errors.append(
                "expired override must preserve the original accepted review decision"
            )

        if payload.get("expires_utc") in (None, ""):
            errors.append("expired override requires expires_utc")

        if not _has_nonempty_list(payload, "followups"):
            errors.append("expired override requires at least one follow-up")

        if "revocation" in payload:
            errors.append("expired override must not include revocation")

    elif status == "revoked":
        review = payload.get("review")
        if isinstance(review, dict) and review.get("decision") != "accepted":
            errors.append(
                "revoked override must preserve the original accepted review decision"
            )

        if payload.get("expires_utc") in (None, ""):
            errors.append(
                "revoked override requires expires_utc from the original accepted override"
            )

         followups = payload.get("followups")
        if not isinstance(followups, list) or not followups:
            errors.append("revoked override requires at least one follow-up")

        revocation = payload.get("revocation")
        if not isinstance(revocation, dict):
            errors.append("revoked override requires a revocation record")
        else:
            expires_utc = _parse_datetime(payload.get("expires_utc"))
            revoked_utc = _parse_datetime(revocation.get("revoked_utc"))
            if expires_utc is None:
                errors.append(
                    "revoked override requires expires_utc to be a parseable date-time"
                )

            if revoked_utc is None:
                errors.append(
                    "revoked override requires revocation.revoked_utc to be a parseable date-time"
                )
             if expires_utc is None:
                errors.append(
                    "revoked override requires expires_utc to be a parseable date-time"
                )

            if revoked_utc is None:
                errors.append(
                    "revoked override requires revocation.revoked_utc to be a parseable date-time"
                )

            if expires_utc is not None and revoked_utc is not None:
                if revoked_utc >= expires_utc:
                    errors.append(
                        "revoked override requires revocation.revoked_utc to be "
                        "before the original expires_utc authorization window"
                    )

    return errors


def _release_decision_reference_errors(
    *,
    payload: dict[str, Any],
    release_decision_path_override: str | None,
    release_decision_schema_path: Path,
) -> list[str]:
    errors: list[str] = []

    raw_path = release_decision_path_override
    if raw_path is None:
        raw_path = payload.get("release_decision_path")

    if not isinstance(raw_path, str) or not raw_path.strip():
        return ["release decision reference path is missing or not a string"]

    release_decision_path = _resolve_repo_path(raw_path)

    if not release_decision_path.is_file():
        return [
            "referenced release_decision_v0 artifact is missing: "
            f"{_rel(release_decision_path)}"
        ]

    expected_sha = payload.get("release_decision_sha256")
    actual_sha = _sha256(release_decision_path)

    if expected_sha != actual_sha:
        errors.append(
            "release_decision_sha256 does not match referenced artifact: "
            f"expected={expected_sha!r} actual={actual_sha!r}"
        )

    try:
        release_decision = _read_json(release_decision_path)
    except Exception as exc:
        errors.append(f"referenced release_decision_v0 could not be read: {exc}")
        return errors

    if not isinstance(release_decision, dict):
        errors.append("referenced release_decision_v0 root is not an object")
        return errors

    release_schema_errors = _validate_with_schema(
        payload=release_decision,
        schema_path=release_decision_schema_path,
        label="release_decision_v0",
    )
    errors.extend(release_schema_errors)

    expected_level = payload.get("release_level_before_override")
    actual_level = release_decision.get("release_level")

    if actual_level != expected_level:
        errors.append(
            "release_level_before_override does not match referenced "
            "release_decision_v0.release_level: "
            f"expected={expected_level!r} actual={actual_level!r}"
        )

    target = payload.get("target")
    release_target = release_decision.get("target")

    if isinstance(target, str) and isinstance(release_target, str):
        if target != release_target:
            errors.append(
                "break-glass target does not match referenced release decision target: "
                f"expected={target!r} actual={release_target!r}"
            )

    return errors


def validate_break_glass_override(
    *,
    input_path: Path,
    schema_path: Path,
    release_decision_path_override: str | None,
    release_decision_schema_path: Path,
    check_release_decision_reference: bool,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not input_path.is_file():
        return False, [f"break-glass override artifact is missing: {_rel(input_path)}"]

    try:
        payload = _read_json(input_path)
    except Exception as exc:
        return False, [f"break-glass override artifact could not be read: {exc}"]

    if not isinstance(payload, dict):
        return False, ["break-glass override artifact root is not an object"]

    errors.extend(
        _validate_with_schema(
            payload=payload,
            schema_path=schema_path,
            label="break_glass_override_v0",
        )
    )

    errors.extend(_semantic_errors(payload))

    if check_release_decision_reference:
        errors.extend(
            _release_decision_reference_errors(
                payload=payload,
                release_decision_path_override=release_decision_path_override,
                release_decision_schema_path=release_decision_schema_path,
            )
        )

    return not errors, errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a PULSEmech break_glass_override_v0 artifact."
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to break_glass_override_v0.json.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to schemas/break_glass_override_v0.schema.json.",
    )
    parser.add_argument(
        "--release-decision",
        default=None,
        help=(
            "Optional path to the referenced release_decision_v0.json. "
            "When omitted, release_decision_path from the override artifact is used."
        ),
    )
    parser.add_argument(
        "--release-decision-schema",
        default=str(DEFAULT_RELEASE_DECISION_SCHEMA),
        help="Path to schemas/release_decision_v0.schema.json.",
    )
    parser.add_argument(
        "--no-release-decision-check",
        action="store_true",
        help=(
            "Validate only the break-glass artifact shape and semantics. "
            "Do not require or validate the referenced release_decision_v0 artifact."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable validation summary.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    input_path = Path(args.input)
    schema_path = Path(args.schema)
    release_decision_schema_path = Path(args.release_decision_schema)

    if not input_path.is_absolute():
        input_path = REPO_ROOT / input_path
    if not schema_path.is_absolute():
        schema_path = REPO_ROOT / schema_path
    if not release_decision_schema_path.is_absolute():
        release_decision_schema_path = REPO_ROOT / release_decision_schema_path

    ok, errors = validate_break_glass_override(
        input_path=input_path,
        schema_path=schema_path,
        release_decision_path_override=args.release_decision,
        release_decision_schema_path=release_decision_schema_path,
        check_release_decision_reference=not args.no_release_decision_check,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "ok": ok,
                    "input": _rel(input_path),
                    "schema": _rel(schema_path),
                    "release_decision_check": not args.no_release_decision_check,
                    "errors": errors,
                },
                indent=2,
                sort_keys=True,
            )
        )
    elif ok:
        print(f"OK: break_glass_override_v0 is valid: {_rel(input_path)}")
    else:
        print(f"ERROR: break_glass_override_v0 is invalid: {_rel(input_path)}")
        for error in errors:
            print(f"- {error}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
