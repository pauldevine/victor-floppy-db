"""
Integration tests for the floppies app.
Tests complete workflows and interactions between components.
"""
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from pathlib import Path
import tempfile
import os

from .models import (
    Entry, Creator, ArchCollection, Language, Subject,
    ZipArchive, ZipContent, FluxFile, PhotoImage, ScriptRun
)


class EntryWorkflowIntegrationTest(TestCase):
    """Test complete entry creation and management workflow."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_complete_entry_creation_workflow(self):
        """Test creating an entry with all relationships."""
        # Create related objects
        creator = Creator.objects.create(name="Test Creator")
        collection = ArchCollection.objects.create(name="test_collection")
        language = Language.objects.create(name="English")
        subject = Subject.objects.create(name="Victor 9000")

        # Create entry with relationships
        entry = Entry.objects.create(
            identifier="test-workflow-disk",
            title="Test Workflow Disk",
            description="Complete workflow test",
            mediatype=Entry.Mediatypes.SOFTWARE,
            needsWork=True
        )

        # Add many-to-many relationships
        entry.creators.add(creator)
        entry.collections.add(collection)
        entry.languages.add(language)
        entry.subjects.add(subject)

        # Create ZIP archive
        zip_archive = ZipArchive.objects.create(
            archive="/test/path/test.zip",
            entry=entry
        )

        # Create ZIP contents
        zip_content1 = ZipContent.objects.create(
            zipArchive=zip_archive,
            file="file1.txt",
            md5sum="abc123",
            suffix=".txt",
            size_bytes=1024
        )

        zip_content2 = ZipContent.objects.create(
            zipArchive=zip_archive,
            file="disk.a2r",
            md5sum="def456",
            suffix=".a2r",
            size_bytes=2048
        )

        # Create FluxFile for .a2r file
        flux_file = FluxFile.objects.create(
            zipContent=zip_content2,
            file="disk.a2r"
        )

        # Create photos
        photo = PhotoImage.objects.create(
            entry=entry,
            image="/test/path/front.jpg"
        )

        # Verify complete structure
        self.assertEqual(entry.creators.count(), 1)
        self.assertEqual(entry.collections.count(), 1)
        self.assertEqual(entry.languages.count(), 1)
        self.assertEqual(entry.subjects.count(), 1)
        self.assertEqual(entry.ziparchives.count(), 1)
        self.assertEqual(entry.photos.count(), 1)

        # Verify media files retrieval
        media_files = entry.get_media_files()
        self.assertEqual(len(media_files), 2)  # 1 zip + 1 photo
        self.assertIn("/test/path/test.zip", media_files)
        self.assertIn("/test/path/front.jpg", media_files)

        # Verify ZIP contents
        contents = zip_archive.zipcontent_set.all()
        self.assertEqual(contents.count(), 2)

        # Verify FluxFile exists for .a2r file
        self.assertTrue(hasattr(zip_content2, 'fluxfile'))


    def test_entry_status_workflow(self):
        """Test entry status progression workflow."""
        entry = Entry.objects.create(
            identifier="status-test",
            title="Status Test Disk",
            needsWork=True,
            readyToUpload=False,
            uploaded=False
        )

        # Initial state
        self.assertTrue(entry.needsWork)
        self.assertFalse(entry.readyToUpload)
        self.assertFalse(entry.uploaded)

        # Mark as ready to upload
        entry.needsWork = False
        entry.readyToUpload = True
        entry.save()

        entry.refresh_from_db()
        self.assertFalse(entry.needsWork)
        self.assertTrue(entry.readyToUpload)

        # Mark as uploaded
        entry.uploaded = True
        entry.save()

        entry.refresh_from_db()
        self.assertTrue(entry.uploaded)


    def test_entry_deletion_cascade(self):
        """Test that deleting an entry cascades to related objects."""
        entry = Entry.objects.create(
            identifier="cascade-test",
            title="Cascade Test"
        )

        # Create related objects
        zip_archive = ZipArchive.objects.create(
            archive="/test/cascade.zip",
            entry=entry
        )

        photo = PhotoImage.objects.create(
            entry=entry,
            image="/test/photo.jpg"
        )

        script_run = ScriptRun.objects.create(
            entry=entry,
            text="Test run"
        )

        # Get IDs
        zip_id = zip_archive.id
        photo_id = photo.id
        script_id = script_run.id

        # Delete entry
        entry.delete()

        # Verify cascade deletion
        self.assertFalse(ZipArchive.objects.filter(id=zip_id).exists())
        self.assertFalse(PhotoImage.objects.filter(id=photo_id).exists())
        self.assertFalse(ScriptRun.objects.filter(id=script_id).exists())


class SearchAndFilterIntegrationTest(TestCase):
    """Test search and filter functionality."""

    def setUp(self):
        """Create test entries with various attributes."""
        # Create entries with different statuses
        for i in range(10):
            Entry.objects.create(
                identifier=f"disk-{i:02d}",
                title=f"Disk {i:02d}",
                needsWork=(i % 2 == 0),
                readyToUpload=(i % 3 == 0),
                uploaded=(i % 4 == 0)
            )

        # Create specific searchable entries
        Entry.objects.create(
            identifier="wordperfect-5-1",
            title="WordPerfect 5.1"
        )

        Entry.objects.create(
            identifier="lotus-123",
            title="Lotus 1-2-3"
        )

    def test_search_by_title(self):
        """Test searching entries by title."""
        response = self.client.get(
            reverse('floppies:search-results') + '?q=WordPerfect'
        )

        self.assertEqual(response.status_code, 200)
        results = response.context['object_list']
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].title, "WordPerfect 5.1")

    def test_search_by_identifier(self):
        """Test searching entries by identifier."""
        response = self.client.get(
            reverse('floppies:search-results') + '?q=lotus'
        )

        self.assertEqual(response.status_code, 200)
        results = response.context['object_list']
        self.assertEqual(results.count(), 1)
        self.assertEqual(results[0].identifier, "lotus-123")

    def test_filter_needs_work(self):
        """Test filtering by needsWork status."""
        response = self.client.get(
            reverse('floppies:index') + '?needswork=true'
        )

        self.assertEqual(response.status_code, 200)
        entries = response.context['latest_entry_list']

        # All should have needsWork=True
        for entry in entries:
            self.assertTrue(entry.needsWork)

    def test_filter_next_upload(self):
        """Test filtering entries ready for upload."""
        response = self.client.get(
            reverse('floppies:index') + '?nextupload=true'
        )

        self.assertEqual(response.status_code, 200)
        entries = response.context['latest_entry_list']

        # All should be ready to upload and not uploaded
        for entry in entries:
            self.assertTrue(entry.readyToUpload)
            self.assertFalse(entry.needsWork)
            self.assertFalse(entry.uploaded)

    def test_combined_filters(self):
        """Test that multiple filters work together correctly."""
        # Get all entries ready to upload
        ready_entries = Entry.objects.filter(
            readyToUpload=True,
            needsWork=False,
            uploaded=False
        )

        self.assertGreater(ready_entries.count(), 0)


class AdminActionsIntegrationTest(TestCase):
    """Test Django admin custom actions."""

    def setUp(self):
        """Set up admin user and test entries."""
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        self.client = Client()
        self.client.login(username='admin', password='admin123')

        # Create test entries
        for i in range(5):
            Entry.objects.create(
                identifier=f"admin-test-{i}",
                title=f"Admin Test {i}",
                needsWork=True,
                readyToUpload=False,
                uploaded=False
            )

    def test_bulk_mark_ready_to_upload(self):
        """Test bulk action to mark entries as ready to upload."""
        entries = Entry.objects.all()
        entry_ids = [str(e.id) for e in entries]

        # Simulate admin action
        response = self.client.post(
            reverse('admin:floppies_entry_changelist'),
            {
                'action': 'mark_ready_to_upload',
                '_selected_action': entry_ids,
            },
            follow=True
        )

        self.assertEqual(response.status_code, 200)

        # Verify all entries are now ready to upload
        for entry in Entry.objects.all():
            entry.refresh_from_db()
            self.assertTrue(entry.readyToUpload)
            self.assertFalse(entry.needsWork)


class ZipArchiveIntegrationTest(TestCase):
    """Test ZIP archive handling and relationships."""

    def test_zip_with_multiple_file_types(self):
        """Test ZIP archive with various file types."""
        entry = Entry.objects.create(
            identifier="mixed-files",
            title="Mixed Files Disk"
        )

        zip_archive = ZipArchive.objects.create(
            archive="/test/mixed.zip",
            entry=entry
        )

        # Create various file types
        files = [
            ("readme.txt", ".txt", 100),
            ("program.exe", ".exe", 50000),
            ("disk.a2r", ".a2r", 200000),
            ("photo.jpg", ".jpg", 150000),
            ("data.bin", ".bin", 30000),
        ]

        created_contents = []
        for filename, suffix, size in files:
            content = ZipContent.objects.create(
                zipArchive=zip_archive,
                file=filename,
                md5sum=f"md5_{filename}",
                suffix=suffix,
                size_bytes=size
            )
            created_contents.append(content)

        # Create FluxFile for .a2r
        a2r_content = created_contents[2]
        FluxFile.objects.create(
            zipContent=a2r_content,
            file="disk.a2r"
        )

        # Verify structure
        self.assertEqual(zip_archive.zipcontent_set.count(), 5)

        # Verify flux file exists only for .a2r
        for content in created_contents:
            if content.suffix == ".a2r":
                self.assertTrue(hasattr(content, 'fluxfile'))
            else:
                self.assertFalse(hasattr(content, 'fluxfile'))


class PaginationIntegrationTest(TestCase):
    """Test pagination across multiple pages."""

    def setUp(self):
        """Create enough entries to span multiple pages."""
        for i in range(75):  # 3 pages worth (25 per page)
            Entry.objects.create(
                identifier=f"page-test-{i:03d}",
                title=f"Page Test {i:03d}"
            )

    def test_pagination_first_page(self):
        """Test first page of results."""
        response = self.client.get(reverse('floppies:index'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['latest_entry_list']), 25)
        self.assertTrue(response.context['page_obj'].has_next())
        self.assertFalse(response.context['page_obj'].has_previous())

    def test_pagination_middle_page(self):
        """Test middle page of results."""
        response = self.client.get(reverse('floppies:index') + '?page=2')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['latest_entry_list']), 25)
        self.assertTrue(response.context['page_obj'].has_next())
        self.assertTrue(response.context['page_obj'].has_previous())

    def test_pagination_last_page(self):
        """Test last page of results."""
        response = self.client.get(reverse('floppies:index') + '?page=3')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['latest_entry_list']), 25)
        self.assertFalse(response.context['page_obj'].has_next())
        self.assertTrue(response.context['page_obj').has_previous())


class EdgeCaseTest(TestCase):
    """Test edge cases and boundary conditions."""

    def test_entry_with_empty_strings(self):
        """Test entry creation with empty strings."""
        entry = Entry.objects.create(
            identifier="",
            title=""
        )

        self.assertEqual(entry.identifier, "")
        self.assertEqual(entry.title, "")

    def test_entry_with_very_long_identifier(self):
        """Test entry with maximum length identifier."""
        long_id = "a" * 500  # Max length
        entry = Entry.objects.create(
            identifier=long_id,
            title="Long ID Test"
        )

        self.assertEqual(len(entry.identifier), 500)

    def test_zip_content_with_no_suffix(self):
        """Test ZIP content without file extension."""
        entry = Entry.objects.create(
            identifier="no-suffix-test",
            title="No Suffix Test"
        )

        zip_archive = ZipArchive.objects.create(
            archive="/test/nosuffix.zip",
            entry=entry
        )

        content = ZipContent.objects.create(
            zipArchive=zip_archive,
            file="README",  # No extension
            suffix=None,
            size_bytes=0
        )

        self.assertIsNone(content.suffix)

    def test_entry_get_media_files_with_no_files(self):
        """Test get_media_files on entry with no media."""
        entry = Entry.objects.create(
            identifier="no-media",
            title="No Media Test"
        )

        media_files = entry.get_media_files()
        self.assertEqual(len(media_files), 0)

    def test_multiple_zip_archives_per_entry(self):
        """Test entry with multiple ZIP archives."""
        entry = Entry.objects.create(
            identifier="multi-zip",
            title="Multiple ZIPs"
        )

        for i in range(3):
            ZipArchive.objects.create(
                archive=f"/test/archive{i}.zip",
                entry=entry
            )

        self.assertEqual(entry.ziparchives.count(), 3)

        media_files = entry.get_media_files()
        self.assertEqual(len(media_files), 3)

    def test_script_run_with_very_long_text(self):
        """Test ScriptRun with large text output."""
        entry = Entry.objects.create(
            identifier="large-output",
            title="Large Output Test"
        )

        # Create large text (simulating a long script output)
        large_text = "x" * 10000

        script_run = ScriptRun.objects.create(
            entry=entry,
            text=large_text,
            script="long_running_script.py"
        )

        self.assertEqual(len(script_run.text), 10000)
