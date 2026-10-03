import uuid

from django.db import migrations, models


def asignar_tokens(apps, schema_editor):
    Factura = apps.get_model("manager", "facturas_cai")
    Cotizacion = apps.get_model("manager", "Cotizacion")
    for modelo in (Factura, Cotizacion):
        for documento in modelo.objects.filter(documento_token__isnull=True).iterator():
            documento.documento_token = uuid.uuid4()
            documento.save(update_fields=["documento_token"])


class Migration(migrations.Migration):
    dependencies = [("manager", "0040_configuracionempresa_cotizacion_dias_validez")]

    operations = [
        migrations.AddField(
            model_name="facturas_cai",
            name="documento_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="cotizacion",
            name="documento_token",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(asignar_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="facturas_cai",
            name="documento_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="cotizacion",
            name="documento_token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
