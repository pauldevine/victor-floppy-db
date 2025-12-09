# Generated migration for archive synchronization fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('floppies', '0004_add_duplicate_detection'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='archive_sync_status',
            field=models.CharField(
                choices=[
                    ('NC', 'Never Checked'),
                    ('IS', 'In Sync'),
                    ('OS', 'Out of Sync'),
                    ('LO', 'Local Only (Not in Archive)'),
                    ('AO', 'Archive Only (Not Local)'),
                    ('ER', 'Sync Error')
                ],
                default='NC',
                help_text='Current synchronization status with Internet Archive',
                max_length=2
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='last_sync_check',
            field=models.DateTimeField(
                blank=True,
                help_text='Last time sync status was checked against Internet Archive',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='last_archive_sync',
            field=models.DateTimeField(
                blank=True,
                help_text='Last time this entry was successfully synchronized with Internet Archive',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='sync_notes',
            field=models.TextField(
                blank=True,
                help_text='Details about synchronization differences or issues',
                null=True
            ),
        ),
    ]
