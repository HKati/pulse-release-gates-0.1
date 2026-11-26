#!/usr/bin/env python3
"""Bound the manual OG write to one owner, source, run, file and ref.

The generation job is read-only. The writer uses only the standard library;
it never installs Pillow or executes content from the candidate artifact.
GitHub-provided context and trusted workflow/code are trust assumptions, not
claims that a contents:write token has server-side per-file restrictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import tempfile
import zlib

REPOSITORY = "HKati/pulse-release-gates-0.1"
REPOSITORY_ID = "1061766508"
OWNER = "HKati"
OWNER_ID = "128643840"
REF = "refs/heads/main"
WORKFLOW = ".github/workflows/make_org.yml"
REMOTE = "https://github.com/" + REPOSITORY + ".git"
OUTPUT = "og_image_1200x630.png"
RECEIPT = "receipt.json"
WIDTH, HEIGHT = 1200, 630
MAX_INPUT = 64 * 1024 * 1024
MAX_OUTPUT = 8 * 1024 * 1024
MESSAGE = "chore(assets): regenerate og_image_1200x630.png [skip ci]"
SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
DECIMAL = re.compile(r"[1-9][0-9]{0,19}\Z")


class BoundaryError(ValueError):
    """A required identity, payload or mutation boundary was not satisfied."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise BoundaryError(reason)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(data: bytes) -> dict:
    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, "duplicate_json_key")
            value[key] = item
        return value

    def bad_constant(_):
        raise BoundaryError("non_finite_json")

    def finite_float(text):
        value = float(text)
        require(math.isfinite(value), "non_finite_json")
        return value

    value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                       parse_constant=bad_constant, parse_float=finite_float)
    require(type(value) is dict, "json_object_required")
    return value


def encode(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n").encode()


def regular_bytes(path: Path, limit: int) -> bytes:
    """Read a bounded ordinary file without following its final symlink."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "regular_file_required")
        require(0 < info.st_size <= limit, "file_size_out_of_bounds")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        after = os.fstat(fd)
        require(len(data) == info.st_size and len(data) <= limit, "file_changed_while_reading")
        require((info.st_size, info.st_mtime_ns, info.st_ctime_ns) ==
                (after.st_size, after.st_mtime_ns, after.st_ctime_ns), "file_changed_while_reading")
        return data
    finally:
        os.close(fd)


def authorised_context(env: dict, event: dict) -> dict:
    expected = {
        "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
        "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REPOSITORY_ID": REPOSITORY_ID,
        "GITHUB_REPOSITORY_OWNER": OWNER, "GITHUB_REPOSITORY_OWNER_ID": OWNER_ID,
        "GITHUB_ACTOR": OWNER, "GITHUB_ACTOR_ID": OWNER_ID,
        "GITHUB_TRIGGERING_ACTOR": OWNER, "GITHUB_REF": REF,
        "GITHUB_REF_TYPE": "branch", "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_WORKFLOW_REF": REPOSITORY + "/" + WORKFLOW + "@" + REF,
    }
    for name, value in expected.items():
        require(env.get(name) == value, "unauthorised_context:" + name)
    source = env.get("GITHUB_SHA", "")
    require(bool(SHA.fullmatch(source)) and source != "0" * 40, "source_sha_required")
    require(env.get("GITHUB_WORKFLOW_SHA") == source, "workflow_source_mismatch")
    for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        require(bool(DECIMAL.fullmatch(env.get(name, ""))), "missing_run_identity:" + name)
    repo = event.get("repository", {})
    sender = event.get("sender", {})
    owner = repo.get("owner", {}) if type(repo) is dict else {}
    require(type(repo) is dict and type(repo.get("id")) is int and
            repo["id"] == int(REPOSITORY_ID) and repo.get("full_name") == REPOSITORY,
            "event_repository_mismatch")
    require(repo.get("default_branch") == "main" and repo.get("fork") is False,
            "event_repository_policy_mismatch")
    require(type(owner) is dict and type(owner.get("id")) is int and
            owner["id"] == int(OWNER_ID) and owner.get("login") == OWNER,
            "event_owner_mismatch")
    require(type(sender) is dict and type(sender.get("id")) is int and
            sender["id"] == int(OWNER_ID) and sender.get("login") == OWNER,
            "event_sender_mismatch")
    require(event.get("ref") in ("main", REF), "event_ref_mismatch")
    inputs = event.get("inputs")
    require(type(inputs) is dict and set(inputs) == {"source", "bgcolor"}, "input_contract")
    source_path, bgcolor = inputs["source"], inputs["bgcolor"]
    require(type(source_path) is str and 0 < len(source_path) <= 512, "source_path_required")
    posix = PurePosixPath(source_path)
    require(not posix.is_absolute() and str(posix) == source_path and
            ".." not in posix.parts and "." not in posix.parts and
            all(part.lower() != ".git" for part in posix.parts) and
            "\\" not in source_path and
            all(ord(c) >= 32 and ord(c) != 127 for c in source_path), "unsafe_source_path")
    require(type(bgcolor) is str and 0 < len(bgcolor) <= 128 and
            all(ord(c) >= 32 and ord(c) != 127 for c in bgcolor), "invalid_bgcolor")
    return {
        "repository": REPOSITORY, "repository_id": REPOSITORY_ID,
        "owner_id": OWNER_ID, "actor": OWNER, "actor_id": OWNER_ID,
        "triggering_actor": OWNER, "ref": REF, "source_sha": source,
        "workflow_ref": expected["GITHUB_WORKFLOW_REF"], "workflow_sha": source,
        "run_id": env["GITHUB_RUN_ID"], "run_attempt": env["GITHUB_RUN_ATTEMPT"],
        "source_path": source_path, "bgcolor": bgcolor,
    }


def git_env() -> dict:
    # Do not inherit Git config injection, credential helpers, replace refs,
    # author overrides, PYTHONPATH or a shell-selected Git executable.
    return {"PATH": os.defpath, "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0"}


def git(repo: Path, *args: str, data: bytes | None = None, env: dict | None = None,
        check: bool = True) -> subprocess.CompletedProcess:
    command = ["/usr/bin/git", "--literal-pathspecs", "-c", "core.hooksPath=/dev/null",
               "-c", "core.fsmonitor=false", "-c", "credential.helper=", "-C", str(repo), *args]
    result = subprocess.run(command, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=git_env() if env is None else env, check=False, timeout=120)
    if check and result.returncode != 0:
        # Never print arbitrary command/config output containing credentials.
        raise BoundaryError("git_operation_failed:" + str(result.returncode))
    return result


def checkout_source(repo: Path, context: dict) -> tuple[bytes, str]:
    require(git(repo, "rev-parse", "--show-toplevel").stdout.decode().strip() == str(repo.resolve()),
            "checkout_root_mismatch")
    require(git(repo, "rev-parse", "--verify", "HEAD").stdout.decode().strip() == context["source_sha"],
            "checkout_source_mismatch")
    dangerous = git(repo, "config", "--local", "--name-only", "--get-regexp",
                    r"^(include|includeif|url\.|remote\..*\.(pushurl|mirror)|core\.(sshcommand|gitproxy)|http\..*\.(extraheader|proxy)|credential\.)",
                    check=False)
    require(dangerous.returncode in (0, 1) and not dangerous.stdout, "unsafe_local_git_config")
    require(not git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout,
            "checkout_not_clean")
    current = repo
    for part in PurePosixPath(context["source_path"]).parts:
        current /= part
        require(not current.is_symlink(), "source_symlink")
    raw = regular_bytes(current, MAX_INPUT)
    listing = git(repo, "ls-tree", "-z", "HEAD", "--", context["source_path"]).stdout
    rows = listing.rstrip(b"\0").split(b"\0")
    require(len(rows) == 1 and b"\t" in rows[0], "source_not_tracked")
    meta, name = rows[0].split(b"\t", 1)
    fields = meta.split()
    require(len(fields) == 3 and fields[0] == b"100644" and fields[1] == b"blob" and
            name.decode() == context["source_path"], "source_not_regular_tracked_file")
    blob = fields[2].decode()
    require(git(repo, "cat-file", "blob", blob).stdout == raw, "source_bytes_mismatch")
    old = git(repo, "ls-tree", "-z", "HEAD", "--", OUTPUT).stdout
    if old:
        require(old.startswith(b"100644 blob ") and old.endswith(b"\t" + OUTPUT.encode() + b"\0"),
                "output_tree_mode")
        regular_bytes(repo / OUTPUT, MAX_OUTPUT)
    else:
        require(not (repo / OUTPUT).exists() and not (repo / OUTPUT).is_symlink(),
                "unexpected_output_path")
    return raw, blob


def validate_png(raw: bytes) -> None:
    """Validate the small RGB PNG subset emitted by the unchanged generator."""
    require(0 < len(raw) <= MAX_OUTPUT and raw[:8] == b"\x89PNG\r\n\x1a\n", "png_signature_or_size")
    offset, chunks, compressed = 8, [], bytearray()
    while offset < len(raw):
        require(offset + 12 <= len(raw), "png_truncated_chunk")
        length = struct.unpack(">I", raw[offset:offset + 4])[0]
        kind = raw[offset + 4:offset + 8]
        end = offset + 12 + length
        require(end <= len(raw), "png_chunk_length")
        body = raw[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", raw[offset + 8 + length:end])[0]
        require(zlib.crc32(kind + body) & 0xffffffff == crc, "png_crc")
        if not chunks:
            require(kind == b"IHDR" and body == struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0),
                    "png_dimensions_or_format")
        elif kind == b"IDAT":
            require(chunks[-1] in (b"IHDR", b"IDAT"), "png_idat_order")
            compressed.extend(body)
        else:
            require(kind == b"IEND" and length == 0 and end == len(raw) and chunks[-1] == b"IDAT",
                    "png_unexpected_chunk_or_tail")
        chunks.append(kind)
        offset = end
    require(chunks and chunks[-1] == b"IEND" and compressed, "png_incomplete")
    expected = HEIGHT * (1 + WIDTH * 3)
    decoder = zlib.decompressobj()
    pixels = decoder.decompress(bytes(compressed), expected + 1)
    require(len(pixels) == expected and decoder.eof and not decoder.unused_data and
            not decoder.unconsumed_tail, "png_decompressed_size_or_stream")
    require(all(value <= 4 for value in pixels[::1 + WIDTH * 3]), "png_filter")


def receipt(context: dict, source: bytes, source_blob: str, image: bytes) -> dict:
    return {"schema": "pulse_og_write_candidate_v0", "context": context,
            "source_git_blob": source_blob, "source_sha256": sha256(source),
            "output_path": OUTPUT, "output_sha256": sha256(image), "output_size": len(image),
            "width": WIDTH, "height": HEIGHT, "release_authority_effect": "none"}


def generate(repo: Path, context: dict, bundle: Path) -> dict:
    source, source_blob = checkout_source(repo, context)
    # Only the read-only generation job imports Pillow.
    from PIL import Image, ImageOps
    import io
    with Image.open(io.BytesIO(source)) as opened:
        im = opened.convert("RGB")
    im2 = ImageOps.contain(im, (WIDTH, HEIGHT))  # keep aspect ratio, no crop
    canvas = Image.new("RGB", (WIDTH, HEIGHT), context["bgcolor"])
    canvas.paste(im2, ((WIDTH - im2.width)//2, (HEIGHT - im2.height)//2))
    stream = io.BytesIO()
    canvas.save(stream, "PNG")
    image = stream.getvalue()
    validate_png(image)
    checkout_source(repo, context)  # the checkout must still be unchanged
    bundle.mkdir(parents=False, exist_ok=False)
    (bundle / OUTPUT).write_bytes(image)
    record = receipt(context, source, source_blob, image)
    (bundle / RECEIPT).write_bytes(encode(record))
    return record


def validate_bundle(repo: Path, context: dict, bundle: Path, expected_digest: str) -> bytes:
    require(bool(SHA256.fullmatch(expected_digest)), "expected_digest_required")
    require(not bundle.is_symlink() and bundle.is_dir() and
            {p.name for p in bundle.iterdir()} == {OUTPUT, RECEIPT}, "bundle_exact_file_set")
    source, source_blob = checkout_source(repo, context)
    image = regular_bytes(bundle / OUTPUT, MAX_OUTPUT)
    require(sha256(image) == expected_digest, "output_digest_mismatch")
    validate_png(image)
    record = strict_json(regular_bytes(bundle / RECEIPT, 16384))
    expected = receipt(context, source, source_blob, image)
    # Canonical bytes also distinguish bool/int and reject unrecognised fields.
    require(encode(record) == encode(expected), "candidate_binding_mismatch")
    return image


def validate_commit(repo: Path, base: str, commit: str, image: bytes) -> None:
    parents = git(repo, "rev-list", "--parents", "-n", "1", commit).stdout.decode().split()
    require(parents == [commit, base], "commit_parent_mismatch")
    changed = git(repo, "diff-tree", "--no-commit-id", "--name-only", "--no-renames", "-r", "-z",
                  base, commit).stdout
    require(changed == OUTPUT.encode() + b"\0", "commit_path_scope")
    row = git(repo, "ls-tree", "-z", commit, "--", OUTPUT).stdout
    require(row.startswith(b"100644 blob "), "commit_output_mode")
    require(git(repo, "show", commit + ":" + OUTPUT).stdout == image, "commit_output_bytes")


def prepare_commit(repo: Path, context: dict, bundle: Path, expected_digest: str) -> str | None:
    image = validate_bundle(repo, context, bundle, expected_digest)
    base = context["source_sha"]
    current = git(repo, "show", base + ":" + OUTPUT, check=False)
    if current.returncode == 0 and current.stdout == image:
        return None
    # Neither git add nor git commit is used: no attributes filters or project
    # hooks may turn one image update into code execution or additional paths.
    blob = git(repo, "hash-object", "-w", "--stdin", data=image).stdout.decode().strip()
    git(repo, "update-index", "--add", "--cacheinfo", "100644," + blob + "," + OUTPUT)
    require(git(repo, "diff", "--cached", "--name-only", "-z", "HEAD").stdout == OUTPUT.encode() + b"\0",
            "staged_path_scope")
    tree = git(repo, "write-tree").stdout.decode().strip()
    commit = git(repo, "-c", "user.name=github-actions[bot]", "-c",
                 "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                 "commit-tree", tree, "-p", base, "-m", MESSAGE).stdout.decode().strip()
    require(bool(SHA.fullmatch(commit)), "commit_identity")
    validate_commit(repo, base, commit, image)
    # Keep the local checkout coherent without moving any remote ref.
    fd, name = tempfile.mkstemp(prefix=".og-image-", dir=repo)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(image)
        os.chmod(name, 0o644)
        os.replace(name, repo / OUTPUT)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    git(repo, "update-ref", "HEAD", commit, base)
    require(not git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout,
            "post_commit_checkout_not_clean")
    return commit


def pre_push_program(base: str, commit: str, remote: str) -> str:
    # Git supplies the advertised old remote object to this hook. A stale tip,
    # including a rewind, is rejected before normal (non-force) push sends it.
    return ("#!" + sys.executable + " -I\n"
            "import sys\n"
            f"expected_remote = {remote!r}\n"
            f"expected = [{commit!r}, {commit!r}, {REF!r}, {base!r}]\n"
            "payload = sys.stdin.buffer.read(4097)\n"
            "if len(payload) > 4096: raise SystemExit(1)\n"
            "rows = [line.split() for line in payload.decode(\"ascii\").splitlines()]\n"
            "if sys.argv[1:] != [expected_remote, expected_remote] or rows != [expected]:\n"
            "    sys.stderr.write('OG write rejected: remote tip or ref scope changed\\n')\n"
            "    raise SystemExit(1)\n")


def push_commit(repo: Path, base: str, commit: str, token: str) -> None:
    require(bool(token) and "\n" not in token and "\r" not in token, "write_token_required")
    image = regular_bytes(repo / OUTPUT, MAX_OUTPUT)
    validate_commit(repo, base, commit, image)
    require(git(repo, "rev-parse", "HEAD").stdout.decode().strip() == commit, "head_changed_before_push")
    require(not git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout,
            "dirty_before_push")
    with tempfile.TemporaryDirectory(prefix="pulse-og-write-") as temp:
        home = Path(temp)
        hook = home / "pre-push"
        hook.write_text(pre_push_program(base, commit, REMOTE), encoding="utf-8")
        hook.chmod(0o700)
        askpass = home / "askpass"
        askpass.write_text("#!/bin/sh\ncase \"$1\" in\n"
                           "  *Username*) printf '%s\\n' 'x-access-token' ;;\n"
                           "  *Password*) printf '%s\\n' \"$OG_PUSH_TOKEN\" ;;\n"
                           "  *) exit 1 ;;\nesac\n", encoding="utf-8")
        askpass.chmod(0o700)
        env = git_env()
        env.update({"GIT_ASKPASS": str(askpass), "OG_PUSH_TOKEN": token, "HOME": str(home)})
        result = git(repo, "-c", "core.hooksPath=" + temp, "-c", "push.followTags=false",
                     "-c", "push.gpgSign=false", "-c", "http.followRedirects=false",
                     "push", "--porcelain", REMOTE, commit + ":" + REF,
                     env=env, check=False)
        require(result.returncode == 0, "push_rejected_no_retry")
        # Do not infer success from a zero exit if no ref update was reported.
        lines = result.stdout.decode("utf-8", errors="strict").splitlines()
        updates = [line.split("\t") for line in lines if "\t" in line]
        require(len(updates) == 1 and updates[0][0] == " " and
                updates[0][1] == commit + ":" + REF, "push_result_unconfirmed_no_retry")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preflight", "generate", "write"))
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    try:
        event = strict_json(regular_bytes(Path(os.environ["GITHUB_EVENT_PATH"]), 1024 * 1024))
        context = authorised_context(dict(os.environ), event)
        repo = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
        require(Path(__file__).resolve() == repo / "tools/make_og_write_boundary_v0.py", "trusted_tool_path")
        checkout_source(repo, context)
        if args.operation == "preflight":
            artifact = os.environ.get("OG_ARTIFACT_ID")
            if artifact is not None:
                require(bool(DECIMAL.fullmatch(artifact)), "artifact_id_required")
                require(bool(SHA256.fullmatch(os.environ.get("OG_EXPECTED_SHA256", ""))), "digest_required")
            print("OG preflight: authorised exact source")
        elif args.operation == "generate":
            require(args.bundle is not None, "bundle_path_required")
            record = generate(repo, context, args.bundle)
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
                stream.write("image_sha256=" + record["output_sha256"] + "\n")
            print("OG candidate generated; no repository write permission")
        else:
            require(args.bundle is not None, "bundle_path_required")
            require(bool(DECIMAL.fullmatch(os.environ.get("OG_ARTIFACT_ID", ""))), "artifact_id_required")
            commit = prepare_commit(repo, context, args.bundle, os.environ.get("OG_EXPECTED_SHA256", ""))
            outcome = "unchanged_no_commit_no_push"
            if commit is not None:
                push_commit(repo, context["source_sha"], commit, os.environ.get("GITHUB_TOKEN", ""))
                outcome = "one_file_push_accepted"
            print("OG write: " + outcome)
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write("## Bounded OG write\n\n" +
                             "Outcome: `" + outcome + "`\n\n" +
                             "Source: `" + context["source_sha"] + "`\n\n" +
                             "Artifact ID: `" + os.environ["OG_ARTIFACT_ID"] + "`\n\n" +
                             "PNG SHA-256: `" + os.environ["OG_EXPECTED_SHA256"] + "`\n\n" +
                             "Commit: `" + (commit or "none") + "`\n")
        return 0
    except (BoundaryError, KeyError, OSError, ValueError, zlib.error, subprocess.SubprocessError) as exc:
        # Error types/codes are enough; do not echo arbitrary inputs or tokens.
        code = str(exc) if isinstance(exc, BoundaryError) else type(exc).__name__
        print("OG boundary rejected: " + code, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
