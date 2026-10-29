import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from urllib.parse import urlsplit

from usuarios.decorators import jwt_required

from .link_preview import LinkPreviewError, buscar_preview_link
from .models import Tarefa


def tarefa_para_json(tarefa):
    return {
        'id': tarefa.id,
        'usuario_id': tarefa.usuario_id,
        'nome': tarefa.nome,
        'descricao': tarefa.descricao,
        'data_prazo': tarefa.data_prazo,
        'estado': tarefa.estado,
        'url': tarefa.url,
        'url_titulo': tarefa.url_titulo,
    }


def _resolver_url_titulo(url):
    """Busca o título da URL no próprio backend (ver tarefas/link_preview.py
    para as defesas contra SSRF) — o título exibido nunca vem do que o
    cliente informou, só do que o servidor efetivamente buscou.

    Se o esquema não for http/https, a URL nem é persistida (não só a busca
    é recusada): do contrário, uma URL `javascript:`/`file:` rejeitada pelo
    fetch ainda acabaria salva "crua" no banco só por ter falhado a busca.
    Para falhas depois dessa checagem de formato (host bloqueado, timeout,
    DNS), a URL é salva sem título — o link em si continua válido para o
    usuário visitar, só não deu para buscar o título."""
    if not url:
        return None, None

    partes = urlsplit(url)
    if partes.scheme not in ('http', 'https') or not partes.hostname:
        return None, None

    try:
        preview = buscar_preview_link(url)
    except LinkPreviewError:
        return url, None
    return preview['url'], preview['titulo']


@require_http_methods(['POST'])
@jwt_required
def preview_link(request):
    """Preview isolado, chamado pelo frontend ao colar uma URL no formulário
    (feedback imediato, antes de salvar a tarefa) — usa a mesma busca
    protegida contra SSRF de `_resolver_url_titulo`."""
    dados = json.loads(request.body or '{}')
    url = (dados.get('url') or '').strip()
    if not url:
        return JsonResponse({'erro': 'URL obrigatória.'}, status=400)

    try:
        preview = buscar_preview_link(url)
    except LinkPreviewError as erro:
        return JsonResponse({'erro': str(erro)}, status=422)

    return JsonResponse(preview)


@require_http_methods(['GET'])
@jwt_required
def listar_tarefas_por_usuario(request, usuario_id):
    # Correção de IDOR (Projeto00/Vulnerabilidades item 3): o id da URL não é
    # mais confiável por si só — precisa bater com o id do usuário autenticado
    # no JWT. Sem isso, qualquer pessoa logada conseguia ler as tarefas de
    # qualquer outro usuário só trocando o número na URL.
    if request.usuario['id'] != usuario_id:
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)

    # Correção de SQL Injection (era vulnerabilidade proposital do Projeto01:
    # o filtro por nome concatenava o valor digitado direto na query SQL, sem
    # parametrização — um valor como ' OR '1'='1' -- quebrava a condição de
    # usuario_id e retornava as tarefas de todos os usuários). O ORM do
    # Django sempre parametriza os valores de filter()/icontains(), então o
    # termo digitado nunca é interpretado como SQL, só como dado. Ver
    # Documentação/Projeto01/Vulnerabilidades.md (para a falha original).
    nome_filtro = request.GET.get('nome')

    tarefas = Tarefa.objects.filter(usuario_id=usuario_id)
    if nome_filtro is not None:
        tarefas = tarefas.filter(nome__icontains=nome_filtro)

    return JsonResponse([tarefa_para_json(t) for t in tarefas], safe=False)


@require_http_methods(['POST'])
@jwt_required
def criar_tarefa(request):
    dados = json.loads(request.body or '{}')

    # Correção de IDOR (Projeto00/Vulnerabilidades item 8): o usuario_id vem
    # do token, não do corpo da requisição — do contrário, qualquer pessoa
    # logada poderia criar tarefas em nome de outro usuário só informando o
    # id dele no JSON.
    url, url_titulo = _resolver_url_titulo((dados.get('url') or '').strip())
    tarefa = Tarefa.objects.create(
        usuario_id=request.usuario['id'],
        nome=dados.get('nome', ''),
        descricao=dados.get('descricao', ''),
        data_prazo=dados.get('data_prazo') or None,
        estado=dados.get('estado', Tarefa.ESPERANDO),
        url=url,
        url_titulo=url_titulo,
    )

    return JsonResponse(tarefa_para_json(tarefa), status=201)


@require_http_methods(['PUT', 'DELETE'])
@jwt_required
def tarefa_detalhe(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)

    # Correção de IDOR (Projeto00/Vulnerabilidades item 3): confirma que a
    # tarefa pertence ao usuário autenticado antes de editar/apagar. Devolve
    # 404 (em vez de 403) para não revelar a outros usuários que o id existe.
    if tarefa.usuario_id != request.usuario['id']:
        return JsonResponse({'erro': 'Tarefa não encontrada.'}, status=404)

    if request.method == 'DELETE':
        tarefa.delete()
        return JsonResponse({}, status=204)

    dados = json.loads(request.body or '{}')
    tarefa.nome = dados.get('nome', tarefa.nome)
    tarefa.descricao = dados.get('descricao', tarefa.descricao)
    tarefa.data_prazo = dados.get('data_prazo', tarefa.data_prazo)
    tarefa.estado = dados.get('estado', tarefa.estado)

    nova_url = (dados.get('url') or '').strip()
    if 'url' in dados and nova_url != (tarefa.url or ''):
        # Só busca de novo se a URL realmente mudou — evita refazer a
        # requisição de preview em toda movimentação de card no Kanban.
        tarefa.url, tarefa.url_titulo = _resolver_url_titulo(nova_url)

    tarefa.save()

    return JsonResponse(tarefa_para_json(tarefa))
