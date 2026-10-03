from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0014_permisos_operativos_caja_bodega"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="cajaac",
            options={
                "permissions": [
                    ("operar_caja", "Puede operar la caja"),
                    ("modificar_precio_caja", "Puede modificar precios en caja"),
                ],
            },
        ),
    ]
