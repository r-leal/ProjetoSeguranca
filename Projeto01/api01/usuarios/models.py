from django.db import models


class Usuario(models.Model):
    """Projeto 01 (inseguro de propósito): senha em hash MD5 sem salt e papéis
    de acesso. Ver Documentação/Projeto01/Vulnerabilidades.md."""

    PAPEL_USUARIO = 'usuario'
    PAPEL_ADMIN = 'admin'
    PAPEL_GERENTE = 'gerente'

    PAPEIS = [
        (PAPEL_USUARIO, 'Usuário'),
        (PAPEL_ADMIN, 'Admin'),
        (PAPEL_GERENTE, 'Gerente'),
    ]

    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=100)
    data_nascimento = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=32)
    papel = models.CharField(max_length=20, choices=PAPEIS, default=PAPEL_USUARIO)

    def __str__(self):
        return self.email
