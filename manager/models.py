from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
import uuid
from decimal import Decimal
import random
import string

from .enums import (
    EstadoCompra,
    EstadoCuenta,
    EstadoDevolucionCompra,
    Estados,
    MotivoDevolucion,
)


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

    dni = models.CharField(
        max_length=14
    )

    nombre = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    nombre2 = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    apellido = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    apellido2 = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    empresa = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    direccion = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    enviar_factura_whatsapp = models.BooleanField(
        default=False,
        help_text="Envía la factura por WhatsApp al facturar a nombre de este cliente."
    )

    email = models.EmailField(
        max_length=100,
        null=True,
        blank=True
    )

    d_credito = models.IntegerField(
        null=True,
        blank=True
    )

    max_credito = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True
    )

    pais = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    departamento = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    municipio = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    cod_cliente = models.CharField(
        max_length=7,
        unique=True,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["is_delete", "id"], name="cliente_listado_idx"),
        ]
        permissions = [
            (
                "enviar_facturas_whatsapp",
                "Puede marcar clientes para enviar facturas por WhatsApp",
            ),
        ]

    def generar_codigo_cliente(self):

        caracteres = string.ascii_uppercase + string.digits

        while True:

            codigo = "".join(
                random.choices(caracteres, k=7)
            )

            if not Clientes.objects.filter(
                cod_cliente=codigo
            ).exists():

                return codigo

    def save(self, *args, **kwargs):

        if not self.cod_cliente:
            self.cod_cliente = self.generar_codigo_cliente()

        self.f_modificacion = timezone.now()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self):

        return " ".join(
            filter(
                None,
                [
                    self.nombre,
                    self.nombre2,
                    self.apellido,
                    self.apellido2
                ]
            )
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
    valor = models.IntegerField(null=False, blank=False, default=0)

    def __str__(self):
        return self.abreviatura


# =========================
# PRODUCTOS
# =========================
class Productos(Abstracto):
    tienda_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    nombre = models.CharField(max_length=100)

    descripcion = models.CharField(max_length=200, blank=True, default="")

    categoria = models.ForeignKey(
        Categorias, on_delete=models.PROTECT, related_name="categoria_productos"
    )

    unidad_medida = models.ForeignKey(
        UMedidas, on_delete=models.PROTECT, related_name="umedida_productos"
    )

    marca = models.ForeignKey(
        Marcas, on_delete=models.PROTECT, related_name="marca_productos"
    )

    vencimiento = models.BooleanField(default=False)
    codigo_sku = models.CharField(max_length=100, unique=True)

    precio_venta = models.DecimalField(max_digits=18, decimal_places=2)
    precio_venta_min = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    precio_venta_max = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )

    impuesto = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    equival_unid = models.PositiveIntegerField(
        default=1
    )
    is_master = models.BooleanField(default=False)

    class Meta:
        indexes = [
            # Listados y buscadores de productos/inventario.
            models.Index(
                fields=["is_delete", "is_active", "nombre", "id"],
                name="prod_listado_act_nombre_idx",
            ),
            models.Index(
                fields=["is_delete", "nombre", "id"],
                name="prod_listado_nombre_idx",
            ),
        ]

    def __str__(self):
        return self.nombre


class ProductosRel(Abstracto):
    producto_master = models.ForeignKey(
        Productos,
        on_delete=models.CASCADE,
        related_name="producto_master_rel"
    )

    producto_relacionado = models.ForeignKey(
        Productos,
        on_delete=models.CASCADE,
        related_name="producto_relacionado_rel"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["producto_master", "producto_relacionado"],
                name="unique_producto_rel"
            )
        ]

    def __str__(self):
        return (
            f"{self.producto_master.nombre} - "
            f"{self.producto_relacionado.nombre}"
        )

        
class ProductosImagenes(models.Model):
    producto = models.ForeignKey(
        Productos, on_delete=models.CASCADE, related_name="imagenes_producto"
    )
    imagen_nombre = models.CharField(max_length=100, null=True, blank=True)
    # Nombre remoto real (incluye el prefijo aleatorio), independiente del host.
    imagen_archivo = models.CharField(max_length=150, blank=True, default="")
    imagen_url = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.producto.nombre} - {self.imagen_nombre or self.imagen_archivo or self.imagen_url}"


# =========================
# COMBOS
# =========================
class Combos(Abstracto):
    nombre = models.CharField(max_length=120)
    codigo_sku = models.CharField(max_length=50, unique=True)
    costo_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=18, decimal_places=2)
    precio_venta_min = models.DecimalField(max_digits=18, decimal_places=2)
    precio_venta_max = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} ({self.codigo_sku})"


class ComboImagen(models.Model):
    """Imagen principal opcional de un combo, almacenada en Nextcloud."""

    combo = models.OneToOneField(
        Combos, on_delete=models.CASCADE, related_name="imagen"
    )
    imagen_nombre = models.CharField(max_length=100, null=True, blank=True)
    imagen_archivo = models.CharField(max_length=150, blank=True, default="")
    imagen_url = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.combo.nombre} - {self.imagen_nombre or self.imagen_archivo}"


class ConfiguracionEmpresa(Abstracto):
    """Configuración única de la empresa para esta instalación del ERP."""

    nombre_comercial = models.CharField(max_length=150, default="Orvend Mart")
    razon_social = models.CharField(max_length=180, blank=True, default="")
    rtn = models.CharField(max_length=30, blank=True, default="")
    telefono = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(max_length=100, blank=True, default="")
    direccion = models.CharField(max_length=255, blank=True, default="")
    mensaje_factura = models.CharField(max_length=180, blank=True, default="")
    MONEDA_LEMPIRA = "HNL"
    MONEDA_DOLAR = "USD"
    MONEDA_OPCIONES = (
        (MONEDA_LEMPIRA, "L. Lempira"),
        (MONEDA_DOLAR, "$. Dólar"),
    )
    moneda = models.CharField(
        max_length=3,
        choices=MONEDA_OPCIONES,
        default=MONEDA_LEMPIRA,
    )
    cotizacion_dias_validez = models.PositiveIntegerField(default=7)
    DISENO_RECIBO = "RECIBO"
    DISENO_PAGINA = "PAGINA"
    DISENO_FACTURA_OPCIONES = (
        (DISENO_RECIBO, "Recibo"),
        (DISENO_PAGINA, "Página"),
    )
    diseno_factura = models.CharField(
        max_length=10,
        choices=DISENO_FACTURA_OPCIONES,
        default=DISENO_RECIBO,
    )
    logo_nombre = models.CharField(max_length=100, blank=True, default="")
    logo_archivo = models.CharField(max_length=150, blank=True, default="")
    logo_url = models.CharField(max_length=255, blank=True, default="")
    tienda_color_primario = models.CharField(max_length=7, default="#32877F")
    tienda_color_secundario = models.CharField(max_length=7, default="#10463E")
    tienda_color_acento = models.CharField(max_length=7, default="#F5A623")
    tienda_subtitulo = models.CharField(max_length=180, blank=True, default="")

    class Meta:
        verbose_name = "Configuración de empresa"
        verbose_name_plural = "Configuración de empresa"
        permissions = [
            ("gestionar_configuracion", "Puede administrar la configuración de empresa"),
            ("gestionar_tienda_virtual", "Puede configurar la tienda virtual"),
        ]

    def __str__(self):
        return self.nombre_comercial

    @property
    def simbolo_moneda(self):
        return "$." if self.moneda == self.MONEDA_DOLAR else "L."


class SuscripcionSistema(models.Model):
    """Vigencia comercial de esta instalación de OrvendMart.

    Solo existe un registro. Mantenerlo separado de la configuración del
    negocio evita que un usuario operativo pueda cambiar el acceso al sistema.
    """

    CLAVE_CACHE_ESTADO = "manager:suscripcion_sistema:estado:v1"

    unica_configuracion = models.BooleanField(default=True, unique=True, editable=False)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activa = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True, default="")
    f_creacion = models.DateTimeField(auto_now_add=True)
    f_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pago y suscripción"
        verbose_name_plural = "Pago y suscripción"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="suscripcion_fechas_validas",
            )
        ]

    def __str__(self):
        return f"Suscripción {self.fecha_inicio} a {self.fecha_fin}"

    def esta_vigente_en(self, fecha=None):
        fecha = fecha or timezone.localdate()
        return self.activa and self.fecha_inicio <= fecha <= self.fecha_fin

    @classmethod
    def estado_actual(cls):
        """Obtiene el estado con caché para no consultar la BD por solicitud."""
        estado = cache.get(cls.CLAVE_CACHE_ESTADO)
        if estado is not None:
            return estado

        suscripcion = cls.objects.only(
            "fecha_inicio", "fecha_fin", "activa"
        ).first()
        if suscripcion is None:
            # Una instalación nueva no queda bloqueada antes de que el
            # administrador pueda registrar su primer período.
            estado = {"configurada": False, "vigente": True}
        else:
            estado = {
                "configurada": True,
                "vigente": suscripcion.esta_vigente_en(),
                "fecha_inicio": suscripcion.fecha_inicio.isoformat(),
                "fecha_fin": suscripcion.fecha_fin.isoformat(),
            }

        # Un período puede vencer al cambiar de día. Un TTL breve evita una
        # consulta por cada petición sin retrasar materialmente el bloqueo.
        cache.set(cls.CLAVE_CACHE_ESTADO, estado, timeout=300)
        return estado

    @classmethod
    def esta_vigente(cls):
        return cls.estado_actual()["vigente"]

    @classmethod
    def invalidar_cache(cls):
        cache.delete(cls.CLAVE_CACHE_ESTADO)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invalidar_cache()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.invalidar_cache()


class BannerTienda(models.Model):
    """Banner opcional de la portada pública, almacenado en Nextcloud."""

    configuracion = models.ForeignKey(
        ConfiguracionEmpresa,
        on_delete=models.CASCADE,
        related_name="banners_tienda",
    )
    TIPO_BANNER = "BANNER"
    TIPO_CARRUSEL = "CARRUSEL"
    TIPO_OPCIONES = ((TIPO_BANNER, "Banner"), (TIPO_CARRUSEL, "Carrusel"))
    tipo = models.CharField(max_length=10, choices=TIPO_OPCIONES, default=TIPO_CARRUSEL)
    imagen_nombre = models.CharField(max_length=120)
    imagen_archivo = models.CharField(max_length=180, unique=True)
    imagen_url = models.CharField(max_length=255, blank=True, default="")
    titulo = models.CharField(max_length=100, blank=True, default="")
    enlace = models.CharField(max_length=255, blank=True, default="")
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ("orden", "id")

    def __str__(self):
        return f"Banner {self.id} - {self.configuracion.nombre_comercial}"


class DetalleCombo(models.Model):
    combo = models.ForeignKey(
        Combos, on_delete=models.CASCADE, related_name="detalles"
    )
    producto = models.ForeignKey(
        Productos, on_delete=models.PROTECT, related_name="detalles_combo"
    )
    cantidad = models.DecimalField(max_digits=18, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["combo", "producto"], name="unique_producto_combo"
            )
        ]


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
    saldo = models.DecimalField(max_digits=18, decimal_places=2, default=0, null=True, blank=True) 

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
        blank=True,
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
    nombre = models.CharField(max_length=120)
    ubicacion = models.CharField(max_length=255, null=True, blank=True)
    codigo = models.CharField(max_length=10, null=True, blank=True)
    es_bodega = models.BooleanField(default=False)
    es_tienda = models.BooleanField(default=False)
    bodega = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="tiendas"
    )

    def __str__(self):
        return self.nombre


# =========================
# COMPRAS
# =========================
class Compras(Abstracto):
    documento_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
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
        blank=False,
    )
    tipo_compra = models.IntegerField()

    estado = models.CharField(
        max_length=20, choices=EstadoCompra.choices, default=EstadoCompra.PENDIENTE
    )

    fecha_compra = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True)
    fecha_llegada_bodega = models.DateTimeField(null=True, blank=True)
    llegada_bodega_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compras_llegadas_bodega",
    )
    total = models.DecimalField(max_digits=18, decimal_places=2)
    total_antes_impuesto = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    total_impuesto = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    saldo_utilizado = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    es_cambio = models.BooleanField(default=False)
    observaciones = models.CharField(max_length=200, blank=True, default="")
    ubicacion = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="ubicacion_compras",
    )

    class Meta:
        indexes = [
            # Recepción por ubicación/estado y listados/exportaciones por fecha.
            models.Index(
                fields=["is_delete", "ubicacion", "estado", "fecha_compra"],
                name="compr_recep_ubi_est_fecha_idx",
            ),
            models.Index(
                fields=["is_delete", "fecha_compra"],
                name="compr_export_fecha_idx",
            ),
            models.Index(
                fields=["u_creo_id", "is_delete", "id"],
                name="compr_usuario_listado_idx",
            ),
        ]

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
        blank=False,
    )
    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_compra_detalles",
        null=False,
        blank=False,
    )

    cantidad = models.DecimalField(max_digits=18, decimal_places=2)
    precio_compra = models.DecimalField(max_digits=18, decimal_places=2)
    impuesto_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    impuesto_unitario = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    precio_compra_con_impuesto = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["compra", "producto"], name="detallecomp_compra_prod_idx"
            ),
            models.Index(
                fields=["producto", "is_delete"], name="detallecomp_prod_act_idx"
            ),
        ]

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
        blank=False,
    )
    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_autorizaciones",
        null=False,
        blank=False,
    )

    cantidad_comprada = models.DecimalField(max_digits=18, decimal_places=2)
    # Una recepción convertida desde unidades hijas puede equivaler a una
    # fracción de presentación (p. ej. 10 de 12 unidades = 0.833333 caja).
    cantidad_autorizada = models.DecimalField(max_digits=18, decimal_places=6)

    fvencimiento = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["compra", "producto"], name="hautcomp_compra_prod_idx"
            ),
        ]
        permissions = [
            (
                "gestionar_recepcion_inventario",
                "Puede gestionar la recepción de inventario",
            ),
            (
                "multirecepcion",
                "Puede ver y gestionar recepciones de todas las ubicaciones",
            ),
        ]


# =========================
# DEVOLUCIÓN COMPRA
# =========================
class DevolucionCompra(Abstracto):
    RESOLUCION_CAMBIO = "CAMBIO"
    RESOLUCION_SALDO_FAVOR = "SALDO_FAVOR"
    RESOLUCION_OPCIONES = (
        (RESOLUCION_CAMBIO, "Cambio"),
        (RESOLUCION_SALDO_FAVOR, "Saldo a favor"),
    )

    compra = models.ForeignKey(
        Compras,
        on_delete=models.CASCADE,
        related_name="compra_devoluciones",
        null=False,
        blank=False,
    )
    # Se expone en URLs y documentos en lugar del ID consecutivo interno.
    documento_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    estado = models.CharField(
        max_length=20,
        choices=EstadoDevolucionCompra.choices,
        default=EstadoDevolucionCompra.PENDIENTE,
    )
    observaciones = models.CharField(max_length=300, blank=True, default="")
    resolucion = models.CharField(
        max_length=20, choices=RESOLUCION_OPCIONES, null=True, blank=True
    )
    monto_resolucion = models.DecimalField(
        max_digits=18, decimal_places=2, default=0
    )
    compra_cambio = models.ForeignKey(
        Compras,
        on_delete=models.SET_NULL,
        related_name="devoluciones_cambio_origen",
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["compra", "estado"], name="devcomp_compra_estado_idx"
            ),
        ]

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
        blank=False,
    )
    compra = models.ForeignKey(
        Compras,
        on_delete=models.CASCADE,
        related_name="compra_devolucion_detalles",
        null=False,
        blank=False,
    )
    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_devolucion_detalles",
        null=False,
        blank=False,
    )

    # Equivalente de la presentación comprada; permite devolver unidades hijo.
    cantidad = models.DecimalField(max_digits=18, decimal_places=6)
    producto_hijo = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_hijo_devolucion_detalles",
        null=True,
        blank=True,
    )
    cantidad_hijo = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )

    motivo = models.IntegerField(choices=MotivoDevolucion.choices)

    class Meta:
        indexes = [
            models.Index(
                fields=["compra", "producto"], name="devcompdet_compra_prod_idx"
            ),
        ]

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
        blank=False,
    )
    compra = models.ForeignKey(
        Compras,
        on_delete=models.CASCADE,
        related_name="compra_cuentas_por_pagar",
        null=False,
        blank=False,
    )

    monto_total = models.DecimalField(max_digits=18, decimal_places=2)
    monto_pendiente = models.DecimalField(max_digits=18, decimal_places=2)

    fecha_vencimiento = models.DateTimeField()

    estado = models.IntegerField(
        choices=EstadoCuenta.choices, default=EstadoCuenta.PENDIENTE
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["estado", "fecha_vencimiento"], name="cxp_estado_venc_idx"
            ),
        ]

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
        blank=False,
    )

    monto_abonado = models.DecimalField(max_digits=18, decimal_places=2)
    monto_pendiente = models.DecimalField(max_digits=18, decimal_places=2)

    liquidado = models.BooleanField(default=False)

    def __str__(self):
        return f"Abono #{self.id}"


# =========================
# TRASLADOS
# =========================
class Traslados(Abstracto):
    documento_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitado_traslados",
    )

    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="autorizaciones_traslados",
    )

    ubicacion_origen = models.ForeignKey(
        Ubicaciones, on_delete=models.PROTECT, related_name="ubicacion_origen_traslados"
    )

    ubicacion_destino = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="ubicacion_destino_traslados",
    )

    fecha_autorizacion = models.DateTimeField(null=True, blank=True)

    estado = models.CharField(max_length=20, choices=Estados.choices)

    observaciones = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(
                fields=["is_delete", "ubicacion_destino", "estado", "f_creacion"],
                name="traslado_dest_est_fecha_idx",
            ),
        ]

    def __str__(self):
        return f"Traslado #{self.id}"


# =========================
# DETALLES TRASLADOS
# =========================
class DetalleTraslado(Abstracto):
    traslado = models.ForeignKey(
        Traslados, on_delete=models.CASCADE, related_name="detalles_traslado"
    )

    producto = models.ForeignKey(
        "Productos", on_delete=models.PROTECT, related_name="productos_traslado"
    )

    cantidad_solicitada = models.DecimalField(max_digits=18, decimal_places=2)
    cantidad_entregada = models.DecimalField(max_digits=18, decimal_places=2, default=0)


# =========================
# INVENTARIOS
# =========================
class Inventarios(Abstracto):
    producto = models.ForeignKey(
        Productos, on_delete=models.PROTECT, related_name="producto_inventarios"
    )

    compra = models.ForeignKey(
        Compras,
        on_delete=models.PROTECT,
        related_name="compra_inventarios",
        null=True,
    )
    ubicacion = models.ForeignKey(
        Ubicaciones, on_delete=models.PROTECT, related_name="ubicacion_inventarios"
    )

    cantidad = models.DecimalField(max_digits=18, decimal_places=6)

    stock_minimo = models.DecimalField(max_digits=18, decimal_places=2, default=5)

    fvencimiento = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["producto", "ubicacion", "is_delete"],
                name="inv_prod_ubi_act_idx",
            ),
            models.Index(
                fields=["producto", "is_delete", "fvencimiento"],
                name="inv_prod_act_venc_idx",
            ),
        ]

    def __str__(self):
        return f"{self.producto} - {self.cantidad}"


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
    tipo_movimiento = models.IntegerField(choices=TipoMovimientoInventario.choices)

    # Producto afectado
    producto = models.ForeignKey(
        Productos, on_delete=models.CASCADE, related_name="movimientos"
    )

    # Ubicaciones
    ubicacion_origen = models.ForeignKey(
        Ubicaciones,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_origen",
    )

    ubicacion_destino = models.ForeignKey(
        Ubicaciones,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_destino",
    )

    # Cantidad (siempre positiva)
    cantidad = models.DecimalField(max_digits=18, decimal_places=6)

    # Auditoría
    stock_anterior = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    stock_resultante = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )

    # Documento origen
    compra = models.ForeignKey(
        Compras, on_delete=models.SET_NULL, null=True, blank=True
    )

    traslado = models.ForeignKey(
        Traslados, on_delete=models.SET_NULL, null=True, blank=True
    )

    venta_id = models.IntegerField(null=True, blank=True)  # futura tabla ventas

    def __str__(self):
        return f"Movimiento {self.id} - {self.get_tipo_movimiento_display()}"





class Descuento(Abstracto):
    # =========================
    # IDENTIFICACION
    # =========================

    nombre = models.CharField(max_length=150)

    descripcion = models.TextField(null=True, blank=True)

    # =========================
    # TIPO ACTIVACION
    # =========================

    es_cupon = models.BooleanField(default=False)

    codigo = models.CharField(max_length=50, unique=True, null=True, blank=True)

    # =========================
    # TIPO DESCUENTO
    # =========================

    es_porcentaje = models.BooleanField(default=True)

    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # =========================
    # TIPO CANTIDAD
    # =========================

    es_cantidad = models.BooleanField(default=False)

    cantidad_lleva = models.IntegerField(null=True, blank=True)
    cantidad_paga = models.IntegerField(null=True, blank=True)
    # =========================
    # APLICACION
    # =========================

    aplicar_productos = models.BooleanField(default=False)

    aplicar_categorias = models.BooleanField(default=False)

    productos = models.ForeignKey(
        Productos, on_delete=models.SET_NULL, blank=True, null=True
    )

    categorias = models.ForeignKey(
        Categorias, on_delete=models.SET_NULL, blank=True, null=True
    )

    # =========================
    # LIMITES
    # =========================

    limite_uso = models.IntegerField(null=True, blank=True)

    cantidad_usados = models.IntegerField(default=0)

    # =========================
    # FECHAS
    # =========================

    fecha_inicio = models.DateTimeField(null=True, blank=True)

    fecha_fin = models.DateTimeField(null=True, blank=True)

    # =========================
    # CONFIGURACIONES
    # =========================

    acumulable = models.BooleanField(default=False)

    # =========================
    # METODOS
    # =========================

    def vigente(self):

        ahora = timezone.now()

        if self.fecha_inicio and ahora < self.fecha_inicio:
            return False

        if self.fecha_fin and ahora > self.fecha_fin:
            return False

        if self.limite_uso is not None:
            if self.cantidad_usados >= self.limite_uso:
                return False

        return self.is_active and not self.is_delete

    def generar_codigo(self):

        return str(uuid.uuid4()).replace("-", "").upper()[:10]

    def save(self, *args, **kwargs):

        self.f_modificacion = timezone.now()

        if self.es_cupon and not self.codigo:
            self.codigo = self.generar_codigo()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class PerfilUsuario(models.Model):
    usuarios = models.OneToOneField(User, on_delete=models.CASCADE)
    ubicacion = models.ForeignKey(
        Ubicaciones, on_delete=models.PROTECT, related_name="usuarios_ubicacion"
    )

    def __str__(self):
        return self.usuarios.username


class datos_sat(Abstracto):
    nombre_cai = models.CharField(max_length=100, null=True)
    numero_cai = models.CharField(max_length=100)
    rango_inicial = models.IntegerField()
    rango_final = models.IntegerField()
    fecha_de_emision = models.DateTimeField()
    fecha_de_vencimiento = models.DateTimeField()

    id_sucursal = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="sucursal_cai",
        blank=True,
        null=False,
    )

    def __str__(self):
        return self.numero_cai


class facturas_cai(Abstracto):
    numero_factura = models.IntegerField(unique=True)
    documento_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    id_cai = models.ForeignKey(
        datos_sat,
        on_delete=models.PROTECT,
        related_name="cai_facturas",
        null=True,
        blank=True,
    )
    es_sat = models.BooleanField(default=False)

    def __str__(self):
        return f"Factura #{self.numero_factura} - CAI: {self.id_cai.numero_cai}"


class Ventas(Abstracto):
    TIPO_VENTA_CONTADO = "contado"
    TIPO_VENTA_CREDITO = "credito"
    TIPO_VENTA_OPCIONES = (
        (TIPO_VENTA_CONTADO, "Contado"),
        (TIPO_VENTA_CREDITO, "Crédito"),
    )

    id_factura_cai = models.ForeignKey(
        facturas_cai,
        on_delete=models.PROTECT,
        related_name="factura_ventas",
        null=True,
        blank=True,
    )

    id_cliente = models.ForeignKey(
        Clientes,
        on_delete=models.PROTECT,
        related_name="cliente_ventas",
        null=True,
        blank=True,
    )

    sucursal = models.ForeignKey(
        Ubicaciones, on_delete=models.PROTECT, related_name="sucursal_ventas"
    )

    subtotal = models.DecimalField(max_digits=18, decimal_places=2)

    impuesto_15 = models.DecimalField(max_digits=18, decimal_places=2)

    impuesto_18 = models.DecimalField(max_digits=18, decimal_places=2)

    descuento = models.DecimalField(max_digits=18, decimal_places=2)

    nota_credito = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    con_rtn = models.BooleanField(default=False)

    costo_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    utilidad_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    total = models.DecimalField(max_digits=18, decimal_places=2)

    tipo_pago = models.CharField(max_length=50)
    tipo_venta = models.CharField(
        max_length=20, choices=TIPO_VENTA_OPCIONES, default=TIPO_VENTA_CONTADO
    )

    class Meta:
        indexes = [
            models.Index(fields=["f_creacion"], name="venta_fecha_idx"),
            models.Index(
                fields=["sucursal", "f_creacion"], name="venta_suc_fecha_idx"
            ),
        ]

    def __str__(self):
        return f"Venta #{self.id}"


# =========================
# CUENTAS POR COBRAR
# =========================
class CuentasPorCobrar(Abstracto):
    cliente = models.ForeignKey(
        Clientes,
        on_delete=models.PROTECT,
        related_name="cliente_cuentas_por_cobrar",
    )

    venta = models.OneToOneField(
        Ventas,
        on_delete=models.PROTECT,
        related_name="venta_cuenta_por_cobrar",
    )

    monto_total = models.DecimalField(max_digits=18, decimal_places=2)
    monto_pendiente = models.DecimalField(max_digits=18, decimal_places=2)
    fecha_vencimiento = models.DateTimeField()

    estado = models.IntegerField(
        choices=EstadoCuenta.choices,
        default=EstadoCuenta.PENDIENTE,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["estado", "fecha_vencimiento"], name="cxc_estado_venc_idx"
            ),
        ]

    def __str__(self):
        return f"Cuenta por cobrar #{self.id} - {self.get_estado_display()}"

    @property
    def pagado(self):
        return self.monto_pendiente <= 0


class RegistroAbonosCobrar(Abstracto):
    cuenta_por_cobrar = models.ForeignKey(
        CuentasPorCobrar,
        on_delete=models.CASCADE,
        related_name="cuenta_abonos",
    )

    monto_abonado = models.DecimalField(max_digits=18, decimal_places=2)
    monto_pendiente = models.DecimalField(max_digits=18, decimal_places=2)
    liquidado = models.BooleanField(default=False)

    def __str__(self):
        return f"Abono por cobrar #{self.id}"


class DetalleVenta(Abstracto):
    venta = models.ForeignKey(
        Ventas, on_delete=models.PROTECT, related_name="venta_detalles"
    )

    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_venta_detalles",
        null=True,
        blank=True,
    )

    combo = models.ForeignKey(
        Combos,
        on_delete=models.PROTECT,
        related_name="combo_venta_detalles",
        null=True,
        blank=True,
    )

    cantidad = models.DecimalField(max_digits=18, decimal_places=2)

    precio_unitario = models.DecimalField(max_digits=18, decimal_places=2)

    costo_unitario = models.DecimalField(max_digits=18, decimal_places=2)

    utilidad_unitaria = models.DecimalField(max_digits=18, decimal_places=2)

    utilidad_total = models.DecimalField(max_digits=18, decimal_places=2)

    descuento = models.DecimalField(max_digits=18, decimal_places=2)

    # Importes por línea para distinguir precio original y devoluciones.
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    monto_devuelto = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    impuesto_15 = models.DecimalField(max_digits=18, decimal_places=2)

    impuesto_18 = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        indexes = [
            models.Index(
                fields=["venta", "producto"], name="detalleventa_venta_prod_idx"
            ),
        ]


class Cotizacion(Abstracto):
    """Propuesta comercial generada desde Caja; no afecta inventario ni caja."""

    numero_cotizacion = models.CharField(max_length=20, unique=True)
    documento_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    cliente = models.ForeignKey(
        Clientes,
        on_delete=models.PROTECT,
        related_name="cliente_cotizaciones",
        null=True,
        blank=True,
    )
    cliente_nombre = models.CharField(max_length=180, blank=True, default="")
    con_rtn = models.BooleanField(default=False)
    sucursal = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="sucursal_cotizaciones",
    )
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    impuesto_15 = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    impuesto_18 = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        ordering = ["-id"]
        permissions = [
            ("generar_cotizaciones", "Puede generar cotizaciones desde caja"),
        ]

    def __str__(self):
        return self.numero_cotizacion


class DetalleCotizacion(Abstracto):
    cotizacion = models.ForeignKey(
        Cotizacion,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="producto_cotizacion_detalles",
        null=True,
        blank=True,
    )
    combo = models.ForeignKey(
        Combos,
        on_delete=models.PROTECT,
        related_name="combo_cotizacion_detalles",
        null=True,
        blank=True,
    )
    codigo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=18, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=18, decimal_places=2)
    descuento = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    impuesto_15 = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    impuesto_18 = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)


class DevolucionVenta(Abstracto):
    RESOLUCION_NOTA_CREDITO = "NOTA_CREDITO"
    RESOLUCION_DEDUCIR_SALDO = "DEDUCIR_SALDO"
    RESOLUCION_OPCIONES = (
        (RESOLUCION_NOTA_CREDITO, "Nota de crédito"),
        (RESOLUCION_DEDUCIR_SALDO, "Deducir saldo"),
    )

    class Estado(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        USADA = "USADA", "Usada"
        ANULADA = "ANULADA", "Anulada"

    venta = models.ForeignKey(
        Ventas,
        on_delete=models.PROTECT,
        related_name="devoluciones_venta",
    )
    nota_credito = models.CharField(max_length=24, unique=True)
    motivo = models.IntegerField(choices=MotivoDevolucion.choices)
    justificacion = models.CharField(max_length=500)
    monto_total = models.DecimalField(max_digits=18, decimal_places=2)
    estado = models.CharField(
        max_length=12,
        choices=Estado.choices,
        default=Estado.DISPONIBLE,
    )
    venta_aplicada = models.ForeignKey(
        Ventas,
        on_delete=models.PROTECT,
        related_name="notas_credito_aplicadas",
        null=True,
        blank=True,
    )
    fecha_uso = models.DateTimeField(null=True, blank=True)
    resolucion = models.CharField(
        max_length=20,
        choices=RESOLUCION_OPCIONES,
        default=RESOLUCION_NOTA_CREDITO,
    )
    abono_cxc = models.OneToOneField(
        RegistroAbonosCobrar,
        on_delete=models.SET_NULL,
        related_name="devolucion_origen",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.nota_credito} - Venta #{self.venta_id}"


class DevolucionVentaDetalle(models.Model):
    devolucion_venta = models.ForeignKey(
        DevolucionVenta,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    detalle_venta = models.ForeignKey(
        DetalleVenta,
        on_delete=models.PROTECT,
        related_name="devolucion_detalles",
    )
    producto = models.ForeignKey(Productos, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=18, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=18, decimal_places=2)
    total = models.DecimalField(max_digits=18, decimal_places=2)

    def __str__(self):
        return f"Devolución {self.devolucion_venta_id} - {self.producto.nombre}"


class tarjetas(Abstracto):
    id_factura = models.OneToOneField(
        Ventas, on_delete=models.PROTECT, related_name="factura_tarjetas"
    )
    digitos = models.CharField(max_length=4)
    numero_autorizacion = models.CharField(max_length=50)

    def __str__(self):
        return f"Tarjeta ****{self.digitos} - Autorización: {self.numero_autorizacion}"



# =========================
# APERTURA CAJA
# =========================
class CajaAC(Abstracto):

    ESTADO_CHOICES = (
        ("abierta", "Abierta"),
        ("cuadre", "Cuadre"),
        ("cerrada", "Cerrada"),
    )

    class Meta:
        permissions = [
            ("operar_caja", "Puede operar la caja"),
            ("modificar_precio_caja", "Puede modificar precios en caja"),
            ("ver_dashboard", "Puede ver el dashboard"),
        ]

    usuario_id = models.IntegerField()

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default="abierta"
    )

    fecha_apertura = models.DateTimeField(auto_now_add=True)

    monto_apertura = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True
    )

    monto_cierre = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    ventas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Instantánea al cerrar: los retiros no disminuyen las ventas generadas.
    retiros_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    diferencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    deposito_esperado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    deposito_recibido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    tarjeta_esperado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    tarjeta_recibido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    cheque_esperado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    cheque_recibido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

class DetalleCuadreCaja(models.Model):

    caja = models.ForeignKey(
        CajaAC,
        on_delete=models.CASCADE,
        related_name="detalles_cuadre"
    )

    denominacion = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )

    cantidad = models.PositiveIntegerField(
        default=0
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )


class RetiroCaja(Abstracto):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        COMPLETADO = "COMPLETADO", "Completado"
        CANCELADO = "CANCELADO", "Cancelado"

    caja = models.ForeignKey(CajaAC, on_delete=models.PROTECT, related_name="retiros")
    cajero_id = models.IntegerField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    completado_por_id = models.IntegerField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    observaciones = models.CharField(max_length=250, blank=True, default="")

    class Meta:
        permissions = [
            ("gestionar_retiros_caja", "Puede solicitar retiros de efectivo de caja"),
        ]


class Notificacion(Abstracto):
    """Avisos dirigidos a un usuario o publicados para todos los usuarios."""

    class Tipo(models.TextChoices):
        RETIRO_CAJA = "RETIRO_CAJA", "Retiro de caja"
        STOCK_BAJO = "STOCK_BAJO", "Stock bajo"
        VENCIMIENTO = "VENCIMIENTO", "Próximo vencimiento"
        CUENTA_COBRAR = "CUENTA_COBRAR", "Cuenta por cobrar"
        CUENTA_PAGAR = "CUENTA_PAGAR", "Cuenta por pagar"
        SUSCRIPCION = "SUSCRIPCION", "Suscripción"
        SISTEMA = "SISTEMA", "Sistema"

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notificaciones",
    )
    para_todos = models.BooleanField(default=False)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.SISTEMA)
    titulo = models.CharField(max_length=120)
    mensaje = models.CharField(max_length=300, blank=True, default="")
    referencia = models.CharField(max_length=120, blank=True, default="")
    leida = models.BooleanField(default=False)
    retiro_caja = models.ForeignKey(
        RetiroCaja,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notificaciones",
    )

    class Meta:
        ordering = ["-f_creacion"]


class ReservaInventario(Abstracto):

    class Estado(models.TextChoices):
        RESERVADA = "RESERVADA", "Reservada"
        CONSUMIDA = "CONSUMIDA", "Consumida"
        CANCELADA = "CANCELADA", "Cancelada"

    producto = models.ForeignKey(
        Productos,
        on_delete=models.PROTECT,
        related_name="reservas_inventario",
    )

    ubicacion = models.ForeignKey(
        Ubicaciones,
        on_delete=models.PROTECT,
        related_name="reservas_inventario",
    )

    cantidad = models.DecimalField(
        max_digits=18,
        decimal_places=6,
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.RESERVADA,
    )

    traslado = models.ForeignKey(
        Traslados,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reservas_inventario",
    )

    venta = models.ForeignKey(
        Ventas,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reservas_inventario",
    )
    
