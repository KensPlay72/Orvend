import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from manager.models import CajaAC, SuscripcionSistema
@csrf_exempt
def login_view(request):
    if request.method == "POST":

        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({"message": "JSON inválido"}, status=400)

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JsonResponse({"message": "Campos requeridos"}, status=400)

        user = authenticate(request, username=username, password=password)

        if user is None:
            return JsonResponse({"message": "Credenciales incorrectas"}, status=401)

        if not user.is_active:
            return JsonResponse({"message": "Usuario inactivo"}, status=403)

        # El superusuario necesita conservar acceso para actualizar el período
        # desde el admin. Los demás usuarios no inician sesión sin vigencia.
        suscripcion_vigente = SuscripcionSistema.esta_vigente()
        if not user.is_superuser and not suscripcion_vigente:
            return JsonResponse(
                {
                    "message": "La suscripción de este sistema no está vigente.",
                    "redirect_url": reverse("suscripcion_vencida"),
                    "acceso_bloqueado": True,
                },
            )

        login(request, user)

        caja_pendiente_anterior = CajaAC.objects.filter(
            usuario_id=user.id,
            estado__in=["abierta", "cuadre"],
            fecha_apertura__date__lt=timezone.localdate(),
            is_active=True,
            is_delete=False,
        ).exists()

        if user.is_superuser and not suscripcion_vigente:
            redirect_url = reverse("admin:index")
        elif caja_pendiente_anterior and (
            user.is_superuser or user.has_perm("manager.operar_caja")
        ):
            redirect_url = "/manager/caja/cuadre/"
        elif user.is_superuser:
            redirect_url = "/manager/dashboard/"
        elif user.has_perm("manager.operar_caja") or user.has_perm("manager.generar_cotizaciones"):
            redirect_url = "/manager/caja/"
        elif user.has_perm("manager.view_cotizacion"):
            redirect_url = "/manager/cotizaciones/"
        elif user.has_perm("manager.gestionar_retiros_caja"):
            redirect_url = "/manager/caja/retiros/"
        elif user.has_perm("manager.gestionar_recepcion_inventario"):
            redirect_url = "/manager/bodega/recepcion_inventario/"
        elif user.has_perm("manager.gestionar_configuracion"):
            redirect_url = "/manager/configuracion/"
        elif user.has_perm("manager.view_productos"):
            redirect_url = "/manager/productos/"
        elif user.has_perm("manager.view_inventarios"):
            redirect_url = "/manager/inventario/"
        elif user.has_perm("manager.view_compras"):
            redirect_url = "/manager/compras/"
        elif user.has_perm("manager.view_ventas"):
            redirect_url = "/manager/ventas/"
        elif user.has_perm("manager.view_clientes"):
            redirect_url = "/manager/clientes/"
        elif user.has_perm("manager.view_proveedores"):
            redirect_url = "/manager/proveedores/"
        elif user.has_perm("manager.ver_dashboard"):
            redirect_url = "/manager/dashboard/"
        else:
            redirect_url = "/"

        return JsonResponse({
            "message": "Login exitoso",
            "username": user.username,
            "redirect_url": redirect_url,
        })

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")
