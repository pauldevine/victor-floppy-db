"""
Tests for utility functions in the scripts directory.
Run with: python -m pytest scripts/test_utils.py
"""
import unittest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up Django before importing modules
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")

import django
try:
    django.setup()
except:
    pass  # May fail in test environment without proper DB setup


class TestSanitizeString(unittest.TestCase):
    """Test the sanitize_string function."""

    def test_sanitize_lowercase(self):
        """Test that string is converted to lowercase."""
        from disk_mustering import sanitize_string
        result = sanitize_string("HELLO WORLD")
        self.assertEqual(result, "hello-world")

    def test_sanitize_spaces_to_hyphens(self):
        """Test that spaces are replaced with hyphens."""
        from disk_mustering import sanitize_string
        result = sanitize_string("hello world test")
        self.assertEqual(result, "hello-world-test")

    def test_sanitize_special_characters(self):
        """Test that special characters are replaced with hyphens."""
        from disk_mustering import sanitize_string
        result = sanitize_string("hello@world!test")
        self.assertEqual(result, "hello-world-test")

    def test_sanitize_multiple_hyphens(self):
        """Test that multiple consecutive hyphens are collapsed."""
        from disk_mustering import sanitize_string
        result = sanitize_string("hello   world")
        self.assertEqual(result, "hello-world")

    def test_sanitize_trailing_hyphen(self):
        """Test that trailing hyphens are removed."""
        from disk_mustering import sanitize_string
        result = sanitize_string("hello world!")
        self.assertEqual(result, "hello-world")

    def test_sanitize_complex_string(self):
        """Test sanitizing a complex string."""
        from disk_mustering import sanitize_string
        result = sanitize_string("WordPerfect 5.1 (1989) - Disk #1")
        self.assertEqual(result, "wordperfect-5-1-1989-disk-1")


class TestStripHighBit(unittest.TestCase):
    """Test the strip_high_bit function."""

    def test_strip_high_bit_normal_text(self):
        """Test with normal ASCII text."""
        from disk_mustering import strip_high_bit
        result = strip_high_bit("Hello World")
        self.assertEqual(result, "Hello World")

    def test_strip_high_bit_with_high_bits(self):
        """Test with text containing high bit characters."""
        from disk_mustering import strip_high_bit
        # Character with high bit set (e.g., extended ASCII)
        text_with_high_bit = "Hello\x80World"
        result = strip_high_bit(text_with_high_bit)
        # High bit should be stripped
        self.assertNotIn("\x80", result)

    def test_strip_high_bit_removes_null_bytes(self):
        """Test that null bytes are replaced."""
        from disk_mustering import strip_high_bit
        result = strip_high_bit("Hello\x00World")
        self.assertNotIn("\x00", result)
        self.assertIn("\ufffd", result)  # Replacement character

    def test_strip_high_bit_removes_ctrl_z(self):
        """Test that Ctrl-Z (0x1A) is removed."""
        from disk_mustering import strip_high_bit
        result = strip_high_bit("Hello\x1aWorld")
        self.assertEqual(result, "HelloWorld")


class TestMD5Function(unittest.TestCase):
    """Test the md5 function."""

    def test_md5_file_hash(self):
        """Test MD5 hash calculation."""
        from disk_mustering import md5

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("Hello World")
            temp_file = f.name

        try:
            result = md5(temp_file)
            # Known MD5 hash of "Hello World"
            expected = "b10a8db164e0754105b7a99be72e3fe5"
            self.assertEqual(result, expected)
        finally:
            os.unlink(temp_file)

    def test_md5_empty_file(self):
        """Test MD5 hash of empty file."""
        from disk_mustering import md5

        # Create an empty temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            result = md5(temp_file)
            # Known MD5 hash of empty string
            expected = "d41d8cd98f00b204e9800998ecf8427e"
            self.assertEqual(result, expected)
        finally:
            os.unlink(temp_file)


class TestCheckDirExists(unittest.TestCase):
    """Test the check_dir_exists function."""

    def test_check_existing_directory(self):
        """Test with an existing directory."""
        from disk_mustering import check_dir_exists

        with tempfile.TemporaryDirectory() as tmpdir:
            result = check_dir_exists(tmpdir)
            self.assertTrue(result)

    def test_check_nonexistent_directory(self):
        """Test with a non-existent directory."""
        from disk_mustering import check_dir_exists

        result = check_dir_exists("/this/path/does/not/exist")
        self.assertFalse(result)

    def test_check_directory_with_path_object(self):
        """Test with a Path object."""
        from disk_mustering import check_dir_exists

        with tempfile.TemporaryDirectory() as tmpdir:
            path_obj = Path(tmpdir)
            result = check_dir_exists(path_obj)
            self.assertTrue(result)


class TestGetFilesFromDir(unittest.TestCase):
    """Test the get_files_from_dir function."""

    def test_get_files_from_dir_flat(self):
        """Test getting files from a flat directory."""
        from disk_mustering import get_files_from_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.txt")
            Path(file1).touch()
            Path(file2).touch()

            result = get_files_from_dir(tmpdir)
            self.assertEqual(len(result), 2)
            self.assertTrue(any("file1.txt" in f for f in result))
            self.assertTrue(any("file2.txt" in f for f in result))

    def test_get_files_from_dir_recursive(self):
        """Test getting files from nested directories."""
        from disk_mustering import get_files_from_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(subdir, "file2.txt")
            Path(file1).touch()
            Path(file2).touch()

            result = get_files_from_dir(tmpdir)
            # Should include both files and the subdirectory
            self.assertGreaterEqual(len(result), 2)
            self.assertTrue(any("file1.txt" in f for f in result))
            # The subdirectory itself is also added
            self.assertTrue(any("subdir" in f for f in result))

    def test_get_files_ignores_hidden_files(self):
        """Test that hidden files are ignored."""
        from disk_mustering import get_files_from_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create regular and hidden files
            regular_file = os.path.join(tmpdir, "file.txt")
            hidden_file = os.path.join(tmpdir, ".hidden")
            Path(regular_file).touch()
            Path(hidden_file).touch()

            result = get_files_from_dir(tmpdir)
            # Should only include regular file
            self.assertTrue(any("file.txt" in f for f in result))
            self.assertFalse(any(".hidden" in f for f in result))


class TestIsRecent(unittest.TestCase):
    """Test the isRecent function."""

    def test_isrecent_new_file(self):
        """Test with a newly created file."""
        from disk_mustering import isRecent

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            result = isRecent(temp_file)
            self.assertTrue(result)
        finally:
            os.unlink(temp_file)

    def test_isrecent_old_file(self):
        """Test with an old file (simulated by changing mtime)."""
        from disk_mustering import isRecent
        from datetime import datetime, timedelta
        import time

        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = f.name

        try:
            # Set file modification time to 48 hours ago
            old_time = (datetime.now() - timedelta(hours=48)).timestamp()
            os.utime(temp_file, (old_time, old_time))

            result = isRecent(temp_file)
            self.assertFalse(result)
        finally:
            os.unlink(temp_file)


if __name__ == '__main__':
    unittest.main()
