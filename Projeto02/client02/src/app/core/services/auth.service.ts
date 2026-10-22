import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';
import { Usuario, UsuarioToken } from '../models/usuario';
import { API_BASE_URL } from '../api.config';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  // Access token de vida curta, guardado só em memória — nunca em
  // localStorage/sessionStorage. Isso reduz a janela de exposição caso um
  // XSS consiga rodar JavaScript na página: um script injetado não acha
  // nada persistido para roubar. O refresh token, de vida mais longa, fica
  // num cookie HttpOnly setado pelo backend — este serviço nunca tem
  // acesso a ele via JS, só o browser, que o envia automaticamente.
  // Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 7).
  private accessToken: string | null = null;
  private usuarioAtual: UsuarioToken | null = null;

  constructor(private http: HttpClient) {}

  login(email: string, senha: string): Observable<{ token: string }> {
    return this.http
      .post<{ token: string }>(`${API_BASE_URL}/login`, { email, senha })
      .pipe(tap((resposta) => this.definirAccessToken(resposta.token)));
  }

  cadastrar(usuario: Usuario): Observable<Usuario> {
    return this.http.post<Usuario>(`${API_BASE_URL}/usuarios`, usuario);
  }

  // Busca os dados do usuário logado no backend (GET /api/usuarios/me),
  // protegido por jwt_required — a assinatura e a expiração do token são
  // verificadas no servidor antes de devolver qualquer dado, diferente de
  // usuarioLogado() abaixo, que só decodifica o payload sem checar nada.
  buscarUsuarioLogado(): Observable<Usuario> {
    return this.http.get<Usuario>(`${API_BASE_URL}/usuarios/me`);
  }

  // Chamado uma única vez, na inicialização do app (ver APP_INITIALIZER em
  // app.config.ts): tenta usar o refresh token (cookie HttpOnly, enviado
  // automaticamente pelo browser) para obter um access token novo sem
  // exigir login de novo. É o que mantém a sessão viva depois de um reload
  // de página — o access token em memória se perde nesse momento, mas o
  // cookie continua lá.
  restaurarSessao(): Observable<string> {
    return this.refrescarToken();
  }

  // Também usado pelo interceptor quando um request volta 401 por access
  // token expirado: pede um access token novo ao backend, que valida o
  // refresh token recebido e o ROTACIONA (emite um substituto e invalida o
  // antigo). Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md
  // (seção 5).
  refrescarToken(): Observable<string> {
    return this.http.post<{ token: string }>(`${API_BASE_URL}/token/refresh`, {}).pipe(
      tap((resposta) => this.definirAccessToken(resposta.token)),
      map((resposta) => resposta.token)
    );
  }

  logout(): void {
    // Revoga o refresh token no backend — um logout que só "esquecesse" o
    // token aqui no cliente não impediria que ele continuasse sendo usado
    // para gerar novos access tokens. O access token em memória é limpo
    // independentemente da resposta do servidor, para nunca deixar o app
    // achando que ainda está logado.
    this.http.post(`${API_BASE_URL}/logout`, {}).subscribe({ error: () => undefined });
    this.accessToken = null;
    this.usuarioAtual = null;
  }

  getToken(): string | null {
    return this.accessToken;
  }

  // VALIDADO SÓ PARA EXIBIÇÃO (nome no cabeçalho, esconder a aba de admin
  // na UI): o payload do JWT é apenas decodificado em base64, sem checar
  // assinatura nem expiração no cliente — essa validação é sempre feita de
  // novo no backend (ver papel_required em usuarios/decorators.py). Nunca
  // usar o papel devolvido aqui para decidir se uma ação é permitida.
  usuarioLogado(): UsuarioToken | null {
    return this.usuarioAtual;
  }

  private definirAccessToken(token: string): void {
    this.accessToken = token;
    this.usuarioAtual = this.decodificarPayload(token);
  }

  private decodificarPayload(token: string): UsuarioToken | null {
    try {
      const payloadBase64 = token.split('.')[1];
      const json = atob(payloadBase64.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(json);
    } catch {
      return null;
    }
  }
}
