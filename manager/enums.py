from django.db import models


class EstadoCompra(models.TextChoices):
    PENDIENTE = "Pendiente", "Pendiente"
    EN_RECEPCION = "En Recepcion", "En Recepción"
    RECEPCION_PARCIAL = "Recepcion Parcial", "Recepción Parcial"
    COMPLETADO = "Completado", "Completado"
    CON_DEVOLUCION = "Con Devolucion", "Con Devolución"
    PENDIENTE_RESOLUCION = "Pendiente Resolucion", "Pendiente Resolución"
    CERRADA = "Cerrada", "Cerrada"
    CANCELADA = "Cancelada", "Cancelada"


class EstadoDevolucionCompra(models.TextChoices):
    PENDIENTE = "Pendiente", "Pendiente"
    APROBADA = "Aprobada", "Aprobada"
    RECHAZADA = "Rechazada", "Rechazada"
    COMPLETADA = "Completada", "Completada"
    CANCELADA = "Cancelada", "Cancelada"


class Estados(models.TextChoices):
    PENDIENTE = "Pendiente", "Pendiente"
    COMPLETADO = "Completado", "Completado"
    CANCELADA = "Cancelada", "Cancelada"


class EstadoCuenta(models.IntegerChoices):
    PENDIENTE = 1, "Pendiente"
    PARCIAL = 2, "Parcial"
    PAGADO = 3, "Pagado"
    CANCELADO = 4, "Cancelado"


class MotivoDevolucion(models.IntegerChoices):
    PRODUCTO_DANADO = 1, "Producto dañado"
    PRODUCTO_VENCIDO = 2, "Producto vencido"
    ERROR_PEDIDO = 3, "Error de pedido"
    PRODUCTO_INCORRECTO = 4, "Producto incorrecto"
    EXCESO_INVENTARIO = 5, "Exceso de inventario"
    OTRO = 6, "Otro"


class TipoMovimiento(models.IntegerChoices):
    # ENTRADAS
    ENTRADA_COMPRA = 1, "Entrada Compra"
    TRASLADO_ENTRADA = 2, "Traslado Entrada"
    AJUSTE_ENTRADA = 3, "Ajuste Entrada"
    DEVOLUCION_CLIENTE = 4, "Devolución Cliente"
    CAMBIO_CLIENTE_ENTRADA = 5, "Cambio Cliente Entrada"

    # SALIDAS
    SALIDA_VENTA = 10, "Salida Venta"
    TRASLADO_SALIDA = 11, "Traslado Salida"
    AJUSTE_SALIDA = 12, "Ajuste Salida"
    DESCARTE = 13, "Descarte"
    DEVOLUCION_PROVEEDOR = 14, "Devolución Proveedor"
    CAMBIO_CLIENTE_SALIDA = 15, "Cambio Cliente Salida"
