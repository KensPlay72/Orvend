import json
import textwrap
import traceback
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from io import BytesIO
from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.core import signing
from django.db import transaction
from django.db.models import Q, Sum, OuterRef, Subquery, F, Min, Max, Prefetch, Value, DecimalField, Count
from django.http import Http404, HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.templatetags.static import static
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from reportlab.lib.units import mm
from .nextcloud import subir_archivo, obtener_archivo,eliminar_archivo
from PIL import Image, UnidentifiedImageError
from .whatsapp import enviar_factura_por_whatsapp
from .notificaciones_alertas import actualizar_notificaciones_alertas
from .notificaciones_service import estado_notificaciones_usuario
from .notificaciones_realtime import publicar_actualizacion_usuarios
import os
import uuid
from django.db.models.functions import TruncDate, Coalesce
import random
from urllib.parse import urlencode, urljoin


from .enums import (
    EstadoCompra,
    EstadoCuenta,
    EstadoDevolucionCompra,
    Estados,
    MotivoDevolucion,
)
from .models import (
    Categorias,
    Clientes,
    Compras,
    CuentasPorPagar,
    CuentasPorCobrar,
    RegistroAbonosCobrar,
    DetalleCompra,
    DetalleTraslado,
    DevolucionCompra,
    DevolucionCompraDetalle,
    HAutorizarCompra,
    Inventarios,
    Marcas,
    MovimientoInventario,
    Productos,
    Proveedores,
    ProveedoresContactos,
    RegistroAbonos,
    TipoMovimientoInventario,
    Traslados,
    Ubicaciones,
    UMedidas,
    Descuento,
    ProductosImagenes,
    PerfilUsuario,
    datos_sat,
    facturas_cai,
    Ventas,
    DetalleVenta,
    Cotizacion,
    DetalleCotizacion,
    DevolucionVenta,
    DevolucionVentaDetalle,
    tarjetas,
    CajaAC,
    Combos,
    ComboImagen,
    BannerTienda,
    ConfiguracionEmpresa,
    SuscripcionSistema,
    DetalleCuadreCaja,
    RetiroCaja,
    Notificacion,
    DetalleCombo,
    ProductosRel,
    ReservaInventario,
)


ZONA_HONDURAS = ZoneInfo("America/Tegucigalpa")


def _fecha_honduras(valor):
    """Convierte fechas almacenadas en UTC a la hora local de Honduras."""
    if timezone.is_naive(valor):
        return timezone.make_aware(valor, ZONA_HONDURAS)
    return timezone.localtime(valor, ZONA_HONDURAS)


def _rango_fechas_honduras(fecha_inicio, fecha_fin):
    """Devuelve un rango [inicio, fin) para filtrar ventas por fecha hondureña."""
    inicio = date.fromisoformat(str(fecha_inicio))
    fin = date.fromisoformat(str(fecha_fin)) + timedelta(days=1)
    return (
        timezone.make_aware(datetime.combine(inicio, datetime.min.time()), ZONA_HONDURAS),
        timezone.make_aware(datetime.combine(fin, datetime.min.time()), ZONA_HONDURAS),
    )


def _logo_empresa_pdf():
    """Obtiene el logo configurado o conserva el logo predeterminado del ERP."""
    logo_predeterminado = os.path.join(settings.BASE_DIR, "static", "img", "LH.webp")
    try:
        configuracion = ConfiguracionEmpresa.objects.filter(
            is_active=True, is_delete=False
        ).first()
        if configuracion and configuracion.logo_archivo:
            contenido = obtener_archivo(
                configuracion.logo_archivo,
                settings.NEXTCLOUD_FOLDER_CONFI,
            ).content
            return ImageReader(BytesIO(contenido))
    except Exception:
        pass
    return logo_predeterminado


def _puede_gestionar_configuracion(usuario):
    return usuario.is_superuser or usuario.has_perm("manager.gestionar_configuracion")


def _puede_gestionar_tienda(usuario):
    return usuario.is_superuser or usuario.has_perm("manager.gestionar_tienda_virtual")


def _puede_operar_caja(usuario):
    return usuario.is_superuser or usuario.has_perm("manager.operar_caja")


def _puede_generar_cotizaciones(usuario):
    return _puede_operar_caja(usuario) or usuario.has_perm("manager.generar_cotizaciones")


def _requiere_superusuario(request):
    if not request.user.is_superuser:
        raise PermissionDenied


def _normalizar_encabezado_excel(valor):
    return (
        str(valor or "")
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace(" ", "_")
    )


def _leer_filas_excel(archivo):
    if not archivo or not archivo.name.lower().endswith(".xlsx"):
        raise ValueError("Selecciona un archivo Excel con extensión .xlsx.")

    libro = load_workbook(archivo, read_only=True, data_only=True)
    hoja = libro.active
    filas = hoja.iter_rows(values_only=True)
    encabezados = [_normalizar_encabezado_excel(valor) for valor in next(filas, [])]
    if not encabezados or not any(encabezados):
        raise ValueError("El archivo no contiene encabezados.")

    datos = []
    for numero_fila, valores in enumerate(filas, start=2):
        if not any(valor not in (None, "") for valor in valores):
            continue
        datos.append(
            (
                numero_fila,
                {
                    encabezados[indice]: valores[indice]
                    for indice in range(min(len(encabezados), len(valores)))
                    if encabezados[indice]
                },
            )
        )
    return encabezados, datos


def _respuesta_excel(libro, nombre_archivo):
    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)
    response = HttpResponse(
        salida.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    return response


def _libro_exportacion_grande(titulo, encabezados, anchos=None):
    """Libro en modo streaming para exportaciones que pueden tener miles de filas."""
    libro = Workbook(write_only=True)
    hoja = libro.create_sheet(title=titulo)
    relleno = PatternFill("solid", fgColor="32877F")
    fila_encabezado = []
    for encabezado in encabezados:
        celda = WriteOnlyCell(hoja, value=encabezado)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = relleno
        celda.alignment = Alignment(horizontal="center")
        fila_encabezado.append(celda)
    hoja.append(fila_encabezado)
    hoja.freeze_panes = "A2"
    if anchos:
        for indice, ancho in enumerate(anchos, start=1):
            hoja.column_dimensions[get_column_letter(indice)].width = ancho
    return libro, hoja


def _agregar_fila_exportacion(hoja, valores, formatos=None):
    """Agrega una fila sin retener celdas anteriores en memoria."""
    formatos = formatos or {}
    fila = []
    for indice, valor in enumerate(valores, start=1):
        formato = formatos.get(indice)
        if formato:
            celda = WriteOnlyCell(hoja, value=valor)
            celda.number_format = formato
            fila.append(celda)
        else:
            fila.append(valor)
    hoja.append(fila)


def _libro_plantilla(titulo, encabezados):
    libro = Workbook()
    hoja = libro.active
    hoja.title = titulo
    hoja.append(encabezados)
    relleno = PatternFill("solid", fgColor="32877F")
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = relleno
        celda.alignment = Alignment(horizontal="center")
        hoja.column_dimensions[celda.column_letter].width = max(len(celda.value) + 4, 18)
    hoja.freeze_panes = "A2"
    return libro


def _puede_ver_cotizaciones(usuario):
    return usuario.is_superuser or usuario.has_perm("manager.view_cotizacion")


def _validar_color_tienda(valor, etiqueta):
    valor = (valor or "").strip().upper()
    if len(valor) != 7 or not valor.startswith("#"):
        raise ValueError(f"{etiqueta} debe tener formato hexadecimal, por ejemplo #32877F")
    try:
        int(valor[1:], 16)
    except ValueError as error:
        raise ValueError(f"{etiqueta} debe tener formato hexadecimal válido") from error
    return valor


def _validar_banner_tienda(archivo):
    formatos = {"image/jpeg", "image/png", "image/webp"}
    if archivo.content_type not in formatos:
        raise ValueError("Cada banner debe ser JPG, PNG o WEBP")
    if archivo.size > 5 * 1024 * 1024:
        raise ValueError("Cada banner puede pesar como máximo 5 MB")
    try:
        imagen = Image.open(archivo)
        ancho, alto = imagen.size
        imagen.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Uno de los banners no es una imagen válida") from error
    finally:
        archivo.seek(0)
    if (ancho, alto) != (1920, 640):
        raise ValueError("Cada banner debe medir exactamente 1920 × 640 píxeles")


@login_required
def dashboard_view(request):
    if not request.user.is_superuser and not request.user.has_perm("manager.ver_dashboard"):
        raise PermissionDenied("No tiene permiso para ver el dashboard")

    # ==========================================================
    # FECHAS
    # ==========================================================

    hoy = timezone.localtime()

    inicio_hoy = hoy.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    fin_hoy = inicio_hoy + timedelta(days=1)

    inicio_mes = hoy.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    inicio_grafico = inicio_hoy - timedelta(days=29)

    # ==========================================================
    # TOTAL DE PRODUCTOS
    # ==========================================================

    total_productos = (
        Productos.objects
        .filter(
            is_active=True,
            is_delete=False
        )
        .count()
    )

    # ==========================================================
    # VENTAS DE HOY
    # ==========================================================

    ventas_hoy = (
        Ventas.objects
        .filter(
            f_creacion__gte=inicio_hoy,
            f_creacion__lt=fin_hoy,
            is_active=True,
            is_delete=False
        )
        .aggregate(
            total=Sum("total")
        )["total"] or 0
    )

    # ==========================================================
    # VENTAS DEL MES
    # ==========================================================

    ventas_mes = (
        Ventas.objects
        .filter(
            f_creacion__gte=inicio_mes,
            f_creacion__lt=fin_hoy,
            is_active=True,
            is_delete=False
        )
        .aggregate(
            total=Sum("total")
        )["total"] or 0
    )

    # ==========================================================
    # UTILIDAD DEL MES
    # ==========================================================

    utilidad_mes = (
        Ventas.objects
        .filter(
            f_creacion__gte=inicio_mes,
            f_creacion__lt=fin_hoy,
            is_active=True,
            is_delete=False
        )
        .aggregate(
            total=Sum("utilidad_total")
        )["total"] or 0
    )

    # ==========================================================
    # COMPRAS DEL MES
    # ==========================================================

    compras_mes = (
        Compras.objects
        .filter(
            fecha_compra__gte=inicio_mes,
            fecha_compra__lt=fin_hoy,
            is_active=True,
            is_delete=False
        )
        .aggregate(
            total=Sum("total")
        )["total"] or 0
    )

    # ==========================================================
    # VENTAS ÚLTIMOS 30 DÍAS
    # ==========================================================

    ventas_30_dias_query = (
        Ventas.objects
        .filter(
            f_creacion__gte=inicio_grafico,
            f_creacion__lt=fin_hoy,
            is_active=True,
            is_delete=False
        )
        .annotate(
            fecha=TruncDate("f_creacion")
        )
        .values("fecha")
        .annotate(
            total=Sum("total")
        )
        .order_by("fecha")
    )

    ventas_por_dia = {
        item["fecha"]: item["total"]
        for item in ventas_30_dias_query
    }

    fechas_grafico = []
    valores_grafico = []

    for i in range(30):

        fecha = (
            inicio_grafico.date()
            + timedelta(days=i)
        )

        fechas_grafico.append(
            fecha.strftime("%d/%m")
        )

        valores_grafico.append(
            float(ventas_por_dia.get(fecha, 0))
        )

    # ==========================================================
    # STOCK BAJO
    # ==========================================================

    stock_por_producto = (
        Inventarios.objects
        .filter(
            is_active=True,
            is_delete=False,
            producto__is_active=True,
            producto__is_delete=False,
        )
        .values(
            "producto",
            "producto__nombre",
            "ubicacion",
            "ubicacion__nombre",
        )
        .annotate(
            stock_total=Sum("cantidad"),
            stock_minimo=Min("stock_minimo"),
        )
        .filter(
            stock_total__lte=F("stock_minimo")
        )
        .order_by(
            "stock_total"
        )
    )

    productos_bajo_stock = stock_por_producto.count()

    alertas_stock = stock_por_producto[:10]

    # ==========================================================
    # PRODUCTOS PRÓXIMOS A VENCER
    # ==========================================================

    fecha_limite = hoy + timedelta(days=30)

    vencimientos_query = (
        Inventarios.objects
        .filter(
            is_active=True,
            is_delete=False,
            producto__is_active=True,
            producto__is_delete=False,
            cantidad__gt=0,
            fvencimiento__isnull=False,
            fvencimiento__gte=hoy,
            fvencimiento__lte=fecha_limite,
        )
        .select_related(
            "producto",
            "ubicacion",
            "compra",
        )
        .order_by(
            "fvencimiento"
        )
    )
    alertas_vencimiento = vencimientos_query[:10]

    # ==========================================================
    # CUENTAS POR PAGAR
    # ==========================================================

    cuentas_pendientes = (
        CuentasPorPagar.objects
        .filter(
            is_active=True,
            is_delete=False,
            monto_pendiente__gt=0
        )
        .count()
    )

    # ==========================================================
    # TRASLADOS
    # ==========================================================

    total_traslados = (
        Traslados.objects
        .filter(
            is_active=True,
            is_delete=False
        )
        .count()
    )

    # ==========================================================
    # CAJAS ABIERTAS
    # ==========================================================

    cajas_abiertas = (
        CajaAC.objects
        .filter(
            is_active=True,
            is_delete=False,
            estado="abierta"
        )
        .count()
    )

    # ==========================================================
    # CONTEXT
    # ==========================================================

    context = {

        "total_productos": total_productos,

        "ventas_hoy": ventas_hoy,
        "ventas_mes": ventas_mes,
        "utilidad_mes": utilidad_mes,
        "compras_mes": compras_mes,

        "productos_bajo_stock": productos_bajo_stock,

        "cuentas_pendientes": cuentas_pendientes,
        "total_traslados": total_traslados,
        "cajas_abiertas": cajas_abiertas,

        "alertas_stock": alertas_stock,
        "alertas_vencimiento": alertas_vencimiento,

        "fechas_grafico": fechas_grafico,
        "valores_grafico": valores_grafico,
    }

    # ==========================================================
    # RENDER
    # ==========================================================

    return render(
        request,
        "dashboard.html",
        context
    )

# ───────────────────────────────────────────────────────────────
# UNIDADES DE MEDIDA
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_umedidas", raise_exception=True)
def umedidas_view(request):

    search = request.GET.get("search", "").strip()

    query = UMedidas.objects.all()

    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    if search:
        query = query.filter(
            Q(nombre__icontains=search) | Q(abreviatura__icontains=search)
        )

    paginator = Paginator(query.order_by("id"), 10)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
        "fecha_hoy": timezone.localdate(timezone=ZONA_HONDURAS).strftime("%Y-%m-%d"),
    }

    return render(request, "gestiones/presentaciones.html", context)


@login_required
@permission_required("manager.add_umedidas", raise_exception=True)
@require_POST
def post_umedida(request):

    try:
        data = json.loads(request.body)

        nombre = (data.get("nombre") or "").strip()
        abreviatura = (data.get("abreviatura") or "").strip()
        valor = (data.get("valor") or "").strip()

        if not nombre or not abreviatura or not valor:
            return JsonResponse(
                {"success": False, "message": "Todos los campos son obligatorios"},
                status=400,
            )

        if UMedidas.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": "Ya existe una unidad de medida con ese nombre",
                },
                status=400,
            )

        UMedidas.objects.create(
            nombre=nombre,
            abreviatura=abreviatura,
            valor=valor,
            u_creo_id=request.user.id,
        )

        return JsonResponse({"success": True, "message": "Creado correctamente"})

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)}, status=500
        )


@login_required
@permission_required("manager.view_umedidas", raise_exception=True)
def get_umedida(request, id):

    try:
        medida = UMedidas.objects.filter(id=id).first()

        if not medida or medida.is_delete:
            return JsonResponse(
                {"success": False, "message": "Unidad de medida no encontrada"},
                status=404,
            )

        return JsonResponse(
            {
                "success": True,
                "presentacion": {
                    "id": medida.id,
                    "nombre": medida.nombre,
                    "abreviatura": medida.abreviatura,
                    "valor": medida.valor,
                    "isActive": medida.is_active,
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)}, status=500
        )


@login_required
@permission_required("manager.change_umedidas", raise_exception=True)
@require_http_methods(["PUT"])
def put_umedida(request, id):

    try:
        data = json.loads(request.body)
        nombre = (data.get("Nombre") or "").strip()
        abreviatura = (data.get("Abreviatura") or "").strip()
        valor = (data.get("Valor") or "").strip()
        is_active = data.get("IsActive", True)

        if not nombre or not abreviatura or not valor:
            return JsonResponse(
                {"success": False, "message": "Todos los campos son obligatorios"},
                status=400,
            )

        medida = UMedidas.objects.filter(id=id).first()

        if not medida or medida.is_delete:
            return JsonResponse(
                {"success": False, "message": "Unidad de medida no encontrada"},
                status=404,
            )

        if (
            UMedidas.objects.filter(nombre=nombre, is_delete=False)
            .exclude(id=id)
            .exists()
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Ya existe una unidad de medida con ese nombre",
                },
                status=400,
            )

        medida.nombre = nombre
        medida.abreviatura = abreviatura
        medida.valor = valor
        medida.is_active = is_active
        medida.u_modifico_id = request.user.id
        medida.f_modificacion = timezone.now()
        medida.save()

        return JsonResponse(
            {"success": True, "message": "Presentación actualizada correctamente"}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)}, status=500
        )


@login_required
@permission_required("manager.delete_umedidas", raise_exception=True)
@require_http_methods(["DELETE"])
def delete_umedida(request, id):

    try:
        medida = UMedidas.objects.filter(id=id).first()

        if not medida or medida.is_delete:
            return JsonResponse(
                {"success": False, "message": "Unidad de medida no encontrada"},
                status=404,
            )

        medida.is_delete = True
        medida.u_modifico_id = request.user.id
        medida.f_modificacion = timezone.now()
        medida.save()

        return JsonResponse(
            {"success": True, "message": "Unidad de medida eliminada correctamente"}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)}, status=500
        )


@login_required
# @permission_required('manager.view_umedidas', raise_exception=True)
def search_umedidas(request):

    search = request.GET.get("search", "").strip()

    items = UMedidas.objects.filter(is_delete=False, is_active=True)
    if search:
        items = items.filter(
            Q(nombre__icontains=search) | Q(abreviatura__icontains=search)
        ).order_by("nombre")[:20]
    else:
        # Muestra primero las presentaciones realmente utilizadas y completa
        # las cinco sugerencias con las demás disponibles cuando sea necesario.
        items = items.annotate(
            veces_usada=Count(
                "umedida_productos",
                filter=Q(
                    umedida_productos__is_active=True,
                    umedida_productos__is_delete=False,
                ),
            )
        ).order_by("-veces_usada", "nombre")[:5]

    data = [
        {"id": u.id, "nombre": u.nombre, "abreviatura": u.abreviatura} for u in items
    ]

    return JsonResponse(data, safe=False)


# ───────────────────────────────────────────────────────────────
# MARCAS
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_marcas", raise_exception=True)
def marcas_view(request):

    search = request.GET.get("search", "").strip()

    query = Marcas.objects.all()

    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    if search:
        query = query.filter(
            Q(nombre__icontains=search) | Q(descripcion__icontains=search)
        )

    paginator = Paginator(query.order_by("id"), 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "gestiones/marcas.html", context)


@login_required
@permission_required("manager.add_marcas", raise_exception=True)
@require_POST
def post_marca(request):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        descripcion = (data.get("Descripcion") or "").strip()

        if not nombre:
            return JsonResponse(
                {"success": False, "message": "El nombre es obligatorio"}, status=400
            )

        if Marcas.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe una marca con ese nombre"},
                status=400,
            )

        marca = Marcas.objects.create(
            nombre=nombre, descripcion=descripcion, u_creo_id=request.user.id
        )

        return JsonResponse(
            {"success": True, "message": "Marca registrada correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_marcas", raise_exception=True)
def get_marca(request, id):

    marca = Marcas.objects.filter(id=id, is_delete=False).first()

    if not marca:
        return JsonResponse(
            {"success": False, "message": "Marca no encontrada"}, status=404
        )

    return JsonResponse(
        {
            "success": True,
            "marca": {
                "id": marca.id,
                "nombre": marca.nombre,
                "descripcion": marca.descripcion,
                "isActive": marca.is_active,
            },
        }
    )


@login_required
@permission_required("manager.change_marcas", raise_exception=True)
@require_http_methods(["PUT"])
def put_marca(request, id):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        descripcion = (data.get("Descripcion") or "").strip()
        is_active = data.get("IsActive", True)

        if not nombre:
            return JsonResponse(
                {"success": False, "message": "El nombre es obligatorio"}, status=400
            )

        marca = Marcas.objects.filter(id=id).first()

        if not marca or marca.is_delete:
            return JsonResponse(
                {"success": False, "message": "Marca no encontrada"}, status=404
            )

        if (
            Marcas.objects.filter(nombre=nombre, is_delete=False)
            .exclude(id=id)
            .exists()
        ):
            return JsonResponse(
                {"success": False, "message": "Ya existe una marca con ese nombre"},
                status=400,
            )

        marca.nombre = nombre
        marca.descripcion = descripcion
        marca.is_active = is_active
        marca.u_modifico_id = request.user.id
        marca.f_modificacion = timezone.now()
        marca.save()

        return JsonResponse(
            {"success": True, "message": "Marca actualizada correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.delete_marcas", raise_exception=True)
@require_http_methods(["DELETE"])
def delete_marca(request, id):

    marca = Marcas.objects.filter(id=id).first()

    if not marca or marca.is_delete:
        return JsonResponse(
            {"success": False, "message": "Marca no encontrada"}, status=404
        )

    marca.is_delete = True
    marca.u_modifico_id = request.user.id
    marca.f_modificacion = timezone.now()
    marca.save()

    return JsonResponse({"success": True, "message": "Marca eliminada correctamente"})


@login_required
# @permission_required('manager.view_marcas', raise_exception=True)
def search_marcas(request):

    search = request.GET.get("search", "").strip()

    items = Marcas.objects.filter(is_delete=False, is_active=True)
    if search:
        items = items.filter(
            Q(nombre__icontains=search) | Q(descripcion__icontains=search)
        ).order_by("nombre")[:20]
    else:
        items = items.annotate(
            veces_usada=Count(
                "marca_productos",
                filter=Q(
                    marca_productos__is_active=True,
                    marca_productos__is_delete=False,
                ),
            )
        ).order_by("-veces_usada", "nombre")[:5]

    data = [
        {"id": m.id, "nombre": m.nombre, "descripcion": m.descripcion} for m in items
    ]

    return JsonResponse(data, safe=False)


# ───────────────────────────────────────────────────────────────
# CATEGORIAS
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_categorias", raise_exception=True)
def categorias_view(request):

    search = request.GET.get("search", "").strip()

    query = Categorias.objects.all()

    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    if search:
        query = query.filter(
            Q(nombre__icontains=search) | Q(descripcion__icontains=search)
        )

    paginator = Paginator(query.order_by("id"), 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "gestiones/categorias.html", context)


@login_required
@permission_required("manager.add_categorias", raise_exception=True)
@require_POST
def post_categoria(request):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        descripcion = (data.get("Descripcion") or "").strip()

        if not nombre:
            return JsonResponse(
                {"success": False, "message": "El nombre es obligatorio"}, status=400
            )

        if Categorias.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe una categoría con ese nombre"},
                status=400,
            )

        Categorias.objects.create(
            nombre=nombre, descripcion=descripcion, u_creo_id=request.user.id
        )

        return JsonResponse(
            {"success": True, "message": "Categoría registrada correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_categorias", raise_exception=True)
def get_categoria(request, id):

    categoria = Categorias.objects.filter(id=id, is_delete=False).first()

    if not categoria:
        return JsonResponse(
            {"success": False, "message": "Categoría no encontrada"}, status=404
        )

    return JsonResponse(
        {
            "success": True,
            "categoria": {
                "id": categoria.id,
                "nombre": categoria.nombre,
                "descripcion": categoria.descripcion,
                "isActive": categoria.is_active,
            },
        }
    )


@login_required
@permission_required("manager.change_categorias", raise_exception=True)
@require_http_methods(["PUT"])
def put_categoria(request, id):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        descripcion = (data.get("Descripcion") or "").strip()
        is_active = data.get("IsActive", True)

        if not nombre:
            return JsonResponse(
                {"success": False, "message": "El nombre es obligatorio"}, status=400
            )

        categoria = Categorias.objects.filter(id=id).first()

        if not categoria or categoria.is_delete:
            return JsonResponse(
                {"success": False, "message": "Categoría no encontrada"}, status=404
            )

        if (
            Categorias.objects.filter(nombre=nombre, is_delete=False)
            .exclude(id=id)
            .exists()
        ):
            return JsonResponse(
                {"success": False, "message": "Ya existe una categoría con ese nombre"},
                status=400,
            )

        categoria.nombre = nombre
        categoria.descripcion = descripcion
        categoria.is_active = is_active
        categoria.u_modifico_id = request.user.id
        categoria.f_creacion = timezone.now()
        categoria.save()

        return JsonResponse(
            {"success": True, "message": "Categoría actualizada correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.delete_categorias", raise_exception=True)
@require_http_methods(["DELETE"])
def delete_categoria(request, id):

    categoria = Categorias.objects.filter(id=id).first()

    if not categoria or categoria.is_delete:
        return JsonResponse(
            {"success": False, "message": "Categoría no encontrada"}, status=404
        )

    categoria.is_delete = True
    categoria.u_modifico_id = request.user.id
    categoria.f_modificacion = timezone.now()
    categoria.save()

    return JsonResponse(
        {"success": True, "message": "Categoría eliminada correctamente"}
    )


@login_required
# @permission_required('manager.view_categorias', raise_exception=True)
def search_categorias(request):

    search = request.GET.get("search", "").strip()

    items = Categorias.objects.filter(is_delete=False, is_active=True)
    if search:
        items = items.filter(
            Q(nombre__icontains=search) | Q(descripcion__icontains=search)
        ).order_by("nombre")[:20]
    else:
        items = items.annotate(
            veces_usada=Count(
                "categoria_productos",
                filter=Q(
                    categoria_productos__is_active=True,
                    categoria_productos__is_delete=False,
                ),
            )
        ).order_by("-veces_usada", "nombre")[:5]

    data = [
        {"id": c.id, "nombre": c.nombre, "descripcion": c.descripcion} for c in items
    ]

    return JsonResponse(data, safe=False)


# ───────────────────────────────────────────────────────────────
# PROVEEDORES
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_proveedores", raise_exception=True)
def proveedores_view(request):

    search = request.GET.get("search", "").strip()

    query = Proveedores.objects.all()

    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    if search:
        query = query.filter(
            Q(nombre_legal__icontains=search)
            | Q(nombre_comercial__icontains=search)
            | Q(rtn__icontains=search)
            | Q(telefono__icontains=search)
            | Q(email__icontains=search)
        )

    paginator = Paginator(query.order_by("id"), 10)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "gestiones/proveedores.html", context)


@login_required
@permission_required("manager.add_proveedores", raise_exception=True)
@require_http_methods(["POST"])
def post_proveedor(request):
    try:
        data = json.loads(request.body)

        nombre_legal = (data.get("nombre_legal") or "").strip()
        nombre_comercial = (data.get("nombre_comercial") or "").strip()
        rtn = (data.get("rtn") or "").strip()
        dias_credito = data.get("dias_credito")
        telefono = (data.get("telefono") or "").strip()
        email = (data.get("email") or "").strip()

        if not all([nombre_legal, nombre_comercial, rtn, dias_credito]):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Nombre legal, nombre comercial, RTN y días de crédito son obligatorios",
                },
                status=400,
            )

        if Proveedores.objects.filter(rtn=rtn, is_delete=False).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un proveedor con ese RTN"},
                status=400,
            )

        Proveedores.objects.create(
            nombre_legal=nombre_legal,
            nombre_comercial=nombre_comercial,
            rtn=rtn,
            dias_credito=dias_credito,
            telefono=telefono,
            email=email,
            u_creo_id=request.user.id,
        )

        return JsonResponse(
            {"success": True, "message": "Proveedor creado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_proveedores", raise_exception=True)
def get_proveedor(request, id):
    try:
        proveedor = Proveedores.objects.filter(id=id).first()

        if not proveedor or proveedor.is_delete:
            return JsonResponse(
                {"success": False, "message": "Proveedor no encontrado"}, status=404
            )

        return JsonResponse(
            {
                "success": True,
                "proveedor": {
                    "id": proveedor.id,
                    "nombre_legal": proveedor.nombre_legal,
                    "nombre_comercial": proveedor.nombre_comercial,
                    "rtn": proveedor.rtn,
                    "dias_credito": proveedor.dias_credito,
                    "telefono": proveedor.telefono,
                    "email": proveedor.email,
                    "saldo": float(proveedor.saldo or 0),
                    "is_active": proveedor.is_active,
                },
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.change_proveedores", raise_exception=True)
@require_http_methods(["PUT"])
def put_proveedor(request, id):

    try:
        data = json.loads(request.body)

        nombre_legal = (data.get("nombre_legal") or "").strip()
        nombre_comercial = (data.get("nombre_comercial") or "").strip()
        rtn = (data.get("rtn") or "").strip()
        dias_credito = data.get("dias_credito")
        telefono = (data.get("telefono") or "").strip()
        email = (data.get("email") or "").strip()

        # adaptado a tu JS
        is_active = data.get("IsActive", True)

        if not all([nombre_legal, nombre_comercial, rtn, dias_credito]):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Nombre legal, nombre comercial, RTN y días de crédito son obligatorios",
                },
                status=400,
            )

        proveedor = Proveedores.objects.filter(id=id).first()

        if not proveedor or proveedor.is_delete:
            return JsonResponse(
                {"success": False, "message": "Proveedor no encontrado"}, status=404
            )

        if Proveedores.objects.filter(rtn=rtn, is_delete=False).exclude(id=id).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un proveedor con ese RTN"},
                status=400,
            )

        proveedor.nombre_legal = nombre_legal
        proveedor.nombre_comercial = nombre_comercial
        proveedor.rtn = rtn
        proveedor.dias_credito = dias_credito
        proveedor.telefono = telefono
        proveedor.email = email
        proveedor.is_active = is_active
        proveedor.u_modifico_id = request.user.id
        proveedor.f_modificacion = timezone.now()

        proveedor.save()

        return JsonResponse(
            {"success": True, "message": "Proveedor actualizado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.delete_proveedores", raise_exception=True)
@require_http_methods(["DELETE"])
def delete_proveedor(request, id):

    try:
        proveedor = Proveedores.objects.filter(id=id).first()

        if not proveedor or proveedor.is_delete:
            return JsonResponse(
                {"success": False, "message": "Proveedor no encontrado"}, status=404
            )

        proveedor.is_delete = True
        proveedor.u_modifico_id = request.user.id
        proveedor.f_modificacion = timezone.now()
        proveedor.save()

        return JsonResponse(
            {"success": True, "message": "Proveedor eliminado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
def search_proveedores(request):
    search = request.GET.get("search", "").strip()

    proveedores = Proveedores.objects.filter(is_delete=False, is_active=True)

    if search:
        proveedores = proveedores.filter(
            Q(nombre_legal__icontains=search) | Q(nombre_comercial__icontains=search)
        ).order_by("nombre_legal")
    else:
        proveedores = proveedores.annotate(
            veces_usado=Count("proveedor_compras")
        ).order_by("-veces_usado", "nombre_legal")

    proveedores = proveedores[:5] if not search else proveedores[:20]

    results = [
        {
            "id": p.id,
            "nombreLegal": p.nombre_legal,
            "nombreComercial": p.nombre_comercial,
            "saldo": float(p.saldo or 0),
        }
        for p in proveedores
    ]

    return JsonResponse(results, safe=False)


# ───────────────────────────────────────────────────────────────
# PROVEEDORES CONTACTOS
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_proveedorescontactos", raise_exception=True)
def proveedores_contactos_view(request):

    search = request.GET.get("search", "").strip()

    query = ProveedoresContactos.objects.select_related("proveedor").all()

    # soft delete
    query = query.filter(is_delete=False)

    # search
    if search:
        query = query.filter(
            Q(nombre__icontains=search)
            | Q(puesto__icontains=search)
            | Q(email__icontains=search)
            | Q(telefono__icontains=search)
            | Q(proveedor__nombre_legal__icontains=search)
            | Q(proveedor__nombre_comercial__icontains=search)
        )

    paginator = Paginator(query.order_by("-id"), 10)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "proveedorescontactos": page_obj.object_list,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "gestiones/proveedorescontactos.html", context)


@login_required
@permission_required("manager.add_proveedorescontactos", raise_exception=True)
@require_http_methods(["POST"])
def post_proveedor_contacto(request):

    try:
        data = json.loads(request.body)

        proveedor_id = data.get("proveedor")
        nombre = (data.get("nombre") or "").strip()
        puesto = (data.get("puesto") or "").strip()
        telefono = (data.get("telefono") or "").strip()
        email = (data.get("email") or "").strip()
        observaciones = (data.get("observaciones") or "").strip()

        if not proveedor_id or not nombre or not puesto or not telefono or not email:
            return JsonResponse(
                {"success": False, "message": "Campos obligatorios incompletos"},
                status=400,
            )

        proveedor = Proveedores.objects.filter(id=proveedor_id, is_delete=False).first()
        if not proveedor:
            return JsonResponse(
                {"success": False, "message": "Proveedor no encontrado"}, status=404
            )

        contacto = ProveedoresContactos.objects.create(
            proveedor=proveedor,
            nombre=nombre,
            puesto=puesto,
            telefono=telefono,
            email=email,
            observaciones=observaciones,
            u_creo_id=request.user.id,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Contacto creado correctamente",
                "id": contacto.id,
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_proveedorescontactos", raise_exception=True)
def get_proveedor_contacto(request, id):

    contacto = (
        ProveedoresContactos.objects.select_related("proveedor")
        .filter(id=id, is_delete=False)
        .first()
    )

    if not contacto:
        return JsonResponse(
            {"success": False, "message": "Contacto no encontrado"}, status=404
        )

    return JsonResponse(
        {
            "success": True,
            "proveedorcont": {
                "id": contacto.id,
                "proveedores": {
                    "id": contacto.proveedor.id if contacto.proveedor else None,
                    "nombre_comercial": (
                        contacto.proveedor.nombre_comercial
                        if contacto.proveedor
                        else ""
                    ),
                    "nombre_legal": (
                        contacto.proveedor.nombre_legal if contacto.proveedor else ""
                    ),
                },
                "nombre": contacto.nombre,
                "puesto": contacto.puesto,
                "telefono": contacto.telefono,
                "email": contacto.email,
                "observaciones": contacto.observaciones,
                "is_active": contacto.is_active,
            },
        }
    )


@login_required
@permission_required("manager.change_proveedorescontactos", raise_exception=True)
@require_http_methods(["PUT"])
def put_proveedor_contacto(request, id):

    try:
        data = json.loads(request.body)

        contacto = ProveedoresContactos.objects.filter(id=id, is_delete=False).first()

        if not contacto:
            return JsonResponse(
                {"success": False, "message": "Contacto no encontrado"}, status=404
            )

        proveedor_id = data.get("proveedor")

        if proveedor_id:
            proveedor = Proveedores.objects.filter(
                id=proveedor_id, is_delete=False
            ).first()
            if not proveedor:
                return JsonResponse(
                    {"success": False, "message": "Proveedor no válido"}, status=400
                )
            contacto.proveedor = proveedor

        contacto.nombre = data.get("nombre", contacto.nombre)
        contacto.puesto = data.get("puesto", contacto.puesto)
        contacto.telefono = data.get("telefono", contacto.telefono)
        contacto.email = data.get("email", contacto.email)
        contacto.observaciones = data.get("observaciones", contacto.observaciones)

        contacto.is_active = data.get("is_active", contacto.is_active)
        contacto.u_modifico_id = request.user.id
        contacto.f_modificacion = timezone.now()

        contacto.save()

        return JsonResponse(
            {"success": True, "message": "Contacto actualizado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.delete_proveedorescontactos", raise_exception=True)
@require_http_methods(["DELETE"])
def delete_proveedor_contacto(request, id):

    contacto = ProveedoresContactos.objects.filter(id=id, is_delete=False).first()

    if not contacto:
        return JsonResponse(
            {"success": False, "message": "Contacto no encontrado"}, status=404
        )

    contacto.is_delete = True
    contacto.u_modifico_id = request.user.id
    contacto.f_modificacion = timezone.now()
    contacto.save()

    return JsonResponse(
        {"success": True, "message": "Contacto eliminado correctamente"}
    )


# ───────────────────────────────────────────────────────────────
# PRODUCTOS
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_productos", raise_exception=True)
def productos_view(request):

    search = request.GET.get("search", "").strip()

    query = Productos.objects.select_related(
        "categoria",
        "unidad_medida",
        "marca",
    ).prefetch_related(
        "imagenes_producto"
    )

    query = query.filter(is_delete=False)

    total_productos = query.count()
    productos_activos = query.filter(is_active=True).count()
    productos_inactivos = query.filter(is_active=False).count()

    if search:
        query = query.filter(
            Q(nombre__icontains=search)
            | Q(codigo_sku__icontains=search)
        )

    paginator = Paginator(
        query.order_by("nombre", "id"),
        10,
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "gestiones/productos.html",
        {
            "page_obj": page_obj,
            "search": search,
            "total_productos": total_productos,
            "productos_activos": productos_activos,
            "productos_inactivos": productos_inactivos,
            "mostrar_buscador": True,
        },
    )


@login_required
@permission_required("manager.view_combos", raise_exception=True)
def combos_view(request):
    costo_reciente = Subquery(
        DetalleCompra.objects.filter(producto_id=OuterRef("pk"))
        .order_by("-compra__fecha_compra", "-id")
        .values("precio_compra")[:1]
    )
    productos = (
        Productos.objects.filter(is_active=True, is_delete=False)
        .annotate(
            existencia=Sum("producto_inventarios__cantidad"),
            costo_actual=costo_reciente,
        )
        .filter(existencia__gt=0)
        .order_by("nombre")
    )
    productos_catalogo = []
    for producto in productos.select_related("unidad_medida").prefetch_related(
        "imagenes_producto"
    ):
        imagen = next(iter(producto.imagenes_producto.all()), None)
        productos_catalogo.append(
            {
                "id": producto.id,
                "nombre": producto.nombre,
                "sku": producto.codigo_sku,
                "stock": float(producto.existencia or 0),
                "costo": float(producto.costo_actual or 0),
                "presentacion": producto.unidad_medida.abreviatura,
                "imagen": (
                    reverse("producto_imagen", args=[imagen.id])
                    if imagen and imagen.imagen_archivo
                    else "/static/img/default.webp"
                ),
            }
        )

    return render(
        request,
        "gestiones/combos.html",
        {
            "productos_catalogo": productos_catalogo,
            "total_combos": Combos.objects.filter(is_delete=False).count(),
            "puede_registrar_combo": request.user.has_perm("manager.add_combos"),
            "mostrar_buscador": False,
        },
    )


@login_required
@permission_required("manager.view_combos", raise_exception=True)
def combos_list_view(request):
    search = request.GET.get("search", "").strip()
    combos = Combos.objects.filter(is_delete=False).select_related("imagen")
    if search:
        combos = combos.filter(Q(nombre__icontains=search) | Q(codigo_sku__icontains=search))
    paginator = Paginator(
        combos.order_by("nombre"),
        10,
    )
    page_obj = paginator.get_page(request.GET.get("page", 1))
    return render(
        request,
        "gestiones/combos_list.html",
        {
            "combos": page_obj,
            "page_obj": page_obj,
            "search": search,
            "mostrar_buscador": True,
        },
    )


@login_required
@permission_required("manager.view_combos", raise_exception=True)
def detalle_combo(request, combo_id):
    combo = get_object_or_404(
        Combos.objects.prefetch_related("detalles__producto__imagenes_producto"),
        id=combo_id,
        is_delete=False,
    )
    detalles = []
    for detalle in combo.detalles.select_related("producto", "producto__unidad_medida"):
        imagen = next(iter(detalle.producto.imagenes_producto.all()), None)
        detalles.append(
            {
                "nombre": detalle.producto.nombre,
                "sku": detalle.producto.codigo_sku,
                "presentacion": detalle.producto.unidad_medida.abreviatura,
                "cantidad": str(detalle.cantidad),
                "imagen": (
                    reverse("producto_imagen", args=[imagen.id])
                    if imagen and imagen.imagen_archivo
                    else "/static/img/default.webp"
                ),
            }
        )
    return JsonResponse(
        {
            "success": True,
            "combo": {"nombre": combo.nombre, "sku": combo.codigo_sku},
            "detalles": detalles,
        }
    )


@login_required
def combo_imagen(request, imagen_id):
    try:
        imagen = ComboImagen.objects.get(
            id=imagen_id,
            combo__is_delete=False,
        )
        response_nextcloud = obtener_archivo(imagen.imagen_archivo)
        return HttpResponse(
            response_nextcloud.content,
            content_type=response_nextcloud.headers.get(
                "Content-Type", "application/octet-stream"
            ),
        )
    except ComboImagen.DoesNotExist:
        return HttpResponse("Imagen no encontrada", status=404)
    except Exception as error:
        return HttpResponse(f"Error obteniendo imagen: {str(error)}", status=500)


@login_required
def configuracion_view(request):
    if not _puede_gestionar_configuracion(request.user):
        raise PermissionDenied
    configuracion = ConfiguracionEmpresa.objects.filter(
        is_delete=False
    ).prefetch_related("banners_tienda").first()
    suscripcion = SuscripcionSistema.objects.only(
        "fecha_inicio", "fecha_fin", "activa"
    ).first()
    dias_suscripcion_restantes = None
    if suscripcion:
        dias_suscripcion_restantes = (
            suscripcion.fecha_fin - timezone.localdate()
        ).days
    return render(
        request,
        "gestiones/configuracion.html",
        {
            "configuracion": configuracion,
            "suscripcion_sistema": suscripcion,
            "dias_suscripcion_restantes": dias_suscripcion_restantes,
            "banner_principal": (
                configuracion.banners_tienda.filter(tipo=BannerTienda.TIPO_BANNER).first()
                if configuracion
                else None
            ),
            "banners_carrusel": (
                configuracion.banners_tienda.filter(tipo=BannerTienda.TIPO_CARRUSEL)
                if configuracion
                else []
            ),
            "puede_gestionar_tienda": _puede_gestionar_tienda(request.user),
            "mostrar_buscador": False,
        },
    )


@login_required
@require_POST
def guardar_configuracion(request):
    if not _puede_gestionar_configuracion(request.user):
        raise PermissionDenied
    try:
        nombre_comercial = request.POST.get("nombre_comercial", "").strip()
        if not nombre_comercial:
            raise ValueError("Ingresa el nombre comercial del negocio")
        for campo, etiqueta in (("rtn", "El RTN"), ("telefono", "El teléfono")):
            valor = request.POST.get(campo, "").strip()
            if valor and not valor.isdigit():
                raise ValueError(f"{etiqueta} solo puede contener números")

        configuracion = ConfiguracionEmpresa.objects.filter(is_delete=False).first()
        creando = configuracion is None
        if creando:
            configuracion = ConfiguracionEmpresa(u_creo_id=request.user.id)

        for campo in (
            "nombre_comercial",
            "razon_social",
            "rtn",
            "telefono",
            "email",
            "direccion",
            "mensaje_factura",
        ):
            setattr(configuracion, campo, request.POST.get(campo, "").strip())
        try:
            dias_validez = int(request.POST.get("cotizacion_dias_validez", 7))
        except (TypeError, ValueError):
            raise ValueError("Los días de validez de la cotización no son válidos")
        if not 1 <= dias_validez <= 365:
            raise ValueError("Los días de validez de la cotización deben estar entre 1 y 365")
        configuracion.cotizacion_dias_validez = dias_validez
        diseno_factura = request.POST.get(
            "diseno_factura", ConfiguracionEmpresa.DISENO_RECIBO
        )
        if diseno_factura not in {
            ConfiguracionEmpresa.DISENO_RECIBO,
            ConfiguracionEmpresa.DISENO_PAGINA,
        }:
            raise ValueError("El diseño de factura seleccionado no es válido")
        configuracion.diseno_factura = diseno_factura
        moneda = request.POST.get(
            "moneda", ConfiguracionEmpresa.MONEDA_LEMPIRA
        )
        if moneda not in {
            ConfiguracionEmpresa.MONEDA_LEMPIRA,
            ConfiguracionEmpresa.MONEDA_DOLAR,
        }:
            raise ValueError("La moneda seleccionada no es válida")
        configuracion.moneda = moneda
        puede_gestionar_tienda = _puede_gestionar_tienda(request.user)
        configuracion.tienda_color_primario = _validar_color_tienda(
            request.POST.get("tienda_color_primario", "#32877F"),
            "El color primario",
        )
        configuracion.tienda_color_secundario = _validar_color_tienda(
            request.POST.get("tienda_color_secundario", "#10463E"),
            "El color secundario",
        )
        configuracion.tienda_color_acento = _validar_color_tienda(
            request.POST.get("tienda_color_acento", "#F5A623"),
            "El color de botones",
        )
        configuracion.tienda_subtitulo = request.POST.get(
            "tienda_subtitulo", ""
        ).strip()
        configuracion.u_modifico_id = request.user.id
        configuracion.f_modificacion = timezone.now()

        logo = request.FILES.get("logo")
        quitar_logo = request.POST.get("quitar_logo") == "true"
        if logo:
            extension = logo.name.rsplit(".", 1)[-1].lower()
            if extension not in {"jpg", "jpeg", "png", "webp"}:
                raise ValueError("El logo debe ser JPG, PNG o WEBP")
            nombre_original = logo.name.replace(" ", "_")
            nombre_archivo = f"empresa_{uuid.uuid4().hex[:8]}_{nombre_original}"
            logo_url = subir_archivo(
                logo,
                nombre_archivo,
                settings.NEXTCLOUD_FOLDER_CONFI,
            )
            logo_anterior = configuracion.logo_archivo
            configuracion.logo_nombre = nombre_original
            configuracion.logo_archivo = nombre_archivo
            configuracion.logo_url = logo_url
            configuracion.save()
            if logo_anterior:
                eliminar_archivo(logo_anterior, settings.NEXTCLOUD_FOLDER_CONFI)

        # La primera configuración puede no traer logo. Debe persistirse antes
        # de consultar o crear BannerTienda, que tiene una FK obligatoria.
        if configuracion.pk is None:
            configuracion.save()

        if not puede_gestionar_tienda:
            banners_eliminar = []
        else:
            banners_eliminar = json.loads(request.POST.get("eliminar_banners", "[]"))
        if not isinstance(banners_eliminar, list):
            raise ValueError("Los banners a eliminar no son válidos")
        for banner in BannerTienda.objects.filter(
            configuracion=configuracion,
            id__in=banners_eliminar,
        ):
            eliminar_archivo(banner.imagen_archivo, settings.NEXTCLOUD_FOLDER_CONFI)
            banner.delete()

        banner_principal = request.FILES.get("banner_principal")
        carrusel = request.FILES.getlist("carrusel")
        if not puede_gestionar_tienda and (banner_principal or carrusel):
            raise PermissionDenied
        if not puede_gestionar_tienda:
            banner_principal, carrusel = None, []
        existentes_carrusel = BannerTienda.objects.filter(
            configuracion=configuracion,
            tipo=BannerTienda.TIPO_CARRUSEL,
        ).count()
        if carrusel and not 2 <= existentes_carrusel + len(carrusel) <= 5:
            raise ValueError("El carrusel debe tener entre 2 y 5 imágenes")
        if banner_principal and BannerTienda.objects.filter(
            configuracion=configuracion,
            tipo=BannerTienda.TIPO_BANNER,
        ).exists():
            raise ValueError("Solo puedes tener un banner principal")
        banners = [(banner_principal, BannerTienda.TIPO_BANNER)] if banner_principal else []
        banners += [(imagen, BannerTienda.TIPO_CARRUSEL) for imagen in carrusel]
        orden_inicial = (
            BannerTienda.objects.filter(configuracion=configuracion).aggregate(
                mayor=Max("orden")
            )["mayor"]
            or 0
        )
        for indice, (banner, tipo_banner) in enumerate(banners, start=1):
            _validar_banner_tienda(banner)
            extension = banner.name.rsplit(".", 1)[-1].lower()
            nombre_original = banner.name.replace(" ", "_")
            nombre_archivo = f"banner_{uuid.uuid4().hex[:10]}.{extension}"
            banner_url = subir_archivo(
                banner,
                nombre_archivo,
                settings.NEXTCLOUD_FOLDER_CONFI,
            )
            BannerTienda.objects.create(
                configuracion=configuracion,
                imagen_nombre=nombre_original,
                imagen_archivo=nombre_archivo,
                imagen_url=banner_url,
                orden=orden_inicial + indice,
                tipo=tipo_banner,
            )
        else:
            logo_anterior = configuracion.logo_archivo if quitar_logo else ""
            if quitar_logo:
                configuracion.logo_nombre = ""
                configuracion.logo_archivo = ""
                configuracion.logo_url = ""
            configuracion.save()
            if logo_anterior:
                eliminar_archivo(logo_anterior, settings.NEXTCLOUD_FOLDER_CONFI)

        return JsonResponse(
            {
                "success": True,
                "message": "Configuración creada correctamente" if creando else "Configuración actualizada correctamente",
            }
        )
    except ValueError as error:
        return JsonResponse({"success": False, "message": str(error)}, status=400)
    except Exception:
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "message": "No fue posible guardar la configuración"},
            status=500,
        )


@login_required
def configuracion_logo(request):
    if not _puede_gestionar_configuracion(request.user):
        raise PermissionDenied
    configuracion = ConfiguracionEmpresa.objects.filter(is_delete=False).first()
    if not configuracion or not configuracion.logo_archivo:
        return HttpResponse("Logo no encontrado", status=404)
    try:
        archivo = obtener_archivo(
            configuracion.logo_archivo,
            settings.NEXTCLOUD_FOLDER_CONFI,
        )
        return HttpResponse(
            archivo.content,
            content_type=archivo.headers.get("Content-Type", "application/octet-stream"),
        )
    except Exception:
        return HttpResponse("No fue posible obtener el logo", status=500)


@login_required
def configuracion_banner(request, banner_id):
    if not _puede_gestionar_configuracion(request.user):
        raise PermissionDenied
    banner = get_object_or_404(BannerTienda, id=banner_id)
    try:
        archivo = obtener_archivo(
            banner.imagen_archivo,
            settings.NEXTCLOUD_FOLDER_CONFI,
        )
        return HttpResponse(
            archivo.content,
            content_type=archivo.headers.get("Content-Type", "image/jpeg"),
        )
    except Exception:
        return HttpResponse("No fue posible obtener el banner", status=500)


@login_required
@require_POST
@permission_required("manager.add_combos", raise_exception=True)
def guardar_combo(request):
    try:
        es_json = request.content_type and request.content_type.startswith(
            "application/json"
        )
        data = json.loads(request.body) if es_json else request.POST
        nombre = (data.get("nombre") or "").strip()
        codigo_sku = (data.get("codigo_sku") or "").strip()
        detalles_recibidos = data.get("detalles") or []
        if not es_json:
            detalles_recibidos = json.loads(detalles_recibidos or "[]")
        imagen_combo = request.FILES.get("imagen")

        if imagen_combo:
            extension = imagen_combo.name.rsplit(".", 1)[-1].lower()
            if extension not in {"jpg", "jpeg", "png", "webp"}:
                raise ValueError("La imagen del combo debe ser JPG, PNG o WEBP")

        if not nombre or not codigo_sku:
            raise ValueError("Ingresa el nombre y SKU del combo")
        if len(nombre) > 120 or len(codigo_sku) > 50:
            raise ValueError("El nombre o SKU supera la longitud permitida")
        if not detalles_recibidos:
            raise ValueError("Agrega al menos un producto al combo")

        def decimal_positivo(valor, campo):
            try:
                numero = Decimal(str(valor))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError(f"{campo} no es válido")
            if numero < 0:
                raise ValueError(f"{campo} no puede ser negativo")
            return numero

        precio_venta = decimal_positivo(data.get("precio_venta"), "El precio de venta")
        precio_minimo = decimal_positivo(data.get("precio_minimo"), "El precio mínimo")
        precio_maximo = decimal_positivo(data.get("precio_maximo"), "El precio máximo")
        if precio_minimo > precio_venta or precio_venta > precio_maximo:
            raise ValueError("El precio de venta debe estar entre el mínimo y el máximo")

        cantidades = {}
        for detalle in detalles_recibidos:
            try:
                producto_id = int(detalle.get("producto_id"))
            except (TypeError, ValueError):
                raise ValueError("Hay un producto inválido en el combo")
            if producto_id in cantidades:
                raise ValueError("No repitas productos en el combo")
            cantidad = decimal_positivo(detalle.get("cantidad"), "La cantidad")
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor que cero")
            cantidades[producto_id] = cantidad

        with transaction.atomic():
            if Combos.objects.filter(codigo_sku__iexact=codigo_sku).exists():
                raise ValueError("Ya existe un combo con este SKU")

            productos = {
                producto.id: producto
                for producto in Productos.objects.filter(
                    id__in=cantidades,
                    is_active=True,
                    is_delete=False,
                ).annotate(existencia=Sum("producto_inventarios__cantidad"))
            }
            if len(productos) != len(cantidades):
                raise ValueError("Uno o más productos ya no están disponibles")

            detalles_combo = []
            costo_total = Decimal("0.00")
            for producto_id, cantidad in cantidades.items():
                producto = productos[producto_id]
                existencia = producto.existencia or Decimal("0")
                if cantidad > existencia:
                    raise ValueError(
                        f"La cantidad de {producto.nombre} supera las existencias disponibles"
                    )
                ultima_compra = (
                    DetalleCompra.objects.filter(producto_id=producto_id)
                    .order_by("-compra__fecha_compra", "-id")
                    .values_list("precio_compra", flat=True)
                    .first()
                )
                costo_unitario = ultima_compra or Decimal("0.00")
                costo_total += costo_unitario * cantidad
                detalles_combo.append(
                    DetalleCombo(
                        producto=producto,
                        cantidad=cantidad,
                        costo_unitario=costo_unitario,
                    )
                )

            combo = Combos.objects.create(
                nombre=nombre,
                codigo_sku=codigo_sku,
                costo_total=costo_total,
                precio_venta=precio_venta,
                precio_venta_min=precio_minimo,
                precio_venta_max=precio_maximo,
                u_creo_id=request.user.id,
            )
            for detalle in detalles_combo:
                detalle.combo = combo
            DetalleCombo.objects.bulk_create(detalles_combo)

            if imagen_combo:
                nombre_original = imagen_combo.name.replace(" ", "_")
                nombre_archivo = f"combo_{uuid.uuid4().hex[:8]}_{nombre_original}"
                imagen_url = subir_archivo(imagen_combo, nombre_archivo)
                ComboImagen.objects.create(
                    combo=combo,
                    imagen_nombre=nombre_original,
                    imagen_archivo=nombre_archivo,
                    imagen_url=imagen_url,
                )

        return JsonResponse(
            {"success": True, "message": "Combo registrado correctamente", "id": combo.id},
            status=201,
        )
    except ValueError as error:
        return JsonResponse({"success": False, "message": str(error)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "La información enviada no es válida"}, status=400)
    except Exception:
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "message": "No fue posible registrar el combo"},
            status=500,
        )


@login_required
@require_POST
@permission_required("manager.change_combos", raise_exception=True)
def cambiar_estado_combo(request, combo_id):
    combo = get_object_or_404(Combos, id=combo_id, is_delete=False)
    combo.is_active = not combo.is_active
    combo.u_modifico_id = request.user.id
    combo.f_modificacion = timezone.now()
    combo.save(update_fields=["is_active", "u_modifico_id", "f_modificacion"])
    return JsonResponse(
        {
            "success": True,
            "activo": combo.is_active,
            "message": "Combo activado correctamente"
            if combo.is_active
            else "Combo inactivado correctamente",
        }
    )


@login_required
@permission_required("manager.view_productos", raise_exception=True)
def exportar_productos_excel(request):
    search = request.GET.get("search", "").strip()

    productos = Productos.objects.select_related(
        "categoria",
        "unidad_medida",
        "marca",
    ).filter(is_delete=False)

    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) | Q(codigo_sku__icontains=search)
        )

    encabezados = [
        "ID producto",
        "Producto",
        "Descripción",
        "Categoría",
        "Presentación",
        "Marca",
        "SKU",
        "Precio venta",
        "Precio mínimo",
        "Precio máximo",
        "Impuesto",
        "Equivalencia",
        "Es producto padre",
        "Requiere vencimiento",
        "Estado",
    ]
    libro, hoja = _libro_exportacion_grande(
        "Productos",
        encabezados,
        [12, 34, 38, 22, 20, 20, 22, 16, 16, 16, 12, 14, 18, 20, 14],
    )

    for producto in productos.order_by("id").iterator(chunk_size=500):
        _agregar_fila_exportacion(
            hoja,
            [
                producto.id,
                producto.nombre,
                producto.descripcion,
                producto.categoria.nombre,
                producto.unidad_medida.nombre,
                producto.marca.nombre,
                producto.codigo_sku,
                producto.precio_venta,
                producto.precio_venta_min,
                producto.precio_venta_max,
                producto.impuesto / Decimal("100"),
                producto.equival_unid,
                "Sí" if producto.is_master else "No",
                "Sí" if producto.vencimiento else "No",
                "Activo" if producto.is_active else "Inactivo",
            ],
            formatos={8: "#,##0.00", 9: "#,##0.00", 10: "#,##0.00", 11: "0.00%"},
        )
    return _respuesta_excel(libro, "productos.xlsx")


CATALOGOS_IMPORTABLES = {
    "categorias": (Categorias, "Categorías"),
    "marcas": (Marcas, "Marcas"),
    "presentaciones": (UMedidas, "Presentaciones"),
}


@login_required
def exportar_catalogo_excel(request, tipo):
    _requiere_superusuario(request)
    configuracion = CATALOGOS_IMPORTABLES.get(tipo)
    if not configuracion:
        raise Http404("Catálogo no válido")

    modelo, titulo = configuracion
    libro = _libro_plantilla(titulo, ["ID", "Nombre", "Descripción"])
    hoja = libro.active
    for registro in modelo.objects.filter(is_delete=False).order_by("id"):
        hoja.append([registro.id, registro.nombre, getattr(registro, "descripcion", "")])
    hoja.auto_filter.ref = hoja.dimensions
    return _respuesta_excel(libro, f"{tipo}.xlsx")


@login_required
def descargar_plantilla_catalogo(request, tipo):
    _requiere_superusuario(request)
    configuracion = CATALOGOS_IMPORTABLES.get(tipo)
    if not configuracion:
        raise Http404("Catálogo no válido")

    _, titulo = configuracion
    encabezados = (
        ["Nombre", "Abreviatura", "Valor"]
        if tipo == "presentaciones"
        else ["Nombre", "Descripción"]
    )
    return _respuesta_excel(
        _libro_plantilla(titulo, encabezados), f"plantilla_{tipo}.xlsx"
    )


@login_required
@require_POST
def importar_catalogo_excel(request, tipo):
    _requiere_superusuario(request)
    configuracion = CATALOGOS_IMPORTABLES.get(tipo)
    if not configuracion:
        return JsonResponse({"success": False, "message": "Catálogo no válido."}, status=404)

    modelo, titulo = configuracion
    try:
        encabezados, filas = _leer_filas_excel(request.FILES.get("archivo"))
        requeridos = (
            {"nombre", "abreviatura", "valor"}
            if tipo == "presentaciones"
            else {"nombre", "descripcion"}
        )
        if not requeridos.issubset(encabezados):
            faltantes = ", ".join(sorted(requeridos - set(encabezados)))
            raise ValueError(f"Faltan columnas requeridas: {faltantes}.")

        errores = []
        registros = []
        nombres_archivo = set()
        existentes = set(
            modelo.objects.filter(is_delete=False).values_list("nombre", flat=True)
        )
        for numero, fila in filas:
            nombre = str(fila.get("nombre") or "").strip()
            if not nombre:
                errores.append(f"Fila {numero}: el nombre es obligatorio.")
                continue
            clave = nombre.casefold()
            if clave in nombres_archivo or nombre in existentes:
                errores.append(f"Fila {numero}: el nombre '{nombre}' ya existe.")
                continue
            nombres_archivo.add(clave)

            if tipo == "presentaciones":
                abreviatura = str(fila.get("abreviatura") or "").strip()
                try:
                    valor = int(fila.get("valor"))
                except (TypeError, ValueError):
                    valor = 0
                if not abreviatura or valor <= 0:
                    errores.append(
                        f"Fila {numero}: abreviatura y valor mayor a cero son obligatorios."
                    )
                    continue
                registros.append({"nombre": nombre, "abreviatura": abreviatura, "valor": valor})
            else:
                registros.append(
                    {"nombre": nombre, "descripcion": str(fila.get("descripcion") or "").strip()}
                )

        if errores:
            raise ValueError("\n".join(errores[:8]))
        if not registros:
            raise ValueError("No se encontraron filas para importar.")

        with transaction.atomic():
            modelo.objects.bulk_create(
                [modelo(**registro, u_creo_id=request.user.id) for registro in registros]
            )
        return JsonResponse({"success": True, "message": f"{len(registros)} {titulo.lower()} importadas correctamente."})
    except ValueError as error:
        return JsonResponse({"success": False, "message": str(error)}, status=400)
    except Exception as error:
        # En desarrollo el motivo se devuelve al modal para que el usuario pueda
        # corregir el archivo o aplicar la migración correspondiente. En
        # producción se conserva el mensaje genérico y el detalle queda en log.
        traceback.print_exc()
        mensaje = (
            f"No se pudo importar el archivo: {error}"
            if settings.DEBUG
            else "No se pudo importar el archivo."
        )
        return JsonResponse({"success": False, "message": mensaje}, status=500)


PRODUCTOS_PLANTILLA = [
    "Nombre", "Descripción", "Categoría ID", "Presentación ID", "Marca ID", "SKU",
    "Precio venta", "Precio mínimo", "Precio máximo", "Impuesto", "Equivalencia",
    "Es padre", "Requiere vencimiento",
]


@login_required
def descargar_plantilla_productos(request):
    _requiere_superusuario(request)
    return _respuesta_excel(
        _libro_plantilla("Productos", PRODUCTOS_PLANTILLA), "plantilla_productos.xlsx"
    )


@login_required
@require_POST
def importar_productos_excel(request):
    _requiere_superusuario(request)
    try:
        encabezados, filas = _leer_filas_excel(request.FILES.get("archivo"))
        requeridos = {_normalizar_encabezado_excel(encabezado) for encabezado in PRODUCTOS_PLANTILLA}
        if not requeridos.issubset(encabezados):
            faltantes = ", ".join(sorted(requeridos - set(encabezados)))
            raise ValueError(f"Faltan columnas requeridas: {faltantes}.")

        productos = []
        errores = []
        skus_archivo = set()
        skus_existentes = set(Productos.objects.values_list("codigo_sku", flat=True))
        categorias = {item.id: item for item in Categorias.objects.filter(is_active=True, is_delete=False)}
        presentaciones = {item.id: item for item in UMedidas.objects.filter(is_active=True, is_delete=False)}
        marcas = {item.id: item for item in Marcas.objects.filter(is_active=True, is_delete=False)}

        for numero, fila in filas:
            try:
                nombre = str(fila.get("nombre") or "").strip()
                sku = str(fila.get("sku") or "").strip()
                categoria_id = int(fila.get("categoria_id"))
                presentacion_id = int(fila.get("presentacion_id"))
                marca_id = int(fila.get("marca_id"))
                precio_venta = Decimal(str(fila.get("precio_venta"))).quantize(Decimal("0.01"))

                def decimal_opcional(valor):
                    if valor is None or str(valor).strip().lower() in {"", "null", "none", "n/a"}:
                        return None
                    return Decimal(str(valor)).quantize(Decimal("0.01"))

                precio_minimo = decimal_opcional(fila.get("precio_minimo"))
                precio_maximo = decimal_opcional(fila.get("precio_maximo"))
                impuesto = Decimal(str(fila.get("impuesto"))).quantize(Decimal("0.01"))
                equivalencia = int(fila.get("equivalencia"))
            except (InvalidOperation, TypeError, ValueError):
                errores.append(f"Fila {numero}: revisa IDs, precios, impuesto y equivalencia.")
                continue

            if (
                not nombre
                or not sku
                or len(nombre) > 100
                or len(sku) > 100
                or equivalencia <= 0
                or precio_venta < 0
                or (precio_minimo is not None and precio_minimo < 0)
                or (precio_maximo is not None and precio_maximo < 0)
                or (
                    precio_minimo is not None
                    and precio_maximo is not None
                    and precio_maximo < precio_minimo
                )
            ):
                errores.append(
                    f"Fila {numero}: nombre y SKU admiten hasta 100 caracteres; "
                    "revisa también precios y equivalencia."
                )
                continue
            if sku in skus_archivo or sku in skus_existentes:
                errores.append(f"Fila {numero}: el SKU '{sku}' ya existe.")
                continue
            if categoria_id not in categorias or presentacion_id not in presentaciones or marca_id not in marcas:
                errores.append(f"Fila {numero}: categoría, presentación o marca no existe o está inactiva.")
                continue

            si = {"si", "sí", "true", "1", "yes"}
            productos.append(
                Productos(
                    nombre=nombre,
                    descripcion=str(fila.get("descripcion") or "").strip(),
                    categoria_id=categoria_id,
                    unidad_medida_id=presentacion_id,
                    marca_id=marca_id,
                    codigo_sku=sku,
                    precio_venta=precio_venta,
                    precio_venta_min=precio_minimo,
                    precio_venta_max=precio_maximo,
                    impuesto=impuesto,
                    equival_unid=equivalencia,
                    is_master=str(fila.get("es_padre") or "").strip().lower() in si,
                    vencimiento=str(fila.get("requiere_vencimiento") or "").strip().lower() in si,
                    u_creo_id=request.user.id,
                )
            )
            skus_archivo.add(sku)

        if errores:
            raise ValueError("\n".join(errores[:8]))
        if not productos:
            raise ValueError("No se encontraron filas para importar.")
        with transaction.atomic():
            Productos.objects.bulk_create(productos)
        return JsonResponse({"success": True, "message": f"{len(productos)} productos importados correctamente."})
    except ValueError as error:
        return JsonResponse({"success": False, "message": str(error)}, status=400)
    except Exception as error:
        traceback.print_exc()
        mensaje = (
            f"No se pudo importar el archivo: {error}"
            if settings.DEBUG
            else "No se pudo importar el archivo."
        )
        return JsonResponse({"success": False, "message": mensaje}, status=500)


@login_required
def producto_imagen(request, imagen_id):

    try:

        imagen = ProductosImagenes.objects.get(
            id=imagen_id,
            producto__is_delete=False,
        )

        # Consultar la imagen directamente en Nextcloud
        response_nextcloud = obtener_archivo(
            imagen.imagen_archivo
        )

        # Devolver la imagen al navegador
        response = HttpResponse(
            response_nextcloud.content,
            content_type=response_nextcloud.headers.get(
                "Content-Type",
                "application/octet-stream",
            ),
        )

        return response

    except ProductosImagenes.DoesNotExist:

        return HttpResponse(
            "Imagen no encontrada",
            status=404,
        )

    except Exception:
        # Una imagen remota no debe convertir la pantalla de productos en un 500.
        # El navegador recibe el recurso predeterminado si Nextcloud no responde.
        return redirect(static("img/default.webp"))


@login_required
def api_productos(request):

    search = request.GET.get("search", "").strip()
    try:
        page = max(1, int(request.GET.get("page", 1)))
        # El endpoint es público para las vistas internas: no se permiten
        # páginas enormes solicitadas desde una URL manipulada.
        limit = min(50, max(1, int(request.GET.get("limit", 10))))
    except ValueError:
        return JsonResponse({"error": "Paginación inválida"}, status=400)

    query = (
        Productos.objects.select_related(
            "categoria",
            "unidad_medida",
            "marca",
        )
        .prefetch_related("imagenes_producto")
        .filter(is_delete=False,is_active=True)
    )

    # =========================
    # SEARCH
    # =========================

    if search:
        query = query.filter(
            Q(nombre__icontains=search)
            | Q(codigo_sku__icontains=search)
        )

    # =========================
    # PAGINADOR
    # =========================

    paginator = Paginator(
        query.order_by("nombre", "id"),
        limit,
    )

    page_obj = paginator.get_page(page)

    results = []

    for p in page_obj:

        # ==========================================
        # IMÁGENES DEL PRODUCTO
        # ==========================================

        imagenes = []

        for imagen in p.imagenes_producto.all():

            imagenes.append(
                {
                    "id": imagen.id,
                    "nombre": (
                        imagen.imagen_nombre
                        if imagen.imagen_nombre
                        else ""
                    ),
                    "url": request.build_absolute_uri(
                        reverse(
                            "producto_imagen",
                            args=[imagen.id],
                        )
                    ),
                }
            )

        # ==========================================
        # IMAGEN PRINCIPAL
        # ==========================================

        imagen_principal = (
            imagenes[0]
            if imagenes
            else None
        )

        # ==========================================
        # RESULTADO
        # ==========================================

        results.append(
            {
                "id": p.id,
                "nombre": p.nombre,
                "codigoSKU": p.codigo_sku,
                "precioVenta": str(p.precio_venta),
                "precioVentaMin": str(p.precio_venta_min) if p.precio_venta_min is not None else "",
                "precioVentaMax": str(p.precio_venta_max) if p.precio_venta_max is not None else "",

                "unidadMedida": {
                    "nombre": (
                        p.unidad_medida.nombre
                        if p.unidad_medida
                        else ""
                    ),
                    "abreviatura": (
                        p.unidad_medida.abreviatura
                        if p.unidad_medida
                        else ""
                    ),
                },

                "categoria": {
                    "nombre": (
                        p.categoria.nombre
                        if p.categoria
                        else ""
                    )
                },

                "marca": {
                    "nombre": (
                        p.marca.nombre
                        if p.marca
                        else ""
                    )
                },

                # ==================================
                # IMAGEN PRINCIPAL
                # ==================================

                "imagenUrl": (
                    imagen_principal["url"]
                    if imagen_principal
                    else ""
                ),

                "imagenNombre": (
                    imagen_principal["nombre"]
                    if imagen_principal
                    else ""
                ),

                # ==================================
                # TODAS LAS IMÁGENES
                # ==================================

                "imagenes": imagenes,
            }
        )

    data = {
        "results": results,
        "page": page_obj.number,
        "totalPages": paginator.num_pages,
    }

    return JsonResponse(data)


@login_required
def api_productos_caja(request):
    """Productos vendibles en la sucursal del cajero, paginados para móvil."""
    if not _puede_generar_cotizaciones(request.user):
        raise PermissionDenied("No tiene permiso para buscar productos en Caja")

    perfil = get_object_or_404(PerfilUsuario, usuarios=request.user)
    if not perfil.ubicacion_id:
        return JsonResponse({"error": "El usuario no pertenece a ninguna ubicación"}, status=400)

    try:
        page = max(1, int(request.GET.get("page", 1)))
        limit = min(20, max(1, int(request.GET.get("limit", 10))))
    except ValueError:
        return JsonResponse({"error": "Paginación inválida"}, status=400)

    busqueda = request.GET.get("search", "").strip()
    ubicaciones = obtener_ubicaciones_inventario(perfil.ubicacion_id)
    cero = Value(Decimal("0"), output_field=DecimalField(max_digits=18, decimal_places=6))
    existencia = Inventarios.objects.filter(
        producto_id=OuterRef("pk"), ubicacion_id__in=ubicaciones,
        is_delete=False, cantidad__gt=0,
    ).values("producto_id").annotate(total=Sum("cantidad")).values("total")[:1]
    reservado = ReservaInventario.objects.filter(
        producto_id=OuterRef("pk"), ubicacion_id__in=ubicaciones,
        estado=ReservaInventario.Estado.RESERVADA, is_delete=False,
    ).values("producto_id").annotate(total=Sum("cantidad")).values("total")[:1]

    productos = Productos.objects.select_related("unidad_medida").prefetch_related("imagenes_producto").filter(
        is_delete=False, is_active=True,
    ).annotate(
        existencia_caja=Coalesce(Subquery(existencia), cero),
        reservado_caja=Coalesce(Subquery(reservado), cero),
    )
    if busqueda:
        productos = productos.filter(Q(nombre__icontains=busqueda) | Q(codigo_sku__icontains=busqueda))

    page_obj = Paginator(productos.order_by("nombre", "id"), limit).get_page(page)
    results = []
    for producto in page_obj:
        imagen = producto.imagenes_producto.first()
        stock_disponible = max(
            Decimal("0"), producto.existencia_caja - producto.reservado_caja
        )
        results.append({
            "codigoSKU": producto.codigo_sku,
            "nombre": producto.nombre,
            "stock": str(stock_disponible),
            "precioVenta": str(producto.precio_venta),
            "unidad": producto.unidad_medida.nombre if producto.unidad_medida else "",
            "imagenUrl": request.build_absolute_uri(reverse("producto_imagen", args=[imagen.id])) if imagen else "",
        })
    return JsonResponse({"results": results, "page": page_obj.number, "totalPages": page_obj.paginator.num_pages})


@login_required
@permission_required("manager.add_productos", raise_exception=True)
@require_http_methods(["POST"])
def post_producto(request):
    try:
        nombre = request.POST.get("nombre", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        categoria_id = request.POST.get("categoria")
        unidad_medida_id = request.POST.get("unidad_medida")
        marca_id = request.POST.get("marca")
        codigo_sku = request.POST.get("codigo_sku", "").strip()
        precio_venta = request.POST.get("precio_venta", "").replace(",", ".")
        precio_venta_min = request.POST.get("precio_venta_min", "").replace(",", ".")
        precio_venta_max = request.POST.get("precio_venta_max", "").replace(",", ".")
        vencimiento = str(request.POST.get("Vencimiento")).lower() == "true"
        impuesto = request.POST.get("impuesto", "0").strip()

        imagenes = request.FILES.getlist("Imagenes")
        espadre = str(request.POST.get("Espadre")).lower() == "true"
        vunid = int(request.POST.get("vunid", "0").strip())

        # =====================
        # VALIDACIONES
        # =====================
        if not all(
            [
                nombre,
                categoria_id,
                unidad_medida_id,
                marca_id,
                codigo_sku,
                precio_venta,
                impuesto,
            ]
        ):
            return JsonResponse(
                {"success": False, "message": "Campos obligatorios faltantes"},
                status=400,
            )

        if Productos.objects.filter(codigo_sku=codigo_sku).exists():
            return JsonResponse(
                {"success": False, "message": "SKU ya existe"},
                status=400,
            )

        categoria = Categorias.objects.filter(id=categoria_id).first()
        unidad = UMedidas.objects.filter(id=unidad_medida_id).first()
        marca = Marcas.objects.filter(id=marca_id).first()

        if not categoria or not unidad or not marca:
            return JsonResponse(
                {"success": False, "message": "Datos inválidos"},
                status=400,
            )

        try:
            precio_venta = Decimal(precio_venta)
            precio_venta_min = Decimal(precio_venta_min) if precio_venta_min else None
            precio_venta_max = Decimal(precio_venta_max) if precio_venta_max else None
        except (InvalidOperation, ValueError):
            return JsonResponse(
                {"success": False, "message": "Los precios deben ser valores numéricos válidos"},
                status=400,
            )

        if (
            precio_venta < 0
            or (precio_venta_min is not None and precio_venta_min < 0)
            or (precio_venta_max is not None and precio_venta_max < 0)
            or (
                precio_venta_min is not None
                and precio_venta_max is not None
                and precio_venta_max < precio_venta_min
            )
        ):
            return JsonResponse(
                {"success": False, "message": "El precio máximo debe ser mayor o igual al precio mínimo"},
                status=400,
            )

        # =====================
        # CREAR PRODUCTO
        # =====================
        producto = Productos.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            categoria=categoria,
            unidad_medida=unidad,
            marca=marca,
            codigo_sku=codigo_sku,
            precio_venta=precio_venta,
            precio_venta_min=precio_venta_min,
            precio_venta_max=precio_venta_max,
            vencimiento=vencimiento,
            impuesto=impuesto,
            is_master=espadre,
            equival_unid=vunid,
            u_creo_id=request.user.id,
        )

        # =====================
        # GUARDAR IMÁGENES EN NEXTCLOUD
        # =====================

        for imagen in imagenes:
            original_name = imagen.name.replace(" ", "_")
            random_prefix = uuid.uuid4().hex[:5]
            nuevo_nombre = f"{random_prefix}_{original_name}"

            # Subir directamente el archivo recibido a Nextcloud
            imagen_url = subir_archivo(
                imagen,
                nuevo_nombre
            )

            ProductosImagenes.objects.create(
                producto=producto,
                imagen_nombre=original_name,
                imagen_archivo=nuevo_nombre,
                imagen_url=imagen_url,
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Producto creado correctamente"
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "message": f"Error interno: {str(e)}"
            },
            status=500,
        )

@login_required
@permission_required("manager.view_productos", raise_exception=True)
def get_producto(request, id):

    producto = (
        Productos.objects.select_related(
            "categoria",
            "unidad_medida",
            "marca",
        )
        .prefetch_related("imagenes_producto")
        .filter(
            id=id,
            is_delete=False,
        )
        .first()
    )

    if not producto:
        return JsonResponse(
            {
                "success": False,
                "message": "Producto no encontrado",
            },
            status=404,
        )

    imagenes = []

    for imagen in producto.imagenes_producto.all():

        imagenes.append(
            {
                "id": imagen.id,
                "nombre": imagen.imagen_nombre,

                # IMPORTANTE:
                # Ya no mandamos directamente la URL de Nextcloud
                "url": reverse(
                    "producto_imagen",
                    args=[imagen.id],
                ),
            }
        )

    return JsonResponse(
        {
            "success": True,

            "producto": {
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "codigoSKU": producto.codigo_sku,
                "precioVenta": float(producto.precio_venta),
                "precioVentaMin": float(producto.precio_venta_min) if producto.precio_venta_min is not None else None,
                "precioVentaMax": float(producto.precio_venta_max) if producto.precio_venta_max is not None else None,
                "isActive": producto.is_active,
                "vencimiento": producto.vencimiento,
                "impuesto": float(producto.impuesto),
                "equival_unid": producto.equival_unid,
                "is_master": producto.is_master,

                "imagenes": imagenes,

                "categoriaId": (
                    producto.categoria.id
                    if producto.categoria
                    else None
                ),

                "categoria": (
                    {
                        "nombre": producto.categoria.nombre
                    }
                    if producto.categoria
                    else None
                ),

                "unidadMedidaId": (
                    producto.unidad_medida.id
                    if producto.unidad_medida
                    else None
                ),

                "unidadMedida": (
                    {
                        "nombre": producto.unidad_medida.nombre,
                        "abreviatura": producto.unidad_medida.abreviatura,
                    }
                    if producto.unidad_medida
                    else None
                ),

                "marcasId": (
                    producto.marca.id
                    if producto.marca
                    else None
                ),

                "marcas": (
                    {
                        "nombre": producto.marca.nombre
                    }
                    if producto.marca
                    else None
                ),
            },
        }
    )

@login_required
@permission_required("manager.change_productos", raise_exception=True)
@require_http_methods(["POST"])
def put_producto(request, id):

    try:

        import uuid

        producto = Productos.objects.filter(
            id=id,
            is_delete=False,
        ).first()

        if not producto:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Producto no encontrado",
                },
                status=404,
            )

        data = request.POST

        # =========================
        # DATOS BÁSICOS
        # =========================

        producto.nombre = data.get("Nombre", "").strip()
        producto.descripcion = data.get("Descripcion", "").strip()

        categoria_id = data.get("CategoriaId")
        unidad_id = data.get("UnidadMedidaId")
        marca_id = data.get("MarcaId")

        if not categoria_id or not unidad_id or not marca_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Categoría, Presentación y Marca son obligatorias",
                },
                status=400,
            )

        producto.categoria_id = categoria_id
        producto.unidad_medida_id = unidad_id
        producto.marca_id = marca_id

        producto.codigo_sku = data.get(
            "CodigoSKU",
            "",
        ).strip()

        precio_venta = data.get("precioVenta", "").replace(",", ".")
        precio_venta_min = data.get("precioVentaMin", "").replace(",", ".")
        precio_venta_max = data.get("precioVentaMax", "").replace(",", ".")

        try:
            precio_venta = Decimal(precio_venta)
            precio_venta_min = Decimal(precio_venta_min) if precio_venta_min else None
            precio_venta_max = Decimal(precio_venta_max) if precio_venta_max else None
        except (InvalidOperation, ValueError):
            return JsonResponse(
                {"success": False, "message": "Los precios deben ser valores numéricos válidos"},
                status=400,
            )

        if (
            precio_venta < 0
            or (precio_venta_min is not None and precio_venta_min < 0)
            or (precio_venta_max is not None and precio_venta_max < 0)
            or (
                precio_venta_min is not None
                and precio_venta_max is not None
                and precio_venta_max < precio_venta_min
            )
        ):
            return JsonResponse(
                {"success": False, "message": "El precio máximo debe ser mayor o igual al precio mínimo"},
                status=400,
            )

        producto.precio_venta_min = precio_venta_min
        producto.precio_venta_max = precio_venta_max
        producto.precio_venta = precio_venta

        impuesto = data.get(
            "impuesto",
            "0",
        ).replace(",", ".")

        producto.impuesto = float(impuesto)

        producto.is_active = (
            str(data.get("IsActive")).lower() == "true"
        )

        producto.is_master = (
            str(data.get("Espadre")).lower() == "true"
        )

        producto.vencimiento = (
            str(data.get("Vencimiento")).lower() == "true"
        )

        producto.equival_unid = data.get("vunid")

        producto.f_modificacion = timezone.now()
        producto.u_modifico_id = request.user.id

        # =========================
        # GUARDAR PRODUCTO
        # =========================

        producto.save()

        # =========================
        # ELIMINAR IMÁGENES
        # =========================

        imagenes_eliminar = request.POST.getlist(
            "ImagenesEliminar[]"
        )

        if imagenes_eliminar:

            imagenes_db = ProductosImagenes.objects.filter(
                id__in=imagenes_eliminar,
                producto=producto,
            )

            for imagen in imagenes_db:

                try:

                    eliminar_archivo(
                        imagen.imagen_archivo
                    )

                except Exception as e:

                    return JsonResponse(
                        {
                            "success": False,
                            "message": (
                                "No se pudo eliminar "
                                f"la imagen {imagen.imagen_nombre}: "
                                f"{str(e)}"
                            ),
                        },
                        status=500,
                    )

                # Eliminar registro de BD
                imagen.delete()

        # =========================
        # NUEVAS IMÁGENES
        # =========================

        imagenes = request.FILES.getlist(
            "Imagenes"
        )

        for imagen in imagenes:

            nombre_original = imagen.name.replace(
                " ",
                "_",
            )

            random_prefix = uuid.uuid4().hex[:5]

            nuevo_nombre = (
                f"{random_prefix}_{nombre_original}"
            )

            # =========================
            # SUBIR A NEXTCLOUD
            # =========================

            imagen_url = subir_archivo(
                imagen,
                nuevo_nombre,
            )

            # =========================
            # GUARDAR EN BD
            # =========================

            ProductosImagenes.objects.create(
                producto=producto,
                imagen_nombre=nombre_original,
                imagen_archivo=nuevo_nombre,
                imagen_url=imagen_url,
            )

        return JsonResponse(
            {
                "success": True,
                "message": "Producto actualizado correctamente",
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": f"Error interno: {str(e)}",
            },
            status=500,
        )


@login_required
@permission_required("manager.delete_productos", raise_exception=True)
@require_http_methods(["DELETE"])
def delete_producto(request, id):

    try:
        producto = Productos.objects.filter(id=id, is_delete=False).first()

        if not producto:
            return JsonResponse(
                {"success": False, "message": "Producto no encontrado"}, status=404
            )

        producto.is_delete = True
        producto.is_active = False
        producto.f_modificacion = timezone.now()
        producto.u_modifico_id = request.user.id
        producto.save()

        return JsonResponse(
            {"success": True, "message": "Producto eliminado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_productos", raise_exception=True)
def search_productos(request):

    search = request.GET.get("search", "").strip()

    items = Productos.objects.filter(is_delete=False, is_active=True).select_related(
        "marca", "categoria"
    )
    if search:
        items = items.filter(
            Q(nombre__icontains=search) | Q(codigo_sku__icontains=search)
        ).order_by("nombre")[:20]
    else:
        # Las sugerencias iniciales muestran los cinco productos que más se
        # han utilizado en ventas; si hay menos, se completan con los demás.
        items = items.annotate(
            veces_usada=Count(
                "producto_venta_detalles",
                filter=Q(
                    producto_venta_detalles__is_delete=False,
                    producto_venta_detalles__venta__is_delete=False,
                ),
            )
        ).order_by("-veces_usada", "nombre")[:5]

    data = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "codigo": p.codigo_sku,
            "marca": p.marca.nombre if p.marca else "",
            "categoria": p.categoria.nombre if p.categoria else "",
        }
        for p in items
    ]

    return JsonResponse(data, safe=False)



@login_required
@permission_required("manager.view_productos", raise_exception=True)
def get_productos_padre(request):
    search = request.GET.get("search", "").strip()
    productos = (
        Productos.objects.select_related(
            "categoria",
            "unidad_medida",
            "marca",
        )
        .filter(
            is_delete=False,
            is_active=True,
            is_master=True,
        )
    )

    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) | Q(codigo_sku__icontains=search)
        ).order_by("nombre")[:20]
    else:
        productos = productos.annotate(
            veces_usada=Count(
                "producto_venta_detalles",
                filter=Q(
                    producto_venta_detalles__is_delete=False,
                    producto_venta_detalles__venta__is_delete=False,
                ),
            )
        ).order_by("-veces_usada", "nombre")[:5]

    data = []

    for producto in productos:
        data.append(
            {
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "codigoSKU": producto.codigo_sku,
                "precioVenta": float(producto.precio_venta),
                "precioVentaMin": float(producto.precio_venta_min) if producto.precio_venta_min is not None else None,
                "precioVentaMax": float(producto.precio_venta_max) if producto.precio_venta_max is not None else None,
                "isActive": producto.is_active,
                "vencimiento": producto.vencimiento,
                "impuesto": float(producto.impuesto),
                "equival_unid": producto.equival_unid,
                "is_master": producto.is_master,

                "categoriaId": (
                    producto.categoria.id
                    if producto.categoria
                    else None
                ),

                "categoria": (
                    {
                        "nombre": producto.categoria.nombre
                    }
                    if producto.categoria
                    else None
                ),

                "unidadMedidaId": (
                    producto.unidad_medida.id
                    if producto.unidad_medida
                    else None
                ),

                "unidadMedida": (
                    {
                        "nombre": producto.unidad_medida.nombre,
                        "abreviatura": producto.unidad_medida.abreviatura,
                    }
                    if producto.unidad_medida
                    else None
                ),

                "marcasId": (
                    producto.marca.id
                    if producto.marca
                    else None
                ),

                "marcas": (
                    {
                        "nombre": producto.marca.nombre
                    }
                    if producto.marca
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "productos": data,
        }
    )

@login_required
@permission_required("manager.view_productos", raise_exception=True)
def get_productos_hijos(request):
    search = request.GET.get("search", "").strip()
    productos = (
        Productos.objects.select_related(
            "categoria",
            "unidad_medida",
            "marca",
        )
        .filter(
            is_delete=False,
            is_active=True,
            is_master=False,
        )
    )

    if search:
        productos = productos.filter(
            Q(nombre__icontains=search) | Q(codigo_sku__icontains=search)
        ).order_by("nombre")[:20]
    else:
        productos = productos.annotate(
            veces_usada=Count(
                "producto_venta_detalles",
                filter=Q(
                    producto_venta_detalles__is_delete=False,
                    producto_venta_detalles__venta__is_delete=False,
                ),
            )
        ).order_by("-veces_usada", "nombre")[:5]

    data = []

    for producto in productos:
        data.append(
            {
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "codigoSKU": producto.codigo_sku,
                "precioVenta": float(producto.precio_venta),
                "precioVentaMin": float(producto.precio_venta_min) if producto.precio_venta_min is not None else None,
                "precioVentaMax": float(producto.precio_venta_max) if producto.precio_venta_max is not None else None,
                "isActive": producto.is_active,
                "vencimiento": producto.vencimiento,
                "impuesto": float(producto.impuesto),
                "equival_unid": producto.equival_unid,
                "is_master": producto.is_master,

                "categoriaId": (
                    producto.categoria.id
                    if producto.categoria
                    else None
                ),

                "categoria": (
                    {
                        "nombre": producto.categoria.nombre
                    }
                    if producto.categoria
                    else None
                ),

                "unidadMedidaId": (
                    producto.unidad_medida.id
                    if producto.unidad_medida
                    else None
                ),

                "unidadMedida": (
                    {
                        "nombre": producto.unidad_medida.nombre,
                        "abreviatura": producto.unidad_medida.abreviatura,
                    }
                    if producto.unidad_medida
                    else None
                ),

                "marcasId": (
                    producto.marca.id
                    if producto.marca
                    else None
                ),

                "marcas": (
                    {
                        "nombre": producto.marca.nombre
                    }
                    if producto.marca
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "productos": data,
        }
    )

@login_required
@permission_required("manager.view_productosrel", raise_exception=True)
def productos_rel_view(request):

    search = request.GET.get("search", "").strip()

    query = (
        ProductosRel.objects
        .select_related(
            "producto_master",
            "producto_relacionado",
        )
        .all()
    )

    # =========================
    # OCULTAR ELIMINADOS
    # =========================
    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    # =========================
    # BUSCADOR
    # =========================
    if search:
        query = query.filter(
            Q(producto_master__nombre__icontains=search)
            | Q(producto_master__codigo_sku__icontains=search)
            | Q(producto_relacionado__nombre__icontains=search)
            | Q(producto_relacionado__codigo_sku__icontains=search)
        )

    # =========================
    # PAGINACIÓN
    # =========================
    paginator = Paginator(
        query.order_by("id"),
        10
    )

    page_number = request.GET.get("page", 1)

    page_obj = paginator.get_page(page_number)

    # =========================
    # CONTEXT
    # =========================
    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(
        request,
        "gestiones/productosrel.html",
        context
    )



@login_required
@permission_required(
    "manager.add_productosrel",
    raise_exception=True
)
@require_POST
def post_productosrel(request):

    try:

        # =========================
        # LEER JSON
        # =========================

        data = json.loads(request.body)

        producto_master_id = data.get("producto_master")
        producto_relacionado_id = data.get("producto_relacionado")


        # =========================
        # VALIDAR CAMPOS
        # =========================

        if not producto_master_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Debe seleccionar un producto padre"
                },
                status=400
            )


        if not producto_relacionado_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Debe seleccionar un producto hijo"
                },
                status=400
            )


        # =========================
        # EVITAR MISMO PRODUCTO
        # =========================

        if producto_master_id == producto_relacionado_id:

            return JsonResponse(
                {
                    "success": False,
                    "message": "El producto padre y el producto hijo no pueden ser el mismo"
                },
                status=400
            )


        # =========================
        # BUSCAR PRODUCTO PADRE
        # =========================

        producto_master = (
            Productos.objects
            .filter(
                id=producto_master_id,
                is_delete=False,
                is_master=True,
            )
            .first()
        )


        if not producto_master:

            return JsonResponse(
                {
                    "success": False,
                    "message": "El producto padre no existe o no es un producto padre"
                },
                status=404
            )


        # =========================
        # BUSCAR PRODUCTO HIJO
        # =========================

        producto_relacionado = (
            Productos.objects
            .filter(
                id=producto_relacionado_id,
                is_delete=False,
                is_master=False,
            )
            .first()
        )


        if not producto_relacionado:

            return JsonResponse(
                {
                    "success": False,
                    "message": "El producto hijo no existe o es un producto padre"
                },
                status=404
            )


        # =========================
        # VALIDAR RELACIÓN DUPLICADA
        # =========================

        if ProductosRel.objects.filter(
            producto_master=producto_master,
            producto_relacionado=producto_relacionado,
        ).exists():

            return JsonResponse(
                {
                    "success": False,
                    "message": "Esta relación de productos ya existe"
                },
                status=400
            )


        # =========================
        # CREAR RELACIÓN
        # =========================

        relacion = ProductosRel.objects.create(
            producto_master=producto_master,
            producto_relacionado=producto_relacionado,
            u_creo_id=request.user.id,
        )


        # =========================
        # RESPUESTA
        # =========================

        return JsonResponse(
            {
                "success": True,
                "message": "Relación de productos registrada correctamente",
                "id": relacion.id,
            }
        )


    except json.JSONDecodeError:

        return JsonResponse(
            {
                "success": False,
                "message": "Los datos enviados no tienen un formato JSON válido"
            },
            status=400
        )


    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e)
            },
            status=500
        )

@login_required
@permission_required(
    "manager.view_productosrel",
    raise_exception=True
)
def get_productosrel(request, id):

    relacion = (
        ProductosRel.objects
        .select_related(
            "producto_master",
            "producto_relacionado",
        )
        .filter(
            id=id,
            is_delete=False,
        )
        .first()
    )

    if not relacion:

        return JsonResponse(
            {
                "success": False,
                "message": "Relación de productos no encontrada",
            },
            status=404,
        )


    return JsonResponse(
        {
            "success": True,

            "productosrel": {

                "id": relacion.id,

                "productoMasterId":
                    relacion.producto_master.id,

                "productoMaster":
                    relacion.producto_master.nombre,

                "productoRelacionadoId":
                    relacion.producto_relacionado.id,

                "productoRelacionado":
                    relacion.producto_relacionado.nombre,

                "isActive":
                    relacion.is_active,

            },
        }
    )


@login_required
@permission_required(
    "manager.change_productosrel",
    raise_exception=True
)
@require_http_methods(["PUT"])
def put_productosrel(request, id):

    try:

        # =========================
        # LEER JSON
        # =========================

        data = json.loads(request.body)

        producto_master_id = data.get(
            "producto_master"
        )

        producto_relacionado_id = data.get(
            "producto_relacionado"
        )

        is_active = data.get(
            "IsActive",
            True
        )


        # =========================
        # VALIDAR CAMPOS
        # =========================

        if not producto_master_id:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Debe seleccionar un producto padre",
                },
                status=400,
            )


        if not producto_relacionado_id:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Debe seleccionar un producto hijo",
                },
                status=400,
            )


        # =========================
        # EVITAR MISMO PRODUCTO
        # =========================

        if (
            str(producto_master_id)
            == str(producto_relacionado_id)
        ):

            return JsonResponse(
                {
                    "success": False,
                    "message":
                        "El producto padre y el producto hijo no pueden ser el mismo",
                },
                status=400,
            )


        # =========================
        # BUSCAR RELACIÓN
        # =========================

        relacion = (
            ProductosRel.objects
            .filter(id=id)
            .first()
        )


        if not relacion or relacion.is_delete:

            return JsonResponse(
                {
                    "success": False,
                    "message":
                        "Relación de productos no encontrada",
                },
                status=404,
            )


        # =========================
        # BUSCAR PADRE
        # =========================

        producto_master = (
            Productos.objects
            .filter(
                id=producto_master_id,
                is_delete=False,
                is_master=True,
            )
            .first()
        )


        if not producto_master:

            return JsonResponse(
                {
                    "success": False,
                    "message":
                        "El producto padre no existe o no es un producto padre",
                },
                status=404,
            )


        # =========================
        # BUSCAR HIJO
        # =========================

        producto_relacionado = (
            Productos.objects
            .filter(
                id=producto_relacionado_id,
                is_delete=False,
                is_master=False,
            )
            .first()
        )


        if not producto_relacionado:

            return JsonResponse(
                {
                    "success": False,
                    "message":
                        "El producto hijo no existe o es un producto padre",
                },
                status=404,
            )


        # =========================
        # VALIDAR DUPLICADO
        # =========================

        existe = (
            ProductosRel.objects
            .filter(
                producto_master=producto_master,
                producto_relacionado=producto_relacionado,
                is_delete=False,
            )
            .exclude(id=id)
            .exists()
        )


        if existe:

            return JsonResponse(
                {
                    "success": False,
                    "message":
                        "Ya existe esta relación de productos",
                },
                status=400,
            )


        # =========================
        # ACTUALIZAR
        # =========================

        relacion.producto_master = producto_master

        relacion.producto_relacionado = (
            producto_relacionado
        )

        relacion.is_active = is_active

        relacion.u_modifico_id = request.user.id

        relacion.f_modificacion = timezone.now()

        relacion.save()


        # =========================
        # RESPUESTA
        # =========================

        return JsonResponse(
            {
                "success": True,
                "message":
                    "Relación de productos actualizada correctamente",
            }
        )


    except json.JSONDecodeError:

        return JsonResponse(
            {
                "success": False,
                "message":
                    "Los datos enviados no tienen un formato JSON válido",
            },
            status=400,
        )


    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500,
        )



# ───────────────────────────────────────────────────────────────
# UBICACIONES
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_ubicaciones", raise_exception=True)
def ubicaciones_view(request):

    search = request.GET.get("search", "").strip()

    query = Ubicaciones.objects.all()

    # -------------------------
    # SEARCH
    # -------------------------
    if search:
        query = query.filter(Q(nombre__icontains=search) | Q(codigo__icontains=search))

    # -------------------------
    # PAGINADOR
    # -------------------------
    paginator = Paginator(query.order_by("id"), 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "gestiones/ubicaciones.html", context)


@login_required
@permission_required("manager.add_ubicaciones", raise_exception=True)
@require_POST
def post_ubicaciones(request):

    try:
        data = json.loads(request.body)

        nombre = (data.get("nombre") or "").strip()
        codigo = (data.get("codigo") or "").strip()
        ubicaciones = (data.get("ubicacion") or "").strip()
        es_bodega = data.get("es_bodega", False)
        es_tienda = data.get("es_tienda", False)

        relacion_bodega = data.get("relacion_bodega", False)
        bodega_id = data.get("bodega_id")

        # =========================
        # VALIDACIONES BÁSICAS
        # =========================
        if not nombre:
            return JsonResponse(
                {"success": False, "message": "El nombre es obligatorio"},
                status=400,
            )

        if not es_bodega and not es_tienda:
            return JsonResponse(
                {"success": False, "message": "Debe seleccionar bodega o tienda"},
                status=400,
            )

        # =========================
        # DUPLICADOS
        # =========================
        if Ubicaciones.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe una ubicación con ese nombre"},
                status=400,
            )

        # =========================
        # CREAR OBJETO
        # =========================
        ubicacion = Ubicaciones(
            nombre=nombre,
            ubicacion=ubicaciones,
            codigo=codigo,
            es_bodega=es_bodega,
            es_tienda=es_tienda,
            u_creo_id=request.user.id,
        )

        # =========================
        # RELACIÓN (SOLO TIENDA)
        # =========================
        if es_tienda and relacion_bodega and bodega_id:
            ubicacion.bodega_id = bodega_id

        ubicacion.save()

        return JsonResponse(
            {"success": True, "message": "Ubicación creada correctamente"}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)},
            status=500,
        )


@login_required
@permission_required("manager.view_ubicaciones", raise_exception=True)
def get_ubicaciones(request, id):

    try:
        ubicacion = Ubicaciones.objects.filter(id=id).first()

        if not ubicacion or ubicacion.is_delete:
            return JsonResponse(
                {"success": False, "message": "Ubicación no encontrada"}, status=404
            )

        return JsonResponse(
            {
                "success": True,
                "ubicacion": {
                    "id": ubicacion.id,
                    "nombre": ubicacion.nombre,
                    "detalle": ubicacion.ubicacion,
                    "codigo": ubicacion.codigo,
                    "es_bodega": ubicacion.es_bodega,
                    "es_tienda": ubicacion.es_tienda,
                    "bodegaid": ubicacion.bodega.id if ubicacion.bodega else None,
                    "bodeganombre": ubicacion.bodega.nombre if ubicacion.bodega else "",
                    "isActive": ubicacion.is_active,
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)}, status=500
        )


@login_required
@permission_required("manager.change_ubicaciones", raise_exception=True)
@require_http_methods(["PUT"])
def put_ubicaciones(request, id):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        codigo = (data.get("Codigo") or "").strip()
        ubicaciones = (data.get("ubicacion") or "").strip()
        es_bodega = data.get("es_bodega", False)
        es_tienda = data.get("es_tienda", False)

        relacion_bodega = data.get("relacion_bodega", False)
        bodegaid = data.get("bodegaid")

        is_active = data.get("IsActive", True)

        # VALIDACIONES BÁSICAS
        if not nombre:
            return JsonResponse(
                {"success": False, "message": "Nombre es obligatorio"},
                status=400,
            )

        ubicacion = Ubicaciones.objects.filter(id=id, is_delete=False).first()

        if not ubicacion:
            return JsonResponse(
                {"success": False, "message": "Ubicación no encontrada"},
                status=404,
            )

        # DUPLICADOS
        if (
            Ubicaciones.objects.filter(nombre=nombre, is_delete=False)
            .exclude(id=id)
            .exists()
        ):
            return JsonResponse(
                {"success": False, "message": "Ya existe una ubicación con ese nombre"},
                status=400,
            )

        # =========================
        # ASIGNACIÓN CAMPOS
        # =========================
        ubicacion.nombre = nombre
        ubicacion.codigo = codigo
        ubicacion.ubicacion = ubicaciones
        ubicacion.es_bodega = es_bodega
        ubicacion.es_tienda = es_tienda

        # =========================
        # RELACIÓN BODEGA ↔ TIENDA
        # =========================
        if es_tienda and relacion_bodega and bodegaid:
            try:
                bodega = Ubicaciones.objects.get(id=bodegaid, es_bodega=True)
                ubicacion.bodega = bodega
            except Ubicaciones.DoesNotExist:
                return JsonResponse(
                    {"success": False, "message": "Bodega inválida"},
                    status=400,
                )
        else:
            ubicacion.bodega = None

        ubicacion.is_active = is_active
        ubicacion.u_modifico_id = request.user.id
        ubicacion.f_modificacion = timezone.now()
        ubicacion.save()

        return JsonResponse(
            {"success": True, "message": "Ubicación actualizada correctamente"}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)},
            status=500,
        )


@login_required
@permission_required("manager.delete_ubicaciones", raise_exception=True)
@require_http_methods(["DELETE"])
def delete_ubicaciones(request, id):

    try:
        ubicacion = Ubicaciones.objects.filter(id=id).first()

        if not ubicacion or ubicacion.is_delete:
            return JsonResponse(
                {"success": False, "message": "Ubicación no encontrada"}, status=404
            )

        ubicacion.is_delete = True
        ubicacion.u_modifico_id = request.user.id
        ubicacion.f_modificacion = timezone.now()
        ubicacion.save()

        return JsonResponse(
            {"success": True, "message": "Ubicación eliminada correctamente"}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)}, status=500
        )


@login_required
def search_ubicaciones(request):

    search = request.GET.get("search", "").strip()

    items = Ubicaciones.objects.filter(is_delete=False, is_active=True)

    if search:
        items = items.filter(
            Q(nombre__icontains=search) | Q(codigo__icontains=search)
        ).order_by("nombre")
    else:
        # Se consideran compras y traslados para sugerir las ubicaciones más
        # usadas. Los conteos distintos evitan duplicados al combinar relaciones.
        items = items.annotate(
            uso_compras=Count("ubicacion_compras", distinct=True),
            uso_origen=Count("ubicacion_origen_traslados", distinct=True),
            uso_destino=Count("ubicacion_destino_traslados", distinct=True),
        ).order_by("-uso_compras", "-uso_origen", "-uso_destino", "nombre")

    items = items[:5] if not search else items[:20]

    data = [
        {
            "id": u.id,
            "nombre": u.nombre,
            "codigo": u.codigo,
            "es_bodega": u.es_bodega,
            "es_tienda": u.es_tienda,
        }
        for u in items
    ]

    return JsonResponse(data, safe=False)


@login_required
def search_bodegas(request):

    search = request.GET.get("search", "").strip()

    items = Ubicaciones.objects.filter(is_delete=False, is_active=True, es_bodega=True)

    if search:
        items = items.filter(
            Q(nombre__icontains=search) | Q(codigo__icontains=search)
        ).order_by("nombre")[:20]
    else:
        items = items.annotate(
            uso_compras=Count("ubicacion_compras", distinct=True),
            uso_origen=Count("ubicacion_origen_traslados", distinct=True),
            uso_destino=Count("ubicacion_destino_traslados", distinct=True),
        ).order_by("-uso_compras", "-uso_origen", "-uso_destino", "nombre")[:5]

    data = [
        {
            "id": b.id,
            "nombre": b.nombre,
            "codigo": b.codigo,
        }
        for b in items
    ]

    return JsonResponse(data, safe=False)


# ───────────────────────────────────────────────────────────────
# COMPRAS
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_compras", raise_exception=True)
def compras_view(request):

    search = request.GET.get("search", "").strip()

    compras = Compras.objects.select_related("proveedor", "ubicacion")

    # SOLO SUS COMPRAS
    compras = compras.filter(u_creo_id=request.user.id, is_delete=False)

    # Búsqueda
    if search:
        compras = compras.filter(
            Q(proveedor__nombre_legal__icontains=search)
            | Q(proveedor__nombre_comercial__icontains=search)
            | Q(total__icontains=search)
            | Q(observaciones__icontains=search)
        )

    # CONTADORES (IMPORTANTE: sin search para que sean totales reales)
    base_compras = Compras.objects.filter(
        u_creo_id=request.user.id, is_delete=False
    )

    total_compras = base_compras.count()

    compras_completadas = base_compras.filter(estado="Completado").count()

    compras_pendientes = base_compras.filter(estado="Pendiente").count()

    # Orden + paginación
    compras = compras.order_by("-id")

    paginator = Paginator(compras, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
        # CONTADORES
        "total_compras": total_compras,
        "compras_completadas": compras_completadas,
        "compras_pendientes": compras_pendientes,
    }

    return render(request, "compras/compras.html", context)


@login_required
@permission_required("manager.view_compras", raise_exception=True)
def exportar_compras_excel(request):
    """Genera el detalle de compras para el rango de fechas solicitado."""
    fecha_inicio = request.GET.get("fecha_inicio", "").strip()
    fecha_fin = request.GET.get("fecha_fin", "").strip()
    if not fecha_inicio or not fecha_fin:
        return HttpResponse("Debe indicar la fecha inicial y final.", status=400)

    try:
        inicio_honduras, fin_honduras = _rango_fechas_honduras(
            fecha_inicio, fecha_fin
        )
    except (TypeError, ValueError):
        return HttpResponse("El rango de fechas no es válido.", status=400)

    if inicio_honduras >= fin_honduras:
        return HttpResponse("La fecha inicial no puede ser posterior a la final.", status=400)

    compras = (
        Compras.objects.select_related("proveedor", "ubicacion")
        .prefetch_related("compra_detalles__producto")
        .filter(
            is_delete=False,
            fecha_compra__gte=inicio_honduras,
            fecha_compra__lt=fin_honduras,
        )
        .order_by("-fecha_compra", "-id")
    )

    encabezados = [
        "Compra",
        "Fecha",
        "Proveedor",
        "Recepción",
        "Tipo de compra",
        "Estado",
        "Vencimiento",
        "Producto",
        "SKU",
        "Cantidad",
        "Precio unitario",
        "Impuesto %",
        "Impuesto unitario",
        "Antes de impuesto",
        "Impuestos línea",
        "Total línea",
        "Total compra antes de impuesto",
        "Total impuestos compra",
        "Total compra después de impuesto",
        "Saldo utilizado",
        "Saldo pendiente crédito",
    ]
    libro, hoja = _libro_exportacion_grande(
        "Compras",
        encabezados,
        [12, 20, 28, 22, 16, 18, 16, 34, 22, 12, 16, 12, 16, 16, 16, 16, 18, 18, 20, 16, 20],
    )

    for compra in compras.iterator(chunk_size=200):
        total_antes = Decimal(compra.total_antes_impuesto or 0)
        total_impuesto = Decimal(compra.total_impuesto or 0)
        if total_antes == 0 and total_impuesto == 0:
            total_antes = Decimal(compra.total)
        saldo_utilizado = Decimal(compra.saldo_utilizado or 0)
        saldo_pendiente_credito = (
            Decimal(compra.total) - saldo_utilizado
            if compra.tipo_compra == Compras.TIPO_CREDITO
            else Decimal("0.00")
        )

        for detalle in compra.compra_detalles.all():
            precio = Decimal(detalle.precio_compra)
            cantidad = Decimal(detalle.cantidad)
            impuesto_unitario = Decimal(detalle.impuesto_unitario or 0)
            precio_con_impuesto = Decimal(
                detalle.precio_compra_con_impuesto or detalle.precio_compra
            )
            subtotal = precio * cantidad
            impuesto_linea = impuesto_unitario * cantidad
            _agregar_fila_exportacion(
                hoja,
                [
                    compra.id,
                    _fecha_honduras(compra.fecha_compra).replace(tzinfo=None),
                    compra.proveedor.nombre_comercial,
                    compra.ubicacion.nombre,
                    compra.get_tipo_compra_display(),
                    compra.get_estado_display(),
                    _fecha_honduras(compra.fecha_vencimiento).date()
                    if compra.fecha_vencimiento
                    else "",
                    detalle.producto.nombre,
                    detalle.producto.codigo_sku,
                    cantidad,
                    precio,
                    Decimal(detalle.impuesto_porcentaje or 0),
                    impuesto_unitario,
                    subtotal,
                    impuesto_linea,
                    precio_con_impuesto * cantidad,
                    total_antes,
                    total_impuesto,
                    compra.total,
                    saldo_utilizado,
                    saldo_pendiente_credito,
                ],
                formatos={
                    2: "dd/mm/yyyy hh:mm",
                    7: "dd/mm/yyyy",
                    10: "#,##0.00",
                    11: "#,##0.00",
                    12: "#,##0.00",
                    13: "#,##0.00",
                    14: "#,##0.00",
                    15: "#,##0.00",
                    16: "#,##0.00",
                    17: "#,##0.00",
                    18: "#,##0.00",
                    19: "#,##0.00",
                    20: "#,##0.00",
                    21: "#,##0.00",
                },
            )
    return _respuesta_excel(
        libro, f"compras_{fecha_inicio}_{fecha_fin}.xlsx"
    )


@login_required
@permission_required("manager.view_compras", raise_exception=True)
def realizarcompra_view(request):
    return render(request, "compras/realizarcompra.html", {})


@login_required
@permission_required("manager.add_compras", raise_exception=True)
@require_http_methods(["POST"])
def post_compra(request):
    try:
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse(
                {"success": False, "message": "JSON inválido"}, status=400
            )

        proveedor_id = data.get("proveedorId")
        ubicacion_id = data.get("recepcionId")
        tipo_compra = data.get("tipoCompra", 1)
        usar_saldo = bool(data.get("usarSaldo", False))
        observaciones = data.get("observaciones", "").strip()
        detalles = data.get("detalles", [])

        if not proveedor_id or not ubicacion_id:
            return JsonResponse(
                {"success": False, "message": "Proveedor y ubicación son obligatorios"},
                status=400,
            )

        if not detalles:
            return JsonResponse(
                {"success": False, "message": "Debe incluir al menos un producto"},
                status=400,
            )

        proveedor = Proveedores.objects.filter(id=proveedor_id, is_delete=False).first()
        if not proveedor:
            return JsonResponse(
                {
                    "success": False,
                    "message": "El proveedor no existe o está eliminado",
                },
                status=400,
            )

        ubicacion = Ubicaciones.objects.filter(id=ubicacion_id, is_delete=False).first()
        if not ubicacion:
            return JsonResponse(
                {
                    "success": False,
                    "message": "La ubicación no existe o está eliminada",
                },
                status=400,
            )

        with transaction.atomic():
            total_antes_impuesto = Decimal("0.00")
            total_impuesto = Decimal("0.00")
            detalles_procesados = []

            for item in detalles:
                producto_id = item.get("productoId")

                try:
                    cantidad = Decimal(str(item.get("cantidad") or 0))
                    precio = Decimal(str(item.get("precioCompra") or 0))
                    impuesto_porcentaje = Decimal(str(item.get("impuesto") or 0))
                except:
                    return JsonResponse(
                        {"success": False, "message": "Cantidad, precio o impuesto inválido"},
                        status=400,
                    )

                if cantidad <= 0 or precio <= 0 or impuesto_porcentaje < 0 or impuesto_porcentaje > 100:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Cantidad y precio deben ser mayores a 0; el impuesto debe estar entre 0 y 100",
                        },
                        status=400,
                    )

                producto = Productos.objects.filter(
                    id=producto_id, is_delete=False
                ).first()
                if not producto:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": f"Producto {producto_id} no existe",
                        },
                        status=400,
                    )

                subtotal = cantidad * precio
                impuesto_unitario = (precio * impuesto_porcentaje / Decimal("100")).quantize(Decimal("0.01"))
                impuesto_linea = impuesto_unitario * cantidad
                precio_con_impuesto = precio + impuesto_unitario
                total_antes_impuesto += subtotal
                total_impuesto += impuesto_linea

                detalles_procesados.append(
                    {
                        "producto": producto,
                        "cantidad": cantidad,
                        "precio": precio,
                        "impuesto_porcentaje": impuesto_porcentaje,
                        "impuesto_unitario": impuesto_unitario,
                        "precio_con_impuesto": precio_con_impuesto,
                    }
                )

            total = total_antes_impuesto + total_impuesto
            saldo_utilizado = (
                min(Decimal(proveedor.saldo or 0), total)
                if usar_saldo
                else Decimal("0")
            )
            saldo_pendiente = total - saldo_utilizado

            compra = Compras.objects.create(
                proveedor=proveedor,
                ubicacion=ubicacion,
                tipo_compra=tipo_compra,
                observaciones=observaciones,
                estado=EstadoCompra.PENDIENTE,
                total=total,
                total_antes_impuesto=total_antes_impuesto,
                total_impuesto=total_impuesto,
                saldo_utilizado=saldo_utilizado,
                u_creo_id=request.user.id,
            )

            for item in detalles_procesados:
                DetalleCompra.objects.create(
                    compra=compra,
                    producto=item["producto"],
                    cantidad=item["cantidad"],
                    precio_compra=item["precio"],
                    impuesto_porcentaje=item["impuesto_porcentaje"],
                    impuesto_unitario=item["impuesto_unitario"],
                    precio_compra_con_impuesto=item["precio_con_impuesto"],
                    u_creo_id=request.user.id,
                )

            if tipo_compra == Compras.TIPO_CREDITO and proveedor.dias_credito > 0:
                compra.fecha_vencimiento = timezone.now() + timezone.timedelta(
                    days=proveedor.dias_credito
                )
                compra.save()

            if saldo_utilizado > 0:
                proveedor.saldo = Decimal(proveedor.saldo or 0) - saldo_utilizado
                proveedor.save(update_fields=["saldo"])

            if tipo_compra == Compras.TIPO_CREDITO and saldo_pendiente > 0:
                CuentasPorPagar.objects.create(
                    proveedor_id=proveedor.id,
                    compra_id=compra.id,
                    monto_total=saldo_pendiente,
                    monto_pendiente=saldo_pendiente,
                    fecha_vencimiento=compra.fecha_vencimiento or timezone.now(),
                    estado=EstadoCuenta.PENDIENTE,
                    u_creo_id=request.user.id,
                )

        return JsonResponse(
            {
                "success": True,
                "message": "Compra registrada correctamente",
                "compraId": compra.id,
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error interno: {str(e)}"}, status=500
        )


def _tracking_compra(compra):
    """Construye el recorrido visual usando únicamente estados ya persistidos."""
    recepcion_registrada = HAutorizarCompra.objects.filter(compra_id=compra.id).exists()
    cantidades_autorizadas = dict(
        HAutorizarCompra.objects.filter(compra_id=compra.id)
        .values("producto_id")
        .annotate(total=Sum("cantidad_autorizada"))
        .values_list("producto_id", "total")
    )
    inventario_ingresado = Inventarios.objects.filter(
        compra_id=compra.id,
        is_active=True,
        is_delete=False,
    ).exists()
    devolucion = (
        DevolucionCompra.objects.filter(compra_id=compra.id, is_delete=False)
        .order_by("-f_creacion", "-id")
        .first()
    )
    cantidades_compradas = dict(
        compra.compra_detalles.values("producto_id")
        .annotate(total=Sum("cantidad"))
        .values_list("producto_id", "total")
    )
    # Inventario solo se considera un paso completado cuando toda la compra
    # fue autorizada. Una recepción parcial debe permanecer en Recepción.
    recepcion_completa = bool(cantidades_compradas) and all(
        (cantidades_autorizadas.get(producto_id, Decimal("0")) + Decimal("0.000005"))
        >= cantidad
        for producto_id, cantidad in cantidades_compradas.items()
    )
    cantidades_devueltas = dict(
        DevolucionCompraDetalle.objects.filter(
            compra_id=compra.id,
            devolucion_compra__estado__in=(
                EstadoDevolucionCompra.PENDIENTE,
                EstadoDevolucionCompra.APROBADA,
                EstadoDevolucionCompra.COMPLETADA,
            ),
        )
        .values("producto_id")
        .annotate(total=Sum("cantidad"))
        .values_list("producto_id", "total")
    )
    devolucion_total = bool(cantidades_compradas) and all(
        (cantidades_devueltas.get(producto_id, Decimal("0")) + Decimal("0.000005"))
        >= cantidad
        for producto_id, cantidad in cantidades_compradas.items()
    )

    def detalle_estado_devolucion():
        if devolucion.estado == EstadoDevolucionCompra.RECHAZADA:
            # Las devoluciones anteriores guardaban el motivo dentro de
            # observaciones; se conserva esa compatibilidad.
            marca_motivo = "RECHAZO:"
            observaciones = devolucion.observaciones or ""
            if marca_motivo in observaciones:
                motivo = observaciones.rsplit(marca_motivo, 1)[-1].strip()
                if motivo:
                    return f"Motivo: {motivo}"
            return "Motivo de rechazo no registrado"

        if devolucion.estado in (
            EstadoDevolucionCompra.APROBADA,
            EstadoDevolucionCompra.COMPLETADA,
        ):
            return (
                f"Resolución: {devolucion.get_resolucion_display()}"
                if devolucion.resolucion
                else "Resolución pendiente de registrar"
            )
        return ""

    pasos = [
        {"nombre": "Compra", "icono": "bx-cart"},
        {"nombre": "En bodega", "icono": "bx-package"},
        {"nombre": "Recepción", "icono": "bx-clipboard"},
    ]
    paso_actual = 0
    if compra.fecha_llegada_bodega:
        paso_actual = 1
    if recepcion_registrada:
        paso_actual = 2
    if not devolucion_total:
        pasos.append({"nombre": "Inventario", "icono": "bx-box"})
        if inventario_ingresado and recepcion_completa:
            paso_actual = len(pasos) - 1
    if devolucion:
        pasos.append(
            {
                "nombre": "Devolución",
                "icono": "bx-undo",
            }
        )
        pasos.append(
            {
                "nombre": devolucion.get_estado_display(),
                "ayuda": detalle_estado_devolucion(),
                "icono": (
                    "bx-check-circle"
                    if devolucion.estado in (
                        EstadoDevolucionCompra.APROBADA,
                        EstadoDevolucionCompra.COMPLETADA,
                    )
                    else "bx-x-circle"
                    if devolucion.estado in (
                        EstadoDevolucionCompra.RECHAZADA,
                        EstadoDevolucionCompra.CANCELADA,
                    )
                    else "bx-time-five"
                ),
            }
        )
        paso_actual = len(pasos) - 1
        # Un rechazo devuelve los productos a recepción para que vuelvan a
        # inventario. Puede coexistir con el Inventario previo de una
        # recepción parcial, por eso el icono se repite al final.
        if devolucion.estado == EstadoDevolucionCompra.RECHAZADA:
            pasos.append(
                {
                    "nombre": "Inventario",
                    "icono": "bx-box",
                    "ayuda": "Productos reintegrados al inventario tras el rechazo.",
                }
            )
            paso_actual = len(pasos) - 1

    return {
        "clave": str(compra.documento_token),
        "pasos": pasos,
        "paso_actual": paso_actual,
        "version": (
            f"{devolucion.id}:{devolucion.estado}:{devolucion.resolucion or ''}:{devolucion.observaciones}:{int(devolucion_total)}"
            if devolucion
            else f"normal:{int(devolucion_total)}"
        ),
    }


@login_required
def detalle_compra_view(request, token):

    puede_ver_compras = request.user.has_perm("manager.view_compras")
    puede_recepcionar = request.user.has_perm(
        "manager.gestionar_recepcion_inventario"
    )
    if not puede_ver_compras and not puede_recepcionar:
        raise PermissionDenied("No tiene permiso para ver el detalle de la compra")

    compra = get_object_or_404(
        Compras.objects.select_related("proveedor", "ubicacion").prefetch_related(
            "compra_detalles__producto"
        ),
        documento_token=token,
    )
    if not puede_ver_compras:
        ubicaciones_permitidas = _ubicaciones_recepcion_usuario(request.user)
        if (
            ubicaciones_permitidas is not None
            and compra.ubicacion_id not in ubicaciones_permitidas
        ):
            raise PermissionDenied("No puede ver compras de esta ubicación")

    # Solo el permiso de Compras habilita importes; la vista desde la que se
    # abrió el detalle no modifica esa autorización.
    mostrar_importes = puede_ver_compras
    busqueda = request.GET.get("search", "").strip()
    detalles_query = compra.compra_detalles.select_related(
        "producto__unidad_medida"
    ).order_by("id")
    if busqueda:
        detalles_query = detalles_query.filter(
            Q(producto__nombre__icontains=busqueda)
            | Q(producto__codigo_sku__icontains=busqueda)
        )
    page_obj = Paginator(detalles_query, 10).get_page(request.GET.get("page", 1))
    detalles = []

    for d in page_obj:
        producto = d.producto

        detalles.append(
            {
                "productoNombre": producto.nombre,
                "productoId": producto.id,
                "cantidad": float(d.cantidad),
            }
        )
        if mostrar_importes:
            impuesto_unitario = Decimal(d.impuesto_unitario or 0)
            precio_con_impuesto = Decimal(
                d.precio_compra_con_impuesto or d.precio_compra
            )
            subtotal = Decimal(d.cantidad) * Decimal(d.precio_compra)
            detalles[-1].update(
                {
                    "presentacion": (
                        getattr(producto.unidad_medida, "abreviatura", "N/A")
                        if hasattr(producto, "unidad_medida")
                        else "N/A"
                    ),
                    "sku": getattr(producto, "codigo_sku", "N/A"),
                    "precioCompra": float(d.precio_compra),
                    "impuesto": float(d.impuesto_porcentaje or 0),
                    "impuestoUnitario": float(impuesto_unitario),
                    "subtotal": float(subtotal),
                    "total": float(Decimal(d.cantidad) * precio_con_impuesto),
                }
            )

    total_antes_impuesto = Decimal(compra.total_antes_impuesto or 0)
    total_impuesto = Decimal(compra.total_impuesto or 0)
    if total_antes_impuesto == 0 and total_impuesto == 0:
        total_antes_impuesto = Decimal(compra.total)

    data = {
        "id": compra.id,
        "token": compra.documento_token,
        "ubicacion": compra.ubicacion.nombre,
        "proveedorNombre": compra.proveedor.nombre_comercial,
        "tipoCompra": compra.get_tipo_compra_display(),
        "totalProductos": int(
            compra.compra_detalles.aggregate(total=Sum("cantidad"))["total"] or 0
        ),
        "detalles": detalles,
        "mostrar_importes": mostrar_importes,
        "puede_marcar_llegada": (
            puede_recepcionar
            and compra.fecha_llegada_bodega is None
            and compra.estado == EstadoCompra.PENDIENTE
        ),
        "llegada_registrada": compra.fecha_llegada_bodega is not None,
        "tracking": _tracking_compra(compra),
    }

    if mostrar_importes:
        data.update(
            {
                "totalAntesImpuesto": float(total_antes_impuesto),
                "totalImpuesto": float(total_impuesto),
                "total": float(compra.total),
                "saldoUtilizado": float(compra.saldo_utilizado or 0),
                "saldoPendiente": float(
                    Decimal(compra.total) - Decimal(compra.saldo_utilizado or 0)
                ),
            }
        )

    return render(
        request,
        "compras/detallecompra.html",
        {"compra": data, "page_obj": page_obj, "search": busqueda},
    )


@csrf_exempt
@login_required
@permission_required("manager.view_compras", raise_exception=True)
def proxy_compras_pdf(request, token):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        # Obtener compra con detalles
        compra = get_object_or_404(
            Compras.objects.select_related("proveedor", "ubicacion").prefetch_related(
                "compra_detalles__producto"
            ),
            documento_token=token,
        )

        # Consultar usuario creador
        usuario_creo = User.objects.filter(id=compra.u_creo_id).first()

        u_creo_nombre = "Desconocido"
        if usuario_creo:
            nombre = f"{usuario_creo.first_name} {usuario_creo.last_name}".strip()
            u_creo_nombre = nombre if nombre else usuario_creo.username

        # Construir datos para PDF
        data = {
            "id": compra.id,
            "proveedorNombre": compra.proveedor.nombre_comercial,
            "ubicacion": compra.ubicacion.nombre,
            "tipoCompra": compra.get_tipo_compra_display(),
            "fechaCompra": compra.fecha_compra,
            "observaciones": compra.observaciones,
            "totalProductos": sum(d.cantidad for d in compra.compra_detalles.all()),
            "uCreo": u_creo_nombre,
            "detalles": [
                {
                    "productoNombre": d.producto.nombre,
                    "sku": getattr(d.producto, "codigo_sku", "N/A"),
                    "cantidad": float(d.cantidad),
                    "precioCompra": float(d.precio_compra),
                }
                for d in compra.compra_detalles.all()
            ],
            "total": float(compra.total),
            "saldoUtilizado": float(compra.saldo_utilizado or 0),
            "saldoPendiente": float(
                Decimal(compra.total) - Decimal(compra.saldo_utilizado or 0)
            ),
        }

        pdf_bytes = generar_pdf_compra(data)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="Compra_{compra.id}.pdf"'
        return response

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


def generar_pdf_compra(compra, logo_path=None):

    if logo_path is None:
        logo_path = _logo_empresa_pdf()

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Logo
    try:
        c.drawImage(
            logo_path,
            width - 120,
            height - 60,
            width=80,
            height=40,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception:
        pass

    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "ORDEN DE COMPRA")

    # Encabezado
    c.setFont("Helvetica", 11)

    y = height - 80
    line_height = 18

    fecha = compra["fechaCompra"]
    try:
        fecha = datetime.fromisoformat(str(fecha)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass

    c.drawString(50, y, f"Compra ID: {compra['id']}")
    c.drawString(50, y - line_height, f"Proveedor: {compra['proveedorNombre']}")
    c.drawString(50, y - 2 * line_height, f"Observaciones: {compra['observaciones']}")

    c.drawString(300, y, f"Fecha: {fecha}")
    c.drawString(300, y - line_height, f"Total Productos: {compra['totalProductos']}")

    # Línea
    y_sep = y - 3 * line_height - 5
    c.line(50, y_sep, width - 50, y_sep)

    # Tabla
    y_table = y_sep - 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_table, "Producto")
    c.drawString(250, y_table, "SKU")
    c.drawString(330, y_table, "Cantidad")
    c.drawString(400, y_table, "Precio")
    c.drawString(470, y_table, "Total")

    y_table -= 15
    c.setFont("Helvetica", 10)

    subtotal = 0

    for d in compra["detalles"]:
        total_linea = d["cantidad"] * d["precioCompra"]
        subtotal += total_linea

        c.drawString(50, y_table, d["productoNombre"])
        c.drawString(250, y_table, d["sku"])
        c.drawRightString(360, y_table, str(d["cantidad"]))
        c.drawRightString(430, y_table, f"{d['precioCompra']:.2f}")
        c.drawRightString(520, y_table, f"{total_linea:.2f}")

        y_table -= 15

        if y_table < 120:
            c.showPage()
            y_table = height - 50

    # Totales
    total = compra["total"]
    saldo_pendiente = compra.get("saldoPendiente", total)

    y_tot = y_table - 30

    c.drawRightString(420, y_tot, "Subtotal:")
    c.drawRightString(520, y_tot, f"{subtotal:.2f}")

    c.drawRightString(420, y_tot - 15, "Saldo pendiente:")
    c.drawRightString(520, y_tot - 15, f"{saldo_pendiente:.2f}")

    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(420, y_tot - 30, "TOTAL:")
    c.drawRightString(520, y_tot - 30, f"{saldo_pendiente:.2f}")

    # Firmas
    y_sign = 80

    c.line(100, y_sign, 250, y_sign)
    c.drawString(100, y_sign - 15, f"Responsable: {compra['uCreo']}")

    c.line(350, y_sign, 500, y_sign)
    c.drawString(350, y_sign - 15, f"Proveedor: {compra['proveedorNombre']}")

    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


@login_required
@permission_required("manager.change_compras", raise_exception=True)
def editar_compra(request, token):
    compra = get_object_or_404(
        Compras.objects.select_related("proveedor", "ubicacion").prefetch_related(
            "compra_detalles__producto__unidad_medida"
        ),
        documento_token=token,
    )

    if compra.es_cambio:
        return HttpResponseForbidden("Las compras generadas por cambio no se pueden editar")

    detalles = compra.compra_detalles.all()

    compra_data = {
        "proveedorId": compra.proveedor.id,
        "proveedorNombre": compra.proveedor.nombre_comercial,
        "ubicacionId": compra.ubicacion.id,
        "ubicacionNombre": getattr(compra.ubicacion, "nombre", "N/A"),
        "totalCompra": float(compra.total),
        "totalAntesImpuesto": float(compra.total_antes_impuesto or 0),
        "totalImpuesto": float(compra.total_impuesto or 0),
        "saldoUtilizado": float(compra.saldo_utilizado or 0),
        "tipoCompra": compra.tipo_compra,
        "observaciones": compra.observaciones,
        "detalles": [
            {
                "id": d.id,
                "productoId": d.producto.id,
                "productoNombre": d.producto.nombre,
                "cantidad": float(d.cantidad),
                "precioCompra": float(d.precio_compra),
                "impuesto": float(d.impuesto_porcentaje or 0),
                "impuestoUnitario": float(d.impuesto_unitario or 0),
                "precioCompraConImpuesto": float(
                    d.precio_compra_con_impuesto or d.precio_compra
                ),
                "sku": getattr(d.producto, "codigo_sku", "N/A"),
                "presentacion": getattr(
                    getattr(d.producto, "unidad_medida", None), "abreviatura", "N/A"
                ),
            }
            for d in detalles
        ],
    }

    return render(
        request,
        "compras/editarcompra.html",
        {"compra": compra_data, "compra_token": compra.documento_token},
    )


@csrf_exempt
@transaction.atomic
@login_required
@permission_required("manager.change_compras", raise_exception=True)
def editar_compra_put(request, token):

    if request.method != "PUT":
        return JsonResponse({"message": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)

        proveedor_id = data.get("proveedorId")
        tipo_compra = int(data.get("tipoCompra"))
        usar_saldo = bool(data.get("usarSaldo", False))
        observaciones = data.get("observaciones", "")
        ubicacion_id = data.get("recepcionId")
        detalles = data.get("detalles", [])

        compra = get_object_or_404(
            Compras.objects.select_related("proveedor").prefetch_related("compra_detalles"),
            documento_token=token,
        )

        if compra.es_cambio:
            return JsonResponse(
                {"message": "Las compras generadas por cambio no se pueden editar"},
                status=400,
            )

        # =====================
        # VALIDACIONES
        # =====================
        if compra.estado != "Pendiente":
            return JsonResponse(
                {"message": "Solo se pueden editar compras pendientes"}, status=400
            )

        if not Ubicaciones.objects.filter(id=ubicacion_id, is_delete=False).exists():
            return JsonResponse({"message": "Ubicación no válida"}, status=400)

        proveedor_nuevo = Proveedores.objects.filter(
            id=proveedor_id, is_delete=False
        ).first()
        if not proveedor_nuevo:
            return JsonResponse({"message": "Proveedor no válido"}, status=400)

        if tipo_compra == Compras.TIPO_CREDITO:
            if not request.user.has_perm("manager.view_cuentasporpagar"):
                return JsonResponse(
                    {"message": "No tiene permiso para comprar al crédito"}, status=403
                )
            if not proveedor_nuevo.dias_credito or proveedor_nuevo.dias_credito <= 0:
                return JsonResponse(
                    {"message": "El proveedor no tiene días de crédito disponibles"}, status=400
                )

        # =====================
        # ACTUALIZAR COMPRA
        # =====================
        proveedor_anterior = compra.proveedor
        saldo_anterior_utilizado = Decimal(compra.saldo_utilizado or 0)
        if saldo_anterior_utilizado > 0:
            proveedor_anterior.saldo = Decimal(proveedor_anterior.saldo or 0) + saldo_anterior_utilizado
            proveedor_anterior.save(update_fields=["saldo"])
            if proveedor_anterior.id == proveedor_nuevo.id:
                proveedor_nuevo.refresh_from_db(fields=["saldo"])

        compra.proveedor_id = proveedor_id
        compra.tipo_compra = tipo_compra
        compra.ubicacion_id = ubicacion_id
        compra.observaciones = observaciones
        compra.u_modifico_id = request.user.id
        compra.f_modificacion = timezone.now()

        # =====================
        # ELIMINAR DETALLES
        # =====================
        compra.compra_detalles.all().delete()

        # =====================
        # RECREAR DETALLES
        # =====================
        total_antes_impuesto = Decimal("0.00")
        total_impuesto = Decimal("0.00")

        for d in detalles:
            producto_id = d.get("productoId")

            try:
                cantidad = Decimal(str(d.get("cantidad", 0)))
                precio = Decimal(str(d.get("precioCompra", 0)))
                impuesto_porcentaje = Decimal(str(d.get("impuesto") or 0))
            except (InvalidOperation, TypeError, ValueError):
                return JsonResponse(
                    {"message": "Cantidad, precio o impuesto inválido"}, status=400
                )

            if cantidad <= 0 or precio <= 0 or impuesto_porcentaje < 0 or impuesto_porcentaje > 100:
                return JsonResponse(
                    {"message": "Cantidad y precio deben ser mayores a 0; el impuesto debe estar entre 0 y 100"},
                    status=400,
                )

            if not Productos.objects.filter(id=producto_id, is_delete=False).exists():
                return JsonResponse(
                    {"message": f"Producto {producto_id} no existe"}, status=400
                )

            subtotal = cantidad * precio
            impuesto_unitario = (precio * impuesto_porcentaje / Decimal("100")).quantize(Decimal("0.01"))
            impuesto_linea = impuesto_unitario * cantidad
            precio_con_impuesto = precio + impuesto_unitario
            total_antes_impuesto += subtotal
            total_impuesto += impuesto_linea

            DetalleCompra.objects.create(
                compra=compra,
                producto_id=producto_id,
                cantidad=cantidad,
                precio_compra=precio,
                impuesto_porcentaje=impuesto_porcentaje,
                impuesto_unitario=impuesto_unitario,
                precio_compra_con_impuesto=precio_con_impuesto,
                u_creo_id=request.user.id,
            )

        # =====================
        # TOTAL
        # =====================
        total = total_antes_impuesto + total_impuesto
        saldo_utilizado = (
            min(Decimal(proveedor_nuevo.saldo or 0), total)
            if usar_saldo
            else Decimal("0")
        )
        saldo_pendiente = total - saldo_utilizado
        if saldo_utilizado > 0:
            proveedor_nuevo.saldo = Decimal(proveedor_nuevo.saldo or 0) - saldo_utilizado
            proveedor_nuevo.save(update_fields=["saldo"])

        compra.total = total
        compra.total_antes_impuesto = total_antes_impuesto
        compra.total_impuesto = total_impuesto
        compra.saldo_utilizado = saldo_utilizado

        # =====================
        # CUENTA POR PAGAR
        # =====================
        cuenta = CuentasPorPagar.objects.filter(
            compra_id=compra.id, is_delete=False
        ).first()

        # =====================
        # CRÉDITO
        # =====================
        if tipo_compra == 2:
            proveedor = Proveedores.objects.get(id=proveedor_id)

            if proveedor.dias_credito > 0:
                compra.fecha_vencimiento = timezone.now() + timedelta(
                    days=proveedor.dias_credito
                )
            else:
                compra.fecha_vencimiento = timezone.now()

            if cuenta:
                abonado = cuenta.monto_total - cuenta.monto_pendiente

                cuenta.proveedor_id = proveedor_id

                cuenta.monto_total = saldo_pendiente
                cuenta.monto_pendiente = max(saldo_pendiente - abonado, Decimal("0.00"))

                # estado automático
                if cuenta.monto_pendiente <= 0:
                    cuenta.estado = EstadoCuenta.PAGADO
                elif abonado > 0:
                    cuenta.estado = EstadoCuenta.PARCIAL
                else:
                    cuenta.estado = EstadoCuenta.PENDIENTE

                cuenta.fecha_vencimiento = compra.fecha_vencimiento
                cuenta.u_modifico_id = request.user.id
                cuenta.f_modificacion = timezone.now()
                cuenta.save()

            elif saldo_pendiente > 0:
                CuentasPorPagar.objects.create(
                    proveedor_id=proveedor_id,
                    compra_id=compra.id,
                    monto_total=saldo_pendiente,
                    monto_pendiente=saldo_pendiente,
                    fecha_vencimiento=compra.fecha_vencimiento,
                    estado=EstadoCuenta.PENDIENTE,
                    u_creo_id=request.user.id,
                )

        # =====================
        # CONTADO
        # =====================
        else:
            compra.fecha_vencimiento = None

            if cuenta:
                cuenta.is_delete = True
                cuenta.u_modifico_id = request.user.id
                cuenta.f_modificacion = timezone.now()
                cuenta.save()

        # =====================
        # GUARDAR COMPRA
        # =====================
        compra.save()

        return JsonResponse({"message": "Compra actualizada correctamente"})

    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)


# ───────────────────────────────────────────────────────────────
# CUENTAS POR PAGAR
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_cuentasporpagar", raise_exception=True)
def cuentas_por_pagar_view(request):

    search = request.GET.get("search", "").strip()

    query = CuentasPorPagar.objects.select_related("proveedor", "compra").filter(
        is_delete=False
    )

    # =====================
    # BUSCADOR
    # =====================
    if search:
        query = query.filter(
            Q(proveedor__nombre_legal__icontains=search)
            | Q(compra__id__icontains=search)
        )

    # =====================
    # CONTADORES
    # =====================
    total_pendientes = query.filter(estado=EstadoCuenta.PENDIENTE).count()
    total_parciales = query.filter(estado=EstadoCuenta.PARCIAL).count()
    total_pagadas = query.filter(estado=EstadoCuenta.PAGADO).count()
    cuentas_totales = query.count()

    # =====================
    # PAGINACIÓN
    # =====================
    paginator = Paginator(query.order_by("-id"), 10)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    hoy = timezone.localdate()
    for cuenta in page_obj:
        cuenta.dias_restantes = (cuenta.fecha_vencimiento.date() - hoy).days
        cuenta.dias_en_mora = max(-cuenta.dias_restantes, 0)

        if cuenta.monto_pendiente <= Decimal("0"):
            cuenta.estado_vencimiento = "cuenta-al-dia"
        elif cuenta.dias_restantes < 0:
            cuenta.estado_vencimiento = "cuenta-en-mora"
        elif cuenta.dias_restantes <= 5:
            cuenta.estado_vencimiento = "cuenta-por-vencer"
        else:
            cuenta.estado_vencimiento = "cuenta-al-dia"

    # =====================
    # CONTEXTO
    # =====================
    context = {
        "page_obj": page_obj,
        "cuentas": page_obj,  # para tu template actual
        "search": search,
        "total_pendientes": total_pendientes,
        "total_parciales": total_parciales,
        "total_pagadas": total_pagadas,
        "cuentas_totales": cuentas_totales,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "page_range": paginator.page_range,
        "mostrar_buscador": True,
    }

    return render(request, "gestiones/cuentasxpagar.html", context)


# ───────────────────────────────────────────────────────────────
# CUENTAS POR COBRAR
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_cuentasporcobrar", raise_exception=True)
def cuentas_por_cobrar_view(request):

    search = request.GET.get("search", "").strip()

    query = CuentasPorCobrar.objects.select_related(
        "cliente",
        "venta__id_factura_cai",
    ).filter(is_delete=False)

    if search:
        query = query.filter(
            Q(cliente__nombre__icontains=search)
            | Q(cliente__nombre2__icontains=search)
            | Q(cliente__apellido__icontains=search)
            | Q(cliente__apellido2__icontains=search)
            | Q(cliente__empresa__icontains=search)
            | Q(cliente__dni__icontains=search)
            | Q(venta__id_factura_cai__numero_factura__icontains=search)
        )

    total_pendientes = query.filter(estado=EstadoCuenta.PENDIENTE).count()
    total_parciales = query.filter(estado=EstadoCuenta.PARCIAL).count()
    total_pagadas = query.filter(estado=EstadoCuenta.PAGADO).count()
    cuentas_totales = query.count()

    paginator = Paginator(query.order_by("-id"), 10)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    hoy = timezone.localdate()

    for cuenta in page_obj:
        cuenta.dias_restantes = (cuenta.fecha_vencimiento.date() - hoy).days
        cuenta.dias_en_mora = max(-cuenta.dias_restantes, 0)

        if cuenta.monto_pendiente <= Decimal("0"):
            cuenta.estado_vencimiento = "cuenta-al-dia"
        elif cuenta.dias_restantes < 0:
            cuenta.estado_vencimiento = "cuenta-en-mora"
        elif cuenta.dias_restantes <= 5:
            cuenta.estado_vencimiento = "cuenta-por-vencer"
        else:
            cuenta.estado_vencimiento = "cuenta-al-dia"

    return render(
        request,
        "gestiones/cuentasxcobrar.html",
        {
            "cuentas": page_obj,
            "search": search,
            "total_pendientes": total_pendientes,
            "total_parciales": total_parciales,
            "total_pagadas": total_pagadas,
            "cuentas_totales": cuentas_totales,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "page_range": paginator.page_range,
            "mostrar_buscador": True,
        },
    )


@login_required
@permission_required("manager.view_cuentasporpagar", raise_exception=True)
def historial_abonos_pagar(request, id):
    cuenta = get_object_or_404(CuentasPorPagar, id=id, is_delete=False)
    abonos = list(
        RegistroAbonos.objects.filter(
            cuenta_por_pagar=cuenta,
            is_delete=False,
        ).order_by("-f_creacion", "-id")
    )
    usuarios = User.objects.in_bulk(
        [abono.u_creo_id for abono in abonos if abono.u_creo_id]
    )

    def nombre_usuario(usuario_id):
        usuario = usuarios.get(usuario_id)
        if not usuario:
            return "Sistema"
        return usuario.username

    return JsonResponse(
        {
            "success": True,
            "cuenta": cuenta.id,
            "abonos": [
                {
                    "usuario": nombre_usuario(abono.u_creo_id),
                    "fecha": timezone.localtime(abono.f_creacion).strftime(
                        "%d/%m/%Y %I:%M %p"
                    ),
                    "monto": f"{abono.monto_abonado:.2f}",
                }
                for abono in abonos
            ],
        }
    )


@login_required
@permission_required("manager.view_cuentasporcobrar", raise_exception=True)
def historial_abonos_cobrar(request, id):
    cuenta = get_object_or_404(CuentasPorCobrar, id=id, is_delete=False)
    abonos = list(
        RegistroAbonosCobrar.objects.filter(
            cuenta_por_cobrar=cuenta,
            is_delete=False,
        ).order_by("-f_creacion", "-id")
    )
    usuarios = User.objects.in_bulk(
        [abono.u_creo_id for abono in abonos if abono.u_creo_id]
    )

    def nombre_usuario(usuario_id):
        usuario = usuarios.get(usuario_id)
        if not usuario:
            return "Sistema"
        return usuario.username

    return JsonResponse(
        {
            "success": True,
            "cuenta": cuenta.id,
            "abonos": [
                {
                    "usuario": nombre_usuario(abono.u_creo_id),
                    "fecha": timezone.localtime(abono.f_creacion).strftime(
                        "%d/%m/%Y %I:%M %p"
                    ),
                    "monto": f"{abono.monto_abonado:.2f}",
                }
                for abono in abonos
            ],
        }
    )


@login_required
@require_http_methods(["POST"])
@transaction.atomic
@permission_required("manager.add_registroabonoscobrar", raise_exception=True)
def registrar_abono_cobrar(request, id):
    try:
        data = json.loads(request.body)
        monto_abono = Decimal(str(data.get("montoAbono", 0)))

        cuenta = CuentasPorCobrar.objects.select_for_update().filter(
            id=id,
            is_delete=False,
        ).first()

        if not cuenta:
            return JsonResponse(
                {"success": False, "message": "Cuenta por cobrar no encontrada"},
                status=404,
            )

        if cuenta.estado == EstadoCuenta.PAGADO:
            return JsonResponse(
                {"success": False, "message": "La cuenta ya está pagada"},
                status=400,
            )

        if monto_abono <= 0:
            return JsonResponse(
                {"success": False, "message": "El abono debe ser mayor a 0"},
                status=400,
            )

        if monto_abono > cuenta.monto_pendiente:
            return JsonResponse(
                {
                    "success": False,
                    "message": "El abono no puede ser mayor al monto pendiente",
                },
                status=400,
            )

        nuevo_pendiente = cuenta.monto_pendiente - monto_abono

        RegistroAbonosCobrar.objects.create(
            cuenta_por_cobrar=cuenta,
            monto_abonado=monto_abono,
            monto_pendiente=nuevo_pendiente,
            liquidado=(nuevo_pendiente <= 0),
            u_creo_id=request.user.id,
        )

        cuenta.monto_pendiente = nuevo_pendiente

        if nuevo_pendiente == 0:
            cuenta.estado = EstadoCuenta.PAGADO
        elif nuevo_pendiente < cuenta.monto_total:
            cuenta.estado = EstadoCuenta.PARCIAL
        else:
            cuenta.estado = EstadoCuenta.PENDIENTE

        cuenta.u_modifico_id = request.user.id
        cuenta.f_modificacion = timezone.now()
        cuenta.save()

        return JsonResponse(
            {"success": True, "message": "Abono registrado correctamente"}
        )

    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse(
            {"success": False, "message": "El monto del abono no es válido"},
            status=400,
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@csrf_exempt
@login_required
@transaction.atomic
@permission_required("manager.add_registroabonos", raise_exception=True)
def registrar_abono(request, id):
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        data = json.loads(request.body)

        monto_abono = Decimal(str(data.get("montoAbono", 0)))

        # =====================
        # OBTENER CUENTA
        # =====================
        cuenta = get_object_or_404(CuentasPorPagar, id=id, is_delete=False)

        # =====================
        # VALIDACIONES
        # =====================
        if cuenta.estado == EstadoCuenta.PAGADO:
            return JsonResponse(
                {"success": False, "message": "La cuenta ya está pagada"}, status=400
            )

        if monto_abono <= 0:
            return JsonResponse(
                {"success": False, "message": "El abono debe ser mayor a 0"}, status=400
            )

        if monto_abono > cuenta.monto_pendiente:
            return JsonResponse(
                {
                    "success": False,
                    "message": "El abono no puede ser mayor al monto pendiente",
                },
                status=400,
            )

        # =====================
        # CALCULAR NUEVO SALDO
        # =====================
        nuevo_pendiente = cuenta.monto_pendiente - monto_abono

        # =====================
        # CREAR ABONO
        # =====================
        RegistroAbonos.objects.create(
            cuenta_por_pagar=cuenta,
            monto_abonado=monto_abono,
            monto_pendiente=nuevo_pendiente,
            liquidado=(nuevo_pendiente <= 0),
            u_creo_id=request.user.id,
        )

        # =====================
        # ACTUALIZAR CUENTA
        # =====================
        cuenta.monto_pendiente = nuevo_pendiente

        if nuevo_pendiente == 0:
            cuenta.estado = EstadoCuenta.PAGADO
        elif nuevo_pendiente < cuenta.monto_total:
            cuenta.estado = EstadoCuenta.PARCIAL
        else:
            cuenta.estado = EstadoCuenta.PENDIENTE

        cuenta.u_modifico_id = request.user.id
        cuenta.f_modificacion = timezone.now()
        cuenta.save()

        return JsonResponse(
            {"success": True, "message": "Abono registrado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# ───────────────────────────────────────────────────────────────
# CLIENTES
# ───────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_clientes", raise_exception=True)
def clientes_view(request):

    search = request.GET.get("search", "").strip()

    clientes_qs = Clientes.objects.all()

    # =====================
    # BUSCADOR
    # =====================
    if search:
        clientes_qs = clientes_qs.filter(
            Q(dni__icontains=search)
            | Q(nombre__icontains=search)
            | Q(nombre2__icontains=search)
            | Q(apellido__icontains=search)
            | Q(apellido2__icontains=search)
            | Q(empresa__icontains=search)
            | Q(email__icontains=search)
            | Q(telefono__icontains=search)
        )

    # =====================
    # CONTADORES (sobre el queryset filtrado o total)
    # =====================
    total_clientes = Clientes.objects.count()
    clientes_activos = Clientes.objects.filter(is_active=True).count()
    clientes_inactivos = Clientes.objects.filter(is_active=False).count()

    # =====================
    # PAGINACIÓN
    # =====================
    paginator = Paginator(clientes_qs.order_by("-id"), 10)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # rango de páginas (como ya vienes usando)
    page_range = paginator.page_range

    context = {
        "clientes": page_obj,
        "page": page_obj.number,
        "page_range": page_range,
        "total_pages": paginator.num_pages,
        "search": search,
        # contadores
        "total_clientes": total_clientes,
        "clientes_activos": clientes_activos,
        "clientes_inactivos": clientes_inactivos,
        "mostrar_buscador": True,
    }

    return render(request, "clientes.html", context)


@login_required
@permission_required("manager.view_clientes", raise_exception=True)
def exportar_clientes_excel(request):
    search = request.GET.get("search", "").strip()
    puede_ver_credito = request.user.has_perm("manager.view_cuentasporcobrar")
    puede_ver_whatsapp = request.user.has_perm("manager.enviar_facturas_whatsapp")

    clientes = Clientes.objects.filter(is_delete=False)
    if search:
        clientes = clientes.filter(
            Q(dni__icontains=search)
            | Q(nombre__icontains=search)
            | Q(nombre2__icontains=search)
            | Q(apellido__icontains=search)
            | Q(apellido2__icontains=search)
            | Q(empresa__icontains=search)
            | Q(email__icontains=search)
            | Q(telefono__icontains=search)
        )

    encabezados = [
        "ID cliente",
        "DNI/RTN",
        "Nombre",
        "Empresa",
        "Dirección",
        "Teléfono",
        "Correo",
        "País",
        "Departamento",
        "Municipio",
        "Estado",
    ]
    if puede_ver_credito:
        encabezados.extend(["Días de crédito", "Crédito máximo"])
    if puede_ver_whatsapp:
        encabezados.append("Enviar facturas por WhatsApp")
    libro, hoja = _libro_exportacion_grande(
        "Clientes", encabezados, [14, 18, 32, 28, 36, 18, 28, 18, 22, 22, 14, 16, 18, 24]
    )

    for cliente in clientes.order_by("id").iterator(chunk_size=500):
        fila = [
            cliente.id,
            cliente.dni,
            cliente.nombre_completo or "",
            cliente.empresa or "",
            cliente.direccion or "",
            cliente.telefono or "",
            cliente.email or "",
            cliente.pais or "",
            cliente.departamento or "",
            cliente.municipio or "",
            "Activo" if cliente.is_active else "Inactivo",
        ]
        if puede_ver_credito:
            fila.extend([cliente.d_credito or 0, cliente.max_credito or Decimal("0")])
        if puede_ver_whatsapp:
            fila.append("Sí" if cliente.enviar_factura_whatsapp else "No")
        formatos = {}
        if puede_ver_credito:
            formatos[encabezados.index("Crédito máximo") + 1] = "#,##0.00"
        _agregar_fila_exportacion(hoja, fila, formatos=formatos)

    return _respuesta_excel(libro, "clientes.xlsx")


@csrf_exempt
@login_required
@permission_required(
    "manager.add_clientes",
    raise_exception=True
)
def post_clientes(request):

    # ==========================================================
    # VALIDAR METODO
    # ==========================================================

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "message": "Método no permitido"
            },
            status=405
        )


    try:

        # ==========================================================
        # LEER JSON
        # ==========================================================

        data = json.loads(request.body)


        # ==========================================================
        # DATOS PRINCIPALES
        # ==========================================================

        dni = (data.get("dni") or "").strip()


        if not dni:

            return JsonResponse(
                {
                    "success": False,
                    "message": "El DNI es obligatorio"
                },
                status=400
            )


        # ==========================================================
        # VALIDAR DNI DUPLICADO
        # ==========================================================

        if Clientes.objects.filter(
            dni=dni,
            is_delete=False
        ).exists():

            return JsonResponse(
                {
                    "success": False,
                    "message": "Ya existe un cliente con ese DNI"
                },
                status=400
            )


        # ==========================================================
        # GENERAR CODIGO DE CLIENTE
        # ==========================================================

        while True:

            cod_cliente = str(
                random.randint(
                    1000000,
                    9999999
                )
            )

            if not Clientes.objects.filter(
                cod_cliente=cod_cliente
            ).exists():

                break


        # ==========================================================
        # DATOS DE CREDITO
        # ==========================================================

        d_credito = data.get("d_credito")

        if d_credito not in [None, ""]:

            d_credito = int(d_credito)

        else:

            d_credito = None


        max_credito = data.get("max_credito")

        if max_credito not in [None, ""]:

            max_credito = max_credito

        else:

            max_credito = None


        # ==========================================================
        # CREAR CLIENTE
        # ==========================================================

        cliente = Clientes.objects.create(

            cod_cliente=cod_cliente,

            dni=dni,

            nombre=data.get("nombre") or None,

            nombre2=data.get("nombre2") or None,

            apellido=data.get("apellido") or None,

            apellido2=data.get("apellido2") or None,

            empresa=data.get("empresa") or None,

            direccion=data.get("direccion") or None,

            telefono=data.get("telefono") or None,

            enviar_factura_whatsapp=(
                bool(data.get("enviar_factura_whatsapp", False))
                if request.user.has_perm("manager.enviar_facturas_whatsapp")
                else False
            ),

            email=data.get("email") or None,

            pais=data.get("pais") or None,

            departamento=data.get("departamento") or None,

            municipio=data.get("municipio") or None,

            d_credito=d_credito,

            max_credito=max_credito,

            u_creo_id=request.user.id,
        )


        # ==========================================================
        # RESPUESTA
        # ==========================================================

        return JsonResponse(
            {
                "success": True,
                "message": "Cliente registrado correctamente",
                "id": cliente.id,
                "cod_cliente": cliente.cod_cliente,
            }
        )


    except ValueError as e:

        return JsonResponse(
            {
                "success": False,
                "message": f"Datos inválidos: {str(e)}"
            },
            status=400
        )


    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e)
            },
            status=500
        )

@login_required
@permission_required(
    "manager.view_clientes",
    raise_exception=True
)
def get_cliente(request, id):

    try:

        # ==========================================================
        # CLIENTE
        # ==========================================================

        cliente = Clientes.objects.filter(
            id=id,
            is_delete=False
        ).first()


        if not cliente:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Cliente no encontrado"
                },
                status=404
            )


        # ==========================================================
        # DATOS
        # ==========================================================

        data = {

            "id": cliente.id,

            "cod_cliente": cliente.cod_cliente,

            "dni": cliente.dni,

            "nombre": cliente.nombre,

            "nombre2": cliente.nombre2,

            "apellido": cliente.apellido,

            "apellido2": cliente.apellido2,

            "empresa": cliente.empresa,

            "direccion": cliente.direccion,

            "telefono": cliente.telefono,

            "enviar_factura_whatsapp": (
                cliente.enviar_factura_whatsapp
                if request.user.has_perm("manager.enviar_facturas_whatsapp")
                else False
            ),

            "email": cliente.email,

            "pais": cliente.pais,

            "departamento": cliente.departamento,

            "municipio": cliente.municipio,

            "d_credito": cliente.d_credito,

            "max_credito": cliente.max_credito,

            "isActive": cliente.is_active,
        }


        return JsonResponse(
            {
                "success": True,
                "cliente": data
            }
        )


    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e)
            },
            status=500
        )

@login_required
@permission_required(
    "manager.change_clientes",
    raise_exception=True
)
def put_cliente(request, id):

    # ==========================================================
    # METODO
    # ==========================================================

    if request.method != "PUT":

        return JsonResponse(
            {
                "success": False,
                "message": "Método no permitido"
            },
            status=405
        )


    try:

        # ==========================================================
        # JSON
        # ==========================================================

        data = json.loads(request.body)


        # ==========================================================
        # DNI
        # ==========================================================

        dni = (data.get("dni") or "").strip()


        if not dni:

            return JsonResponse(
                {
                    "success": False,
                    "message": "El DNI es obligatorio"
                },
                status=400
            )


        # ==========================================================
        # CLIENTE
        # ==========================================================

        cliente = get_object_or_404(
            Clientes,
            id=id,
            is_delete=False
        )


        # ==========================================================
        # VALIDAR DNI DUPLICADO
        # ==========================================================

        if Clientes.objects.filter(
            dni=dni,
            is_delete=False
        ).exclude(
            id=id
        ).exists():

            return JsonResponse(
                {
                    "success": False,
                    "message": "Ya existe otro cliente con ese DNI"
                },
                status=400
            )


        # ==========================================================
        # DATOS PERSONALES
        # ==========================================================

        cliente.dni = dni

        cliente.nombre = (
            data.get("nombre") or None
        )

        cliente.nombre2 = (
            data.get("nombre2") or None
        )

        cliente.apellido = (
            data.get("apellido") or None
        )

        cliente.apellido2 = (
            data.get("apellido2") or None
        )

        cliente.empresa = (
            data.get("empresa") or None
        )


        # ==========================================================
        # CONTACTO
        # ==========================================================

        cliente.direccion = (
            data.get("direccion") or None
        )

        cliente.email = (
            data.get("email") or None
        )

        cliente.telefono = (
            data.get("telefono") or None
        )

        # Solo el permiso específico puede cambiar la autorización de envío.
        # Sin él, el valor ya guardado se conserva aunque alguien altere el JS.
        if request.user.has_perm("manager.enviar_facturas_whatsapp"):
            cliente.enviar_factura_whatsapp = bool(
                data.get("enviar_factura_whatsapp", False)
            )


        # ==========================================================
        # UBICACION
        # ==========================================================

        cliente.pais = (
            data.get("pais") or None
        )

        cliente.departamento = (
            data.get("departamento") or None
        )

        cliente.municipio = (
            data.get("municipio") or None
        )


        # ==========================================================
        # CREDITO
        # ==========================================================

        d_credito = data.get("d_credito")

        if d_credito not in [None, ""]:

            cliente.d_credito = int(d_credito)

        else:

            cliente.d_credito = None


        max_credito = data.get("max_credito")

        if max_credito not in [None, ""]:

            cliente.max_credito = max_credito

        else:

            cliente.max_credito = None


        # ==========================================================
        # ESTADO
        # ==========================================================

        cliente.is_active = data.get(
            "isActive",
            True
        )


        # ==========================================================
        # AUDITORIA
        # ==========================================================

        cliente.u_modifico_id = request.user.id

        cliente.f_modificacion = timezone.now()


        # ==========================================================
        # GUARDAR
        # ==========================================================

        cliente.save()


        # ==========================================================
        # RESPUESTA
        # ==========================================================

        return JsonResponse(
            {
                "success": True,
                "message": "Cliente actualizado correctamente"
            }
        )


    except ValueError as e:

        return JsonResponse(
            {
                "success": False,
                "message": f"Datos inválidos: {str(e)}"
            },
            status=400
        )


    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e)
            },
            status=500
        )

@login_required
def search_clientes(request):

    if not (
        request.user.is_superuser
        or request.user.has_perm("manager.view_clientes")
        or _puede_generar_cotizaciones(request.user)
    ):
        raise PermissionDenied("No tiene permiso para buscar clientes")

    search = request.GET.get("search", "").strip()

    items = Clientes.objects.filter(is_delete=False, is_active=True)

    if search:
        items = (
            items.filter(
                Q(nombre__icontains=search)
                | Q(nombre2__icontains=search)
                | Q(apellido__icontains=search)
                | Q(apellido2__icontains=search)
                | Q(empresa__icontains=search)
                | Q(dni__icontains=search)
                | Q(telefono__icontains=search)
            )
            .distinct()
            .order_by("nombre")
        )
    else:
        items = items.order_by("-id")

    items = items[:8]

    data = [
        {
            "id": c.id,
            "dni": c.dni,
            "nombre_completo": c.nombre_completo,
            "empresa": c.empresa,
            "telefono": c.telefono,
        }
        for c in items
    ]

    return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────
# BODEGA
# ─────────────────────────────────────────────────────────────
def dashboard_bodega(request):
    return render(request, "bodega/dashboard.html")


def _ubicaciones_recepcion_usuario(user):
    """Ubicaciones que puede recibir; None significa acceso global."""
    if user.is_superuser or user.has_perm("manager.multirecepcion"):
        return None
    try:
        ubicacion = PerfilUsuario.objects.select_related("ubicacion").get(
            usuarios=user
        ).ubicacion
    except PerfilUsuario.DoesNotExist:
        raise PermissionDenied("El usuario no tiene una ubicación asignada")

    permitidas = {ubicacion.id}
    if ubicacion.bodega_id:
        permitidas.add(ubicacion.bodega_id)
    if ubicacion.es_bodega:
        permitidas.update(
            Ubicaciones.objects.filter(
                bodega_id=ubicacion.id, is_active=True, is_delete=False
            ).values_list("id", flat=True)
        )
    return permitidas


@login_required
@permission_required("manager.gestionar_recepcion_inventario", raise_exception=True)
def recepcion_inventario_view(request):

    search = request.GET.get("search", "").strip()
    ubicaciones_permitidas = _ubicaciones_recepcion_usuario(request.user)

    recepciones = []

    # =========================================================
    # COMPRAS
    # =========================================================
    compras_qs = (
        Compras.objects.filter(is_delete=False)
        .select_related("proveedor", "ubicacion", "llegada_bodega_por")
        .prefetch_related("compra_detalles")
    )
    if ubicaciones_permitidas is not None:
        compras_qs = compras_qs.filter(ubicacion_id__in=ubicaciones_permitidas)

    if search:
        compras_qs = compras_qs.filter(
            Q(id__icontains=search) | Q(proveedor__nombre_comercial__icontains=search)
        )

    # Antes se hacía una suma de autorizaciones y otra de devoluciones por cada
    # producto de cada compra. En una recepción grande eso creaba N+1 consultas.
    # Las dos agregaciones se resuelven ahora en consultas agrupadas fijas.
    compras_ids = list(compras_qs.values_list("id", flat=True))
    autorizados_por_producto = {
        (fila["compra_id"], fila["producto_id"]): fila["total"] or Decimal("0")
        for fila in HAutorizarCompra.objects.filter(compra_id__in=compras_ids)
        .values("compra_id", "producto_id")
        .annotate(total=Sum("cantidad_autorizada"))
    }
    devueltos_por_producto = {
        (fila["compra_id"], fila["producto_id"]): fila["total"] or Decimal("0")
        for fila in DevolucionCompraDetalle.objects.filter(
            compra_id__in=compras_ids,
            devolucion_compra__estado__in=ESTADOS_DEVOLUCION_ACTIVA,
        )
        .values("compra_id", "producto_id")
        .annotate(total=Sum("cantidad"))
    }

    for c in compras_qs:
        total_productos = Decimal("0.00")

        for d in c.compra_detalles.all():
            autorizado = autorizados_por_producto.get(
                (c.id, d.producto_id), Decimal("0.00")
            )
            devuelto = devueltos_por_producto.get(
                (c.id, d.producto_id), Decimal("0.00")
            )

            pendiente = d.cantidad - autorizado - devuelto

            if pendiente > 0:
                total_productos += pendiente

        recepciones.append(
            {
                "id": c.id,
                "token": c.documento_token,
                "tipo": "Compra",
                "tipo_codigo": "COMPRA",
                "detalle_url": reverse("detalle_compra", args=[c.documento_token]),
                "es_cambio": c.es_cambio,
                "referencia": getattr(c.proveedor, "nombre_comercial", ""),
                "fecha": c.fecha_compra,
                "cantidad": float(total_productos),
                "estado": c.estado,
                "llego_bodega": c.fecha_llegada_bodega is not None,
                "fecha_llegada_bodega": c.fecha_llegada_bodega,
                "llegada_bodega_por": c.llegada_bodega_por,
                "llegada_bodega_usuario": (
                    c.llegada_bodega_por.get_full_name()
                    or c.llegada_bodega_por.username
                    if c.llegada_bodega_por
                    else ""
                ),
                "puede_marcar_llegada": (
                    total_productos > 0
                    and c.fecha_llegada_bodega is None
                    and c.estado == EstadoCompra.PENDIENTE
                ),
                "puede_autorizar": (
                    total_productos > 0 and c.fecha_llegada_bodega is not None
                ),
            }
        )

    # =========================================================
    # TRASLADOS
    # =========================================================
    traslados_qs = (
        Traslados.objects.filter(is_delete=False)
        .select_related("ubicacion_origen", "ubicacion_destino")
        .prefetch_related("detalles_traslado")
    )
    if ubicaciones_permitidas is not None:
        traslados_qs = traslados_qs.filter(
            ubicacion_destino_id__in=ubicaciones_permitidas
        )

    if search:
        traslados_qs = traslados_qs.filter(
            Q(id__icontains=search)
            | Q(ubicacion_origen__nombre__icontains=search)
            | Q(ubicacion_destino__nombre__icontains=search)
        )

    for t in traslados_qs:
        total_pendiente = Decimal("0.00")

        for d in t.detalles_traslado.all():
            pendiente = d.cantidad_solicitada - d.cantidad_entregada
            if pendiente > 0:
                total_pendiente += pendiente

        recepciones.append(
            {
                "id": t.id,
                "token": t.documento_token,
                "tipo": "Traslado",
                "tipo_codigo": "TRASLADO",
                "detalle_url": reverse("detalle_traslado", args=[t.documento_token]),
                "referencia": f"{t.ubicacion_origen.nombre} → {t.ubicacion_destino.nombre}",
                "fecha": t.f_creacion,
                "cantidad": float(total_pendiente),
                "estado": t.estado,
                "llego_bodega": False,
                "puede_marcar_llegada": False,
                "puede_autorizar": total_pendiente > 0,
            }
        )

    # =========================================================
    # ORDENAR TODO JUNTO POR FECHA DESC
    # =========================================================
    recepciones = sorted(recepciones, key=lambda x: x["fecha"], reverse=True)

    # =========================================================
    # CONTADORES
    # =========================================================
    entradas_completadas = len([x for x in recepciones if x["estado"] == "Completado"])
    entradas_pendientes = len(
        [
            x
            for x in recepciones
            if x["estado"] in (EstadoCompra.PENDIENTE, EstadoCompra.LLEGADA_BODEGA)
        ]
    )
    total_entradas = len(recepciones)

    total_devoluciones = DevolucionCompra.objects.filter(
        compra_id__in=compras_ids
    ).count()

    # =========================================================
    # PAGINADOR MANUAL
    # =========================================================
    paginator = Paginator(recepciones, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "recepciones": page_obj.object_list,
        "compras_completadas": entradas_completadas,
        "compras_pendientes": entradas_pendientes,
        "total_compras": total_entradas,
        "total_devoluciones": total_devoluciones,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "page_range": paginator.page_range,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "bodega/einventario.html", context)


@login_required
@require_POST
@transaction.atomic
@permission_required("manager.gestionar_recepcion_inventario", raise_exception=True)
def marcar_llegada_compra(request, token):
    """Registra la entrega física en bodega sin afectar el inventario."""
    compra = get_object_or_404(
        Compras.objects.select_for_update().select_related("ubicacion"),
        documento_token=token,
        is_active=True,
        is_delete=False,
    )
    ubicaciones_permitidas = _ubicaciones_recepcion_usuario(request.user)
    if (
        ubicaciones_permitidas is not None
        and compra.ubicacion_id not in ubicaciones_permitidas
    ):
        raise PermissionDenied("No puede registrar llegadas para esta ubicación")

    if compra.fecha_llegada_bodega:
        return JsonResponse(
            {"ok": True, "mensaje": "La compra ya está en bodega."}
        )
    if compra.estado != EstadoCompra.PENDIENTE:
        return JsonResponse(
            {
                "ok": False,
                "mensaje": "Solo puede marcar llegadas de compras pendientes.",
            },
            status=400,
        )

    compra.fecha_llegada_bodega = timezone.now()
    compra.llegada_bodega_por = request.user
    compra.estado = EstadoCompra.LLEGADA_BODEGA
    compra.u_modifico_id = request.user.id
    compra.f_modificacion = timezone.now()
    compra.save(
        update_fields=[
            "fecha_llegada_bodega",
            "llegada_bodega_por",
            "estado",
            "u_modifico_id",
            "f_modificacion",
        ]
    )
    return JsonResponse(
        {
            "ok": True,
            "mensaje": "La compra está en bodega. Aún no se ingresó inventario.",
        }
    )


@login_required
@permission_required("manager.gestionar_recepcion_inventario", raise_exception=True)
def autorizar_entrada_view(request, tipo, token):

    ubicaciones_permitidas = _ubicaciones_recepcion_usuario(request.user)

    # =========================================================
    # SI ES COMPRA
    # =========================================================
    if tipo == "Compra":
        compra = get_object_or_404(
            Compras.objects.select_related("proveedor", "ubicacion").prefetch_related(
                "compra_detalles__producto__unidad_medida",
                "compra_detalles__producto__marca",
            ),
            documento_token=token,
        )

        if (
            ubicaciones_permitidas is not None
            and compra.ubicacion_id not in ubicaciones_permitidas
        ):
            raise PermissionDenied("No puede recibir compras de esta ubicación")
        if not compra.fecha_llegada_bodega:
            raise PermissionDenied(
                "Primero debe marcar la compra como en bodega"
            )

        historial = HAutorizarCompra.objects.filter(compra_id=compra.id)

        devoluciones_pendientes = DevolucionCompraDetalle.objects.filter(
            compra_id=compra.id,
            devolucion_compra__estado__in=ESTADOS_DEVOLUCION_ACTIVA,
        )

        detalles = []

        for d in compra.compra_detalles.all():
            autorizado = historial.filter(producto_id=d.producto_id).aggregate(
                total=Sum("cantidad_autorizada")
            )["total"] or Decimal("0")

            bloqueado = devoluciones_pendientes.filter(
                producto_id=d.producto_id
            ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

            disponible = d.cantidad - autorizado - bloqueado

            # Compatibilidad con recepciones antiguas guardadas con dos
            # decimales: evita dejar una fracción residual de presentación.
            if disponible <= Decimal("0.005"):
                disponible = Decimal("0")

            hijos = []
            relaciones_hijo = ProductosRel.objects.filter(
                producto_master=d.producto,
                is_active=True,
                is_delete=False,
                producto_relacionado__is_active=True,
                producto_relacionado__is_delete=False,
            ).select_related("producto_relacionado__unidad_medida")
            equivalencia_padre = Decimal(d.producto.equival_unid or 1)
            for relacion in relaciones_hijo:
                hijo = relacion.producto_relacionado
                equivalencia_hijo = Decimal(hijo.equival_unid or 1)
                maximo_hijo = (disponible * equivalencia_padre) / equivalencia_hijo
                hijos.append(
                    {
                        "id": hijo.id,
                        "nombre": hijo.nombre,
                        "sku": hijo.codigo_sku or "N/A",
                        "presentacion": getattr(hijo.unidad_medida, "abreviatura", "unidad"),
                        "equivalencia": float(equivalencia_padre / equivalencia_hijo),
                        "maximo": float(maximo_hijo),
                    }
                )

            detalles.append(
                {
                    "productoId": d.producto.id,
                    "productoNombre": d.producto.nombre,
                    "cantidad": float(disponible),
                    "precioCompra": float(d.precio_compra),
                    "sku": d.producto.codigo_sku or "N/A",
                    "presentacion": getattr(
                        d.producto.unidad_medida, "abreviatura", "N/A"
                    ),
                    "marcas": getattr(d.producto.marca, "nombre", "N/A"),
                    "requiereVencimiento": d.producto.vencimiento,
                    "hijos": hijos,
                }
            )

        puede_autorizar = any(x["cantidad"] > 0 for x in detalles)

        compra_data = {
        "id": compra.id,
        "token": compra.documento_token,
            "proveedorNombre": compra.proveedor.nombre_legal,
            "total": float(compra.total),
            "tipoCompra": compra.tipo_compra,
            "observaciones": compra.observaciones,
            "fechaCompra": compra.fecha_compra.strftime("%Y-%m-%d %H:%M"),
            "detalles": detalles,
            "puede_autorizar": puede_autorizar,
            "tipo": "Compra",
            "tracking": _tracking_compra(compra),
        }

    # =========================================================
    # SI ES TRASLADO
    # =========================================================
    elif tipo == "Traslado":
        traslado = get_object_or_404(
            Traslados.objects.select_related(
                "ubicacion_origen", "ubicacion_destino", "solicitado_por"
            ).prefetch_related(
                "detalles_traslado__producto__unidad_medida",
                "detalles_traslado__producto__marca",
            ),
            documento_token=token,
        )

        if (
            ubicaciones_permitidas is not None
            and traslado.ubicacion_destino_id not in ubicaciones_permitidas
        ):
            raise PermissionDenied("No puede recibir traslados de esta ubicación")

        detalles = []

        for d in traslado.detalles_traslado.all():
            pendiente = d.cantidad_solicitada - d.cantidad_entregada

            if pendiente < 0:
                pendiente = Decimal("0")

            detalles.append(
                {
                    "productoId": d.producto.id,
                    "productoNombre": d.producto.nombre,
                    "cantidad": float(pendiente),
                    "precioCompra": 0,
                    "sku": d.producto.codigo_sku or "N/A",
                    "presentacion": getattr(
                        d.producto.unidad_medida, "abreviatura", "N/A"
                    ),
                    "marcas": getattr(d.producto.marca, "nombre", "N/A"),
                    "requiereVencimiento": False,
                }
            )

        puede_autorizar = any(x["cantidad"] > 0 for x in detalles)

        compra_data = {
            "id": traslado.id,
            "proveedorNombre": "",
            "total": 0,
            "tipoCompra": "TRASLADO INTERNO",
            "observaciones": traslado.observaciones,
            "fechaCompra": traslado.f_creacion.strftime("%Y-%m-%d %H:%M"),
            "detalles": detalles,
            "puede_autorizar": puede_autorizar,
            "tipo": "Traslado",
        }

    else:
        raise Http404("Tipo no válido")

    # Evita columnas vacías: solo se muestran cuando algún detalle realmente
    # requiere fecha de vencimiento o puede convertirse a un producto hijo.
    compra_data["mostrar_vencimiento"] = any(
        detalle.get("requiereVencimiento", False)
        for detalle in compra_data["detalles"]
    )
    compra_data["mostrar_conversion"] = any(
        detalle.get("hijos", []) for detalle in compra_data["detalles"]
    )
    paginator = Paginator(compra_data["detalles"], 10)
    detalles_paginados = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "bodega/confiinventario.html",
        {
            "compra_id": compra_data["id"],
            "compra": compra_data,
            "detalles": detalles_paginados,
            "page_obj": detalles_paginados,
        },
    )


def obtener_productos_relacionados(producto, cantidad):

    productos_inventario = []

    # ==========================================
    # OBTENER RELACIONES DONDE ES PRODUCTO PADRE
    # ==========================================

    relaciones_padre = (
        ProductosRel.objects
        .select_related(
            "producto_master",
            "producto_relacionado",
        )
        .filter(
            producto_master=producto,
            is_active=True,
            is_delete=False,
        )
    )

    # ==========================================
    # OBTENER RELACIONES DONDE ES PRODUCTO HIJO
    # ==========================================

    relaciones_hijo = (
        ProductosRel.objects
        .select_related(
            "producto_master",
            "producto_relacionado",
        )
        .filter(
            producto_relacionado=producto,
            is_active=True,
            is_delete=False,
        )
    )

    # ==========================================
    # PRODUCTOS INVOLUCRADOS
    # ==========================================

    productos = {
        producto.id: producto
    }

    # ==========================================
    # AGREGAR PRODUCTOS HIJOS
    # ==========================================

    for rel in relaciones_padre:

        productos[
            rel.producto_relacionado.id
        ] = rel.producto_relacionado

    # ==========================================
    # AGREGAR PRODUCTOS PADRE
    # ==========================================

    for rel in relaciones_hijo:

        productos[
            rel.producto_master.id
        ] = rel.producto_master

        # Un hijo comparte existencias con todos los demás hijos del mismo
        # padre. Por ello, una salida de uno debe actualizar a cada hermano.
        for hermano in ProductosRel.objects.select_related(
            "producto_relacionado"
        ).filter(
            producto_master=rel.producto_master,
            is_active=True,
            is_delete=False,
        ):
            productos[hermano.producto_relacionado.id] = hermano.producto_relacionado

    # ==========================================
    # CONVERTIR A UNIDAD BASE
    # ==========================================

    equivalencia_producto = (
        Decimal(producto.equival_unid)
        if producto.equival_unid
        else Decimal("1")
    )

    cantidad_base = (
        Decimal(cantidad)
        * equivalencia_producto
    )

    # ==========================================
    # CALCULAR CANTIDAD PARA CADA PRODUCTO
    # ==========================================

    for prod in productos.values():

        equivalencia = (
            Decimal(prod.equival_unid)
            if prod.equival_unid
            else Decimal("1")
        )

        cantidad_convertida = (
            cantidad_base
            / equivalencia
        )

        productos_inventario.append(
            {
                "producto": prod,
                "cantidad": cantidad_convertida,
            }
        )

    return productos_inventario


ESTADOS_DEVOLUCION_ACTIVA = (
    EstadoDevolucionCompra.PENDIENTE,
    EstadoDevolucionCompra.APROBADA,
)


def actualizar_estado_recepcion_compra(compra):
    """Calcula el estado con unidades recibidas y devoluciones activas."""
    autorizados = dict(
        HAutorizarCompra.objects.filter(compra_id=compra.id)
        .values("producto_id").annotate(total=Sum("cantidad_autorizada"))
        .values_list("producto_id", "total")
    )
    devueltos = dict(
        DevolucionCompraDetalle.objects.filter(
            compra_id=compra.id,
            devolucion_compra__estado__in=ESTADOS_DEVOLUCION_ACTIVA,
        ).values("producto_id").annotate(total=Sum("cantidad")).values_list("producto_id", "total")
    )
    detalles = compra.compra_detalles.all()
    hay_devolucion = any(devueltos.values())
    completada = all(
        (
            autorizados.get(detalle.producto_id, Decimal("0"))
            + devueltos.get(detalle.producto_id, Decimal("0"))
            + Decimal("0.005")
        ) >= detalle.cantidad
        for detalle in detalles
    )

    if hay_devolucion:
        nuevo_estado = EstadoCompra.CON_DEVOLUCION
    elif completada:
        nuevo_estado = EstadoCompra.COMPLETADO
    elif any(autorizados.values()):
        nuevo_estado = EstadoCompra.RECEPCION_PARCIAL
    else:
        nuevo_estado = (
            EstadoCompra.LLEGADA_BODEGA
            if compra.fecha_llegada_bodega
            else EstadoCompra.PENDIENTE
        )

    if compra.estado != nuevo_estado:
        compra.estado = nuevo_estado
        compra.save(update_fields=["estado"])


@csrf_exempt
@transaction.atomic
@login_required
@permission_required("manager.gestionar_recepcion_inventario", raise_exception=True)
def post_autorizar_inventario(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        data = json.loads(request.body)

        entrada_id = data.get("EntradaId")
        tipo = data.get("TipoEntrada")
        productos = data.get("Productos", [])

        if not entrada_id or not tipo or not productos:
            return JsonResponse(
                {"success": False, "message": "Datos incompletos"}, status=400
            )

        ubicaciones_permitidas = _ubicaciones_recepcion_usuario(request.user)

        # =====================================================
        # COMPRA
        # =====================================================
        if tipo == "COMPRA":

            entrada = get_object_or_404(
                Compras.objects
                .select_related("ubicacion")
                .prefetch_related("compra_detalles"),
                id=entrada_id,
            )
            if (
                ubicaciones_permitidas is not None
                and entrada.ubicacion_id not in ubicaciones_permitidas
            ):
                raise PermissionDenied("No puede recibir compras de esta ubicación")
            if not entrada.fecha_llegada_bodega:
                raise PermissionDenied(
                    "Primero debe marcar la compra como en bodega"
                )

            ubicacion_destino = entrada.ubicacion

            detalles = entrada.compra_detalles.all()

            for p in productos:

                producto_id = p.get("ProductoId")

                cantidad = Decimal(
                    str(p.get("Cantidad", 0))
                )

                fvencimiento = p.get("Fvencimiento")

                if cantidad <= 0:
                    continue

                detalle = detalles.filter(
                    producto_id=producto_id
                ).first()

                if not detalle:
                    continue

                autorizado_actual = (
                    HAutorizarCompra.objects
                    .filter(
                        compra_id=entrada.id,
                        producto_id=producto_id,
                    )
                    .aggregate(
                        total=Sum("cantidad_autorizada")
                    )["total"]
                    or Decimal("0")
                )

                devuelto_actual = DevolucionCompraDetalle.objects.filter(
                    compra_id=entrada.id,
                    producto_id=producto_id,
                    devolucion_compra__estado__in=ESTADOS_DEVOLUCION_ACTIVA,
                ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

                pendiente = detalle.cantidad - autorizado_actual - devuelto_actual

                if cantidad > pendiente:

                    return JsonResponse(
                        {
                            "success": False,
                            "message":
                                f"Excede cantidad pendiente producto {producto_id}",
                        },
                        status=400,
                    )

                producto = (
                    Productos.objects
                    .filter(
                        id=producto_id,
                        is_delete=False,
                    )
                    .first()
                )

                if not producto:

                    return JsonResponse(
                        {
                            "success": False,
                            "message":
                                f"Producto {producto_id} no existe",
                        },
                        status=400,
                    )

                fecha_vencimiento = (
                    parse_datetime(fvencimiento)
                    if fvencimiento
                    else None
                )

                # =====================================================
                # REGISTRAR AUTORIZACION
                # =====================================================

                HAutorizarCompra.objects.create(
                    compra_id=entrada.id,
                    producto_id=producto_id,
                    cantidad_comprada=detalle.cantidad,
                    cantidad_autorizada=cantidad,
                    fvencimiento=fecha_vencimiento,
                    u_creo_id=request.user.id,
                )

                # =====================================================
                # PRODUCTO + RELACIONES
                # =====================================================

                productos_inventario = obtener_productos_relacionados(
                    producto, cantidad
                )

                # =====================================================
                # CREAR INVENTARIO
                # =====================================================

                for item in productos_inventario:

                    producto_inventario = item["producto"]
                    cantidad_inventario = item["cantidad"]

                    stock_anterior = (
                        Inventarios.objects
                        .filter(
                            producto=producto_inventario,
                            ubicacion=ubicacion_destino,
                        )
                        .aggregate(
                            total=Sum("cantidad")
                        )["total"]
                        or Decimal("0")
                    )

                    stock_resultante = (
                        stock_anterior
                        + cantidad_inventario
                    )

                    Inventarios.objects.create(
                        producto=producto_inventario,
                        ubicacion=ubicacion_destino,
                        compra=entrada,
                        cantidad=cantidad_inventario,
                        fvencimiento=fecha_vencimiento,
                        u_creo_id=request.user.id,
                    )

                    MovimientoInventario.objects.create(
                        tipo_movimiento=TipoMovimientoInventario.ENTRADA_COMPRA,
                        producto=producto_inventario,
                        ubicacion_destino=ubicacion_destino,
                        cantidad=cantidad_inventario,
                        stock_anterior=stock_anterior,
                        stock_resultante=stock_resultante,
                        compra_id=entrada.id,
                    )

            actualizar_estado_recepcion_compra(entrada)
                
        # =====================================================
        # TRASLADO
        # =====================================================
        elif tipo == "TRASLADO":

            entrada = get_object_or_404(
                Traslados.objects.select_related(
                    "ubicacion_origen",
                    "ubicacion_destino",
                ),
                id=entrada_id,
            )
            if (
                ubicaciones_permitidas is not None
                and entrada.ubicacion_destino_id not in ubicaciones_permitidas
            ):
                raise PermissionDenied("No puede recibir traslados de esta ubicación")

            origen = entrada.ubicacion_origen
            destino = entrada.ubicacion_destino

            detalles = DetalleTraslado.objects.filter(
                traslado_id=entrada.id
            )

            for p in productos:

                producto_id = p.get("ProductoId")

                cantidad = Decimal(
                    str(p.get("Cantidad", 0))
                )

                fvencimiento = p.get("Fvencimiento")

                if cantidad <= 0:
                    continue

                detalle = detalles.filter(
                    producto_id=producto_id
                ).first()

                if not detalle:
                    return JsonResponse(
                        {
                            "success": False,
                            "message":
                                f"No existe detalle de traslado para el producto {producto_id}",
                        },
                        status=400,
                    )

                # =====================================================
                # VALIDAR CANTIDAD PENDIENTE DEL TRASLADO
                # =====================================================

                cantidad_ya_entregada = (
                    detalle.cantidad_entregada
                    or Decimal("0")
                )

                cantidad_pendiente = (
                    detalle.cantidad_solicitada
                    - cantidad_ya_entregada
                )

                if cantidad > cantidad_pendiente:

                    return JsonResponse(
                        {
                            "success": False,
                            "message":
                                f"La cantidad autorizada excede la cantidad pendiente "
                                f"para {detalle.producto.nombre}. "
                                f"Pendiente: {cantidad_pendiente}",
                        },
                        status=400,
                    )

                # =====================================================
                # PRODUCTO PRINCIPAL + RELACIONES
                # =====================================================

                producto = Productos.objects.get(
                    id=producto_id,
                    is_delete=False,
                )

                productos_transferir = (
                    obtener_productos_relacionados(
                        producto,
                        cantidad,
                    )
                )

                # =====================================================
                # PROCESAR CADA PRODUCTO / RELACIÓN
                # =====================================================

                for item in productos_transferir:

                    producto_transferir = item["producto"]

                    cantidad_transferir = Decimal(
                        str(item["cantidad"])
                    )

                    if cantidad_transferir <= 0:
                        continue

                    # =================================================
                    # RESERVA DEL PRODUCTO
                    # =================================================

                    reserva = (
                        ReservaInventario.objects
                        .select_for_update()
                        .filter(
                            producto=producto_transferir,
                            ubicacion=origen,
                            traslado=entrada,
                            estado=ReservaInventario.Estado.RESERVADA,
                            is_delete=False,
                            cantidad__gt=0,
                        )
                        .order_by("f_creacion")
                        .first()
                    )

                    if not reserva:

                        return JsonResponse(
                            {
                                "success": False,
                                "message":
                                    f"No existe una reserva activa para "
                                    f"{producto_transferir.nombre} "
                                    f"en {origen.nombre}",
                            },
                            status=400,
                        )

                    # =================================================
                    # VALIDAR QUE LA RESERVA ALCANCE
                    # =================================================

                    if reserva.cantidad < cantidad_transferir:

                        return JsonResponse(
                            {
                                "success": False,
                                "message":
                                    f"La reserva de {producto_transferir.nombre} "
                                    f"no es suficiente. "
                                    f"Reservada: {reserva.cantidad}, "
                                    f"solicitada: {cantidad_transferir}",
                            },
                            status=400,
                        )

                    # =================================================
                    # BUSCAR INVENTARIO DE ORIGEN FIFO
                    # =================================================

                    capas_origen = (
                        Inventarios.objects
                        .select_for_update()
                        .filter(
                            producto=producto_transferir,
                            ubicacion=origen,
                            is_delete=False,
                            cantidad__gt=0,
                        )
                        .order_by("f_creacion")
                    )

                    stock_total = (
                        capas_origen.aggregate(
                            total=Sum("cantidad")
                        )["total"]
                        or Decimal("0")
                    )

                    if stock_total < cantidad_transferir:

                        return JsonResponse(
                            {
                                "success": False,
                                "message":
                                    f"El inventario físico de "
                                    f"{producto_transferir.nombre} "
                                    f"no es suficiente. "
                                    f"Disponible: {stock_total}, "
                                    f"necesario: {cantidad_transferir}",
                            },
                            status=400,
                        )

                    # =================================================
                    # TRANSFERIR FIFO
                    # =================================================

                    restante = cantidad_transferir

                    for capa in capas_origen:

                        if restante <= 0:
                            break

                        stock_anterior_origen = Decimal(
                            str(capa.cantidad)
                        )

                        consumir = min(
                            stock_anterior_origen,
                            restante,
                        )

                        # =============================================
                        # COSTO DEL LOTE
                        # =============================================

                        costo_unitario = Decimal("0")

                        if capa.compra_id:

                            detalle_compra = (
                                DetalleCompra.objects
                                .filter(
                                    compra_id=capa.compra_id,
                                    producto_id=producto_transferir.id,
                                )
                                .first()
                            )

                            if detalle_compra:
                                costo_unitario = (
                                    detalle_compra.precio_compra
                                )

                        # =============================================
                        # DESCONTAR ORIGEN
                        # =============================================

                        capa.cantidad -= consumir

                        stock_resultante_origen = (
                            capa.cantidad
                        )

                        capa.save(
                            update_fields=["cantidad"]
                        )

                        # =============================================
                        # MOVIMIENTO SALIDA
                        # =============================================

                        MovimientoInventario.objects.create(
                            tipo_movimiento=
                                TipoMovimientoInventario.TRASLADO_SALIDA,

                            producto=producto_transferir,

                            ubicacion_origen=origen,
                            ubicacion_destino=destino,

                            cantidad=consumir,

                            stock_anterior=
                                stock_anterior_origen,

                            stock_resultante=
                                stock_resultante_origen,

                            traslado=entrada,
                        )

                        # =============================================
                        # CREAR INVENTARIO EN DESTINO
                        # =============================================

                        stock_anterior_destino = (
                            Inventarios.objects
                            .filter(
                                producto=producto_transferir,
                                ubicacion=destino,
                                is_delete=False,
                            )
                            .aggregate(
                                total=Sum("cantidad")
                            )["total"]
                            or Decimal("0")
                        )

                        stock_resultante_destino = (
                            stock_anterior_destino
                            + consumir
                        )

                        Inventarios.objects.create(
                            producto=producto_transferir,
                            ubicacion=destino,
                            cantidad=consumir,
                            compra=capa.compra,
                            fvencimiento=(
                                capa.fvencimiento
                                if capa.fvencimiento
                                else (
                                    parse_datetime(fvencimiento)
                                    if fvencimiento
                                    else None
                                )
                            ),
                            u_creo_id=request.user.id,
                        )

                        # =============================================
                        # MOVIMIENTO ENTRADA
                        # =============================================

                        MovimientoInventario.objects.create(
                            tipo_movimiento=
                                TipoMovimientoInventario.TRASLADO_ENTRADA,

                            producto=producto_transferir,

                            ubicacion_origen=origen,
                            ubicacion_destino=destino,

                            cantidad=consumir,

                            stock_anterior=
                                stock_anterior_destino,

                            stock_resultante=
                                stock_resultante_destino,

                            traslado=entrada,
                        )

                        restante -= consumir

                    # =================================================
                    # CONSUMIR RESERVA
                    # =================================================

                    reserva.cantidad -= cantidad_transferir

                    if reserva.cantidad <= 0:

                        reserva.cantidad = Decimal("0")

                        reserva.estado = (
                            ReservaInventario.Estado.CONSUMIDA
                        )

                    reserva.save(
                        update_fields=[
                            "cantidad",
                            "estado",
                        ]
                    )

                # =====================================================
                # ACTUALIZAR CANTIDAD ENTREGADA
                # =====================================================

                detalle.cantidad_entregada = (
                    cantidad_ya_entregada
                    + cantidad
                )

                detalle.save(
                    update_fields=[
                        "cantidad_entregada"
                    ]
                )

            # =========================================================
            # AUTORIZACIÓN
            # =========================================================

            entrada.autorizado_por = request.user
            entrada.fecha_autorizacion = timezone.now()

            # =========================================================
            # DETERMINAR ESTADO
            # =========================================================

            detalles_refresh = (
                DetalleTraslado.objects
                .filter(
                    traslado_id=entrada.id
                )
            )

            completado = all(
                (
                    d.cantidad_entregada
                    or Decimal("0")
                )
                >= d.cantidad_solicitada
                for d in detalles_refresh
            )

            if completado:

                entrada.estado = Estados.COMPLETADO

            else:

                entrada.estado = Estados.PENDIENTE

            entrada.save()

        else:
            return JsonResponse(
                {"success": False, "message": "Tipo inválido"}, status=400
            )

        return JsonResponse(
            {"success": True, "message": "Inventario procesado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@csrf_exempt
@transaction.atomic
@login_required
@permission_required("manager.add_devolucioncompra", raise_exception=True)
def post_devolucion_compra(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        data = json.loads(request.body)

        compra_id = data.get("CompraId")
        observaciones = data.get("Observaciones", "").strip()
        productos = data.get("Productos", [])

        if not compra_id:
            raise Exception("Compra no recibida")

        if not productos:
            raise Exception("No hay productos para devolución")

        # =========================
        # COMPRA
        # =========================
        compra = get_object_or_404(
            Compras.objects.select_related("ubicacion", "proveedor").prefetch_related(
                "compra_detalles", "compra_devoluciones"
            ),
            id=compra_id,
        )
        ubicaciones_permitidas = _ubicaciones_recepcion_usuario(request.user)
        if (
            ubicaciones_permitidas is not None
            and compra.ubicacion_id not in ubicaciones_permitidas
        ):
            raise PermissionDenied("No puede devolver compras de esta ubicación")

        productos_validados = []

        # =========================
        # VALIDACIÓN DE PRODUCTOS
        # =========================
        for p in productos:
            producto_id = p.get("ProductoId")
            cantidad_raw = p.get("Cantidad", 0)
            producto_hijo_id = p.get("ProductoHijoId")
            cantidad_hijo_raw = p.get("CantidadHijo")
            motivo_raw = p.get("Motivo")

            try:
                cantidad = Decimal(str(cantidad_raw or 0))
            except:
                raise Exception(f"Cantidad inválida para producto {producto_id}")

            if motivo_raw in [None, ""]:
                raise Exception(f"Debe indicar motivo para producto {producto_id}")

            motivo = int(motivo_raw)

            detalle_compra = compra.compra_detalles.filter(
                producto_id=producto_id
            ).first()

            if not detalle_compra:
                raise Exception(f"Producto {producto_id} no pertenece a esta compra")

            producto_hijo = None
            cantidad_hijo = None
            if producto_hijo_id:
                relacion = ProductosRel.objects.select_related(
                    "producto_master", "producto_relacionado"
                ).filter(
                    producto_master_id=producto_id,
                    producto_relacionado_id=producto_hijo_id,
                    is_active=True,
                    is_delete=False,
                ).first()
                if not relacion:
                    raise Exception("El producto hijo no pertenece a la presentación comprada")
                try:
                    cantidad_hijo = Decimal(str(cantidad_hijo_raw or 0))
                except (InvalidOperation, TypeError, ValueError):
                    raise Exception("La cantidad de unidades a devolver no es válida")
                if cantidad_hijo <= 0:
                    raise Exception("La cantidad de unidades a devolver debe ser mayor que cero")
                producto_hijo = relacion.producto_relacionado
                equivalencia_padre = Decimal(relacion.producto_master.equival_unid or 1)
                equivalencia_hijo = Decimal(producto_hijo.equival_unid or 1)
                cantidad = (cantidad_hijo * equivalencia_hijo / equivalencia_padre).quantize(
                    Decimal("0.000001")
                )

            if cantidad <= 0:
                continue

            cantidad_comprada = detalle_compra.cantidad
            cantidad_recibida = HAutorizarCompra.objects.filter(
                compra_id=compra.id,
                producto_id=producto_id,
            ).aggregate(total=Sum("cantidad_autorizada"))["total"] or Decimal("0")

            # =========================
            # DEVOLUCIONES ACTIVAS (IMPORTANTE)
            # SOLO PENDIENTES Y APROBADAS
            # =========================
            cantidad_devuelta = DevolucionCompraDetalle.objects.filter(
                compra_id=compra.id,
                producto_id=producto_id,
                devolucion_compra__estado__in=ESTADOS_DEVOLUCION_ACTIVA,
            ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

            disponible = cantidad_comprada - cantidad_recibida - cantidad_devuelta

            if cantidad > disponible:
                raise Exception(
                    f"La cantidad a devolver del producto {producto_id} excede lo disponible. "
                    f"Disponible: {disponible}"
                )

            # Al devolver una unidad hija se convierte toda la presentación
            # pendiente: las unidades no devueltas se reciben de inmediato.
            cantidad_a_confirmar = (
                disponible - cantidad if producto_hijo else Decimal("0")
            )

            productos_validados.append(
                {
                    "producto_id": producto_id,
                    "producto_padre": detalle_compra.producto,
                    "detalle_compra": detalle_compra,
                    "cantidad": cantidad,
                    "motivo": motivo,
                    "producto_hijo_id": producto_hijo.id if producto_hijo else None,
                    "cantidad_hijo": cantidad_hijo,
                    "cantidad_a_confirmar": cantidad_a_confirmar,
                }
            )

        if not productos_validados:
            raise Exception("No hay productos válidos para devolución")

        # =========================
        # CREAR DEVOLUCIÓN
        # =========================
        devolucion = DevolucionCompra.objects.create(
            compra=compra,
            observaciones=observaciones,
            estado=EstadoDevolucionCompra.PENDIENTE,
            u_creo_id=request.user.id,
        )

        # =========================
        # DETALLES
        # =========================
        for item in productos_validados:
            DevolucionCompraDetalle.objects.create(
                devolucion_compra=devolucion,
                compra=compra,
                producto_id=item["producto_id"],
                cantidad=item["cantidad"],
                motivo=item["motivo"],
                producto_hijo_id=item["producto_hijo_id"],
                cantidad_hijo=item["cantidad_hijo"],
            )

        # Las unidades restantes de una presentación convertida ingresan en la
        # misma transacción. Ej.: caja de 12, devolución de 2 = recepción de 10.
        for item in productos_validados:
            cantidad_a_confirmar = item["cantidad_a_confirmar"]
            if cantidad_a_confirmar <= 0:
                continue

            HAutorizarCompra.objects.create(
                compra=compra,
                producto_id=item["producto_id"],
                cantidad_comprada=item["detalle_compra"].cantidad,
                cantidad_autorizada=cantidad_a_confirmar,
                fvencimiento=None,
                u_creo_id=request.user.id,
            )

            for inventario_item in obtener_productos_relacionados(
                item["producto_padre"], cantidad_a_confirmar
            ):
                producto_inventario = inventario_item["producto"]
                cantidad_inventario = inventario_item["cantidad"]
                stock_anterior = (
                    Inventarios.objects.filter(
                        producto=producto_inventario,
                        ubicacion=compra.ubicacion,
                    ).aggregate(total=Sum("cantidad"))["total"]
                    or Decimal("0")
                )
                stock_resultante = stock_anterior + cantidad_inventario

                Inventarios.objects.create(
                    producto=producto_inventario,
                    ubicacion=compra.ubicacion,
                    compra=compra,
                    cantidad=cantidad_inventario,
                    fvencimiento=None,
                    u_creo_id=request.user.id,
                )
                MovimientoInventario.objects.create(
                    tipo_movimiento=TipoMovimientoInventario.ENTRADA_COMPRA,
                    producto=producto_inventario,
                    ubicacion_destino=compra.ubicacion,
                    cantidad=cantidad_inventario,
                    stock_anterior=stock_anterior,
                    stock_resultante=stock_resultante,
                    compra_id=compra.id,
                )

        actualizar_estado_recepcion_compra(compra)

        # =========================
        # RECARGAR DEVOLUCIÓN
        # =========================
        devolucion = (
            DevolucionCompra.objects.select_related("compra__proveedor")
            .prefetch_related("devolucion_detalles__producto")
            .get(id=devolucion.id)
        )

        # =========================
        # PDF
        # =========================
        pdf = generar_pdf_devolucion(devolucion)

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="DevolucionCompra_{devolucion.id}.pdf"'
        )

        return response

    except Exception as e:
        traceback.print_exc()
        transaction.set_rollback(True)

        return JsonResponse({"success": False, "message": str(e)}, status=500)


# ─────────────────────────────────────────────────────────────
# GENERADOR PDF DEVOLUCION DJANGO
# ─────────────────────────────────────────────────────────────
def generar_pdf_devolucion(devolucion, logo_path=None):
    if logo_path is None:
        logo_path = _logo_empresa_pdf()
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # ============================================
    # LOGO MISMA POSICIÓN QUE COMPRA
    # ============================================
    try:
        c.drawImage(
            logo_path,
            width - 120,
            height - 60,
            width=80,
            height=40,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception:
        pass

    # ============================================
    # TITULO
    # ============================================
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "DEVOLUCIÓN DE COMPRA")

    c.setFont("Helvetica", 11)

    y = height - 80
    line_height = 18

    fecha = _fecha_honduras(devolucion.f_creacion).strftime("%d/%m/%Y %H:%M")

    proveedor_nombre = getattr(
        devolucion.compra.proveedor, "nombre_legal", None
    ) or getattr(devolucion.compra.proveedor, "nombre_comercial", "N/A")

    total_productos = devolucion.devolucion_detalles.count()

    # Encabezado
    c.drawString(50, y, f"Devolución ID: {devolucion.id}")
    c.drawString(50, y - line_height, f"Compra ID: {devolucion.compra.id}")
    c.drawString(50, y - 2 * line_height, f"Proveedor: {proveedor_nombre}")
    c.drawString(
        50, y - 3 * line_height, f"Observaciones: {str(devolucion.observaciones)[:40]}"
    )

    c.drawString(300, y, f"Fecha: {fecha}")
    c.drawString(300, y - line_height, f"Estado: {devolucion.estado}")
    c.drawString(300, y - 2 * line_height, f"Total Productos: {total_productos}")
    if devolucion.resolucion:
        resolucion_texto = dict(DevolucionCompra.RESOLUCION_OPCIONES).get(
            devolucion.resolucion, devolucion.resolucion
        )
        c.drawString(300, y - 3 * line_height, f"Resolución: {resolucion_texto}")
        if devolucion.resolucion == DevolucionCompra.RESOLUCION_SALDO_FAVOR:
            c.drawString(
                300,
                y - 4 * line_height,
                f"Saldo a favor: L. {devolucion.monto_resolucion:.2f}",
            )

    # Línea
    lineas_resolucion = 2 if devolucion.resolucion == DevolucionCompra.RESOLUCION_SALDO_FAVOR else (1 if devolucion.resolucion else 0)
    y_sep = y - (4 + lineas_resolucion) * line_height - 5
    c.line(50, y_sep, width - 50, y_sep)

    # ============================================
    # TABLA
    # ============================================
    y_table = y_sep - 20

    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y_table, "Producto")
    c.drawString(250, y_table, "SKU")
    c.drawString(330, y_table, "Cantidad")
    c.drawString(400, y_table, "Motivo")

    y_table -= 15
    c.setFont("Helvetica", 10)

    motivos_dict = {
        0: "Producto Dañado",  # Compatibilidad con devoluciones anteriores.
        1: "Producto Dañado",
        2: "Producto Vencido",
        3: "Error de Pedido",
        4: "Producto Incorrecto",
        5: "Exceso Inventario",
        6: "Otro",
    }

    for item in devolucion.devolucion_detalles.select_related("producto", "producto_hijo").all():
        producto_devolucion = item.producto_hijo or item.producto
        producto_nombre = str(producto_devolucion.nombre)[:28]
        sku = str(producto_devolucion.codigo_sku)
        cantidad = f"{item.cantidad_hijo} und." if item.producto_hijo_id else str(item.cantidad)
        motivo = motivos_dict.get(item.motivo, "N/A")

        c.drawString(50, y_table, producto_nombre)
        c.drawString(250, y_table, sku)
        c.drawRightString(360, y_table, cantidad)
        c.drawString(400, y_table, motivo)

        y_table -= 15

        if y_table < 120:
            c.showPage()
            y_table = height - 50

            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y_table, "Producto")
            c.drawString(250, y_table, "SKU")
            c.drawString(330, y_table, "Cantidad")
            c.drawString(400, y_table, "Motivo")

            y_table -= 15
            c.setFont("Helvetica", 10)

    # ============================================
    # RESPONSABLES
    # ============================================
    usuario_compra = User.objects.filter(id=devolucion.compra.u_creo_id).first()
    usuario_devolucion = User.objects.filter(id=devolucion.u_creo_id).first()

    responsable_compra = usuario_compra.username if usuario_compra else "Sistema"
    responsable_devolucion = (
        usuario_devolucion.username if usuario_devolucion else "Sistema"
    )

    y_sign = 80

    c.line(100, y_sign, 250, y_sign)
    c.drawString(100, y_sign - 15, f"Responsable Compra: {responsable_compra}")

    c.line(350, y_sign, 500, y_sign)
    c.drawString(350, y_sign - 15, f"Responsable Devolución: {responsable_devolucion}")

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


# ─────────────────────────────────────────────────────────────
# INVENTARIOS
# ─────────────────────────────────────────────────────────────
@login_required
@permission_required("manager.view_inventarios", raise_exception=True)
def inventario_view(request):

    search = request.GET.get("search", "").strip()

    productos_qs = (
        Productos.objects.select_related(
            "unidad_medida",
            "marca",
            "categoria",
        )
        .prefetch_related(
            "imagenes_producto" 
        )
        .filter(is_active=True, is_delete=False)
    )

    if search:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=search)
            | Q(codigo_sku__icontains=search)
            | Q(marca__nombre__icontains=search)
        )

    paginator = Paginator(productos_qs.order_by("nombre", "id"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    descuentos = Descuento.objects.filter(
        is_active=True,
        is_delete=False,
        es_cupon=False,
    ).select_related("productos", "categorias")

    productos_list = []

    for p in page_obj:
        precio_original = Decimal(p.precio_venta)
        precio_final = precio_original

        descuento_producto = None
        descuento_categoria = None

        for d in descuentos:
            if not d.vigente():
                continue

            if d.aplicar_productos and d.productos_id and d.productos_id == p.id:
                descuento_producto = d

            if (
                d.aplicar_categorias
                and d.categorias_id
                and d.categorias_id == p.categoria_id
            ):
                descuento_categoria = d

        descuentos_aplicados = []

        if descuento_producto:
            descuentos_aplicados.append(descuento_producto)

            if descuento_producto.acumulable and descuento_categoria:
                descuentos_aplicados.append(descuento_categoria)

        elif descuento_categoria:
            descuentos_aplicados.append(descuento_categoria)

        total_descuento = Decimal("0.00")

        for d in descuentos_aplicados:
            if d.es_porcentaje:
                descuento = (precio_original * Decimal(d.valor)) / Decimal("100")
            else:
                descuento = Decimal(d.valor)

            total_descuento += descuento

        precio_final = precio_original - total_descuento

        if precio_final < 0:
            precio_final = Decimal("0.00")

        # ==========================================
        # IMAGEN (NUEVA TABLA CORREGIDA)
        # ==========================================

        imagen_obj = p.imagenes_producto.all().first()

        imagen_url = (
            request.build_absolute_uri(
                reverse("producto_imagen", args=[imagen_obj.id])
            )
            if imagen_obj and imagen_obj.imagen_archivo
            else "/static/img/default.webp"
        )

        productos_list.append(
            {
                "id": p.id,
                "nombre": p.nombre,
                "unidadMedida": {
                    "abreviatura": getattr(
                        p.unidad_medida,
                        "abreviatura",
                        "N/A",
                    )
                },
                "marcas": {
                    "nombre": getattr(
                        p.marca,
                        "nombre",
                        "N/A",
                    )
                },
                "codigoSKU": p.codigo_sku,
                # PRECIOS
                "precioVenta": float(precio_original),
                "precioFinal": float(precio_final),
                # DESCUENTOS
                "tieneDescuento": len(descuentos_aplicados) > 0,
                "descuentos": [
                    {
                        "nombre": d.nombre,
                        "valor": float(d.valor),
                        "es_porcentaje": d.es_porcentaje,
                    }
                    for d in descuentos_aplicados
                ],
                # IMAGEN CORREGIDA
                "imagenUrl": imagen_url,
            }
        )

    ubicaciones = Ubicaciones.objects.filter(is_delete=False).order_by("nombre")

    return render(
        request,
        "inventario/inventario.html",
        {
            "productos": productos_list,
            "ubicaciones": ubicaciones,
            "page": page_obj.number,
            "total_pages": paginator.num_pages,
            "page_range": paginator.page_range,
            "search": search,
            "mostrar_buscador": True,
            "mostrar_exportar_inventario": True,
        },
    )


@login_required
@permission_required("manager.view_inventarios", raise_exception=True)
def exportar_inventario_excel(request):
    """Exporta las existencias agrupadas de todas las ubicaciones activas."""
    search = request.GET.get("search", "").strip()

    productos = (
        Productos.objects.select_related("categoria", "unidad_medida", "marca")
        .filter(is_active=True, is_delete=False)
        .prefetch_related(
            Prefetch(
                "producto_master_rel",
                queryset=ProductosRel.objects.select_related(
                    "producto_master", "producto_relacionado"
                ),
                to_attr="relaciones_como_master",
            ),
            Prefetch(
                "producto_relacionado_rel",
                queryset=ProductosRel.objects.select_related(
                    "producto_master", "producto_relacionado"
                ),
                to_attr="relaciones_como_relacionado",
            ),
            Prefetch(
                "producto_compra_detalles",
                queryset=(
                    DetalleCompra.objects.filter(
                        is_delete=False,
                        compra__is_delete=False,
                    )
                    .select_related("compra__proveedor")
                    .order_by("-compra__fecha_compra")
                ),
                to_attr="compras_producto",
            ),
        )
    )

    if search:
        productos = productos.filter(
            Q(nombre__icontains=search)
            | Q(codigo_sku__icontains=search)
            | Q(marca__nombre__icontains=search)
        )

    productos = list(productos.order_by("nombre"))
    existencias = dict(
        Inventarios.objects.filter(
            producto_id__in=[producto.id for producto in productos],
            is_delete=False,
        )
        .values("producto_id")
        .annotate(total=Sum("cantidad"))
        .values_list("producto_id", "total")
    )
    fechas_vencimiento = {}
    for producto_id, fecha in (
        Inventarios.objects.filter(
            producto_id__in=[producto.id for producto in productos],
            is_delete=False,
            cantidad__gt=0,
            fvencimiento__isnull=False,
        )
        .order_by("producto_id", "fvencimiento")
        .values_list("producto_id", "fvencimiento")
    ):
        fecha_formateada = _fecha_honduras(fecha).strftime("%d/%m/%Y")
        fechas_producto = fechas_vencimiento.setdefault(producto_id, [])
        if fecha_formateada not in fechas_producto:
            fechas_producto.append(fecha_formateada)

    encabezados = [
        "ID producto",
        "Producto",
        "Categoría",
        "Marca",
        "Presentación",
        "SKU",
        "Proveedor",
        "Existencia mayor",
        "Existencia menor",
        "Equivalencia menor",
        "Equivalencia mayor",
        "Es padre",
        "Fechas de vencimiento",
    ]
    libro, hoja = _libro_exportacion_grande(
        "Inventario",
        encabezados,
        [14, 36, 22, 20, 20, 22, 28, 18, 18, 18, 18, 14, 30],
    )

    for producto in productos:
        existencia = existencias.get(producto.id) or Decimal("0")
        equivalencia_menor, equivalencia_mayor = _obtener_equivalencias_producto(
            producto
        )
        unidades_menores = existencia * Decimal(producto.equival_unid or 1)
        existencia = existencia.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        unidades_menores = unidades_menores.quantize(
            Decimal("0.01"), rounding=ROUND_DOWN
        )

        # El Excel recibe enteros como enteros; los decimales se truncaron arriba
        # para no convertir, por ejemplo, 6.968 en 6.97.
        if existencia == existencia.to_integral_value():
            existencia = int(existencia)
        if unidades_menores == unidades_menores.to_integral_value():
            unidades_menores = int(unidades_menores)

        _agregar_fila_exportacion(
            hoja,
            [
                producto.id,
                producto.nombre,
                producto.categoria.nombre,
                producto.marca.nombre,
                producto.unidad_medida.nombre,
                producto.codigo_sku,
                _obtener_proveedor_producto(producto),
                existencia,
                unidades_menores,
                equivalencia_menor,
                equivalencia_mayor,
                "Sí" if producto.is_master else "No",
                ", ".join(fechas_vencimiento.get(producto.id, [])),
            ],
            formatos={
                8: "#,##0" if isinstance(existencia, int) else "#,##0.00",
                9: "#,##0" if isinstance(unidades_menores, int) else "#,##0.00",
                10: "#,##0",
                11: "#,##0",
            },
        )
    return _respuesta_excel(libro, "inventario.xlsx")


@login_required
@permission_required("manager.view_inventarios", raise_exception=True)
def get_inventario_producto(request, id):
    try:
        producto = get_object_or_404(
            Productos.objects.select_related(
                "marca"
            ).prefetch_related(
                "imagenes_producto"
            ),
            id=id,
            is_delete=False,
        )

        # ==========================================
        # INVENTARIO FÍSICO POR UBICACIÓN
        # ==========================================

        inventarios = (
            Inventarios.objects.select_related(
                "ubicacion"
            )
            .filter(
                producto_id=id,
                is_delete=False,
                cantidad__gt=0,
            )
            .values(
                "ubicacion__id",
                "ubicacion__nombre",
            )
            .annotate(
                total_cantidad=Sum("cantidad")
            )
            .order_by(
                "ubicacion__nombre"
            )
        )

        inventario_list = []

        for inv in inventarios:

            ubicacion_id = inv["ubicacion__id"]

            # ==========================================
            # STOCK FÍSICO
            # ==========================================

            stock_fisico = Decimal(
                str(
                    inv["total_cantidad"] or 0
                )
            )

            # ==========================================
            # STOCK RESERVADO
            #
            # Solo tomamos reservas:
            #
            #   estado = RESERVADA
            #
            # Y de esta ubicación específicamente.
            # ==========================================

            reservado = (
                ReservaInventario.objects
                .filter(
                    producto_id=id,
                    ubicacion_id=ubicacion_id,
                    estado=ReservaInventario.Estado.RESERVADA,
                    is_delete=False,
                )
                .aggregate(
                    total=Sum("cantidad")
                )["total"]
                or Decimal("0.00")
            )

            reservado = Decimal(
                str(reservado)
            )

            # ==========================================
            # STOCK DISPONIBLE
            # ==========================================

            stock_disponible = stock_fisico - reservado

            if stock_disponible < 0:
                stock_disponible = Decimal(
                    "0.00"
                )

            # ==========================================
            # AGREGAR RESULTADO
            # ==========================================

            inventario_list.append(
                {
                    "ubicacion": inv[
                        "ubicacion__nombre"
                    ],
                    "cantidad": float(
                        _stock_para_mostrar(stock_disponible)
                    ),
                }
            )

        # ==========================================
        # IMAGEN DESDE NEXTCLOUD
        # ==========================================

        imagen = (
            producto.imagenes_producto.first()
        )

        tiene_imagen = bool(imagen and imagen.imagen_archivo)

        if tiene_imagen:
            imagen_url = request.build_absolute_uri(
                reverse(
                    "producto_imagen",
                    args=[imagen.id],
                )
            )
        else:
            imagen_url = "/static/img/default.webp"

        # ==========================================
        # RESPUESTA
        # ==========================================

        return JsonResponse(
            {
                "producto": {
                    "id": producto.id,
                    "nombre": producto.nombre,
                    "imagenUrl": imagen_url,
                    "tieneImagen": tiene_imagen,
                },
                "inventario": inventario_list,
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "error": str(e)
            },
            status=500,
        )


@login_required
@permission_required("manager.view_devolucioncompra", raise_exception=True)
def devoluciones_view(request):

    search = request.GET.get("search", "").strip()

    query = DevolucionCompra.objects.filter(
        compra__u_creo_id=request.user.id, is_delete=False
    ).select_related("compra", "compra__proveedor", "compra__ubicacion")

    if search:
        query = query.filter(
            Q(id__icontains=search)
            | Q(compra__id__icontains=search)
            | Q(compra__proveedor__nombre_legal__icontains=search)
            | Q(compra__proveedor__nombre_comercial__icontains=search)
            | Q(observaciones__icontains=search)
            | Q(estado__icontains=search)
        )

    paginator = Paginator(query.order_by("-id"), 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "devoluciones/devoluciones.html", context)


@login_required
@permission_required("manager.view_devolucioncompra", raise_exception=True)
def detalle_devolucion_view(request, token):

    devolucion = get_object_or_404(
        DevolucionCompra.objects.select_related(
            "compra", "compra__proveedor", "compra__ubicacion"
        ).prefetch_related(
            "devolucion_detalles__producto",
            "devolucion_detalles__producto_hijo",
        ),
        documento_token=token,
        compra__u_creo_id=request.user.id,
    )

    context = {
        "devolucion": devolucion,
        "detalles": devolucion.devolucion_detalles.all(),
    }

    return render(request, "devoluciones/detalle_devoluciones.html", context)


@login_required
@permission_required("manager.change_devolucioncompra", raise_exception=True)
@transaction.atomic
def aprobar_devolucion_view(request, token):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        data = json.loads(request.body or "{}")
        resolucion = data.get("resolucion")
        resoluciones_validas = {
            DevolucionCompra.RESOLUCION_CAMBIO,
            DevolucionCompra.RESOLUCION_SALDO_FAVOR,
        }
        if resolucion not in resoluciones_validas:
            return JsonResponse(
                {"success": False, "message": "Debe seleccionar una resolución válida"},
                status=400,
            )

        devolucion = get_object_or_404(
            DevolucionCompra.objects.select_related(
                "compra__proveedor", "compra__ubicacion"
            ).prefetch_related(
                "compra__compra_detalles",
                "devolucion_detalles__producto",
                "devolucion_detalles__producto_hijo",
            ),
            documento_token=token,
        )

        if devolucion.estado != EstadoDevolucionCompra.PENDIENTE:
            return JsonResponse(
                {"success": False, "message": "La devolución ya fue procesada"},
                status=400,
            )

        detalles_compra = {
            detalle.producto_id: detalle
            for detalle in devolucion.compra.compra_detalles.all()
        }
        productos_resolucion = []
        monto_resolucion = Decimal("0")

        for detalle_devolucion in devolucion.devolucion_detalles.all():
            detalle_compra = detalles_compra.get(detalle_devolucion.producto_id)
            if not detalle_compra:
                raise Exception("No se encontró el costo original del producto devuelto")

            producto_resolucion = detalle_devolucion.producto_hijo or detalle_devolucion.producto
            cantidad_resolucion = (
                detalle_devolucion.cantidad_hijo
                if detalle_devolucion.producto_hijo_id
                else detalle_devolucion.cantidad
            )
            if not cantidad_resolucion or cantidad_resolucion <= 0:
                raise Exception("La devolución contiene una cantidad inválida")

            equivalencia_origen = Decimal(detalle_devolucion.producto.equival_unid or 1)
            equivalencia_producto = Decimal(producto_resolucion.equival_unid or 1)
            costo_unitario_exacto = (
                Decimal(detalle_compra.precio_compra)
                * equivalencia_producto
                / equivalencia_origen
            )
            monto_linea = (costo_unitario_exacto * Decimal(cantidad_resolucion)).quantize(
                Decimal("0.01")
            )
            monto_resolucion += monto_linea
            productos_resolucion.append(
                {
                    "producto": producto_resolucion,
                    "cantidad": cantidad_resolucion,
                    "precio_compra": costo_unitario_exacto.quantize(Decimal("0.01")),
                }
            )

        monto_resolucion = monto_resolucion.quantize(Decimal("0.01"))
        compra_cambio = None
        proveedor = devolucion.compra.proveedor

        if resolucion == DevolucionCompra.RESOLUCION_CAMBIO:
            compra_cambio = Compras.objects.create(
                proveedor=proveedor,
                tipo_compra=devolucion.compra.tipo_compra,
                estado=EstadoCompra.PENDIENTE,
                total=Decimal("0"),
                es_cambio=True,
                observaciones=f"Compra de reposición por devolución #{devolucion.id}",
                ubicacion=devolucion.compra.ubicacion,
                u_creo_id=request.user.id,
            )
            for producto in productos_resolucion:
                DetalleCompra.objects.create(
                    compra=compra_cambio,
                    producto=producto["producto"],
                    cantidad=producto["cantidad"],
                    precio_compra=Decimal("0"),
                    u_creo_id=request.user.id,
                )
        else:
            proveedor.saldo = (proveedor.saldo or Decimal("0")) + monto_resolucion
            proveedor.save(update_fields=["saldo"])

        devolucion.estado = EstadoDevolucionCompra.APROBADA
        devolucion.resolucion = resolucion
        devolucion.monto_resolucion = monto_resolucion
        devolucion.compra_cambio = compra_cambio
        devolucion.u_modifico_id = request.user.id
        devolucion.save(
            update_fields=[
                "estado",
                "resolucion",
                "monto_resolucion",
                "compra_cambio",
                "u_modifico_id",
            ]
        )
        actualizar_estado_recepcion_compra(devolucion.compra)

        pdf = generar_pdf_devolucion(devolucion)

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Devolucion_Aprobada_{devolucion.id}.pdf"'
        )

        return response

    except Exception as e:
        transaction.set_rollback(True)
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.change_devolucioncompra", raise_exception=True)
@transaction.atomic
def rechazar_devolucion_view(request, token):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        data = json.loads(request.body or "{}")
        motivo_rechazo = data.get("motivo", "Sin motivo")

        devolucion = get_object_or_404(DevolucionCompra, documento_token=token)

        if devolucion.estado != EstadoDevolucionCompra.PENDIENTE:
            return JsonResponse(
                {"success": False, "message": "La devolución ya fue procesada"},
                status=400,
            )

        devolucion.estado = EstadoDevolucionCompra.RECHAZADA
        devolucion.observaciones = (
            devolucion.observaciones or ""
        ) + f" | RECHAZO: {motivo_rechazo}"
        devolucion.u_modifico_id = request.user.id
        devolucion.save()
        actualizar_estado_recepcion_compra(devolucion.compra)

        pdf = generar_pdf_devolucion(devolucion)

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Devolucion_Rechazada_{devolucion.id}.pdf"'
        )

        return response

    except Exception as e:
        transaction.set_rollback(True)
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_traslados", raise_exception=True)
def traslados_view(request):
    ubicaciones = Ubicaciones.objects.filter(is_delete=False).order_by("nombre")
    context = {"ubicaciones": ubicaciones}
    return render(request, "traslados/traslados.html", context)


@login_required
@permission_required("manager.view_traslados", raise_exception=True)
def inventario_por_ubicacion(request, ubicacion_id):

    try:
        page = max(1, int(request.GET.get("page", 1)))
        limit = min(20, max(1, int(request.GET.get("limit", 10))))
    except ValueError:
        return JsonResponse({"error": "Paginación inválida"}, status=400)

    search = request.GET.get("search", "").strip()

    imagen_subquery = (
        ProductosImagenes.objects
        .filter(
            producto_id=OuterRef("producto_id"),
            imagen_archivo__isnull=False,
        )
        .exclude(
            imagen_archivo=""
        )
        .values("id")[:1]
    )

    reserva_subquery = (
        ReservaInventario.objects
        .filter(
            producto_id=OuterRef("producto_id"),
            ubicacion_id=ubicacion_id,
            estado=ReservaInventario.Estado.RESERVADA,
            is_active=True,
            is_delete=False,
        )
        .values("producto_id")
        .annotate(total=Sum("cantidad"))
        .values("total")[:1]
    )

    inventario = (
        Inventarios.objects
        .filter(
            ubicacion_id=ubicacion_id,
            cantidad__gt=0,
        )
        .values(
            "producto_id",
            "producto__nombre",
            "producto__codigo_sku",
            "producto__unidad_medida__nombre",
        )
        .annotate(
            total_stock=Sum("cantidad"),
            imagen_id=Subquery(imagen_subquery),
        )
        .annotate(
            total_reservado=Coalesce(
                Subquery(reserva_subquery),
                Value(Decimal("0"), output_field=DecimalField(max_digits=18, decimal_places=4)),
            ),
            stock_disponible=F("total_stock") - F("total_reservado"),
        )
        .filter(stock_disponible__gte=1)
        .order_by("producto__nombre", "producto_id")
    )

    if search:
        inventario = inventario.filter(
            Q(producto__nombre__icontains=search)
            | Q(producto__codigo_sku__icontains=search)
        )

    page_obj = Paginator(inventario, limit).get_page(page)

    data = []

    for item in page_obj:

        stock = float(
            item["stock_disponible"] or 0
        )

        if stock < 1:
            continue

        imagen_url = ""

        if item["imagen_id"]:

            imagen_url = request.build_absolute_uri(
                reverse(
                    "producto_imagen",
                    args=[item["imagen_id"]],
                )
            )

        data.append(
            {
                "producto_id": item["producto_id"],
                "nombre": item["producto__nombre"],
                "sku": item["producto__codigo_sku"],
                "imagen": imagen_url,
                "unidad": item[
                    "producto__unidad_medida__nombre"
                ],
                "stock": stock,
            }
        )

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "totalPages": page_obj.paginator.num_pages,
        "total": page_obj.paginator.count,
    })


@login_required
@permission_required(
    "manager.add_traslados",
    raise_exception=True
)
@require_http_methods(["POST"])
def post_traslado(request):

    try:

        # =====================================================
        # LEER JSON
        # =====================================================

        try:
            data = json.loads(request.body)

        except Exception:
            return JsonResponse(
                {
                    "success": False,
                    "message": "JSON inválido"
                },
                status=400
            )

        origen_id = data.get("origenId")
        destino_id = data.get("destinoId")
        observaciones = data.get(
            "observaciones",
            ""
        ).strip()

        detalles = data.get(
            "detalles",
            []
        )

        # =====================================================
        # VALIDACIONES GENERALES
        # =====================================================

        if not origen_id or not destino_id:

            return JsonResponse(
                {
                    "success": False,
                    "message":
                        "Debe seleccionar origen y destino"
                },
                status=400
            )

        if origen_id == destino_id:

            return JsonResponse(
                {
                    "success": False,
                    "message":
                        "Origen y destino no pueden ser iguales"
                },
                status=400
            )

        if not detalles:

            return JsonResponse(
                {
                    "success": False,
                    "message":
                        "Debe incluir al menos un producto"
                },
                status=400
            )

        # =====================================================
        # UBICACIONES
        # =====================================================

        origen = (
            Ubicaciones.objects
            .filter(
                id=origen_id,
                is_active=True,
                is_delete=False,
            )
            .first()
        )

        destino = (
            Ubicaciones.objects
            .filter(
                id=destino_id,
                is_active=True,
                is_delete=False,
            )
            .first()
        )

        if not origen or not destino:

            return JsonResponse(
                {
                    "success": False,
                    "message": "Ubicaciones inválidas"
                },
                status=400
            )

        # =====================================================
        # TRANSACCIÓN
        # =====================================================

        with transaction.atomic():

            # =================================================
            # CREAR TRASLADO
            # =================================================

            traslado = Traslados.objects.create(
                solicitado_por_id=request.user.id,
                ubicacion_origen=origen,
                ubicacion_destino=destino,
                observaciones=observaciones,
                estado=Estados.PENDIENTE,
                u_creo_id=request.user.id,
            )

            # =================================================
            # PRODUCTOS DEL TRASLADO
            # =================================================

            for item in detalles:

                producto_id = item.get(
                    "productoId"
                )

                # ---------------------------------------------
                # CANTIDAD
                # ---------------------------------------------

                try:

                    cantidad_solicitada = Decimal(
                        str(
                            item.get(
                                "cantidad",
                                0
                            )
                        )
                    )

                except Exception:

                    raise Exception(
                        "Cantidad inválida"
                    )

                if cantidad_solicitada <= 0:

                    raise Exception(
                        "Cantidad debe ser mayor a 0"
                    )

                if cantidad_solicitada != cantidad_solicitada.to_integral_value():

                    raise Exception(
                        "La cantidad a trasladar debe ser un número entero"
                    )

                # ---------------------------------------------
                # PRODUCTO
                # ---------------------------------------------

                producto = (
                    Productos.objects
                    .filter(
                        id=producto_id,
                        is_active=True,
                        is_delete=False,
                    )
                    .first()
                )

                if not producto:

                    raise Exception(
                        f"Producto {producto_id} no existe"
                    )

                # =================================================
                # OBTENER TODAS LAS RELACIONES
                # =================================================

                productos_relacionados = (
                    obtener_productos_relacionados(
                        producto,
                        cantidad_solicitada
                    )
                )

                # =================================================
                # VALIDAR STOCK DISPONIBLE DE TODO EL GRUPO
                #
                # STOCK DISPONIBLE =
                # STOCK FÍSICO - STOCK RESERVADO
                # =================================================

                for relacion in productos_relacionados:

                    producto_inventario = (
                        relacion["producto"]
                    )

                    cantidad_reservar = (
                        relacion["cantidad"]
                    )

                    # -----------------------------------------
                    # STOCK FÍSICO
                    # -----------------------------------------

                    stock_fisico = (
                        Inventarios.objects
                        .filter(
                            producto=producto_inventario,
                            ubicacion=origen,
                            is_active=True,
                            is_delete=False,
                            cantidad__gt=0,
                        )
                        .aggregate(
                            total=Sum("cantidad")
                        )["total"]
                        or Decimal("0")
                    )

                    # -----------------------------------------
                    # STOCK RESERVADO
                    # -----------------------------------------

                    stock_reservado = (
                        ReservaInventario.objects
                        .filter(
                            producto=producto_inventario,
                            ubicacion=origen,
                            estado=(
                                ReservaInventario
                                .Estado
                                .RESERVADA
                            ),
                            is_active=True,
                            is_delete=False,
                        )
                        .aggregate(
                            total=Sum("cantidad")
                        )["total"]
                        or Decimal("0")
                    )

                    # -----------------------------------------
                    # STOCK DISPONIBLE
                    # -----------------------------------------

                    stock_disponible = (
                        stock_fisico
                        - stock_reservado
                    )

                    # -----------------------------------------
                    # VALIDAR
                    # -----------------------------------------

                    if stock_disponible < cantidad_reservar:

                        raise Exception(
                            f"Stock insuficiente para "
                            f"{producto_inventario.nombre}. "
                            f"Disponible: "
                            f"{stock_disponible}"
                        )

                # =================================================
                # CREAR DETALLE DEL TRASLADO
                #
                # IMPORTANTE:
                # Aquí guardamos solamente lo que el usuario
                # solicitó originalmente.
                # =================================================

                DetalleTraslado.objects.create(
                    traslado=traslado,
                    producto=producto,
                    cantidad_solicitada=cantidad_solicitada,
                    u_creo_id=request.user.id,
                )

                # =================================================
                # CREAR RESERVAS
                #
                # AQUÍ YA NO TOCAMOS INVENTARIOS
                # =================================================

                for relacion in productos_relacionados:

                    producto_inventario = (
                        relacion["producto"]
                    )

                    cantidad_reservar = (
                        relacion["cantidad"]
                    )

                    ReservaInventario.objects.create(
                        producto=producto_inventario,
                        ubicacion=origen,
                        cantidad=cantidad_reservar,
                        estado=(
                            ReservaInventario
                            .Estado
                            .RESERVADA
                        ),
                        traslado=traslado,
                        u_creo_id=request.user.id,
                    )

            # =====================================================
            # TODO CORRECTO
            # =====================================================

        return JsonResponse(
            {
                "success": True,
                "message":
                    "Traslado registrado y stock reservado correctamente",
                "trasladoId": traslado.id,
            }
        )

    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message":
                    f"Error interno: {str(e)}"
            },
            status=500
        )

# __________________________
## RUTA DE CAJA##
# _________________________
def _efectivo_disponible_retiro(caja, incluir_pendientes=False):
    """Efectivo físico esperado para una caja, descontando retiros."""
    fecha_caja = timezone.localdate(caja.fecha_apertura)
    ventas_contado = Ventas.objects.filter(
        u_creo_id=caja.usuario_id,
        f_creacion__date=fecha_caja,
        tipo_pago="contado",
    ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")

    estados = [RetiroCaja.Estado.COMPLETADO]
    if incluir_pendientes:
        estados.append(RetiroCaja.Estado.PENDIENTE)
    retiros = RetiroCaja.objects.filter(
        caja=caja,
        estado__in=estados,
        is_active=True,
        is_delete=False,
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
    return caja.monto_apertura + ventas_contado - retiros


@login_required
@permission_required("manager.gestionar_retiros_caja", raise_exception=True)
def retiros_caja_view(request):
    cajas = list(
        CajaAC.objects.filter(estado__in=["abierta", "cuadre"], is_active=True, is_delete=False)
        .order_by("fecha_apertura")
    )
    usuarios = {
        usuario.id: (f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username)
        for usuario in User.objects.filter(id__in=[caja.usuario_id for caja in cajas])
    }
    for caja in cajas:
        caja.cajero_nombre = usuarios.get(caja.usuario_id, "No disponible")
        caja.efectivo_disponible = _efectivo_disponible_retiro(caja, incluir_pendientes=True)

    retiros = list(RetiroCaja.objects.select_related("caja").order_by("-f_creacion")[:100])
    ids_usuarios = {retiro.cajero_id for retiro in retiros}
    nombres_retiros = {
        usuario.id: (f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username)
        for usuario in User.objects.filter(id__in=ids_usuarios)
    }
    for retiro in retiros:
        retiro.cajero_nombre = nombres_retiros.get(retiro.cajero_id, "No disponible")
    return render(request, "caja/retiros_caja.html", {"cajas": cajas, "retiros": retiros, "usuarios": usuarios, "mostrar_buscador_retiros": True})


@login_required
@permission_required("manager.gestionar_retiros_caja", raise_exception=True)
def retiros_caja_list_view(request):
    retiros_query = RetiroCaja.objects.select_related("caja").order_by("-f_creacion")
    paginator = Paginator(retiros_query, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    retiros = list(page_obj)
    nombres = {
        usuario.id: (f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username)
        for usuario in User.objects.filter(id__in={retiro.cajero_id for retiro in retiros})
    }
    for retiro in retiros:
        retiro.cajero_nombre = nombres.get(retiro.cajero_id, "No disponible")
    return render(
        request,
        "caja/retiros_caja_list.html",
        {
            "retiros": retiros,
            "page_obj": page_obj,
            "search": request.GET.get("search", ""),
            "mostrar_buscador_retiros": True,
            "buscador_retiros_listado": True,
        },
    )


@login_required
@require_POST
@permission_required("manager.gestionar_retiros_caja", raise_exception=True)
def crear_retiro_caja(request):
    try:
        caja = CajaAC.objects.get(
            id=request.POST.get("caja_id"),
            estado__in=["abierta", "cuadre"],
            is_active=True,
            is_delete=False,
        )
        monto = Decimal(request.POST.get("monto", "0"))
    except (CajaAC.DoesNotExist, InvalidOperation, TypeError):
        return JsonResponse({"ok": False, "mensaje": "Datos del retiro no válidos."}, status=400)

    if monto <= 0:
        return JsonResponse({"ok": False, "mensaje": "El monto debe ser mayor que cero."}, status=400)

    disponible = _efectivo_disponible_retiro(caja, incluir_pendientes=True)
    if monto > disponible:
        return JsonResponse({"ok": False, "mensaje": "El retiro supera el efectivo disponible en caja."}, status=400)

    retiro = RetiroCaja.objects.create(
        caja=caja,
        cajero_id=caja.usuario_id,
        monto=monto,
        observaciones=(request.POST.get("observaciones") or "").strip(),
        u_creo_id=request.user.id,
    )
    Notificacion.objects.create(
        usuario_id=caja.usuario_id,
        tipo=Notificacion.Tipo.RETIRO_CAJA,
        titulo="Retiro solicitado",
        mensaje=f"L. {monto:.2f} · Caja #{caja.id}",
        retiro_caja=retiro,
        u_creo_id=request.user.id,
    )
    return JsonResponse({"ok": True, "mensaje": "Solicitud de retiro enviada al cajero."})


@login_required
@require_POST
def completar_retiro_caja(request, id):
    retiro = get_object_or_404(
        RetiroCaja,
        id=id,
        cajero_id=request.user.id,
        estado=RetiroCaja.Estado.PENDIENTE,
        is_active=True,
        is_delete=False,
    )
    retiro.estado = RetiroCaja.Estado.COMPLETADO
    retiro.completado_por_id = request.user.id
    retiro.fecha_completado = timezone.now()
    retiro.u_modifico_id = request.user.id
    retiro.save()
    Notificacion.objects.filter(
        retiro_caja=retiro,
        usuario_id=request.user.id,
        leida=False,
        is_active=True,
        is_delete=False,
    ).update(leida=True, u_modifico_id=request.user.id, f_modificacion=timezone.now())
    return JsonResponse({"ok": True, "mensaje": "Retiro confirmado."})


@login_required
@require_POST
def marcar_notificacion_leida(request, id):
    """Marca un aviso propio como visto sin recargar la vista actual."""
    notificacion = get_object_or_404(
        Notificacion,
        id=id,
        usuario=request.user,
        leida=False,
        is_active=True,
        is_delete=False,
    )
    notificacion.leida = True
    notificacion.u_modifico_id = request.user.id
    notificacion.f_modificacion = timezone.now()
    notificacion.save(update_fields=["leida", "u_modifico_id", "f_modificacion"])
    pendientes = Notificacion.objects.filter(
        usuario=request.user,
        leida=False,
        is_active=True,
        is_delete=False,
    ).count()
    return JsonResponse({"ok": True, "pendientes": pendientes})


@login_required
@require_GET
def estado_notificaciones(request):
    """Devuelve el panel vigente; las alertas se sincronizan por eventos/tarea."""
    return JsonResponse(estado_notificaciones_usuario(request.user))


@login_required
def caja_view(request):

    if not _puede_generar_cotizaciones(request.user):
        raise PermissionDenied("No tiene permiso para acceder a Caja")

    puede_operar_caja = _puede_operar_caja(request.user)

    hoy = timezone.localdate()

    caja_pendiente = CajaAC.objects.filter(
        usuario_id=request.user.id,
        estado__in=["abierta", "cuadre"],
    ).order_by("fecha_apertura", "id").first()

    cajas_hoy = CajaAC.objects.filter(
        usuario_id=request.user.id,
        fecha_apertura__date=hoy,
    )
    caja_cerrada = cajas_hoy.filter(estado="cerrada").exists()

    mostrar_modal_apertura = False
    caja_cerrada_hoy = False
    caja_abierta = False

    if (
        caja_pendiente
        and timezone.localdate(caja_pendiente.fecha_apertura) < hoy
        and puede_operar_caja
    ):
        # Defensa adicional si se accede a Caja sin pasar por el middleware.
        return redirect("cuadre_caja")

    if caja_pendiente and caja_pendiente.estado == "abierta":
        caja_abierta = timezone.localdate(caja_pendiente.fecha_apertura) == hoy

    elif caja_pendiente and caja_pendiente.estado == "cuadre" and puede_operar_caja:
        # Ya inició el cierre pero todavía no ha terminado el cuadre.
        return redirect("cuadre_caja")

    elif caja_cerrada:
        # Ya terminó completamente la caja del día.
        caja_cerrada_hoy = True

    elif puede_operar_caja:
        # El usuario todavía no ha abierto caja hoy.
        mostrar_modal_apertura = True

    context = {
        "mostrar_buscador": False,
        "mostrar_codigo": True,
        "mostrar_modal_apertura": mostrar_modal_apertura,
        "caja_cerrada_hoy": caja_cerrada_hoy,
        "caja_abierta": caja_abierta,
        "caja_pendiente_anterior": bool(
            caja_pendiente
            and timezone.localdate(caja_pendiente.fecha_apertura) != hoy
        ),
        "puede_operar_caja": puede_operar_caja,
        "puede_generar_cotizaciones": _puede_generar_cotizaciones(request.user),
    }

    return render(request, "caja/caja.html", context)


@login_required
@require_POST
@permission_required("manager.operar_caja", raise_exception=True)
def abrir_caja(request):

    try:
        monto = Decimal(
            request.POST.get("monto_apertura", "0")
        )
    except (InvalidOperation, TypeError):
        return JsonResponse({
            "ok": False,
            "mensaje": "El monto de apertura no es válido."
        }, status=400)

    # ... existing code ...

    if monto < 0:
        return JsonResponse({
            "ok": False,
            "mensaje": "El monto de apertura no puede ser negativo."
        }, status=400)

    hoy = timezone.localdate()

    caja_pendiente = CajaAC.objects.filter(
        usuario_id=request.user.id,
        estado__in=["abierta", "cuadre"],
    ).order_by("fecha_apertura", "id").first()

    if caja_pendiente:

        if caja_pendiente.estado == "cuadre":
            mensaje = "Esta caja ya se encuentra en proceso de cuadre."

        else:
            mensaje = "Debe cerrar la caja pendiente antes de abrir una nueva."

        return JsonResponse({
            "ok": False,
            "mensaje": mensaje
        }, status=400)

    caja = CajaAC.objects.create(
        usuario_id=request.user.id,
        monto_apertura=monto,
        estado="abierta",
        u_creo_id=request.user.id
    )

    return JsonResponse({
        "ok": True,
        "mensaje": "Caja abierta correctamente.",
        "caja_id": caja.id
    })
# Busqueda de Productos por codigo de barra en caja.


@login_required
@require_POST
@permission_required("manager.operar_caja", raise_exception=True)
def iniciar_cuadre(request):

    hoy = timezone.localdate()

    caja = CajaAC.objects.filter(
        usuario_id=request.user.id,
        estado="abierta",
    ).order_by("fecha_apertura", "id").first()

    if not caja:
        return JsonResponse({
            "ok": False,
            "mensaje": "No existe una caja abierta para iniciar el cuadre."
        }, status=400)

    caja.estado = "cuadre"
    caja.u_modifico_id = request.user.id
    caja.save()

    return JsonResponse({
        "ok": True,
        "redirect_url": reverse("cuadre_caja")
    })


@login_required
@permission_required("manager.operar_caja", raise_exception=True)
def cuadre_caja(request):

    hoy = timezone.localdate()

    caja = CajaAC.objects.filter(
        usuario_id=request.user.id,
        estado="cuadre",
    ).order_by("fecha_apertura", "id").first()

    if not caja:
        # Al entrar otro día, la caja abierta pendiente pasa directamente al
        # proceso de cierre; no puede seguir operándose ni abrirse otra.
        caja = CajaAC.objects.filter(
            usuario_id=request.user.id,
            estado="abierta",
            fecha_apertura__date__lt=hoy,
            is_active=True,
            is_delete=False,
        ).order_by("fecha_apertura", "id").first()
        if caja:
            caja.estado = "cuadre"
            caja.u_modifico_id = request.user.id
            caja.save(update_fields=["estado", "u_modifico_id"])

    if not caja:
        return redirect("caja")

    # =========================
    # VENTAS DEL USUARIO HOY
    # =========================

    fecha_caja = timezone.localdate(caja.fecha_apertura)
    ventas_por_tipo = Ventas.objects.filter(
        u_creo_id=request.user.id,
        f_creacion__date=fecha_caja
    ).values("tipo_pago").annotate(total=Sum("total"))

    totales_pago = {
        venta["tipo_pago"]: venta["total"] or Decimal("0.00")
        for venta in ventas_por_tipo
    }
    ventas_hoy = sum(totales_pago.values(), Decimal("0.00"))
    ventas_contado = totales_pago.get("contado", Decimal("0.00"))
    ventas_deposito = totales_pago.get("depostivo", Decimal("0.00"))
    ventas_tarjeta = totales_pago.get("tarjeta", Decimal("0.00"))
    ventas_cheque = totales_pago.get("cheque", Decimal("0.00"))
    total_retiros = RetiroCaja.objects.filter(
        caja=caja,
        estado=RetiroCaja.Estado.COMPLETADO,
        is_active=True,
        is_delete=False,
    ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

    # =========================
    # TOTAL ESPERADO
    # =========================

    total_esperado = _efectivo_disponible_retiro(caja)
    configuracion = ConfiguracionEmpresa.objects.filter(
        is_active=True, is_delete=False
    ).only("moneda").first()
    es_dolar = bool(
        configuracion
        and configuracion.moneda == ConfiguracionEmpresa.MONEDA_DOLAR
    )
    denominaciones_efectivo = (
        [
            Decimal("0.01"), Decimal("0.05"), Decimal("0.10"),
            Decimal("0.25"), Decimal("0.50"), Decimal("1.00"),
            Decimal("5.00"), Decimal("10.00"), Decimal("20.00"),
            Decimal("50.00"), Decimal("100.00"),
        ]
        if es_dolar
        else [
            Decimal("1.00"), Decimal("2.00"), Decimal("5.00"),
            Decimal("10.00"), Decimal("20.00"), Decimal("50.00"),
            Decimal("100.00"), Decimal("200.00"), Decimal("500.00"),
        ]
    )

    context = {
        "caja": caja,
        "ventas_hoy": ventas_hoy,
        "ventas_contado": ventas_contado,
        "ventas_deposito": ventas_deposito,
        "ventas_tarjeta": ventas_tarjeta,
        "ventas_cheque": ventas_cheque,
        "total_retiros": total_retiros,
        "total_esperado": total_esperado,
        "denominaciones_efectivo": denominaciones_efectivo,
        "descripcion_denominaciones": (
            "Ingresa la cantidad de monedas y billetes por denominación"
            if es_dolar
            else "Ingresa la cantidad de billetes por denominación"
        ),
    }

    return render(
        request,
        "caja/cuadre_caja.html",
        context
    )

@login_required
@transaction.atomic
@permission_required("manager.operar_caja", raise_exception=True)
def cerrar_cuadre_caja(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "ok": False,
                "mensaje": "Método no permitido."
            },
            status=405
        )

    hoy = timezone.localdate()

    caja = CajaAC.objects.filter(
        usuario_id=request.user.id,
        estado="cuadre",
    ).order_by("fecha_apertura", "id").first()

    if not caja:
        return JsonResponse(
            {
                "ok": False,
                "mensaje": "No existe una caja en estado de cuadre."
            },
            status=400
        )

    try:
        data = request.POST

        # =========================
        # DENOMINACIONES
        # =========================

        configuracion = ConfiguracionEmpresa.objects.filter(
            is_active=True, is_delete=False
        ).only("moneda").first()
        denominaciones = (
            [
                Decimal("0.01"), Decimal("0.05"), Decimal("0.10"),
                Decimal("0.25"), Decimal("0.50"), Decimal("1.00"),
                Decimal("5.00"), Decimal("10.00"), Decimal("20.00"),
                Decimal("50.00"), Decimal("100.00"),
            ]
            if configuracion and configuracion.moneda == ConfiguracionEmpresa.MONEDA_DOLAR
            else [
                Decimal("1.00"), Decimal("2.00"), Decimal("5.00"),
                Decimal("10.00"), Decimal("20.00"), Decimal("50.00"),
                Decimal("100.00"), Decimal("200.00"), Decimal("500.00"),
            ]
        )

        total_contado = Decimal("0.00")

        detalles = []

        for denominacion in denominaciones:

            cantidad_key = f"cantidad_{denominacion}"

            cantidad = int(data.get(cantidad_key, 0) or 0)

            if cantidad < 0:
                return JsonResponse(
                    {
                        "ok": False,
                        "mensaje": "La cantidad no puede ser negativa."
                    },
                    status=400
                )

            subtotal = denominacion * cantidad

            total_contado += subtotal

            detalles.append({
                "denominacion": denominacion,
                "cantidad": cantidad,
                "subtotal": subtotal,
            })

        # =========================
        # VENTAS DEL DÍA
        # =========================

        fecha_caja = timezone.localdate(caja.fecha_apertura)
        ventas_por_tipo = Ventas.objects.filter(
            u_creo_id=request.user.id,
            f_creacion__date=fecha_caja
        ).values("tipo_pago").annotate(total=Sum("total"))

        totales_pago = {
            venta["tipo_pago"]: venta["total"] or Decimal("0.00")
            for venta in ventas_por_tipo
        }
        ventas_hoy = sum(totales_pago.values(), Decimal("0.00"))
        ventas_contado = totales_pago.get("contado", Decimal("0.00"))
        ventas_deposito = totales_pago.get("depostivo", Decimal("0.00"))
        ventas_tarjeta = totales_pago.get("tarjeta", Decimal("0.00"))
        ventas_cheque = totales_pago.get("cheque", Decimal("0.00"))
        total_retiros = RetiroCaja.objects.filter(
            caja=caja,
            estado=RetiroCaja.Estado.COMPLETADO,
            is_active=True,
            is_delete=False,
        ).aggregate(total=Sum("monto"))["total"] or Decimal("0.00")

        montos_otros_pagos = {}
        for tipo, esperado in {
            "deposito": ventas_deposito,
            "tarjeta": ventas_tarjeta,
            "cheque": ventas_cheque,
        }.items():
            valor_recibido = (data.get(f"monto_{tipo}") or "").strip()
            if esperado > 0 and not valor_recibido:
                return JsonResponse(
                    {
                        "ok": False,
                        "mensaje": f"Ingrese el monto recibido por {tipo}.",
                    },
                    status=400,
                )

            recibido = Decimal(valor_recibido or "0.00")
            if recibido < 0:
                return JsonResponse(
                    {
                        "ok": False,
                        "mensaje": "Los montos recibidos no pueden ser negativos.",
                    },
                    status=400,
                )
            montos_otros_pagos[tipo] = recibido

        # =========================
        # TOTAL ESPERADO
        # =========================

        total_esperado = _efectivo_disponible_retiro(caja)

        # =========================
        # DIFERENCIA
        # =========================

        diferencia = (
            total_contado - total_esperado
        )

        # =========================
        # GUARDAR DETALLES
        # =========================

        DetalleCuadreCaja.objects.filter(
            caja=caja
        ).delete()

        for detalle in detalles:

            DetalleCuadreCaja.objects.create(
                caja=caja,
                denominacion=detalle["denominacion"],
                cantidad=detalle["cantidad"],
                subtotal=detalle["subtotal"],
            )

        # Un retiro pendiente nunca salió físicamente de la caja. Al cerrar,
        # queda cancelado y su aviso deja de mostrarse al cajero.
        retiros_pendientes = RetiroCaja.objects.select_for_update().filter(
            caja=caja,
            estado=RetiroCaja.Estado.PENDIENTE,
            is_active=True,
            is_delete=False,
        )
        ids_retiros_pendientes = list(retiros_pendientes.values_list("id", flat=True))
        if ids_retiros_pendientes:
            ahora = timezone.now()
            retiros_pendientes.update(
                estado=RetiroCaja.Estado.CANCELADO,
                u_modifico_id=request.user.id,
                f_modificacion=ahora,
            )
            Notificacion.objects.filter(
                retiro_caja_id__in=ids_retiros_pendientes,
                is_active=True,
                is_delete=False,
            ).update(
                leida=True,
                is_active=False,
                is_delete=True,
                u_modifico_id=request.user.id,
                f_modificacion=ahora,
            )
            transaction.on_commit(
                lambda usuario_id=caja.usuario_id: publicar_actualizacion_usuarios([usuario_id])
            )

        # =========================
        # CERRAR CAJA
        # =========================

        caja.ventas = ventas_hoy
        caja.retiros_total = total_retiros
        caja.monto_cierre = total_contado
        caja.diferencia = diferencia
        caja.deposito_esperado = ventas_deposito
        caja.deposito_recibido = montos_otros_pagos["deposito"]
        caja.tarjeta_esperado = ventas_tarjeta
        caja.tarjeta_recibido = montos_otros_pagos["tarjeta"]
        caja.cheque_esperado = ventas_cheque
        caja.cheque_recibido = montos_otros_pagos["cheque"]
        caja.fecha_cierre = timezone.now()
        caja.estado = "cerrada"

        caja.save()

        return JsonResponse({
            "ok": True,
            "mensaje": "El cuadre de caja se cerró correctamente.",
            "total_contado": str(total_contado),
            "total_esperado": str(total_esperado),
            "diferencia": str(diferencia),
            "otros_pagos": {
                tipo: {
                    "esperado": str(esperado),
                    "recibido": str(montos_otros_pagos[tipo]),
                    "diferencia": str(montos_otros_pagos[tipo] - esperado),
                }
                for tipo, esperado in {
                    "deposito": ventas_deposito,
                    "tarjeta": ventas_tarjeta,
                    "cheque": ventas_cheque,
                }.items()
            },
        })

    except (ValueError, InvalidOperation) as e:

        return JsonResponse(
            {
                "ok": False,
                "mensaje": "Los datos enviados no son válidos."
            },
            status=400
        )


@login_required
def cajas_manager_view(request):

    # =========================
    # VALIDAR PERMISO
    # =========================

    if not request.user.has_perm("manager.view_cajaac"):
        raise PermissionDenied("No tienes permiso")


    # =========================
    # FECHA
    # =========================

    fecha = request.GET.get("fecha", "").strip()

    if fecha:

        try:
            fecha_filtro = datetime.strptime(
                fecha,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            fecha_filtro = timezone.localdate()

    else:

        fecha_filtro = timezone.localdate()


    # =========================
    # BUSCAR
    # =========================

    search = request.GET.get(
        "search",
        ""
    ).strip()


    # =========================
    # CAJAS DEL DÍA
    # =========================

    cajas = CajaAC.objects.filter(
        fecha_apertura__date=fecha_filtro
    ).order_by(
        "-fecha_apertura"
    )


    # =========================
    # FILTRO POR USUARIO
    # =========================

    if search:

        usuarios_ids = User.objects.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        ).values_list(
            "id",
            flat=True
        )

        cajas = cajas.filter(
            usuario_id__in=usuarios_ids
        )


    # =========================
    # USUARIOS
    # =========================

    usuarios = User.objects.in_bulk(
        [caja.usuario_id for caja in cajas]
    )


    # =========================
    # PAGINACIÓN
    # =========================

    paginator = Paginator(
        cajas,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )


    # =========================
    # DATOS DE LA TABLA
    # =========================

    for caja in page_obj:

        usuario = usuarios.get(
            caja.usuario_id
        )

        if usuario:

            caja.usuario_nombre = (
                usuario.get_full_name()
                or usuario.username
            )

        else:

            caja.usuario_nombre = (
                f"Usuario #{caja.usuario_id}"
            )


        # =========================
        # TOTAL CIERRE
        # =========================

        if caja.estado == "cerrada":
            caja.cerro_con = (
                (caja.monto_cierre or Decimal("0.00"))
                + (caja.deposito_recibido or Decimal("0.00"))
                + (caja.tarjeta_recibido or Decimal("0.00"))
                + (caja.cheque_recibido or Decimal("0.00"))
            )
            # Recursos efectivamente recibidos más efectivo retirado.
            caja.total_cierre = caja.cerro_con + (caja.retiros_total or Decimal("0.00"))
            caja.diferencia_general = (
                (caja.diferencia or Decimal("0.00"))
                + ((caja.deposito_recibido or Decimal("0.00")) - (caja.deposito_esperado or Decimal("0.00")))
                + ((caja.tarjeta_recibido or Decimal("0.00")) - (caja.tarjeta_esperado or Decimal("0.00")))
                + ((caja.cheque_recibido or Decimal("0.00")) - (caja.cheque_esperado or Decimal("0.00")))
            )

        else:

            caja.total_cierre = None
            caja.cerro_con = None
            caja.diferencia_general = None


    context = {
        "page_obj": page_obj,
        "search": search,
        "fecha": fecha_filtro,
    }


    return render(
        request,
        "caja/cajas_manager.html",
        context
    )


def obtener_ubicaciones_inventario(ubicacion_id):
    try:
        ubicacion = Ubicaciones.objects.get(
            id=ubicacion_id,
            is_delete=False
        )
    except Ubicaciones.DoesNotExist:
        return [ubicacion_id]

    ubicaciones = [ubicacion.id]

    if ubicacion.bodega_id:
        ubicaciones.append(ubicacion.bodega_id)

    return ubicaciones


def _generar_nota_credito():
    while True:
        nota_credito = f"NC-{uuid.uuid4().hex[:12].upper()}"
        if not DevolucionVenta.objects.filter(nota_credito=nota_credito).exists():
            return nota_credito


def _reintegrar_inventario_devolucion(venta, detalle_venta, cantidad):
    """Reintegra al inventario las mismas equivalencias afectadas en la venta."""
    ubicaciones = obtener_ubicaciones_inventario(venta.sucursal_id)

    for item in obtener_productos_relacionados(detalle_venta.producto, cantidad):
        producto_inventario = item["producto"]
        cantidad_reintegrar = Decimal(item["cantidad"])

        if cantidad_reintegrar <= 0:
            continue

        lote = (
            Inventarios.objects.select_for_update()
            .filter(
                producto=producto_inventario,
                ubicacion_id=venta.sucursal_id,
            )
            .order_by("f_creacion", "id")
            .first()
        )

        if not lote:
            lote_referencia = (
                Inventarios.objects.select_for_update()
                .filter(
                    producto=producto_inventario,
                    ubicacion_id__in=ubicaciones,
                )
                .order_by("f_creacion", "id")
                .first()
            )
            lote = Inventarios.objects.create(
                producto=producto_inventario,
                compra_id=lote_referencia.compra_id if lote_referencia else None,
                ubicacion_id=venta.sucursal_id,
                cantidad=Decimal("0"),
                stock_minimo=lote_referencia.stock_minimo if lote_referencia else Decimal("5"),
                fvencimiento=lote_referencia.fvencimiento if lote_referencia else None,
                u_creo_id=venta.u_creo_id,
            )

        stock_anterior = lote.cantidad
        lote.cantidad += cantidad_reintegrar
        lote.save(update_fields=["cantidad"])

        stock_resultante = (
            Inventarios.objects.filter(
                producto=producto_inventario,
                ubicacion_id=venta.sucursal_id,
            ).aggregate(total=Sum("cantidad"))["total"]
            or Decimal("0")
        )

        MovimientoInventario.objects.create(
            tipo_movimiento=TipoMovimientoInventario.DEVOLUCION_CLIENTE,
            producto=producto_inventario,
            ubicacion_destino_id=venta.sucursal_id,
            cantidad=cantidad_reintegrar,
            stock_anterior=stock_anterior,
            stock_resultante=stock_resultante,
            venta_id=venta.id,
        )


@login_required
@permission_required("manager.add_devolucionventa", raise_exception=True)
def devoluciones_venta_view(request):
    return render(
        request,
        "caja/devoluciones_venta.html",
        {"motivos": MotivoDevolucion.choices, "mostrar_buscar_factura": True},
    )


@login_required
@permission_required("manager.add_devolucionventa", raise_exception=True)
def buscar_factura_devolucion_venta(request, numero_factura):
    try:
        venta = (
            Ventas.objects.select_related("id_factura_cai", "id_cliente", "sucursal")
            .prefetch_related("venta_detalles__producto")
            .filter(id_factura_cai__numero_factura=numero_factura)
            .first()
        )

        if not venta:
            return JsonResponse(
                {"success": False, "message": "No se encontró la factura"},
                status=404,
            )

        detalles = []
        for detalle in venta.venta_detalles.filter(producto__isnull=False):
            cantidad_devuelta = (
                DevolucionVentaDetalle.objects.filter(
                    detalle_venta=detalle,
                    devolucion_venta__is_delete=False,
                )
                .exclude(devolucion_venta__estado=DevolucionVenta.Estado.ANULADA)
                .aggregate(total=Sum("cantidad"))["total"]
                or Decimal("0")
            )
            cantidad_disponible = max(detalle.cantidad - cantidad_devuelta, Decimal("0"))

            detalles.append(
                {
                    "detalleVentaId": detalle.id,
                    "producto": detalle.producto.nombre,
                    "cantidadVendida": str(detalle.cantidad),
                    "cantidadDevuelta": str(cantidad_devuelta),
                    "cantidadDisponible": str(cantidad_disponible),
                    "precioUnitario": str(detalle.precio_unitario),
                }
            )

        cliente = (
            {
                "id": venta.id_cliente.id,
                "nombre": (
                    (venta.id_cliente.empresa or venta.id_cliente.nombre_completo)
                    if venta.con_rtn
                    else venta.id_cliente.nombre_completo
                ),
            }
            if venta.id_cliente
            else {"id": None, "nombre": "Consumidor Final"}
        )

        return JsonResponse(
            {
                "success": True,
                "factura": {
                    "id": venta.id_factura_cai.id,
                    "numero": venta.id_factura_cai.numero_factura,
                    "fecha": venta.f_creacion.strftime("%d/%m/%Y"),
                    "sucursal": venta.sucursal.nombre,
                    "tipoVenta": venta.tipo_venta,
                    "tipoVentaTexto": venta.get_tipo_venta_display(),
                    "cliente": cliente,
                },
                "detalles": detalles,
            }
        )
    except Exception:
        traceback.print_exc()
        return JsonResponse(
            {"success": False, "message": "No fue posible consultar la factura."},
            status=500,
        )


@require_POST
@login_required
@permission_required("manager.add_devolucionventa", raise_exception=True)
@transaction.atomic
def crear_devolucion_venta(request):
    try:
        data = json.loads(request.body)
        factura_id = data.get("facturaId")
        motivo = data.get("motivo")
        justificacion = (data.get("justificacion") or "").strip()
        resolucion_solicitada = data.get("resolucion")
        detalles_solicitados = data.get("detalles", [])

        if not factura_id or not detalles_solicitados:
            return JsonResponse(
                {"success": False, "message": "Seleccione al menos un producto"},
                status=400,
            )

        if not justificacion:
            return JsonResponse(
                {"success": False, "message": "La justificación es obligatoria"},
                status=400,
            )

        try:
            motivo = int(motivo)
        except (TypeError, ValueError):
            motivo = None

        if motivo not in dict(MotivoDevolucion.choices):
            return JsonResponse(
                {"success": False, "message": "Seleccione un motivo válido"},
                status=400,
            )

        venta = (
            Ventas.objects.select_for_update(of=("self",))
            .select_related("id_factura_cai", "sucursal")
            .filter(id_factura_cai_id=factura_id)
            .first()
        )
        if not venta:
            return JsonResponse(
                {"success": False, "message": "La factura no existe"}, status=404
            )

        if venta.tipo_venta == Ventas.TIPO_VENTA_CREDITO:
            if resolucion_solicitada not in {
                DevolucionVenta.RESOLUCION_NOTA_CREDITO,
                DevolucionVenta.RESOLUCION_DEDUCIR_SALDO,
            }:
                return JsonResponse(
                    {"success": False, "message": "Seleccione cómo resolver la devolución a crédito"},
                    status=400,
                )
        else:
            resolucion_solicitada = DevolucionVenta.RESOLUCION_NOTA_CREDITO

        detalle_ids = [item.get("detalleVentaId") for item in detalles_solicitados]
        if len(detalle_ids) != len(set(detalle_ids)):
            return JsonResponse(
                {"success": False, "message": "No repita productos en la devolución"},
                status=400,
            )

        detalles_venta = {
            detalle.id: detalle
            for detalle in DetalleVenta.objects.select_for_update(of=("self",))
            .select_related("producto")
            .filter(id__in=detalle_ids, venta=venta)
        }

        if len(detalles_venta) != len(set(detalle_ids)):
            return JsonResponse(
                {"success": False, "message": "Hay productos que no pertenecen a la factura"},
                status=400,
            )

        devolucion = DevolucionVenta.objects.create(
            venta=venta,
            nota_credito=_generar_nota_credito(),
            motivo=motivo,
            justificacion=justificacion,
            monto_total=Decimal("0"),
            resolucion=resolucion_solicitada,
            u_creo_id=request.user.id,
        )

        monto_total = Decimal("0")
        for item in detalles_solicitados:
            detalle_venta = detalles_venta[item.get("detalleVentaId")]
            try:
                cantidad = Decimal(str(item.get("cantidad")))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError("La cantidad devuelta no es válida")

            if cantidad <= 0:
                raise ValueError("La cantidad devuelta debe ser mayor a cero")

            cantidad_previa = (
                DevolucionVentaDetalle.objects.filter(
                    detalle_venta=detalle_venta,
                    devolucion_venta__is_delete=False,
                )
                .exclude(devolucion_venta__estado=DevolucionVenta.Estado.ANULADA)
                .aggregate(total=Sum("cantidad"))["total"]
                or Decimal("0")
            )
            cantidad_disponible = detalle_venta.cantidad - cantidad_previa

            if cantidad > cantidad_disponible:
                raise ValueError(
                    f"La cantidad de {detalle_venta.producto.nombre} excede lo disponible para devolver"
                )

            proporcion = cantidad / detalle_venta.cantidad
            total_linea_original = (
                (detalle_venta.cantidad * detalle_venta.precio_unitario)
                - detalle_venta.descuento
                + (detalle_venta.impuesto_15 * detalle_venta.cantidad)
                + (detalle_venta.impuesto_18 * detalle_venta.cantidad)
            )
            total_detalle = total_linea_original * proporcion
            DevolucionVentaDetalle.objects.create(
                devolucion_venta=devolucion,
                detalle_venta=detalle_venta,
                producto=detalle_venta.producto,
                cantidad=cantidad,
                precio_unitario=detalle_venta.precio_unitario,
                total=total_detalle,
            )
            detalle_venta.monto_devuelto = (
                Decimal(detalle_venta.monto_devuelto or 0) + total_detalle
            )
            detalle_venta.save(update_fields=["monto_devuelto"])
            _reintegrar_inventario_devolucion(venta, detalle_venta, cantidad)
            monto_total += total_detalle

        devolucion.monto_total = monto_total
        if resolucion_solicitada == DevolucionVenta.RESOLUCION_DEDUCIR_SALDO:
            cuenta = CuentasPorCobrar.objects.select_for_update(of=("self",)).filter(
                venta=venta,
                is_delete=False,
            ).first()
            if not cuenta:
                raise ValueError("La factura no tiene una cuenta por cobrar activa")
            if monto_total > cuenta.monto_pendiente:
                raise ValueError(
                    "La devolución excede el saldo pendiente; seleccione nota de crédito"
                )

            nuevo_pendiente = cuenta.monto_pendiente - monto_total
            abono = RegistroAbonosCobrar.objects.create(
                cuenta_por_cobrar=cuenta,
                monto_abonado=monto_total,
                monto_pendiente=nuevo_pendiente,
                liquidado=(nuevo_pendiente <= 0),
                u_creo_id=request.user.id,
            )
            cuenta.monto_pendiente = nuevo_pendiente
            cuenta.estado = (
                EstadoCuenta.PAGADO
                if nuevo_pendiente <= 0
                else EstadoCuenta.PARCIAL
            )
            cuenta.u_modifico_id = request.user.id
            cuenta.f_modificacion = timezone.now()
            cuenta.save()
            devolucion.abono_cxc = abono
            devolucion.estado = DevolucionVenta.Estado.USADA
            devolucion.fecha_uso = timezone.now()

        devolucion.save(
            update_fields=[
                "monto_total",
                "estado",
                "abono_cxc",
                "fecha_uso",
            ]
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Devolución registrada correctamente",
                "notaCredito": devolucion.nota_credito,
                "monto": str(devolucion.monto_total),
                "resolucion": devolucion.resolucion,
            }
        )

    except (ValueError, KeyError) as error:
        transaction.set_rollback(True)
        return JsonResponse({"success": False, "message": str(error)}, status=400)
    except Exception as error:
        transaction.set_rollback(True)
        return JsonResponse({"success": False, "message": str(error)}, status=500)


def _nombre_cliente_devolucion(venta):
    if not venta.id_cliente:
        return "Consumidor Final"
    if venta.con_rtn:
        return venta.id_cliente.empresa or venta.id_cliente.nombre_completo
    return venta.id_cliente.nombre_completo


def _consulta_devoluciones_venta(fecha_inicio, fecha_fin, sucursal, estado=""):
    inicio_honduras, fin_honduras = _rango_fechas_honduras(fecha_inicio, fecha_fin)
    devoluciones = DevolucionVenta.objects.select_related(
        "venta__id_factura_cai", "venta__id_cliente", "venta__sucursal"
    ).prefetch_related("detalles__producto").filter(
        is_delete=False,
        f_creacion__gte=inicio_honduras,
        f_creacion__lt=fin_honduras,
    ).order_by("-f_creacion")

    if sucursal:
        devoluciones = devoluciones.filter(venta__sucursal_id=sucursal)

    if estado in {DevolucionVenta.Estado.DISPONIBLE, DevolucionVenta.Estado.USADA}:
        devoluciones = devoluciones.filter(estado=estado)

    return devoluciones


@login_required
@permission_required("manager.view_devolucionventa", raise_exception=True)
def devoluciones_venta_list(request):
    fecha_hoy = timezone.localdate(timezone=ZONA_HONDURAS).strftime("%Y-%m-%d")
    fecha_inicio = request.GET.get("fecha_inicio") or fecha_hoy
    fecha_fin = request.GET.get("fecha_fin") or fecha_hoy
    sucursal = request.GET.get("sucursal")
    estado = request.GET.get("estado", "").strip().upper()

    devoluciones_base = _consulta_devoluciones_venta(fecha_inicio, fecha_fin, sucursal)
    disponibles_count = devoluciones_base.filter(
        estado=DevolucionVenta.Estado.DISPONIBLE
    ).count()
    usadas_count = devoluciones_base.filter(
        estado=DevolucionVenta.Estado.USADA
    ).count()
    devoluciones = (
        devoluciones_base.filter(estado=estado)
        if estado in {DevolucionVenta.Estado.DISPONIBLE, DevolucionVenta.Estado.USADA}
        else devoluciones_base
    )
    page_obj = Paginator(devoluciones, 25).get_page(request.GET.get("page"))

    sucursales_con_notas = DevolucionVenta.objects.filter(
        is_delete=False,
        venta__sucursal__is_delete=False,
    ).values_list("venta__sucursal_id", flat=True).distinct()

    return render(
        request,
        "caja/devoluciones_venta_list.html",
        {
            "page_obj": page_obj,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "sucursales": Ubicaciones.objects.filter(
                id__in=sucursales_con_notas,
                es_tienda=True,
                is_delete=False,
            ).order_by("nombre"),
            "sucursal_seleccionada": sucursal,
            "estado_seleccionado": estado,
            "disponibles_count": disponibles_count,
            "usadas_count": usadas_count,
        },
    )


@login_required
@permission_required("manager.view_devolucionventa", raise_exception=True)
def exportar_devoluciones_venta_excel(request):
    fecha_hoy = timezone.localdate(timezone=ZONA_HONDURAS).strftime("%Y-%m-%d")
    fecha_inicio = request.GET.get("fecha_inicio") or fecha_hoy
    fecha_fin = request.GET.get("fecha_fin") or fecha_hoy
    sucursal = request.GET.get("sucursal")
    estado = request.GET.get("estado", "").strip().upper()

    devoluciones = _consulta_devoluciones_venta(
        fecha_inicio, fecha_fin, sucursal, estado
    )

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Devoluciones venta"
    encabezados = [
        "Nota de devolución", "Fecha", "Factura", "Cliente", "Sucursal",
        "Motivo", "Justificación", "Productos", "Monto", "Estado",
    ]
    hoja.append(encabezados)

    color_encabezado = PatternFill("solid", fgColor="32877F")
    for celda in hoja[1]:
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = color_encabezado
        celda.alignment = Alignment(horizontal="center")

    for devolucion in devoluciones:
        productos = "; ".join(
            f"{detalle.producto.nombre} x {detalle.cantidad:.2f}"
            for detalle in devolucion.detalles.all()
        )
        hoja.append([
            devolucion.nota_credito,
            _fecha_honduras(devolucion.f_creacion).date(),
            devolucion.venta.id_factura_cai.numero_factura,
            _nombre_cliente_devolucion(devolucion.venta),
            devolucion.venta.sucursal.nombre,
            devolucion.get_motivo_display(),
            devolucion.justificacion,
            productos,
            devolucion.monto_total,
            devolucion.get_estado_display(),
        ])

    for celda in hoja["B"][1:]:
        celda.number_format = "dd/mm/yyyy"
    for celda in hoja["I"][1:]:
        celda.number_format = '#,##0.00'

    for columna in range(1, hoja.max_column + 1):
        letra = get_column_letter(columna)
        ancho = max(len(str(hoja.cell(fila, columna).value or "")) for fila in range(1, hoja.max_row + 1))
        hoja.column_dimensions[letra].width = min(ancho + 2, 42)

    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions
    salida = BytesIO()
    libro.save(salida)
    salida.seek(0)

    response = HttpResponse(
        salida.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="devoluciones_venta_{fecha_inicio}_{fecha_fin}.xlsx"'
    )
    return response


@login_required
@permission_required("manager.operar_caja", raise_exception=True)
def notas_credito_disponibles(request):
    referencia = (request.GET.get("search") or "").strip()

    if not referencia:
        return JsonResponse({"success": True, "notas": []})

    notas = DevolucionVenta.objects.select_related(
        "venta__sucursal", "venta__id_cliente", "venta__id_factura_cai"
    ).filter(
        estado=DevolucionVenta.Estado.DISPONIBLE,
        is_active=True,
        is_delete=False,
    )

    if not request.user.is_superuser:
        perfil = PerfilUsuario.objects.filter(usuarios=request.user).first()
        if not perfil or not perfil.ubicacion_id:
            return JsonResponse(
                {"success": False, "message": "El usuario no tiene una sucursal asignada"},
                status=400,
            )
        notas = notas.filter(venta__sucursal_id=perfil.ubicacion_id)

    filtro_busqueda = Q(nota_credito__icontains=referencia)
    if referencia.isdigit():
        filtro_busqueda |= Q(
            venta__id_factura_cai__numero_factura=int(referencia)
        )
    notas = notas.filter(filtro_busqueda)

    return JsonResponse(
        {
            "success": True,
            "notas": [
                {
                    "id": nota.id,
                    "nota": nota.nota_credito,
                    "monto": str(nota.monto_total),
                    "factura": nota.venta.id_factura_cai.numero_factura,
                    "cliente": (
                        nota.venta.id_cliente.nombre_completo
                        if nota.venta.id_cliente
                        else "Consumidor Final"
                    ),
                }
                for nota in notas.order_by("-f_creacion")
            ],
        }
    )

def _stock_disponible_caja(producto_id, ubicaciones):
    existencia = (
        Inventarios.objects.filter(
            producto_id=producto_id,
            ubicacion_id__in=ubicaciones,
            is_delete=False,
            cantidad__gt=0,
        ).aggregate(total=Sum("cantidad"))["total"]
        or Decimal("0")
    )
    reservado = (
        ReservaInventario.objects.filter(
            producto_id=producto_id,
            ubicacion_id__in=ubicaciones,
            estado=ReservaInventario.Estado.RESERVADA,
            is_delete=False,
        ).aggregate(total=Sum("cantidad"))["total"]
        or Decimal("0")
    )
    return max(Decimal(str(existencia)) - Decimal(str(reservado)), Decimal("0"))


def _stock_para_mostrar(stock):
    """Muestra dos decimales sin redondear el inventario físico real."""
    return Decimal(str(stock)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


class StockInsuficienteError(Exception):
    """Error controlado para devolver el stock vigente a Caja sin recargarla."""

    def __init__(self, producto, disponible, requerido):
        self.producto_id = producto.id
        self.producto_nombre = producto.nombre
        self.disponible = Decimal(str(disponible))
        self.requerido = Decimal(str(requerido))
        super().__init__(
            f"Ya no hay existencias suficientes de {producto.nombre}. "
            f"Disponible: {self.disponible}, necesario: {self.requerido}."
        )


def _datos_combo_caja(combo, ubicaciones):
    detalles = list(combo.detalles.select_related("producto"))
    if not detalles:
        return None

    disponibilidad = []
    for detalle in detalles:
        if not detalle.producto.is_active or detalle.producto.is_delete:
            return None
        disponibilidad.append(
            _stock_disponible_caja(detalle.producto_id, ubicaciones) / detalle.cantidad
        )
    stock = min(disponibilidad) if disponibilidad else Decimal("0")
    if stock <= 0:
        return None

    return {
        "id": combo.id,
        "combo_id": combo.id,
        "es_combo": True,
        "codigo_sku": combo.codigo_sku,
        "nombre": combo.nombre,
        "precio_venta": combo.precio_venta,
        "precio_venta_min": combo.precio_venta_min,
        "precio_venta_max": combo.precio_venta_max,
        "id_categoria": None,
        "isv": Decimal("0"),
        "tipos_isv": Decimal("0"),
        "stock": stock,
        "lleva": 0,
        "paga": 0,
        "descuentos": 0,
        "acumulable": False,
    }


def _numero_siguiente_cotizacion():
    ultima = Cotizacion.objects.select_for_update().order_by("-id").first()
    consecutivo = 1
    if ultima:
        try:
            consecutivo = int(ultima.numero_cotizacion.rsplit("-", 1)[-1]) + 1
        except (ValueError, IndexError):
            consecutivo = ultima.id + 1
    return f"COT-{consecutivo:06d}"


@login_required
@require_POST
def crear_cotizacion(request):
    try:
        if not _puede_generar_cotizaciones(request.user):
            raise PermissionDenied("No tiene permiso para generar cotizaciones")
        data = json.loads(request.body)
        productos = data.get("productos", [])
        cliente_id = data.get("cliente_id")
        cliente_nombre = (data.get("cliente_nombre") or "").strip()
        con_rtn = bool(data.get("con_rtn"))

        if not productos:
            return JsonResponse({"success": False, "message": "Agregue productos a la cotización"}, status=400)

        perfil = PerfilUsuario.objects.get(usuarios=request.user)
        if not perfil.ubicacion_id:
            return JsonResponse({"success": False, "message": "El usuario no tiene una sucursal asignada"}, status=400)

        with transaction.atomic():
            cliente = None
            if cliente_id:
                cliente = Clientes.objects.filter(
                    id=cliente_id, is_active=True, is_delete=False
                ).first()
                if not cliente:
                    return JsonResponse({"success": False, "message": "El cliente seleccionado no existe"}, status=400)

            subtotal_total = Decimal("0")
            descuento_total = Decimal("0")
            impuesto_15_total = Decimal("0")
            impuesto_18_total = Decimal("0")
            lineas = []

            for item in productos:
                cantidad = Decimal(str(item.get("cantidad", 0)))
                precio = Decimal(str(item.get("precio_venta", 0)))
                descuento = Decimal(str(item.get("descuento", 0)))
                if cantidad <= 0 or precio < 0:
                    raise ValueError("Las cantidades y precios de la cotización no son válidos")

                combo_id = item.get("combo_id")
                producto_id = item.get("id")
                producto = None
                combo = None
                if combo_id:
                    combo = Combos.objects.filter(id=combo_id, is_active=True, is_delete=False).first()
                    if not combo:
                        raise ValueError("Uno de los combos ya no está disponible")
                    codigo = combo.codigo_sku
                    nombre = combo.nombre
                else:
                    producto = Productos.objects.filter(id=producto_id, is_active=True, is_delete=False).first()
                    if not producto:
                        raise ValueError("Uno de los productos ya no está disponible")
                    codigo = producto.codigo_sku
                    nombre = producto.nombre

                impuesto_15 = Decimal(str(item.get("isv15_acumulable", 0)))
                impuesto_18 = Decimal(str(item.get("isv18_acumulable", 0)))
                subtotal = cantidad * precio
                subtotal_total += subtotal
                descuento_total += descuento
                impuesto_15_total += impuesto_15
                impuesto_18_total += impuesto_18
                lineas.append({
                    "producto": producto, "combo": combo, "codigo": codigo, "nombre": nombre,
                    "cantidad": cantidad, "precio": precio, "descuento": descuento,
                    "impuesto_15": impuesto_15, "impuesto_18": impuesto_18, "subtotal": subtotal,
                })

            cotizacion = Cotizacion.objects.create(
                numero_cotizacion=_numero_siguiente_cotizacion(),
                cliente=cliente,
                cliente_nombre=cliente_nombre if cliente else "",
                con_rtn=con_rtn if cliente else False,
                sucursal_id=perfil.ubicacion_id,
                subtotal=subtotal_total,
                descuento=descuento_total,
                impuesto_15=impuesto_15_total,
                impuesto_18=impuesto_18_total,
                total=subtotal_total + impuesto_15_total + impuesto_18_total - descuento_total,
                u_creo_id=request.user.id,
            )
            for linea in lineas:
                DetalleCotizacion.objects.create(
                    cotizacion=cotizacion,
                    producto=linea["producto"], combo=linea["combo"], codigo=linea["codigo"],
                    nombre=linea["nombre"], cantidad=linea["cantidad"],
                    precio_unitario=linea["precio"], descuento=linea["descuento"],
                    impuesto_15=linea["impuesto_15"], impuesto_18=linea["impuesto_18"],
                    subtotal=linea["subtotal"], u_creo_id=request.user.id,
                )

        return JsonResponse({
            "success": True,
            "id": cotizacion.id,
            "numero": cotizacion.numero_cotizacion,
            "pdf_url": reverse(
                "imprimir_cotizacion",
                kwargs={"token": cotizacion.documento_token},
            ),
        })
    except (ValueError, InvalidOperation, json.JSONDecodeError) as error:
        return JsonResponse({"success": False, "message": str(error)}, status=400)
    except PerfilUsuario.DoesNotExist:
        return JsonResponse({"success": False, "message": "El usuario no tiene un perfil configurado"}, status=400)
    except Exception as error:
        return JsonResponse({"success": False, "message": str(error)}, status=500)


@login_required
def imprimir_cotizacion(request, token):
    if not (_puede_generar_cotizaciones(request.user) or _puede_ver_cotizaciones(request.user)):
        raise PermissionDenied("No tiene permiso para imprimir cotizaciones")
    filtros_cotizacion = {
        "documento_token": token,
        "is_active": True,
        "is_delete": False,
    }
    cotizacion = get_object_or_404(
        Cotizacion.objects.select_related("cliente", "sucursal"),
        **filtros_cotizacion,
    )
    detalles = list(cotizacion.detalles.filter(is_active=True, is_delete=False).order_by("id"))
    configuracion = ConfiguracionEmpresa.objects.filter(
        is_active=True, is_delete=False
    ).first()
    simbolo_moneda = configuracion.simbolo_moneda if configuracion else "L."
    color_primario = HexColor(
        (configuracion.tienda_color_primario if configuracion else "#32877F")
        or "#32877F"
    )
    ancho, alto = A4
    margen = 38
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = alto - 48
    try:
        pdf.drawImage(_logo_empresa_pdf(), margen, y - 32, width=125, height=42, preserveAspectRatio=True, mask="auto")
    except Exception:
        pass
    pdf.setFont("Helvetica-Bold", 20)
    pdf.setFillColor(color_primario)
    pdf.drawRightString(ancho - margen, y, "COTIZACIÓN")
    pdf.setFillColor("#000000")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(ancho - margen, y - 18, cotizacion.numero_cotizacion)
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(ancho - margen, y - 33, _fecha_honduras(cotizacion.f_creacion).strftime("%d/%m/%Y %I:%M %p"))
    nombre_empresa = configuracion.nombre_comercial if configuracion else "Orvend Mart"
    datos_empresa = [nombre_empresa]
    if configuracion:
        datos_empresa.extend(textwrap.wrap(configuracion.direccion or "", width=34))
        if configuracion.rtn:
            datos_empresa.append(f"RTN: {configuracion.rtn}")
        if configuracion.email:
            datos_empresa.append(configuracion.email)
        if configuracion.telefono:
            datos_empresa.append(f"Tel.: {configuracion.telefono}")

    empresa_y = y - 45
    for indice, linea in enumerate(datos_empresa):
        pdf.setFont("Helvetica-Bold" if indice == 0 else "Helvetica", 9 if indice == 0 else 8)
        pdf.drawString(margen, empresa_y, linea)
        empresa_y -= 11
    y = min(y - 70, empresa_y - 9)
    pdf.setStrokeColor("#D8E5E2")
    pdf.line(margen, y, ancho - margen, y)
    y -= 22
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(margen, y, "CLIENTE")
    pdf.drawString(ancho / 2 + 5, y, "SUCURSAL")
    y -= 15
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margen, y, cotizacion.cliente_nombre or (cotizacion.cliente.nombre if cotizacion.cliente else "Cliente final"))
    pdf.drawString(ancho / 2 + 5, y, str(cotizacion.sucursal))
    if cotizacion.con_rtn and cotizacion.cliente and cotizacion.cliente.dni:
        y -= 14
        pdf.setFont("Helvetica", 9)
        pdf.drawString(margen, y, f"RTN: {cotizacion.cliente.dni}")
    y -= 30
    columnas = [
        margen,
        margen + 250,
        margen + 310,
        margen + 385,
        margen + 465,
        ancho - margen,
    ]
    tabla_superior = y
    y_fila = y - 32
    detalles_visibles = []
    for detalle in detalles:
        if y_fila < 205:
            break
        detalles_visibles.append(detalle)
        y_fila -= 20
    tabla_inferior = y_fila + 8
    pdf.setFillColor("#FFFFFF")
    pdf.setStrokeColor("#D8E5E2")
    pdf.roundRect(
        margen,
        tabla_inferior,
        ancho - (margen * 2),
        tabla_superior - tabla_inferior,
        7,
        fill=1,
        stroke=1,
    )
    pdf.setFillColor(color_primario)
    pdf.roundRect(margen, y - 18, ancho - (margen * 2), 18, 7, fill=1, stroke=0)
    pdf.rect(margen, y - 18, ancho - (margen * 2), 10, fill=1, stroke=0)
    pdf.setFillColor("#FFFFFF")
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(columnas[0] + 12, y - 12, "PRODUCTO")
    pdf.drawString(columnas[1] + 8, y - 12, "CANT.")
    pdf.drawString(columnas[2] + 8, y - 12, "P/U")
    pdf.drawString(columnas[3] + 8, y - 12, "DESCUENTO")
    pdf.drawString(columnas[4] + 8, y - 12, "TOTAL")
    y -= 32
    pdf.setFillColor("#263B36")
    pdf.setFont("Helvetica", 8)
    for indice, detalle in enumerate(detalles_visibles):
        nombre = textwrap.shorten(detalle.nombre, width=40, placeholder="...")
        total_linea = detalle.subtotal - detalle.descuento
        if indice % 2 == 0:
            pdf.setFillColor("#F4F8F7")
            pdf.rect(margen + 1, y - 15, ancho - (margen * 2) - 2, 19, fill=1, stroke=0)
        pdf.setStrokeColor("#E2ECE9")
        pdf.line(margen + 1, y - 8, ancho - margen - 1, y - 8)
        pdf.setFillColor("#263B36")
        pdf.drawString(columnas[0] + 12, y, nombre)
        pdf.drawString(columnas[1] + 8, y, f"{detalle.cantidad:g}")
        pdf.drawString(columnas[2] + 8, y, f"{simbolo_moneda} {detalle.precio_unitario:.2f}")
        pdf.drawString(columnas[3] + 8, y, f"{simbolo_moneda} {detalle.descuento:.2f}")
        pdf.drawRightString(columnas[5] - 12, y, f"{simbolo_moneda} {total_linea:.2f}")
        y -= 20
    # Los importes siempre se mantienen en la esquina inferior derecha,
    # independientemente de cuántos productos tenga la cotización.
    y = 150
    total_x = ancho - margen
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(total_x, y, f"Subtotal: {simbolo_moneda} {cotizacion.subtotal:.2f}")
    y -= 15
    pdf.drawRightString(total_x, y, f"Descuento: {simbolo_moneda} {cotizacion.descuento:.2f}")
    y -= 15
    pdf.drawRightString(total_x, y, f"ISV: {simbolo_moneda} {(cotizacion.impuesto_15 + cotizacion.impuesto_18):.2f}")
    y -= 22
    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(color_primario)
    pdf.drawRightString(total_x, y, f"TOTAL: {simbolo_moneda} {cotizacion.total:.2f}")
    dias_validez = configuracion.cotizacion_dias_validez if configuracion else 7
    fecha_vencimiento = _fecha_honduras(cotizacion.f_creacion) + timedelta(days=dias_validez)
    pdf.setFillColor("#71817D")
    pdf.setFont("Helvetica", 8)
    if configuracion and configuracion.mensaje_factura:
        pdf.drawString(
            margen,
            68,
            textwrap.shorten(configuracion.mensaje_factura, width=115, placeholder="..."),
        )
    pdf.drawString(
        margen,
        55,
        f"Cotización válida por {dias_validez} días (hasta {fecha_vencimiento.strftime('%d/%m/%Y')}).",
    )
    pdf.drawString(margen, 42, "Documento informativo. No es una factura ni genera un compromiso de pago.")
    pdf.showPage()
    pdf.save()
    respuesta = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    respuesta["Content-Disposition"] = f'inline; filename="{cotizacion.numero_cotizacion}.pdf"'
    return respuesta


@login_required
def cotizaciones_view(request):
    if not _puede_ver_cotizaciones(request.user):
        raise PermissionDenied("No tiene permiso para ver cotizaciones")

    cotizaciones = Cotizacion.objects.select_related("cliente", "sucursal").filter(
        is_active=True,
        is_delete=False,
    )
    busqueda = request.GET.get("buscar", "").strip()
    if busqueda:
        cotizaciones = cotizaciones.filter(
            Q(numero_cotizacion__icontains=busqueda)
            | Q(cliente_nombre__icontains=busqueda)
            | Q(cliente__nombre__icontains=busqueda)
            | Q(cliente__dni__icontains=busqueda)
        )

    cotizaciones = cotizaciones.annotate(
        cantidad_productos=Coalesce(
            Sum(
                "detalles__cantidad",
                filter=Q(detalles__is_active=True, detalles__is_delete=False),
            ),
            Value(Decimal("0"), output_field=DecimalField(max_digits=18, decimal_places=2)),
        )
    )
    page_obj = Paginator(cotizaciones.order_by("-f_creacion"), 10).get_page(
        request.GET.get("page", 1)
    )
    return render(request, "caja/cotizaciones.html", {
        "cotizaciones": page_obj,
        "page_obj": page_obj,
        "busqueda": busqueda,
        "mostrar_buscador": False,
        "mostrar_buscador_cotizaciones": True,
        "mostrar_codigo": False,
    })


@login_required
def busqueda_codigo(request, codigo):
    if not _puede_generar_cotizaciones(request.user):
        raise PermissionDenied("No tiene permiso para buscar productos en Caja")
    # ==========================================
    # VERIFICAR PERFIL Y UBICACIÓN
    # ==========================================
    try:
        perfil = PerfilUsuario.objects.get(
            usuarios=request.user
        )
    except PerfilUsuario.DoesNotExist:
        return JsonResponse(
            {"error": "El usuario no pertenece a ninguna ubicación"},
            status=400
        )

    if not perfil.ubicacion_id:
        return JsonResponse(
            {"error": "El usuario no pertenece a ninguna ubicación"},
            status=400
        )

    sucursal_id = perfil.ubicacion_id

    # ==========================================
    # UBICACIONES QUE COMPARTEN INVENTARIO
    # ==========================================
    ubicaciones = obtener_ubicaciones_inventario(
        sucursal_id
    )

    cotizacion = (
        Cotizacion.objects.prefetch_related("detalles")
        .filter(
            numero_cotizacion__iexact=codigo,
            sucursal_id=sucursal_id,
            is_active=True,
            is_delete=False,
        )
        .first()
    )
    if cotizacion:
        return JsonResponse({
            "es_cotizacion": True,
            "numero_cotizacion": cotizacion.numero_cotizacion,
            "productos": [
                {
                    "id": detalle.producto_id,
                    "combo_id": detalle.combo_id,
                    "es_combo": bool(detalle.combo_id),
                    "codigo_sku": detalle.codigo,
                    "nombre": detalle.nombre,
                    "cantidad": float(detalle.cantidad),
                    "precio_venta": float(detalle.precio_unitario),
                    "descuento": float(detalle.descuento),
                    "subtotal": float(detalle.subtotal),
                    "isv_15": float(detalle.impuesto_15),
                    "isv_18": float(detalle.impuesto_18),
                }
                for detalle in cotizacion.detalles.filter(is_active=True, is_delete=False)
            ],
        })

    # ==========================================
    # BUSCAR PRODUCTO
    # ==========================================
    try:
        producto = Productos.objects.get(
            codigo_sku=codigo,
            is_delete=False,
            is_active=True
        )

        # ==========================================
        # EXISTENCIA FÍSICA
        # TIENDA + BODEGA SI ESTÁN RELACIONADAS
        # ==========================================
        stock_disponible = _stock_disponible_caja(producto.id, ubicaciones)

        if stock_disponible <= 0:
            return JsonResponse(
                {
                    "error": "El producto no tiene existencia disponible en esta sucursal"
                },
                status=400
            )

        # ==========================================
        # CALCULAR ISV
        # ==========================================
        isv = producto.precio_venta * (
            Decimal(producto.impuesto) / Decimal(100)
        )

        data = {
            "id": producto.id,
            "codigo_sku": producto.codigo_sku,
            "nombre": producto.nombre,
            "precio_venta": producto.precio_venta,
            "precio_venta_min": producto.precio_venta_min,
            "precio_venta_max": producto.precio_venta_max,
            "id_categoria": producto.categoria_id,
            "isv": isv,
            "tipos_isv": producto.impuesto,
            "stock": _stock_para_mostrar(stock_disponible),
        }

        # ==========================================
        # DESCUENTO POR CANTIDAD
        # ==========================================
        cantidad_descuento = descuento_cantidad(data)

        if cantidad_descuento["lleva"] > 0:
            data["lleva"] = cantidad_descuento["lleva"]
            data["paga"] = cantidad_descuento["paga"]
            data["descuentos"] = 0
            data["acumulable"] = cantidad_descuento["es_acumulable"]
        else:
            descuento = valor_descuento(data)
            data["lleva"] = 0
            data["paga"] = 0
            data["descuentos"] = descuento.get("valor", 0)
            data["acumulable"] = descuento.get(
                "es_acumulable",
                False
            )

        return JsonResponse(data)

    except Productos.DoesNotExist:
        combo = Combos.objects.filter(
            codigo_sku=codigo,
            is_delete=False,
            is_active=True,
        ).first()
        if not combo:
            return JsonResponse({"error": "Producto o combo no encontrado"}, status=404)
        datos_combo = _datos_combo_caja(combo, ubicaciones)
        if not datos_combo:
            return JsonResponse(
                {"error": "El combo no tiene existencias disponibles en esta sucursal"},
                status=400,
            )
        return JsonResponse(datos_combo)


@login_required
def busqueda_nombre(request, producto):
    if not _puede_generar_cotizaciones(request.user):
        raise PermissionDenied("No tiene permiso para buscar productos en Caja")
    # ==========================================
    # VERIFICAR PERFIL Y UBICACIÓN
    # ==========================================
    try:
        perfil = PerfilUsuario.objects.get(
            usuarios=request.user
        )
    except PerfilUsuario.DoesNotExist:
        return JsonResponse(
            {"error": "El usuario no pertenece a ninguna ubicación"},
            status=400
        )

    if not perfil.ubicacion_id:
        return JsonResponse(
            {"error": "El usuario no pertenece a ninguna ubicación"},
            status=400
        )

    sucursal_id = perfil.ubicacion_id

    # ==========================================
    # UBICACIONES QUE COMPARTEN INVENTARIO
    # ==========================================
    ubicaciones = obtener_ubicaciones_inventario(
        sucursal_id
    )

    # ==========================================
    # VALIDAR BÚSQUEDA
    # ==========================================
    if not producto or len(producto) < 2:
        return JsonResponse([], safe=False)

    # ==========================================
    # BUSCAR PRODUCTOS
    # ==========================================
    items = (
        Productos.objects.filter(
            is_delete=False,
            is_active=True,
            nombre__icontains=producto,
        )
        .distinct()
        .order_by("nombre")[:20]
    )

    data = []

    for c in items:
        # ==========================================
        # EXISTENCIA FÍSICA
        # TIENDA + BODEGA SI ESTÁN RELACIONADAS
        # ==========================================
        stock_disponible = _stock_disponible_caja(c.id, ubicaciones)

        # ==========================================
        # SI NO HAY STOCK DISPONIBLE
        # NO MOSTRAR PRODUCTO
        # ==========================================
        if stock_disponible <= 0:
            continue

        # ==========================================
        # VALORES INICIALES
        # ==========================================
        lleva = 0
        paga = 0
        descuento = 0
        es_acumulable = False

        # ==========================================
        # DESCUENTO POR CANTIDAD
        # ==========================================
        cantidad_descuento = descuento_cantidad(
            data={
                "id": c.id
            }
        )

        if cantidad_descuento["lleva"] > 0:
            lleva = cantidad_descuento["lleva"]
            paga = cantidad_descuento["paga"]
            es_acumulable = cantidad_descuento["es_acumulable"]
        else:
            descuento_data = valor_descuento(
                {
                    "id": c.id,
                    "id_categoria": c.categoria_id,
                    "precio_venta": c.precio_venta,
                }
            )

            descuento = descuento_data["valor"]
            es_acumulable = descuento_data["es_acumulable"]

        # ==========================================
        # DATOS DEL PRODUCTO
        # ==========================================
        producto_data = {
            "id": c.id,
            "codigo_sku": c.codigo_sku,
            "nombre": c.nombre,
            "precio_venta": c.precio_venta,
            "precio_venta_min": c.precio_venta_min,
            "precio_venta_max": c.precio_venta_max,
            "lleva": lleva,
            "paga": paga,
            "descuento": descuento,
            "es_acumulable": es_acumulable,
            "isv": c.precio_venta * (
                Decimal(c.impuesto) / Decimal(100)
            ),
            "tipos_isv": c.impuesto,
            "stock": _stock_para_mostrar(stock_disponible),
        }

        data.append(producto_data)

    combos = Combos.objects.filter(
        is_delete=False,
        is_active=True,
        nombre__icontains=producto,
    ).order_by("nombre")[:20]
    for combo in combos:
        datos_combo = _datos_combo_caja(combo, ubicaciones)
        if datos_combo:
            data.append(datos_combo)

    return JsonResponse(
        data,
        safe=False
    )


def _desglosar_precio_venta_incluye_isv(precio_venta, porcentaje_isv):
    """Separa el precio final configurado en subtotal e ISV.

    En Caja el precio de venta ya es el importe que paga el cliente. Por ello
    el ISV se calcula sobre ese importe y no se vuelve a sumar al total.
    """
    precio = Decimal(str(precio_venta or 0))
    porcentaje = Decimal(str(porcentaje_isv or 0))
    impuesto = precio * porcentaje / Decimal("100")
    return precio - impuesto, impuesto


@login_required
@require_http_methods(["POST"])
@permission_required("manager.operar_caja", raise_exception=True)
def guardar_compra(request):
    try:
        with transaction.atomic():

            caja_abierta_hoy = (
                CajaAC.objects.select_for_update()
                .filter(
                    usuario_id=request.user.id,
                    estado="abierta",
                    fecha_apertura__date=timezone.localdate(),
                    is_active=True,
                    is_delete=False,
                )
                .exists()
            )
            if not caja_abierta_hoy:
                raise Exception(
                    "Debes abrir una caja del día antes de realizar una venta."
                )

            # =====================================================
            # PERFIL / UBICACIONES COMPARTIDAS
            # =====================================================

            perfil = PerfilUsuario.objects.get(
                usuarios=request.user
            )

            sucursal_id = perfil.ubicacion_id

            ubicaciones_inventario = obtener_ubicaciones_inventario(
                sucursal_id
            )

            if not ubicaciones_inventario:
                ubicaciones_inventario = [sucursal_id]

            # =====================================================
            # DATOS RECIBIDOS
            # =====================================================

            data = json.loads(request.body)

            pago = data.get("pagos", [])
            productos = data.get("productos", [])
            tarjeta = data.get("tarjeta", [])
            cliente = data.get("cliente", {})
            nota_credito_id = data.get("nota_credito_id")

            if not pago:
                raise Exception("No se recibieron los datos de pago")

            if not productos:
                raise Exception("No se recibieron productos")

            tipo_pago = pago[0].get("tipo_pago")
            if tipo_pago not in {"contado", "tarjeta", "credito", "depostivo", "cheque"}:
                raise Exception("El tipo de pago seleccionado no es válido")

            try:
                total_original = Decimal(str(pago[0].get("total_original")))
            except (InvalidOperation, TypeError, ValueError):
                raise Exception("El total de la venta no es válido")

            monto_nota_credito = Decimal("0")
            nota_credito = None
            if nota_credito_id:
                nota_credito = (
                    DevolucionVenta.objects.select_for_update()
                    .select_related("venta__sucursal")
                    .filter(
                        id=nota_credito_id,
                        estado=DevolucionVenta.Estado.DISPONIBLE,
                        is_active=True,
                        is_delete=False,
                    )
                    .first()
                )
                if not nota_credito:
                    raise Exception("La nota de crédito ya no está disponible")

                if (
                    not request.user.is_superuser
                    and nota_credito.venta.sucursal_id != sucursal_id
                ):
                    raise Exception("La nota de crédito no pertenece a esta sucursal")

                monto_nota_credito = nota_credito.monto_total
                if total_original < monto_nota_credito:
                    raise Exception(
                        "La compra debe ser igual o mayor al valor de la nota de crédito"
                    )

            total_a_pagar = total_original - monto_nota_credito
            pago[0]["total"] = total_a_pagar

            if tipo_pago == "credito":
                if not request.user.has_perm("manager.view_cuentasporcobrar"):
                    raise Exception(
                        "No tiene permiso para registrar ventas a crédito"
                    )

                cliente_id = cliente.get("id")

                if not cliente_id:
                    raise Exception(
                        "Debe seleccionar un cliente para realizar una venta a crédito"
                    )

                # Bloquea el cliente durante la validación para que dos ventas
                # simultáneas no puedan exceder su límite de crédito.
                cliente_credito = Clientes.objects.select_for_update().filter(
                    id=cliente_id,
                    is_active=True,
                    is_delete=False,
                ).first()

                if not cliente_credito:
                    raise Exception("El cliente seleccionado no existe o está inactivo")

                if not cliente_credito.d_credito or cliente_credito.d_credito <= 0:
                    raise Exception(
                        "El cliente no tiene días de crédito configurados"
                    )

                if (
                    cliente_credito.max_credito is None
                    or cliente_credito.max_credito <= Decimal("0")
                ):
                    raise Exception(
                        "El cliente no tiene un límite de crédito configurado"
                    )

                try:
                    monto_nueva_venta = Decimal(str(pago[0].get("total")))
                except (InvalidOperation, TypeError, ValueError):
                    raise Exception("El total de la venta a crédito no es válido")

                if monto_nueva_venta <= Decimal("0"):
                    raise Exception("El total de la venta a crédito debe ser mayor a cero")

                cuentas_pendientes = list(
                    CuentasPorCobrar.objects.select_for_update().filter(
                        cliente=cliente_credito,
                        is_active=True,
                        is_delete=False,
                        monto_pendiente__gt=0,
                        estado__in=[
                            EstadoCuenta.PENDIENTE,
                            EstadoCuenta.PARCIAL,
                        ],
                    )
                )

                monto_en_mora = sum(
                    (
                        cuenta.monto_pendiente
                        for cuenta in cuentas_pendientes
                        if cuenta.fecha_vencimiento < timezone.now()
                    ),
                    Decimal("0"),
                )

                if monto_en_mora > Decimal("0"):
                    raise Exception(
                        f"El cliente tiene una mora de L. {monto_en_mora:.2f}"
                    )

                credito_utilizado = sum(
                    (cuenta.monto_pendiente for cuenta in cuentas_pendientes),
                    Decimal("0"),
                )

                credito_resultante = credito_utilizado + monto_nueva_venta

                if credito_resultante > cliente_credito.max_credito:
                    credito_disponible = max(
                        cliente_credito.max_credito - credito_utilizado,
                        Decimal("0"),
                    )
                    raise Exception(
                        "El cliente excede su límite de crédito. "
                        f"Límite: L. {cliente_credito.max_credito:.2f}; "
                        f"disponible: L. {credito_disponible:.2f}"
                    )

            # =====================================================
            # NUMERO DE FACTURA
            # =====================================================

            # El consecutivo es único en toda la instalación. Se bloquea una
            # fila compartida antes de leer MAX()+1 para que dos cajeros no
            # puedan reservar el mismo número de factura al mismo tiempo.
            ultima_factura_bloqueada = (
                facturas_cai.objects.select_for_update()
                .order_by("-numero_factura")
                .first()
            )
            if ultima_factura_bloqueada is None:
                # En una instalación sin facturas aún, la configuración es
                # el candado común que evita la carrera de la primera venta.
                ConfiguracionEmpresa.objects.select_for_update().filter(
                    is_delete=False
                ).order_by("id").first()

            sat = datos_sat.objects.select_for_update().filter(
                id_sucursal_id=sucursal_id,
                is_active=True,
                is_delete=False,
            ).first()

            numero_factura = None
            id_cai = None
            es_sat = False

            if sat:
                hoy = timezone.now().date()

                if sat.fecha_de_vencimiento.date() < hoy:
                    raise Exception(
                        f"El CAI {sat.numero_cai} está vencido"
                    )

                ultimo_numero = (
                    facturas_cai.objects
                    .filter(id_cai=sat)
                    .aggregate(
                        Max("numero_factura")
                    )["numero_factura__max"]
                )

                if ultimo_numero is None:
                    numero_factura = sat.rango_inicial
                else:
                    numero_factura = ultimo_numero + 1

                if numero_factura > sat.rango_final:
                    raise Exception(
                        f"El CAI {sat.numero_cai} agotó su rango autorizado"
                    )

                id_cai = sat
                es_sat = True

            else:
                ultimo_numero = (
                    facturas_cai.objects
                    .aggregate(
                        Max("numero_factura")
                    )["numero_factura__max"]
                    or 100000000
                )

                numero_factura = ultimo_numero + 1

            # =====================================================
            # CREAR FACTURA
            # =====================================================

            factura_cai = facturas_cai.objects.create(
                numero_factura=numero_factura,
                id_cai=id_cai,
                es_sat=es_sat,
                u_creo_id=request.user.id,
            )

            # =====================================================
            # TOTALES
            # =====================================================

            costo_total_venta = Decimal("0")
            utilidad_total_venta = Decimal("0")
            subtotal_venta = Decimal("0")
            impuesto_15_venta = Decimal("0")
            impuesto_18_venta = Decimal("0")
            descuento_venta = Decimal("0")

            # =====================================================
            # CREAR VENTA
            # =====================================================

            tipo_venta = (
                Ventas.TIPO_VENTA_CREDITO
                if tipo_pago == "credito"
                else Ventas.TIPO_VENTA_CONTADO
            )

            venta = Ventas.objects.create(
                id_factura_cai=factura_cai,
                id_cliente_id=cliente.get("id"),
                sucursal_id=sucursal_id,
                subtotal=pago[0].get("subtotal"),
                impuesto_15=pago[0].get("isv15"),
                impuesto_18=pago[0].get("isv18"),
                descuento=pago[0].get("descuento"),
                nota_credito=monto_nota_credito,
                con_rtn=bool(cliente.get("con_rtn")),
                total=pago[0].get("total"),
                tipo_pago=tipo_pago,
                tipo_venta=tipo_venta,
                costo_total=0,
                utilidad_total=0,
                u_creo_id=request.user.id,
            )

            if nota_credito:
                nota_credito.estado = DevolucionVenta.Estado.USADA
                nota_credito.venta_aplicada = venta
                nota_credito.fecha_uso = timezone.now()
                nota_credito.u_modifico_id = request.user.id
                nota_credito.save(
                    update_fields=[
                        "estado",
                        "venta_aplicada",
                        "fecha_uso",
                        "u_modifico_id",
                    ]
                )

            # =====================================================
            # TARJETA
            # =====================================================

            if venta.tipo_pago == "tarjeta":

                if not tarjeta:
                    raise Exception(
                        "Información de tarjeta no recibida"
                    )

                digitos = (
                    tarjeta[0].get("digitos") or ""
                ).strip()

                autorizacion = (
                    tarjeta[0].get("numero_autorizacion") or ""
                ).strip()

                if not digitos:
                    raise Exception(
                        "Debe ingresar los últimos 4 dígitos"
                    )

                if not digitos.isdigit():
                    raise Exception(
                        "Los últimos 4 dígitos deben ser numéricos"
                    )

                if len(digitos) != 4:
                    raise Exception(
                        "Los últimos 4 dígitos deben contener exactamente 4 números"
                    )

                if not autorizacion:
                    raise Exception(
                        "Debe ingresar el número de autorización"
                    )

                tarjetas.objects.create(
                    id_factura=venta,
                    digitos=digitos,
                    numero_autorizacion=autorizacion,
                    u_creo_id=request.user.id,
                )

            if venta.tipo_pago == "credito":
                CuentasPorCobrar.objects.create(
                    cliente=cliente_credito,
                    venta=venta,
                    monto_total=venta.total,
                    monto_pendiente=venta.total,
                    fecha_vencimiento=(
                        timezone.now()
                        + timedelta(days=cliente_credito.d_credito)
                    ),
                    estado=EstadoCuenta.PENDIENTE,
                    u_creo_id=request.user.id,
                )

            # =====================================================
            # DETALLE DE PRODUCTOS
            # =====================================================

            for p in productos:

                producto_id = p.get("id")
                combo_id = p.get("combo_id")

                cantidad_vendida = Decimal(
                    str(p.get("cantidad"))
                )

                precio_venta = Decimal(
                    str(p.get("precio_venta"))
                )

                if cantidad_vendida <= 0:
                    raise Exception(
                        f"La cantidad debe ser mayor a cero para "
                        f"{p.get('nombre')}"
                    )

                if combo_id:
                    combo = (
                        Combos.objects.prefetch_related("detalles__producto")
                        .filter(id=combo_id, is_active=True, is_delete=False)
                        .first()
                    )
                    if not combo or not combo.detalles.exists():
                        raise Exception("El combo no existe, está inactivo o no tiene productos")
                    if precio_venta != combo.precio_venta:
                        if not request.user.has_perm("manager.modificar_precio_caja"):
                            raise Exception("No tiene permiso para modificar precios en caja")
                        if precio_venta < combo.precio_venta_min or precio_venta > combo.precio_venta_max:
                            raise Exception("El precio del combo está fuera del rango permitido")
                    producto = None
                    productos_inventario = [
                        {"producto": detalle.producto, "cantidad": detalle.cantidad * cantidad_vendida}
                        for detalle in combo.detalles.all()
                    ]
                else:
                    producto = (
                        Productos.objects
                        .filter(id=producto_id, is_active=True, is_delete=False)
                        .first()
                    )
                    if not producto:
                        raise Exception(f"El producto {producto_id} no existe o está inactivo")
                    if precio_venta != producto.precio_venta:
                        if not request.user.has_perm("manager.modificar_precio_caja"):
                            raise Exception("No tiene permiso para modificar precios en caja")
                        if (
                            producto.precio_venta_min is not None
                            and precio_venta < producto.precio_venta_min
                        ):
                            raise Exception(
                                f"El precio de {producto.nombre} no puede ser menor a "
                                f"L. {producto.precio_venta_min:.2f}"
                            )
                        if (
                            producto.precio_venta_max is not None
                            and precio_venta > producto.precio_venta_max
                        ):
                            raise Exception(
                                f"El precio de {producto.nombre} no puede ser mayor a "
                                f"L. {producto.precio_venta_max:.2f}"
                            )
                    productos_inventario = obtener_productos_relacionados(
                        producto, cantidad_vendida
                    )

                costo_total_producto = Decimal("0")

                # =================================================
                # PROCESAR INVENTARIO
                # =================================================

                for item in productos_inventario:

                    producto_inventario = item["producto"]

                    cantidad_a_rebajar = Decimal(
                        item["cantidad"]
                    )

                    if cantidad_a_rebajar <= 0:
                        continue

                    # =================================================
                    # STOCK COMPARTIDO
                    # =================================================

                    # =================================================
                    # LOTES FIFO COMPARTIDOS BLOQUEADOS
                    # =================================================
                    # El bloqueo se toma antes de comprobar el saldo. Así,
                    # dos cajeros que intenten vender la última unidad no
                    # pueden leer el mismo lote y descontarlo dos veces.
                    lotes = list(
                        Inventarios.objects
                        .select_for_update()
                        .filter(
                            producto=producto_inventario,
                            ubicacion_id__in=ubicaciones_inventario,
                            is_active=True,
                            is_delete=False,
                            cantidad__gt=0,
                        )
                        .order_by("f_creacion", "id")
                    )

                    stock_total = sum(
                        (Decimal(str(lote.cantidad)) for lote in lotes),
                        Decimal("0"),
                    )
                    stock_reservado = (
                        ReservaInventario.objects.filter(
                            producto=producto_inventario,
                            ubicacion_id__in=ubicaciones_inventario,
                            estado=ReservaInventario.Estado.RESERVADA,
                            is_delete=False,
                        ).aggregate(total=Sum("cantidad"))["total"]
                        or Decimal("0")
                    )
                    stock_disponible = max(
                        stock_total - Decimal(str(stock_reservado)), Decimal("0")
                    )

                    if stock_disponible < cantidad_a_rebajar:
                        raise StockInsuficienteError(
                            producto_inventario,
                            stock_disponible,
                            cantidad_a_rebajar,
                        )

                    cantidad_necesaria = cantidad_a_rebajar

                    # =================================================
                    # REBAJAR LOTES
                    # =================================================

                    for lote in lotes:

                        if cantidad_necesaria <= 0:
                            break

                        cantidad_consumida = min(
                            lote.cantidad,
                            cantidad_necesaria,
                        )

                        # =================================================
                        # COSTO DEL LOTE
                        # =================================================

                        detalle_compra = (
                            DetalleCompra.objects
                            .filter(
                                compra_id=lote.compra_id,
                                producto_id=lote.producto_id,
                            )
                            .first()
                        )

                        if detalle_compra:

                            costo_unitario_lote = (
                                detalle_compra.precio_compra
                            )

                        else:

                            relaciones_hacia_padre = (
                                ProductosRel.objects
                                .filter(
                                    producto_relacionado=producto_inventario,
                                    is_active=True,
                                    is_delete=False,
                                )
                                .select_related(
                                    "producto_master"
                                )
                            )

                            costo_unitario_lote = None

                            for relacion in relaciones_hacia_padre:

                                producto_padre = (
                                    relacion.producto_master
                                )

                                detalle_padre = (
                                    DetalleCompra.objects
                                    .filter(
                                        compra_id=lote.compra_id,
                                        producto_id=producto_padre.id,
                                    )
                                    .first()
                                )

                                if detalle_padre:

                                    equivalencia_padre = (
                                        Decimal(
                                            producto_padre.equival_unid
                                        )
                                        if producto_padre.equival_unid
                                        else Decimal("1")
                                    )

                                    equivalencia_hijo = (
                                        Decimal(
                                            producto_inventario.equival_unid
                                        )
                                        if producto_inventario.equival_unid
                                        else Decimal("1")
                                    )

                                    costo_unitario_lote = (
                                        Decimal(
                                            detalle_padre.precio_compra
                                        )
                                        * equivalencia_hijo
                                        / equivalencia_padre
                                    )

                                    break

                            if costo_unitario_lote is None:
                                raise Exception(
                                    f"No existe costo registrado para "
                                    f"{producto_inventario.nombre} "
                                    f"en el lote {lote.id}"
                                )

                        # =================================================
                        # COSTO
                        # =================================================

                        costo_total_producto += (
                            cantidad_consumida
                            * costo_unitario_lote
                        )

                        # =================================================
                        # STOCK ANTES
                        # =================================================

                        stock_anterior = lote.cantidad

                        # =================================================
                        # REBAJAR LOTE
                        # =================================================

                        lote.cantidad -= cantidad_consumida

                        cantidad_necesaria -= cantidad_consumida

                        lote.save(
                            update_fields=["cantidad"]
                        )

                        # =================================================
                        # STOCK RESULTANTE
                        # =================================================

                        stock_resultante = (
                            Inventarios.objects
                            .filter(
                                producto=producto_inventario,
                                ubicacion_id=lote.ubicacion_id,
                            )
                            .aggregate(
                                total=Sum("cantidad")
                            )["total"]
                            or Decimal("0")
                        )

                        # =================================================
                        # MOVIMIENTO
                        # =================================================

                        MovimientoInventario.objects.create(
                            tipo_movimiento=TipoMovimientoInventario.SALIDA_VENTA,
                            producto=producto_inventario,
                            ubicacion_origen_id=lote.ubicacion_id,
                            cantidad=cantidad_consumida,
                            stock_anterior=stock_anterior,
                            stock_resultante=stock_resultante,
                        )

                    # =================================================
                    # VALIDAR SALIDA
                    # =================================================

                    if cantidad_necesaria > 0:
                        raise Exception(
                            f"No fue posible completar la salida de "
                            f"{producto_inventario.nombre}. "
                            f"Faltan {cantidad_necesaria} unidades."
                        )

                # =================================================
                # PRECIO FINAL, ISV Y UTILIDAD
                # =================================================

                porcentaje_isv = (
                    Decimal(str(producto.impuesto or 0))
                    if producto
                    else Decimal("0")
                )
                precio_sin_isv, impuesto_unitario = (
                    _desglosar_precio_venta_incluye_isv(
                        precio_venta, porcentaje_isv
                    )
                )
                subtotal_linea = cantidad_vendida * precio_sin_isv
                impuesto_linea = cantidad_vendida * impuesto_unitario
                descuento_linea = Decimal(str(p.get("descuento", 0)))

                if porcentaje_isv == Decimal("15"):
                    impuesto_15_linea = impuesto_linea
                    impuesto_18_linea = Decimal("0")
                elif porcentaje_isv == Decimal("18"):
                    impuesto_15_linea = Decimal("0")
                    impuesto_18_linea = impuesto_linea
                else:
                    impuesto_15_linea = Decimal("0")
                    impuesto_18_linea = Decimal("0")

                costo_promedio = (
                    costo_total_producto /
                    cantidad_vendida
                )

                utilidad_unitaria = (
                    precio_sin_isv -
                    costo_promedio
                )

                utilidad_total = (
                    utilidad_unitaria *
                    cantidad_vendida
                )

                costo_total_venta += (
                    costo_total_producto
                )

                utilidad_total_venta += (
                    utilidad_total
                )
                subtotal_venta += subtotal_linea
                impuesto_15_venta += impuesto_15_linea
                impuesto_18_venta += impuesto_18_linea
                descuento_venta += descuento_linea

                # =================================================
                # DETALLE DE VENTA
                # =================================================

                DetalleVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    combo_id=combo_id if combo_id else None,
                    cantidad=cantidad_vendida,
                    precio_unitario=precio_venta,
                    costo_unitario=costo_promedio,
                    utilidad_unitaria=utilidad_unitaria,
                    utilidad_total=utilidad_total,
                    descuento=descuento_linea,
                    subtotal=subtotal_linea,
                    monto_devuelto=Decimal("0"),
                    impuesto_15=impuesto_15_linea,
                    impuesto_18=impuesto_18_linea,
                    u_creo_id=request.user.id,
                )

            # =====================================================
            # ACTUALIZAR VENTA
            # =====================================================

            venta.costo_total = costo_total_venta
            venta.utilidad_total = utilidad_total_venta
            venta.subtotal = subtotal_venta
            venta.impuesto_15 = impuesto_15_venta
            venta.impuesto_18 = impuesto_18_venta
            venta.descuento = descuento_venta
            venta.total = (
                subtotal_venta
                + impuesto_15_venta
                + impuesto_18_venta
                - descuento_venta
                - monto_nota_credito
            )

            venta.save(
                update_fields=[
                    "costo_total",
                    "utilidad_total",
                    "subtotal",
                    "impuesto_15",
                    "impuesto_18",
                    "descuento",
                    "total",
                ]
            )

            # =====================================================
            # ENVÍO DE FACTURA POR WHATSAPP
            # =====================================================
            # n8n recibe una URL firmada temporal. La factura normal conserva
            # su protección de sesión y permisos dentro del ERP.
            cliente_factura = venta.id_cliente
            if (
                cliente_factura
                and cliente_factura.enviar_factura_whatsapp
                and cliente_factura.telefono
            ):
                token_descarga = signing.dumps(
                    {"factura_token": str(factura_cai.documento_token)},
                    salt="manager.factura-n8n-v1",
                    compress=True,
                )
                ruta_factura = reverse(
                    "descargar_factura_n8n",
                    kwargs={"token": factura_cai.documento_token},
                )
                base_publica = settings.FACTURA_PUBLIC_BASE_URL
                factura_url = (
                    urljoin(base_publica.rstrip("/") + "/", ruta_factura.lstrip("/"))
                    if base_publica
                    else request.build_absolute_uri(ruta_factura)
                )
                factura_url = f"{factura_url}?{urlencode({'access_token': token_descarga})}"
                nombre_cliente = (
                    (cliente_factura.empresa or cliente_factura.nombre_completo)
                    if venta.con_rtn
                    else (cliente_factura.nombre_completo or cliente_factura.empresa)
                )
                transaction.on_commit(
                    lambda: enviar_factura_por_whatsapp(
                        nombre_cliente=nombre_cliente or "Cliente",
                        telefono=cliente_factura.telefono,
                        factura_url=factura_url,
                        numero_factura=factura_cai.numero_factura,
                    )
                )

            # =====================================================
            # RESPUESTA
            # =====================================================

            return JsonResponse(
                {
                    "success": True,
                    "id_factura": factura_cai.id,
                    "numero_factura": numero_factura,
                    "es_sat": es_sat,
                    "pdf_url": reverse(
                        "imprimir_factura",
                        kwargs={"token": factura_cai.documento_token},
                    ),
                }
            )

    except StockInsuficienteError as e:
        return JsonResponse(
            {
                "success": False,
                "message": str(e),
                "stock_insuficiente": {
                    "producto_id": e.producto_id,
                    "producto_nombre": e.producto_nombre,
                    "disponible": str(_stock_para_mostrar(e.disponible)),
                    "requerido": str(e.requerido),
                },
            },
            status=409,
        )
    except Exception as e:

        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500,
        )

        
def _generar_factura_pagina_pdf(factura_cai, venta, detalles, cajero, configuracion):
    """Factura A4 con el mismo lenguaje visual que las cotizaciones."""
    ancho, alto = A4
    margen = 38
    color = HexColor(configuracion.tienda_color_primario or "#32877F")
    simbolo_moneda = configuracion.simbolo_moneda
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = alto - 48

    try:
        pdf.drawImage(
            _logo_empresa_pdf(), margen, y - 32, width=125, height=42,
            preserveAspectRatio=True, mask="auto",
        )
    except Exception:
        pass

    pdf.setFillColor(color)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawRightString(ancho - margen, y, "FACTURA")
    pdf.setFillColor("#000000")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(ancho - margen, y - 18, f"No. {factura_cai.numero_factura}")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(
        ancho - margen, y - 33,
        _fecha_honduras(venta.f_creacion).strftime("%d/%m/%Y %I:%M %p"),
    )
    pdf.setFont("Helvetica", 8)
    if factura_cai.es_sat and factura_cai.id_cai:
        pdf.drawRightString(ancho - margen, y - 47, f"CAI: {factura_cai.id_cai.numero_cai}")
    else:
        pdf.drawRightString(ancho - margen, y - 47, "Factura personalizada")

    datos_empresa = [configuracion.nombre_comercial]
    datos_empresa.extend(textwrap.wrap(configuracion.direccion or "", width=34))
    if configuracion.rtn:
        datos_empresa.append(f"RTN: {configuracion.rtn}")
    if configuracion.email:
        datos_empresa.append(configuracion.email)
    if configuracion.telefono:
        datos_empresa.append(f"Tel.: {configuracion.telefono}")
    empresa_y = y - 45
    for indice, linea in enumerate(datos_empresa):
        pdf.setFont("Helvetica-Bold" if indice == 0 else "Helvetica", 9 if indice == 0 else 8)
        pdf.drawString(margen, empresa_y, linea)
        empresa_y -= 11
    y = min(y - 70, empresa_y - 9)

    pdf.setStrokeColor("#D8E5E2")
    pdf.line(margen, y, ancho - margen, y)
    y -= 20
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(margen, y, "CLIENTE")
    pdf.drawString(ancho / 2 + 5, y, "SUCURSAL")
    y -= 15
    pdf.setFont("Helvetica", 10)
    if venta.id_cliente:
        cliente = (venta.id_cliente.empresa or venta.id_cliente.nombre_completo) if venta.con_rtn else venta.id_cliente.nombre_completo
    else:
        cliente = "Consumidor final"
    pdf.drawString(margen, y, cliente)
    pdf.drawString(ancho / 2 + 5, y, str(venta.sucursal))
    if venta.con_rtn and venta.id_cliente and venta.id_cliente.dni:
        y -= 14
        pdf.setFont("Helvetica", 9)
        pdf.drawString(margen, y, f"RTN: {venta.id_cliente.dni}")
    y -= 30

    columnas = [
        margen,
        margen + 250,
        margen + 310,
        margen + 385,
        margen + 465,
        ancho - margen,
    ]
    tabla_superior = y
    y_fila = y - 32
    detalles_visibles = []
    for detalle in detalles:
        if y_fila < 205:
            break
        detalles_visibles.append(detalle)
        y_fila -= 20
    tabla_inferior = y_fila + 8
    pdf.setFillColor("#FFFFFF")
    pdf.setStrokeColor("#D8E5E2")
    pdf.roundRect(margen, tabla_inferior, ancho - (margen * 2), tabla_superior - tabla_inferior, 7, fill=1, stroke=1)
    pdf.setFillColor(color)
    pdf.roundRect(margen, tabla_superior - 18, ancho - (margen * 2), 18, 7, fill=1, stroke=0)
    pdf.rect(margen, tabla_superior - 18, ancho - (margen * 2), 10, fill=1, stroke=0)
    pdf.setFillColor("#FFFFFF")
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(columnas[0] + 12, tabla_superior - 12, "PRODUCTO")
    pdf.drawString(columnas[1] + 8, tabla_superior - 12, "CANT.")
    pdf.drawString(columnas[2] + 8, tabla_superior - 12, "P/U")
    pdf.drawString(columnas[3] + 8, tabla_superior - 12, "DESCUENTO")
    pdf.drawString(columnas[4] + 8, tabla_superior - 12, "TOTAL")

    y = tabla_superior - 32
    pdf.setFillColor("#263B36")
    pdf.setFont("Helvetica", 8)
    for indice, detalle in enumerate(detalles_visibles):
        nombre = detalle.combo.nombre if detalle.combo_id else detalle.producto.nombre
        total_linea = (detalle.cantidad * detalle.precio_unitario) - detalle.descuento
        if indice % 2 == 0:
            pdf.setFillColor("#F4F8F7")
            pdf.rect(margen + 1, y - 15, ancho - (margen * 2) - 2, 19, fill=1, stroke=0)
        pdf.setStrokeColor("#E2ECE9")
        pdf.line(margen + 1, y - 8, ancho - margen - 1, y - 8)
        pdf.setFillColor("#263B36")
        pdf.drawString(columnas[0] + 12, y, textwrap.shorten(nombre, width=40, placeholder="..."))
        pdf.drawString(columnas[1] + 8, y, f"{detalle.cantidad:g}")
        pdf.drawString(columnas[2] + 8, y, f"{simbolo_moneda} {detalle.precio_unitario:.2f}")
        pdf.drawString(columnas[3] + 8, y, f"{simbolo_moneda} {detalle.descuento:.2f}")
        pdf.drawRightString(columnas[5] - 12, y, f"{simbolo_moneda} {total_linea:.2f}")
        y -= 20

    total_x = ancho - margen
    y = 150
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(total_x, y, f"Subtotal: {simbolo_moneda} {venta.subtotal:.2f}")
    y -= 15
    pdf.drawRightString(total_x, y, f"Descuento: {simbolo_moneda} {venta.descuento:.2f}")
    y -= 15
    pdf.drawRightString(total_x, y, f"ISV: {simbolo_moneda} {(venta.impuesto_15 + venta.impuesto_18):.2f}")
    y -= 22
    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(color)
    pdf.drawRightString(total_x, y, f"TOTAL: {simbolo_moneda} {venta.total:.2f}")
    pdf.setFillColor("#71817D")
    pdf.setFont("Helvetica", 8)
    if configuracion.mensaje_factura:
        pdf.drawString(margen, 52, textwrap.shorten(configuracion.mensaje_factura, width=115, placeholder="..."))
    pdf.drawString(margen, 39, f"Cajero: {cajero}")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def imprimir_factura(request, token, es_integracion=False):
    if not es_integracion and not (
        request.user.is_superuser
        or _puede_operar_caja(request.user)
        or request.user.has_perm("manager.view_ventas")
    ):
        raise PermissionDenied("No tiene permiso para imprimir facturas")

    # ==========================================
    # FACTURA CAI
    # ==========================================

    factura_cai = (
        facturas_cai.objects.select_related(
            "id_cai",
            "id_cai__id_sucursal",
        )
        .filter(documento_token=token)
        .first()
    )

    if not factura_cai:
        return HttpResponse("Factura no encontrada", status=404)

    # ==========================================
    # VENTA
    # ==========================================

    venta = (
        Ventas.objects.select_related(
            "id_cliente",
            "sucursal",
            "id_factura_cai",
        )
        .filter(id_factura_cai=factura_cai)
        .first()
    )

    if not venta:
        return HttpResponse("Venta no encontrada", status=404)

    # ==========================================
    # DETALLE
    # ==========================================

    detalles = list(
        DetalleVenta.objects.select_related("producto", "combo")
        .prefetch_related("combo__detalles__producto")
        .filter(venta=venta)
        .order_by("id")
    )

    def nombre_linea_factura(detalle):
        if detalle.combo_id:
            componentes = " | ".join(
                f"{componente.cantidad:.2f}".rstrip("0").rstrip(".")
                + f" × {componente.producto.nombre}"
                for componente in detalle.combo.detalles.all()
            )
            return f"{detalle.combo.nombre} ({componentes})"
        return str(detalle.producto)

    # ==========================================
    # TARJETA
    # ==========================================

    tarjeta = tarjetas.objects.filter(id_factura=venta).first()

    # ==========================================
    # CAJERO
    # ==========================================

    cajero = "No disponible"

    if venta.u_creo_id:
        usuario = User.objects.filter(id=venta.u_creo_id).first()

        if usuario:
            nombre = (f"{usuario.first_name} {usuario.last_name}").strip()

            cajero = nombre if nombre else usuario.username

    # ==========================================
    # DATOS SAT
    # ==========================================

    cai = factura_cai.id_cai

    es_sat = factura_cai.es_sat

    # ==========================================
    # IDENTIDAD COMERCIAL
    # ==========================================

    configuracion = ConfiguracionEmpresa.objects.filter(
        is_active=True, is_delete=False
    ).first()
    nombre_empresa = (
        configuracion.nombre_comercial if configuracion else "Orvend Mart"
    )
    direccion_empresa = (
        configuracion.direccion
        if configuracion and configuracion.direccion
        else getattr(venta.sucursal, "ubicacion", "")
    )
    lineas_empresa = [nombre_empresa]
    lineas_empresa.extend(textwrap.wrap(direccion_empresa, width=35))
    if configuracion and configuracion.rtn:
        lineas_empresa.append(f"RTN: {configuracion.rtn}")
    if configuracion and configuracion.email:
        lineas_empresa.append(configuracion.email)
    if configuracion and configuracion.telefono:
        lineas_empresa.append(f"Tel.: {configuracion.telefono}")
    mensaje_factura = (
        configuracion.mensaje_factura
        if configuracion and configuracion.mensaje_factura
        else "Gracias por su compra"
    )
    if (
        configuracion
        and configuracion.diseno_factura == ConfiguracionEmpresa.DISENO_PAGINA
    ):
        return HttpResponse(
            _generar_factura_pagina_pdf(
                factura_cai,
                venta,
                detalles,
                cajero,
                configuracion,
            ),
            content_type="application/pdf",
            headers={"Content-Disposition": 'inline; filename="factura.pdf"'},
        )
    lineas_mensaje_factura = textwrap.wrap(mensaje_factura, width=35) or [mensaje_factura]

    # ==========================================
    # CALCULAR ALTO DINAMICO
    # ==========================================

    ancho_ticket = 80 * mm
    margen_ticket = 10
    inicio_producto = margen_ticket
    fin_producto = 110
    inicio_cantidad = fin_producto
    fin_cantidad = 175
    inicio_total = fin_cantidad
    fin_total = ancho_ticket - margen_ticket
    centro_cantidad = (inicio_cantidad + fin_cantidad) / 2
    ancho_producto = fin_producto - inicio_producto

    def envolver_linea_producto(texto):
        palabras = texto.split()
        lineas, linea_actual = [], ""
        for palabra in palabras:
            candidata = f"{linea_actual} {palabra}".strip()
            if linea_actual and pdfmetrics.stringWidth(candidata, "Helvetica", 8) > ancho_producto:
                lineas.append(linea_actual)
                linea_actual = palabra
            else:
                linea_actual = candidata
        if linea_actual:
            lineas.append(linea_actual)
        return lineas or ["-"]

    lineas_detalle_factura = [
        envolver_linea_producto(nombre_linea_factura(detalle))
        for detalle in detalles
    ]

    # El recibo se dibuja desde la parte superior. Antes se reservaban 145 mm
    # fijos y luego se sumaba el contenido variable, dejando mucho papel en
    # blanco después del mensaje. Calculamos cada bloque con los mismos saltos
    # verticales usados al imprimir para que el corte quede justo al final.
    cantidad_lineas_totales = 4 + int(
        bool(venta.nota_credito and venta.nota_credito > 0)
    )
    alto_encabezado = 60 + (len(lineas_empresa) * 11)
    alto_datos_factura = 83
    alto_cliente = 44 if venta.con_rtn and venta.id_cliente else 32
    alto_tabla = 22 + (
        sum(len(lineas) for lineas in lineas_detalle_factura) * 12
    )
    alto_totales = 38 + (cantidad_lineas_totales * 12)
    alto_tarjeta = 47 if tarjeta else 0
    alto_pie = 25 + (len(lineas_mensaje_factura) * 10)

    alto_ticket = (
        25  # margen superior
        + alto_encabezado
        + alto_datos_factura
        + alto_cliente
        + alto_tabla
        + alto_totales
        + alto_tarjeta
        + alto_pie
        + 15  # margen inferior de seguridad
    )

    # ==========================================
    # CREAR PDF
    # ==========================================

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=(ancho_ticket, alto_ticket))

    ancho = ancho_ticket

    y = alto_ticket - 25

    # ==========================================
    # ENCABEZADO
    # ==========================================

    logo_path = _logo_empresa_pdf()
    logo_width = 80
    logo_height = 32

    try:
        pdf.drawImage(
            logo_path,
            (ancho - logo_width) / 2,
            y - logo_height + 8,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception:
        # La factura sigue generándose aunque el archivo del logo no esté disponible.
        pass

    y -= 40
    for indice, linea in enumerate(lineas_empresa):
        pdf.setFont("Helvetica-Bold" if indice == 0 else "Helvetica", 10 if indice == 0 else 8)
        pdf.drawCentredString(ancho / 2, y, linea)
        y -= 11

    y -= 5

    pdf.line(10, y, ancho - 10, y)

    y -= 15
    # ==========================================
    # DATOS FACTURA
    # ==========================================

    pdf.setFont("Helvetica-Bold", 9)

    pdf.drawCentredString(ancho / 2, y, "DATOS FACTURA")

    y -= 15

    pdf.setFont("Helvetica", 8)

    if es_sat and cai:
        numero = str(factura_cai.numero_factura).zfill(len(str(cai.rango_final)))

        pdf.drawCentredString(ancho / 2, y, f"CAI: {cai.nombre_cai}")

        y -= 12

        pdf.drawCentredString(ancho / 2, y, f"No: {cai.numero_cai}-{numero}")

    else:
        pdf.drawCentredString(ancho / 2, y, f"No Factura: {factura_cai.numero_factura}")

        y -= 12

        pdf.drawCentredString(ancho / 2, y, "Factura personalizada")

    y -= 12

    pdf.drawCentredString(
        ancho / 2,
        y,
        f"Fecha: {_fecha_honduras(venta.f_creacion).strftime('%d/%m/%Y %I:%M %p')}",
    )

    y -= 12

    pdf.drawCentredString(ancho / 2, y, f"Cajero: {cajero}")

    y -= 20

    # ==========================================
    # CLIENTE
    # ==========================================

    pdf.setFont("Helvetica-Bold", 9)

    pdf.drawString(10, y, "CLIENTE")

    y -= 12

    pdf.setFont("Helvetica", 8)

    if venta.id_cliente:
        if venta.con_rtn:
            nombre_empresa = venta.id_cliente.empresa or venta.id_cliente.nombre_completo
            pdf.drawString(10, y, nombre_empresa[:42])
            y -= 12
            pdf.drawString(10, y, f"RTN: {venta.id_cliente.dni}")
        else:
            pdf.drawString(10, y, venta.id_cliente.nombre_completo[:42])

    else:
        pdf.drawString(10, y, "Consumidor Final")

    y -= 20

    # ==========================================
    # DETALLE PRODUCTOS
    # ==========================================

    pdf.setFont("Helvetica-Bold", 8)

    pdf.drawString(inicio_producto, y, "PRODUCTO")
    pdf.drawCentredString(centro_cantidad, y, "CANT (P/U)")
    pdf.drawRightString(fin_total, y, "TOTAL")

    y -= 10

    pdf.line(10, y, ancho - 10, y)

    y -= 12

    pdf.setFont("Helvetica", 8)

    for detalle, lineas_nombre in zip(detalles, lineas_detalle_factura):
        total_linea = detalle.cantidad * detalle.precio_unitario

        cantidad_y_precio = f"{detalle.cantidad:.2f}({detalle.precio_unitario:.2f})"

        for indice, linea_nombre in enumerate(lineas_nombre):
            pdf.drawString(inicio_producto, y, linea_nombre)
            if indice == 0:
                pdf.drawCentredString(centro_cantidad, y, cantidad_y_precio)
                pdf.drawRightString(fin_total, y, f"{total_linea:.2f}")
            y -= 12


    # ==========================================
    # TOTALES
    # ==========================================

    y -= 5

    pdf.line(10, y, ancho - 10, y)

    y -= 15

    pdf.setFont("Helvetica", 8)

    totales_factura = [
        ("Subtotal", venta.subtotal),
        ("ISV 15%", venta.impuesto_15),
        ("ISV 18%", venta.impuesto_18),
        ("Descuento", venta.descuento),
    ]
    if venta.nota_credito and venta.nota_credito > 0:
        totales_factura.append(("Devolución", venta.nota_credito))

    for nombre, valor in totales_factura:
        # Etiqueta a la izquierda
        pdf.drawString(10, y, nombre)

        # Valor alineado a la derecha
        monto_mostrado = (
            f"- L {valor:.2f}"
            if nombre == "Devolución"
            else f"L {valor:.2f}"
        )
        pdf.drawRightString(ancho - 10, y, monto_mostrado)

        y -= 12

    y -= 3

    pdf.line(10, y, ancho - 10, y)

    y -= 15

    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawString(10, y, "TOTAL")

    pdf.drawRightString(
        ancho - 10,
        y,
        f"L {venta.total:.2f}",
    )

    if tarjeta:
        y -= 20

    # ==========================================
    # TARJETA
    # ==========================================

    if tarjeta:
        pdf.setFont("Helvetica", 8)

        pdf.drawString(10, y, f"Tarjeta ****{tarjeta.digitos}")

        y -= 12

        pdf.drawString(10, y, f"Autorizacion: {tarjeta.numero_autorizacion}")

        y -= 15

    # ==========================================
    # PIE
    # ==========================================

    y -= 25

    pdf.setFont("Helvetica", 8)
    for linea in lineas_mensaje_factura:
        pdf.drawCentredString(ancho / 2, y, linea)
        y -= 10

    pdf.save()

    buffer.seek(0)

    return HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="factura.pdf"'},
    )


def descargar_factura_n8n(request, token):
    """API interna para que n8n descargue una factura durante un minuto."""
    access_token = request.GET.get("access_token", "")

    try:
        data = signing.loads(
            access_token,
            salt="manager.factura-n8n-v1",
            max_age=settings.N8N_FACTURA_URL_EXPIRA_SEGUNDOS,
        )
    except signing.SignatureExpired:
        return JsonResponse(
            {"success": False, "message": "El enlace temporal de factura expiró."},
            status=403,
        )
    except signing.BadSignature:
        return JsonResponse(
            {"success": False, "message": "El enlace temporal de factura no es válido."},
            status=403,
        )

    if data.get("factura_token") != str(token):
        return JsonResponse(
            {"success": False, "message": "El token no corresponde a la factura."},
            status=403,
        )

    return imprimir_factura(request, token, es_integracion=True)


@login_required
@permission_required("manager.view_datos_sat", raise_exception=True)
def datos_sat_view(request):
    search = request.GET.get("search", "").strip()

    query = datos_sat.objects.all()

    if search:
        query = query.filter(
            Q(id_sucursal__nombre__icontains=search)
            | Q(nombre_cai__icontains=search)
            | Q(numero_cai__icontains=search)
        )

    sucursales = Ubicaciones.objects.filter(is_active=True, is_delete=False).order_by(
        "nombre"
    )

    paginator = Paginator(query.order_by("-id"), 10)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
        "sucursales": sucursales,
    }

    return render(request, "sat/datos_sat.html", context)


@login_required
@permission_required("manager.view_datos_sat", raise_exception=True)
def get_datos_sat(request, id):

    sat = (
        datos_sat.objects.filter(id=id, is_delete=False)
        .select_related("id_sucursal")
        .first()
    )

    if not sat:
        return JsonResponse(
            {"success": False, "message": "Datos SAT no encontrados"}, status=404
        )

    return JsonResponse(
        {
            "success": True,
            "datos_sat": {
                "id": sat.id,
                "nombre_cai": sat.nombre_cai,
                "numero_cai": sat.numero_cai,
                "rango_inicial": sat.rango_inicial,
                "rango_final": sat.rango_final,
                "fecha_de_emision": sat.fecha_de_emision.strftime("%Y-%m-%d"),
                "fecha_de_vencimiento": sat.fecha_de_vencimiento.strftime("%Y-%m-%d"),
                "id_sucursal": sat.id_sucursal.id,
                "isActive": sat.is_active,
            },
        }
    )


@login_required
@permission_required("manager.change_datos_sat", raise_exception=True)
@require_http_methods(["PUT"])
def put_datos_sat(request, id):

    try:
        data = json.loads(request.body)

        nombre_cai = (data.get("nombre_cai") or "").strip()
        numero_cai = (data.get("numero_cai") or "").strip()
        rango_inicial = data.get("rango_inicial")
        rango_final = data.get("rango_final")
        fecha_de_emision = data.get("fecha_de_emision")
        fecha_de_vencimiento = data.get("fecha_de_vencimiento")
        id_sucursal = data.get("id_sucursal")
        is_active = data.get("IsActive", True)
        if not all(
            [
                nombre_cai,
                numero_cai,
                rango_inicial,
                rango_final,
                fecha_de_emision,
                fecha_de_vencimiento,
                id_sucursal,
            ]
        ):
            return JsonResponse(
                {"success": False, "message": "Todos los campos son obligatorios"},
                status=400,
            )

        sat = datos_sat.objects.filter(id=id).first()

        if not sat or sat.is_delete:
            return JsonResponse(
                {"success": False, "message": "Datos SAT no encontrado"}, status=404
            )

        # Validar CAI duplicado
        if (
            datos_sat.objects.filter(numero_cai=numero_cai, is_delete=False)
            .exclude(id=id)
            .exists()
        ):
            return JsonResponse(
                {"success": False, "message": "Ya existe un CAI con ese número"},
                status=400,
            )

        # Validar rango
        if int(rango_inicial) > int(rango_final):
            return JsonResponse(
                {
                    "success": False,
                    "message": "El rango inicial no puede ser mayor al rango final",
                },
                status=400,
            )

        sat.nombre_cai = nombre_cai
        sat.numero_cai = numero_cai
        sat.rango_inicial = rango_inicial
        sat.rango_final = rango_final
        sat.fecha_de_emision = fecha_de_emision
        sat.fecha_de_vencimiento = fecha_de_vencimiento
        sat.id_sucursal_id = id_sucursal
        sat.is_active = is_active

        sat.u_modifico_id = request.user.id
        sat.f_modificacion = timezone.now()

        sat.save()

        return JsonResponse(
            {"success": True, "message": "Datos SAT actualizado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.add_datos_sat", raise_exception=True)
@require_POST
def post_datos_sat(request):
    try:
        data = json.loads(request.body)

        id_sucursal = data.get("id_sucursal")
        nombre_cai = data.get("nombre_cai")
        numero_cai = data.get("numero_cai")
        rango_inicial = data.get("rango_inicial")
        rango_final = data.get("rango_final")
        fecha_de_emision = data.get("fecha_de_emision")
        fecha_de_vencimiento = data.get("fecha_de_vencimiento")

        if not all(
            [
                id_sucursal,
                nombre_cai,
                numero_cai,
                rango_inicial,
                rango_final,
                fecha_de_emision,
                fecha_de_vencimiento,
            ]
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Todos los campos son requeridos",
                },
                status=400,
            )

        datos_sat.objects.create(
            id_sucursal_id=id_sucursal,
            nombre_cai=nombre_cai,
            numero_cai=numero_cai,
            rango_inicial=int(rango_inicial),
            rango_final=int(rango_final),
            fecha_de_emision=fecha_de_emision,
            fecha_de_vencimiento=fecha_de_vencimiento,
            u_creo_id=request.user.id,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Datos SAT creados correctamente",
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "message": str(e),
            },
            status=500,
        )


@login_required
def descuento_cupon(request, cupon, id):

    if not _puede_operar_caja(request.user):
        return JsonResponse(
            {"error": "No tiene permiso para aplicar cupones"},
            status=403,
        )

    caja_abierta = CajaAC.objects.filter(
        usuario_id=request.user.id,
        fecha_apertura__date=timezone.localdate(),
        estado="abierta",
        is_active=True,
        is_delete=False,
    ).exists()
    if not caja_abierta:
        return JsonResponse(
            {"error": "La caja debe estar abierta para aplicar cupones"},
            status=400,
        )

    producto = Productos.objects.get(id=id)

    data = {"precio_venta": producto.precio_venta}

    descuento_cupon_producto = (
        Descuento.objects.filter(
            productos__id=id, is_active=True, es_cupon=True, codigo=cupon
        )
        .values()
        .first()
    )

    if not descuento_cupon_producto:
        return JsonResponse(
            {"error": "Este cupon no aplica en este produco"}, status=403
        )

    valor_descuento_producto = 0

    if descuento_cupon_producto["es_porcentaje"] == True:
        valor_descuento_producto = data["precio_venta"] * (
            descuento_cupon_producto["valor"] / 100
        )
    else:
        valor_descuento_producto = descuento_cupon_producto["valor"]

    descuento = {"descuento": valor_descuento_producto}

    return JsonResponse(descuento, safe=False)



def valor_descuento(data):

    ahora = timezone.now()

    # ==========================================================
    # DESCUENTO DIRECTO AL PRODUCTO
    # ==========================================================

    descuento_producto = (
        Descuento.objects.filter(
            productos__id=data["id"],
            is_active=True,
            is_delete=False,
            es_cupon=False,
            es_cantidad=False,
            fecha_inicio__lte=ahora,
        )
        .filter(
            Q(fecha_fin__isnull=True) |
            Q(fecha_fin__gte=ahora)
        )
        .values()
        .first()
    )

    # ==========================================================
    # DESCUENTO POR CATEGORÍA
    # ==========================================================

    descuento_categoria = (
        Descuento.objects.filter(
            categorias__id=data["id_categoria"],
            is_active=True,
            is_delete=False,
            es_cupon=False,
            es_cantidad=False,
            fecha_inicio__lte=ahora,
        )
        .filter(
            Q(fecha_fin__isnull=True) |
            Q(fecha_fin__gte=ahora)
        )
        .values()
        .first()
    )

    # ==========================================================
    # SI NO EXISTE NINGÚN DESCUENTO
    # ==========================================================

    if not descuento_producto and not descuento_categoria:
        return {
            "valor": Decimal("0.00"),
            "es_acumulable": False,
        }

    precio_venta = Decimal(
        str(data.get("precio_venta", 0))
    )

    # ==========================================================
    # VALORES INICIALES
    # ==========================================================

    valor_descuento_producto = Decimal("0.00")
    valor_descuento_categoria = Decimal("0.00")

    total_descuento = Decimal("0.00")

    acumulable = False

    # ==========================================================
    # DESCUENTO POR PRODUCTO
    # ==========================================================

    if descuento_producto:

        valor = Decimal(
            str(
                descuento_producto.get("valor", 0)
            )
        )

        if descuento_producto["es_porcentaje"]:

            valor_descuento_producto = (
                precio_venta * valor
            ) / Decimal("100")

        else:

            valor_descuento_producto = valor

        # ------------------------------------------------------
        # EVITAR DESCUENTO MAYOR AL PRECIO
        # ------------------------------------------------------

        if valor_descuento_producto > precio_venta:

            valor_descuento_producto = precio_venta

        # ======================================================
        # ¿ES ACUMULABLE?
        # ======================================================

        if descuento_producto["acumulable"]:

            acumulable = True

            # --------------------------------------------------
            # DESCUENTO DE CATEGORÍA
            # --------------------------------------------------

            if descuento_categoria:

                valor = Decimal(
                    str(
                        descuento_categoria.get(
                            "valor",
                            0
                        )
                    )
                )

                if descuento_categoria["es_porcentaje"]:

                    valor_descuento_categoria = (
                        precio_venta * valor
                    ) / Decimal("100")

                else:

                    valor_descuento_categoria = valor

                # ----------------------------------------------
                # EVITAR DESCUENTO MAYOR AL PRECIO
                # ----------------------------------------------

                if valor_descuento_categoria > precio_venta:

                    valor_descuento_categoria = precio_venta

            # --------------------------------------------------
            # SUMAR DESCUENTOS
            # --------------------------------------------------

            total_descuento = (
                valor_descuento_producto
                + valor_descuento_categoria
            )

        else:

            # --------------------------------------------------
            # SOLO DESCUENTO DEL PRODUCTO
            # --------------------------------------------------

            total_descuento = (
                valor_descuento_producto
            )

    # ==========================================================
    # SOLO DESCUENTO DE CATEGORÍA
    # ==========================================================

    else:

        if descuento_categoria:

            valor = Decimal(
                str(
                    descuento_categoria.get(
                        "valor",
                        0
                    )
                )
            )

            if descuento_categoria["es_porcentaje"]:

                valor_descuento_categoria = (
                    precio_venta * valor
                ) / Decimal("100")

            else:

                valor_descuento_categoria = valor

            # ----------------------------------------------
            # EVITAR DESCUENTO MAYOR AL PRECIO
            # ----------------------------------------------

            if valor_descuento_categoria > precio_venta:

                valor_descuento_categoria = precio_venta

            total_descuento = (
                valor_descuento_categoria
            )

    # ==========================================================
    # SEGURIDAD
    # ==========================================================

    if total_descuento > precio_venta:

        total_descuento = precio_venta

    if total_descuento < 0:

        total_descuento = Decimal("0.00")

    # ==========================================================
    # RESPUESTA
    # ==========================================================

    return {
        "valor": total_descuento,
        "es_acumulable": acumulable,
    }

def descuento_cantidad(data):

    ahora = timezone.now()

    descuento = (
        Descuento.objects.filter(
            productos__id=data["id"],
            is_active=True,
            is_delete=False,
            es_cantidad=True,
            es_cupon=False,
            fecha_inicio__lte=ahora,
        )
        .filter(
            Q(fecha_fin__isnull=True) |
            Q(fecha_fin__gte=ahora)
        )
        .values()
        .first()
    )

    if not descuento:
        return {
            "lleva": 0,
            "paga": 0,
            "es_acumulable": False,
        }

    return {
        "lleva": descuento["cantidad_lleva"],
        "paga": descuento["cantidad_paga"],
        "es_acumulable": descuento["acumulable"],
    }

@login_required
@permission_required("manager.view_traslados", raise_exception=True)
def traslados_list(request):
    search = request.GET.get("search", "").strip()

    traslados = (
        Traslados.objects.select_related(
            "solicitado_por",
            "autorizado_por",
            "ubicacion_origen",
            "ubicacion_destino",
        )
        .filter(is_delete=False)
        .order_by("-id")
    )

    if search:
        traslados = traslados.filter(
            Q(id__icontains=search)
            | Q(ubicacion_origen__nombre__icontains=search)
            | Q(ubicacion_destino__nombre__icontains=search)
            | Q(estado__icontains=search)
        )

    paginator = Paginator(traslados, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "traslados/traslados_view.html",
        {
            "page_obj": page_obj,
            "search": search,
        },
    )


@login_required
@permission_required("manager.view_traslados", raise_exception=True)
def detalle_traslado_view(request, token):
    traslado = get_object_or_404(
        Traslados.objects.select_related(
            "solicitado_por",
            "autorizado_por",
            "ubicacion_origen",
            "ubicacion_destino",
        ).prefetch_related(
            "detalles_traslado__producto__unidad_medida",
            "detalles_traslado__producto__marca",
        ),
        documento_token=token,
        is_delete=False,
    )

    detalles = []
    total_solicitado = Decimal("0")
    total_trasladado = Decimal("0")
    for detalle in traslado.detalles_traslado.all():
        producto = detalle.producto
        cantidad_solicitada = Decimal(detalle.cantidad_solicitada or 0)
        cantidad_trasladada = Decimal(detalle.cantidad_entregada or 0)
        total_solicitado += cantidad_solicitada
        total_trasladado += cantidad_trasladada
        detalles.append(
            {
                "nombre": producto.nombre,
                "presentacion": getattr(producto.unidad_medida, "abreviatura", "N/A"),
                "marca": getattr(producto.marca, "nombre", "N/A"),
                "sku": producto.codigo_sku or "N/A",
                "cantidad_solicitada": cantidad_solicitada,
                "cantidad_trasladada": cantidad_trasladada,
            }
        )

    data = {
        "id": traslado.id,
        "origen": traslado.ubicacion_origen.nombre,
        "destino": traslado.ubicacion_destino.nombre,
        "solicitado_por": traslado.solicitado_por.username,
        "autorizado_por": (
            traslado.autorizado_por.username if traslado.autorizado_por else "Pendiente"
        ),
        "fecha_solicitud": traslado.f_creacion,
        "fecha_autorizacion": traslado.fecha_autorizacion,
        "estado": traslado.get_estado_display(),
        "observaciones": traslado.observaciones,
        "total_solicitado": total_solicitado,
        "total_trasladado": total_trasladado,
        "detalles": detalles,
    }
    return render(request, "traslados/detalletraslado.html", {"traslado": data})


@login_required
@permission_required("manager.view_descuento", raise_exception=True)
def descuentos_view(request):

    search = request.GET.get("search", "").strip()

    descuentos = Descuento.objects.filter(is_delete=False).order_by("-id")

    # =========================
    # BUSQUEDA
    # =========================

    if search:
        descuentos = descuentos.filter(nombre__icontains=search)

    # =========================
    # PAGINACION
    # =========================

    paginator = Paginator(descuentos, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "inventario/descuentos.html", context)


@login_required
@permission_required("manager.add_descuento", raise_exception=True)
@require_POST
def post_descuento(request):

    try:
        data = json.loads(request.body)

        # =========================
        # INFORMACION GENERAL
        # =========================
        nombre = (data.get("nombre") or "").strip()
        descripcion = (data.get("descripcion") or "").strip()

        # =========================
        # CUPONES
        # =========================
        es_cupon = data.get("es_cupon", False)
        codigo = (data.get("codigo") or "").strip()

        # =========================
        # TIPO DESCUENTO
        # =========================
        es_porcentaje = data.get("es_porcentaje", True)
        valor = data.get("valor") or None

        # Convertir valor a decimal seguro
        if valor is not None and valor != "":
            try:
                valor = float(valor)
            except:
                return JsonResponse(
                    {"success": False, "message": "Valor inválido"}, status=400
                )
        else:
            valor = None

        # =========================
        # CANTIDAD
        # =========================
        es_cantidad = data.get("es_cantidad", False)
        cantidad_lleva = data.get("cantidad_lleva") or None
        cantidad_paga = data.get("cantidad_paga") or None

        # =========================
        # APLICACION
        # =========================
        aplicar_productos = data.get("aplicar_productos", False)
        aplicar_categorias = data.get("aplicar_categorias", False)

        productoid = data.get("productoid") or None
        categoriaid = data.get("categoriaid") or None

        # =========================
        # LIMITES
        # =========================
        limite_uso = data.get("limite_uso") or None

        # =========================
        # FECHAS
        # =========================
        fecha_inicio = data.get("fecha_inicio") or None
        fecha_fin = data.get("fecha_fin") or None

        # =========================
        # CONFIGURACIONES
        # =========================
        acumulable = data.get("acumulable", False)

        # =========================
        # VALIDACIONES
        # =========================
        if not nombre:
            return JsonResponse(
                {"success": False, "message": "El nombre es obligatorio"}, status=400
            )

        if Descuento.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un descuento con ese nombre"},
                status=400,
            )

        # =========================
        # CUPON VALIDACION
        # =========================
        if es_cupon:
            if codigo:
                if Descuento.objects.filter(codigo=codigo, is_delete=False).exists():
                    return JsonResponse(
                        {"success": False, "message": "El código ya existe"}, status=400
                    )
            else:
                codigo = None
        else:
            codigo = None

        # =========================
        # VALIDAR APLICACION
        # =========================
        if aplicar_productos and aplicar_categorias:
            return JsonResponse(
                {
                    "success": False,
                    "message": "No puedes aplicar a productos y categorías al mismo tiempo",
                },
                status=400,
            )

        if aplicar_productos and not productoid:
            return JsonResponse(
                {"success": False, "message": "Debes seleccionar un producto"},
                status=400,
            )

        if aplicar_categorias and not categoriaid:
            return JsonResponse(
                {"success": False, "message": "Debes seleccionar una categoría"},
                status=400,
            )

        # =========================
        # CREAR DESCUENTO
        # =========================
        descuento = Descuento.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            es_cupon=es_cupon,
            codigo=codigo,
            es_porcentaje=es_porcentaje,
            valor=valor,
            es_cantidad=es_cantidad,
            cantidad_lleva=cantidad_lleva if es_cantidad else None,
            cantidad_paga=cantidad_paga if es_cantidad else None,
            aplicar_productos=aplicar_productos,
            aplicar_categorias=aplicar_categorias,
            limite_uso=limite_uso if limite_uso else None,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            acumulable=acumulable,
            u_creo_id=request.user.id,
        )

        # =========================
        # RELACIONES (FOREIGN KEY FIX)
        # =========================
        if aplicar_productos and productoid:
            producto = Productos.objects.filter(id=productoid).first()
            if producto:
                descuento.productos = producto

        if aplicar_categorias and categoriaid:
            categoria = Categorias.objects.filter(id=categoriaid).first()
            if categoria:
                descuento.categorias = categoria

        descuento.save()

        return JsonResponse(
            {"success": True, "message": "Descuento registrado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_descuento", raise_exception=True)
def get_descuento(request, id):

    try:
        descuento = Descuento.objects.filter(id=id, is_delete=False).first()

        if not descuento:
            return JsonResponse(
                {"success": False, "message": "Descuento no encontrado"}, status=404
            )

        producto = descuento.productos if descuento.productos_id else None
        categoria = descuento.categorias if descuento.categorias_id else None

        return JsonResponse(
            {
                "success": True,
                "descuento": {
                    # =========================
                    # GENERAL
                    # =========================
                    "id": descuento.id,
                    "nombre": descuento.nombre,
                    "descripcion": descuento.descripcion,
                    # =========================
                    # CUPON
                    # =========================
                    "es_cupon": descuento.es_cupon,
                    "codigo": descuento.codigo,
                    # =========================
                    # TIPO DESCUENTO
                    # =========================
                    "es_porcentaje": descuento.es_porcentaje,
                    "valor": str(descuento.valor) if descuento.valor else "",
                    # =========================
                    # CANTIDAD
                    # =========================
                    "es_cantidad": descuento.es_cantidad,
                    "cantidad_lleva": descuento.cantidad_lleva,
                    "cantidad_paga": descuento.cantidad_paga,
                    # =========================
                    # APLICACION
                    # =========================
                    "aplicar_productos": descuento.aplicar_productos,
                    "aplicar_categorias": descuento.aplicar_categorias,
                    "productoid": producto.id if producto else None,
                    "productonombre": producto.nombre if producto else "",
                    "categoriaid": categoria.id if categoria else None,
                    "categorianombre": categoria.nombre if categoria else "",
                    # =========================
                    # LIMITES / FECHAS
                    # =========================
                    "limite_uso": descuento.limite_uso,
                    "fecha_inicio": (
                        descuento.fecha_inicio.strftime("%Y-%m-%dT%H:%M")
                        if descuento.fecha_inicio
                        else ""
                    ),
                    "fecha_fin": (
                        descuento.fecha_fin.strftime("%Y-%m-%dT%H:%M")
                        if descuento.fecha_fin
                        else ""
                    ),
                    # =========================
                    # CONFIG
                    # =========================
                    "acumulable": descuento.acumulable,
                    "is_active": descuento.is_active,
                },
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.change_descuento", raise_exception=True)
@require_http_methods(["PUT"])
def put_descuento(request, id):

    try:
        descuento = Descuento.objects.filter(id=id, is_delete=False).first()

        if not descuento:
            return JsonResponse(
                {"success": False, "message": "Descuento no encontrado"}, status=404
            )

        data = json.loads(request.body)

        # =========================
        # HELPERS
        # =========================
        def to_bool(val):
            return str(val).lower() in ["true", "1", "on", "yes"]

        def to_int(val):
            try:
                return int(val)
            except:
                return None

        # =========================
        # GENERAL
        # =========================
        nombre = (data.get("nombre") or "").strip()
        descripcion = (data.get("descripcion") or "").strip()

        # =========================
        # CUPON
        # =========================
        es_cupon = to_bool(data.get("es_cupon"))
        codigo = (data.get("codigo") or "").strip()

        # =========================
        # TIPO DESCUENTO
        # =========================
        es_porcentaje = to_bool(data.get("es_porcentaje"))
        valor = data.get("valor") or None

        # =========================
        # CANTIDAD
        # =========================
        es_cantidad = to_bool(data.get("es_cantidad"))
        cantidad_lleva = to_int(data.get("cantidad_lleva"))
        cantidad_paga = to_int(data.get("cantidad_paga"))

        # =========================
        # APLICACION
        # =========================
        aplicar_productos = to_bool(data.get("aplicar_productos"))
        aplicar_categorias = to_bool(data.get("aplicar_categorias"))

        productoid = data.get("productoid")
        categoriaid = data.get("categoriaid")

        # =========================
        # LIMITES / FECHAS
        # =========================
        limite_uso = to_int(data.get("limite_uso"))
        fecha_inicio = data.get("fecha_inicio") or None
        fecha_fin = data.get("fecha_fin") or None

        # =========================
        # CONFIG
        # =========================
        acumulable = to_bool(data.get("acumulable"))
        is_active = to_bool(data.get("is_active"))

        # =========================
        # VALIDACIONES BÁSICAS
        # =========================
        if not nombre:
            return JsonResponse(
                {"success": False, "message": "El nombre es obligatorio"}, status=400
            )

        existe = Descuento.objects.filter(nombre=nombre, is_delete=False).exclude(id=id)

        if existe.exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un descuento con ese nombre"},
                status=400,
            )

        if aplicar_productos and aplicar_categorias:
            return JsonResponse(
                {
                    "success": False,
                    "message": "No puedes aplicar a productos y categorías al mismo tiempo",
                },
                status=400,
            )

        # =========================
        # UPDATE
        # =========================
        descuento.nombre = nombre
        descuento.descripcion = descripcion

        descuento.es_cupon = es_cupon
        descuento.codigo = codigo if es_cupon else None

        descuento.es_porcentaje = es_porcentaje
        descuento.valor = valor

        # CANTIDAD
        descuento.es_cantidad = es_cantidad
        descuento.cantidad_lleva = cantidad_lleva if es_cantidad else None
        descuento.cantidad_paga = cantidad_paga if es_cantidad else None

        # APLICACION
        descuento.aplicar_productos = aplicar_productos
        descuento.aplicar_categorias = aplicar_categorias

        descuento.limite_uso = limite_uso
        descuento.fecha_inicio = fecha_inicio or None
        descuento.fecha_fin = fecha_fin or None

        descuento.acumulable = acumulable
        descuento.is_active = is_active

        descuento.u_modifico_id = request.user.id

        descuento.save()

        # =========================
        # RELACIONES (FK NO M2M)
        # =========================
        descuento.productos = None
        descuento.categorias = None

        if aplicar_productos and productoid:
            producto = Productos.objects.filter(id=productoid, is_delete=False).first()
            if producto:
                descuento.productos = producto

        if aplicar_categorias and categoriaid:
            categoria = Categorias.objects.filter(
                id=categoriaid, is_delete=False
            ).first()
            if categoria:
                descuento.categorias = categoria

        descuento.save()

        return JsonResponse(
            {"success": True, "message": "Descuento actualizado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_ventas", raise_exception=True)
def ventas_view(request):

    fecha_hoy = timezone.localdate(timezone=ZONA_HONDURAS)

    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    sucursal = request.GET.get("sucursal")

    if not fecha_inicio:
        fecha_inicio = fecha_hoy.strftime("%Y-%m-%d")

    if not fecha_fin:
        fecha_fin = fecha_hoy.strftime("%Y-%m-%d")

    inicio_honduras, fin_honduras = _rango_fechas_honduras(fecha_inicio, fecha_fin)
    detalles = (
        DetalleVenta.objects.select_related(
            "producto",
            "combo",
            "venta",
            "venta__id_cliente",
            "venta__sucursal",
            "venta__id_factura_cai",
        )
        .filter(
            venta__f_creacion__gte=inicio_honduras,
            venta__f_creacion__lt=fin_honduras,
        )
        .order_by("-venta__id")
    )

    # ======================================
    # FILTRO SUCURSAL
    # ======================================

    if sucursal:
        detalles = detalles.filter(venta__sucursal_id=sucursal)

    devoluciones_por_detalle = dict(
        DevolucionVentaDetalle.objects.filter(
            detalle_venta__in=detalles,
            devolucion_venta__is_delete=False,
        )
        .exclude(devolucion_venta__estado=DevolucionVenta.Estado.ANULADA)
        .values("detalle_venta_id")
        .annotate(total=Sum("total"))
        .values_list("detalle_venta_id", "total")
    )

    # ======================================
    # TOTAL GENERAL
    # ======================================

    total_general = detalles.aggregate(total=Sum("utilidad_total"))["total"] or 0

    total_vendido = detalles.aggregate(total=Sum("venta__total"))["total"] or 0

    paginator = Paginator(detalles, 25)

    page_obj = paginator.get_page(request.GET.get("page"))

    usuarios = {
        u.id: (f"{u.first_name} {u.last_name}".strip() or u.username)
        for u in User.objects.all()
    }

    for detalle in page_obj:
        detalle.cajero_nombre = usuarios.get(detalle.venta.u_creo_id, "No disponible")
        detalle.subtotal_linea = detalle.subtotal or (
            detalle.cantidad * detalle.precio_unitario
        )
        detalle.devolucion_linea = (
            devoluciones_por_detalle.get(detalle.id, Decimal("0")) or Decimal("0")
        )
        detalle.total_neto_linea = (
            detalle.subtotal_linea
            - (detalle.descuento or Decimal("0"))
            - detalle.devolucion_linea
        )

    context = {
        "page_obj": page_obj,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "total_vendido": total_vendido,
        "total_utilidad": total_general,
        "sucursales": Ubicaciones.objects.filter(
            es_tienda=True,
            is_delete=False,
        ),
        "sucursal_seleccionada": sucursal,
    }

    return render(
        request,
        "inventario/ventas.html",
        context,
    )


def _obtener_equivalencias_producto(producto):
    """Devuelve la equivalencia menor y mayor de la presentación relacionada."""
    relaciones = (
        getattr(producto, "relaciones_como_master", [])
        or getattr(producto, "relaciones_como_relacionado", [])
    )

    if not relaciones:
        return producto.equival_unid, producto.equival_unid

    relacion = relaciones[0]
    return (
        relacion.producto_relacionado.equival_unid,
        relacion.producto_master.equival_unid,
    )


def _obtener_proveedor_producto(producto):
    """Obtiene el proveedor de la compra más reciente del producto."""
    compras_producto = getattr(producto, "compras_producto", [])
    if not compras_producto:
        return ""

    return compras_producto[0].compra.proveedor.nombre_comercial


@login_required
@permission_required("manager.view_ventas", raise_exception=True)
def exportar_ventas_excel(request):
    fecha_hoy = timezone.localdate(timezone=ZONA_HONDURAS).strftime("%Y-%m-%d")
    fecha_inicio = request.GET.get("fecha_inicio") or fecha_hoy
    fecha_fin = request.GET.get("fecha_fin") or fecha_hoy
    sucursal = request.GET.get("sucursal")

    inicio_honduras, fin_honduras = _rango_fechas_honduras(fecha_inicio, fecha_fin)
    detalles = (
        DetalleVenta.objects.select_related(
            "producto",
            "combo",
            "producto__categoria",
            "producto__marca",
            "producto__unidad_medida",
            "venta",
            "venta__id_cliente",
            "venta__sucursal",
            "venta__id_factura_cai",
        )
        .prefetch_related(
            Prefetch(
                "producto__producto_master_rel",
                queryset=ProductosRel.objects.select_related(
                    "producto_master", "producto_relacionado"
                ),
                to_attr="relaciones_como_master",
            ),
            Prefetch(
                "producto__producto_relacionado_rel",
                queryset=ProductosRel.objects.select_related(
                    "producto_master", "producto_relacionado"
                ),
                to_attr="relaciones_como_relacionado",
            ),
            Prefetch(
                "producto__producto_compra_detalles",
                queryset=(
                    DetalleCompra.objects.filter(
                        is_delete=False,
                        compra__is_delete=False,
                    )
                    .select_related("compra__proveedor")
                    .order_by("-compra__fecha_compra")
                ),
                to_attr="compras_producto",
            ),
        )
        .filter(
            venta__f_creacion__gte=inicio_honduras,
            venta__f_creacion__lt=fin_honduras,
        )
        .order_by("-venta__id")
    )

    if sucursal:
        detalles = detalles.filter(venta__sucursal_id=sucursal)

    devoluciones_por_detalle = dict(
        DevolucionVentaDetalle.objects.filter(
            detalle_venta__in=detalles,
            devolucion_venta__is_delete=False,
        )
        .exclude(devolucion_venta__estado=DevolucionVenta.Estado.ANULADA)
        .values("detalle_venta_id")
        .annotate(total=Sum("total"))
        .values_list("detalle_venta_id", "total")
    )

    usuarios = {
        usuario.id: (f"{usuario.first_name} {usuario.last_name}".strip() or usuario.username)
        for usuario in User.objects.all()
    }

    encabezados = [
        "Factura",
        "Fecha",
        "ID cliente",
        "Nombre cliente",
        "Cajero",
        "Sucursal",
        "Tipo de venta",
        "Tipo de pago",
        "ID producto",
        "Producto",
        "Categoría",
        "Proveedor",
        "Marca",
        "Presentación",
        "Cantidad",
        "Precio unitario",
        "Costo unitario",
        "Utilidad unitaria",
        "Utilidad total",
        "Subtotal línea",
        "ISV línea",
        "ISV %",
        "Descuento línea",
        "Devolución línea",
        "Total neto línea",
        "Equivalencia mínima",
        "Equivalencia máxima",
    ]
    libro, hoja = _libro_exportacion_grande(
        "Ventas",
        encabezados,
        [16, 14, 14, 28, 22, 22, 16, 20, 15, 34, 22, 24, 20, 20, 12, 16, 16, 16, 16, 16, 16, 16, 12, 16, 16, 16, 16],
    )

    for detalle in detalles.iterator(chunk_size=200):
        subtotal_linea = detalle.subtotal or (
            detalle.cantidad * detalle.precio_unitario
        )
        isv_linea = (
            Decimal(detalle.impuesto_15 or 0)
            + Decimal(detalle.impuesto_18 or 0)
        )
        importe_bruto_linea = Decimal(detalle.precio_unitario or 0) * Decimal(
            detalle.cantidad or 0
        )
        isv_porcentaje = (
            (isv_linea * Decimal("100") / importe_bruto_linea)
            if importe_bruto_linea > 0 and isv_linea > 0
            else Decimal("0")
        )
        devolucion_linea = (
            devoluciones_por_detalle.get(detalle.id, Decimal("0")) or Decimal("0")
        )
        total_neto_linea = (
            subtotal_linea
            - (detalle.descuento or Decimal("0"))
            - devolucion_linea
        )
        cliente_id = detalle.venta.id_cliente.id if detalle.venta.id_cliente else ""
        cliente_nombre = (
            detalle.venta.id_cliente.nombre_completo
            if detalle.venta.id_cliente
            else "Consumidor Final"
        )
        producto = detalle.producto
        equivalencia_min, equivalencia_max = (
            _obtener_equivalencias_producto(producto)
            if producto
            else ("", "")
        )
        _agregar_fila_exportacion(
            hoja,
            [
                detalle.venta.id_factura_cai.numero_factura
                if detalle.venta.id_factura_cai
                else "",
                _fecha_honduras(detalle.venta.f_creacion).date(),
                cliente_id,
                cliente_nombre,
                usuarios.get(detalle.venta.u_creo_id, "No disponible"),
                detalle.venta.sucursal.nombre,
                detalle.venta.get_tipo_venta_display(),
                {
                    "contado": "Pago al contado",
                    "tarjeta": "Pago con tarjeta",
                    "credito": "Pago a crédito",
                    "depostivo": "Depósito bancario",
                    "cheque": "Pago con cheque",
                }.get(detalle.venta.tipo_pago, detalle.venta.tipo_pago),
                producto.id if producto else f"COMBO-{detalle.combo_id}",
                producto.nombre if producto else detalle.combo.nombre,
                producto.categoria.nombre if producto else "Combo",
                _obtener_proveedor_producto(producto) if producto else "",
                producto.marca.nombre if producto else "",
                producto.unidad_medida.nombre if producto else "",
                detalle.cantidad,
                detalle.precio_unitario,
                detalle.costo_unitario,
                detalle.utilidad_unitaria,
                detalle.utilidad_total,
                subtotal_linea,
                isv_linea,
                isv_porcentaje,
                detalle.descuento,
                devolucion_linea,
                total_neto_linea,
                equivalencia_min,
                equivalencia_max,
            ],
            formatos={
                2: "dd/mm/yyyy",
                15: "#,##0.00",
                16: "#,##0.00",
                17: "#,##0.00",
                18: "#,##0.00",
                19: "#,##0.00",
                20: "#,##0.00",
                21: "#,##0.00",
                22: '0.##"%"',
                23: "#,##0.00",
                24: "#,##0.00",
                25: "#,##0.00",
                26: "#,##0",
                27: "#,##0",
            },
        )
    return _respuesta_excel(libro, f"ventas_{fecha_inicio}_{fecha_fin}.xlsx")
