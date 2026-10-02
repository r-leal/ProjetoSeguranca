# Projeto00 — Backend (api00)

Documentação técnica do backend. Para visão geral do projeto ver
[[Projeto00/Visao|Projeto00 — Visão]]; para o frontend ver [[Projeto00/Frontend]].

## Arquitetura

O `api00` é um projeto Django clássico, mas usado **apenas como API** — não há
templates HTML nem renderização server-side. A arquitetura segue o padrão
**MTV do Django (Model-Template-View)** adaptado para API pura, o que na prática vira
**Model → View (controller) → URLconf (roteador)**, sem a camada de Template:

```
Requisição HTTP
     │
     ▼
api00/urls.py              ← URLconf raiz: decide qual app trata a URL
     │
     ▼
<app>/urls.py                ← URLconf do app: decide qual view trata a URL
     │
     ▼
<app>/views.py                ← função Python: lê request, chama o ORM, monta JSON
     │
     ▼
<app>/models.py                ← classes Django ORM: leem/escrevem no banco
     │
     ▼
db.sqlite3
     │
     ▼
JsonResponse  ──────────────→  de volta pro cliente HTTP
```

Pontos importantes dessa arquitetura:

- **Não usa Django REST Framework (DRF)**. Serialização é manual: cada app tem uma
  função auxiliar (`usuario_para_json`, `tarefa_para_json`) que converte o objeto do
  model num `dict` para o `JsonResponse`. Não há validação de schema automática —
  `request.body` é lido com `json.loads` e os campos são extraídos com `.get(...)`.
- **Não tem camada de serviço/repositório**. As views chamam o ORM (`Model.objects...`)
  diretamente. Para um projeto deste tamanho (e propositalmente simples/inseguro) isso é
  aceitável, mas é uma limitação se o projeto crescer: regra de negócio e acesso a dado
  ficam misturados na view.
- **Views são baseadas em função** (`def minha_view(request): ...`), não em classes
  (`APIView`/`ViewSet`). Cada view decide o método HTTP aceito via o decorator
  `@require_http_methods([...])`.
- **Sem autenticação/sessão real**: não usa `django.contrib.auth` para login (apesar do
  app estar instalado em `INSTALLED_APPS`), nem `rest_framework.authtoken`/JWT. "Estar
  logado" é um conceito que só existe no frontend (ver [[Projeto00/Frontend]]).
- **CSRF desativado** (`@csrf_exempt` em todas as views) e **CORS liberado para
  qualquer origem** (`CORS_ALLOW_ALL_ORIGINS = True`) — falhas propositais, ver
  [[Projeto00/Visao]].

## Organização de pastas

```
api00/
├── manage.py
├── requirements.txt
├── db.sqlite3                 (não versionado)
├── api00/                     ← projeto (configuração global)
│   ├── settings.py
│   ├── urls.py                 ← URLconf raiz
│   ├── asgi.py / wsgi.py
├── usuarios/                   ← app de domínio
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
└── tarefas/                    ← app de domínio
    ├── models.py
    ├── views.py
    ├── urls.py
    ├── admin.py
    └── migrations/
```

Cada **app** Django é um módulo de domínio autocontido (models + views + urls +
migrations + admin próprios). O projeto (`api00/api00/`) só centraliza configuração
(`settings.py`) e agrega as rotas de cada app (`urls.py` raiz com `include(...)`).

## Apps de domínio

| App | Responsabilidade | Model | Registrado no admin? |
|---|---|---|---|
| `usuarios` | Cadastro e login | `Usuario` | Sim (`admin.site.register(Usuario)`) |
| `tarefas` | CRUD do quadro Kanban | `Tarefa` | Não (`tarefas/admin.py` vazio) |

### Modelo de dados

**`usuarios.Usuario`** (`usuarios/models.py`)

| Campo | Tipo Django | Observação |
|---|---|---|
| `id` | auto (PK) | |
| `nome` | `CharField(100)` | |
| `sobrenome` | `CharField(100)` | |
| `data_nascimento` | `DateField` | opcional |
| `email` | `EmailField` | único |
| `senha` | `CharField(255)` | **texto puro, sem hash** (inseguro de propósito) |

**`tarefas.Tarefa`** (`tarefas/models.py`)

| Campo | Tipo Django | Observação |
|---|---|---|
| `id` | auto (PK) | |
| `usuario` | `ForeignKey(Usuario, on_delete=CASCADE)` | dono da tarefa; apagar usuário apaga tarefas |
| `nome` | `CharField(150)` | |
| `descricao` | `TextField` | opcional |
| `data_prazo` | `DateField` | opcional |
| `estado` | `CharField(20)` com `choices` | `esperando` \| `em_andamento` \| `concluido`, default `esperando` |

Persistência: **SQLite**, arquivo `api00/db.sqlite3` (fora do Git). O schema é versionado
via `migrations/0001_initial.py` de cada app — os `.py` em `migrations/` **são**
versionados; o arquivo de dados (`db.sqlite3`) não.

## Rotas da API

Prefixo comum `/api`, montado em `api00/api00/urls.py`:
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('usuarios.urls')),
    path('api/', include('tarefas.urls')),
]
```

### `usuarios` (`usuarios/urls.py`)

| Método | Rota | View | Input (body JSON) | Output |
|---|---|---|---|---|
| `POST` | `/api/usuarios` | `cadastrar_usuario` | `{ nome, sobrenome, data_nascimento?, email, senha }` | `201` + objeto `Usuario` |
| `POST` | `/api/login` | `login` | `{ email, senha }` | `200` + objeto `Usuario` **ou** `401` + `{ erro }` |

⚠️ `login` compara `email`/`senha` direto no banco em texto puro
(`Usuario.objects.filter(email=..., senha=...)`), e ambas as views devolvem a senha em
texto puro no corpo da resposta.

### `tarefas` (`tarefas/urls.py`)

| Método | Rota | View | Input (body JSON) | Output |
|---|---|---|---|---|
| `GET` | `/api/usuarios/<usuario_id>/tarefas` | `listar_tarefas_por_usuario` | — (param de URL) | `200` + lista de `Tarefa` |
| `POST` | `/api/tarefas` | `criar_tarefa` | `{ usuario_id, nome, descricao?, data_prazo?, estado? }` | `201` + `Tarefa` criada |
| `PUT` | `/api/tarefas/<tarefa_id>` | `tarefa_detalhe` | `{ nome?, descricao?, data_prazo?, estado? }` | `200` + `Tarefa` atualizada |
| `DELETE` | `/api/tarefas/<tarefa_id>` | `tarefa_detalhe` | — | `204` sem corpo |

Formato JSON de `Tarefa` (serialização manual via `tarefa_para_json`):
```json
{
  "id": 1,
  "usuario_id": 3,
  "nome": "Implementar login",
  "descricao": "...",
  "data_prazo": "2026-10-05",
  "estado": "esperando"
}
```

⚠️ `GET /api/usuarios/<usuario_id>/tarefas` não valida se quem pergunta é o dono do
`usuario_id` — qualquer id pode ser consultado (falta de autorização, proposital).

## Bibliotecas (`requirements.txt`)

| Pacote | Versão | Uso |
|---|---|---|
| `Django` | 6.1.1 | Framework web / ORM / admin |
| `django-cors-headers` | 4.9.0 | Middleware de CORS (configurado liberado) |
| `asgiref` | 3.12.1 | Suporte ASGI (dependência do Django) |
| `sqlparse` | 0.6.0 | Dependência do Django (parsing de SQL) |
| `tzdata` | 2026.4 | Dados de timezone (`USE_TZ = True`) |

## Configuração relevante (`api00/settings.py`)

- `DATABASES.default` → `sqlite3`, arquivo `db.sqlite3` na raiz de `api00/`.
- `ALLOWED_HOSTS = ['*']` e `CORS_ALLOW_ALL_ORIGINS = True`.
- `MIDDLEWARE` sem `CsrfViewMiddleware` e sem `XFrameOptionsMiddleware`.
- `DEBUG = True` — stack traces detalhados expostos ao cliente em caso de erro.
- `INSTALLED_APPS` inclui `django.contrib.auth`/`admin`/`sessions` (padrão do
  `startproject`), mas o projeto **não usa** esse sistema de autenticação para a API —
  só serve para o painel `/admin/` funcionar.
