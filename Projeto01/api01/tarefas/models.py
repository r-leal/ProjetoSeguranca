from django.db import models

from usuarios.models import Usuario


class Tarefa(models.Model):
    ESPERANDO = 'esperando'
    EM_ANDAMENTO = 'em_andamento'
    CONCLUIDO = 'concluido'

    ESTADOS = [
        (ESPERANDO, 'Esperando'),
        (EM_ANDAMENTO, 'Em andamento'),
        (CONCLUIDO, 'Concluído'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='tarefas')
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True)
    data_prazo = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESPERANDO)

    def __str__(self):
        return self.nome
