from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0018_motivo_devolucionventa_cambio"),
    ]

    operations = [
        migrations.AddField(
            model_name="ventas",
            name="nota_credito",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="devolucionventa",
            name="fecha_uso",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="devolucionventa",
            name="venta_aplicada",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="notas_credito_aplicadas", to="manager.ventas"),
        ),
    ]
