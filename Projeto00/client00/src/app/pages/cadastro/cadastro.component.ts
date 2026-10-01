import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { Usuario } from '../../core/models/usuario';

@Component({
  selector: 'app-cadastro',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './cadastro.component.html',
  styleUrl: './cadastro.component.css'
})
export class CadastroComponent {
  usuario: Usuario = {
    nome: '',
    sobrenome: '',
    data_nascimento: '',
    email: '',
    senha: ''
  };
  erro = '';

  constructor(private authService: AuthService, private router: Router) {}

  cadastrar(): void {
    this.erro = '';
    this.authService.cadastrar(this.usuario).subscribe({
      next: () => this.router.navigate(['/login']),
      error: () => (this.erro = 'Não foi possível criar o usuário.')
    });
  }
}
