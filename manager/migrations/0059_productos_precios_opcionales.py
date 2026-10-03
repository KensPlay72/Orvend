from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0058_configuracionempresa_moneda"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productos",
            name="precio_venta_min",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name="productos",
            name="precio_venta_max",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
    ]
