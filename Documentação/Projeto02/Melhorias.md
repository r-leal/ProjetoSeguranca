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
quem o lesse. O [[Projeto02/Frontend|client02]] não persiste mais o access token em
nenhum *storage* do browser: ele vive só numa variável privada do `AuthService`, perdida
a cada reload. A continuidade da sessão entre reloads passa a vir do refresh token, que
fica num cookie `HttpOnly` — inacessível a JavaScript, inclusive um XSS.

**Ressalva**: o payload do access token continua sendo decodificado no cliente
(`AuthService.usuarioLogado()`, sem verificar assinatura) para exibir nome/papel na UI.
Isso não é mais classificado como vulnerabilidade: o dado não persiste em lugar nenhum
fora da memória da aba atual, nenhuma decisão de autorização depende dele (sempre
reforçada no backend via `jwt_required`/`papel_required`), e o próprio
[[Projeto02/SegurancaAutorizacaoAcesso]] (seção 2) documenta esse uso como aceitável.

### Broken Access Control — listagem de usuários sem checar papel (item 5 de [[Projeto01/Vulnerabilidades]])

**Corrigida.** `usuarios/views.py:listar_usuarios` no [[Projeto01]] exigia só
`@jwt_required` — qualquer usuário autenticado, de qualquer papel, lia a lista completa
de usuários cadastrados. O [[Projeto02/Backend|api02]] adiciona
`@papel_required(Usuario.PAPEL_ADMIN)` (empilhado com `jwt_required` por cima, para que
`request.usuario` já exista quando o papel é checado) — chamar a rota com um token de
papel `usuario`/`gerente` agora devolve `403`. O guia
[[Projeto01/Ataque-A01-ListagemUsuariosSemChecarPapel]] **não funciona mais** contra o
[[Projeto02/Backend|api02]].

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
- **`CsrfViewMiddleware` ativado, protegendo as rotas que passam a depender de cookie**
  (`/token/refresh`, `/logout`): isso não é a correção retroativa do item 5 de
  [[Projeto00/Vulnerabilidades]] (CSRF desativado) — aquele item nunca foi de fato
  explorável nas rotas que autenticam por header `Authorization` (não há cookie
  ambiente para uma requisição forjada usar). É, antes, uma prevenção: a introdução do
  refresh token em cookie (seção 1) criou a primeira credencial de cookie real do
  projeto, e ela já nasce protegida por CSRF (`X-XSRF-TOKEN` exigido), em vez de
  introduzir uma exposição nova. As demais rotas continuam `@csrf_exempt`, de propósito,
  por autenticarem via header.
- **Access token em memória + `withCredentials` + retry automático em 401**
  (`client02/.../auth.interceptor.ts`, reescrito): o interceptor do [[Projeto01]] só
  anexava o header; o do [[Projeto02]] também envia cookies entre origens e, ao receber
  `401` (access token expirado), chama o refresh e repete a requisição original uma
  única vez — sem isso, a vida curta do access token (15 min) deslogaria o usuário com
  muita frequência.
- **`APP_INITIALIZER` para restaurar sessão no boot do app** (`app.config.ts`, novo):
  evita a corrida entre o reload de página (que perde o access token em memória) e o
  `ngOnInit` de componentes de rota, que antes rodariam achando que não havia sessão.
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
| 3 | Token sai do `localStorage`; access token só em memória, refresh token em cookie `HttpOnly` | Vulnerabilidade corrigida | — (decodificação sem verificar assinatura no cliente passa a ser uso documentado, não vulnerabilidade) |
| 4 | `GET /api/usuarios` exige papel admin no backend (`papel_required`) | Vulnerabilidade corrigida | — (totalmente resolvido) |
| 5 | CORS restrito a `http://localhost:4200` com credenciais | Vulnerabilidade corrigida (origem: [[Projeto00/Vulnerabilidades]] item 6) | — (totalmente resolvido) |
| 6 | Refresh token revogável, rotacionado, com detecção de reuso | Hardening/qualidade | — |
| 7 | `papel_required` como decorator reutilizável | Hardening/qualidade | — |
| 8 | `JWT_SECRET_KEY` separado do `SECRET_KEY` do Django | Hardening/qualidade | — (fallback de dev ainda hardcoded, mesma limitação residual do item 7 de [[Projeto00/Vulnerabilidades]]) |
| 9 | `CsrfViewMiddleware` protegendo as rotas que dependem de cookie | Hardening/qualidade | — |
| 10 | Interceptor com `withCredentials` + retry automático em 401; `APP_INITIALIZER` de restauração de sessão | Hardening/qualidade | — |
| 11 | Preview de link na tarefa, com defesas contra SSRF desde a primeira versão (`tarefas/link_preview.py`) | Funcionalidade nova, construída com hardening (não corrige nada pré-existente) | — |

Nenhuma destas comparações se estende a projetos anteriores ao [[Projeto01]] — mesmo
quando a falha de origem está catalogada em [[Projeto00/Vulnerabilidades]], a baseline de
"antes" usada aqui é sempre o estado em que o [[Projeto01]] a deixou.
