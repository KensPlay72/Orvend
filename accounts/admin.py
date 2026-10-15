from django.contrib import admin
from .models import permision


@admin.register(permision)
class PermisionAdmin(admin.ModelAdmin):
    list_display = ("login_manager", "home_page", "ecommerce")

    def has_add_permission(self, request):
        return not permision.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
