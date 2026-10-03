from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("manager", "0021_combos_detallecombo")]

    operations = [
        migrations.AlterField(
            model_name="detalleventa",
            name="producto",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="producto_venta_detalles",
                to="manager.productos",
            ),
        ),
        migrations.AddField(
            model_name="detalleventa",
            name="combo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="combo_venta_detalles",
                to="manager.combos",
            ),
        ),
    ]
