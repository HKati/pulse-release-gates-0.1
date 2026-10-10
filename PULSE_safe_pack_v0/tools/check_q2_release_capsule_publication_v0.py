#!/usr/bin/env python3
"""Owner-only capsule publication supervision; no inference or release authority."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q2_intake_io_v0 as io
import load_q2_release_intake_v0 as intake
import check_q2_release_intake_v0 as independent

PROFILE = io.PACK + "profiles/q2_release_capsule_publication_v0.json"
SCHEMA = "schemas/q2_release_capsule_publication_v0.schema.json"
BUILDER = io.PACK + "tools/build_q2_release_capsule_v0.py"
CHECKER = io.PACK + "tools/check_q2_release_capsule_publication_v0.py"
WORKFLOW = ".github/workflows/q2_release_capsule_publication_v0.yml"
SOURCE_PATHS = tuple(sorted(set(io.SOURCE_PATHS) | {PROFILE, SCHEMA, BUILDER, CHECKER, WORKFLOW}))
TOKEN = "PULSE_Q2_PUBLICATION_TOKEN"
REPOSITORY = "HKati/pulse-release-gates-0.1"


def load_profile(repo):
    p = io.strict_json(io.read_file(repo / PROFILE, 128 * 1024))
    contract = io.strict_json(io.read_file(repo / SCHEMA, 128 * 1024))
    # The bootstrap child intentionally has no jsonschema dependency. Canonical
    # equality implements this closed schema's const without importing payloads.
    io.require(io.encode(p) == io.encode(contract["$defs"]["publication_profile"]["const"]),
               "q2_source_mismatch")
    io.require(p["record_type"] == "q2_release_capsule_publication_profile_v0" and
               p["source_paths"] == list(SOURCE_PATHS) and p["authority_effect"] == "none" and
               p["production_gate_eligible"] is False and p["current_inference_count"] == 0,
               "q2_source_mismatch")
    return p


def source_closure(repo, revision):
    """Own explicit closure; do not expand the intake's source-role contract."""
    io.require(re.fullmatch(r"[0-9a-f]{40}", revision or "") is not None, "q2_source_mismatch")
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
           "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
    def git(args):
        p = subprocess.run(["/usr/bin/git", "--no-replace-objects", "-c", "credential.helper=", *args],
                           cwd=repo, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=15, check=False)
        io.require(p.returncode == 0 and len(p.stdout) <= 65536, "q2_source_mismatch")
        return p.stdout
    io.require(git(["rev-parse", "--verify", "HEAD^{commit}"]) == revision.encode() + b"\n",
               "q2_source_mismatch")
    entries = {}
    for row in git(["ls-tree", "-rz", "--full-tree", revision, "--", *SOURCE_PATHS]).split(b"\0"):
        if row:
            metadata, name = row.split(b"\t")
            entries[name.decode("ascii")] = metadata.decode("ascii").split()
    io.require(set(entries) == set(SOURCE_PATHS), "q2_source_mismatch")
    result = []
    for name in sorted(entries):
        raw = io.read_file(repo / name, 2 * 1024 * 1024)
        mode = "100755" if (repo / name).stat().st_mode & 0o111 else "100644"
        oid = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        io.require(entries[name] == [mode, "blob", oid], "q2_source_mismatch")
        result.append({"path": name, "size_bytes": len(raw), "sha256": io.digest(raw)})
    return result


def authorize(repo, env, profile):
    """All local authority checks precede any network or payload IO."""
    a = profile["authorization"]
    revision = env.get("GITHUB_SHA", "")
    wanted = {"GITHUB_REPOSITORY": REPOSITORY, "GITHUB_EVENT_NAME": "workflow_dispatch",
              "GITHUB_REF": "refs/heads/main", "GITHUB_WORKFLOW_SHA": revision,
              "GITHUB_WORKFLOW": "Q2 release capsule publication v0", "GITHUB_RUN_ATTEMPT": "1",
              "GITHUB_WORKFLOW_REF": REPOSITORY + "/" + WORKFLOW + "@refs/heads/main",
              "GITHUB_ACTOR": "HKati", "GITHUB_TRIGGERING_ACTOR": "HKati",
              "GITHUB_ACTOR_ID": "128643840", "GITHUB_ACTIONS": "true", "RUNNER_OS": "Linux",
              "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_WORKSPACE": str(repo),
              "PULSE_Q2_PUBLICATION_SOURCE": revision}
    io.require(all(env.get(k) == v for k, v in wanted.items()) and
               re.fullmatch(r"[1-9][0-9]{0,23}", env.get("GITHUB_RUN_ID", "")) is not None and
               a == {"repository": REPOSITORY, "workflow": WORKFLOW,
                     "workflow_name": wanted["GITHUB_WORKFLOW"], "actor": "HKati", "actor_id": 128643840,
                     "event": "workflow_dispatch", "ref": "refs/heads/main", "run_attempt": 1},
               "q2_context_rejected")
    io.require(bool(env.get("GITHUB_EVENT_PATH")), "q2_context_rejected")
    event = io.strict_json(io.read_file(Path(env["GITHUB_EVENT_PATH"]), 512 * 1024))
    sender = event.get("sender", {})
    io.require(event.get("inputs") == {"source_commit": revision} and
               event.get("ref") in ("main", "refs/heads/main") and
               sender.get("login") == "HKati" and type(sender.get("id")) is int and
               sender["id"] == 128643840 and sender.get("type") == "User" and
               event.get("repository", {}).get("full_name") == REPOSITORY, "q2_context_rejected")
    sources = source_closure(repo, revision)
    return {"repository": REPOSITORY, "workflow": WORKFLOW, "source_commit": revision,
            "run_id": env["GITHUB_RUN_ID"], "run_attempt": 1}, sources


def api_json(transport, suffix, deadline):
    # Suffixes are formed internally from fixed paths and validated numeric IDs.
    request = urllib.request.Request("https://api.github.com/repos/" + REPOSITORY + suffix,
        headers={"Authorization": "Bearer " + transport.token, "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"})
    with transport.opener.open(request, timeout=deadline.remaining()) as response:
        io.require(response.status == 200, "q2_transport_rejected")
        return io.strict_json(response.read(512 * 1024 + 1), 512 * 1024)


def check_origin(artifact, run, expectation):
    """Actual API origin, expiry, attempt and source; never select latest by name."""
    origin = artifact.get("workflow_run", {})
    io.require(type(expectation["artifact_id"]) is int and expectation["artifact_id"] > 0 and
               type(artifact.get("id")) is int and artifact["id"] == expectation["artifact_id"] and
               artifact.get("name") == expectation["artifact_name"] and
               artifact.get("expired") is False and
               artifact.get("size_in_bytes") == expectation["archive_size_bytes"] and
               artifact.get("digest") == "sha256:" + expectation["archive_sha256"] and
               str(origin.get("id")) == expectation["run_id"] and
               origin.get("repository_id") == origin.get("head_repository_id") == 1061766508 and
               origin.get("head_branch") == "main" and
               origin.get("head_sha") == expectation["source_commit"] and
               type(run.get("id")) is int and str(run["id"]) == expectation["run_id"] and
               type(run.get("run_attempt")) is int and run["run_attempt"] == expectation["run_attempt"] and
               run.get("head_sha") == expectation["source_commit"] and
               run.get("repository", {}).get("full_name") == REPOSITORY and
               run.get("head_repository", {}).get("full_name") == REPOSITORY and
               run.get("event") == "workflow_dispatch" and run.get("head_branch") == "main",
               "q2_transport_rejected")


def download_artifact(transport, expected, destination, deadline):
    io.require(type(expected["artifact_id"]) is int and expected["artifact_id"] > 0 and
               re.fullmatch(r"[1-9][0-9]{0,23}", expected["run_id"]) is not None and
               expected["repository"] == REPOSITORY and expected["run_attempt"] == 1,
               "q2_transport_rejected")
    artifact = api_json(transport, f'/actions/artifacts/{expected["artifact_id"]}', deadline)
    run = api_json(transport, f'/actions/runs/{expected["run_id"]}/attempts/1', deadline)
    check_origin(artifact, run, expected)
    transport.download(REPOSITORY, expected["artifact_id"], expected, destination, deadline)


def download_bootstrap(expected, destination, deadline):
    """Uncredentialed, fixed profile URL; at most one validated GitHub redirect."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), io._NoRedirect())
    url = expected["url"]
    parsed = urllib.parse.urlsplit(url)
    io.require(parsed.scheme == "https" and parsed.hostname in ("github.com", "files.pythonhosted.org")
               and not parsed.username and not parsed.password and not parsed.fragment, "q2_transport_rejected")
    try:
        response = opener.open(urllib.request.Request(url), timeout=deadline.remaining())
    except urllib.error.HTTPError as exc:
        location = exc.headers.get("Location", "")
        status = exc.code
        exc.close()
        redirect = urllib.parse.urlsplit(location)
        io.require(status in (301, 302, 303, 307, 308) and parsed.hostname == "github.com" and
                   redirect.scheme == "https" and redirect.port in (None, 443) and
                   redirect.hostname == "release-assets.githubusercontent.com" and
                   not redirect.username and not redirect.password and not redirect.fragment,
                   "q2_transport_rejected")
        response = opener.open(urllib.request.Request(location), timeout=deadline.remaining())
    with response:
        io.require(response.status == 200 and response.headers.get("Content-Length") in
                   (None, str(expected["archive_size_bytes"])), "q2_transport_rejected")
        size, hashed = 0, hashlib.sha256()
        with destination.open("xb") as output:
            while True:
                deadline.remaining()
                raw = response.read(min(65536, expected["archive_size_bytes"] + 1 - size))
                if not raw:
                    break
                size += len(raw)
                io.require(size <= expected["archive_size_bytes"], "q2_archive_limit")
                output.write(raw)
                hashed.update(raw)
        io.require(size == expected["archive_size_bytes"] and hashed.hexdigest() == expected["archive_sha256"],
                   "q2_digest_mismatch")


def check_capsule(repo, private, profile, deadline):
    """Verify every member and replay with the unchanged independent semantic engine.

    These are byte-comparison parameters, not a fabricated hosted intake request.
    No evaluation identity, invented artifact ID or request-authentication claim.
    """
    p = intake.load_profile(repo)
    expected = profile["capsule"]
    io.require(io.file_binding(private / "capsule.zip", p["limits"]["capsule_archive_bytes"], deadline) ==
               {k: expected[k] for k in ("archive_size_bytes", "archive_sha256")}, "q2_digest_mismatch")
    parameters = {k: p[k] for k in ("capture_expectation", "selection", "comparison_profile",
                                    "reduction_profile", "native_verification_mode")}
    parameters["release_subject"] = {k: expected[k] for k in
                                    ("archive_size_bytes", "archive_sha256", "capsule_manifest_sha256")}
    result = independent.check_bound_inputs(repo, private, parameters, p, intake.empty_result(p), deadline)
    io.require(result["checks"] == {"request": False, "capture": True, "subject": True,
                                    "replay": True, "summary": True} and result["input_valid"] is True and
               result["metric_pass"] is False and result["process_exit"] == 1, "q2_replay_rejected")
    return result


def environment_record():
    return {"implementation": platform.python_implementation(), "python": platform.python_version(),
            "unicode": unicodedata.unidata_version, "zlib_compile": zlib.ZLIB_VERSION,
            "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION}


def install_verifier_dependencies(private, profile, deadline):
    """Install only the eight preserved wheels, with no package-index resolution.

    This stdlib-only path runs before any verifier dependency is imported. The
    workflow uses a fresh setup-python environment; children receive no token.
    """
    wheels = private / "verifier-wheels"
    wheels.mkdir(mode=0o700)
    limits, prep = profile["limits"], profile["preparation"]
    with io.Archive(private / "preparation.zip", maximum_bytes=prep["archive_size_bytes"],
                    max_members=limits["preparation_members"], member_bytes=limits["member_bytes"],
                    expanded_bytes=limits["preparation_expanded_bytes"], deadline=deadline,
                    expected_sha256=prep["archive_sha256"]) as archive:
        for row in profile["verifier_wheels"]:
            raw = archive.read("q2-runtime-preparation/" + row["path"], row["size"])
            io.require(len(raw) == row["size"] and io.digest(raw) == row["sha256"], "q2_digest_mismatch")
            io.write_new(wheels / Path(row["path"]).name, raw)
    requirements = private / "verifier-requirements.txt"
    io.write_new(requirements, "".join(f'{r["name"]}=={r["version"]} --hash=sha256:{r["sha256"]}\n'
                                      for r in profile["verifier_wheels"]).encode("ascii"))
    pip = profile["pip"]
    # The installer is a separate, pinned bootstrap, never a payload dependency.
    raw = io.read_file(private / pip["filename"], pip["archive_size_bytes"], pip["archive_sha256"], deadline)
    io.require(len(raw) == pip["archive_size_bytes"], "q2_digest_mismatch")
    installer = private / "verified-pip.whl"
    io.write_new(installer, raw)
    command = [sys.executable, "-I", "-B", "-c",
               "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('pip',run_name='__main__')",
               str(installer), "--isolated", "--disable-pip-version-check", "--no-cache-dir",
               "install", "--no-index", "--no-deps", "--require-hashes", "--only-binary=:all:",
               "--force-reinstall", "--no-compile", "--find-links", str(wheels), "-r", str(requirements)]
    rc = io.private_process(command, cwd=private, environment=io.replay_environment(private),
                            timeout=deadline.remaining(90), new_session=True)
    io.require(rc == 0, "q2_replay_environment")


def copy_verified(source, destination, expected, deadline):
    """Transfer held, digest-bound bytes only; never reuse a destination file."""
    fd, before = io._open_regular(source)
    try:
        io.require(before.st_size == expected["archive_size_bytes"], "q2_digest_mismatch")
        target = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(target, "wb") as out:
            hashed, size = hashlib.sha256(), 0
            while True:
                deadline.remaining()
                raw = os.read(fd, 65536)
                if not raw:
                    break
                size += len(raw)
                io.require(size <= before.st_size, "q2_unstable_input")
                hashed.update(raw)
                out.write(raw)
            io.require(size == before.st_size and hashed.hexdigest() == expected["archive_sha256"] and
                       io._identity(before) == io._identity(os.fstat(fd)), "q2_digest_mismatch")
            out.flush()
            os.fsync(out.fileno())
    finally:
        os.close(fd)


def private_verification_record(context, profile):
    """Closed internal result. This is neither authentication nor a public receipt."""
    return {"record_type": "q2_capsule_private_verification_v0", **context,
            "capsule": profile["capsule"], "verification_environment": environment_record(),
            "checks": {"request": False, "capture": True, "subject": True, "replay": True, "summary": True},
            "input_valid": True, "metric_pass": False, "process_exit": 1,
            "authority_effect": "none", "production_gate_eligible": False}


def check_private(repo, private):
    """Credential-free semantic child; caller must authenticate and clean up."""
    io.require(not any(k.startswith("PULSE_Q2_") for k in os.environ), "q2_context_rejected")
    private = io.check_private_directory(repo, private)
    with io.interrupt_boundary(180) as deadline:
        profile = load_profile(repo)
        context = io.strict_json(io.read_file(private / "verification-context.json", 128 * 1024))
        io.require(set(context) == {"binding", "source_bindings"} and
                   source_closure(repo, context["binding"]["source_commit"]) == context["source_bindings"],
                   "q2_source_mismatch")
        check_capsule(repo, private, profile, deadline)
        io.require(source_closure(repo, context["binding"]["source_commit"]) == context["source_bindings"],
                   "q2_source_mismatch")
        io.write_new(private / "verification.json", io.encode(private_verification_record(context, profile)))


def verify_in_fresh_workspace(repo, build_private, parent, profile, binding, sources, deadline):
    """Only two bound archives and trusted context cross the build/check boundary."""
    context = {"binding": binding, "source_bindings": sources}
    with io.private_workspace(repo, str(parent)) as work:
        private = work["path"]
        for filename, expected in (("capture.zip", profile["capture"]), ("capsule.zip", profile["capsule"])):
            copy_verified(build_private / filename, private / filename, expected, deadline)
        io.write_new(private / "verification-context.json", io.encode(context))
        rc = io.private_process([sys.executable, "-I", "-B", str(repo / CHECKER), "check-private",
                                 "--repo-root", str(repo), "--private-input", str(private)],
                                cwd=private, environment=io.replay_environment(private),
                                timeout=deadline.remaining(180), new_session=True)
        io.require(rc == 0, "q2_replay_rejected")
        raw = io.read_file(private / "verification.json", 128 * 1024)
        io.require(raw == io.encode(private_verification_record(context, profile)), "q2_replay_rejected")
    io.require(work["cleanup_verified"], "q2_cleanup_failed")


def receipt(repo, phase, binding, sources, profile, artifact_id, packing):
    result = {"schema_version": "q2_release_capsule_publication_v0", "status": phase,
              "binding": binding, "source_bindings": sources, "capsule": profile["capsule"],
              "verifier_dependencies": profile["verifier_wheels"],
              "artifact_id": artifact_id, "packing_environment": packing,
              "verification_environment": environment_record(),
              "checks": {k: True for k in ("capture", "subject", "replay", "summary")},
              "historical_metric_pass": False, "historical_process_exit": 1,
              "cleanup": "verified_removed", "release_host_verification": "not_observed",
              "authority_effect": "none", "production_gate_eligible": False, "current_inference_count": 0}
    io.validate(result, io.read_file(repo / SCHEMA, 128 * 1024))
    return result


def supervise(repo, phase, environment=None):
    env = dict(os.environ if environment is None else environment)
    token = env.pop(TOKEN, "")
    for name in tuple(os.environ):
        if name.startswith("PULSE_Q2_"):
            os.environ.pop(name, None)
    output, created = None, False
    try:
        with io.interrupt_boundary(900) as deadline:
            p = load_profile(repo)
            binding, sources = authorize(repo, env, p)
            io.require(phase in ("build", "verify-download"), "q2_context_rejected")
            artifact_id, packing = None, None
            if phase == "verify-download":
                value = env.get("PULSE_Q2_PUBLICATION_ARTIFACT_ID", "")
                io.require(re.fullmatch(r"[1-9][0-9]{0,23}", value) is not None, "q2_transport_rejected")
                artifact_id = int(value)
            else:
                io.require(not env.get("PULSE_Q2_PUBLICATION_ARTIFACT_ID"), "q2_context_rejected")
            io.require(environment_record()["python"] == "3.11.16" and
                       environment_record()["unicode"] == "14.0.0", "q2_replay_environment")
            parent = Path(env["RUNNER_TEMP"]).absolute()
            io.require(parent.is_dir() and not any(x.is_symlink() for x in (parent, *parent.parents)) and
                       parent != repo and repo not in parent.parents, "q2_file_rejected")
            io.require(shutil.disk_usage(parent).free >= p["limits"]["minimum_free_bytes"], "q2_archive_limit")
            output = parent / "q2-capsule-publication"
            output.mkdir(mode=0o700)  # Existing files/directories/links are never reused.
            created = True
            transport = io.GitHubArtifactTransport(token)
            main = api_json(transport, "/git/ref/heads/main", deadline)
            io.require(main.get("object", {}).get("sha") == binding["source_commit"], "q2_source_mismatch")
            with io.private_workspace(repo, str(parent)) as work:
                private = work["path"]
                download_artifact(transport, p["capture"], private / "capture.zip", deadline)
                download_artifact(transport, p["preparation"], private / "preparation.zip", deadline)
                download_bootstrap(p["pip"], private / p["pip"]["filename"], deadline)
                if phase == "build":
                    download_bootstrap(p["bootstrap"], private / p["bootstrap"]["filename"], deadline)
                else:
                    expected = {**binding, **p["capsule"], "artifact_id": artifact_id,
                                "artifact_name": p["capsule"]["file_name"]}
                    download_artifact(transport, expected, private / "capsule.zip", deadline)
                del transport
                token = None
                install_verifier_dependencies(private, p, deadline)
                if phase == "build":
                    io.write_new(private / "build-context.json", io.encode({"binding": binding, "source_bindings": sources}))
                    rc = io.private_process([sys.executable, "-I", "-B", str(repo / BUILDER),
                                             "--repo-root", str(repo), "--private-input", str(private)],
                                            cwd=private, environment=io.replay_environment(private),
                                            timeout=deadline.remaining(700), new_session=True)
                    io.require(rc == 0, "q2_subject_mismatch")
                    packing = io.strict_json(io.read_file(private / "packing-environment.json", 4096))
                verify_in_fresh_workspace(repo, private, parent, p, binding, sources, deadline)
                # Recheck source after children; no builder-supplied semantic verdict is consumed.
                io.require(source_closure(repo, binding["source_commit"]) == sources, "q2_source_mismatch")
                if phase == "build":
                    destination = output / p["capsule"]["file_name"]
                    copy_verified(private / "capsule.zip", destination, p["capsule"], deadline)
            io.require(work["cleanup_verified"], "q2_cleanup_failed")
            result = receipt(repo, "preupload_verified" if phase == "build" else "roundtrip_verified",
                             binding, sources, p, artifact_id, packing)
            io.write_new(output / "publication.json", io.encode(result))
        return result
    except BaseException:
        if created:
            shutil.rmtree(output)
            io.require(not os.path.lexists(output), "q2_cleanup_failed")
        raise
    finally:
        token = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify-download", "check-private"))
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--private-input", type=Path)
    args = parser.parse_args()
    try:
        repo = args.repo_root.resolve(strict=True)
        if args.mode == "check-private":
            io.require(args.private_input is not None, "q2_context_rejected")
            check_private(repo, args.private_input)
            return 0
        io.require(args.private_input is None, "q2_context_rejected")
        supervise(repo, args.mode)
        print("q2_publication_verified")
        return 0
    except Exception as exc:
        print(exc.code if isinstance(exc, io.IntakeError) else "q2_internal_error")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
