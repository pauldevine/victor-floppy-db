"""
Django management command to find and mark duplicate disk entries.

This command scans all Entry records and identifies duplicates based on
MD5 hash comparison of all files in their ZIP archives.

Usage:
    python manage.py find_duplicates [--auto-mark] [--dry-run]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q
from floppies.models import Entry
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Find and optionally mark duplicate disk entries based on file hash comparison'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto-mark',
            action='store_true',
            help='Automatically mark duplicates without confirmation',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing duplicate marks before scanning',
        )
        parser.add_argument(
            '--identifier',
            type=str,
            help='Only check duplicates for a specific entry identifier',
        )

    def handle(self, *args, **options):
        auto_mark = options['auto_mark']
        dry_run = options['dry_run']
        clear = options['clear']
        identifier = options['identifier']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Clear existing marks if requested
        if clear:
            if dry_run:
                count = Entry.objects.filter(duplicates__isnull=False).distinct().count()
                self.stdout.write(f'Would clear duplicate marks for {count} entries')
            else:
                self.stdout.write('Clearing existing duplicate marks...')
                cleared_count = 0
                for entry in Entry.objects.filter(duplicates__isnull=False).distinct():
                    entry.duplicates.clear()
                    cleared_count += 1
                self.stdout.write(self.style.SUCCESS(f'Cleared {cleared_count} entries'))

        # Get queryset
        if identifier:
            queryset = Entry.objects.filter(identifier=identifier)
            if not queryset.exists():
                raise CommandError(f'Entry with identifier "{identifier}" not found')
            self.stdout.write(f'Checking duplicates for: {identifier}')
        else:
            # Only check entries that have ZIP archives
            queryset = Entry.objects.filter(ziparchives__isnull=False).distinct()
            self.stdout.write(f'Scanning {queryset.count()} entries with ZIP archives...')

        duplicates_found = []
        entries_processed = 0
        total_entries = queryset.count()

        for entry in queryset:
            entries_processed += 1

            # Progress indicator every 10 entries
            if entries_processed % 10 == 0:
                self.stdout.write(f'Progress: {entries_processed}/{total_entries}', ending='\r')

            # Find duplicates for this entry
            duplicate_entries = entry.find_duplicates()

            if duplicate_entries.exists():
                for duplicate in duplicate_entries:
                    # Store as tuple to avoid duplicates (A,B) and (B,A)
                    pair = tuple(sorted([entry.id, duplicate.id]))
                    if pair not in [d['pair'] for d in duplicates_found]:
                        duplicates_found.append({
                            'pair': pair,
                            'entry1': entry,
                            'entry2': duplicate,
                        })

        # Clear progress line
        self.stdout.write(' ' * 50, ending='\r')

        # Report results
        if not duplicates_found:
            self.stdout.write(self.style.SUCCESS('No duplicates found!'))
            return

        self.stdout.write(self.style.WARNING(f'\nFound {len(duplicates_found)} duplicate pairs:'))
        self.stdout.write('')

        for i, dup in enumerate(duplicates_found, 1):
            entry1 = dup['entry1']
            entry2 = dup['entry2']
            self.stdout.write(
                f'{i}. {self.style.HTTP_INFO(entry1.identifier)} ⟷ '
                f'{self.style.HTTP_INFO(entry2.identifier)}'
            )
            self.stdout.write(f'   "{entry1.title}" ⟷ "{entry2.title}"')

            # Show file count and sample hashes
            hashes1 = entry1.get_file_hashes()
            self.stdout.write(f'   {len(hashes1)} matching files')
            self.stdout.write('')

        # Mark duplicates if requested
        if auto_mark or (not dry_run and self._confirm_marking()):
            if dry_run:
                self.stdout.write(self.style.WARNING(
                    f'Would mark {len(duplicates_found)} duplicate pairs'
                ))
            else:
                marked_count = 0
                for dup in duplicates_found:
                    entry1 = dup['entry1']
                    entry2 = dup['entry2']
                    if entry1.mark_as_duplicate(entry2):
                        marked_count += 1

                self.stdout.write(self.style.SUCCESS(
                    f'\nMarked {marked_count} duplicate pairs'
                ))
        else:
            self.stdout.write(self.style.WARNING(
                '\nNo duplicates were marked. Use --auto-mark to mark automatically.'
            ))

    def _confirm_marking(self):
        """Ask user for confirmation before marking duplicates."""
        try:
            response = input('\nMark these as duplicates? [y/N]: ')
            return response.lower() in ['y', 'yes']
        except KeyboardInterrupt:
            self.stdout.write('\nCancelled.')
            return False
