import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Usuario


def usuario_para_json(usuario):
    return {
        'id': usuario.id,
        'nome': usuario.nome,
        'sobrenome': usuario.sobrenome,
        'data_nascimento': usuario.data_nascimento,
        'email': usuario.email,
        'senha': usuario.senha,
    }


@csrf_exempt
@require_http_methods(['POST'])
def cadastrar_usuario(request):
    dados = json.loads(request.body or '{}')

    usuario = Usuario.objects.create(
        nome=dados.get('nome', ''),
        sobrenome=dados.get('sobrenome', ''),
        data_nascimento=dados.get('data_nascimento') or None,
        email=dados.get('email', ''),
        senha=dados.get('senha', ''),
    )

    return JsonResponse(usuario_para_json(usuario), status=201)


@csrf_exempt
@require_http_methods(['POST'])
def login(request):
    dados = json.loads(request.body or '{}')
    email = dados.get('email', '')
    senha = dados.get('senha', '')

    usuario = Usuario.objects.filter(email=email, senha=senha).first()
    if usuario is None:
        return JsonResponse({'erro': 'Email ou senha inválidos.'}, status=401)

    return JsonResponse(usuario_para_json(usuario))
