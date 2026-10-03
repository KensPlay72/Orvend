from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0013_productos_rango_precio_venta"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="cajaac",
            options={
                "permissions": [
                    ("operar_caja", "Puede operar la caja"),
                ],
            },
        ),
        migrations.AlterModelOptions(
            name="hautorizarcompra",
            options={
                "permissions": [
                    (
                        "gestionar_recepcion_inventario",
                        "Puede gestionar la recepción de inventario",
                    ),
                ],
            },
        ),
    ]
