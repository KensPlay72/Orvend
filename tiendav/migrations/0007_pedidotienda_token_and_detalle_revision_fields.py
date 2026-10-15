import uuid
from decimal import Decimal
from django.db import migrations, models


EXISTING_TOKENS = {
    1: uuid.UUID("c8e34b10-4d4c-5a49-83c5-427d237e39b9"),
    2: uuid.UUID("59e173d8-f7e1-5139-b9da-c602d3b92e3e"),
    3: uuid.UUID("6a8faf9e-1525-5e9b-9978-e13ba5e3d528"),
    4: uuid.UUID("487a7a95-d943-57be-8369-d4ed0ba37346"),
    5: uuid.UUID("e69ce98e-b92d-59f6-8721-36c34e1ff9f5"),
    6: uuid.UUID("c940f596-f2f3-528e-aa0f-36844b6b6cc9"),
    7: uuid.UUID("cdb9fe09-1fbc-5e46-86ec-f14d09fd698d"),
}

EXISTING_REVIEWS = {
    1: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    2: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    3: {"estado": "RECHAZADO", "cantidad_aprobada": Decimal("0.0"), "justificacion": "Producto agotado"},
    8: {"estado": "AJUSTADO", "cantidad_aprobada": Decimal("2.0"), "justificacion": "Tenemos 2 en existencias"},
    9: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("2.0"), "justificacion": "", "entregada": True},
    10: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    11: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    12: {"estado": "RECHAZADO", "cantidad_aprobada": Decimal("0.0"), "justificacion": "Sin Stock"},
    13: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    14: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    15: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    16: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    17: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    18: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    19: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    20: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    21: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    22: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
    23: {"estado": "ACEPTADO", "cantidad_aprobada": Decimal("1.0"), "justificacion": ""},
}


def migrar_datos_revisiones_y_tokens(apps, schema_editor):
    PedidoTienda = apps.get_model('tiendav', 'PedidoTienda')
    DetallePedidoTienda = apps.get_model('tiendav', 'DetallePedidoTienda')

    # Asignar tokens a todos los PedidoTienda
    usados = set()
    for pedido in PedidoTienda.objects.all():
        token_val = EXISTING_TOKENS.get(pedido.id)
        if not token_val or token_val in usados:
            token_val = uuid.uuid4()
            while token_val in usados:
                token_val = uuid.uuid4()
        usados.add(token_val)
        pedido.token = token_val
        pedido.save(update_fields=['token'])

    # Poblar revisiones de DetallePedidoTienda
    for detalle in DetallePedidoTienda.objects.all():
        rev = EXISTING_REVIEWS.get(detalle.id, {})
        estado = rev.get('estado')
        if not estado:
            pedido_estado = detalle.pedido.estado if detalle.pedido else ''
            if detalle.reserva_id and getattr(detalle.reserva, 'estado', None) == 'CANCELADA':
                estado = 'RECHAZADO'
            elif pedido_estado in {'ACEPTADO', 'PAGADO', 'ENTREGADO'}:
                estado = 'ACEPTADO'
            else:
                estado = 'PENDIENTE'

        detalle.estado_revision = estado
        if rev.get('cantidad_aprobada') is not None:
            detalle.cantidad_aprobada = rev['cantidad_aprobada']
        elif estado == 'RECHAZADO':
            detalle.cantidad_aprobada = Decimal('0')
        elif estado in {'ACEPTADO', 'AJUSTADO'}:
            detalle.cantidad_aprobada = detalle.cantidad

        detalle.justificacion = rev.get('justificacion', '')
        detalle.justificacion_devolucion = rev.get('justificacion_devolucion', '')
        detalle.entregado = bool(rev.get('entregada'))
        detalle.save(update_fields=[
            'estado_revision',
            'cantidad_aprobada',
            'justificacion',
            'justificacion_devolucion',
            'entregado',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('tiendav', '0006_pedidotienda_cliente_nombre_pedidotienda_cliente_pos_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedidotienda',
            name='token',
            field=models.UUIDField(default=uuid.uuid4, null=True, editable=False),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='estado_revision',
            field=models.CharField(
                choices=[
                    ('PENDIENTE', 'Pendiente'),
                    ('EN_REVISION', 'En revisión'),
                    ('ACEPTADO', 'Aceptado'),
                    ('AJUSTADO', 'Ajustado'),
                    ('RECHAZADO', 'Rechazado'),
                    ('DEVUELTO', 'Devuelto'),
                ],
                default='PENDIENTE',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='cantidad_aprobada',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='justificacion',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='justificacion_devolucion',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='detallepedidotienda',
            name='entregado',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(migrar_datos_revisiones_y_tokens, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='pedidotienda',
            name='token',
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
