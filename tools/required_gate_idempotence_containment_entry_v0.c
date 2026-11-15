/* Fixed freestanding Linux x86-64 entry for the selected bootstrap view.
 *
 * Run only after the outer runner installs its private read-only filesystem,
 * namespace and syscall boundary. These local checks are preconditions, not
 * authentication of that boundary or of this source-to-binary relationship.
 * The caller independently selects the exact compiled ELF bytes.
 *
 * No libc or dynamic interpreter is used. This entry never imports or invokes
 * an operator. It accepts only the fixed worker or collector diagnostic phase.
 */
#if !defined(__linux__) || !defined(__x86_64__)
#error "The containment entry requires Linux x86-64."
#endif

typedef unsigned int u32;
typedef unsigned long u64;

struct limit64 { u64 soft; u64 hard; };
struct capability_header { u32 version; int pid; };
struct capability_data { u32 effective; u32 permitted; u32 inheritable; };

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
                      : "rcx", "r11", "memory");
    return result;
}

static __attribute__((noreturn)) void
reject(const char *message, u64 size, long status)
{
    while (size != 0) {
        long written = call6(1, 2, (long) message, (long) size, 0, 0, 0);
        if (written == -4)  /* EINTR */
            continue;
        if (written <= 0)
            break;
        message += written;
        size -= (u64) written;
    }
    call6(60, status, 0, 0, 0, 0, 0);
    __builtin_unreachable();
}

#define REJECT(message, status) reject(message "\n", sizeof(message "\n") - 1, status)

static int
same(const char *left, const char *right)
{
    for (u64 index = 0; index != 10; ++index) {
        if (left[index] != right[index])
            return 0;
        if (left[index] == '\0')
            return 1;
    }
    return 0;
}

static void
set_limit(long resource, u64 value)
{
    struct limit64 limit = { value, value };
    if (call6(302, 0, resource, (long) &limit, 0, 0, 0) != 0)
        REJECT("containment_entry_limit_failed", 126);
}

static __attribute__((noreturn, used)) void
entry(u64 *stack)
{
    if (stack[0] != 2)
        REJECT("containment_entry_phase_invalid", 64);
    const char *phase = (const char *) stack[2];
    if (!same(phase, "worker") && !same(phase, "collector"))
        REJECT("containment_entry_phase_invalid", 64);

    /* PR_GET_NO_NEW_PRIVS and PR_GET_SECCOMP. Neither identifies the filter. */
    if (call6(157, 39, 0, 0, 0, 0, 0) != 1 ||
        call6(157, 21, 0, 0, 0, 0, 0) != 2)
        REJECT("containment_entry_boundary_missing", 126);

    struct capability_header header = { 0x20080522U, 0 };
    struct capability_data caps[2] = {{0, 0, 0}, {0, 0, 0}};
    if (call6(125, (long) &header, (long) caps, 0, 0, 0, 0) != 0 ||
        caps[0].effective || caps[0].permitted || caps[0].inheritable ||
        caps[1].effective || caps[1].permitted || caps[1].inheritable)
        REJECT("containment_entry_capabilities_present", 126);

    /* Do not inherit launcher, policy, payload or unrelated descriptors. */
    if (call6(436, 3, 0xFFFFFFFFUL, 0, 0, 0, 0) != 0)
        REJECT("containment_entry_close_range_failed", 126);

    set_limit(0, 5);                   /* RLIMIT_CPU */
    set_limit(9, 512UL * 1024 * 1024); /* RLIMIT_AS */
    set_limit(4, 0);                   /* RLIMIT_CORE */
    set_limit(1, 0);                   /* RLIMIT_FSIZE */
    set_limit(7, 64);                  /* RLIMIT_NOFILE */

    const char *arguments[] = {
        "/runtime/native/ld-linux-x86-64.so.2", "--inhibit-cache",
        "--library-path", "/runtime/native", "/runtime/python/bin/python3.11",
        "-I", "-S", "-B", "/runtime/bootstrap/probe.py", "--phase", phase, 0
    };
    /* bubblewrap adds PWD; replace the environment rather than inheriting it. */
    const char *environment[] = { "LC_ALL=C", "TZ=UTC", 0 };
    call6(59, (long) arguments[0], (long) arguments, (long) environment, 0, 0, 0);
    REJECT("containment_entry_exec_failed", 126);
}

/* Linux initial rsp points to argc, argv and envp. Preserve it as argument 1
 * while giving the compiler's C function a System V aligned call stack. */
__asm__(".global _start\n"
        ".type _start,@function\n"
        "_start:\n"
        "mov %rsp,%rdi\n"
        "and $-16,%rsp\n"
        "call entry\n");
