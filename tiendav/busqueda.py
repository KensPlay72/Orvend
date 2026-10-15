import re
import unicodedata
from django.db.models import Q


def normalizar_texto_simple(texto):
    """Convierte a minúsculas y remueve tildes y diacríticos excepto la ñ si es posible."""
    if not texto:
        return ""
    texto = texto.strip().lower()
    nfd = unicodedata.normalize("NFD", texto)
    sin_diacriticos = "".join(
        c for c in nfd if unicodedata.category(c) != "Mn"
    )
    return unicodedata.normalize("NFC", sin_diacriticos)


def quitar_tildes(texto):
    """Devuelve el texto en minúsculas sin acentos ortográficos."""
    return normalizar_texto_simple(texto)


def variantes_ortograficas(palabra):
    """
    Genera versiones con y sin tildes para compensar diferencias entre
    lo digitado por el usuario y lo registrado en la base de datos.
    """
    res = {palabra.lower()}
    sin_acento = quitar_tildes(palabra)
    res.add(sin_acento)
    # Reemplazo de ñ por n y viceversa por si hay teclados sin ñ
    if "ñ" in sin_acento:
        res.add(sin_acento.replace("ñ", "n"))

    # Intentos de acentuación común en español
    tildes = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}
    for v, vt in tildes.items():
        if v in sin_acento:
            res.add(sin_acento.replace(v, vt, 1))

    return res


def generar_variantes_termino(termino):
    """
    Expande un término de búsqueda generando sus formas canónicas, singulares,
    raíces y variantes ortográficas.

    Ejemplos:
    - 'archivos'   -> ['archivos', 'archivo', 'archiv', 'archi']
    - 'archivador' -> ['archivador', 'archivadora', 'archiv', 'archivo']
    - 'lapices'    -> ['lapices', 'lápices', 'lapiz', 'lápiz', 'lapic']
    - 'carpetas'   -> ['carpetas', 'carpeta', 'carpet']
    - 'papeles'    -> ['papeles', 'papel']
    """
    if not termino:
        return []

    limpio = termino.strip().lower()
    # Eliminar puntuación exterior
    limpio = re.sub(r"^[^\wáéíóúüñÁÉÍÓÚÜÑ]+|[^\wáéíóúüñÁÉÍÓÚÜÑ]+$", "", limpio)
    if not limpio:
        return []

    candidatos = set()
    candidatos.add(limpio)
    candidatos.update(variantes_ortograficas(limpio))

    # --- 1. Despluralización ---
    despluralizados = set()
    for w in list(candidatos):
        w_len = len(w)
        # Regla: -ces -> -z (lapices -> lapiz, luces -> luz, peces -> pez)
        if w.endswith("ces") and w_len >= 4:
            despluralizados.add(w[:-3] + "z")
            despluralizados.add(w[:-3] + "c")
            despluralizados.add(w[:-2])
        # Regla: terminaciones en -es (papeles -> papel, colores -> color, relojes -> reloj)
        elif w.endswith("es") and w_len >= 4:
            despluralizados.add(w[:-2])  # papel, color
            despluralizados.add(w[:-1])  # por si era terminación en -e (chocolates -> chocolate)
        # Regla: terminaciones en -s (archivos -> archivo, cajas -> caja, grapas -> grapa)
        elif w.endswith("s") and w_len >= 3 and not w.endswith("ss"):
            despluralizados.add(w[:-1])

    candidatos.update(despluralizados)

    # --- 2. Flexión de género para adjetivos/sustantivos comunes ---
    genero = set()
    for w in list(candidatos):
        if len(w) >= 4:
            if w.endswith("o"):
                genero.add(w[:-1] + "a")
            elif w.endswith("a"):
                genero.add(w[:-1] + "o")
    candidatos.update(genero)

    # --- 3. Raíces / Stemming para coincidencia parcial de palabras ---
    raices = set()
    sufijos_derivativos = (
        "dora", "dores", "doras", "dor",
        "era", "eros", "eras", "ero",
        "ita", "itos", "itas", "ito",
        "ada", "ados", "adas", "ado",
        "iva", "ivos", "ivas", "ivo",
        "cion", "ciones", "ción", "ciones",
    )
    for w in list(candidatos):
        w_len = len(w)
        if w_len >= 5:
            for suf in sufijos_derivativos:
                if w.endswith(suf) and len(w) - len(suf) >= 3:
                    raiz = w[: -len(suf)]
                    raices.add(raiz)
                    # Si termina en consonante, probar con terminación en vocal común
                    raices.add(raiz + "o")
                    raices.add(raiz + "a")

            # Raíces directas por longitud (para 'archivos' -> 'archivo' -> 'archiv')
            if w_len >= 5:
                raices.add(w[:-1])
            if w_len >= 6:
                raices.add(w[:-2])

    candidatos.update(raices)

    # Asegurar que todas las formas generadas tengan su versión con y sin tildes
    todas_variantes = set()
    for c in candidatos:
        todas_variantes.add(c)
        todas_variantes.add(quitar_tildes(c))

    # Filtrar por longitud mínima razonable
    min_len = 2 if len(limpio) <= 3 else 3
    resultado = [v for v in todas_variantes if len(v) >= min_len and v.strip()]

    # Ordenar: primero coincidencias exactas, luego por longitud descendente
    resultado.sort(key=lambda x: (x == limpio, quitar_tildes(x) == quitar_tildes(limpio), len(x)), reverse=True)
    return resultado


def construir_filtro_busqueda(cadena_busqueda, campos, modo="and"):
    """
    Construye un objeto Q de Django que realiza una búsqueda inteligente
    en los campos especificados, tokenizando por palabras y expandiendo
    cada palabra con singulares, raíces y variantes ortográficas.

    :param cadena_busqueda: String ingresado por el usuario.
    :param campos: Lista de nombres de campos en los modelos a consultar.
    :param modo: 'and' (todas las palabras deben coincidir) o 'or' (al menos una).
    """
    if not cadena_busqueda or not cadena_busqueda.strip():
        return Q()

    tokens = [t.strip() for t in re.split(r"[\s,;+\-_/]+", cadena_busqueda) if t.strip()]
    if not tokens:
        return Q()

    filtro_combinado = Q() if modo == "and" else Q()
    primera_iteracion = True

    for token in tokens:
        variantes = generar_variantes_termino(token)
        if not variantes:
            variantes = [token.lower(), quitar_tildes(token)]

        q_token = Q()
        for var in variantes:
            for campo in campos:
                q_token |= Q(**{f"{campo}__icontains": var})

        if modo == "and":
            if primera_iteracion:
                filtro_combinado = q_token
                primera_iteracion = False
            else:
                filtro_combinado &= q_token
        else:
            filtro_combinado |= q_token

    return filtro_combinado
