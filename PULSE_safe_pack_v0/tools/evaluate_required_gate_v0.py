#!/usr/bin/env python3
"""Evaluate one canonical ``gates.required`` entry and record candidate evidence.

The dispatcher is intentionally fail-closed. It emits ``pass: true`` only for
registered deterministic evaluators backed by checked-in evidence and tools.
An unimplemented gate is recorded as failed; it is never promoted from a static
boolean, a fixture name, or a missing artifact.

The output is candidate evidence only. It does not write ``status.json``,
materialize ``release_required`` gates, replace ``check_gates.py``, or create
release authority.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml
from jsonschema import Draft202012Validator, FormatChecker


RESULT_SCHEMA = "required_gate_evaluation_result_v0"
PLAN_SCHEMA = "required_gate_evaluation_plan_v0"
EVALUATOR_ID = "pulse_required_gate_dispatcher_v0"
EVALUATOR_VERSION = "0.1.0"

TOOL_PATH = "PULSE_safe_pack_v0/tools/evaluate_required_gate_v0.py"
POLICY_PATH = "pulse_gate_policy_v0.yml"
REGISTRY_PATH = "pulse_gate_registry_v0.yml"
PLAN_PATH = (
    "PULSE_safe_pack_v0/profiles/"
    "required_gate_evaluations_v0.json"
)
SCHEMA_PATH = (
    "schemas/required_gate_evaluation_result_v0.schema.json"
)
OUTPUT_ROOT = (
    "PULSE_safe_pack_v0/artifacts/required_gate_inputs"
)
WORK_ROOT = (
    "PULSE_safe_pack_v0/artifacts/"
    "required_gate_evaluator_work"
)

GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GATE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class UniqueYamlLoader(yaml.SafeLoader):
    pass


def _unique_yaml_mapping(
    loader: UniqueYamlLoader,
    node: Any,
    deep: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(
            key_node,
            deep=deep,
        )

        if key in result:
            raise ValueError(
                f"duplicate YAML key {key!r}"
            )

        result[key] = loader.construct_object(
            value_node,
            deep=deep,
        )

    return result


UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _unique_yaml_mapping,
)


def _unique_json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for key, value in pairs:
        if key in result:
            raise ValueError(
                f"duplicate JSON key {key!r}"
            )

        result[key] = value

    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(
        f"non-finite JSON constant {value!r}"
    )


def load_json(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: "
                f"{path}"
            )
            return None

        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_nonfinite,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"{label} is not valid JSON: {exc}"
        )
        return None

    if not isinstance(payload, dict):
        errors.append(
            f"{label} must be a JSON object"
        )
        return None

    return payload


def load_yaml(
    path: Path,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: "
                f"{path}"
            )
            return None

        payload = yaml.load(
            path.read_text(encoding="utf-8"),
            Loader=UniqueYamlLoader,
        )

    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"{label} is not valid YAML: {exc}"
        )
        return None

    if not isinstance(payload, dict):
        errors.append(
            f"{label} must be a YAML mapping"
        )
        return None

    return payload


def sha256_file(
    path: Path,
    label: str,
    errors: list[str],
) -> str | None:
    try:
        if path.is_symlink() or not path.is_file():
            errors.append(
                f"{label} not found as a regular file: "
                f"{path}"
            )
            return None

        digest = hashlib.sha256()

        with path.open("rb") as handle:
            for chunk in iter(
                lambda: handle.read(65536),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()

    except OSError as exc:
        errors.append(
            f"{label} could not be hashed: {exc}"
        )
        return None


def repo_relative(
    repo: Path,
    path: Path,
) -> str:
    return (
        path.resolve()
        .relative_to(repo.resolve())
        .as_posix()
    )


def canonical_file(
    repo: Path,
    relative_path: str,
    label: str,
    errors: list[str],
) -> Path | None:
    path = (repo / relative_path).resolve()

    try:
        path.relative_to(repo)

    except ValueError:
        errors.append(
            f"{label} escapes repository root: "
            f"{relative_path!r}"
        )
        return None

    if path.is_symlink() or not path.is_file():
        errors.append(
            f"{label} not found as a checked-in "
            f"regular file: {relative_path!r}"
        )
        return None

    return path


def safe_output(
    repo: Path,
    supplied: Path,
    errors: list[str],
) -> Path | None:
    path = (
        supplied.resolve()
        if supplied.is_absolute()
        else (repo / supplied).resolve()
    )

    root = (repo / OUTPUT_ROOT).resolve()

    try:
        path.relative_to(root)

    except ValueError:
        errors.append(
            f"output path must remain under "
            f"{OUTPUT_ROOT!r}"
        )
        return None

    if path == root:
        errors.append(
            "output path must name a file"
        )
        return None

    return path


def created_utc() -> str:
    source_date_epoch = os.getenv(
        "SOURCE_DATE_EPOCH",
        "",
    ).strip()

    if source_date_epoch:
        if not source_date_epoch.isdigit():
            raise ValueError(
                "SOURCE_DATE_EPOCH must be an "
                "integer Unix timestamp"
            )

        value = dt.datetime.fromtimestamp(
            int(source_date_epoch),
            tz=dt.timezone.utc,
        )

    else:
        value = dt.datetime.now(
            dt.timezone.utc
        )

    return (
        value.replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def artifact_ref(
    repo: Path,
    path: Path,
    kind: str,
    schema_version: str | None,
    errors: list[str],
) -> dict[str, Any] | None:
    digest = sha256_file(
        path,
        f"artifact {path}",
        errors,
    )

    if digest is None:
        return None

    return {
        "path": repo_relative(repo, path),
        "sha256": digest,
        "kind": kind,
        "schema_version": schema_version,
    }


def add_ref(
    refs: dict[str, dict[str, Any]],
    repo: Path,
    path: Path,
    kind: str,
    schema_version: str | None,
    errors: list[str],
) -> str | None:
    item = artifact_ref(
        repo,
        path,
        kind,
        schema_version,
        errors,
    )

    if item is None:
        return None

    relative = str(item["path"])

    if (
        relative in refs
        and refs[relative] != item
    ):
        errors.append(
            "conflicting artifact reference for "
            f"{relative!r}"
        )
        return None

    refs[relative] = item
    return relative


def required_gates(
    policy: dict[str, Any],
    errors: list[str],
) -> list[str]:
    gates = policy.get("gates")

    if not isinstance(gates, dict):
        errors.append(
            "policy must contain canonical "
            "top-level gates mapping"
        )
        return []

    required = gates.get("required")

    if (
        not isinstance(required, list)
        or not required
    ):
        errors.append(
            "policy gates.required must be "
            "a non-empty array"
        )
        return []

    result: list[str] = []
    seen: set[str] = set()

    for raw in required:
        gate = (
            raw.strip()
            if isinstance(raw, str)
            else ""
        )

        if not GATE_ID_RE.fullmatch(gate):
            errors.append(
                "policy gates.required contains "
                f"invalid gate id {raw!r}"
            )

        elif gate in seen:
            errors.append(
                "policy gates.required contains "
                f"duplicate gate id {gate!r}"
            )

        else:
            seen.add(gate)
            result.append(gate)

    return result


def registry_gates(
    registry: dict[str, Any],
    errors: list[str],
) -> set[str]:
    gates = registry.get("gates")

    if (
        not isinstance(gates, dict)
        or not gates
    ):
        errors.append(
            "registry must contain a non-empty "
            "top-level gates mapping"
        )
        return set()

    result: set[str] = set()

    for raw in gates:
        gate = (
            raw.strip()
            if isinstance(raw, str)
            else ""
        )

        if not GATE_ID_RE.fullmatch(gate):
            errors.append(
                "registry contains invalid gate id "
                f"{raw!r}"
            )

        else:
            result.add(gate)

    return result


def flag_value(
    command: list[Any],
    flag: str,
) -> str | None:
    try:
        index = command.index(flag)

    except ValueError:
        return None

    if (
        index + 1 >= len(command)
        or not isinstance(
            command[index + 1],
            str,
        )
    ):
        return None

    return command[index + 1]


def validate_plan_entry(
    plan: dict[str, Any],
    gate_id: str,
    evaluation_id: str,
    output_path: str,
    errors: list[str],
) -> None:
    if plan.get("schema_version") != PLAN_SCHEMA:
        errors.append(
            "plan.schema_version must be "
            f"{PLAN_SCHEMA!r}"
        )

    evaluations = plan.get("evaluations")

    if not isinstance(evaluations, dict):
        errors.append(
            "plan.evaluations must be an object"
        )
        return

    entry = evaluations.get(gate_id)

    if not isinstance(entry, dict):
        errors.append(
            "plan has no object entry for gate "
            f"{gate_id!r}"
        )
        return

    if (
        entry.get("evaluation_id")
        != evaluation_id
    ):
        errors.append(
            "plan evaluation_id mismatch: expected "
            f"{evaluation_id!r}, got "
            f"{entry.get('evaluation_id')!r}"
        )

    command = entry.get("command")

    if (
        not isinstance(command, list)
        or len(command) < 2
    ):
        errors.append(
            "plan command must be an array "
            "with an evaluator path"
        )

    else:
        if (
            command[0] != "{python}"
            or command[1] != TOOL_PATH
        ):
            errors.append(
                "plan command must invoke the "
                "canonical required-gate dispatcher"
            )

        if (
            flag_value(command, "--gate-id")
            != gate_id
        ):
            errors.append(
                "plan command --gate-id must "
                "match the plan entry key"
            )

        if (
            flag_value(command, "--out")
            != output_path
        ):
            errors.append(
                "plan command --out must match "
                "the requested output path"
            )

    result = entry.get("result")

    if not isinstance(result, dict):
        errors.append(
            "plan result must be an object"
        )

    else:
        if (
            result.get("artifact")
            != output_path
        ):
            errors.append(
                "plan result.artifact must match "
                "the requested output path"
            )

        if (
            result.get("json_pointer")
            != "/pass"
        ):
            errors.append(
                "plan result.json_pointer must be "
                "literal '/pass'"
            )

    artifacts = entry.get(
        "evidence_artifacts"
    )

    if (
        not isinstance(artifacts, list)
        or len(artifacts) != 1
    ):
        errors.append(
            "plan must declare exactly one "
            "gate result artifact"
        )

    elif not isinstance(artifacts[0], dict):
        errors.append(
            "plan evidence artifact descriptor "
            "must be an object"
        )

    else:
        if (
            artifacts[0].get("path")
            != output_path
        ):
            errors.append(
                "plan evidence artifact path "
                "must match output path"
            )

        if (
            artifacts[0].get(
                "schema_version"
            )
            != RESULT_SCHEMA
        ):
            errors.append(
                "plan evidence artifact "
                "schema_version must be "
                f"{RESULT_SCHEMA!r}"
            )


def validate_schema(
    payload: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    result: list[str] = []

    for error in sorted(
        validator.iter_errors(payload),
        key=lambda item: list(
            item.absolute_path
        ),
    ):
        location = ".".join(
            str(part)
            for part in error.absolute_path
        )

        result.append(
            (
                f"{location}: "
                if location
                else ""
            )
            + error.message
        )

    return result


def json_pointer(
    payload: Any,
    pointer: str,
) -> Any:
    current = payload

    for raw in pointer.split("/")[1:]:
        token = (
            raw.replace("~1", "/")
            .replace("~0", "~")
        )

        if (
            isinstance(current, dict)
            and token in current
        ):
            current = current[token]

        elif (
            isinstance(current, list)
            and token.isdigit()
            and int(token) < len(current)
        ):
            current = current[int(token)]

        else:
            raise KeyError(pointer)

    return current


def reset_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        if (
            path.is_symlink()
            or not path.is_dir()
        ):
            path.unlink()

        else:
            shutil.rmtree(path)

    path.mkdir(
        parents=True,
        exist_ok=True,
    )


@dataclass(frozen=True)
class Context:
    repo: Path
    gate_id: str
    evaluation_id: str
    output: Path
    created_utc: str
    git_sha: str
    run_key: str
    repository: str
    release_candidate: str | None
    policy_sha256: str
    registry_sha256: str
    plan_sha256: str
    tool_sha256: str
    timeout_seconds: int

    @property
    def work_dir(self) -> Path:
        return (
            self.repo
            / WORK_ROOT
            / self.gate_id
        )


@dataclass(frozen=True)
class Recipe:
    builder: str
    sources: tuple[
        tuple[str, str],
        ...,
    ]
    summary_name: str
    pointer: str
    details: str
    arguments: Callable[
        [Context, Path, dict[str, Path]],
        list[str],
    ]
    extra_inputs: tuple[str, ...] = ()


def common_builder_args(
    ctx: Context,
    summary: Path,
) -> list[str]:
    return [
        "--out",
        str(summary),
        "--run_id",
        ctx.run_key,
        "--created_utc",
        ctx.created_utc,
        "--tool",
        EVALUATOR_ID,
        "--tool_version",
        EVALUATOR_VERSION,
        "--git_sha",
        ctx.git_sha,
    ]


def refusal_args(
    ctx: Context,
    summary: Path,
    sources: dict[str, Path],
) -> list[str]:
    return [
        "--result_json",
        str(sources["result"]),
        "--input_manifest",
        repo_relative(
            ctx.repo,
            sources["manifest"],
        ),
        *common_builder_args(
            ctx,
            summary,
        ),
        "--notes",
        (
            "Current-run deterministic reduction "
            "over checked-in refusal reference "
            "evidence."
        ),
    ]


def sanit_args(
    ctx: Context,
    summary: Path,
    sources: dict[str, Path],
) -> list[str]:
    return [
        "--result_json",
        str(sources["result"]),
        "--input_manifest",
        repo_relative(
            ctx.repo,
            sources["manifest"],
        ),
        *common_builder_args(
            ctx,
            summary,
        ),
        "--notes",
        (
            "Current-run deterministic reduction "
            "over checked-in sanitization "
            "reference evidence."
        ),
    ]


def q1_args(
    ctx: Context,
    summary: Path,
    sources: dict[str, Path],
) -> list[str]:
    return [
        "--labels_jsonl",
        str(sources["labels"]),
        "--input_manifest",
        repo_relative(
            ctx.repo,
            sources["manifest"],
        ),
        *common_builder_args(
            ctx,
            summary,
        ),
        "--notes",
        (
            "Current-run deterministic reduction "
            "over checked-in groundedness labels."
        ),
    ]


def q4_args(
    ctx: Context,
    summary: Path,
    sources: dict[str, Path],
) -> list[str]:
    return [
        "--stats_json",
        str(sources["stats"]),
        "--input_manifest",
        repo_relative(
            ctx.repo,
            sources["manifest"],
        ),
        "--spec",
        repo_relative(
            ctx.repo,
            sources["spec"],
        ),
        *common_builder_args(
            ctx,
            summary,
        ),
        "--notes",
        (
            "Current-run deterministic reduction "
            "over checked-in canonical Q4 SLO "
            "reference evidence."
        ),
    ]


def refusal_delta_args(
    ctx: Context,
    summary: Path,
    sources: dict[str, Path],
) -> list[str]:
    return [
        "--pairs",
        str(sources["pairs"]),
        "--out",
        str(summary),
        "--policy_config",
        str(sources["policy_config"]),
    ]


RECIPES: dict[str, Recipe] = {
    "pass_controls_refusal": Recipe(
        builder=(
            "PULSE_safe_pack_v0/tools/"
            "build_refusal_smoke_reference_summary.py"
        ),
        sources=(
            (
                "result",
                "examples/"
                "refusal_smoke_result.pass_v0.json",
            ),
            (
                "manifest",
                "examples/"
                "refusal_smoke_input_manifest.json",
            ),
        ),
        summary_name=(
            "refusal_smoke_reference_summary.json"
        ),
        pointer="/pass",
        details=(
            "Refusal control reducer emitted "
            "literal pass=true."
        ),
        arguments=refusal_args,
    ),
    "refusal_delta_pass": Recipe(
        builder=(
            "PULSE_safe_pack_v0/tools/"
            "refusal_delta.py"
        ),
        sources=(
            (
                "pairs",
                "PULSE_safe_pack_v0/examples/"
                "refusal_pairs.jsonl",
            ),
            (
                "policy_config",
                "PULSE_safe_pack_v0/profiles/"
                "pulse_policy.yaml",
            ),
        ),
        extra_inputs=(
            "PULSE_safe_pack_v0/tools/"
            "refusal_delta_calc.py",
        ),
        summary_name=(
            "refusal_delta_summary.json"
        ),
        pointer="/pass",
        details=(
            "Refusal-delta evaluator emitted "
            "literal pass=true."
        ),
        arguments=refusal_delta_args,
    ),
    "pass_controls_sanit": Recipe(
        builder=(
            "PULSE_safe_pack_v0/tools/"
            "build_sanit_smoke_reference_summary.py"
        ),
        sources=(
            (
                "result",
                "examples/"
                "sanit_smoke_result.pass_v0.json",
            ),
            (
                "manifest",
                "examples/"
                "sanit_smoke_input_manifest.json",
            ),
        ),
        summary_name=(
            "sanit_smoke_reference_summary.json"
        ),
        pointer="/pass_controls_sanit",
        details=(
            "Sanitization control reducer emitted "
            "pass_controls_sanit=true."
        ),
        arguments=sanit_args,
    ),
    "sanitization_effective": Recipe(
        builder=(
            "PULSE_safe_pack_v0/tools/"
            "build_sanit_smoke_reference_summary.py"
        ),
        sources=(
            (
                "result",
                "examples/"
                "sanit_smoke_result.pass_v0.json",
            ),
            (
                "manifest",
                "examples/"
                "sanit_smoke_input_manifest.json",
            ),
        ),
        summary_name=(
            "sanit_effectiveness_reference_summary.json"
        ),
        pointer="/sanitization_effective",
        details=(
            "Sanitization reducer emitted "
            "sanitization_effective=true."
        ),
        arguments=sanit_args,
    ),
    "q1_grounded_ok": Recipe(
        builder=(
            "PULSE_safe_pack_v0/tools/"
            "build_q1_reference_summary.py"
        ),
        sources=(
            (
                "labels",
                "examples/"
                "q1_reference_labels.pass_120.jsonl",
            ),
            (
                "manifest",
                "examples/"
                "q1_reference_input_manifest.json",
            ),
        ),
        extra_inputs=(
            "metrics/specs/"
            "q1_groundedness_v0.yml",
        ),
        summary_name=(
            "q1_groundedness_reference_summary.json"
        ),
        pointer="/pass",
        details=(
            "Q1 groundedness reducer emitted "
            "literal pass=true."
        ),
        arguments=q1_args,
    ),
    "q4_slo_ok": Recipe(
        builder=(
            "PULSE_safe_pack_v0/tools/"
            "build_q4_slo_reference_summary.py"
        ),
        sources=(
            (
                "stats",
                "examples/"
                "q4_slo_stats.pass_v0.json",
            ),
            (
                "manifest",
                "examples/"
                "q4_slo_input_manifest.json",
            ),
            (
                "spec",
                "metrics/specs/"
                "q4_slo_v0.yml",
            ),
        ),
        extra_inputs=(
            "schemas/metrics/"
            "q4_slo_summary_v0.schema.json",
        ),
        summary_name=(
            "q4_slo_reference_summary.json"
        ),
        pointer="/pass",
        details=(
            "Canonical Q4 SLO reducer emitted "
            "literal pass=true from mean-cost, "
            "latency, evidence-count, and "
            "measurement-quality checks."
        ),
        arguments=q4_args,
    ),
}


UNSUPPORTED_REASONS = {
    "effect_present": (
        "No canonical executable evidence rule "
        "is registered for effect_present; "
        "refusal-delta presence or magnitude is "
        "not silently reinterpreted as this gate."
    ),
    "psf_monotonicity_ok": (
        "No dedicated current-run PSF "
        "monotonicity evaluator is registered."
    ),
    "psf_mono_shift_resilient": (
        "No monotonicity shift evaluator and "
        "shift evidence set are registered."
    ),
    "pass_controls_comm": (
        "No dedicated current-run "
        "communication-control evaluator "
        "is registered."
    ),
    "psf_commutativity_ok": (
        "No dedicated current-run PSF "
        "commutativity evaluator is registered."
    ),
    "psf_comm_shift_resilient": (
        "No commutativity shift evaluator and "
        "shift evidence set are registered."
    ),
    "sanit_shift_resilient": (
        "No sanitization shift evaluator and "
        "shift evidence set are registered."
    ),
    "psf_action_monotonicity_ok": (
        "No dedicated current-run "
        "action-monotonicity evaluator "
        "is registered."
    ),
    "psf_idempotence_ok": (
        "No dedicated current-run idempotence "
        "evaluator is registered."
    ),
    "psf_path_independence_ok": (
        "No dedicated current-run "
        "path-independence evaluator "
        "is registered."
    ),
    "psf_pii_monotonicity_ok": (
        "No dedicated current-run "
        "PII-monotonicity evaluator "
        "is registered."
    ),
    "q2_consistency_ok": (
        "No deterministic Q2 agreement-group "
        "producer and evidence set are registered."
    ),
    "q3_fairness_ok": (
        "No deterministic Q3 slice-aware "
        "fairness producer and evidence set "
        "are registered."
    ),
}


SPEC_BY_GATE = {
    "q1_grounded_ok": (
        "metrics/specs/q1_groundedness_v0.yml"
    ),
    "q2_consistency_ok": (
        "metrics/specs/q2_consistency_v0.yml"
    ),
    "q3_fairness_ok": (
        "metrics/specs/q3_fairness_v0.yml"
    ),
    "q4_slo_ok": (
        "metrics/specs/q4_slo_v0.yml"
    ),
}


def run_recipe(
    ctx: Context,
    recipe: Recipe,
    refs: dict[str, dict[str, Any]],
) -> tuple[
    dict[str, Any],
    list[str],
    list[str],
]:
    diagnostics: list[str] = []

    warnings = [
        (
            "This current-run evaluator reduces "
            "checked-in archived reference evidence; "
            "it proves deterministic reference "
            "mechanics, not live production-model "
            "behavior."
        )
    ]

    reset_directory(ctx.work_dir)

    summary = (
        ctx.work_dir
        / recipe.summary_name
    )

    stdout_path = (
        ctx.work_dir
        / "builder.stdout.txt"
    )

    stderr_path = (
        ctx.work_dir
        / "builder.stderr.txt"
    )

    builder = canonical_file(
        ctx.repo,
        recipe.builder,
        "gate evaluator",
        diagnostics,
    )

    sources: dict[str, Path] = {}

    for name, source_path in recipe.sources:
        source = canonical_file(
            ctx.repo,
            source_path,
            f"{ctx.gate_id} source {name}",
            diagnostics,
        )

        if source is not None:
            sources[name] = source

            add_ref(
                refs,
                ctx.repo,
                source,
                "evaluation_input",
                None,
                diagnostics,
            )

    for extra_path in recipe.extra_inputs:
        extra = canonical_file(
            ctx.repo,
            extra_path,
            (
                f"{ctx.gate_id} "
                "supporting input"
            ),
            diagnostics,
        )

        if extra is not None:
            add_ref(
                refs,
                ctx.repo,
                extra,
                "evaluation_tool_dependency",
                None,
                diagnostics,
            )

    command = [
        sys.executable,
        (
            str(builder)
            if builder
            else recipe.builder
        ),
    ]

    if (
        builder is not None
        and not diagnostics
    ):
        command.extend(
            recipe.arguments(
                ctx,
                summary,
                sources,
            )
        )

        add_ref(
            refs,
            ctx.repo,
            builder,
            "evaluation_tool",
            None,
            diagnostics,
        )

    exit_code: int | None = None
    stdout = ""
    stderr = ""

    if not diagnostics:
        environment = os.environ.copy()

        environment.update(
            {
                "PULSE_RUN_MODE": "prod",
                "PULSE_RUN_KEY": ctx.run_key,
                "PULSE_GIT_SHA": ctx.git_sha,
                "GITHUB_SHA": ctx.git_sha,
            }
        )

        try:
            result = subprocess.run(
                command,
                cwd=ctx.repo,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=ctx.timeout_seconds,
                check=False,
            )

            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr

        except subprocess.TimeoutExpired as exc:
            stdout = (
                exc.stdout.decode(
                    errors="replace"
                )
                if isinstance(
                    exc.stdout,
                    bytes,
                )
                else str(
                    exc.stdout or ""
                )
            )

            stderr = (
                exc.stderr.decode(
                    errors="replace"
                )
                if isinstance(
                    exc.stderr,
                    bytes,
                )
                else str(
                    exc.stderr or ""
                )
            )

            diagnostics.append(
                "evaluation timed out after "
                f"{ctx.timeout_seconds} seconds"
            )

        except OSError as exc:
            diagnostics.append(
                "evaluation command could not run: "
                f"{exc}"
            )

    stdout_path.write_text(
        stdout,
        encoding="utf-8",
    )

    stderr_path.write_text(
        stderr,
        encoding="utf-8",
    )

    evidence_paths: list[str] = []

    for path, kind in (
        (
            stdout_path,
            "evaluation_stdout",
        ),
        (
            stderr_path,
            "evaluation_stderr",
        ),
    ):
        relative = add_ref(
            refs,
            ctx.repo,
            path,
            kind,
            None,
            diagnostics,
        )

        if relative:
            evidence_paths.append(relative)

    if exit_code not in (None, 0):
        diagnostics.append(
            "evaluation command exited with "
            f"code {exit_code}"
        )

    summary_payload: dict[str, Any] | None = None

    if (
        summary.is_symlink()
        or not summary.is_file()
    ):
        diagnostics.append(
            "evaluation did not produce the "
            "declared summary artifact"
        )

    else:
        relative = add_ref(
            refs,
            ctx.repo,
            summary,
            "evaluation_summary",
            None,
            diagnostics,
        )

        if relative:
            evidence_paths.append(relative)

        summary_payload = load_json(
            summary,
            (
                f"{ctx.gate_id} "
                "evaluation summary"
            ),
            diagnostics,
        )

    if summary_payload is not None:
        try:
            value = json_pointer(
                summary_payload,
                recipe.pointer,
            )

        except KeyError:
            diagnostics.append(
                "summary JSON pointer "
                f"{recipe.pointer!r} is missing"
            )

        else:
            if value is not True:
                diagnostics.append(
                    "summary JSON pointer "
                    f"{recipe.pointer!r} must be "
                    "literal true"
                )

    for source in sources.values():
        relative = repo_relative(
            ctx.repo,
            source,
        )

        if relative not in evidence_paths:
            evidence_paths.append(relative)

    if builder is not None:
        relative = repo_relative(
            ctx.repo,
            builder,
        )

        if relative not in evidence_paths:
            evidence_paths.append(relative)

    if not evidence_paths:
        evidence_paths = sorted(refs)[:1]

    passed = (
        exit_code == 0
        and summary_payload is not None
        and not diagnostics
    )

    check = {
        "check_id": (
            f"pulse.required."
            f"{ctx.gate_id}.reference.v0"
        ),
        "kind": "python",
        "passed": passed,
        "details": (
            recipe.details
            if passed
            else (
                f"{recipe.details} "
                "The check failed closed."
            )
        ),
        "command": command,
        "exit_code": exit_code,
        "evidence_paths": sorted(
            set(evidence_paths)
        ),
        "diagnostics": diagnostics,
    }

    return check, diagnostics, warnings


def unsupported_check(
    ctx: Context,
    refs: dict[str, dict[str, Any]],
) -> tuple[
    dict[str, Any],
    list[str],
    list[str],
]:
    reason = UNSUPPORTED_REASONS.get(
        ctx.gate_id,
        (
            "No dedicated current-run evaluator "
            "is registered for this required gate."
        ),
    )

    spec_path = SPEC_BY_GATE.get(
        ctx.gate_id
    )

    if spec_path:
        ignored: list[str] = []

        spec = canonical_file(
            ctx.repo,
            spec_path,
            (
                f"{ctx.gate_id} "
                "metric specification"
            ),
            ignored,
        )

        if spec is not None:
            add_ref(
                refs,
                ctx.repo,
                spec,
                "metric_spec",
                Path(spec_path).stem,
                ignored,
            )

    diagnostics = [reason]

    check = {
        "check_id": (
            f"pulse.required."
            f"{ctx.gate_id}.implementation.v0"
        ),
        "kind": "contract",
        "passed": False,
        "details": (
            "A required gate may pass only "
            "through a dedicated, checked-in, "
            "current-run evaluator with recorded "
            "evidence. No fallback PASS is allowed."
        ),
        "command": [
            "internal",
            (
                "require-dedicated-"
                "current-run-evaluator"
            ),
            ctx.gate_id,
        ],
        "exit_code": None,
        "evidence_paths": sorted(refs),
        "diagnostics": diagnostics,
    }

    return check, diagnostics, []


def identity(
    errors: list[str],
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    if (
        os.getenv(
            "PULSE_RUN_MODE",
            "",
        )
        .strip()
        .lower()
        != "prod"
    ):
        errors.append(
            "PULSE_RUN_MODE must be literal 'prod'"
        )

    git_sha = (
        os.getenv(
            "PULSE_GIT_SHA",
            "",
        )
        .strip()
        .lower()
        or os.getenv(
            "GITHUB_SHA",
            "",
        )
        .strip()
        .lower()
    )

    if not GIT_SHA_RE.fullmatch(git_sha):
        errors.append(
            "PULSE_GIT_SHA or GITHUB_SHA must be "
            "a concrete 40-hex commit SHA"
        )
        git_sha = None

    run_key = os.getenv(
        "PULSE_RUN_KEY",
        "",
    ).strip()

    if not run_key:
        errors.append(
            "PULSE_RUN_KEY must be a non-empty "
            "current-run identity"
        )
        run_key = None

    repository = os.getenv(
        "GITHUB_REPOSITORY",
        "",
    ).strip()

    if not repository:
        errors.append(
            "GITHUB_REPOSITORY must be a "
            "non-empty repository identity"
        )
        repository = None

    return git_sha, run_key, repository


def build_result(
    repo: Path,
    gate_id: str,
    output: Path,
    timeout_seconds: int,
) -> tuple[
    dict[str, Any] | None,
    list[str],
    bool,
]:
    errors: list[str] = []

    if not GATE_ID_RE.fullmatch(gate_id):
        errors.append(
            f"invalid gate id {gate_id!r}"
        )

    env_gate = os.getenv(
        "PULSE_REQUIRED_GATE_ID",
        "",
    ).strip()

    if env_gate != gate_id:
        errors.append(
            "PULSE_REQUIRED_GATE_ID must match "
            f"--gate-id (expected {gate_id!r}, "
            f"got {env_gate!r})"
        )

    evaluation_id = os.getenv(
        "PULSE_REQUIRED_GATE_EVALUATION_ID",
        "",
    ).strip()

    if not evaluation_id:
        errors.append(
            "PULSE_REQUIRED_GATE_EVALUATION_ID "
            "must be non-empty"
        )

    if timeout_seconds <= 0:
        errors.append(
            "timeout-seconds must be greater "
            "than zero"
        )

    policy_path = canonical_file(
        repo,
        POLICY_PATH,
        "policy",
        errors,
    )

    registry_path = canonical_file(
        repo,
        REGISTRY_PATH,
        "registry",
        errors,
    )

    plan_path = canonical_file(
        repo,
        PLAN_PATH,
        "evaluation plan",
        errors,
    )

    schema_path = canonical_file(
        repo,
        SCHEMA_PATH,
        "result schema",
        errors,
    )

    tool_path = canonical_file(
        repo,
        TOOL_PATH,
        "dispatcher tool",
        errors,
    )

    policy = (
        load_yaml(
            policy_path,
            "policy",
            errors,
        )
        if policy_path
        else None
    )

    registry = (
        load_yaml(
            registry_path,
            "registry",
            errors,
        )
        if registry_path
        else None
    )

    plan = (
        load_json(
            plan_path,
            "evaluation plan",
            errors,
        )
        if plan_path
        else None
    )

    schema = (
        load_json(
            schema_path,
            "result schema",
            errors,
        )
        if schema_path
        else None
    )

    required = (
        required_gates(
            policy,
            errors,
        )
        if policy
        else []
    )

    registry_ids = (
        registry_gates(
            registry,
            errors,
        )
        if registry
        else set()
    )

    if gate_id not in required:
        errors.append(
            f"gate {gate_id!r} is not in "
            "canonical gates.required"
        )

    if gate_id not in registry_ids:
        errors.append(
            f"gate {gate_id!r} is not present "
            "in the gate registry"
        )

    output_relative = repo_relative(
        repo,
        output,
    )

    if plan and evaluation_id:
        validate_plan_entry(
            plan,
            gate_id,
            evaluation_id,
            output_relative,
            errors,
        )

    git_sha, run_key, repository = identity(
        errors
    )

    policy_sha = (
        sha256_file(
            policy_path,
            "policy",
            errors,
        )
        if policy_path
        else None
    )

    registry_sha = (
        sha256_file(
            registry_path,
            "registry",
            errors,
        )
        if registry_path
        else None
    )

    plan_sha = (
        sha256_file(
            plan_path,
            "evaluation plan",
            errors,
        )
        if plan_path
        else None
    )

    tool_sha = (
        sha256_file(
            tool_path,
            "dispatcher tool",
            errors,
        )
        if tool_path
        else None
    )

    try:
        timestamp = created_utc()

    except ValueError as exc:
        errors.append(str(exc))
        timestamp = ""

    if errors:
        return None, errors, False

    assert policy_path
    assert registry_path
    assert plan_path
    assert schema_path
    assert tool_path
    assert schema
    assert git_sha
    assert run_key
    assert repository
    assert policy_sha
    assert registry_sha
    assert plan_sha
    assert tool_sha

    ctx = Context(
        repo=repo,
        gate_id=gate_id,
        evaluation_id=evaluation_id,
        output=output,
        created_utc=timestamp,
        git_sha=git_sha,
        run_key=run_key,
        repository=repository,
        release_candidate=(
            os.getenv(
                "GITHUB_REF_NAME",
                "",
            ).strip()
            or None
        ),
        policy_sha256=policy_sha,
        registry_sha256=registry_sha,
        plan_sha256=plan_sha,
        tool_sha256=tool_sha,
        timeout_seconds=timeout_seconds,
    )

    refs: dict[str, dict[str, Any]] = {}
    ref_errors: list[str] = []

    for path, kind, schema_version in (
        (
            policy_path,
            "gate_policy",
            None,
        ),
        (
            registry_path,
            "gate_registry",
            None,
        ),
        (
            plan_path,
            "evaluation_plan",
            PLAN_SCHEMA,
        ),
        (
            schema_path,
            "json_schema",
            RESULT_SCHEMA,
        ),
        (
            tool_path,
            "evaluation_tool",
            None,
        ),
    ):
        add_ref(
            refs,
            repo,
            path,
            kind,
            schema_version,
            ref_errors,
        )

    if ref_errors:
        return None, ref_errors, False

    if gate_id in RECIPES:
        check, diagnostics, warnings = (
            run_recipe(
                ctx,
                RECIPES[gate_id],
                refs,
            )
        )

    else:
        check, diagnostics, warnings = (
            unsupported_check(
                ctx,
                refs,
            )
        )

    passed = (
        check["passed"] is True
        and not diagnostics
    )

    payload = {
        "schema_version": RESULT_SCHEMA,
        "created_utc": timestamp,
        "gate_id": gate_id,
        "evaluation_id": evaluation_id,
        "pass": passed,
        "status": (
            "passed"
            if passed
            else "failed"
        ),
        "run_identity": {
            "git_sha": git_sha,
            "run_key": run_key,
            "run_mode": "prod",
        },
        "subject": {
            "repository": repository,
            "commit_sha": git_sha,
            "release_candidate": (
                ctx.release_candidate
            ),
        },
        "policy_binding": {
            "policy_path": POLICY_PATH,
            "policy_sha256": policy_sha,
            "policy_set": "required",
        },
        "registry_binding": {
            "registry_path": REGISTRY_PATH,
            "registry_sha256": registry_sha,
        },
        "plan_binding": {
            "plan_path": PLAN_PATH,
            "plan_sha256": plan_sha,
            "plan_schema_version": PLAN_SCHEMA,
        },
        "evaluator": {
            "id": EVALUATOR_ID,
            "version": EVALUATOR_VERSION,
            "tool_path": TOOL_PATH,
            "tool_sha256": tool_sha,
        },
        "input_artifacts": [
            refs[key]
            for key in sorted(refs)
        ],
        "checks": [check],
        "diagnostics": diagnostics,
        "warnings": warnings,
        "authority_boundary": {
            "normative": False,
            "creates_release_authority": False,
            "materializes_status": False,
            "materializes_release_required": False,
            "direct_recorded_evidence_candidate": False,
            "replaces_check_gates": False,
        },
    }

    schema_errors = validate_schema(
        payload,
        schema,
    )

    if schema_errors:
        return (
            None,
            [
                (
                    "result schema validation "
                    f"failed: {item}"
                )
                for item in schema_errors
            ],
            False,
        )

    return payload, [], passed


def main(
    argv: list[str] | None = None,
) -> int:
    root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo-root",
        default=str(root),
    )

    parser.add_argument(
        "--gate-id",
        required=True,
    )

    parser.add_argument(
        "--out",
        required=True,
    )

    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
    )

    args = parser.parse_args(argv)

    repo = Path(
        args.repo_root
    ).resolve()

    if not repo.is_dir():
        print(
            "ERRORS (fail-closed):\n"
            f" - repo root is not a "
            f"directory: {repo}",
            file=sys.stderr,
        )
        return 1

    path_errors: list[str] = []

    output = safe_output(
        repo,
        Path(args.out),
        path_errors,
    )

    if output is None:
        print(
            "ERRORS (fail-closed):",
            file=sys.stderr,
        )

        for error in path_errors:
            print(
                f" - {error}",
                file=sys.stderr,
            )

        return 1

    if output.exists() or output.is_symlink():
        if (
            output.is_dir()
            and not output.is_symlink()
        ):
            print(
                "ERRORS (fail-closed):\n"
                " - output path is a directory: "
                f"{output}",
                file=sys.stderr,
            )
            return 1

        output.unlink()

    payload, errors, passed = build_result(
        repo=repo,
        gate_id=args.gate_id.strip(),
        output=output,
        timeout_seconds=args.timeout_seconds,
    )

    if payload is None:
        print(
            "ERRORS (fail-closed):",
            file=sys.stderr,
        )

        for error in errors:
            print(
                f" - {error}",
                file=sys.stderr,
            )

        return 1

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
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

    print(f"Wrote {output}")

    if not passed:
        print(
            "ERROR: required gate "
            f"{args.gate_id!r} failed closed; "
            "see recorded diagnostics.",
            file=sys.stderr,
        )
        return 1

    print(
        "OK: required gate "
        f"{args.gate_id!r} passed with "
        "recorded current-run evidence"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
