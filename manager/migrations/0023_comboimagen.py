from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("manager", "0022_detalleventa_combo")]

    operations = [
        migrations.CreateModel(
            name="ComboImagen",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("imagen_nombre", models.CharField(blank=True, max_length=100, null=True)),
                ("imagen_archivo", models.CharField(blank=True, default="", max_length=150)),
                ("imagen_url", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "combo",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="imagen",
                        to="manager.combos",
                    ),
                ),
            ],
        )
    ]
