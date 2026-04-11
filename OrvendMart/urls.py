from django.contrib import admin
from django.urls import path, include

from OrvendMart import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # login/logout
    path('accounts/', include('accounts.urls')),
    path('manager/', include('manager.urls')),

    path('', include('pages.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)