import json

from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from usuarios.decorators import jwt_required

from .models import Tarefa


def tarefa_para_json(tarefa):
    return {
        'id': tarefa.id,
        'usuario_id': tarefa.usuario_id,
        'nome': tarefa.nome,
        'descricao': tarefa.descricao,
        'data_prazo': tarefa.data_prazo,
        'estado': tarefa.estado,
    }


def _linha_para_json(linha):
    return {
        'id': linha[0],
        'usuario_id': linha[1],
        'nome': linha[2],
        'descricao': linha[3],
        'data_prazo': linha[4],
        'estado': linha[5],
    }


@csrf_exempt
@require_http_methods(['GET'])
@jwt_required
def listar_tarefas_por_usuario(request, usuario_id):
    # Correção de IDOR (Projeto00/Vulnerabilidades item 3): o id da URL não é
    # mais confiável por si só — precisa bater com o id do usuário autenticado
    # no JWT. Sem isso, qualquer pessoa logada conseguia ler as tarefas de
    # qualquer outro usuário só trocando o número na URL.
    if request.usuario['id'] != usuario_id:
        return JsonResponse({'erro': 'Acesso negado.'}, status=403)

    nome_filtro = request.GET.get('nome')

    if nome_filtro is None:
        tarefas = Tarefa.objects.filter(usuario_id=usuario_id)
        return JsonResponse([tarefa_para_json(t) for t in tarefas], safe=False)

    # VULNERABILIDADE PROPOSITAL (Projeto01 — SQL Injection):
    # o filtro por nome da aba de busca do Kanban é concatenado diretamente
    # na consulta SQL, sem parametrização. Um valor como
    # ' OR '1'='1' -- quebra a condição de usuario_id e retorna as tarefas
    # de todos os usuários. Ver Documentação/Projeto01/Vulnerabilidades.md.
    query = (
        "SELECT id, usuario_id, nome, descricao, data_prazo, estado "
        "FROM tarefas_tarefa "
        f"WHERE usuario_id = {usuario_id} AND nome LIKE '%{nome_filtro}%'"
    )
    with connection.cursor() as cursor:
        cursor.execute(query)
        linhas = cursor.fetchall()

    return JsonResponse([_linha_para_json(linha) for linha in linhas], safe=False)


@csrf_exempt
@require_http_methods(['POST'])
@jwt_required
def criar_tarefa(request):
    dados = json.loads(request.body or '{}')

    # Correção de IDOR (Projeto00/Vulnerabilidades item 8): o usuario_id vem
    # do token, não do corpo da requisição — do contrário, qualquer pessoa
    # logada poderia criar tarefas em nome de outro usuário só informando o
    # id dele no JSON.
    tarefa = Tarefa.objects.create(
        usuario_id=request.usuario['id'],
        nome=dados.get('nome', ''),
        descricao=dados.get('descricao', ''),
        data_prazo=dados.get('data_prazo') or None,
        estado=dados.get('estado', Tarefa.ESPERANDO),
    )

    return JsonResponse(tarefa_para_json(tarefa), status=201)


@csrf_exempt
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
    tarefa.save()

    return JsonResponse(tarefa_para_json(tarefa))
