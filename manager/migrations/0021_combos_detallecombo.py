from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("manager", "0020_ventas_con_rtn")]

    operations = [
        migrations.CreateModel(
            name="Combos",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("is_delete", models.BooleanField(default=False)),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(blank=True, null=True)),
                ("u_creo_id", models.IntegerField(blank=True, null=True)),
                ("u_modifico_id", models.IntegerField(blank=True, null=True)),
                ("nombre", models.CharField(max_length=120)),
                ("codigo_sku", models.CharField(max_length=50, unique=True)),
                ("costo_total", models.DecimalField(decimal_places=2, default=0, max_digits=18)),
                ("precio_venta", models.DecimalField(decimal_places=2, max_digits=18)),
                ("precio_venta_min", models.DecimalField(decimal_places=2, max_digits=18)),
                ("precio_venta_max", models.DecimalField(decimal_places=2, max_digits=18)),
            ],
        ),
        migrations.CreateModel(
            name="DetalleCombo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad", models.DecimalField(decimal_places=2, max_digits=18)),
                ("costo_unitario", models.DecimalField(decimal_places=2, max_digits=18)),
                ("combo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="detalles", to="manager.combos")),
                ("producto", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="detalles_combo", to="manager.productos")),
            ],
        ),
        migrations.AddConstraint(
            model_name="detallecombo",
            constraint=models.UniqueConstraint(fields=("combo", "producto"), name="unique_producto_combo"),
        ),
    ]
