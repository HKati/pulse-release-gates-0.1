#!/usr/bin/env python3
"""Q2 preparation phase: stage candidate runtime bytes, never run inference.

This is the first executable subset of the section 6.6 acquisition inventory.
Only the ``prepare-runtime`` subcommand exists. It creates a review candidate;
it does not install its wheels, run a model, produce responses or admit Q2.
The separately implemented checker must check the finished directory.
"""
from __future__ import annotations

import argparse
import email.parser
import hashlib
import html.parser
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile

REPOSITORY = "HKati/pulse-release-gates-0.1"
WORKFLOW = ".github/workflows/q2_reference_acquisition_v0.yml"
SELF = "PULSE_safe_pack_v0/tools/acquire_q2_reference_inputs_v0.py"
CHECKER = "PULSE_safe_pack_v0/tools/check_q2_reference_capture_v0.py"
SELECTION = "PULSE_safe_pack_v0/profiles/q2_reference_subject_v0.json"
REQUESTS = "PULSE_safe_pack_v0/examples/q2_reference_field_extraction_v0/requests.json"
SOURCE_PATHS = (WORKFLOW, SELF, CHECKER, SELECTION, REQUESTS)
SELECTION_SHA256 = "e81a9dd0a5080d84dae8c4bbfc843b46510f580e74254c1aed0dddbe76375f3e"
REQUESTS_SHA256 = "fa0412c6a702e220e5d0c8b09a5e854fe35ac89d4801977eeee0f2a6e5cae997"
MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
REVISION = "12fd25f77366fa6b3b4b768ec3050bf629380bac"
WEIGHTS_SHA256 = "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c"
MODEL_FILES = ("config.json", "generation_config.json", "merges.txt", "model.safetensors",
               "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.json")
HF_API = f"https://huggingface.co/api/models/{MODEL}/revision/{REVISION}?blobs=true"
TORCH_INDEX = "https://download.pytorch.org/whl/cpu/torch/"
TORCH_WHEEL = "torch-2.8.0+cpu-cp311-cp311-manylinux_2_28_x86_64.whl"
ROOTS = {"torch": "2.8.0+cpu", "transformers": "4.57.6", "rfc8785": "0.1.4", "jsonschema": "4.25.1"}
MAX_FILE = 512 * 1024 * 1024
MAX_JSON = 16 * 1024 * 1024
MAX_WHEELS = 64
MAX_TOTAL = 1536 * 1024 * 1024
STATE = {"authority_effect": "none", "production_gate_eligible": False,
         "inference_executed": False, "native_runtime_qualified": False,
         "materialized_subject_bound": False, "capture_dispatch_authorized": False,
         "dependency_closure_status": "staged_review_candidate"}


class PreparationError(ValueError):
    """A stable, non-sensitive diagnostic code, never an HTTP body or URL."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PreparationError(code)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(raw: bytes):
    require(len(raw) <= MAX_JSON and not raw.startswith(b"\xef\xbb\xbf"), "json_encoding_or_size")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def bad_number(_):
        raise PreparationError("non_finite_json")
    try:
        result = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs,
                            parse_constant=bad_number)
        def walk(value, depth=0):
            require(depth <= 64, "json_depth")
            if isinstance(value, str):
                value.encode("utf-8", "strict")
            elif type(value) is float:
                require(math.isfinite(value), "non_finite_json")
            elif isinstance(value, dict):
                for k, v in value.items(): walk(k, depth + 1); walk(v, depth + 1)
            elif isinstance(value, list):
                for v in value: walk(v, depth + 1)
        walk(result)
        return result
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PreparationError("invalid_json") from exc


def encode(value) -> bytes:
    # Preparation files use this exact file representation, not a JCS claim.
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       indent=2) + "\n").encode("utf-8")


def read_file(path: Path, limit: int = MAX_FILE) -> bytes:
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_size <= limit,
            "not_bounded_regular_file")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    require(len(data) == st.st_size, "file_changed_or_oversize")
    return data


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(data); out.flush(); os.fsync(out.fileno())


def clean_env(home: Path) -> dict[str, str]:
    # Deliberately do not inherit tokens, proxies, PYTHONPATH or pip indexes.
    return {"PATH": os.defpath, "HOME": str(home), "TMPDIR": str(home),
            "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PIP_CONFIG_FILE": os.devnull,
            "PYTHONNOUSERSITE": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}


def git_bytes(repo: Path, args: list[str]) -> bytes:
    command = ["/usr/bin/git", "--no-replace-objects", "-c", "protocol.allow=never",
               "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args]
    proc = subprocess.run(command, env=clean_env(repo), stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    require(proc.returncode == 0, "source_git_query_failed")
    return proc.stdout


def check_context(repo: Path, expected: str, env: dict[str, str]) -> dict:
    require(re.fullmatch(r"[a-f0-9]{40}", expected) is not None, "invalid_source_sha")
    require(env.get("GITHUB_REPOSITORY") == REPOSITORY, "repository_mismatch")
    require(env.get("GITHUB_EVENT_NAME") == "workflow_dispatch", "manual_dispatch_required")
    require(env.get("GITHUB_REF") == "refs/heads/main", "main_required")
    require(env.get("GITHUB_ACTOR") == "HKati" and env.get("GITHUB_TRIGGERING_ACTOR") == "HKati",
            "owner_dispatch_required")
    require(env.get("GITHUB_RUN_ATTEMPT") == "1", "attempt_one_required")
    require(env.get("GITHUB_SHA") == expected and env.get("GITHUB_WORKFLOW_SHA") == expected,
            "workflow_source_mismatch")
    require(env.get("GITHUB_WORKFLOW_REF") == f"{REPOSITORY}/{WORKFLOW}@refs/heads/main",
            "workflow_ref_mismatch")
    run_id = env.get("GITHUB_RUN_ID", "")
    require(re.fullmatch(r"[1-9][0-9]{0,19}", run_id) is not None, "invalid_run_id")
    require(git_bytes(repo, ["rev-parse", "HEAD"]).decode().strip() == expected, "checkout_mismatch")
    require(platform.python_implementation() == "CPython" and platform.python_version() == "3.11.16",
            "native_python_target_required")
    require(platform.system() == "Linux" and platform.machine() == "x86_64", "native_platform_required")
    os_release = platform.freedesktop_os_release()
    require(os_release.get("ID") == "ubuntu" and os_release.get("VERSION_ID") == "24.04",
            "ubuntu_2404_required")
    require(env.get("ImageOS") == "ubuntu24" and bool(env.get("ImageVersion")), "runner_image_missing")
    return {"repository": REPOSITORY, "source_commit": expected, "workflow": WORKFLOW,
            "run_id": run_id, "run_attempt": 1, "event": "workflow_dispatch",
            "actor": "HKati", "python": platform.python_version(), "architecture": "x86_64",
            "os": "ubuntu-24.04", "runner_image": env["ImageVersion"],
            "origin": "owner_dispatched_github_preparation"}


def fixed_sources(repo: Path, sha: str) -> dict[str, bytes]:
    result = {}
    for rel in SOURCE_PATHS:
        data = read_file(repo / rel, MAX_JSON)
        require(data == git_bytes(repo, ["cat-file", "blob", f"{sha}:{rel}"]), "source_byte_mismatch")
        result[rel] = data
    require(digest(result[SELECTION]) == SELECTION_SHA256, "selection_changed")
    require(digest(result[REQUESTS]) == REQUESTS_SHA256, "workload_changed")
    require(Path(__file__).resolve() == (repo / SELF).resolve(), "producer_location_mismatch")
    return result


def validate_model_metadata(raw: bytes) -> dict[str, dict]:
    metadata = strict_json(raw)
    require(type(metadata) is dict and metadata.get("sha") == REVISION, "model_revision_mismatch")
    require(metadata.get("id", metadata.get("modelId")) == MODEL, "model_repository_mismatch")
    siblings = metadata.get("siblings")
    require(type(siblings) is list and len(siblings) <= 1024, "model_file_metadata_missing")
    result = {}
    for item in siblings:
        require(type(item) is dict and type(item.get("rfilename")) is str, "model_metadata_invalid")
        name = item["rfilename"]
        if name not in MODEL_FILES:
            continue
        require(name not in result, "duplicate_model_file")
        require(re.fullmatch(r"[a-f0-9]{40}", str(item.get("blobId", ""))) is not None,
                "model_blob_identity_missing")
        lfs = item.get("lfs")
        if lfs is not None:
            require(type(lfs) is dict and re.fullmatch(r"[a-f0-9]{64}", str(lfs.get("sha256", "")))
                    is not None, "model_lfs_identity_missing")
            size = lfs.get("size")
        else:
            size = item.get("size")
        require(type(size) is int and 0 < size <= MAX_FILE, "model_size_invalid")
        result[name] = item
    require(set(result) == set(MODEL_FILES), "model_file_scope_mismatch")
    require(result["model.safetensors"].get("lfs", {}).get("sha256") == WEIGHTS_SHA256,
            "selected_weights_mismatch")
    return result


def bind_model_file(name: str, data: bytes, meta: dict) -> dict:
    lfs = meta.get("lfs")
    size = lfs["size"] if lfs else meta["size"]
    require(len(data) == size, "model_size_mismatch")
    if lfs:
        require(digest(data) == lfs["sha256"], "model_sha256_mismatch")
    else:
        git_hash = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        require(git_hash == meta["blobId"], "model_blob_mismatch")
    return {"path": f"model/{name}", "size": len(data), "sha256": digest(data),
            "upstream_blob_sha1": meta["blobId"],
            "upstream_lfs_sha256": lfs["sha256"] if lfs else None}


def validate_tokens(model_dir: Path) -> None:
    for name in ("config.json", "generation_config.json"):
        data = strict_json(read_file(model_dir / name, MAX_JSON))
        require(type(data) is dict, "model_config_invalid")
        for key, value in (("bos_token_id", 1), ("eos_token_id", 2), ("pad_token_id", 2)):
            require(type(data.get(key)) is int and data[key] == value, "selected_token_id_mismatch")
    config = strict_json(read_file(model_dir / "tokenizer_config.json", MAX_JSON))
    def content(value): return value.get("content") if isinstance(value, dict) else value
    for key, text in (("bos_token", "<|im_start|>"), ("eos_token", "<|im_end|>"),
                      ("pad_token", "<|im_end|>")):
        require(content(config.get(key)) == text, "tokenizer_config_token_mismatch")
    require(type(config.get("chat_template")) is str and config["chat_template"], "chat_template_missing")
    tokenizer = strict_json(read_file(model_dir / "tokenizer.json", MAX_JSON))
    tokens = tokenizer.get("added_tokens")
    require(type(tokens) is list, "tokenizer_tokens_missing")
    for number, text in ((1, "<|im_start|>"), (2, "<|im_end|>")):
        matches = [x for x in tokens if type(x) is dict and x.get("id") == number]
        require(len(matches) == 1 and matches[0].get("content") == text
                and matches[0].get("special") is True, "tokenizer_id_map_mismatch")


class WheelLinks(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(v for k, v in attrs if k == "href" and v is not None)


def torch_download_identity(raw: bytes) -> tuple[str, str]:
    require(len(raw) <= MAX_JSON, "index_oversize")
    parser = WheelLinks(); parser.feed(raw.decode("utf-8", "strict"))
    matches = set()
    for href in parser.links:
        u = urllib.parse.urlsplit(urllib.parse.urljoin(TORCH_INDEX, href))
        if urllib.parse.unquote(u.path.rsplit("/", 1)[-1]) != TORCH_WHEEL:
            continue
        require(u.scheme == "https" and u.hostname in {"download.pytorch.org", "download-r2.pytorch.org"}
                and u.port in (None, 443) and not u.username and not u.password and not u.query,
                "torch_origin_invalid")
        require(re.fullmatch(r"sha256=[0-9a-f]{64}", u.fragment) is not None, "torch_hash_missing")
        matches.add((urllib.parse.urlunsplit(u._replace(fragment="")), u.fragment[7:]))
    require(len(matches) == 1, "torch_wheel_missing_or_ambiguous")
    return next(iter(matches))


def project_name(value: str) -> str:
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value) is not None,
            "package_name_invalid")
    return re.sub(r"[-_.]+", "-", value).lower()


def wheel_identity(path: Path) -> tuple[str, str]:
    require(path.name.endswith(".whl") and re.fullmatch(r"[A-Za-z0-9_.+-]+\.whl", path.name)
            is not None, "wheel_filename_invalid")
    with zipfile.ZipFile(path) as wheel:
        infos = wheel.infolist()
        require(len(infos) <= 50000 and len({i.filename for i in infos}) == len(infos), "wheel_members_invalid")
        for i in infos:
            p = PurePosixPath(i.filename)
            require(not p.is_absolute() and ".." not in p.parts and "\\" not in i.filename,
                    "wheel_path_invalid")
        metas = [i for i in infos if i.filename.endswith(".dist-info/METADATA")
                 and len(PurePosixPath(i.filename).parts) == 2]
        require(len(metas) == 1 and metas[0].file_size <= MAX_JSON, "wheel_metadata_invalid")
        metadata = email.parser.BytesParser().parsebytes(wheel.read(metas[0]), headersonly=True)
    require(len(metadata.get_all("Name", [])) == 1 and len(metadata.get_all("Version", [])) == 1,
            "wheel_identity_ambiguous")
    name = project_name(metadata["Name"]); version = metadata["Version"]
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+!-]*", version) is not None, "version_invalid")
    require(not name.startswith(("nvidia-", "cuda-")) and name not in {"triton", "torchvision", "torchaudio"},
            "non_selected_runtime_dependency")
    require(all("@" not in x and "://" not in x for x in metadata.get_all("Requires-Dist", [])),
            "direct_url_dependency_forbidden")
    require(project_name(path.name.split("-", 1)[0]) == name, "wheel_name_mismatch")
    return name, version


def pypi_identity(raw: bytes, name: str, version: str, filename: str) -> tuple[str, str]:
    document = strict_json(raw)
    info = document.get("info", {})
    require(project_name(info.get("name", "")) == name and info.get("version") == version,
            "pypi_identity_mismatch")
    candidates = [u for u in document.get("urls", []) if u.get("filename") == filename]
    require(len(candidates) == 1, "pypi_wheel_ambiguous")
    wheel = candidates[0]; url = urllib.parse.urlsplit(wheel.get("url", ""))
    require(wheel.get("packagetype") == "bdist_wheel" and wheel.get("yanked") is False,
            "pypi_not_live_wheel")
    require(url.scheme == "https" and url.hostname == "files.pythonhosted.org"
            and url.port in (None, 443) and not url.username and not url.password
            and not url.query and not url.fragment, "pypi_origin_invalid")
    sha = wheel.get("digests", {}).get("sha256", "")
    require(re.fullmatch(r"[a-f0-9]{64}", sha) is not None, "pypi_hash_missing")
    return wheel["url"], sha


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    @staticmethod
    def check(url: str) -> None:
        u = urllib.parse.urlsplit(url); h = u.hostname or ""
        require(u.scheme == "https" and u.port in (None, 443) and not u.username and not u.password
                and (h in {"huggingface.co", "cdn-lfs.huggingface.co", "download.pytorch.org",
                           "download-r2.pytorch.org", "pypi.org", "files.pythonhosted.org"}
                     or h.endswith(".hf.co")), "download_origin_not_allowed")
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.check(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Transport:
    def __init__(self, deadline: float):
        self.deadline = deadline
        self.total = 0
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), SafeRedirect())
    def get(self, url: str, path: Path, limit: int) -> bytes:
        SafeRedirect.check(url)
        require(time.monotonic() < self.deadline, "preparation_deadline")
        request = urllib.request.Request(url, headers={"User-Agent": "PULSEmech-Q2-preparation-v0",
                                                       "Accept-Encoding": "identity"})
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with self.opener.open(request, timeout=30) as response, path.open("xb") as out:
                require(response.status == 200, "download_http_status")
                require(response.headers.get("Content-Encoding", "identity") == "identity", "download_encoding")
                received = 0
                while True:
                    require(time.monotonic() < self.deadline, "preparation_deadline")
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    received += len(chunk); self.total += len(chunk)
                    require(received <= limit and self.total <= MAX_TOTAL, "download_size_limit")
                    out.write(chunk)
                out.flush(); os.fsync(out.fileno())
            return read_file(path, limit)
        except PreparationError:
            raise
        except Exception as exc:
            # Never leak signed redirect queries or response bodies into CI logs.
            raise PreparationError("download_failed") from exc


def pip_download(wheelhouse: Path, private_dir: Path, deadline: float) -> None:
    # This resolves/downloads wheels only. No wheel code or build backend runs.
    command = [sys.executable, "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
               "--no-input", "download", "--only-binary=:all:", "--no-cache-dir", "--retries", "0",
               "--timeout", "30", "--index-url", "https://pypi.org/simple", "--dest", str(wheelhouse),
               str(wheelhouse / TORCH_WHEEL), "transformers==4.57.6", "rfc8785==0.1.4", "jsonschema==4.25.1"]
    remaining = min(900, int(deadline - time.monotonic()))
    require(remaining > 0, "preparation_deadline")
    with (private_dir / "pip-download.log").open("xb") as log:
        result = subprocess.run(command, env=clean_env(private_dir), cwd=private_dir,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=log, timeout=remaining)
    require(result.returncode == 0, "wheel_resolution_download_failed")


def lock_bytes(wheels: list[dict]) -> bytes:
    header = "# Q2 runtime review candidate; native model qualification and adoption are pending.\n"
    return (header + "".join(f"{w['name']}=={w['version']} --hash=sha256:{w['sha256']}\n"
                             for w in sorted(wheels, key=lambda x: x["name"]))).encode("ascii")


def build_file_index(directory: Path) -> list[dict]:
    entries = []
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "output_symlink")
        if path.is_dir(): continue
        data = read_file(path)
        entries.append({"path": path.relative_to(directory).as_posix(),
                        "size": len(data), "sha256": digest(data)})
    require(sum(e["size"] for e in entries) <= MAX_TOTAL, "output_total_limit")
    return entries


def prepare(repo: Path, output: Path, expected: str) -> None:
    context = check_context(repo, expected, dict(os.environ))
    sources = fixed_sources(repo, expected)  # No network or output before these checks.
    require(not output.exists() and not output.is_symlink(), "output_already_exists")
    output.mkdir(mode=0o700)
    private_dir = output.parent / (output.name + "-private")
    private_dir.mkdir(mode=0o700)
    deadline = time.monotonic() + 1800
    transport = Transport(deadline)
    for rel, raw in sources.items(): write_new(output / "source" / rel, raw)
    print("Q2 preparation: fixed source verified; downloading selected model bytes", flush=True)
    metadata_raw = transport.get(HF_API, output / "upstream/model.json", MAX_JSON)
    model_metadata = validate_model_metadata(metadata_raw)
    model_records = []
    for name in MODEL_FILES:
        url = f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}"
        raw = transport.get(url, output / "model" / name, MAX_FILE)
        model_records.append(bind_model_file(name, raw, model_metadata[name]))
    validate_tokens(output / "model")
    write_new(output / "q2_reference_model_files_v0.json", encode({
        "record_type": "q2_reference_model_files_candidate_v0", "model_repository": MODEL,
        "model_revision": REVISION, "files": model_records, "authority_effect": "none",
        "native_runtime_qualified": False, "adopted": False}))
    print("Q2 preparation: model bytes checked; staging CPU wheels", flush=True)
    raw = transport.get(TORCH_INDEX, output / "upstream/torch-cpu-index.html", MAX_JSON)
    torch_url, torch_sha = torch_download_identity(raw)
    data = transport.get(torch_url, output / "wheelhouse" / TORCH_WHEEL, MAX_FILE)
    require(digest(data) == torch_sha, "torch_wheel_digest_mismatch")
    pip_download(output / "wheelhouse", private_dir, deadline)
    paths = sorted((output / "wheelhouse").iterdir())
    require(4 <= len(paths) <= MAX_WHEELS, "wheel_count_invalid")
    wheels = []; seen = set()
    for path in paths:
        data = read_file(path); name, version = wheel_identity(path)
        require(name not in seen, "multiple_wheels_for_distribution"); seen.add(name)
        if name == "torch":
            require(path.name == TORCH_WHEEL and version == ROOTS["torch"], "torch_variant_mismatch")
            url, sha = torch_url, torch_sha
            meta_path = "upstream/torch-cpu-index.html"
        else:
            meta_path = f"upstream/pypi/{name}-{version}.json"
            raw = transport.get(f"https://pypi.org/pypi/{name}/{version}/json", output / meta_path, MAX_JSON)
            url, sha = pypi_identity(raw, name, version, path.name)
        require(digest(data) == sha, "wheel_upstream_digest_mismatch")
        wheels.append({"name": name, "version": version, "path": f"wheelhouse/{path.name}",
                       "sha256": sha, "size": len(data), "upstream_metadata": meta_path, "url": url})
    versions = {w["name"]: w["version"] for w in wheels}
    require(all(versions.get(n) == v for n, v in ROOTS.items()), "root_dependency_changed")
    write_new(output / "requirements-q2-reference-v0.lock", lock_bytes(wheels))
    report = {"record_type": "q2_reference_runtime_preparation_v0", "context": context,
              "roots": ROOTS, "state": STATE, "wheels": wheels,
              "source_paths": list(SOURCE_PATHS), "files": build_file_index(output)}
    require(time.monotonic() < deadline, "preparation_deadline")
    write_new(output / "preparation.json", encode(report))
    print("Q2 preparation: candidate bytes complete; separate checker is still required", flush=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare-runtime", help="stage a review candidate; no inference")
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--expected-source-sha", required=True)
    args = parser.parse_args(argv)
    try:
        prepare(args.repo_root.resolve(strict=True), args.output_dir.absolute(), args.expected_source_sha)
        return 0
    except PreparationError as exc:
        print(f"Q2 preparation rejected: {exc}", file=sys.stderr)
    except (OSError, subprocess.SubprocessError, zipfile.BadZipFile, KeyError, TypeError, ValueError):
        print("Q2 preparation rejected: incomplete_or_invalid_preparation", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
