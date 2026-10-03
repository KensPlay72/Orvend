import uuid

from django.db import migrations, models


def asignar_tokens(apps, schema_editor):
    Compra = apps.get_model("manager", "Compras")
    Traslado = apps.get_model("manager", "Traslados")

    for modelo in (Compra, Traslado):
        for documento in modelo.objects.filter(documento_token__isnull=True).iterator():
            documento.documento_token = uuid.uuid4()
            documento.save(update_fields=["documento_token"])


class Migration(migrations.Migration):
    dependencies = [("manager", "0044_clientes_enviar_factura_whatsapp_permission")]

    operations = [
        migrations.AddField(
            model_name="compras",
            name="documento_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="traslados",
            name="documento_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(asignar_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="compras",
            name="documento_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="traslados",
            name="documento_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
