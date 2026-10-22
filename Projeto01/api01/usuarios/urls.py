from django.urls import path

from . import views

urlpatterns = [
    path('usuarios', views.usuarios_collection, name='usuarios_collection'),
    path('usuarios/me', views.usuario_logado, name='usuario_logado'),
    path('login', views.login, name='login'),
]
