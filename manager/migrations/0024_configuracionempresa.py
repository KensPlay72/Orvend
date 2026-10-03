from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0023_comboimagen")]

    operations = [
        migrations.CreateModel(
            name="ConfiguracionEmpresa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("is_delete", models.BooleanField(default=False)),
                ("f_creacion", models.DateTimeField(auto_now_add=True)),
                ("f_modificacion", models.DateTimeField(blank=True, null=True)),
                ("u_creo_id", models.IntegerField(blank=True, null=True)),
                ("u_modifico_id", models.IntegerField(blank=True, null=True)),
                ("nombre_comercial", models.CharField(default="Orvend Mart", max_length=150)),
                ("razon_social", models.CharField(blank=True, default="", max_length=180)),
                ("rtn", models.CharField(blank=True, default="", max_length=30)),
                ("telefono", models.CharField(blank=True, default="", max_length=30)),
                ("email", models.EmailField(blank=True, default="", max_length=100)),
                ("direccion", models.CharField(blank=True, default="", max_length=255)),
                ("mensaje_factura", models.CharField(blank=True, default="", max_length=180)),
                ("logo_nombre", models.CharField(blank=True, default="", max_length=100)),
                ("logo_archivo", models.CharField(blank=True, default="", max_length=150)),
                ("logo_url", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={
                "verbose_name": "Configuración de empresa",
                "verbose_name_plural": "Configuración de empresa",
                "permissions": [("gestionar_configuracion", "Puede administrar la configuración de empresa")],
            },
        )
    ]
