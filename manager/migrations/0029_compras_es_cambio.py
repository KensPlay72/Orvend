from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0028_compras_saldo_utilizado")]

    operations = [
        migrations.AddField(
            model_name="compras",
            name="es_cambio",
            field=models.BooleanField(default=False),
        ),
    ]
