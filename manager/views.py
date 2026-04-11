from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST

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
    print(page_obj.object_list.count())
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