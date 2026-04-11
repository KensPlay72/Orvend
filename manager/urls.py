from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("presentaciones/", views.umedidas_view, name="presentaciones"),
    path("presentaciones/post/", views.post_umedida, name="post_umedida"),

] 