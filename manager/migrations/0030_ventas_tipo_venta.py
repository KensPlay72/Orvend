from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0029_compras_es_cambio")]

    operations = [
        migrations.AddField(
            model_name="ventas",
            name="tipo_venta",
            field=models.CharField(choices=[("contado", "Contado"), ("credito", "Crédito")], default="contado", max_length=20),
        ),
    ]
