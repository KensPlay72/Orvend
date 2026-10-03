from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0016_productosimagenes_imagen_archivo"),
    ]

    operations = [
        migrations.CreateModel(
            name="DevolucionVenta",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("is_delete", models.BooleanField(default=False)),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(blank=True, null=True)),
                ("u_creo_id", models.IntegerField(blank=True, null=True)),
                ("u_modifico_id", models.IntegerField(blank=True, null=True)),
                ("nota_credito", models.CharField(max_length=24, unique=True)),
                ("motivo", models.IntegerField(choices=[(1, "Producto dañado"), (2, "Producto vencido"), (3, "Error de pedido"), (4, "Producto incorrecto"), (5, "Exceso de inventario"), (6, "Otro")])),
                ("justificacion", models.CharField(max_length=500)),
                ("monto_total", models.DecimalField(decimal_places=2, max_digits=18)),
                ("estado", models.CharField(choices=[("DISPONIBLE", "Disponible"), ("USADA", "Usada"), ("ANULADA", "Anulada")], default="DISPONIBLE", max_length=12)),
                ("venta", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="devoluciones_venta", to="manager.ventas")),
            ],
        ),
        migrations.CreateModel(
            name="DevolucionVentaDetalle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad", models.DecimalField(decimal_places=2, max_digits=18)),
                ("precio_unitario", models.DecimalField(decimal_places=2, max_digits=18)),
                ("total", models.DecimalField(decimal_places=2, max_digits=18)),
                ("detalle_venta", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="devolucion_detalles", to="manager.detalleventa")),
                ("devolucion_venta", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalles", to="manager.devolucionventa")),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="manager.productos")),
            ],
        ),
    ]
