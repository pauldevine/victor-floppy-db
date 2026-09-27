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


def first_value(value) -> str:
    """Return a single string from an archive metadata value (which may be a list)."""
    if isinstance(value, list):
        value = value[0] if value else ''
    return (value or '').strip()


def split_values(value) -> List[str]:
    """
    Normalize a multi-valued archive field into a list of clean names.

    Internet Archive stores repeated fields either as a list or as a single
    ';'-separated string (e.g. "Victor 9000; ACT Sirius 1"), so both forms are
    split and stripped.
    """
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    names = []
    for item in value:
        names.extend(part.strip() for part in str(item).split(';'))
    return [name for name in names if name]


def local_names(related_manager) -> List[str]:
    """Return stripped names from an Entry many-to-many relation."""
    return [obj.name.strip() for obj in related_manager.all() if obj.name and obj.name.strip()]


def parse_archive_date(archive_date: str):
    """
    Parse an archive 'date' value into a date, or None if it is empty or partial.

    Archive dates may be 'YYYY', 'YYYY-MM', 'YYYY-MM-DD' or a full timestamp;
    only values with a full day can be stored in a DateField.
    """
    if len(archive_date) < 10:
        return None
    try:
        return datetime.fromisoformat(archive_date[:10]).date()
    except ValueError:
        return None


def is_upload_date(local_date, archive_meta) -> bool:
    """
    True if a local publicationDate is really the archive upload date.

    Older imports copied the archive's 'publicdate' (when the item was uploaded)
    into publicationDate, so that value does not describe the software itself.
    """
    if not local_date:
        return False
    return first_value(archive_meta.get('publicdate'))[:10] == local_date.isoformat()


def _format_set_difference(label, local, archive) -> str:
    only_local = sorted(set(local) - set(archive))
    only_archive = sorted(set(archive) - set(local))
    return f"{label}: only local={only_local}, only archive={only_archive}"


def compare_metadata(entry, archive_item) -> Tuple[bool, List[str]]:
    """
    Compare local Entry metadata with Internet Archive item metadata.

    Values are normalized before comparison so that storage differences
    (';'-joined vs list values, surrounding whitespace, missing optional
    fields) are not reported as drift.

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
    archive_title = first_value(archive_meta.get('title'))
    local_title = (entry.title or '').strip()
    if local_title != archive_title:
        differences.append(f"Title: local='{local_title}' vs archive='{archive_title}'")

    # Compare description. Both sides store the same HTML, so compare it as-is.
    archive_desc = first_value(archive_meta.get('description'))
    local_desc = (entry.description or '').strip()
    if local_desc != archive_desc:
        differences.append(f"Description differs (length: local={len(local_desc)}, archive={len(archive_desc)})")

    # Compare mediatype
    archive_mediatype = first_value(archive_meta.get('mediatype')).lower()
    local_mediatype_name = entry.get_mediatype_display().lower()
    if local_mediatype_name != archive_mediatype:
        differences.append(f"Media type: local='{local_mediatype_name}' vs archive='{archive_mediatype}'")

    # Compare date. The archive may hold a partial date ('1984'), so match at
    # the archive's precision. A local value equal to the upload date is not a
    # real publication date and is ignored when the archive has no date.
    archive_date = first_value(archive_meta.get('date'))
    local_date = entry.publicationDate.isoformat() if entry.publicationDate else ''
    if archive_date:
        if not local_date.startswith(archive_date[:10]):
            note = " (local is the archive upload date)" if is_upload_date(entry.publicationDate, archive_meta) else ""
            differences.append(f"Date: local='{local_date}' vs archive='{archive_date}'{note}")
    elif local_date and not is_upload_date(entry.publicationDate, archive_meta):
        differences.append(f"Date: local='{local_date}' vs archive has no date")

    # Compare creators
    archive_creators = split_values(archive_meta.get('creator'))
    local_creators = local_names(entry.creators)
    if set(local_creators) != set(archive_creators):
        differences.append(_format_set_difference("Creators", local_creators, archive_creators))

    # Compare subjects
    archive_subjects = split_values(archive_meta.get('subject'))
    local_subjects = local_names(entry.subjects)
    if set(local_subjects) != set(archive_subjects):
        differences.append(_format_set_difference("Subjects", local_subjects, archive_subjects))

    # Compare collections. Archive curators can move items between
    # collections after upload, so a difference here usually means the local
    # copy is stale.
    archive_collections = split_values(archive_meta.get('collection'))
    local_collections = local_names(entry.collections)
    if set(local_collections) != set(archive_collections):
        differences.append(_format_set_difference("Collections", local_collections, archive_collections))

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
        archive_title = first_value(archive_meta.get('title'))
        if (entry.title or '').strip() != archive_title and archive_title:
            changes.append(f"Title: '{entry.title}' → '{archive_title}'")
            if not dry_run:
                entry.title = archive_title

        # Update description
        archive_desc = first_value(archive_meta.get('description'))
        if archive_desc and (entry.description or '').strip() != archive_desc:
            changes.append(f"Description updated (length: {len(archive_desc)} chars)")
            if not dry_run:
                entry.description = archive_desc

        # Update mediatype
        archive_mediatype = first_value(archive_meta.get('mediatype'))
        if archive_mediatype:
            mediatype_key = entry.Mediatypes.get_mediatype_key(archive_mediatype)
            if entry.mediatype != mediatype_key:
                changes.append(f"Media type: {entry.get_mediatype_display()} → {archive_mediatype}")
                if not dry_run:
                    entry.mediatype = mediatype_key

        # Update date
        parsed_date = parse_archive_date(first_value(archive_meta.get('date')))
        if parsed_date and entry.publicationDate != parsed_date:
            changes.append(f"Date: {entry.publicationDate} → {parsed_date}")
            if not dry_run:
                entry.publicationDate = parsed_date

        # Update creators
        archive_creators = split_values(archive_meta.get('creator'))
        if archive_creators:
            if set(local_names(entry.creators)) != set(archive_creators):
                changes.append(f"Creators: {len(archive_creators)} from archive")
                if not dry_run:
                    entry.creators.clear()
                    for creator_name in archive_creators:
                        creator, _ = Creator.objects.get_or_create(name=creator_name)
                        entry.creators.add(creator)

        # Update subjects
        archive_subjects = split_values(archive_meta.get('subject'))
        if archive_subjects:
            if set(local_names(entry.subjects)) != set(archive_subjects):
                changes.append(f"Subjects: {len(archive_subjects)} from archive")
                if not dry_run:
                    entry.subjects.clear()
                    for subject_name in archive_subjects:
                        subject, _ = Subject.objects.get_or_create(name=subject_name)
                        entry.subjects.add(subject)

        # Update collections
        archive_collections = split_values(archive_meta.get('collection'))
        if archive_collections:
            if set(local_names(entry.collections)) != set(archive_collections):
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
            # Send the HTML as stored; the archive renders it in the description.
            metadata['description'] = entry.description
            changes.append(f"Description: {len(metadata['description'])} chars")

        if entry.mediatype:
            metadata['mediatype'] = entry.get_mediatype_display().lower()
            changes.append(f"Media type: {metadata['mediatype']}")

        # Skip a publicationDate that is only the archive upload date, so it
        # never overwrites (or invents) a real publication date on the archive.
        if entry.publicationDate and not is_upload_date(entry.publicationDate, archive_item.metadata):
            metadata['date'] = entry.publicationDate.isoformat()
            changes.append(f"Date: {metadata['date']}")

        # Add creators
        creators = local_names(entry.creators)
        if creators:
            metadata['creator'] = creators
            changes.append(f"Creators: {len(creators)}")

        # Add subjects
        subjects = local_names(entry.subjects)
        if subjects:
            metadata['subject'] = subjects
            changes.append(f"Subjects: {len(subjects)}")

        # Add collections
        collections = local_names(entry.collections)
        if collections:
            metadata['collection'] = collections
            changes.append(f"Collections: {len(collections)}")

        # Add contributors
        contributors = local_names(entry.contributors)
        if contributors:
            metadata['contributor'] = contributors
            changes.append(f"Contributors: {len(contributors)}")

        # Add languages
        languages = local_names(entry.languages)
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
