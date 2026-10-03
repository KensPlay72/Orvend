from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("manager", "0045_compras_traslados_documento_token"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inventarios",
            name="cantidad",
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="cantidad",
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="stock_anterior",
            field=models.DecimalField(
                blank=True, decimal_places=6, max_digits=18, null=True
            ),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="stock_resultante",
            field=models.DecimalField(
                blank=True, decimal_places=6, max_digits=18, null=True
            ),
        ),
        migrations.AlterField(
            model_name="reservainventario",
            name="cantidad",
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
    ]
