from django.core.cache import cache

from .models import ConfiguracionEmpresa


CLAVE_TEMA_EMPRESA = "manager:tema_empresa:v1"


def invalidar_tema_empresa_cache():
    """Se invoca al guardar la configuración; evita una consulta por vista."""
    cache.delete(CLAVE_TEMA_EMPRESA)


def _tema_empresa_cacheado():
    tema = cache.get(CLAVE_TEMA_EMPRESA)
    if tema is not None:
        return tema

    configuracion = ConfiguracionEmpresa.objects.filter(
        is_active=True, is_delete=False
    ).only(
        "tienda_color_primario",
        "tienda_color_secundario",
        "tienda_color_acento",
        "moneda",
    ).first()
    tema = {
        "tema_principal": (
            configuracion.tienda_color_primario if configuracion else "#32877F"
        ),
        "tema_secundario": (
            configuracion.tienda_color_secundario if configuracion else "#10463E"
        ),
        "tema_botones": (
            configuracion.tienda_color_acento if configuracion else "#3F8886"
        ),
        "moneda_sistema": (
            configuracion.moneda if configuracion else ConfiguracionEmpresa.MONEDA_LEMPIRA
        ),
        "moneda_simbolo": (
            configuracion.simbolo_moneda if configuracion else "L."
        ),
    }
    # El guardado de ConfiguraciónEmpresa invalida esta entrada. El TTL corto
    # mantiene coherencia incluso si la instalación usa varios procesos locales.
    cache.set(CLAVE_TEMA_EMPRESA, tema, timeout=60)
    return tema


def tema_empresa(request):
    """Expone tema cacheado; las notificaciones llegan por WebSocket."""
    try:
        return _tema_empresa_cacheado()
    except Exception:
        # Una página de error debe seguir renderizando sin depender de cache/BD.
        return {
            "tema_principal": "#32877F",
            "tema_secundario": "#10463E",
            "tema_botones": "#3F8886",
            "moneda_sistema": ConfiguracionEmpresa.MONEDA_LEMPIRA,
            "moneda_simbolo": "L.",
        }
