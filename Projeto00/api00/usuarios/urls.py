from django.urls import path

from . import views

urlpatterns = [
    path('usuarios', views.cadastrar_usuario, name='cadastrar_usuario'),
    path('login', views.login, name='login'),
]
