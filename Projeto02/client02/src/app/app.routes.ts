import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login.component';
import { CadastroComponent } from './pages/cadastro/cadastro.component';
import { KanbanComponent } from './pages/kanban/kanban.component';
import { SobreComponent } from './pages/sobre/sobre.component';
import { UsuariosComponent } from './pages/usuarios/usuarios.component';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'cadastro', component: CadastroComponent },
  { path: 'kanban', component: KanbanComponent },
  { path: 'usuarios', component: UsuariosComponent },
  { path: 'sobre', component: SobreComponent },
  { path: '**', redirectTo: 'login' }
];
