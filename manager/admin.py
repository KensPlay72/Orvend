from django.contrib import admin
from .models import UMedidas


@admin.register(UMedidas)
class UMedidasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'abreviatura', 'is_active', 'is_delete')
    search_fields = ('nombre', 'abreviatura')
    list_filter = ('is_active', 'is_delete')