"""Projeto 02: implementação mínima de JWT (HS256) usando apenas a
biblioteca padrão, agora com claim "exp" validada no backend a cada
requisição.

Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seções 2 e 4) e,
para contraste, a falha original em
Documentação/Projeto01/Ataque-A07-TokenSemExpiracao.md."""

import base64
import hashlib
import hmac
import json
import time

from django.conf import settings


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _base64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def gerar_token(usuario, ttl_segundos: int | None = None) -> str:
    """Gera um access token de vida curta (padrão:
    ``settings.ACCESS_TOKEN_TTL_SEGUNDOS``). O payload leva só o necessário
    para identificar e autorizar o usuário — nunca dados sensíveis, já que
    o payload de um JWT é apenas Base64, não é criptografado."""
    ttl = ttl_segundos if ttl_segundos is not None else settings.ACCESS_TOKEN_TTL_SEGUNDOS
    agora = int(time.time())

    header = {'alg': 'HS256', 'typ': 'JWT'}
    payload = {
        'id': usuario.id,
        'nome': usuario.nome,
        'sobrenome': usuario.sobrenome,
        'email': usuario.email,
        'papel': usuario.papel,
        'iat': agora,
        'exp': agora + ttl,
    }

    header_b64 = _base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload).encode('utf-8'))
    assinatura = hmac.new(
        settings.JWT_SECRET_KEY.encode('utf-8'),
        f'{header_b64}.{payload_b64}'.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    assinatura_b64 = _base64url_encode(assinatura)

    return f'{header_b64}.{payload_b64}.{assinatura_b64}'


def decodificar_payload(token: str) -> dict:
    partes = token.split('.')
    if len(partes) != 3:
        raise ValueError('Token malformado.')
    return json.loads(_base64url_decode(partes[1]))


def verificar_token(token: str) -> dict:
    """Valida a assinatura HMAC do token, confirma que não está expirado e
    devolve o payload decodificado.

    Usado nas rotas de tarefas para impedir IDOR: a identidade do usuário
    vem do token assinado, nunca de um parâmetro informado pelo cliente.
    As duas checagens abaixo (assinatura e expiração) têm que acontecer
    aqui, no backend, a cada requisição — nunca basta confiar que o
    frontend vai descartar um token expirado por conta própria.
    """
    partes = token.split('.')
    if len(partes) != 3:
        raise ValueError('Token malformado.')
    header_b64, payload_b64, assinatura_b64 = partes

    assinatura_esperada = hmac.new(
        settings.JWT_SECRET_KEY.encode('utf-8'),
        f'{header_b64}.{payload_b64}'.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    assinatura_recebida = _base64url_decode(assinatura_b64)

    if not hmac.compare_digest(assinatura_esperada, assinatura_recebida):
        raise ValueError('Assinatura do token inválida.')

    payload = json.loads(_base64url_decode(payload_b64))

    exp = payload.get('exp')
    if exp is None:
        raise ValueError('Token sem expiração.')
    if time.time() > exp:
        raise ValueError('Token expirado.')

    return payload
