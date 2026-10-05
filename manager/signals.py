from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import (
    CuentasPorCobrar,
    CuentasPorPagar,
    ConfiguracionEmpresa,
    Inventarios,
    Notificacion,
    RegistroAbonos,
    RegistroAbonosCobrar,
    RetiroCaja,
    SuscripcionSistema,
)
from .context_processors import invalidar_tema_empresa_cache
from .notificaciones_alertas import programar_sincronizacion_alertas
from .notificaciones_realtime import (
    publicar_actualizacion_global,
    publicar_actualizacion_usuarios,
)


def _sincronizar_alertas_despues_de_commit():
    programar_sincronizacion_alertas()


@receiver(post_save, sender=Inventarios)
@receiver(post_delete, sender=Inventarios)
@receiver(post_save, sender=CuentasPorCobrar)
@receiver(post_delete, sender=CuentasPorCobrar)
@receiver(post_save, sender=CuentasPorPagar)
@receiver(post_delete, sender=CuentasPorPagar)
@receiver(post_save, sender=RegistroAbonos)
@receiver(post_delete, sender=RegistroAbonos)
@receiver(post_save, sender=RegistroAbonosCobrar)
@receiver(post_delete, sender=RegistroAbonosCobrar)
@receiver(post_save, sender=SuscripcionSistema)
@receiver(post_delete, sender=SuscripcionSistema)
def sincronizar_alertas_operativas(sender, instance, **kwargs):
    if not kwargs.get("raw", False):
        _sincronizar_alertas_despues_de_commit()


@receiver(post_save, sender=ConfiguracionEmpresa)
@receiver(post_delete, sender=ConfiguracionEmpresa)
def invalidar_tema_empresa(sender, instance, **kwargs):
    """Invalida el tema cacheado únicamente cuando se cambia la configuración."""
    transaction.on_commit(invalidar_tema_empresa_cache)


@receiver(post_save, sender=Notificacion)
def publicar_notificacion_guardada(sender, instance, **kwargs):
    def publicar():
        if instance.para_todos:
            publicar_actualizacion_global()
        elif instance.usuario_id:
            publicar_actualizacion_usuarios([instance.usuario_id])

    transaction.on_commit(publicar)


@receiver(post_save, sender=RetiroCaja)
def publicar_actualizacion_retiro(sender, instance, **kwargs):
    transaction.on_commit(
        lambda: publicar_actualizacion_usuarios([instance.cajero_id])
    )
