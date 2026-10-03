from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0033_configuracionempresa_tienda_bannertienda")]

    operations = [
        migrations.AddField(
            model_name="bannertienda",
            name="tipo",
            field=models.CharField(choices=[("BANNER", "Banner"), ("CARRUSEL", "Carrusel")], default="CARRUSEL", max_length=10),
        ),
    ]
