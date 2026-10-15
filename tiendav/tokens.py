from django.core import signing


CATEGORIA_SALT = "tiendav.categoria"


def token_categoria(categoria_id):
    return signing.dumps(categoria_id, salt=CATEGORIA_SALT, compress=True)


def id_desde_token_categoria(valor):
    if valor.isdigit():
        return int(valor)
    try:
        categoria_id = signing.loads(valor, salt=CATEGORIA_SALT)
    except (signing.BadSignature, TypeError, ValueError):
        return None
    return categoria_id if isinstance(categoria_id, int) and categoria_id > 0 else None
