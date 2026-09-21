# Restores the doNotUpload field on Entry.
#
# This field was added directly to the working tree in January 2024 and the
# migration (0004_entry_donotupload) was applied to the live database, but
# neither was ever committed. The November 2025 cleanup started from a fresh
# clone, so the field was absent from models.py while the NOT NULL column
# remained in the database -- which made every new Entry insert fail.
#
# The column already exists in the live database, so apply this with --fake
# there. On a fresh database it runs normally and creates the column.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('floppies', '0005_add_archive_sync_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='doNotUpload',
            field=models.BooleanField(default=False),
        ),
    ]
