from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0055_notificacion_tipos_cuentas")]

    operations = [
        migrations.AddField(
            model_name="compras",
            name="fecha_llegada_bodega",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="compras",
            name="llegada_bodega_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="compras_llegadas_bodega",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="compras",
            name="estado",
            field=models.CharField(
                choices=[
                    ("Pendiente", "Pendiente"),
                    ("Llegada Bodega", "Llegó a bodega"),
                    ("En Recepcion", "En Recepción"),
                    ("Recepcion Parcial", "Recepción Parcial"),
                    ("Completado", "Completado"),
                    ("Con Devolucion", "Con Devolución"),
                    ("Pendiente Resolucion", "Pendiente Resolución"),
                    ("Cerrada", "Cerrada"),
                    ("Cancelada", "Cancelada"),
                ],
                default="Pendiente",
                max_length=20,
            ),
        ),
    ]
