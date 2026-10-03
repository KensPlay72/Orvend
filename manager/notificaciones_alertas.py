"""Generación idempotente de alertas de inventario para el panel de notificaciones."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F, Min, Q, Sum
from django.utils import timezone

from .models import CuentasPorCobrar, CuentasPorPagar, Inventarios, Notificacion
from .notificaciones_realtime import publicar_actualizacion_usuarios


def _usuarios_con_permiso(codename):
    return User.objects.filter(is_active=True).filter(
        Q(is_superuser=True)
        | Q(
            user_permissions__codename=codename,
            user_permissions__content_type__app_label="manager",
        )
        | Q(
            groups__permissions__codename=codename,
            groups__permissions__content_type__app_label="manager",
        )
    ).distinct()


def _sincronizar(usuarios, tipo, alertas):
    """Sincroniza un tipo de alerta en bloque, sin una consulta por usuario."""
    alertas = {alerta["referencia"]: alerta for alerta in alertas}
    referencias = set(alertas)
    ahora = timezone.now()
    usuario_ids = list(usuarios.values_list("id", flat=True))
    if not usuario_ids:
        return set()

    existentes = list(
        Notificacion.objects.filter(
            usuario_id__in=usuario_ids,
            tipo=tipo,
            is_active=True,
            is_delete=False,
        ).only("id", "usuario_id", "referencia", "titulo", "mensaje")
    )
    existentes_por_clave = {
        (notificacion.usuario_id, notificacion.referencia): notificacion
        for notificacion in existentes
    }
    usuarios_cambiados = set()
    nuevas = []
    actualizar = []

    for usuario_id in usuario_ids:
        for referencia, alerta in alertas.items():
            existente = existentes_por_clave.get((usuario_id, referencia))
            if existente is None:
                nuevas.append(
                    Notificacion(
                        usuario_id=usuario_id,
                        tipo=tipo,
                        titulo=alerta["titulo"],
                        mensaje=alerta["mensaje"],
                        referencia=referencia,
                    )
                )
                usuarios_cambiados.add(usuario_id)
            elif (
                existente.titulo != alerta["titulo"]
                or existente.mensaje != alerta["mensaje"]
            ):
                existente.titulo = alerta["titulo"]
                existente.mensaje = alerta["mensaje"]
                existente.f_modificacion = ahora
                actualizar.append(existente)
                usuarios_cambiados.add(usuario_id)

    if nuevas:
        Notificacion.objects.bulk_create(nuevas, batch_size=500)
    if actualizar:
        Notificacion.objects.bulk_update(
            actualizar, ["titulo", "mensaje", "f_modificacion"], batch_size=500
        )

    resueltas = Notificacion.objects.filter(
        usuario_id__in=usuario_ids,
        tipo=tipo,
        is_active=True,
        is_delete=False,
    )
    if referencias:
        resueltas = resueltas.exclude(referencia__in=referencias)
    usuarios_resueltos = set(resueltas.values_list("usuario_id", flat=True))
    if usuarios_resueltos:
        resueltas.update(is_active=False, f_modificacion=ahora)
        usuarios_cambiados.update(usuarios_resueltos)

    return usuarios_cambiados


def actualizar_notificaciones_alertas(*, emitir=True):
    """Sincroniza alertas por cambios operativos o por tarea programada."""
    hoy = timezone.localtime()
    stock_query = (
        Inventarios.objects.filter(
            is_active=True,
            is_delete=False,
            producto__is_active=True,
            producto__is_delete=False,
        )
        .values("producto", "producto__nombre", "ubicacion", "ubicacion__nombre")
        .annotate(stock_total=Sum("cantidad"), stock_minimo=Min("stock_minimo"))
        .filter(stock_total__lte=F("stock_minimo"))
    )
    vencimientos_query = (
        Inventarios.objects.filter(
            is_active=True,
            is_delete=False,
            producto__is_active=True,
            producto__is_delete=False,
            cantidad__gt=0,
            fvencimiento__isnull=False,
            fvencimiento__gte=hoy,
            fvencimiento__lte=hoy + timedelta(days=30),
        )
        .select_related("producto", "ubicacion")
        .order_by("fvencimiento")
    )

    stock = [
        {
            "referencia": f"stock:{item['producto']}:{item['ubicacion']}",
            "titulo": f"Stock bajo: {item['producto__nombre']}",
            "mensaje": (
                f"{item['ubicacion__nombre']} · Actual: {item['stock_total']:.2f} "
                f"| mínimo: {item['stock_minimo']:.2f}"
            ),
        }
        for item in stock_query
    ]
    vencimientos = [
        {
            "referencia": f"vencimiento:{item.id}:{item.fvencimiento.date().isoformat()}",
            "titulo": f"Próximo a vencer: {item.producto.nombre}",
            "mensaje": (
                f"{item.ubicacion.nombre} · Vence el "
                f"{timezone.localtime(item.fvencimiento).strftime('%d/%m/%Y')}"
            ),
        }
        for item in vencimientos_query
    ]

    def alertas_cuentas(cuentas, es_cobro):
        tipo_cuenta = "cobrar" if es_cobro else "pagar"
        nombre_relacion = "cliente" if es_cobro else "proveedor"
        resultado = []

        for cuenta in cuentas:
            dias_restantes = (cuenta.fecha_vencimiento.date() - hoy.date()).days
            relacionado = getattr(cuenta, nombre_relacion)
            if es_cobro:
                nombre = (
                    relacionado.nombre_completo
                    or relacionado.empresa
                    or relacionado.dni
                )
            else:
                nombre = relacionado.nombre_legal or relacionado.nombre_comercial
            monto = f"L. {cuenta.monto_pendiente:.2f}"

            if dias_restantes <= 0:
                resultado.append(
                    {
                        "referencia": f"{tipo_cuenta}:mora:{cuenta.id}",
                        "titulo": f"Cuenta en mora: {nombre}",
                        "mensaje": f"{nombre} ha caído en mora. Debe {monto}.",
                    }
                )
                continue

            resultado.append(
                {
                    "referencia": f"{tipo_cuenta}:vencimiento:{cuenta.id}:{hoy.date().isoformat()}",
                    "titulo": f"Cuenta por vencer: {nombre}",
                    "mensaje": f"Faltan {dias_restantes} día{'s' if dias_restantes != 1 else ''} para {'cobrar' if es_cobro else 'pagar'} {monto}.",
                }
            )
        return resultado

    cuentas_por_cobrar = CuentasPorCobrar.objects.filter(
        is_active=True,
        is_delete=False,
        monto_pendiente__gt=0,
        fecha_vencimiento__date__lte=hoy.date() + timedelta(days=5),
    ).select_related("cliente")
    cuentas_por_pagar = CuentasPorPagar.objects.filter(
        is_active=True,
        is_delete=False,
        monto_pendiente__gt=0,
        fecha_vencimiento__date__lte=hoy.date() + timedelta(days=5),
    ).select_related("proveedor")
    usuarios_compras = _usuarios_con_permiso("view_compras")
    usuarios_afectados = set()
    usuarios_afectados.update(
        _sincronizar(usuarios_compras, Notificacion.Tipo.STOCK_BAJO, stock)
    )
    usuarios_afectados.update(
        _sincronizar(usuarios_compras, Notificacion.Tipo.VENCIMIENTO, vencimientos)
    )
    usuarios_afectados.update(_sincronizar(
        _usuarios_con_permiso("gestionar_recepcion_inventario"),
        Notificacion.Tipo.VENCIMIENTO,
        vencimientos,
    ))
    usuarios_afectados.update(_sincronizar(
        _usuarios_con_permiso("view_cuentasporcobrar"),
        Notificacion.Tipo.CUENTA_COBRAR,
        alertas_cuentas(cuentas_por_cobrar, es_cobro=True),
    ))
    usuarios_afectados.update(_sincronizar(
        _usuarios_con_permiso("view_cuentasporpagar"),
        Notificacion.Tipo.CUENTA_PAGAR,
        alertas_cuentas(cuentas_por_pagar, es_cobro=False),
    ))
    if emitir:
        publicar_actualizacion_usuarios(usuarios_afectados)


def programar_sincronizacion_alertas():
    """Agrupa cambios dentro de una misma transacción en una sola sincronización."""
    conexion = transaction.get_connection()
    for registro in conexion.run_on_commit:
        funcion = registro[1]
        if getattr(funcion, "_sincroniza_alertas", False):
            return

    def sincronizar():
        actualizar_notificaciones_alertas()

    sincronizar._sincroniza_alertas = True
    transaction.on_commit(sincronizar)
