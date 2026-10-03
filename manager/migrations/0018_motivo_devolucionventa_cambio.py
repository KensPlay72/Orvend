from django.db import migrations, models


MOTIVOS = [
    (1, "Producto dañado"),
    (2, "Producto vencido"),
    (3, "Error de pedido"),
    (4, "Producto incorrecto"),
    (5, "Exceso de inventario"),
    (6, "Otro"),
    (7, "Cambio"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0017_devolucionventa_devolucionventadetalle"),
    ]

    operations = [
        migrations.AlterField(
            model_name="devolucioncompradetalle",
            name="motivo",
            field=models.IntegerField(choices=MOTIVOS),
        ),
        migrations.AlterField(
            model_name="devolucionventa",
            name="motivo",
            field=models.IntegerField(choices=MOTIVOS),
        ),
    ]
