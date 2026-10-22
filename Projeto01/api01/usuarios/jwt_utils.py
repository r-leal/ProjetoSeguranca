"""Projeto 01 (inseguro de propósito): implementação mínima de JWT (HS256)
usando apenas a biblioteca padrão, sem a claim "exp" — os tokens emitidos
nunca expiram. Ver Documentação/Projeto01/Vulnerabilidades.md."""

import base64
import hashlib
import hmac
import json

from django.conf import settings


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _base64url_decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def gerar_token(usuario) -> str:
    header = {'alg': 'HS256', 'typ': 'JWT'}
    payload = {
        'id': usuario.id,
        'nome': usuario.nome,
        'sobrenome': usuario.sobrenome,
        'email': usuario.email,
        'papel': usuario.papel,
    }

    header_b64 = _base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload).encode('utf-8'))
    assinatura = hmac.new(
        settings.JWT_SECRET.encode('utf-8'),
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
    """Valida a assinatura HMAC do token e devolve o payload decodificado.

    Usado nas rotas de tarefas para impedir IDOR: a identidade do usuário
    vem do token assinado, nunca de um parâmetro informado pelo cliente.
    """
    partes = token.split('.')
    if len(partes) != 3:
        raise ValueError('Token malformado.')
    header_b64, payload_b64, assinatura_b64 = partes

    assinatura_esperada = hmac.new(
        settings.JWT_SECRET.encode('utf-8'),
        f'{header_b64}.{payload_b64}'.encode('utf-8'),
        hashlib.sha256,
    ).digest()
    assinatura_recebida = _base64url_decode(assinatura_b64)

    if not hmac.compare_digest(assinatura_esperada, assinatura_recebida):
        raise ValueError('Assinatura do token inválida.')

    return json.loads(_base64url_decode(payload_b64))
