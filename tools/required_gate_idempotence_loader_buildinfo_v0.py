"""Check declared relationships in two original Debian build-record payloads.

Inputs are cleartext candidates, not authenticated statements.  This module
does not verify an OpenPGP signature, authorize an issuer, run a build, or
execute a target.  Only two complete binary package payloads are supplied and
checked; the other eighteen outputs are cross-record declarations.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import hashlib
import re


PROFILE = "debian_glibc_2_41_12_deb13u4_amd64_build_records_v0"
VERSION = "2.41-12+deb13u4"
BUILDINFO_NAME = "glibc_" + VERSION + "_amd64-buildd.buildinfo"
BUILDINFO_ENVELOPE = {
    "size_bytes": 15502,
    "sha256": "5af18d1a381adb80a101b714b57c7822e5f0442f68e148df26b0dbcc4a1ca1e9",
}
INPUT_BINDINGS = {
    "libc6_2.41-12+deb13u4_amd64.deb": {
        "size_bytes": 2846580,
        "sha256": "967aa62605721081c3eb2a17650611a792aa802d76a6511d1840242623d204c9"},
    "libc6-dbg_2.41-12+deb13u4_amd64.deb": {
        "size_bytes": 7373052,
        "sha256": "0123a767a462c59d75e1bd56c4a0f7192c389f600e4743e807d3d33c679dbcf7"},
    "Sources.xz": {
        "size_bytes": 10540436,
        "sha256": "6002f81f463a2d976d84b34170367cc16da2d60bd0ba9ab9d868d6e1c1a935d9"},
    "glibc_2.41-12+deb13u4.dsc": {
        "size_bytes": 7576,
        "sha256": "0915324aa646bb99abfaa9aa6ecb734b30babd28454a3e51f3152912370fbd3e"},
    "glibc_2.41.orig.tar.xz": {
        "size_bytes": 20323540,
        "sha256": "f24aa441021121a79266f0d75242706cab8843a47901fefe74527491807f1998"},
    "glibc_2.41-12+deb13u4.debian.tar.xz": {
        "size_bytes": 499524,
        "sha256": "dda4153511bfd543502d18e5bc9323110996fe9c531f14ae3fad6eb17f027c7d"},
}
OUTPUT_PACKAGES = (
    "libc-bin", "libc-bin-dbgsym", "libc-dev-bin", "libc-dev-bin-dbgsym",
    "libc-devtools", "libc-devtools-dbgsym", "libc6", "libc6-dbg", "libc6-dev",
    "libc6-dev-dbgsym", "libc6-dev-i386", "libc6-dev-x32", "libc6-i386",
    "libc6-i386-dbgsym", "libc6-udeb", "libc6-x32", "libc6-x32-dbgsym",
    "locales-all", "nscd", "nscd-dbgsym",
)
OUTPUT_FILES = {
    name + "_" + VERSION + "_amd64." + ("udeb" if name == "libc6-udeb" else "deb")
    for name in OUTPUT_PACKAGES
}
SELECTED_PACKAGES = (
    "libc6_2.41-12+deb13u4_amd64.deb",
    "libc6-dbg_2.41-12+deb13u4_amd64.deb",
)
SOURCE_INPUTS = (
    "glibc_2.41-12+deb13u4.dsc", "glibc_2.41.orig.tar.xz",
    "glibc_2.41-12+deb13u4.debian.tar.xz",
)
BUILDINFO_FIELDS = {
    "Format", "Source", "Binary", "Architecture", "Version", "Checksums-Md5",
    "Checksums-Sha1", "Checksums-Sha256", "Build-Origin", "Build-Architecture",
    "Build-Date", "Build-Path", "Installed-Build-Depends", "Environment",
}
CHANGES_FIELDS = {
    "Format", "Date", "Source", "Binary", "Architecture", "Version", "Distribution",
    "Urgency", "Maintainer", "Changed-By", "Description", "Closes", "Changes",
    "Checksums-Sha1", "Checksums-Sha256", "Files",
}
TOOLCHAIN = {"gcc-14": "14.2.0-19", "binutils": "2.44-3", "dpkg-dev": "1.22.22"}
ENVIRONMENT = {
    "DEB_BUILD_OPTIONS": "parallel=6", "LANG": "C.UTF-8",
    "LC_COLLATE": "C.UTF-8", "LC_CTYPE": "C.UTF-8", "SOURCE_DATE_EPOCH": "1782769072",
}
POLICY = {
    "claim_scope": "syntactic_declared_build_record_relationships_only",
    "payload_bytes": 65536, "line_bytes": 4096, "lines": 1024,
    "fields": 32, "installed_dependencies": 512,
    "output_bytes": 64 * 1024 * 1024, "buildinfo_outputs": 20, "changes_outputs": 21,
    "source": "glibc", "version": VERSION, "architecture": "amd64",
    "buildinfo_format": "1.0", "changes_format": "1.8",
    "selected_original_payloads": 2, "unselected_output_payloads": 18,
    "source_input_hashes_directly_attested": False,
    "weak_checksums_are_security_bindings": False,
    "candidate_payloads_are_authenticated": False,
}
BOUNDARY = {
    "signature_verified": False,
    "builder_authority_verified": False,
    "authenticated_build_provenance": False,
    "source_build_gate_satisfied": False,
    "source_input_hashes_directly_attested": False,
    "source_binary_equivalence_verified": False,
    "unselected_output_payloads_verified": False,
    "native_acquisition_performed": False,
    "consumer_resolution_observed": False,
    "original_acquisition_ready": False,
    "metric_pass": None,
    "authority_effect": "none",
}
_FIELD = re.compile(rb"([A-Za-z][A-Za-z0-9-]{0,63}):(?: ([^\n]*))?\Z")
_PACKAGE = r"[a-z0-9][a-z0-9+.-]*"
_DEPENDENCY = re.compile(
    r"(" + _PACKAGE + r"(?::[a-z0-9][a-z0-9-]*)?) \(= ([0-9][A-Za-z0-9.+:~\-]*)\)(,?)\Z")
_ENVIRONMENT = re.compile(r'([A-Z][A-Z0-9_]*)="([A-Za-z0-9_./=:+ -]*)"\Z')
_DATE = re.compile(
    r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun), ([0-9]{2}) "
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"([0-9]{4}) ([0-9]{2}):([0-9]{2}):([0-9]{2}) ([+-])([0-9]{2})([0-9]{2})\Z")


class BuildinfoError(ValueError):
    """Stable rejection code without untrusted payload text."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise BuildinfoError(code)


def _binding(raw):
    return {"size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _checksums(raw):
    return {"size_bytes": len(raw),
            "md5": hashlib.md5(raw, usedforsecurity=False).hexdigest(),
            "sha1": hashlib.sha1(raw, usedforsecurity=False).hexdigest(),
            "sha256": hashlib.sha256(raw).hexdigest()}


def _preflight(buildinfo_payload, changes_payload, buildinfo_envelope, inputs):
    _need(type(inputs) is dict and set(inputs) == set(INPUT_BINDINGS),
          "buildinfo_input_inventory")
    for name, expected in INPUT_BINDINGS.items():
        _need(type(inputs[name]) is bytes and len(inputs[name]) == expected["size_bytes"],
              "buildinfo_input_size")
    for raw in (buildinfo_payload, changes_payload):
        _need(type(raw) is bytes and 0 < len(raw) <= POLICY["payload_bytes"],
              "buildinfo_payload_size")
    _need(type(buildinfo_envelope) is bytes
          and len(buildinfo_envelope) == BUILDINFO_ENVELOPE["size_bytes"],
          "buildinfo_envelope_size")


def _fields(raw, expected):
    _need(raw.endswith(b"\n") and all(byte == 10 or 32 <= byte <= 126 for byte in raw),
          "buildinfo_payload_encoding")
    lines = raw.split(b"\n")
    lines.pop()  # one mandatory final LF
    if lines and lines[-1] == b"":
        lines.pop()  # optional single paragraph terminator
    _need(0 < len(lines) <= POLICY["lines"] and all(lines),
          "buildinfo_single_paragraph")
    result, seen, current = {}, set(), None
    for line in lines:
        _need(len(line) <= POLICY["line_bytes"] and not line.endswith(b" "),
              "buildinfo_line_limit_or_whitespace")
        if line.startswith(b" "):
            _need(current is not None, "buildinfo_orphan_continuation")
            result[current].append(line[1:].decode("ascii"))
            continue
        match = _FIELD.fullmatch(line)
        _need(match is not None, "buildinfo_field_syntax")
        current = match[1].decode("ascii")
        _need(current.lower() not in seen, "buildinfo_duplicate_field")
        seen.add(current.lower())
        result[current] = ["" if match[2] is None else match[2].decode("ascii")]
        _need(len(result) <= POLICY["fields"], "buildinfo_field_limit")
    _need(set(result) == expected, "buildinfo_field_inventory")
    return result


def _one(fields, name):
    values = fields[name]
    _need(len(values) == 1 and bool(values[0]) and values[0] == values[0].strip(),
          "buildinfo_scalar_field")
    return values[0]


def _rows(fields, name, maximum):
    values = fields[name]
    _need(values[0] == "" and 1 <= len(values) - 1 <= maximum
          and all(values[1:]), "buildinfo_multiline_field")
    return values[1:]


def _identity(fields, form):
    _need(_one(fields, "Format") == form and _one(fields, "Source") == "glibc"
          and _one(fields, "Version") == VERSION
          and _one(fields, "Architecture") == "amd64", "buildinfo_identity")
    names = _one(fields, "Binary").split(" ")
    _need(len(names) == len(set(names)) == len(OUTPUT_PACKAGES)
          and set(names) == set(OUTPUT_PACKAGES), "buildinfo_binary_inventory")


def _checksum_rows(fields, name, digest_name, width, expected, *, files=False):
    rows = _rows(fields, name, len(expected))
    _need(len(rows) == len(expected), "buildinfo_checksum_count")
    expression = re.compile(
        r"([0-9a-f]{" + str(width) + r"}) ([1-9][0-9]{0,8}) "
        + (r"([a-z][a-z-]*) (required|optional) " if files else "")
        + r"([A-Za-z0-9+_.-]+)\Z")
    result = {}
    for row in rows:
        match = expression.fullmatch(row)
        _need(match is not None, "buildinfo_checksum_syntax")
        filename = match.groups()[-1]
        size = int(match[2])
        _need(filename in expected and filename not in result, "buildinfo_checksum_inventory")
        _need(size <= POLICY["output_bytes"], "buildinfo_output_size")
        result[filename] = {"size_bytes": size, digest_name: match[1]}
        if files:
            _need(match[3] in {"libs", "debug", "libdevel", "devel", "debian-installer",
                              "localization", "admin"}, "buildinfo_files_section")
            result[filename].update(section=match[3], priority=match[4])
    _need(set(result) == expected, "buildinfo_checksum_inventory")
    return result


def _merge_rosters(fields, *, changes):
    expected = OUTPUT_FILES | {BUILDINFO_NAME} if changes else OUTPUT_FILES
    md5 = _checksum_rows(fields, "Files" if changes else "Checksums-Md5",
                         "md5", 32, expected, files=changes)
    sha1 = _checksum_rows(fields, "Checksums-Sha1", "sha1", 40, expected)
    sha256 = _checksum_rows(fields, "Checksums-Sha256", "sha256", 64, expected)
    result = {}
    for name in sorted(expected):
        _need(md5[name]["size_bytes"] == sha1[name]["size_bytes"] == sha256[name]["size_bytes"],
              "buildinfo_checksum_size_disagreement")
        result[name] = {**md5[name], **sha1[name], **sha256[name]}
    return result


def _date(value):
    match = _DATE.fullmatch(value)
    _need(match is not None, "buildinfo_date_syntax")
    weekday, day, month, year, hour, minute, second, sign, zone_hour, zone_minute = match.groups()
    _need(int(zone_hour) <= 14 and int(zone_minute) < 60
          and (int(zone_hour) != 14 or int(zone_minute) == 0), "buildinfo_date_zone")
    offset = (int(zone_hour) * 60 + int(zone_minute)) * (1 if sign == "+" else -1)
    try:
        selected = datetime(int(year), "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split().index(month) + 1,
                            int(day), int(hour), int(minute), int(second),
                            tzinfo=timezone(timedelta(minutes=offset)))
    except ValueError as exc:
        raise BuildinfoError("buildinfo_date_value") from exc
    _need("Mon Tue Wed Thu Fri Sat Sun".split()[selected.weekday()] == weekday,
          "buildinfo_date_weekday")
    return int(selected.timestamp())


def _dependencies(fields):
    rows = _rows(fields, "Installed-Build-Depends", POLICY["installed_dependencies"])
    result = {}
    for index, row in enumerate(rows):
        match = _DEPENDENCY.fullmatch(row)
        _need(match is not None and len(match[2]) <= 128, "buildinfo_dependency_syntax")
        name, version, comma = match.groups()
        _need(bool(comma) == (index < len(rows) - 1), "buildinfo_dependency_separator")
        _need(name not in result, "buildinfo_dependency_duplicate")
        result[name] = version
    _need(all(result.get(name) == version for name, version in TOOLCHAIN.items()),
          "buildinfo_toolchain")
    return dict(sorted(result.items()))


def _environment(fields):
    rows = _rows(fields, "Environment", 16)
    result = {}
    for row in rows:
        match = _ENVIRONMENT.fullmatch(row)
        _need(match is not None, "buildinfo_environment_syntax")
        name, value = match.groups()
        _need(name not in result, "buildinfo_environment_duplicate")
        result[name] = value
    _need(result == ENVIRONMENT, "buildinfo_environment_profile")
    return dict(sorted(result.items()))


def _upload(fields):
    _need(_one(fields, "Distribution") == "trixie" and _one(fields, "Urgency") == "medium",
          "buildinfo_upload_profile")
    maintainer = _one(fields, "Maintainer")
    changed_by = _one(fields, "Changed-By")
    _need(maintainer == "all / amd64 / i386 Build Daemon (x86-grnet-03) "
          "<buildd_amd64-x86-grnet-03@buildd.debian.org>"
          and changed_by == "Aurelien Jarno <aurel32@debian.org>", "buildinfo_declared_identity")
    descriptions = {}
    for row in _rows(fields, "Description", 20):
        match = re.fullmatch(r"(" + _PACKAGE + r") +\- (.+)", row)
        _need(match is not None and match[1] not in descriptions, "buildinfo_description")
        descriptions[match[1]] = match[2]
    _need(set(descriptions) == {name for name in OUTPUT_PACKAGES if not name.endswith("-dbgsym")},
          "buildinfo_description_inventory")
    closed = _one(fields, "Closes").split(" ")
    _need(all(re.fullmatch(r"[1-9][0-9]{0,8}", value) for value in closed)
          and len(set(closed)) == len(closed)
          and set(closed) == {"1134543", "1134544", "1135405"}, "buildinfo_closes")
    changelog = _rows(fields, "Changes", 64)
    _need(changelog[0] == "glibc (" + VERSION + ") trixie; urgency=medium",
          "buildinfo_changelog_identity")
    return {"date": _one(fields, "Date"), "date_epoch": _date(_one(fields, "Date")),
            "distribution": "trixie", "urgency": "medium", "maintainer": maintainer,
            "changed_by": changed_by, "description": dict(sorted(descriptions.items())),
            "closes": sorted(map(int, closed)),
            "changelog": _binding(("\n".join(changelog) + "\n").encode("ascii"))}


def derive_buildinfo_facts(*, buildinfo_payload, changes_payload, buildinfo_envelope, inputs):
    """Return syntactic declarations and exact selected-payload relationships.

    The separate envelope adapter and wrapper must bind candidate extraction to
    preserved carriers. Neither that binding nor this result authenticates an
    issuer, the declared build process, or the declared source input bytes.
    """
    try:
        _preflight(buildinfo_payload, changes_payload, buildinfo_envelope, inputs)
        build = _fields(buildinfo_payload, BUILDINFO_FIELDS)
        changes = _fields(changes_payload, CHANGES_FIELDS)
        _identity(build, "1.0")
        _identity(changes, "1.8")
        build_rows = _merge_rosters(build, changes=False)
        change_rows = _merge_rosters(changes, changes=True)
        for name, row in build_rows.items():
            _need(all(row[key] == change_rows[name][key]
                      for key in ("size_bytes", "md5", "sha1", "sha256")),
                  "buildinfo_cross_record_output")
        _need(_one(build, "Build-Origin") == "Debian"
              and _one(build, "Build-Architecture") == "amd64"
              and _one(build, "Build-Path") == "/build/reproducible-path/glibc-2.41",
              "buildinfo_build_profile")
        dependencies = _dependencies(build)
        environment = _environment(build)
        build_epoch = _date(_one(build, "Build-Date"))
        upload = _upload(changes)
        _need(build_epoch == 1783791760 and upload["date_epoch"] == 1782769072
              and int(environment["SOURCE_DATE_EPOCH"]) == upload["date_epoch"]
              and upload["date_epoch"] <= build_epoch, "buildinfo_date_relationship")
        bindings = {}
        for name, expected in INPUT_BINDINGS.items():
            bindings[name] = _binding(inputs[name])
            _need(bindings[name] == expected, "buildinfo_input_sha256")
        envelope = _checksums(buildinfo_envelope)
        _need({key: envelope[key] for key in ("size_bytes", "sha256")} == BUILDINFO_ENVELOPE,
              "buildinfo_envelope_sha256")
        _need(all(change_rows[BUILDINFO_NAME][key] == value for key, value in envelope.items()),
              "buildinfo_envelope_row")
        selected = {}
        for name in SELECTED_PACKAGES:
            selected[name] = _checksums(inputs[name])
            _need(build_rows[name] == selected[name], "buildinfo_original_package_row")
        output_rows = [{"name": name, **change_rows[name],
                        "complete_payload_checked": name in selected}
                       for name in sorted(build_rows)]
        return {
            "record_type": "required_gate_idempotence_loader_buildinfo_facts_v0",
            "profile": PROFILE,
            "claim_scope": POLICY["claim_scope"],
            "candidate_payloads": {"buildinfo": _binding(buildinfo_payload),
                                   "changes": _binding(changes_payload)},
            "buildinfo_envelope": dict(BUILDINFO_ENVELOPE),
            "input_bindings": dict(sorted(bindings.items())),
            "source_identity": {"name": "glibc", "version": VERSION, "architecture": "amd64",
                                "binary_only_build_record": True,
                                "direct_source_checksums_present": False},
            "declared_build": {"origin": "Debian", "architecture": "amd64",
                "date": _one(build, "Build-Date"), "date_epoch": build_epoch,
                "path": _one(build, "Build-Path"), "installed_dependencies": dependencies,
                "toolchain": dict(sorted(TOOLCHAIN.items())), "environment": environment},
            "declared_upload": upload,
            "output_rosters": {"buildinfo_count": 20, "changes_count": 21,
                              "outputs": output_rows,
                              "buildinfo_envelope_row": {"name": BUILDINFO_NAME, **change_rows[BUILDINFO_NAME]}},
            "selected_original_packages": dict(sorted(selected.items())),
            "source_input_artifacts": {name: bindings[name] for name in SOURCE_INPUTS},
            "limitations": {
                "payload_origin": "unverified_cleartext_candidates",
                "source_identity_role": "declared_name_version_join_to_separately_pinned_source_artifacts",
                "installed_dependencies_and_environment_are_declared_only": True,
                "weak_checksums_role": "cross_record_consistency_only",
                "unselected_output_payload_count": 18,
                "candidate_to_envelope_extraction_checked_by_this_module": False,
            },
            "boundary": copy.deepcopy(BOUNDARY),
        }
    except BuildinfoError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError) as exc:
        raise BuildinfoError("buildinfo_record_invalid") from exc
