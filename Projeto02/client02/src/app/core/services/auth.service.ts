import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { Usuario } from '../models/usuario';
import { API_BASE_URL } from '../api.config';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  // Access token e refresh token ficam só em cookies HttpOnly, setados pelo
  // backend — este serviço nunca tem acesso a eles via JS, só o navegador,
  // que os envia automaticamente em toda requisição para /api. O único
  // estado guardado aqui é o usuário autenticado, que vem já validado nas
  // respostas de /login e /token/refresh (JSON devolvido pelo backend após
  // checar a assinatura/expiração do token).
  // Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 7).
  private usuarioAtual: Usuario | null = null;

  constructor(private http: HttpClient) {}

  login(email: string, senha: string): Observable<Usuario> {
    return this.http
      .post<Usuario>(`${API_BASE_URL}/login`, { email, senha })
      .pipe(tap((usuario) => (this.usuarioAtual = usuario)));
  }

  cadastrar(usuario: Usuario): Observable<Usuario> {
    return this.http.post<Usuario>(`${API_BASE_URL}/usuarios`, usuario);
  }

  // Busca os dados do usuário logado no backend (GET /api/usuarios/me),
  // protegido por jwt_required — útil para revalidar/atualizar os dados
  // exibidos sem depender de um novo login ou refresh.
  buscarUsuarioLogado(): Observable<Usuario> {
    return this.http
      .get<Usuario>(`${API_BASE_URL}/usuarios/me`)
      .pipe(tap((usuario) => (this.usuarioAtual = usuario)));
  }

  // Chamado uma única vez, na inicialização do app (ver APP_INITIALIZER em
  // app.config.ts): tenta usar o refresh token (cookie HttpOnly, enviado
  // automaticamente pelo browser) para obter um access token novo sem
  // exigir login de novo. É o que mantém a sessão viva depois de um reload
  // de página — o usuário em memória se perde nesse momento, mas os cookies
  // continuam lá.
  restaurarSessao(): Observable<Usuario> {
    return this.refrescarToken();
  }

  // Também usado pelo interceptor quando um request volta 401 por access
  // token expirado: pede um access token novo ao backend, que valida o
  // refresh token recebido (cookie) e o ROTACIONA (emite um substituto e
  // invalida o antigo), devolvendo o novo access token em outro cookie
  // HttpOnly. Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md
  // (seção 5).
  refrescarToken(): Observable<Usuario> {
    return this.http
      .post<Usuario>(`${API_BASE_URL}/token/refresh`, {})
      .pipe(tap((usuario) => (this.usuarioAtual = usuario)));
  }

  logout(): void {
    // Revoga o refresh token no backend e limpa os cookies de access/refresh
    // — um logout que só "esquecesse" o usuário aqui no cliente não
    // impediria que o refresh token continuasse sendo usado para gerar
    // novos access tokens. O estado em memória é limpo independentemente da
    // resposta do servidor, para nunca deixar o app achando que ainda está
    // logado.
    this.http.post(`${API_BASE_URL}/logout`, {}).subscribe({ error: () => undefined });
    this.usuarioAtual = null;
  }

  // Dados do usuário autenticado, já validados pelo backend (vieram de
  // /login, /token/refresh ou /usuarios/me) — nunca decodificados
  // localmente de um token, porque o access token não é mais legível por
  // JavaScript.
  usuarioLogado(): Usuario | null {
    return this.usuarioAtual;
  }
}
