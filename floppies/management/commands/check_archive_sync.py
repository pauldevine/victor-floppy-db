"""
Django management command to check and synchronize entries with Internet Archive.

This command can check sync status, pull from archive, or push to archive.

Usage:
    python manage.py check_archive_sync [--pull] [--push] [--identifier ID]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from floppies.models import Entry
from floppies import archive_sync
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check and synchronize Entry metadata with Internet Archive'

    def add_arguments(self, parser):
        parser.add_argument(
            '--identifier',
            type=str,
            help='Only check a specific entry identifier',
        )
        parser.add_argument(
            '--pull',
            action='store_true',
            help='Pull metadata from archive and update local entries (archive as source of truth)',
        )
        parser.add_argument(
            '--push',
            action='store_true',
            help='Push local metadata to archive (local as source of truth)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )
        parser.add_argument(
            '--out-of-sync-only',
            action='store_true',
            help='Only process entries that are already marked as out of sync',
        )
        parser.add_argument(
            '--uploaded-only',
            action='store_true',
            help='Only check entries that are marked as uploaded',
        )

    def handle(self, *args, **options):
        identifier = options['identifier']
        pull = options['pull']
        push = options['push']
        dry_run = options['dry_run']
        out_of_sync_only = options['out_of_sync_only']
        uploaded_only = options['uploaded_only']

        if pull and push:
            raise CommandError('Cannot use both --pull and --push. Choose one.')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Build queryset
        if identifier:
            queryset = Entry.objects.filter(identifier=identifier)
            if not queryset.exists():
                raise CommandError(f'Entry with identifier "{identifier}" not found')
            self.stdout.write(f'Processing entry: {identifier}')
        else:
            queryset = Entry.objects.all()
            if out_of_sync_only:
                queryset = queryset.filter(archive_sync_status=Entry.ArchiveSyncStatus.OUT_OF_SYNC)
                self.stdout.write(f'Processing {queryset.count()} out-of-sync entries')
            elif uploaded_only:
                queryset = queryset.filter(uploaded=True)
                self.stdout.write(f'Processing {queryset.count()} uploaded entries')
            else:
                self.stdout.write(f'Processing {queryset.count()} entries')

        # Execute appropriate action
        if pull:
            self._pull_from_archive(queryset, dry_run)
        elif push:
            self._push_to_archive(queryset, dry_run)
        else:
            self._check_sync_status(queryset)

    def _check_sync_status(self, queryset):
        """Check sync status for all entries."""
        self.stdout.write('Checking synchronization status with Internet Archive...')
        self.stdout.write('')

        def progress_callback(current, total):
            if current % 10 == 0 or current == total:
                self.stdout.write(f'Progress: {current}/{total}', ending='\r')

        try:
            summary = archive_sync.bulk_check_sync_status(queryset, progress_callback)

            # Clear progress line
            self.stdout.write(' ' * 50, ending='\r')

            # Display summary
            self.stdout.write(self.style.SUCCESS(f'\nSync Check Complete!'))
            self.stdout.write(f'Total entries checked: {summary["total"]}')
            self.stdout.write(self.style.SUCCESS(f'  ✅ In sync: {summary["in_sync"]}'))
            self.stdout.write(self.style.WARNING(f'  ⚠️  Out of sync: {summary["out_of_sync"]}'))
            self.stdout.write(self.style.HTTP_INFO(f'  📁 Local only: {summary["local_only"]}'))
            if summary['errors'] > 0:
                self.stdout.write(self.style.ERROR(f'  ❌ Errors: {summary["errors"]}'))

            # Show examples of out-of-sync entries
            if summary['out_of_sync'] > 0:
                self.stdout.write('')
                self.stdout.write(self.style.WARNING('Out-of-sync entries:'))
                out_of_sync_details = [
                    d for d in summary['details']
                    if d['status'] == Entry.ArchiveSyncStatus.OUT_OF_SYNC
                ]
                for detail in out_of_sync_details[:10]:  # Show first 10
                    self.stdout.write(f'  • {detail["identifier"]}')
                    for diff in detail['differences'][:3]:  # Show first 3 differences
                        self.stdout.write(f'    - {diff}')

                if len(out_of_sync_details) > 10:
                    self.stdout.write(f'  ... and {len(out_of_sync_details) - 10} more')

                self.stdout.write('')
                self.stdout.write('To fix these, run:')
                self.stdout.write('  python manage.py check_archive_sync --pull  (to pull from archive)')
                self.stdout.write('  python manage.py check_archive_sync --push  (to push to archive)')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during sync check: {e}'))
            logger.exception("Error during sync check")

    def _pull_from_archive(self, queryset, dry_run):
        """Pull metadata from archive to local entries."""
        action_text = "Would pull" if dry_run else "Pulling"
        self.stdout.write(f'{action_text} metadata from Internet Archive to local database...')
        self.stdout.write('')

        updated_count = 0
        error_count = 0
        no_change_count = 0

        total = queryset.count()
        for i, entry in enumerate(queryset, 1):
            if i % 10 == 0 or i == total:
                self.stdout.write(f'Progress: {i}/{total}', ending='\r')

            result = archive_sync.pull_from_archive(entry, dry_run=dry_run)

            if result['success']:
                if result['changes']:
                    updated_count += 1
                    self.stdout.write('')  # Clear progress line
                    self.stdout.write(self.style.SUCCESS(f'✅ {entry.identifier}'))
                    for change in result['changes'][:5]:  # Limit to first 5 changes
                        self.stdout.write(f'   {change}')
                else:
                    no_change_count += 1
            else:
                error_count += 1
                self.stdout.write('')  # Clear progress line
                self.stdout.write(self.style.ERROR(f'❌ {entry.identifier}: {result["error"]}'))

        # Clear progress line
        self.stdout.write(' ' * 50, ending='\r')

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'\n{"Preview complete!" if dry_run else "Pull complete!"}'))
        self.stdout.write(f'Total entries: {total}')
        self.stdout.write(self.style.SUCCESS(f'  ✅ Updated: {updated_count}'))
        self.stdout.write(f'  ⚪ No changes needed: {no_change_count}')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  ❌ Errors: {error_count}'))

        if dry_run and updated_count > 0:
            self.stdout.write('')
            self.stdout.write('Run without --dry-run to apply these changes.')

    def _push_to_archive(self, queryset, dry_run):
        """Push local metadata to archive."""
        action_text = "Would push" if dry_run else "Pushing"
        self.stdout.write(f'{action_text} local metadata to Internet Archive...')
        self.stdout.write('')

        updated_count = 0
        error_count = 0
        no_change_count = 0

        total = queryset.count()
        for i, entry in enumerate(queryset, 1):
            if i % 10 == 0 or i == total:
                self.stdout.write(f'Progress: {i}/{total}', ending='\r')

            result = archive_sync.push_to_archive(entry, dry_run=dry_run)

            if result['success']:
                if result['changes']:
                    updated_count += 1
                    self.stdout.write('')  # Clear progress line
                    self.stdout.write(self.style.SUCCESS(f'✅ {entry.identifier}'))
                    for change in result['changes'][:5]:  # Limit to first 5 changes
                        self.stdout.write(f'   {change}')
                else:
                    no_change_count += 1
            else:
                error_count += 1
                self.stdout.write('')  # Clear progress line
                self.stdout.write(self.style.ERROR(f'❌ {entry.identifier}: {result["error"]}'))

        # Clear progress line
        self.stdout.write(' ' * 50, ending='\r')

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'\n{"Preview complete!" if dry_run else "Push complete!"}'))
        self.stdout.write(f'Total entries: {total}')
        self.stdout.write(self.style.SUCCESS(f'  ✅ Updated: {updated_count}'))
        self.stdout.write(f'  ⚪ No changes needed: {no_change_count}')
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  ❌ Errors: {error_count}'))

        if dry_run and updated_count > 0:
            self.stdout.write('')
            self.stdout.write('Run without --dry-run to apply these changes.')
