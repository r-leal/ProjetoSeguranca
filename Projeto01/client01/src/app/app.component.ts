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
  title = 'client01';

  constructor(private authService: AuthService) {}

  // VULNERABILIDADE PROPOSITAL (Projeto01 — Broken Access Control): esta aba
  // só é escondida aqui na UI, decidido com base no papel decodificado do
  // próprio JWT (sem verificação de assinatura no cliente) — não existe
  // nenhum guard de rota, e o backend (GET /api/usuarios) também não confere
  // papel, só exige estar logado. Ver Documentação/Projeto01/Vulnerabilidades.md.
  get mostrarAbaUsuarios(): boolean {
    return this.authService.usuarioLogado()?.papel === 'admin';
  }
}
