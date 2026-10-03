from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("manager", "0037_cotizacion_generar_cotizaciones_permission")]

    operations = [
        migrations.AlterModelOptions(
            name="cajaac",
            options={
                "permissions": [
                    ("operar_caja", "Puede operar la caja"),
                    ("modificar_precio_caja", "Puede modificar precios en caja"),
                    ("ver_dashboard", "Puede ver el dashboard"),
                ],
            },
        ),
    ]
