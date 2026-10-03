from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0031_devolucionventa_resolucion_credito")]

    operations = [
        migrations.AddField(
            model_name="detalleventa",
            name="monto_devuelto",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name="detalleventa",
            name="subtotal",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=18),
        ),
    ]
