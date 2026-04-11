from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views
import os

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),



    path("presentaciones/", views.umedidas_view, name="presentaciones"),
    path("presentaciones/post/", views.post_umedida, name="post_umedida"),
    path("presentaciones/get/<int:id>/", views.get_umedida, name="get_umedida"),
    path("presentaciones/put/<int:id>/", views.put_umedida, name="put_umedida"),
    path("presentaciones/delete/<int:id>/", views.delete_umedida, name="delete_umedida"),
    path("presentaciones/search/", views.search_umedidas, name="search_umedidas"),


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
    path("categorias/delete/<int:id>/", views.delete_categoria, name="delete_categoria"),
    path("categorias/search/", views.search_categorias, name="search_categorias"),


    path("proveedores/", views.proveedores_view, name="proveedores"),
    path("proveedores/post/", views.post_proveedor, name="post_proveedor"),
    path("proveedores/get/<int:id>/", views.get_proveedor, name="get_proveedor"),
    path("proveedores/put/<int:id>/", views.put_proveedor, name="put_proveedor"),
    path("proveedores/delete/<int:id>/", views.delete_proveedor, name="delete_proveedor"),
    path("proveedores/search/", views.search_proveedores, name="search_proveedores"),

    path("proveedores/contactos/", views.proveedores_contactos_view , name="proveedores_contactos"),
    path("proveedores/contactos/post/", views.post_proveedor_contacto, name="post_proveedor_contacto"),
    path("proveedores/contactos/get/<int:id>/", views.get_proveedor_contacto, name="get_proveedor_contacto"),
    path("proveedores/contactos/put/<int:id>/", views.put_proveedor_contacto, name="put_proveedor_contacto"),
    path("proveedores/contactos/delete/<int:id>/", views.delete_proveedor_contacto, name="delete_proveedor_contacto"),

    path("productos/", views.productos_view, name="productos"),
    path("productos/post/", views.post_producto, name="post_producto"),
    path("productos/get/<int:id>/", views.get_producto, name="get_producto"),
    path("productos/put/<int:id>/", views.put_producto, name="put_producto"),
    path("productos/delete/<int:id>/", views.delete_producto, name="delete_producto"),
    path("productos/search/", views.search_productos, name="search_productos"),
] 
