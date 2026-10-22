import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { Router } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
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
  novaTarefa: Partial<Tarefa> = { nome: '', descricao: '', data_prazo: '' };
  usuarioId: number | null = null;
  usuarioNome = '';
  filtroNome = '';

  readonly estados: { chave: EstadoTarefa; titulo: string }[] = [
    { chave: 'esperando', titulo: 'Esperando' },
    { chave: 'em_andamento', titulo: 'Em andamento' },
    { chave: 'concluido', titulo: 'Concluído' }
  ];

  constructor(
    private taskService: TaskService,
    private authService: AuthService,
    private router: Router,
    private sanitizer: DomSanitizer
  ) {}

  // VULNERABILIDADE PROPOSITAL (Projeto00 — XSS armazenado):
  // bypassSecurityTrustHtml desliga o sanitizador do Angular para a descrição
  // da tarefa, que é entrada do usuário não validada. Ver Documentação/Projeto00/Vulnerabilidades.md.
  descricaoHtml(tarefa: Tarefa): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(tarefa.descricao);
  }

  ngOnInit(): void {
    // O id vem do payload decodificado do JWT só para montar a URL de
    // /tarefas — não é uma fonte confiável de autorização por si só (ver
    // comentário em AuthService.usuarioLogado()); quem de fato garante que
    // só o dono vê suas tarefas é a checagem feita no backend. O nome
    // exibido, porém, vem de buscarUsuarioLogado(), que é validado pelo
    // backend via jwt_required (GET /api/usuarios/me).
    const usuarioToken = this.authService.usuarioLogado();
    if (!usuarioToken || !usuarioToken.id) {
      return;
    }
    this.usuarioId = usuarioToken.id;

    this.authService.buscarUsuarioLogado().subscribe({
      next: (usuario) => (this.usuarioNome = usuario.nome),
      error: (erro) => this.tratarErroAutenticacao(erro)
    });

    this.carregarTarefas();
  }

  carregarTarefas(): void {
    if (!this.usuarioId) return;
    this.taskService.listarPorUsuario(this.usuarioId).subscribe({
      next: (tarefas) => (this.tarefas = tarefas),
      error: (erro) => this.tratarErroAutenticacao(erro)
    });
  }

  // VULNERABILIDADE PROPOSITAL (Projeto01 — SQL Injection): este filtro
  // envia o termo digitado direto para o backend, que o concatena numa query
  // SQL sem parametrização. Ex.: pesquisar por "x' OR '1'='1' -- " retorna as
  // tarefas de todos os usuários. Ver Documentação/Projeto01/Vulnerabilidades.md.
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

  criarTarefa(): void {
    if (!this.usuarioId || !this.novaTarefa.nome) return;
    const tarefa: Tarefa = {
      usuario_id: this.usuarioId,
      nome: this.novaTarefa.nome ?? '',
      descricao: this.novaTarefa.descricao ?? '',
      data_prazo: this.novaTarefa.data_prazo ?? '',
      estado: 'esperando'
    };
    this.taskService.criar(tarefa).subscribe(() => {
      this.novaTarefa = { nome: '', descricao: '', data_prazo: '' };
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
