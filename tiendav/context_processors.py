from django.core.cache import cache
from manager.models import Categorias


def categorias_navegacion(request):
    if not request.path_info.startswith("/tienda/"):
        return {"categorias_nav": Categorias.objects.none()}

    categorias = cache.get("tienda_categorias_nav")
    if categorias is None:
        categorias = list(
            Categorias.objects.filter(
                is_active=True,
                is_delete=False,
                categoria_productos__is_active=True,
                categoria_productos__is_delete=False,
            )
            .distinct()
            .order_by("nombre")
        )
        cache.set("tienda_categorias_nav", categorias, 300)

    return {"categorias_nav": categorias}
