from django.db import models


class Usuario(models.Model):
    """Projeto 02: senha com hash seguro (PBKDF2, via
    django.contrib.auth.hashers) e papéis de acesso.

    Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 6.1) e,
    para contraste, a falha original em
    Documentação/Projeto01/Ataque-A04-MD5SemSalt.md."""

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
    # 255 para acomodar o hash do PBKDF2 ("pbkdf2_sha256$<iterações>$<salt>$<hash>"),
    # bem mais longo que os 32 caracteres de um hex MD5.
    senha = models.CharField(max_length=255)
    papel = models.CharField(max_length=20, choices=PAPEIS, default=PAPEL_USUARIO)

    def __str__(self):
        return self.email


class RefreshToken(models.Model):
    """Refresh token opaco (não é um JWT) emitido no login, usado só para
    obter um novo access token em POST /api/token/refresh.

    Fica persistido no backend — ao contrário do access token (JWT
    stateless) — justamente para ser revogável: um registro aqui pode ser
    invalidado a qualquer momento (logout, rotação, suspeita de roubo), algo
    que não é possível com um JWT puro sem esperar ele expirar.

    Nunca guardamos o token em texto puro: só o hash SHA-256 dele
    (``token_hash``), para que um dump do banco não exponha tokens usáveis
    diretamente. Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md
    (seção 5)."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='refresh_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()
    revogado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        estado = 'revogado' if self.revogado_em else 'ativo'
        return f'RefreshToken({self.usuario_id}, {estado})'
