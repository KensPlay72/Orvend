import json
import traceback
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.exceptions import PermissionDenied

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

        if not nombre or not abreviatura:
            return JsonResponse(
                {"success": False, "message": "Nombre y abreviatura son obligatorios"},
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
            nombre=nombre, abreviatura=abreviatura, u_creo_id=request.user.id
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
        is_active = data.get("IsActive", True)

        if not nombre or not abreviatura:
            return JsonResponse(
                {"success": False, "message": "Nombre y abreviatura son obligatorios"},
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
        medida.is_active = is_active
        medida.u_modifico_id = request.user.id
        medida.f_modificacion = timezone.now()
        medida.save()

        return JsonResponse({"success": True, "message": "Actualizado correctamente"})

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
        "categoria", "unidad_medida", "marca"
    ).all()

    # excluir eliminados
    query = query.filter(is_delete=False)

    # -------------------------
    # CONTADORES (NO AFECTADOS POR PAGINADOR)
    # -------------------------
    total_productos = query.count()
    productos_activos = query.filter(is_active=True).count()
    productos_inactivos = query.filter(is_active=False).count()

    # -------------------------
    # SEARCH
    # -------------------------
    if search:
        query = query.filter(
            Q(nombre__icontains=search) | Q(codigo_sku__icontains=search)
        )

    # -------------------------
    # PAGINADOR
    # -------------------------
    paginator = Paginator(query.order_by("id"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "search": search,
        # contadores
        "total_productos": total_productos,
        "productos_activos": productos_activos,
        "productos_inactivos": productos_inactivos,
    }

    return render(request, "gestiones/productos.html", context)


@login_required
def api_productos(request):

    search = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 10))

    query = Productos.objects.select_related(
        "categoria", "unidad_medida", "marca"
    ).filter(is_delete=False)

    # SEARCH
    if search:
        query = query.filter(
            Q(nombre__icontains=search) | Q(codigo_sku__icontains=search)
        )

    # PAGINADOR
    paginator = Paginator(query.order_by("id"), limit)
    page_obj = paginator.get_page(page)

    # RESPONSE JSON
    data = {
        "results": [
            {
                "id": p.id,
                "nombre": p.nombre,
                "codigoSKU": p.codigo_sku,
                "precioVenta": str(p.precio_venta),
                "unidadMedida": {
                    "nombre": p.unidad_medida.nombre if p.unidad_medida else ""
                },
                "categoria": {"nombre": p.categoria.nombre if p.categoria else ""},
                "marca": {"nombre": p.marca.nombre if p.marca else ""},
                "imagenUrl": p.imagen_url or "",
                "imagenNombre": p.imagen_nombre or "",
            }
            for p in page_obj
        ],
        "page": page_obj.number,
        "totalPages": paginator.num_pages,
    }

    return JsonResponse(data)


@login_required
@permission_required("manager.add_productos", raise_exception=True)
@require_http_methods(["POST"])
def post_producto(request):
    try:
        import os
        import uuid

        nombre = request.POST.get("nombre", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        categoria_id = request.POST.get("categoria")
        unidad_medida_id = request.POST.get("unidad_medida")
        marca_id = request.POST.get("marca")
        codigo_sku = request.POST.get("codigo_sku", "").strip()
        precio_venta = request.POST.get("precio_venta")
        vencimiento = str(request.POST.get("Vencimiento")).lower() == "true"

        imagen = request.FILES.get("Imagen")

        # =========================
        # VALIDACIONES
        # =========================
        if (
            not nombre
            or not categoria_id
            or not unidad_medida_id
            or not marca_id
            or not codigo_sku
            or not precio_venta
        ):
            return JsonResponse(
                {"success": False, "message": "Campos obligatorios faltantes"},
                status=400,
            )

        if Productos.objects.filter(codigo_sku=codigo_sku).exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": "Ya existe un producto con ese código SKU",
                },
                status=400,
            )

        categoria = Categorias.objects.filter(id=categoria_id).first()
        unidad = UMedidas.objects.filter(id=unidad_medida_id).first()
        marca = Marcas.objects.filter(id=marca_id).first()

        if not categoria or not unidad or not marca:
            return JsonResponse(
                {"success": False, "message": "Categoría, unidad o marca inválida"},
                status=400,
            )

        # =========================
        # CREAR PRODUCTO
        # =========================
        producto = Productos(
            nombre=nombre,
            descripcion=descripcion,
            categoria=categoria,
            unidad_medida=unidad,
            marca=marca,
            codigo_sku=codigo_sku,
            precio_venta=precio_venta,
            vencimiento=vencimiento,
            u_creo_id=request.user.id,
        )

        # =========================
        # IMAGEN (5 caracteres + nombre original)
        # =========================
        if imagen:
            # Limpiar nombre original (quitar espacios)
            nombre_original = imagen.name.replace(" ", "_")

            # Generar prefijo de 5 caracteres
            random_prefix = uuid.uuid4().hex[:5]

            # Nuevo nombre
            nuevo_nombre = f"{random_prefix}_{nombre_original}"

            # Ruta física
            base_dir = os.path.join(settings.BASE_DIR, "manager", "media", "productos")
            os.makedirs(base_dir, exist_ok=True)

            file_path = os.path.join(base_dir, nuevo_nombre)

            # Guardar archivo
            with open(file_path, "wb+") as destination:
                for chunk in imagen.chunks():
                    destination.write(chunk)

            # Guardar en BD
            producto.imagen_nombre = nuevo_nombre
            producto.imagen_url = f"/manager/media/productos/{nuevo_nombre}"

        # =========================
        # GUARDAR
        # =========================
        producto.save()

        return JsonResponse(
            {"success": True, "message": "Producto registrado correctamente"}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": "Error interno: " + str(e)}, status=500
        )


@login_required
@permission_required("manager.view_productos", raise_exception=True)
def get_producto(request, id):

    producto = (
        Productos.objects.select_related("categoria", "unidad_medida", "marca")
        .filter(id=id, is_delete=False)
        .first()
    )

    if not producto:
        return JsonResponse(
            {"success": False, "message": "Producto no encontrado"}, status=404
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
                "imagenNombre": producto.imagen_nombre,
                "imagenUrl": producto.imagen_url,
                "isActive": producto.is_active,
                "vencimiento": producto.vencimiento,
                # relaciones
                "categoriaId": producto.categoria.id if producto.categoria else None,
                "categoria": (
                    {"nombre": producto.categoria.nombre}
                    if producto.categoria
                    else None
                ),
                "unidadMedidaId": (
                    producto.unidad_medida.id if producto.unidad_medida else None
                ),
                "unidadMedida": (
                    {
                        "nombre": producto.unidad_medida.nombre,
                        "abreviatura": producto.unidad_medida.abreviatura,
                    }
                    if producto.unidad_medida
                    else None
                ),
                "marcasId": producto.marca.id if producto.marca else None,
                "marcas": {"nombre": producto.marca.nombre} if producto.marca else None,
            },
        }
    )


@login_required
@permission_required("manager.change_productos", raise_exception=True)
@require_http_methods(["POST"])
def put_producto(request, id):

    try:
        # Buscar el producto
        producto = Productos.objects.filter(id=id, is_delete=False).first()

        if not producto:
            return JsonResponse(
                {"success": False, "message": "Producto no encontrado"}, status=404
            )

        data = request.POST

        # =========================
        # CAMPOS BÁSICOS
        # =========================
        producto.nombre = data.get("Nombre", "").strip()
        producto.descripcion = data.get("Descripcion", "").strip()

        # Validar campos obligatorios
        categoria_id = data.get("CategoriaId")
        unidad_id = data.get("UnidadMedidaId")
        marca_id = data.get("MarcaId")

        if not categoria_id or not unidad_id or not marca_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Categoría, Unidad de Medida y Marca son obligatorios",
                },
                status=400,
            )

        producto.categoria_id = categoria_id
        producto.unidad_medida_id = unidad_id
        producto.marca_id = marca_id

        producto.codigo_sku = data.get("CodigoSKU", "").strip()

        # Precio
        precio = data.get("precioVenta", "0").replace(",", ".")
        producto.precio_venta = float(precio)

        # Booleanos
        producto.vencimiento = str(data.get("Vencimiento")).lower() == "true"
        producto.is_active = str(data.get("IsActive")).lower() == "true"

        # Auditoría
        producto.f_modificacion = timezone.now()
        producto.u_modifico_id = request.user.id

        # =========================
        # IMAGEN (REEMPLAZO)
        # =========================
        file = request.FILES.get("Imagen")

        if file:
            import os
            import uuid

            # Eliminar imagen anterior si existe
            try:
                if producto.imagen_nombre:
                    ruta_anterior = os.path.join(
                        settings.MEDIA_ROOT, "productos", producto.imagen_nombre
                    )
                    if os.path.exists(ruta_anterior):
                        os.remove(ruta_anterior)
            except Exception as e:
                print("Error eliminando imagen anterior:", e)

            # Generar nombre: 5 caracteres + "_" + nombre original
            random_prefix = uuid.uuid4().hex[:5]
            unique_name = f"{random_prefix}_{file.name}"
            file.name = unique_name

            upload_path = os.path.join("productos", file.name)

            producto.imagen_nombre = file.name
            producto.imagen_url = f"/manager/media/{upload_path}"

            # Guardar archivo
            full_path = os.path.join(settings.MEDIA_ROOT, "productos")
            os.makedirs(full_path, exist_ok=True)

            with open(os.path.join(full_path, file.name), "wb+") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

        # =========================
        # GUARDAR
        # =========================
        producto.save()

        return JsonResponse(
            {"success": True, "message": "Producto actualizado correctamente"}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error interno: {str(e)}"}, status=500
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
        print(traceback.format_exc())
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
    print(compra_data)

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

    print(compra_data)

    return render(
        request,
        "bodega/confiinventario.html",
        {
            "compra_id": id,
            "compra": compra_data,
        },
    )


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
                Compras.objects.select_related("ubicacion").prefetch_related(
                    "compra_detalles"
                ),
                id=entrada_id,
            )

            ubicacion_destino = entrada.ubicacion
            detalles = entrada.compra_detalles.all()

            for p in productos:
                producto_id = p.get("ProductoId")
                cantidad = Decimal(str(p.get("Cantidad", 0)))
                fvencimiento = p.get("Fvencimiento")

                if cantidad <= 0:
                    continue

                detalle = detalles.filter(producto_id=producto_id).first()
                if not detalle:
                    continue

                autorizado_actual = HAutorizarCompra.objects.filter(
                    compra_id=entrada.id,
                    producto_id=producto_id,
                ).aggregate(total=Sum("cantidad_autorizada"))["total"] or Decimal("0")

                pendiente = detalle.cantidad - autorizado_actual

                if cantidad > pendiente:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": f"Excede cantidad pendiente producto {producto_id}",
                        },
                        status=400,
                    )

                HAutorizarCompra.objects.create(
                    compra_id=entrada.id,
                    producto_id=producto_id,
                    cantidad_comprada=detalle.cantidad,
                    cantidad_autorizada=cantidad,
                    fvencimiento=parse_datetime(fvencimiento) if fvencimiento else None,
                    u_creo_id=request.user.id,
                )

                Inventarios.objects.create(
                    producto_id=producto_id,
                    ubicacion=ubicacion_destino,
                    compra=entrada,
                    cantidad=cantidad,
                    fvencimiento=parse_datetime(fvencimiento) if fvencimiento else None,
                    u_creo_id=request.user.id,
                )

                MovimientoInventario.objects.create(
                    tipo_movimiento=TipoMovimientoInventario.ENTRADA_COMPRA,
                    producto_id=producto_id,
                    ubicacion_destino=ubicacion_destino,
                    cantidad=cantidad,
                    stock_anterior=0,
                    stock_resultante=cantidad,
                    compra_id=entrada.id,
                )

            autorizados = (
                HAutorizarCompra.objects.filter(compra_id=entrada.id)
                .values("producto_id")
                .annotate(total=Sum("cantidad_autorizada"))
            )

            map_aut = {a["producto_id"]: a["total"] for a in autorizados}

            completado = all(
                map_aut.get(d.producto_id, Decimal("0")) >= d.cantidad for d in detalles
            )

            entrada.estado = (
                EstadoCompra.COMPLETADO if completado else EstadoCompra.PENDIENTE
            )
            entrada.save()

        # =====================================================
        # TRASLADO
        # =====================================================
        elif tipo == "TRASLADO":
            entrada = get_object_or_404(
                Traslados.objects.select_related(
                    "ubicacion_origen", "ubicacion_destino"
                ),
                id=entrada_id,
            )

            origen = entrada.ubicacion_origen
            destino = entrada.ubicacion_destino

            detalles = DetalleTraslado.objects.filter(traslado_id=entrada.id)

            for p in productos:
                producto_id = p.get("ProductoId")
                cantidad = Decimal(str(p.get("Cantidad", 0)))
                fvencimiento = p.get("Fvencimiento")

                if cantidad <= 0:
                    continue

                detalle = detalles.filter(producto_id=producto_id).first()
                if not detalle:
                    continue

                # =====================================================
                # NO SUMA → SOLO REEMPLAZA
                # =====================================================
                detalle.cantidad_entregada = cantidad
                detalle.save(update_fields=["cantidad_entregada"])

                Inventarios.objects.create(
                    producto_id=producto_id,
                    ubicacion=destino,
                    cantidad=cantidad,
                    fvencimiento=parse_datetime(fvencimiento) if fvencimiento else None,
                    u_creo_id=request.user.id,
                )

                MovimientoInventario.objects.create(
                    tipo_movimiento=TipoMovimientoInventario.TRASLADO_ENTRADA,
                    producto_id=producto_id,
                    ubicacion_origen=origen,
                    ubicacion_destino=destino,
                    cantidad=cantidad,
                    stock_anterior=0,
                    stock_resultante=cantidad,
                    traslado_id=entrada.id,
                )

            entrada.autorizado_por = request.user
            entrada.fecha_autorizacion = timezone.now()

            # =====================================================
            # ESTADO SOLO SI ES IGUAL EXACTO
            # =====================================================
            detalles_refresh = DetalleTraslado.objects.filter(traslado_id=entrada.id)

            completado = all(
                d.cantidad_entregada == d.cantidad_solicitada for d in detalles_refresh
            )

            entrada.estado = Estados.COMPLETADO if completado else Estados.PENDIENTE

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

    productos_qs = Productos.objects.select_related(
        "unidad_medida", "marca", "categoria"
    )

    if search:
        productos_qs = productos_qs.filter(
            Q(nombre__icontains=search)
            | Q(codigo_sku__icontains=search)
            | Q(marca__nombre__icontains=search)
        )

    paginator = Paginator(productos_qs.order_by("nombre"), 12)

    page_obj = paginator.get_page(request.GET.get("page"))

    # =========================
    # DESCUENTOS AUTOMÁTICOS
    # =========================

    descuentos = Descuento.objects.filter(
        is_active=True,
        is_delete=False,
        es_cupon=False,
    ).prefetch_related("productos", "categorias")

    productos_list = []

    for p in page_obj:
        precio_original = Decimal(p.precio_venta)

        precio_final = precio_original

        descuento_producto = None

        descuento_categoria = None

        # =========================
        # BUSCAR DESCUENTOS
        # =========================

        for d in descuentos:
            if not d.vigente():
                continue

            # =========================
            # PRODUCTO
            # =========================

            if d.aplicar_productos:
                if d.productos.filter(id=p.id).exists():
                    descuento_producto = d

            # =========================
            # CATEGORIA
            # =========================

            if d.aplicar_categorias:
                if d.categorias.filter(id=p.categoria_id).exists():
                    descuento_categoria = d

        # =========================
        # CALCULAR DESCUENTO
        # =========================

        descuentos_aplicados = []

        # =========================
        # SI EXISTE PRODUCTO
        # =========================

        if descuento_producto:
            descuentos_aplicados.append(descuento_producto)

            # SI ES ACUMULABLE
            if descuento_producto.acumulable and descuento_categoria:
                descuentos_aplicados.append(descuento_categoria)

        # =========================
        # SI NO HAY PRODUCTO
        # =========================

        elif descuento_categoria:
            descuentos_aplicados.append(descuento_categoria)

        # =========================
        # APLICAR TODOS
        # =========================

        total_descuento = Decimal("0.00")

        nombres_descuentos = []

        for d in descuentos_aplicados:
            nombres_descuentos.append(d.nombre)

            # =========================
            # PORCENTAJE
            # =========================

            if d.es_porcentaje:
                descuento = (precio_original * Decimal(d.valor)) / Decimal(100)

            else:
                descuento = Decimal(d.valor)

            total_descuento += descuento

        precio_final = precio_original - total_descuento

        # evitar negativos
        if precio_final < 0:
            precio_final = Decimal("0.00")

        productos_list.append(
            {
                "id": p.id,
                "nombre": p.nombre,
                "unidadMedida": {
                    "abreviatura": getattr(p.unidad_medida, "abreviatura", "N/A")
                },
                "marcas": {"nombre": getattr(p.marca, "nombre", "N/A")},
                "codigoSKU": p.codigo_sku,
                # =========================
                # PRECIOS
                # =========================
                "precioVenta": float(precio_original),
                "precioFinal": float(precio_final),
                "tieneDescuento": len(descuentos_aplicados) > 0,
                "descuentos": [
                    {
                        "nombre": d.nombre,
                        "valor": float(d.valor),
                        "es_porcentaje": d.es_porcentaje,
                    }
                    for d in descuentos_aplicados
                ],
            }
        )

    ubicaciones = Ubicaciones.objects.filter(is_delete=False).order_by("nombre")

    context = {
        "productos": productos_list,
        "ubicaciones": ubicaciones,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "page_range": paginator.page_range,
        "search": search,
        "mostrar_buscador": True,
    }

    return render(request, "inventario/inventario.html", context,)


@login_required
@permission_required("manager.view_inventarios", raise_exception=True)
def get_inventario_producto(request, id):

    try:
        producto = get_object_or_404(
            Productos.objects.select_related("marca"),
            id=id,
            is_delete=False,
        )

        # ==========================================
        # STOCK FISICO AGRUPADO POR UBICACION
        # ==========================================
        inventarios = (
            Inventarios.objects.select_related("ubicacion")
            .filter(
                producto_id=id,
                is_delete=False,
                cantidad__gt=0,
            )
            .values("ubicacion__id", "ubicacion__nombre")
            .annotate(total_cantidad=Sum("cantidad"))
            .order_by("ubicacion__nombre")
        )

        inventario_list = []

        for inv in inventarios:
            ubicacion_id = inv["ubicacion__id"]
            stock_fisico = Decimal(str(inv["total_cantidad"] or 0))

            # ==========================================
            # STOCK RESERVADO EN TRASLADOS PENDIENTES
            # ==========================================
            reservado = DetalleTraslado.objects.filter(
                producto_id=id,
                traslado__ubicacion_origen_id=ubicacion_id,
                traslado__estado__in=["PENDIENTE", "EN_TRANSITO"],
                traslado__is_delete=False,
            ).aggregate(total=Sum("cantidad_solicitada"))["total"] or Decimal("0.00")

            stock_disponible = stock_fisico - Decimal(str(reservado))

            if stock_disponible < 0:
                stock_disponible = Decimal("0.00")

            inventario_list.append(
                {
                    "ubicacion": inv["ubicacion__nombre"],
                    "cantidad": float(stock_disponible),
                }
            )

        return JsonResponse(
            {
                "producto": {
                    "id": producto.id,
                    "nombre": producto.nombre,
                    "imagenUrl": (
                        producto.imagen_url
                        if producto.imagen_url
                        else "/static/img/noimage.png"
                    ),
                },
                "inventario": inventario_list,
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


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

    inventario = (
        Inventarios.objects.select_related("producto", "producto__unidad_medida")
        .filter(
            ubicacion_id=ubicacion_id,
            cantidad__gt=0,
        )
        .values(
            "producto_id",
            "producto__nombre",
            "producto__codigo_sku",
            "producto__imagen_url",
            "producto__unidad_medida__nombre",
        )
        .annotate(total_stock=Sum("cantidad"))
    )

    data = []

    for item in inventario:
        stock = float(item["total_stock"] or 0)

        if stock <= 0:
            continue

        data.append(
            {
                "producto_id": item["producto_id"],
                "nombre": item["producto__nombre"],
                "sku": item["producto__codigo_sku"],
                "imagen": item["producto__imagen_url"],
                "unidad": item["producto__unidad_medida__nombre"],
                "stock": stock,
            }
        )

    return JsonResponse(data, safe=False)


@login_required
@permission_required("manager.add_traslados", raise_exception=True)
@require_http_methods(["POST"])
def post_traslado(request):
    try:
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse(
                {"success": False, "message": "JSON inválido"}, status=400
            )

        origen_id = data.get("origenId")
        destino_id = data.get("destinoId")
        observaciones = data.get("observaciones", "").strip()
        detalles = data.get("detalles", [])

        if not origen_id or not destino_id:
            return JsonResponse(
                {"success": False, "message": "Debe seleccionar origen y destino"},
                status=400,
            )

        if origen_id == destino_id:
            return JsonResponse(
                {"success": False, "message": "Origen y destino no pueden ser iguales"},
                status=400,
            )

        if not detalles:
            return JsonResponse(
                {"success": False, "message": "Debe incluir al menos un producto"},
                status=400,
            )

        origen = Ubicaciones.objects.filter(id=origen_id, is_delete=False).first()
        destino = Ubicaciones.objects.filter(id=destino_id, is_delete=False).first()

        if not origen or not destino:
            return JsonResponse(
                {"success": False, "message": "Ubicaciones inválidas"},
                status=400,
            )

        with transaction.atomic():
            traslado = Traslados.objects.create(
                solicitado_por_id=request.user.id,
                ubicacion_origen=origen,
                ubicacion_destino=destino,
                observaciones=observaciones,
                estado=Estados.PENDIENTE,
                u_creo_id=request.user.id,
            )

            for item in detalles:
                producto_id = item.get("productoId")

                try:
                    cantidad_solicitada = Decimal(str(item.get("cantidad") or 0))
                except:
                    return JsonResponse(
                        {"success": False, "message": "Cantidad inválida"},
                        status=400,
                    )

                if cantidad_solicitada <= 0:
                    return JsonResponse(
                        {"success": False, "message": "Cantidad debe ser mayor a 0"},
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

                capas_origen = Inventarios.objects.filter(
                    producto_id=producto_id,
                    ubicacion_id=origen_id,
                    is_delete=False,
                    cantidad__gt=0,
                ).order_by("f_creacion")

                stock_total = sum([Decimal(str(x.cantidad)) for x in capas_origen])

                if stock_total < cantidad_solicitada:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": f"Stock insuficiente para {producto.nombre}. Disponible {stock_total}",
                        },
                        status=400,
                    )

                DetalleTraslado.objects.create(
                    traslado=traslado,
                    producto=producto,
                    cantidad_solicitada=cantidad_solicitada,
                    u_creo_id=request.user.id,
                )

                restante = cantidad_solicitada

                # ===============================
                # DESCONTAR SOLO ORIGEN FIFO
                # ===============================
                for capa in capas_origen:
                    if restante <= 0:
                        break

                    stock_capa = Decimal(str(capa.cantidad))
                    stock_anterior_origen = stock_capa

                    consumir = min(stock_capa, restante)

                    capa.cantidad -= consumir
                    capa.save()

                    MovimientoInventario.objects.create(
                        tipo_movimiento=TipoMovimientoInventario.TRASLADO_SALIDA,
                        producto=producto,
                        ubicacion_origen=origen,
                        ubicacion_destino=destino,
                        cantidad=consumir,
                        stock_anterior=stock_anterior_origen,
                        stock_resultante=capa.cantidad,
                        traslado=traslado,
                    )

                    restante -= consumir

        return JsonResponse(
            {
                "success": True,
                "message": "Traslado registrado correctamente y stock reservado",
                "trasladoId": traslado.id,
            }
        )

    except Exception as e:
        print(traceback.format_exc())
        return JsonResponse(
            {"success": False, "message": f"Error interno: {str(e)}"},
            status=500,
        )

#__________________________
## RUTA DE CAJA##
#_________________________
@login_required
def caja_view(request):    
    if not request.user.groups.filter(name="cajeros").exists():
        raise PermissionDenied("No tienes permiso")

    context = {
        "mostrar_buscador":False,
        "mostrar_codigo":True
    }

    return render(request,"caja/caja.html",context)

#Busqueda de Productos por codigo de barra en caja.

@login_required
def busqueda_codigo(request,codigo):

    if not request.user.groups.filter(name='cajeros').exists():
        return JsonResponse({
            "error":"Usuario no valido"
        },status=403)

    try:
        producto = Productos.objects.get(
            codigo_sku =codigo
        )

        data = {
            "id": producto.id,
            "codigo_sku":producto.codigo_sku,
            "nombre":producto.nombre,
            "precio_venta":producto.precio_venta
        }

        return JsonResponse(data)
    
    except Productos.DoesNotExist:
        return JsonResponse({
            "error":"Producto no encontrado"
        },status=404)

@login_required
def busqueda_nombre(request,producto):

    if not request.user.groups.filter(name='cajeros').exists():
        return JsonResponse({
            "error":"Usuario no valido"
        },status=403)    

    if not producto or len(producto)<2:
        return JsonResponse({},safe=False)

    items =(Productos.objects.filter(is_delete=False,is_active=True)
            .filter(Q(nombre__icontains=producto)).order_by("nombre")[:20]
            )

    data=[{"id":c.id,"codigo_sku":c.codigo_sku,"nombre":c.nombre,"precio_venta":c.precio_venta} for c in items]

    return JsonResponse(data,safe=False)



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

        valor = data.get("valor")

        # =========================
        # APLICACION
        # =========================

        aplicar_productos = data.get("aplicar_productos", False)

        aplicar_categorias = data.get("aplicar_categorias", False)

        productoid = data.get("productoid")

        categoriaid = data.get("categoriaid")

        # =========================
        # LIMITES
        # =========================

        limite_uso = data.get("limite_uso")

        # =========================
        # FECHAS
        # =========================

        fecha_inicio = data.get("fecha_inicio") or None

        fecha_fin = data.get("fecha_fin") or None

        # =========================
        # CONFIGURACIONES
        # =========================

        acumulable = data.get("acumulable", False)

        requiere_codigo = data.get("requiere_codigo", False)

        # =========================
        # VALIDACIONES
        # =========================

        if not nombre:
            return JsonResponse(
                {"success": False, "message": "El nombre es obligatorio"}, status=400
            )

        if valor in [None, ""]:
            return JsonResponse(
                {"success": False, "message": "El valor es obligatorio"}, status=400
            )

        if Descuento.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un descuento con ese nombre"},
                status=400,
            )

        # =========================
        # VALIDAR CODIGO CUPON
        # =========================

        if es_cupon:
            # Si escribió código manual
            if codigo:
                if Descuento.objects.filter(codigo=codigo, is_delete=False).exists():
                    return JsonResponse(
                        {"success": False, "message": "El código ya existe"}, status=400
                    )

            # Si no escribió código
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
            aplicar_productos=aplicar_productos,
            aplicar_categorias=aplicar_categorias,
            limite_uso=limite_uso if limite_uso else None,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            acumulable=acumulable,
            requiere_codigo=requiere_codigo,
            u_creo_id=request.user.id,
        )

        # =========================
        # MANY TO MANY
        # =========================

        if aplicar_productos and productoid:
            producto = Productos.objects.filter(id=productoid).first()

            if producto:
                descuento.productos.add(producto)

        if aplicar_categorias and categoriaid:
            categoria = Categorias.objects.filter(id=categoriaid).first()

            if categoria:
                descuento.categorias.add(categoria)

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

        producto = descuento.productos.first()

        categoria = descuento.categorias.first()

        return JsonResponse(
            {
                "success": True,
                "descuento": {
                    "id": descuento.id,
                    "nombre": descuento.nombre,
                    "descripcion": descuento.descripcion,
                    "es_cupon": descuento.es_cupon,
                    "codigo": descuento.codigo,
                    "es_porcentaje": descuento.es_porcentaje,
                    "valor": str(descuento.valor),
                    "aplicar_productos": descuento.aplicar_productos,
                    "aplicar_categorias": descuento.aplicar_categorias,
                    "productoid": producto.id if producto else None,
                    "productonombre": producto.nombre if producto else "",
                    "categoriaid": categoria.id if categoria else None,
                    "categorianombre": categoria.nombre if categoria else "",
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
                    "acumulable": descuento.acumulable,
                    "requiere_codigo": descuento.requiere_codigo,
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
                {
                    "success": False,
                    "message": "Descuento no encontrado",
                },
                status=404,
            )

        data = json.loads(request.body)

        # =========================
        # INFORMACION GENERAL
        # =========================

        nombre = (data.get("nombre") or "").strip()

        descripcion = (data.get("descripcion") or "").strip()

        # =========================
        # CUPON
        # =========================

        es_cupon = data.get("es_cupon", False)

        codigo = (data.get("codigo") or "").strip()

        # =========================
        # TIPO DESCUENTO
        # =========================

        es_porcentaje = data.get("es_porcentaje", True)

        valor = data.get("valor")

        # =========================
        # APLICACION
        # =========================

        aplicar_productos = data.get("aplicar_productos", False)

        aplicar_categorias = data.get("aplicar_categorias", False)

        productoid = data.get("productoid")

        categoriaid = data.get("categoriaid")

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

        requiere_codigo = data.get("requiere_codigo", False)

        is_active = data.get("is_active", True)

        # =========================
        # VALIDACIONES
        # =========================

        if not nombre:
            return JsonResponse(
                {
                    "success": False,
                    "message": "El nombre es obligatorio",
                },
                status=400,
            )

        existe = Descuento.objects.filter(
            nombre=nombre,
            is_delete=False,
        ).exclude(id=id)

        if existe.exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": "Ya existe un descuento con ese nombre",
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

        descuento.aplicar_productos = aplicar_productos

        descuento.aplicar_categorias = aplicar_categorias

        descuento.limite_uso = limite_uso

        descuento.fecha_inicio = fecha_inicio

        descuento.fecha_fin = fecha_fin

        descuento.acumulable = acumulable

        descuento.requiere_codigo = requiere_codigo

        descuento.is_active = is_active

        descuento.u_modifico_id = request.user.id

        descuento.save()

        # =========================
        # MANY TO MANY
        # =========================

        descuento.productos.clear()

        descuento.categorias.clear()

        if aplicar_productos and productoid:
            producto = Productos.objects.filter(id=productoid, is_delete=False).first()

            if producto:
                descuento.productos.add(producto)

        if aplicar_categorias and categoriaid:
            categoria = Categorias.objects.filter(
                id=categoriaid, is_delete=False
            ).first()

            if categoria:
                descuento.categorias.add(categoria)

        return JsonResponse(
            {
                "success": True,
                "message": "Descuento actualizado correctamente",
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
