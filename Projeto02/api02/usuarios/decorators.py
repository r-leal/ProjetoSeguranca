import json
from functools import wraps

from django.conf import settings
from django.http import JsonResponse

from .jwt_utils import verificar_token


def jwt_required(view_func):
    """Exige um JWT válido no cookie HttpOnly de access token (enviado
    automaticamente pelo navegador) e anexa o payload decodificado em
    ``request.usuario``.

    O access token não passa mais pelo corpo da resposta nem é lido por
    JavaScript no frontend — fica só no cookie, fora do alcance de um XSS
    que tente roubá-lo via ``document.cookie`` ou interceptando a resposta
    de rede. Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md
    (seção 7).

    Usado nas rotas de tarefas para corrigir o IDOR do Projeto00: a
    identidade de quem faz a requisição passa a vir do token assinado, não
    mais de um id aceito cegamente na URL ou no corpo da requisição.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = request.COOKIES.get(settings.ACCESS_COOKIE_NAME)
        if not token:
            return JsonResponse({'erro': 'Token de autenticação ausente.'}, status=401)

        try:
            request.usuario = verificar_token(token)
        except (ValueError, json.JSONDecodeError):
            return JsonResponse({'erro': 'Token inválido.'}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper


def papel_required(*papeis_permitidos):
    """Exige que o usuário autenticado tenha um dos papéis informados.

    Resolve autorização (o que o usuário pode fazer), não autenticação (quem
    ele é) — por isso depende de ``request.usuario`` já ter sido preenchido
    por ``jwt_required``. Use sempre nessa ordem, com ``jwt_required`` por
    cima:

        @jwt_required
        @papel_required(Usuario.PAPEL_ADMIN)
        def minha_view(request): ...

    Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 3) e,
    para contraste, a falha original (rota de admin que só exigia estar
    logado, sem checar papel) em
    Documentação/Projeto01/Vulnerabilidades.md.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            usuario = getattr(request, 'usuario', None)
            if usuario is None or usuario.get('papel') not in papeis_permitidos:
                return JsonResponse({'erro': 'Acesso negado para este papel.'}, status=403)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
