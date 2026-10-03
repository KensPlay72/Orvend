from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0060_productos_nombre_sku_100"),
    ]

    operations = [
        migrations.AddField(
            model_name="compras",
            name="total_antes_impuesto",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="compras",
            name="total_impuesto",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="detallecompra",
            name="impuesto_porcentaje",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="detallecompra",
            name="impuesto_unitario",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="detallecompra",
            name="precio_compra_con_impuesto",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
    ]
