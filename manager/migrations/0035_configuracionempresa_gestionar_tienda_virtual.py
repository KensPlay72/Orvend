from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("manager", "0034_bannertienda_tipo")]

    operations = [
        migrations.AlterModelOptions(
            name="configuracionempresa",
            options={
                "verbose_name": "Configuración de empresa",
                "verbose_name_plural": "Configuración de empresa",
                "permissions": [
                    ("gestionar_configuracion", "Puede administrar la configuración de empresa"),
                    ("gestionar_tienda_virtual", "Puede configurar la tienda virtual"),
                ],
            },
        ),
    ]
