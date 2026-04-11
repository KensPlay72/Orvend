from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import *
from django.core.files.storage import default_storage
from django.conf import settings
import os
import uuid


@login_required
def dashboard_view(request):
    return render(request, "dashboard.html")

#───────────────────────────────────────────────────────────────
# UNIDADES DE MEDIDA
#───────────────────────────────────────────────────────────────
@login_required
@permission_required('manager.view_umedidas', raise_exception=True)
def umedidas_view(request):

    search = request.GET.get("search", "").strip()

    query = UMedidas.objects.all()

    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    if search:
        query = query.filter(
            Q(nombre__icontains=search) |
            Q(abreviatura__icontains=search)
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
@permission_required('manager.add_umedidas', raise_exception=True)
@require_POST
def post_umedida(request):

    try:
        data = json.loads(request.body)

        nombre = (data.get("nombre") or "").strip()
        abreviatura = (data.get("abreviatura") or "").strip()

        if not nombre or not abreviatura:
            return JsonResponse({
                "success": False,
                "message": "Nombre y abreviatura son obligatorios"
            }, status=400)

        if UMedidas.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe una unidad de medida con ese nombre"
            }, status=400)

        UMedidas.objects.create(
            nombre=nombre,
            abreviatura=abreviatura,
            u_creo_id=request.user.id
        )

        return JsonResponse({
            "success": True,
            "message": "Creado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Error interno: " + str(e)
        }, status=500)
    

@login_required
@permission_required('manager.view_umedidas', raise_exception=True)
def get_umedida(request, id):

    try:
        medida = UMedidas.objects.filter(id=id).first()

        if not medida or medida.is_delete:
            return JsonResponse({
                "success": False,
                "message": "Unidad de medida no encontrada"
            }, status=404)

        return JsonResponse({
            "success": True,
            "presentacion": {
                "id": medida.id,
                "nombre": medida.nombre,
                "abreviatura": medida.abreviatura,
                "isActive": medida.is_active 
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Error interno: " + str(e)
        }, status=500)


@login_required
@permission_required('manager.change_umedidas', raise_exception=True)
@require_http_methods(["PUT"])
def put_umedida(request, id):

    try:
        data = json.loads(request.body)
        nombre = (data.get("Nombre") or "").strip()
        abreviatura = (data.get("Abreviatura") or "").strip()
        is_active = data.get("IsActive", True)

        if not nombre or not abreviatura:
            return JsonResponse({
                "success": False,
                "message": "Nombre y abreviatura son obligatorios"
            }, status=400)

        medida = UMedidas.objects.filter(id=id).first()

        if not medida or medida.is_delete:
            return JsonResponse({
                "success": False,
                "message": "Unidad de medida no encontrada"
            }, status=404)

        if UMedidas.objects.filter(nombre=nombre, is_delete=False).exclude(id=id).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe una unidad de medida con ese nombre"
            }, status=400)

        medida.nombre = nombre
        medida.abreviatura = abreviatura
        medida.is_active = is_active
        medida.u_modifico_id = request.user.id
        medida.f_modificacion = timezone.now()
        medida.save()

        return JsonResponse({
            "success": True,
            "message": "Actualizado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Error interno: " + str(e)
        }, status=500)
    
@login_required
@permission_required('manager.delete_umedidas', raise_exception=True)
@require_http_methods(["DELETE"])
def delete_umedida(request, id):

    try:
        medida = UMedidas.objects.filter(id=id).first()

        if not medida or medida.is_delete:
            return JsonResponse({
                "success": False,
                "message": "Unidad de medida no encontrada"
            }, status=404)

        medida.is_delete = True
        medida.u_modifico_id = request.user.id
        medida.f_modificacion = timezone.now()
        medida.save()

        return JsonResponse({
            "success": True,
            "message": "Unidad de medida eliminada correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Error interno: " + str(e)
        }, status=500)
    

@login_required
#@permission_required('manager.view_umedidas', raise_exception=True)
def search_umedidas(request):

    search = request.GET.get("search", "").strip()

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    items = UMedidas.objects.filter(
        is_delete=False,
        is_active=True
    ).filter(
        Q(nombre__icontains=search) |
        Q(abreviatura__icontains=search)
    ).order_by("nombre")[:20]

    data = [
        {
            "id": u.id,
            "nombre": u.nombre,
            "abreviatura": u.abreviatura
        }
        for u in items
    ]

    return JsonResponse(data, safe=False)

#───────────────────────────────────────────────────────────────
# MARCAS
#───────────────────────────────────────────────────────────────
@login_required
@permission_required('manager.view_marcas', raise_exception=True)
def marcas_view(request):

    search = request.GET.get("search", "").strip()

    query = Marcas.objects.all()

    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    if search:
        query = query.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
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
@permission_required('manager.add_marcas', raise_exception=True)
@require_POST
def post_marca(request):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        descripcion = (data.get("Descripcion") or "").strip()

        if not nombre:
            return JsonResponse({
                "success": False,
                "message": "El nombre es obligatorio"
            }, status=400)

        if Marcas.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe una marca con ese nombre"
            }, status=400)

        marca = Marcas.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            u_creo_id=request.user.id
        )

        return JsonResponse({
            "success": True,
            "message": "Marca registrada correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    

@login_required
@permission_required('manager.view_marcas', raise_exception=True)
def get_marca(request, id):

    marca = Marcas.objects.filter(id=id, is_delete=False).first()

    if not marca:
        return JsonResponse({
            "success": False,
            "message": "Marca no encontrada"
        }, status=404)

    return JsonResponse({
        "success": True,
        "marca": {
            "id": marca.id,
            "nombre": marca.nombre,
            "descripcion": marca.descripcion,
            "isActive": marca.is_active
        }
    })


@login_required
@permission_required('manager.change_marcas', raise_exception=True)
@require_http_methods(["PUT"])
def put_marca(request, id):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        descripcion = (data.get("Descripcion") or "").strip()
        is_active = data.get("IsActive", True)

        if not nombre:
            return JsonResponse({
                "success": False,
                "message": "El nombre es obligatorio"
            }, status=400)

        marca = Marcas.objects.filter(id=id).first()

        if not marca or marca.is_delete:
            return JsonResponse({
                "success": False,
                "message": "Marca no encontrada"
            }, status=404)

        if Marcas.objects.filter(nombre=nombre, is_delete=False).exclude(id=id).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe una marca con ese nombre"
            }, status=400)

        marca.nombre = nombre
        marca.descripcion = descripcion
        marca.is_active = is_active
        marca.u_modifico_id = request.user.id
        marca.f_modificacion = timezone.now()
        marca.save()

        return JsonResponse({
            "success": True,
            "message": "Marca actualizada correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    

@login_required
@permission_required('manager.delete_marcas', raise_exception=True)
@require_http_methods(["DELETE"])
def delete_marca(request, id):

    marca = Marcas.objects.filter(id=id).first()

    if not marca or marca.is_delete:
        return JsonResponse({
            "success": False,
            "message": "Marca no encontrada"
        }, status=404)

    marca.is_delete = True
    marca.u_modifico_id = request.user.id
    marca.f_modificacion = timezone.now()
    marca.save()

    return JsonResponse({
        "success": True,
        "message": "Marca eliminada correctamente"
    })


@login_required
#@permission_required('manager.view_marcas', raise_exception=True)
def search_marcas(request):

    search = request.GET.get("search", "").strip()

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    items = Marcas.objects.filter(
        is_delete=False,
        is_active=True
    ).filter(
        Q(nombre__icontains=search) |
        Q(descripcion__icontains=search)
    ).order_by("nombre")[:20]

    data = [
        {
            "id": m.id,
            "nombre": m.nombre,
            "descripcion": m.descripcion
        }
        for m in items
    ]

    return JsonResponse(data, safe=False)


#───────────────────────────────────────────────────────────────
# CATEGORIAS
#───────────────────────────────────────────────────────────────
@login_required
@permission_required('manager.view_categorias', raise_exception=True)
def categorias_view(request):

    search = request.GET.get("search", "").strip()

    query = Categorias.objects.all()

    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    if search:
        query = query.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
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
@permission_required('manager.add_categorias', raise_exception=True)
@require_POST
def post_categoria(request):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        descripcion = (data.get("Descripcion") or "").strip()

        if not nombre:
            return JsonResponse({
                "success": False,
                "message": "El nombre es obligatorio"
            }, status=400)

        if Categorias.objects.filter(nombre=nombre, is_delete=False).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe una categoría con ese nombre"
            }, status=400)

        Categorias.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            u_creo_id=request.user.id
        )

        return JsonResponse({
            "success": True,
            "message": "Categoría registrada correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    

@login_required
@permission_required('manager.view_categorias', raise_exception=True)
def get_categoria(request, id):

    categoria = Categorias.objects.filter(id=id, is_delete=False).first()

    if not categoria:
        return JsonResponse({
            "success": False,
            "message": "Categoría no encontrada"
        }, status=404)

    return JsonResponse({
        "success": True,
        "categoria": {
            "id": categoria.id,
            "nombre": categoria.nombre,
            "descripcion": categoria.descripcion,
            "isActive": categoria.is_active
        }
    })


@login_required
@permission_required('manager.change_categorias', raise_exception=True)
@require_http_methods(["PUT"])
def put_categoria(request, id):

    try:
        data = json.loads(request.body)

        nombre = (data.get("Nombre") or "").strip()
        descripcion = (data.get("Descripcion") or "").strip()
        is_active = data.get("IsActive", True)

        if not nombre:
            return JsonResponse({
                "success": False,
                "message": "El nombre es obligatorio"
            }, status=400)

        categoria = Categorias.objects.filter(id=id).first()

        if not categoria or categoria.is_delete:
            return JsonResponse({
                "success": False,
                "message": "Categoría no encontrada"
            }, status=404)

        if Categorias.objects.filter(nombre=nombre, is_delete=False).exclude(id=id).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe una categoría con ese nombre"
            }, status=400)

        categoria.nombre = nombre
        categoria.descripcion = descripcion
        categoria.is_active = is_active
        categoria.u_modifico_id = request.user.id
        categoria.f_creacion = timezone.now()
        categoria.save()

        return JsonResponse({
            "success": True,
            "message": "Categoría actualizada correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    
@login_required
@permission_required('manager.delete_categorias', raise_exception=True)
@require_http_methods(["DELETE"])
def delete_categoria(request, id):

    categoria = Categorias.objects.filter(id=id).first()

    if not categoria or categoria.is_delete:
        return JsonResponse({
            "success": False,
            "message": "Categoría no encontrada"
        }, status=404)

    categoria.is_delete = True
    categoria.u_modifico_id = request.user.id
    categoria.f_modificacion = timezone.now()
    categoria.save()

    return JsonResponse({
        "success": True,
        "message": "Categoría eliminada correctamente"
    })


@login_required
#@permission_required('manager.view_categorias', raise_exception=True)
def search_categorias(request):

    search = request.GET.get("search", "").strip()

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    items = Categorias.objects.filter(
        is_delete=False,
        is_active=True
    ).filter(
        Q(nombre__icontains=search) |
        Q(descripcion__icontains=search)
    ).order_by("nombre")[:20]

    data = [
        {
            "id": c.id,
            "nombre": c.nombre,
            "descripcion": c.descripcion
        }
        for c in items
    ]

    return JsonResponse(data, safe=False)


#───────────────────────────────────────────────────────────────
# PROVEEDORES
#───────────────────────────────────────────────────────────────
@login_required
@permission_required('manager.view_proveedores', raise_exception=True)
def proveedores_view(request):

    search = request.GET.get("search", "").strip()

    query = Proveedores.objects.all()

    if not request.user.is_superuser:
        query = query.filter(is_delete=False)

    if search:
        query = query.filter(
            Q(nombre_legal__icontains=search) |
            Q(nombre_comercial__icontains=search) |
            Q(rtn__icontains=search) |
            Q(telefono__icontains=search) |
            Q(email__icontains=search)
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
@permission_required('manager.add_proveedores', raise_exception=True)
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

        if not all([nombre_legal, nombre_comercial, rtn, dias_credito, telefono, email]):
            return JsonResponse({
                "success": False,
                "message": "Todos los campos son obligatorios"
            }, status=400)

        if Proveedores.objects.filter(rtn=rtn, is_delete=False).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe un proveedor con ese RTN"
            }, status=400)

        Proveedores.objects.create(
            nombre_legal=nombre_legal,
            nombre_comercial=nombre_comercial,
            rtn=rtn,
            dias_credito=dias_credito,
            telefono=telefono,
            email=email,
            u_creo_id=request.user.id
        )

        return JsonResponse({
            "success": True,
            "message": "Proveedor creado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    

@login_required
@permission_required('manager.view_proveedores', raise_exception=True)
def get_proveedor(request, id):
    try:
        proveedor = Proveedores.objects.filter(id=id).first()

        if not proveedor or proveedor.is_delete:
            return JsonResponse({
                "success": False,
                "message": "Proveedor no encontrado"
            }, status=404)

        return JsonResponse({
            "success": True,
            "proveedor": {
                "id": proveedor.id,
                "nombre_legal": proveedor.nombre_legal,
                "nombre_comercial": proveedor.nombre_comercial,
                "rtn": proveedor.rtn,
                "dias_credito": proveedor.dias_credito,
                "telefono": proveedor.telefono,
                "email": proveedor.email,
                "is_active": proveedor.is_active
            }
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)


@login_required
@permission_required('manager.change_proveedores', raise_exception=True)
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

        if not all([nombre_legal, nombre_comercial, rtn, dias_credito, telefono, email]):
            return JsonResponse({
                "success": False,
                "message": "Todos los campos son obligatorios"
            }, status=400)

        proveedor = Proveedores.objects.filter(id=id).first()

        if not proveedor or proveedor.is_delete:
            return JsonResponse({
                "success": False,
                "message": "Proveedor no encontrado"
            }, status=404)

        if Proveedores.objects.filter(rtn=rtn, is_delete=False).exclude(id=id).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe un proveedor con ese RTN"
            }, status=400)

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

        return JsonResponse({
            "success": True,
            "message": "Proveedor actualizado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    

@login_required
@permission_required('manager.delete_proveedores', raise_exception=True)
@require_http_methods(["DELETE"])
def delete_proveedor(request, id):

    try:
        proveedor = Proveedores.objects.filter(id=id).first()

        if not proveedor or proveedor.is_delete:
            return JsonResponse({
                "success": False,
                "message": "Proveedor no encontrado"
            }, status=404)

        proveedor.is_delete = True
        proveedor.u_modifico_id = request.user.id
        proveedor.f_modificacion = timezone.now()
        proveedor.save()

        return JsonResponse({
            "success": True,
            "message": "Proveedor eliminado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    

@login_required
@permission_required('manager.view_proveedores', raise_exception=True)
def search_proveedores(request):

    search = request.GET.get("search", "").strip()

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    proveedores = Proveedores.objects.filter(
        is_delete=False,
        is_active=True
    ).filter(
        Q(nombre_legal__icontains=search) |
        Q(nombre_comercial__icontains=search)
    ).order_by("nombre_comercial")[:20]

    results = [
        {
            "id": p.id,
            "nombreLegal": p.nombre_legal,
            "nombreComercial": p.nombre_comercial,
        }
        for p in proveedores
    ]

    return JsonResponse(results, safe=False)


#───────────────────────────────────────────────────────────────
# PROVEEDORES CONTACTOS
#───────────────────────────────────────────────────────────────
@login_required
@permission_required('manager.view_proveedorescontactos', raise_exception=True)
def proveedores_contactos_view(request):

    search = request.GET.get("search", "").strip()

    query = ProveedoresContactos.objects.select_related("proveedor").all()

    # soft delete
    query = query.filter(is_delete=False)

    # search
    if search:
        query = query.filter(
            Q(nombre__icontains=search) |
            Q(puesto__icontains=search) |
            Q(email__icontains=search) |
            Q(telefono__icontains=search) |
            Q(proveedor__nombre_legal__icontains=search) |
            Q(proveedor__nombre_comercial__icontains=search)
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
@permission_required('manager.add_proveedorescontactos', raise_exception=True)
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
            return JsonResponse({
                "success": False,
                "message": "Campos obligatorios incompletos"
            }, status=400)

        proveedor = Proveedores.objects.filter(id=proveedor_id, is_delete=False).first()
        if not proveedor:
            return JsonResponse({
                "success": False,
                "message": "Proveedor no encontrado"
            }, status=404)

        contacto = ProveedoresContactos.objects.create(
            proveedor=proveedor,
            nombre=nombre,
            puesto=puesto,
            telefono=telefono,
            email=email,
            observaciones=observaciones,
            u_creo_id=request.user.id
        )

        return JsonResponse({
            "success": True,
            "message": "Contacto creado correctamente",
            "id": contacto.id
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)


@login_required
@permission_required('manager.view_proveedorescontactos', raise_exception=True)
def get_proveedor_contacto(request, id):

    contacto = ProveedoresContactos.objects.select_related("proveedor").filter(
        id=id,
        is_delete=False
    ).first()

    if not contacto:
        return JsonResponse({
            "success": False,
            "message": "Contacto no encontrado"
        }, status=404)

    return JsonResponse({
        "success": True,
        "proveedorcont": {
            "id": contacto.id,
            "proveedores": {
                "id": contacto.proveedor.id if contacto.proveedor else None,
                "nombre_comercial": contacto.proveedor.nombre_comercial if contacto.proveedor else "",
                "nombre_legal": contacto.proveedor.nombre_legal if contacto.proveedor else "",
            },
            "nombre": contacto.nombre,
            "puesto": contacto.puesto,
            "telefono": contacto.telefono,
            "email": contacto.email,
            "observaciones": contacto.observaciones,
            "is_active": contacto.is_active
        }
    })


@login_required
@permission_required('manager.change_proveedorescontactos', raise_exception=True)
@require_http_methods(["PUT"])
def put_proveedor_contacto(request, id):

    try:
        data = json.loads(request.body)

        contacto = ProveedoresContactos.objects.filter(
            id=id,
            is_delete=False
        ).first()

        if not contacto:
            return JsonResponse({
                "success": False,
                "message": "Contacto no encontrado"
            }, status=404)

        proveedor_id = data.get("proveedor")

        if proveedor_id:
            proveedor = Proveedores.objects.filter(id=proveedor_id, is_delete=False).first()
            if not proveedor:
                return JsonResponse({
                    "success": False,
                    "message": "Proveedor no válido"
                }, status=400)
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

        return JsonResponse({
            "success": True,
            "message": "Contacto actualizado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    

@login_required
@permission_required('manager.delete_proveedorescontactos', raise_exception=True)
@require_http_methods(["DELETE"])
def delete_proveedor_contacto(request, id):

    contacto = ProveedoresContactos.objects.filter(
        id=id,
        is_delete=False
    ).first()

    if not contacto:
        return JsonResponse({
            "success": False,
            "message": "Contacto no encontrado"
        }, status=404)

    contacto.is_delete = True
    contacto.u_modifico_id = request.user.id
    contacto.f_modificacion = timezone.now()
    contacto.save()

    return JsonResponse({
        "success": True,
        "message": "Contacto eliminado correctamente"
    })   

@login_required
@permission_required('manager.view_productos', raise_exception=True)
def productos_view(request):

    search = request.GET.get("search", "").strip()

    query = Productos.objects.select_related(
        "categoria",
        "unidad_medida",
        "marca"
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
            Q(nombre__icontains=search) |
            Q(codigo_sku__icontains=search)
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
@permission_required('manager.add_productos', raise_exception=True)
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
        vencimiento = request.POST.get("Vencimiento") == "true"

        imagen = request.FILES.get("Imagen")

        if not nombre or not categoria_id or not unidad_medida_id or not marca_id or not codigo_sku or not precio_venta:
            return JsonResponse({
                "success": False,
                "message": "Campos obligatorios faltantes"
            }, status=400)

        if Productos.objects.filter(codigo_sku=codigo_sku).exists():
            return JsonResponse({
                "success": False,
                "message": "Ya existe un producto con ese código SKU"
            }, status=400)

        categoria = Categorias.objects.filter(id=categoria_id).first()
        unidad = UMedidas.objects.filter(id=unidad_medida_id).first()
        marca = Marcas.objects.filter(id=marca_id).first()

        if not categoria or not unidad or not marca:
            return JsonResponse({
                "success": False,
                "message": "Categoría, unidad o marca inválida"
            }, status=400)

        producto = Productos(
            nombre=nombre,
            descripcion=descripcion,
            categoria=categoria,
            unidad_medida=unidad,
            marca=marca,
            codigo_sku=codigo_sku,
            precio_venta=precio_venta,
            vencimiento=vencimiento,
            u_creo_id=request.user.id
        )

        if imagen:
            unique_id = uuid.uuid4().hex[:8]
            nombre_original = imagen.name.replace(" ", "_")
            nuevo_nombre = f"{unique_id}_{nombre_original}"

            # ruta física dentro de la app manager
            base_dir = os.path.join(settings.BASE_DIR, "manager", "media", "productos")

            # crear carpeta si no existe
            os.makedirs(base_dir, exist_ok=True)

            # ruta completa del archivo
            file_path = os.path.join(base_dir, nuevo_nombre)

            # guardar archivo manualmente
            with open(file_path, "wb+") as destination:
                for chunk in imagen.chunks():
                    destination.write(chunk)

            # guardar en BD
            producto.imagen_nombre = nuevo_nombre
            producto.imagen_url = f"/manager/media/productos/{nuevo_nombre}"

        producto.save()

        return JsonResponse({
            "success": True,
            "message": "Producto registrado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": "Error interno: " + str(e)
        }, status=500)


@login_required
@permission_required('manager.view_productos', raise_exception=True)
def get_producto(request, id):

    producto = Productos.objects.select_related(
        "categoria",
        "unidad_medida",
        "marca"
    ).filter(
        id=id,
        is_delete=False
    ).first()

    if not producto:
        return JsonResponse({
            "success": False,
            "message": "Producto no encontrado"
        }, status=404)

    return JsonResponse({
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
            "categoria": {
                "nombre": producto.categoria.nombre
            } if producto.categoria else None,

            "unidadMedidaId": producto.unidad_medida.id if producto.unidad_medida else None,
            "unidadMedida": {
                "nombre": producto.unidad_medida.nombre,
                "abreviatura": producto.unidad_medida.abreviatura
            } if producto.unidad_medida else None,

            "marcasId": producto.marca.id if producto.marca else None,
            "marcas": {
                "nombre": producto.marca.nombre
            } if producto.marca else None,
        }
    })


@login_required
@permission_required('manager.change_productos', raise_exception=True)
@require_http_methods(["PUT"])
def put_producto(request, id):

    try:
        producto = Productos.objects.filter(id=id, is_delete=False).first()

        if not producto:
            return JsonResponse({
                "success": False,
                "message": "Producto no encontrado"
            }, status=404)

        data = request.POST

        producto.nombre = data.get("Nombre", "").strip()
        producto.descripcion = data.get("Descripcion", "").strip()

        producto.categoria_id = data.get("CategoriaId")
        producto.unidad_medida_id = data.get("UnidadMedidaId")
        producto.marca_id = data.get("MarcaId")

        producto.codigo_sku = data.get("CodigoSKU", "").strip()

        precio = data.get("precioVenta", "0").replace(",", ".")
        producto.precio_venta = float(precio)

        producto.vencimiento = data.get("Vencimiento") == "true" or data.get("Vencimiento") == True

        producto.is_active = data.get("IsActive") == "true" or data.get("IsActive") == True

        producto.f_modificacion = timezone.now()
        producto.u_modifico_id = request.user.id

        # =========================
        # IMAGEN (si viene nueva)
        # =========================
        file = request.FILES.get("Imagen")

        if file:
            import os
            import uuid

            # nombre único
            unique_name = f"{uuid.uuid4().hex}_{file.name}"
            file.name = unique_name

            upload_path = os.path.join("productos", file.name)

            producto.imagen_nombre = file.name
            producto.imagen_url = f"/manager/media/{upload_path}"

            # guardar archivo manual (si no usas ImageField)
            full_path = os.path.join(settings.MEDIA_ROOT, "productos")
            os.makedirs(full_path, exist_ok=True)

            with open(os.path.join(full_path, file.name), "wb+") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

        producto.save()

        return JsonResponse({
            "success": True,
            "message": "Producto actualizado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error interno: {str(e)}"
        }, status=500)


@login_required
@permission_required('manager.delete_productos', raise_exception=True)
@require_http_methods(["DELETE"])
def delete_producto(request, id):

    try:
        producto = Productos.objects.filter(id=id, is_delete=False).first()

        if not producto:
            return JsonResponse({
                "success": False,
                "message": "Producto no encontrado"
            }, status=404)

        producto.is_delete = True
        producto.is_active = False
        producto.f_modificacion = timezone.now()
        producto.u_modifico_id = request.user.id
        producto.save()

        return JsonResponse({
            "success": True,
            "message": "Producto eliminado correctamente"
        })

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)
    


@login_required
@permission_required('manager.view_productos', raise_exception=True)
def search_productos(request):

    search = request.GET.get("search", "").strip()

    if not search or len(search) < 2:
        return JsonResponse([], safe=False)

    items = Productos.objects.filter(
        is_delete=False,
        is_active=True
    ).filter(
        Q(nombre__icontains=search) |
        Q(codigo_sku__icontains=search)
    ).select_related("marca", "categoria")[:20]

    data = [
        {
            "id": p.id,
            "nombre": p.nombre,
            "codigo": p.codigo_sku,
            "marca": p.marca.nombre if p.marca else "",
            "categoria": p.categoria.nombre if p.categoria else ""
        }
        for p in items
    ]

    return JsonResponse(data, safe=False)





