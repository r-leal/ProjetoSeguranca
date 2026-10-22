import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { API_BASE_URL } from '../api.config';
import { AuthService } from '../services/auth.service';

/**
 * Anexa o access token (guardado em memória pelo AuthService) como
 * `Authorization: Bearer <token>` em toda requisição à API, e liga
 * `withCredentials` para que o browser envie (e aceite) o cookie HttpOnly
 * do refresh token e o cookie de CSRF entre localhost:4200 e
 * localhost:8000 — sem isso, cookies simplesmente não são enviados em
 * requisições cross-origin.
 *
 * Se a API responder 401 (access token expirado), tenta renovar via
 * refresh token e refaz a requisição original uma única vez — é esse
 * fluxo que evita deslogar o usuário a cada 15 minutos (vida curta do
 * access token) sem abrir mão de expiração curta.
 *
 * Ver Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seções 5 e 7).
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);

  if (!req.url.startsWith(API_BASE_URL)) {
    return next(req);
  }

  const anexarToken = (token: string | null) =>
    req.clone({
      withCredentials: true,
      setHeaders: token ? { Authorization: `Bearer ${token}` } : {}
    });

  // Rotas de autenticação não entram no fluxo de retry — tentar renovar o
  // token numa falha de /login ou /token/refresh causaria um loop; e 401
  // em POST /usuarios (cadastro público) não tem relação com token algum.
  const semRetryDeRefresh =
    req.url.endsWith('/login') ||
    req.url.endsWith('/token/refresh') ||
    (req.method === 'POST' && req.url.endsWith('/usuarios'));

  return next(anexarToken(authService.getToken())).pipe(
    catchError((erro: HttpErrorResponse) => {
      if (erro.status !== 401 || semRetryDeRefresh) {
        return throwError(() => erro);
      }

      return authService
        .refrescarToken()
        .pipe(switchMap((novoToken) => next(anexarToken(novoToken))));
    })
  );
};
