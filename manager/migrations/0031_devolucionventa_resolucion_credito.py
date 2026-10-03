from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("manager", "0030_ventas_tipo_venta")]

    operations = [
        migrations.AddField(
            model_name="devolucionventa",
            name="abono_cxc",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="devolucion_origen", to="manager.registroabonoscobrar"),
        ),
        migrations.AddField(
            model_name="devolucionventa",
            name="resolucion",
            field=models.CharField(choices=[("NOTA_CREDITO", "Nota de crédito"), ("DEDUCIR_SALDO", "Deducir saldo")], default="NOTA_CREDITO", max_length=20),
        ),
    ]
