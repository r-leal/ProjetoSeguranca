import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'client02';

  constructor(private authService: AuthService) {}

  // Esconder a aba aqui é só UX: mesmo vindo já validado pelo backend (ver
  // AuthService.usuarioLogado()), nada impede alguém de reabilitar a aba
  // via DevTools e tentar chamar a rota de qualquer forma — não é controle
  // de acesso por si só. Quem garante isso de verdade é o backend — GET
  // /api/usuarios exige @papel_required(Usuario.PAPEL_ADMIN), não só estar
  // logado. Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md
  // (seção 3); para a falha original (sem checagem nenhuma no backend), ver
  // Documentação/Projeto01/Vulnerabilidades.md.
  get mostrarAbaUsuarios(): boolean {
    return this.authService.usuarioLogado()?.papel === 'admin';
  }
}
