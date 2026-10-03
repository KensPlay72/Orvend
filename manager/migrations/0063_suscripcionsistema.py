from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0062_indices_rendimiento"),
    ]

    operations = [
        migrations.CreateModel(
            name="SuscripcionSistema",
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
                (
                    "unica_configuracion",
                    models.BooleanField(default=True, editable=False, unique=True),
                ),
                ("fecha_inicio", models.DateField()),
                ("fecha_fin", models.DateField()),
                ("activa", models.BooleanField(default=True)),
                ("observaciones", models.TextField(blank=True, default="")),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Pago y suscripción",
                "verbose_name_plural": "Pago y suscripción",
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("fecha_fin__gte", models.F("fecha_inicio"))),
                        name="suscripcion_fechas_validas",
                    )
                ],
            },
        ),
    ]
