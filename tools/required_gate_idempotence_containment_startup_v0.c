/* Fixed pre-exec phase of L for the containment-entry profile, Linux x86-64.
 *
 * This source is a separately selected startup helper, not the historical
 * single-tracee guard or static containment entry. Its only successful terminal
 * operation is the fixed execveat below. No libc, allocator, shell, task-creation
 * operation, receipt descriptor, caller-selected payload or fallback is used.
 *
 * Descriptor ownership means the current UID/GID reported by fstat. Local
 * checks do not authenticate the observer, barrier writer, tracer, build,
 * source/binary relationship or host. Those are independent qualification and
 * observation obligations. In particular, pipe inode equality is not a proof
 * of who owns another endpoint. This implementation has not been qualified by
 * native execution merely because its source or compiled ELF is checked.
 */
#if !defined(__linux__) || !defined(__x86_64__)
#error "The containment startup requires Linux x86-64."
#endif
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "The containment startup requires little-endian syscall structures."
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
struct kernel_timespec { long sec, nsec; };
struct kernel_pollfd { int fd; short events, revents; };
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
_Static_assert(sizeof(struct kernel_timespec) == 16 &&
               sizeof(struct kernel_pollfd) == 8,
               "Linux x86-64 clock/poll ABI required");
_Static_assert(sizeof(struct sock_filter) == 8 &&
               sizeof(struct sock_fprog) == 16 &&
               __builtin_offsetof(struct sock_fprog, filter) == 8,
               "Linux classic-BPF ABI required");

enum {
    NR_read = 0, NR_write = 1, NR_close = 3, NR_fstat = 5, NR_poll = 7,
    NR_lseek = 8, NR_pread64 = 17, NR_exit = 60, NR_fcntl = 72,
    NR_chdir = 80, NR_getuid = 102, NR_getgid = 104, NR_geteuid = 107,
    NR_getegid = 108, NR_getppid = 110, NR_capget = 125, NR_prctl = 157,
    NR_clock_gettime = 228, NR_execveat = 322, NR_close_range = 436,
    F_GETFD = 1, F_SETFD = 2, F_GETFL = 3, F_SETFL = 4,
    F_GETPIPE_SZ = 1032, F_GET_SEALS = 1034,
    FD_CLOEXEC = 1, O_ACCMODE = 3, O_RDONLY = 0, O_WRONLY = 1,
    O_NONBLOCK = 04000, O_LARGEFILE = 0100000,
    S_IFMT = 0170000, S_IFREG = 0100000, S_IFIFO = 0010000,
    S_ISUID = 04000, S_ISGID = 02000,
    PR_SET_PDEATHSIG = 1, PR_GET_PDEATHSIG = 2,
    PR_GET_SECCOMP = 21, PR_SET_SECCOMP = 22,
    PR_SET_NO_NEW_PRIVS = 38, PR_GET_NO_NEW_PRIVS = 39,
    SIGKILL = 9, CLOCK_MONOTONIC = 1, SECCOMP_MODE_FILTER = 2,
    AT_EMPTY_PATH = 0x1000, FULL_SEALS = 15,
    EINTR_VALUE = 4, EAGAIN_VALUE = 11,
    POLLIN_VALUE = 1, POLLERR_VALUE = 8, POLLHUP_VALUE = 16,
    POLLNVAL_VALUE = 32, STDERR_MAX_BYTES = 96
};

/* Independent producer and checker reconstruct these 34 little-endian rows.
 * 272 bytes; SHA-256:
 * cc75cb083fb0f6b235eb429384dfb5aaffdd4653891eb2010cd0fd5b6939a51f.
 * Non-x86-64 and x32 are killed. Other syscalls are allowed except fork,
 * vfork, clone3, io_uring_setup/enter/register and non-selected clone shapes.
 * The namespace clone ignores args 2..5. The glibc clone requires null
 * parent_tid (arg 2), nonnull child_tid (arg 3), null tls (arg 4), and ignores
 * arg 5. Flags, stack and pointer tests inspect their full 64-bit values.
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

static u64 deadline_ns;
static int stderr_ready;
static u32 owner_uid, owner_gid;

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
    /* Recheck the pipe and restore/read back NONBLOCK even on the rejection
     * path: failure may itself have detected changed inherited status flags.
     * Suppress the diagnostic on any error. Never retry EINTR or finish a
     * partial write. A missing reader may cause terminal SIGPIPE. Concurrent
     * changes by an untrusted observer are not authenticated by this helper.
     */
    if (stderr_ready && size <= STDERR_MAX_BYTES) {
        struct kernel_stat info;
        long flags = call6(NR_fcntl, 2, F_GETFL, 0, 0, 0, 0);
        if (flags >= 0 && (flags & O_ACCMODE) == O_WRONLY &&
            (flags & ~(long) (O_ACCMODE | O_NONBLOCK)) == 0 &&
            call6(NR_fstat, 2, (long) &info, 0, 0, 0, 0) == 0 &&
            (info.mode & S_IFMT) == S_IFIFO &&
            call6(NR_fcntl, 2, F_GETPIPE_SZ, 0, 0, 0, 0) > 0 &&
            call6(NR_fcntl, 2, F_SETFL, flags | O_NONBLOCK, 0, 0, 0) == 0 &&
            call6(NR_fcntl, 2, F_GETFL, 0, 0, 0, 0) == (O_WRONLY | O_NONBLOCK))
            (void) call6(NR_write, 2, (long) message, (long) size, 0, 0, 0);
    }
    (void) call6(NR_exit, status, 0, 0, 0, 0, 0);
    __asm__ volatile ("ud2"); /* Trap if an outer policy made exit return. */
    __builtin_unreachable();
}

#define REJECT(message, status) \
    reject(message "\n", sizeof(message "\n") - 1, status)

static u64
monotonic_ns(void)
{
    struct kernel_timespec now;
    for (u32 attempt = 0; attempt != 8; ++attempt) {
        long result = call6(NR_clock_gettime, CLOCK_MONOTONIC,
                            (long) &now, 0, 0, 0, 0);
        if (result == -EINTR_VALUE)
            continue;
        if (result != 0 || now.sec < 0 || now.nsec < 0 ||
            now.nsec >= 1000000000L ||
            (u64) now.sec > (0xffffffffffffffffUL - 999999999UL) / 1000000000UL)
            REJECT("containment_startup_clock_failed", 126);
        return (u64) now.sec * 1000000000UL + (u64) now.nsec;
    }
    REJECT("containment_startup_clock_interrupted", 126);
}

static void
deadline_check(void)
{
    if (monotonic_ns() >= deadline_ns)
        REJECT("containment_startup_deadline", 126);
}

static long
bounded_call6(long number, long a, long b, long c, long d, long e, long f)
{
    for (u32 attempt = 0; attempt != 8; ++attempt) {
        deadline_check();
        long result = call6(number, a, b, c, d, e, f);
        if (result != -EINTR_VALUE)
            return result;
    }
    REJECT("containment_startup_syscall_interrupted", 126);
}

static void
prepare_pipe(int fd, long access)
{
    struct kernel_stat info;
    long flags = bounded_call6(NR_fcntl, fd, F_GETFL, 0, 0, 0, 0);
    if (flags < 0 || (flags & O_ACCMODE) != access ||
        (flags & ~(long) (O_ACCMODE | O_NONBLOCK)) != 0 ||
        bounded_call6(NR_fstat, fd, (long) &info, 0, 0, 0, 0) != 0 ||
        (info.mode & S_IFMT) != S_IFIFO ||
        bounded_call6(NR_fcntl, fd, F_GETPIPE_SZ, 0, 0, 0, 0) <= 0 ||
        bounded_call6(NR_fcntl, fd, F_SETFL, flags | O_NONBLOCK, 0, 0, 0) != 0 ||
        bounded_call6(NR_fcntl, fd, F_GETFL, 0, 0, 0, 0) != (access | O_NONBLOCK))
        REJECT("containment_startup_pipe_invalid", 126);
}

static long
expected_parent(u64 *stack)
{
    static const char name[] = "pulsemech-containment-startup-v0";
    if (stack[0] != 2 || stack[1] == 0 || stack[2] == 0 || stack[3] != 0)
        REJECT("containment_startup_arguments_invalid", 64);
    const char *arg0 = (const char *) stack[1];
    const char *arg1 = (const char *) stack[2];
    for (u64 index = 0; index != sizeof(name); ++index) {
        if (arg0[index] != name[index])
            REJECT("containment_startup_arguments_invalid", 64);
    }
    if (arg1[0] < '1' || arg1[0] > '9')
        REJECT("containment_startup_parent_argument_invalid", 64);
    u64 parent = 0;
    for (u32 index = 0; index != 11; ++index) {
        char digit = arg1[index];
        if (digit == '\0') {
            if (parent > 1)
                return (long) parent;
            break;
        }
        if (index == 10 || digit < '0' || digit > '9' ||
            parent > (2147483647UL - (u64) (digit - '0')) / 10UL)
            break;
        parent = parent * 10UL + (u64) (digit - '0');
    }
    REJECT("containment_startup_parent_argument_invalid", 64);
}

static void
check_parent(long parent)
{
    if (bounded_call6(NR_getppid, 0, 0, 0, 0, 0, 0) != parent)
        REJECT("containment_startup_parent_lost", 126);
}

static void
check_parent_death_signal(long parent)
{
    int signal = 0;
    if (bounded_call6(NR_prctl, PR_GET_PDEATHSIG, (long) &signal, 0, 0, 0, 0) != 0 ||
        signal != SIGKILL)
        REJECT("containment_startup_parent_signal_invalid", 126);
    check_parent(parent);
}

static void
check_credentials(int initial)
{
    long uid = bounded_call6(NR_getuid, 0, 0, 0, 0, 0, 0);
    long gid = bounded_call6(NR_getgid, 0, 0, 0, 0, 0, 0);
    if (uid <= 0 || gid <= 0 || (u64) uid >= 0xffffffffUL ||
        (u64) gid >= 0xffffffffUL ||
        bounded_call6(NR_geteuid, 0, 0, 0, 0, 0, 0) != uid ||
        bounded_call6(NR_getegid, 0, 0, 0, 0, 0, 0) != gid ||
        (!initial && ((u32) uid != owner_uid || (u32) gid != owner_gid)))
        REJECT("containment_startup_credentials_invalid", 126);
    owner_uid = (u32) uid;
    owner_gid = (u32) gid;
    struct capability_header header = {0x20080522U, 0};
    struct capability_data caps[2] = {{0, 0, 0}, {0, 0, 0}};
    if (bounded_call6(NR_capget, (long) &header, (long) caps, 0, 0, 0, 0) != 0 ||
        caps[0].effective || caps[0].permitted || caps[0].inheritable ||
        caps[1].effective || caps[1].permitted || caps[1].inheritable)
        REJECT("containment_startup_capabilities_present", 126);
}

struct payload_binding { int fd; long size; u8 digest[32]; };
static const struct payload_binding payloads[] = {
    {0, 0, {
        0xe3,0xb0,0xc4,0x42,0x98,0xfc,0x1c,0x14,0x9a,0xfb,0xf4,0xc8,0x99,0x6f,0xb9,0x24,
        0x27,0xae,0x41,0xe4,0x64,0x9b,0x93,0x4c,0xa4,0x95,0x99,0x1b,0x78,0x52,0xb8,0x55}},
    {3, 454, {
        0x52,0x75,0x7c,0xae,0xa0,0x6d,0x24,0x7a,0xc1,0xcf,0x34,0x33,0xc0,0x69,0x74,0xbd,
        0xec,0xba,0x7e,0xcb,0x06,0x9e,0x87,0x59,0xf0,0x7a,0x91,0x46,0x5c,0x88,0x28,0x47}},
    {4, 9568, {
        0x7a,0x21,0xb2,0xe4,0xd6,0x0d,0xc0,0x80,0x14,0x9d,0x9a,0x91,0x9b,0x60,0x4e,0x39,
        0xf6,0xfb,0x29,0xbe,0x42,0xd4,0x62,0xe9,0x79,0xb4,0x6d,0x3c,0x43,0x9b,0x95,0xab}},
    {5, 1160, {
        0x9f,0x35,0x70,0xa8,0x7b,0x1f,0xde,0x59,0x29,0x9d,0x69,0xd2,0x42,0x49,0x6c,0xbd,
        0x9d,0x2f,0x1b,0x16,0x31,0xa4,0x0d,0xbc,0x5e,0xd8,0xe4,0x97,0x6e,0xdf,0xa6,0xab}},
    {6, 80248, {
        0x57,0x32,0x36,0xe5,0x32,0x8a,0xc2,0xeb,0xb0,0x8f,0x59,0xae,0x3a,0x98,0x05,0xb4,
        0xf8,0xd1,0x2b,0xde,0xf1,0x4b,0xe8,0xaf,0x44,0x50,0xd5,0x46,0x32,0x94,0x98,0x5f}}
};

/* Small local SHA-256 implementation. Every compression is exactly 64 rounds.
 * The caller checks the deadline for each pread chunk of at most 4096 bytes;
 * each update below therefore has at most 65 bounded copy/block iterations.
 * No per-round or per-block clock syscalls consume the observer's event budget.
 * Hashing never moves descriptor offsets.
 */
struct sha256_state { u32 h[8]; u64 bytes; u32 used; u8 block[64]; };

static u32
rotate_right(u32 value, u32 count)
{
    return (value >> count) | (value << (32U - count));
}

static void
sha256_block(struct sha256_state *state)
{
    static const u32 constants[64] = {
        0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
        0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
        0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
        0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
        0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
        0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
        0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
        0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
    };
    u32 words[64];
    for (u32 index = 0; index != 16; ++index) {
        u32 offset = index * 4;
        words[index] = (u32) state->block[offset] << 24 |
                       (u32) state->block[offset + 1] << 16 |
                       (u32) state->block[offset + 2] << 8 |
                       (u32) state->block[offset + 3];
    }
    for (u32 index = 16; index != 64; ++index) {
        u32 a = words[index - 15], b = words[index - 2];
        u32 s0 = rotate_right(a, 7) ^ rotate_right(a, 18) ^ (a >> 3);
        u32 s1 = rotate_right(b, 17) ^ rotate_right(b, 19) ^ (b >> 10);
        words[index] = words[index - 16] + s0 + words[index - 7] + s1;
    }
    u32 a = state->h[0], b = state->h[1], c = state->h[2], d = state->h[3];
    u32 e = state->h[4], f = state->h[5], g = state->h[6], h = state->h[7];
    for (u32 index = 0; index != 64; ++index) {
        u32 s1 = rotate_right(e, 6) ^ rotate_right(e, 11) ^ rotate_right(e, 25);
        u32 choose = (e & f) ^ (~e & g);
        u32 t1 = h + s1 + choose + constants[index] + words[index];
        u32 s0 = rotate_right(a, 2) ^ rotate_right(a, 13) ^ rotate_right(a, 22);
        u32 majority = (a & b) ^ (a & c) ^ (b & c);
        u32 t2 = s0 + majority;
        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }
    state->h[0] += a; state->h[1] += b; state->h[2] += c; state->h[3] += d;
    state->h[4] += e; state->h[5] += f; state->h[6] += g; state->h[7] += h;
}

static void
sha256_update(struct sha256_state *state, const u8 *bytes, u32 count)
{
    state->bytes += count;
    while (count != 0) {
        u32 take = 64 - state->used;
        if (take > count)
            take = count;
        for (u32 index = 0; index != take; ++index)
            state->block[state->used + index] = bytes[index];
        state->used += take;
        bytes += take;
        count -= take;
        if (state->used == 64) {
            sha256_block(state);
            state->used = 0;
        }
    }
}

static void
sha256_finish(struct sha256_state *state, u8 digest[32])
{
    deadline_check();
    u64 bits = state->bytes * 8;
    state->block[state->used++] = 0x80;
    if (state->used > 56) {
        for (u32 index = state->used; index != 64; ++index)
            state->block[index] = 0;
        sha256_block(state);
        state->used = 0;
    }
    for (u32 index = state->used; index != 56; ++index)
        state->block[index] = 0;
    for (u32 index = 0; index != 8; ++index)
        state->block[63 - index] = (u8) (bits >> (index * 8));
    sha256_block(state);
    for (u32 index = 0; index != 32; ++index)
        digest[index] = (u8) (state->h[index / 4] >> (24 - (index % 4) * 8));
}

static void
hash_descriptor(const struct payload_binding *binding)
{
    struct sha256_state state = {
        {0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
         0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19}, 0, 0, {0}
    };
    u8 buffer[4096], digest[32];
    long offset = 0;
    while (offset < binding->size) {
        deadline_check();
        long count = binding->size - offset;
        if (count > (long) sizeof(buffer))
            count = (long) sizeof(buffer);
        long result = bounded_call6(NR_pread64, binding->fd, (long) buffer,
                                    count, offset, 0, 0);
        if (result <= 0 || result > count)
            REJECT("containment_startup_payload_read_failed", 126);
        sha256_update(&state, buffer, (u32) result);
        offset += result;
    }
    if (bounded_call6(NR_pread64, binding->fd, (long) buffer, 1,
                      binding->size, 0, 0) != 0)
        REJECT("containment_startup_payload_extent_invalid", 126);
    sha256_finish(&state, digest);
    u32 difference = 0;
    for (u32 index = 0; index != 32; ++index)
        difference |= (u32) (digest[index] ^ binding->digest[index]);
    if (difference != 0)
        REJECT("containment_startup_payload_digest_invalid", 126);
}

struct fd_snapshot {
    u64 dev, ino, nlink, rdev;
    long size, status_flags;
    u32 mode, uid, gid;
};

static int
is_payload(int fd)
{
    return fd == 0 || (fd >= 3 && fd <= 6);
}

static const struct payload_binding *
binding_for(int fd)
{
    return &payloads[fd == 0 ? 0 : fd - 2];
}

static void
read_metadata(int fd, struct fd_snapshot *snapshot)
{
    struct kernel_stat info;
    long flags = bounded_call6(NR_fcntl, fd, F_GETFL, 0, 0, 0, 0);
    if (flags < 0 ||
        bounded_call6(NR_fstat, fd, (long) &info, 0, 0, 0, 0) != 0 ||
        info.uid != owner_uid || info.gid != owner_gid ||
        bounded_call6(NR_fcntl, fd, F_GETFD, 0, 0, 0, 0) !=
            (fd >= 6 ? FD_CLOEXEC : 0))
        REJECT("containment_startup_descriptor_invalid", 126);
    if (is_payload(fd)) {
        if ((info.mode & S_IFMT) != S_IFREG ||
            (info.mode & (S_ISUID | S_ISGID)) != 0 ||
            (flags & O_ACCMODE) != O_RDONLY ||
            (flags & ~(long) O_LARGEFILE) != 0 ||
            info.size != binding_for(fd)->size ||
            bounded_call6(NR_fcntl, fd, F_GET_SEALS, 0, 0, 0, 0) != FULL_SEALS ||
            bounded_call6(NR_lseek, fd, 0, 1, 0, 0, 0) != 0)
            REJECT("containment_startup_sealed_descriptor_invalid", 126);
    } else {
        long access = fd == 7 ? O_RDONLY : O_WRONLY;
        if ((info.mode & S_IFMT) != S_IFIFO || flags != (access | O_NONBLOCK) ||
            bounded_call6(NR_fcntl, fd, F_GETPIPE_SZ, 0, 0, 0, 0) <= 0)
            REJECT("containment_startup_pipe_invalid", 126);
    }
    snapshot->dev = info.dev;
    snapshot->ino = info.ino;
    snapshot->nlink = info.nlink;
    snapshot->rdev = info.rdev;
    snapshot->size = info.size;
    snapshot->status_flags = flags;
    snapshot->mode = info.mode;
    snapshot->uid = info.uid;
    snapshot->gid = info.gid;
}

static int
same_snapshot(const struct fd_snapshot *left, const struct fd_snapshot *right)
{
    return left->dev == right->dev && left->ino == right->ino &&
           left->nlink == right->nlink && left->rdev == right->rdev &&
           left->size == right->size && left->status_flags == right->status_flags &&
           left->mode == right->mode && left->uid == right->uid && left->gid == right->gid;
}

static void
validate_descriptors(struct fd_snapshot snapshots[8], int count, int initial)
{
    for (int fd = 0; fd != count; ++fd) {
        deadline_check();
        struct fd_snapshot before, after;
        read_metadata(fd, &before);
        if (!initial && !same_snapshot(&before, &snapshots[fd]))
            REJECT("containment_startup_descriptor_changed", 126);
        if (is_payload(fd))
            hash_descriptor(binding_for(fd));
        read_metadata(fd, &after);
        if (!same_snapshot(&before, &after))
            REJECT("containment_startup_descriptor_changed", 126);
        if (initial)
            snapshots[fd] = after;
    }
    /* Independent regular inputs are pairwise distinct, as are all three
     * pipe roles. Do not mistake a descriptor number for object continuity.
     */
    for (int left = 0; left != count; ++left) {
        for (int right = left + 1; right < count; ++right) {
            if (is_payload(left) == is_payload(right) &&
                snapshots[left].dev == snapshots[right].dev &&
                snapshots[left].ino == snapshots[right].ino)
                REJECT("containment_startup_descriptor_alias", 126);
        }
    }
}

static void
read_release(long parent, const struct fd_snapshot *barrier)
{
    static const u8 token[] = "PULSEv0\n";
    u8 received[sizeof(token)];
    u32 used = 0;
    /* Both the 30-second deadline and the independent iteration cap apply.
     * Read one byte beyond the token to reject trailing bytes; a complete
     * token without EOF never releases L. Poll waits at most 100 ms at a time.
     */
    for (u32 attempt = 0; attempt != 1024; ++attempt) {
        deadline_check();
        check_parent(parent);
        long result = bounded_call6(NR_read, 7, (long) received,
                                    (long) sizeof(received) - used, 0, 0, 0);
        if (result > 0) {
            if ((u64) result > sizeof(received) - used ||
                used + (u32) result > sizeof(token) - 1)
                REJECT("containment_startup_barrier_trailing_bytes", 126);
            for (u32 index = 0; index != (u32) result; ++index) {
                if (received[index] != token[used + index])
                    REJECT("containment_startup_barrier_token_invalid", 126);
            }
            used += (u32) result;
            continue;
        }
        if (result == 0) {
            struct fd_snapshot after;
            if (used != sizeof(token) - 1)
                REJECT("containment_startup_barrier_truncated", 126);
            read_metadata(7, &after);
            if (!same_snapshot(barrier, &after))
                REJECT("containment_startup_barrier_changed", 126);
            check_parent_death_signal(parent);
            return;
        }
        if (result != -EAGAIN_VALUE)
            REJECT("containment_startup_barrier_read_failed", 126);
        u64 now = monotonic_ns();
        if (now >= deadline_ns)
            REJECT("containment_startup_deadline", 126);
        u64 remaining_ms = (deadline_ns - now + 999999UL) / 1000000UL;
        long timeout_ms = remaining_ms > 100 ? 100 : (long) remaining_ms;
        struct kernel_pollfd pollfd = {7, POLLIN_VALUE, 0};
        result = bounded_call6(NR_poll, (long) &pollfd, 1, timeout_ms, 0, 0, 0);
        if (result < 0 || result > 1 ||
            (pollfd.revents & (POLLERR_VALUE | POLLNVAL_VALUE)) != 0 ||
            (pollfd.revents & ~(POLLIN_VALUE | POLLHUP_VALUE)) != 0)
            REJECT("containment_startup_barrier_poll_failed", 126);
    }
    REJECT("containment_startup_barrier_iteration_limit", 126);
}

static __attribute__((noreturn, used)) void
startup_main(u64 *stack)
{
    /* Include all preparation and both byte validations in the one deadline.
     * No timeout is restarted at barrier release or before the fixed exec.
     */
    u64 started = monotonic_ns();
    if (started > 0xffffffffffffffffUL - 30000000000UL)
        REJECT("containment_startup_clock_range", 126);
    deadline_ns = started + 30000000000UL;
    prepare_pipe(2, O_WRONLY);
    stderr_ready = 1;

    long parent = expected_parent(stack);
    check_parent(parent);
    if (bounded_call6(NR_prctl, PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0, 0) != 0)
        REJECT("containment_startup_parent_signal_failed", 126);
    check_parent_death_signal(parent); /* Includes the parent-loss race check. */
    check_credentials(1);
    if (bounded_call6(NR_chdir, (long) "/", 0, 0, 0, 0, 0) != 0 ||
        bounded_call6(NR_close_range, 8, 0xffffffffUL, 0, 0, 0, 0) != 0)
        REJECT("containment_startup_preparation_failed", 126);

    prepare_pipe(1, O_WRONLY);
    prepare_pipe(7, O_RDONLY);
    for (int fd = 0; fd != 8; ++fd) {
        long flag = fd >= 6 ? FD_CLOEXEC : 0;
        if (bounded_call6(NR_fcntl, fd, F_SETFD, flag, 0, 0, 0) != 0 ||
            bounded_call6(NR_fcntl, fd, F_GETFD, 0, 0, 0, 0) != flag)
            REJECT("containment_startup_inheritance_invalid", 126);
    }
    struct fd_snapshot descriptors[8];
    validate_descriptors(descriptors, 8, 1);
    check_parent_death_signal(parent);
    read_release(parent, &descriptors[7]);

    /* Framing success is not enough: bind the same complete sealed bytes,
     * metadata, zero offsets and descriptor flags again before closing FD 7.
     */
    check_credentials(0);
    validate_descriptors(descriptors, 7, 0);
    check_parent_death_signal(parent);
    deadline_check();
    /* close is never retried: Linux releases the descriptor even on EINTR. */
    if (call6(NR_close, 7, 0, 0, 0, 0, 0) != 0)
        REJECT("containment_startup_barrier_close_failed", 126);

    if (bounded_call6(NR_prctl, PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0, 0) != 0 ||
        bounded_call6(NR_prctl, PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0, 0) != 1)
        REJECT("containment_startup_no_new_privileges_failed", 126);
    struct sock_fprog program = {
        (u16) (sizeof(pulse_task_guard) / sizeof(pulse_task_guard[0])), 0, 0,
        pulse_task_guard
    };
    deadline_check();
    /* Submit once. Mode readback is not privileged filter-byte readback. */
    if (call6(NR_prctl, PR_SET_SECCOMP, SECCOMP_MODE_FILTER,
              (long) &program, 0, 0, 0) != 0 ||
        bounded_call6(NR_prctl, PR_GET_SECCOMP, 0, 0, 0, 0, 0) != 2 ||
        bounded_call6(NR_prctl, PR_GET_NO_NEW_PRIVS, 0, 0, 0, 0, 0) != 1)
        REJECT("containment_startup_task_guard_failed", 126);
    check_parent_death_signal(parent);
    const char *arguments[] = {"bubblewrap", "--args", "3", 0};
    const char *environment[] = {"LC_ALL=C", "TZ=UTC", 0};
    deadline_check();
    (void) call6(NR_execveat, 6, (long) "", (long) arguments,
                 (long) environment, AT_EMPTY_PATH, 0);
    REJECT("containment_startup_exec_failed", 126);
}

/* Linux initial rsp addresses argc, argv and envp. Preserve that pointer and
 * use a System V aligned call stack. There is no libc startup or return path.
 */
__asm__(".section .text\n"
        ".global _start\n"
        ".type _start,@function\n"
        "_start:\n"
        "mov %rsp,%rdi\n"
        "and $-16,%rsp\n"
        "call startup_main\n"
        "ud2\n"
        ".size _start,.-_start\n");
