"""Fixed Linux x86-64 syscall policy for the finite bootstrap entry.

This filter is one part of the caller's read-only namespace boundary. It does
not authenticate the launcher, host, entry binary or observed runtime. A filter
installed before the first exec must allow execve; later same-process execve
calls remain possible. Process creation and unknown system calls are denied.
"""
from __future__ import annotations

import struct

PROFILE = "linux_x86_64_bubblewrap_bootstrap_v0"
ENTRY_SOURCE_PATH = "tools/required_gate_idempotence_containment_entry_v0.c"
POLICY_SOURCE_PATH = "tools/required_gate_idempotence_containment_policy_v0.py"
ENTRY_PATH = "/runtime/bootstrap/containment-entry"
AUDIT_ARCH_X86_64 = 0xC000003E
X32_SYSCALL_BIT = 0x40000000
ALLOW = 0x7FFF0000
DENY = 0x00050000 | 1  # SECCOMP_RET_ERRNO | EPERM
KILL_PROCESS = 0x80000000

# Fixed x86-64 Linux ABI numbers. Filesystem writes are additionally prohibited
# by private read-only mounts and the entry's zero RLIMIT_FSIZE. Open/read calls
# are needed by the loader and Python imports; they expose only the selected
# view. There are no sockets, process creation, mount/namespace changes, ptrace,
# io_uring, BPF, keyring, module-loading or filesystem-mutation calls here.
SYSCALLS = {
    "read": 0, "write": 1, "open": 2, "close": 3, "stat": 4,
    "fstat": 5, "lstat": 6, "poll": 7, "lseek": 8, "mmap": 9,
    "mprotect": 10, "munmap": 11, "brk": 12, "rt_sigaction": 13,
    "rt_sigprocmask": 14, "rt_sigreturn": 15, "pread64": 17,
    "readv": 19, "writev": 20, "access": 21, "sched_yield": 24,
    "mremap": 25, "madvise": 28, "dup": 32, "dup2": 33,
    "nanosleep": 35, "getpid": 39, "execve": 59, "exit": 60,
    "wait4": 61, "uname": 63, "fcntl": 72, "getdents": 78,
    "getcwd": 79, "readlink": 89, "getrlimit": 97, "getrusage": 98,
    "sysinfo": 99, "getuid": 102, "getgid": 104, "geteuid": 107,
    "getegid": 108, "getppid": 110, "capget": 125, "sigaltstack": 131,
    "prctl": 157, "arch_prctl": 158, "gettid": 186, "futex": 202,
    "sched_getaffinity": 204, "getdents64": 217, "set_tid_address": 218,
    "clock_gettime": 228, "clock_getres": 229, "clock_nanosleep": 230,
    "exit_group": 231, "openat": 257, "newfstatat": 262,
    "readlinkat": 267, "faccessat": 269, "pselect6": 270,
    "ppoll": 271, "set_robust_list": 273, "prlimit64": 302,
    "getrandom": 318, "statx": 332, "rseq": 334, "close_range": 436,
    "faccessat2": 439,
}
ALLOWED_SYSCALLS = tuple(sorted(SYSCALLS.values()))


def policy_instructions() -> tuple[tuple[int, int, int, int], ...]:
    """Return sock_filter rows for the fixed policy, never caller input."""
    load, equal, bitset, ret = 0x20, 0x15, 0x45, 0x06
    rows = [
        (load, 0, 0, 4),  # seccomp_data.arch
        (equal, 1, 0, AUDIT_ARCH_X86_64),
        (ret, 0, 0, KILL_PROCESS),
        (load, 0, 0, 0),  # seccomp_data.nr
        (bitset, 0, 1, X32_SYSCALL_BIT),
        (ret, 0, 0, KILL_PROCESS),
    ]
    for number in ALLOWED_SYSCALLS:
        rows.extend(((equal, 0, 1, number), (ret, 0, 0, ALLOW)))
    rows.append((ret, 0, 0, DENY))
    return tuple(rows)


def policy_bytes() -> bytes:
    """Native x86-64 little-endian classic BPF, consumed by bubblewrap."""
    return b"".join(struct.pack("<HBBI", *row) for row in policy_instructions())


def evaluate_policy(arch: int, number: int) -> int:
    """Evaluate the declared ABI policy without installing a kernel filter."""
    if type(arch) is not int or type(number) is not int:
        raise ValueError("containment_policy_integer_required")
    if not 0 <= arch <= 0xFFFFFFFF or not 0 <= number <= 0xFFFFFFFF:
        raise ValueError("containment_policy_word_required")
    if arch != AUDIT_ARCH_X86_64 or number & X32_SYSCALL_BIT:
        return KILL_PROCESS
    return ALLOW if number in ALLOWED_SYSCALLS else DENY
