from decimal import Decimal, InvalidOperation, ROUND_DOWN

from django import template

from tiendav.tokens import token_categoria


register = template.Library()


@register.filter
def unidades_cliente(valor):
    """Muestra unidades completas sin redondear hacia arriba."""
    try:
        return int(Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_DOWN))
    except (InvalidOperation, TypeError, ValueError):
        return 0


@register.filter
def tiene_stock_entero(valor):
    """Verifica si la existencia cuenta con al menos 1 unidad entera para la venta."""
    try:
        if valor is None:
            return False
        return Decimal(str(valor)) >= Decimal("1")
    except (InvalidOperation, TypeError, ValueError):
        return False


@register.filter
def categoria_token(categoria):
    """Genera un token firmado para los enlaces públicos de categorías."""
    if not categoria:
        return ""
    return token_categoria(categoria.pk)


@register.filter
def limpiar_telefono_wa(valor):
    """Extrae únicamente dígitos numéricos para generar el enlace hacia wa.me."""
    if not valor:
        return ""
    import re
    return re.sub(r"\D", "", str(valor))

