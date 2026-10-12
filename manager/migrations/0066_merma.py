import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("manager", "0065_traslados_llegada_bodega"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Merma",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("is_delete", models.BooleanField(default=False)),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(blank=True, null=True)),
                ("u_creo_id", models.IntegerField(blank=True, null=True)),
                ("u_modifico_id", models.IntegerField(blank=True, null=True)),
                ("motivo", models.CharField(choices=[("VENCIDO", "Producto vencido"), ("DANADO", "Producto dañado"), ("CONTAMINADO", "Producto contaminado"), ("ERROR_OPERATIVO", "Error operativo"), ("OTRO", "Otro")], max_length=20)),
                ("observaciones", models.CharField(blank=True, default="", max_length=255)),
                ("ubicacion", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mermas", to="manager.ubicaciones")),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="mermas", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="DetalleMerma",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("is_delete", models.BooleanField(default=False)),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(blank=True, null=True)),
                ("u_creo_id", models.IntegerField(blank=True, null=True)),
                ("u_modifico_id", models.IntegerField(blank=True, null=True)),
                ("cantidad", models.DecimalField(decimal_places=6, max_digits=18)),
                ("stock_anterior", models.DecimalField(decimal_places=6, max_digits=18)),
                ("stock_resultante", models.DecimalField(decimal_places=6, max_digits=18)),
                ("merma", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalles", to="manager.merma")),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="detalles_merma", to="manager.productos")),
            ],
        ),
        migrations.AddConstraint(
            model_name="detallemerma",
            constraint=models.UniqueConstraint(fields=("merma", "producto"), name="unique_producto_merma"),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="merma",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimientos_merma", to="manager.merma"),
        ),
    ]
