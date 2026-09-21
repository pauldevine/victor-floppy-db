# Creates the Entry.identifier index on databases that predate 0001_initial.
#
# 0001_initial was regenerated from the models in September 2026 to replace a
# migration history that no longer described the live schema. Existing
# databases adopt it with `migrate floppies --fake-initial`, which skips table
# creation -- but the identifier index was never actually built there (the old
# history thought it already existed). This adds it if missing, and is a no-op
# on fresh databases where 0001_initial already created it.

from django.db import migrations


def create_identifier_index(apps, schema_editor):
    Entry = apps.get_model('floppies', 'Entry')
    field = Entry._meta.get_field('identifier')
    table = Entry._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(cursor, table)
    if any(c['index'] and c['columns'] == [field.column] for c in constraints.values()):
        return
    schema_editor.execute(schema_editor._create_index_sql(Entry, fields=[field]))
    like_index_sql = schema_editor._create_like_index_sql(Entry, field)
    if like_index_sql is not None:
        schema_editor.execute(like_index_sql)


class Migration(migrations.Migration):

    dependencies = [
        ('floppies', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_identifier_index, migrations.RunPython.noop),
    ]
