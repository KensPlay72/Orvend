from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0032_detalleventa_subtotal_monto_devuelto")]

    operations = [
        migrations.AddField(
            model_name="configuracionempresa",
            name="tienda_color_acento",
            field=models.CharField(default="#F5A623", max_length=7),
        ),
        migrations.AddField(
            model_name="configuracionempresa",
            name="tienda_color_primario",
            field=models.CharField(default="#32877F", max_length=7),
        ),
        migrations.AddField(
            model_name="configuracionempresa",
            name="tienda_color_secundario",
            field=models.CharField(default="#10463E", max_length=7),
        ),
        migrations.AddField(
            model_name="configuracionempresa",
            name="tienda_subtitulo",
            field=models.CharField(blank=True, default="", max_length=180),
        ),
        migrations.CreateModel(
            name="BannerTienda",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("imagen_nombre", models.CharField(max_length=120)),
                ("imagen_archivo", models.CharField(max_length=180, unique=True)),
                ("imagen_url", models.CharField(blank=True, default="", max_length=255)),
                ("titulo", models.CharField(blank=True, default="", max_length=100)),
                ("enlace", models.CharField(blank=True, default="", max_length=255)),
                ("orden", models.PositiveIntegerField(default=0)),
                ("activo", models.BooleanField(default=True)),
                ("configuracion", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="banners_tienda", to="manager.configuracionempresa")),
            ],
            options={"ordering": ("orden", "id")},
        ),
    ]
