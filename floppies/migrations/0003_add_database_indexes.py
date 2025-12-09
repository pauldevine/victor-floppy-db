# Generated migration to add database indexes for performance

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('floppies', '0002_rename_rumtime_to_runtime'),
    ]

    operations = [
        # First, add created_date and modified_date fields to Django's state
        # (These fields already exist in DB from BaseModel but weren't in migration state)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='entry',
                    name='created_date',
                    field=models.DateTimeField(auto_now_add=True),
                ),
                migrations.AddField(
                    model_name='entry',
                    name='modified_date',
                    field=models.DateTimeField(auto_now=True),
                ),
            ],
            database_operations=[],  # Fields already exist in DB
        ),
        # Add missing models to state that exist in DB but not in migrations
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='ZipContent',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_date', models.DateTimeField(auto_now_add=True)),
                        ('modified_date', models.DateTimeField(auto_now=True)),
                        ('file', models.CharField(max_length=2048)),
                        ('md5sum', models.CharField(blank=True, max_length=32, null=True)),
                        ('suffix', models.CharField(blank=True, max_length=20, null=True)),
                        ('size_bytes', models.BigIntegerField(blank=True, null=True)),
                        ('zipArchive', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='floppies.ziparchive')),
                    ],
                    options={
                        'abstract': False,
                    },
                ),
                migrations.CreateModel(
                    name='FluxFile',
                    fields=[
                        ('zipContent', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='floppies.zipcontent')),
                        ('file', models.CharField(max_length=2048)),
                    ],
                ),
                migrations.CreateModel(
                    name='TextFile',
                    fields=[
                        ('zipContent', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='floppies.zipcontent')),
                        ('raw_read', models.TextField()),
                        ('converted', models.TextField(blank=True, null=True)),
                    ],
                ),
                migrations.CreateModel(
                    name='InfoChunk',
                    fields=[
                        ('fluxFile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='floppies.fluxfile')),
                        ('info_version', models.PositiveSmallIntegerField()),
                        ('creator', models.CharField(max_length=32)),
                        ('drive_type', models.PositiveSmallIntegerField()),
                        ('write_protected', models.BooleanField()),
                        ('synchronized', models.BooleanField()),
                        ('hard_sector_count', models.PositiveSmallIntegerField()),
                    ],
                ),
                migrations.CreateModel(
                    name='MetaChunk',
                    fields=[
                        ('fluxFile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to='floppies.fluxfile')),
                        ('title', models.CharField(blank=True, max_length=255)),
                        ('subtitle', models.CharField(blank=True, max_length=255, null=True)),
                        ('publisher', models.CharField(blank=True, max_length=255, null=True)),
                        ('developer', models.CharField(blank=True, max_length=255, null=True)),
                        ('copyright', models.CharField(blank=True, max_length=255, null=True)),
                        ('version', models.CharField(blank=True, max_length=255, null=True)),
                        ('language', models.CharField(blank=True, max_length=2, null=True)),
                        ('requires_platform', models.CharField(blank=True, max_length=255, null=True)),
                        ('requires_machine', models.CharField(blank=True, max_length=255, null=True)),
                        ('requires_ram', models.CharField(blank=True, max_length=255, null=True)),
                        ('notes', models.TextField(blank=True, null=True)),
                        ('side', models.CharField(blank=True, max_length=255, null=True)),
                        ('side_name', models.CharField(blank=True, max_length=255, null=True)),
                        ('contributor', models.CharField(blank=True, max_length=255, null=True)),
                        ('image_date', models.DateTimeField(blank=True, null=True)),
                    ],
                ),
            ],
            database_operations=[],  # All models already exist in DB
        ),
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
