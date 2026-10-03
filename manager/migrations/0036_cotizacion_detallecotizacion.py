from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [("manager", "0035_configuracionempresa_gestionar_tienda_virtual")]

    operations = [
        migrations.CreateModel(
            name="Cotizacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("is_delete", models.BooleanField(default=False)),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(blank=True, null=True)),
                ("u_creo_id", models.IntegerField(blank=True, null=True)),
                ("u_modifico_id", models.IntegerField(blank=True, null=True)),
                ("numero_cotizacion", models.CharField(max_length=20, unique=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("impuesto_15", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("impuesto_18", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("descuento", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("cliente", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="cliente_cotizaciones", to="manager.clientes")),
                ("sucursal", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="sucursal_cotizaciones", to="manager.ubicaciones")),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="DetalleCotizacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("is_delete", models.BooleanField(default=False)),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(blank=True, null=True)),
                ("u_creo_id", models.IntegerField(blank=True, null=True)),
                ("u_modifico_id", models.IntegerField(blank=True, null=True)),
                ("codigo", models.CharField(max_length=100)),
                ("nombre", models.CharField(max_length=255)),
                ("cantidad", models.DecimalField(decimal_places=2, max_digits=18)),
                ("precio_unitario", models.DecimalField(decimal_places=2, max_digits=18)),
                ("descuento", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("impuesto_15", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("impuesto_18", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("combo", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="combo_cotizacion_detalles", to="manager.combos")),
                ("cotizacion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalles", to="manager.cotizacion")),
                ("producto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="producto_cotizacion_detalles", to="manager.productos")),
            ],
        ),
    ]
