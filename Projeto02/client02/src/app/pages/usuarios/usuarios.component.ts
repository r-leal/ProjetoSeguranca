import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService } from '../../core/services/admin.service';
import { Usuario } from '../../core/models/usuario';

@Component({
  selector: 'app-usuarios',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './usuarios.component.html',
  styleUrl: './usuarios.component.css'
})
export class UsuariosComponent implements OnInit {
  usuarios: Usuario[] = [];
  filtro = '';

  constructor(private adminService: AdminService) {}

  ngOnInit(): void {
    this.carregar();
  }

  carregar(): void {
    this.adminService.listarUsuarios(this.filtro).subscribe((usuarios) => {
      this.usuarios = usuarios;
    });
  }

  filtrar(): void {
    this.carregar();
  }

  limparFiltro(): void {
    this.filtro = '';
    this.carregar();
  }
}
