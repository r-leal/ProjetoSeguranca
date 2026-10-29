# Projeto02 — Estrutura

Índice da documentação técnica do Projeto02.

| Documento | Conteúdo |
|---|---|
| [[Projeto02/Visao\|Visão]] | Objetivo, o que mudou em relação ao [[Projeto01]], descrição funcional, modelo de dados |
| [[Projeto02/SegurancaAutorizacaoAcesso]] | Guia didático de JWT, papéis, criptografia, refresh token, expiração, httpOnly cookies — base das mudanças deste projeto |
| [[Projeto02/Backend]] | Arquitetura, apps, models, rotas da API, JWT, refresh token, bibliotecas (Django) |
| [[Projeto02/Frontend]] | Arquitetura, rotas, páginas, services, interceptor, armazenamento (Angular) |
| [[Projeto02/Vulnerabilidades]] | Vulnerabilidades propositais que continuam exploráveis neste projeto |
| [[Projeto02/Melhorias]] | O que melhorou (vulnerabilidades corrigidas, hardening) em relação ao [[Projeto01]] |

## Visão geral dos subprojetos

| Subprojeto | Pasta | Stack | Papel |
|---|---|---|---|
| Backend | `Projeto02/api02/` | Django 6.1.1 (Python) | API REST que expõe usuários e tarefas, emite/valida JWT + refresh token, persiste em SQLite |
| Frontend | `Projeto02/client02/` | Angular 18 (TypeScript, standalone components) | SPA consumida no navegador, fala com a API via HTTP |

Comunicação: `client02` → HTTP/JSON (+ cookies) → proxy do dev server (`/api` →
`http://localhost:8000/api`, `proxy.conf.json`) → `api02`, origem restrita a
`http://localhost:4200` (`CORS_ALLOWED_ORIGINS`). Diferente do [[Projeto01]], a sessão
agora tem duas partes, nenhuma delas manuseada pelo frontend: um access token (JWT, vida
curta) e um refresh token (opaco, vida mais longa), os dois só em cookies `HttpOnly` —
detalhes em [[Projeto02/Backend]] e [[Projeto02/Frontend]].

## Fluxo ponta a ponta

```
client02 (Angular, :4200)
  LoginComponent / CadastroComponent / KanbanComponent / UsuariosComponent
        │  HttpClient (JSON, withCredentials)
        ▼
  authInterceptor  ──→  só garante withCredentials: true — nenhum token anexado
        │               cookies access_token/refresh_token (HttpOnly) e XSRF-TOKEN,
        │               enviados automaticamente pelo browser
        │               em 401 → AuthService.refrescarToken() → retry
        ▼  /api/... (mesma origem)
proxy do dev server (proxy.conf.json)  ──→  http://localhost:8000/api/...
        ▼
api02 (Django, :8000)
  CsrfViewMiddleware  ← protege toda rota que autentica por cookie (tarefas,
        │                /usuarios/me, listar_usuarios, /token/refresh, /logout)
        ▼
  urls.py (raiz) → usuarios/urls.py | tarefas/urls.py
        │
        ▼
  jwt_required (lê access_token do cookie, valida assinatura + exp)
        │  → papel_required (valida papel, em /usuarios)
        ▼
  views.py (usuarios | tarefas) — JSON in/out, nunca um token no corpo
        │
        ▼
  models.py (Usuario com senha PBKDF2, RefreshToken, Tarefa) — Django ORM
        │  (filtro de tarefas por nome parametrizado — sem SQL cru)
        ▼
  db.sqlite3 (arquivo local, não versionado)
```
