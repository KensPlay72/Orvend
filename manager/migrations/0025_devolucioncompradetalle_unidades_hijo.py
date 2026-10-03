from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("manager", "0024_configuracionempresa")]

    operations = [
        migrations.AlterField(
            model_name="hautorizarcompra",
            name="cantidad_autorizada",
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AlterField(
            model_name="devolucioncompradetalle",
            name="cantidad",
            field=models.DecimalField(decimal_places=6, max_digits=18),
        ),
        migrations.AddField(
            model_name="devolucioncompradetalle",
            name="cantidad_hijo",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name="devolucioncompradetalle",
            name="producto_hijo",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="producto_hijo_devolucion_detalles", to="manager.productos"),
        ),
    ]
