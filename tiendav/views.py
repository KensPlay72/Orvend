import json
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .busqueda import construir_filtro_busqueda
from .tokens import id_desde_token_categoria, token_categoria
from manager.models import (
    BannerTienda,
    Categorias,
    ConfiguracionEmpresa,
    Descuento,
    Inventarios,
    MovimientoInventario,
    Productos,
    ProductosImagenes,
    ReservaInventario,
    TipoMovimientoInventario,
    Ubicaciones,
)
from manager.nextcloud import obtener_archivo
from .models import ClienteTienda, DetallePedidoTienda, PedidoTienda


CAMPO_DECIMAL_INVENTARIO = DecimalField(max_digits=18, decimal_places=6)
CATEGORIAS_INICIO_POR_LOTE = 10
PRODUCTOS_POR_CARRUSEL_INICIO = 12


def _configuracion_tienda():
    return ConfiguracionEmpresa.objects.filter(
        is_active=True,
        is_delete=False,
    ).first()


def _sucursales_tienda():
    return Ubicaciones.objects.filter(
        is_active=True,
        is_delete=False,
        es_tienda=True,
    ).order_by("nombre")


def _anotar_existencia_disponible(productos, sucursales):
    reservas = (
        ReservaInventario.objects.filter(
            producto_id=OuterRef("pk"),
            ubicacion__in=sucursales,
            estado=ReservaInventario.Estado.RESERVADA,
            is_active=True,
            is_delete=False,
        )
        .order_by()
        .values("producto_id")
        .annotate(total=Sum("cantidad"))
        .values("total")
    )
    cero = Value(Decimal("0"), output_field=CAMPO_DECIMAL_INVENTARIO)
    return productos.annotate(
        _existencia_fisica=Coalesce(
            Sum(
                "producto_inventarios__cantidad",
                filter=Q(
                    producto_inventarios__is_active=True,
                    producto_inventarios__is_delete=False,
                    producto_inventarios__ubicacion__in=sucursales,
                ),
            ),
            cero,
        ),
        _existencia_reservada=Coalesce(
            Subquery(reservas, output_field=CAMPO_DECIMAL_INVENTARIO),
            cero,
        ),
    ).annotate(
        existencia=ExpressionWrapper(
            F("_existencia_fisica") - F("_existencia_reservada"),
            output_field=CAMPO_DECIMAL_INVENTARIO,
        )
    )


def _productos_con_stock(sucursales):
    """Productos activos disponibles al menos en una tienda pública."""
    productos = (
        Productos.objects.filter(is_active=True, is_delete=False)
        .select_related("categoria", "marca", "unidad_medida")
        .prefetch_related(
            Prefetch(
                "imagenes_producto",
                queryset=ProductosImagenes.objects.exclude(imagen_archivo=""),
            )
        )
    )
    return _anotar_existencia_disponible(productos, sucursales).filter(
        existencia__gte=Decimal("1")
    )


def _productos_publicos(sucursales):
    """Todos los productos activos que se pueden consultar en la tienda."""
    productos = (
        Productos.objects.filter(is_active=True, is_delete=False)
        .select_related("categoria", "marca", "unidad_medida")
        .prefetch_related(
            Prefetch(
                "imagenes_producto",
                queryset=ProductosImagenes.objects.exclude(imagen_archivo=""),
            )
        )
    )
    return _anotar_existencia_disponible(productos, sucursales)


def _descuentos_publicos():
    ahora = timezone.now()
    return list(
        Descuento.objects.filter(
            is_active=True,
            is_delete=False,
            es_cupon=False,
            es_cantidad=False,
            valor__gt=Decimal("0"),
        )
        .filter(Q(fecha_inicio__isnull=True) | Q(fecha_inicio__lte=ahora))
        .filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora))
        .filter(Q(limite_uso__isnull=True) | Q(cantidad_usados__lt=F("limite_uso")))
        .filter(
            Q(aplicar_productos=True, productos__isnull=False)
            | Q(aplicar_categorias=True, categorias__isnull=False)
        )
        .select_related("productos", "categorias")
        .order_by("id")
    )


def _anotar_precios_oferta(productos, descuentos):
    descuentos_producto = {}
    descuentos_categoria = {}
    for descuento in descuentos:
        if descuento.aplicar_productos and descuento.productos_id:
            descuentos_producto[descuento.productos_id] = descuento
        if descuento.aplicar_categorias and descuento.categorias_id:
            descuentos_categoria[descuento.categorias_id] = descuento

    for producto in productos:
        original = producto.precio_venta
        descuento_producto = descuentos_producto.get(producto.id)
        descuento_categoria = descuentos_categoria.get(producto.categoria_id)
        aplicados = []
        if descuento_producto:
            aplicados.append(descuento_producto)
            if descuento_producto.acumulable and descuento_categoria:
                aplicados.append(descuento_categoria)
        elif descuento_categoria:
            aplicados.append(descuento_categoria)

        total_descuento = Decimal("0")
        for descuento in aplicados:
            valor = descuento.valor or Decimal("0")
            total_descuento += (
                original * valor / Decimal("100")
                if descuento.es_porcentaje
                else valor
            )
        precio_oferta = max(
            Decimal("0"),
            original - total_descuento,
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        producto.precio_oferta = precio_oferta
        producto.tiene_oferta = bool(aplicados and precio_oferta < original)


def _filtrar_productos_en_oferta(productos, descuentos):
    productos_descuento = {
        descuento.productos_id: descuento
        for descuento in descuentos
        if descuento.aplicar_productos and descuento.productos_id
    }
    categorias_descuento = {
        descuento.categorias_id
        for descuento in descuentos
        if descuento.aplicar_categorias and descuento.categorias_id
    }
    productos_sin_descuento_categoria = {
        producto_id
        for producto_id, descuento in productos_descuento.items()
        if not descuento.acumulable
    }
    categorias_aplicables = categorias_descuento
    condicion = Q(pk__in=productos_descuento)
    if categorias_aplicables:
        condicion |= Q(categoria_id__in=categorias_aplicables) & ~Q(
            pk__in=productos_sin_descuento_categoria
        )
    if not productos_descuento and not categorias_aplicables:
        return productos.none()
    return productos.filter(condicion)


def _cliente_de_sesion(request):
    cliente_id = request.session.get("tienda_cliente_id")
    if not cliente_id:
        return None
    cliente = ClienteTienda.objects.filter(id=cliente_id).first()
    if cliente is None:
        request.session.pop("tienda_cliente_id", None)
        request.session.pop("tienda_cliente_nombre", None)
    return cliente


def _url_siguiente(request):
    destino = request.POST.get("next") or request.GET.get("next") or reverse(
        "tiendav:historial"
    )
    if not url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return reverse("tiendav:historial")
    return destino


def _archivo_publico(nombre_archivo, carpeta, cache_seconds=604800):
    """Entrega imágenes públicas con caché en memoria y encabezados HTTP para carga instantánea."""
    clave_cache = f"tienda_img_{carpeta}_{nombre_archivo}"
    cached_data = cache.get(clave_cache)
    if cached_data is not None:
        contenido, content_type = cached_data
    else:
        try:
            archivo = obtener_archivo(nombre_archivo, carpeta)
            contenido = archivo.content
            content_type = archivo.headers.get("Content-Type", "image/webp")
            cache.set(clave_cache, (contenido, content_type), cache_seconds)
        except Exception:
            return HttpResponse("No fue posible obtener la imagen", status=500)

    response = HttpResponse(contenido, content_type=content_type)
    response["Cache-Control"] = f"public, max-age={cache_seconds}, immutable"
    return response


@require_GET
def logo_tienda(request):
    configuracion = _configuracion_tienda()
    if not configuracion or not configuracion.logo_archivo:
        return HttpResponse(status=404)
    return _archivo_publico(configuracion.logo_archivo, settings.NEXTCLOUD_FOLDER_CONFI)


@require_GET
def banner_tienda(request, banner_id):
    banner = get_object_or_404(
        BannerTienda,
        id=banner_id,
        activo=True,
        configuracion__is_active=True,
        configuracion__is_delete=False,
    )
    return _archivo_publico(banner.imagen_archivo, settings.NEXTCLOUD_FOLDER_CONFI)


@require_GET
def producto_imagen_tienda(request, imagen_id):
    imagen = get_object_or_404(
        ProductosImagenes,
        id=imagen_id,
        producto__is_active=True,
        producto__is_delete=False,
    )
    return _archivo_publico(imagen.imagen_archivo, settings.NEXTCLOUD_FOLDER_PRODUCTOS)


@require_GET
def ubicacion_imagen_tienda(request, ubicacion_id):
    ubicacion = get_object_or_404(
        Ubicaciones,
        id=ubicacion_id,
        es_tienda=True,
        is_active=True,
        is_delete=False,
    )
    if not ubicacion.imagen_archivo:
        return HttpResponse(status=404)
    return _archivo_publico(ubicacion.imagen_archivo, settings.NEXTCLOUD_FOLDER_CONFI)


@require_GET
def inicio(request):
    """Portada pública con productos disponibles en alguna tienda."""
    configuracion = _configuracion_tienda()
    sucursales = _sucursales_tienda()
    busqueda = request.GET.get("buscar", "").strip()
    ver_ofertas = request.GET.get("ofertas", "").strip() == "1"
    categorias = Categorias.objects.filter(
        is_active=True,
        is_delete=False,
        categoria_productos__is_active=True,
        categoria_productos__is_delete=False,
    ).distinct().order_by("nombre")
    categoria_parametro = request.GET.get("categoria", "").strip()
    categoria_id = id_desde_token_categoria(categoria_parametro)
    categoria_seleccionada = None
    productos = _productos_publicos(sucursales)
    if busqueda:
        campos_producto = [
            "nombre",
            "codigo_sku",
            "categoria__nombre",
            "marca__nombre",
        ]
        filtro_and = construir_filtro_busqueda(busqueda, campos_producto, modo="and")
        productos_filtrados = productos.filter(filtro_and)
        if not productos_filtrados.exists() and len(busqueda.split()) > 1:
            filtro_or = construir_filtro_busqueda(busqueda, campos_producto, modo="or")
            productos = productos.filter(filtro_or)
        else:
            productos = productos_filtrados
    if categoria_id:
        categoria_seleccionada = categorias.filter(id=categoria_id).first()
        if categoria_seleccionada:
            productos = productos.filter(categoria=categoria_seleccionada)
        else:
            categoria_id = None

    ver_catalogo = request.GET.get("catalogo", "").strip() == "1"
    mostrar_catalogo = bool(busqueda or categoria_id or ver_catalogo or ver_ofertas)
    categoria_token = ""
    if categoria_seleccionada:
        categoria_token = token_categoria(categoria_seleccionada.pk)
    descuentos = _descuentos_publicos()
    if ver_ofertas:
        productos = _filtrar_productos_en_oferta(productos, descuentos)
    page_obj = None
    if mostrar_catalogo:
        por_pagina = 15
        page_obj = Paginator(productos.order_by("nombre", "id"), por_pagina).get_page(
            request.GET.get("page")
        )

    categorias_con_carrusel = []
    categorias_inicio_tiene_mas = False
    categorias_inicio_siguiente_offset = 0
    if not mostrar_catalogo:
        carga_categorias = request.GET.get("cargar_categorias") == "1"
        total_categorias_inicio = categorias.count()
        offset = 0
        if carga_categorias:
            try:
                offset = int(request.GET.get("desde", "0"))
            except ValueError:
                return HttpResponseBadRequest("El inicio de categorías no es válido.")
            if offset < 0 or offset > total_categorias_inicio:
                return HttpResponseBadRequest("El inicio de categorías no es válido.")

        categorias_inicio = list(
            categorias[offset : offset + CATEGORIAS_INICIO_POR_LOTE]
        )
        productos_por_categoria = {categoria.id: [] for categoria in categorias_inicio}
        productos_a_anotar = []
        for categoria in categorias_inicio:
            productos_categoria = list(
                productos.filter(
                    categoria_id=categoria.id,
                    categoria__is_active=True,
                    categoria__is_delete=False,
                ).order_by("nombre", "id")[:PRODUCTOS_POR_CARRUSEL_INICIO]
            )
            productos_por_categoria[categoria.id] = productos_categoria
            productos_a_anotar.extend(productos_categoria)

        _anotar_precios_oferta(productos_a_anotar, descuentos)
        categorias_con_carrusel = [
            {"categoria": categoria, "productos": productos_por_categoria[categoria.id]}
            for categoria in categorias_inicio
        ]
        categorias_inicio_tiene_mas = (
            total_categorias_inicio > offset + len(categorias_inicio)
        )
        categorias_inicio_siguiente_offset = offset + len(categorias_inicio)

        if carga_categorias:
            return JsonResponse(
                {
                    "html": render_to_string(
                        "partials/categoria_carrusel.html",
                        {"categorias_con_carrusel": categorias_con_carrusel},
                        request=request,
                    ),
                    "has_more": categorias_inicio_tiene_mas,
                    "next_offset": categorias_inicio_siguiente_offset,
                }
            )

    if page_obj:
        _anotar_precios_oferta(page_obj.object_list, descuentos)

    banner_principal = None
    banners_carrusel = []
    if configuracion:
        banner_principal = configuracion.banners_tienda.filter(
            tipo=BannerTienda.TIPO_BANNER,
            activo=True,
        ).first()
        banners_carrusel = list(
            configuracion.banners_tienda.filter(
                tipo=BannerTienda.TIPO_CARRUSEL,
                activo=True,
            ).order_by("orden", "id")
        )

    carrusel_posicion = (len(categorias_con_carrusel) + 1) // 2 if categorias_con_carrusel else 0
    categorias_primera_mitad = categorias_con_carrusel[:carrusel_posicion]
    categorias_segunda_mitad = categorias_con_carrusel[carrusel_posicion:]

    return render(
        request,
        "inicio.html",
        {
            "configuracion": configuracion,
            "sucursales": sucursales,
            "busqueda": busqueda,
            "categorias": categorias,
            "categoria_id": categoria_id,
            "categoria_token": categoria_token,
            "categoria_seleccionada": categoria_seleccionada,
            "ver_catalogo": ver_catalogo,
            "ver_ofertas": ver_ofertas,
            "page_obj": page_obj,
            "categorias_con_carrusel": categorias_con_carrusel,
            "categorias_primera_mitad": categorias_primera_mitad,
            "categorias_segunda_mitad": categorias_segunda_mitad,
            "categorias_inicio_tiene_mas": categorias_inicio_tiene_mas,
            "categorias_inicio_siguiente_offset": categorias_inicio_siguiente_offset,
            "banner_principal": banner_principal,
            "banners_carrusel": banners_carrusel,
            "cliente_tienda": _cliente_de_sesion(request),
        },
    )


@require_GET
def detalle_producto(request, token):
    producto = get_object_or_404(
        Productos.objects.select_related(
            "categoria", "marca", "unidad_medida"
        ).prefetch_related(
            Prefetch(
                "imagenes_producto",
                queryset=ProductosImagenes.objects.exclude(imagen_archivo=""),
            )
        ),
        tienda_token=token,
        is_active=True,
        is_delete=False,
    )
    sucursales = list(_sucursales_tienda())
    existencias = {
        item["ubicacion_id"]: item["total"] or Decimal("0")
        for item in (
            Inventarios.objects.filter(
                producto=producto,
                ubicacion__in=sucursales,
                is_active=True,
                is_delete=False,
            )
            .values("ubicacion_id")
            .annotate(total=Sum("cantidad"))
        )
    }
    reservas = {
        item["ubicacion_id"]: item["total"] or Decimal("0")
        for item in (
            ReservaInventario.objects.filter(
                producto=producto,
                ubicacion__in=sucursales,
                estado=ReservaInventario.Estado.RESERVADA,
                is_active=True,
                is_delete=False,
            )
            .values("ubicacion_id")
            .annotate(total=Sum("cantidad"))
        )
    }
    disponibilidad = []
    total_unidades_enteras = 0
    for sucursal in sucursales:
        stock_neto = max(
            Decimal("0"),
            existencias.get(sucursal.id, Decimal("0"))
            - reservas.get(sucursal.id, Decimal("0")),
        )
        unidades = int(stock_neto)
        tiene_stock_tienda = stock_neto >= Decimal("1")
        if tiene_stock_tienda:
            total_unidades_enteras += unidades

        disponibilidad.append(
            {
                "ubicacion": sucursal,
                "existencia": stock_neto,
                "unidades_enteras": unidades,
                "tiene_stock": tiene_stock_tienda,
            }
        )

    tiene_stock = any(item["tiene_stock"] for item in disponibilidad)
    productos_relacionados = list(
        _productos_con_stock(sucursales)
        .filter(categoria=producto.categoria)
        .exclude(id=producto.id)
        .order_by("nombre", "id")[:12]
    )
    descuentos = _descuentos_publicos()
    _anotar_precios_oferta([producto, *productos_relacionados], descuentos)
    return render(
        request,
        "detalle_producto.html",
        {
            "configuracion": _configuracion_tienda(),
            "producto": producto,
            "sucursales": sucursales,
            "disponibilidad": disponibilidad,
            "tiene_stock": tiene_stock,
            "total_unidades_enteras": total_unidades_enteras,
            "productos_relacionados": productos_relacionados,
            "cliente_tienda": _cliente_de_sesion(request),
        },
    )


def _email_valido(email):
    try:
        validate_email(email)
    except ValidationError:
        return False
    return True


@require_http_methods(["GET", "POST"])
def cuenta_cliente(request):
    if _cliente_de_sesion(request):
        return redirect(_url_siguiente(request))

    error = ""
    form_mode = (
        request.POST.get("accion", "ingresar")
        if request.method == "POST"
        else request.GET.get("modo", "ingresar")
    )
    if form_mode not in {"ingresar", "registrar"}:
        form_mode = "ingresar"
    if request.method == "POST":
        accion = form_mode
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        if accion == "registrar":
            nombre = request.POST.get("nombre", "").strip()
            telefono = request.POST.get("telefono", "").strip()
            confirmacion = request.POST.get("confirmar_password", "")
            if not nombre or not email or not password:
                error = "Completa tu nombre, correo y contraseña."
            elif len(nombre) > 150 or len(email) > 254 or len(telefono) > 30:
                error = "Revisa la longitud del nombre, correo o teléfono."
            elif not _email_valido(email):
                error = "Ingresa un correo electrónico válido."
            elif len(password) < 8:
                error = "La contraseña debe tener al menos 8 caracteres."
            elif not (
                any(c.isupper() for c in password)
                and any(c.islower() for c in password)
                and any(c.isdigit() for c in password)
            ):
                error = "La contraseña debe incluir al menos una letra mayúscula, una minúscula y un número."
            elif password != confirmacion:
                error = "Las contraseñas no coinciden."
            elif ClienteTienda.objects.filter(email=email).exists():
                error = "Ya existe una cuenta con ese correo."
            else:
                try:
                    with transaction.atomic():
                        cliente = ClienteTienda.objects.create(
                            nombre=nombre,
                            email=email,
                            telefono=telefono,
                            password=make_password(password),
                        )
                except IntegrityError:
                    error = "Ya existe una cuenta con ese correo."
                else:
                    request.session.cycle_key()
                    request.session["tienda_cliente_id"] = cliente.id
                    request.session["tienda_cliente_nombre"] = cliente.nombre
                    return redirect(_url_siguiente(request))
        elif accion == "ingresar":
            cliente = ClienteTienda.objects.filter(email=email).first()
            if cliente and check_password(password, cliente.password):
                request.session.cycle_key()
                request.session["tienda_cliente_id"] = cliente.id
                request.session["tienda_cliente_nombre"] = cliente.nombre
                return redirect(_url_siguiente(request))
            error = "El correo o la contraseña no son correctos."
        else:
            error = "La opción de acceso no es válida."

    return render(
        request,
        "cuenta.html",
        {
            "configuracion": _configuracion_tienda(),
            "sucursales": _sucursales_tienda(),
            "cliente_tienda": None,
            "error": error,
            "form_mode": form_mode,
            "next_url": _url_siguiente(request),
        },
    )


@require_POST
def cerrar_sesion_cliente(request):
    request.session.pop("tienda_cliente_id", None)
    request.session.pop("tienda_cliente_nombre", None)
    return redirect("tiendav:inicio")


@require_http_methods(["GET", "POST"])
def perfil_cliente(request):
    cliente = _cliente_de_sesion(request)
    if not cliente:
        return redirect(f"{reverse('tiendav:cuenta')}?next={reverse('tiendav:perfil')}")

    error = ""
    if request.method == "POST":
        campos = {
            "nombre": request.POST.get("nombre", "").strip(),
            "telefono": request.POST.get("telefono", "").strip(),
            "direccion": request.POST.get("direccion", "").strip(),
            "municipio": request.POST.get("municipio", "").strip(),
            "departamento": request.POST.get("departamento", "").strip(),
            "indicaciones_entrega": request.POST.get(
                "indicaciones_entrega", ""
            ).strip(),
        }
        limites = {
            "nombre": 150,
            "telefono": 30,
            "direccion": 255,
            "municipio": 100,
            "departamento": 100,
            "indicaciones_entrega": 255,
        }
        if not campos["nombre"]:
            error = "El nombre es obligatorio."
        elif any(len(campos[campo]) > limite for campo, limite in limites.items()):
            error = "Uno o más datos superan la longitud permitida."
        else:
            for campo, valor in campos.items():
                setattr(cliente, campo, valor)
            cliente.save(update_fields=list(campos))
            request.session["tienda_cliente_nombre"] = cliente.nombre
            return redirect(f"{reverse('tiendav:perfil')}?actualizado=1")

        for campo, valor in campos.items():
            setattr(cliente, campo, valor)

    return render(
        request,
        "perfil.html",
        {
            "configuracion": _configuracion_tienda(),
            "sucursales": _sucursales_tienda(),
            "cliente_tienda": cliente,
            "error": error,
            "perfil_actualizado": request.GET.get("actualizado") == "1",
        },
    )


@require_GET
def historial_cliente(request):
    cliente = _cliente_de_sesion(request)
    if not cliente:
        return redirect(
            f"{reverse('tiendav:cuenta')}?next={reverse('tiendav:historial')}"
        )
    pedidos = (
        PedidoTienda.objects.filter(cliente=cliente)
        .annotate(total_detalles=Count("detalles"))
        .select_related("ubicacion")
        .order_by("-creado", "-id")
    )
    page_obj = Paginator(pedidos, 10).get_page(request.GET.get("page", 1))
    for pedido in page_obj:
        pedido.detalles_historial = list(
            DetallePedidoTienda.objects.filter(pedido_id=pedido.id)
            .select_related("producto", "reserva", "producto_cambio")
            .prefetch_related(
                Prefetch(
                    "producto__imagenes_producto",
                    queryset=ProductosImagenes.objects.exclude(imagen_archivo=""),
                ),
                Prefetch(
                    "producto_cambio__imagenes_producto",
                    queryset=ProductosImagenes.objects.exclude(imagen_archivo=""),
                ),
            )
            .order_by("id")[:5]
        )

    return render(
        request,
        "historial.html",
        {
            "configuracion": _configuracion_tienda(),
            "sucursales": _sucursales_tienda(),
            "cliente_tienda": cliente,
            "pedidos": page_obj,
            "page_obj": page_obj,
        },
    )


def detalle_pedido_cliente(request, token=None, pedido_id=None):
    cliente = _cliente_de_sesion(request)
    if not cliente:
        return redirect(
            f"{reverse('tiendav:cuenta')}?next={reverse('tiendav:historial')}"
        )

    if token:
        try:
            pedido = get_object_or_404(
                PedidoTienda.objects.select_related("ubicacion"),
                token=token,
                cliente=cliente,
            )
        except (ValueError, ValidationError):
            raise Http404("Pedido no encontrado")
    else:
        pedido = get_object_or_404(
            PedidoTienda.objects.select_related("ubicacion"),
            id=pedido_id,
            cliente=cliente,
        )
        return redirect("tiendav:detalle_pedido", token=pedido.token)

    detalles_queryset = (
        pedido.detalles.select_related("producto", "producto_cambio")
        .prefetch_related(
            Prefetch(
                "producto__imagenes_producto",
                queryset=ProductosImagenes.objects.exclude(imagen_archivo=""),
            ),
            Prefetch(
                "producto_cambio__imagenes_producto",
                queryset=ProductosImagenes.objects.exclude(imagen_archivo=""),
            ),
        )
    )
    page_obj = Paginator(detalles_queryset, 10).get_page(
        request.GET.get("page", 1)
    )
    detalles = list(page_obj.object_list)
    return render(
        request,
        "detalle_pedido.html",
        {
            "configuracion": _configuracion_tienda(),
            "sucursales": _sucursales_tienda(),
            "cliente_tienda": cliente,
            "pedido": pedido,
            "detalles": detalles,
            "page_obj": page_obj,
        },
    )


@require_GET
def lista_categorias(request):
    """Listado completo de categorías disponibles en la tienda virtual."""
    configuracion = _configuracion_tienda()
    sucursales = _sucursales_tienda()
    cliente_tienda = _cliente_de_sesion(request)

    categorias_qs = (
        Categorias.objects.filter(
            is_active=True,
            is_delete=False,
            categoria_productos__is_active=True,
            categoria_productos__is_delete=False,
        )
        .annotate(
            total_productos=Count(
                "categoria_productos",
                filter=Q(
                    categoria_productos__is_active=True,
                    categoria_productos__is_delete=False,
                ),
                distinct=True,
            )
        )
        .filter(total_productos__gt=0)
        .distinct()
        .order_by("nombre")
    )

    categorias = list(categorias_qs)
    for cat in categorias:
        cat.token = token_categoria(cat.pk)

    return render(
        request,
        "categorias.html",
        {
            "configuracion": configuracion,
            "sucursales": sucursales,
            "cliente_tienda": cliente_tienda,
            "categorias": categorias,
        },
    )


@require_GET
def ubicaciones_tienda(request):
    sucursales = _sucursales_tienda()
    return render(
        request,
        "ubicaciones.html",
        {
            "configuracion": _configuracion_tienda(),
            "sucursales": sucursales,
            "cliente_tienda": _cliente_de_sesion(request),
        },
    )


@require_POST
def crear_pedido(request):
    cliente = _cliente_de_sesion(request)
    if not cliente:
        return JsonResponse(
            {"success": False, "auth_required": True},
            status=401,
        )

    try:
        datos = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "message": "El contenido del pedido no es válido."},
            status=400,
        )
    if not isinstance(datos, dict) or not isinstance(datos.get("items"), list):
        return JsonResponse(
            {"success": False, "message": "Agrega productos antes de continuar."},
            status=400,
        )
    try:
        ubicacion_id = int(datos.get("ubicacion"))
    except (TypeError, ValueError):
        return JsonResponse(
            {"success": False, "message": "Selecciona una tienda válida."},
            status=400,
        )
    if not 1 <= len(datos["items"]) <= 50:
        return JsonResponse(
            {"success": False, "message": "El pedido debe incluir entre 1 y 50 productos."},
            status=400,
        )

    cantidades = {}
    try:
        for item in datos["items"]:
            if not isinstance(item, dict) or type(item.get("quantity")) is not int:
                raise ValueError
            token = UUID(str(item.get("token", "")))
            cantidad = item["quantity"]
            if not 1 <= cantidad <= 999:
                raise ValueError
            cantidades[token] = cantidades.get(token, 0) + cantidad
            if cantidades[token] > 999:
                raise ValueError
    except (TypeError, ValueError, AttributeError):
        return JsonResponse(
            {"success": False, "message": "Revisa las cantidades de los productos."},
            status=400,
        )

    sucursal = _sucursales_tienda().filter(id=ubicacion_id).first()
    if sucursal is None:
        return JsonResponse(
            {"success": False, "message": "La tienda seleccionada ya no está disponible."},
            status=400,
        )
    productos = {
        producto.tienda_token: producto
        for producto in Productos.objects.filter(
            tienda_token__in=cantidades,
            is_active=True,
            is_delete=False,
        )
    }
    if len(productos) != len(cantidades):
        tokens_no_disponibles = [
            str(token) for token in cantidades if token not in productos
        ]
        return JsonResponse(
            {
                "success": False,
                "message": "Uno o más productos ya no están disponibles.",
                "unavailable_items": tokens_no_disponibles,
                "location": sucursal.nombre,
            },
            status=400,
        )

    descuentos = _descuentos_publicos()
    _anotar_precios_oferta(list(productos.values()), descuentos)

    with transaction.atomic():
        inventarios = list(
            Inventarios.objects.select_for_update()
            .filter(
                producto__in=productos.values(),
                ubicacion=sucursal,
                is_active=True,
                is_delete=False,
                cantidad__gt=0,
            )
            .order_by("producto_id", "fvencimiento", "id")
        )
        capas_por_producto = {}
        for inventario in inventarios:
            capas_por_producto.setdefault(inventario.producto_id, []).append(inventario)

        reservas_por_producto = {
            item["producto_id"]: item["total"] or Decimal("0")
            for item in (
                ReservaInventario.objects.filter(
                    producto__in=productos.values(),
                    ubicacion=sucursal,
                    estado=ReservaInventario.Estado.RESERVADA,
                    is_active=True,
                    is_delete=False,
                )
                .values("producto_id")
                .annotate(total=Sum("cantidad"))
            )
        }
        no_disponibles = []
        for token, cantidad in cantidades.items():
            producto = productos[token]
            stock = sum(
                (capa.cantidad for capa in capas_por_producto.get(producto.id, [])),
                Decimal("0"),
            )
            disponible = stock - reservas_por_producto.get(producto.id, Decimal("0"))
            if disponible < cantidad:
                no_disponibles.append(
                    {
                        "token": str(token),
                        "name": producto.nombre,
                        "available": str(max(disponible, Decimal("0"))),
                    }
                )
        if no_disponibles:
            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        f"Hay productos sin unidades suficientes en {sucursal.nombre}. "
                        "Revisa los productos marcados en el carrito."
                    ),
                    "unavailable_items": no_disponibles,
                    "location": sucursal.nombre,
                },
                status=400,
            )

        detalles_pedido = []
        total = Decimal("0")
        for token, cantidad in cantidades.items():
            producto = productos[token]
            cantidad_decimal = Decimal(cantidad)
            precio = producto.precio_oferta
            subtotal = precio * cantidad_decimal
            reserva = ReservaInventario.objects.create(
                producto=producto,
                ubicacion=sucursal,
                cantidad=cantidad_decimal,
                estado=ReservaInventario.Estado.RESERVADA,
            )
            detalles_pedido.append(
                DetallePedidoTienda(
                    producto=producto,
                    reserva=reserva,
                    nombre_producto=producto.nombre,
                    codigo_sku=producto.codigo_sku,
                    cantidad=cantidad_decimal,
                    precio_unitario=precio,
                    subtotal=subtotal,
                )
            )
            total += subtotal

        pedido = PedidoTienda.objects.create(
            cliente=cliente,
            ubicacion=sucursal,
            total=total,
        )
        for detalle in detalles_pedido:
            detalle.pedido = pedido
        DetallePedidoTienda.objects.bulk_create(detalles_pedido)

    return JsonResponse(
        {
            "success": True,
            "message": "Tu pedido quedó reservado y está pendiente de confirmación.",
            "redirect": reverse("tiendav:historial"),
        },
        status=201,
    )
