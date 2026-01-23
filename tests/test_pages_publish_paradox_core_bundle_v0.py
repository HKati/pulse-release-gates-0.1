def _safe_mount_parts(mount: str) -> List[str]:
    """
    Convert a user-provided mount string into safe path parts.

    Reject:
      - empty mounts
      - backslashes
      - absolute mounts
      - '.' or '..' segments (including embedded '/./')
      - empty segments (e.g. 'a//b')
    """
    raw = str(mount).strip()
    if not raw:
        _fail("Mount must be non-empty")

    # Enforce forward-slash semantics to avoid platform surprises.
    if "\\" in raw:
        _fail("Mount must use forward slashes ('/'), not backslashes ('\\')")

    # Reject absolute mounts BEFORE stripping slashes.
    if raw.startswith("/"):
        _fail(f"Mount must be relative, got absolute mount: {mount!r}")

    raw = raw.strip("/")
    if not raw:
        _fail("Mount must not be '/' only")

    # IMPORTANT: reject dot-segments BEFORE any normalization.
    raw_parts = raw.split("/")
    for seg in raw_parts:
        if seg in ("", ".", ".."):
            _fail(f"Mount contains forbidden path segment {seg!r}: {mount!r}")

    # Keep a POSIX-path sanity check.
    p = PurePosixPath("/".join(raw_parts))
    if p.is_absolute():
        _fail(f"Mount must be relative, got absolute mount: {mount!r}")

    return raw_parts

