from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("manager", "0043_hautorizarcompra_multirecepcion_permission"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientes",
            name="enviar_factura_whatsapp",
            field=models.BooleanField(
                default=False,
                help_text="Envía la factura por WhatsApp al facturar a nombre de este cliente.",
            ),
        ),
        migrations.AlterModelOptions(
            name="clientes",
            options={
                "permissions": [
                    (
                        "enviar_facturas_whatsapp",
                        "Puede marcar clientes para enviar facturas por WhatsApp",
                    ),
                ],
            },
        ),
    ]
