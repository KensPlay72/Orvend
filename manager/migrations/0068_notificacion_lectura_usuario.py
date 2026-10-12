import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("manager", "0067_merma_documento_token"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificacionLectura",
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
                ("is_active", models.BooleanField(default=True)),
                ("is_delete", models.BooleanField(default=False)),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(blank=True, null=True)),
                ("u_creo_id", models.IntegerField(blank=True, null=True)),
                ("u_modifico_id", models.IntegerField(blank=True, null=True)),
                (
                    "notificacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lecturas",
                        to="manager.notificacion",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lecturas_notificaciones",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        fields=("notificacion", "usuario"),
                        name="uniq_notif_lectura_user",
                    )
                ],
            },
        ),
    ]
