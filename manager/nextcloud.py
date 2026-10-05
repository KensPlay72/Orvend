import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings
from urllib.parse import quote

_TIEMPO_ESPERA_ARCHIVO = (3.05, 12)


def _carpeta_nextcloud(carpeta=None):
    """Obtiene la carpeta remota evitando mezclar archivos por módulo."""
    carpeta = carpeta or settings.NEXTCLOUD_FOLDER_PRODUCTOS
    if not carpeta:
        raise ValueError("La carpeta de Nextcloud no está configurada")
    return carpeta


def url_archivo(nombre_archivo, carpeta=None):
    """Construye la URL WebDAV únicamente con la configuración actual."""
    if not nombre_archivo:
        raise ValueError("El nombre remoto del archivo es obligatorio")

    return (
        f"{settings.NEXTCLOUD_URL.rstrip('/')}"
        f"/remote.php/dav/files/{quote(settings.NEXTCLOUD_USER, safe='')}"
        f"/{quote(_carpeta_nextcloud(carpeta), safe='/')}"
        f"/{quote(str(nombre_archivo), safe='')}"
    )


def subir_archivo(archivo, nombre_archivo, carpeta=None):

    url = url_archivo(nombre_archivo, carpeta)

    response = requests.put(
        url,
        data=archivo,
        auth=HTTPBasicAuth(
            settings.NEXTCLOUD_USER,
            settings.NEXTCLOUD_PASSWORD,
        ),
    )

    if response.status_code not in (201, 204):
        raise Exception(
            f"Error subiendo archivo a Nextcloud: "
            f"{response.status_code} - {response.text}"
        )

    return url


def obtener_archivo(nombre_archivo, carpeta=None):

    response = requests.get(
        url_archivo(nombre_archivo, carpeta),
        auth=HTTPBasicAuth(
            settings.NEXTCLOUD_USER,
            settings.NEXTCLOUD_PASSWORD,
        ),
        timeout=_TIEMPO_ESPERA_ARCHIVO,
    )

    if response.status_code != 200:
        raise Exception(
            f"Error obteniendo archivo de Nextcloud: "
            f"{response.status_code} - {response.text}"
        )

    return response


def eliminar_archivo(nombre_archivo, carpeta=None):
    response = requests.delete(
        url_archivo(nombre_archivo, carpeta),
        auth=HTTPBasicAuth(
            settings.NEXTCLOUD_USER,
            settings.NEXTCLOUD_PASSWORD,
        ),
    )

    if response.status_code not in (204, 404):
        raise Exception(
            f"Error eliminando archivo de Nextcloud: "
            f"{response.status_code} - {response.text}"
        )

    return True
