from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("manager", "0070_ubicaciones_departamento_ubicaciones_pais"),
    ]

    operations = [
        migrations.AddField(
            model_name="ventas",
            name="origen",
            field=models.CharField(
                choices=[("local", "Local"), ("ecommerce", "E-commerce")],
                default="local",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="ventas",
            name="ecommerce_pedido_id",
            field=models.PositiveBigIntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="ventas",
            name="cliente_ecommerce_nombre",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
    ]
