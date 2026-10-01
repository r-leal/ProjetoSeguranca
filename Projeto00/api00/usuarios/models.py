from django.db import models


class Usuario(models.Model):
    """Projeto 00 (inseguro de propósito): sem papéis e com senha em texto puro."""

    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=100)
    data_nascimento = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=255)

    def __str__(self):
        return self.email
