from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .notificaciones_realtime import grupo_usuario
from .notificaciones_service import estado_notificaciones_usuario


class NotificacionesConsumer(AsyncJsonWebsocketConsumer):
    """Mantiene sincronizado el panel sin consultas HTTP periódicas."""

    async def connect(self):
        usuario = self.scope.get("user")
        if not usuario or not usuario.is_authenticated:
            await self.close(code=4401)
            return

        self.grupo_usuario = grupo_usuario(usuario.id)
        await self.channel_layer.group_add(self.grupo_usuario, self.channel_name)
        await self.channel_layer.group_add("notificaciones.global", self.channel_name)
        await self.accept()
        await self.enviar_estado()

    async def disconnect(self, close_code):
        if hasattr(self, "grupo_usuario"):
            await self.channel_layer.group_discard(self.grupo_usuario, self.channel_name)
            await self.channel_layer.group_discard(
                "notificaciones.global", self.channel_name
            )

    async def notificaciones_actualizar(self, event):
        await self.enviar_estado()

    async def enviar_estado(self):
        usuario_id = self.scope["user"].id
        estado = await self.obtener_estado(usuario_id)
        await self.send_json({"tipo": "estado_notificaciones", "estado": estado})

    @database_sync_to_async
    def obtener_estado(self, usuario_id):
        return estado_notificaciones_usuario(usuario_id)
