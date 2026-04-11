from django.contrib import admin
from .models import *


@admin.register(UMedidas)
class UMedidasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'abreviatura', 'is_active', 'is_delete')
    search_fields = ('nombre', 'abreviatura')
    list_filter = ('is_active', 'is_delete')


@admin.register(Marcas)
class MarcasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'is_active', 'is_delete')
    search_fields = ('nombre', 'descripcion')
    list_filter = ('is_active', 'is_delete')

@admin.register(Categorias)
class CategoriasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'is_active', 'is_delete')
    search_fields = ('nombre', 'descripcion')
    list_filter = ('is_active', 'is_delete')

@admin.register(Proveedores)
class ProveedoresAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre_legal',
        'nombre_comercial',
        'rtn',
        'dias_credito',
        'telefono',
        'email',
        'is_active',
        'is_delete'
    )

    search_fields = (
        'nombre_legal',
        'nombre_comercial',
        'rtn',
        'email'
    )

    list_filter = (
        'is_active',
        'is_delete',
        'dias_credito'
    )

@admin.register(ProveedoresContactos)
class ProveedoresContactosAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "proveedor",
        "nombre",
        "puesto",
        "telefono",
        "email",
        "is_active",
        "is_delete",
        "f_creacion",
    )

    list_filter = (
        "is_active",
        "is_delete",
        "proveedor",
    )

    search_fields = (
        "nombre",
        "puesto",
        "telefono",
        "email",
        "proveedor__nombre_comercial",
        "proveedor__nombre_legal",
    )

    ordering = ("-id",)

    autocomplete_fields = ("proveedor",)