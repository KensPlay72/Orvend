from django.urls import path

from . import views

app_name = "tiendav"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("categorias/", views.lista_categorias, name="categorias"),
    path("cuenta/", views.cuenta_cliente, name="cuenta"),
    path("cuenta/cerrar-sesion/", views.cerrar_sesion_cliente, name="cerrar_sesion"),
    path("mi-perfil/", views.perfil_cliente, name="perfil"),
    path("mis-pedidos/", views.historial_cliente, name="historial"),
    path("mis-pedidos/<uuid:token>/", views.detalle_pedido_cliente, name="detalle_pedido"),
    path("mis-pedidos/<int:pedido_id>/", views.detalle_pedido_cliente),
    path("pedidos/crear/", views.crear_pedido, name="crear_pedido"),
    path("logo/", views.logo_tienda, name="logo"),
    path("banner/<int:banner_id>/", views.banner_tienda, name="banner"),
    path("producto/<int:imagen_id>/imagen/", views.producto_imagen_tienda, name="producto_imagen"),
    path("producto/<uuid:token>/", views.detalle_producto, name="detalle_producto"),
    path("ubicaciones/", views.ubicaciones_tienda, name="ubicaciones"),
    path("ubicaciones/<int:ubicacion_id>/imagen/", views.ubicacion_imagen_tienda, name="ubicacion_imagen"),
]
