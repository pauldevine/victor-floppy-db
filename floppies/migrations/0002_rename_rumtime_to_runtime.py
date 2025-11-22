# Generated migration to fix typo: rumtime -> runtime

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('floppies', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='scriptrun',
            old_name='rumtime',
            new_name='runtime',
        ),
    ]
