#!/usr/bin/env python3
"""Source-bound QRH entry point; invoke this trusted .py file with python -I.

The caller supplies an independently approved source-manifest SHA-256. This
launcher, interpreter, stdlib, installed dependencies and host remain trusted.
This is a code-binding boundary, not an OS sandbox or native proof adapter.
"""
from __future__ import annotations

import sys

# Check before even standard-library imports: without -I the script directory
# could shadow argparse/json before a later check had a chance to reject it.
if __name__ == '__main__' and not sys.flags.isolated:
    print('QRH_BIND_ISOLATED_PROCESS_REQUIRED', file=sys.stderr)
    raise SystemExit(2)

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import MappingProxyType

CONTEXT_NAME = '_qrh003_source_runtime'
TOOL_NAMES = frozenset({'common', 'audit', 'verify', 'authority', 'collect',
                       'acquire', 'source_closure', 'preflight', 'run_tests',
                       'prepare', 'transition_report'})
COMMANDS = TOOL_NAMES - {'common', 'audit'}
MAX_FILE = 4 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
# Linux UAPI values, also used by the pinned preflight implementation. Some
# CPython builds omit these names despite a kernel that supports sealing.
F_ADD_SEALS = getattr(fcntl, 'F_ADD_SEALS', 1033)
F_GET_SEALS = getattr(fcntl, 'F_GET_SEALS', 1034)
REQUIRED_SEALS = (getattr(fcntl, 'F_SEAL_WRITE', 0x0008) |
                  getattr(fcntl, 'F_SEAL_GROW', 0x0004) |
                  getattr(fcntl, 'F_SEAL_SHRINK', 0x0002) |
                  getattr(fcntl, 'F_SEAL_SEAL', 0x0001))


class BindingError(RuntimeError):
    pass


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise BindingError('QRH_BIND_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def invalid(_):
        raise BindingError('QRH_BIND_NONFINITE_JSON')
    return json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=pairs,
                      parse_constant=invalid)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def logical_path(name):
    if (not isinstance(name, str) or not name or '\\' in name or '\x00' in name
            or ':' in name or name.startswith('/')
            or any(p in ('', '.', '..') for p in name.split('/'))
            or str(PurePosixPath(name)) != name):
        raise BindingError('QRH_BIND_UNSAFE_PATH')
    return name


def read_regular(path, limit=MAX_FILE):
    path = Path(os.path.abspath(os.fspath(path)))
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                            os.O_CLOEXEC, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK |
                     os.O_CLOEXEC, dir_fd=directory)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise BindingError('QRH_BIND_FILE_TYPE_OR_SIZE')
            chunks, total = [], 0
            while True:
                chunk = os.read(fd, min(65536, limit + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > limit:
                    raise BindingError('QRH_BIND_FILE_TOO_LARGE')
            after = os.fstat(fd)
            stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if stamp(before) != stamp(after):
                raise BindingError('QRH_BIND_FILE_CHANGED_DURING_READ')
            return b''.join(chunks)
        finally:
            os.close(fd)
    finally:
        os.close(directory)


@contextmanager
def sealed_bytes(raw, name):
    """Seal the exact launcher/manifest bytes inherited by child processes."""
    fd = os.memfd_create(name, os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
    try:
        position = 0
        while position < len(raw):
            count = os.write(fd, raw[position:])
            if count <= 0:
                raise BindingError('QRH_BIND_SNAPSHOT_WRITE_FAILED')
            position += count
        fcntl.fcntl(fd, F_ADD_SEALS, REQUIRED_SEALS)
        if fcntl.fcntl(fd, F_GET_SEALS) & REQUIRED_SEALS != REQUIRED_SEALS:
            raise BindingError('QRH_BIND_SNAPSHOT_SEAL_FAILED')
        os.lseek(fd, 0, os.SEEK_SET)
        yield fd
    finally:
        os.close(fd)


def read_manifest_fd(fd):
    if fcntl.fcntl(fd, F_GET_SEALS) & REQUIRED_SEALS != REQUIRED_SEALS:
        raise BindingError('QRH_BIND_UNSEALED_MANIFEST_FD')
    size = os.fstat(fd).st_size
    if not 0 < size <= MAX_FILE:
        raise BindingError('QRH_BIND_MANIFEST_SIZE')
    return os.pread(fd, size, 0)


class AliasLoader(importlib.abc.Loader):
    def __init__(self, canonical):
        self.canonical = canonical

    def create_module(self, spec):
        return importlib.import_module(self.canonical)

    def exec_module(self, module):
        pass  # The canonical, verified source module has already executed.


class SourceRuntime(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def __init__(self, root, manifest_raw, expected_sha256):
        self.root = Path(os.path.abspath(os.fspath(root)))
        if (not isinstance(expected_sha256, str) or
                re.fullmatch(r'[0-9a-f]{64}', expected_sha256) is None or
                digest(manifest_raw) != expected_sha256):
            raise BindingError('QRH_BIND_MANIFEST_DIGEST_MISMATCH')
        manifest = strict_json(manifest_raw)
        if (not isinstance(manifest, dict) or
                manifest.get('schema_version') != 'qrh003_repository_source_manifest_v1' or
                manifest.get('repository_path') != 'studies/openai_math_003_qrh_v0'):
            raise BindingError('QRH_BIND_MANIFEST_VERSION')
        entries = manifest.get('files')
        if not isinstance(entries, list) or not 1 <= len(entries) <= 256:
            raise BindingError('QRH_BIND_MANIFEST_INVENTORY')
        files, total = {}, 0
        for row in entries:
            if not isinstance(row, dict) or set(row) != {'path', 'size_bytes', 'sha256'}:
                raise BindingError('QRH_BIND_MANIFEST_FIELDS')
            name = logical_path(row['path'])
            size, wanted = row['size_bytes'], row['sha256']
            if (name in files or name == 'SOURCE_MANIFEST.json' or type(size) is not int
                    or not 0 <= size <= MAX_FILE or not isinstance(wanted, str)
                    or re.fullmatch(r'[0-9a-f]{64}', wanted) is None):
                raise BindingError('QRH_BIND_MANIFEST_INVENTORY')
            total += size
            if total > MAX_TOTAL:
                raise BindingError('QRH_BIND_SOURCE_BUDGET')
            raw = read_regular(self.root / name)
            if len(raw) != size or digest(raw) != wanted:
                raise BindingError('QRH_BIND_SOURCE_DIGEST_MISMATCH:' + name)
            files[name] = raw
        if (manifest.get('file_count_excluding_this_manifest') != len(files) or
                manifest.get('total_bytes_excluding_this_manifest') != total):
            raise BindingError('QRH_BIND_MANIFEST_TOTAL_MISMATCH')
        required = {'source_bound.py'} | {'tools/' + n + '.py' for n in TOOL_NAMES}
        if not required <= set(files):
            raise BindingError('QRH_BIND_REQUIRED_SOURCE_MISSING')
        code, aliases = {}, {}
        for name, raw in files.items():
            if name.startswith('tools/') and name.endswith('.py'):
                stem = name[6:-3]
                if stem not in TOOL_NAMES:
                    raise BindingError('QRH_BIND_UNSUPPORTED_TOOL_MODULE')
                canonical = 'tools.' + stem
                aliases[stem] = canonical
            elif name.startswith('tests/') and name.endswith('.py'):
                stem = name[6:-3]
                if re.fullmatch(r'test_[A-Za-z0-9_]+', stem) is None:
                    raise BindingError('QRH_BIND_UNSUPPORTED_TEST_MODULE')
                canonical = stem  # Preserve the published unittest IDs.
                aliases['tests.' + stem] = canonical
            else:
                continue
            code[canonical] = (name, compile(raw, str(self.root / name), 'exec',
                                            dont_inherit=True, optimize=0))
        self.files = MappingProxyType(files)
        self.code = MappingProxyType(code)
        self.aliases = MappingProxyType(aliases)
        self.manifest_raw = manifest_raw
        self.manifest_sha256 = expected_sha256
        self.verifier_files = MappingProxyType({name: digest(raw) for name, raw in files.items()
            if name == 'source_bound.py' or name.startswith(('tools/', 'tests/')) and name.endswith('.py')})

    def contract(self):
        return {'schema_version': 'qrh003_source_binding_v1',
                'source_manifest_sha256': self.manifest_sha256,
                'launcher_sha256': digest(self.files['source_bound.py']),
                'module_execution': 'COMPILED_FROM_VERIFIED_SOURCE_BYTES'}

    def install(self):
        if CONTEXT_NAME in sys.modules or any(
                n in self.aliases or n in self.code or n in ('tools', 'tests') or
                n.startswith(('tools.', 'tests.')) for n in sys.modules):
            raise BindingError('QRH_BIND_PRELOADED_STUDY_MODULE')
        sys.meta_path.insert(0, self)
        sys.modules[CONTEXT_NAME] = self

    def find_spec(self, fullname, path=None, target=None):
        if fullname in ('tools', 'tests'):
            return importlib.util.spec_from_loader(fullname, self, is_package=True)
        if fullname in self.aliases:
            return importlib.util.spec_from_loader(fullname, AliasLoader(self.aliases[fullname]))
        if fullname in self.code:
            return importlib.util.spec_from_loader(fullname, self)
        if fullname.startswith(('tools.', 'tests.', 'test_')):
            raise BindingError('QRH_BIND_UNANCHORED_IMPORT:' + fullname)
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        if module.__name__ in ('tools', 'tests'):
            module.__path__ = []
            return
        name, code = self.code[module.__name__]
        module.__file__ = str(self.root / name)
        module.__cached__ = None
        exec(code, module.__dict__)

    @contextmanager
    def child(self, command, arguments):
        if command not in {'preflight', 'run_tests'}:
            raise BindingError('QRH_BIND_CHILD_COMMAND_UNSUPPORTED')
        with sealed_bytes(self.files['source_bound.py'], 'qrh-launcher') as executable:
            with sealed_bytes(self.manifest_raw, 'qrh-source-manifest') as inventory:
                argv = [sys.executable, '-I', '/proc/self/fd/' + str(executable),
                        '--root', str(self.root), '--manifest-fd', str(inventory),
                        '--source-manifest-sha256', self.manifest_sha256,
                        command, *map(str, arguments)]
                yield argv, (executable, inventory)


def main(argv=None):
    if not sys.flags.isolated:
        raise BindingError('QRH_BIND_ISOLATED_PROCESS_REQUIRED')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--source-manifest', type=Path)
    source.add_argument('--manifest-fd', type=int)
    parser.add_argument('--source-manifest-sha256', required=True)
    parser.add_argument('command', choices=sorted(COMMANDS))
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    raw = (read_manifest_fd(args.manifest_fd) if args.manifest_fd is not None else
           read_regular(args.source_manifest or args.root / 'SOURCE_MANIFEST.json'))
    runtime = SourceRuntime(args.root, raw, args.source_manifest_sha256)
    runtime.install()
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    return importlib.import_module('tools.' + args.command).main(arguments)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'binding_status': 'REJECTED', 'error': str(exc),
                          'authority_granted': False}), file=sys.stderr)
        raise SystemExit(2)
