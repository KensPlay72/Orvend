from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tiendav", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientetienda",
            name="direccion",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="clientetienda",
            name="municipio",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="clientetienda",
            name="departamento",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="clientetienda",
            name="indicaciones_entrega",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
