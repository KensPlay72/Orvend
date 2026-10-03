import uuid

from django.db import migrations, models


def asignar_tokens(apps, schema_editor):
    Producto = apps.get_model("manager", "Productos")
    for producto in Producto.objects.filter(tienda_token__isnull=True).iterator():
        producto.tienda_token = uuid.uuid4()
        producto.save(update_fields=["tienda_token"])


class Migration(migrations.Migration):
    dependencies = [("manager", "0051_cajaac_retiros_total")]

    operations = [
        migrations.AddField(
            model_name="productos",
            name="tienda_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(asignar_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="productos",
            name="tienda_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
