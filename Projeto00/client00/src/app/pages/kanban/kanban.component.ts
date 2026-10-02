import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
    const usuario = this.authService.usuarioLogado();
    if (!usuario || !usuario.id) {
      return;
    }
    this.usuarioId = usuario.id;
    this.carregarTarefas();
  }

  carregarTarefas(): void {
    if (!this.usuarioId) return;
    this.taskService.listarPorUsuario(this.usuarioId).subscribe((tarefas) => {
      this.tarefas = tarefas;
    });
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
}
