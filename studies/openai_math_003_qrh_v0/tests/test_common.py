"""Filesystem/JSON failure boundaries used by the production verifier."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from common import AuditError, strict_loads, canonical_bytes, secure_read, exclusive_write, sha256_file


class TestCommonBoundary(unittest.TestCase):
    def test_duplicate_json_key(self):
        with self.assertRaises(AuditError):
            strict_loads(b'{"gates":{},"gates":{"a":true}}')

    def test_nonfinite_number(self):
        for raw in (b'NaN', b'Infinity', b'-Infinity', b'1e9999'):
            with self.subTest(raw=raw), self.assertRaises(AuditError):
                strict_loads(raw)

    def test_integer_true_remains_distinct(self):
        self.assertIs(type(strict_loads(b'{"x":1}')['x']), int)
        self.assertNotEqual(canonical_bytes({'x': True}), canonical_bytes({'x': 1}))

    def test_no_silent_unicode_replacement(self):
        with self.assertRaises(AuditError):
            strict_loads(b'{"x":"\xff"}')

    def test_frozen_bytes_are_not_reread(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence'
            path.write_bytes(b'before')
            raw = secure_read(directory, 'evidence')
            path.write_bytes(b'after')
            self.assertEqual(b'before', raw)
            self.assertEqual(b'after', secure_read(directory, 'evidence'))

    def test_symlink_leaf_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'real').write_bytes(b'payload')
            (root / 'link').symlink_to(root / 'real')
            with self.assertRaises(AuditError):
                secure_read(root, 'link')

    def test_symlink_directory_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'real').mkdir()
            (root / 'real' / 'value').write_bytes(b'payload')
            (root / 'link').symlink_to(root / 'real', target_is_directory=True)
            with self.assertRaises(AuditError):
                secure_read(root, 'link/value')

    def test_parent_and_absolute_escape_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for name in ('../value', '/etc/passwd', 'x/../value', './value', 'x//value'):
                with self.subTest(name=name), self.assertRaises(AuditError):
                    secure_read(directory, name)

    def test_fifo_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / 'fifo'
            os.mkfifo(fifo)
            with self.assertRaises(AuditError):
                secure_read(directory, 'fifo')
            with self.assertRaises(AuditError):
                sha256_file(fifo)

    def test_exclusive_publication_preserves_previous_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'certificate.json'
            exclusive_write(path, b'original')
            with self.assertRaises(AuditError):
                exclusive_write(path, b'replacement')
            self.assertEqual(b'original', path.read_bytes())


if __name__ == '__main__':
    unittest.main()
