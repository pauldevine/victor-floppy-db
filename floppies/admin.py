from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Entry, Creator, ArchCollection, Contributor, FluxFile, Language,
    PhotoImage, RandoFile, Subject, TextFile, ZipArchive, ZipContent,
    ScriptRun, InfoChunk, MetaChunk
)
from . import archive_sync


class HasDuplicatesFilter(admin.SimpleListFilter):
    """Custom filter to show entries with or without duplicates."""
    title = 'has duplicates'
    parameter_name = 'has_duplicates'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(duplicates__isnull=False).distinct()
        if self.value() == 'no':
            return queryset.filter(duplicates__isnull=True)


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    """Enhanced admin for Entry model with search, filters, and better display."""
    list_display = ['identifier', 'title', 'mediatype', 'uploaded', 'needsWork', 'readyToUpload',
                    'duplicate_badge', 'sync_status_badge', 'modified_date']
    list_filter = ['uploaded', 'needsWork', 'readyToUpload', 'mediatype', 'hasFluxFile', 'hasFileContents',
                   'archive_sync_status', HasDuplicatesFilter]
    search_fields = ['identifier', 'title', 'description']
    date_hierarchy = 'modified_date'
    filter_horizontal = ['creators', 'collections', 'contributors', 'languages', 'subjects', 'duplicates']
    readonly_fields = ['created_date', 'modified_date', 'last_sync_check', 'last_archive_sync']
    fieldsets = (
        ('Identification', {
            'fields': ('identifier', 'title', 'folder', 'fullArchivePath')
        }),
        ('Metadata', {
            'fields': ('mediatype', 'publicationDate', 'description', 'creators', 'contributors', 'subjects', 'languages', 'collections')
        }),
        ('Status Flags', {
            'fields': ('uploaded', 'needsWork', 'readyToUpload', 'hasFluxFile', 'hasFileContents', 'hasDiskImg')
        }),
        ('Archive Synchronization', {
            'fields': ('archive_sync_status', 'last_sync_check', 'last_archive_sync', 'sync_notes'),
            'classes': ('collapse',),
            'description': 'Synchronization status with Internet Archive'
        }),
        ('Duplicates', {
            'fields': ('duplicates',),
            'classes': ('collapse',),
            'description': 'Entries that contain exactly the same files (based on MD5 hashes)'
        }),
        ('Timestamps', {
            'fields': ('created_date', 'modified_date'),
            'classes': ('collapse',)
        }),
    )
    actions = [
        'mark_ready_to_upload', 'mark_needs_work', 'mark_uploaded',
        'find_and_mark_duplicates', 'clear_duplicate_marks',
        'check_archive_sync', 'pull_from_archive', 'push_to_archive'
    ]

    def duplicate_badge(self, obj):
        """Display a badge showing duplicate count."""
        count = obj.duplicates.count()
        if count > 0:
            return f'🔄 {count}'
        return '-'
    duplicate_badge.short_description = 'Duplicates'

    def sync_status_badge(self, obj):
        """Display a colored badge showing archive sync status."""
        status_icons = {
            Entry.ArchiveSyncStatus.IN_SYNC: ('✅', 'green', 'In Sync'),
            Entry.ArchiveSyncStatus.OUT_OF_SYNC: ('⚠️', 'orange', 'Out of Sync'),
            Entry.ArchiveSyncStatus.LOCAL_ONLY: ('📁', 'blue', 'Local Only'),
            Entry.ArchiveSyncStatus.ARCHIVE_ONLY: ('☁️', 'purple', 'Archive Only'),
            Entry.ArchiveSyncStatus.ERROR: ('❌', 'red', 'Error'),
            Entry.ArchiveSyncStatus.NEVER_CHECKED: ('❓', 'gray', 'Never Checked'),
        }
        icon, color, label = status_icons.get(obj.archive_sync_status, ('❓', 'gray', 'Unknown'))
        return format_html(
            '<span style="color: {};" title="{}">{}</span>',
            color, label, icon
        )
    sync_status_badge.short_description = 'Sync'

    def mark_ready_to_upload(self, request, queryset):
        """Mark selected entries as ready to upload."""
        updated = queryset.update(readyToUpload=True, needsWork=False)
        self.message_user(request, f'{updated} entries marked as ready to upload.')
    mark_ready_to_upload.short_description = 'Mark as ready to upload'

    def mark_needs_work(self, request, queryset):
        """Mark selected entries as needing work."""
        updated = queryset.update(needsWork=True, readyToUpload=False)
        self.message_user(request, f'{updated} entries marked as needing work.')
    mark_needs_work.short_description = 'Mark as needs work'

    def mark_uploaded(self, request, queryset):
        """Mark selected entries as uploaded."""
        updated = queryset.update(uploaded=True)
        self.message_user(request, f'{updated} entries marked as uploaded.')
    mark_uploaded.short_description = 'Mark as uploaded'

    def find_and_mark_duplicates(self, request, queryset):
        """Find and mark duplicates for selected entries."""
        marked_count = 0
        duplicate_pairs = []

        for entry in queryset:
            duplicates = entry.find_duplicates()
            for duplicate in duplicates:
                if entry.mark_as_duplicate(duplicate):
                    marked_count += 1
                    duplicate_pairs.append(f'{entry.identifier} ⟷ {duplicate.identifier}')

        if marked_count > 0:
            self.message_user(
                request,
                f'Found and marked {marked_count} duplicate relationships. Examples: {", ".join(duplicate_pairs[:5])}'
            )
        else:
            self.message_user(request, 'No duplicates found for selected entries.', level='WARNING')
    find_and_mark_duplicates.short_description = 'Find and mark duplicates'

    def clear_duplicate_marks(self, request, queryset):
        """Clear all duplicate marks for selected entries."""
        cleared_count = 0
        for entry in queryset:
            count = entry.duplicates.count()
            if count > 0:
                entry.duplicates.clear()
                cleared_count += 1

        self.message_user(request, f'Cleared duplicate marks for {cleared_count} entries.')
    clear_duplicate_marks.short_description = 'Clear duplicate marks'

    def check_archive_sync(self, request, queryset):
        """Check synchronization status with Internet Archive for selected entries."""
        try:
            summary = archive_sync.bulk_check_sync_status(queryset)

            message_parts = [
                f"Checked {summary['total']} entries:",
                f"✅ {summary['in_sync']} in sync",
                f"⚠️ {summary['out_of_sync']} out of sync",
                f"📁 {summary['local_only']} local only",
            ]
            if summary['errors'] > 0:
                message_parts.append(f"❌ {summary['errors']} errors")

            self.message_user(request, ' | '.join(message_parts))
        except Exception as e:
            self.message_user(request, f'Error checking sync status: {e}', level='ERROR')
    check_archive_sync.short_description = '🔍 Check sync with Internet Archive'

    def pull_from_archive(self, request, queryset):
        """Pull metadata from Internet Archive and overwrite local data (Archive as source of truth)."""
        updated_count = 0
        error_count = 0
        all_changes = []

        for entry in queryset:
            result = archive_sync.pull_from_archive(entry)
            if result['success']:
                if result['changes']:
                    updated_count += 1
                    all_changes.extend(result['changes'][:2])  # Limit examples
            else:
                error_count += 1
                self.message_user(
                    request,
                    f"Error pulling {entry.identifier}: {result['error']}",
                    level='ERROR'
                )

        if updated_count > 0:
            changes_preview = ', '.join(all_changes[:5])
            if len(all_changes) > 5:
                changes_preview += f' ... and {len(all_changes) - 5} more'
            self.message_user(
                request,
                f'✅ Updated {updated_count} entries from Internet Archive. Changes: {changes_preview}'
            )
        else:
            self.message_user(request, 'No entries needed updates.', level='WARNING')

        if error_count > 0:
            self.message_user(request, f'❌ {error_count} entries had errors.', level='ERROR')
    pull_from_archive.short_description = '⬇️ Pull from Internet Archive (overwrite local)'

    def push_to_archive(self, request, queryset):
        """Push local metadata to Internet Archive (Local as source of truth)."""
        updated_count = 0
        error_count = 0
        all_changes = []

        for entry in queryset:
            result = archive_sync.push_to_archive(entry)
            if result['success']:
                if result['changes']:
                    updated_count += 1
                    all_changes.extend(result['changes'][:2])  # Limit examples
            else:
                error_count += 1
                self.message_user(
                    request,
                    f"Error pushing {entry.identifier}: {result['error']}",
                    level='ERROR'
                )

        if updated_count > 0:
            changes_preview = ', '.join(all_changes[:5])
            if len(all_changes) > 5:
                changes_preview += f' ... and {len(all_changes) - 5} more'
            self.message_user(
                request,
                f'✅ Pushed {updated_count} entries to Internet Archive. Changes: {changes_preview}'
            )
        else:
            self.message_user(request, 'No entries needed updates.', level='WARNING')

        if error_count > 0:
            self.message_user(request, f'❌ {error_count} entries had errors.', level='ERROR')
    push_to_archive.short_description = '⬆️ Push to Internet Archive (overwrite remote)'


@admin.register(Creator)
class CreatorAdmin(admin.ModelAdmin):
    """Enhanced admin for Creator model."""
    list_display = ['name', 'created_date']
    search_fields = ['name']
    readonly_fields = ['created_date', 'modified_date']


@admin.register(ArchCollection)
class ArchCollectionAdmin(admin.ModelAdmin):
    """Enhanced admin for ArchCollection model."""
    list_display = ['name', 'created_date']
    search_fields = ['name']
    readonly_fields = ['created_date', 'modified_date']


@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
    """Enhanced admin for Contributor model."""
    list_display = ['name', 'created_date']
    search_fields = ['name']
    readonly_fields = ['created_date', 'modified_date']


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    """Enhanced admin for Language model."""
    list_display = ['name', 'created_date']
    search_fields = ['name']
    readonly_fields = ['created_date', 'modified_date']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    """Enhanced admin for Subject model."""
    list_display = ['name', 'created_date']
    search_fields = ['name']
    readonly_fields = ['created_date', 'modified_date']


@admin.register(ZipArchive)
class ZipArchiveAdmin(admin.ModelAdmin):
    """Enhanced admin for ZipArchive model."""
    list_display = ['archive', 'entry', 'created_date']
    list_filter = ['created_date']
    search_fields = ['archive', 'entry__title', 'entry__identifier']
    readonly_fields = ['created_date', 'modified_date']
    raw_id_fields = ['entry']


@admin.register(ZipContent)
class ZipContentAdmin(admin.ModelAdmin):
    """Enhanced admin for ZipContent model."""
    list_display = ['file', 'suffix', 'size_bytes', 'md5sum', 'created_date']
    list_filter = ['suffix', 'created_date']
    search_fields = ['file', 'md5sum']
    readonly_fields = ['created_date', 'modified_date']
    raw_id_fields = ['zipArchive']


@admin.register(PhotoImage)
class PhotoImageAdmin(admin.ModelAdmin):
    """Enhanced admin for PhotoImage model."""
    list_display = ['image', 'entry', 'created_date']
    search_fields = ['image', 'entry__title']
    readonly_fields = ['created_date', 'modified_date']
    raw_id_fields = ['entry']


@admin.register(RandoFile)
class RandoFileAdmin(admin.ModelAdmin):
    """Enhanced admin for RandoFile model."""
    list_display = ['file', 'suffix', 'entry', 'created_date']
    list_filter = ['suffix']
    search_fields = ['file', 'entry__title']
    readonly_fields = ['created_date', 'modified_date']
    raw_id_fields = ['entry']


@admin.register(ScriptRun)
class ScriptRunAdmin(admin.ModelAdmin):
    """Enhanced admin for ScriptRun audit logs."""
    list_display = ['entry', 'script', 'function', 'runtime', 'parentPath']
    list_filter = ['script', 'function', 'runtime']
    search_fields = ['entry__title', 'entry__identifier', 'text', 'parentPath']
    readonly_fields = ['created_date', 'modified_date', 'runtime']
    raw_id_fields = ['entry']
    date_hierarchy = 'runtime'


@admin.register(FluxFile)
class FluxFileAdmin(admin.ModelAdmin):
    """Enhanced admin for FluxFile model."""
    list_display = ['file', 'zipContent', 'created_date']
    search_fields = ['file']
    readonly_fields = ['created_date', 'modified_date']


@admin.register(InfoChunk)
class InfoChunkAdmin(admin.ModelAdmin):
    """Enhanced admin for InfoChunk model."""
    list_display = ['fluxFile', 'creator', 'drive_type', 'info_version']
    list_filter = ['drive_type', 'write_protected', 'synchronized']
    search_fields = ['creator', 'fluxFile__file']
    readonly_fields = ['created_date', 'modified_date']


@admin.register(MetaChunk)
class MetaChunkAdmin(admin.ModelAdmin):
    """Enhanced admin for MetaChunk model."""
    list_display = ['title', 'publisher', 'language', 'fluxFile']
    list_filter = ['language']
    search_fields = ['title', 'publisher', 'developer', 'notes']
    readonly_fields = ['created_date', 'modified_date']


@admin.register(TextFile)
class TextFileAdmin(admin.ModelAdmin):
    """Enhanced admin for TextFile model."""
    list_display = ['zipContent', 'created_date']
    search_fields = ['raw_read', 'converted']
    readonly_fields = ['created_date', 'modified_date']
