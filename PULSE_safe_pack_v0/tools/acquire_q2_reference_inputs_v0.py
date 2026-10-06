#!/usr/bin/env python3
"""Selected Q2 runtime preparation and owner-confirmed 150-slot capture.

Preparation stages candidate bytes without installation or inference. Capture
uses the adopted native runtime and the fixed workload, preserving all original
occurrences for separate checking. Neither mode admits a production Q2 gate.
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


def preparation_main(argv=None) -> int:
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


# One selected capture path. No generic model/platform dispatch is exposed.
CAPTURE_NATIVE = 'PULSE_safe_pack_v0/tools/qualify_q2_reference_runtime_v0.py'
CAPTURE_CHECK_NATIVE = 'PULSE_safe_pack_v0/tools/check_q2_reference_qualification_v0.py'
CAPTURE_WORKER = 'PULSE_safe_pack_v0/tools/run_q2_reference_subject_v0.py'
CAPTURE_SCHEMA = 'schemas/metrics/q2_reference_capture_v0.schema.json'
CAPTURE_MODEL_MAP = 'PULSE_safe_pack_v0/profiles/q2_reference_model_files_v0.json'
CAPTURE_LOCK = 'PULSE_safe_pack_v0/requirements-q2-reference-v0.lock'
CAPTURE_REDUCER = 'PULSE_safe_pack_v0/tools/build_q2_reference_summary.py'
CAPTURE_SUMMARY_CHECKER = 'PULSE_safe_pack_v0/tools/check_q2_reference_summary.py'
CAPTURE_ORIGINAL_DIR = 'PULSE_safe_pack_v0/examples/q2_runtime_preparation_v0/run_37148637546/'
CAPTURE_SOURCE_PATHS = tuple(sorted({WORKFLOW, SELF, CHECKER, CAPTURE_NATIVE, CAPTURE_CHECK_NATIVE,
    CAPTURE_WORKER, CAPTURE_MODEL_MAP, CAPTURE_LOCK, CAPTURE_SCHEMA, SELECTION, REQUESTS,
    'PULSE_safe_pack_v0/profiles/q2_reference_diagnostic_v0.json',
    'schemas/metrics/q2_reference_qualification_v0.schema.json', CAPTURE_REDUCER, CAPTURE_SUMMARY_CHECKER,
    'metrics/specs/q2_consistency_v0.yml', 'schemas/metrics/q2_consistency_input_v0.schema.json',
    'schemas/metrics/q2_consistency_summary_v0.schema.json', 'schemas/dataset_manifest.schema.json',
    *(CAPTURE_ORIGINAL_DIR + n for n in ('preparation.json', 'q2-runtime-preparation-check.json',
    'q2_reference_model_files_v0.json', 'requirements-q2-reference-v0.lock'))}))
CAPTURE_LIMITS = {'generation_seconds': 15, 'phase_seconds': 1200, 'memory_bytes': 4294967296, 'tasks': 64, 'retries': 0}


def capture_encode(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n').encode('utf-8')


def capture_native_module(repo, expected):
    import importlib.util
    # Validate the dispatch boundary before importing any local native helper.
    require(type(expected) is str and re.fullmatch('[a-f0-9]{40}', expected), 'capture_source_sha_shape')
    expected_env = {'GITHUB_REPOSITORY': REPOSITORY, 'GITHUB_EVENT_NAME': 'workflow_dispatch',
        'GITHUB_REF': 'refs/heads/main', 'GITHUB_ACTOR': 'HKati', 'GITHUB_TRIGGERING_ACTOR': 'HKati',
        'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_SHA': expected, 'GITHUB_WORKFLOW_SHA': expected,
        'GITHUB_WORKFLOW_REF': REPOSITORY + '/' + WORKFLOW + '@refs/heads/main'}
    require(all(os.environ.get(k) == v for k, v in expected_env.items()), 'capture_dispatch_context')
    require(re.fullmatch('[1-9][0-9]{0,19}', os.environ.get('GITHUB_RUN_ID', '')), 'capture_run_identity')
    require(os.geteuid() == 0, 'capture_supervisor_requires_root')
    raw = read_file(repo / CAPTURE_NATIVE, MAX_JSON)
    original = subprocess.run(['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
        '-c', 'core.hooksPath=/dev/null', '-c', 'safe.directory=' + str(repo), '-C', str(repo),
        'cat-file', 'blob', f'{expected}:{CAPTURE_NATIVE}'], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=clean_env(repo), timeout=30)
    require(original.returncode == 0 and original.stdout == raw, 'capture_native_source_changed')
    require(Path(__file__).resolve() == (repo / SELF).resolve(), 'capture_producer_location')
    spec = importlib.util.spec_from_file_location('q2_capture_native_service_helpers', repo / CAPTURE_NATIVE)
    native = importlib.util.module_from_spec(spec)
    # Execute the exact checked bytes; do not reopen the runner-owned file.
    exec(compile(raw, str(repo / CAPTURE_NATIVE), 'exec'), native.__dict__)
    return native


def capture_slot_inventory(raw):
    require(digest(raw) == REQUESTS_SHA256, 'capture_workload_digest')
    workload = strict_json(raw)
    require(len(workload['groups']) == 50 and len(workload['occurrence_inventory']) == 150, 'capture_workload_extent')
    slots = []
    for index, row in enumerate(workload['occurrence_inventory'], 1):
        number = (index - 1) // 3 + 1; repeat = (index - 1) % 3 + 1
        group = workload['groups'][number - 1]
        expected = {'ordinal': index, 'call_id': f'q2fx-{number:03d}-r{repeat:02d}',
                    'group_id': f'q2fx-{number:03d}', 'repeat_index': repeat,
                    'request_sha256': group['request_sha256']}
        require(capture_encode(row) == capture_encode(expected), 'capture_slot_order')
        slots.append({**row, 'attempt': 1})
    return workload, slots


def capture_snapshot(repo, target, expected, native):
    rows = native.snapshot_sources(repo, target, expected)
    for name in sorted(set(CAPTURE_SOURCE_PATHS) - set(native.SOURCES)):
        raw = native.safe_read(repo / name)
        original = native.control(['/usr/bin/git', '--no-replace-objects', '-c', 'protocol.allow=never',
            '-c', 'safe.directory=' + str(repo), '-c', 'core.hooksPath=/dev/null', '-C', str(repo),
            'cat-file', 'blob', f'{expected}:{name}'], timeout=30).stdout
        require(raw == original, 'capture_source_bytes')
        native.save(target / name, raw)
        rows.append({'path': name, 'size': len(raw), 'sha256': digest(raw)})
    require({r['path'] for r in rows} == set(CAPTURE_SOURCE_PATHS), 'capture_source_scope')
    return sorted(rows, key=lambda row: row['path'])


def capture_phase(native, prefix, stage, command, work, python, output, deadline):
    """Same external barrier as qualification; capture additionally checks cleanup."""
    service = native.Service(prefix, stage, command, work, python, output / (stage + '.log'), deadline)
    error = None; cleanup = None
    try: service.complete()
    except BaseException as exc: error = exc
    try: cleanup = native.close_capture_service(service)
    except BaseException as exc:
        if error is None: error = exc
    try:
        native.save(output / (stage + '-sandbox.json'), capture_encode(service.observation))
        if cleanup is not None:
            native.save(output / (stage + '-cleanup.json'), capture_encode(cleanup))
    except BaseException as exc:
        if error is None: error = exc
    if error is not None: raise error
    return cleanup


def capture_failure_code(exc):
    # Never echo paths, generated content, exceptions from downloaded dependencies.
    if type(exc).__name__ in ('PreparationError', 'NativeQualificationError') and len(exc.args) == 1:
        value = exc.args[0]
        if type(value) is str and re.fullmatch('[a-z][a-z0-9_]{0,95}', value): return value
    return 'capture_runtime_or_evidence_unavailable'


def capture_record_row(path, output, raw):
    return {'path': path.relative_to(output).as_posix(), 'size': len(raw), 'sha256': digest(raw)}


def capture_session_exchange(native, service, prefix, output, pre, subject_raw, slots, occurrences):
    """Per-call external permission/receipt, with durable full terminal inventory.

    The original response is received before any filesystem/control calls. Each
    timer is then closed and its inactive state observed before the next slot.
    A partial or late frame is kept as failure evidence, never an UNKNOWN answer.
    """
    from datetime import datetime, timezone
    identity = {'prelaunch_sha256': digest(capture_encode(pre)), 'subject_sha256': digest(subject_raw),
                'source_commit': pre['context']['source_commit'], 'run_id': pre['context']['run_id'], 'run_attempt': 1}
    worker_launch = service.runtime_deadline_ns - service.observation['capture_runtime_seconds'] * 1_000_000_000
    terminal = {'record_type': 'q2_capture_transcript_v0', 'record_status': 'native', 'status': 'failed',
        'error_code': 'capture_incomplete', 'binding': identity, 'occurrences': occurrences,
        'worker_launch_ns': worker_launch, 'worker_deadline_ns': service.runtime_deadline_ns,
        'worker_exit_code': None, 'session_end': None, 'session_end_ns': None, 'cleanup': None,
        'sandbox': service.observation, 'ended_at': None, 'authority_effect': 'none', 'production_gate_eligible': False}
    error = None; active_timer = None
    try:
        expected_subject = native.strict_json(subject_raw)
        service.send(b'BIND ' + digest(subject_raw).encode('ascii') + b'\n')
        bound = native.strict_json(service.reader.line(min(service.deadline, time.monotonic() + 20)))
        require(capture_encode(bound) == capture_encode({'record_type': 'q2_capture_bound_v0', 'binding': identity}),
                'capture_subject_acknowledgement')
        for slot, occurrence in zip(slots, occurrences):
            stem = output / 'calls' / slot['call_id']
            ready_raw = response_raw = None
            slot_error = None
            try:
                occurrence['status'] = 'preparation_failed'
                service.send(('PREPARE ' + slot['call_id'] + '\n').encode('ascii'))
                ready_raw = service.reader.line(min(service.deadline, time.monotonic() + 20))
                ready_at = time.monotonic_ns()
                require(len(ready_raw) <= 128 * 1024, 'capture_ready_bound')
                ready = native.strict_json(ready_raw)
                require(ready.get('record_type') == 'q2_capture_slot_ready_v0'
                        and capture_encode(ready.get('slot')) == capture_encode(slot)
                        and capture_encode(ready.get('binding')) == capture_encode(identity)
                        and capture_encode(ready.get('effective_generation')) == capture_encode(expected_subject['effective_generation'])
                        and capture_encode(ready.get('runtime')) == capture_encode(expected_subject['runtime']), 'capture_slot_ready')
                ids = ready.get('input_ids')
                require(type(ids) is list and 1 <= len(ids) <= 4096
                        and all(type(i) is int and 0 <= i < 49152 for i in ids), 'capture_ready_tokens')
                occurrence['ready_received_ns'] = ready_at
                # Root-owned intent exists before the timer/GO. No source output
                # or generated record is copied into another call slot.
                native.save(stem.with_suffix('.intent.json'), capture_encode({'slot': slot, 'binding': identity,
                    'generation_seconds': 15, 'retries': 0, 'intent': 'before_GO'}))
                active_timer = prefix + f"-call-{slot['ordinal']:03d}"
                arm_begin = time.monotonic_ns()
                timer = native.watchdog(active_timer, service.unit)
                occurrence.update(watchdog_armed=True, watchdog_unit=timer, watchdog_arm_begin_ns=arm_begin)
                ceiling = min(arm_begin + 20_000_000_000, service.runtime_deadline_ns, pre['phase_deadline_ns'])
                require(time.monotonic_ns() + 15_000_000_000 < ceiling, 'capture_full_window_unavailable')
                # A complete unsolicited frame already waiting before GO is not a response.
                require(not service.reader.buffer and not service.reader.selector.select(0), 'capture_unsolicited_output')
                occurrence['status'] = 'attempt_uncertain'
                start = service.send(('GENERATE ' + slot['call_id'] + '\n').encode('ascii'))
                deadline = start + 15_000_000_000
                occurrence.update(generation_start_ns=start, generation_deadline_ns=deadline)
                require(deadline < ceiling, 'capture_full_window_unavailable')
                response_raw = service.reader.line(deadline / 1e9)
                received = time.monotonic_ns()
                occurrence['response_received_ns'] = received
                require(received <= deadline and len(response_raw) <= 128 * 1024, 'capture_response_late_or_large')
                # No following call can inherit an active prior timer.
                occurrence['watchdog_closed'] = native.disarm_capture_watchdog(active_timer)
                active_timer = None
                response = native.strict_json(response_raw)
                require(response.get('record_type') == 'q2_capture_response_v0'
                        and capture_encode(response.get('slot')) == capture_encode(slot)
                        and capture_encode(response.get('binding')) == capture_encode(identity), 'capture_response_identity')
                occurrence['status'] = 'completed'
                native.save(stem.with_suffix('.utf8'), response['text'].encode('utf-8'))
            except BaseException as exc:
                slot_error = exc
            # Keep both received frames independently; a failed publication must
            # not replace the first protocol/timing error or authorize another GO.
            for key, raw in (('ready', ready_raw), ('response', response_raw)):
                if raw is not None:
                    path = stem.with_suffix('.' + key + '.json')
                    try:
                        native.save(path, raw)
                        occurrence[key] = capture_record_row(path, output, raw)
                    except BaseException as exc:
                        if slot_error is None: slot_error = exc
            if slot_error is not None:
                # BoundedReader has already capped this unfinished frame. It is
                # rejection evidence, not a completed response or UNKNOWN answer.
                partial = bytes(service.reader.buffer)
                if partial:
                    try: native.save(stem.with_suffix('.partial.bin'), partial)
                    except BaseException: pass
                raise slot_error
        service.send(b'FINISH\n')
        final_raw = service.reader.line(min(service.deadline, pre['phase_deadline_ns'] / 1e9))
        end = native.strict_json(final_raw)
        require(capture_encode(end) == capture_encode({'record_type': 'q2_capture_session_end_v0',
                'binding': identity, 'completed_calls': 150}), 'capture_session_end')
        _, rc = service.complete(empty_tail=True, deadline=min(service.runtime_deadline_ns, pre['phase_deadline_ns']) / 1e9)
        terminal.update(session_end=end, session_end_ns=time.monotonic_ns(), worker_exit_code=rc)
        require(terminal['session_end_ns'] <= service.runtime_deadline_ns, 'capture_session_late')
    except BaseException as exc:
        error = exc
    # Always stop/reap before final evidence publication. Never mask the first error.
    try: terminal['cleanup'] = native.close_capture_service(service)
    except BaseException as exc:
        if error is None: error = exc
    if active_timer is not None:
        try: native.disarm_capture_watchdog(active_timer)
        except BaseException as exc:
            if error is None: error = exc
    if error is None:
        terminal.update(status='completed', error_code=None)
    else:
        terminal['error_code'] = capture_failure_code(error)
    terminal['ended_at'] = datetime.now(timezone.utc).isoformat()
    native.save(output / 'transcript.json', capture_encode(terminal))
    if error is not None: raise error
    return terminal


def capture_derive(output, pre, terminal, native):
    """Producer extraction only. The separate checker re-tokenizes/reconstructs."""
    groups = []
    require(terminal['status'] == 'completed' and len(terminal['occurrences']) == 150, 'capture_derivation_incomplete')
    for i, occurrence in enumerate(terminal['occurrences']):
        slot = occurrence['slot']
        require(occurrence['status'] == 'completed', 'capture_missing_response')
        raw = native.safe_read(output / occurrence['response']['path'])
        require(digest(raw) == occurrence['response']['sha256'], 'capture_changed_response')
        response = native.strict_json(raw)
        item = {'response_id': slot['call_id']}
        if response['stop_reason'] == 'eos': item.update(kind='answer', answer=response['text'])
        else:
            require(response['stop_reason'] == 'token_limit', 'capture_extraction_outcome')
            item['kind'] = 'unknown'
        if i % 3 == 0: groups.append({'group_id': slot['group_id'], 'responses': []})
        groups[-1]['responses'].append(item)
    raw = capture_encode({'schema_version': 'q2_consistency_input_v0', 'record_status': 'archived_response_records',
        'extraction_profile': 'typed_final_answer_or_refusal_v0', 'grouping': {'method_id': 'exact_request_repeats_v0',
        'method_version': 'v0', 'seed': 0, 'sampling_parameters': {'repeats': 3}}, 'groups': groups})
    manifest = capture_encode({'manifest_version': '1.0.0', 'dataset_id': 'q2-field-extractor-' + pre['context']['run_id'],
        'time_range': {'from': pre['started_at'], 'to': terminal['ended_at']},
        'source': {'kind': 'artifact', 'uri': 'github-actions:' + REPOSITORY + '/' + pre['context']['run_id'] + '/1',
                   'description': 'Original fixed Q2 capture; reviewed collector and GitHub host trusted.'},
        'sampling': {'strategy': 'full', 'n': 50, 'seed': 0},
        'hashes': {'input_sha256': digest(raw), 'code_sha': pre['context']['source_commit']},
        'pii_handling': {'scrubbed': False, 'notes': 'Authored controlled inputs; original outputs retained without redaction.'}})
    handoff = {'record_type': 'q2_capture_handoff_v0', 'binding': terminal['binding'],
        'transcript_sha256': digest(capture_encode(terminal)), 'groups_sha256': digest(raw),
        'manifest_sha256': digest(manifest), 'authority_effect': 'none', 'production_gate_eligible': False}
    native.save(output / 'groups.json', raw); native.save(output / 'dataset-manifest.json', manifest)
    native.save(output / 'handoff.json', capture_encode(handoff))
    return handoff


CAPTURE_REDUCTION_SCRIPT = r'''
import hashlib,importlib.util,json,pathlib,subprocess,sys
source,evidence,out=map(pathlib.Path,sys.argv[1:4])
groups_sha,manifest_sha=sys.argv[4:6]
spec=importlib.util.spec_from_file_location('capture_independent_checks',source/'PULSE_safe_pack_v0/tools/check_q2_reference_capture_v0.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
n=c.capture_native(source)
obs=n.parse(n.read(evidence/'capturecheck-sandbox.json'))
c.capture_sandbox(obs,'capturecheck',n)
c.capture_cleanup_check(n.parse(n.read(evidence/'capturecheck-cleanup.json')),obs['unit'])
common=['--groups',str(evidence/'groups.json'),'--dataset-manifest',str(evidence/'dataset-manifest.json'),
        '--expected-groups-sha256',groups_sha,'--expected-manifest-sha256',manifest_sha]
with (out/'summary-build.log').open('xb') as log:
    made=subprocess.run([sys.executable,'-I','-B',str(source/'PULSE_safe_pack_v0/tools/build_q2_reference_summary.py'),
                         *common,'--out',str(out/'summary.json')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=60)
if made.returncode not in (0,1):sys.exit(75)
raw=n.read(out/'summary.json');sha=hashlib.sha256(raw).hexdigest()
summary=n.parse(raw)
if type(summary.get('pass')) is not bool or made.returncode != (0 if summary['pass'] else 1):sys.exit(76)
with (out/'summary-check.json').open('xb') as log:
    checked=subprocess.run([sys.executable,'-I','-B',str(source/'PULSE_safe_pack_v0/tools/check_q2_reference_summary.py'),
        *common,'--summary',str(out/'summary.json'),'--expected-summary-sha256',sha],
        stdin=subprocess.DEVNULL,stdout=log,stderr=log,timeout=60)
if checked.returncode != 0:sys.exit(77)
result=n.parse(n.read(out/'summary-check.json'))
if result.get('ok') is not True or result.get('recomputed_pass') is not summary['pass']:sys.exit(78)
with (out/'reduction.json').open('xb') as f:
    f.write(c.capture_bytes({'record_type':'q2_capture_reduction_v0','builder_exit_code':made.returncode,
        'checker_exit_code':checked.returncode,'metric_pass':summary['pass'],'summary_sha256':sha,
        'groups_sha256':groups_sha,'manifest_sha256':manifest_sha,'authority_effect':'none','production_gate_eligible':False}))
'''


def capture_reference(repo, archive, destination, expected, confirmed):
    import shutil
    import tempfile
    import uuid
    from datetime import datetime, timezone
    require(confirmed is True, 'capture_confirmation_required')
    repo = repo.resolve(strict=True); archive = archive.absolute(); destination = destination.absolute()
    require(not destination.exists() and not destination.is_symlink() and not destination.is_relative_to(repo)
            and not any(p.is_symlink() for p in destination.parents), 'capture_fresh_output_required')
    native = capture_native_module(repo, expected)
    ctx = native.check_context(repo, expected, dict(os.environ))
    ctx['origin'] = 'owner_dispatched_github_q2_capture'
    # The complete immutable authored inventory is available even if setup fails.
    workload, slots = capture_slot_inventory(native.safe_read(repo / REQUESTS))
    occurrences = [{'slot': s, 'status': 'not_attempted', 'ready_received_ns': None, 'generation_start_ns': None,
        'generation_deadline_ns': None, 'response_received_ns': None, 'watchdog_arm_begin_ns': None,
        'watchdog_armed': False, 'watchdog_unit': None, 'watchdog_closed': None, 'ready': None, 'response': None} for s in slots]
    destination.mkdir(mode=0o700)
    start = time.monotonic_ns(); deadline_ns = start + 1200_000_000_000; deadline = deadline_ns / 1e9
    prefix = 'pulse-q2-' + uuid.uuid4().hex[:24]
    stage = Path(tempfile.mkdtemp(prefix=prefix + '-', dir='/var/tmp')); stage.chmod(0o755)
    output = stage / 'evidence'; output.mkdir(mode=0o755)
    python = Path(sys.executable).resolve(strict=True)
    status = 'failed'; error = 'capture_not_finished'; checked = None; reduction = None; service = None
    try:
        native.save(output / 'planned-slots.json', capture_encode(slots))
        sources = stage / 'source'; source_rows = capture_snapshot(repo, sources, expected, native)
        native.freeze(sources)
        for row in source_rows:
            native.save(output / 'source' / row['path'], native.safe_read(sources / row['path']))
        raw = native.safe_read(archive, native.ARCHIVE_SIZE)
        require(len(raw) == native.ARCHIVE_SIZE and digest(raw) == native.ARCHIVE_SHA, 'capture_archive_digest')
        copy_archive = stage / 'original.zip'; native.save(copy_archive, raw); del raw
        native.bounded_local([python, '-I', '-B', sources / CAPTURE_CHECK_NATIVE, 'verify-inputs',
            '--archive', copy_archive, '--staging', stage / 'staged', '--source-root', sources,
            '--repo-root', repo, '--expected-source-sha', expected, '--output', output / 'input-check.json'],
            output / 'input-check.log', deadline)
        preflight = native.strict_json(native.safe_read(output / 'input-check.json'))
        require(preflight['source_files'] == [r for r in source_rows if r['path'] in native.SOURCES]
                and preflight['preparation_source_commit'] == native.PREPARATION_SOURCE, 'capture_input_checker_binding')
        bundle = stage / 'staged/bundle'; (stage / 'staged').chmod(0o755); bundle.chmod(0o755); native.freeze(bundle)
        install = stage / 'install'; native.writable_directory(install)
        capture_phase(native, prefix, 'installer', [python, '-I', '-B', '-c', native.INSTALLER, install,
            bundle / 'wheelhouse', sources / CAPTURE_LOCK, install], install, python, output, deadline)
        venv = install / 'venv'; native.freeze(venv)
        for name in ('bootstrap.json', 'bootstrap-pip.log', 'pip-report.json', 'pip-install.log'):
            native.save(output / name, native.safe_read(install / name))
        native.freeze(install); install.chmod(0o755)
        work = stage / 'installcheck'; native.writable_directory(work)
        capture_phase(native, prefix, 'installcheck', [python, '-I', '-B', sources / CAPTURE_CHECK_NATIVE,
            'verify-installation', '--venv', venv, '--bundle', bundle, '--bootstrap-inventory', output / 'bootstrap.json',
            '--pip-report', output / 'pip-report.json', '--output', work / 'installation.json'], work, python, output, deadline)
        installed_raw = native.safe_read(work / 'installation.json'); installed = native.strict_json(installed_raw)
        native.save(output / 'installation.json', installed_raw); native.freeze(work)
        pre = {'record_type': 'q2_capture_prelaunch_v0', 'record_status': 'native', 'context': ctx,
            'source_files': source_rows, 'preparation_source_commit': native.PREPARATION_SOURCE,
            'preparation_run_id': native.PREPARATION_RUN, 'artifact_sha256': native.ARCHIVE_SHA,
            'selection_sha256': SELECTION_SHA256, 'workload_sha256': REQUESTS_SHA256,
            'installation_sha256': digest(installed_raw),
            'environment_inventory_sha256': digest(capture_encode(installed['inventory'])),
            'slots': slots, 'planned_calls': 150, 'limits': CAPTURE_LIMITS,
            'phase_start_ns': start, 'phase_deadline_ns': deadline_ns,
            'started_at': datetime.now(timezone.utc).isoformat(), 'authority_effect': 'none', 'production_gate_eligible': False}
        pre_raw = capture_encode(pre); native.save(output / 'capture-prelaunch.json', pre_raw)
        work = stage / 'worker'; native.writable_directory(work)
        service = native.Service(prefix, 'captureworker', [venv / 'bin/python', '-I', '-B', sources / CAPTURE_WORKER,
            '--source-root', sources, '--bundle', bundle, '--prelaunch', output / 'capture-prelaunch.json',
            '--expected-prelaunch-sha256', digest(pre_raw), '--mode', 'capture-reference',
            '--subject', output / 'capture-subject.json'], work, python, output / 'captureworker.log', deadline)
        ready_raw = service.reader.line(min(service.deadline, time.monotonic() + 180))
        ready = native.strict_json(ready_raw)
        require(ready.get('record_type') == 'q2_capture_model_ready_v0'
                and capture_encode(ready.get('binding')) == capture_encode({
                    'prelaunch_sha256': digest(pre_raw), 'source_commit': expected,
                    'run_id': ctx['run_id'], 'run_attempt': 1}), 'capture_model_not_ready')
        runtime_expected = {'torch': '2.8.0+cpu', 'transformers': '4.57.6', 'device': 'cpu',
            'dtype': 'torch.float32', 'attention': 'eager', 'threads': 1, 'interop_threads': 1,
            'deterministic': True, 'evaluation': True, 'model_class': 'LlamaForCausalLM',
            'seed': 1729, 'model_defaults': False, 'compile': False, 'quantization': 'none'}
        require(capture_encode(ready.get('runtime')) == capture_encode(runtime_expected), 'capture_runtime_not_ready')
        generation = workload['groups'][0]['request']['generation']
        require(type(ready.get('effective_generation')) is dict and
                all(capture_encode(ready['effective_generation'].get(k)) == capture_encode(v)
                    for k, v in generation.items()) and ready['effective_generation'].get('disable_compile') is True,
                'capture_generation_not_ready')
        native.save(output / 'capture-model-ready.json', ready_raw)
        selection = native.strict_json(native.safe_read(sources / SELECTION))
        model_map = native.strict_json(native.safe_read(sources / CAPTURE_MODEL_MAP))
        subject = {'record_type': 'q2_capture_subject_v0', 'prelaunch_sha256': digest(pre_raw),
            'definition_sha256': selection['release_subject']['definition_sha256'],
            'worker_sha256': next(r['sha256'] for r in source_rows if r['path'] == CAPTURE_WORKER),
            'installation_sha256': digest(installed_raw), 'environment_inventory_sha256': pre['environment_inventory_sha256'],
            'model_files': model_map['files'], 'platform': ctx, 'ready_sha256': digest(ready_raw),
            'effective_generation': ready['effective_generation'], 'runtime': ready['runtime'],
            'authority_effect': 'none', 'production_gate_eligible': False}
        subject_raw = capture_encode(subject); native.save(output / 'capture-subject.json', subject_raw)
        running = service; service = None  # Exchange owns mandatory cleanup, including failures.
        terminal = capture_session_exchange(native, running, prefix, output, pre, subject_raw, slots, occurrences)
        handoff = capture_derive(output, pre, terminal, native)
        work = stage / 'capturecheck'; native.writable_directory(work)
        capture_phase(native, prefix, 'capturecheck', [venv / 'bin/python', '-I', '-B', sources / CHECKER, 'verify-capture',
            '--source-root', sources, '--evidence', output, '--bundle', bundle, '--venv', venv,
            '--expected-source-sha', expected, '--expected-run-id', ctx['run_id'],
            '--expected-prelaunch-sha256', digest(pre_raw), '--expected-subject-sha256', digest(subject_raw),
            '--expected-transcript-sha256', handoff['transcript_sha256'],
            '--expected-source-inventory-sha256', digest(capture_encode(source_rows)),
            '--output', work / 'capture-check.json'], work, python, output, deadline)
        checked_raw = native.safe_read(work / 'capture-check.json'); checked = native.strict_json(checked_raw)
        for key in ('groups_sha256', 'manifest_sha256', 'transcript_sha256', 'binding'):
            require(capture_encode(checked[key]) == capture_encode(handoff[key]), 'capture_checker_binding')
        require(checked.get('complete_original_capture_verified') is True
                and checked.get('decoding_and_extraction_verified') is True and checked.get('verified_calls') == 150,
                'capture_checker_rejected')
        native.save(output / 'capture-check.json', checked_raw); native.freeze(work)
        work = stage / 'reduction'; native.writable_directory(work)
        capture_phase(native, prefix, 'reduction', [venv / 'bin/python', '-I', '-B', '-c', CAPTURE_REDUCTION_SCRIPT,
            sources, output, work, handoff['groups_sha256'], handoff['manifest_sha256']], work, python, output, deadline)
        for name in ('summary.json', 'summary-check.json', 'summary-build.log', 'reduction.json'):
            native.save(output / name, native.safe_read(work / name))
        reduction = native.strict_json(native.safe_read(output / 'reduction.json'))
        require(type(reduction['metric_pass']) is bool
                and reduction['builder_exit_code'] == (0 if reduction['metric_pass'] else 1)
                and reduction['checker_exit_code'] == 0 and reduction['groups_sha256'] == handoff['groups_sha256']
                and reduction['manifest_sha256'] == handoff['manifest_sha256'], 'capture_reduction_verdict')
        require(time.monotonic_ns() <= deadline_ns, 'capture_phase_deadline')
        status = 'captured_metric_pass' if reduction['metric_pass'] else 'captured_metric_fail'; error = None
    except BaseException as exc:
        error = capture_failure_code(exc)
    finally:
        if service is not None:
            try: native.close_capture_service(service)
            except BaseException as exc:
                if error is None: error = capture_failure_code(exc)
                status = 'failed'
        # Preserve bounded phase outputs even when the service failed before its
        # normal handoff. Never replace already retained bytes or hide first error.
        for phase, names in (
            ('install', ('bootstrap.json', 'bootstrap-pip.log', 'pip-report.json', 'pip-install.log')),
            ('installcheck', ('installation.json',)), ('capturecheck', ('capture-check.json',)),
            ('reduction', ('summary.json', 'summary-check.json', 'summary-build.log', 'reduction.json'))):
            for name in names:
                path = stage / phase / name
                try:
                    if path.exists() and not (output / name).exists():
                        native.save(output / name, native.safe_read(path))
                except BaseException as exc:
                    if error is None: error = capture_failure_code(exc)
                    status = 'failed'
        # Full planned extent remains explicit even if preparation/model loading failed.
        evidence = []
        try:
            native.save(output / 'terminal-slots.json', capture_encode(occurrences))
            for path in sorted(output.rglob('*')):
                if path.is_file():
                    data = native.safe_read(path)
                    evidence.append(capture_record_row(path, output, data))
            report = {'record_type': 'q2_reference_capture_v0', 'record_status': 'native', 'status': status,
                'error_code': error, 'context': ctx, 'planned_calls': 150,
                'received_complete_slots': sum(o['status'] == 'completed' for o in occurrences),
                'complete_original_capture_verified': checked is not None and checked.get('complete_original_capture_verified') is True,
                'metric_pass': reduction['metric_pass'] if reduction is not None else None,
                'authority_effect': 'none', 'production_gate_eligible': False, 'evidence': evidence,
                'phase_start_ns': start, 'phase_end_ns': time.monotonic_ns(),
                'trust_boundary': 'reviewed_collector_pinned_dependencies_and_GitHub_host'}
            # The terminal report is published only after every evidence member
            # has been copied. A partial copy must never carry a successful report.
            for path in sorted(output.rglob('*')):
                if path.is_file(): native.save(destination / path.relative_to(output), native.safe_read(path))
            shutil.rmtree(stage)
            uid = int(os.environ.get('SUDO_UID', os.getuid())); gid = int(os.environ.get('SUDO_GID', os.getgid()))
            for path in [destination, *destination.rglob('*')]:
                os.chown(path, uid, gid); os.chmod(path, 0o700 if path.is_dir() else 0o600)
            # Publish the terminal filename only after ownership/privacy work.
            # A failed metadata write/ownership/rename leaves no capture.json.
            pending = destination / '.capture-report.pending'
            native.save(pending, capture_encode(report))
            os.chown(pending, uid, gid); os.chmod(pending, 0o600)
            require(not (destination / 'capture.json').exists(), 'capture_report_destination_exists')
            os.replace(pending, destination / 'capture.json')
        finally:
            if stage.exists(): shutil.rmtree(stage)
    print('Q2 capture ' + status + '; no production admission or release authority')
    return 0 if status == 'captured_metric_pass' else 1


def capture_main(argv):
    parser = argparse.ArgumentParser(description='Owner-only fixed 150-slot Q2 capture.')
    parser.add_argument('phase', choices=['capture-reference'])
    for flag in ('repo-root', 'archive', 'output-dir'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--expected-source-sha', required=True)
    parser.add_argument('--confirm-capture-retention', action='store_true')
    args = parser.parse_args(argv)
    import signal
    def terminated(signum, frame): raise PreparationError('capture_external_timeout')
    previous = signal.signal(signal.SIGTERM, terminated)
    try:
        return capture_reference(args.repo_root, args.archive, args.output_dir, args.expected_source_sha,
                                 args.confirm_capture_retention)
    except Exception:
        print('Q2 capture refused or evidence publication failed; no authority', file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'capture-reference':
        return capture_main(argv)
    return preparation_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
