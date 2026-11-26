"""Bound the selected public rebuilder snapshot and parse source-resolution facts.

All inputs are bytes.  Nothing here accesses the network, executes source code,
verifies a signature, or selects an acceptance policy.  The separate checker
must freshly reconstruct the original archive/source/build-record/signature
chain and require an independently selected policy digest before admission.

The public log is unsigned and explicitly truncated.  Preserved implementation
sources explain reviewed semantics, not the code deployed for this rebuild.
Retrieval metadata is an authored observation, not an authenticated timestamp.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import re
import stat
import struct
import zipfile
import zlib


PROFILE = "original_loader_public_rebuilder_snapshot_v0"
EVIDENCE_ARCHIVE_REL = (
    "docs/compute/required_gate_idempotence_loader_rebuild_acceptance_v0/"
    "preservation/public_service_evidence_v0.zip"
)
SOURCE_INPUT_BINDINGS = {
    "glibc_2.41-12+deb13u4.dsc": {
        "size_bytes": 7576,
        "sha256": "0915324aa646bb99abfaa9aa6ecb734b30babd28454a3e51f3152912370fbd3e",
    },
    "glibc_2.41.orig.tar.xz": {
        "size_bytes": 20323540,
        "sha256": "f24aa441021121a79266f0d75242706cab8843a47901fefe74527491807f1998",
    },
    "glibc_2.41-12+deb13u4.debian.tar.xz": {
        "size_bytes": 499524,
        "sha256": "dda4153511bfd543502d18e5bc9323110996fe9c531f14ae3fad6eb17f027c7d",
    },
}
BUILDINFO_NAME = "glibc_2.41-12+deb13u4_amd64.buildinfo"
BUILDINFO_BINDING = {
    "size_bytes": 15502,
    "sha256": "5af18d1a381adb80a101b714b57c7822e5f0442f68e148df26b0dbcc4a1ca1e9",
}
PRIOR_CARRIER_NAMES = (
    "libc6_attestation.json", "libc6_dbg_attestation.json", "public_keys.json",
)
EVIDENCE_ARCHIVE_BINDING = {'sha256': 'a826480a93d9a9a4fc458502731370d67845f2dfc67d4f95e5b59b9941246db3', 'size_bytes': 486911}
EVIDENCE_MEMBERS = {'debrebuild.pl': {'sha256': '53a98e5ed34575fc3cb54b1d8506cba9a4782f66315d60936a3003caf5622390',
                   'size_bytes': 28931,
                   'url': 'https://sources.debian.org/data/main/d/devscripts/2.26.15/scripts/debrebuild.pl'},
 'libc6_attestation.json': {'sha256': 'dc7cc8831246e1fac3aa29d02177f5ce85253fde5d586e1848a869c7805df2c6',
                            'size_bytes': 1104,
                            'url': 'https://reproduce.debian.net/amd64/api/v1/builds/269686/artifacts/710018/attestation'},
 'libc6_dbg_attestation.json': {'sha256': '9e7e500b1aa181474a4ceb4bde60779fe6adb95ade3812c82833b037b49ceda4',
                                'size_bytes': 1112,
                                'url': 'https://reproduce.debian.net/amd64/api/v1/builds/269686/artifacts/710019/attestation'},
 'public_keys.json': {'sha256': 'ae30bbb97ab1d57cb8bc874571cc8883f9ea44ca105ff27feb3e621c9ac85761',
                      'size_bytes': 142,
                      'url': 'https://reproduce.debian.net/amd64/api/v1/meta/public-keys'},
 'rebuild_269686.json': {'sha256': '8f33a6f92164c91d76a335e3b14510f92c22a8c64cf5b09ba28918b521606231',
                         'size_bytes': 274,
                         'url': 'https://reproduce.debian.net/amd64/api/v1/builds/269686'},
 'rebuild_269686.log': {'sha256': '014cdf663727e61b0e5c4c8a761be3374cdb249479abfd9ab4348ce995d721a4',
                        'size_bytes': 20971567,
                        'url': 'https://reproduce.debian.net/amd64/api/v1/builds/269686/log'},
 'rebuilder-debian.sh': {'sha256': '66d6e397dad32c5000a72da11d1a9de5c7a36a210bb1f138489be11679a81820',
                         'size_bytes': 3845,
                         'url': 'https://raw.githubusercontent.com/kpcyrd/rebuilderd/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/worker/rebuilder-debian.sh'},
 'rebuilderd_LICENSE': {'sha256': 'd62f065830aa3739cc031156b9690805c7b2e811b4a178c8b4acd8725d561c94',
                        'size_bytes': 35142,
                        'url': 'https://raw.githubusercontent.com/kpcyrd/rebuilderd/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/LICENSE'},
 'rebuilderd_daemon_attestation.rs': {'sha256': 'cda2f3da41e710f451f0591e713c5ffcbd82658fd518ec15f517c895a2e5e38f',
                                      'size_bytes': 10928,
                                      'url': 'https://raw.githubusercontent.com/kpcyrd/rebuilderd/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/daemon/src/attestation.rs'},
 'rebuilderd_daemon_build.rs': {'sha256': '8b5bfa7a152871edef92290fccbaf99acb40502cd4c530a1ba6a4f88c4f47b43',
                                'size_bytes': 15555,
                                'url': 'https://raw.githubusercontent.com/kpcyrd/rebuilderd/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/daemon/src/api/v1/build.rs'},
 'rebuilderd_daemon_meta.rs': {'sha256': '629bd3e68b732592239c5a31ab3449774127a8ed216157e41155351625c6069c',
                               'size_bytes': 4081,
                               'url': 'https://raw.githubusercontent.com/kpcyrd/rebuilderd/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/daemon/src/api/v1/meta.rs'},
 'rebuilderd_worker_rebuild.rs': {'sha256': '2b6d0b3406878888cb69c0f4791474609bf07703e4aa6975dd29011e84a1eee9',
                                  'size_bytes': 10515,
                                  'url': 'https://raw.githubusercontent.com/kpcyrd/rebuilderd/8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999/worker/src/rebuild.rs'},
 'retrieval_manifest_v0.json': {'sha256': 'bf7b2d0380c233a2561803e9ac47d4012a632bf7f19770ebf299318f6d5161d4',
                                'size_bytes': 8463,
                                'url': None},
 'service_overview.html': {'sha256': '1defd250800c1bf35aed13720d4f9b8c8581b1b92a7fc190a3563c3b5de6e883',
                           'size_bytes': 13901,
                           'url': 'https://reproduce.debian.net/'}}
EVIDENCE_DECODED_BYTES = 21105560
EVIDENCE_ARCHIVE_BYTES_MAX = 8 * 1024 * 1024
LOG_TRUNCATED_AT = 20 * 1024 * 1024
LOG_TRUNCATION_MARKER = b"\n\nTRUNCATED DUE TO SIZE LIMIT: 20971520 bytes\n\n"
LOG_BYTES_MAX = LOG_TRUNCATED_AT + len(LOG_TRUNCATION_MARKER)
LOG_LINES_MAX = 30000
LOG_LINE_BYTES_MAX = 16384
CONTROL_BYTES_MAX = 65536
SNAPSHOT_STARTED_AT_UTC = "2026-11-23T22:00:10Z"
SNAPSHOT_COMPLETED_AT_UTC = "2026-11-23T22:02:34Z"
REBUILDERD_COMMIT = "8c996c248f9b9668fa62fcd8fe8aa2fd0ed7b999"
DEVSCRIPTS_VERSION = "2.26.15"
WORK_ROOT = "/srv/rebuilderd/tmp/rebuilderdgnwD60"
INPUT_DIR = WORK_ROOT + "/inputs"
SOURCE_NAME = "glibc"
SOURCE_VERSION = "2.41-12+deb13u4"
DSC_NAME = "glibc_2.41-12+deb13u4.dsc"
SOURCE_URLS = {
    name: "https://deb.debian.org/debian/pool/main/g/glibc/" + name.replace("+", "%2b")
    for name in SOURCE_INPUT_BINDINGS
}
SERVICE_METADATA = {
    "id": 269686, "name": SOURCE_NAME, "version": SOURCE_VERSION,
    "distribution": "debian", "release": "trixie-proposed-updates",
    "architecture": "amd64", "backend": "debian", "retries": 0,
    "started_at": "2026-07-11T21:20:36.846705500",
    "built_at": "2026-07-11T22:32:30.931810002", "status": "GOOD",
}
BOUNDARY = {
    "public_service_snapshot_is_signed": False,
    "public_log_is_signed": False,
    "public_log_is_complete": False,
    "source_input_hashes_directly_attested": False,
    "retrieval_metadata_is_independently_authenticated_timestamp": False,
    "historical_rebuilder_key_role_authenticated": False,
    "historical_signing_time_authenticated": False,
    "historical_worker_identity_authenticated": False,
    "historical_deployment_authenticated": False,
    "native_rebuild_observed_by_this_checker": False,
    "original_buildinfo_signature_verified": False,
    "original_dsc_signature_verified": False,
    "project_acceptance_policy_selected": False,
    "source_build_gate_satisfied": False,
    "original_acquisition_authorized": False,
    "b2_complete": False,
    "metric_pass": None,
    "authority_effect": "none",
}


class AcceptanceEvidenceError(ValueError):
    """Stable rejection code without reflected input or parser diagnostics."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise AcceptanceEvidenceError(code)


def _binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _bound(raw, expected, code):
    _need(_binding(raw) == {name: expected[name] for name in ("size_bytes", "sha256")}, code)


def _input_extents(buildinfo_bytes, source_inputs):
    _need(type(buildinfo_bytes) is bytes
          and len(buildinfo_bytes) == BUILDINFO_BINDING["size_bytes"],
          "rebuild_acceptance_buildinfo_size")
    _need(type(source_inputs) is dict and set(source_inputs) == set(SOURCE_INPUT_BINDINGS),
          "rebuild_acceptance_source_inventory")
    for name, expected in SOURCE_INPUT_BINDINGS.items():
        _need(type(source_inputs[name]) is bytes
              and len(source_inputs[name]) == expected["size_bytes"],
              "rebuild_acceptance_source_size")


def preflight_public_service_inputs(*, archive_bytes, buildinfo_bytes, source_inputs):
    """Inspect every external extent before any input hash, parse or subprocess."""
    _need(type(archive_bytes) is bytes and 0 < len(archive_bytes) <= EVIDENCE_ARCHIVE_BYTES_MAX,
          "rebuild_acceptance_archive_size")
    _input_extents(buildinfo_bytes, source_inputs)


def _input_facts(buildinfo_bytes, source_inputs):
    _bound(buildinfo_bytes, BUILDINFO_BINDING, "rebuild_acceptance_buildinfo_binding")
    for name, expected in SOURCE_INPUT_BINDINGS.items():
        _bound(source_inputs[name], expected, "rebuild_acceptance_source_binding")
    # These fields come from the freshly hashed complete original carrier.
    for field, expected in ((b"Source", b"glibc"), (b"Version", b"2.41-12+deb13u4"),
                            (b"Build-Architecture", b"amd64")):
        values = re.findall(rb"^" + field + rb": ([^\n]+)$", buildinfo_bytes, re.MULTILINE)
        _need(values == [expected], "rebuild_acceptance_buildinfo_identity")
    return {
        "buildinfo": {"filename": BUILDINFO_NAME, **_binding(buildinfo_bytes)},
        "source_inputs": [{"filename": name, **_binding(source_inputs[name])}
                          for name in sorted(source_inputs)],
    }


def _zip_directory(raw):
    # Bound the directory before ZipFile can allocate member objects.  This
    # selected ZIP has no prefixes, comments, ZIP64, data descriptors or extras.
    _need(len(raw) >= 22, "rebuild_acceptance_archive_directory")
    end = struct.unpack("<4s4H2LH", raw[-22:])
    signature, disk, directory_disk, disk_count, count, size, offset, comment = end
    _need(signature == b"PK\x05\x06" and disk == directory_disk == comment == 0
          and disk_count == count == len(EVIDENCE_MEMBERS)
          and 0 < size <= 8192 and 0 <= offset <= len(raw)
          and offset + size == len(raw) - 22,
          "rebuild_acceptance_archive_directory")
    return offset


def read_public_service_evidence(archive_bytes):
    """Read the exact bounded ZIP in memory; never extract paths to disk."""
    _need(type(archive_bytes) is bytes
          and 0 < len(archive_bytes) <= EVIDENCE_ARCHIVE_BYTES_MAX,
          "rebuild_acceptance_archive_size")
    try:
        directory_offset = _zip_directory(archive_bytes)
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            _need(names == sorted(EVIDENCE_MEMBERS) and len(set(names)) == len(names),
                  "rebuild_acceptance_archive_roster")
            _need(not archive.comment and archive.start_dir == directory_offset,
                  "rebuild_acceptance_archive_metadata")
            total, cursor = 0, 0
            # Preflight ALL member metadata before reading or hashing ANY body.
            for info in infos:
                expected = EVIDENCE_MEMBERS[info.filename]
                mode = info.external_attr >> 16
                _need(info.orig_filename == info.filename and not info.is_dir()
                      and info.create_system == 3 and stat.S_ISREG(mode)
                      and stat.S_IMODE(mode) == 0o600 and info.flag_bits == 0
                      and info.compress_type == zipfile.ZIP_DEFLATED
                      and info.create_version == info.extract_version == 20
                      and info.date_time == (1980, 1, 1, 0, 0, 0)
                      and not info.extra and not info.comment
                      and info.file_size == expected["size_bytes"]
                      and 0 < info.compress_size <= len(archive_bytes)
                      and info.header_offset == cursor,
                      "rebuild_acceptance_archive_member")
                _need(cursor + 30 <= directory_offset, "rebuild_acceptance_archive_local_header")
                local = struct.unpack("<4s5H3L2H", archive_bytes[cursor:cursor + 30])
                sig, version, flags, method, mtime, mdate, crc, csize, usize, nlen, elen = local
                name = info.filename.encode("ascii")
                _need(sig == b"PK\x03\x04" and version == 20 and flags == 0
                      and method == zipfile.ZIP_DEFLATED and mtime == 0 and mdate == 33
                      and crc == info.CRC and csize == info.compress_size
                      and usize == info.file_size and nlen == len(name) and elen == 0
                      and archive_bytes[cursor + 30:cursor + 30 + nlen] == name,
                      "rebuild_acceptance_archive_local_header")
                cursor += 30 + nlen + csize
                total += info.file_size
                _need(cursor <= directory_offset and total <= EVIDENCE_DECODED_BYTES,
                      "rebuild_acceptance_archive_extent")
            _need(cursor == directory_offset and total == EVIDENCE_DECODED_BYTES,
                  "rebuild_acceptance_archive_extent")
            files = {}
            for info in infos:
                with archive.open(info, "r") as stream:
                    value = stream.read(info.file_size + 1)
                _bound(value, EVIDENCE_MEMBERS[info.filename],
                       "rebuild_acceptance_evidence_member_binding")
                files[info.filename] = value
        _bound(archive_bytes, EVIDENCE_ARCHIVE_BINDING, "rebuild_acceptance_archive_binding")
        return files
    except AcceptanceEvidenceError:
        raise
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, EOFError, zlib.error,
            ValueError, TypeError, KeyError, IndexError, UnicodeError, struct.error) as exc:
        raise AcceptanceEvidenceError("rebuild_acceptance_archive_invalid") from exc


def _pairs(pairs):
    value = {}
    for key, child in pairs:
        _need(key not in value, "rebuild_acceptance_json_duplicate_key")
        value[key] = child
    return value


def _integer(value):
    _need(re.fullmatch(r"-?[0-9]{1,10}", value) is not None,
          "rebuild_acceptance_json_integer")
    return int(value)


def _no_number(_value):
    raise AcceptanceEvidenceError("rebuild_acceptance_json_number")


def _json(raw):
    _need(type(raw) is bytes and 0 < len(raw) <= CONTROL_BYTES_MAX,
          "rebuild_acceptance_json_size")
    try:
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs,
                           parse_int=_integer, parse_float=_no_number, parse_constant=_no_number)
    except AcceptanceEvidenceError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise AcceptanceEvidenceError("rebuild_acceptance_json_invalid") from exc
    nodes, pending = 0, [(value, 0)]
    while pending:
        item, depth = pending.pop()
        nodes += 1
        _need(nodes <= 512 and depth <= 8, "rebuild_acceptance_json_complexity")
        if type(item) is dict:
            pending.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
    return value


def _utc(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}(-[0-9]{2}){2}T[0-9]{2}(:[0-9]{2}){2}Z",
                                            value) is not None,
          "rebuild_acceptance_snapshot_time")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise AcceptanceEvidenceError("rebuild_acceptance_snapshot_time") from exc


def _snapshot(raw):
    value = _json(raw)
    fields = {"record_type", "snapshot_started_at_utc", "snapshot_completed_at_utc",
              "retrieval_transport", "retrieval_metadata_is_independently_authenticated_timestamp",
              "retrieval_metadata_is_historical_execution_proof", "responses"}
    _need(type(value) is dict and set(value) == fields
          and value["record_type"] == "required_gate_idempotence_loader_public_service_retrieval_v0"
          and value["retrieval_transport"] == "https_certificate_validation_enabled"
          and value["retrieval_metadata_is_independently_authenticated_timestamp"] is False
          and value["retrieval_metadata_is_historical_execution_proof"] is False,
          "rebuild_acceptance_snapshot_fields")
    _need(value["snapshot_started_at_utc"] == SNAPSHOT_STARTED_AT_UTC
          and value["snapshot_completed_at_utc"] == SNAPSHOT_COMPLETED_AT_UTC,
          "rebuild_acceptance_snapshot_time")
    start, end = _utc(SNAPSHOT_STARTED_AT_UTC), _utc(SNAPSHOT_COMPLETED_AT_UTC)
    names = sorted(set(EVIDENCE_MEMBERS) - {"retrieval_manifest_v0.json"})
    rows = value["responses"]
    _need(type(rows) is list and len(rows) == len(names), "rebuild_acceptance_snapshot_roster")
    row_fields = {"filename", "url", "final_url", "http_status", "http_date", "http_content_type",
                  "retrieval_started_at_utc", "observed_at_utc", "size_bytes", "sha256"}
    for name, row in zip(names, rows):
        _need(type(row) is dict and set(row) == row_fields and row["filename"] == name,
              "rebuild_acceptance_snapshot_roster")
        expected = EVIDENCE_MEMBERS[name]
        _need(row["url"] == row["final_url"] == expected["url"]
              and type(row["http_status"]) is int and row["http_status"] == 200
              and type(row["size_bytes"]) is int and row["size_bytes"] == expected["size_bytes"]
              and row["sha256"] == expected["sha256"]
              and type(row["http_date"]) is str and 0 < len(row["http_date"]) <= 64
              and type(row["http_content_type"]) is str and 0 < len(row["http_content_type"]) <= 64,
              "rebuild_acceptance_snapshot_response")
        _need(start <= _utc(row["retrieval_started_at_utc"]) <= _utc(row["observed_at_utc"]) <= end,
              "rebuild_acceptance_snapshot_time")
    return value


def _one_line(lines, prefix, code):
    selected = [(index, line) for index, line in enumerate(lines) if line.startswith(prefix)]
    _need(len(selected) == 1, code)
    return selected[0]


def _parse_rebuild_log(log_bytes, *, buildinfo_bytes, source_inputs):
    """Parse bounded source observations, without granting provenance authority.

    This pure parser intentionally does not require the fixed log digest so its
    grammar and cross-input checks can be tested independently.  Production
    admission uses derive_public_service_facts, which first binds every carrier.
    No statement below converts unsigned log text into signed evidence.
    """
    _need(type(log_bytes) is bytes and 0 < len(log_bytes) <= LOG_BYTES_MAX,
          "rebuild_acceptance_log_size")
    _input_extents(buildinfo_bytes, source_inputs)
    _need(log_bytes.endswith(LOG_TRUNCATION_MARKER)
          and log_bytes.count(b"TRUNCATED DUE TO SIZE LIMIT:") == 1,
          "rebuild_acceptance_log_truncation_marker")
    body = log_bytes[:-len(LOG_TRUNCATION_MARKER)]
    _need(len(body) == LOG_TRUNCATED_AT, "rebuild_acceptance_log_truncation_extent")
    _need(b"\x00" not in body, "rebuild_acceptance_log_nul")
    # Bound list allocation before splitting an untrusted 20 MiB prefix.
    _need(body.count(b"\n") < LOG_LINES_MAX, "rebuild_acceptance_log_complexity")
    try:
        body.decode("utf-8")
    except UnicodeError as exc:
        raise AcceptanceEvidenceError("rebuild_acceptance_log_encoding") from exc
    lines = body.split(b"\n")
    _need(len(lines) <= LOG_LINES_MAX and max(map(len, lines)) <= LOG_LINE_BYTES_MAX,
          "rebuild_acceptance_log_complexity")
    joined = _input_facts(buildinfo_bytes, source_inputs)
    preparing, line = _one_line(lines, b"Preparing download of sources for ",
                                "rebuild_acceptance_log_input")
    input_path = INPUT_DIR + "/" + BUILDINFO_NAME
    dsc_path = INPUT_DIR + "/" + DSC_NAME
    _need(line == ("Preparing download of sources for " + input_path).encode()
          and lines[preparing + 1:preparing + 4]
          == [b"Source: glibc", b"Version: 2.41-12+deb13u4", b"rebuilderd-worker node: osuosl44-amd64"],
          "rebuild_acceptance_log_identity")
    # The log repeats identity fields in sbuild metadata and the displayed dsc.
    _need([line for line in lines if line.startswith(b"Source:")]
          == [b"Source: glibc"] * 2
          and [line for line in lines if line.startswith(b"Version:")]
          == [b"Version: 2.41-12+deb13u4"] * 3,
          "rebuild_acceptance_log_identity")
    uri_rows = [(index, line) for index, line in enumerate(lines) if line.startswith(b"'https:")]
    _need(len(uri_rows) == 3, "rebuild_acceptance_log_source_roster")
    downloads, source_positions = [], []
    seen = set()
    for index, line in uri_rows:
        match = re.fullmatch(rb"'([^'\n]+)' ([^ ]+) ([0-9]{1,9}) SHA256:([0-9a-f]{64})", line)
        _need(match is not None, "rebuild_acceptance_log_source_row")
        url, name, size, digest = (part.decode("ascii") for part in match.groups())
        _need(name in SOURCE_INPUT_BINDINGS and name not in seen,
              "rebuild_acceptance_log_source_roster")
        seen.add(name)
        expected = SOURCE_INPUT_BINDINGS[name]
        _need(url == SOURCE_URLS[name] and int(size) == expected["size_bytes"]
              and digest == hashlib.sha256(source_inputs[name]).hexdigest(),
              "rebuild_acceptance_log_source_join")
        downloads.append({"filename": name, "url": url, "size_bytes": int(size),
                          "sha256": digest, "line": index + 1})
        source_positions.append(index)
    _need(seen == set(SOURCE_INPUT_BINDINGS), "rebuild_acceptance_log_source_roster")
    checksum_rows = [(index, line) for index, line in enumerate(lines)
                     if re.match(rb"^[0-9a-f]{64}  ", line)]
    _need(len(checksum_rows) == 3, "rebuild_acceptance_log_checksum_roster")
    checksums, checksum_positions = [], []
    seen = set()
    for index, line in checksum_rows:
        match = re.fullmatch(rb"([0-9a-f]{64})  ([^ ]+)", line)
        _need(match is not None, "rebuild_acceptance_log_checksum_row")
        digest, name = (part.decode("ascii") for part in match.groups())
        _need(name in SOURCE_INPUT_BINDINGS and name not in seen,
              "rebuild_acceptance_log_checksum_roster")
        seen.add(name)
        _need(digest == hashlib.sha256(source_inputs[name]).hexdigest(),
              "rebuild_acceptance_log_checksum_join")
        checksums.append({"filename": name, "sha256": digest, "line": index + 1})
        checksum_positions.append(index)
    command_index, command = _one_line(lines, b"+ nice /usr/bin/debrebuild ",
                                      "rebuild_acceptance_log_debrebuild")
    expected_command = ("+ nice /usr/bin/debrebuild --buildresult=" + WORK_ROOT
                        + "/out --builder=sbuild+unshare --cache=/srv/rebuilderd/cache -- " + input_path)
    _need(command == expected_command.encode(), "rebuild_acceptance_log_debrebuild")
    sbuild_index, sbuild = _one_line(lines, b"env --chdir=", "rebuild_acceptance_log_sbuild")
    # Parse the displayed command as data: never invoke a shell or the builder.
    tokens = sbuild.decode("ascii").split(" ")
    expected_tokens = [
        "env", "--chdir=" + WORK_ROOT + "/out", "DEB_BUILD_OPTIONS=parallel=6",
        "LANG=C.UTF-8", "LC_COLLATE=C.UTF-8", "LC_CTYPE=C.UTF-8", "SOURCE_DATE_EPOCH=1782769072",
        "SBUILD_CONFIG=/srv/rebuilderd/tmp/debrebuildp1Evni/debrebuild.sbuildrc.JaXdY4X8Efxt",
        "sbuild", "--build=amd64", "--host=amd64", "--arch-any", "--no-arch-all",
        "--chroot=/srv/rebuilderd/tmp/debrebuildp1Evni/debrebuild.tar.i0b1qMRi_nl5",
        "--chroot-mode=unshare", "--dist=unstable", "--no-run-lintian", "--no-run-piuparts",
        "--no-run-autopkgtest", "--no-apt-update", "--no-apt-upgrade", "--no-apt-distupgrade",
        "--no-source", "--verbose", "--nolog", "--bd-uninstallable-explainer=",
        "--build-path=/build/reproducible-path", "--dsc-dir=glibc-2.41", dsc_path,
    ]
    _need(tokens == expected_tokens,
          "rebuild_acceptance_log_sbuild")
    extract_index, extract = _one_line(lines, b"dpkg-source: info: extracting ",
                                      "rebuild_acceptance_log_extract")
    _need(extract == b"dpkg-source: info: extracting glibc in /build/reproducible-path/glibc-2.41"
          and lines[extract_index + 1:extract_index + 3] == [
              b"dpkg-source: info: unpacking glibc_2.41.orig.tar.xz",
              b"dpkg-source: info: unpacking glibc_2.41-12+deb13u4.debian.tar.xz"]
          and sum(line.startswith(b"dpkg-source: info: unpacking ") for line in lines) == 2,
          "rebuild_acceptance_log_extract")
    _need(preparing < min(source_positions) <= max(source_positions) < min(checksum_positions)
          <= max(checksum_positions) < command_index < sbuild_index < extract_index,
          "rebuild_acceptance_log_order")
    buildinfo_warning = (input_path + " contains a GPG signature which has NOT been validated").encode()
    dsc_warning = ("dpkg-source: warning: cannot verify inline signature for ./" + DSC_NAME
                   + ": no acceptable signature found").encode()
    _need(lines.count(buildinfo_warning) == 1 and lines.count(dsc_warning) == 1,
          "rebuild_acceptance_log_signature_warning")
    _need(not any(b"Finished running debrebuild" in line for line in lines),
          "rebuild_acceptance_log_completion_claim")
    return {
        "carrier": _binding(log_bytes), "unsigned": True, "is_complete": False,
        "truncated_prefix_bytes": len(body), "truncation_marker": LOG_TRUNCATION_MARKER.decode("ascii"),
        "source_name": SOURCE_NAME, "source_version": SOURCE_VERSION,
        "worker_name_claimed_by_unsigned_log": "osuosl44-amd64",
        "buildinfo_input_path": input_path, "dsc_input_path": dsc_path,
        "source_download_rows": sorted(downloads, key=lambda row: row["filename"]),
        "source_checksum_rows": sorted(checksums, key=lambda row: row["filename"]),
        "debrebuild_command": command.decode("ascii"), "debrebuild_command_line": command_index + 1,
        "sbuild_command": sbuild.decode("ascii"), "sbuild_command_line": sbuild_index + 1,
        "source_extract_line": extract_index + 1,
        "source_unpack_filenames": ["glibc_2.41.orig.tar.xz", "glibc_2.41-12+deb13u4.debian.tar.xz"],
        "source_resolution_order_verified": True, "source_raw_bytes_joined": True,
        "buildinfo_unvalidated_signature_warning_observed": True,
        "dsc_unvalidated_signature_warning_observed": True,
        "build_completion_observed_in_log": False, **joined,
    }


def parse_rebuild_log(log_bytes, *, buildinfo_bytes, source_inputs):
    """Expose the bounded parser with stable rejection codes for malformed data."""
    try:
        return _parse_rebuild_log(log_bytes, buildinfo_bytes=buildinfo_bytes,
                                  source_inputs=source_inputs)
    except AcceptanceEvidenceError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, OverflowError, RecursionError) as exc:
        raise AcceptanceEvidenceError("rebuild_acceptance_log_invalid") from exc


def derive_public_service_facts(*, archive_bytes, buildinfo_bytes, source_inputs):
    """Freshly join exact public snapshot bytes to the supplied original bytes."""
    preflight_public_service_inputs(archive_bytes=archive_bytes, buildinfo_bytes=buildinfo_bytes,
                                    source_inputs=source_inputs)
    try:
        files = read_public_service_evidence(archive_bytes)
        snapshot = _snapshot(files["retrieval_manifest_v0.json"])
        metadata = _json(files["rebuild_269686.json"])
        # JSON comparison preserves distinctions such as integer 0 versus false.
        _need(json.dumps(metadata, sort_keys=True) == json.dumps(SERVICE_METADATA, sort_keys=True),
              "rebuild_acceptance_service_metadata")
        log = parse_rebuild_log(files["rebuild_269686.log"], buildinfo_bytes=buildinfo_bytes,
                                source_inputs=source_inputs)
        implementation_names = ("rebuilder-debian.sh", "rebuilderd_worker_rebuild.rs",
                                "rebuilderd_daemon_attestation.rs", "rebuilderd_daemon_build.rs",
                                "rebuilderd_daemon_meta.rs", "debrebuild.pl", "rebuilderd_LICENSE")
        return {
            "record_type": "required_gate_idempotence_loader_public_service_facts_v0",
            "profile": PROFILE, "archive": _binding(archive_bytes),
            "members": copy.deepcopy(EVIDENCE_MEMBERS), "snapshot": snapshot,
            "service_metadata": metadata, "log": log,
            "buildinfo": copy.deepcopy(log["buildinfo"]),
            "source_inputs": copy.deepcopy(log["source_inputs"]),
            "fresh_prior_carrier_bindings": {name: _binding(files[name]) for name in PRIOR_CARRIER_NAMES},
            "reviewed_implementation": {
                "rebuilderd_commit": REBUILDERD_COMMIT, "devscripts_version": DEVSCRIPTS_VERSION,
                "members": {name: copy.deepcopy(EVIDENCE_MEMBERS[name]) for name in implementation_names},
                "purpose": "preserved_public_implementation_for_explicit_policy_review",
                "deployed_code_identity_authenticated": False,
                "source_code_executed_by_this_helper": False,
            },
            "boundary": copy.deepcopy(BOUNDARY),
        }
    except AcceptanceEvidenceError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError, OverflowError, RecursionError) as exc:
        raise AcceptanceEvidenceError("rebuild_acceptance_public_evidence_invalid") from exc
