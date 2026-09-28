#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pulse_ci.yml"
RUNTIME_REQUIREMENTS = (
    ROOT
    / "PULSE_safe_pack_v0"
    / "requirements-llamaguard-v0.txt"
)

RELEASE_TOKEN = "steps.release_mode.outputs.is_release == '1'"
HOSTED_MODE_TOKEN = (
    "steps.release_mode.outputs.llamaguard_evidence_mode == 'hosted_full_runtime'"
)

MODEL_REVISION = (
    "acf7aafa60f0410f8f42b1fa35e077d705892029"
)

LLAMAGUARD_STEPS = (
    "release-grade initialize LlamaGuard runtime identity",
    "release-grade install pinned LlamaGuard runtime",
    "release-grade produce current-run LlamaGuard raw evidence",
    "release-grade build canonical LlamaGuard summary",
    "release-grade upload current-run LlamaGuard evidence",
)

ORDERED_STEPS = (
    "release-grade initialize current-run evidence identity",
    "release-grade build self-contained PULSE evidence floor",
    "upload self-contained PULSE evidence floor",
    *LLAMAGUARD_STEPS,
    (
        '"Strict external evidence: require external summaries '
        'present (pre-augment, fail-closed)"'
    ),
)


def _workflow_text() -> str:
    assert WORKFLOW.is_file(), f"missing workflow: {WORKFLOW}"
    return WORKFLOW.read_text(
        encoding="utf-8",
        errors="strict",
    )


def _step_block(text: str, name: str) -> str:
    lines = text.splitlines()
    start_pattern = re.compile(
        rf"^(?P<indent>\s*)-\s+name:\s+{re.escape(name)}\s*$"
    )

    for index, line in enumerate(lines):
        match = start_pattern.match(line)

        if match is None:
            continue

        indent = len(match.group("indent"))
        block = [line]

        for following in lines[index + 1 :]:
            stripped = following.lstrip()
            following_indent = len(following) - len(stripped)

            if (
                stripped.startswith("- name:")
                and following_indent <= indent
            ):
                break

            block.append(following)

        return "\n".join(block)

    raise AssertionError(f"workflow step not found: {name}")


def test_llamaguard_mode_input_defaults_to_tier0_not_required() -> None:
    text = _workflow_text()

    assert "llamaguard_evidence_mode:" in text
    assert (
        'description: "LlamaGuard evidence lane for release-grade runs"'
        in text
    )
    assert 'default: "tier0_not_required"' in text
    assert "type: choice" in text
    assert '- "tier0_not_required"' in text
    assert '- "hosted_full_runtime"' in text


def test_preflight_exports_llamaguard_evidence_mode_and_run_key() -> None:
    text = _workflow_text()
    block = _step_block(
        text,
        "CI pack layout preflight (fail-closed on release-grade)",
    )

    assert "PULSE_LLAMAGUARD_EVIDENCE_MODE" in block
    assert "tier0_not_required" in block
    assert "hosted_full_runtime" in block
    assert ".inputs.llamaguard_evidence_mode" in block
    assert "invalid llamaguard_evidence_mode" in block
    assert "PULSE_RUN_KEY=" in block
    assert 'echo "PULSE_RUN_KEY=${PULSE_RUN_KEY}" >> "$GITHUB_ENV"' in block
    assert (
        "PULSE_LLAMAGUARD_EVIDENCE_MODE=${PULSE_LLAMAGUARD_EVIDENCE_MODE}"
        in block
    )
    assert (
        "llamaguard_evidence_mode=${PULSE_LLAMAGUARD_EVIDENCE_MODE}"
        in block
    )


def test_llamaguard_release_steps_exist_in_mechanical_order() -> None:
    text = _workflow_text()
    positions = []

    for name in ORDERED_STEPS:
        marker = f"- name: {name}"
        position = text.find(marker)

        assert position >= 0, f"missing workflow step: {name}"
        positions.append(position)

    assert positions == sorted(positions), (
        "Tier 0 floor and LlamaGuard workflow steps are out of mechanical order"
    )


def test_llamaguard_runtime_steps_are_hosted_mode_opt_in() -> None:
    text = _workflow_text()

    for name in LLAMAGUARD_STEPS:
        block = _step_block(text, name)

        assert RELEASE_TOKEN in block, (
            f"{name!r} must remain conditional on release mode"
        )
        assert HOSTED_MODE_TOKEN in block, (
            f"{name!r} must require hosted_full_runtime opt-in"
        )


def test_strict_external_summary_precheck_is_hosted_mode_only() -> None:
    text = _workflow_text()
    block = _step_block(
        text,
        (
            '"Strict external evidence: require external summaries '
            'present (pre-augment, fail-closed)"'
        ),
    )

    assert "strict_external_evidence == 'true'" in block
    assert "startsWith(github.ref, 'refs/tags/v')" in block
    assert "startsWith(github.ref, 'refs/tags/V')" in block
    assert HOSTED_MODE_TOKEN in block


def test_hugging_face_secret_is_scoped_to_inference_step() -> None:
    text = _workflow_text()
    producer = _step_block(
        text,
        "release-grade produce current-run LlamaGuard raw evidence",
    )

    assert text.count("${{ secrets.HF_TOKEN }}") == 1
    assert "HF_TOKEN: ${{ secrets.HF_TOKEN }}" in producer
    assert '--token-env "HF_TOKEN"' in producer

    for name in (
        "release-grade initialize current-run evidence identity",
        "release-grade build self-contained PULSE evidence floor",
        "release-grade initialize LlamaGuard runtime identity",
        "release-grade install pinned LlamaGuard runtime",
        "release-grade build canonical LlamaGuard summary",
        "release-grade upload current-run LlamaGuard evidence",
    ):
        assert "${{ secrets.HF_TOKEN }}" not in _step_block(
            text,
            name,
        )


def test_producer_uses_current_run_identity_and_canonical_paths() -> None:
    text = _workflow_text()
    shared_identity = _step_block(
        text,
        "release-grade initialize current-run evidence identity",
    )
    runtime_identity = _step_block(
        text,
        "release-grade initialize LlamaGuard runtime identity",
    )
    producer = _step_block(
        text,
        "release-grade produce current-run LlamaGuard raw evidence",
    )

    assert (
        "PULSE_EXTERNAL_SIGNER_IDENTITY="
        '"repo:${GITHUB_REPOSITORY:?}:workflow:'
        '.github/workflows/pulse_ci.yml"'
    ) in shared_identity
    assert "PULSE_CREATED_UTC" in shared_identity
    assert "PULSE_RELEASE_CANDIDATE" in shared_identity
    assert "LLAMAGUARD_VERSION" not in shared_identity

    assert f'LLAMAGUARD_VERSION="{MODEL_REVISION}"' in runtime_identity

    required_tokens = (
        'tools/run_llamaguard_current_evidence_v0.py',
        'examples/llamaguard_current_run_cases_v0.jsonl',
        'artifacts/external/llamaguard_raw.jsonl',
        (
            "artifacts/external/"
            "llamaguard_evaluator_manifest_v0.json"
        ),
        'schemas/llamaguard_evaluator_manifest_v0.schema.json',
        '--model-revision "${LLAMAGUARD_VERSION}"',
        '--repository "${GITHUB_REPOSITORY}"',
        '--git-sha "${GITHUB_SHA}"',
        '--run-key "${PULSE_RUN_KEY}"',
        '--workflow-ref "${GITHUB_WORKFLOW_REF}"',
        '--release-candidate "${PULSE_RELEASE_CANDIDATE}"',
        '--created-utc "${PULSE_CREATED_UTC}"',
    )

    for token in required_tokens:
        assert token in producer, (
            f"producer workflow step is missing {token!r}"
        )


def test_existing_adapter_consumes_current_run_outputs() -> None:
    text = _workflow_text()
    summary = _step_block(
        text,
        "release-grade build canonical LlamaGuard summary",
    )

    required_tokens = (
        'tools/adapters/llamaguard_ingest.py',
        '--in "${PACK_DIR}/artifacts/external/'
        'llamaguard_raw.jsonl"',
        '--dataset "${PACK_DIR}/examples/'
        'llamaguard_current_run_cases_v0.jsonl"',
        '--evaluator-manifest "${PACK_DIR}/artifacts/external/'
        'llamaguard_evaluator_manifest_v0.json"',
        '--out "${PACK_DIR}/artifacts/external/'
        'llamaguard_summary.json"',
        '--run-id "${PULSE_RUN_KEY}"',
        '--generated-at "${PULSE_CREATED_UTC}"',
        '--release-candidate "${PULSE_RELEASE_CANDIDATE}"',
        '--git-sha "${GITHUB_SHA}"',
        '--repository "${GITHUB_REPOSITORY}"',
        '--signer-identity "${PULSE_EXTERNAL_SIGNER_IDENTITY}"',
        '--tool-version "${LLAMAGUARD_VERSION}"',
    )

    for token in required_tokens:
        assert token in summary, (
            f"summary workflow step is missing {token!r}"
        )


def test_lane_does_not_directly_mutate_release_authority() -> None:
    text = _workflow_text()
    producer = _step_block(
        text,
        "release-grade produce current-run LlamaGuard raw evidence",
    )
    summary = _step_block(
        text,
        "release-grade build canonical LlamaGuard summary",
    )
    lane = producer + "\n" + summary

    forbidden = (
        "status.json",
        "check_gates.py",
        "materialize_release_required_from_verifier_v0.py",
        "check_recorded_release_evidence_v0.py",
        "build_recorded_release_candidates_v0.py",
        "attest-build-provenance",
    )

    for token in forbidden:
        assert token not in lane, (
            "LlamaGuard producer lane must not directly invoke "
            f"{token!r}"
        )


def test_standing_candidate_verifier_materializer_path_remains() -> None:
    text = _workflow_text()
    summary_position = text.index(
        "tools/adapters/llamaguard_ingest.py"
    )

    standing_tools = (
        "tools/build_recorded_release_candidates_v0.py",
        "tools/build_release_evidence_input_manifest_v0.py",
        "tools/check_recorded_release_evidence_v0.py",
        "tools/materialize_release_required_from_verifier_v0.py",
    )
    positions = []

    for tool in standing_tools:
        position = text.find(tool)

        assert position > summary_position, (
            f"standing release path tool missing or precedes summary: {tool}"
        )
        positions.append(position)

    assert positions == sorted(positions), (
        "standing candidate/verifier/materializer order changed"
    )


def test_runtime_requirements_are_exactly_pinned() -> None:
    assert RUNTIME_REQUIREMENTS.is_file(), (
        f"missing runtime requirements: {RUNTIME_REQUIREMENTS}"
    )

    entries = [
        line.strip()
        for line in RUNTIME_REQUIREMENTS.read_text(
            encoding="utf-8",
            errors="strict",
        ).splitlines()
        if line.strip()
    ]

    assert entries == [
        "--extra-index-url https://download.pytorch.org/whl/cpu",
        "torch==2.9.1+cpu",
        "transformers==4.57.6",
        "huggingface-hub==0.36.0",
        "safetensors==0.7.0",
    ]


def test_current_run_artifacts_are_archived_fail_closed() -> None:
    text = _workflow_text()
    upload = _step_block(
        text,
        "release-grade upload current-run LlamaGuard evidence",
    )

    assert (
        "name: llamaguard-current-run-"
        "${{ github.run_id }}-${{ github.run_attempt }}"
    ) in upload
    assert (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_raw.jsonl"
    ) in upload
    assert (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_evaluator_manifest_v0.json"
    ) in upload
    assert (
        "PULSE_safe_pack_v0/artifacts/external/"
        "llamaguard_summary.json"
    ) in upload
    assert "if-no-files-found: error" in upload



def _run_preflight_fixture(
    *, event: str, ref: str, inputs: dict[str, object],
    checker_exit: int = 0,
) -> tuple[subprocess.CompletedProcess[str], str, str, list[str] | None]:
    """Execute the actual preflight body with a local layout-call witness.

    The witness records routing and propagates a chosen exit status; it does
    not implement layout validation or claim hosted/release evidence.
    """
    workflow = yaml.safe_load(_workflow_text())
    preflight = next(
        step for step in workflow["jobs"]["pulse"]["steps"]
        if step.get("id") == "release_mode"
    )
    with tempfile.TemporaryDirectory(prefix="pulse-preflight-") as directory:
        root = Path(directory)
        (root / "tools").mkdir()
        (root / "PULSE_safe_pack_v0").mkdir()
        (root / "tools/check_pack_layout.py").write_text(
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['LAYOUT_CALL']).write_text(json.dumps(sys.argv[1:]))\n"
            "raise SystemExit(int(os.environ['LAYOUT_EXIT']))\n",
            encoding="utf-8",
        )
        event_path = root / "event.json"
        event_path.write_text(json.dumps({"inputs": inputs}), encoding="utf-8")
        environment_path = root / "github.env"
        output_path = root / "github.output"
        environment_path.touch()
        output_path.touch()
        witness_path = root / "layout-call.json"
        env = os.environ.copy()
        env.update({
            "GITHUB_EVENT_NAME": event, "GITHUB_REF": ref,
            "GITHUB_EVENT_PATH": str(event_path),
            "GITHUB_ENV": str(environment_path),
            "GITHUB_OUTPUT": str(output_path),
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_WORKFLOW": "PULSE CI", "GITHUB_WORKSPACE": str(root),
            "LAYOUT_CALL": str(witness_path), "LAYOUT_EXIT": str(checker_exit),
        })
        body = preflight["run"].replace(
            "${{ env.PACK_DIR }}", str(root / "PULSE_safe_pack_v0")
        )
        assert "${{" not in body, "fixture must resolve every Actions expression"
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", body],
            cwd=root, env=env, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=False, timeout=20,
        )
        call = json.loads(witness_path.read_text()) if witness_path.exists() else None
        return result, environment_path.read_text(), output_path.read_text(), call


def test_preflight_executes_supported_release_mode_matrix() -> None:
    cases = (
        ("push", "refs/heads/main", {}, False, "tier0_not_required"),
        ("pull_request", "refs/pull/1/merge", {}, False, "tier0_not_required"),
        ("workflow_dispatch", "refs/heads/main", {}, False, "tier0_not_required"),
        ("workflow_dispatch", "refs/heads/main",
         {"strict_external_evidence": False}, False, "tier0_not_required"),
        ("workflow_dispatch", "refs/heads/main",
         {"strict_external_evidence": "false", "llamaguard_evidence_mode": "hosted_full_runtime"},
         False, "hosted_full_runtime"),
        ("workflow_dispatch", "refs/heads/main",
         {"strict_external_evidence": True, "llamaguard_evidence_mode": "hosted_full_runtime"},
         True, "hosted_full_runtime"),
        ("workflow_dispatch", "refs/heads/main",
         {"strict_external_evidence": "true", "llamaguard_evidence_mode": "hosted_full_runtime"},
         True, "hosted_full_runtime"),
        ("push", "refs/tags/v-test", {}, True, "hosted_full_runtime"),
        ("push", "refs/tags/V-test", {}, True, "hosted_full_runtime"),
        ("workflow_dispatch", "refs/tags/v-test",
         {"strict_external_evidence": True, "llamaguard_evidence_mode": "tier0_not_required"},
         True, "hosted_full_runtime"),
    )
    for event, ref, inputs, release, mode in cases:
        result, environment, output, call = _run_preflight_fixture(
            event=event, ref=ref, inputs=inputs,
        )
        assert result.returncode == 0, (event, ref, inputs, result.stderr, result.stdout)
        assert f"is_release={int(release)}\n" in output
        assert f"llamaguard_evidence_mode={mode}\n" in output
        assert f"PULSE_MODE={'prod' if release else 'core'}\n" in environment
        assert f"PULSE_POLICY_SET={'required' if release else 'core_required'}\n" in environment
        assert "PULSE_RUN_KEY=GITHUB_RUN_ID=123|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI\n" in environment
        assert call is not None
        assert ("--release-grade" in call) is release


def test_preflight_rejects_inconsistent_release_before_outputs() -> None:
    cases = [
        ({"strict_external_evidence": True}, "requires hosted_full_runtime"),
        ({"strict_external_evidence": "true", "llamaguard_evidence_mode": "tier0_not_required"},
         "requires hosted_full_runtime"),
        ({"strict_external_evidence": True, "llamaguard_evidence_mode": "unknown"},
         "invalid llamaguard_evidence_mode"),
    ]
    for invalid in ("yes", "", 1, [], {"true": True}):
        cases.append((
            {"strict_external_evidence": invalid, "llamaguard_evidence_mode": "hosted_full_runtime"},
            "invalid strict_external_evidence",
        ))
    for inputs, diagnostic in cases:
        result, environment, output, call = _run_preflight_fixture(
            event="workflow_dispatch", ref="refs/heads/main", inputs=inputs,
        )
        assert result.returncode != 0, inputs
        assert diagnostic in result.stdout, (inputs, result.stdout, result.stderr)
        assert environment == "" and output == "", "rejected input must not publish release flags"
        assert call is None, "inconsistent input must stop before the layout/evidence path"


def test_preflight_preserves_layout_failure() -> None:
    result, _, _, call = _run_preflight_fixture(
        event="workflow_dispatch", ref="refs/heads/main",
        inputs={"strict_external_evidence": True, "llamaguard_evidence_mode": "hosted_full_runtime"},
        checker_exit=9,
    )
    assert result.returncode == 9
    assert call is not None and "--release-grade" in call

def main() -> int:
    test_llamaguard_mode_input_defaults_to_tier0_not_required()
    test_preflight_exports_llamaguard_evidence_mode_and_run_key()
    test_preflight_executes_supported_release_mode_matrix()
    test_preflight_rejects_inconsistent_release_before_outputs()
    test_preflight_preserves_layout_failure()
    test_llamaguard_release_steps_exist_in_mechanical_order()
    test_llamaguard_runtime_steps_are_hosted_mode_opt_in()
    test_strict_external_summary_precheck_is_hosted_mode_only()
    test_hugging_face_secret_is_scoped_to_inference_step()
    test_producer_uses_current_run_identity_and_canonical_paths()
    test_existing_adapter_consumes_current_run_outputs()
    test_lane_does_not_directly_mutate_release_authority()
    test_standing_candidate_verifier_materializer_path_remains()
    test_runtime_requirements_are_exactly_pinned()
    test_current_run_artifacts_are_archived_fail_closed()
    print("OK: LlamaGuard hosted runtime workflow opt-in wiring locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
