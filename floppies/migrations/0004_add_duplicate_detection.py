# Generated migration to add duplicate detection functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('floppies', '0003_add_database_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='duplicates',
            field=models.ManyToManyField(
                blank=True,
                help_text='Other entries that are exact duplicates (same MD5 hashes for all files)',
                related_name='_floppies_entry_duplicates_+',
                to='floppies.entry'
            ),
        ),
    ]
