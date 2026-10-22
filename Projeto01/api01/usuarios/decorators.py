import json
from functools import wraps

from django.http import JsonResponse

from .jwt_utils import verificar_token


def jwt_required(view_func):
    """Exige um JWT válido no header Authorization e anexa o payload
    decodificado em ``request.usuario``.

    Usado nas rotas de tarefas para corrigir o IDOR do Projeto00: a
    identidade de quem faz a requisição passa a vir do token assinado, não
    mais de um id aceito cegamente na URL ou no corpo da requisição.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'erro': 'Token de autenticação ausente.'}, status=401)

        token = auth_header[len('Bearer '):].strip()
        try:
            request.usuario = verificar_token(token)
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({'erro': 'Token inválido.'}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper
