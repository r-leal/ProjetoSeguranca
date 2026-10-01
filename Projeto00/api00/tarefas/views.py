import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

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


@csrf_exempt
@require_http_methods(['GET'])
def listar_tarefas_por_usuario(request, usuario_id):
    tarefas = Tarefa.objects.filter(usuario_id=usuario_id)
    return JsonResponse([tarefa_para_json(t) for t in tarefas], safe=False)


@csrf_exempt
@require_http_methods(['POST'])
def criar_tarefa(request):
    dados = json.loads(request.body or '{}')

    tarefa = Tarefa.objects.create(
        usuario_id=dados.get('usuario_id'),
        nome=dados.get('nome', ''),
        descricao=dados.get('descricao', ''),
        data_prazo=dados.get('data_prazo') or None,
        estado=dados.get('estado', Tarefa.ESPERANDO),
    )

    return JsonResponse(tarefa_para_json(tarefa), status=201)


@csrf_exempt
@require_http_methods(['PUT', 'DELETE'])
def tarefa_detalhe(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, id=tarefa_id)

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
