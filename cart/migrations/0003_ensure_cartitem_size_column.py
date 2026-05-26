from django.db import migrations


def ensure_cartitem_size_column(apps, schema_editor):
    table_name = 'cart_cartitem'
    column_name = 'size'

    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing_columns = {
            col.name.lower()
            for col in connection.introspection.get_table_description(cursor, table_name)
        }

    if column_name in existing_columns:
        return

    quoted_table = schema_editor.quote_name(table_name)
    quoted_column = schema_editor.quote_name(column_name)
    schema_editor.execute(
        f"ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} varchar(10) NULL"
    )


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('cart', '0002_alter_cart_options_alter_cartitem_options'),
    ]

    operations = [
        migrations.RunPython(ensure_cartitem_size_column, migrations.RunPython.noop),
    ]
