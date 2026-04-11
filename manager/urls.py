from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),



    path("presentaciones/", views.umedidas_view, name="presentaciones"),
    path("presentaciones/post/", views.post_umedida, name="post_umedida"),
    path("presentaciones/get/<int:id>/", views.get_umedida, name="get_umedida"),
    path("presentaciones/put/<int:id>/", views.put_umedida, name="put_umedida"),
    path("presentaciones/delete/<int:id>/", views.delete_umedida, name="delete_umedida"),
] 