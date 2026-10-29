import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PreviewLink, Tarefa } from '../models/tarefa';
import { API_BASE_URL } from '../api.config';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  constructor(private http: HttpClient) {}

  // A busca de fato (SSRF-safe) acontece no backend — ver
  // tarefas/link_preview.py. Usado para feedback imediato no formulário;
  // o título salvo na tarefa é sempre recalculado pelo backend no
  // criar/editar, nunca confiado a partir do que este preview devolveu.
  previewLink(url: string): Observable<PreviewLink> {
    return this.http.post<PreviewLink>(`${API_BASE_URL}/tarefas/preview-link`, { url });
  }

  listarPorUsuario(usuarioId: number): Observable<Tarefa[]> {
    return this.http.get<Tarefa[]>(`${API_BASE_URL}/usuarios/${usuarioId}/tarefas`);
  }

  // Correção de SQL Injection (era vulnerabilidade proposital do Projeto01):
  // o termo digitado aqui chega ao backend só como valor de query string; a
  // view usa Tarefa.objects.filter(nome__icontains=...) do ORM do Django, que
  // sempre parametriza o valor — nunca mais concatenado numa query SQL crua.
  // Ver Documentação/Projeto01/Vulnerabilidades.md (para a falha original).
  filtrarPorNome(usuarioId: number, nome: string): Observable<Tarefa[]> {
    const url = `${API_BASE_URL}/usuarios/${usuarioId}/tarefas?nome=${encodeURIComponent(nome)}`;
    return this.http.get<Tarefa[]>(url);
  }

  criar(tarefa: Tarefa): Observable<Tarefa> {
    return this.http.post<Tarefa>(`${API_BASE_URL}/tarefas`, tarefa);
  }

  atualizar(tarefa: Tarefa): Observable<Tarefa> {
    return this.http.put<Tarefa>(`${API_BASE_URL}/tarefas/${tarefa.id}`, tarefa);
  }

  remover(id: number): Observable<void> {
    return this.http.delete<void>(`${API_BASE_URL}/tarefas/${id}`);
  }
}
