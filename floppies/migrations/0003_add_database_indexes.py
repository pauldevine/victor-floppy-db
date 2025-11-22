# Generated migration to add database indexes for performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('floppies', '0002_rename_rumtime_to_runtime'),
    ]

    operations = [
        # Add index to Entry.identifier (frequently searched/filtered)
        migrations.AlterField(
            model_name='entry',
            name='identifier',
            field=models.CharField(max_length=500, db_index=True),
        ),
        # Add index to Entry.title (frequently searched/sorted)
        migrations.AlterField(
            model_name='entry',
            name='title',
            field=models.CharField(max_length=500, db_index=True),
        ),
        # Add composite index for common filter combination
        migrations.AddIndex(
            model_name='entry',
            index=models.Index(
                fields=['uploaded', 'readyToUpload', 'needsWork'],
                name='entry_upload_status_idx'
            ),
        ),
        # Add index for modified_date (used for date ordering)
        migrations.AddIndex(
            model_name='entry',
            index=models.Index(
                fields=['-modified_date'],
                name='entry_modified_date_idx'
            ),
        ),
        # Add index to ZipContent.suffix (filtered for .a2r, .flux files)
        migrations.AlterField(
            model_name='zipcontent',
            name='suffix',
            field=models.CharField(max_length=20, blank=True, null=True, db_index=True),
        ),
    ]
