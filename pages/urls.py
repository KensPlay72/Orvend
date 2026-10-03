from django.urls import path
from . import views

urlpatterns = [
    path('public/<str:asset_name>', views.public_asset, name='public_asset'),
    path('politica-privacidad/', views.politica_privacidad, name='politica_privacidad'),
    path('politica-cookies/', views.politica_cookies, name='politica_cookies'),
    path('terminos-y-condiciones/', views.terminos_condiciones, name='terminos_condiciones'),
    path('politica-reembolsos/', views.politica_reembolsos, name='politica_reembolsos'),
    path('suscripcion-vencida/', views.suscripcion_vencida, name='suscripcion_vencida'),
    path('', views.home, name='home'),
]
