from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import UMedidas


@login_required
def dashboard_view(request):
    return render(request, "dashboard.html")

#───────────────────────────────────────────────────────────────
# REGISTRO DE UNIDADES DE MEDIDA
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

    return render(request, "presentaciones.html", context)



@login_required
@permission_required('manager.add_umedidas', raise_exception=True)
@require_POST
def post_umedida(request):

    try:
        data = json.loads(request.body)

        nombre = (data.get("nombre") or "").strip()
        abreviatura = (data.get("abreviatura") or "").strip()
        is_active = data.get("is_active", True)

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
            is_active=is_active,
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
                "isActive": medida.is_active   # 👈 importante para tu JS
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

        # si no viene IsActive, asumimos True
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