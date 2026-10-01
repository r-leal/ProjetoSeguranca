import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Tarefa } from '../models/tarefa';
import { API_BASE_URL } from '../api.config';

@Injectable({
  providedIn: 'root'
})
export class TaskService {
  constructor(private http: HttpClient) {}

  listarPorUsuario(usuarioId: number): Observable<Tarefa[]> {
    return this.http.get<Tarefa[]>(`${API_BASE_URL}/usuarios/${usuarioId}/tarefas`);
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
