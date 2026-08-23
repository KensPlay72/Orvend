import requests
from requests.auth import HTTPBasicAuth
from django.conf import settings


def subir_archivo(archivo, nombre_archivo):

    url = (
        f"{settings.NEXTCLOUD_URL}"
        f"/remote.php/dav/files/"
        f"{settings.NEXTCLOUD_USER}/"
        f"{settings.NEXTCLOUD_FOLDER}/"
        f"/{nombre_archivo}"
    )

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


def obtener_archivo(url):

    response = requests.get(
        url,
        auth=HTTPBasicAuth(
            settings.NEXTCLOUD_USER,
            settings.NEXTCLOUD_PASSWORD,
        ),
    )

    if response.status_code != 200:
        raise Exception(
            f"Error obteniendo archivo de Nextcloud: "
            f"{response.status_code} - {response.text}"
        )

    return response


def eliminar_archivo(url):

    response = requests.delete(
        url,
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