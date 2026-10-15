from django.urls import resolve
from pages.views import error_404
from .models import permision


class EcommerceActivoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            match = request.resolver_match or resolve(request.path_info)
        except Exception:
            match = None

        if match and (match.app_name == "tiendav" or match.namespace == "tiendav"):
            if not permision.ecommerce_activo():
                return error_404(request)

        return self.get_response(request)
