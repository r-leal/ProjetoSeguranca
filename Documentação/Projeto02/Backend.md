# Projeto02 — Backend (api02)

Documentação técnica do backend. Para visão geral do projeto ver
[[Projeto02/Visao|Projeto02 — Visão]]; para o frontend ver [[Projeto02/Frontend]]. Este
documento assume a arquitetura do [[Projeto01/Backend|api01]] como base e foca no que
mudou.

## Arquitetura

Mesma base do [[Projeto01/Backend|api01]] — Django usado só como API, sem DRF, views
baseadas em função, `usuarios/jwt_utils.py` + `usuarios/decorators.py` validando o JWT —
com três adições:

```
Requisição HTTP
     │
     ▼
api02/urls.py              ← URLconf raiz
     │
     ▼
CsrfViewMiddleware  (novo)   ← só rejeita requisições sem X-XSRF-TOKEN nas rotas que
     │                         dependem de cookie (/token/refresh, /logout)
     ▼
<app>/urls.py                ← URLconf do app
     │
     ▼
jwt_required                 ← valida assinatura E expiração (exp), anexa request.usuario
     │
     ▼
papel_required(*papeis)  (novo)  ← valida request.usuario['papel'], usado em /usuarios
     │
     ▼
<app>/views.py                ← lê request, chama o ORM (ou SQL cru em tarefas, herdado), monta JSON
     │
     ▼
<app>/models.py                ← Usuario (senha PBKDF2), RefreshToken (novo), Tarefa
     │
     ▼
db.sqlite3
     │
     ▼
JsonResponse  ──────────────→  de volta pro cliente HTTP
```

Diferenças de arquitetura em relação ao [[Projeto01/Backend|api01]]:

- **`usuarios/jwt_utils.py`**: `gerar_token()` agora inclui `iat`/`exp` no payload
  (`ttl_segundos`, padrão `settings.ACCESS_TOKEN_TTL_SEGUNDOS`); `verificar_token()`
  rejeita token sem `exp` ou expirado, além de continuar validando a assinatura HMAC
  via `hmac.compare_digest`.
- **`usuarios/decorators.py`**: além do `jwt_required` herdado, ganha
  `papel_required(*papeis_permitidos)` — exige que `request.usuario['papel']` esteja
  entre os papéis informados; depende de `jwt_required` já ter rodado antes (empilhados
  com `jwt_required` por cima).
- **`usuarios/refresh_utils.py`** (novo): `gerar_refresh_token()`,
  `rotacionar_refresh_token()` e `revogar_refresh_token()` — emissão, rotação (com
  detecção de reuso) e revogação de refresh tokens. Nunca manipula o token em texto
  puro no banco, só o hash SHA-256 (`RefreshToken.token_hash`).
- CORS deixa de ser liberado para qualquer origem (`CORS_ALLOWED_ORIGINS` explícito +
  `CORS_ALLOW_CREDENTIALS`), e `CsrfViewMiddleware` passa a existir no `MIDDLEWARE` —
  ambos herdados *sem alteração* do [[Projeto01]] até aqui, agora corrigidos/adicionados
  (ver [[Projeto02/Melhorias]]).
- `listar_tarefas_por_usuario` continua com o mesmo caminho de SQL cru por f-string no
  filtro por nome — **sem alteração**, herdado do [[Projeto01/Backend|api01]]
  (⚠️ [[Projeto01/Vulnerabilidades]] item 4).

## Organização de pastas

```
api02/
├── manage.py
├── requirements.txt
├── db.sqlite3                 (não versionado)
├── api02/                     ← projeto (configuração global)
│   ├── settings.py             ← + JWT_SECRET_KEY, ACCESS/REFRESH_TOKEN_TTL, cookies, CORS/CSRF
│   ├── urls.py                  ← URLconf raiz (idêntico ao Projeto01)
│   ├── asgi.py / wsgi.py
├── usuarios/                   ← app de domínio
│   ├── models.py                ← senha CharField(255) + RefreshToken (novo)
│   ├── views.py                   ← + token_refresh, logout, papel_required em listar_usuarios
│   ├── jwt_utils.py                ← + iat/exp
│   ├── decorators.py                ← + papel_required
│   ├── refresh_utils.py              ← novo
│   ├── urls.py                        ← + /logout, /token/refresh
│   ├── admin.py
│   └── migrations/                     ← 0002_alter_usuario_senha_refreshtoken.py (novo)
└── tarefas/                    ← app de domínio (idêntico ao Projeto01)
    ├── models.py
    ├── views.py
    ├── urls.py
    └── migrations/
```

## Apps de domínio

| App | Responsabilidade | Model | Registrado no admin? |
|---|---|---|---|
| `usuarios` | Cadastro, login, emissão/rotação/revogação de token, perfil do usuário logado, listagem de usuários (restrita a admin) | `Usuario`, `RefreshToken` | `Usuario`: sim; `RefreshToken`: não |
| `tarefas` | CRUD do quadro Kanban, protegido por JWT | `Tarefa` | Não |

### Modelo de dados

**`usuarios.Usuario`** (`usuarios/models.py`)

| Campo | Tipo Django | Observação |
|---|---|---|
| `id` | auto (PK) | |
| `nome` | `CharField(100)` | |
| `sobrenome` | `CharField(100)` | |
| `data_nascimento` | `DateField` | opcional |
| `email` | `EmailField` | único |
| `senha` | `CharField(255)` | hash **PBKDF2 + salt** via `make_password()` — era `CharField(32)` com MD5 sem salt no [[Projeto01]] (ver [[Projeto02/Melhorias]]) |
| `papel` | `CharField(20)` com `choices` | `usuario` \| `admin` \| `gerente`, default `usuario`; cadastro público sempre grava `usuario` (herdado) |

**`usuarios.RefreshToken`** (novo, `usuarios/models.py`)

| Campo | Tipo Django | Observação |
|---|---|---|
| `id` | auto (PK) | |
| `usuario` | `ForeignKey(Usuario, on_delete=CASCADE)` | `related_name='refresh_tokens'` |
| `token_hash` | `CharField(64, unique=True)` | SHA-256 do token — o valor em texto puro **nunca** é persistido |
| `criado_em` | `DateTimeField(auto_now_add=True)` | |
| `expira_em` | `DateTimeField` | `settings.REFRESH_TOKEN_TTL_SEGUNDOS` (7 dias) após a emissão |
| `revogado_em` | `DateTimeField` | opcional; marcado na rotação, no logout, ou em massa por suspeita de reuso |

**`tarefas.Tarefa`** (`tarefas/models.py`) — igual ao [[Projeto01/Backend|api01]]
(`usuario` FK CASCADE, `nome`, `descricao`, `data_prazo`, `estado`), **mais** dois campos
novos para a funcionalidade de preview de link:

| Campo | Tipo Django | Observação |
|---|---|---|
| `url` | `URLField(500, blank=True, null=True)` | link opcional informado pelo usuário |
| `url_titulo` | `CharField(200, blank=True, null=True)` | título obtido pelo backend (`link_preview.py`) — nunca aceito cru do cliente |

Persistência: **SQLite**, arquivo `api02/db.sqlite3` (fora do Git). Schema alterado por
`usuarios/migrations/0002_alter_usuario_senha_refreshtoken.py` (amplia `senha` para 255
caracteres e cria `RefreshToken`) e por
`tarefas/migrations/0002_tarefa_url_tarefa_url_titulo.py` (campos `url`/`url_titulo`).

## Preview de link na tarefa (proteção contra SSRF)

Funcionalidade nova em relação ao [[Projeto01]]: a tarefa pode ter uma URL de
referência opcional, e o backend busca essa URL para extrair o `<title>` da página,
exibido no card do Kanban. Como é o **servidor** quem faz essa requisição de saída a
partir de um valor fornecido pelo usuário, esse é um vetor clássico de **SSRF
(Server-Side Request Forgery)** — sem cuidado, a mesma funcionalidade permitiria ao
atacante usar o backend como proxy para alcançar endereços internos da rede onde a API
roda (ex.: o serviço de metadados de nuvem em `169.254.169.254`, ou outras portas do
próprio `localhost`).

`tarefas/link_preview.py` (novo módulo, só biblioteca padrão) implementa as defesas:

1. **Allowlist de esquema**: só `http`/`https` são aceitos (bloqueia `file://`,
   `gopher://`, etc.).
2. **Resolução e validação de IP, não só de hostname**: `socket.getaddrinfo()` resolve
   o host, e **todos** os IPs retornados são checados com `ipaddress` — qualquer um
   privado, loopback, link-local (o que já cobre `169.254.169.254`), reservado ou
   multicast rejeita a URL inteira.
3. **Conexão direta no IP já validado**: `_ConexaoHTTPPorIP`/`_ConexaoHTTPSPorIP`
   (subclasses de `http.client.HTTPConnection`/`HTTPSConnection`) sobrescrevem
   `connect()` para abrir o socket no IP validado, não no hostname — fecha a janela de
   **DNS rebinding** (validar um IP público e, se a biblioteca HTTP resolvesse o
   hostname de novo no `connect()`, o DNS responder um IP interno diferente nessa
   segunda consulta). Para HTTPS, o SNI e a validação do
   certificado continuam usando o hostname original (`server_hostname=self.host`), só a
   conexão TCP é que vai para o IP fixado.
4. **Redirecionamentos revalidados do zero**: um `3xx` é seguido manualmente
   (`_requisitar` chama a si mesma), reaplicando as checagens 1–3 à nova URL — um host
   externo "confiável" poderia redirecionar para um endereço interno.
5. **Timeout curto (3s) e limite de bytes lidos (200 KB)** — evita abuso como prender
   conexões ou baixar respostas muito grandes.

`usuarios`/`tarefas/views.py:_resolver_url_titulo` usa essa busca ao criar/editar uma
tarefa (só quando a `url` é nova ou mudou, para não refazer a requisição em toda
movimentação de card) — se o esquema for inválido, a URL nem é salva; se a busca falhar
por outro motivo (host bloqueado, timeout), a tarefa é salva com a URL mas sem título. O
título salvo **nunca** vem do que o cliente enviou, mesmo que o cliente tenha chamado o
endpoint de preview antes.

## JWT (access token)

`usuarios/jwt_utils.py` continua sendo um HS256 manual (só biblioteca padrão), agora com
expiração:

```python
def gerar_token(usuario, ttl_segundos=None) -> str:
    ttl = ttl_segundos if ttl_segundos is not None else settings.ACCESS_TOKEN_TTL_SEGUNDOS
    agora = int(time.time())
    payload = {
        'id': usuario.id, 'nome': usuario.nome, 'sobrenome': usuario.sobrenome,
        'email': usuario.email, 'papel': usuario.papel,
        'iat': agora, 'exp': agora + ttl,
    }
    # header.payload em base64url, assinatura HMAC-SHA256 com settings.JWT_SECRET_KEY
```

- `ACCESS_TOKEN_TTL_SEGUNDOS = 15 * 60` (15 minutos) — vida curta de propósito.
- `verificar_token()` valida a assinatura (`hmac.compare_digest`) **e** confere `exp`
  antes de devolver o payload; levanta `ValueError` para token sem `exp` ou expirado,
  que `jwt_required` converte em `401`.
- `JWT_SECRET_KEY` é lido de `os.environ.get('JWT_SECRET_KEY', <fallback de dev>)` —
  **independente** do `SECRET_KEY` do Django (ver [[Projeto02/Melhorias]]). O fallback de
  desenvolvimento continua hardcoded no código, então o mesmo risco do item 7 de
  [[Projeto00/Vulnerabilidades]] (segredo commitado) ainda se aplica a ele se o projeto
  for exposto sem sobrescrever a variável de ambiente.

## Refresh token

`usuarios/refresh_utils.py` (novo) — token opaco de 48 bytes (`secrets.token_urlsafe`),
nunca um JWT:

- **Emissão** (`gerar_refresh_token`): cria um `RefreshToken` com o hash SHA-256 do
  valor bruto e `expira_em = agora + REFRESH_TOKEN_TTL_SEGUNDOS` (7 dias); devolve o
  valor bruto só para ser colocado direto no cookie.
- **Rotação** (`rotacionar_refresh_token`): busca pelo hash; se não existir → inválido;
  se já tiver `revogado_em` preenchido → **reuso detectado**, revoga todos os
  `RefreshToken` ativos daquele usuário (toda a sessão cai) e rejeita; se expirado →
  inválido; senão, marca o atual como revogado e emite um substituto, devolvendo também
  o `Usuario` para gerar um novo access token.
- **Revogação** (`revogar_refresh_token`): usado no logout, marca o token recebido como
  revogado sem emitir substituto.

## Rotas da API

Prefixo comum `/api`, montado em `api02/api02/urls.py` (idêntico ao [[Projeto01]]):
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('usuarios.urls')),
    path('api/', include('tarefas.urls')),
]
```

### `usuarios` (`usuarios/urls.py`)

| Método | Rota | View | Autenticação | CSRF | Input (body JSON) | Output |
|---|---|---|---|---|---|---|
| `GET`/`POST` | `/api/usuarios` | `usuarios_collection` → `listar_usuarios` / `cadastrar_usuario` | `GET`: `jwt_required` **+ `papel_required(PAPEL_ADMIN)`**; `POST`: nenhuma (pública) | isenta (`@csrf_exempt`) | `POST`: `{ nome, sobrenome, data_nascimento?, email, senha }`; `GET`: `?q=<termo>` opcional | `POST`: `201` + `Usuario`; `GET`: `200` + lista **ou** `403` se papel ≠ admin |
| `POST` | `/api/login` | `login` | nenhuma (pública) | isenta, mas seta cookie CSRF (`@ensure_csrf_cookie`) | `{ email, senha }` | `200` + `{ token }` + `Set-Cookie: refresh_token` **ou** `401` |
| `POST` | `/api/logout` | `logout` (novo) | `jwt_required` | protegida (exige `X-XSRF-TOKEN`) | — | `200` + `{}`, revoga e limpa o cookie `refresh_token` |
| `POST` | `/api/token/refresh` | `token_refresh` (novo) | cookie `refresh_token` | protegida | — | `200` + `{ token }` + novo `Set-Cookie: refresh_token` **ou** `401` |
| `GET` | `/api/usuarios/me` | `usuario_logado` | `jwt_required` | isenta | — | `200` + `Usuario` do token **ou** `401` |

`cadastrar_usuario` agora grava `senha=make_password(...)` em vez de `hash_md5(...)`.
`login` compara com `check_password()` e, no sucesso, emite **os dois tokens**: o access
token no corpo da resposta, o refresh token só no cookie `Set-Cookie: refresh_token=...;
HttpOnly; Path=/api; SameSite=Lax` (`Secure` quando `DEBUG=False`).

⚠️ `listar_usuarios` corrige a falha do [[Projeto01]] (item 5 de
[[Projeto01/Vulnerabilidades]]): agora exige `papel_required(Usuario.PAPEL_ADMIN)`, além
de `jwt_required` — chamar a rota com um token de usuário comum devolve `403`.

### `tarefas` (`tarefas/urls.py`) — idêntico ao [[Projeto01/Backend|api01]]

| Método | Rota | View | Checagem de posse | Input (body JSON) | Output |
|---|---|---|---|---|---|
| `GET` | `/api/usuarios/<usuario_id>/tarefas` | `listar_tarefas_por_usuario` | `usuario_id` da URL == `id` do token, senão `403` | `?nome=` opcional (ver ⚠️) | `200` + lista de `Tarefa` |
| `POST` | `/api/tarefas` | `criar_tarefa` | `usuario_id` sempre = `id` do token | `{ nome, descricao?, data_prazo?, estado?, url? }` | `201` + `Tarefa` criada (com `url_titulo` resolvido pelo backend) |
| `PUT` | `/api/tarefas/<tarefa_id>` | `tarefa_detalhe` | `tarefa.usuario_id` == `id` do token, senão `404` | `{ nome?, descricao?, data_prazo?, estado?, url? }` | `200` + `Tarefa` atualizada |
| `DELETE` | `/api/tarefas/<tarefa_id>` | `tarefa_detalhe` | idem acima | — | `204` sem corpo |
| `POST` | `/api/tarefas/preview-link` | `preview_link` (novo) | `jwt_required` | `{ url }` | `200` + `{ url, titulo }` **ou** `422` se a URL for inválida/bloqueada (ver "Preview de link", acima) |

⚠️ `GET /api/usuarios/<usuario_id>/tarefas?nome=<termo>` continua montando a consulta com
SQL cru e f-string — **sem alteração** em relação ao [[Projeto01/Backend|api01]]. Ver
[[Projeto01/Vulnerabilidades]] item 4.

## Bibliotecas (`requirements.txt`)

Idêntico ao [[Projeto01/Backend|api01]] — nenhuma biblioteca nova. O refresh token usa só
`secrets`/`hashlib` da biblioteca padrão; o hash de senha usa `django.contrib.auth`
(já instalado em `INSTALLED_APPS` desde o [[Projeto00]]).

| Pacote | Versão | Uso |
|---|---|---|
| `Django` | 6.1.1 | Framework web / ORM / admin / hashers de senha / CSRF |
| `django-cors-headers` | 4.9.0 | Middleware de CORS (agora restrito, com credenciais) |
| `asgiref` | 3.12.1 | Suporte ASGI |
| `sqlparse` | 0.6.0 | Dependência do Django |
| `tzdata` | 2026.4 | Dados de timezone |

## Configuração relevante (`api02/settings.py`)

Em relação ao [[Projeto01/Backend|api01]]:

- `JWT_SECRET_KEY` — nova, independente do `SECRET_KEY` (lida de
  `os.environ.get('JWT_SECRET_KEY', <fallback dev>)`).
- `ACCESS_TOKEN_TTL_SEGUNDOS = 900`, `REFRESH_TOKEN_TTL_SEGUNDOS = 604800`,
  `REFRESH_COOKIE_NAME = 'refresh_token'`.
- `REFRESH_COOKIE_SECURE = not DEBUG`, `REFRESH_COOKIE_SAMESITE = 'Lax'`.
- `MIDDLEWARE` ganha `django.middleware.csrf.CsrfViewMiddleware` (ausente desde o
  [[Projeto00]]).
- `CORS_ALLOWED_ORIGINS = ['http://localhost:4200']` e `CORS_ALLOW_CREDENTIALS = True`
  substituem `CORS_ALLOW_ALL_ORIGINS = True` (herdado sem alteração até o [[Projeto01]]).
- `CORS_ALLOW_HEADERS` estendido com `'x-xsrf-token'` (fora da lista default do
  `django-cors-headers`), necessário para o preflight do browser aceitar o header que o
  Angular envia.
- `CSRF_COOKIE_NAME = 'XSRF-TOKEN'`, `CSRF_HEADER_NAME = 'HTTP_X_XSRF_TOKEN'`,
  `CSRF_COOKIE_HTTPONLY = False` (precisa ser legível pelo Angular),
  `CSRF_COOKIE_SECURE = not DEBUG`, `CSRF_COOKIE_SAMESITE = 'Lax'`,
  `CSRF_TRUSTED_ORIGINS = ['http://localhost:4200']`.
- `SECRET_KEY`, `DEBUG = True` e `ALLOWED_HOSTS = ['*']` — **sem alteração**, herdados do
  [[Projeto00]] (ver [[Projeto00/Vulnerabilidades]] item 7).
