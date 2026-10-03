"""Publicación de eventos WebSocket para el panel de notificaciones."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def grupo_usuario(usuario_id):
    return f"notificaciones.usuario.{usuario_id}"


def publicar_actualizacion_usuarios(usuario_ids):
    """Solicita al navegador de cada usuario refrescar su panel por WebSocket."""
    ids = {int(usuario_id) for usuario_id in usuario_ids if usuario_id}
    if not ids:
        return

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        enviar = async_to_sync(channel_layer.group_send)
        for usuario_id in ids:
            enviar(grupo_usuario(usuario_id), {"type": "notificaciones.actualizar"})
    except Exception:
        # Una operación del ERP no debe fallar si el proceso de WebSocket o
        # Redis se está reiniciando. El cliente se reconectará automáticamente.
        return


def publicar_actualizacion_global():
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "notificaciones.global", {"type": "notificaciones.actualizar"}
            )
    except Exception:
        return
