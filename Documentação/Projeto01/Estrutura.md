# Projeto01 — Estrutura

Índice da documentação técnica do Projeto01.

| Documento | Conteúdo |
|---|---|
| [[Projeto01/Visao\|Visão]] | Objetivo, o que mudou em relação ao [[Projeto00]], descrição funcional, modelo de dados |
| [[Projeto01/Backend]] | Arquitetura, apps, models, rotas da API, JWT, bibliotecas (Django) |
| [[Projeto01/Frontend]] | Arquitetura, rotas, páginas, services, interceptor, armazenamento local (Angular) |
| [[Projeto01/Vulnerabilidades]] | Vulnerabilidades propositais que continuam exploráveis neste projeto |
| [[Projeto01/Melhorias]] | O que melhorou (vulnerabilidades corrigidas, hardening) em relação ao [[Projeto00]] |

## Visão geral dos subprojetos

| Subprojeto | Pasta | Stack | Papel |
|---|---|---|---|
| Backend | `Projeto01/api01/` | Django 6.1.1 (Python) | API REST que expõe usuários e tarefas, emite/valida JWT, persiste em SQLite |
| Frontend | `Projeto01/client01/` | Angular 18 (TypeScript, standalone components) | SPA consumida no navegador, fala com a API via HTTP |

Comunicação: `client01` → HTTP/JSON → `api01` em `http://localhost:8000/api`
(constante `API_BASE_URL`). Diferente do [[Projeto00]], agora existe um JWT emitido no
login — guardado em `localStorage` (não em cookie) e anexado automaticamente pelo
`authInterceptor` em toda requisição HTTP (detalhes em [[Projeto01/Frontend]]). O backend
valida esse token (assinatura, não expiração) nas rotas de `tarefas` e em
`GET /api/usuarios/me` (detalhes em [[Projeto01/Backend]] e [[Projeto01/Melhorias]]) —
mas `GET /api/usuarios` (listagem, nova aba "Usuários") só confere que o token é válido,
sem checar o papel de quem chama (ver [[Projeto01/Vulnerabilidades]] item 5).

## Fluxo ponta a ponta

```
client01 (Angular, :4200)
  LoginComponent / CadastroComponent / KanbanComponent
        │  HttpClient (JSON)
        ▼
  authInterceptor  ──→  anexa "Authorization: Bearer <token>" lido do localStorage
        │
        ▼  http://localhost:8000/api/...
api01 (Django, :8000)
  urls.py (raiz) → usuarios/urls.py | tarefas/urls.py
        │
        ▼
  jwt_required (usuarios/decorators.py) — rotas de tarefas e /usuarios/me
        │  valida assinatura HMAC do token (usuarios/jwt_utils.py)
        ▼
  views.py (usuarios | tarefas) — JSON in/out, @csrf_exempt
        │
        ▼
  models.py (Usuario com papel + senha MD5, Tarefa) — Django ORM
   (listar_tarefas_por_usuario com filtro "nome" usa SQL cru, sem ORM — ver
    [[Projeto01/Vulnerabilidades]] item 4)
        │
        ▼
  db.sqlite3 (arquivo local, não versionado)
```
