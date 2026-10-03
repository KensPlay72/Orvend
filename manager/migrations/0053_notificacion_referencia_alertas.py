from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0052_productos_tienda_token")]

    operations = [
        migrations.AddField(
            model_name="notificacion",
            name="referencia",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
    ]
