"""Emissão, rotação e revogação de refresh tokens.

Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 5) para a
explicação didática de por que separamos access token (JWT stateless, vida
curta) de refresh token (opaco, persistido no backend, revogável)."""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import RefreshToken


class RefreshTokenInvalido(Exception):
    """Levantado quando o refresh token recebido é desconhecido, já foi
    revogado (inclusive por reuso suspeito) ou está expirado."""


def _hash(token_bruto: str) -> str:
    return hashlib.sha256(token_bruto.encode('utf-8')).hexdigest()


def gerar_refresh_token(usuario):
    """Cria e persiste um novo refresh token para o usuário, devolvendo o
    valor em texto puro (só existe fora do banco por tempo nenhum: é
    colocado direto num cookie HttpOnly e nunca retorna no corpo JSON)."""
    token_bruto = secrets.token_urlsafe(48)
    expira_em = timezone.now() + timedelta(seconds=settings.REFRESH_TOKEN_TTL_SEGUNDOS)
    RefreshToken.objects.create(
        usuario=usuario,
        token_hash=_hash(token_bruto),
        expira_em=expira_em,
    )
    return token_bruto, expira_em


def rotacionar_refresh_token(token_bruto: str):
    """Valida o refresh token recebido e emite um substituto (rotação: o
    antigo é marcado como revogado e um novo é criado a cada uso).

    Se o hash não existir ou estiver expirado, o token é rejeitado. Se o
    hash existir mas já tiver sido revogado antes, é sinal de **reuso** de
    um refresh token que não deveria mais circular (ex.: foi roubado e tanto
    o dono legítimo quanto o atacante tentaram usá-lo) — nesse caso,
    revogamos toda a sessão do usuário por segurança, não só o token
    recebido.
    """
    token_hash = _hash(token_bruto)
    try:
        registro = RefreshToken.objects.select_related('usuario').get(token_hash=token_hash)
    except RefreshToken.DoesNotExist:
        raise RefreshTokenInvalido('Refresh token desconhecido.')

    if registro.revogado_em is not None:
        RefreshToken.objects.filter(
            usuario=registro.usuario,
            revogado_em__isnull=True,
        ).update(revogado_em=timezone.now())
        raise RefreshTokenInvalido('Refresh token já utilizado; sessão revogada por segurança.')

    if registro.expira_em < timezone.now():
        raise RefreshTokenInvalido('Refresh token expirado.')

    registro.revogado_em = timezone.now()
    registro.save(update_fields=['revogado_em'])

    novo_token_bruto, nova_expiracao = gerar_refresh_token(registro.usuario)
    return novo_token_bruto, nova_expiracao, registro.usuario


def revogar_refresh_token(token_bruto: str) -> None:
    """Usado no logout: invalida o refresh token recebido para que ele não
    possa mais ser usado para obter novos access tokens."""
    RefreshToken.objects.filter(
        token_hash=_hash(token_bruto),
        revogado_em__isnull=True,
    ).update(revogado_em=timezone.now())
