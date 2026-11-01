#!/usr/bin/env python3
"""Read-only GitHub acquisition for Q3 external postflight; never authorize capture.

Network access requires --allow-network and a GITHUB_TOKEN environment value.
No native execution, retry, model/tokenizer acquisition or GitHub write is provided.
A saved acquisition record is unsigned: it is not offline evidence of origin.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import sys
import time
import types
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = 'HKati/pulse-release-gates-0.1'
API_ROOT = 'https://api.github.com'
API_PREFIX = '/repos/' + REPOSITORY + '/actions/'
API_VERSION = '2022-11-28'
COMPARATOR_SHA256 = 'a0bbeb20ae368992883747277946f78a4926ffd71a276756ee611a81a047d16b'
MAX_SELECTION = 128 * 1024
MAX_METADATA = 4 * 1024**2
MAX_ARCHIVE = 64 * 1024**2
MAX_LOG = 16 * 1024**2
IO_TIMEOUT = 20
TOTAL_SECONDS = 180
STORAGE_SUFFIXES = ('.blob.core.windows.net', '.actions.githubusercontent.com')
IDENTITIES = ('repository', 'source_commit', 'run_id', 'run_attempt', 'job_id',
              'artifact_id', 'request_sha256', 'token_map_sha256')
SELECTION_FIELDS = set(IDENTITIES) | {'record_type', 'archive', 'source_files',
                                     'comparator_sha256', 'acquirer_sha256'}
BOUNDARIES = {
    'authority_effect': 'none', 'capture_handoff_approved': False,
    'new_execution_authorized': False, 'production_gate_eligible': False,
    'current_run_evidence': False, 'policy_activation': False,
    'model_executed': False, 'tokenization_reperformed': False,
    'metric_evaluated': False, 'capture_consent': 'not_evaluated',
    'artifact_attempt_attestation': None, 'verifier_execution_attested': False,
    'saved_record_authenticates_origin': False,
}


class AcquisitionError(ValueError):
    """Stable codes only; never expose credentials, signed URLs or server errors."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise AcquisitionError(code)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def open_directory(path: Path) -> int:
    """Hold a directory through a no-symlink walk from the filesystem root."""
    path = Path(os.path.abspath(path))
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                          dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_source(path: Path, maximum: int) -> bytes:
    path = Path(os.path.abspath(path))
    parent = open_directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     dir_fd=parent)
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and 0 < before.st_size <= maximum, 'INPUT_FILE_BOUND')
        data = bytearray()
        while len(data) <= maximum:
            block = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size,
                              s.st_mtime_ns, s.st_ctime_ns)
        current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        require(identity(before) == identity(os.fstat(fd)) == identity(current)
                and len(data) == before.st_size, 'INPUT_FILE_CHANGED')
        return bytes(data)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def load_comparator():
    """Compile exactly the reviewed bytes, not a cached bytecode substitute."""
    path = Path(__file__).parent / 'check_q3_external_postflight_v0.py'
    raw = read_source(path, MAX_SELECTION)
    require(digest(raw) == COMPARATOR_SHA256, 'UNREVIEWED_COMPARATOR')
    module = types.ModuleType('q3_live_postflight_comparator')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec', dont_inherit=True), module.__dict__)
    return module


def select(raw: bytes, expected_sha256: str, m) -> dict:
    require(m.sha(expected_sha256) and digest(raw) == expected_sha256, 'SELECTION_DIGEST')
    require(len(raw) <= MAX_SELECTION, 'SELECTION_BOUND')
    s = m.strict_json(raw)
    m.fields(s, SELECTION_FIELDS, 'ACQUISITION_SELECTION_FIELDS')
    require(s['record_type'] == 'q3_external_postflight_acquisition_request_v0'
            and s['repository'] == REPOSITORY, 'SELECTION_IDENTITY')
    require(m.sha(s['acquirer_sha256'])
            and digest(read_source(Path(__file__), MAX_SELECTION)) == s['acquirer_sha256'],
            'ACQUIRER_IDENTITY')
    require(s['comparator_sha256'] == COMPARATOR_SHA256, 'COMPARATOR_SELECTION')
    m.fields(s['archive'], {'sha256', 'size_bytes'}, 'ARCHIVE_SELECTION_FIELDS')
    require(m.sha(s['archive']['sha256']) and m.positive(s['archive']['size_bytes'])
            and s['archive']['size_bytes'] <= MAX_ARCHIVE, 'ARCHIVE_SELECTION_BOUND')
    # Reuse the comparator's closed identity/source-selection validation before I/O.
    e = expectation(s, {n: b'x' for n in m.INPUTS}, m)
    e['inputs']['artifact.zip'] = dict(s['archive'])
    body = m.encode(e)
    m.selection(body, m.digest(body))
    return s


def expectation(s: dict, raw: dict[str, bytes], m) -> dict:
    return {'record_type': 'q3_external_postflight_expectation_v0',
            **{k: s[k] for k in IDENTITIES},
            'verifier_sha256': s['comparator_sha256'],
            'source_files': s['source_files'],
            'inputs': {n: {'sha256': digest(b), 'size_bytes': len(b)} for n, b in raw.items()}}


def paths(s: dict) -> dict[str, str]:
    return {
        'run.json': API_PREFIX + f'runs/{s["run_id"]}/attempts/1',
        'jobs.json': API_PREFIX + f'runs/{s["run_id"]}/attempts/1/jobs?per_page=100&page=1',
        'artifact.json': API_PREFIX + f'artifacts/{s["artifact_id"]}',
        'artifact.zip': API_PREFIX + f'artifacts/{s["artifact_id"]}/zip',
        'job.log': API_PREFIX + f'jobs/{s["job_id"]}/logs',
    }


def api_url(path: str) -> str:
    require(type(path) is str and re.fullmatch(
        re.escape(API_PREFIX) + r'(?:runs/[1-9][0-9]{0,18}/attempts/1'
        r'(?:/jobs\?per_page=100&page=1)?|artifacts/[1-9][0-9]{0,18}(?:/zip)?'
        r'|jobs/[1-9][0-9]{0,18}/logs)', path) is not None, 'API_ENDPOINT')
    return API_ROOT + path


def storage_url(value: str) -> str:
    require(type(value) is str and 0 < len(value) <= 8192
            and all(32 < ord(c) < 127 for c in value) and '\\' not in value,
            'STORAGE_URL')
    p = urllib.parse.urlsplit(value)
    host = p.hostname or ''
    require(p.scheme == 'https' and p.netloc == host and not p.fragment
            and host == host.lower() and re.fullmatch(r'[a-z0-9.-]+', host) is not None
            and all(host.split('.')) and any(host.endswith(s) for s in STORAGE_SUFFIXES)
            and p.path.startswith('/') and not p.path.startswith('//'), 'STORAGE_URL')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubReader:
    """Only GET; fresh no-cookie openers; token only on fixed GitHub API routes."""
    def __init__(self, token: str):
        require(type(token) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,512}', token) is not None,
                'TOKEN_MISSING_OR_INVALID')
        self._token = token
        self._deadline = time.monotonic() + TOTAL_SECONDS
        self.transfers: list[dict] = []

    def remaining(self) -> float:
        left = self._deadline - time.monotonic()
        require(left > 0, 'ACQUISITION_DEADLINE')
        return min(IO_TIMEOUT, left)

    @staticmethod
    def header(response, key: str) -> str | None:
        values = response.headers.get_all(key, [])
        require(len(values) <= 1, 'DUPLICATE_HTTP_HEADER')
        return values[0] if values else None

    def _get(self, url: str, maximum: int, api: bool, redirect: bool = False):
        # This is also checked here so a caller cannot send credentials to another host.
        if api:
            require(url.startswith(API_ROOT), 'API_ENDPOINT')
            require(api_url(url[len(API_ROOT):]) == url, 'API_ENDPOINT')
        else:
            storage_url(url)
        headers = {'Accept-Encoding': 'identity', 'User-Agent': 'PULSE-Q3-postflight-v0'}
        if api:
            headers.update({'Accept': 'application/vnd.github+json',
                            'X-GitHub-Api-Version': API_VERSION,
                            'Authorization': 'Bearer ' + self._token})
        request = urllib.request.Request(url, headers=headers, method='GET')
        # No proxy from the environment, cookie jar, netrc, or implicit redirect handler.
        context = ssl.create_default_context()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                    urllib.request.HTTPSHandler(context=context), NoRedirect())
        response = None
        try:
            try:
                response = opener.open(request, timeout=self.remaining())
            except urllib.error.HTTPError as exc:
                response = exc
            status = response.status
            if redirect:
                require(status == 302, 'DOWNLOAD_REDIRECT_STATUS')
                location = self.header(response, 'Location')
                return storage_url(location)
            require(status == 200, 'HTTP_STATUS')
            require(self.header(response, 'Content-Encoding') in (None, 'identity'),
                    'HTTP_CONTENT_ENCODING')
            length = self.header(response, 'Content-Length')
            if length is not None:
                require(re.fullmatch(r'[0-9]{1,12}', length) is not None
                        and 0 < int(length) <= maximum, 'HTTP_SIZE')
            if api:
                content_type = self.header(response, 'Content-Type') or ''
                require(content_type.split(';', 1)[0].strip().lower()
                        in ('application/json', 'application/vnd.github+json'), 'HTTP_CONTENT_TYPE')
                require(not self.header(response, 'Link'), 'UNSUPPORTED_PAGINATION')
            data = bytearray()
            while len(data) <= maximum:
                self.remaining()
                block = response.read1(min(65536, maximum + 1 - len(data)))
                if not block:
                    break
                data.extend(block)
                require(len(data) <= maximum, 'HTTP_SIZE')
            require(0 < len(data) <= maximum
                    and (length is None or len(data) == int(length)), 'HTTP_SIZE')
            self.remaining()
            return bytes(data)
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            raise AcquisitionError('HTTP_TRANSPORT') from exc
        finally:
            if response is not None:
                response.close()

    def json(self, path: str) -> bytes:
        body = self._get(api_url(path), MAX_METADATA, True)
        self.transfers.append({'endpoint': path, 'sha256': digest(body), 'size_bytes': len(body),
                               'download_host': None})
        return body

    def download(self, path: str, maximum: int) -> bytes:
        require(path.endswith(('/zip', '/logs')), 'DOWNLOAD_ENDPOINT')
        # A signed storage URL is only accepted from this verified-TLS API response.
        location = self._get(api_url(path), 0, True, True)
        body = self._get(location, maximum, False)
        self.transfers.append({'endpoint': path, 'sha256': digest(body), 'size_bytes': len(body),
                               'download_host': urllib.parse.urlsplit(location).hostname})
        return body


class EvidenceDirectory:
    """Exclusive private output directory. Keep complete acquired records on failure."""
    def __init__(self, path: Path):
        path = Path(os.path.abspath(path))
        self.parent = open_directory(path.parent)
        self.fd = None
        self.files: dict[str, dict] = {}
        try:
            os.mkdir(path.name, 0o700, dir_fd=self.parent)  # never reuse/overwrite an attempt
            self.fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                              dir_fd=self.parent)
            os.fchmod(self.fd, 0o700)
            require(stat.S_IMODE(os.fstat(self.fd).st_mode) == 0o700, 'OUTPUT_DIRECTORY_MODE')
        except BaseException:
            self.close()
            raise

    def write(self, name: str, raw: bytes) -> None:
        require(re.fullmatch(r'[a-z][a-z0-9_.-]{0,79}', name) is not None
                and type(raw) is bytes and len(raw) <= MAX_ARCHIVE, 'OUTPUT_MEMBER')
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=self.fd)
        try:
            os.fchmod(fd, 0o600)
            view = memoryview(raw)
            while view:
                written = os.write(fd, view)
                require(written > 0, 'OUTPUT_WRITE')
                view = view[written:]
            os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            h = hashlib.sha256(); count = 0
            while True:
                block = os.read(fd, 65536)
                if not block:
                    break
                h.update(block); count += len(block)
            st = os.fstat(fd)
            named = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
            require((st.st_dev, st.st_ino) == (named.st_dev, named.st_ino)
                    and st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600
                    and count == st.st_size == len(raw) and h.hexdigest() == digest(raw),
                    'OUTPUT_READBACK')
            self.files[name] = {'sha256': digest(raw), 'size_bytes': len(raw)}
        finally:
            os.close(fd)
        os.fsync(self.fd)

    def finish(self) -> None:
        require(set(os.listdir(self.fd)) == set(self.files), 'OUTPUT_INVENTORY')
        for name, pin in self.files.items():
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                         dir_fd=self.fd)
            try:
                before = os.fstat(fd)
                require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                        and stat.S_IMODE(before.st_mode) == 0o600
                        and before.st_size == pin['size_bytes'], 'OUTPUT_INVENTORY_MEMBER')
                h = hashlib.sha256(); count = 0
                while count <= pin['size_bytes']:
                    block = os.read(fd, min(65536, pin['size_bytes'] + 1 - count))
                    if not block:
                        break
                    h.update(block); count += len(block)
                identity = lambda t: (t.st_dev, t.st_ino, t.st_mode, t.st_nlink,
                                      t.st_size, t.st_mtime_ns, t.st_ctime_ns)
                named = os.stat(name, dir_fd=self.fd, follow_symlinks=False)
                require(identity(before) == identity(os.fstat(fd)) == identity(named)
                        and count == pin['size_bytes'] and h.hexdigest() == pin['sha256'],
                        'OUTPUT_INVENTORY_MEMBER')
            finally:
                os.close(fd)
        self.write('inventory.json', encode({'record_type': 'q3_postflight_acquisition_inventory_v0',
            'files': dict(self.files), 'inventory_self_excluded': True, **BOUNDARIES}))
        os.fsync(self.parent)

    def close(self) -> None:
        if self.fd is not None:
            os.close(self.fd); self.fd = None
        if self.parent is not None:
            os.close(self.parent); self.parent = None


def metadata_valid(s: dict, raw: dict[str, bytes], m, now: datetime) -> None:
    require(type(now) is datetime and now.utcoffset() is not None, 'CLOCK')
    require(all(type(raw.get(n)) is bytes and 0 < len(raw[n]) <= MAX_METADATA
                for n in ('run.json', 'jobs.json', 'artifact.json')), 'METADATA_BOUND')
    e = expectation(s, {**raw, 'job.log': b'x', 'artifact.zip': b'x'}, m)
    e['inputs']['artifact.zip'] = dict(s['archive'])
    m.metadata(e, raw)
    art = m.strict_json(raw['artifact.json'])
    require(m.stamp(art['expires_at']) > now >= m.stamp(art['created_at']), 'ARTIFACT_NOT_CURRENT')


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def acquire(s: dict, reader, store: EvidenceDirectory, m,
            clock=None) -> tuple[dict, bytes]:
    """Shared sequence; test doubles are in-process only, never a CLI input."""
    clock = clock or utc_now
    selected = paths(s)
    names = ('run.json', 'jobs.json', 'artifact.json')
    raw = {}
    for name in names:
        raw[name] = reader.json(selected[name]); store.write(name, raw[name])
    metadata_valid(s, raw, m, clock())  # reject substitution before archive/log acquisition
    for name, maximum in [('artifact.zip', s['archive']['size_bytes']), ('job.log', MAX_LOG)]:
        body = reader.download(selected[name], maximum)
        require(type(body) is bytes and 0 < len(body) <= maximum, 'DOWNLOAD_SIZE')
        store.write(name, body); raw[name] = body
        if name == 'artifact.zip':
            require(len(body) == s['archive']['size_bytes']
                    and digest(body) == s['archive']['sha256'], 'ARCHIVE_DIGEST_OR_SIZE')
    after = {}
    for name in names:
        after[name] = reader.json(selected[name]); store.write(name.replace('.json', '.after.json'), after[name])
    metadata_valid(s, after, m, clock())
    # Conservative v0: even an ancillary metadata change requires a new reviewed observation.
    require(all(m.encode(m.strict_json(raw[n])) == m.encode(m.strict_json(after[n])) for n in names),
            'METADATA_CHANGED_DURING_ACQUISITION')
    e = m.encode(expectation(s, raw, m))
    store.write('expectation.json', e)
    result = m.compare(e, digest(e), raw)
    comparison = m.encode(result)
    store.write('comparison.json', comparison)
    return result, comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection', type=Path, required=True)
    parser.add_argument('--selection-sha256', required=True)
    parser.add_argument('--output-dir', type=Path,
                        help='New directory below an existing trusted parent; never replaced')
    parser.add_argument('--validate-selection-only', action='store_true')
    parser.add_argument('--allow-network', action='store_true', help='Explicit read-only acquisition consent')
    args = parser.parse_args(argv)
    store = None; reader = None; m = None
    started = utc_now().isoformat()
    selection_sha = None
    try:
        m = load_comparator()
        raw = read_source(args.selection, MAX_SELECTION)
        s = select(raw, args.selection_sha256, m)
        selection_sha = digest(raw)
        if args.validate_selection_only:
            require(not args.allow_network and args.output_dir is None, 'VALIDATE_ONLY_ARGUMENTS')
            sys.stdout.buffer.write(encode({'record_type': 'q3_postflight_selection_validation_v0',
                'selection_sha256': selection_sha, 'selection_valid': True,
                'network_accessed': False, **BOUNDARIES}))
            return 0
        require(args.allow_network and args.output_dir is not None, 'READ_ONLY_ACQUISITION_CONSENT')
        reader = GitHubReader(os.environ.get('GITHUB_TOKEN', ''))
        store = EvidenceDirectory(args.output_dir)
        store.write('selection.json', raw)
        result, comparison = acquire(s, reader, store, m)
        receipt = {'record_type': 'q3_external_postflight_acquisition_v0',
            'status': 'complete', 'disposition': result['disposition'],
            'selection_sha256': selection_sha, 'comparison_sha256': digest(comparison),
            'acquirer_sha256': s['acquirer_sha256'], 'comparator_sha256': s['comparator_sha256'],
            'observation_channel': 'live_github_https_api_and_api_selected_storage',
            'transport_trust': 'local_tls_ca_store_and_github_service',
            'metadata_recheck': 'UNCHANGED', 'api_version': API_VERSION,
            'started_at': started, 'completed_at': utc_now().isoformat(),
            'transfers': reader.transfers, **BOUNDARIES}
        store.write('acquisition.json', encode(receipt)); store.finish()
        sys.stdout.buffer.write(encode(receipt))
        return 0 if result['disposition'] == 'CONSISTENT_OFFLINE' else 2
    except (AcquisitionError, OSError, ValueError, KeyError, TypeError, RecursionError, KeyboardInterrupt) as exc:
        trusted = (AcquisitionError,) + ((m.PostflightError,) if m is not None else ())
        code = str(exc) if isinstance(exc, trusted) else 'ACQUISITION_INCOMPLETE'
        failure = {'record_type': 'q3_external_postflight_acquisition_error_v0',
            'status': 'incomplete', 'disposition': 'REJECT_INVALID_OR_INCOMPLETE',
            'error_code': code, 'selection_sha256': selection_sha,
            'started_at': started, 'completed_at': utc_now().isoformat(),
            'transfers': reader.transfers if reader is not None else [], **BOUNDARIES}
        if store is not None:
            try:
                store.write('failure.json', encode(failure)); store.finish()
            except (OSError, AcquisitionError):
                failure['preservation_complete'] = False
        sys.stderr.buffer.write(encode(failure))
        return 1
    finally:
        if store is not None:
            store.close()


if __name__ == '__main__':
    raise SystemExit(main())
