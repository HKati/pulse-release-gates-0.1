/* Fixed authored task-guard qualification probe, Linux x86-64.
 *
 * This is not the containment startup helper, original launcher or payload.
 * The observer admits this executable at its initial exec stop, then records
 * every selected syscall, filter submission, birth, exec and owned removal.
 * getpid markers below are a fixed tracing protocol, not trusted receipts.
 * No output, libc, allocator, shell, path exec, instruction patching or retry
 * is used. A failed expectation exits 120. Unsupported required clone shapes
 * cannot become successful qualification merely by returning an errno.
 *
 * FD 0: empty read-only fully sealed regular input.
 * FD 1/2: distinct owned nonblocking output pipes; no bytes are emitted.
 * FD 3: read-only fully sealed selected probe ELF, retained until self-exec.
 * The observer must independently establish the exact descriptor roster and
 * byte/build selection. Local metadata checks do not authenticate that trust.
 */
#if !defined(__linux__) || !defined(__x86_64__)
#error "The containment task probe requires Linux x86-64."
#endif
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "The containment task probe requires little-endian syscall structures."
#endif

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long u64;

struct kernel_stat {
    u64 dev, ino, nlink;
    u32 mode, uid, gid, padding;
    u64 rdev;
    long size, blksize, blocks;
    u64 atime, atime_nsec, mtime, mtime_nsec, ctime, ctime_nsec;
    long reserved[3];
};
struct capability_header { u32 version; int pid; };
struct capability_data { u32 effective, permitted, inheritable; };
struct sock_filter { u16 code; u8 jt, jf; u32 k; };
struct sock_fprog {
    u16 length, padding16;
    u32 padding32;
    const struct sock_filter *filter;
};

_Static_assert(sizeof(u8) == 1 && sizeof(u16) == 2 && sizeof(u32) == 4 &&
               sizeof(u64) == 8 && sizeof(long) == 8 && sizeof(void *) == 8,
               "Linux x86-64 scalar ABI required");
_Static_assert(sizeof(struct kernel_stat) == 144 &&
               __builtin_offsetof(struct kernel_stat, mode) == 24 &&
               __builtin_offsetof(struct kernel_stat, size) == 48,
               "Linux x86-64 stat ABI required");
_Static_assert(sizeof(struct sock_filter) == 8 &&
               sizeof(struct sock_fprog) == 16 &&
               __builtin_offsetof(struct sock_fprog, filter) == 8,
               "Linux classic-BPF ABI required");

enum {
    NR_fstat = 5, NR_pause = 34, NR_getpid = 39, NR_clone = 56,
    NR_fork = 57, NR_vfork = 58, NR_exit = 60, NR_wait4 = 61,
    NR_fcntl = 72, NR_getuid = 102, NR_getgid = 104,
    NR_geteuid = 107, NR_getegid = 108, NR_getppid = 110,
    NR_capget = 125, NR_prctl = 157, NR_execveat = 322,
    NR_io_uring_setup = 425, NR_io_uring_enter = 426,
    NR_io_uring_register = 427, NR_clone3 = 435,
    F_GETFD = 1, F_SETFD = 2, F_GETFL = 3, F_GET_SEALS = 1034,
    FD_CLOEXEC = 1, O_RDONLY = 0, O_WRONLY = 1,
    O_NONBLOCK = 04000, O_LARGEFILE = 0100000,
    S_IFMT = 0170000, S_IFREG = 0100000, S_IFIFO = 0010000,
    S_ISUID = 04000, S_ISGID = 02000,
    PR_SET_PDEATHSIG = 1, PR_GET_PDEATHSIG = 2,
    PR_GET_SECCOMP = 21, PR_SET_SECCOMP = 22,
    PR_SET_NO_NEW_PRIVS = 38, PR_GET_NO_NEW_PRIVS = 39,
    SIGKILL = 9, SIGSYS = 31, FULL_SEALS = 15,
    SECCOMP_MODE_FILTER = 2, AT_EMPTY_PATH = 0x1000,
    PREINSTALL = 1, POSTINSTALL = 2, R_BORN = 3, T_BORN = 4,
    AFTER_EXEC = 5, PARK = 6, REAPED = 7, CONTROL = 8,
    ROLE_L = 0, ROLE_R = 1, ROLE_T = 2,
    CASE_EXEC_DENIAL = 19, CASE_GRAPH_INHERITANCE = 20,
    CASE_GRAPH_CANCEL = 21
};

/* Same 34 selected instructions as the startup-helper task guard.
 * 272 bytes; SHA-256:
 * cc75cb083fb0f6b235eb429384dfb5aaffdd4653891eb2010cd0fd5b6939a51f.
 * This literal source array is compared with independent golden bytes by the
 * data-only checker and captured again at the native submission stop.
 */
static const struct sock_filter pulse_task_guard[]
    __attribute__((used, section(".pulse_task_guard"), aligned(8))) = {
    {0x20, 0, 0, 4},
    {0x15, 0, 31, 0xc000003e},
    {0x20, 0, 0, 0},
    {0x45, 29, 0, 0x40000000},
    {0x15, 28, 0, 57},
    {0x15, 27, 0, 58},
    {0x15, 26, 0, 425},
    {0x15, 25, 0, 426},
    {0x15, 24, 0, 427},
    {0x15, 23, 0, 435},
    {0x15, 0, 21, 56},
    {0x20, 0, 0, 20},
    {0x15, 0, 20, 0},
    {0x20, 0, 0, 24},
    {0x15, 0, 18, 0},
    {0x20, 0, 0, 28},
    {0x15, 0, 16, 0},
    {0x20, 0, 0, 16},
    {0x15, 13, 0, 0x7e020011},
    {0x15, 0, 13, 0x01200011},
    {0x20, 0, 0, 32},
    {0x15, 0, 11, 0},
    {0x20, 0, 0, 36},
    {0x15, 0, 9, 0},
    {0x20, 0, 0, 48},
    {0x15, 0, 7, 0},
    {0x20, 0, 0, 52},
    {0x15, 0, 5, 0},
    {0x20, 0, 0, 40},
    {0x15, 0, 2, 0},
    {0x20, 0, 0, 44},
    {0x15, 1, 0, 0},
    {0x06, 0, 0, 0x7fff0000},
    {0x06, 0, 0, 0x80000000}
};
_Static_assert(sizeof(pulse_task_guard) == 272, "Fixed guard length required");

static const char *const case_names[] = {
    "native_getpid", "fork", "vfork", "clone3", "io_uring_setup",
    "io_uring_enter", "io_uring_register", "x32_getpid", "compat_getpid",
    "clone_unselected", "clone_l_upper", "clone_l_stack",
    "clone_r_null_tid", "clone_r_parent_tid", "clone_r_tls",
    "clone_r_stack", "clone_r_upper", "clone_r_unselected",
    "exec_denial", "graph_inheritance", "graph_cancel"
};
_Static_assert(sizeof(case_names) / sizeof(case_names[0]) == 21,
               "Fixed qualification case roster required");

/* CLONE_CHILD_SETTID writes this word in T's separate address space before
 * returning to userspace. The observer binds its actual address, writable
 * mapping and child-side value; a source declaration alone proves none of it.
 */
static volatile int child_tid;

static long
call6(long number, long a, long b, long c, long d, long e, long f)
{
    register long r10 __asm__("r10") = d;
    register long r8 __asm__("r8") = e;
    register long r9 __asm__("r9") = f;
    long result;
    __asm__ volatile ("syscall"
                      : "=a" (result)
                      : "a" (number), "D" (a), "S" (b), "d" (c),
                        "r" (r10), "r" (r8), "r" (r9)
                      : "rcx", "r11", "cc", "memory");
    return result;
}

static __attribute__((noreturn)) void
finish(long status)
{
    (void) call6(NR_exit, status, 0, 0, 0, 0, 0);
    __asm__ volatile ("ud2");
    __builtin_unreachable();
}

static void
need(int condition)
{
    if (!condition)
        finish(120);
}

static int
same(const char *actual, const char *expected)
{
    for (u32 index = 0; index != 64; ++index) {
        if (actual[index] != expected[index])
            return 0;
        if (actual[index] == '\0')
            return 1;
    }
    return 0;
}

static long
parent_pid(const char *text)
{
    u64 value = 0;
    need(text[0] >= '1' && text[0] <= '9');
    for (u32 index = 0; index != 11; ++index) {
        unsigned char ch = (unsigned char) text[index];
        if (ch == 0) {
            need(value > 1 && value <= 2147483647UL);
            return (long) value;
        }
        need(index < 10 && ch >= '0' && ch <= '9');
        value = value * 10 + (u64) (ch - '0');
        need(value <= 2147483647UL);
    }
    finish(120);
}

static void
marker(long case_id, long stage, long role, long value0, long value1)
{
    need(call6(NR_getpid, 0x50554c5345515630L, case_id, stage,
               role, value0, value1) > 0);
}

static void
check_credentials_and_descriptors(void)
{
    long uid = call6(NR_getuid, 0, 0, 0, 0, 0, 0);
    long gid = call6(NR_getgid, 0, 0, 0, 0, 0, 0);
    need(uid > 0 && gid > 0 &&
         call6(NR_geteuid, 0, 0, 0, 0, 0, 0) == uid &&
         call6(NR_getegid, 0, 0, 0, 0, 0, 0) == gid);
    struct capability_header header = {0x20080522U, 0};
    struct capability_data data[2] = {{0, 0, 0}, {0, 0, 0}};
    need(call6(NR_capget, (long) &header, (long) data, 0, 0, 0, 0) == 0);
    need(data[0].effective == 0 && data[0].permitted == 0 &&
         data[0].inheritable == 0 && data[1].effective == 0 &&
         data[1].permitted == 0 && data[1].inheritable == 0);
    struct kernel_stat records[4];
    for (long fd = 0; fd != 4; ++fd) {
        struct kernel_stat *info = &records[fd];
        need(call6(NR_fstat, fd, (long) info, 0, 0, 0, 0) == 0);
        need(info->uid == (u32) uid && info->gid == (u32) gid);
        need(call6(NR_fcntl, fd, F_GETFD, 0, 0, 0, 0) == 0);
        long flags = call6(NR_fcntl, fd, F_GETFL, 0, 0, 0, 0);
        if (fd == 0 || fd == 3) {
            need((info->mode & S_IFMT) == S_IFREG &&
                 (info->mode & (S_ISUID | S_ISGID)) == 0);
            need(flags == O_RDONLY || flags == (O_RDONLY | O_LARGEFILE));
            need(call6(NR_fcntl, fd, F_GET_SEALS, 0, 0, 0, 0) == FULL_SEALS);
            need(fd == 0 ? info->size == 0 :
                 (info->size > 0 && info->size <= 262144));
        } else {
            need((info->mode & S_IFMT) == S_IFIFO);
            need(flags == (O_WRONLY | O_NONBLOCK));
        }
    }
    need(records[0].dev != records[3].dev || records[0].ino != records[3].ino);
    need(records[1].dev != records[2].dev || records[1].ino != records[2].ino);
}

static void
prepare_parent(long expected)
{
    need(call6(NR_getppid, 0, 0, 0, 0, 0, 0) == expected);
    need(call6(NR_prctl, PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0, 0) == 0);
    int configured = 0;
    need(call6(NR_prctl, PR_GET_PDEATHSIG, (long) &configured, 0, 0, 0, 0) == 0);
    need(configured == SIGKILL &&
         call6(NR_getppid, 0, 0, 0, 0, 0, 0) == expected);
}

static void
install_guard(void)
{
    need(call6(NR_prctl, PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0, 0) == 0);
    need(call6(NR_prctl, PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0, 0) == 1);
    struct sock_fprog program = {34, 0, 0, pulse_task_guard};
    need(call6(NR_prctl, PR_SET_SECCOMP, SECCOMP_MODE_FILTER,
               (long) &program, 0, 0, 0) == 0);
    need(call6(NR_prctl, PR_GET_SECCOMP, 0, 0, 0, 0, 0) == 2);
    need(call6(NR_prctl, PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0, 0) == 1);
}

static __attribute__((noreturn)) void
deny_fork(void)
{
    (void) call6(NR_fork, 0, 0, 0, 0, 0, 0);
    finish(120);
}

static __attribute__((noreturn)) void
park(long case_id, long role)
{
    marker(case_id, PARK, role, 0, 0);
    /* The observer holds the marker ENTRY stop and never restarts this role.
     * pause is a fail-closed fallback if an incorrect observer does resume it;
     * the observer's fixed deadline and inherited EXITKILL remain required.
     */
    (void) call6(NR_pause, 0, 0, 0, 0, 0, 0);
    finish(120);
}

static __attribute__((noreturn)) void
self_exec(const char *case_name, const char *observer_text)
{
    need(call6(NR_fcntl, 3, F_SETFD, FD_CLOEXEC, 0, 0, 0) == 0);
    need(call6(NR_fcntl, 3, F_GETFD, 0, 0, 0, 0) == FD_CLOEXEC);
    const char *arguments[] = {
        "pulsemech-containment-task-probe-v0", case_name,
        observer_text, "after-exec", 0
    };
    const char *environment[] = {"LC_ALL=C", "TZ=UTC", 0};
    (void) call6(NR_execveat, 3, (long) "", (long) arguments,
                 (long) environment, AT_EMPTY_PATH, 0);
    finish(120);
}

static __attribute__((noreturn)) void
reap_then_deny(long case_id, long role, long child)
{
    int status = 0;
    long got = call6(NR_wait4, child, (long) &status, 0, 0, 0, 0);
    marker(case_id, REAPED, role, got, (long) status);
    need(got == child && status >= 0 && (status & ~128) == SIGSYS);
    deny_fork();
}

static __attribute__((noreturn)) void
graph(long case_id, const char *case_name, const char *observer_text)
{
    long first = call6(NR_clone, 0x7e020011L, 0, 0xa2, 0xa3, 0xa4, 0xa5);
    need(first >= 0);
    if (first > 0) {
        if (case_id == CASE_GRAPH_CANCEL)
            park(case_id, ROLE_L);
        reap_then_deny(case_id, ROLE_L, first);
    }
    /* R is PID 1 in the new PID namespace; getppid may correctly be zero.
     * Parent identities are joined in the outer observer's PID namespace.
     */
    marker(case_id, R_BORN, ROLE_R, 0, 0);
    child_tid = 0;
    long second = call6(NR_clone, 0x01200011L, 0, 0,
                        (long) &child_tid, 0, 0xa5);
    need(second >= 0);
    if (second > 0) {
        if (case_id == CASE_GRAPH_CANCEL)
            park(case_id, ROLE_R);
        reap_then_deny(case_id, ROLE_R, second);
    }
    long own_pid = call6(NR_getpid, 0, 0, 0, 0, 0, 0);
    need(own_pid > 0 && child_tid == own_pid);
    marker(case_id, T_BORN, ROLE_T, (long) &child_tid, (long) child_tid);
    self_exec(case_name, observer_text);
}

static __attribute__((naked, noreturn)) void
compat_getpid(void)
{
    /* i386 argument registers are EBX, ECX, EDX, ESI, EDI and EBP. Do not
     * confuse this syscall 20 with native x86-64 syscall 20. The observer
     * records PTRACE_GET_SYSCALL_INFO.arch=0x40000003 at its entry stop.
     */
    /* A standalone assembly leaf avoids an inline push into C's red zone.
     * It has no return to C, so no callee-saved register needs restoration.
     */
    __asm__("mov $20,%eax\n"
            "xor %ebx,%ebx\n"
            "xor %ecx,%ecx\n"
            "xor %edx,%edx\n"
            "xor %esi,%esi\n"
            "xor %edi,%edi\n"
            "xor %ebp,%ebp\n"
            "int $0x80\n"
            "mov $60,%eax\n"
            "mov $120,%edi\n"
            "xor %esi,%esi\n"
            "xor %edx,%edx\n"
            "xor %r10d,%r10d\n"
            "xor %r8d,%r8d\n"
            "xor %r9d,%r9d\n"
            "syscall\n"
            "ud2\n");
}

static __attribute__((noreturn)) void
negative_case(long case_id)
{
    long nr = 0;
    long flags = 0, stack = 0, parent_tid = 0, tid = 0, tls = 0, unused = 0;
    switch (case_id) {
    case 2: nr = NR_fork; break;
    case 3: nr = NR_vfork; break;
    case 4: nr = NR_clone3; break;
    case 5: nr = NR_io_uring_setup; break;
    case 6: nr = NR_io_uring_enter; break;
    case 7: nr = NR_io_uring_register; break;
    case 8: nr = 0x40000027L; break;
    case 9: compat_getpid();
    case 10: nr = NR_clone; flags = 17; break;
    case 11:
        nr = NR_clone; flags = 0x000000017e020011L;
        parent_tid = 0xa2; tid = 0xa3; tls = 0xa4; unused = 0xa5;
        break;
    case 12:
        nr = NR_clone; flags = 0x7e020011L; stack = 0x100000000L;
        parent_tid = 0xa2; tid = 0xa3; tls = 0xa4; unused = 0xa5;
        break;
    case 13: case 14: case 15: case 16: case 17: case 18:
        nr = NR_clone; flags = 0x01200011L;
        tid = (long) &child_tid; unused = 0xa5;
        if (case_id == 13) tid = 0;
        if (case_id == 14) parent_tid = 0x100000000L;
        if (case_id == 15) tls = 0x100000000L;
        if (case_id == 16) stack = 0x100000000L;
        if (case_id == 17) flags = 0x0000000101200011L;
        if (case_id == 18) flags = 0x01200111L;
        break;
    default: finish(120);
    }
    (void) call6(nr, flags, stack, parent_tid, tid, tls, unused);
    finish(120);
}

__attribute__((used, noreturn)) static void
probe_main(u64 *initial_stack)
{
    need(initial_stack[0] == 4);
    const char *const *arguments = (const char *const *) (initial_stack + 1);
    need(arguments[0] && arguments[1] && arguments[2] && arguments[3] &&
         arguments[4] == 0);
    need(same(arguments[0], "pulsemech-containment-task-probe-v0"));
    long case_id = 0;
    for (u32 index = 0; index != 21; ++index)
        if (same(arguments[1], case_names[index]))
            case_id = (long) index + 1;
    need(case_id != 0);
    long expected_parent = parent_pid(arguments[2]);
    if (same(arguments[3], "after-exec")) {
        need(case_id == CASE_EXEC_DENIAL || case_id == CASE_GRAPH_INHERITANCE ||
             case_id == CASE_GRAPH_CANCEL);
        /* No filter installation or parent-relative credentials assumption
         * here. T inhabits R's user/PID namespaces; this tests inheritance.
         */
        need(call6(NR_prctl, PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0, 0) == 1);
        need(call6(NR_prctl, PR_GET_SECCOMP, 0, 0, 0, 0, 0) == 2);
        long role = case_id == CASE_EXEC_DENIAL ? ROLE_L : ROLE_T;
        marker(case_id, AFTER_EXEC, role, 0, 0);
        need(call6(NR_getpid, 0, 0, 0, 0, 0, 0) > 0);
        if (case_id == CASE_GRAPH_CANCEL)
            park(case_id, role);
        deny_fork();
    }
    need(same(arguments[3], "initial"));
    marker(case_id, PREINSTALL, ROLE_L, 0, 0);
    prepare_parent(expected_parent);
    check_credentials_and_descriptors();
    install_guard();
    need(call6(NR_getppid, 0, 0, 0, 0, 0, 0) == expected_parent);
    marker(case_id, POSTINSTALL, ROLE_L, 0, 0);
    if (case_id == 1) {
        need(call6(NR_getpid, 0, 0, 0, 0, 0, 0) > 0);
        marker(case_id, CONTROL, ROLE_L, 0, 0);
        finish(0);
    }
    if (case_id == CASE_EXEC_DENIAL)
        self_exec(arguments[1], arguments[2]);
    if (case_id == CASE_GRAPH_INHERITANCE || case_id == CASE_GRAPH_CANCEL)
        graph(case_id, arguments[1], arguments[2]);
    negative_case(case_id);
}

/* Preserve the kernel's initial stack and enter C with a System V aligned
 * call stack. This ELF has no libc startup or return path.
 */
__asm__(".section .text\n"
        ".global _start\n"
        ".type _start,@function\n"
        "_start:\n"
        "mov %rsp,%rdi\n"
        "and $-16,%rsp\n"
        "call probe_main\n"
        "ud2\n"
        ".size _start,.-_start\n");
