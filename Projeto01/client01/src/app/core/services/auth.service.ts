import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Usuario, UsuarioToken } from '../models/usuario';
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../api.config';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  constructor(private http: HttpClient) {}

  login(email: string, senha: string): Observable<{ token: string }> {
    return this.http
      .post<{ token: string }>(`${API_BASE_URL}/login`, { email, senha })
      .pipe(tap((resposta) => this.salvarToken(resposta.token)));
  }

  cadastrar(usuario: Usuario): Observable<Usuario> {
    return this.http.post<Usuario>(`${API_BASE_URL}/usuarios`, usuario);
  }

  // Busca os dados do usuário logado no backend (GET /api/usuarios/me),
  // protegido por jwt_required — a assinatura do token é verificada no
  // servidor antes de devolver qualquer dado, diferente de usuarioLogado()
  // abaixo, que só decodifica o payload sem checar nada.
  buscarUsuarioLogado(): Observable<Usuario> {
    return this.http.get<Usuario>(`${API_BASE_URL}/usuarios/me`);
  }

  logout(): void {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }

  getToken(): string | null {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  }

  // VULNERABILIDADE PROPOSITAL (Projeto01 — token nunca expira e payload não
  // verificado): o payload do JWT é apenas decodificado em base64 no
  // cliente, sem checar assinatura nem expiração — usar só para dados de
  // exibição não sensíveis (ex.: montar a URL de /tarefas). Para dados que
  // importam de verdade, usar buscarUsuarioLogado(), que é validado no
  // backend. Ver Documentação/Projeto01/Vulnerabilidades.md.
  usuarioLogado(): UsuarioToken | null {
    const token = this.getToken();
    if (!token) return null;

    try {
      const payloadBase64 = token.split('.')[1];
      const json = atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(json);
    } catch {
      return null;
    }
  }

  private salvarToken(token: string): void {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  }
}
