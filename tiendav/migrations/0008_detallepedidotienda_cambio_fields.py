import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0001_initial'),
        ('tiendav', '0007_pedidotienda_token_and_detalle_revision_fields'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='pedidotienda',
            options={
                'ordering': ('-creado', '-id'),
                'permissions': [
                    ('cambiar_producto_pedido', 'Puede cambiar producto en pedido'),
                    ('anexar_producto_pedido', 'Puede anexar producto a pedido'),
                ],
            },
        ),
        migrations.AlterField(
            model_name='detallepedidotienda',
            name='estado_revision',
            field=models.CharField(
                choices=[
                    ('PENDIENTE', 'Pendiente'),
                    ('ACEPTADO', 'Aceptado'),
                    ('AJUSTADO', 'Ajustado'),
                    ('CAMBIADO', 'Cambiado'),
                    ('RECHAZADO', 'Rechazado'),
                    ('DEVUELTO', 'Devuelto'),
                ],
                default='PENDIENTE',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='cantidad_cambio',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='precio_unitario_cambio',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='producto_cambio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='detalles_cambio_tienda', to='manager.productos'),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='reserva_cambio',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='detalle_cambio_tienda', to='manager.reservainventario'),
        ),
    ]
