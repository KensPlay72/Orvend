from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("manager", "0039_cotizacion_cliente_nombre_con_rtn")]

    operations = [
        migrations.AddField(
            model_name="configuracionempresa",
            name="cotizacion_dias_validez",
            field=models.PositiveIntegerField(default=7),
        ),
    ]
