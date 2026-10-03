from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0041_documentos_tokens_uuid")]

    operations = [
        migrations.AddField(
            model_name="configuracionempresa",
            name="diseno_factura",
            field=models.CharField(
                choices=[("RECIBO", "Recibo"), ("PAGINA", "Página")],
                default="RECIBO",
                max_length=10,
            ),
        ),
    ]
