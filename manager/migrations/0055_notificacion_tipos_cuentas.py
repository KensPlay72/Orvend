from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("manager", "0054_alter_notificacion_tipo")]

    operations = [
        migrations.AlterField(
            model_name="notificacion",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("RETIRO_CAJA", "Retiro de caja"),
                    ("STOCK_BAJO", "Stock bajo"),
                    ("VENCIMIENTO", "Próximo vencimiento"),
                    ("CUENTA_COBRAR", "Cuenta por cobrar"),
                    ("CUENTA_PAGAR", "Cuenta por pagar"),
                    ("SISTEMA", "Sistema"),
                ],
                default="SISTEMA",
                max_length=20,
            ),
        ),
    ]
