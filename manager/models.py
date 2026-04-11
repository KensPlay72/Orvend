from django.db import models
from .enums import *


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
# COMPRAS
# =========================
class Compras(Abstracto):
    TIPO_CONTADO = 1
    TIPO_CREDITO = 2

    TIPO_COMPRA_OPCIONES = (
        (TIPO_CONTADO, "Contado"),
        (TIPO_CREDITO, "Crédito"),
    )

    proveedor_id = models.IntegerField()

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

    ubicacion_id = models.IntegerField()

    def get_tipo_compra_display(self):
        return dict(self.TIPO_COMPRA_OPCIONES).get(self.tipo_compra, "Desconocido")

    def __str__(self):
        return f"Compra #{self.id} - {self.get_tipo_compra_display()}"


# =========================
# DETALLE COMPRA
# =========================

class DetalleCompra(Abstracto):
    compra_id = models.IntegerField()
    producto_id = models.IntegerField()

    cantidad = models.DecimalField(max_digits=18, decimal_places=2)
    precio_compra = models.DecimalField(max_digits=18, decimal_places=2)

    @property
    def total(self):
        return self.cantidad * self.precio_compra


# =========================
# AUTORIZACIÓN COMPRA
# =========================

class HAutorizarCompra(Abstracto):
    compra_id = models.IntegerField()
    producto_id = models.IntegerField()

    cantidad_comprada = models.DecimalField(max_digits=18, decimal_places=2)
    cantidad_autorizada = models.DecimalField(max_digits=18, decimal_places=2)

    fvencimiento = models.DateTimeField(null=True, blank=True)


# =========================
# DEVOLUCIÓN COMPRA
# =========================

class DevolucionCompra(Abstracto):
    compras_id = models.IntegerField()

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
    devolucion_compra_id = models.IntegerField()
    compras_id = models.IntegerField()
    producto_id = models.IntegerField()

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

    proveedor_id = models.IntegerField()
    compra_id = models.IntegerField()

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
    cuenta_por_pagar_id = models.IntegerField()

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
        related_name="inventarios"
    )

    compra = models.ForeignKey(
        "Compras",
        on_delete=models.PROTECT,
        related_name="inventarios"
    )

    ubicacion = models.ForeignKey(
        "Ubicaciones",
        on_delete=models.PROTECT,
        related_name="inventarios"
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
# MARCAS
# =========================

class Marcas(Abstracto):
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return self.nombre


# =========================
# TIPO MOVIMIENTO INVENTARIO
# =========================

class MovimientoInventario(Abstracto):


    tipo_movimiento = models.IntegerField(
        choices=TipoMovimiento.choices
    )

    producto = models.ForeignKey(
        "Productos",
        on_delete=models.PROTECT,
        related_name="movimientos"
    )

    ubicacion_origen = models.ForeignKey(
        "Ubicaciones",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_origen"
    )

    ubicacion_destino = models.ForeignKey(
        "Ubicaciones",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_destino"
    )

    cantidad = models.DecimalField(max_digits=18, decimal_places=2)

    stock_anterior = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    stock_resultante = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    compra_id = models.IntegerField(null=True, blank=True)
    traslado_id = models.IntegerField(null=True, blank=True)
    venta_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.producto} - {self.get_tipo_movimiento_display()}"


# =========================
# PRODUCTOS
# =========================

class Productos(Abstracto):
    nombre = models.CharField(max_length=50)

    descripcion = models.CharField(max_length=200, blank=True, default="")

    categoria = models.ForeignKey(
        "Categorias",
        on_delete=models.PROTECT,
        related_name="productos"
    )

    unidad_medida = models.ForeignKey(
        "UMedidas",
        on_delete=models.PROTECT,
        related_name="productos"
    )

    marca = models.ForeignKey(
        "Marcas",
        on_delete=models.PROTECT,
        related_name="productos"
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
        related_name="contactos",
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
# TRASLADOS
# =========================
class Traslados(Abstracto):
    solicitado_por_id = models.IntegerField()
    autorizado_por_id = models.IntegerField(null=True, blank=True)

    ubicacion_origen = models.ForeignKey(
        "Ubicaciones",
        on_delete=models.PROTECT,
        related_name="traslados_origen"
    )

    ubicacion_destino = models.ForeignKey(
        "Ubicaciones",
        on_delete=models.PROTECT,
        related_name="traslados_destino"
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
        related_name="detalles"
    )

    producto = models.ForeignKey(
        "Productos",
        on_delete=models.PROTECT
    )

    cantidad_solicitada = models.DecimalField(max_digits=18, decimal_places=2)
    cantidad_entregada = models.DecimalField(max_digits=18, decimal_places=2, default=0)

# =========================
# UBICACIONES
# =========================
class Ubicaciones(Abstracto):
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=20)

    codigo = models.CharField(max_length=10, null=True, blank=True)

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




