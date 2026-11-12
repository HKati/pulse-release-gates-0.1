"""Semantic adapter regressions; synthetic fixtures never prove an observed run.

Tests exercise real existing LlamaGuard content/schema/parser code. Successful
signature and Q2 subprocess fixtures are in-process mocks only; production has
no fixture backend, saved-verdict fallback, or option to skip fresh execution.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import pulsemech_compute_admission_rejection_semantics_v0 as semantic  # noqa: E402


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def _identity(commit=None):
    return {"repository": semantic.REPOSITORY, "source_commit": commit or _head(),
            "run_id": 12345, "run_attempt": 1, "event": "workflow_dispatch",
            "ref": "refs/heads/main"}


@pytest.fixture
def q2_fixture(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    identity = _identity("a" * 40)
    capture, capsule = tmp_path / "capture.zip", tmp_path / "capsule.zip"
    capture.write_bytes(b"controlled capture fixture")
    capsule.write_bytes(b"controlled capsule fixture")

    def archive(path):
        raw = path.read_bytes()
        return {"archive_size_bytes": len(raw), "archive_sha256": semantic._digest(raw)}

    evaluation = {key: identity[key] for key in ("repository", "source_commit", "event", "ref")}
    evaluation["workflow"] = semantic.WORKFLOW
    request = {"evaluation_identity": evaluation,
               "capture_expectation": archive(capture), "release_subject": archive(capsule)}
    raw = semantic._canonical(request)
    bindings = [{"path": semantic.Q2_CHECKER, "sha256": "b" * 64,
                 "size_bytes": 100, "git_blob_sha1": "c" * 40, "mode": "100644"}]
    q2_bindings = [{key: bindings[0][key] for key in ("path", "sha256", "size_bytes")}]
    result = {
        "schema_version": "q2_release_intake_result_v0", "record_status": "archived_capture_intake",
        "input_valid": True, "metric_pass": False, "process_exit": 1,
        "checks": {key: True for key in ("request", "capture", "subject", "replay", "summary")},
        "cleanup": "verified_removed", "current_inference_count": 0,
        "authority_effect": "none", "production_gate_eligible": False,
        "evaluation_binding": {**evaluation, "workflow_sha": identity["source_commit"],
                               "run_id": "12345", "run_attempt": 1,
                               "request_sha256": semantic._digest(raw)},
        "request_sha256": semantic._digest(raw), "source_bindings": q2_bindings,
        "metrics": {"eligible_groups": 49, "min_eligible_groups": 50},
    }
    monkeypatch.setattr(semantic, "_source_snapshot", lambda *args: ({"source": b"fixed"}, bindings))
    monkeypatch.setattr(semantic, "_python_identity", lambda *args, **kwargs: {
        "executable": {"sha256": "d" * 64, "bytes": 1},
        "runtime": {"implementation": "CPython", "version": [3, 11, 16], "unicode": "14.0.0"},
    })
    executions = []

    def run(argv, **kwargs):
        executions.append((argv, kwargs))
        private = Path(argv[argv.index("--private-input") + 1])
        (private / "result.json").write_bytes(semantic._canonical({**result, "cleanup": "not_created"}))
        return 1, b"", b""

    monkeypatch.setattr(semantic, "_run", run)
    args = [repo, raw, capture, capsule, result, copy.deepcopy(result), identity, Path(sys.executable), work]
    return args, executions


def test_q2_valid_negative_requires_fresh_cli_and_real_private_cleanup(q2_fixture):
    args, executions = q2_fixture
    report = semantic.verify_q2(*args)
    assert len(executions) == 1
    argv, _ = executions[0]
    assert argv[1:3] == ["-I", "-B"]
    assert argv[3].endswith(semantic.Q2_CHECKER)
    assert not Path(argv[argv.index("--private-input") + 1]).exists()
    assert list(args[-1].iterdir()) == []
    assert report["metric_pass"] is False and report["process_exit"] == 1
    assert report["current_inference_count"] == 0
    assert report["original_runtime_reads_proven"] is False
    assert report["fresh_result"]["cleanup"] == "not_created"
    assert report["private_cleanup"] == "verified_removed"


def test_q2_saved_positive_flags_cannot_replace_failed_replay(q2_fixture, monkeypatch):
    args, _ = q2_fixture

    def failed(argv, **kwargs):
        private = Path(argv[argv.index("--private-input") + 1])
        (private / "result.json").write_bytes(semantic._canonical({**args[4], "input_valid": False,
                                                                  "metric_pass": None, "process_exit": 2}))
        return 2, b"", b""

    monkeypatch.setattr(semantic, "_run", failed)
    with pytest.raises(semantic.SemanticVerificationError, match="q2_independent_replay_rejected"):
        semantic.verify_q2(*args)
    assert list(args[-1].iterdir()) == []


def test_q2_full_fresh_record_must_equal_both_saved_records(q2_fixture, monkeypatch):
    args, _ = q2_fixture

    def changed(argv, **kwargs):
        private = Path(argv[argv.index("--private-input") + 1])
        changed_result = {**args[4], "cleanup": "not_created", "metrics": {"eligible_groups": 48}}
        (private / "result.json").write_bytes(semantic._canonical(changed_result))
        return 1, b"", b""

    monkeypatch.setattr(semantic, "_run", changed)
    with pytest.raises(semantic.SemanticVerificationError, match="fresh_replay_saved_record_mismatch"):
        semantic.verify_q2(*args)


@pytest.mark.parametrize("mutation", ["success", "wrong_run", "independent_difference", "missing_check"])
def test_q2_rejects_wrong_original_semantics_before_replay(q2_fixture, mutation):
    args, executions = q2_fixture
    if mutation == "success":
        args[4]["metric_pass"] = True
    elif mutation == "wrong_run":
        args[6] = {**args[6], "run_id": 12346}
    elif mutation == "independent_difference":
        args[5]["metrics"]["eligible_groups"] = 48
    else:
        args[4]["checks"].pop("replay")
    with pytest.raises(semantic.SemanticVerificationError):
        semantic.verify_q2(*args)
    assert executions == []


def test_q2_archive_byte_mismatch_is_not_relabelled_as_valid_negative(q2_fixture):
    args, executions = q2_fixture
    args[2].write_bytes(b"X" * args[2].stat().st_size)
    with pytest.raises(semantic.SemanticVerificationError, match="archive_digest_mismatch"):
        semantic.verify_q2(*args)
    assert executions == [] and list(args[-1].iterdir()) == []


def test_q2_archive_symlink_is_rejected(q2_fixture, tmp_path):
    args, executions = q2_fixture
    link = tmp_path / "capture-link.zip"
    link.symlink_to(args[2])
    args[2] = link
    with pytest.raises(semantic.SemanticVerificationError, match="unsafe"):
        semantic.verify_q2(*args)
    assert executions == []


def test_q2_record_bytes_reject_duplicate_json_keys(q2_fixture):
    args, _ = q2_fixture
    args[4] = b'{"input_valid":true,"input_valid":false}'
    with pytest.raises(semantic.SemanticVerificationError, match="duplicate_json_key"):
        semantic.verify_q2(*args)


def test_q2_controlled_report_does_not_depend_on_private_directory(q2_fixture, tmp_path):
    args, _ = q2_fixture
    first = semantic._canonical(semantic.verify_q2(*args))
    other = tmp_path / "other-work"
    other.mkdir()
    args[-1] = other
    second = semantic._canonical(semantic.verify_q2(*args))
    assert first == second
    assert str(tmp_path).encode() not in first


def test_exact_q2_runtime_is_required_even_when_saved_result_is_valid(tmp_path, monkeypatch):
    monkeypatch.setattr(semantic, "_run", lambda *args, **kwargs: (0, semantic._canonical({
        "implementation": "CPython", "version": [3, 12, 14], "unicode": "15.0.0",
        "jsonschema": "4.25.1", "PyYAML": "6.0.3"}), b""))
    with pytest.raises(semantic.SemanticVerificationError, match="exact_replay_runtime_required"):
        semantic._python_identity(Path(sys.executable).resolve(), cwd=tmp_path, home=tmp_path, q2=True)


@pytest.fixture
def small_git_repo(tmp_path, monkeypatch):
    repo = tmp_path / "git-source"
    repo.mkdir()
    files = {semantic.WORKFLOW: b"name: controlled fixture\n", semantic.POLICY: b"fixture: true\n",
             "checked.py": b"print('fixture')\n"}
    for name, raw in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for argv in (["git", "init", "-q"], ["git", "add", "."],
                 ["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                  "-c", "commit.gpgsign=false", "commit", "-qm", "controlled fixture"]):
        subprocess.run(argv, cwd=repo, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    monkeypatch.setattr(semantic, "WORKFLOW_SHA256", semantic._digest(files[semantic.WORKFLOW]))
    monkeypatch.setattr(semantic, "POLICY_SHA256", semantic._digest(files[semantic.POLICY]))
    return repo, commit


def test_source_snapshot_checks_actual_checkout_and_file_modes(small_git_repo):
    repo, commit = small_git_repo
    values, _ = semantic._source_snapshot(repo, commit, ("checked.py",))
    assert values["checked.py"] == b"print('fixture')\n"
    (repo / "checked.py").chmod(0o755)
    with pytest.raises(semantic.SemanticVerificationError, match="source_worktree_mismatch"):
        semantic._source_snapshot(repo, commit, ("checked.py",))


def test_source_snapshot_rejects_dirty_semantic_source(small_git_repo):
    repo, commit = small_git_repo
    (repo / "checked.py").write_bytes(b"raise SystemExit(0)\n")
    with pytest.raises(semantic.SemanticVerificationError, match="source_worktree_mismatch"):
        semantic._source_snapshot(repo, commit, ("checked.py",))


def test_source_snapshot_rejects_other_commit(small_git_repo):
    repo, _ = small_git_repo
    with pytest.raises(semantic.SemanticVerificationError, match="source_head_mismatch"):
        semantic._source_snapshot(repo, "f" * 40, ("checked.py",))


def test_subprocess_does_not_inherit_credentials_or_python_injection(tmp_path, monkeypatch):
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "PULSE_Q2_TRANSPORT_TOKEN", "PYTHONPATH"):
        monkeypatch.setenv(name, "must-not-reach-child")
    command = ("import json,os; print(json.dumps({key:key in os.environ for key in "
               "['GH_TOKEN','GITHUB_TOKEN','PULSE_Q2_TRANSPORT_TOKEN','PYTHONPATH']}))")
    code, out, _ = semantic._run([sys.executable, "-I", "-B", "-c", command],
                                 cwd=tmp_path, home=tmp_path, timeout=10)
    assert code == 0 and all(value is False for value in json.loads(out).values())


def test_subprocess_output_is_bounded_while_running(tmp_path):
    code = "import os;\nwhile True: os.write(1,b'x'*65536)"
    with pytest.raises(semantic.SemanticVerificationError, match="semantic_process_output_limit"):
        semantic._run([sys.executable, "-I", "-B", "-c", code],
                      cwd=tmp_path, home=tmp_path, timeout=5)


def _load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def llama_fixture(tmp_path):
    identity = _identity()
    sources, _ = semantic._source_snapshot(REPO, identity["source_commit"],
                                           semantic.LLAMAGUARD_SOURCES + (semantic.LEGACY_CHECKER,))
    root = tmp_path / "fixture-source"
    for name, raw in sources.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    runner = _load_module(root / (semantic.PACK + "tools/run_llamaguard_current_evidence_v0.py"),
                          "admission_test_llamaguard_runner")
    ingest = _load_module(root / (semantic.PACK + "tools/adapters/llamaguard_ingest.py"),
                          "admission_test_llamaguard_ingest")
    cases = runner._load_cases(root / runner.DATASET_REL)
    stamp = "2026-11-12T10:00:00Z"
    run = {"repository": semantic.REPOSITORY, "git_sha": identity["source_commit"],
           "run_key": "GITHUB_RUN_ID=12345|GITHUB_RUN_ATTEMPT=1|GITHUB_WORKFLOW=PULSE CI",
           "run_id": 12345, "run_attempt": 1, "workflow_name": "PULSE CI",
           "workflow_ref": semantic.REPOSITORY + "/" + semantic.WORKFLOW + "@refs/heads/main",
           "workflow_path": semantic.WORKFLOW, "release_candidate": "main", "created_utc": stamp}
    model = {"id": runner.MODEL_ID, "revision": runner.MODEL_REVISION, "dtype": "float32"}
    generation = {"manual_seed": 0, "do_sample": False, "num_beams": 1,
                  "pad_token_id": 0, "max_new_tokens": 20}
    records = []
    for index, case in enumerate(cases):
        records.append({**case, "llamaguard": {"label": "safe", "categories": [], "raw_output": "safe"},
                        "model": model,
                        "run": {**{key: value for key, value in run.items() if key != "workflow_path"},
                                "case_index": index},
                        "inference": {**generation, "device": "cpu", "torch_threads": 2,
                                      "prompt_tokens": 12, "generated_tokens": 1}})
    raw = b"".join(semantic._canonical(record) for record in records)
    raw_path = root / runner.RAW_REL
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    manifest = {
        "schema_version": runner.TOOL_SCHEMA,
        "producer": {"path": runner.TOOL_REL, "tool": "run_llamaguard_current_evidence_v0.py",
                     "version": runner.TOOL_VERSION, "sha256": semantic._digest(sources[runner.TOOL_REL])},
        "run": run, "model": model,
        "runtime": {"versions": {"python": "3.11.16", "torch": "2.9.1+cpu", "transformers": "4.57.6",
                                 "huggingface_hub": "0.36.0", "tokenizers": "0.22.1", "safetensors": "0.7.0"},
                    "device": "cpu", "torch_threads": 2, "generation": generation},
        "dataset": {"path": runner.DATASET_REL, "sha256": semantic._digest(sources[runner.DATASET_REL]),
                    "case_count": 6},
        "output": {"raw_evidence_path": runner.RAW_REL, "raw_evidence_sha256": semantic._digest(raw),
                   "record_count": 6, "safe_count": 6, "unsafe_count": 0},
        "schema_binding": {"path": runner.MANIFEST_SCHEMA_REL,
                           "sha256": semantic._digest(sources[runner.MANIFEST_SCHEMA_REL])},
        "authority_boundary": runner.AUTHORITY_BOUNDARY,
    }
    manifest_path = root / runner.MANIFEST_REL
    manifest_path.write_bytes(semantic._canonical(manifest))
    summary = ingest._build_summary(
        repo_root=root, raw_path=raw_path, dataset_path=root / runner.DATASET_REL,
        evaluator_manifest_path=manifest_path, schema_path=root / ingest.SUMMARY_SCHEMA_REL,
        thresholds_path=root / ingest.THRESHOLDS_REL, run_id=run["run_key"], generated_at=stamp,
        release_candidate="main", git_sha=identity["source_commit"], repository=semantic.REPOSITORY,
        signer_identity="repo:" + semantic.REPOSITORY + ":workflow:" + semantic.WORKFLOW,
        tool_version=runner.MODEL_REVISION, adapter_version=ingest.ADAPTER_VERSION,
    )
    hosted = {"llamaguard_raw.jsonl": raw, "llamaguard_evaluator_manifest_v0.json": manifest_path.read_bytes(),
              "llamaguard_summary.json": semantic._canonical(summary)}
    # Deliberately incomplete envelope and self-asserted report. Production must
    # reject these; success tests mock the fresh backend invocation in-process.
    report = {"status": "verified", "errors": [],
              "attestation": {"verified": True, "backend": "gh-attestation"}}
    attested = {**hosted, "llamaguard_summary.bundle.json": b"{}\n",
                "llamaguard_summary.envelope.json": semantic._canonical({
                    "verification": {"verified_at": "2026-11-12T10:01:00Z"}}),
                "llamaguard_attestation_verifier_v1.json": semantic._canonical(report)}
    work = tmp_path / "work"
    work.mkdir()
    return [REPO, hosted, attested, identity, work], report


def _mock_signature_only(monkeypatch, saved_report):
    original = semantic._run
    calls = []

    def run(argv, **kwargs):
        if "'r2c13_builder'" in argv[-1]:
            calls.append(argv)
            return 0, semantic._canonical({
                "schema_version": "pulsemech_step5c_local_r2_attestation_core_v0", "report": saved_report,
                "verified_at": "2026-11-12T10:01:00Z", "bundle_sha256": semantic._digest(b"{}\n")}), b""
        return original(argv, **kwargs)

    monkeypatch.setattr(semantic, "_run", run)
    monkeypatch.setattr(semantic, "_trusted_gh", lambda: (b"not-executed-test-placeholder", {
        "sha256": "d" * 64, "bytes": 29, "trust_scope": "unit_test_mock_only"}))
    return calls


def test_real_llamaguard_content_rebuild_and_controlled_signature_flow(llama_fixture, monkeypatch):
    args, saved_report = llama_fixture
    calls = _mock_signature_only(monkeypatch, saved_report)
    report = semantic.verify_llamaguard(*args)
    assert report["content"]["record_count"] == 6
    assert report["content"]["safe_count"] == 6
    assert report["fresh_content_checker_executed"] is True
    assert report["original_runtime_reads_proven"] is False
    assert report["model_execution_replayed"] is False
    assert len(calls) == 1
    assert list(args[-1].iterdir()) == []


def test_llamaguard_saved_verified_report_cannot_replace_actual_verifier(llama_fixture, monkeypatch):
    args, _ = llama_fixture
    # The placeholder is never executed: the real unchanged attestation driver
    # rejects the forged envelope before reaching the backend.
    monkeypatch.setattr(semantic, "_trusted_gh", lambda: (b"not-executed", {"sha256": "a" * 64}))
    with pytest.raises(semantic.SemanticVerificationError, match="fresh_signature_rejected"):
        semantic.verify_llamaguard(*args)
    assert list(args[-1].iterdir()) == []


@pytest.mark.parametrize("change", ["case_input", "run_id", "token_budget", "classification", "missing_row"])
def test_actual_llamaguard_content_checker_rejects_bound_record_changes(llama_fixture, monkeypatch, change):
    args, _ = llama_fixture
    records = [json.loads(line) for line in args[1]["llamaguard_raw.jsonl"].splitlines()]
    if change == "case_input":
        records[0]["input"] = "An unreviewed prompt"
    elif change == "run_id":
        records[0]["run"]["run_id"] += 1
    elif change == "token_budget":
        records[0]["inference"]["max_new_tokens"] = 21
    elif change == "classification":
        records[0]["llamaguard"]["label"] = "unsafe"
    else:
        records.pop()
    mutated = b"".join(semantic._canonical(row) for row in records)
    args[1]["llamaguard_raw.jsonl"] = args[2]["llamaguard_raw.jsonl"] = mutated
    monkeypatch.setattr(semantic, "_trusted_gh", lambda: pytest.fail("invalid content reached backend"))
    with pytest.raises(semantic.SemanticVerificationError, match="fresh_content_rejected"):
        semantic.verify_llamaguard(*args)


def test_llamaguard_artifact_copies_must_match(llama_fixture):
    args, _ = llama_fixture
    args[2]["llamaguard_summary.json"] += b" "
    with pytest.raises(semantic.SemanticVerificationError, match="artifact_copies_disagree"):
        semantic.verify_llamaguard(*args)


def test_llamaguard_cannot_drop_bundle_or_saved_report(llama_fixture):
    args, _ = llama_fixture
    args[2].pop("llamaguard_summary.bundle.json")
    with pytest.raises(semantic.SemanticVerificationError, match="member_set_mismatch"):
        semantic.verify_llamaguard(*args)


def test_llamaguard_fails_closed_when_trusted_backend_is_unavailable(llama_fixture, monkeypatch):
    args, _ = llama_fixture

    def unavailable():
        raise semantic.SemanticVerificationError("trusted_gh_unavailable")

    monkeypatch.setattr(semantic, "_trusted_gh", unavailable)
    with pytest.raises(semantic.SemanticVerificationError, match="trusted_gh_unavailable"):
        semantic.verify_llamaguard(*args)


def test_controlled_llamaguard_report_is_independent_of_temp_directory(llama_fixture, monkeypatch, tmp_path):
    args, report = llama_fixture
    _mock_signature_only(monkeypatch, report)
    first = semantic._canonical(semantic.verify_llamaguard(*args))
    args[-1] = tmp_path / "second-work"
    args[-1].mkdir()
    second = semantic._canonical(semantic.verify_llamaguard(*args))
    assert first == second
    assert str(tmp_path).encode() not in first


def test_llamaguard_original_times_must_fit_explicit_run(llama_fixture):
    args, _ = llama_fixture
    args[3] = {**args[3], "run_started_at": "2026-11-12T10:00:30Z",
               "updated_at": "2026-11-12T10:02:00Z"}
    with pytest.raises(semantic.SemanticVerificationError, match="outside_original_run"):
        semantic.verify_llamaguard(*args)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
