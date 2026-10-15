from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tiendav', '0008_detallepedidotienda_cambio_fields'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='pedidotienda',
            index=models.Index(fields=['cliente', '-creado'], name='pedidotienda_cli_creado_idx'),
        ),
        migrations.AddIndex(
            model_name='pedidotienda',
            index=models.Index(fields=['estado', '-creado'], name='pedidotienda_est_creado_idx'),
        ),
        migrations.AddIndex(
            model_name='detallepedidotienda',
            index=models.Index(fields=['pedido', 'id'], name='detpedtienda_ped_id_idx'),
        ),
        migrations.AddIndex(
            model_name='detallepedidotienda',
            index=models.Index(fields=['producto', 'estado_revision'], name='detpedtienda_prod_rev_idx'),
        ),
    ]
