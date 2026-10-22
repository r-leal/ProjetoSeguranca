from django.urls import path

from . import views

urlpatterns = [
    path('usuarios/<int:usuario_id>/tarefas', views.listar_tarefas_por_usuario, name='listar_tarefas_por_usuario'),
    path('tarefas', views.criar_tarefa, name='criar_tarefa'),
    path('tarefas/<int:tarefa_id>', views.tarefa_detalhe, name='tarefa_detalhe'),
    path('tarefas/preview-link', views.preview_link, name='preview_link'),
]
