from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0019_ventas_nota_credito_y_uso_devolucion"),
    ]

    operations = [
        migrations.AddField(
            model_name="ventas",
            name="con_rtn",
            field=models.BooleanField(default=False),
        ),
    ]
