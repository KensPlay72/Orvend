from django.db import migrations, models


def actualizar_origen_ventas_ruta(apps, schema_editor):
    Ventas = apps.get_model('manager', 'Ventas')
    try:
        PedidoTienda = apps.get_model('tiendav', 'PedidoTienda')
        pedidos_ruta_ids = list(
            PedidoTienda.objects.filter(origen='CAJA_RUTA').values_list('id', flat=True)
        )
        if pedidos_ruta_ids:
            Ventas.objects.filter(ecommerce_pedido_id__in=pedidos_ruta_ids).update(origen='ruta')
    except Exception:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0073_alter_cajaac_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ventas',
            name='origen',
            field=models.CharField(
                choices=[('local', 'Local'), ('ecommerce', 'E-commerce'), ('ruta', 'De ruta')],
                default='local',
                max_length=12,
            ),
        ),
        migrations.RunPython(actualizar_origen_ventas_ruta, reverse_code=migrations.RunPython.noop),
    ]
