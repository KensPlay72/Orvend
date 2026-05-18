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
    UMedidas,
    Traslados,
    DetalleTraslado,
    Inventarios,
    MovimientoInventario,
    TipoMovimientoInventario,
    Descuento,
    Ubicaciones,
)
from django.utils import timezone
from django.utils.timezone import now
from django.db import transaction
from django import forms
from decimal import Decimal


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


@admin.register(Descuento)
class DescuentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "tipo_descuento",
        "valor",
        "codigo",
        "aplicacion",
        "is_active",
        "fecha_inicio",
        "fecha_fin",
    )

    list_filter = (
        "es_cupon",
        "es_porcentaje",
        "aplicar_productos",
        "aplicar_categorias",
        "is_active",
    )

    search_fields = (
        "nombre",
        "codigo",
        "descripcion",
    )

    ordering = ("-id",)

    readonly_fields = (
        "f_creacion",
        "f_modificacion",
    )  # si tu Abstracto los tiene

    fieldsets = (
        (
            "Información general",
            {
                "fields": (
                    "nombre",
                    "descripcion",
                    "is_active",
                )
            },
        ),
        (
            "Cupón",
            {
                "fields": (
                    "es_cupon",
                    "codigo",
                )
            },
        ),
        (
            "Tipo de descuento",
            {
                "fields": (
                    "es_porcentaje",
                    "valor",
                    "acumulable",
                    "requiere_codigo",
                )
            },
        ),
        (
            "Aplicación",
            {
                "fields": (
                    "aplicar_productos",
                    "aplicar_categorias",
                    "producto",
                    "categoria",
                )
            },
        ),
        (
            "Límites",
            {
                "fields": (
                    "limite_uso",
                    "fecha_inicio",
                    "fecha_fin",
                )
            },
        ),
    )

    def tipo_descuento(self, obj):
        if obj.es_cupon:
            return "Cupón"
        return "Automático"

    tipo_descuento.short_description = "Tipo"

    def aplicacion(self, obj):
        if obj.aplicar_productos:
            return "Producto"
        if obj.aplicar_categorias:
            return "Categoría"
        return "General"

    aplicacion.short_description = "Aplica a"


# =========================
# FORM PERSONALIZADO
# =========================
class UbicacionesAdminForm(forms.ModelForm):
    class Meta:
        model = Ubicaciones
        fields = "__all__"

    def clean(self):

        cleaned_data = super().clean()

        es_bodega = cleaned_data.get("es_bodega")
        es_tienda = cleaned_data.get("es_tienda")
        bodega = cleaned_data.get("bodega")

        # =========================
        # VALIDAR TIPO
        # =========================
        if not es_bodega and not es_tienda:
            raise forms.ValidationError("Debe seleccionar si es bodega o tienda.")

        # =========================
        # NO AMBOS
        # =========================
        if es_bodega and es_tienda:
            raise forms.ValidationError("No puede ser bodega y tienda al mismo tiempo.")

        # =========================
        # SI ES BODEGA NO PUEDE
        # TENER BODEGA PADRE
        # =========================
        if es_bodega and bodega:
            raise forms.ValidationError("Una bodega no puede pertenecer a otra bodega.")

        # =========================
        # SI ES TIENDA
        # VALIDAR QUE LA RELACION
        # SEA UNA BODEGA
        # =========================
        if es_tienda and bodega:
            if not bodega.es_bodega:
                raise forms.ValidationError(
                    "La ubicación relacionada debe ser una bodega."
                )

        return cleaned_data


# =========================
# ADMIN
# =========================
@admin.register(Ubicaciones)
class UbicacionesAdmin(admin.ModelAdmin):
    form = UbicacionesAdminForm

    list_display = (
        "id",
        "nombre",
        "codigo",
        "tipo_visual",
        "bodega",
        "is_active",
    )

    list_filter = (
        "es_bodega",
        "es_tienda",
        "is_active",
    )

    search_fields = (
        "nombre",
        "codigo",
    )

    autocomplete_fields = ("bodega",)

    readonly_fields = (
        "f_creacion",
        "f_modificacion",
    )

    fieldsets = (
        (
            "Información General",
            {
                "fields": (
                    "nombre",
                    "codigo",
                )
            },
        ),
        (
            "Tipo",
            {
                "fields": (
                    "es_bodega",
                    "es_tienda",
                )
            },
        ),
        (
            "Relación",
            {
                "fields": ("bodega",),
                "description": "Solo las tiendas pueden relacionarse con una bodega.",
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
                    "u_creo",
                    "u_modifico",
                    "f_creacion",
                    "f_modificacion",
                )
            },
        ),
    )

    # =========================
    # VISUALIZACION TIPO
    # =========================
    def tipo_visual(self, obj):

        if obj.es_bodega:
            return "Bodega"

        if obj.es_tienda:
            return "Tienda"

        return "Sin tipo"

    tipo_visual.short_description = "Tipo"

    # =========================
    # FILTRAR SOLO BODEGAS
    # =========================
    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "bodega":
            kwargs["queryset"] = Ubicaciones.objects.filter(
                es_bodega=True,
                is_delete=False,
            )

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs,
        )
