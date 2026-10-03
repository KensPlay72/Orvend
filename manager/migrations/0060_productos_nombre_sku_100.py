from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0059_productos_precios_opcionales"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productos",
            name="nombre",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="productos",
            name="codigo_sku",
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
