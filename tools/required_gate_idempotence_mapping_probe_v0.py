#!/usr/bin/env python3
"""Exact authored Linux x86-64 cooperative-stop probe; no compiler is invoked.

The sole argument is eight lowercase hexadecimal digits encoding the expected
parent PID.  The fixed instruction stream installs parent-death SIGKILL,
validates argc and that argument, compares getppid(), and stops itself with
kill(getpid(), SIGSTOP).  It exits 124 if unexpectedly continued.  Exit 125
means PR_SET_PDEATHSIG failed, 126 means an invalid argument, and 127 means a
different parent.  This is a POST-EXEC checkpoint, not a ptrace exec event.

The bytes below define the probe.  They are not a claim about an external
compiler or a selected launcher.  One RX load page and an explicit nonexecuting
stack are encoded directly.  There is no interpreter or dynamic segment.
"""
from __future__ import annotations

import struct

BASE_ADDRESS = 0x400000
PAGE_BYTES = 4096
ENTRY_OFFSET = 64 + 2 * 56
PARENT_ARGUMENT = "lowercase_hex8"
EXIT_CONTINUED = 124
EXIT_PDEATH_FAILED = 125
EXIT_ARGUMENT_INVALID = 126
EXIT_PARENT_MISMATCH = 127

# x86-64, little endian.  Offsets below are relative to ENTRY_OFFSET.
CODE = bytes.fromhex(
    # 00: prctl(PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0); failure -> 9d.
    "b89d000000bf01000000be0900000031d24531d24531c04531c90f05"
    "4885c0757c"
    # 21: require argc==2; argv[1]; accumulator r12d=0; eight digits.
    "48833c2402757c488b7424104531e4b908000000"
    # 35: accept only 0..9 or a..f, accumulate uint32, exactly eight.
    "0fb60683f830726783f839760f83f861725d83f866775883e857eb03"
    "83e83041c1e4044109c448ffc6ffc975d3"
    # 62: require NUL, nonzero, signed-positive PID; invalid -> a4.
    "803e00753d4585e4743841f7c400000080752f"
    # 75: getppid(); compare expected PID; mismatch -> ab.
    "b86e0000000f054439e0752a"
    # 81: kill(getpid(), SIGSTOP).  No ptrace, file, network or fork call.
    "b8270000000f0589c7be13000000b83e0000000f05"
    # 96: unexpected continuation -> exit(124); three failures 125..127.
    "bf7c000000eb13bf7d000000eb0cbf7e000000eb05bf7f000000"
    # b0: exit(status); ud2 if the kernel unexpectedly returns.
    "b83c0000000f050f0b"
)


def parent_argument(pid: int) -> str:
    """Encode the observer PID, never caller-provided executable arguments."""
    if type(pid) is not int or not 0 < pid < 2**31:
        raise ValueError("mapping_observer_pid_invalid")
    return format(pid, "08x")


def probe_bytes() -> bytes:
    """Return only the one fixed 4096-byte static ELF for this profile."""
    identity = b"\x7fELF\x02\x01\x01" + bytes(9)
    header = struct.pack(
        "<16sHHIQQQIHHHHHH", identity, 2, 62, 1,
        BASE_ADDRESS + ENTRY_OFFSET, 64, 0, 0, 64, 56, 2, 0, 0, 0,
    )
    load = struct.pack(
        "<IIQQQQQQ", 1, 5, 0, BASE_ADDRESS, BASE_ADDRESS,
        PAGE_BYTES, PAGE_BYTES, PAGE_BYTES,
    )
    stack = struct.pack("<IIQQQQQQ", 0x6474E551, 6, 0, 0, 0, 0, 0, 16)
    return (header + load + stack + CODE).ljust(PAGE_BYTES, b"\0")
