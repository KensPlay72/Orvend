from django.db import models
from .enums import *
from django.conf import settings


class Abstracto(models.Model):
    is_active = models.BooleanField(default=True)
    is_delete = models.BooleanField(default=False)

    f_creacion = models.DateTimeField(auto_now_add=True)
    f_modificacion = models.DateTimeField(null=True, blank=True)

    u_creo_id = models.IntegerField(null=True, blank=True)
    u_modifico_id = models.IntegerField(null=True, blank=True)

    class Meta:
        abstract = True

# =========================
# CATEGORIAS
# =========================

class Categorias(Abstracto):
    nombre = models.CharField(max_length=30)
    descripcion = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre
    
# =========================
# CLIENTES
# =========================
class Clientes(Abstracto):
    dni = models.CharField(max_length=14)

    nombre = models.CharField(max_length=100, null=True, blank=True)
    nombre2 = models.CharField(max_length=100, null=True, blank=True)

    apellido = models.CharField(max_length=100, null=True, blank=True)
    apellido2 = models.CharField(max_length=100, null=True, blank=True)

    empresa = models.CharField(max_length=100, null=True, blank=True)
    direccion = models.CharField(max_length=100, null=True, blank=True)

    telefono = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self):
        return " ".join(
            filter(None, [
                self.nombre,
                self.nombre2,
                self.apellido,
                self.apellido2
            ])
        ).strip()
    
# =========================
# MARCAS
# =========================
class Marcas(Abstracto):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return self.nombre


# =========================
# UNIDAD DE MEDIDA
# =========================
class UMedidas(Abstracto):
    nombre = models.CharField(max_length=30)
    abreviatura = models.CharField(max_length=10)

    def __str__(self):
        return self.abreviatura

# =========================
# PRODUCTOS
# =========================
class Productos(Abstracto):
    nombre = models.CharField(max_length=50)

    descripcion = models.CharField(max_length=200, blank=True, default="")

    categoria = models.ForeignKey(
        Categorias,
        on_delete=models.PROTECT,
        related_name="categoria_productos"
    )

    unidad_medida = models.ForeignKey(
        UMedidas,
        on_delete=models.PROTECT,
        related_name="umedida_productos"
    )

    marca = models.ForeignKey(
        Marcas,
        on_delete=models.PROTECT,
        related_name="marca_productos"
    )

    vencimiento = models.BooleanField(default=False)
    codigo_sku = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=200, blank=True, default="")

    precio_venta = models.DecimalField(max_digits=18, decimal_places=2)

    imagen_nombre = models.CharField(max_length=100, null=True, blank=True)
    imagen_url = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.nombre

# =========================
# PROVEEDORES
# =========================
class Proveedores(Abstracto):
    nombre_legal = models.CharField(max_length=150)
    nombre_comercial = models.CharField(max_length=150)
    rtn = models.CharField(max_length=50)
    dias_credito = models.IntegerField()

    telefono = models.CharField(max_length=30)
    email = models.EmailField(max_length=100)

    def __str__(self):
        return self.nombre_comercial

# =========================
# PROVEEDORES CONTACTOS
# =========================
class ProveedoresContactos(Abstracto):
    proveedor = models.ForeignKey(
        Proveedores,
        on_delete=models.CASCADE,
        related_name="proveedor_contactos",
        null=True,
        blank=True
    )

    nombre = models.CharField(max_length=100)
    puesto = models.CharField(max_length=100)
    telefono = models.CharField(max_length=30)
    email = models.EmailField(max_length=100)
    observaciones = models.CharField(max_length=150, blank=True, default="")

    def __str__(self):
        return self.nombre


# =========================
# UBICACIONES
# =========================
class Ubicaciones(Abstracto):

    class TipoUbicacion(models.IntegerChoices):
        BODEGA = 1, "Bodega"
        TIENDA = 2, "Tienda"

    nombre = models.CharField(max_length=120)
    tipo = models.IntegerField(choices=TipoUbicacion.choices)
    codigo = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.nombre


# =========================
# COMPRAS
# =========================
class Compras(Abstracto):
    TIPO_CONTADO = 1
    TIPO_CREDITO = 2

    TIPO_COMPRA_OPCIONES = (
        (TIPO_CONTADO, "Contado"),
        (TIPO_CREDITO, "Crédito"),
    )

    proveedor = models.ForeignKey(
        Proveedores,
        on_delete=models.CASCADE,
        related_name="proveedor_compras",
        null=False,
        blank=False
    )
    tipo_compra = models.IntegerField()

    estado = models.CharField(
        max_length=20,
        choices=EstadoCompra.choices,
        default=EstadoCompra.PENDIENTE
    )

    fecha_compra = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
    total = models.DecimalField(max_digits=18, decimal_places=2)
    observaciones = models.CharField(max_length=200, blank=True, default="")
    ubicacion = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="ubicacion_compras",
    )

    def get_tipo_compra_display(self):
        return dict(self.TIPO_COMPRA_OPCIONES).get(self.tipo_compra, "Desconocido")

    def __str__(self):
        return f"Compra #{self.id} - {self.get_tipo_compra_display()}"


# =========================
# DETALLE COMPRA
# =========================
class DetalleCompra(Abstracto):
    compra = models.ForeignKey(
        Compras,
        on_delete=models.CASCADE,
        related_name="compra_detalles",
        null=False,
        blank=False
    )
    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_compra_detalles",
        null=False,
        blank=False
    )

    cantidad = models.DecimalField(max_digits=18, decimal_places=2)
    precio_compra = models.DecimalField(max_digits=18, decimal_places=2)

    @property
    def total(self):
        return self.cantidad * self.precio_compra


# =========================
# AUTORIZACIÓN COMPRA
# =========================
class HAutorizarCompra(Abstracto):
    compra = models.ForeignKey(
        Compras,
        on_delete=models.CASCADE,
        related_name="compra_autorizaciones",
        null=False,
        blank=False
    )
    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_autorizaciones",
        null=False,
        blank=False
    )

    cantidad_comprada = models.DecimalField(max_digits=18, decimal_places=2)
    cantidad_autorizada = models.DecimalField(max_digits=18, decimal_places=2)

    fvencimiento = models.DateTimeField(null=True, blank=True)


# =========================
# DEVOLUCIÓN COMPRA
# =========================
class DevolucionCompra(Abstracto):
    compra = models.ForeignKey(
        Compras,
        on_delete=models.CASCADE,
        related_name="compra_devoluciones",
        null=False,
        blank=False
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoCompra.choices,
        default=EstadoCompra.PENDIENTE
    )

    observaciones = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return f"Devolución #{self.id}"


# =========================
# DETALLE DEVOLUCIÓN
# =========================
class DevolucionCompraDetalle(models.Model):
    devolucion_compra = models.ForeignKey(
        DevolucionCompra,
        on_delete=models.CASCADE,
        related_name="devolucion_detalles",
        null=False,
        blank=False
    )
    compra = models.ForeignKey(
        Compras,
        on_delete=models.CASCADE,
        related_name="compra_devolucion_detalles",
        null=False,
        blank=False
    )
    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_devolucion_detalles",
        null=False,
        blank=False
    )

    cantidad = models.DecimalField(max_digits=18, decimal_places=2)

    motivo = models.IntegerField(
        choices=MotivoDevolucion.choices
    )

    def __str__(self):
        return f"Detalle devolución #{self.id}"

# =========================
# CUENTAS POR PAGAR
# =========================
class CuentasPorPagar(Abstracto):
    proveedor = models.ForeignKey(
        Proveedores,
        on_delete=models.CASCADE,
        related_name="proveedor_cuentas_por_pagar",
        null=False,
        blank=False
    )
    compra = models.ForeignKey(
        Compras,
        on_delete=models.CASCADE,
        related_name="compra_cuentas_por_pagar",
        null=False,
        blank=False
    )

    monto_total = models.DecimalField(max_digits=18, decimal_places=2)
    monto_pendiente = models.DecimalField(max_digits=18, decimal_places=2)

    fecha_vencimiento = models.DateTimeField()

    estado = models.IntegerField(
        choices=EstadoCuenta.choices,
        default=EstadoCuenta.PENDIENTE
    )

    def __str__(self):
        return f"Cuenta #{self.id} - {self.get_estado_display()}"

    @property
    def pagado(self):
        return self.monto_pendiente <= 0


# =========================
# REGISTRO ABONOS
# =========================
class RegistroAbonos(Abstracto):
    cuenta_por_pagar = models.ForeignKey(
        CuentasPorPagar,
        on_delete=models.CASCADE,
        related_name="cuenta_abonos",
        null=False,
        blank=False
    )

    monto_abonado = models.DecimalField(max_digits=18, decimal_places=2)
    monto_pendiente = models.DecimalField(max_digits=18, decimal_places=2)

    liquidado = models.BooleanField(default=False)

    def __str__(self):
        return f"Abono #{self.id}"
    
# =========================
# INVENTARIOS
# =========================
class Inventarios(Abstracto):
    producto = models.ForeignKey(
        "Productos",
        on_delete=models.PROTECT,
        related_name="producto_inventarios"
    )

    compra = models.ForeignKey(
        "Compras",
        on_delete=models.PROTECT,
        related_name="compra_inventarios",
        null=True,
    )

    ubicacion = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="ubicacion_inventarios"
    )

    cantidad = models.DecimalField(max_digits=18, decimal_places=2)

    stock_minimo = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=5
    )

    fvencimiento = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.producto} - {self.cantidad}"


# =========================
# TRASLADOS
# =========================
class Traslados(Abstracto):
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='solicitado_traslados'
    )

    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='autorizaciones_traslados'
    )

    ubicacion_origen = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="ubicacion_origen_traslados"
    )

    ubicacion_destino = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="ubicacion_destino_traslados"
    )

    fecha_autorizacion = models.DateTimeField(null=True, blank=True)

    estado = models.CharField(
        max_length=20,
        choices=EstadoCompra.choices
    )

    observaciones = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return f"Traslado #{self.id}"

# =========================
# DETALLES TRASLADOS
# =========================
class DetalleTraslado(Abstracto):
    traslado = models.ForeignKey(
        Traslados,
        on_delete=models.CASCADE,
        related_name="detalles_traslado"
    )

    producto = models.ForeignKey(
        "Productos",
        on_delete=models.PROTECT,
        related_name="productos_traslado"
    )

    cantidad_solicitada = models.DecimalField(max_digits=18, decimal_places=2)
    cantidad_entregada = models.DecimalField(max_digits=18, decimal_places=2, default=0)

# =========================
# MOVIMIENTOS INVENTARIOS
# =========================
class TipoMovimientoInventario(models.IntegerChoices):
    # ENTRADAS
    ENTRADA_COMPRA = 1, "Entrada Compra"
    TRASLADO_ENTRADA = 2, "Traslado Entrada"
    AJUSTE_ENTRADA = 3, "Ajuste Entrada"
    DEVOLUCION_CLIENTE = 4, "Devolución Cliente"
    CAMBIO_CLIENTE_ENTRADA = 5, "Cambio Cliente Entrada"

    # SALIDAS
    SALIDA_VENTA = 10, "Salida Venta"
    TRASLADO_SALIDA = 11, "Traslado Salida"
    AJUSTE_SALIDA = 12, "Ajuste Salida"
    DESCARTE = 13, "Descarte"
    DEVOLUCION_PROVEEDOR = 14, "Devolución Proveedor"
    CAMBIO_CLIENTE_SALIDA = 15, "Cambio Cliente Salida"


class MovimientoInventario(models.Model):
    tipo_movimiento = models.IntegerField(
        choices=TipoMovimientoInventario.choices
    )

    # Producto afectado
    producto = models.ForeignKey(
        Productos,
        on_delete=models.CASCADE,
        related_name='movimientos'
    )

    # Ubicaciones
    ubicacion_origen = models.ForeignKey(
        Ubicaciones,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_origen'
    )

    ubicacion_destino = models.ForeignKey(
        Ubicaciones,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_destino'
    )

    # Cantidad (siempre positiva)
    cantidad = models.DecimalField(max_digits=18, decimal_places=2)

    # Auditoría
    stock_anterior = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    stock_resultante = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )

    # Documento origen
    compra = models.ForeignKey(
        Compras,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    traslado = models.ForeignKey(
        Traslados,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    venta_id = models.IntegerField(null=True, blank=True)  # futura tabla ventas

    def __str__(self):
        return f"Movimiento {self.id} - {self.get_tipo_movimiento_display()}"



