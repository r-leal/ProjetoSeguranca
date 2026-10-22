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
    # Link opcional de referência da tarefa. O título é sempre obtido pelo
    # backend (tarefas/link_preview.py), nunca aceito cru do cliente — é o
    # próprio backend que busca a URL, então as defesas contra SSRF
    # (validação de esquema/IP, sem seguir redirecionamento para rede
    # interna) vivem lá, não aqui.
    url = models.URLField(max_length=500, blank=True, null=True)
    url_titulo = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.nome
