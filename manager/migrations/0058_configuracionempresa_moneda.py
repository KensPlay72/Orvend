from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("manager", "0057_devolucioncompra_documento_token")]

    operations = [
        migrations.AddField(
            model_name="configuracionempresa",
            name="moneda",
            field=models.CharField(
                choices=[("HNL", "L. Lempira"), ("USD", "$. Dólar")],
                default="HNL",
                max_length=3,
            ),
        ),
    ]
