from django.contrib import admin
from .enums import EstadoCuenta
from .models import (
    Categorias,
    Clientes,
    Compras,
    CuentasPorPagar,
    DetalleCompra,
    Marcas,
    Productos,
    Proveedores,
    ProveedoresContactos,
    RegistroAbonos,
    Ubicaciones,
    UMedidas,
    Traslados,
    DetalleTraslado,
    Inventarios,
    MovimientoInventario,
    TipoMovimientoInventario,
    PerfilUsuario
)
from django.utils import timezone
from django.utils.timezone import now
from django.db import transaction
from decimal import Decimal
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

@admin.register(UMedidas)
class UMedidasAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "abreviatura", "is_active", "is_delete")
    search_fields = ("nombre", "abreviatura")
    list_filter = ("is_active", "is_delete")


@admin.register(Marcas)
class MarcasAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion", "is_active", "is_delete")
    search_fields = ("nombre", "descripcion")
    list_filter = ("is_active", "is_delete")


@admin.register(Categorias)
class CategoriasAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "descripcion", "is_active", "is_delete")
    search_fields = ("nombre", "descripcion")
    list_filter = ("is_active", "is_delete")


@admin.register(Proveedores)
class ProveedoresAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre_legal",
        "nombre_comercial",
        "rtn",
        "dias_credito",
        "telefono",
        "email",
        "is_active",
        "is_delete",
    )

    search_fields = ("nombre_legal", "nombre_comercial", "rtn", "email")

    list_filter = ("is_active", "is_delete", "dias_credito")


@admin.register(ProveedoresContactos)
class ProveedoresContactosAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "proveedor",
        "nombre",
        "puesto",
        "telefono",
        "email",
        "is_active",
        "is_delete",
        "f_creacion",
    )

    list_filter = (
        "is_active",
        "is_delete",
        "proveedor",
    )

    search_fields = (
        "nombre",
        "puesto",
        "telefono",
        "email",
        "proveedor__nombre_comercial",
        "proveedor__nombre_legal",
    )

    ordering = ("-id",)

    autocomplete_fields = ("proveedor",)


@admin.register(Productos)
class ProductosAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "categoria",
        "unidad_medida",
        "marca",
        "codigo_sku",
        "precio_venta",
        "is_active",
        "is_delete",
        "vencimiento",
    )

    list_filter = (
        "is_active",
        "is_delete",
        "categoria",
        "marca",
        "unidad_medida",
        "vencimiento",
    )

    search_fields = (
        "nombre",
        "codigo_sku",
        "descripcion",
        "categoria__nombre",
        "marca__nombre",
    )

    readonly_fields = (
        "f_creacion",
        "f_modificacion",
        "u_creo_id",
        "u_modifico_id",
    )

    fieldsets = (
        (
            "Información general",
            {
                "fields": (
                    "nombre",
                    "descripcion",
                    "codigo_sku",
                )
            },
        ),
        (
            "Clasificación",
            {
                "fields": (
                    "categoria",
                    "unidad_medida",
                    "marca",
                )
            },
        ),
        (
            "Precios y control",
            {
                "fields": (
                    "precio_venta",
                    "vencimiento",
                )
            },
        ),
        (
            "Imagen",
            {
                "fields": (
                    "imagen_nombre",
                    "imagen_url",
                )
            },
        ),
        (
            "Estado",
            {
                "fields": (
                    "is_active",
                    "is_delete",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "f_creacion",
                    "f_modificacion",
                    "u_creo_id",
                    "u_modifico_id",
                )
            },
        ),
    )


@admin.register(Ubicaciones)
class UbicacionesAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "get_tipo_display", "codigo")
    list_filter = ("tipo",)
    search_fields = ("nombre", "codigo")
    ordering = ("id",)

    def save_model(self, request, obj, form, change):
        # Validar duplicados activos
        if (
            Ubicaciones.objects.filter(nombre=obj.nombre, is_delete=False)
            .exclude(id=obj.id)
            .exists()
        ):
            raise ValueError("Ya existe una ubicación con ese nombre")

        # Auditoría (solo al crear)
        if not obj.pk:
            obj.u_creo_id = request.user.id

        super().save_model(request, obj, form, change)


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1
    fields = ("producto", "cantidad", "precio_compra")
    autocomplete_fields = ["producto"]


@admin.register(Compras)
class ComprasAdmin(admin.ModelAdmin):
    list_display = ("id", "proveedor", "tipo_compra", "total", "estado", "fecha_compra")
    list_filter = ("estado", "tipo_compra", "fecha_compra")
    search_fields = ("id", "proveedor__nombre_legal", "proveedor__nombre_comercial")
    autocomplete_fields = ["proveedor", "ubicacion"]
    inlines = [DetalleCompraInline]


@admin.register(CuentasPorPagar)
class CuentasPorPagarAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "proveedor",
        "compra",
        "monto_total",
        "monto_pendiente",
        "estado",
        "fecha_vencimiento",
    )
    list_filter = ("estado", "fecha_vencimiento")
    search_fields = ("proveedor__nombre_legal", "compra__id")
    autocomplete_fields = ["proveedor", "compra"]

    readonly_fields = ("monto_total", "monto_pendiente")


@admin.register(RegistroAbonos)
class RegistroAbonosAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cuenta_por_pagar",
        "monto_abonado",
        "monto_pendiente",
        "liquidado",
    )

    autocomplete_fields = ["cuenta_por_pagar"]

    def save_model(self, request, obj, form, change):
        cuenta = obj.cuenta_por_pagar

        if obj.monto_abonado <= 0:
            raise ValueError("El abono debe ser mayor a 0")

        if obj.monto_abonado > cuenta.monto_pendiente:
            raise ValueError("El abono no puede ser mayor al pendiente")

        nuevo_pendiente = cuenta.monto_pendiente - obj.monto_abonado

        obj.monto_pendiente = nuevo_pendiente
        obj.liquidado = nuevo_pendiente <= 0
        obj.u_creo_id = request.user.id

        # actualizar cuenta
        cuenta.monto_pendiente = nuevo_pendiente

        if nuevo_pendiente <= 0:
            cuenta.estado = EstadoCuenta.PAGADO
        elif nuevo_pendiente < cuenta.monto_total:
            cuenta.estado = EstadoCuenta.PARCIAL
        else:
            cuenta.estado = EstadoCuenta.PENDIENTE

        cuenta.u_modifico_id = request.user.id
        cuenta.f_modificacion = timezone.now()
        cuenta.save()

        super().save_model(request, obj, form, change)


@admin.register(Clientes)
class ClientesAdmin(admin.ModelAdmin):
    # =====================
    # LISTA
    # =====================
    list_display = (
        "id",
        "dni",
        "nombre_completo",
        "empresa",
        "telefono",
        "email",
        "is_active",
        "is_delete",
    )

    # =====================
    # BUSCADOR
    # =====================
    search_fields = (
        "dni",
        "nombre",
        "nombre2",
        "apellido",
        "apellido2",
        "empresa",
        "email",
        "telefono",
    )

    # =====================
    # FILTROS
    # =====================
    list_filter = (
        "is_active",
        "is_delete",
    )

    # =====================
    # CAMPOS SOLO LECTURA
    # =====================
    readonly_fields = (
        "u_creo_id",
        "f_creacion",
        "u_modifico_id",
        "f_modificacion",
    )

    # =====================
    # ORDEN
    # =====================
    ordering = ("-id",)

    # =====================
    # EDICIÓN RÁPIDA
    # =====================
    list_editable = ("is_active",)

    # =====================
    # OPTIMIZACIÓN
    # =====================
    list_per_page = 20

    # =====================
    # CAMPOS EN FORMULARIO
    # =====================
    fieldsets = (
        (
            "Información Personal",
            {
                "fields": (
                    "dni",
                    "nombre",
                    "nombre2",
                    "apellido",
                    "apellido2",
                )
            },
        ),
        (
            "Contacto",
            {
                "fields": (
                    "empresa",
                    "direccion",
                    "telefono",
                    "email",
                )
            },
        ),
        (
            "Estado",
            {
                "fields": (
                    "is_active",
                    "is_delete",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "u_creo_id",
                    "f_creacion",
                    "u_modifico_id",
                    "f_modificacion",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    # =====================
    # NOMBRE
    # =====================
    def nombre_completo(self, obj):
        return obj.nombre_completo

    nombre_completo.short_description = "Nombre completo"

# =========================
# INLINE DETALLE
# =========================
class DetalleTrasladoInline(admin.TabularInline):
    model = DetalleTraslado
    extra = 1

    fields = (
        "producto",
        "cantidad_solicitada",
        "cantidad_entregada",
    )

    autocomplete_fields = ("producto",)


# =========================
# TRASLADOS ADMIN
# =========================
@admin.register(Traslados)
class TrasladosAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ubicacion_origen",
        "ubicacion_destino",
        "estado",
        "solicitado_por",
        "autorizado_por",
    )

    fields = (
        "solicitado_por",
        "autorizado_por",
        "ubicacion_origen",
        "ubicacion_destino",
        "fecha_autorizacion",
        "estado",
        "observaciones",
    )

    readonly_fields = (
        "solicitado_por",
        "autorizado_por",
        "fecha_autorizacion",
    )

    inlines = [DetalleTrasladoInline]

    # =========================
    # CREAR / EDITAR TRASLADO
    # =========================
    def save_model(self, request, obj, form, change):

        if not obj.pk:
            obj.solicitado_por = request.user

        if obj.estado == "COMPLETADO" and not obj.fecha_autorizacion:
            obj.fecha_autorizacion = now()
            obj.autorizado_por = request.user

        super().save_model(request, obj, form, change)

    # =========================
    # APLICAR INVENTARIO AL GUARDAR DETALLES
    # =========================
    def save_formset(self, request, form, formset, change):

        instances = formset.save(commit=False)

        with transaction.atomic():
            for detalle in instances:
                if not detalle.pk:  # SOLO NUEVOS
                    producto = detalle.producto
                    origen = form.instance.ubicacion_origen
                    destino = form.instance.ubicacion_destino
                    cantidad = Decimal(detalle.cantidad_solicitada)

                    # =========================
                    # VALIDAR STOCK FIFO
                    # =========================
                    capas_origen = Inventarios.objects.filter(
                        producto=producto,
                        ubicacion_id=origen.id,
                        is_delete=False,
                        cantidad__gt=0,
                    ).order_by("f_creacion")

                    stock_total = sum(Decimal(x.cantidad) for x in capas_origen)

                    if stock_total < cantidad:
                        raise Exception(
                            f"Stock insuficiente para {producto.nombre}. Disponible {stock_total}"
                        )

                    restante = cantidad

                    # =========================
                    # DESCUENTO FIFO
                    # =========================
                    for capa in capas_origen:
                        if restante <= 0:
                            break

                        stock_capa = Decimal(capa.cantidad)
                        consumir = min(stock_capa, restante)

                        stock_anterior = stock_capa

                        capa.cantidad -= consumir
                        capa.save()

                        MovimientoInventario.objects.create(
                            tipo_movimiento=TipoMovimientoInventario.TRASLADO_SALIDA,
                            producto=producto,
                            ubicacion_origen=origen,
                            ubicacion_destino=destino,
                            cantidad=consumir,
                            stock_anterior=stock_anterior,
                            stock_resultante=capa.cantidad,
                            traslado=form.instance,
                        )

                        restante -= consumir

                detalle.save()

            formset.save_m2m()

class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False

class CustUserAdmin(UserAdmin):
    inlines= [PerfilUsuarioInline]

admin.site.unregister(User)
admin.site.register(User,CustUserAdmin)
