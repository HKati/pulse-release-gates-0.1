#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "artifacts"
    / "release_decision_v0.json"
)

DEFAULT_OUT = (
    REPO_ROOT
    / "PULSE_safe_pack_v0"
    / "artifacts"
    / "release_decision_v0_ledger_section.html"
)

DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "release_decision_v0.schema.json"

def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _escape(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_bool_label(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "missing"
    return f"invalid:{type(value).__name__}"


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _css_class_for_release_level(level: str) -> str:
    if level == "PROD-PASS":
        return "release-decision-pass-prod"
    if level == "STAGE-PASS":
        return "release-decision-pass-stage"
    if level == "FAIL":
        return "release-decision-fail"
    return "release-decision-unknown"


def _status_pill(label: str, css_class: str) -> str:
    return f'<span class="release-decision-pill {css_class}">{_escape(label)}</span>'


def _render_styles() -> str:
    return """
<style>
.release-decision-v0 {
  border: 1px solid #d0d7de;
  border-radius: 12px;
  padding: 16px;
  margin: 18px 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #ffffff;
}

.release-decision-v0 h2 {
  margin: 0 0 8px 0;
  font-size: 1.25rem;
}

.release-decision-v0 .release-decision-note {
  color: #57606a;
  margin: 0 0 14px 0;
  font-size: 0.95rem;
}

.release-decision-grid {
  display: grid;
  grid-template-columns: minmax(180px, 0.35fr) 1fr;
  gap: 8px 14px;
  margin: 12px 0 16px 0;
}

.release-decision-label {
  color: #57606a;
  font-weight: 600;
}

.release-decision-value {
  color: #24292f;
  word-break: break-word;
}

.release-decision-pill {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.9rem;
  line-height: 1.6;
}

.release-decision-pass-prod {
  color: #0a3622;
  background: #dafbe1;
  border: 1px solid #4ac26b;
}

.release-decision-pass-stage {
  color: #0969da;
  background: #ddf4ff;
  border: 1px solid #54aeef;
}

.release-decision-fail {
  color: #82071e;
  background: #ffebe9;
  border: 1px solid #ff8182;
}

.release-decision-missing,
.release-decision-invalid,
.release-decision-unknown {
  color: #5c2d00;
  background: #fff8c5;
  border: 1px solid #d4a72c;
}

.release-decision-section-title {
  margin: 14px 0 6px 0;
  font-size: 1rem;
  font-weight: 700;
}

.release-decision-list {
  margin: 6px 0 0 20px;
  padding: 0;
}

.release-decision-list li {
  margin: 3px 0;
}

.release-decision-empty {
  color: #57606a;
  font-style: italic;
}

.release-decision-warning {
  border-left: 4px solid #d4a72c;
  padding: 8px 12px;
  background: #fff8c5;
  margin-top: 12px;
}

.release-decision-error {
  border-left: 4px solid #cf222e;
  padding: 8px 12px;
  background: #ffebe9;
  margin-top: 12px;
}
</style>
""".strip()


def _render_key_value(label: str, value: Any) -> str:
    return (
        '<div class="release-decision-label">'
        f"{_escape(label)}"
        "</div>"
        '<div class="release-decision-value">'
        f"{_escape(value)}"
        "</div>"
    )


def _render_list(items: list[Any], *, empty_label: str) -> str:
    if not items:
        return f'<div class="release-decision-empty">{_escape(empty_label)}</div>'

    rows = []
    for item in items:
        rows.append(f"<li>{_escape(item)}</li>")

    return '<ul class="release-decision-list">' + "\n".join(rows) + "</ul>"


def _render_conditions(conditions: dict[str, Any]) -> str:
    rows = [
        _render_key_value(
            "External evidence mode",
            conditions.get("external_evidence_mode", "missing"),
        ),
        _render_key_value(
            "detectors_materialized_ok",
            _as_bool_label(conditions.get("detectors_materialized_ok")),
        ),
        _render_key_value(
            "external_summaries_present",
            _as_bool_label(conditions.get("external_summaries_present")),
        ),
        _render_key_value(
            "external_all_pass",
            _as_bool_label(conditions.get("external_all_pass")),
        ),
        _render_key_value(
            "stubbed",
            _as_bool_label(conditions.get("stubbed")),
        ),
        _render_key_value(
            "scaffold",
            _as_bool_label(conditions.get("scaffold")),
        ),
        _render_key_value(
            "no_stubbed_gates",
            _as_bool_label(conditions.get("no_stubbed_gates")),
        ),
    ]

    return (
        '<div class="release-decision-section-title">Release conditions</div>'
        '<div class="release-decision-grid">'
        + "\n".join(rows)
        + "</div>"
    )


def _render_missing(input_path: Path) -> str:
    return f"""
{_render_styles()}
<section id="release-decision-v0" class="release-decision-v0">
  <h2>Release decision v0</h2>
  <p class="release-decision-note">
    Read-only Quality Ledger section for the materialized release decision artifact.
  </p>

  {_status_pill("MISSING", "release-decision-missing")}

  <div class="release-decision-warning">
    <strong>Release decision artifact is not materialized.</strong><br>
    Expected artifact:
    <code>{_escape(_rel(input_path))}</code><br>
    The Quality Ledger must not infer STAGE-PASS or PROD-PASS from a missing
    release decision artifact.
  </div>
</section>
""".strip()


def _render_invalid(input_path: Path, error: str) -> str:
    return f"""
{_render_styles()}
<section id="release-decision-v0" class="release-decision-v0">
  <h2>Release decision v0</h2>
  <p class="release-decision-note">
    Read-only Quality Ledger section for the materialized release decision artifact.
  </p>

  {_status_pill("INVALID", "release-decision-invalid")}

  <div class="release-decision-error">
    <strong>Release decision artifact is present but invalid.</strong><br>
    Artifact:
    <code>{_escape(_rel(input_path))}</code><br>
    Error:
    <code>{_escape(error)}</code><br>
    The Quality Ledger must not infer STAGE-PASS or PROD-PASS from an invalid
    release decision artifact.
  </div>
</section>
""".strip()


def _release_decision_artifact_error(payload: Any, schema_path: Path) -> str | None:
    if not isinstance(payload, dict):
        return "release decision artifact root is not an object"

    if not schema_path.exists():
        return f"release decision schema is missing: {_rel(schema_path)}"

    try:
        import jsonschema
    except Exception as exc:
        return f"jsonschema import failed: {exc}"

    try:
        schema_payload = _read_json(schema_path)
    except Exception as exc:
        return f"release decision schema could not be read: {exc}"

    try:
        jsonschema.Draft202012Validator.check_schema(schema_payload)
    except Exception as exc:
        return f"release decision schema is not a valid JSON Schema: {exc}"

    try:
        validator = jsonschema.Draft202012Validator(
            schema_payload,
            format_checker=jsonschema.FormatChecker(),
        )
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    except Exception as exc:
        return f"release decision artifact schema validation failed to run: {exc}"

    if errors:
        rendered_errors = []
        for error in errors[:5]:
            path = ".".join(str(part) for part in error.path) or "<root>"
            rendered_errors.append(f"{path}: {error.message}")

        suffix = ""
        if len(errors) > 5:
            suffix = f" (+{len(errors) - 5} more)"

        return (
            "release decision artifact failed schema validation: "
            + "; ".join(rendered_errors)
            + suffix
        )

    return None


def _render_release_decision(input_path: Path, payload: dict[str, Any]) -> str:
    release_level = str(payload.get("release_level", "UNKNOWN"))
    target = payload.get("target", "missing")
    run_mode = payload.get("run_mode", "missing")
    required_gates_passed = payload.get("required_gates_passed", "missing")

    active_gate_sets = ", ".join(str(x) for x in _as_list(payload.get("active_gate_sets")))
    effective_required_gates = _as_list(payload.get("effective_required_gates"))
    blocking_reasons = _as_list(payload.get("blocking_reasons"))
    decision_basis = _as_list(payload.get("decision_basis"))
    conditions = payload.get("conditions") if isinstance(payload.get("conditions"), dict) else {}

    producer = payload.get("producer") if isinstance(payload.get("producer"), dict) else {}
    producer_label = (
        f"{producer.get('name', 'unknown')}"
        f"@{producer.get('version', 'unknown')}"
    )

    rows = [
        _render_key_value("Artifact", _rel(input_path)),
        _render_key_value("Release level", release_level),
        _render_key_value("Target", target),
        _render_key_value("Run mode", run_mode),
        _render_key_value("Required gates passed", _as_bool_label(required_gates_passed)),
        _render_key_value("Active gate sets", active_gate_sets or "missing"),
        _render_key_value("Producer", producer_label),
        _render_key_value("Status path", payload.get("status_path", "missing")),
        _render_key_value("Policy path", payload.get("policy_path", "missing")),
        _render_key_value("Status SHA-256", payload.get("status_sha256", "missing")),
        _render_key_value("Policy SHA-256", payload.get("policy_sha256", "missing")),
        _render_key_value("Git SHA", payload.get("git_sha", "missing")),
    ]

    return f"""
{_render_styles()}
<section id="release-decision-v0" class="release-decision-v0">
  <h2>Release decision v0</h2>
  <p class="release-decision-note">
    Read-only Quality Ledger section. This section renders the materialized
    <code>release_decision_v0.json</code> artifact; it does not compute or
    redefine release semantics.
  </p>

  {_status_pill(release_level, _css_class_for_release_level(release_level))}

  <div class="release-decision-grid">
    {"".join(rows)}
  </div>

  {_render_conditions(conditions)}

  <div class="release-decision-section-title">Effective required gates</div>
  {_render_list(effective_required_gates, empty_label="No effective required gates recorded.")}

  <div class="release-decision-section-title">Blocking reasons</div>
  {_render_list(blocking_reasons, empty_label="No blocking reasons recorded.")}

  <div class="release-decision-section-title">Decision basis</div>
  {_render_list(decision_basis, empty_label="No decision basis recorded.")}

  <div class="release-decision-warning">
    <strong>Authority boundary:</strong>
    this Ledger section is a reader of <code>release_decision_v0.json</code>.
    It must not override <code>status.json</code>, <code>check_gates.py</code>,
    the active gate set, or the primary release-gating workflow.
  </div>
</section>
""".strip()


def render_release_decision_section(
    input_path: Path, schema_path: Path = DEFAULT_SCHEMA
) -> tuple[str, int]:
    if not input_path.exists():
        return _render_missing(input_path), 0

    try:
        payload = _read_json(input_path)
    except Exception as exc:
        return _render_invalid(input_path, str(exc)), 1

    error = _release_decision_artifact_error(payload, schema_path)
    if error is not None:
        return _render_invalid(input_path, error), 1

    return _render_release_decision(input_path, payload), 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render a read-only Quality Ledger HTML section from "
            "release_decision_v0.json."
        )
    )

    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to release_decision_v0.json.",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Path to write the rendered HTML fragment.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to schemas/release_decision_v0.schema.json.",
    )
    parser.add_argument(
        "--strict-missing",
        action="store_true",
        help="Return exit code 1 when the release decision artifact is missing.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    input_path = Path(args.input)
    out_path = Path(args.out)
    schema_path = Path(args.schema)

    if not input_path.is_absolute():
        input_path = REPO_ROOT / input_path
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    if not schema_path.is_absolute():
        schema_path = REPO_ROOT / schema_path

    rendered, rc = render_release_decision_section(input_path, schema_path)

    if args.strict_missing and not input_path.exists():
        rc = 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered + "\n", encoding="utf-8")

    if rc == 0:
        print(f"OK: wrote release decision ledger section: {_rel(out_path)}")
    else:
        print(f"ERROR: wrote release decision ledger section with invalid input: {_rel(out_path)}")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
