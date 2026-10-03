"""Consultas y serialización compartidas por HTTP y WebSocket."""

from django.db.models import Q
from django.urls import reverse

from .models import Notificacion, RetiroCaja


def estado_notificaciones_usuario(usuario):
    usuario_id = getattr(usuario, "id", usuario)
    pendientes = Notificacion.objects.filter(
        Q(usuario_id=usuario_id) | Q(para_todos=True),
        is_active=True,
        is_delete=False,
        leida=False,
    )
    notificaciones = list(
        pendientes.select_related("retiro_caja").order_by("-f_creacion")[:8]
    )

    def serializar(notificacion):
        retiro = notificacion.retiro_caja
        es_accion = bool(retiro and retiro.estado == RetiroCaja.Estado.PENDIENTE)
        es_lectura = notificacion.tipo != Notificacion.Tipo.RETIRO_CAJA
        return {
            "id": notificacion.id,
            "tipo": notificacion.tipo,
            "titulo": notificacion.titulo,
            "mensaje": notificacion.mensaje,
            "accion": es_accion,
            "url": reverse("completar_retiro_caja", args=[retiro.id]) if es_accion else "",
            "monto": f"{retiro.monto:.2f}" if es_accion else "",
            "read_url": (
                reverse("marcar_notificacion_leida", args=[notificacion.id])
                if es_lectura
                else ""
            ),
        }

    return {
        "ok": True,
        "ids": [notificacion.id for notificacion in notificaciones],
        "notificaciones": [serializar(notificacion) for notificacion in notificaciones],
        "pendientes": pendientes.count(),
    }
