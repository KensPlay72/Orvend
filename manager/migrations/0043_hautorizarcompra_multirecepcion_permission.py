from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("manager", "0042_configuracionempresa_diseno_factura")]

    operations = [
        migrations.AlterModelOptions(
            name="hautorizarcompra",
            options={
                "permissions": [
                    (
                        "gestionar_recepcion_inventario",
                        "Puede gestionar la recepción de inventario",
                    ),
                    (
                        "multirecepcion",
                        "Puede ver y gestionar recepciones de todas las ubicaciones",
                    ),
                ],
            },
        ),
    ]
