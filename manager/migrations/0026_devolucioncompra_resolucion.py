from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("manager", "0025_devolucioncompradetalle_unidades_hijo")]

    operations = [
        migrations.AddField(
            model_name="devolucioncompra",
            name="compra_cambio",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="devoluciones_cambio_origen", to="manager.compras"),
        ),
        migrations.AddField(
            model_name="devolucioncompra",
            name="monto_resolucion",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="devolucioncompra",
            name="resolucion",
            field=models.CharField(blank=True, choices=[("CAMBIO", "Cambio"), ("SALDO_FAVOR", "Saldo a favor")], max_length=20, null=True),
        ),
    ]
