import json
import textwrap
import traceback
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
from io import BytesIO
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, OuterRef, Subquery
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from reportlab.lib.units import mm
from .nextcloud import subir_archivo, obtener_archivo,eliminar_archivo
import os
import uuid
from .enums import EstadoCompra, EstadoCuenta, EstadoDevolucionCompra, Estados
from .models import (
    Categorias,
    Clientes,
    Compras,
    CuentasPorPagar,
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
    tarjetas,
    CajaAC,
    DetalleCuadreCaja,
    ProductosRel,
    ReservaInventario,
)


@login_required
def dashboard_view(request):
    return render(request, "dashboard.html")


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

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    items = (
        UMedidas.objects.filter(is_delete=False, is_active=True)
        .filter(Q(nombre__icontains=search) | Q(abreviatura__icontains=search))
        .order_by("nombre")[:20]
    )

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

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    items = (
        Marcas.objects.filter(is_delete=False, is_active=True)
        .filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))
        .order_by("nombre")[:20]
    )

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

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    items = (
        Categorias.objects.filter(is_delete=False, is_active=True)
        .filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))
        .order_by("nombre")[:20]
    )

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

        if not all(
            [nombre_legal, nombre_comercial, rtn, dias_credito, telefono, email]
        ):
            return JsonResponse(
                {"success": False, "message": "Todos los campos son obligatorios"},
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

        if not all(
            [nombre_legal, nombre_comercial, rtn, dias_credito, telefono, email]
        ):
            return JsonResponse(
                {"success": False, "message": "Todos los campos son obligatorios"},
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

    # si hay texto buscar coincidencias
    if search:
        proveedores = proveedores.filter(
            Q(nombre_legal__icontains=search) | Q(nombre_comercial__icontains=search)
        ).order_by("nombre_legal")
    else:
        # sugerencias iniciales al abrir
        proveedores = proveedores.order_by("-id")

    proveedores = proveedores[:8]

    results = [
        {
            "id": p.id,
            "nombreLegal": p.nombre_legal,
            "nombreComercial": p.nombre_comercial,
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
        query.order_by("id"),
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
def producto_imagen(request, imagen_id):

    try:

        imagen = ProductosImagenes.objects.get(
            id=imagen_id,
            producto__is_delete=False,
        )

        # Consultar la imagen directamente en Nextcloud
        response_nextcloud = obtener_archivo(
            imagen.imagen_url
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

    except Exception as e:

        return HttpResponse(
            f"Error obteniendo imagen: {str(e)}",
            status=500,
        )


@login_required
def api_productos(request):

    search = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))

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
        query.order_by("id"),
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

                "unidadMedida": {
                    "nombre": (
                        p.unidad_medida.nombre
                        if p.unidad_medida
                        else ""
                    )
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
        precio_venta = request.POST.get("precio_venta")
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

        precio = data.get(
            "precioVenta",
            "0",
        ).replace(",", ".")

        producto.precio_venta = float(precio)

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

                    # URL real donde está el archivo en Nextcloud
                    url_nextcloud = imagen.imagen_url

                    # Limpiar doble slash
                    url_nextcloud = url_nextcloud.replace(
                        "/Productos//",
                        "/Productos/",
                    )

                    eliminar_archivo(
                        url_nextcloud
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

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    items = (
        Productos.objects.filter(is_delete=False, is_active=True)
        .filter(Q(nombre__icontains=search) | Q(codigo_sku__icontains=search))
        .select_related("marca", "categoria")[:20]
    )

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

    productos = (
        Productos.objects.select_related(
            "categoria",
            "unidad_medida",
            "marca",
        )
        .filter(
            is_delete=False,
            is_master=True,
        )
        .order_by("nombre")
    )

    data = []

    for producto in productos:
        data.append(
            {
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "codigoSKU": producto.codigo_sku,
                "precioVenta": float(producto.precio_venta),
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

    productos = (
        Productos.objects.select_related(
            "categoria",
            "unidad_medida",
            "marca",
        )
        .filter(
            is_delete=False,
            is_master=False,
        )
        .order_by("nombre")
    )

    data = []

    for producto in productos:
        data.append(
            {
                "id": producto.id,
                "nombre": producto.nombre,
                "descripcion": producto.descripcion,
                "codigoSKU": producto.codigo_sku,
                "precioVenta": float(producto.precio_venta),
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
        items = items.order_by("-id")

    items = items[:8]

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
        ).order_by("nombre")
    else:
        items = items.order_by("-id")

    items = items[:8]

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
    compras = compras.filter(u_creo_id=request.user.id)

    # Búsqueda
    if search:
        compras = compras.filter(
            Q(proveedor__nombre_legal__icontains=search)
            | Q(proveedor__nombre_comercial__icontains=search)
            | Q(total__icontains=search)
            | Q(observaciones__icontains=search)
        )

    # CONTADORES (IMPORTANTE: sin search para que sean totales reales)
    base_compras = Compras.objects.filter(u_creo_id=request.user.id)

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
            total = Decimal("0.00")
            detalles_procesados = []

            for item in detalles:
                producto_id = item.get("productoId")

                try:
                    cantidad = Decimal(str(item.get("cantidad") or 0))
                    precio = Decimal(str(item.get("precioCompra") or 0))
                except:
                    return JsonResponse(
                        {"success": False, "message": "Cantidad o precio inválido"},
                        status=400,
                    )

                if cantidad <= 0 or precio <= 0:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Cantidad y precio deben ser mayores a 0",
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
                total += subtotal

                detalles_procesados.append(
                    {"producto": producto, "cantidad": cantidad, "precio": precio}
                )

            compra = Compras.objects.create(
                proveedor=proveedor,
                ubicacion=ubicacion,
                tipo_compra=tipo_compra,
                observaciones=observaciones,
                estado=EstadoCompra.PENDIENTE,
                total=total,
                u_creo_id=request.user.id,
            )

            for item in detalles_procesados:
                DetalleCompra.objects.create(
                    compra=compra,
                    producto=item["producto"],
                    cantidad=item["cantidad"],
                    precio_compra=item["precio"],
                    u_creo_id=request.user.id,
                )

            if tipo_compra == Compras.TIPO_CREDITO and proveedor.dias_credito > 0:
                compra.fecha_vencimiento = timezone.now() + timezone.timedelta(
                    days=proveedor.dias_credito
                )
                compra.save()

            if tipo_compra == Compras.TIPO_CREDITO:
                CuentasPorPagar.objects.create(
                    proveedor_id=proveedor.id,
                    compra_id=compra.id,
                    monto_total=total,
                    monto_pendiente=total,
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


@login_required
@permission_required("manager.view_compras", raise_exception=True)
def detalle_compra_view(request, id):

    compra = get_object_or_404(
        Compras.objects.select_related("proveedor", "ubicacion").prefetch_related(
            "compra_detalles__producto"
        ),
        id=id,
        u_creo_id=request.user.id,
    )

    detalles = []

    for d in compra.compra_detalles.all():
        producto = d.producto

        detalles.append(
            {
                "productoNombre": producto.nombre,
                "productoId": producto.id,
                "presentacion": (
                    getattr(producto.unidad_medida, "abreviatura", "N/A")
                    if hasattr(producto, "unidad_medida")
                    else "N/A"
                ),
                "sku": getattr(producto, "codigo_sku", "N/A"),
                "precioCompra": float(d.precio_compra),
                "cantidad": float(d.cantidad),
                "total": float(d.cantidad * d.precio_compra),
            }
        )

    data = {
        "id": compra.id,
        "ubicacion": compra.ubicacion.nombre,
        "proveedorNombre": compra.proveedor.nombre_comercial,
        "tipoCompra": compra.get_tipo_compra_display(),
        "total": float(compra.total),
        "totalProductos": float(sum(d.cantidad for d in compra.compra_detalles.all())),
        "detalles": detalles,
    }

    return render(request, "compras/detallecompra.html", {"compra": data})


@csrf_exempt
@login_required
@permission_required("manager.view_compras", raise_exception=True)
def proxy_compras_pdf(request, id):

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
            id=id,
            u_creo_id=request.user.id,
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
        }

        pdf_bytes = generar_pdf_compra(data)

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="Compra_{id}.pdf"'
        return response

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
def generar_pdf_compra(compra, logo_path="static/img/LH.png"):

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
    impuesto = subtotal * 0.15
    total = subtotal + impuesto

    y_tot = y_table - 30

    c.drawRightString(420, y_tot, "Subtotal:")
    c.drawRightString(520, y_tot, f"{subtotal:.2f}")

    c.drawRightString(420, y_tot - 15, "Impuesto 15%:")
    c.drawRightString(520, y_tot - 15, f"{impuesto:.2f}")

    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(420, y_tot - 30, "TOTAL:")
    c.drawRightString(520, y_tot - 30, f"{total:.2f}")

    # Firmas
    y_sign = 80

    c.line(100, y_sign, 250, y_sign)
    c.drawString(100, y_sign - 15, f"Responsable: {compra['uCreo']}")

    c.line(350, y_sign, 500, y_sign)
    c.drawString(350, y_sign - 15, f"Proveedor: {compra['proveedorNombre']}")

    c.showPage()
    c.save()

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


@login_required
@permission_required("manager.change_compras", raise_exception=True)
def editar_compra(request, id):
    compra = get_object_or_404(
        Compras.objects.select_related("proveedor", "ubicacion").prefetch_related(
            "compra_detalles__producto__unidad_medida"
        ),
        id=id,
    )

    detalles = compra.compra_detalles.all()

    compra_data = {
        "proveedorId": compra.proveedor.id,
        "proveedorNombre": compra.proveedor.nombre_comercial,
        "ubicacionId": compra.ubicacion.id,
        "ubicacionNombre": getattr(compra.ubicacion, "nombre", "N/A"),
        "totalCompra": float(compra.total),
        "tipoCompra": compra.tipo_compra,
        "observaciones": compra.observaciones,
        "detalles": [
            {
                "id": d.id,
                "productoId": d.producto.id,
                "productoNombre": d.producto.nombre,
                "cantidad": float(d.cantidad),
                "precioCompra": float(d.precio_compra),
                "sku": getattr(d.producto, "codigo_sku", "N/A"),
                "presentacion": getattr(
                    getattr(d.producto, "unidad_medida", None), "abreviatura", "N/A"
                ),
            }
            for d in detalles
        ],
    }

    return render(
        request, "compras/editarcompra.html", {"compra": compra_data, "idcompra": id}
    )


@csrf_exempt
@transaction.atomic
@login_required
@permission_required("manager.change_compras", raise_exception=True)
def editar_compra_put(request, id):

    if request.method != "PUT":
        return JsonResponse({"message": "Método no permitido"}, status=405)

    try:
        data = json.loads(request.body)

        proveedor_id = data.get("proveedorId")
        tipo_compra = int(data.get("tipoCompra"))
        observaciones = data.get("observaciones", "")
        ubicacion_id = data.get("recepcionId")
        detalles = data.get("detalles", [])

        compra = get_object_or_404(
            Compras.objects.prefetch_related("compra_detalles"), id=id
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

        if not Proveedores.objects.filter(id=proveedor_id, is_delete=False).exists():
            return JsonResponse({"message": "Proveedor no válido"}, status=400)

        # =====================
        # ACTUALIZAR COMPRA
        # =====================
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
        total = Decimal("0.00")

        for d in detalles:
            producto_id = d.get("productoId")

            cantidad = Decimal(str(d.get("cantidad", 0)))
            precio = Decimal(str(d.get("precioCompra", 0)))

            if not Productos.objects.filter(id=producto_id, is_delete=False).exists():
                return JsonResponse(
                    {"message": f"Producto {producto_id} no existe"}, status=400
                )

            subtotal = cantidad * precio
            total += subtotal

            DetalleCompra.objects.create(
                compra=compra,
                producto_id=producto_id,
                cantidad=cantidad,
                precio_compra=precio,
                u_creo_id=request.user.id,
            )

        # =====================
        # TOTAL
        # =====================
        compra.total = total

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

                cuenta.monto_total = total
                cuenta.monto_pendiente = max(total - abonado, Decimal("0.00"))

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

            else:
                CuentasPorPagar.objects.create(
                    proveedor_id=proveedor_id,
                    compra_id=compra.id,
                    monto_total=total,
                    monto_pendiente=total,
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


@csrf_exempt
@login_required
@permission_required("manager.add_clientes", raise_exception=True)
def post_clientes(request):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        data = json.loads(request.body)

        dni = (data.get("dni") or "").strip()

        if not dni:
            return JsonResponse(
                {"success": False, "message": "El DNI es obligatorio"}, status=400
            )

        # =====================
        # VALIDAR DUPLICADO
        # =====================
        if Clientes.objects.filter(dni=dni, is_delete=False).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un cliente con ese DNI"},
                status=400,
            )

        # =====================
        # CREAR CLIENTE
        # =====================
        cliente = Clientes.objects.create(
            dni=dni,
            nombre=data.get("nombre") or None,
            nombre2=data.get("nombre2") or None,
            apellido=data.get("apellido") or None,
            apellido2=data.get("apellido2") or None,
            empresa=data.get("empresa") or None,
            direccion=data.get("direccion") or None,
            email=data.get("email") or None,
            telefono=data.get("telefono") or None,
            u_creo_id=request.user.id,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Cliente registrado correctamente",
                "id": cliente.id,
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_clientes", raise_exception=True)
def get_cliente(request, id):

    try:
        cliente = Clientes.objects.filter(id=id, is_delete=False).first()

        if not cliente:
            return JsonResponse(
                {"success": False, "message": "Cliente no encontrado"}, status=404
            )

        data = {
            "id": cliente.id,
            "dni": cliente.dni,
            "nombre": cliente.nombre,
            "nombre2": cliente.nombre2,
            "apellido": cliente.apellido,
            "apellido2": cliente.apellido2,
            "empresa": cliente.empresa,
            "direccion": cliente.direccion,
            "email": cliente.email,
            "telefono": cliente.telefono,
            "isActive": cliente.is_active,
        }

        return JsonResponse({"success": True, "cliente": data})

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.change_clientes", raise_exception=True)
def put_cliente(request, id):

    if request.method != "PUT":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        data = json.loads(request.body)

        dni = (data.get("dni") or "").strip()

        if not dni:
            return JsonResponse(
                {"success": False, "message": "El DNI es obligatorio"}, status=400
            )

        cliente = get_object_or_404(Clientes, id=id, is_delete=False)

        # =====================
        # VALIDAR DUPLICADO DNI
        # =====================
        if Clientes.objects.filter(dni=dni, is_delete=False).exclude(id=id).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe otro cliente con ese DNI"},
                status=400,
            )

        # =====================
        # ACTUALIZAR CAMPOS
        # =====================
        cliente.dni = dni
        cliente.nombre = data.get("nombre") or None
        cliente.nombre2 = data.get("nombre2") or None
        cliente.apellido = data.get("apellido") or None
        cliente.apellido2 = data.get("apellido2") or None
        cliente.empresa = data.get("empresa") or None
        cliente.direccion = data.get("direccion") or None
        cliente.email = data.get("email") or None
        cliente.telefono = data.get("telefono") or None

        cliente.is_active = data.get("isActive", True)

        # =====================
        # AUDITORÍA
        # =====================
        cliente.u_modifico_id = request.user.id
        cliente.f_modificacion = timezone.now()

        cliente.save()

        return JsonResponse(
            {"success": True, "message": "Cliente actualizado correctamente"}
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required
@permission_required("manager.view_clientes", raise_exception=True)
def search_clientes(request):

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


@login_required
@permission_required("manager.view_hautorizarcompra", raise_exception=True)
def recepcion_inventario_view(request):

    search = request.GET.get("search", "").strip()

    recepciones = []

    # =========================================================
    # COMPRAS
    # =========================================================
    compras_qs = Compras.objects.select_related("proveedor").prefetch_related(
        "compra_detalles",
        "compra_autorizaciones",
        "compra_devoluciones__devolucion_detalles",
    )

    if search:
        compras_qs = compras_qs.filter(
            Q(id__icontains=search) | Q(proveedor__nombre_comercial__icontains=search)
        )

    for c in compras_qs:
        total_productos = Decimal("0.00")

        for d in c.compra_detalles.all():
            autorizado = c.compra_autorizaciones.filter(
                producto_id=d.producto_id
            ).aggregate(total=Sum("cantidad_autorizada"))["total"] or Decimal("0.00")

            devuelto = DevolucionCompraDetalle.objects.filter(
                compra_id=c.id,
                producto_id=d.producto_id,
                devolucion_compra__estado=EstadoDevolucionCompra.PENDIENTE,
            ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0.00")

            pendiente = d.cantidad - autorizado - devuelto

            if pendiente > 0:
                total_productos += pendiente

        recepciones.append(
            {
                "id": c.id,
                "tipo": "Compra",
                "tipo_codigo": "COMPRA",
                "referencia": getattr(c.proveedor, "nombre_comercial", ""),
                "fecha": c.fecha_compra,
                "cantidad": float(total_productos),
                "estado": c.estado,
                "puede_autorizar": total_productos > 0,
            }
        )

    # =========================================================
    # TRASLADOS
    # =========================================================
    traslados_qs = Traslados.objects.select_related(
        "ubicacion_origen", "ubicacion_destino"
    ).prefetch_related("detalles_traslado")

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
                "tipo": "Traslado",
                "tipo_codigo": "TRASLADO",
                "referencia": f"{t.ubicacion_origen.nombre} → {t.ubicacion_destino.nombre}",
                "fecha": t.f_creacion,
                "cantidad": float(total_pendiente),
                "estado": t.estado,
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
    entradas_pendientes = len([x for x in recepciones if x["estado"] == "Pendiente"])
    total_entradas = len(recepciones)

    total_devoluciones = DevolucionCompra.objects.filter(compra__in=compras_qs).count()

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
@permission_required("manager.view_hautorizarcompra", raise_exception=True)
def autorizar_entrada_view(request, tipo, id):

    # =========================================================
    # SI ES COMPRA
    # =========================================================
    if tipo == "Compra":
        compra = get_object_or_404(
            Compras.objects.select_related("proveedor", "ubicacion").prefetch_related(
                "compra_detalles__producto__unidad_medida",
                "compra_detalles__producto__marca",
            ),
            id=id,
        )

        historial = HAutorizarCompra.objects.filter(compra_id=compra.id)

        devoluciones_pendientes = DevolucionCompraDetalle.objects.filter(
            compra_id=compra.id,
            devolucion_compra__estado=EstadoDevolucionCompra.PENDIENTE,
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

            if disponible < 0:
                disponible = Decimal("0")

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
                }
            )

        puede_autorizar = any(x["cantidad"] > 0 for x in detalles)

        compra_data = {
            "id": compra.id,
            "proveedorNombre": compra.proveedor.nombre_legal,
            "total": float(compra.total),
            "tipoCompra": compra.tipo_compra,
            "observaciones": compra.observaciones,
            "fechaCompra": compra.fecha_compra.strftime("%Y-%m-%d %H:%M"),
            "detalles": detalles,
            "puede_autorizar": puede_autorizar,
            "tipo": "Compra",
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
            id=id,
        )

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

    return render(
        request,
        "bodega/confiinventario.html",
        {
            "compra_id": id,
            "compra": compra_data,
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

        
@csrf_exempt
@transaction.atomic
@login_required
@permission_required("manager.add_hautorizarcompra", raise_exception=True)
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

                pendiente = (
                    detalle.cantidad
                    - autorizado_actual
                )

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

                productos_inventario = (
                    obtener_productos_relacionados(
                        producto,
                        cantidad,
                    )
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

            # =====================================================
            # ACTUALIZAR ESTADO DE LA COMPRA
            # =====================================================

            autorizados = (
                HAutorizarCompra.objects
                .filter(compra_id=entrada.id)
                .values("producto_id")
                .annotate(
                    total=Sum("cantidad_autorizada")
                )
            )

            map_autorizados = {
                a["producto_id"]: a["total"]
                for a in autorizados
            }

            completado = all(
                map_autorizados.get(
                    detalle.producto_id,
                    Decimal("0")
                ) >= detalle.cantidad
                for detalle in detalles
            )

            alguno_autorizado = any(
                map_autorizados.get(
                    detalle.producto_id,
                    Decimal("0")
                ) > 0
                for detalle in detalles
            )

            if completado:
                entrada.estado = EstadoCompra.COMPLETADO

            elif alguno_autorizado:
                entrada.estado = EstadoCompra.RECEPCION_PARCIAL

            else:
                entrada.estado = EstadoCompra.PENDIENTE

            entrada.save(
                update_fields=["estado"]
            )
                
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

        productos_validados = []

        # =========================
        # VALIDACIÓN DE PRODUCTOS
        # =========================
        for p in productos:
            producto_id = p.get("ProductoId")
            cantidad_raw = p.get("Cantidad", 0)
            motivo_raw = p.get("Motivo")

            try:
                cantidad = Decimal(str(cantidad_raw or 0))
            except:
                raise Exception(f"Cantidad inválida para producto {producto_id}")

            if cantidad <= 0:
                continue

            if motivo_raw in [None, ""]:
                raise Exception(f"Debe indicar motivo para producto {producto_id}")

            motivo = int(motivo_raw)

            detalle_compra = compra.compra_detalles.filter(
                producto_id=producto_id
            ).first()

            if not detalle_compra:
                raise Exception(f"Producto {producto_id} no pertenece a esta compra")

            cantidad_comprada = detalle_compra.cantidad

            # =========================
            # DEVOLUCIONES ACTIVAS (IMPORTANTE)
            # SOLO PENDIENTES Y APROBADAS
            # =========================
            cantidad_devuelta = DevolucionCompraDetalle.objects.filter(
                compra_id=compra.id,
                producto_id=producto_id,
                devolucion_compra__estado__in=[
                    EstadoDevolucionCompra.PENDIENTE,
                    EstadoDevolucionCompra.APROBADA,
                ],
            ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0")

            disponible = cantidad_comprada - cantidad_devuelta

            if cantidad > disponible:
                raise Exception(
                    f"La cantidad a devolver del producto {producto_id} excede lo disponible. "
                    f"Disponible: {disponible}"
                )

            productos_validados.append(
                {"producto_id": producto_id, "cantidad": cantidad, "motivo": motivo}
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
            )

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
@login_required
def generar_pdf_devolucion(devolucion, logo_path="static/img/LH.png"):
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

    fecha = devolucion.f_creacion.strftime("%d/%m/%Y %H:%M")

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

    # Línea
    y_sep = y - 4 * line_height - 5
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
        0: "Producto Dañado",
        1: "Producto Vencido",
        2: "Error de Pedido",
        3: "Producto Incorrecto",
        4: "Exceso Inventario",
        5: "Otro",
    }

    for item in devolucion.devolucion_detalles.select_related("producto").all():
        producto_nombre = str(item.producto.nombre)[:28]
        sku = str(item.producto.codigo_sku)
        cantidad = str(item.cantidad)
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
            "imagenes_producto"  # 👈 importante para la tabla nueva
        )
        .filter(is_delete=False)
    )

    if search:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=search)
            | Q(codigo_sku__icontains=search)
            | Q(marca__nombre__icontains=search)
        )

    paginator = Paginator(productos_qs.order_by("nombre"), 12)
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
            imagen_obj.imagen_url
            if imagen_obj and imagen_obj.imagen_url
            else "/static/img/noimage.png"
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
        },
    )


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

            stock_disponible = (
                stock_fisico - reservado
            )

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
                        stock_disponible
                    ),
                }
            )

        # ==========================================
        # IMAGEN DESDE NEXTCLOUD
        # ==========================================

        imagen = (
            producto.imagenes_producto.first()
        )

        if imagen:
            imagen_url = request.build_absolute_uri(
                reverse(
                    "producto_imagen",
                    args=[imagen.id],
                )
            )
        else:
            imagen_url = "/static/img/noimage.png"

        # ==========================================
        # RESPUESTA
        # ==========================================

        return JsonResponse(
            {
                "producto": {
                    "id": producto.id,
                    "nombre": producto.nombre,
                    "imagenUrl": imagen_url,
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
def detalle_devolucion_view(request, id):

    devolucion = get_object_or_404(
        DevolucionCompra.objects.select_related(
            "compra", "compra__proveedor", "compra__ubicacion"
        ).prefetch_related("devolucion_detalles__producto"),
        id=id,
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
def aprobar_devolucion_view(request, id):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        devolucion = get_object_or_404(DevolucionCompra, id=id)

        if devolucion.estado != EstadoDevolucionCompra.PENDIENTE:
            return JsonResponse(
                {"success": False, "message": "La devolución ya fue procesada"},
                status=400,
            )

        devolucion.estado = EstadoDevolucionCompra.APROBADA
        devolucion.u_modifico_id = request.user.id
        devolucion.save()

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
def rechazar_devolucion_view(request, id):

    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        data = json.loads(request.body or "{}")
        motivo_rechazo = data.get("motivo", "Sin motivo")

        devolucion = get_object_or_404(DevolucionCompra, id=id)

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

    imagen_subquery = (
        ProductosImagenes.objects
        .filter(
            producto_id=OuterRef("producto_id"),
            imagen_url__isnull=False,
        )
        .exclude(
            imagen_url=""
        )
        .values("id")[:1]
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
    )

    data = []

    for item in inventario:

        stock = float(
            item["total_stock"] or 0
        )

        if stock <= 0:
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

    return JsonResponse(
        data,
        safe=False,
    )


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
@login_required
def caja_view(request):

    if not request.user.groups.filter(name="cajeros").exists():
        raise PermissionDenied("No tienes permiso")

    hoy = timezone.localdate()

    caja_hoy = CajaAC.objects.filter(
        usuario_id=request.user.id,
        fecha_apertura__date=hoy
    ).first()

    mostrar_modal_apertura = False
    caja_cerrada_hoy = False
    caja_abierta = False

    if caja_hoy is None:
        # El usuario todavía no ha abierto caja hoy.
        mostrar_modal_apertura = True

    elif caja_hoy.estado == "abierta":
        # La caja está abierta.
        caja_abierta = True

    elif caja_hoy.estado == "cuadre":
        # Ya inició el cierre pero todavía no ha
        # terminado el cuadre.
        return redirect("cuadre_caja")

    elif caja_hoy.estado == "cerrada":
        # Ya terminó completamente la caja del día.
        caja_cerrada_hoy = True

    context = {
        "mostrar_buscador": False,
        "mostrar_codigo": True,
        "mostrar_modal_apertura": mostrar_modal_apertura,
        "caja_cerrada_hoy": caja_cerrada_hoy,
        "caja_abierta": caja_abierta,
    }

    return render(request, "caja/caja.html", context)


@login_required
@require_POST
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

    caja_hoy = CajaAC.objects.filter(
        usuario_id=request.user.id,
        fecha_apertura__date=hoy
    ).first()

    if caja_hoy:

        if caja_hoy.estado == "cerrada":
            mensaje = "Esta caja ya fue cerrada por el día de hoy."

        elif caja_hoy.estado == "cuadre":
            mensaje = "Esta caja ya se encuentra en proceso de cuadre."

        else:
            mensaje = "Ya existe una caja abierta para el día de hoy."

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
def iniciar_cuadre(request):

    hoy = timezone.localdate()

    caja = CajaAC.objects.filter(
        usuario_id=request.user.id,
        fecha_apertura__date=hoy,
        estado="abierta"
    ).first()

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
def cuadre_caja(request):

    if not request.user.groups.filter(name="cajeros").exists():
        raise PermissionDenied("No tienes permiso")

    hoy = timezone.localdate()

    caja = CajaAC.objects.filter(
        usuario_id=request.user.id,
        fecha_apertura__date=hoy,
        estado="cuadre"
    ).first()

    if not caja:
        return redirect("caja")

    # =========================
    # VENTAS DEL USUARIO HOY
    # =========================

    ventas_hoy = Ventas.objects.filter(
        u_creo_id=request.user.id,
        f_creacion__date=hoy
    ).aggregate(
        total=Sum("total")
    )["total"] or Decimal("0.00")

    # =========================
    # TOTAL ESPERADO
    # =========================

    total_esperado = (
        caja.monto_apertura + ventas_hoy
    )

    context = {
        "caja": caja,
        "ventas_hoy": ventas_hoy,
        "total_esperado": total_esperado,
    }

    return render(
        request,
        "caja/cuadre_caja.html",
        context
    )

@login_required
@transaction.atomic
def cerrar_cuadre_caja(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "ok": False,
                "mensaje": "Método no permitido."
            },
            status=405
        )

    if not request.user.groups.filter(name="cajeros").exists():
        raise PermissionDenied("No tienes permiso")

    hoy = timezone.localdate()

    caja = CajaAC.objects.filter(
        usuario_id=request.user.id,
        fecha_apertura__date=hoy,
        estado="cuadre"
    ).first()

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

        denominaciones = [
            Decimal("1.00"),
            Decimal("2.00"),
            Decimal("5.00"),
            Decimal("10.00"),
            Decimal("20.00"),
            Decimal("50.00"),
            Decimal("100.00"),
            Decimal("200.00"),
            Decimal("500.00"),
        ]

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

        ventas_hoy = Ventas.objects.filter(
            u_creo_id=request.user.id,
            f_creacion__date=hoy
        ).aggregate(
            total=Sum("total")
        )["total"] or Decimal("0.00")

        # =========================
        # TOTAL ESPERADO
        # =========================

        total_esperado = (
            caja.monto_apertura + ventas_hoy
        )

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

        # =========================
        # CERRAR CAJA
        # =========================

        caja.ventas = ventas_hoy
        caja.monto_cierre = total_contado
        caja.diferencia = diferencia
        caja.fecha_cierre = timezone.now()
        caja.estado = "cerrada"

        caja.save()

        return JsonResponse({
            "ok": True,
            "mensaje": "El cuadre de caja se cerró correctamente.",
            "total_contado": str(total_contado),
            "total_esperado": str(total_esperado),
            "diferencia": str(diferencia),
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

            caja.total_cierre = (
                caja.monto_apertura +
                caja.ventas
            )

        else:

            caja.total_cierre = None


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

@login_required
def busqueda_codigo(request, codigo):

    if not request.user.groups.filter(name="cajeros").exists():
        return JsonResponse(
            {"error": "Usuario no valido"},
            status=403
        )

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
        # ==========================================

        existencia = (
            Inventarios.objects.filter(
                producto_id=producto.id,
                ubicacion_id=sucursal_id,
                is_delete=False,
                cantidad__gt=0
            )
            .aggregate(
                total=Sum("cantidad")
            )["total"]
            or Decimal("0")
        )

        existencia = Decimal(str(existencia))

        # ==========================================
        # RESERVAS ACTIVAS
        # ==========================================

        reservado = (
            ReservaInventario.objects.filter(
                producto_id=producto.id,
                ubicacion_id=sucursal_id,
                estado=ReservaInventario.Estado.RESERVADA,
                is_delete=False,
            )
            .aggregate(
                total=Sum("cantidad")
            )["total"]
            or Decimal("0")
        )

        reservado = Decimal(str(reservado))

        # ==========================================
        # EXISTENCIA DISPONIBLE
        # ==========================================

        stock_disponible = existencia - reservado

        if stock_disponible < 0:
            stock_disponible = Decimal("0")

        if stock_disponible <= 0:
            return JsonResponse(
                {
                    "error": "El producto no tiene existencia disponible en esta sucursal"
                },
                status=400,
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
            "id_categoria": producto.categoria_id,
            "isv": isv,
            "tipos_isv": producto.impuesto,
            "stock": stock_disponible,
        }

        # ==========================================
        # DESCUENTO POR CANTIDAD
        # ==========================================

        cantidad_descuento = descuento_cantidad(data)

        if cantidad_descuento["lleva"] > 0:

            data["lleva"] = cantidad_descuento["lleva"]
            data["paga"] = cantidad_descuento["paga"]
            data["descuentos"] = 0
            data["acumulable"] = (
                cantidad_descuento["es_acumulable"]
            )

        else:

            descuento = valor_descuento(data)

            data["lleva"] = 0
            data["paga"] = 0
            data["descuentos"] = descuento.get(
                "valor",
                0
            )
            data["acumulable"] = descuento.get(
                "es_acumulable",
                False
            )

        return JsonResponse(data)

    except Productos.DoesNotExist:
        return JsonResponse(
            {"error": "Producto no encontrado"},
            status=404
        )
    

@login_required
def busqueda_nombre(request, producto):

    if not request.user.groups.filter(name="cajeros").exists():
        return JsonResponse(
            {"error": "Usuario no valido"},
            status=403
        )

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
        # ==========================================

        existencia = (
            Inventarios.objects.filter(
                producto_id=c.id,
                ubicacion_id=sucursal_id,
                is_delete=False,
            )
            .aggregate(
                total=Sum("cantidad")
            )["total"]
            or Decimal("0")
        )

        existencia = Decimal(str(existencia))

        # ==========================================
        # RESERVAS ACTIVAS
        # ==========================================

        reservado = (
            ReservaInventario.objects.filter(
                producto_id=c.id,
                ubicacion_id=sucursal_id,
                estado=ReservaInventario.Estado.RESERVADA,
                is_delete=False,
            )
            .aggregate(
                total=Sum("cantidad")
            )["total"]
            or Decimal("0")
        )

        reservado = Decimal(str(reservado))

        # ==========================================
        # STOCK DISPONIBLE
        # ==========================================

        stock_disponible = existencia - reservado

        if stock_disponible < 0:
            stock_disponible = Decimal("0")

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

            es_acumulable = (
                cantidad_descuento[
                    "es_acumulable"
                ]
            )

        else:

            descuento_data = valor_descuento(
                {
                    "id": c.id,
                    "id_categoria": c.categoria_id,
                    "precio_venta": c.precio_venta,
                }
            )

            descuento = descuento_data["valor"]

            es_acumulable = (
                descuento_data[
                    "es_acumulable"
                ]
            )

        # ==========================================
        # DATOS DEL PRODUCTO
        # ==========================================

        producto_data = {
            "id": c.id,
            "codigo_sku": c.codigo_sku,
            "nombre": c.nombre,
            "precio_venta": c.precio_venta,

            "lleva": lleva,
            "paga": paga,

            "descuento": descuento,
            "es_acumulable": es_acumulable,

            "isv": c.precio_venta * (
                Decimal(c.impuesto) / Decimal(100)
            ),

            "tipos_isv": c.impuesto,

            # IMPORTANTE:
            # Enviar disponible, no físico
            "stock": stock_disponible,
        }

        data.append(producto_data)

    return JsonResponse(
        data,
        safe=False
    )



@login_required
@require_http_methods(["POST"])
def guardar_compra(request):
    try:
        with transaction.atomic():

            # =====================================================
            # PERFIL / SUCURSAL
            # =====================================================

            perfil = PerfilUsuario.objects.get(
                usuarios=request.user
            )

            sucursal_id = perfil.ubicacion_id

            # =====================================================
            # DATOS RECIBIDOS
            # =====================================================

            data = json.loads(request.body)

            pago = data.get("pagos", [])
            productos = data.get("productos", [])
            tarjeta = data.get("tarjeta", [])
            cliente = data.get("cliente", {})

            if not pago:
                raise Exception("No se recibieron los datos de pago")

            if not productos:
                raise Exception("No se recibieron productos")

            # =====================================================
            # GENERAR NUMERO DE FACTURA
            # =====================================================

            sat = datos_sat.objects.filter(
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
            # TOTALES GENERALES
            # =====================================================

            costo_total_venta = Decimal("0")
            utilidad_total_venta = Decimal("0")

            # =====================================================
            # CREAR VENTA
            # =====================================================

            venta = Ventas.objects.create(
                id_factura_cai=factura_cai,
                id_cliente_id=cliente.get("id"),
                sucursal_id=sucursal_id,
                subtotal=pago[0].get("subtotal"),
                impuesto_15=pago[0].get("isv15"),
                impuesto_18=pago[0].get("isv18"),
                descuento=pago[0].get("descuento"),
                total=pago[0].get("total"),
                tipo_pago=pago[0].get("tipo_pago"),
                costo_total=0,
                utilidad_total=0,
                u_creo_id=request.user.id,
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

            # =====================================================
            # DETALLE DE PRODUCTOS
            # =====================================================

            for p in productos:

                producto_id = p.get("id")

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

                # =================================================
                # OBTENER PRODUCTO VENDIDO
                # =================================================

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
                        f"El producto {producto_id} no existe o está inactivo"
                    )

                # =================================================
                # OBTENER TODOS LOS PRODUCTOS RELACIONADOS
                #
                # Ejemplo:
                #
                # Caja = equival_unid 12
                # Lapiz = equival_unid 1
                #
                # Venta:
                # Caja 1
                #
                # Resultado:
                # Caja  = 1
                # Lapiz = 12
                #
                # Venta:
                # Lapiz 8
                #
                # Resultado:
                # Lapiz = 8
                # Caja  = 0.666666...
                # =================================================

                productos_inventario = (
                    obtener_productos_relacionados(
                        producto,
                        cantidad_vendida,
                    )
                )

                # =================================================
                # COSTO TOTAL DE ESTA LÍNEA DE VENTA
                #
                # IMPORTANTE:
                #
                # Aquí NO usamos únicamente el producto vendido.
                #
                # Calculamos el costo de todos los productos que
                # realmente se están rebajando del inventario.
                # =================================================

                costo_total_producto = Decimal("0")

                # =================================================
                # PROCESAR CADA PRODUCTO DEL GRUPO
                # =================================================

                for item in productos_inventario:

                    producto_inventario = item["producto"]

                    cantidad_a_rebajar = Decimal(
                        item["cantidad"]
                    )

                    if cantidad_a_rebajar <= 0:
                        continue

                    # =================================================
                    # STOCK DEL PRODUCTO RELACIONADO
                    # =================================================

                    stock_total = (
                        Inventarios.objects
                        .filter(
                            producto=producto_inventario,
                            ubicacion_id=sucursal_id,
                            cantidad__gt=0,
                        )
                        .aggregate(
                            total=Sum("cantidad")
                        )["total"]
                        or Decimal("0")
                    )

                    # =================================================
                    # VALIDAR STOCK
                    #
                    # Ejemplo:
                    #
                    # Caja = 10
                    # Lapiz = 120
                    #
                    # Venta 8 lapices:
                    #
                    # Lapiz necesita 8
                    # Caja necesita 0.666666
                    #
                    # Ambos deben tener stock.
                    # =================================================

                    if stock_total < cantidad_a_rebajar:

                        raise Exception(
                            f"Stock insuficiente para "
                            f"{producto_inventario.nombre}. "
                            f"Disponible: {stock_total}, "
                            f"necesario: {cantidad_a_rebajar}"
                        )

                    # =================================================
                    # LOTES FIFO
                    # =================================================

                    lotes = (
                        Inventarios.objects
                        .filter(
                            producto=producto_inventario,
                            ubicacion_id=sucursal_id,
                            cantidad__gt=0,
                        )
                        .order_by("f_creacion", "id")
                    )

                    cantidad_necesaria = (
                        cantidad_a_rebajar
                    )

                    # =================================================
                    # REBAJAR LOTES
                    # =================================================

                    for lote in lotes:

                        if cantidad_necesaria <= 0:
                            break

                        # =================================================
                        # CANTIDAD QUE SALE DE ESTE LOTE
                        # =================================================

                        cantidad_consumida = min(
                            lote.cantidad,
                            cantidad_necesaria,
                        )

                        # =================================================
                        # OBTENER COSTO DEL LOTE
                        # =================================================

                        detalle_compra = (
                            DetalleCompra.objects
                            .filter(
                                compra_id=lote.compra_id,
                                producto_id=lote.producto_id,
                            )
                            .first()
                        )

                        # =================================================
                        # COSTO DIRECTO
                        #
                        # Si el producto fue comprado directamente:
                        #
                        # Compra:
                        # Lapiz 100 unidades
                        # Precio = 2.00
                        #
                        # Entonces:
                        # costo = 2.00
                        # =================================================

                        if detalle_compra:

                            costo_unitario_lote = (
                                detalle_compra.precio_compra
                            )

                        else:

                            # =================================================
                            # COSTO DERIVADO
                            #
                            # Esto sucede cuando:
                            #
                            # Compramos:
                            # Caja Lapiz = L20
                            #
                            # Caja contiene:
                            # 12 Lapices
                            #
                            # Inventario crea:
                            #
                            # Caja = 1
                            # Lapiz = 12
                            #
                            # El lote de Lapiz no tiene DetalleCompra
                            # porque realmente compramos una Caja.
                            #
                            # Entonces buscamos el costo del producto
                            # padre/master.
                            # =================================================

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

                                    # ==========================================
                                    # COSTO POR UNIDAD DEL PRODUCTO HIJO
                                    #
                                    # Ejemplo:
                                    #
                                    # Caja = L20
                                    # equival_unid Caja = 12
                                    #
                                    # Lapiz:
                                    # equival_unid = 1
                                    #
                                    # costo:
                                    #
                                    # 20 * 1 / 12 = 1.666666
                                    # ==========================================

                                    costo_unitario_lote = (
                                        Decimal(
                                            detalle_padre.precio_compra
                                        )
                                        * equivalencia_hijo
                                        / equivalencia_padre
                                    )

                                    break

                            # =================================================
                            # SI NO SE PUDO ENCONTRAR COSTO
                            # =================================================

                            if costo_unitario_lote is None:

                                raise Exception(
                                    f"No existe costo registrado para "
                                    f"{producto_inventario.nombre} "
                                    f"en el lote {lote.id}"
                                )

                        # =================================================
                        # ACUMULAR COSTO
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

                        cantidad_necesaria -= (
                            cantidad_consumida
                        )

                        lote.save(
                            update_fields=["cantidad"]
                        )

                        # =================================================
                        # STOCK RESULTANTE DEL PRODUCTO
                        # =================================================

                        stock_resultante = (
                            Inventarios.objects
                            .filter(
                                producto=producto_inventario,
                                ubicacion_id=sucursal_id,
                            )
                            .aggregate(
                                total=Sum("cantidad")
                            )["total"]
                            or Decimal("0")
                        )

                        # =================================================
                        # MOVIMIENTO DE INVENTARIO
                        # =================================================

                        MovimientoInventario.objects.create(
                            tipo_movimiento=TipoMovimientoInventario.SALIDA_VENTA,
                            producto=producto_inventario,
                            ubicacion_origen_id=sucursal_id,
                            cantidad=cantidad_consumida,
                            stock_anterior=stock_anterior,
                            stock_resultante=stock_resultante,
                        )

                    # =================================================
                    # SEGURIDAD
                    # =================================================

                    if cantidad_necesaria > 0:

                        raise Exception(
                            f"No fue posible completar la salida de "
                            f"{producto_inventario.nombre}. "
                            f"Faltan {cantidad_necesaria} unidades."
                        )

                # =================================================
                # COSTO PROMEDIO DE LA LÍNEA
                #
                # OJO:
                #
                # Aquí dividimos entre la cantidad vendida del
                # producto original.
                #
                # Si vendemos 1 Caja:
                #
                # costo_total = costo Caja + costo de sus 12 Lapices
                #
                # Pero para evitar duplicar el costo, realmente
                # debemos considerar que los productos relacionados
                # representan el MISMO inventario económico.
                #
                # Por eso usamos el costo del producto vendido.
                # =================================================

                costo_promedio = (
                    costo_total_producto / cantidad_vendida
                )

                utilidad_unitaria = (
                    precio_venta - costo_promedio
                )

                utilidad_total = (
                    utilidad_unitaria
                    * cantidad_vendida
                )

                costo_total_venta += (
                    costo_total_producto
                )

                utilidad_total_venta += (
                    utilidad_total
                )

                # =================================================
                # CREAR DETALLE DE VENTA
                # =================================================

                DetalleVenta.objects.create(
                    venta=venta,
                    producto_id=producto_id,
                    cantidad=cantidad_vendida,
                    precio_unitario=precio_venta,
                    costo_unitario=costo_promedio,
                    utilidad_unitaria=utilidad_unitaria,
                    utilidad_total=utilidad_total,

                    descuento=Decimal(
                        str(
                            p.get(
                                "descuento",
                                0,
                            )
                        )
                    ),

                    impuesto_15=Decimal(
                        str(
                            p.get(
                                "isv_15",
                                0,
                            )
                        )
                    ),

                    impuesto_18=Decimal(
                        str(
                            p.get(
                                "isv_18",
                                0,
                            )
                        )
                    ),

                    u_creo_id=request.user.id,
                )

            # =====================================================
            # ACTUALIZAR TOTALES DE LA VENTA
            # =====================================================

            venta.costo_total = costo_total_venta
            venta.utilidad_total = utilidad_total_venta

            venta.save(
                update_fields=[
                    "costo_total",
                    "utilidad_total",
                ]
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
def imprimir_factura(request, id_factura):

    # ==========================================
    # FACTURA CAI
    # ==========================================

    factura_cai = (
        facturas_cai.objects.select_related(
            "id_cai",
            "id_cai__id_sucursal",
        )
        .filter(id=id_factura)
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

    detalles = (
        DetalleVenta.objects.select_related("producto")
        .filter(venta=venta)
        .order_by("id")
    )

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
    # SUCURSAL
    # ==========================================

    direccion = ""

    if venta.sucursal:
        direccion = getattr(venta.sucursal, "ubicacion", "")

    # ==========================================
    # CALCULAR ALTO DINAMICO
    # ==========================================

    ancho_ticket = 80 * mm

    lineas_direccion = len(textwrap.wrap(direccion, width=35))

    alto_ticket = (
        130 * mm  # encabezado, cliente, totales y pie
        + (len(detalles) * 12)
        + (lineas_direccion * 10)
    )

    if tarjeta:
        alto_ticket += 15 * mm

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

    pdf.setFont("Helvetica-Bold", 14)

    pdf.drawCentredString(ancho / 2, y, "ORVEND MART")

    y -= 18

    pdf.setFont("Helvetica", 8)

    for linea in textwrap.wrap(direccion, width=35):
        pdf.drawCentredString(ancho / 2, y, linea)

        y -= 10

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
        ancho / 2, y, f"Fecha: {venta.f_creacion.strftime('%d/%m/%Y %I:%M %p')}"
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
        pdf.drawString(10, y, f"{venta.id_cliente}")

    else:
        pdf.drawString(10, y, "Consumidor Final")

    y -= 20

    # ==========================================
    # DETALLE PRODUCTOS
    # ==========================================

    pdf.setFont("Helvetica-Bold", 8)

    pdf.drawString(10, y, "PRODUCTO")

    pdf.drawRightString(150, y, "CANT")

    pdf.drawRightString(205, y, "P/U")

    pdf.drawRightString(290, y, "TOTAL")

    y -= 10

    pdf.line(10, y, ancho - 10, y)

    y -= 12

    pdf.setFont("Helvetica", 8)

    for detalle in detalles:
        total_linea = detalle.cantidad * detalle.precio_unitario

        # producto limitado para no invadir columnas
        nombre_producto = str(detalle.producto)[:18]

        pdf.drawString(10, y, nombre_producto)

        pdf.drawRightString(150, y, str(detalle.cantidad))

        pdf.drawRightString(205, y, f"{detalle.precio_unitario:.2f}")

        pdf.drawRightString(290, y, f"{total_linea:.2f}")

        y -= 12

    # ==========================================
    # TOTALES
    # ==========================================

    y -= 5

    pdf.line(10, y, ancho - 10, y)

    y -= 15

    pdf.setFont("Helvetica", 8)

    for nombre, valor in [
        ("Subtotal", venta.subtotal),
        ("ISV 15%", venta.impuesto_15),
        ("ISV 18%", venta.impuesto_18),
        ("Descuento", venta.descuento),
    ]:
        # Etiqueta a la izquierda
        pdf.drawString(10, y, nombre)

        # Valor alineado a la derecha
        pdf.drawRightString(ancho - 10, y, f"L {valor:.2f}")

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

    pdf.drawCentredString(ancho / 2, y, "Gracias por su compra")

    pdf.save()

    buffer.seek(0)

    return HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="factura.pdf"'},
    )


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


# función para el valor del desciuento
def valor_descuento(data):
    descuento_producto = (
        Descuento.objects.filter(
            productos__id=data["id"], is_active=True, es_cupon=False, es_cantidad=False
        )
        .values()
        .first()
    )

    descuento_categoria = (
        Descuento.objects.filter(
            categorias__id=data["id_categoria"], is_active=True, es_cupon=False
        )
        .values()
        .first()
    )

    if not descuento_categoria:
        descuento_categoria = {
            "es_porcentaje": False,
            "valor": 0,
        }

    if not descuento_categoria and not descuento_producto:
        return {"valor": 0.00, "es_acumulable": False}

    valor_descuento_producto = 0
    valor_descuento_categoria = 0
    total_descuento = 0
    acumulable = False

    if descuento_producto:
        # descuento por producto
        if descuento_producto["es_porcentaje"] == True:
            valor_descuento_producto = data["precio_venta"] * (
                descuento_producto["valor"] / 100
            )
        else:
            valor_descuento_producto = descuento_producto["valor"]

        ##descuento por categoria
        if descuento_categoria["es_porcentaje"] == True:
            valor_descuento_categoria = data["precio_venta"] * (
                descuento_categoria["valor"] / 100
            )
        else:
            valor_descuento_categoria = descuento_categoria["valor"]

        if descuento_producto["acumulable"] == True:
            total_descuento = valor_descuento_producto + valor_descuento_categoria
            acumulable = True
        else:
            total_descuento = valor_descuento_producto
    else:
        if descuento_categoria["es_porcentaje"] == True:
            valor_descuento_categoria = data["precio_venta"] * (
                descuento_categoria["valor"] / 100
            )
        else:
            valor_descuento_categoria = descuento_categoria["valor"]

        total_descuento = valor_descuento_categoria

    return {"valor": total_descuento, "es_acumulable": acumulable}



def descuento_cantidad(data):
    descuento = (
        Descuento.objects.filter(
            productos__id=data["id"], is_active=True, es_cantidad=True
        )
        .values()
        .first()
    )

    if not descuento:
        return {"lleva": 0, "paga": 0, "es_acumulable": False}
    else:
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

    fecha_hoy = date.today()

    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")
    sucursal = request.GET.get("sucursal")

    if not fecha_inicio:
        fecha_inicio = fecha_hoy.strftime("%Y-%m-%d")

    if not fecha_fin:
        fecha_fin = fecha_hoy.strftime("%Y-%m-%d")

    detalles = (
        DetalleVenta.objects.select_related(
            "producto",
            "venta",
            "venta__id_cliente",
            "venta__sucursal",
            "venta__id_factura_cai",
        )
        .filter(
            venta__f_creacion__date__gte=fecha_inicio,
            venta__f_creacion__date__lte=fecha_fin,
        )
        .order_by("-venta__id")
    )

    # ======================================
    # FILTRO SUCURSAL
    # ======================================

    if sucursal:
        detalles = detalles.filter(venta__sucursal_id=sucursal)

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
