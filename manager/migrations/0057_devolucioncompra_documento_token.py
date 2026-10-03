import uuid

from django.db import migrations, models


def asignar_tokens_devoluciones(apps, schema_editor):
    DevolucionCompra = apps.get_model("manager", "DevolucionCompra")
    for devolucion in DevolucionCompra.objects.filter(documento_token__isnull=True).iterator():
        devolucion.documento_token = uuid.uuid4()
        devolucion.save(update_fields=["documento_token"])


class Migration(migrations.Migration):

    dependencies = [("manager", "0056_compras_llegada_bodega")]

    operations = [
        migrations.AddField(
            model_name="devolucioncompra",
            name="documento_token",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(asignar_tokens_devoluciones, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="devolucioncompra",
            name="documento_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
