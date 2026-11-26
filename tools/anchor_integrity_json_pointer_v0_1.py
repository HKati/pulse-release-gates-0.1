#!/usr/bin/env python3
"""Bounded, source-span-preserving JSON Pointer projection for Anchor WP2B.

RFC 6901 resolves a value; it does not specify that value's digest bytes.
This explicit application profile hashes the original JSON value token for
an evidence locator and decoded UTF-8 string content for a claim locator.
No numeric conversion, serialization or Unicode normalization is performed.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

PROFILE = "rfc6901_source_spans_v1"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_DEPTH = 64
MAX_NODES = 100000
MAX_ITEMS = 4096
MAX_POINTER_BYTES = 4096
MAX_POINTER_TOKENS = 64
_NUMBER = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_STRING_SPECIAL = re.compile(rb'["\\\x00-\x1f]')
_ARRAY_INDEX = re.compile(r"(?:0|[1-9][0-9]*)\Z")
_BAD_ESCAPE = re.compile(r"~(?![01])")
_WHITESPACE = b" \t\r\n"


class ProjectionError(Exception):
    """Stable code only; never quote artifact-controlled content."""
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _Node:
    __slots__ = ("start", "end", "kind", "value")

    def __init__(self, start: int, end: int, kind: str, value: Any = None) -> None:
        self.start, self.end, self.kind, self.value = start, end, kind, value


class Document:
    """Validate a complete UTF-8 document and retain exact value byte spans.

    Duplicate decoded object keys and unpaired surrogates are rejected even
    outside the selected path. JSON numbers remain lexemes: large exponents
    do not pass through a binary float. File, nesting, node and member counts
    are bounded. This parser never reads files or accesses a network.
    """
    def __init__(self, data: bytes) -> None:
        if not isinstance(data, bytes):
            raise ProjectionError("json_pointer_source_type")
        if len(data) > MAX_FILE_BYTES:
            raise ProjectionError("json_pointer_file_limit")
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise ProjectionError("json_pointer_source_not_utf8") from exc
        if data.startswith(b"\xef\xbb\xbf"):
            raise ProjectionError("json_pointer_bom_not_allowed")
        self.data = data
        self.pos = 0
        self.nodes = 0
        try:
            self.root = self._value(0)
            self._space()
            if self.pos != len(data):
                raise ProjectionError("json_pointer_invalid_json")
        except RecursionError as exc:
            raise ProjectionError("json_pointer_complexity_limit") from exc
        self.source_sha256 = hashlib.sha256(data).hexdigest()

    def _space(self) -> None:
        while self.pos < len(self.data) and self.data[self.pos] in _WHITESPACE:
            self.pos += 1

    def _tick(self, depth: int) -> None:
        self.nodes += 1
        if depth > MAX_DEPTH or self.nodes > MAX_NODES:
            raise ProjectionError("json_pointer_complexity_limit")

    def _string(self) -> _Node:
        start = self.pos
        self.pos += 1
        while self.pos < len(self.data):
            match = _STRING_SPECIAL.search(self.data, self.pos)
            if match is None:
                break
            index = match.start()
            char = self.data[index]
            if char == 34:  # closing quote; escaped quotes were skipped below
                self.pos = index + 1
                try:
                    value = json.loads(self.data[start:self.pos].decode("utf-8"))
                    value.encode("utf-8", errors="strict")
                except (ValueError, UnicodeError) as exc:
                    raise ProjectionError("json_pointer_invalid_string") from exc
                return _Node(start, self.pos, "string", value)
            if char < 32:
                raise ProjectionError("json_pointer_invalid_string")
            # Skip the escape introducer and the next byte. json.loads validates
            # the complete string's escapes and surrogate pairs before acceptance.
            self.pos = index + 2
        raise ProjectionError("json_pointer_invalid_string")

    def _value(self, depth: int) -> _Node:
        self._space()
        self._tick(depth)
        start = self.pos
        if start >= len(self.data):
            raise ProjectionError("json_pointer_invalid_json")
        char = self.data[start]
        if char == 34:
            return self._string()
        if char == 123:  # object
            self.pos += 1
            members: dict[str, _Node] = {}
            self._space()
            if self.data[self.pos:self.pos + 1] == b"}":
                self.pos += 1
                return _Node(start, self.pos, "object", members)
            while True:
                self._space()
                if self.data[self.pos:self.pos + 1] != b'"':
                    raise ProjectionError("json_pointer_invalid_json")
                self._tick(depth + 1)  # count decoded keys as well as values
                key = self._string().value
                if key in members:
                    raise ProjectionError("json_pointer_duplicate_key")
                if len(members) >= MAX_ITEMS:
                    raise ProjectionError("json_pointer_item_limit")
                self._space()
                if self.data[self.pos:self.pos + 1] != b":":
                    raise ProjectionError("json_pointer_invalid_json")
                self.pos += 1
                members[key] = self._value(depth + 1)
                self._space()
                delimiter = self.data[self.pos:self.pos + 1]
                self.pos += 1
                if delimiter == b"}":
                    return _Node(start, self.pos, "object", members)
                if delimiter != b",":
                    raise ProjectionError("json_pointer_invalid_json")
        if char == 91:  # array
            self.pos += 1
            members_list: list[_Node] = []
            self._space()
            if self.data[self.pos:self.pos + 1] == b"]":
                self.pos += 1
                return _Node(start, self.pos, "array", members_list)
            while True:
                if len(members_list) >= MAX_ITEMS:
                    raise ProjectionError("json_pointer_item_limit")
                members_list.append(self._value(depth + 1))
                self._space()
                delimiter = self.data[self.pos:self.pos + 1]
                self.pos += 1
                if delimiter == b"]":
                    return _Node(start, self.pos, "array", members_list)
                if delimiter != b",":
                    raise ProjectionError("json_pointer_invalid_json")
        for literal, kind in ((b"true", "boolean"), (b"false", "boolean"), (b"null", "null")):
            if self.data.startswith(literal, start):
                self.pos += len(literal)
                return _Node(start, self.pos, kind)
        number = _NUMBER.match(self.data, start)
        if number is None:
            raise ProjectionError("json_pointer_invalid_json")
        self.pos = number.end()
        return _Node(start, self.pos, "number")

    def _resolve(self, pointer: str) -> _Node:
        if not isinstance(pointer, str):
            raise ProjectionError("json_pointer_type")
        try:
            raw_pointer = pointer.encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise ProjectionError("json_pointer_invalid_unicode") from exc
        if len(raw_pointer) > MAX_POINTER_BYTES:
            raise ProjectionError("json_pointer_length_limit")
        # The utility understands the RFC root pointer. Existing WP1 packet
        # schemas admit only pointers beginning with '/', and are not relaxed.
        if pointer == "":
            return self.root
        if not pointer.startswith("/") or _BAD_ESCAPE.search(pointer):
            raise ProjectionError("json_pointer_syntax")
        tokens = pointer[1:].split("/")
        if len(tokens) > MAX_POINTER_TOKENS:
            raise ProjectionError("json_pointer_token_limit")
        node = self.root
        for raw in tokens:
            token = raw.replace("~1", "/").replace("~0", "~")
            if node.kind == "object":
                if token not in node.value:
                    raise ProjectionError("json_pointer_member_missing")
                node = node.value[token]
            elif node.kind == "array":
                if _ARRAY_INDEX.fullmatch(token) is None:
                    raise ProjectionError("json_pointer_array_index")
                # Bound before int conversion, including extremely long digits.
                upper = str(len(node.value))
                if len(token) > len(upper) or (len(token) == len(upper) and token >= upper):
                    raise ProjectionError("json_pointer_index_out_of_bounds")
                index = int(token)
                if index >= len(node.value):
                    raise ProjectionError("json_pointer_index_out_of_bounds")
                node = node.value[index]
            else:
                raise ProjectionError("json_pointer_scalar_traversal")
        return node

    def project(self, pointer: str, purpose: str) -> tuple[bytes, dict[str, Any]]:
        if purpose not in ("claim", "evidence"):
            raise ProjectionError("json_pointer_projection_purpose")
        node = self._resolve(pointer)
        original = self.data[node.start:node.end]
        if purpose == "claim":
            if node.kind != "string":
                raise ProjectionError("json_pointer_claim_requires_string")
            selected = node.value.encode("utf-8")
            projection = "decoded_string_utf8"
        else:
            selected = original
            projection = "source_value_bytes"
        receipt = {
            "pointer": pointer, "purpose": purpose, "projection": projection,
            "source_sha256": self.source_sha256,
            "start_byte": node.start, "end_byte": node.end,
            "selected_value_type": node.kind,
            "source_slice_sha256": hashlib.sha256(original).hexdigest(),
            "projected_sha256": hashlib.sha256(selected).hexdigest(),
        }
        return selected, receipt
