"""
Utilities for synchronizing Entry data with Internet Archive.

This module provides functions to:
- Check sync status between local database and Internet Archive
- Pull metadata from Internet Archive to update local entries
- Push metadata from local entries to Internet Archive
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from django.utils import timezone

logger = logging.getLogger(__name__)

# Try to import internetarchive, but make it optional
try:
    import internetarchive as ia
    IA_AVAILABLE = True
except ImportError:
    IA_AVAILABLE = False
    logger.warning("internetarchive library not available. Archive sync features will be disabled.")


class ArchiveSyncError(Exception):
    """Custom exception for archive synchronization errors."""
    pass


def check_ia_available():
    """Check if Internet Archive library is available."""
    if not IA_AVAILABLE:
        raise ArchiveSyncError(
            "Internet Archive library is not installed. "
            "Install it with: pip install internetarchive"
        )


def get_archive_item(identifier: str):
    """
    Get an Internet Archive item by identifier.

    Args:
        identifier: The Internet Archive identifier

    Returns:
        internetarchive.Item object or None if not found

    Raises:
        ArchiveSyncError: If IA library is not available
    """
    check_ia_available()

    try:
        item = ia.get_item(identifier)
        # Check if item exists by checking if it has metadata
        if not item.exists:
            return None
        return item
    except Exception as e:
        logger.error(f"Error fetching archive item {identifier}: {e}")
        raise ArchiveSyncError(f"Failed to fetch item from Internet Archive: {e}")


def compare_metadata(entry, archive_item) -> Tuple[bool, List[str]]:
    """
    Compare local Entry metadata with Internet Archive item metadata.

    Args:
        entry: Entry model instance
        archive_item: internetarchive.Item object

    Returns:
        Tuple of (is_in_sync: bool, differences: List[str])
    """
    differences = []

    if not archive_item:
        return False, ["Item not found in Internet Archive"]

    # Get archive metadata
    archive_meta = archive_item.metadata

    # Compare title
    archive_title = archive_meta.get('title', '')
    if isinstance(archive_title, list):
        archive_title = archive_title[0] if archive_title else ''
    if entry.title != archive_title:
        differences.append(f"Title: local='{entry.title}' vs archive='{archive_title}'")

    # Compare description
    archive_desc = archive_meta.get('description', '')
    if isinstance(archive_desc, list):
        archive_desc = archive_desc[0] if archive_desc else ''
    # Strip HTML tags for comparison (local uses RichTextField)
    from django.utils.html import strip_tags
    local_desc = strip_tags(entry.description or '')
    if local_desc != archive_desc:
        differences.append(f"Description differs (length: local={len(local_desc)}, archive={len(archive_desc)})")

    # Compare mediatype
    archive_mediatype = archive_meta.get('mediatype', '')
    local_mediatype_name = entry.get_mediatype_display().lower()
    if local_mediatype_name != archive_mediatype:
        differences.append(f"Media type: local='{local_mediatype_name}' vs archive='{archive_mediatype}'")

    # Compare date
    archive_date = archive_meta.get('date', '')
    if isinstance(archive_date, list):
        archive_date = archive_date[0] if archive_date else ''
    local_date = entry.publicationDate.isoformat() if entry.publicationDate else ''
    if local_date != archive_date:
        differences.append(f"Date: local='{local_date}' vs archive='{archive_date}'")

    # Compare creators
    archive_creators = archive_meta.get('creator', [])
    if isinstance(archive_creators, str):
        archive_creators = [archive_creators]
    local_creators = [c.name for c in entry.creators.all()]
    if set(local_creators) != set(archive_creators):
        differences.append(f"Creators: local={local_creators} vs archive={archive_creators}")

    # Compare subjects
    archive_subjects = archive_meta.get('subject', [])
    if isinstance(archive_subjects, str):
        archive_subjects = [archive_subjects]
    local_subjects = [s.name for s in entry.subjects.all()]
    if set(local_subjects) != set(archive_subjects):
        differences.append(f"Subjects differ (local={len(local_subjects)}, archive={len(archive_subjects)})")

    # Compare collections
    archive_collections = archive_meta.get('collection', [])
    if isinstance(archive_collections, str):
        archive_collections = [archive_collections]
    local_collections = [c.name for c in entry.collections.all()]
    if set(local_collections) != set(archive_collections):
        differences.append(f"Collections differ (local={len(local_collections)}, archive={len(archive_collections)})")

    is_in_sync = len(differences) == 0
    return is_in_sync, differences


def check_entry_sync_status(entry) -> Dict:
    """
    Check the synchronization status of an Entry with Internet Archive.

    Args:
        entry: Entry model instance

    Returns:
        Dictionary with sync information:
        {
            'status': ArchiveSyncStatus value,
            'in_sync': bool,
            'differences': List[str],
            'archive_exists': bool,
            'error': Optional[str]
        }
    """
    from .models import Entry

    result = {
        'status': Entry.ArchiveSyncStatus.NEVER_CHECKED,
        'in_sync': False,
        'differences': [],
        'archive_exists': False,
        'error': None
    }

    try:
        check_ia_available()
    except ArchiveSyncError as e:
        result['status'] = Entry.ArchiveSyncStatus.ERROR
        result['error'] = str(e)
        return result

    try:
        # Get archive item
        archive_item = get_archive_item(entry.identifier)

        if not archive_item:
            result['status'] = Entry.ArchiveSyncStatus.LOCAL_ONLY
            result['differences'] = ["Item not found in Internet Archive"]
            return result

        result['archive_exists'] = True

        # Compare metadata
        is_in_sync, differences = compare_metadata(entry, archive_item)
        result['in_sync'] = is_in_sync
        result['differences'] = differences

        if is_in_sync:
            result['status'] = Entry.ArchiveSyncStatus.IN_SYNC
        else:
            result['status'] = Entry.ArchiveSyncStatus.OUT_OF_SYNC

    except Exception as e:
        logger.error(f"Error checking sync status for {entry.identifier}: {e}")
        result['status'] = Entry.ArchiveSyncStatus.ERROR
        result['error'] = str(e)

    return result


def pull_from_archive(entry, dry_run=False) -> Dict:
    """
    Pull metadata from Internet Archive and update local Entry.

    Args:
        entry: Entry model instance
        dry_run: If True, only show what would be changed without making changes

    Returns:
        Dictionary with update information:
        {
            'success': bool,
            'changes': List[str],
            'error': Optional[str]
        }
    """
    from .models import Creator, Subject, ArchCollection, Language

    result = {
        'success': False,
        'changes': [],
        'error': None
    }

    try:
        check_ia_available()

        # Get archive item
        archive_item = get_archive_item(entry.identifier)

        if not archive_item:
            result['error'] = "Item not found in Internet Archive"
            return result

        archive_meta = archive_item.metadata
        changes = []

        # Update title
        archive_title = archive_meta.get('title', '')
        if isinstance(archive_title, list):
            archive_title = archive_title[0] if archive_title else ''
        if entry.title != archive_title and archive_title:
            changes.append(f"Title: '{entry.title}' → '{archive_title}'")
            if not dry_run:
                entry.title = archive_title

        # Update description
        archive_desc = archive_meta.get('description', '')
        if isinstance(archive_desc, list):
            archive_desc = archive_desc[0] if archive_desc else ''
        if archive_desc:
            from django.utils.html import strip_tags
            local_desc = strip_tags(entry.description or '')
            if local_desc != archive_desc:
                changes.append(f"Description updated (length: {len(archive_desc)} chars)")
                if not dry_run:
                    entry.description = archive_desc

        # Update mediatype
        archive_mediatype = archive_meta.get('mediatype', '')
        if archive_mediatype:
            mediatype_key = entry.Mediatypes.get_mediatype_key(archive_mediatype)
            if entry.mediatype != mediatype_key:
                changes.append(f"Media type: {entry.get_mediatype_display()} → {archive_mediatype}")
                if not dry_run:
                    entry.mediatype = mediatype_key

        # Update date
        archive_date = archive_meta.get('date', '')
        if isinstance(archive_date, list):
            archive_date = archive_date[0] if archive_date else ''
        if archive_date:
            from datetime import datetime
            try:
                parsed_date = datetime.fromisoformat(archive_date.replace('Z', '+00:00')).date()
                if entry.publicationDate != parsed_date:
                    changes.append(f"Date: {entry.publicationDate} → {parsed_date}")
                    if not dry_run:
                        entry.publicationDate = parsed_date
            except ValueError:
                pass  # Skip invalid dates

        # Update creators
        archive_creators = archive_meta.get('creator', [])
        if isinstance(archive_creators, str):
            archive_creators = [archive_creators]
        if archive_creators:
            local_creator_names = [c.name for c in entry.creators.all()]
            if set(local_creator_names) != set(archive_creators):
                changes.append(f"Creators: {len(archive_creators)} from archive")
                if not dry_run:
                    entry.creators.clear()
                    for creator_name in archive_creators:
                        creator, _ = Creator.objects.get_or_create(name=creator_name)
                        entry.creators.add(creator)

        # Update subjects
        archive_subjects = archive_meta.get('subject', [])
        if isinstance(archive_subjects, str):
            archive_subjects = [archive_subjects]
        if archive_subjects:
            local_subject_names = [s.name for s in entry.subjects.all()]
            if set(local_subject_names) != set(archive_subjects):
                changes.append(f"Subjects: {len(archive_subjects)} from archive")
                if not dry_run:
                    entry.subjects.clear()
                    for subject_name in archive_subjects:
                        subject, _ = Subject.objects.get_or_create(name=subject_name)
                        entry.subjects.add(subject)

        # Update collections
        archive_collections = archive_meta.get('collection', [])
        if isinstance(archive_collections, str):
            archive_collections = [archive_collections]
        if archive_collections:
            local_collection_names = [c.name for c in entry.collections.all()]
            if set(local_collection_names) != set(archive_collections):
                changes.append(f"Collections: {len(archive_collections)} from archive")
                if not dry_run:
                    entry.collections.clear()
                    for collection_name in archive_collections:
                        collection, _ = ArchCollection.objects.get_or_create(name=collection_name)
                        entry.collections.add(collection)

        if not dry_run and changes:
            entry.last_archive_sync = timezone.now()
            entry.archive_sync_status = entry.ArchiveSyncStatus.IN_SYNC
            entry.sync_notes = f"Pulled from archive: {', '.join(changes)}"
            entry.save()

        result['success'] = True
        result['changes'] = changes

    except Exception as e:
        logger.error(f"Error pulling from archive for {entry.identifier}: {e}")
        result['error'] = str(e)

    return result


def push_to_archive(entry, dry_run=False) -> Dict:
    """
    Push local Entry metadata to Internet Archive.

    Args:
        entry: Entry model instance
        dry_run: If True, only show what would be changed without making changes

    Returns:
        Dictionary with update information:
        {
            'success': bool,
            'changes': List[str],
            'error': Optional[str]
        }
    """
    result = {
        'success': False,
        'changes': [],
        'error': None
    }

    try:
        check_ia_available()

        # Get archive item (or create if it doesn't exist)
        archive_item = get_archive_item(entry.identifier)

        if not archive_item:
            result['error'] = "Item not found in Internet Archive. Cannot push to non-existent item."
            return result

        # Prepare metadata for upload
        metadata = {}
        changes = []

        if entry.title:
            metadata['title'] = entry.title
            changes.append(f"Title: {entry.title}")

        if entry.description:
            from django.utils.html import strip_tags
            metadata['description'] = strip_tags(entry.description)
            changes.append(f"Description: {len(metadata['description'])} chars")

        if entry.mediatype:
            metadata['mediatype'] = entry.get_mediatype_display().lower()
            changes.append(f"Media type: {metadata['mediatype']}")

        if entry.publicationDate:
            metadata['date'] = entry.publicationDate.isoformat()
            changes.append(f"Date: {metadata['date']}")

        # Add creators
        creators = [c.name for c in entry.creators.all()]
        if creators:
            metadata['creator'] = creators
            changes.append(f"Creators: {len(creators)}")

        # Add subjects
        subjects = [s.name for s in entry.subjects.all()]
        if subjects:
            metadata['subject'] = subjects
            changes.append(f"Subjects: {len(subjects)}")

        # Add collections
        collections = [c.name for c in entry.collections.all()]
        if collections:
            metadata['collection'] = collections
            changes.append(f"Collections: {len(collections)}")

        # Add contributors
        contributors = [c.name for c in entry.contributors.all()]
        if contributors:
            metadata['contributor'] = contributors
            changes.append(f"Contributors: {len(contributors)}")

        # Add languages
        languages = [lang.name for lang in entry.languages.all()]
        if languages:
            metadata['language'] = languages
            changes.append(f"Languages: {len(languages)}")

        if not dry_run:
            # Push metadata to archive
            archive_item.modify_metadata(metadata)

            entry.last_archive_sync = timezone.now()
            entry.archive_sync_status = entry.ArchiveSyncStatus.IN_SYNC
            entry.sync_notes = f"Pushed to archive: {', '.join(changes)}"
            entry.save()

        result['success'] = True
        result['changes'] = changes

    except Exception as e:
        logger.error(f"Error pushing to archive for {entry.identifier}: {e}")
        result['error'] = str(e)

    return result


def bulk_check_sync_status(entries, progress_callback=None) -> Dict:
    """
    Check sync status for multiple entries.

    Args:
        entries: QuerySet or list of Entry instances
        progress_callback: Optional callable(current, total) for progress updates

    Returns:
        Dictionary with summary:
        {
            'total': int,
            'in_sync': int,
            'out_of_sync': int,
            'local_only': int,
            'errors': int,
            'details': List[Dict]
        }
    """
    summary = {
        'total': 0,
        'in_sync': 0,
        'out_of_sync': 0,
        'local_only': 0,
        'errors': 0,
        'details': []
    }

    total = len(entries) if hasattr(entries, '__len__') else entries.count()

    for i, entry in enumerate(entries, 1):
        if progress_callback:
            progress_callback(i, total)

        status_info = check_entry_sync_status(entry)

        # Update entry with check results
        entry.last_sync_check = timezone.now()
        entry.archive_sync_status = status_info['status']
        if status_info['differences']:
            entry.sync_notes = '\n'.join(status_info['differences'])
        entry.save()

        summary['total'] += 1

        if status_info['status'] == entry.ArchiveSyncStatus.IN_SYNC:
            summary['in_sync'] += 1
        elif status_info['status'] == entry.ArchiveSyncStatus.OUT_OF_SYNC:
            summary['out_of_sync'] += 1
        elif status_info['status'] == entry.ArchiveSyncStatus.LOCAL_ONLY:
            summary['local_only'] += 1
        elif status_info['status'] == entry.ArchiveSyncStatus.ERROR:
            summary['errors'] += 1

        summary['details'].append({
            'identifier': entry.identifier,
            'status': status_info['status'],
            'differences': status_info['differences']
        })

    return summary
