"""Etiquetas reutilizables para paginadores de Orvend."""

from django import template


register = template.Library()


@register.simple_tag
def paginas_cercanas(pagina_actual, total_paginas, radio=2):
    """Devuelve la ventana de páginas alrededor de la página actual."""
    try:
        pagina_actual = int(pagina_actual)
        total_paginas = int(total_paginas)
        radio = int(radio)
    except (TypeError, ValueError):
        return ()

    if total_paginas < 1:
        return ()

    inicio = max(1, pagina_actual - radio)
    fin = min(total_paginas, pagina_actual + radio)
    return range(inicio, fin + 1)
