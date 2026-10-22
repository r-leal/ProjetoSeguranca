import hashlib
import json

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .decorators import jwt_required
from .jwt_utils import gerar_token
from .models import Usuario


def hash_md5(texto: str) -> str:
    """Projeto 01 (inseguro de propósito): MD5 sem salt para armazenar senhas."""
    return hashlib.md5(texto.encode('utf-8')).hexdigest()


def usuario_para_json(usuario):
    return {
        'id': usuario.id,
        'nome': usuario.nome,
        'sobrenome': usuario.sobrenome,
        'data_nascimento': usuario.data_nascimento,
        'email': usuario.email,
        'papel': usuario.papel,
    }


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def usuarios_collection(request):
    if request.method == 'POST':
        return cadastrar_usuario(request)
    return listar_usuarios(request)


def cadastrar_usuario(request):
    dados = json.loads(request.body or '{}')

    # Correção de escalonamento de privilégio (ver Documentação/Projeto01/Melhorias.md):
    # todo cadastro público nasce com o papel mínimo, nunca com um valor vindo
    # do corpo da requisição.
    usuario = Usuario.objects.create(
        nome=dados.get('nome', ''),
        sobrenome=dados.get('sobrenome', ''),
        data_nascimento=dados.get('data_nascimento') or None,
        email=dados.get('email', ''),
        senha=hash_md5(dados.get('senha', '')),
        papel=Usuario.PAPEL_USUARIO,
    )

    return JsonResponse(usuario_para_json(usuario), status=201)


@jwt_required
def listar_usuarios(request):
    # VULNERABILIDADE PROPOSITAL (Projeto01 — Broken Access Control): esta rota
    # é destinada à aba "Usuários", visível só para quem está logado como
    # admin no frontend — mas aqui, no backend, @jwt_required só confere que
    # existe um JWT válido, nunca que request.usuario['papel'] == 'admin'.
    # Qualquer usuário autenticado (papel "usuario" inclusive) que chame esta
    # rota diretamente lê a lista completa de usuários do sistema.
    # Ver Documentação/Projeto01/Vulnerabilidades.md.
    termo = request.GET.get('q', '')
    usuarios = Usuario.objects.all()
    if termo:
        usuarios = usuarios.filter(
            Q(nome__icontains=termo) | Q(sobrenome__icontains=termo) | Q(email__icontains=termo)
        )
    return JsonResponse([usuario_para_json(u) for u in usuarios.order_by('id')], safe=False)


@csrf_exempt
@require_http_methods(['POST'])
def login(request):
    dados = json.loads(request.body or '{}')
    email = dados.get('email', '')
    senha = dados.get('senha', '')

    usuario = Usuario.objects.filter(email=email, senha=hash_md5(senha)).first()
    if usuario is None:
        return JsonResponse({'erro': 'Email ou senha inválidos.'}, status=401)

    # VULNERABILIDADE PROPOSITAL (Projeto01 — token sem expiração):
    # o JWT gerado aqui não possui claim "exp" e o backend nunca o invalida,
    # então, uma vez emitido, o token continua válido para sempre.
    token = gerar_token(usuario)

    return JsonResponse({'token': token})


@csrf_exempt
@require_http_methods(['GET'])
@jwt_required
def usuario_logado(request):
    # Correção de IDOR (análoga à de tarefas/views.py): o id vem do token
    # assinado, não de um parâmetro na URL — por isso esta rota não precisa
    # (e não deve) aceitar um id de usuário como argumento.
    usuario = get_object_or_404(Usuario, id=request.usuario['id'])
    return JsonResponse(usuario_para_json(usuario))
