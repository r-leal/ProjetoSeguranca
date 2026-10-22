import { APP_INITIALIZER, ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors, withXsrfConfiguration } from '@angular/common/http';
import { catchError, of } from 'rxjs';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { AuthService } from './core/services/auth.service';

// Roda antes do app renderizar qualquer rota: tenta restaurar a sessão a
// partir do refresh token (cookie HttpOnly) depois de um reload de página.
// Sem isso, haveria uma corrida entre a restauração (assíncrona) e o
// ngOnInit dos componentes de rota, que leriam "não autenticado" antes do
// refresh terminar. Falha aqui só significa "não estava logado" — por isso
// o erro é silenciado em vez de propagado.
function restaurarSessaoAoIniciar(authService: AuthService) {
  return () => authService.restaurarSessao().pipe(catchError(() => of(null)));
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(
      withInterceptors([authInterceptor]),
      // Nomes de cookie/header têm que bater com CSRF_COOKIE_NAME /
      // CSRF_HEADER_NAME em api02/settings.py — é a defesa contra CSRF nas
      // rotas que dependem do cookie do refresh token. Ver
      // Documentação/Projeto02/SegurancaAutorizacaoAcesso.md (seção 7.3).
      withXsrfConfiguration({ cookieName: 'XSRF-TOKEN', headerName: 'X-XSRF-TOKEN' })
    ),
    {
      provide: APP_INITIALIZER,
      useFactory: restaurarSessaoAoIniciar,
      deps: [AuthService],
      multi: true
    }
  ]
};
