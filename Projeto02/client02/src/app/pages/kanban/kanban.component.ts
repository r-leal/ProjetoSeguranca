import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { TaskService } from '../../core/services/task.service';
import { AuthService } from '../../core/services/auth.service';
import { EstadoTarefa, Tarefa } from '../../core/models/tarefa';

@Component({
  selector: 'app-kanban',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './kanban.component.html',
  styleUrl: './kanban.component.css'
})
export class KanbanComponent implements OnInit {
  tarefas: Tarefa[] = [];
  novaTarefa: Partial<Tarefa> = { nome: '', descricao: '', data_prazo: '', url: '' };
  usuarioId: number | null = null;
  usuarioNome = '';
  filtroNome = '';
  previewCarregando = false;
  previewErro = '';

  readonly estados: { chave: EstadoTarefa; titulo: string }[] = [
    { chave: 'esperando', titulo: 'Esperando' },
    { chave: 'em_andamento', titulo: 'Em andamento' },
    { chave: 'concluido', titulo: 'Concluído' }
  ];

  constructor(
    private taskService: TaskService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // usuarioLogado() já vem validado pelo backend (login, refresh de
    // sessão ou GET /api/usuarios/me) — diferente da versão anterior, não é
    // mais um payload de JWT decodificado sem checagem no cliente, porque o
    // access token não é mais legível por JavaScript. Mesmo assim, quem de
    // fato garante que só o dono vê/edita suas tarefas é a checagem feita
    // no backend, nunca este id usado só para montar a URL de /tarefas.
    const usuario = this.authService.usuarioLogado();
    if (!usuario || !usuario.id) {
      return;
    }
    this.usuarioId = usuario.id;
    this.usuarioNome = usuario.nome;

    this.carregarTarefas();
  }

  carregarTarefas(): void {
    if (!this.usuarioId) return;
    this.taskService.listarPorUsuario(this.usuarioId).subscribe({
      next: (tarefas) => (this.tarefas = tarefas),
      error: (erro) => this.tratarErroAutenticacao(erro)
    });
  }

  filtrarTarefas(): void {
    if (!this.usuarioId) return;

    if (!this.filtroNome.trim()) {
      this.carregarTarefas();
      return;
    }

    this.taskService.filtrarPorNome(this.usuarioId, this.filtroNome).subscribe({
      next: (tarefas) => (this.tarefas = tarefas),
      error: (erro) => this.tratarErroAutenticacao(erro)
    });
  }

  limparFiltro(): void {
    this.filtroNome = '';
    this.carregarTarefas();
  }

  tarefasPorEstado(estado: EstadoTarefa): Tarefa[] {
    return this.tarefas.filter((t) => t.estado === estado);
  }

  // Preview só para feedback imediato no formulário — a busca real
  // (SSRF-safe) e o título salvo de verdade vêm sempre do backend no
  // momento de criar/editar a tarefa (tarefas/link_preview.py), nunca do
  // que este preview devolveu aqui no cliente.
  previsualizarLink(): void {
    const url = (this.novaTarefa.url ?? '').trim();
    this.previewErro = '';
    if (!url) return;

    this.previewCarregando = true;
    this.taskService.previewLink(url).subscribe({
      next: (preview) => {
        this.previewCarregando = false;
        this.novaTarefa.url_titulo = preview.titulo;
      },
      error: () => {
        this.previewCarregando = false;
        this.novaTarefa.url_titulo = null;
        this.previewErro = 'Não foi possível pré-visualizar este link.';
      }
    });
  }

  criarTarefa(): void {
    if (!this.usuarioId || !this.novaTarefa.nome) return;
    const tarefa: Tarefa = {
      usuario_id: this.usuarioId,
      nome: this.novaTarefa.nome ?? '',
      descricao: this.novaTarefa.descricao ?? '',
      data_prazo: this.novaTarefa.data_prazo ?? '',
      estado: 'esperando',
      url: this.novaTarefa.url ?? ''
    };
    this.taskService.criar(tarefa).subscribe(() => {
      this.novaTarefa = { nome: '', descricao: '', data_prazo: '', url: '' };
      this.previewErro = '';
      this.carregarTarefas();
    });
  }

  moverTarefa(tarefa: Tarefa, novoEstado: EstadoTarefa): void {
    const atualizada = { ...tarefa, estado: novoEstado };
    this.taskService.atualizar(atualizada).subscribe(() => this.carregarTarefas());
  }

  removerTarefa(tarefa: Tarefa): void {
    if (!tarefa.id) return;
    this.taskService.remover(tarefa.id).subscribe(() => this.carregarTarefas());
  }

  sair(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  private tratarErroAutenticacao(erro: HttpErrorResponse): void {
    if (erro.status === 401) {
      this.sair();
    }
  }
}
