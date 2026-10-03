from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0027_merge_0026_devolucioncompra_resolucion_0026_proveedores_saldo")]

    operations = [
        migrations.AddField(
            model_name="compras",
            name="saldo_utilizado",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
    ]
