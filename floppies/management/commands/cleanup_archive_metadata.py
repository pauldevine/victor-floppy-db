"""
Django management command to clean up local metadata that drifted from Internet Archive.

Runs as a dry run by default; pass --apply to write changes. Two phases:

1. Local names (no network): merge Subject/Creator/Contributor/Language/
   ArchCollection rows whose names have stray whitespace (e.g. ' MS-DOS',
   left behind by splitting ';'-joined archive values) into the trimmed name.
2. Archive (one request per entry): for entries that exist on the archive,
   - replace local collections with the archive's (curators move items
     after upload, e.g. open_source_software -> vintagesoftware)
   - fix publicationDate: take the archive 'date' when it is a full date,
     and clear values that are only the archive upload date ('publicdate').

Usage:
    python manage.py cleanup_archive_metadata [--apply] [--identifier ID]
        [--skip-archive] [--limit N]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from floppies.models import Entry, Subject, Creator, Contributor, Language, ArchCollection
from floppies import archive_sync
import logging

logger = logging.getLogger(__name__)

# (model, Entry many-to-many field name)
NAMED_RELATIONS = [
    (Subject, 'subjects'),
    (Creator, 'creators'),
    (Contributor, 'contributors'),
    (Language, 'languages'),
    (ArchCollection, 'collections'),
]


class Command(BaseCommand):
    help = 'Clean up local metadata (whitespace names, stale collections, upload dates) against Internet Archive'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Write changes (default is a dry run that only reports)',
        )
        parser.add_argument(
            '--identifier',
            type=str,
            help='Only process a specific entry identifier in the archive phase',
        )
        parser.add_argument(
            '--skip-archive',
            action='store_true',
            help='Only run the local name cleanup; do not contact Internet Archive',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Process at most this many entries in the archive phase',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        identifier = options['identifier']

        if not apply:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made (use --apply to write)'))

        self._clean_names(apply)

        if options['skip_archive']:
            return

        try:
            archive_sync.check_ia_available()
        except archive_sync.ArchiveSyncError as e:
            raise CommandError(str(e))

        if identifier:
            queryset = Entry.objects.filter(identifier=identifier)
            if not queryset.exists():
                raise CommandError(f'Entry with identifier "{identifier}" not found')
        else:
            queryset = Entry.objects.order_by('identifier')
        if options['limit']:
            queryset = queryset[:options['limit']]

        self._clean_from_archive(queryset, apply)

        self.stdout.write('')
        self.stdout.write('Run "python manage.py check_archive_sync" afterwards to refresh sync status.')

    def _clean_names(self, apply):
        """Merge related rows whose names have leading/trailing whitespace into the trimmed name."""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Phase 1: names with stray whitespace'))

        total_rows = 0
        with transaction.atomic():
            for model, field in NAMED_RELATIONS:
                dirty = [obj for obj in model.objects.order_by('pk') if obj.name != obj.name.strip()]
                if not dirty:
                    continue

                self.stdout.write(f'  {model.__name__}: {len(dirty)} rows')
                for obj in dirty:
                    trimmed = obj.name.strip()
                    target = model.objects.filter(name=trimmed).exclude(pk=obj.pk).order_by('pk').first()
                    entries = Entry.objects.filter(**{field: obj})
                    entry_count = entries.count()

                    if target:
                        action = f'merge into existing #{target.pk}'
                    else:
                        action = 'rename'
                    self.stdout.write(f'    {obj.name!r} -> {trimmed!r} ({action}, {entry_count} entries)')

                    if not apply:
                        continue

                    if target:
                        for entry in entries:
                            getattr(entry, field).add(target)
                            getattr(entry, field).remove(obj)
                        obj.delete()
                    else:
                        obj.name = trimmed
                        obj.save()
                total_rows += len(dirty)

        if total_rows == 0:
            self.stdout.write('  None found.')
        else:
            verb = 'Cleaned' if apply else 'Would clean'
            self.stdout.write(self.style.SUCCESS(f'  {verb} {total_rows} rows'))

    def _clean_from_archive(self, queryset, apply):
        """Pull collections and fix publication dates for entries that exist on the archive."""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Phase 2: collections and dates from Internet Archive'))

        counts = {'checked': 0, 'not_on_archive': 0, 'collections': 0, 'dates_set': 0,
                  'dates_cleared': 0, 'dates_skipped': 0, 'errors': 0}

        total = queryset.count()
        for i, entry in enumerate(queryset, 1):
            if i % 10 == 0 or i == total:
                self.stdout.write(f'Progress: {i}/{total}', ending='\r')

            try:
                item = archive_sync.get_archive_item(entry.identifier)
            except archive_sync.ArchiveSyncError as e:
                counts['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  ❌ {entry.identifier}: {e}'))
                continue

            if not item:
                counts['not_on_archive'] += 1
                continue
            counts['checked'] += 1

            changes = self._entry_changes(entry, item.metadata, counts)
            if not changes:
                continue

            self.stdout.write(' ' * 50, ending='\r')  # Clear progress line
            self.stdout.write(f'  {entry.identifier}')
            for description, _ in changes:
                self.stdout.write(f'    {description}')

            if apply:
                with transaction.atomic():
                    for _, apply_change in changes:
                        apply_change()
                    entry.save()

        self.stdout.write(' ' * 50, ending='\r')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('  Changes applied:' if apply else '  Changes found (dry run):'))
        self.stdout.write(f'  Entries found on archive: {counts["checked"]}')
        self.stdout.write(f'  Not on archive (skipped): {counts["not_on_archive"]}')
        self.stdout.write(f'  Collections replaced from archive: {counts["collections"]}')
        self.stdout.write(f'  Dates set from archive: {counts["dates_set"]}')
        self.stdout.write(f'  Upload dates cleared: {counts["dates_cleared"]}')
        self.stdout.write(f'  Partial archive dates left for manual review: {counts["dates_skipped"]}')
        if counts['errors']:
            self.stdout.write(self.style.ERROR(f'  Errors: {counts["errors"]}'))

    def _entry_changes(self, entry, archive_meta, counts):
        """Return a list of (description, callable) changes needed for one entry."""
        changes = []

        # Collections: the archive is authoritative, since curators move items.
        archive_collections = archive_sync.split_values(archive_meta.get('collection'))
        local_collections = archive_sync.local_names(entry.collections)
        if archive_collections and set(archive_collections) != set(local_collections):
            counts['collections'] += 1

            def set_collections():
                entry.collections.set([
                    ArchCollection.objects.filter(name=name).order_by('pk').first()
                    or ArchCollection.objects.create(name=name)
                    for name in archive_collections
                ])
            changes.append((f'Collections: {sorted(local_collections)} -> {sorted(archive_collections)}',
                            set_collections))

        # Publication date
        archive_date = archive_sync.first_value(archive_meta.get('date'))
        parsed_date = archive_sync.parse_archive_date(archive_date)
        if parsed_date:
            if entry.publicationDate != parsed_date:
                counts['dates_set'] += 1
                changes.append((f'Date: {entry.publicationDate} -> {parsed_date} (archive date)',
                                lambda: setattr(entry, 'publicationDate', parsed_date)))
        elif archive_date:
            # Partial date such as '1984' cannot be stored in a DateField.
            if entry.publicationDate and not entry.publicationDate.isoformat().startswith(archive_date):
                counts['dates_skipped'] += 1
                self.stdout.write(self.style.WARNING(
                    f'  ⚠️  {entry.identifier}: archive date {archive_date!r} is partial; '
                    f'local {entry.publicationDate} left unchanged'))
        elif archive_sync.is_upload_date(entry.publicationDate, archive_meta):
            counts['dates_cleared'] += 1
            changes.append((f'Date: {entry.publicationDate} -> None (was the archive upload date)',
                            lambda: setattr(entry, 'publicationDate', None)))

        return changes
