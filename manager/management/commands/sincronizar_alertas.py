from django.core.management.base import BaseCommand

from manager.notificaciones_alertas import actualizar_notificaciones_alertas


class Command(BaseCommand):
    help = "Sincroniza alertas operativas y las publica por WebSocket."

    def handle(self, *args, **options):
        actualizar_notificaciones_alertas()
        self.stdout.write(self.style.SUCCESS("Alertas sincronizadas."))
