from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tiendav", "0004_alter_pedidotienda_estado"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="pedidotienda",
            name="estado",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("EN_REVISION", "En revisión"),
                    ("ACEPTADO", "Aceptado"),
                    ("ENTREGADO", "Entregado"),
                    ("RECHAZADO", "Rechazado"),
                ],
                default="PENDIENTE",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="pedidotienda",
            name="entregado_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pedidotienda",
            name="entregado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pedidos_tienda_entregados",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
