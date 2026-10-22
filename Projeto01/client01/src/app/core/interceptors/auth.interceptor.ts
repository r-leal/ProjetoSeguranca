import { HttpInterceptorFn } from '@angular/common/http';
import { AUTH_TOKEN_KEY } from '../api.config';

/**
 * Anexa o JWT salvo no localStorage em toda requisição, como
 * `Authorization: Bearer <token>` — é esse header que o backend valida nas
 * rotas de tarefas para corrigir o IDOR (ver usuarios/decorators.py em api01).
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (!token) {
    return next(req);
  }

  return next(
    req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    })
  );
};
