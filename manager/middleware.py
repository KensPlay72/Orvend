from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .models import CajaAC, SuscripcionSistema


class SecurityHeadersMiddleware:
    """Añade defensas del navegador a documentos HTML del sistema."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if not content_type.startswith("text/html"):
            return response

        response.setdefault(
            "Content-Security-Policy", settings.CONTENT_SECURITY_POLICY
        )
        response.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)
        response.setdefault("Referrer-Policy", settings.SECURE_REFERRER_POLICY)
        # Es un mecanismo heredado, pero satisface navegadores y auditorías que
        # todavía lo consultan. CSP es la protección principal contra XSS.
        response.setdefault("X-XSS-Protection", "1; mode=block")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response


class SuscripcionActivaMiddleware:
    """Restringe las operaciones cuando la suscripción de la instalación venció.

    La fecha se evalúa en el servidor mediante ``timezone.localdate()``. Por
    tanto, modificar la fecha u hora del navegador no puede extender el acceso.
    El servidor de producción debe mantenerse sincronizado por NTP.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ruta = request.path
        usuario = getattr(request, "user", None)

        rutas_publicas = {
            reverse("home"),
            reverse("login"),
            reverse("logout"),
            reverse("politica_privacidad"),
            reverse("politica_cookies"),
            reverse("terminos_condiciones"),
            reverse("politica_reembolsos"),
            reverse("suscripcion_vencida"),
        }
        prefijos_publicos = ("/static/", "/public/", "/manager/media/")
        panel_admin = reverse("admin:index")

        if ruta in rutas_publicas or ruta.startswith(prefijos_publicos):
            return self.get_response(request)

        # El superusuario conserva acceso al admin para renovar el período.
        if (
            usuario
            and usuario.is_authenticated
            and usuario.is_superuser
            and ruta.startswith(panel_admin)
        ):
            return self.get_response(request)

        if not SuscripcionSistema.esta_vigente():
            return redirect("suscripcion_vencida")

        return self.get_response(request)


class CierreCajaPendienteMiddleware:
    """Impide continuar cuando el cajero dejó una caja abierta otro día."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if not usuario or not usuario.is_authenticated:
            return self.get_response(request)

        rutas_permitidas = {
            reverse("cuadre_caja"),
            reverse("cerrar_cuadre_caja"),
            reverse("logout"),
        }
        ruta = request.path
        if (
            ruta not in rutas_permitidas
            and not ruta.startswith("/accounts/")
            and not ruta.startswith("/static/")
            and not ruta.startswith("/public/")
            and not ruta.startswith("/manager/media/")
            and (usuario.is_superuser or usuario.has_perm("manager.operar_caja"))
        ):
            tiene_caja_anterior = CajaAC.objects.filter(
                usuario_id=usuario.id,
                estado__in=["abierta", "cuadre"],
                fecha_apertura__date__lt=timezone.localdate(),
                is_active=True,
                is_delete=False,
            ).exists()
            if tiene_caja_anterior:
                return redirect("cuadre_caja")

        return self.get_response(request)
