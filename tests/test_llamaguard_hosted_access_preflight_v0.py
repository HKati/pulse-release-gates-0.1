#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "check_llamaguard_hosted_access_v0.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "llamaguard_hosted_access_preflight.yml"
TOOLS_TESTS_LIST = ROOT / "ci" / "tools-tests.list"
THIS_TEST = "tests/test_llamaguard_hosted_access_preflight_v0.py"

EXPECTED_MODEL_ID = "meta-llama/Llama-Guard-3-1B"
EXPECTED_MODEL_REVISION = "acf7aafa60f0410f8f42b1fa35e077d705892029"
EXPECTED_HUB_VERSION = "0.36.0"


def _load_tool() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_llamaguard_hosted_access_v0",
        TOOL_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOOL = _load_tool()


def _make_repo(base: Path) -> Path:
    repo = base / "repo"
    producer = repo / "PULSE_safe_pack_v0" / "tools" / "run_llamaguard_current_evidence_v0.py"
    requirements = repo / "PULSE_safe_pack_v0" / "requirements-llamaguard-v0.txt"
    producer.parent.mkdir(parents=True, exist_ok=True)

    producer.write_text(
        "MODEL_ID = \"meta-llama/Llama-Guard-3-1B\"\n"
        "MODEL_REVISION = \"acf7aafa60f0410f8f42b1fa35e077d705892029\"\n",
        encoding="utf-8",
    )
    requirements.write_text(
        "--extra-index-url https://download.pytorch.org/whl/cpu\n\n"
        "torch==2.9.1+cpu\n"
        "transformers==4.57.6\n"
        "huggingface-hub==0.36.0\n"
        "safetensors==0.7.0\n",
        encoding="utf-8",
    )
    return repo


class FakeGatedRepoError(Exception):
    pass


class FakeRepositoryNotFoundError(Exception):
    pass


class FakeRevisionNotFoundError(Exception):
    pass


class FakeEntryNotFoundError(Exception):
    pass


class FakeHubHttpError(Exception):
    pass


def _bindings(*, resolved_revision: str):
    class FakeApi:
        def __init__(self, *, token: str) -> None:
            assert token == "hf_test_secret_value"

        def model_info(self, *, repo_id: str, revision: str, token: str):
            assert repo_id == EXPECTED_MODEL_ID
            assert revision == EXPECTED_MODEL_REVISION
            assert token == "hf_test_secret_value"
            return SimpleNamespace(sha=resolved_revision, gated="auto")

    def fake_download_file(
        *,
        repo_id: str,
        filename: str,
        revision: str,
        token: str,
        cache_dir: str,
    ) -> str:
        assert repo_id == EXPECTED_MODEL_ID
        assert revision == EXPECTED_MODEL_REVISION
        assert token == "hf_test_secret_value"
        assert filename in {"config.json", "tokenizer_config.json"}
        path = Path(cache_dir) / "probe" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"filename": filename, "revision": revision}),
            encoding="utf-8",
        )
        return str(path)

    return TOOL.HuggingFaceBindings(
        api_factory=FakeApi,
        download_file=fake_download_file,
        gated_repo_error=FakeGatedRepoError,
        repository_not_found_error=FakeRepositoryNotFoundError,
        revision_not_found_error=FakeRevisionNotFoundError,
        entry_not_found_error=FakeEntryNotFoundError,
        hub_http_error=FakeHubHttpError,
    )


def _run_check(
    repo: Path,
    *,
    reported_git_sha: str = "a" * 40,
    checked_out_git_sha: str | None = None,
) -> tuple[dict, int]:
    actual_head = checked_out_git_sha or reported_git_sha
    with mock.patch.object(TOOL, "_git_head", return_value=actual_head):
        return TOOL.check_access(
            repo_root=repo,
            token_env="HF_TOKEN",
            repository="HKati/pulse-release-gates-0.1",
            git_sha=reported_git_sha,
            workflow_ref=(
                "HKati/pulse-release-gates-0.1/"
                ".github/workflows/llamaguard_hosted_access_preflight.yml@refs/heads/main"
            ),
            run_id="12345",
            run_attempt="1",
        )


def test_canonical_runtime_identity_comes_from_repository_files() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo = _make_repo(Path(temp))
        runtime = TOOL._canonical_runtime_identity(repo)

    assert runtime["model_id"] == EXPECTED_MODEL_ID
    assert runtime["model_revision"] == EXPECTED_MODEL_REVISION
    assert runtime["huggingface_hub_version"] == EXPECTED_HUB_VERSION
    assert len(runtime["producer_sha256"]) == 64
    assert len(runtime["runtime_requirements_sha256"]) == 64




def test_reported_git_sha_must_match_checked_out_head() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo = _make_repo(Path(temp))
        report, exit_code = _run_check(
            repo,
            reported_git_sha="a" * 40,
            checked_out_git_sha="b" * 40,
        )

    assert exit_code == 1
    assert report["ok"] is False
    assert report["failure"]["kind"] == "git_sha_checkout_mismatch"
    assert report["source"]["git_sha"] == "a" * 40
    assert report["source"]["checked_out_git_sha"] == "b" * 40
    check = next(
        item
        for item in report["checks"]
        if item["check_id"] == "source.git_sha_matches_checkout"
    )
    assert check["passed"] is False


def test_canonical_inputs_reject_symlinked_parent_directory() -> None:
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        outside = _make_repo(base / "outside")
        repo = base / "repo"
        repo.mkdir(parents=True)
        (repo / "PULSE_safe_pack_v0").symlink_to(
            outside / "PULSE_safe_pack_v0",
            target_is_directory=True,
        )

        try:
            TOOL._canonical_runtime_identity(repo)
        except TOOL.PreflightError as exc:
            assert exc.code == "repository_path_symlink_component"
            assert exc.field == TOOL.PRODUCER_REL
        else:
            raise AssertionError("symlinked canonical input parent was accepted")


def test_missing_token_fails_without_loading_network_client() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo = _make_repo(Path(temp))
        with mock.patch.dict(os.environ, {"HF_TOKEN": ""}, clear=False), mock.patch.object(
            TOOL,
            "_load_huggingface_bindings",
            side_effect=AssertionError("network client must not load without a token"),
        ):
            report, exit_code = _run_check(repo)

    assert exit_code == 1
    assert report["ok"] is False
    assert report["status"] == "blocked"
    assert report["failure"]["kind"] == "missing_token"
    assert report["authority_boundary"]["authorizes_release"] is False


def test_success_probes_only_small_metadata_files_and_never_records_token() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo = _make_repo(Path(temp))
        with mock.patch.dict(
            os.environ,
            {"HF_TOKEN": "hf_test_secret_value"},
            clear=False,
        ), mock.patch.object(
            TOOL,
            "_installed_hub_version",
            return_value=EXPECTED_HUB_VERSION,
        ), mock.patch.object(
            TOOL,
            "_load_huggingface_bindings",
            return_value=_bindings(resolved_revision=EXPECTED_MODEL_REVISION),
        ):
            report, exit_code = _run_check(repo)

    rendered = json.dumps(report, sort_keys=True)
    assert exit_code == 0
    assert report["ok"] is True
    assert report["status"] == "accessible"
    assert report["runtime"]["resolved_model_revision"] == EXPECTED_MODEL_REVISION
    assert [item["path"] for item in report["probe_files"]] == [
        "config.json",
        "tokenizer_config.json",
    ]
    assert all(item["json_object"] is True for item in report["probe_files"])
    assert "hf_test_secret_value" not in rendered
    assert report["authority_boundary"] == TOOL.AUTHORITY_BOUNDARY


def test_resolved_revision_mismatch_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo = _make_repo(Path(temp))
        with mock.patch.dict(
            os.environ,
            {"HF_TOKEN": "hf_test_secret_value"},
            clear=False,
        ), mock.patch.object(
            TOOL,
            "_installed_hub_version",
            return_value=EXPECTED_HUB_VERSION,
        ), mock.patch.object(
            TOOL,
            "_load_huggingface_bindings",
            return_value=_bindings(resolved_revision="b" * 40),
        ):
            report, exit_code = _run_check(repo)

    assert exit_code == 1
    assert report["failure"]["kind"] == "model_revision_mismatch"
    assert report["probe_files"] == []


def test_output_safety_refuses_repository_and_status_outputs() -> None:
    with tempfile.TemporaryDirectory() as temp:
        repo = _make_repo(Path(temp))
        outside = Path(temp) / "outside" / "report.json"

        assert TOOL._normalize_output(repo, outside) == outside.resolve()

        for bad in (
            repo / "report.json",
            Path(temp) / "outside" / "status.json",
        ):
            try:
                TOOL._normalize_output(repo, bad)
            except TOOL.PreflightError:
                pass
            else:
                raise AssertionError(f"unsafe output accepted: {bad}")


def test_tool_source_has_no_inference_or_weight_download_surface() -> None:
    text = TOOL_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "snapshot_download",
        "AutoModel",
        "AutoTokenizer",
        "from_pretrained",
        "pytorch_model.bin",
        "model.safetensors",
        "check_gates.py",
        "materialize_release_required_from_verifier_v0.py",
        "actions/attest",
    ):
        assert forbidden not in text, forbidden

    assert TOOL.PROBE_FILES == ("config.json", "tokenizer_config.json")
    assert TOOL.AUTHORITY_BOUNDARY["runs_model_inference"] is False
    assert TOOL.AUTHORITY_BOUNDARY["downloads_model_weights"] is False
    assert TOOL.AUTHORITY_BOUNDARY["authorizes_release"] is False


def test_workflow_is_manual_read_only_and_secret_scoped() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert text.startswith(
        "name: LlamaGuard hosted access preflight release check\n"
    )
    assert "\n  workflow_dispatch:" in text
    for trigger in ("\n  push:", "\n  pull_request:", "\n  schedule:", "\n  release:"):
        assert trigger not in text

    assert "expected_source_sha:" in text
    assert "refs/heads/main" in text
    assert "EXPECTED_SOURCE_SHA" in text
    assert "persist-credentials: false" in text

    assert text.count("secrets.HF_TOKEN") == 1
    assert "set -x" not in text
    assert 'echo "${HF_TOKEN}' not in text
    assert "id-token:" not in text
    assert "attestations:" not in text
    assert "artifact-metadata:" not in text
    assert "actions/attest@" not in text

    assert "tools/check_llamaguard_hosted_access_v0.py" in text
    assert "--token-env \"HF_TOKEN\"" in text
    assert "--output \"${REPORT_PATH}\"" in text
    assert "${{ runner.temp }}/llamaguard_hosted_access_preflight_v0.json" in text

    upload_index = text.index("Upload sanitized hosted-access preflight report")
    tool_index = text.index("tools/check_llamaguard_hosted_access_v0.py")
    assert tool_index < upload_index
    assert "if: ${{ always() }}" in text[upload_index:]
    assert "if-no-files-found: error" in text[upload_index:]
    assert "retention-days: 30" in text[upload_index:]

    for forbidden in (
        "check_gates.py",
        "policy_to_require_args.py",
        "materialize_release_required_from_verifier_v0.py",
        "status.json",
        "release_required",
        "release_blocking",
        "prod_required",
        "stage_required",
    ):
        assert forbidden not in text, forbidden


def test_tools_manifest_registers_preflight_smoke_once() -> None:
    entries = [
        raw.split("#", 1)[0].strip()
        for raw in TOOLS_TESTS_LIST.read_text(encoding="utf-8").splitlines()
        if raw.split("#", 1)[0].strip()
    ]
    assert entries.count(THIS_TEST) == 1
    current_run_test = "tests/test_llamaguard_current_run_workflow_wiring_v0.py"
    assert entries.index(current_run_test) < entries.index(THIS_TEST)


def check_llamaguard_hosted_access_preflight_v0() -> None:
    test_canonical_runtime_identity_comes_from_repository_files()
    test_reported_git_sha_must_match_checked_out_head()
    test_canonical_inputs_reject_symlinked_parent_directory()
    test_missing_token_fails_without_loading_network_client()
    test_success_probes_only_small_metadata_files_and_never_records_token()
    test_resolved_revision_mismatch_fails_closed()
    test_output_safety_refuses_repository_and_status_outputs()
    test_tool_source_has_no_inference_or_weight_download_surface()
    test_workflow_is_manual_read_only_and_secret_scoped()
    test_tools_manifest_registers_preflight_smoke_once()


if __name__ == "__main__":
    check_llamaguard_hosted_access_preflight_v0()
    print("OK: LlamaGuard hosted access preflight contract")
