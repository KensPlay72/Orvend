from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("presentaciones/", views.umedidas_view, name="presentaciones"),
    path("presentaciones/post/", views.post_umedida, name="post_umedida"),
    path("presentaciones/get/<int:id>/", views.get_umedida, name="get_umedida"),
    path("presentaciones/put/<int:id>/", views.put_umedida, name="put_umedida"),
    path(
        "presentaciones/delete/<int:id>/", views.delete_umedida, name="delete_umedida"
    ),
    path("presentaciones/search/", views.search_umedidas, name="search_umedidas"),
    path("catalogos/<str:tipo>/exportar/", views.exportar_catalogo_excel, name="exportar_catalogo_excel"),
    path("catalogos/<str:tipo>/plantilla/", views.descargar_plantilla_catalogo, name="descargar_plantilla_catalogo"),
    path("catalogos/<str:tipo>/importar/", views.importar_catalogo_excel, name="importar_catalogo_excel"),
    path("marcas/", views.marcas_view, name="marcas"),
    path("marcas/post/", views.post_marca, name="post_marca"),
    path("marcas/get/<int:id>/", views.get_marca, name="get_marca"),
    path("marcas/put/<int:id>/", views.put_marca, name="put_marca"),
    path("marcas/delete/<int:id>/", views.delete_marca, name="delete_marca"),
    path("marcas/search/", views.search_marcas, name="search_marcas"),
    path("categorias/", views.categorias_view, name="categorias"),
    path("categorias/post/", views.post_categoria, name="post_categoria"),
    path("categorias/get/<int:id>/", views.get_categoria, name="get_categoria"),
    path("categorias/put/<int:id>/", views.put_categoria, name="put_categoria"),
    path(
        "categorias/delete/<int:id>/", views.delete_categoria, name="delete_categoria"
    ),
    path("categorias/search/", views.search_categorias, name="search_categorias"),
    path("proveedores/", views.proveedores_view, name="proveedores"),
    path("proveedores/post/", views.post_proveedor, name="post_proveedor"),
    path("proveedores/get/<int:id>/", views.get_proveedor, name="get_proveedor"),
    path("proveedores/put/<int:id>/", views.put_proveedor, name="put_proveedor"),
    path(
        "proveedores/delete/<int:id>/", views.delete_proveedor, name="delete_proveedor"
    ),
    path("proveedores/search/", views.search_proveedores, name="search_proveedores"),
    path(
        "proveedores/contactos/",
        views.proveedores_contactos_view,
        name="proveedores_contactos",
    ),
    path(
        "proveedores/contactos/post/",
        views.post_proveedor_contacto,
        name="post_proveedor_contacto",
    ),
    path(
        "proveedores/contactos/get/<int:id>/",
        views.get_proveedor_contacto,
        name="get_proveedor_contacto",
    ),
    path(
        "proveedores/contactos/put/<int:id>/",
        views.put_proveedor_contacto,
        name="put_proveedor_contacto",
    ),
    path(
        "proveedores/contactos/delete/<int:id>/",
        views.delete_proveedor_contacto,
        name="delete_proveedor_contacto",
    ),
    path("productos/", views.productos_view, name="productos"),
    path("configuracion/", views.configuracion_view, name="configuracion"),
    path("configuracion/guardar/", views.guardar_configuracion, name="guardar_configuracion"),
    path("configuracion/logo/", views.configuracion_logo, name="configuracion_logo"),
    path("configuracion/banner/<int:banner_id>/", views.configuracion_banner, name="configuracion_banner"),
    path("combos/", views.combos_view, name="combos"),
    path("combos/guardar/", views.guardar_combo, name="guardar_combo"),
    path("combos/imagen/<int:imagen_id>/", views.combo_imagen, name="combo_imagen"),
    path("combos/lista/", views.combos_list_view, name="combos_list"),
    path("combos/<int:combo_id>/detalle/", views.detalle_combo, name="detalle_combo"),
    path(
        "combos/<int:combo_id>/cambiar-estado/",
        views.cambiar_estado_combo,
        name="cambiar_estado_combo",
    ),
    path(
        "productos/exportar/",
        views.exportar_productos_excel,
        name="exportar_productos_excel",
    ),
    path("productos/plantilla/", views.descargar_plantilla_productos, name="descargar_plantilla_productos"),
    path("productos/importar/", views.importar_productos_excel, name="importar_productos_excel"),
    path(
    "productos/imagen/<int:imagen_id>/",
    views.producto_imagen,
    name="producto_imagen",
    ),
    path("productos/post/", views.post_producto, name="post_producto"),
    path("productos/get/<int:id>/", views.get_producto, name="get_producto"),
    path("productos/put/<int:id>/", views.put_producto, name="put_producto"),
    path("productos/delete/<int:id>/", views.delete_producto, name="delete_producto"),
    path("productos/search/", views.search_productos, name="search_productos"),
    path("api/proxy/productos/", views.api_productos, name="api_productos"),
    path("api/caja/productos/", views.api_productos_caja, name="api_productos_caja"),
    path("api/proxy/productos/padre/", views.get_productos_padre, name="api_productos_padre"),
    path("api/proxy/productos/hijos/", views.get_productos_hijos, name="api_productos_hijos"),
    path(
    "productos-rel/",
        views.productos_rel_view,
        name="productos_rel"
    ),
    path(
        "productosrel/post/",
        views.post_productosrel,
        name="post_productosrel",
    ),
    path(
        "productosrel/get/<int:id>/",
        views.get_productosrel,
        name="get_productosrel",
    ),

    path(
        "productosrel/put/<int:id>/",
        views.put_productosrel,
        name="put_productosrel",
    ),
    path("ubicaciones/", views.ubicaciones_view, name="ubicaciones"),
    path("ubicaciones/post/", views.post_ubicaciones, name="post_ubicaciones"),
    path("ubicaciones/get/<int:id>/", views.get_ubicaciones, name="get_ubicaciones"),
    path("ubicaciones/put/<int:id>/", views.put_ubicaciones, name="put_ubicaciones"),
    path(
        "ubicaciones/delete/<int:id>/",
        views.delete_ubicaciones,
        name="delete_ubicaciones",
    ),
    path("ubicaciones/search/", views.search_ubicaciones, name="search_ubicaciones"),
    path("ubicaciones/bodega/search/", views.search_bodegas, name="search_bodegas"),
    path("compras/", views.compras_view, name="compras"),
    path("compras/exportar/", views.exportar_compras_excel, name="exportar_compras_excel"),
    path(
        "compras/plantilla/",
        views.descargar_plantilla_compras,
        name="descargar_plantilla_compras",
    ),
    path(
        "compras/importar/",
        views.importar_compras_excel,
        name="importar_compras_excel",
    ),
    path("compras/realizarcompra", views.realizarcompra_view, name="realizarcompra"),
    path("compras/realizarcompra/post/", views.post_compra, name="post_compra"),
    path(
        "compras/orden/<uuid:token>/",
        views.detalle_compra_view,
        name="detalle_compra",
    ),
    path(
        "compras/documento/<uuid:token>/pdf/",
        views.proxy_compras_pdf,
        name="compras_pdf",
    ),
    path(
        "compras/documento/<uuid:token>/",
        views.editar_compra,
        name="editar_compra",
    ),
    path(
        "compras/orden/<uuid:token>/guardar/",
        views.editar_compra_put,
        name="editar_compra_put",
    ),
    path("cppagar/", views.cuentas_por_pagar_view, name="cppagar"),
    path("cppagar/post/<int:id>/", views.registrar_abono, name="cppagar_abono"),
    path(
        "cppagar/<int:id>/abonos/",
        views.historial_abonos_pagar,
        name="cppagar_abonos",
    ),
    path("cxcobrar/", views.cuentas_por_cobrar_view, name="cxcobrar"),
    path(
        "cxcobrar/post/<int:id>/",
        views.registrar_abono_cobrar,
        name="cxcobrar_abono",
    ),
    path(
        "cxcobrar/<int:id>/abonos/",
        views.historial_abonos_cobrar,
        name="cxcobrar_abonos",
    ),
    path("clientes/", views.clientes_view, name="clientes"),
    path(
        "clientes/exportar/",
        views.exportar_clientes_excel,
        name="exportar_clientes_excel",
    ),
    path("clientes/post/", views.post_clientes, name="post_cliente"),
    path("clientes/get/<int:id>/", views.get_cliente, name="get_cliente"),
    path("clientes/put/<int:id>/", views.put_cliente, name="put_cliente"),
    path(
        "clientes/search/",
        views.search_clientes,
        name="search_clientes",
    ),
    path("bodega/dashboard/", views.dashboard_bodega, name="dashboard_bodega"),
    path(
        "bodega/recepcion_inventario/",
        views.recepcion_inventario_view,
        name="recepcion_inventario",
    ),
    path(
        "bodega/autorizar/<str:tipo>/<uuid:token>/",
        views.autorizar_entrada_view,
        name="autorizar_entrada",
    ),
    path(
        "bodega/compras/<uuid:token>/marcar-llegada/",
        views.marcar_llegada_compra,
        name="marcar_llegada_compra",
    ),
    path(
        "bodega/traslados/<uuid:token>/marcar-llegada/",
        views.marcar_llegada_traslado,
        name="marcar_llegada_traslado",
    ),
    path(
        "bodega/detalleinventario/post/",
        views.post_autorizar_inventario,
        name="post_autorizar_inventario",
    ),
    path(
        "bodega/devocompras/",
        views.post_devolucion_compra,
        name="post_devolucion_compra",
    ),
    path("inventario/", views.inventario_view, name="inventario"),
    path(
        "inventario/exportar/",
        views.exportar_inventario_excel,
        name="exportar_inventario_excel",
    ),
    path(
        "inventario/<int:id>/",
        views.get_inventario_producto,
        name="get_inventario_producto",
    ),
    path("compras/devoluciones/", views.devoluciones_view, name="devoluciones_view"),
    path(
        "compras/devoluciones/detalles/<uuid:token>/",
        views.detalle_devolucion_view,
        name="detalle_devolucion_view",
    ),
    path(
        "compras/devoluciones/aprobar/<uuid:token>/",
        views.aprobar_devolucion_view,
        name="aprobar_devolucion_view",
    ),
    path(
        "compras/devoluciones/rechazar/<uuid:token>/",
        views.rechazar_devolucion_view,
        name="rechazar_devolucion_view",
    ),
    path(
        "inventario/ubicacion/<int:ubicacion_id>/",
        views.inventario_por_ubicacion,
        name="inventario_por_ubicacion",
    ),
    path("r/traslados/", views.traslados_view, name="traslados_create"),
    path("traslados/post/", views.post_traslado, name="post_traslado"),
    path(
        "traslados/",
        views.traslados_list,
        name="traslados_list",
    ),
    path(
        "traslados/orden/<uuid:token>/",
        views.detalle_traslado_view,
        name="detalle_traslado",
    ),
    path("descuentos/", views.descuentos_view, name="descuentos"),
    path("descuentos/post/", views.post_descuento, name="post_descuento"),
    path("descuentos/get/<int:id>/", views.get_descuento, name="get_descuento"),
    path("descuentos/put/<int:id>/", views.put_descuento, name="put_descuento"),
    path("caja/", views.caja_view, name="caja"),
    path("caja/retiros/", views.retiros_caja_view, name="retiros_caja"),
    path("caja/retiros/listado/", views.retiros_caja_list_view, name="retiros_caja_list"),
    path("caja/retiros/crear/", views.crear_retiro_caja, name="crear_retiro_caja"),
    path("caja/retiros/<int:id>/completar/", views.completar_retiro_caja, name="completar_retiro_caja"),
    path("notificaciones/<int:id>/leer/", views.marcar_notificacion_leida, name="marcar_notificacion_leida"),
    path("notificaciones/estado/", views.estado_notificaciones, name="estado_notificaciones"),
    path("cotizaciones/", views.cotizaciones_view, name="cotizaciones"),
    path("busquedacodigo/<str:codigo>/", views.busqueda_codigo, name="busqueda_codigo"),
    path("cotizaciones/crear/", views.crear_cotizacion, name="crear_cotizacion"),
    path("cotizaciones/pdf/<uuid:token>/", views.imprimir_cotizacion, name="imprimir_cotizacion"),
    path(
        "busquedanombre/<str:producto>/", views.busqueda_nombre, name="busqueda_nombre"
    ),
    path(
        "cupon_descuento/<str:cupon>/<int:id>/",
        views.descuento_cupon,
        name="descuento_cupon",
    ),
    path(
        "datos_sat/",
        views.datos_sat_view,
        name="datos_sat",
    ),
    path(
        "datos_sat/get/<int:id>/",
        views.get_datos_sat,
        name="get_datos_sat",
    ),
    path(
        "datos_sat/put/<int:id>/",
        views.put_datos_sat,
        name="get_datos_sat",
    ),
    path("datos_sat/post/", views.post_datos_sat, name="post_datos_sat"),
    path("realizar_venta/", views.guardar_compra, name="guardar_compra"),
    path(
        "recibo_pdf/<uuid:token>/", views.imprimir_factura, name="imprimir_factura"
    ),
    path(
        "integracion/facturas/<uuid:token>/pdf/",
        views.descargar_factura_n8n,
        name="descargar_factura_n8n",
    ),
    path("ventas/", views.ventas_view, name="ventas"),
    path("ventas/exportar/", views.exportar_ventas_excel, name="exportar_ventas_excel"),
    path(
        "devoluciones-venta/",
        views.devoluciones_venta_view,
        name="devoluciones_venta",
    ),
    path(
        "devoluciones-venta/factura/<int:numero_factura>/",
        views.buscar_factura_devolucion_venta,
        name="buscar_factura_devolucion_venta",
    ),
    path(
        "devoluciones-venta/crear/",
        views.crear_devolucion_venta,
        name="crear_devolucion_venta",
    ),
    path(
        "devoluciones-venta/listado/",
        views.devoluciones_venta_list,
        name="devoluciones_venta_list",
    ),
    path(
        "devoluciones-venta/exportar/",
        views.exportar_devoluciones_venta_excel,
        name="exportar_devoluciones_venta_excel",
    ),
    path(
        "notas-credito/disponibles/",
        views.notas_credito_disponibles,
        name="notas_credito_disponibles",
    ),


    path("abrir/", views.abrir_caja, name="abrir_caja"),
    path("iniciar_cuadre/", views.iniciar_cuadre, name="iniciar_cuadre"),
    path(
    "caja/cuadre/",
    views.cuadre_caja,
    name="cuadre_caja"
    ),

    path(
        "caja/cuadre/cerrar/",
        views.cerrar_cuadre_caja,
        name="cerrar_cuadre_caja"
    ),

    path("cajas_manager/", views.cajas_manager_view, name="cajas_manager"),

]
