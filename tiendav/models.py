import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models

from manager.models import Clientes, Productos, ReservaInventario, Ubicaciones


def generar_numero_pedido():
    from django.db.models import Max

    ultimo = (
        PedidoTienda.objects.filter(numero_pedido__isnull=False)
        .exclude(numero_pedido="")
        .order_by("-id")
        .first()
    )
    consecutivo = 1
    if ultimo and ultimo.numero_pedido:
        try:
            consecutivo = int(ultimo.numero_pedido.rsplit("-", 1)[-1]) + 1
        except (ValueError, IndexError):
            consecutivo = ultimo.id + 1
    else:
        ultimo_id = PedidoTienda.objects.aggregate(max_id=Max("id"))["max_id"] or 0
        consecutivo = ultimo_id + 1

    numero = f"PED-{consecutivo:06d}"
    while PedidoTienda.objects.filter(numero_pedido=numero).exists():
        consecutivo += 1
        numero = f"PED-{consecutivo:06d}"
    return numero


class ClienteTienda(models.Model):
    email = models.EmailField(max_length=254, unique=True)
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30, blank=True, default="")
    direccion = models.CharField(max_length=255, blank=True, default="")
    municipio = models.CharField(max_length=100, blank=True, default="")
    departamento = models.CharField(max_length=100, blank=True, default="")
    indicaciones_entrega = models.CharField(max_length=255, blank=True, default="")
    password = models.CharField(max_length=128)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class PedidoTienda(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_REVISION = "EN_REVISION", "En revisión"
        ACEPTADO = "ACEPTADO", "Aceptado"
        PAGADO = "PAGADO", "Pagado"
        ENTREGADO = "ENTREGADO", "Entregado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    numero_pedido = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    cliente = models.ForeignKey(
        ClienteTienda,
        on_delete=models.PROTECT,
        related_name="pedidos",
        null=True,
        blank=True,
    )
    cliente_pos = models.ForeignKey(
        Clientes,
        on_delete=models.PROTECT,
        related_name="pedidos_tienda",
        null=True,
        blank=True,
    )
    cliente_nombre = models.CharField(
        max_length=180,
        blank=True,
        default="",
    )
    origen = models.CharField(
        max_length=20,
        default="TIENDA_VIRTUAL",
    )
    ubicacion = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="pedidos_tienda",
    )
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    total = models.DecimalField(max_digits=18, decimal_places=2)
    creado = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_tienda_creados",
    )
    procesado = models.DateTimeField(null=True, blank=True)
    procesado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_tienda_procesados",
    )
    entregado_en = models.DateTimeField(null=True, blank=True)
    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos_tienda_entregados",
    )

    class Meta:
        ordering = ("-creado", "-id")
        permissions = [
            ("cambiar_producto_pedido", "Puede cambiar producto en pedido"),
            ("anexar_producto_pedido", "Puede anexar producto a pedido"),
        ]

    @property
    def nombre_cliente(self):
        if self.cliente:
            return self.cliente.nombre
        if self.cliente_pos:
            return self.cliente_pos.nombre_completo or self.cliente_pos.empresa
        return self.cliente_nombre or "Consumidor Final"

    @property
    def telefono_cliente(self):
        if self.cliente and self.cliente.telefono:
            return self.cliente.telefono
        if self.cliente_pos and self.cliente_pos.telefono:
            return self.cliente_pos.telefono
        return ""

    @property
    def email_cliente(self):
        if self.cliente and self.cliente.email:
            return self.cliente.email
        if self.cliente_pos and self.cliente_pos.email:
            return self.cliente_pos.email
        return ""

    @property
    def direccion_cliente(self):
        if self.cliente:
            partes = [self.cliente.direccion, self.cliente.municipio, self.cliente.departamento]
            return ", ".join([p for p in partes if p])
        if self.cliente_pos and self.cliente_pos.direccion:
            partes = [self.cliente_pos.direccion, self.cliente_pos.municipio, self.cliente_pos.departamento]
            return ", ".join([p for p in partes if p])
        return ""

    @property
    def rtn_cliente(self):
        if self.cliente_pos and self.cliente_pos.dni:
            return self.cliente_pos.dni
        return ""

    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            self.numero_pedido = generar_numero_pedido()
        if not self.token:
            self.token = uuid.uuid4()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pedido {self.numero_pedido or f'#{self.id}'}"


class DetallePedidoTienda(models.Model):
    class EstadoRevision(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ACEPTADO = "ACEPTADO", "Aceptado"
        AJUSTADO = "AJUSTADO", "Ajustado"
        CAMBIADO = "CAMBIADO", "Cambiado"
        RECHAZADO = "RECHAZADO", "Rechazado"
        DEVUELTO = "DEVUELTO", "Devuelto"

    pedido = models.ForeignKey(
        PedidoTienda,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="detalles_pedido_tienda",
    )
    reserva = models.OneToOneField(
        ReservaInventario,
        on_delete=models.PROTECT,
        related_name="detalle_pedido_tienda",
    )
    producto_cambio = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="detalles_cambio_tienda",
    )
    reserva_cambio = models.OneToOneField(
        ReservaInventario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="detalle_cambio_tienda",
    )
    nombre_producto = models.CharField(max_length=100)
    codigo_sku = models.CharField(max_length=100)
    cantidad = models.DecimalField(max_digits=18, decimal_places=6)
    cantidad_cambio = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
    )
    precio_unitario = models.DecimalField(max_digits=18, decimal_places=2)
    precio_unitario_cambio = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    subtotal = models.DecimalField(max_digits=18, decimal_places=2)

    estado_revision = models.CharField(
        max_length=20,
        choices=EstadoRevision.choices,
        default=EstadoRevision.PENDIENTE,
    )
    cantidad_aprobada = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        null=True,
        blank=True,
    )
    justificacion = models.TextField(
        blank=True,
        default="",
    )
    justificacion_devolucion = models.TextField(
        blank=True,
        default="",
    )
    entregado = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ("id",)

    @property
    def rev_estado(self):
        if self.estado_revision == self.EstadoRevision.PENDIENTE:
            if getattr(self, "reserva", None) and self.reserva.estado == "CANCELADA":
                return self.EstadoRevision.RECHAZADO
        return self.estado_revision

    @property
    def rev_cantidad_original(self):
        return self.cantidad

    @property
    def rev_cantidad_aprobada(self):
        if self.rev_estado == self.EstadoRevision.CAMBIADO:
            return self.cantidad_cambio if self.cantidad_cambio is not None else self.cantidad
        if self.cantidad_aprobada is not None:
            return self.cantidad_aprobada
        if self.rev_estado == self.EstadoRevision.RECHAZADO:
            return Decimal("0")
        return self.cantidad

    @property
    def rev_producto(self):
        if self.rev_estado == self.EstadoRevision.CAMBIADO and self.producto_cambio:
            return self.producto_cambio
        return self.producto

    @property
    def rev_nombre_producto(self):
        if self.rev_estado == self.EstadoRevision.CAMBIADO and self.producto_cambio:
            return self.producto_cambio.nombre
        return self.nombre_producto

    @property
    def rev_precio_unitario(self):
        if self.rev_estado == self.EstadoRevision.CAMBIADO and self.precio_unitario_cambio is not None:
            return self.precio_unitario_cambio
        return self.precio_unitario

    @property
    def rev_justificacion(self):
        return self.justificacion or ""

    @property
    def rev_justificacion_devolucion(self):
        return self.justificacion_devolucion or ""

    @property
    def rev_entregado(self):
        return bool(self.entregado)

    @property
    def rev_subtotal(self):
        estado = self.rev_estado
        if estado in {self.EstadoRevision.RECHAZADO, self.EstadoRevision.DEVUELTO}:
            return Decimal("0.00")
        if estado == self.EstadoRevision.CAMBIADO:
            pu = self.rev_precio_unitario
            cant = self.rev_cantidad_aprobada
            return (cant * pu).quantize(Decimal("0.01"))
        if estado == self.EstadoRevision.AJUSTADO:
            return (self.rev_cantidad_aprobada * self.precio_unitario).quantize(Decimal("0.01"))
        return self.subtotal

    def __str__(self):
        return f"{self.nombre_producto} - Pedido #{self.pedido_id}"
