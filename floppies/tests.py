"""
Comprehensive test suite for the floppies app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

from .models import (
    Entry, Creator, ArchCollection, Contributor, FluxFile, Language,
    PhotoImage, RandoFile, Subject, TextFile, ZipArchive, ZipContent,
    ScriptRun, InfoChunk, MetaChunk
)


class BaseModelTestCase(TestCase):
    """Test the BaseModel abstract class functionality."""

    def test_created_date_auto_set(self):
        """Test that created_date is automatically set on creation."""
        entry = Entry.objects.create(
            identifier="test-entry",
            title="Test Entry"
        )
        self.assertIsNotNone(entry.created_date)
        self.assertLessEqual(
            (timezone.now() - entry.created_date).total_seconds(),
            2  # Should be created within 2 seconds
        )

    def test_modified_date_auto_updates(self):
        """Test that modified_date is automatically updated."""
        entry = Entry.objects.create(
            identifier="test-entry",
            title="Test Entry"
        )
        original_modified = entry.modified_date

        # Small delay to ensure time difference
        entry.title = "Updated Entry"
        entry.save()

        self.assertGreater(entry.modified_date, original_modified)


class CreatorModelTest(TestCase):
    """Test the Creator model."""

    def test_creator_creation(self):
        """Test creating a Creator instance."""
        creator = Creator.objects.create(name="John Doe")
        self.assertEqual(creator.name, "John Doe")
        self.assertEqual(str(creator), "John Doe")

    def test_creator_unique_name(self):
        """Test that multiple creators can have the same name (no unique constraint)."""
        Creator.objects.create(name="John Doe")
        creator2 = Creator.objects.create(name="John Doe")
        self.assertEqual(Creator.objects.filter(name="John Doe").count(), 2)


class ArchCollectionModelTest(TestCase):
    """Test the ArchCollection model."""

    def test_collection_creation(self):
        """Test creating an ArchCollection instance."""
        collection = ArchCollection.objects.create(name="open_source_software")
        self.assertEqual(collection.name, "open_source_software")
        self.assertEqual(str(collection), "open_source_software")


class LanguageModelTest(TestCase):
    """Test the Language model."""

    def test_language_creation(self):
        """Test creating a Language instance."""
        language = Language.objects.create(name="English")
        self.assertEqual(language.name, "English")
        self.assertEqual(str(language), "English")


class SubjectModelTest(TestCase):
    """Test the Subject model."""

    def test_subject_creation(self):
        """Test creating a Subject instance."""
        subject = Subject.objects.create(name="Victor 9000")
        self.assertEqual(subject.name, "Victor 9000")
        self.assertEqual(str(subject), "Victor 9000")


class EntryModelTest(TestCase):
    """Test the Entry model."""

    def setUp(self):
        """Set up test data."""
        self.creator = Creator.objects.create(name="Test Creator")
        self.collection = ArchCollection.objects.create(name="test_collection")
        self.language = Language.objects.create(name="English")
        self.subject = Subject.objects.create(name="Victor 9000")

    def test_entry_creation(self):
        """Test creating an Entry instance."""
        entry = Entry.objects.create(
            identifier="test-disk-001",
            title="Test Disk 001",
            description="Test description",
            mediatype=Entry.Mediatypes.SOFTWARE
        )
        self.assertEqual(entry.identifier, "test-disk-001")
        self.assertEqual(entry.title, "Test Disk 001")
        self.assertEqual(str(entry), "Test Disk 001")
        self.assertFalse(entry.uploaded)
        self.assertFalse(entry.needsWork)

    def test_entry_with_relationships(self):
        """Test Entry with ManyToMany relationships."""
        entry = Entry.objects.create(
            identifier="test-disk-002",
            title="Test Disk 002"
        )
        entry.creators.add(self.creator)
        entry.collections.add(self.collection)
        entry.languages.add(self.language)
        entry.subjects.add(self.subject)

        self.assertEqual(entry.creators.count(), 1)
        self.assertEqual(entry.collections.count(), 1)
        self.assertEqual(entry.languages.count(), 1)
        self.assertEqual(entry.subjects.count(), 1)

    def test_entry_get_absolute_url(self):
        """Test Entry.get_absolute_url() method."""
        entry = Entry.objects.create(
            identifier="test-disk-003",
            title="Test Disk 003"
        )
        expected_url = reverse("floppies:entry-update", kwargs={"pk": entry.pk})
        self.assertEqual(entry.get_absolute_url(), expected_url)

    def test_entry_get_media_files_empty(self):
        """Test Entry.get_media_files() with no related files."""
        entry = Entry.objects.create(
            identifier="test-disk-004",
            title="Test Disk 004"
        )
        media_files = entry.get_media_files()
        self.assertEqual(len(media_files), 0)

    def test_entry_get_media_files_with_zip_and_photos(self):
        """Test Entry.get_media_files() with zip archives and photos."""
        entry = Entry.objects.create(
            identifier="test-disk-005",
            title="Test Disk 005"
        )

        # Create zip archive
        zip_archive = ZipArchive.objects.create(
            archive="/path/to/test.zip",
            entry=entry
        )

        # Create photo
        photo = PhotoImage.objects.create(
            image="/path/to/photo.jpg",
            entry=entry
        )

        media_files = entry.get_media_files()
        self.assertEqual(len(media_files), 2)
        self.assertIn("/path/to/test.zip", media_files)
        self.assertIn("/path/to/photo.jpg", media_files)

    def test_entry_mediatype_choices(self):
        """Test Entry.Mediatypes choices."""
        entry = Entry.objects.create(
            identifier="test-disk-006",
            title="Test Disk 006",
            mediatype=Entry.Mediatypes.SOFTWARE
        )
        self.assertEqual(entry.mediatype, "SW")
        self.assertEqual(entry.get_mediatype_display(), "Software")

    def test_get_mediatype_key(self):
        """Test Entry.get_mediatype_key() classmethod."""
        self.assertEqual(
            Entry.Mediatypes.get_mediatype_key("software"),
            Entry.Mediatypes.SOFTWARE
        )
        self.assertEqual(
            Entry.Mediatypes.get_mediatype_key("texts"),
            Entry.Mediatypes.TEXTS
        )
        # Default to SOFTWARE for unknown
        self.assertEqual(
            Entry.Mediatypes.get_mediatype_key("unknown"),
            Entry.Mediatypes.SOFTWARE
        )


class ZipArchiveModelTest(TestCase):
    """Test the ZipArchive model."""

    def test_zip_archive_creation(self):
        """Test creating a ZipArchive instance."""
        entry = Entry.objects.create(
            identifier="test-disk",
            title="Test Disk"
        )
        zip_archive = ZipArchive.objects.create(
            archive="/path/to/archive.zip",
            entry=entry
        )
        self.assertEqual(zip_archive.archive, "/path/to/archive.zip")
        self.assertEqual(zip_archive.entry, entry)
        self.assertEqual(str(zip_archive), "/path/to/archive.zip")


class ZipContentModelTest(TestCase):
    """Test the ZipContent model."""

    def test_zip_content_creation(self):
        """Test creating a ZipContent instance."""
        entry = Entry.objects.create(
            identifier="test-disk",
            title="Test Disk"
        )
        zip_archive = ZipArchive.objects.create(
            archive="/path/to/archive.zip",
            entry=entry
        )
        zip_content = ZipContent.objects.create(
            zipArchive=zip_archive,
            file="test.txt",
            md5sum="abc123",
            suffix=".txt",
            size_bytes=1024
        )
        self.assertEqual(zip_content.file, "test.txt")
        self.assertEqual(zip_content.md5sum, "abc123")
        self.assertEqual(zip_content.size_bytes, 1024)


class ScriptRunModelTest(TestCase):
    """Test the ScriptRun model."""

    def test_scriptrun_creation(self):
        """Test creating a ScriptRun instance."""
        entry = Entry.objects.create(
            identifier="test-disk",
            title="Test Disk"
        )
        script_run = ScriptRun.objects.create(
            entry=entry,
            text="Test script output",
            parentPath="/path/to/folder",
            function="test_function",
            script="test_script.py"
        )
        self.assertEqual(script_run.entry, entry)
        self.assertEqual(script_run.text, "Test script output")
        self.assertIsNotNone(script_run.runtime)

    def test_scriptrun_str_with_path(self):
        """Test ScriptRun __str__ with parentPath set."""
        entry = Entry.objects.create(
            identifier="test-disk",
            title="Test Disk"
        )
        script_run = ScriptRun.objects.create(
            entry=entry,
            text="Test",
            parentPath="/path/to/folder"
        )
        str_repr = str(script_run)
        self.assertIn("/path/to/folder", str_repr)
        self.assertIn(script_run.runtime.strftime("%Y-%m-%d"), str_repr)

    def test_scriptrun_str_without_path(self):
        """Test ScriptRun __str__ without parentPath (None)."""
        entry = Entry.objects.create(
            identifier="test-disk",
            title="Test Disk"
        )
        script_run = ScriptRun.objects.create(
            entry=entry,
            text="Test",
            parentPath=None
        )
        str_repr = str(script_run)
        self.assertIn("No Path", str_repr)


class MetaChunkModelTest(TestCase):
    """Test the MetaChunk model."""

    def test_get_language_abbr(self):
        """Test MetaChunk.get_language_abbr() classmethod."""
        self.assertEqual(MetaChunk.get_language_abbr("English"), "en")
        self.assertEqual(MetaChunk.get_language_abbr("Spanish"), "es")
        self.assertEqual(MetaChunk.get_language_abbr("French"), "fr")
        self.assertIsNone(MetaChunk.get_language_abbr("Unknown"))

    def test_get_language_from_abbr(self):
        """Test MetaChunk.get_language_from_abbr() classmethod."""
        self.assertEqual(MetaChunk.get_language_from_abbr("en"), "English")
        self.assertEqual(MetaChunk.get_language_from_abbr("es"), "Spanish")
        self.assertEqual(MetaChunk.get_language_from_abbr("fr"), "French")
        self.assertIsNone(MetaChunk.get_language_from_abbr("xx"))


class IndexViewTest(TestCase):
    """Test the IndexView."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        # Create test entries
        for i in range(30):
            Entry.objects.create(
                identifier=f"test-disk-{i:03d}",
                title=f"Test Disk {i:03d}",
                needsWork=(i % 3 == 0),  # Every 3rd needs work
                readyToUpload=(i % 2 == 0),  # Every 2nd ready to upload
                uploaded=(i % 5 == 0)  # Every 5th uploaded
            )

    def test_index_view_status_code(self):
        """Test that index view returns 200."""
        response = self.client.get(reverse('floppies:index'))
        self.assertEqual(response.status_code, 200)

    def test_index_view_pagination(self):
        """Test that index view paginates correctly."""
        response = self.client.get(reverse('floppies:index'))
        self.assertEqual(response.status_code, 200)
        # Should have 25 entries per page
        self.assertEqual(len(response.context['latest_entry_list']), 25)

    def test_index_view_needs_work_filter(self):
        """Test filtering by needsWork."""
        response = self.client.get(reverse('floppies:index') + '?needswork=true')
        self.assertEqual(response.status_code, 200)
        # All entries should have needsWork=True
        for entry in response.context['latest_entry_list']:
            self.assertTrue(entry.needsWork)

    def test_index_view_next_upload_filter(self):
        """Test filtering by nextupload."""
        response = self.client.get(reverse('floppies:index') + '?nextupload=true')
        self.assertEqual(response.status_code, 200)
        # All entries should be ready to upload and not uploaded
        for entry in response.context['latest_entry_list']:
            self.assertFalse(entry.needsWork)
            self.assertTrue(entry.readyToUpload)
            self.assertFalse(entry.uploaded)

    def test_index_view_date_order(self):
        """Test ordering by date."""
        response = self.client.get(reverse('floppies:index') + '?dateorder=true')
        self.assertEqual(response.status_code, 200)
        entries = list(response.context['latest_entry_list'])
        # Check that entries are ordered by modified_date descending
        for i in range(len(entries) - 1):
            self.assertGreaterEqual(
                entries[i].modified_date,
                entries[i + 1].modified_date
            )


class EntryDetailViewTest(TestCase):
    """Test the Entry detail views."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.entry = Entry.objects.create(
            identifier="test-disk",
            title="Test Disk",
            description="Test description"
        )

    def test_detail_view_status_code(self):
        """Test that detail view returns 200."""
        response = self.client.get(
            reverse('floppies:entry-detail', kwargs={'pk': self.entry.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_contains_entry_data(self):
        """Test that detail view contains entry data."""
        response = self.client.get(
            reverse('floppies:entry-detail', kwargs={'pk': self.entry.pk})
        )
        self.assertContains(response, "Test Disk")
        self.assertContains(response, "test-disk")


class EntryUpdateViewTest(TestCase):
    """Test the Entry update view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.entry = Entry.objects.create(
            identifier="test-disk",
            title="Test Disk"
        )

    def test_update_view_status_code(self):
        """Test that update view returns 200."""
        response = self.client.get(
            reverse('floppies:entry-update', kwargs={'pk': self.entry.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_update_view_context_with_zip_archives(self):
        """Test that update view context includes zip archives."""
        # Create zip archive for entry
        zip_archive = ZipArchive.objects.create(
            archive="/path/to/test.zip",
            entry=self.entry
        )

        response = self.client.get(
            reverse('floppies:entry-update', kwargs={'pk': self.entry.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('zip_archives', response.context)


class SearchViewTest(TestCase):
    """Test the search view."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        Entry.objects.create(
            identifier="wordperfect-disk-1",
            title="WordPerfect Disk 1"
        )
        Entry.objects.create(
            identifier="lotus-123-disk",
            title="Lotus 123 Disk"
        )

    def test_search_view_by_title(self):
        """Test searching by title."""
        response = self.client.get(reverse('floppies:search-results') + '?q=WordPerfect')
        self.assertEqual(response.status_code, 200)
        results = response.context['object_list']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "WordPerfect Disk 1")

    def test_search_view_by_identifier(self):
        """Test searching by identifier."""
        response = self.client.get(reverse('floppies:search-results') + '?q=lotus-123')
        self.assertEqual(response.status_code, 200)
        results = response.context['object_list']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].identifier, "lotus-123-disk")

    def test_search_view_case_insensitive(self):
        """Test that search is case insensitive."""
        response = self.client.get(reverse('floppies:search-results') + '?q=wordperfect')
        self.assertEqual(response.status_code, 200)
        results = response.context['object_list']
        self.assertEqual(len(results), 1)

    def test_search_view_no_query(self):
        """Test search with no query returns all entries."""
        response = self.client.get(reverse('floppies:search-results'))
        self.assertEqual(response.status_code, 200)
        results = response.context['object_list']
        self.assertEqual(len(results), 2)


class EntryFormTest(TestCase):
    """Test the Entry form."""

    def test_form_fields_limited(self):
        """Test that form only exposes allowed fields."""
        from .forms import EntryForm
        form = EntryForm()

        # Check that safe fields are included
        self.assertIn('identifier', form.fields)
        self.assertIn('title', form.fields)
        self.assertIn('description', form.fields)

        # Check that internal fields are excluded
        self.assertNotIn('created_date', form.fields)
        self.assertNotIn('modified_date', form.fields)


class DuplicateDetectionTestCase(TestCase):
    """Test duplicate detection functionality for Entry model."""

    def setUp(self):
        """Create test entries with ZIP archives and content."""
        # Entry 1 with two files
        self.entry1 = Entry.objects.create(
            identifier="disk-001",
            title="Disk 1"
        )
        zip1 = ZipArchive.objects.create(
            archive="/path/to/disk1.zip",
            entry=self.entry1
        )
        ZipContent.objects.create(
            file="file1.txt",
            md5sum="abc123",
            suffix=".txt",
            zipArchive=zip1
        )
        ZipContent.objects.create(
            file="file2.txt",
            md5sum="def456",
            suffix=".txt",
            zipArchive=zip1
        )

        # Entry 2 with same files (exact duplicate)
        self.entry2 = Entry.objects.create(
            identifier="disk-002",
            title="Disk 2 (Duplicate of Disk 1)"
        )
        zip2 = ZipArchive.objects.create(
            archive="/path/to/disk2.zip",
            entry=self.entry2
        )
        ZipContent.objects.create(
            file="copy_file1.txt",
            md5sum="abc123",  # Same hash as entry1
            suffix=".txt",
            zipArchive=zip2
        )
        ZipContent.objects.create(
            file="copy_file2.txt",
            md5sum="def456",  # Same hash as entry1
            suffix=".txt",
            zipArchive=zip2
        )

        # Entry 3 with different files
        self.entry3 = Entry.objects.create(
            identifier="disk-003",
            title="Disk 3 (Different)"
        )
        zip3 = ZipArchive.objects.create(
            archive="/path/to/disk3.zip",
            entry=self.entry3
        )
        ZipContent.objects.create(
            file="other_file.txt",
            md5sum="xyz789",
            suffix=".txt",
            zipArchive=zip3
        )

        # Entry 4 with no ZIP archives
        self.entry4 = Entry.objects.create(
            identifier="disk-004",
            title="Disk 4 (No Files)"
        )

        # Entry 5 with partial overlap
        self.entry5 = Entry.objects.create(
            identifier="disk-005",
            title="Disk 5 (Partial Match)"
        )
        zip5 = ZipArchive.objects.create(
            archive="/path/to/disk5.zip",
            entry=self.entry5
        )
        ZipContent.objects.create(
            file="file1.txt",
            md5sum="abc123",  # Same as entry1's first file
            suffix=".txt",
            zipArchive=zip5
        )
        ZipContent.objects.create(
            file="different.txt",
            md5sum="ghi999",  # Different
            suffix=".txt",
            zipArchive=zip5
        )

    def test_get_file_hashes(self):
        """Test that get_file_hashes returns correct hash set."""
        hashes1 = self.entry1.get_file_hashes()
        self.assertEqual(len(hashes1), 2)
        self.assertIn("abc123", hashes1)
        self.assertIn("def456", hashes1)
        self.assertIsInstance(hashes1, frozenset)

    def test_get_file_hashes_empty(self):
        """Test get_file_hashes for entry with no files."""
        hashes = self.entry4.get_file_hashes()
        self.assertEqual(len(hashes), 0)
        self.assertIsInstance(hashes, frozenset)

    def test_is_duplicate_of_exact_match(self):
        """Test that exact duplicates are detected."""
        self.assertTrue(self.entry1.is_duplicate_of(self.entry2))
        self.assertTrue(self.entry2.is_duplicate_of(self.entry1))

    def test_is_duplicate_of_different(self):
        """Test that different entries are not duplicates."""
        self.assertFalse(self.entry1.is_duplicate_of(self.entry3))
        self.assertFalse(self.entry3.is_duplicate_of(self.entry1))

    def test_is_duplicate_of_partial_match(self):
        """Test that partial matches are not considered duplicates."""
        self.assertFalse(self.entry1.is_duplicate_of(self.entry5))
        self.assertFalse(self.entry5.is_duplicate_of(self.entry1))

    def test_is_duplicate_of_self(self):
        """Test that entry is not considered a duplicate of itself."""
        self.assertFalse(self.entry1.is_duplicate_of(self.entry1))

    def test_is_duplicate_of_no_files(self):
        """Test duplicate detection with entries that have no files."""
        self.assertFalse(self.entry1.is_duplicate_of(self.entry4))
        self.assertFalse(self.entry4.is_duplicate_of(self.entry1))
        self.assertFalse(self.entry4.is_duplicate_of(self.entry4))

    def test_is_duplicate_of_invalid_type(self):
        """Test that is_duplicate_of handles invalid input."""
        self.assertFalse(self.entry1.is_duplicate_of(None))
        self.assertFalse(self.entry1.is_duplicate_of("not an entry"))
        self.assertFalse(self.entry1.is_duplicate_of(123))

    def test_find_duplicates(self):
        """Test that find_duplicates finds all matching entries."""
        duplicates = self.entry1.find_duplicates()
        self.assertEqual(duplicates.count(), 1)
        self.assertIn(self.entry2, duplicates)
        self.assertNotIn(self.entry3, duplicates)
        self.assertNotIn(self.entry5, duplicates)

    def test_find_duplicates_returns_queryset(self):
        """Test that find_duplicates returns a QuerySet."""
        from django.db.models import QuerySet
        duplicates = self.entry1.find_duplicates()
        self.assertIsInstance(duplicates, QuerySet)

    def test_find_duplicates_no_matches(self):
        """Test find_duplicates when there are no duplicates."""
        duplicates = self.entry3.find_duplicates()
        self.assertEqual(duplicates.count(), 0)

    def test_find_duplicates_no_files(self):
        """Test find_duplicates for entry with no files."""
        duplicates = self.entry4.find_duplicates()
        self.assertEqual(duplicates.count(), 0)

    def test_mark_as_duplicate(self):
        """Test marking entries as duplicates."""
        result = self.entry1.mark_as_duplicate(self.entry2)
        self.assertTrue(result)

        # Check that relationship was created (symmetrical)
        self.assertIn(self.entry2, self.entry1.duplicates.all())
        self.assertIn(self.entry1, self.entry2.duplicates.all())

    def test_mark_as_duplicate_non_duplicate(self):
        """Test that marking non-duplicates returns False."""
        result = self.entry1.mark_as_duplicate(self.entry3)
        self.assertFalse(result)

        # Check that no relationship was created
        self.assertNotIn(self.entry3, self.entry1.duplicates.all())

    def test_mark_as_duplicate_idempotent(self):
        """Test that marking duplicates multiple times is idempotent."""
        self.entry1.mark_as_duplicate(self.entry2)
        self.entry1.mark_as_duplicate(self.entry2)

        # Should still only have one duplicate relationship
        self.assertEqual(self.entry1.duplicates.count(), 1)
        self.assertEqual(self.entry2.duplicates.count(), 1)

    def test_has_duplicates_true(self):
        """Test has_duplicates returns True when duplicates exist."""
        self.entry1.mark_as_duplicate(self.entry2)
        self.assertTrue(self.entry1.has_duplicates())
        self.assertTrue(self.entry2.has_duplicates())

    def test_has_duplicates_false(self):
        """Test has_duplicates returns False when no duplicates exist."""
        self.assertFalse(self.entry1.has_duplicates())
        self.assertFalse(self.entry3.has_duplicates())

    def test_clear_duplicates(self):
        """Test clearing duplicate relationships."""
        self.entry1.mark_as_duplicate(self.entry2)
        self.assertTrue(self.entry1.has_duplicates())

        self.entry1.duplicates.clear()
        self.assertFalse(self.entry1.has_duplicates())
        self.assertFalse(self.entry2.has_duplicates())  # Symmetrical

    def test_multiple_duplicates(self):
        """Test entry can have multiple duplicates."""
        # Create another exact duplicate
        entry6 = Entry.objects.create(
            identifier="disk-006",
            title="Disk 6 (Another Duplicate)"
        )
        zip6 = ZipArchive.objects.create(
            archive="/path/to/disk6.zip",
            entry=entry6
        )
        ZipContent.objects.create(
            file="another_file1.txt",
            md5sum="abc123",
            suffix=".txt",
            zipArchive=zip6
        )
        ZipContent.objects.create(
            file="another_file2.txt",
            md5sum="def456",
            suffix=".txt",
            zipArchive=zip6
        )

        # Mark both as duplicates
        self.entry1.mark_as_duplicate(self.entry2)
        self.entry1.mark_as_duplicate(entry6)

        self.assertEqual(self.entry1.duplicates.count(), 2)
        self.assertIn(self.entry2, self.entry1.duplicates.all())
        self.assertIn(entry6, self.entry1.duplicates.all())

    def test_hash_comparison_with_null_md5(self):
        """Test that entries with null MD5 sums are handled correctly."""
        entry7 = Entry.objects.create(
            identifier="disk-007",
            title="Disk 7 (Null MD5)"
        )
        zip7 = ZipArchive.objects.create(
            archive="/path/to/disk7.zip",
            entry=entry7
        )
        ZipContent.objects.create(
            file="no_hash.txt",
            md5sum=None,  # No hash
            suffix=".txt",
            zipArchive=zip7
        )

        hashes = entry7.get_file_hashes()
        self.assertEqual(len(hashes), 0)  # Null hashes should be excluded

    def test_duplicate_detection_with_multiple_zip_archives(self):
        """Test duplicate detection works with entries that have multiple ZIP archives."""
        entry8 = Entry.objects.create(
            identifier="disk-008",
            title="Disk 8 (Multiple ZIPs)"
        )
        # First ZIP
        zip8a = ZipArchive.objects.create(
            archive="/path/to/disk8a.zip",
            entry=entry8
        )
        ZipContent.objects.create(
            file="file1.txt",
            md5sum="abc123",
            suffix=".txt",
            zipArchive=zip8a
        )
        # Second ZIP
        zip8b = ZipArchive.objects.create(
            archive="/path/to/disk8b.zip",
            entry=entry8
        )
        ZipContent.objects.create(
            file="file2.txt",
            md5sum="def456",
            suffix=".txt",
            zipArchive=zip8b
        )

        # Should still detect as duplicate of entry1
        self.assertTrue(self.entry1.is_duplicate_of(entry8))
        self.assertTrue(entry8.is_duplicate_of(self.entry1))
