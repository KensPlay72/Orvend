from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("manager", "0038_cajaac_ver_dashboard_permission")]

    operations = [
        migrations.AddField(
            model_name="cotizacion",
            name="cliente_nombre",
            field=models.CharField(blank=True, default="", max_length=180),
        ),
        migrations.AddField(
            model_name="cotizacion",
            name="con_rtn",
            field=models.BooleanField(default=False),
        ),
    ]
