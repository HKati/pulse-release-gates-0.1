#!/usr/bin/env python3
"""Exact authored Linux x86-64 two-stop memory probe; no compiler is invoked.

The sole argument is eight lowercase hexadecimal digits encoding the expected
parent PID.  The fixed instruction stream installs parent-death SIGKILL,
validates argc and that argument, compares getppid(), and stops itself with
kill(getpid(), SIGSTOP).  After one continuation it writes exactly one byte,
0x5a, to the private writable data page at offset 0x100 and stops itself again.
It exits 124 if continued after that second checkpoint.  Exit 125 means
PR_SET_PDEATHSIG failed, 126 means an invalid argument, and 127 means a different
parent.  These are cooperative POST-EXEC checkpoints, not ptrace exec events.

The bytes below define a separate fixed probe.  One RX load page, one RW load
page, and an explicit nonexecuting stack are encoded directly.  The data page
is initially all zero.  There is no interpreter or dynamic segment.  This
authored transition is not a selected launcher, runtime, or model execution.
"""
from __future__ import annotations

import struct

BASE_ADDRESS = 0x400000
PAGE_BYTES = 4096
ENTRY_OFFSET = 64 + 3 * 56
DATA_OFFSET = 4096
MUTATION_OFFSET = 256
MUTATION_BYTE = 0x5A
ELF_BYTES = 8192
PARENT_ARGUMENT = "lowercase_hex8"
EXIT_CONTINUED = 124
EXIT_PDEATH_FAILED = 125
EXIT_ARGUMENT_INVALID = 126
EXIT_PARENT_MISMATCH = 127

# x86-64, little endian.  Code offsets are relative to ENTRY_OFFSET.
# The parent-validation prefix and its failure-handler offsets are fixed.
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
    # 81: first checkpoint: kill(getpid(), SIGSTOP).
    "b8270000000f0589c7be13000000b83e0000000f05"
    # 96: one expected continuation jumps to b9.  Two padding NOPs keep
    #     the original validation branches and failure-handler offsets.
    "e91e0000009090"
    # 9d/a4/ab: failure exits 125/126/127, respectively.
    "bf7d000000eb0cbf7e000000eb05bf7f000000"
    # b0: exit(status); ud2 if the kernel unexpectedly returns.
    "b83c0000000f050f0b"
    # b9: the only data-page write: mov byte ptr [0x401100], 0x5a.
    #     Address = BASE_ADDRESS + DATA_OFFSET + MUTATION_OFFSET.
    "c60425001140005a"
    # c1: second checkpoint: kill(getpid(), SIGSTOP).
    "b8270000000f0589c7be13000000b83e0000000f05"
    # d6: unexpected second continuation -> exit(124); then ud2.
    "bf7c000000b83c0000000f050f0b"
)


def parent_argument(pid: int) -> str:
    """Encode the observer PID, never caller-provided executable arguments."""
    if type(pid) is not int or not 0 < pid < 2**31:
        raise ValueError("memory_observer_pid_invalid")
    return format(pid, "08x")


def probe_bytes() -> bytes:
    """Return only the fixed 8192-byte static ELF for this two-stop profile."""
    identity = b"\x7fELF\x02\x01\x01" + bytes(9)
    header = struct.pack(
        "<16sHHIQQQIHHHHHH", identity, 2, 62, 1,
        BASE_ADDRESS + ENTRY_OFFSET, 64, 0, 0, 64, 56, 3, 0, 0, 0,
    )
    code_load = struct.pack(
        "<IIQQQQQQ", 1, 5, 0, BASE_ADDRESS, BASE_ADDRESS,
        PAGE_BYTES, PAGE_BYTES, PAGE_BYTES,
    )
    data_load = struct.pack(
        "<IIQQQQQQ", 1, 6, DATA_OFFSET,
        BASE_ADDRESS + DATA_OFFSET, BASE_ADDRESS + DATA_OFFSET,
        PAGE_BYTES, PAGE_BYTES, PAGE_BYTES,
    )
    stack = struct.pack("<IIQQQQQQ", 0x6474E551, 6, 0, 0, 0, 0, 0, 16)
    code_page = (header + code_load + data_load + stack + CODE).ljust(
        PAGE_BYTES, b"\0",
    )
    return code_page + bytes(PAGE_BYTES)
