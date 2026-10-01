import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Usuario } from '../models/usuario';
import { API_BASE_URL } from '../api.config';

const SESSION_KEY = 'usuario_logado';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  constructor(private http: HttpClient) {}

  login(email: string, senha: string): Observable<Usuario> {
    return this.http
      .post<Usuario>(`${API_BASE_URL}/login`, { email, senha })
      .pipe(tap((usuario) => this.salvarSessao(usuario)));
  }

  cadastrar(usuario: Usuario): Observable<Usuario> {
    return this.http.post<Usuario>(`${API_BASE_URL}/usuarios`, usuario);
  }

  logout(): void {
    localStorage.removeItem(SESSION_KEY);
  }

  usuarioLogado(): Usuario | null {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  private salvarSessao(usuario: Usuario): void {
    localStorage.setItem(SESSION_KEY, JSON.stringify(usuario));
  }
}
