from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("manager", "0036_cotizacion_detallecotizacion")]

    operations = [
        migrations.AlterModelOptions(
            name="cotizacion",
            options={
                "ordering": ["-id"],
                "permissions": [
                    ("generar_cotizaciones", "Puede generar cotizaciones desde caja"),
                ],
            },
        ),
    ]
