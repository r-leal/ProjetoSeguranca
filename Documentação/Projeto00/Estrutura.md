# Projeto00 — Estrutura

Índice da documentação técnica do Projeto00.

| Documento | Conteúdo |
|---|---|
| [[Projeto00/Visao\|Visão]] | Objetivo, descrição funcional, vulnerabilidades propositais |
| [[Projeto00/Backend]] | Arquitetura, apps, models, rotas da API, bibliotecas (Django) |
| [[Projeto00/Frontend]] | Arquitetura, rotas, páginas, services, armazenamento local (Angular) |

## Visão geral dos subprojetos

| Subprojeto | Pasta | Stack | Papel |
|---|---|---|---|
| Backend | `Projeto00/api00/` | Django 6.1.1 (Python) | API REST que expõe usuários e tarefas, persiste em SQLite |
| Frontend | `Projeto00/client00/` | Angular 18 (TypeScript, standalone components) | SPA consumida no navegador, fala com a API via HTTP |

Comunicação: `client00` → HTTP/JSON → `api00` em `http://localhost:8000/api`
(constante `API_BASE_URL`). Sem autenticação por cookie/token — a "sessão" existe só no
`localStorage` do navegador (detalhes em [[Projeto00/Frontend]]).

## Fluxo ponta a ponta

```
client00 (Angular, :4200)
  LoginComponent / CadastroComponent / KanbanComponent
        │  HttpClient (JSON)
        ▼
  AuthService / TaskService  ──→  localStorage (sessão em texto puro)
        │
        ▼  http://localhost:8000/api/...
api00 (Django, :8000)
  urls.py (raiz) → usuarios/urls.py | tarefas/urls.py
        │
        ▼
  views.py (usuarios | tarefas) — JSON in/out, @csrf_exempt
        │
        ▼
  models.py (Usuario, Tarefa) — Django ORM
        │
        ▼
  db.sqlite3 (arquivo local, não versionado)
```
