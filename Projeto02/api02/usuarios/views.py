import json

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .decorators import jwt_required, papel_required
from .jwt_utils import gerar_token
from .models import Usuario
from .refresh_utils import (
    RefreshTokenInvalido,
    gerar_refresh_token,
    revogar_refresh_token,
    rotacionar_refresh_token,
)


def usuario_para_json(usuario):
    return {
        'id': usuario.id,
        'nome': usuario.nome,
        'sobrenome': usuario.sobrenome,
        'data_nascimento': usuario.data_nascimento,
        'email': usuario.email,
        'papel': usuario.papel,
    }


def _definir_cookie_refresh(resposta, token_bruto, expira_em):
    resposta.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        token_bruto,
        expires=expira_em,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        # Restringe o cookie às rotas da API — o refresh token não precisa
        # (e não deve) ser enviado em nenhuma outra rota.
        path='/api',
    )


def _limpar_cookie_refresh(resposta):
    resposta.delete_cookie(settings.REFRESH_COOKIE_NAME, path='/api')


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
    #
    # Senha com hash seguro (PBKDF2 + salt, via make_password) — substitui o
    # MD5 sem salt do Projeto01. Ver
    # Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 6.1).
    usuario = Usuario.objects.create(
        nome=dados.get('nome', ''),
        sobrenome=dados.get('sobrenome', ''),
        data_nascimento=dados.get('data_nascimento') or None,
        email=dados.get('email', ''),
        senha=make_password(dados.get('senha', '')),
        papel=Usuario.PAPEL_USUARIO,
    )

    return JsonResponse(usuario_para_json(usuario), status=201)


@jwt_required
@papel_required(Usuario.PAPEL_ADMIN)
def listar_usuarios(request):
    # Correção de Broken Access Control (era vulnerabilidade proposital do
    # Projeto01: @jwt_required só confirmava "está logado", nunca o papel).
    # Agora @papel_required repete no backend a mesma regra que a UI usa só
    # para decidir se mostra a aba "Usuários" — esconder o botão nunca foi
    # controle de acesso de verdade. Ver
    # Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 3) e
    # Documentação/Projeto01/Vulnerabilidades.md (para a falha original).
    termo = request.GET.get('q', '')
    usuarios = Usuario.objects.all()
    if termo:
        usuarios = usuarios.filter(
            Q(nome__icontains=termo) | Q(sobrenome__icontains=termo) | Q(email__icontains=termo)
        )
    return JsonResponse([usuario_para_json(u) for u in usuarios.order_by('id')], safe=False)


@csrf_exempt
@ensure_csrf_cookie
@require_http_methods(['POST'])
def login(request):
    dados = json.loads(request.body or '{}')
    email = dados.get('email', '')
    senha = dados.get('senha', '')

    # check_password compara a senha informada com o hash salvo sem nunca
    # precisar (nem conseguir) "desfazer" o hash — ver
    # Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 6.1).
    usuario = Usuario.objects.filter(email=email).first()
    if usuario is None or not check_password(senha, usuario.senha):
        return JsonResponse({'erro': 'Email ou senha inválidos.'}, status=401)

    # Access token de vida curta (claim "exp", checada em toda requisição
    # por verificar_token) + refresh token de vida mais longa, persistido no
    # backend e entregue só via cookie HttpOnly — nunca no corpo da
    # resposta. Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md
    # (seções 4, 5 e 7); contraste com a falha original em
    # Documentação/Projeto01/Ataque-A07-TokenSemExpiracao.md.
    token = gerar_token(usuario)
    refresh_bruto, refresh_expira_em = gerar_refresh_token(usuario)

    resposta = JsonResponse({'token': token})
    _definir_cookie_refresh(resposta, refresh_bruto, refresh_expira_em)
    return resposta


@ensure_csrf_cookie
@require_http_methods(['POST'])
def token_refresh(request):
    """Troca o refresh token (cookie HttpOnly) por um novo access token.

    Protegida por CSRF (não é @csrf_exempt): como a credencial de entrada é
    um cookie que o browser manda automaticamente, um site de terceiros
    poderia tentar forjar essa chamada — o header X-XSRF-TOKEN, exigido pelo
    CsrfViewMiddleware, só um script rodando no nosso próprio frontend
    consegue montar. Ver
    Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 7.3)."""
    refresh_bruto = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_bruto:
        return JsonResponse({'erro': 'Refresh token ausente.'}, status=401)

    try:
        novo_refresh_bruto, nova_expiracao, usuario = rotacionar_refresh_token(refresh_bruto)
    except RefreshTokenInvalido as erro:
        resposta = JsonResponse({'erro': str(erro)}, status=401)
        _limpar_cookie_refresh(resposta)
        return resposta

    token = gerar_token(usuario)
    resposta = JsonResponse({'token': token})
    _definir_cookie_refresh(resposta, novo_refresh_bruto, nova_expiracao)
    return resposta


@require_http_methods(['POST'])
@jwt_required
def logout(request):
    """Revoga o refresh token no backend — um logout que só "esquece" o
    token no cliente não impede que ele continue sendo usado para gerar
    novos access tokens caso tenha sido copiado por alguém. Ver
    Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 5)."""
    refresh_bruto = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if refresh_bruto:
        revogar_refresh_token(refresh_bruto)

    resposta = JsonResponse({})
    _limpar_cookie_refresh(resposta)
    return resposta


@csrf_exempt
@require_http_methods(['GET'])
@jwt_required
def usuario_logado(request):
    # Correção de IDOR (análoga à de tarefas/views.py): o id vem do token
    # assinado, não de um parâmetro na URL — por isso esta rota não precisa
    # (e não deve) aceitar um id de usuário como argumento.
    usuario = get_object_or_404(Usuario, id=request.usuario['id'])
    return JsonResponse(usuario_para_json(usuario))
