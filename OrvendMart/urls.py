from django.contrib import admin
from django.urls import path, include

from OrvendMart import settings
from django.conf.urls.static import static


handler404 = "pages.views.error_404"
handler403 = "pages.views.error_403"
handler500 = "pages.views.error_500"

urlpatterns = [
    path('orvend-panel-2026/', admin.site.urls),

    # login/logout
    path('accounts/', include('accounts.urls')),
    path('manager/', include('manager.urls')),

    path('', include('pages.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
