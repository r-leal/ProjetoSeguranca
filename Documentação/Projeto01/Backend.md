# Projeto01 — Backend (api01)

Documentação técnica do backend. Para visão geral do projeto ver
[[Projeto01/Visao|Projeto01 — Visão]]; para o frontend ver [[Projeto01/Frontend]]. Este
documento assume a arquitetura do [[Projeto00/Backend|api00]] como base e foca no que
mudou.

## Arquitetura

Mesma base do [[Projeto00/Backend|api00]] — Django usado só como API, sem DRF, sem
camada de serviço/repositório, views baseadas em função — com duas adições:

```
Requisição HTTP
     │
     ▼
api01/urls.py              ← URLconf raiz
     │
     ▼
<app>/urls.py                ← URLconf do app
     │
     ▼
usuarios/decorators.py:jwt_required   ← (novo) exige e valida JWT em rotas protegidas
     │  anexa request.usuario = payload decodificado
     ▼
<app>/views.py                ← lê request, chama o ORM (ou SQL cru, ver abaixo), monta JSON
     │
     ▼
<app>/models.py                ← classes Django ORM
     │
     ▼
db.sqlite3
     │
     ▼
JsonResponse  ──────────────→  de volta pro cliente HTTP
```

Diferenças de arquitetura em relação ao [[Projeto00/Backend|api00]]:

- **`usuarios/jwt_utils.py`** (novo): implementação mínima de JWT HS256 usando só a
  biblioteca padrão (`hashlib`, `hmac`, `base64`, `json`) — sem dependência externa tipo
  `PyJWT`. Expõe `gerar_token(usuario)` (login) e `verificar_token(token)` (valida
  assinatura via `hmac.compare_digest`, usada pelo decorator abaixo).
- **`usuarios/decorators.py`** (novo): `jwt_required`, um decorator reutilizado por
  `tarefas/views.py` e por `usuarios/views.py` (`usuario_logado`). Exige
  `Authorization: Bearer <token>`, valida a assinatura e anexa o payload decodificado em
  `request.usuario` — é essa identidade, não mais um id vindo da URL/corpo, que as views
  protegidas usam para decidir "de quem" é o dado.
- `listar_tarefas_por_usuario` tem dois caminhos: sem filtro, usa o ORM normalmente
  (`Tarefa.objects.filter(...)`); com filtro por nome, monta e executa **SQL cru** via
  `django.db.connection.cursor()` — ver ⚠️ abaixo e [[Projeto01/Vulnerabilidades]] item 4.
- CSRF continua desativado (`@csrf_exempt`) e CORS continua liberado
  (`CORS_ALLOW_ALL_ORIGINS = True`) — herdado sem alteração do [[Projeto00]].

## Organização de pastas

```
api01/
├── manage.py
├── requirements.txt
├── db.sqlite3                 (não versionado)
├── api01/                     ← projeto (configuração global)
│   ├── settings.py             ← + JWT_SECRET
│   ├── urls.py                  ← URLconf raiz
│   ├── asgi.py / wsgi.py
├── usuarios/                   ← app de domínio
│   ├── models.py                ← + campo papel
│   ├── views.py                  ← + hash_md5, gerar_token, usuario_logado
│   ├── jwt_utils.py               ← novo
│   ├── decorators.py              ← novo
│   ├── urls.py                     ← + rota /usuarios/me
│   ├── admin.py
│   └── migrations/
└── tarefas/                    ← app de domínio
    ├── models.py                ← idêntico ao Projeto00
    ├── views.py                   ← + jwt_required, checagem de posse, filtro SQL cru
    ├── urls.py
    └── migrations/
```

## Apps de domínio

| App | Responsabilidade | Model | Registrado no admin? |
|---|---|---|---|
| `usuarios` | Cadastro, login, emissão de JWT, perfil do usuário logado, listagem de usuários | `Usuario` | Sim (`admin.site.register(Usuario)`) |
| `tarefas` | CRUD do quadro Kanban, protegido por JWT | `Tarefa` | Não (app não tem `admin.py`) |

### Modelo de dados

**`usuarios.Usuario`** (`usuarios/models.py`)

| Campo | Tipo Django | Observação |
|---|---|---|
| `id` | auto (PK) | |
| `nome` | `CharField(100)` | |
| `sobrenome` | `CharField(100)` | |
| `data_nascimento` | `DateField` | opcional |
| `email` | `EmailField` | único |
| `senha` | `CharField(32)` | **hash MD5 sem salt** (inseguro de propósito — [[Projeto01/Vulnerabilidades]] item 1) |
| `papel` | `CharField(20)` com `choices` | `usuario` \| `admin` \| `gerente`, default `usuario`; o cadastro público sempre grava `usuario`, ignorando qualquer valor do cliente (ver [[Projeto01/Melhorias]]) |

**`tarefas.Tarefa`** (`tarefas/models.py`) — idêntico ao [[Projeto00/Backend|api00]]:
`usuario` (FK CASCADE), `nome`, `descricao`, `data_prazo`, `estado` (`esperando` \|
`em_andamento` \| `concluido`).

Persistência: **SQLite**, arquivo `api01/db.sqlite3` (fora do Git), schema versionado via
`migrations/0001_initial.py` de cada app.

## JWT

`usuarios/jwt_utils.py` implementa um JWT HS256 manual:

```python
def gerar_token(usuario) -> str:
    payload = {
        'id': usuario.id, 'nome': usuario.nome, 'sobrenome': usuario.sobrenome,
        'email': usuario.email, 'papel': usuario.papel,
    }
    # header.payload em base64url, assinatura HMAC-SHA256 com settings.JWT_SECRET
```

Pontos importantes:
- **Sem claim `exp`** — o token nunca expira (proposital, [[Projeto01/Vulnerabilidades]]
  item 2).
- `JWT_SECRET` em `settings.py` é a **mesma** `SECRET_KEY` insegura e commitada do Django
  (herdada do [[Projeto00/Backend|api00]], item 7 de [[Projeto00/Vulnerabilidades]]).
- `verificar_token()` valida a assinatura com `hmac.compare_digest` antes de confiar em
  qualquer claim — usado por `jwt_required` (ver [[Projeto01/Melhorias]]).

## Rotas da API

Prefixo comum `/api`, montado em `api01/api01/urls.py` (idêntico ao [[Projeto00]]):
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('usuarios.urls')),
    path('api/', include('tarefas.urls')),
]
```

### `usuarios` (`usuarios/urls.py`)

| Método | Rota | View | Autenticação | Input (body JSON) | Output |
|---|---|---|---|---|---|
| `GET`/`POST` | `/api/usuarios` | `usuarios_collection` → `listar_usuarios` / `cadastrar_usuario` | `GET`: **`jwt_required`** (⚠️ sem checar papel); `POST`: nenhuma (pública) | `POST`: `{ nome, sobrenome, data_nascimento?, email, senha }`; `GET`: `?q=<termo>` opcional | `POST`: `201` + `Usuario` (sem senha), sempre com `papel: "usuario"`; `GET`: `200` + lista de `Usuario` |
| `POST` | `/api/login` | `login` | nenhuma (pública) | `{ email, senha }` | `200` + `{ token }` **ou** `401` + `{ erro }` |
| `GET` | `/api/usuarios/me` | `usuario_logado` | **`jwt_required`** | — | `200` + `Usuario` do token **ou** `401` |

`cadastrar_usuario` ignora qualquer `papel` enviado no corpo da requisição — todo
cadastro público nasce com `Usuario.PAPEL_USUARIO` (ver [[Projeto01/Melhorias]]). `login`
compara `hash_md5(senha)` (não a senha em claro, diferente do [[Projeto00/Backend|api00]])
e devolve um JWT em vez do objeto `Usuario`.

`GET /api/usuarios` e `POST /api/usuarios` são despachadas pela mesma view
(`usuarios_collection`, que decide por `request.method`), já que ambas vivem na mesma
URL — `usuarios/urls.py` mapeia só essa view, e `cadastrar_usuario`/`listar_usuarios`
deixaram de ser views Django diretas (perderam seus próprios `@require_http_methods`) e
passaram a ser funções auxiliares chamadas por ela.

⚠️ `listar_usuarios` exige `jwt_required` (então precisa de um token válido de
**qualquer** usuário), mas nunca confere `request.usuario['papel']` — um usuário comum
lê a lista completa de usuários do sistema. Ver [[Projeto01/Vulnerabilidades]] item 5 e
[[Projeto01/Ataque-A01-ListagemUsuariosSemChecarPapel]].

### `tarefas` (`tarefas/urls.py`) — todas protegidas por `jwt_required`

| Método | Rota | View | Checagem de posse | Input (body JSON) | Output |
|---|---|---|---|---|---|
| `GET` | `/api/usuarios/<usuario_id>/tarefas` | `listar_tarefas_por_usuario` | `usuario_id` da URL == `id` do token, senão `403` | `?nome=` opcional (ver ⚠️) | `200` + lista de `Tarefa` |
| `POST` | `/api/tarefas` | `criar_tarefa` | `usuario_id` sempre = `id` do token (corpo ignorado) | `{ nome, descricao?, data_prazo?, estado? }` | `201` + `Tarefa` criada |
| `PUT` | `/api/tarefas/<tarefa_id>` | `tarefa_detalhe` | `tarefa.usuario_id` == `id` do token, senão `404` | `{ nome?, descricao?, data_prazo?, estado? }` | `200` + `Tarefa` atualizada |
| `DELETE` | `/api/tarefas/<tarefa_id>` | `tarefa_detalhe` | idem acima | — | `204` sem corpo |

Essa coluna "checagem de posse" é a correção de IDOR em relação ao
[[Projeto00/Backend|api00]] — ver [[Projeto01/Melhorias]] para o detalhamento completo.

⚠️ `GET /api/usuarios/<usuario_id>/tarefas?nome=<termo>` monta a consulta com SQL cru e
f-string, **depois** de passar pela checagem de posse — ou seja, mesmo autorizado a
consultar seu próprio `usuario_id`, um usuário pode usar o parâmetro `nome` para quebrar
a cláusula `WHERE` e ler tarefas de qualquer outro usuário (SQL Injection, ver
[[Projeto01/Vulnerabilidades]] item 4 e [[Projeto01/Ataque-A05-SQLInjectionFiltro]]):
```python
query = (
    "SELECT id, usuario_id, nome, descricao, data_prazo, estado "
    "FROM tarefas_tarefa "
    f"WHERE usuario_id = {usuario_id} AND nome LIKE '%{nome_filtro}%'"
)
```

## Bibliotecas (`requirements.txt`)

Idêntico ao [[Projeto00/Backend|api00]] — nenhuma biblioteca nova foi adicionada; o JWT é
implementado só com a biblioteca padrão do Python.

| Pacote | Versão | Uso |
|---|---|---|
| `Django` | 6.1.1 | Framework web / ORM / admin |
| `django-cors-headers` | 4.9.0 | Middleware de CORS (configurado liberado) |
| `asgiref` | 3.12.1 | Suporte ASGI (dependência do Django) |
| `sqlparse` | 0.6.0 | Dependência do Django (parsing de SQL) |
| `tzdata` | 2026.4 | Dados de timezone (`USE_TZ = True`) |

## Configuração relevante (`api01/settings.py`)

Igual ao [[Projeto00/Backend|api00]] (`DEBUG = True`, `ALLOWED_HOSTS = ['*']`,
`CORS_ALLOW_ALL_ORIGINS = True`, sem `CsrfViewMiddleware`), **mais**:
- `JWT_SECRET = SECRET_KEY` — reusa a mesma chave insegura e commitada do Django para
  assinar os JWTs (ver [[Projeto00/Vulnerabilidades]] item 7, que agora também afeta a
  integridade dos tokens, não só sessão/cookies hipotéticos).
