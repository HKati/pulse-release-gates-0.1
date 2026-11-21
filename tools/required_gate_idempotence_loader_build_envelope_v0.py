"""Bounded structural extraction of the selected original build envelopes.

This is deliberately not an OpenPGP verifier.  There is no public key, RSA
operation, external process, or signer authorization here.  CRC24 detects armor
damage; a well-formed signature packet and its issuer fields do not authenticate
the returned cleartext candidate.  The caller separately pins complete original
carrier bytes and validates the candidate's build-record relationships.

The selected profile follows RFC 9580 sections 3.2, 4.2, 5.2.3, 6, and 7.  It
accepts printable ASCII and LF, one SHA512 cleartext header, no signature armor
headers, and one version-4 RSA/SHA512 canonical-text signature packet.  Cleartext
with trailing spaces is outside this profile because OpenPGP ignores that
whitespace when signing.  The separator LF before the signature is removed;
dash escaping is then reversed exactly once at each line's beginning.
"""
from __future__ import annotations

import base64
import binascii
import datetime as dt
import hashlib
import re


CARRIER_LIMIT = 64 * 1024
PAYLOAD_LIMIT = 60 * 1024
LINE_LIMIT = 4096
LINE_COUNT_LIMIT = 4096
ARMOR_LIMIT = 4096
ARMOR_LINE_LIMIT = 76
ARMOR_LINE_COUNT_LIMIT = 64
SIGNATURE_PACKET_LIMIT = 2048
SUBPACKET_AREA_LIMIT = 512
RSA_MPI_BITS_LIMIT = 8192

_CLEAR_HEADER = b"-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\n\n"
_SIGNATURE_SEPARATOR = b"\n-----BEGIN PGP SIGNATURE-----\n\n"
_SIGNATURE_END = b"-----END PGP SIGNATURE-----\n"
_RADIX64 = re.compile(rb"[A-Za-z0-9+/]+={0,2}\Z")
_CRC64 = re.compile(rb"=[A-Za-z0-9+/]{4}\Z")

BOUNDARY = {
    "signature_verified": False,
    "payload_authenticated": False,
    "builder_authority_verified": False,
    "authenticated_build_provenance": False,
    "source_build_gate_satisfied": False,
}

POLICY = {
    "format": "openpgp_clearsigned_structural_profile_v0",
    "claim_scope": "structural_metadata_only",
    "character_profile": "printable_ascii_and_lf",
    "cleartext_header": "single_Hash_SHA512",
    "signature_armor_headers": "none",
    "cleartext_trailing_spaces": "rejected",
    "payload_extraction": "remove_separator_lf_then_reverse_dash_escape_once",
    "signature_profile": {
        "packet_tag": 2, "signature_version": 4, "signature_class": "01",
        "public_key_algorithm": 1, "hash_algorithm": 10,
        "hashed_subpacket_types": [2, 33], "unhashed_subpacket_types": [16],
        "critical_subpackets": "rejected",
        "issuer_fingerprint_version": 4, "issuer_fingerprint_size_bytes": 20,
        "rsa_mpi": "one_nonzero_canonical_bounded_integer",
        "digest_prefix": "stored_metadata_only",
        "primary_fingerprint": "unknown",
    },
    "limits": {
        "carrier_bytes": CARRIER_LIMIT, "payload_bytes": PAYLOAD_LIMIT,
        "line_bytes": LINE_LIMIT, "line_count": LINE_COUNT_LIMIT,
        "armor_bytes": ARMOR_LIMIT, "armor_line_bytes": ARMOR_LINE_LIMIT,
        "armor_line_count": ARMOR_LINE_COUNT_LIMIT,
        "signature_packet_bytes": SIGNATURE_PACKET_LIMIT,
        "subpacket_area_bytes": SUBPACKET_AREA_LIMIT,
        "rsa_mpi_bits": RSA_MPI_BITS_LIMIT,
    },
    "boundary": dict(BOUNDARY),
}


class BuildEnvelopeError(ValueError):
    """Stable rejection code without embedding inspected evidence text."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _need(condition, code):
    if not condition:
        raise BuildEnvelopeError("build_envelope_" + code)


def _binding(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _crc24(raw):
    value = 0xB704CE
    for octet in raw:
        value ^= octet << 16
        for _ in range(8):
            value <<= 1
            if value & 0x1000000:
                value ^= 0x1864CFB
    return (value & 0xFFFFFF).to_bytes(3, "big")


def _decode_armor(armor):
    _need(0 < len(armor) <= ARMOR_LIMIT, "armor_size_limit")
    _need(armor.endswith(_SIGNATURE_END), "armor_end_invalid")
    encoded = armor[:-len(_SIGNATURE_END)]
    _need(encoded.endswith(b"\n"), "armor_layout_invalid")
    lines = encoded[:-1].split(b"\n")
    _need(2 <= len(lines) <= ARMOR_LINE_COUNT_LIMIT, "armor_line_count_invalid")
    _need(_CRC64.fullmatch(lines[-1]) is not None, "armor_crc_invalid")
    data_lines = lines[:-1]
    _need(all(0 < len(line) <= ARMOR_LINE_LIMIT and _RADIX64.fullmatch(line)
              is not None for line in data_lines), "armor_base64_invalid")
    encoded_data = b"".join(data_lines)
    _need(len(encoded_data) <= ((SIGNATURE_PACKET_LIMIT + 2) // 3) * 4,
          "signature_packet_size_limit")
    try:
        packet = base64.b64decode(encoded_data, validate=True)
        crc = base64.b64decode(lines[-1][1:], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BuildEnvelopeError("build_envelope_armor_base64_invalid") from exc
    _need(0 < len(packet) <= SIGNATURE_PACKET_LIMIT, "signature_packet_size_limit")
    _need(base64.b64encode(packet) == encoded_data, "armor_base64_noncanonical")
    _need(len(crc) == 3 and _crc24(packet) == crc, "armor_crc_mismatch")
    return packet


def _packet_body(packet):
    _need(len(packet) >= 2 and packet[0] & 0x80, "packet_header_invalid")
    header = packet[0]
    offset = 1
    if header & 0x40:
        _need(header & 0x3F == 2, "packet_tag_unsupported")
        first = packet[offset]
        offset += 1
        if first < 192:
            length = first
        elif first < 224:
            _need(offset < len(packet), "packet_length_truncated")
            length = ((first - 192) << 8) + packet[offset] + 192
            offset += 1
        elif first == 255:
            _need(offset + 4 <= len(packet), "packet_length_truncated")
            length = int.from_bytes(packet[offset:offset + 4], "big")
            offset += 4
        else:
            raise BuildEnvelopeError("build_envelope_partial_packet_unsupported")
        header_format = "current_definite"
    else:
        _need((header >> 2) & 0x0F == 2, "packet_tag_unsupported")
        kind = header & 3
        _need(kind != 3, "indeterminate_packet_unsupported")
        width = (1, 2, 4)[kind]
        _need(offset + width <= len(packet), "packet_length_truncated")
        length = int.from_bytes(packet[offset:offset + width], "big")
        offset += width
        header_format = "legacy_definite"
    _need(0 < length <= SIGNATURE_PACKET_LIMIT, "packet_body_size_limit")
    _need(offset + length == len(packet), "packet_extent_invalid")
    return packet[offset:], header_format


def _subpackets(raw, expected, location):
    _need(0 < len(raw) <= SUBPACKET_AREA_LIMIT, "subpacket_area_size_limit")
    result = {}
    order = []
    offset = 0
    while offset < len(raw):
        first = raw[offset]
        offset += 1
        if first < 192:
            length = first
        elif first < 255:
            _need(offset < len(raw), "subpacket_length_truncated")
            length = ((first - 192) << 8) + raw[offset] + 192
            offset += 1
        else:
            _need(offset + 4 <= len(raw), "subpacket_length_truncated")
            length = int.from_bytes(raw[offset:offset + 4], "big")
            offset += 4
        _need(0 < length <= SUBPACKET_AREA_LIMIT and offset + length <= len(raw),
              "subpacket_extent_invalid")
        kind = raw[offset]
        _need(kind & 0x80 == 0, "critical_subpacket_unsupported")
        _need(kind in expected, location + "_subpacket_unsupported")
        _need(kind not in result, "subpacket_duplicate")
        result[kind] = raw[offset + 1:offset + length]
        order.append(kind)
        offset += length
    _need(set(result) == set(expected), location + "_subpacket_roster_invalid")
    return result, order


def _signature_facts(packet):
    body, header_format = _packet_body(packet)
    _need(len(body) >= 10, "signature_truncated")
    _need(body[:4] == bytes((4, 1, 1, 10)), "signature_profile_unsupported")
    hashed_size = int.from_bytes(body[4:6], "big")
    _need(0 < hashed_size <= SUBPACKET_AREA_LIMIT, "subpacket_area_size_limit")
    hashed_end = 6 + hashed_size
    _need(hashed_end + 2 <= len(body), "hashed_area_truncated")
    unhashed_size = int.from_bytes(body[hashed_end:hashed_end + 2], "big")
    _need(0 < unhashed_size <= SUBPACKET_AREA_LIMIT, "subpacket_area_size_limit")
    unhashed_end = hashed_end + 2 + unhashed_size
    _need(unhashed_end + 4 <= len(body), "unhashed_area_truncated")
    hashed, hashed_order = _subpackets(body[6:hashed_end], {2, 33}, "hashed")
    unhashed, unhashed_order = _subpackets(
        body[hashed_end + 2:unhashed_end], {16}, "unhashed")
    _need(len(hashed[33]) == 21 and hashed[33][0] == 4, "issuer_fingerprint_invalid")
    fingerprint = hashed[33][1:]
    _need(len(unhashed[16]) == 8 and unhashed[16] == fingerprint[-8:],
          "issuer_key_id_mismatch")
    _need(len(hashed[2]) == 4, "signature_time_invalid")
    created = int.from_bytes(hashed[2], "big")
    _need(created > 0, "signature_time_invalid")
    digest_prefix = body[unhashed_end:unhashed_end + 2]
    mpi_bits = int.from_bytes(body[unhashed_end + 2:unhashed_end + 4], "big")
    _need(0 < mpi_bits <= RSA_MPI_BITS_LIMIT, "rsa_mpi_size_limit")
    mpi_size = (mpi_bits + 7) // 8
    mpi_start = unhashed_end + 4
    _need(mpi_start + mpi_size == len(body), "rsa_mpi_extent_invalid")
    mpi = body[mpi_start:]
    _need(mpi[0] != 0 and (len(mpi) - 1) * 8 + mpi[0].bit_length() == mpi_bits,
          "rsa_mpi_noncanonical")
    return {
        "packet_header_format": header_format, "packet_body_size_bytes": len(body),
        "signature_version": 4, "signature_class": "01",
        "public_key_algorithm": 1, "hash_algorithm": 10,
        "claimed_issuer_fingerprint": fingerprint.hex().upper(),
        "claimed_issuer_key_id": unhashed[16].hex().upper(),
        "claimed_signature_created_epoch": created,
        "claimed_signature_created_utc": dt.datetime.fromtimestamp(
            created, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "primary_fingerprint": None,
        "hashed_subpacket_types": hashed_order, "unhashed_subpacket_types": unhashed_order,
        "stored_digest_prefix_hex": digest_prefix.hex(),
        "rsa_signature_mpi_bits": mpi_bits, "rsa_signature_mpi_size_bytes": mpi_size,
    }


def extract_clearsigned_payload(raw):
    """Return an unauthenticated cleartext candidate and structural facts.

    This generic structural profile does not pin an original carrier, issuer,
    timestamp, or build record.  A changed payload or RSA MPI can remain
    structurally valid; complete original-byte binding belongs to the caller.
    All input and internal size bounds are checked before computing any SHA256
    binding.  The stored two-byte digest prefix is not checked or promoted to a
    cryptographic signature verdict.
    """
    _need(type(raw) is bytes and 0 < len(raw) <= CARRIER_LIMIT, "carrier_size_limit")
    _need(raw.count(b"\n") <= LINE_COUNT_LIMIT, "line_count_limit")
    _need(all(octet == 10 or 32 <= octet <= 126 for octet in raw),
          "character_profile_invalid")
    _need(all(len(line) <= LINE_LIMIT for line in raw.split(b"\n")), "line_size_limit")
    _need(raw.startswith(_CLEAR_HEADER), "cleartext_header_invalid")
    content = raw[len(_CLEAR_HEADER):]
    _need(content.count(_SIGNATURE_SEPARATOR) == 1, "signature_separator_invalid")
    escaped, armor = content.split(_SIGNATURE_SEPARATOR, 1)
    lines = []
    dash_count = 0
    for line in escaped.split(b"\n"):
        if line.startswith(b"-"):
            _need(line.startswith(b"- "), "dash_escape_invalid")
            line = line[2:]
            dash_count += 1
        _need(not line.endswith(b" "), "cleartext_trailing_space")
        lines.append(line)
    payload = b"\n".join(lines)
    _need(0 < len(payload) <= PAYLOAD_LIMIT, "payload_size_limit")
    packet = _decode_armor(armor)
    signature = _signature_facts(packet)
    # Bind only after every carrier, line, payload, armor, packet and MPI bound
    # has been checked.  These digests identify bytes, not their authenticity.
    signature["binding"] = _binding(packet)
    facts = {
        "format": "openpgp_clearsigned_structural_profile_v0",
        "claim_scope": "structural_metadata_only",
        "carrier": _binding(raw), "payload": _binding(payload),
        "signature_packet": signature, "dash_unescaped_line_count": dash_count,
        "framing_newline_removed": True, "crc24_checked": True,
        **BOUNDARY,
    }
    return payload, facts
