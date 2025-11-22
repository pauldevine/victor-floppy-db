# Migration to fix typo: rumtime -> runtime
# Also adds ScriptRun model to migration state since it's missing from 0001_initial

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('floppies', '0001_initial'),
    ]

    operations = [
        # Add ScriptRun to migration state only (table already exists in DB)
        # Database operation: do nothing
        # State operation: add ScriptRun model
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='ScriptRun',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_date', models.DateTimeField(auto_now_add=True)),
                        ('modified_date', models.DateTimeField(auto_now=True)),
                        ('text', models.TextField()),
                        ('rumtime', models.DateTimeField(auto_now_add=True)),
                        ('parentPath', models.CharField(blank=True, max_length=2048, null=True)),
                        ('function', models.CharField(blank=True, max_length=512, null=True)),
                        ('script', models.CharField(blank=True, max_length=2048, null=True)),
                        ('entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='floppies.entry')),
                    ],
                    options={
                        'abstract': False,
                    },
                ),
            ],
            database_operations=[],  # Don't create table - it already exists
        ),
        # Then rename the field from rumtime to runtime in both state and database
        migrations.RenameField(
            model_name='scriptrun',
            old_name='rumtime',
            new_name='runtime',
        ),
    ]

