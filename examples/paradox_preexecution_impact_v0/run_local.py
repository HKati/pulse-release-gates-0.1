#!/usr/bin/env python3
"""Owner-authorized scratch launcher for PD-SM-02.

The default operation is preflight only.  Actual source execution requires the
exact authorization literal in profile.json, an eligible independently checked
assessment, a sealed in-memory copy of the exact source bytes, and a new empty
output directory.  This is a local research launcher, not release authority or a
production sandbox.
"""
from __future__ import annotations

import argparse
import ast
import fcntl
import hashlib
import json
import math
import os
import select
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable


PREFLIGHT_SCHEMA = "pd_sm_02_launch_preflight_v0"
EXECUTION_SCHEMA = "pd_sm_02_scratch_execution_v0"


class LaunchError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(code if not detail else f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise LaunchError("duplicate_json_key", key)
        out[key] = value
    return out


def strict_json(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                LaunchError("non_finite_json_number", value)
            ),
        )
    except UnicodeDecodeError as exc:
        raise LaunchError("json_not_utf8", str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise LaunchError("invalid_json", str(exc)) from exc


def canonical_bytes(value: Any) -> bytes:
    def walk(item: Any) -> None:
        if isinstance(item, float) and not math.isfinite(item):
            raise LaunchError("non_finite_value")
        if isinstance(item, dict):
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise LaunchError("non_string_json_key")
                walk(nested)
        elif isinstance(item, list):
            for nested in item:
                walk(nested)

    walk(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise LaunchError(code, detail)


def preflight(
    profile: dict[str, Any], candidate: bytes, assessment: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": PREFLIGHT_SCHEMA,
        "profile_id": profile.get("profile_id"),
        "candidate_sha256": sha256(candidate),
        "profile_sha256": sha256(canonical_bytes(profile)),
        "context_sha256": sha256(canonical_bytes(context)),
        "assessment_sha256": sha256(canonical_bytes(assessment)),
        "execution_started": False,
        "authority_effect": "none",
    }
    if assessment.get("schema_version") != "pd_sm_02_impact_report_v0":
        record.update(status="NO_UNCHECKED_LAUNCH", reason="assessment_schema")
        return record
    if assessment.get("candidate_sha256") != record["candidate_sha256"]:
        record.update(status="BINDING_REJECTED", reason="candidate_sha256")
        return record
    if assessment.get("profile_sha256") != record["profile_sha256"]:
        record.update(status="BINDING_REJECTED", reason="profile_sha256")
        return record
    if assessment.get("context_sha256") != record["context_sha256"]:
        if assessment.get("bound_environment_identity") != context.get("environment_identity"):
            record.update(status="UNRESOLVED_OR_BINDING_REJECTED", reason="environment_identity")
        else:
            record.update(status="BINDING_REJECTED", reason="context_sha256")
        return record
    if assessment.get("bound_subject_request") != context.get("binding"):
        record.update(status="BINDING_REJECTED", reason="subject_request_binding")
        return record
    eligible = set(profile.get("launch_contract", {}).get("eligible_assessments", []))
    if assessment.get("assessment") not in eligible:
        record.update(status="NO_UNCHECKED_LAUNCH", reason="assessment_not_eligible")
        return record
    required_pairs = {
        "source_binding_status": "BOUND",
        "supported_profile_status": "SUPPORTED",
        "source_model_mapping_status": "VERIFIED_FOR_SUPPORTED_LANGUAGE",
        "coverage_status": "COMPLETE_FOR_DECLARED_FINITE_PROFILE",
        "model_nonempty_status": "NONEMPTY",
        "invariant_assessment": "SATISFIED",
        "useful_operation_assessment": "SATISFIED",
        "proof_applicability_status": "ESTABLISHED_FOR_DECLARED_PROFILE",
        "execution_observation_status": "NOT_RUN",
    }
    for key, expected in required_pairs.items():
        if assessment.get(key) != expected:
            record.update(status="NO_UNCHECKED_LAUNCH", reason=f"assessment_field:{key}")
            return record
    if assessment.get("unresolved_critical_obligations") != []:
        record.update(status="NO_UNCHECKED_LAUNCH", reason="unresolved_critical_obligations")
        return record
    record.update(status="ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH", reason=None)
    return record


def _validate_runtime_ast(source: bytes, profile: dict[str, Any]) -> str:
    """Third parser used at launch; return the exact decoded text it checked."""
    language = profile["candidate_language"]
    require(len(source) <= int(language["max_source_bytes"]), "runtime_source_too_large")
    require(not source.startswith(b"\xef\xbb\xbf"), "runtime_utf8_bom_not_allowed")
    if language.get("final_newline_required"):
        require(source.endswith(b"\n"), "runtime_final_newline_required")
    try:
        text = source.decode(language.get("encoding", "utf-8"))
        module = ast.parse(text, filename="<sealed-pd-sm-02-candidate>", mode="exec")
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise LaunchError("runtime_source_parse", str(exc)) from exc
    require(len(module.body) == 1 and isinstance(module.body[0], ast.FunctionDef), "runtime_module_shape")
    fn = module.body[0]
    require(fn.name == language["entrypoint"], "runtime_entrypoint")
    require(not fn.decorator_list and fn.returns is None, "runtime_function_metadata")
    args = fn.args
    require(
        not args.posonlyargs and not args.args and args.vararg is None and not args.kwonlyargs
        and args.kwarg is None and not args.defaults and not args.kw_defaults,
        "runtime_arguments",
    )
    allowed = set(language["primitives"])
    aliases: set[str] = set()
    for statement in fn.body:
        if isinstance(statement, ast.Assign):
            require(len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name), "runtime_assignment")
            require(isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str), "runtime_assignment_value")
            name = statement.targets[0].id
            require(name not in aliases and name not in allowed and not name.startswith("__"), "runtime_alias")
            aliases.add(name)
            continue
        require(isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call), "runtime_statement")
        call = statement.value
        require(isinstance(call.func, ast.Name) and call.func.id in allowed, "runtime_call")
        require(not call.keywords, "runtime_keyword")
        for arg in call.args:
            require(
                (isinstance(arg, ast.Constant) and isinstance(arg.value, str))
                or (isinstance(arg, ast.Name) and arg.id in aliases),
                "runtime_call_argument",
            )
    return text


def _compile_runtime_candidate(source: bytes, profile: dict[str, Any]) -> Any:
    # Compile the same decoded text inspected by all three parsers.  Passing
    # bytes to compile() would re-interpret a Python encoding cookie and could
    # create executable statements that were comments in the checked text.
    text = _validate_runtime_ast(source, profile)
    return compile(text, "<sealed-pd-sm-02-candidate>", "exec")


def _seal_source(source: bytes) -> tuple[int, str]:
    require(hasattr(os, "memfd_create"), "memfd_unavailable")
    fd = os.memfd_create("pd-sm-02-candidate", flags=getattr(os, "MFD_ALLOW_SEALING", 0))
    try:
        view = memoryview(source)
        offset = 0
        while offset < len(view):
            written = os.write(fd, view[offset:])
            if written <= 0:
                raise LaunchError("memfd_short_write")
            offset += written
        os.lseek(fd, 0, os.SEEK_SET)
        seals = 0
        for name in ("F_SEAL_SEAL", "F_SEAL_SHRINK", "F_SEAL_GROW", "F_SEAL_WRITE"):
            seals |= getattr(fcntl, name, 0)
        require(seals != 0 and hasattr(fcntl, "F_ADD_SEALS"), "memfd_seals_unavailable")
        fcntl.fcntl(fd, fcntl.F_ADD_SEALS, seals)
        reread = os.read(fd, len(source) + 1)
        require(reread == source, "sealed_source_readback")
        os.lseek(fd, 0, os.SEEK_SET)
        return fd, sha256(reread)
    except BaseException:
        os.close(fd)
        raise


def _read_line(fd: int, limit: int = 65536, timeout: float = 5.0) -> bytes:
    data = bytearray()
    deadline = time.monotonic() + timeout
    while not data.endswith(b"\n"):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise LaunchError("pipe_timeout")
        part = os.read(fd, 1)
        if not part:
            raise LaunchError("pipe_eof")
        data += part
        if len(data) > limit:
            raise LaunchError("pipe_frame_too_large")
    return bytes(data)


def _monitor(request_fd: int, ack_fd: int, audit_path: Path) -> None:
    try:
        raw = _read_line(request_fd)
        request = strict_json(raw)
        record = {"event": "INTENT", "request": request, "request_sha256": sha256(canonical_bytes(request))}
        raw_record = canonical_bytes(record) + b"\n"
        audit_fd = os.open(audit_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            require(os.write(audit_fd, raw_record) == len(raw_record), "audit_short_write")
            os.fsync(audit_fd)
        finally:
            os.close(audit_fd)
        ack = {"recorded": True, "request_sha256": sha256(canonical_bytes(request))}
        os.write(ack_fd, canonical_bytes(ack) + b"\n")
        os._exit(0)
    except BaseException:
        os._exit(90)


def _execute_in_child(
    source_fd: int, source_digest: str, profile: dict[str, Any], context: dict[str, Any],
    sink_path: Path, audit_path: Path, result_fd: int,
) -> None:
    try:
        source = os.read(source_fd, int(profile["candidate_language"]["max_source_bytes"]) + 1)
        require(sha256(source) == source_digest, "sealed_source_digest")
        candidate_code = _compile_runtime_candidate(source, profile)
        protected = profile["protected_contract"]
        binding = context["binding"]
        evidence = context["evidence"]
        closure = set(evidence.get("facts", []))
        changed = True
        while changed:
            changed = False
            for rule in evidence.get("rules", []):
                if set(rule["premises"]).issubset(closure) and rule["conclusion"] not in closure:
                    closure.add(rule["conclusion"])
                    changed = True

        state: dict[str, Any] = {
            "actor": None, "request": None, "used": set(), "reserved": set(),
            "ack": None, "audit": None, "effects": [], "monitor_pid": None,
            "request_pipe": None, "ack_pipe": None,
        }

        def actor(name: str) -> None:
            state["actor"] = name

        def bind_request(request_id: str, target: str, payload: str) -> None:
            request = {"request_id": request_id, "target": target, "payload": payload}
            require(state["request"] is None, "runtime_duplicate_request")
            state["request"] = request

        def require_source(obligation: str) -> None:
            require(obligation in closure, "runtime_source_not_justified")

        def require_request_match(request_id: str) -> None:
            expected = {key: binding[key] for key in ("request_id", "target", "payload")}
            require(state["request"] == expected and request_id == binding["request_id"], "runtime_request_mismatch")

        def require_unused(request_id: str) -> None:
            require(
                state["request"] is not None and state["request"]["request_id"] == request_id,
                "runtime_request_id",
            )
            require(request_id not in state["used"], "runtime_request_used")

        def reserve(request_id: str) -> None:
            require(
                state["request"] is not None and state["request"]["request_id"] == request_id,
                "runtime_reservation_request",
            )
            state["used"].add(request_id)
            state["reserved"].add(request_id)

        def broker_request(actor_name: str, request_id: str) -> None:
            require(state["monitor_pid"] is None, "runtime_monitor_capacity")
            require(state["actor"] == actor_name, "runtime_actor_binding")
            require(state["request"] is not None and state["request"]["request_id"] == request_id, "runtime_request_id")
            req_r, req_w = os.pipe()
            ack_r, ack_w = os.pipe()
            pid = os.fork()
            if pid == 0:
                os.close(req_w); os.close(ack_r)
                _monitor(req_r, ack_w, audit_path)
            os.close(req_r); os.close(ack_w)
            os.write(req_w, canonical_bytes(state["request"]) + b"\n")
            os.close(req_w)
            state["ack"] = strict_json(_read_line(ack_r))
            os.close(ack_r)
            _, status = os.waitpid(pid, 0)
            require(os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0, "runtime_monitor_failed")
            state["monitor_pid"] = pid
            records = [strict_json(line + b"\n") for line in audit_path.read_bytes().splitlines()]
            state["audit"] = records[0]["request"] if len(records) == 1 else None

        def require_ack_match(request_id: str) -> None:
            request = state["request"]
            expected = {"recorded": True, "request_sha256": sha256(canonical_bytes(request))}
            require(request is not None and request["request_id"] == request_id and state["ack"] == expected, "runtime_ack_mismatch")

        def require_ack_present(request_id: str) -> None:
            require(state["ack"] is not None and state["request"]["request_id"] == request_id, "runtime_ack_missing")

        def require_audit_match(request_id: str) -> None:
            require(state["request"] is not None and state["request"]["request_id"] == request_id and state["audit"] == state["request"], "runtime_audit_mismatch")

        def require_audit_present(request_id: str) -> None:
            require(state["audit"] is not None and state["request"]["request_id"] == request_id, "runtime_audit_missing")

        def append_sink(request_id: str) -> None:
            request = state["request"]
            require(request is not None and request["request_id"] == request_id, "runtime_effect_request")
            require(request_id in state["reserved"], "runtime_effect_unreserved")
            with sink_path.open("ab", buffering=0) as handle:
                raw = request["payload"].encode("utf-8")
                count = handle.write(raw)
                os.fsync(handle.fileno())
            state["effects"].append({"request_id": request_id, "bytes": count})

        def direct_sink_write(actor_name: str, request_id: str) -> None:
            raise LaunchError("direct_effect_route_not_admitted", f"{actor_name}:{request_id}")

        namespace = {
            "__builtins__": {},
            "actor": actor,
            "bind_request": bind_request,
            "require_source": require_source,
            "require_request_match": require_request_match,
            "require_unused": require_unused,
            "reserve": reserve,
            "broker_request": broker_request,
            "require_ack_match": require_ack_match,
            "require_ack_present": require_ack_present,
            "require_audit_match": require_audit_match,
            "require_audit_present": require_audit_present,
            "append_sink": append_sink,
            "direct_sink_write": direct_sink_write,
        }
        exec(candidate_code, namespace, namespace)
        namespace[profile["candidate_language"]["entrypoint"]]()
        result = {
            "status": "COMPLETED",
            "effects": state["effects"],
            "sink_sha256": sha256(sink_path.read_bytes()),
            "sink_bytes": len(sink_path.read_bytes()),
            "audit_sha256": sha256(audit_path.read_bytes()),
            "audit_bytes": len(audit_path.read_bytes()),
        }
        os.write(result_fd, canonical_bytes(result) + b"\n")
        os._exit(0)
    except BaseException as exc:
        error = {"status": "FAILED", "error": type(exc).__name__, "detail": str(exc)}
        try:
            os.write(result_fd, canonical_bytes(error) + b"\n")
        except BaseException:
            pass
        os._exit(91)


def execute_scratch(
    profile: dict[str, Any], candidate: bytes, assessment: dict[str, Any], context: dict[str, Any],
    output: Path, authorization: str,
) -> dict[str, Any]:
    pre = preflight(profile, candidate, assessment, context)
    require(pre["status"] == "ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH", "launch_preflight", pre["status"])
    require(authorization == profile["launch_contract"]["authorization_literal"], "authorization_literal")
    require(os.name == "posix" and hasattr(os, "fork"), "posix_fork_required")
    if profile["launch_contract"].get("single_thread_supervisor_required"):
        require(Path("/proc/self/task").is_dir(), "thread_inventory_unavailable")
        require(len(list(Path("/proc/self/task").iterdir())) == 1, "single_thread_supervisor_required")
    output = output.resolve(strict=False)
    require(output.parent.is_dir() and not output.parent.is_symlink(), "output_parent")
    require(not output.exists(), "output_exists")
    output.mkdir(parents=True, exist_ok=False)
    sink = output / "sink.bin"
    audit = output / "monitor.jsonl"
    sink.write_bytes(b"")
    audit.write_bytes(b"")
    source_fd, source_digest = _seal_source(candidate)
    result_r, result_w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(result_r)
        _execute_in_child(source_fd, source_digest, profile, context, sink, audit, result_w)
    os.close(result_w)
    os.close(source_fd)
    try:
        raw = _read_line(result_r, timeout=float(profile["launch_contract"]["timeout_seconds"]))
    except BaseException:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
        os.close(result_r)
        raise
    os.close(result_r)
    _, status = os.waitpid(pid, 0)
    child = strict_json(raw)
    observed = {
        "schema_version": EXECUTION_SCHEMA,
        "preflight": pre,
        "child": child,
        "child_normal_exit": os.WIFEXITED(status),
        "child_exit_code": os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
        "sink_sha256": sha256(sink.read_bytes()),
        "sink_bytes": len(sink.read_bytes()),
        "audit_sha256": sha256(audit.read_bytes()),
        "audit_bytes": len(audit.read_bytes()),
        "candidate_sha256": source_digest,
        "execution_observation_status": "COMPLETED" if child.get("status") == "COMPLETED" else "FAILED",
        "authority_effect": "none",
    }
    (output / "RESULT.json").write_bytes(json.dumps(observed, sort_keys=True, indent=2).encode("utf-8") + b"\n")
    return observed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--assessment", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--authorize-scratch-execution")
    args = parser.parse_args()

    profile = strict_json(args.profile.read_bytes())
    candidate = args.candidate.read_bytes()
    assessment = strict_json(args.assessment.read_bytes())
    context = strict_json(args.context.read_bytes())
    require(isinstance(profile, dict) and isinstance(assessment, dict) and isinstance(context, dict), "record_type")
    if args.preflight_only:
        result = preflight(profile, candidate, assessment, context)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(json.dumps(result, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        return 0 if result["status"] == "ELIGIBLE_FOR_EXPLICIT_SCRATCH_LAUNCH" else 1
    require(args.authorize_scratch_execution is not None, "missing_explicit_authorization")
    require(args.model is not None, "model_required_for_execution")
    checker = Path(__file__).resolve().with_name("check_impact.py")
    require(checker.is_file(), "checker_missing")
    with tempfile.TemporaryDirectory(prefix="pd-sm-02-check-") as temporary:
        replay_path = Path(temporary) / "assessment.json"
        completed = subprocess.run(
            [
                sys.executable, "-I", "-S", "-B", str(checker),
                "--profile", str(args.profile), "--candidate", str(args.candidate),
                "--model", str(args.model), "--context", str(args.context),
                "--output", str(replay_path),
            ],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, timeout=30,
        )
        require(completed.returncode == 0, "checker_replay_not_eligible", completed.stderr.decode("utf-8", "replace"))
        replayed = strict_json(replay_path.read_bytes())
        require(canonical_bytes(replayed) == canonical_bytes(assessment), "assessment_replay_mismatch")
    result = execute_scratch(profile, candidate, assessment, context, args.output, args.authorize_scratch_execution)
    return 0 if result["execution_observation_status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
